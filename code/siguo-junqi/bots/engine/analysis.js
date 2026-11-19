// 逐手引擎评分（四国暗棋）
//
// 设计约束（与 BOT_API / 复盘安全模型一致）：
// 1. 一致信息视角：本模块只接受已经投影为「暗棋视角」的 view（由 botView 或
//    replay 分析器的 projectFrame 产生）。非己方且未 revealed 的棋子 type 必须为 null。
//    真实隐藏兵种绝不进入搜索或估值。
// 2. 一致采样条件：实际着法与所有候选着法在同一批采样局面、同一搜索深度下评估；
//    一批未完成（超时）则整批丢弃，不产生半批次分数。
// 3. 诚实标注：输出的分是「未校准的启发式引擎分」，不是胜率，也不换算为胜率百分比。
//
// 本模块不修改任何现有引擎行为，只新增导出。

import { BOARD, PIECE_INFO } from '../../server/game.js';
import { legalBotMoves } from './bot.js';
import { inferDomains, samplePosition, simulateStrongMove, searchPosition, rootHeuristic } from './search.js';

const index = new Map(BOARD.nodes.map((node, i) => [node.id, i]));

export const CALIBRATION_NOTE =
  '引擎分为未校准的启发式评估分（子力/位置/终局分），不是胜率，也不代表赢面百分比。';

// 错误等级阈值，单位为本引擎的启发式分（子力价值量级：工兵 48、司令 135、军旗 16000、终局 ±50000）。
// 这些是经验阈值，不是胜率损失。
export const ERROR_THRESHOLDS = Object.freeze({ good: 30, inaccuracy: 100, mistake: 350, blunder: 1000 });

export function classifyLoss(loss, thresholds = ERROR_THRESHOLDS) {
  if (!Number.isFinite(loss) || loss <= thresholds.good) return 'best';
  if (loss <= thresholds.inaccuracy) return 'good';
  if (loss <= thresholds.mistake) return 'inaccuracy';
  if (loss <= thresholds.blunder) return 'mistake';
  return 'blunder';
}

const moveKey = m => `${m.from}>${m.to}`;

function explain(view, best, actual, actualMove, loss) {
  if (!actualMove) return `未提供实际着法，无法比较。${CALIBRATION_NOTE}`;
  if (!actual) return `实际着法不是当前视角下的合法着法，无法比较。${CALIBRATION_NOTE}`;
  if (!best) return `没有可比较的候选着法。${CALIBRATION_NOTE}`;
  if (loss <= 0) return `实际着法与本引擎在暗棋视角下的最佳着法一致。${CALIBRATION_NOTE}`;

  const parts = [];
  const target = BOARD.byId.get(actual.to);
  const bestTarget = BOARD.byId.get(best.to);
  const flag = view.pieces.find(p => p.owner === view.turn && p.type === 'flag');

  // 夺旗机会：最佳着法指向可能藏旗的大本营，且该着未被采用。
  if (bestTarget?.kind === 'hq' && bestTarget.seat && bestTarget.seat !== view.turn) {
    parts.push('存在指向敌方大本营的潜在夺旗着法，实际着法未采用');
  }
  // 送旗 / 进入己方大本营的非防御移动。
  if (target?.kind === 'hq' && target.seat === view.turn) {
    parts.push('实际着法把棋子移入己方大本营，通常只在特定防守情形下合理');
  }
  // 军旗防护圈：是否离开己方军旗两格内。
  if (flag) {
    const flagNode = BOARD.byId.get(flag.position);
    const dist = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
    if (dist(BOARD.byId.get(actual.from), flagNode) <= 2 && dist(target, flagNode) > 2) {
      parts.push('实际着法离开了己方军旗的近身防护圈');
    }
  }
  parts.push(`实际着法引擎分低于最佳着法 ${loss.toFixed(1)} 分，最佳着法为 ${best.from}→${best.to}`);
  parts.push(CALIBRATION_NOTE);
  return parts.join('；') + '。';
}

/**
 * 对单一局面的一组候选着法做一致条件下的评分。
 *
 * @param {object} view 暗棋视角局面（必需字段：turn/mode/activeSeats/pieces[/records/battles]）
 * @param {{from:string,to:string}} actualMove 实战着法（只用 from/to，不接触真实 type）
 * @param {Array} history 本方历史着法，用于重复晃动惩罚
 * @param {object} options budgetMs / maxCandidates / maxSamples / rng
 */
