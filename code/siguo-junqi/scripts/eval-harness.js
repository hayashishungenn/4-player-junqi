// 棋力评测对战框架（P8）
//
// 目标：固定随机种子、多种合法布阵、四座轮换、相同预算、完整棋谱、可重复运行。
// 支持 agent：strong:<budgetMs>（现有 StrongBot）、random（随机合法着法基线）。
// GNN agent 通过 --gnn-cmd 外部推理器接入（见 eval-gnn-agent.md），本脚本保持引擎无关。
//
// 用法示例：
//   node scripts/eval-harness.js --games 100 --mode ffa \
//     --agents strong:80,strong:200 --seed 42 --out research-eval/ffa-100.jsonl
//   node scripts/eval-harness.js --games 100 --mode alliance \
//     --agents strong:80,strong:200 --seed 42 --out research-eval/alliance-100.jsonl

import fs from 'node:fs';
import path from 'node:path';
import { BOARD, PIECE_INFO, SEATS, createArmy, validateSetup, validateMove, resolveBattle,
  sameTeam, hasLegalMove, revealFlagWhenCommanderDies } from '../server/game.js';
import { botView, observeBotBattle, legalBotMoves } from '../bots/engine/bot.js';
import { chooseStrongMove } from '../bots/engine/search.js';

function parseArgs(argv) {
  const out = { games: 20, mode: 'ffa', agents: 'strong:80,strong:200', seed: 42,
    maxPlies: 512, out: 'eval-results.jsonl', setups: 12 };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, '');
    if (!key || argv[i + 1] === undefined) continue;
    out[key] = argv[i + 1];
  }
  out.games = Math.max(1, Number(out.games) || 20);
  out.seed = Number(out.seed) || 42;
  out.maxPlies = Math.max(1, Number(out.maxPlies) || 512);
  out.setups = Math.max(1, Number(out.setups) || 12);
  if (!['ffa', 'alliance'].includes(out.mode)) throw Error('mode 仅支持 ffa / alliance');
  return out;
}

function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (1664525 * s + 1013904223) >>> 0) / 4294967296);
}

function shuffled(list, rng) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
const nodeId = (seat, row, col) => `${seat}-${row}-${col}`;

/** 确定性合法布阵（不依赖 Math.random / crypto），相同 rng 序列必得相同阵型与 id。 */
function makeSetup(seat, rng) {
  const types = [];
  for (const [type, info] of Object.entries(PIECE_INFO)) for (let i = 0; i < info.count; i++) types.push(type);
  const available = [];
  for (let row = 0; row < 6; row++) for (let col = 0; col < 5; col++) {
    const id = nodeId(seat, row, col);
    if (BOARD.byId.get(id)?.kind !== 'camp') available.push(id);
  }
  const hqs = shuffled([nodeId(seat, 5, 1), nodeId(seat, 5, 3)], rng);
  const positions = new Map([['flag', hqs[0]]]);
  const rear = shuffled(available.filter(id => BOARD.byId.get(id).row >= 4 && id !== hqs[0]), rng);
  for (let i = 0; i < 3; i++) positions.set(`mine-${i}`, rear[i]);
  const used = new Set(positions.values());
  const bombCells = shuffled(available.filter(id => BOARD.byId.get(id).row > 0 && !used.has(id)), rng);
  for (let i = 0; i < 2; i++) { positions.set(`bomb-${i}`, bombCells[i]); used.add(bombCells[i]); }
  const open = shuffled(available.filter(id => !used.has(id)), rng);
  const counters = {}, pieces = [];
  let openIndex = 0;
  for (const type of types) {
    const index = counters[type] || 0;
    counters[type] = index + 1;
    const key = type === 'flag' ? 'flag' : `${type}-${index}`;
    const position = positions.get(key) || open[openIndex++];
    pieces.push({ id: `${seat}-${key}`, owner: seat, type, position,
      revealed: false, moved: false, initialPosition: position });
  }
  if (!validateSetup(pieces, seat).ok) throw Error(`生成的布阵不合法：${seat}`);
  return pieces;
}

