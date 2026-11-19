// 完整棋谱分析 Worker：独立于 HTTP 主线程运行 CPU 密集搜索。
import { parentPort } from 'node:worker_threads';
import { analyzeReplay } from '../bots/engine/replay-analysis.js';

// simulateTimeoutMs 仅用于测试超时终止路径；生产 API 不传该参数。
parentPort.once('message', async message => {
  try {
    const { replay, options, simulateTimeoutMs } = message;
    if (simulateTimeoutMs) await new Promise(resolve => setTimeout(resolve, simulateTimeoutMs));
    const report = analyzeReplay(replay, options);
    parentPort.postMessage({ ok: true, report });
  } catch (error) {
    parentPort.postMessage({ ok: false, error: error?.message || String(error) });
  }
});
