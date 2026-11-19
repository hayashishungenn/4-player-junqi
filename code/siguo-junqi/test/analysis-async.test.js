import { fetch, io } from './encrypted-client.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { BOARD, validateMove } from '../server/game.js';

const PORT = '32180', BASE = 'http://127.0.0.1:' + PORT, KEY = 'async-test-key-123';

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

test('分析在 Worker 中运行：分析期间主线程 API 仍可低延迟响应', { timeout: 90000 }, async t => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'junqi-analysis-async-'));
  const sockets = [];
  let child, stderr = '';
  const env = () => ({ ...process.env, PORT, ADMIN_KEY: KEY,
    ACCOUNTS_FILE: path.join(dir, 'accounts.json'), SIGUO_ROOMS_FILE: path.join(dir, 'rooms.json'),
    SIGUO_HISTORY_DIR: path.join(dir, 'history'), SIGUO_PICTURES_DIR: path.join(dir, 'pictures'),
    SIGUO_AVATARS_DIR: path.join(dir, 'avatars'), SIGUO_PROGRAMS_FILE: path.join(dir, 'programs.json'),
    SIGUO_ANALYSIS_TOTAL_MS: '15000', SIGUO_ANALYSIS_WORKERS: '1' });
  child = spawn(process.execPath, ['server/server.js'], { env: env(), stdio: ['ignore', 'pipe', 'pipe'] });
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
    const response = await fetch(BASE + route, { method,
      headers: { 'content-type': 'application/json', Authorization: 'Bearer ' + token, ...(admin ? { 'x-admin-key': KEY } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  }
  async function account(username) {
    assert.equal((await api('/api/admin/accounts', null, 'POST', { username, password: 'test1234' }, true)).status, 201);
    return (await api('/api/login', null, 'POST', { username, password: 'test1234' })).body.token;
  }
  async function connect() {
    const s = io(BASE, { transports: ['websocket'], forceNew: true });
    sockets.push(s); await until(s, 'connect'); return s;
  }
  async function command(s, event, payload, predicate) {
    const p = until(s, 'room-state', predicate); s.emit(event, payload); return await p;
  }
  const host = await account('AsyncHost'), guest = await account('AsyncGuest');
  const hs = await connect();
  const session = until(hs, 'session');
  hs.emit('create-room', { authToken: host, capacity: 2, mode: 'ffa', rated: false });
  const { code } = await session;
  const gs = await connect();
  let v = await command(gs, 'join-room', { authToken: guest, code });
  if (v.viewerSeat !== 'south') await command(gs, 'take-seat', { seat: 'south' }, s => s.viewerSeat === 'south');
  await command(hs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'north')?.ready);
  await command(gs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'south')?.ready);
  let state = await command(hs, 'start-game', undefined, s => s.phase === 'playing');

  // 双方交替走子生成 24 步真实棋谱。
  let lastMovedPly = -1;
  await new Promise(resolve => {
    const onState = s => {
      if (s.phase !== 'playing') return resolve();
      if ((s.ply || 0) >= 24) return resolve();
      if (s.turn === s.viewerSeat && s.ply !== lastMovedPly) {
        const move = safeMove(s); lastMovedPly = s.ply;
        if (move) (s.viewerSeat === 'north' ? hs : gs).emit('move', move);
        else resolve();
      }
    };
    hs.on('room-state', onState); gs.on('room-state', onState);
    onState(state);
  });
  const pending = until(hs, 'room-state', s => s.phase === 'finished');
  hs.emit('resign'); state = await pending;
  assert.ok(state.ply >= 20, `应生成足够棋步，实际 ${state.ply}`);

  // 发起完整分析（不 await），同时测量主线程 API 延迟。
  const analysisPromise = api(`/api/rooms/${code}/analysis`, host, 'POST', { budgetMs: 220, maxMoves: 24 });
  const latencies = [];
  for (let i = 0; i < 8; i++) {
    const start = Date.now();
    const status = await api('/api/analysis/status', null);
    latencies.push(Date.now() - start);
    assert.equal(status.status, 200);
  }
  const report = await analysisPromise;
  assert.equal(report.status, 200, JSON.stringify(report.body));
  assert.equal(report.body.summary.totalMoves, 24);
  const maxLatency = Math.max(...latencies);
  assert.ok(maxLatency < 1500, `主线程请求不应被分析阻塞，最大延迟 ${maxLatency}ms`);
  assert.ok(report.body.persisted === true);
  console.log(JSON.stringify({ code, plies: state.ply, analyzed: report.body.summary.totalMoves,
    maxLatencyMs: maxLatency, latencies }));
});
