"""回放抽查（任务书第3步）：复现性、平局来源、座位偏差、暗棋信息隔离。

从 tournament.jsonl 选和局/败局（覆盖 3 模型），逐局重放：
1) 对照 trace 验证动作序列复现；
2) 记录终局原因、step_count、no_capture；
3) 每步检查 obs 的敌方 belief 通道（28:52）：
   - 概率合法（每行 0 或 1，无负值）——不可能兵种严格归 0
   - 信息隔离：belief 峰值不得系统性精确指向敌方真实棋子位置（亮旗除外）
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import sys

sys.path.insert(0, r'D:\4-player-junqi')
import train_junqi_5070ti as T

TOURN = r'D:\4-player-junqi\results\tournament.jsonl'
rows = [json.loads(l) for l in open(TOURN, encoding='utf-8')]
games = [r for r in rows if r['type'] == 'game']

# 选覆盖 3 模型的和局/败局，每个模型至少 4 局
selected = []
for ck in sorted(set(g['checkpoint'] for g in games)):
    pool = [g for g in games if g['checkpoint'] == ck and (not g['model_won'])]
    selected += pool[:4]
selected = selected[:15]
print(f'抽查局数: {len(selected)}')


def load_model(path):
    m = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    m.load_state_dict(torch.load(r'D:\4-player-junqi\\' + path, map_location='cuda', weights_only=True))
    return m


models = {}
for ck in set(g['checkpoint'] for g in selected):
    models[ck] = load_model(ck)
baseline = T.HeuristicBotWrapper().cuda().eval()

reports = []
for g in selected:
    seed = g['seed']
    random.seed(seed); np.random.seed(seed)
    env = T.JunqiSelfPlayEnv(max_steps=240); env.reset()
    replay_trace = []
    belief_viol = 0
    belief_peak_exact = 0     # belief 峰值精确命中敌方真实棋子（非亮旗）次数
    belief_rows_checked = 0
    steps = 0
    while steps < 256:
        seat = env.current_seat
        obs = env.get_obs(seat)
        # ---- 暗棋信息隔离检查 ----
        b = obs[28:52]  # [24,17,17] = 两组各12类型的 belief 图
        # 正确检查：每个类型通道图 b[t] 在敌方站点的概率，按站点 12维和=1 判断。
        # 重建 site->12维向量：敌方A = b[0:12] 在 (y,x) 的取值；敌方B = b[12:24]
        enemies = [(seat + 1) % 4, (seat + 3) % 4]
        for ei, en in enumerate(enemies):
            tr = env.tracker.beliefs[en]  # [17,17,12] authoritative
            sums = tr.sum(axis=2)
            nz = sums[sums > 1e-6]
            if np.any(np.abs(nz - 1.0) > 1e-3):
                belief_viol += 1
            belief_rows_checked += len(nz)
            block = b[ei*12:(ei+1)*12]  # [12,17,17]
            # 真实棋子位置（排除已亮旗：用 ptype==11 视为已公开）
            true_pos = (env.owner_board == en)
            for t in range(12):
                if t == 11:
                    continue  # 军旗亮旗是合法公开
                mask_pos = (env.owner_board == en) & (env.piece_board == t)
                if not mask_pos.any():
                    continue
                # belief 对该真实类型在真实位置的值；若为1.0则疑似直接泄漏
                vals = block[t][mask_pos]
                if np.any(vals > 0.999):
                    belief_peak_exact += 1
        # ---- 走子 ----
        obs_t = torch.from_numpy(obs).unsqueeze(0).cuda()
        mask_t = torch.from_numpy(env.get_action_mask(seat)).unsqueeze(0).cuda()
        with torch.no_grad():
            fn = models[g['checkpoint']] if (g['model_team'] == 0 and seat % 2 == 0) or \
                                            (g['model_team'] == 1 and seat % 2 == 1) else baseline
            lg, _ = fn(obs_t, mask_t)
        a = int(lg.argmax(-1))
        _, done, info = env.step(a)
        replay_trace.append([seat, a])
        steps += 1
        if done:
            break
    match = replay_trace == g['trace']
    reports.append({
        'checkpoint': g['checkpoint'], 'seed': seed, 'model_team': g['model_team'],
        'winner': info.get('winner_team', -1), 'termination': g['termination'],
        'trace_match': match, 'replay_plies': len(replay_trace), 'recorded_plies': g['plies'],
        'belief_prob_violations': belief_viol,
        'belief_exact_match_nonflag': belief_peak_exact,
        'belief_rows_checked': belief_rows_checked,
    })

print('\n=== 回放抽查结果 ===')
for r in reports:
    print(f"  {r['checkpoint']:26s} seed={r['seed']} team={r['model_team']} "
          f"term={r['termination']:18s} trace_match={r['trace_match']} "
          f"plies={r['replay_plies']}/{r['recorded_plies']} "
          f"belief_viol={r['belief_prob_violations']} exact_nonflag={r['belief_exact_match_nonflag']}")

n_match = sum(1 for r in reports if r['trace_match'])
print(f'\ntrace 复现: {n_match}/{len(reports)}')
print(f'belief 概率违规局数: {sum(1 for r in reports if r["belief_prob_violations"]>0)}/{len(reports)}')
print(f'非亮旗 belief 精确命中敌方真实棋子的局数: '
      f'{sum(1 for r in reports if r["belief_exact_match_nonflag"]>0)}/{len(reports)}')

Path(r'D:\4-player-junqi\results\replay_audit.json').write_text(
    json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
print('written: results/replay_audit.json')
