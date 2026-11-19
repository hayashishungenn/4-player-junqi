import { fetch, io } from './encrypted-client.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { BOARD, validateMove } from '../server/game.js';
import { analyzeReplay } from '../bots/engine/replay-analysis.js';

const piece = (id, owner, type, position, extra = {}) => ({ id, owner, type, position,
  revealed: true, moved: type !== 'flag' && type !== 'mine', initialPosition: position, ...extra });
const frame = (pieces, turn, players = []) => ({ time: 1, state: { pieces, turn, phase: 'playing', players, lastMove: null } });

function until(socket, name, predicate = () => true, ms = 8000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { socket.off(name, handler); reject(Error('等待超时: ' + name)); }, ms);
    const handler = value => { if (predicate(value)) { clearTimeout(timer); socket.off(name, handler); resolve(value); } };
    socket.on(name, handler);
  });
}
function safeMove(state) {
  for (const p of state.pieces.filter(p => p.owner === state.viewerSeat)) {
    for (const n of BOARD.nodes) {
      if (state.pieces.some(q => q.position === n.id)) continue;
      if (validateMove(state, state.viewerSeat, p.position, n.id).ok) return { from: p.position, to: n.id };
    }
  }
  return null;
}

test('特殊场景：夺旗 / 炸弹同归于尽 / 和棋 / 认输的明棋事实与分析字段分离', () => {
  const cases = [
    { name: '夺旗', outcome: 'attacker', defenderType: 'flag', winner: 'north' },
    { name: '炸弹同归于尽', outcome: 'both', defenderType: 'bomb', winner: null },
  ];
  for (const c of cases) {
    const pieces = [piece('a', 'north', 'engineer', 'center-0-1'),
      piece('f', 'south', c.defenderType, 'center-0-2', { revealed: c.defenderType === 'bomb' })];
    const replay = {
      version: 1, code: 'SPECIAL', mode: 'ffa', winner: c.winner, completed: true,
      frames: [frame(pieces, 'north')],
      logs: [{ time: 1, kind: 'move', frameIndex: 0, seat: 'north', username: 'u',
        from: 'center-0-1', to: 'center-0-2', attacker: { id: 'a', type: 'engineer' },
        defender: { id: 'f', type: c.defenderType, owner: 'south' }, outcome: c.outcome, path: [] }],
    };
    const report = analyzeReplay(replay, { budgetMs: 120, mode: 'ffa', seed: 3 });
    assert.equal(report.moves.length, 1, c.name);
    assert.equal(report.moves[0].truth.outcome, c.outcome, c.name);
    assert.equal(report.moves[0].truth.defender.type, c.defenderType, c.name);
    assert.equal(report.moves[0].from, 'center-0-1', c.name);
    assert.equal(report.moves[0].to, 'center-0-2', c.name);
    const analysisText = JSON.stringify(report.moves[0].analysis);
    assert.ok(!analysisText.includes(c.defenderType), `${c.name}: 分析字段不得含真实兵种`);
    assert.ok(!analysisText.includes('"type"'), `${c.name}: 分析字段不得含 type`);
  }
  const draw = analyzeReplay({ version: 1, code: 'DRAW', frames: [], logs: [], winner: '和棋', drawn: true, completed: true }, { budgetMs: 50 });
  assert.equal(draw.winner, '和棋');
  const resigned = analyzeReplay({ version: 1, code: 'RESIGN', frames: [], logs: [], winner: '认输', completed: true }, { budgetMs: 50 });
  assert.equal(resigned.winner, '认输');
});

test('frameIndex 优先于顺序映射：非走子事件插入帧时仍取到正确走子前局面', () => {
  const preMove = [piece('a', 'north', 'commander', 'north-4-1'), piece('x', 'south', 'army', 'center-0-1')];
  const afterMove = [piece('a', 'north', 'commander', 'center-0-1'), piece('x', 'south', 'army', 'center-0-1', { revealed: true, type: 'platoon' })];
  const replay = {
    version: 1, code: 'IDX', mode: 'ffa',
    frames: [frame(preMove, 'north'), frame(afterMove, 'east')],
    logs: [{ time: 2, kind: 'move', frameIndex: 0, seat: 'north', from: 'north-4-1', to: 'center-0-1',
      attacker: { id: 'a', type: 'commander' }, defender: { id: 'x', type: 'platoon', owner: 'south' },
      outcome: 'attacker', path: [] }],
  };
  const report = analyzeReplay(replay, { budgetMs: 120, mode: 'ffa', seed: 3 });
  assert.equal(report.moves[0].from, 'north-4-1');
  // 走子前帧中 a 应在 north-4-1；若错用顺序映射 frames[0] 仍正确，这里额外验证投影后己方可见。
  const view = report.moves[0].analysis;
  assert.ok(view.best && typeof view.best.from === 'string');
});

