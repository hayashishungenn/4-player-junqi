import test from 'node:test';
import assert from 'node:assert/strict';
import { DIFFICULTY_LEVELS, resolveDifficulty, engineOptions } from '../bots/engine/difficulty.js';

test('五档难度预算与采样随档位单调递增', () => {
  assert.equal(DIFFICULTY_LEVELS.length, 5);
  for (let i = 1; i < DIFFICULTY_LEVELS.length; i++) {
    assert.ok(DIFFICULTY_LEVELS[i].budgetMs > DIFFICULTY_LEVELS[i - 1].budgetMs);
    assert.ok(DIFFICULTY_LEVELS[i].maxSamples > DIFFICULTY_LEVELS[i - 1].maxSamples);
    assert.ok(DIFFICULTY_LEVELS[i].maxDepth >= DIFFICULTY_LEVELS[i - 1].maxDepth);
  }
});

test('按 id 与名称解析档位', () => {
  assert.equal(resolveDifficulty(3).name, '中级');
  assert.equal(resolveDifficulty('5').name, '大师');
  assert.equal(resolveDifficulty('初级').id, 2);
  assert.equal(resolveDifficulty(' 高级 ').id, 4);
  assert.equal(resolveDifficulty(0), null);
  assert.equal(resolveDifficulty(99), null);
  assert.equal(resolveDifficulty('菜鸟'), null);
  assert.equal(resolveDifficulty(null), null);
});

test('引擎选项映射与覆盖校验', () => {
  const opts = engineOptions(3);
  assert.equal(opts.level, 3);
  assert.equal(opts.budgetMs, 1000);
  assert.equal(opts.maxSamples, 32);
  assert.equal(opts.maxDepth, 4);
  const custom = engineOptions('大师', { budgetMs: 2500, maxSamples: 40 });
  assert.equal(custom.budgetMs, 2500);
  assert.equal(custom.maxSamples, 40);
  assert.equal(custom.maxDepth, 5);
  assert.throws(() => engineOptions(2, { budgetMs: 0 }), /正数/);
  assert.throws(() => engineOptions(2, { maxDepth: 0 }), /正整数/);
  assert.throws(() => engineOptions('未知'), /未知难度/);
});
