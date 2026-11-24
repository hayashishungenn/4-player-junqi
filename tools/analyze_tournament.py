"""复评统计：胜率/和局率/排除和局胜率（含分母）、终局原因分布、配对差异区间。

配对：同一 seed（seed_base+g）下各模型对战同一基线；座位按 g 奇偶轮换。
差异区间：对 (modelA胜 - modelB胜) 用配对 bootstrap（重采样 seed）给 95% CI。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--data', default=str(ROOT / 'results' / 'tournament.jsonl'))
ap.add_argument('--out', default=str(ROOT / 'results' / 'summary.json'))
args = ap.parse_args()

P = Path(args.data)
OUT = Path(args.out)
rows = [json.loads(l) for l in P.open(encoding='utf-8')]
meta = [r for r in rows if r['type'] == 'meta'][0]
games = [r for r in rows if r['type'] == 'game']

by_ckpt = defaultdict(list)
for g in games:
    by_ckpt[g['checkpoint']].append(g)

# 每个 seed 下每个模型的结果字典
result_by_seed = defaultdict(dict)
for g in games:
    result_by_seed[g['seed']][g['checkpoint']] = g

print('=== impl:', meta['impl_file'])
print('=== seeds:', meta['seed_base'], 'games each:', meta['games_per_candidate'], 'max_steps:', meta['max_steps'])
print('=== ckpt sha:', meta['checkpoint_sha256'])

summary = {}
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
    summary[ck] = dict(n=n, wins=wins, losses=losses, draws=draws, decisive=decisive)
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
rng = np.random.default_rng(0)
seeds = sorted(result_by_seed.keys())
def winvec(ck):
    return np.array([1 if result_by_seed[s][ck]['model_won'] else 0 for s in seeds], dtype=int)
vecs = {ck: winvec(ck) for ck in cks}
print('\n=== 配对差异 bootstrap (重采样 seed, 10000 次, 95% CI; 单位: 胜局数/100) ===')
B = 10000
idx = rng.integers(0, len(seeds), size=(B, len(seeds)))
for i in range(len(cks)):
    for j in range(i+1, len(cks)):
        a, b = cks[i], cks[j]
        da = vecs[a][idx].mean(axis=1)
        db = vecs[b][idx].mean(axis=1)
        diff = (da - db) * 100
        lo, hi = np.percentile(diff, [2.5, 97.5])
        obs = (vecs[a].mean() - vecs[b].mean()) * 100
        print(f'  {a} - {b}: 观测={obs:+.1f}  CI95=[{lo:+.1f}, {hi:+.1f}]  '
              f'{"可区分" if lo>0 or hi<0 else "不可区分(含0)"}')

# 保存机器可读汇总
out = {"meta": meta, "summary": summary,
       "pairwise_ci": "见控制台输出 / 报告"}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nwritten: {OUT}')
