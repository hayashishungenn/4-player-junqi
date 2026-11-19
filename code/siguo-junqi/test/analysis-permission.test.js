import { fetch, io } from './encrypted-client.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const PORT = '32170', BASE = 'http://127.0.0.1:' + PORT, KEY = 'perm-test-key-123';

function until(socket, name, predicate = () => true, ms = 8000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { socket.off(name, handler); reject(Error('等待超时: ' + name)); }, ms);
    const handler = value => { if (predicate(value)) { clearTimeout(timer); socket.off(name, handler); resolve(value); } };
    socket.on(name, handler);
  });
}

test('历史分析报告权限：关闭后仅参与者/管理员可读，重启后保持，猜测房间码无效', { timeout: 90000 }, async t => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'junqi-analysis-perm-'));
  const sockets = [];
  let child, stderr = '';
  const env = () => ({ ...process.env, PORT, ADMIN_KEY: KEY,
    ACCOUNTS_FILE: path.join(dir, 'accounts.json'), SIGUO_ROOMS_FILE: path.join(dir, 'rooms.json'),
    SIGUO_HISTORY_DIR: path.join(dir, 'history'), SIGUO_PICTURES_DIR: path.join(dir, 'pictures'),
    SIGUO_AVATARS_DIR: path.join(dir, 'avatars'), SIGUO_PROGRAMS_FILE: path.join(dir, 'programs.json') });
  async function start() {
    child = spawn(process.execPath, ['server/server.js'], { env: env(), stdio: ['ignore', 'pipe', 'pipe'] });
    child.stderr.on('data', d => stderr += d);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('启动超时: ' + stderr)), 8000);
      child.stdout.on('data', b => { if (b.toString().includes('已启动')) { clearTimeout(timer); resolve(); } });
      child.once('exit', () => reject(Error(stderr)));
    });
  }
  async function stop() {
    if (child && child.exitCode === null) { child.kill(); await new Promise(r => child.once('exit', r)); }
  }
  t.after(async () => { sockets.forEach(s => s.disconnect()); await stop(); await rm(dir, { recursive: true, force: true }); });
  async function api(route, token, method = 'GET', body, admin = false) {
    const response = await fetch(BASE + route, { method,
      headers: { 'content-type': 'application/json', Authorization: 'Bearer ' + token, ...(admin ? { 'x-admin-key': KEY } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  }
  async function account(username, accountType = 'human') {
    assert.equal((await api('/api/admin/accounts', null, 'POST', { username, password: 'test1234', accountType }, true)).status, 201);
    const login = await api('/api/login', null, 'POST', { username, password: 'test1234' });
    assert.equal(login.status, 200);
    return login.body.token;
  }
  async function connect() {
    const s = io(BASE, { transports: ['websocket'], forceNew: true });
    sockets.push(s); await until(s, 'connect'); return s;
  }
  async function command(s, event, payload, predicate) {
    const p = until(s, 'room-state', predicate); s.emit(event, payload); return await p;
  }
  await start();
  const host = await account('PermHost'), guest = await account('PermGuest'), outsider = await account('PermOutsider');

  const log = m => console.error(`[PERM ${new Date().toISOString().slice(11, 19)}] ${m}`);
  const hs = await connect();
  log('Host 已连接');
  const session = until(hs, 'session');
  hs.emit('create-room', { authToken: host, capacity: 2, mode: 'ffa', rated: false });
  const { code } = await session;
  log('房间已创建 ' + code);
  assert.match(code, /^[A-Z0-9]{6}$/);
  const gs = await connect();
  log('Guest 已连接');
  let v = await command(gs, 'join-room', { authToken: guest, code });
  log('Guest 已加入 seat=' + v.viewerSeat);
  if (!v.viewerSeat) await command(gs, 'take-seat', { seat: 'south' }, s => s.viewerSeat === 'south');
  else if (v.viewerSeat !== 'south') await command(gs, 'take-seat', { seat: 'south' }, s => s.viewerSeat === 'south');
  log('Guest 座位= south');
  await command(hs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'north')?.ready);
  log('Host 已准备');
  await command(gs, 'toggle-ready', undefined, s => s.players.find(p => p.seat === 'south')?.ready);
  log('Guest 已准备');
  await command(hs, 'start-game', undefined, s => s.phase === 'playing');
  log('对局已开始');
  const pending = until(hs, 'room-state', s => s.phase === 'finished');
  hs.emit('resign'); await pending;

  // 生成并持久化报告：应携带参与者白名单。
  const generated = await api(`/api/rooms/${code}/analysis`, host, 'POST', { budgetMs: 60, maxMoves: 4 });
  assert.equal(generated.status, 200, JSON.stringify(generated.body));
  assert.ok(Array.isArray(generated.body.access?.allowedUsers), '报告应含权限白名单');
  assert.ok(generated.body.access.allowedUsers.includes('PermHost'));
  assert.ok(generated.body.access.allowedUsers.includes('PermGuest'));
  assert.ok(!generated.body.access.allowedUsers.includes('PermOutsider'));
  assert.equal(generated.body.persisted, true);

  // 关闭房间（默认不保留历史）：房间从内存移除，但分析文件仍在。
  await command(hs, 'close-room', undefined, s => !!s.players);
  assert.equal((await api(`/api/rooms/${code}/replay`, host)).status, 404, '关闭后原 replay API 应返回 404');

  assert.equal((await api(`/api/rooms/${code}/analysis`, host)).status, 200, '参与者 Host 可读');
  assert.equal((await api(`/api/rooms/${code}/analysis`, guest)).status, 200, '参与者 Guest 可读');
  const denied = await api(`/api/rooms/${code}/analysis`, outsider);
  assert.equal(denied.status, 403, '非参与者不可读');
  assert.equal((await api(`/api/rooms/${code}/analysis`, null, 'GET', undefined, true)).status, 200, '管理员可读');
  const guessed = await api('/api/rooms/ZZZZZZ/analysis', host);
  assert.ok([403, 404].includes(guessed.status), '猜测房间码不可读取他人分析');

  // 重启服务后重复验证（报告与白名单来自磁盘）。
  await stop(); await start();
  const host2 = await (await api('/api/login', null, 'POST', { username: 'PermHost', password: 'test1234' })).body.token;
  const outsider2 = await (await api('/api/login', null, 'POST', { username: 'PermOutsider', password: 'test1234' })).body.token;
  assert.equal((await api(`/api/rooms/${code}/analysis`, host2)).status, 200, '重启后参与者仍可读');
  assert.equal((await api(`/api/rooms/${code}/analysis`, outsider2)).status, 403, '重启后非参与者仍不可读');
  assert.equal((await api(`/api/rooms/${code}/analysis`, null, 'GET', undefined, true)).status, 200, '重启后管理员仍可读');
  console.log(JSON.stringify({ code, allowedUsers: generated.body.access.allowedUsers, restart: true }));
});
