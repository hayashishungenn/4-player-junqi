import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeReplay, projectFrame } from '../bots/engine/replay-analysis.js';

const piece = (id, owner, type, position, extra = {}) => ({
  id, owner, type, position, revealed: true, moved: type !== 'flag' && type !== 'mine',
  initialPosition: position, ...extra,
});
const frame = (pieces, turn) => ({ time: 1, state: { pieces, turn, phase: 'playing', lastMove: null, players: [] } });

function winningReplay(revealed = true) {
  const open = [
    piece('a', 'north', 'engineer', 'south-4-1'),
    piece('own', 'north', 'flag', 'north-5-1'),
    piece('f', 'south', 'flag', 'south-5-1', { revealed }),
    piece('enemy', 'south', 'army', 'north-4-1', { revealed }),
  ];
  const after = [
    { ...open[0], position: 'south-5-1' }, open[1],
    { ...open[2], position: null, revealed: true }, open[3],
  ];
  return {
    version: 1, code: 'TEST01', mode: 'ffa', winner: 'north', completed: true, startedAt: 1,
    frames: [frame(open, 'north'), frame(after, 'south')],
    logs: [{ kind: 'move', seat: 'north', username: 'alice', from: 'south-4-1', to: 'south-5-1',
      attacker: { id: 'a', type: 'engineer' }, defender: { id: 'f', type: 'flag', owner: 'south' },
      outcome: 'attacker', engineerTurn: false, path: ['south-4-1', 'south-5-1'] }],
  };
}

test('projectFrame 把对手暗子隐藏，己方与已公开子保留', () => {
  const replay = winningReplay(false);
  const view = projectFrame(replay.frames[0].state, 'north', 'ffa', ['north', 'south']);
  const own = view.pieces.find(p => p.id === 'own');
  const hidden = view.pieces.find(p => p.id === 'f');
  assert.equal(own.type, 'flag');
  assert.equal(hidden.type, null);
  assert.equal(view.records.find(p => p.id === 'a').type, 'engineer');
});

test('完整复盘报告：结构、评分曲线、明棋事实、视角标注', () => {
  const report = analyzeReplay(winningReplay(), { budgetMs: 350, seed: 3, mode: 'ffa' });
  assert.equal(report.summary.totalMoves, 1);
  assert.equal(report.moves.length, 1);
  assert.equal(report.curve.length, 1);
  assert.deepEqual(report.perspective, { analysis: 'dark', truth: 'open' });
  const move = report.moves[0];
  assert.equal(move.ply, 1);
  assert.equal(move.seat, 'north');
  assert.equal(move.analysis.best.from, 'south-4-1');
  assert.equal(move.analysis.best.to, 'south-5-1');
  assert.equal(move.analysis.errorClass, 'best');
  assert.equal(move.truth.defender.type, 'flag');
  assert.equal(move.truth.outcome, 'attacker');
  assert.ok(report.summary.perSeat.north.best >= 1);
  assert.ok(report.calibrationNote.includes('不是胜率'));
});

test('视角分离：分析字段不含真实兵种，明棋事实字段保留', () => {
  const report = analyzeReplay(winningReplay(false), { budgetMs: 300, seed: 5, mode: 'ffa' });
  const move = report.moves[0];
  const analysisText = JSON.stringify(move.analysis);
  assert.ok(!analysisText.includes('flag'), '分析字段不得出现真实兵种 flag');
  assert.ok(!analysisText.includes('engineer'), '分析字段不得出现真实兵种 engineer');
  assert.equal(move.truth.defender.type, 'flag', '明棋事实应保留真实兵种');
});

test('失误被标注进关键失误列表', () => {
  const replay = winningReplay();
  replay.logs[0].from = 'south-4-1';
  replay.logs[0].to = 'south-4-0'; // 离开夺旗点
  const report = analyzeReplay(replay, { budgetMs: 400, seed: 7, mode: 'ffa' });
  assert.equal(report.moves[0].analysis.errorClass, 'blunder');
  assert.equal(report.blunders.length, 1);
  assert.equal(report.blunders[0].ply, 1);
});

test('空棋谱稳健返回', () => {
  const report = analyzeReplay({ version: 1, frames: [], logs: [] }, { budgetMs: 50 });
  assert.equal(report.summary.totalMoves, 0);
  assert.equal(report.moves.length, 0);
  assert.ok(report.warnings.some(w => w.includes('没有局面帧')));
});
