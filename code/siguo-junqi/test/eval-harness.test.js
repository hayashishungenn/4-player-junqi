import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const run = (args) => JSON.parse(execFileSync(process.execPath,
  ['scripts/eval-harness.js', ...args], { cwd: ROOT, encoding: 'utf8' }));

test('评测框架：相同种子下 random agent 完全可重复（纯种子驱动）', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'junqi-eval-repeat-'));
  const out1 = path.join(dir, 'a.jsonl'), out2 = path.join(dir, 'b.jsonl');
  const args = ['--games', '4', '--mode', 'ffa', '--agents', 'random,random',
    '--seed', '123', '--setups', '4'];
  run([...args, '--out', out1]);
  run([...args, '--out', out2]);
  // 去掉墙钟耗时字段后再比较（elapsedMs/ms 非确定性，棋步与结果由种子决定）。
  const strip = text => text.trim().split('\n').map(line => {
    const g = JSON.parse(line);
    for (const key of Object.keys(g.stats || {})) delete g.stats[key].ms;
    for (const m of g.moves || []) delete m.elapsedMs;
    delete g.elapsedMs;
    return JSON.stringify(g);
  });
  assert.deepEqual(strip(fs.readFileSync(out1, 'utf8')), strip(fs.readFileSync(out2, 'utf8')),
    'random agent 由种子完全驱动，相同种子的棋步与结果应一致');
  for (const line of fs.readFileSync(out1, 'utf8').trim().split('\n')) assert.equal(JSON.parse(line).error, null);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('评测框架：四座轮换、多种布阵、完整棋谱、无异常（StrongBot）', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'junqi-eval-test-'));
  const out1 = path.join(dir, 'a.jsonl');
  const args = ['--games', '6', '--mode', 'ffa', '--agents', 'strong:8,strong:20',
    '--seed', '123', '--setups', '4'];
  run([...args, '--out', out1]);
  const a = fs.readFileSync(out1, 'utf8');
  const games = a.trim().split('\n').map(JSON.parse);
  assert.equal(games.length, 6);
  const seatsSeen = new Set(), setupsSeen = new Set();
  for (const g of games) {
    assert.equal(g.error, null, '不应有 agent 异常');
    assert.ok(['flag', 'stalemate', 'auto-draw', 'ply-limit', 'normal'].includes(g.terminal), `终局类型 ${g.terminal}`);
    assert.ok(['north', 'east', 'south', 'west', '和棋', '未决'].includes(g.winner));
    assert.equal(Object.keys(g.agentsSeats).length, 4, '四个座位都应被 agent 控制');
    setupsSeen.add(g.setupIndex);
    // 第一个 agent 在轮换下应覆盖多个座位。
    const firstKey = Object.keys(g.agentsSeats).find(k => k.startsWith(g.agents[0] + '@'));
    seatsSeen.add(g.agentsSeats[firstKey]);
    assert.ok(Array.isArray(g.moves) && g.moves.length === g.plies, '每步都应记录棋谱');
    for (const m of g.moves) {
      assert.equal(typeof m.from, 'string');
      assert.equal(typeof m.to, 'string');
    }
  }
  assert.ok(seatsSeen.size >= 2, `座位应轮换，实际 ${[...seatsSeen]}`);
  assert.ok(setupsSeen.size >= 2, `布阵应多样化，实际 ${[...setupsSeen]}`);
  // 布阵由种子确定性生成：同一 setupIndex 的首步在两次独立运行中相同。
  const out2 = path.join(dir, 'b.jsonl');
  run([...args, '--out', out2]);
  const games2 = fs.readFileSync(out2, 'utf8').trim().split('\n').map(JSON.parse);
  for (let i = 0; i < games.length; i++) {
    assert.equal(games[i].setupIndex, games2[i].setupIndex);
    assert.equal(games[i].moves[0].from, games2[i].moves[0].from, '同布阵首步应一致（确定性）');
    assert.equal(games[i].moves[0].to, games2[i].moves[0].to);
  }
  fs.rmSync(dir, { recursive: true, force: true });
});

test('评测框架：联盟模式胜负按队伍计算（前期 bug 回归）', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'junqi-eval-alliance-'));
  const out = path.join(dir, 'a.jsonl');
  run(['--games', '4', '--mode', 'alliance', '--agents', 'strong:8,strong:20',
    '--seed', '9', '--setups', '3', '--out', out]);
  const games = fs.readFileSync(out, 'utf8').trim().split('\n').map(JSON.parse);
  for (const g of games) {
    assert.ok(g.plies > 0, '联盟对局不应开局即终局');
    assert.ok(['NS', 'EW', 'draw', 'unresolved'].includes(g.winningTeam), `队伍胜者 ${g.winningTeam}`);
    const ns = Object.values(g.agentTeams).filter(t => t === 'NS');
    const ew = Object.values(g.agentTeams).filter(t => t === 'EW');
    assert.equal(ns.length, 2); assert.equal(ew.length, 2);
  }
  fs.rmSync(dir, { recursive: true, force: true });
});

test('统计报告：胜率、置信区间、座位/布阵分项、pairwise Elo 输出且口径一致', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'junqi-eval-report-'));
  const out = path.join(dir, 'a.jsonl');
  run(['--games', '4', '--mode', 'ffa', '--agents', 'strong:8,strong:20',
    '--seed', '7', '--setups', '3', '--out', out]);
  const md = execFileSync(process.execPath, ['scripts/eval-report.js', out],
    { cwd: ROOT, encoding: 'utf8' });
  assert.match(md, /胜率/);
  assert.match(md, /95%CI/);
  assert.match(md, /座位分项/);
  assert.match(md, /布阵分项/);
  assert.match(md, /Elo/);
  assert.match(md, /未校准|代理指标|不等同/);
  fs.rmSync(dir, { recursive: true, force: true });
});
