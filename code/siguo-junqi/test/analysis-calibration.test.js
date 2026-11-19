import test from 'node:test';
import assert from 'node:assert/strict';
import { validateMove } from '../server/game.js';
import { botView } from '../bots/engine/bot.js';
import { evaluateMoveSet, CALIBRATION_NOTE } from '../bots/engine/analysis.js';

function seeded(seed) { return () => ((seed = (1664525 * seed + 1013904223) >>> 0) / 4294967296); }
const piece = (id, owner, type, position, revealed = true) => ({ id, owner, type, position, revealed,
  moved: type !== 'flag' && type !== 'mine', initialPosition: position });
const room = pieces => ({ phase: 'playing', turn: 'north', mode: 'ffa', activeSeats: ['north', 'south'], pieces });

const flagBoard = () => [
  piece('a', 'north', 'engineer', 'south-4-1'), piece('f', 'south', 'flag', 'south-5-1'),
  piece('own', 'north', 'flag', 'north-5-1'), piece('enemy', 'south', 'army', 'north-4-1'),
];
const engageBoard = () => [
  piece('a', 'north', 'commander', 'center-0-1'), piece('x', 'south', 'army', 'center-0-2', false),
  piece('own', 'north', 'flag', 'north-5-1'), piece('f', 'south', 'flag', 'south-5-1', false),
];

test('校准：候选覆盖率被量化，穷尽/非穷尽正确标注', () => {
  const many = evaluateMoveSet(botView(room(flagBoard()), 'north'), null, [], { budgetMs: 200, maxCandidates: 14, rng: seeded(1) });
  assert.equal(many.coverage.legalMoves > 14, true);
  assert.equal(many.coverage.evaluated <= 14 + 1, true);
  assert.equal(many.coverage.ratio < 1, true);
  assert.equal(many.coverage.exhaustive, false);
  assert.ok(many.moveClasses.unsearchedPotentialBest.includes('未知'));

  const few = evaluateMoveSet(botView(room(engageBoard()), 'north'), null, [], { budgetMs: 200, maxCandidates: 14, rng: seeded(1) });
  assert.equal(few.coverage.exhaustive, true, '合法着法不多于候选上限时应穷尽');
  assert.ok(few.moveClasses.unsearchedPotentialBest.includes('无（已穷尽'));
});

test('校准：四类着法区分明确，不把 best 描述为全局最优', () => {
  const r = evaluateMoveSet(botView(room(flagBoard()), 'north'),
    { from: 'south-4-1', to: 'south-4-0' }, [], { budgetMs: 250, rng: seeded(3) });
  assert.ok(r.moveClasses.bestCandidate, '应有根先验最佳候选');
  assert.ok(r.moveClasses.bestEvaluated, '应有已搜索候选最优');
  assert.deepEqual(r.moveClasses.actualMove, { from: 'south-4-1', to: 'south-4-0' });
  assert.ok(r.moveClasses.unsearchedPotentialBest.length > 0);
  assert.ok(CALIBRATION_NOTE.includes('不是胜率'));
  assert.ok(r.explanation.includes('不是胜率'));
});

test('校准：同一局面相同种子重复分析完全一致', () => {
  const view = botView(room(flagBoard()), 'north');
  const a = evaluateMoveSet(view, { from: 'south-4-1', to: 'south-5-1' }, [], { budgetMs: 300, rng: seeded(11) });
  const b = evaluateMoveSet(view, { from: 'south-4-1', to: 'south-5-1' }, [], { budgetMs: 300, rng: seeded(11) });
  const strip = r => { const { elapsedMs, ...rest } = r; return JSON.stringify(rest); };
  assert.equal(strip(a), strip(b), '相同种子的重复分析应逐字段一致');
});

test('校准：关键战术漏检可被错误等级识别', () => {
  const view = botView(room(flagBoard()), 'north');
  const bad = { from: 'south-4-1', to: 'south-4-0' };
  assert.ok(validateMove(room(flagBoard()), 'north', bad.from, bad.to).ok);
  const r = evaluateMoveSet(view, bad, [], { budgetMs: 350, rng: seeded(7) });
  assert.ok(['mistake', 'blunder'].includes(r.errorClass), `劣着应被识别，实际 ${r.errorClass}`);
  assert.ok(r.scoreLoss > 1000, `应产生显著分差，实际 ${r.scoreLoss}`);
});