function makeAgent(spec, rng) {
  if (spec.startsWith('strong:')) {
    const budgetMs = Math.max(1, Number(spec.slice(7)) || 100);
    return { name: spec, budgetMs,
      choose(view, history) {
        const result = chooseStrongMove(view, history, { budgetMs, rng });
        return { move: result.move, samples: result.samples || 0, depth: result.depth || 0 };
      } };
  }
  if (spec === 'random') {
    return { name: 'random', budgetMs: 0,
      choose(view) {
        const moves = legalBotMoves(view);
        return { move: moves.length ? moves[Math.floor(rng() * moves.length)] : null, samples: 0, depth: 0 };
      } };
  }
  throw Error(`未知 agent 规格：${spec}（支持 strong:<ms> / random）`);
}

function winnerTeam(room) {
  const living = SEATS.filter(seat => room.players.some(p => p.seat === seat && !p.eliminated)
    && room.pieces.some(p => p.owner === seat && p.position));
  if (room.mode === 'alliance') {
    const ns = living.some(s => s === 'north' || s === 'south');
    const ew = living.some(s => s === 'east' || s === 'west');
    if (!ns && !ew) return { winner: '和棋', team: 'draw' };
    // 双方联盟都还有存活方时比赛继续；只有一方全灭才判胜负。
    if (ns && !ew) return { winner: '南北联盟', team: 'NS' };
    if (ew && !ns) return { winner: '东西联盟', team: 'EW' };
    return null;
  }
  if (living.length <= 1) return { winner: living[0] || '和棋', team: living[0] || 'draw' };
  return null;
}

