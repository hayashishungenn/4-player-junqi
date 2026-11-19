// 一键多轮棋力评测套件（P8）：串行运行 100 / 500 / 1000+ 局，ffa 与 alliance 分别评测。
// 每轮固定种子、座位轮换、多种布阵；产出统计摘要（原始 JSONL 可再生成，不入库）。
// 用法：
//   node scripts/run-eval-suite.js --games 100,500,1000 --modes ffa,alliance \
//     --agents strong:10,strong:30 --seed 42 --dir eval-results
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const args = process.argv.slice(2);
const opt = { games: '100,500,1000', modes: 'ffa,alliance', agents: 'strong:10,strong:30', seed: '42', dir: 'eval-results' };
for (let i = 0; i < args.length; i += 2) {
  const k = args[i]?.replace(/^--/, '');
  if (k && args[i + 1] !== undefined) opt[k] = args[i + 1];
}
const games = opt.games.split(',').map(Number);
const modes = opt.modes.split(',');
const agents = opt.agents.split(',');
if (games.some(g => !Number.isInteger(g) || g < 1)) throw Error('games 必须为正整数列表');
fs.mkdirSync(opt.dir, { recursive: true });

const summaries = [];
for (const mode of modes) {
  for (const g of games) {
    const stem = `${mode}-${g}`;
    const jsonl = path.join(opt.dir, stem + '.jsonl');
    const md = path.join(opt.dir, stem + '.md');
    const stats = path.join(opt.dir, stem + '-stats.json');
    console.error(`\n[suite] 开始 ${stem}（seed=${opt.seed}, agents=${agents.join(' vs ')})`);
    const run = spawnSync(process.execPath, ['scripts/eval-harness.js',
      '--games', String(g), '--mode', mode, '--agents', opt.agents,
      '--seed', opt.seed, '--setups', String(Math.min(24, Math.max(4, Math.floor(g / 8)))),
      '--out', jsonl], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    if (run.status !== 0) throw Error(`评测失败 ${stem}: ${run.stderr}`);
    const rep = spawnSync(process.execPath, ['scripts/eval-report.js', jsonl,
      '--out', md, '--json', stats], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    if (rep.status !== 0) throw Error(`统计失败 ${stem}: ${rep.stderr}`);
    const s = JSON.parse(fs.readFileSync(stats, 'utf8'));
    summaries.push({ mode, games: g, seed: opt.seed, agents,
      outcomes: s.outcomes, pairwise: s.pairwise,
      byAgent: Object.fromEntries(Object.entries(s.stats).map(([k, v]) =>
        [k, { games: v.games, wins: v.wins, losses: v.losses, draws: v.draws,
          winRate: v.winRate, ci: [v.winRateLow, v.winRateHigh], avgPlies: v.avgPlies }])) });
    process.stdout.write(`${rep.stdout.split('\n').slice(0, 10).join('\n')}\n`);
  }
}
const suitePath = path.join(opt.dir, 'suite-summary.json');
fs.writeFileSync(suitePath, JSON.stringify(summaries, null, 2), 'utf8');
console.error(`\n[suite] 完成 ${summaries.length} 轮，汇总：${suitePath}`);
