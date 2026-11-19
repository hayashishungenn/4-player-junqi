// 评测结果统计报告（P8.3）
// 读取 eval-harness.js 产出的 JSONL，输出胜率/和棋率/置信区间/座位与布阵分项/Elo。
// 用法：node scripts/eval-report.js <result.jsonl> [--out report.md] [--json stats.json]
import fs from 'node:fs';

function wilson(wins, n, z = 1.96) {
  if (!n) return [0, 0];
  const p = wins / n, d = 1 + z * z / n;
  const c = (p + z * z / (2 * n)) / d;
  const h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}

const args = process.argv.slice(2);
const input = args[0];
if (!input) { console.error('用法：node scripts/eval-report.js <result.jsonl> [--out report.md] [--json stats.json]'); process.exit(1); }
let outMd = null, outJson = null;
for (let i = 1; i < args.length; i++) {
  if (args[i] === '--out') outMd = args[++i];
  else if (args[i] === '--json') outJson = args[++i];
}
const games = fs.readFileSync(input, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
if (!games.length) throw Error('无对局数据');
const mode = games[0].mode;
const agents = new Set(games.flatMap(g => g.agents || []));

const stats = {};
for (const agent of agents) {
  stats[agent] = { games: 0, wins: 0, losses: 0, draws: 0, unresolved: 0, errors: 0,
    plies: 0, battles: 0, samples: 0, depth: 0, moves: 0, ms: 0,
    bySeat: {}, bySetup: {}, byOutcome: {} };
}
let totalErrors = 0, totalUnresolved = 0;
const outcomes = {};
const pairwise = {};

for (const g of games) {
  outcomes[g.terminal || 'unknown'] = (outcomes[g.terminal || 'unknown'] || 0) + 1;
  if (g.error) totalErrors++;
  if (g.winningTeam === 'unresolved' || g.winner === '未决') totalUnresolved++;
  const seatToAgent = {};
  for (const [key, seat] of Object.entries(g.agentsSeats || {})) {
    const name = key.split('@')[0];
    seatToAgent[seat] = name;
  }
  // 每个 agent 可能控制多个座位：胜负按该局是否由该 agent 任一席位获胜判定。
  for (const s of g.agents) {
    const keys = Object.keys(g.agentsSeats || {}).filter(k => k.startsWith(s + '@'));
    const st = stats[s];
    st.games++; st.plies += g.plies || 0; st.battles += g.battles || 0;
    for (const key of keys) {
      const agg = g.stats?.[key] || { samples: 0, depth: 0, moves: 0, ms: 0 };
      st.samples += agg.samples || 0; st.depth += agg.depth || 0;
      st.moves += agg.moves || 0; st.ms += agg.ms || 0;
      st.bySeat[g.agentsSeats[key] || 'unknown'] = (st.bySeat[g.agentsSeats[key] || 'unknown'] || 0) + 1;
    }
    st.bySetup[g.setupIndex ?? -1] = (st.bySetup[g.setupIndex ?? -1] || 0) + 1;
    st.byOutcome[g.terminal || 'unknown'] = (st.byOutcome[g.terminal || 'unknown'] || 0) + 1;
    const agentTeams = new Set(keys.map(k => g.agentTeams?.[k]).filter(Boolean));
    let result = 'unresolved';
    if (mode === 'alliance') {
      if (g.winningTeam === 'draw') result = 'draw';
      else if (agentTeams.has(g.winningTeam)) result = 'win';
      else if (['NS', 'EW'].includes(g.winningTeam)) result = 'loss';
    } else {
      if (g.winner === '和棋') result = 'draw';
      else if (g.winner === '未决') result = 'unresolved';
      else if (seatToAgent[g.winner] === s) result = 'win';
      else if (['north', 'east', 'south', 'west'].includes(g.winner)) result = 'loss';
    }
    st[result === 'win' ? 'wins' : result === 'loss' ? 'losses' : result === 'draw' ? 'draws' : 'unresolved']++;
  }
  // pairwise（仅两 agent 配置有意义）
  if (g.agents.length === 2) {
    const [a, b] = g.agents;
    pairwise[a + ' vs ' + b] ||= { aWins: 0, bWins: 0, draws: 0, n: 0 };
    const p = pairwise[a + ' vs ' + b]; p.n++;
    const aTeams = new Set(Object.keys(g.agentsSeats || {}).filter(k => k.startsWith(a + '@')).map(k => g.agentTeams?.[k]));
    const winner = mode === 'alliance'
      ? (aTeams.has(g.winningTeam) ? a : ['NS', 'EW'].includes(g.winningTeam) ? b : null)
      : (seatToAgent[g.winner] === a ? a : seatToAgent[g.winner] === b ? b : null);
    if (g.winningTeam === 'draw' || g.winner === '和棋') p.draws++;
    else if (winner === a) p.aWins++;
    else if (winner === b) p.bWins++;
  }
}

function elo(aWins, bWins, draws, n) {
  // 简化 pairwise Elo：A 得分 = (胜 + 0.5和)/n，按 K=32 迭代估计分差。
  if (!n) return 0;
  const score = (aWins + 0.5 * draws) / n;
  let diff = 0;
  for (let i = 0; i < 200; i++) {
    const expected = 1 / (1 + Math.pow(10, -diff / 400));
    diff += 32 * (score - expected);
    if (Math.abs(score - expected) < 1e-9) break;
    diff = Math.max(-800, Math.min(800, diff));
  }
  return Math.round(diff);
}

const summary = { mode, games: games.length, agents: [...agents],
  outcomes, totalErrors, totalUnresolved, stats, pairwise: {} };
for (const [label, p] of Object.entries(pairwise)) {
  summary.pairwise[label] = { ...p, aWinRate: p.n ? +(p.aWins / p.n).toFixed(4) : 0,
    bWinRate: p.n ? +(p.bWins / p.n).toFixed(4) : 0,
    drawRate: p.n ? +(p.draws / p.n).toFixed(4) : 0, eloDiff: elo(p.aWins, p.bWins, p.draws, p.n) };
}
for (const [agent, st] of Object.entries(summary.stats)) {
  const decided = st.wins + st.losses;
  [st.winRateLow, st.winRateHigh] = wilson(st.wins, st.games);
  st.winRate = st.games ? +(st.wins / st.games).toFixed(4) : 0;
  st.drawRate = st.games ? +(st.draws / st.games).toFixed(4) : 0;
  st.avgPlies = st.games ? +(st.plies / st.games).toFixed(2) : 0;
  st.avgBattles = st.games ? +(st.battles / st.games).toFixed(2) : 0;
  st.avgSamplesPerMove = st.moves ? +(st.samples / st.moves).toFixed(2) : 0;
  st.avgDepth = st.moves ? +(st.depth / st.moves).toFixed(2) : 0;
  st.avgMsPerMove = st.moves ? +(st.ms / st.moves).toFixed(2) : 0;
  st.decided = decided;
}

const lines = [`# 棋力评测报告：${mode}`, '', `- 对局数：${summary.games}`,
  `- 异常终止：${totalErrors}；未决：${totalUnresolved}`,
  `- 终局类型：${JSON.stringify(outcomes)}`, '',
  '| Agent | 局数 | 胜 | 负 | 和 | 胜率 | 胜率95%CI | 和棋率 | 平均步数 | 平均战斗 | 采样/步 | 深度 | ms/步 |',
  '|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|'];
for (const [agent, st] of Object.entries(summary.stats)) {
  lines.push(`| ${agent} | ${st.games} | ${st.wins} | ${st.losses} | ${st.draws} | ${(st.winRate * 100).toFixed(1)}% | [${(st.winRateLow * 100).toFixed(1)}, ${(st.winRateHigh * 100).toFixed(1)}]% | ${(st.drawRate * 100).toFixed(1)}% | ${st.avgPlies} | ${st.avgBattles} | ${st.avgSamplesPerMove} | ${st.avgDepth} | ${st.avgMsPerMove} |`);
}
lines.push('', '## 座位分项', '');
for (const [agent, st] of Object.entries(summary.stats)) lines.push(`- ${agent}: ${JSON.stringify(st.bySeat)}`);
lines.push('', '## 布阵分项', '');
for (const [agent, st] of Object.entries(summary.stats)) lines.push(`- ${agent}: ${JSON.stringify(st.bySetup)}`);
lines.push('', '## 两两对比与 Elo（pairwise 代理指标，非全局评级）', '');
for (const [label, p] of Object.entries(summary.pairwise)) lines.push(`- ${label}: A胜 ${p.aWins} / B胜 ${p.bWins} / 和 ${p.draws} / 共 ${p.n}，Elo差(A-B) ${p.eloDiff}`);
lines.push('', '> 口径：胜率按 agent 参与局数计算；联盟模式按队伍胜/负/和；FFA 按座位名次。Elo 为两两对比的代理指标，不等同于多人/联盟正式评级。置信区间为 Wilson 95%。');
const text = lines.join('\n') + '\n';
if (outMd) fs.writeFileSync(outMd, text, 'utf8');
if (outJson) fs.writeFileSync(outJson, JSON.stringify(summary, null, 2), 'utf8');
process.stdout.write(text);