export function evaluateMoveSet(view, actualMove = null, history = [], options = {}) {
  const {
    budgetMs = 1200, maxCandidates = 14, maxSamples = 48, rng = Math.random,
  } = options;
  const started = Date.now();
  const deadline = started + Math.max(1, budgetMs);
  const legal = legalBotMoves(view);
  const base = {
    ok: false, infoView: 'dark', candidates: [], best: null, actual: null,
    scoreLoss: 0, errorClass: 'none', samples: 0, depth: 0,
    elapsedMs: 0, explanation: '无合法着法。', calibrationNote: CALIBRATION_NOTE,
  };
  if (!legal.length) return base;

  const domains = inferDomains(view);
  const informed = {
    ...view,
    pieces: view.pieces.map(p => ({
      ...p,
      candidates: p.candidates || [...(domains.get(p.id) || [])],
      type: p.type || (domains.get(p.id)?.size === 1 ? [...domains.get(p.id)][0] : null),
    })),
  };
  const ranked = legal.map(m => ({ ...m, prior: rootHeuristic(informed, m, history) }))
    .sort((a, b) => b.prior - a.prior);
  const candidates = ranked.slice(0, Math.max(1, maxCandidates));
  const actualLegal = actualMove ? legal.find(m => moveKey(m) === moveKey(actualMove)) : null;
  if (actualLegal && !candidates.some(m => moveKey(m) === moveKey(actualLegal))) candidates.push(actualLegal);

  const stats = candidates.map(() => ({ sum: 0, square: 0, worst: Infinity, n: 0 }));
  let samples = 0, maxDepth = 0;
  while (Date.now() < deadline && samples < Math.max(1, maxSamples)) {
    const sampled = samplePosition(view, domains, rng, Math.min(deadline, Date.now() + 120));
    if (!sampled) {
      if (samples === 0 && Date.now() < deadline - 130) continue;
      break;
    }
    const depth = samples < 4 ? 2 : samples < 12 ? 3 : 4;
    const scores = [];
    try {
      for (const move of candidates) {
        const src = index.get(move.from), dst = index.get(move.to);
        scores.push(src === undefined || dst === undefined ? 0
          : searchPosition(simulateStrongMove(sampled, { ...move, src, dst }), view.turn,
            depth, -Infinity, Infinity, deadline));
      }
    } catch (error) {
      // searchPosition 超时会抛 TIMEOUT symbol；只把它当作本批次未完成。
      if (Date.now() >= deadline) break;
      throw error;
    }
    samples += 1;
    maxDepth = Math.max(maxDepth, depth + 1);
    candidates.forEach((_, i) => {
      const s = stats[i], value = scores[i];
      s.sum += value; s.square += value * value; s.n += 1;
      s.worst = Math.min(s.worst, value);
    });
  }

  const evaluated = candidates.map((move, i) => {
    const s = stats[i];
    const mean = s.n ? s.sum / s.n : 0;
    const std = s.n ? Math.sqrt(Math.max(0, s.square / s.n - mean * mean)) : 0;
    return {
      from: move.from, to: move.to, prior: Number((move.prior ?? 0).toFixed(2)),
      mean: Number(mean.toFixed(2)), std: Number(std.toFixed(2)),
      worst: s.worst === Infinity ? 0 : Number(s.worst.toFixed(2)),
      samples: s.n, score: Number((mean - 0.16 * std).toFixed(2)),
    };
  }).sort((a, b) => b.score - a.score);

  const best = evaluated[0] || null;
  const actual = actualMove ? evaluated.find(e => e.from === actualMove.from && e.to === actualMove.to) || null : null;
  const scoreLoss = best && actual ? Math.max(0, Number((best.score - actual.score).toFixed(2))) : 0;
  const errorClass = actual ? classifyLoss(scoreLoss) : 'none';

  return {
    ...base, ok: !!actual, candidates: evaluated, best, actual,
    scoreLoss, errorClass, samples, depth: maxDepth,
    elapsedMs: Date.now() - started,
    explanation: explain(view, best, actual, actualMove, scoreLoss),
  };
}