function playGame({ mode, agentSpecs, setups, gameNo, seed, maxPlies }) {
  const rng = seeded(seed + gameNo * 7919);
  const agents = agentSpecs.map(spec => makeAgent(spec, rng));
  // 4 个座位全部由 agent 控制；第 g 局座位 s 由 agent (s+g)%agents.length 执棋。
  const seatToAgent = SEATS.map((_, si) => (si + gameNo) % agents.length);
  const setupBank = Array.from({ length: setups }, (_, i) =>
    SEATS.map(seat => makeSetup(seat, seeded(seed * 131 + i * 977 + SEATS.indexOf(seat)))));
  const chosen = setupBank[gameNo % setupBank.length];
  const pieces = chosen.flatMap((army, i) => army.map(p => ({ ...p, owner: SEATS[i] })));
  const room = { phase: 'playing', turn: 'north', mode, activeSeats: [...SEATS], pieces,
    players: SEATS.map(seat => ({ seat, isBot: true, eliminated: false })),
    replay: { frames: [], logs: [] }, botBattles: [], botKnowledge: new Map() };
  const history = Object.fromEntries(SEATS.map(s => [s, []]));
  const stats = {};
  SEATS.forEach((seat, si) => { stats[agents[seatToAgent[si]].name + '@' + seat] = { samples: 0, depth: 0, moves: 0, ms: 0 }; });
  const moveLogs = [];
  let plies = 0, battles = 0, noCapture = 0, error = null, terminal = 'normal';

  while (plies < maxPlies && !winnerTeam(room)) {
    const seat = room.turn;
    const ai = seatToAgent[SEATS.indexOf(seat)];
    if (ai === undefined || room.players.find(p => p.seat === seat).eliminated) {
      // 轮到已淘汰方：跳到下一存活方。
      const idx = SEATS.indexOf(seat);
      room.turn = SEATS[(idx + 1) % 4];
      continue;
    }
    if (!hasLegalMove(room, seat)) {
      const player = room.players.find(p => p.seat === seat);
      player.eliminated = true;
      for (const p of room.pieces) if (p.owner === seat) p.position = null;
      terminal = 'stalemate';
      continue;
    }
    const view = botView(room, seat);
    const started = Date.now();
    let choice;
    try { choice = agents[ai].choose(view, history[seat]); }
    catch (e) { error = `agent error: ${e.message}`; terminal = 'error'; break; }
    const elapsed = Date.now() - started;
    const key = agents[ai].name + '@' + seat;
    stats[key].samples += choice.samples; stats[key].depth += choice.depth;
    stats[key].moves += 1; stats[key].ms += elapsed;
    if (!choice.move) { terminal = 'no-move'; break; }
    const judged = validateMove(room, seat, choice.move.from, choice.move.to);
    if (!judged.ok) { error = `illegal move ${JSON.stringify(choice.move)}: ${judged.message}`; terminal = 'error'; break; }
    const a = judged.attacker, d = judged.defender;
    a.moved = true; if (judged.engineerTurn) a.revealed = true;
    const outcome = resolveBattle(a, d);
    observeBotBattle(room, a, d, outcome);
    if (d) { battles++; noCapture = 0; } else noCapture++;
    if (outcome === 'attacker' || outcome === 'both') { revealFlagWhenCommanderDies(room, d); d.position = null; }
    if (outcome === 'defender' || outcome === 'both') { revealFlagWhenCommanderDies(room, a); a.position = null; }
    else a.position = choice.move.to;
    let flagCaptured = false;
    if (outcome === 'attacker' && d?.type === 'flag') {
      flagCaptured = true;
      const victim = room.players.find(p => p.seat === d.owner);
      if (victim) victim.eliminated = true;
      for (const p of room.pieces) if (p.owner === d.owner) p.position = null;
      terminal = 'flag';
    }
    const record = { ply: plies + 1, seat, agent: agents[ai].name, from: choice.move.from, to: choice.move.to,
      outcome, samples: choice.samples, depth: choice.depth, elapsedMs: elapsed, flagCaptured };
    moveLogs.push(record);
    room.replay.logs.push({ time: plies, kind: 'move', frameIndex: room.replay.frames.length,
      seat, username: agents[ai].name, from: choice.move.from, to: choice.move.to,
      attacker: { id: a.id, type: a.type }, defender: d ? { id: d.id, type: d.type, owner: d.owner } : null,
      outcome, path: [choice.move.from, choice.move.to] });
    room.replay.frames.push({ time: plies, state: { pieces: room.pieces.map(p => ({ ...p })), turn: room.turn, phase: room.phase,
      lastMove: null, players: room.players.map(p => ({ ...p })) } });
    history[seat] = [...history[seat], choice.move].slice(-16);
    plies++;
    // 夺旗仅淘汰一方；是否终局交给 winnerTeam 判断（FFA 需打到只剩一方，
    // 联盟需一方全灭）。避免过早终止导致胜率统计失真。
    if (noCapture >= 16 || plies >= maxPlies) { terminal = noCapture >= 16 ? 'auto-draw' : 'ply-limit'; break; }
    // 轮转（联盟模式下与 sameTeam 无关，仍按座次）。
    const idx = SEATS.indexOf(seat);
    for (let step = 1; step <= 4; step++) {
      const next = SEATS[(idx + step) % 4];
      if (!room.players.find(p => p.seat === next).eliminated) { room.turn = next; break; }
    }
  }
  const final = winnerTeam(room) || { winner: '未决', team: 'unresolved' };
  const agentsSeats = {};
  SEATS.forEach((seat, si) => { agentsSeats[agents[seatToAgent[si]].name + '@' + seat] = seat; });
  // 联盟队伍归属：南北=north/south，东西=east/west。
  const agentTeams = Object.fromEntries(Object.entries(agentsSeats).map(([k, seat]) =>
    [k, (seat === 'north' || seat === 'south') ? 'NS' : 'EW']));
  return { game: gameNo, mode, seed: seed + gameNo * 7919, setupIndex: gameNo % setupBank.length,
    agents: [...new Set(agents.map(a => a.name))], agentsSeats, agentTeams,
    winner: final.winner, winningTeam: final.team,
    plies, battles, terminal, error,
    stats, moves: moveLogs };
}

const args = parseArgs(process.argv.slice(2));
const agents = args.agents.split(',').map(s => s.trim());
if (agents.length !== 2 && agents.length !== 4) throw Error('agents 需提供 2 或 4 个规格');
agents.forEach(s => makeAgent(s, seeded(1))); // 校验规格
const setups = args.setups;
fs.mkdirSync(path.dirname(path.resolve(args.out)), { recursive: true });
const started = Date.now();
const out = fs.createWriteStream(args.out, { encoding: 'utf8' });
for (let g = 0; g < args.games; g++) {
  const result = playGame({ mode: args.mode, agentSpecs: agents, setups, gameNo: g, seed: args.seed, maxPlies: args.maxPlies });
  out.write(JSON.stringify(result) + '\n');
  if ((g + 1) % 10 === 0 || g === args.games - 1) {
    console.error(`[eval] ${args.mode} ${g + 1}/${args.games} 完成，末局 ${result.winner} / ${result.plies} 步 / ${result.terminal}`);
  }
}
out.end();
console.log(JSON.stringify({ mode: args.mode, games: args.games, agents, seed: args.seed,
  setups: args.setups, out: args.out, elapsedMs: Date.now() - started }));
