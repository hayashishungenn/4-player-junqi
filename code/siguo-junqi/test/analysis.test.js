import test from 'node:test';
import assert from 'node:assert/strict';
import { validateMove } from '../server/game.js';
import { botView } from '../bots/engine/bot.js';
import { classifyLoss, evaluateMoveSet, CALIBRATION_NOTE } from '../bots/engine/analysis.js';

function seeded(seed) { return () => ((seed = (1664525 * seed + 1013904223) >>> 0) / 4294967296); }
const piece = (id, owner, type, position, revealed = true) => ({
  id, owner, type, position, revealed, moved: type !== 'flag' && type !== 'mine',
});
const position = pieces => ({ phase: 'playing', turn: 'north', mode: 'ffa', activeSeats: ['north', 'south'], pieces });

test('错误等级按引擎分差分级', () => {
  assert.equal(classifyLoss(0), 'best');
  assert.equal(classifyLoss(30), 'best');
  assert.equal(classifyLoss(31), 'good');
  assert.equal(classifyLoss(100), 'good');
  assert.equal(classifyLoss(101), 'inaccuracy');
  assert.equal(classifyLoss(350), 'inaccuracy');
  assert.equal(classifyLoss(351), 'mistake');
  assert.equal(classifyLoss(1000), 'mistake');
  assert.equal(classifyLoss(1001), 'blunder');
});

test('夺旗局面：实际着法即最佳，分差为 0，候选全部合法', () => {
  const room = position([
    piece('a', 'north', 'engineer', 'south-4-1'),
    piece('f', 'south', 'flag', 'south-5-1'),
    piece('own', 'north', 'flag', 'north-5-1'),
    piece('enemy', 'south', 'army', 'north-4-1'),
  ]);
  const move = { from: 'south-4-1', to: 'south-5-1' };
  assert.ok(validateMove(room, 'north', move.from, move.to).ok);
  const result = evaluateMoveSet(botView(room, 'north'), move, [], { budgetMs: 350, rng: seeded(3) });
  assert.equal(result.ok, true);
  assert.equal(result.best.from, move.from);
  assert.equal(result.best.to, move.to);
  assert.equal(result.scoreLoss, 0);
  assert.equal(result.errorClass, 'best');
  assert.equal(result.infoView, 'dark');
  assert.ok(result.samples >= 1);
  assert.ok(result.depth >= 1);
  assert.ok(result.candidates.length >= 1);
  for (const c of result.candidates) assert.ok(validateMove(room, 'north', c.from, c.to).ok, `${c.from}>${c.to} 应合法`);
  assert.ok(result.explanation.includes(CALIBRATION_NOTE));
});

test('离开夺旗点属于严重失误，产生正分差与风险解释', () => {
  const room = position([
    piece('a', 'north', 'engineer', 'south-4-1'),
    piece('f', 'south', 'flag', 'south-5-1'),
    piece('own', 'north', 'flag', 'north-5-1'),
    piece('enemy', 'south', 'army', 'north-4-1'),
  ]);
  const best = { from: 'south-4-1', to: 'south-5-1' };
  const bad = { from: 'south-4-1', to: 'south-4-0' };
  assert.ok(validateMove(room, 'north', bad.from, bad.to).ok);
  const result = evaluateMoveSet(botView(room, 'north'), bad, [], { budgetMs: 450, rng: seeded(7) });
  assert.equal(result.ok, true);
  assert.equal(result.best.from, best.from);
  assert.equal(result.best.to, best.to);
  assert.ok(result.scoreLoss > 1000, `分差应显著，实际 ${result.scoreLoss}`);
  assert.equal(result.errorClass, 'blunder');
  assert.ok(result.explanation.includes('大本营'));
  assert.ok(result.explanation.includes(CALIBRATION_NOTE));
});

test('一致信息视角：对手真实暗子身份不影响评分结果', () => {
  const build = hiddenType => position([
    piece('a', 'north', 'engineer', 'south-4-1'),
    { id: 'f', owner: 'south', type: hiddenType, position: 'south-5-1', revealed: false, moved: false, initialPosition: 'south-5-1' },
    piece('own', 'north', 'flag', 'north-5-1'),
    piece('enemy', 'south', 'army', 'north-4-1'),
  ]);
  const viewFlag = botView(build('flag'), 'north');
  const viewMine = botView(build('mine'), 'north');
  assert.deepEqual(viewFlag, viewMine, '暗棋视角应完全一致');
  const move = { from: 'south-4-1', to: 'south-5-1' };
  const a = evaluateMoveSet(viewFlag, move, [], { budgetMs: 300, rng: seeded(11) });
  const b = evaluateMoveSet(viewMine, move, [], { budgetMs: 300, rng: seeded(11) });
  // 采样数/分数依赖墙钟预算，只断言稳定的语义属性，不逐值比较。
  assert.equal(a.infoView, 'dark');
  assert.equal(b.infoView, 'dark');
  assert.equal(a.ok, b.ok);
  assert.equal(a.errorClass, b.errorClass);
  assert.equal(a.best.from, b.best.from);
  assert.equal(a.best.to, b.best.to);
  const text = JSON.stringify({ a, b });
  assert.ok(!text.includes('"type"'));
  assert.ok(!text.includes('mine'));
});
