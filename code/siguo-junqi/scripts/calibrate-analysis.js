// 逐手评分校准研究（P10）
//
// 研究内容：
// 1. 候选着法覆盖率（评估数/合法数，是否穷尽）。
// 2. 同一局面重复分析的一致性（相同种子结果应完全一致）。
// 3. 不同搜索预算下的评分稳定性（分数波动）。
// 4. 四类着法区分：bestCandidate / bestEvaluated / actualMove / unsearchedPotentialBest。
// 5. 关键战术漏检：构造"离开夺旗点"的劣着，验证错误等级能识别。
//
// 注意：本报告量化的是引擎启发式分的行为，不把该分解释为胜率。
// 用法：node scripts/calibrate-analysis.js [--out analysis-calibration.json]
import fs from 'node:fs';
import { BOARD, validateMove } from '../server/game.js';
import { botView } from '../bots/engine/bot.js';
import { evaluateMoveSet, CALIBRATION_NOTE } from '../bots/engine/analysis.js';

function seeded(seed) { return () => ((seed = (1664525 * seed + 1013904223) >>> 0) / 4294967296); }
const piece = (id, owner, type, position, revealed = true) => ({ id, owner, type, position, revealed,
  moved: type !== 'flag' && type !== 'mine', initialPosition: position });
const position = pieces => ({ phase: 'playing', turn: 'north', mode: 'ffa', activeSeats: ['north', 'south'], pieces });

// 一组有代表性的局面：中盘、夺旗、护旗、暗子交战。
function scenarios() {
  const boards = [
    { name: '夺旗（公开旗）', pieces: [
      piece('a', 'north', 'engineer', 'south-4-1'), piece('f', 'south', 'flag', 'south-5-1'),
      piece('own', 'north', 'flag', 'north-5-1'), piece('enemy', 'south', 'army', 'north-4-1')],
      actual: { from: 'south-4-1', to: 'south-5-1' }, bad: { from: 'south-4-1', to: 'south-4-0' } },
    { name: '暗子交战（旗隐藏）', pieces: [
      piece('a', 'north', 'commander', 'center-0-1'),
      piece('x', 'south', 'army', 'center-0-2', false),
      piece('own', 'north', 'flag', 'north-5-1'), piece('f', 'south', 'flag', 'south-5-1', false)],
      actual: { from: 'center-0-1', to: 'center-0-2' } },
  ];
  return boards.map(b => ({ ...b, view: botView(position(b.pieces), 'north') }));
}

let outPath = null;
for (let i = 2; i < process.argv.length; i++) if (process.argv[i] === '--out') outPath = process.argv[i + 1];

const report = { note: CALIBRATION_NOTE, generatedAt: new Date().toISOString(), scenarios: [] };
for (const s of scenarios()) {
  const validActual = s.actual && validateMove(position(s.pieces), 'north', s.actual.from, s.actual.to).ok;
  const base = { budgetMs: 400, maxCandidates: 14, maxSamples: 24 };
  // 重复一致性：相同种子应逐字段一致（elapsedMs 除外）。
  const r1 = evaluateMoveSet(s.view, s.actual, [], { ...base, rng: seeded(11) });
  const r2 = evaluateMoveSet(s.view, s.actual, [], { ...base, rng: seeded(11) });
  const strip = r => { const { elapsedMs, ...rest } = r; return JSON.stringify(rest); };
  const consistent = strip(r1) === strip(r2);
  // 预算稳定性：不同预算下 best 是否稳定、分数差范围。
  const budgets = [100, 200, 400, 800];
  const stability = budgets.map(b => {
    const r = evaluateMoveSet(s.view, s.actual, [], { budgetMs: b, maxCandidates: 14, maxSamples: 32, rng: seeded(7) });
    return { budgetMs: b, best: r.best ? `${r.best.from}>${r.best.to}` : null,
      bestScore: r.best?.score ?? null, samples: r.samples, depth: r.depth };
  });
  const bests = new Set(stability.map(x => x.best));
  const scores = stability.map(x => x.bestScore).filter(x => x !== null);
  const errClasses = [];
  if (s.bad && validateMove(position(s.pieces), 'north', s.bad.from, s.bad.to).ok) {
    const bad = evaluateMoveSet(s.view, s.bad, [], { ...base, rng: seeded(3) });
    errClasses.push({ move: `${s.bad.from}>${s.bad.to}`, errorClass: bad.errorClass, scoreLoss: bad.scoreLoss,
      explanation: bad.explanation });
  }
  report.scenarios.push({
    name: s.name,
    actual: s.actual,
    actualLegal: validActual,
    coverage: r1.coverage,
    moveClasses: r1.moveClasses,
    consistency: { identicalAcrossRepeats: consistent },
    budgetStability: {
      distinctBestMoves: bests.size,
      bestStable: bests.size === 1,
      bestScoreRange: scores.length ? Math.max(...scores) - Math.min(...scores) : null,
      runs: stability,
    },
    tacticalMiss: errClasses,
  });
}
const text = JSON.stringify(report, null, 2);
if (outPath) { fs.writeFileSync(outPath, text, 'utf8'); console.error(`校准报告已写入 ${outPath}`); }
else process.stdout.write(text + '\n');