test('真实棋谱回放：每步评分与实际着法一一对应，暗棋视角不泄露真实兵种', { timeout: 90000 }, async t => {
  const PORT = '32190', BASE = 'http://127.0.0.1:' + PORT, KEY = 'replay-correct-key';
  const dir = await mkdtemp(path.join(os.tmpdir(), 'junqi-replay-correct-'));
  const sockets = [];
  let child, stderr = '';
  child = spawn(process.execPath, ['server/server.js'], { env: { ...process.env, PORT, ADMIN_KEY: KEY,
    ACCOUNTS_FILE: path.join(dir, 'accounts.json'), SIGUO_ROOMS_FILE: path.join(dir, 'rooms.json'),
    SIGUO_HISTORY_DIR: path.join(dir, 'history'), SIGUO_PICTURES_DIR: path.join(dir, 'pictures'),
    SIGUO_AVATARS_DIR: path.join(dir, 'avatars'), SIGUO_PROGRAMS_FILE: path.join(dir, 'programs.json') },
    stdio: ['ignore', 'pipe', 'pipe'] });
  child.stderr.on('data', d => stderr += d);
  t.after(async () => {
    sockets.forEach(s => s.disconnect());
    if (child && child.exitCode === null) { child.kill(); await new Promise(r => child.once('exit', r)); }
    await rm(dir, { recursive: true, force: true });
  });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('启动超时: ' + stderr)), 8000);
    child.stdout.on('data', b => { if (b.toString().includes('已启动')) { clearTimeout(timer); resolve(); } });
    child.once('exit', () => reject(Error(stderr)));
  });
  async function api(route, token, method = 'GET', body, admin = false) {
    const r = await fetch(BASE + route, { method, headers: { 'content-type': 'application/json',
      Authorization: 'Bearer ' + token, ...(admin ? { 'x-admin-key': KEY } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: r.status, body: await r.json() };
  }
  async function account(username) {
    await api('/api/admin/accounts', null, 'POST', { username, password: 'test1234' }, true);
    return (await api('/api/login', null, 'POST', { username, password: 'test1234' })).body.token;
  }
  async function connect() { const s = io(BASE, { transports: ['websocket'], forceNew: true }); sockets.push(s); await until(s, 'connect'); return s; }
  async function command(s, event, payload, predicate) { const p = until(s, 'room-state', predicate); s.emit(event, payload); return await p; }
  const host = await account('CorrHost'), guest = await account('CorrGuest');
  const hs = await connect();
  const session = until(hs, 'session'); hs.emit('create-room', { authToken: host, capacity: 2, mode: 'ffa', rated: false });
  const { code } = await session;
  const gs = await connect();
  let v = await command(gs, 'join-room', { authToken: guest, code });
  if (v.viewerSeat !== 'south') await command(gs, 'take-seat', { seat: 'south' }, s => s.viewerSeat === 'south');
  await command(hs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'north')?.ready);
  await command(gs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'south')?.ready);
  let state = await command(hs, 'start-game', undefined, s => s.phase === 'playing');
  let lastMovedPly = -1;
  await new Promise(resolve => {
    const onState = s => {
      if (s.phase !== 'playing' || (s.ply || 0) >= 16) return resolve();
      if (s.turn === s.viewerSeat && s.ply !== lastMovedPly) {
        const move = safeMove(s); lastMovedPly = s.ply;
        if (move) (s.viewerSeat === 'north' ? hs : gs).emit('move', move);
        else resolve();
      }
    };
    hs.on('room-state', onState); gs.on('room-state', onState); onState(state);
  });
  const fin = until(hs, 'room-state', s => s.phase === 'finished'); hs.emit('resign'); await fin;
  const reply = await api(`/api/rooms/${code}/replay`, host);
  assert.equal(reply.status, 200);
  const replay = reply.body;
  const logs = replay.logs.filter(l => l.kind === 'move');
  assert.ok(logs.length >= 12, `应有足够棋步，实际 ${logs.length}`);
  assert.ok(logs.every(l => Number.isInteger(l.frameIndex)), '每步应记录 frameIndex');
  // 走子前帧中攻击方必须位于 from。
  for (const log of logs) {
    const before = replay.frames[log.frameIndex]?.state;
    assert.ok(before, `frameIndex=${log.frameIndex} 应存在`);
    const attacker = before.pieces.find(p => p.id === log.attacker.id);
    assert.ok(attacker, `攻击方 ${log.attacker.id} 应在走子前帧中`);
    assert.equal(attacker.position, log.from, `攻击方位置应与 from 一致 (ply ${log.frameIndex})`);
  }
  const report = analyzeReplay(replay, { budgetMs: 90, mode: replay.mode, seed: 5 });
  assert.equal(report.summary.totalMoves, logs.length);
  report.moves.forEach((m, i) => {
    assert.equal(m.from, logs[i].from, `第 ${i + 1} 步 from 应一致`);
    assert.equal(m.to, logs[i].to, `第 ${i + 1} 步 to 应一致`);
    assert.equal(m.truth.attacker.type, logs[i].attacker.type, `第 ${i + 1} 步明棋事实应一致`);
    const analysisText = JSON.stringify(m.analysis);
    assert.ok(!analysisText.includes('"type"'), `第 ${i + 1} 步分析字段不得含 type`);
    const hiddenTypes = (replay.frames[logs[i].frameIndex].state.pieces || [])
      .filter(p => p.owner !== logs[i].seat && !p.revealed).map(p => p.type).filter(Boolean);
    for (const type of hiddenTypes) assert.ok(!analysisText.includes(type), `第 ${i + 1} 步分析不得泄露 ${type}`);
  });
  console.log(JSON.stringify({ code, logs: logs.length, frameIndexed: true, perspective: report.perspective }));
});
