// 完整复盘分析器（P4）
//
// 输入：现有 room.replay（frames + logs），不另造棋谱格式。
// 输出：逐手评分、评分曲线、关键失误、最佳着法、整局报告。
//
// 视角分离（安全核心）：
// - analysis 字段：由 projectFrame 投影为「暗棋视角」后交给评分引擎；真实隐藏兵种不进入。
// - truth 字段：仅来自 replay.logs 的公开/赛后信息（真实 type 只在终局明棋视角展示）。
// 二者不在同一对象内混用，报告显式标注 perspective。

import { evaluateMoveSet, CALIBRATION_NOTE } from './analysis.js';

const keyOf = m => `${m.from}>${m.to}`;

/**
 * 把复盘局面帧投影为某一方的暗棋视角。
 * 与 botView 的安全边界等价：非己方且未 revealed 的棋子 type=null。
 */
export function projectFrame(frameState, seat, mode, activeSeats) {
  const records = frameState.pieces || [];
  const project = p => ({
    id: p.id, owner: p.owner, position: p.position,
    type: (p.owner === seat || p.revealed) ? p.type : null,
    moved: !!p.moved, initialPosition: p.initialPosition || null,
  });
  const live = records.filter(p => p.position);
  const seats = activeSeats && activeSeats.length
    ? activeSeats
    : [...new Set(records.map(p => p.owner))];
  return {
    phase: frameState.phase || 'playing', turn: seat, mode,
    activeSeats: seats, occupiedSeats: seats,
    records: records.map(project).sort((a, b) => a.id.localeCompare(b.id)),
    pieces: live.map(project).sort((a, b) => a.position.localeCompare(b.position)),
    battles: [], // 由 logs 累积的公开战果注入，见 analyzeReplay
    livingSeats: [...new Set(live.map(p => p.owner))],
  };
}

/** 从截至 ply 的日志重建公开战果，供弧一致性推断使用（只含 id 与 outcome，不含 type）。 */
function publicBattles(logs, ply) {
  const out = [];
  for (let i = 0; i < ply; i++) {
    const log = logs[i];
    if (log?.defender) out.push({ attacker: log.attacker?.id, defender: log.defender?.id, outcome: log.outcome });
  }
  return out;
}

function historyForSeat(logs, ply, seat) {
  const out = [];
  for (let i = 0; i < ply; i++) if (logs[i]?.seat === seat) out.push({ from: logs[i].from, to: logs[i].to });
  return out;
}

/**
 * 对一份完整 replay 生成分析报告。
 * @param {object} replay {frames:[{state:{pieces,turn,players,phase,lastMove}}], logs:[...], winner, ...}
 * @param {object} options budgetMs / totalBudgetMs / mode / seed / maxCandidates / maxSamples
 */
