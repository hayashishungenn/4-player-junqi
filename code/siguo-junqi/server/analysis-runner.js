// 棋谱分析任务调度器（P7.2）
//
// 目标：把 analyzeReplay 的 CPU 密集计算放进 Worker Threads，避免阻塞 Node 主事件循环；
// 限制整局总预算与最大并发；相同任务去重；超时终止；失败可报告。
// 对外 submitAnalysis() 返回 Promise，解析为与同步版完全相同结构的报告，保持 API 兼容。

import { Worker } from 'node:worker_threads';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_FILE = path.join(__dirname, 'analysis-worker.js');

export const MAX_CONCURRENT = Math.max(1, Number(process.env.SIGUO_ANALYSIS_WORKERS) || 2);
export const MAX_TOTAL_BUDGET_MS = Math.max(50, Math.min(120000, Number(process.env.SIGUO_ANALYSIS_MAX_MS) || 30000));
const DEFAULT_TOTAL_BUDGET_MS = Math.max(50, Math.min(MAX_TOTAL_BUDGET_MS, Number(process.env.SIGUO_ANALYSIS_TOTAL_MS) || 12000));
const DEDUPE_TTL_MS = 60000;
const TIMEOUT_GRACE_MS = 3000;

const queue = [];
const tasks = new Map(); // key -> { promise, createdAt }
const stats = { submitted: 0, completed: 0, failed: 0, timedOut: 0, deduped: 0, active: 0 };
let processing = false;

function pump() {
  if (processing) return;
  processing = true;
  const loop = () => {
    while (stats.active < MAX_CONCURRENT && queue.length) {
      const job = queue.shift();
      stats.active += 1;
      runJob(job).then(job.resolve, job.reject).finally(() => {
        stats.active -= 1;
        loop();
      });
    }
    processing = false;
  };
  loop();
}

function runJob(job) {
  return new Promise((resolve, reject) => {
    let worker;
    try {
      worker = new Worker(WORKER_FILE, {
        workerData: { replay: job.replay, options: job.options },
      });
    } catch (error) {
      reject(error);
      return;
    }
    let settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      worker.terminate().catch(() => {});
      fn(value);
    };
    const timer = setTimeout(() => {
      stats.timedOut += 1;
      finish(reject, Object.assign(new Error('整局分析超过计算预算，已终止'), { code: 'ANALYSIS_TIMEOUT' }));
    }, job.totalBudgetMs + TIMEOUT_GRACE_MS);
    worker.once('message', message => {
      if (!message?.ok) {
        finish(reject, Object.assign(new Error(message?.error || '分析任务失败'), { code: 'ANALYSIS_FAILED' }));
        return;
      }
      finish(resolve, message.report);
    });
    worker.once('error', error => {
      finish(reject, Object.assign(error, { code: 'ANALYSIS_WORKER_ERROR' }));
    });
    worker.once('exit', code => {
      if (!settled) finish(reject, Object.assign(new Error(`分析 Worker 异常退出(${code})`), { code: 'ANALYSIS_WORKER_EXIT' }));
    });
    worker.postMessage(job.message);
  });
}

/** 提交分析任务；相同 key 在缓存期内复用同一 Promise（去重）。 */
export function submitAnalysis(key, replay, options = {}) {
  const existing = tasks.get(key);
  if (existing) {
    stats.deduped += 1;
    return existing.promise;
  }
  const totalBudgetMs = Math.max(50, Math.min(MAX_TOTAL_BUDGET_MS,
    Number(options.totalBudgetMs) || DEFAULT_TOTAL_BUDGET_MS));
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  const entry = { promise, createdAt: Date.now(), key };
  tasks.set(key, entry);
  stats.submitted += 1;
  const job = {
    replay, options: { ...options, totalBudgetMs }, totalBudgetMs,
    message: { replay, options: { ...options, totalBudgetMs }, simulateTimeoutMs: options.simulateTimeoutMs },
    resolve: value => { stats.completed += 1; resolve(value); },
    reject: error => { stats.failed += 1; reject(error); },
  };
  queue.push(job);
  pump();
  // 缓存期内再次提交相同 key 直接复用；过期后清理，避免无界增长。
  setTimeout(() => { if (tasks.get(key) === entry) tasks.delete(key); }, DEDUPE_TTL_MS).unref?.();
  return promise;
}

export function analysisStats() {
  return { ...stats, queued: queue.length, maxConcurrent: MAX_CONCURRENT,
    maxTotalBudgetMs: MAX_TOTAL_BUDGET_MS, defaultTotalBudgetMs: DEFAULT_TOTAL_BUDGET_MS };
}

export function taskKey({ code, maxMoves, budgetMs, replay }) {
  const logs = replay.logs || [], frames = replay.frames || [];
  const marker = `${code}|${maxMoves}|${budgetMs}|${logs.length}|${frames.length}|${logs.at(-1)?.time || 0}|${frames.at(-1)?.time || 0}`;
  return marker;
}
