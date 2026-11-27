"""复评统计：胜率/和局率/排除和局胜率（含分母）、终局原因分布、配对差异区间。

配对：同一 seed（seed_base+g）下各模型对战同一基线；座位按 g 奇偶轮换。
差异区间：对 (modelA胜 - modelB胜) 用配对 bootstrap（重采样 seed）给 95% CI。
pairwise_ci 落盘为机器可读 JSON：胜局率/终局率配对差异 CI、McNemar 精确二项双侧检验，
以及每个 checkpoint 的 Wilson 95% CI / 终局分布 / 座位拆分。
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import NormalDist

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
Z95 = NormalDist().inv_cdf(0.975)  # 1.959963984540054；不依赖 scipy


def _native(v):
    """把 numpy 标量/数组递归转成 json.dumps 可序列化的 Python 原生类型。"""
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, dict):
        return {k: _native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_native(x) for x in v]
    return v


def _wilson(k: int, n: int):
    """比例 k/n 的 Wilson 95% 置信区间；n=0 时返回 (None, None)。"""
    if n <= 0:
        return None, None
    p = k / n
    denom = 1.0 + Z95 * Z95 / n
    center = (p + Z95 * Z95 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 * Z95 / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _mcnemar_exact_two_sided(b: int, c: int) -> float:
    """不一致对 b/c 的精确二项双侧 p（二项参数 n=b+c, p=0.5；不依赖 scipy）。"""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def _diff_ci(vec_a, vec_b, idx, bins=100):
    """按 seed 配对重采样计数差；返回相对比例差（百分点）的观测值与 95% CI。"""
    diff = (vec_a[idx].mean(axis=1) - vec_b[idx].mean(axis=1)) * bins
    lo, hi = np.percentile(diff, [2.5, 97.5])
    obs = (vec_a.mean() - vec_b.mean()) * bins
    return float(obs), float(lo), float(hi)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', default=str(ROOT / 'results' / 'tournament.jsonl'))
    ap.add_argument('--out', default=str(ROOT / 'results' / 'derived' / 'summary.json'))
    ap.add_argument('--bootstrap', type=int, default=10000,
                    help='配对 bootstrap 重采样次数（默认 10000）')
    ap.add_argument('--seed', type=int, default=0,
                    help='bootstrap 随机数种子（默认 0）')
    ap.add_argument('--correction', choices=('holm', 'none'), default='holm',
                    help='两两 McNemar 多重比较校正（默认 holm；none 只报告未校正 p）')
    args = ap.parse_args()

    def ckpt_key(g):
        # 新产物用绝对路径 checkpoint_id 分组；旧产物回退到 basename，保持只读复算。
        return g.get('checkpoint_id') or g['checkpoint']

    P = Path(args.data)
    OUT = Path(args.out)
    B = args.bootstrap
    rows = [json.loads(l) for l in P.open(encoding='utf-8')]
    meta = [r for r in rows if r['type'] == 'meta'][0]
    games = [r for r in rows if r['type'] == 'game']

    by_ckpt = defaultdict(list)
    for g in games:
        by_ckpt[ckpt_key(g)].append(g)

    # 每个 seed 下每个模型的结果字典
    result_by_seed = defaultdict(dict)
    for g in games:
        result_by_seed[g['seed']][ckpt_key(g)] = g

    print('=== impl:', meta['impl_file'])
    print('=== seeds:', meta['seed_base'], 'games each:', meta['games_per_candidate'], 'max_steps:', meta['max_steps'])
    print('=== ckpt sha:', meta['checkpoint_sha256'])

    summary = {}
    per_ckpt = {}
    for ck, gs in by_ckpt.items():
        n = len(gs)
        wins = sum(1 for g in gs if g['model_won'])
        losses = sum(1 for g in gs if g['model_lost'])
        decisive = wins + losses
        draws = n - decisive
        terms = Counter(g['termination'] for g in gs)
        # 配对和局明细
        by_term = {}
        for t, c in terms.items(): by_term[t] = c
        w_lo, w_hi = _wilson(wins, n)
        d_lo, d_hi = _wilson(decisive, n)
        sl = terms.get('step_limit_draw', 0)
        s_lo, s_hi = _wilson(sl, n)
        summary[ck] = dict(n=n, wins=wins, losses=losses, draws=draws, decisive=decisive)
        per_ckpt[ck] = dict(
            n=n, wins=wins, losses=losses, draws=draws, decisive=decisive,
            win_rate=wins / n if n else None,
            win_rate_formula='W/N（含和局，主验收口径）',
            win_rate_ci={'lo': w_lo, 'hi': w_hi},
            win_rate_excl_draws=wins / decisive if decisive else None,
            win_rate_excl_draws_numerator=wins,
            win_rate_excl_draws_denominator=decisive,
            win_rate_excl_draws_formula='W/(W+L)（仅诊断；须同时写 W+L 与 N）',
            decisive_rate=decisive / n if n else None,
            decisive_rate_ci={'lo': d_lo, 'hi': d_hi},
            step_limit_rate=sl / n if n else None,
            step_limit_rate_ci={'lo': s_lo, 'hi': s_hi},
            termination_counts=dict(terms),
            seat_split={
                'team0': dict(n=len([g for g in gs if g['model_team'] == 0]),
                              wins=sum(1 for g in gs if g['model_team'] == 0 and g['model_won']),
                              losses=sum(1 for g in gs if g['model_team'] == 0 and g['model_lost']),
                              draws=sum(1 for g in gs if g['model_team'] == 0
                                        and not g['model_won'] and not g['model_lost'])),
                'team1': dict(n=len([g for g in gs if g['model_team'] == 1]),
                              wins=sum(1 for g in gs if g['model_team'] == 1 and g['model_won']),
                              losses=sum(1 for g in gs if g['model_team'] == 1 and g['model_lost']),
                              draws=sum(1 for g in gs if g['model_team'] == 1
                                        and not g['model_won'] and not g['model_lost'])),
            },
        )
        print(f'\n--- {ck} ---')
        print(f"  胜={wins}/{n} ({wins/n*100:.1f}%)  负={losses}  和={draws} ({draws/n*100:.1f}%)")
        print(f"  排除和局胜率={wins}/{decisive}" + (f" ({wins/decisive*100:.1f}%)" if decisive else ' (分母0)'))
        print(f"  终局原因: {by_term}")
        # 座位偏差
        t0 = [g for g in gs if g['model_team'] == 0]; t1 = [g for g in gs if g['model_team'] == 1]
        print(f"  座位team0: {sum(1 for g in t0 if g['model_won'])}/{len(t0)}胜 | "
              f"team1: {sum(1 for g in t1 if g['model_won'])}/{len(t1)}胜")

    # 配对差异 bootstrap（胜局数差，同 seed 重采样）
    cks = list(by_ckpt.keys())
    rng = np.random.default_rng(args.seed)
    seeds = sorted(result_by_seed.keys())
    def winvec(ck):
        return np.array([1 if result_by_seed[s][ck]['model_won'] else 0 for s in seeds], dtype=int)
    def decvec(ck):
        return np.array([1 if (result_by_seed[s][ck]['model_won'] or
                               result_by_seed[s][ck]['model_lost']) else 0 for s in seeds], dtype=int)
    def slvec(ck):
        return np.array([1 if result_by_seed[s][ck]['termination'] == 'step_limit_draw' else 0
                         for s in seeds], dtype=int)
    vecs = {ck: winvec(ck) for ck in cks}
    decisives = {ck: decvec(ck) for ck in cks}
    step_limits = {ck: slvec(ck) for ck in cks}
    print(f'\n=== 配对差异 bootstrap (重采样 seed, {B} 次, 95% CI; 单位: 胜局数/100) ===')
    # 胜局、终局率共用同一 B / seed / 重采样索引矩阵，保证口径一致。
    idx = rng.integers(0, len(seeds), size=(B, len(seeds)))
    pairwise = []
    decisive_diff_ci = []
    step_limit_diff_ci = []
    for i in range(len(cks)):
        for j in range(i+1, len(cks)):
            a, b = cks[i], cks[j]
            da = vecs[a][idx].mean(axis=1)
            db = vecs[b][idx].mean(axis=1)
            diff = (da - db) * 100
            lo, hi = np.percentile(diff, [2.5, 97.5])
            obs = (vecs[a].mean() - vecs[b].mean()) * 100
            print(f'  {a} - {b}: 观测={obs:+.1f}  CI95=[{lo:+.1f}, {hi:+.1f}]  '
                  f'{"CI不含0" if lo>0 or hi<0 else "CI含0"}')
            # McNemar 不一致对：b = a 胜且 b 未胜（含和局），c = b 胜且 a 未胜。
            nb = int(np.sum((vecs[a] == 1) & (vecs[b] == 0)))
            nc = int(np.sum((vecs[a] == 0) & (vecs[b] == 1)))
            pairwise.append(dict(a=a, b=b, obs_diff=float(obs), ci_lo=float(lo), ci_hi=float(hi),
                                 ci_half_width=float((hi - lo) / 2),
                                 mcnemar_b=nb, mcnemar_c=nc,
                                 mcnemar_p=_mcnemar_exact_two_sided(nb, nc),
                                 mcnemar_p_holm=None, distinguishable=None))
            for src, dest in ((decisives, decisive_diff_ci), (step_limits, step_limit_diff_ci)):
                dobs, dlo, dhi = _diff_ci(src[a], src[b], idx)
                dest.append(dict(a=a, b=b, obs_diff=dobs, ci_lo=dlo, ci_hi=dhi,
                                 unit='percentage_points'))

    # Holm 逐步校正：按未校正 p 升序，adjusted_i = max_{k<=i} ((m-k+1) * p_k)，截断到 1。
    m = len(pairwise)
    if args.correction == 'holm' and m:
        order = sorted(range(m), key=lambda i: pairwise[i]['mcnemar_p'])
        running = 0.0
        for rank, i in enumerate(order):
            running = max(running, (m - rank) * pairwise[i]['mcnemar_p'])
            pairwise[i]['mcnemar_p_holm'] = min(1.0, running)
    for p in pairwise:
        p['effective_p'] = (p['mcnemar_p_holm'] if args.correction == 'holm'
                            else p['mcnemar_p'])
        p['distinguishable'] = bool(
            (p['ci_lo'] > 0 or p['ci_hi'] < 0) and p['effective_p'] < 0.05)
        p['verdict'] = ('可区分' if p['distinguishable'] else
                        '并列/功效不足（CI半宽>5pp时不得写等同）'
                        if p['ci_half_width'] > 5 else '并列/功效不足')
        print(f"  -> {p['a']} vs {p['b']}: {p['verdict']} "
              f"(p={p['mcnemar_p']:.4g}, effective_p={p['effective_p']:.4g})")

    pairwise_ci = {
        'bootstrap_B': B,
        'rng_seed': args.seed,
        'n_seeds': len(seeds),
        'ci_level': 0.95,
        'pairwise': pairwise,
        'decisive_diff_ci': decisive_diff_ci,
        'step_limit_diff_ci': step_limit_diff_ci,
        'per_ckpt': per_ckpt,
        'multiple_comparison': args.correction,
        'decision_rule': '可区分 = 配对 bootstrap 95% CI 不含 0 且 McNemar 双侧 p<0.05（经所选多重比较校正）；否则并列/功效不足',
        'note': ('McNemar 为精确二项双侧检验；不一致对 b=a胜/b未胜，c=b胜/a未胜（和局计为未胜）。'
                 '主验收只看 W/N；W/(W+L) 仅诊断，已同时落盘分子与分母。'
                 'CI半宽>5pp 时不得写“等同”。'),
    }

    # 保存机器可读汇总
    out = {"meta": meta, "summary": summary, "pairwise_ci": pairwise_ci}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(_native(out), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nwritten: {OUT}')


if __name__ == '__main__':
    main()