export function analyzeReplay(replay, options = {}) {
  const {
    budgetMs = 900, mode = replay.mode || 'alliance', seed = 7,
    maxCandidates = 12, maxSamples = 32, totalBudgetMs = 0,
  } = options;
  const overallDeadline = Number.isFinite(totalBudgetMs) && totalBudgetMs > 0
    ? Date.now() + totalBudgetMs : Infinity;
  const frames = replay.frames || [];
  const logs = (replay.logs || []).filter(l => l.kind === 'move' && l.from && l.to);
  const seatsFromPlayers = frames[0]?.state?.players
    ? frames[0].state.players.map(p => p.seat) : [];
  const warnings = [];
  if (!frames.length) warnings.push('没有局面帧，无法分析。');
  if (frames.length < logs.length) warnings.push(`局面帧(${frames.length})少于棋步(${logs.length})，末尾棋步可能缺少走子前局面。`);

  let rngState = seed >>> 0;
  const rng = () => ((rngState = (1664525 * rngState + 1013904223) >>> 0) / 4294967296);
  const moves = [];

  logs.forEach((log, i) => {
    // 新版棋谱在走子时记录 frameIndex，精确定位走子前局面；
    // 旧版棋谱回退到顺序映射 i。认输/淘汰等非走子事件也会产生帧，顺序映射可能错位。
    const frameIndex = Number.isInteger(log.frameIndex) ? log.frameIndex : i;
    const frame = frames[frameIndex];
    if (!frame?.state?.pieces) {
      moves.push({ ply: i + 1, seat: log.seat, from: log.from, to: log.to,
        analysis: { ok: false, errorClass: 'unknown', explanation: '缺少走子前局面帧。', calibrationNote: CALIBRATION_NOTE,
          coverage: { legalMoves: 0, evaluated: 0, ratio: 0, exhaustive: false },
          moveClasses: { bestCandidate: null, bestEvaluated: null, actualMove: { from: log.from, to: log.to },
            unsearchedPotentialBest: '未知（未分析）' } },
        truth: truthOf(log), perspective: { analysis: 'dark', truth: 'open' } });
      return;
    }
    const remaining = overallDeadline - Date.now();
    if (remaining <= 0) {
      moves.push({ ply: i + 1, seat: log.seat, username: log.username || null,
        from: log.from, to: log.to,
        analysis: { ok: false, errorClass: 'unanalyzed', explanation: '整局计算预算耗尽，未分析该步。',
          calibrationNote: CALIBRATION_NOTE, infoView: 'dark',
          coverage: { legalMoves: 0, evaluated: 0, ratio: 0, exhaustive: false },
          moveClasses: { bestCandidate: null, bestEvaluated: null, actualMove: { from: log.from, to: log.to },
            unsearchedPotentialBest: '未知（未分析）' } },
        truth: truthOf(log), perspective: { analysis: 'dark', truth: 'open' } });
      return;
    }
    // 整局预算按剩余棋步均摊，避免前几步耗尽导致后续全部未分析。
    const stepBudget = Math.max(1, Math.min(budgetMs, remaining / Math.max(1, logs.length - i)));
    const activeSeats = (frame.state.players || []).filter(p => !p.eliminated).map(p => p.seat);
    const view = projectFrame(frame.state, log.seat, mode,
      activeSeats.length ? activeSeats : seatsFromPlayers);
    view.battles = publicBattles(logs, i);
    const analysis = evaluateMoveSet(view, { from: log.from, to: log.to },
      historyForSeat(logs, i, log.seat),
      { budgetMs: stepBudget, maxCandidates, maxSamples, rng });
    moves.push({
      ply: i + 1, seat: log.seat, username: log.username || null,
      from: log.from, to: log.to,
      analysis: {
        ok: analysis.ok, best: analysis.best, actual: analysis.actual,
        candidates: analysis.candidates, scoreLoss: analysis.scoreLoss,
        errorClass: analysis.errorClass, samples: analysis.samples, depth: analysis.depth,
        explanation: analysis.explanation, calibrationNote: analysis.calibrationNote,
        infoView: analysis.infoView,
        coverage: analysis.coverage, moveClasses: analysis.moveClasses,
      },
      truth: truthOf(log),
      perspective: { analysis: 'dark', truth: 'open' },
    });
  });

  const unanalyzed = moves.filter(m => m.analysis.errorClass === 'unanalyzed').length;
  if (unanalyzed) warnings.push(`整局计算预算耗尽，${unanalyzed} 步未完成分析。`);

  const order = ['best', 'good', 'inaccuracy', 'mistake', 'blunder'];
  const perSeat = {};
  for (const m of moves) {
    const seat = m.seat;
    perSeat[seat] ||= { moves: 0, totalLoss: 0 };
    perSeat[seat].moves += 1;
    perSeat[seat].totalLoss += Number(m.analysis.scoreLoss) || 0;
    perSeat[seat][m.analysis.errorClass] = (perSeat[seat][m.analysis.errorClass] || 0) + 1;
  }
  for (const seat of Object.keys(perSeat)) {
    perSeat[seat].avgLoss = perSeat[seat].moves
      ? Number((perSeat[seat].totalLoss / perSeat[seat].moves).toFixed(2)) : 0;
  }

  const curve = moves.map(m => ({
    ply: m.ply, seat: m.seat,
    score: m.analysis.actual?.score ?? null,
    bestScore: m.analysis.best?.score ?? null,
    loss: m.analysis.scoreLoss ?? null,
    errorClass: m.analysis.errorClass,
  }));
  const blunders = moves.filter(m => ['mistake', 'blunder'].includes(m.analysis.errorClass))
    .map(m => ({ ply: m.ply, seat: m.seat, from: m.from, to: m.to,
      best: m.analysis.best, loss: m.analysis.scoreLoss, errorClass: m.analysis.errorClass,
      explanation: m.analysis.explanation }));

  return {
    version: 1, code: replay.code || null, mode,
    perspective: { analysis: 'dark', truth: 'open' },
    winner: replay.winner ?? null, completed: !!replay.completed,
    startedAt: replay.startedAt ?? null, finishedAt: replay.finishedAt ?? null,
    ratingChanges: replay.ratingChanges || null,
    summary: { totalMoves: moves.length, perSeat, errorOrder: order },
    moves, curve, blunders, warnings,
    calibrationNote: CALIBRATION_NOTE,
  };
}

/** 赛后明棋视角的着法事实，仅来自日志，不参与分析。 */
function truthOf(log) {
  return {
    attacker: log.attacker ? { id: log.attacker.id, type: log.attacker.type } : null,
    defender: log.defender ? { id: log.defender.id, type: log.defender.type, owner: log.defender.owner } : null,
    outcome: log.outcome || null, engineerTurn: !!log.engineerTurn,
  };
}
