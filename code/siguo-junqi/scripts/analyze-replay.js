// 复盘分析 CLI：node scripts/analyze-replay.js <replay.json> [选项]
// 选项：--budget-ms N  --mode ffa|alliance  --seed N  -o <输出.json>
import fs from 'node:fs';
import path from 'node:path';
import { analyzeReplay } from '../bots/engine/replay-analysis.js';

function usage(msg) {
  if (msg) console.error(`错误：${msg}`);
  console.error('用法：node scripts/analyze-replay.js <replay.json> [--budget-ms N] [--mode ffa|alliance] [--seed N] [-o out.json]');
  process.exit(msg ? 1 : 0);
}

const args = process.argv.slice(2);
if (!args.length || args[0] === '--help' || args[0] === '-h') usage(args.length ? undefined : undefined);
const input = args[0];
if (input.startsWith('-')) usage('缺少 replay.json 路径');

let budgetMs = 900, mode, seed = 7, output = null;
for (let i = 1; i < args.length; i++) {
  const a = args[i];
  if (a === '--budget-ms') budgetMs = Number(args[++i]);
  else if (a === '--mode') mode = args[++i];
  else if (a === '--seed') seed = Number(args[++i]);
  else if (a === '-o' || a === '--output') output = args[++i];
  else usage(`未知选项 ${a}`);
}
if (!Number.isFinite(budgetMs) || budgetMs < 1) usage('budget-ms 必须为正数');

let replay;
try {
  replay = JSON.parse(fs.readFileSync(input, 'utf8'));
} catch (error) {
  console.error(`读取棋谱失败：${error.message}`);
  process.exit(1);
}

const report = analyzeReplay(replay, { budgetMs, mode, seed });
const text = JSON.stringify(report, null, 2);
if (output) {
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
  fs.writeFileSync(output, text, 'utf8');
  console.error(`报告已写入 ${output}`);
} else {
  process.stdout.write(text + '\n');
}

console.error(`\n=== 整局摘要 ===`);
console.error(`棋局 ${report.code || '(无编号)'} | 模式 ${report.mode} | 结果 ${report.winner ?? '未知'} | 棋步 ${report.summary.totalMoves}`);
for (const [seat, stat] of Object.entries(report.summary.perSeat)) {
  console.error(`  ${seat}: ${stat.moves} 步, 平均损失 ${stat.avgLoss}, 最佳 ${stat.best || 0} / 良好 ${stat.good || 0} / 不准确 ${stat.inaccuracy || 0} / 失误 ${stat.mistake || 0} / 严重失误 ${stat.blunder || 0}`);
}
console.error(`关键失误 ${report.blunders.length} 处；${report.calibrationNote}`);
for (const w of report.warnings) console.error(`警告：${w}`);
