import { fetch, io } from './encrypted-client.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { BOARD, validateMove } from '../server/game.js';

const PORT = '32160', BASE = 'http://127.0.0.1:' + PORT;

function until(socket, name, predicate = () => true, ms = 15000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { socket.off(name, handler); reject(Error('等待超时: ' + name)); }, ms);
    const handler = value => { if (predicate(value)) { clearTimeout(timer); socket.off(name, handler); resolve(value); } };
    socket.on(name, handler);
  });
}

// 真人视角：找一个合法着法（validateMove 只看位置/归属，暗子 type=null 不影响）。
function safeMove(state) {
  for (const p of state.pieces.filter(p => p.owner === state.viewerSeat)) {
    for (const n of BOARD.nodes) {
      if (state.pieces.some(q => q.position === n.id)) continue;
      if (validateMove(state, state.viewerSeat, p.position, n.id).ok) return { from: p.position, to: n.id };
    }
  }
  return null;
}

test('1 真人 + 3 AI 四方联盟端到端：四方轮流、结盟、落子合法、棋谱推进', { timeout: 120000 }, async t => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'junqi-alliance-e2e-'));
  const server = spawn(process.execPath, ['server/server.js'], {
    env: { ...process.env, PORT, ADMIN_KEY: 'e2e-admin-key-123',
      ACCOUNTS_FILE: path.join(dir, 'accounts.json'), SIGUO_ROOMS_FILE: path.join(dir, 'rooms.json'),
      SIGUO_PICTURES_DIR: path.join(dir, 'pictures'), SIGUO_AVATARS_DIR: path.join(dir, 'avatars'),
      SIGUO_PROGRAMS_FILE: path.join(dir, 'programs.json'), SIGUO_HISTORY_DIR: path.join(dir, 'history') },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = ''; let socket;
  server.stderr.on('data', d => stderr += d);
  t.after(async () => {
    socket?.disconnect();
    await new Promise(resolve => { if (server.exitCode !== null) return resolve(); server.once('exit', resolve); server.kill(); });
    await rm(dir, { recursive: true, force: true });
  });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('服务器启动超时: ' + stderr)), 8000);
    server.stdout.on('data', b => { if (b.toString().includes('已启动')) { clearTimeout(timer); resolve(); } });
    server.once('error', reject);
  });
  async function api(route, token, method = 'GET', body, admin = false) {
    const response = await fetch(BASE + route, { method,
      headers: { 'content-type': 'application/json', Authorization: 'Bearer ' + token, ...(admin ? { 'x-admin-key': 'e2e-admin-key-123' } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  }
  async function account(username, accountType) {
    assert.equal((await api('/api/admin/accounts', null, 'POST', { username, password: 'test1234', accountType }, true)).status, 201);
    const login = await api('/api/login', null, 'POST', { username, password: 'test1234' });
    assert.equal(login.status, 200);
    return login.body.token;
  }
  const host = await account('E2EHost', 'human');
  const bots = {};
  for (const name of ['E2EEast', 'E2ESouth', 'E2EWest']) bots[name] = await account(name, 'bot');
  const program = await readFile('public/bot-studio-bot.js', 'utf8');
  for (const [name, token] of Object.entries(bots)) {
    assert.equal((await api('/api/program', token, 'PUT', { source: program })).status, 200);
  }

  socket = io(BASE, { transports: ['websocket'], forceNew: true });
  await until(socket, 'connect');
  const session = until(socket, 'session');
  socket.emit('create-room', { authToken: host, capacity: 4, mode: 'alliance', rated: false });
  const { code } = await session;
  assert.ok(code);

  let pending, state;
  const log = m => console.error(`[E2E ${new Date().toISOString().slice(11, 19)}] ${m}`);
  log('房间已创建 ' + code);
  // 三个 AI 先落座 east/south/west（添加 bot 会重置所有人的准备/布阵）。
  for (const [seat, name] of [['east', 'E2EEast'], ['south', 'E2ESouth'], ['west', 'E2EWest']]) {
    pending = until(socket, 'room-state', s => s.players.some(p => p.name === 'BOT · ' + name && p.seat === seat));
    socket.emit('add-bot', { username: name, seat }); await pending;
  }
  log('三个 AI 已落座');
  for (const [name, token] of Object.entries(bots)) {
    assert.equal((await api('/api/program/run', token, 'POST', { enabled: true })).status, 200);
  }
  log('三个 AI 托管程序已启用');
  // 真人布阵：随机布阵 + 准备（在 add-bot 之后）。
  pending = until(socket, 'room-state', s => s.ply === 0);
  socket.emit('randomize-setup');
  pending = until(socket, 'room-state', s => s.players.find(p => p.seat === s.viewerSeat)?.ready);
  socket.emit('toggle-ready'); await pending;
  log('真人已布阵并准备');
  pending = until(socket, 'room-state', s => s.players.every(p => !p.empty && p.ready));
  await pending;
  log('全员准备就绪');

  // 开局。
  pending = until(socket, 'room-state', s => s.phase === 'playing');
  socket.emit('start-game'); state = await pending;
  log('对局已开始 turn=' + state.turn);
  assert.equal(state.mode, 'alliance');
  assert.equal(state.capacity, 4);
  assert.equal(state.players.filter(p => p.isBot).length, 3);

  const seatsSeen = new Set();
  let plies = 0, finished = null, errors = [];
  socket.on('game-error', e => errors.push(e));
  const deadline = Date.now() + 100000;
  await new Promise((resolve) => {
    let lastLog = 0, lastMovedPly = -1;
    const onState = s => {
      if (s.lastMove?.seat) seatsSeen.add(s.lastMove.seat);
      plies = s.ply || 0;
      if (plies !== lastLog) { log(`ply=${plies} turn=${s.turn} phase=${s.phase}`); lastLog = plies; }
      if (s.phase === 'finished') { finished = s; socket.off('room-state', onState); return resolve(); }
      if (s.phase === 'playing' && s.turn === s.viewerSeat && !s.drawOffer && plies !== lastMovedPly) {
        const move = safeMove(s);
        lastMovedPly = plies;
        if (move) { log(`真人走子 ${move.from}->${move.to}`); socket.emit('move', move); }
        else { log('真人无合法着法'); socket.off('room-state', onState); return resolve(); }
      }
      if (plies >= 12 || Date.now() > deadline) { socket.off('room-state', onState); resolve(); }
    };
    socket.on('room-state', onState);
    onState(state); // 立即处理开局状态（可能已轮到真人）
  });

  assert.ok(plies >= 4, `棋步应推进，实际 ${plies}`);
  assert.ok(seatsSeen.size >= 3, `应观察到多方行棋，实际 ${[...seatsSeen]}`);
  assert.ok(errors.length === 0, `不应有 game-error: ${errors.join('; ')}`);
  if (finished) {
    assert.ok(typeof finished.winner === 'string' && finished.winner.length > 0, '终局应有胜者或和棋标记');
  }
  // 若尚未终局，用管理员接口强制结束（alliance 下个人认输只淘汰该方），再取完整棋谱。
  if (!finished) {
    pending = until(socket, 'room-state', s => s.phase === 'finished');
    const fin = await api(`/api/admin/rooms/${code}/finish`, null, 'POST', {}, true);
    assert.equal(fin.status, 200, JSON.stringify(fin.body));
    finished = await pending;
    log('对局已结束 winner=' + finished.winner);
  }
  const replay = await api(`/api/rooms/${code}/replay`, host);
  assert.equal(replay.status, 200);
  assert.ok(replay.body.frames.length >= 2, '应记录棋谱帧');
  assert.ok(replay.body.logs.length >= 4, '应记录至少 4 步棋谱');
  assert.ok(replay.body.logs.some(l => l.kind === 'move' && l.from && l.to), '棋谱应含走步明细');
  console.log(JSON.stringify({ code, plies, seatsSeen: [...seatsSeen], finished: !!finished,
    winner: finished?.winner || null, frames: replay.body.frames.length, logs: replay.body.logs.length }));
});
