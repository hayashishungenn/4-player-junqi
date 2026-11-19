import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeReplay } from '../bots/engine/replay-analysis.js';
import { submitAnalysis, analysisStats, taskKey, MAX_CONCURRENT } from '../server/analysis-runner.js';

const piece = (id, owner, type, position) => ({ id, owner, type, position,
  revealed: true, moved: type !== 'flag' && type !== 'mine', initialPosition: position });
const frame = (pieces, turn) => ({ time: 1, state: { pieces, turn, phase: 'playing', players: [] } });
function replayWith(plies = 1) {
  const frames = [], logs = [];
  for (let i = 0; i < plies; i++) {
    const pieces = [piece('a', 'north', 'engineer', 'center-0-1'),
      piece('own', 'north', 'flag', 'north-5-1'), piece('f', 'south', 'flag', 'south-5-1')];
    frames.push(frame(pieces, 'north'));
    logs.push({ time: i + 1, kind: 'move', seat: 'north', username: 'u' + i,
      from: 'center-0-1', to: 'center-0-2', attacker: { id: 'a', type: 'engineer' },
      defender: null, outcome: 'move', path: [] });
  }
  return { version: 1, code: 'RUNNER', mode: 'ffa', frames, logs };
}

test('整局预算耗尽时标记未分析步骤并给出警告', () => {
  const report = analyzeReplay(replayWith(6), { budgetMs: 120, totalBudgetMs: 1, mode: 'ffa', seed: 3 });
  assert.ok(report.summary.totalMoves === 6);
  assert.ok(report.moves.every(m => m.analysis.errorClass === 'unanalyzed' || m.analysis.ok !== undefined));
  assert.ok(report.warnings.some(w => w.includes('预算耗尽')) || report.moves.some(m => m.analysis.errorClass === 'unanalyzed'));
});

test('任务键包含房间、预算与日志规模，内容变化则键变化', () => {
  const a = replayWith(2), b = replayWith(3);
  const keyA = taskKey({ code: 'X', maxMoves: 60, budgetMs: 150, replay: a });
  assert.equal(keyA, taskKey({ code: 'X', maxMoves: 60, budgetMs: 150, replay: a }));
  assert.notEqual(keyA, taskKey({ code: 'X', maxMoves: 60, budgetMs: 150, replay: b }));
  assert.notEqual(keyA, taskKey({ code: 'X', maxMoves: 40, budgetMs: 150, replay: a }));
});

test('去重：相同任务键复用同一 Promise，统计 deduped 增长', async () => {
  const replay = replayWith(2);
  const key = 'dedupe-' + Date.now();
  const before = analysisStats().deduped;
  const [a, b] = await Promise.all([
    submitAnalysis(key, replay, { budgetMs: 60, mode: 'ffa', seed: 3, totalBudgetMs: 4000 }),
    submitAnalysis(key, replay, { budgetMs: 60, mode: 'ffa', seed: 3, totalBudgetMs: 4000 }),
  ]);
  assert.equal(a.summary.totalMoves, 2);
  assert.equal(a.summary.totalMoves, b.summary.totalMoves);
  assert.ok(analysisStats().deduped > before);
});

test('并发上限：多任务运行时活动 Worker 数不超过上限', async () => {
  const before = analysisStats().submitted;
  const jobs = [];
  for (let i = 0; i < MAX_CONCURRENT + 3; i++) {
    jobs.push(submitAnalysis('concurrent-' + Date.now() + '-' + i, replayWith(1),
      { budgetMs: 50, mode: 'ffa', seed: i, totalBudgetMs: 4000 }));
  }
  const reports = await Promise.all(jobs);
  assert.equal(reports.length, MAX_CONCURRENT + 3);
  assert.ok(reports.every(r => r.summary.totalMoves === 1));
  assert.equal(analysisStats().submitted - before, MAX_CONCURRENT + 3);
});

test('超时终止：Worker 超时被 terminate，返回 ANALYSIS_TIMEOUT 且统计记录', async () => {
  const before = analysisStats().timedOut;
  await assert.rejects(
    submitAnalysis('timeout-' + Date.now(), replayWith(1),
      { budgetMs: 50, totalBudgetMs: 50, simulateTimeoutMs: 20000 }),
    error => error.code === 'ANALYSIS_TIMEOUT',
  );
  assert.ok(analysisStats().timedOut > before, 'timedOut 计数应增长');
});

test('失败报告：非法 replay 数据返回 ANALYSIS_FAILED 而非崩溃', async () => {
  await assert.rejects(
    submitAnalysis('fail-' + Date.now(), null,
      { budgetMs: 50, totalBudgetMs: 4000 }),
    error => !!error.code && error.code.startsWith('ANALYSIS_'),
  );
});
