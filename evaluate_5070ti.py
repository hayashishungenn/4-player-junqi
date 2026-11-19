"""评测：刚训练的 JunqiActorCritic（team0 = 学习方）对战内置规则基线 HeuristicBotWrapper（team1）。

用途：量化当前 checkpoint 的真实胜率，对应任务书阶段三验收线（胜率≥65%）。
不依赖共享内存 worker，单进程单局板评估即可。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train_junqi_5070ti as T  # noqa: E402


def play_episode(model, heuristic, max_steps: int = 240):
    env = T.JunqiSelfPlayEnv(max_steps=max_steps)
    env.reset()
    steps = 0
    while steps < max_steps + 16:
        seat = env.current_seat
        obs = torch.from_numpy(env.get_obs(seat)).unsqueeze(0).cuda()
        mask = torch.from_numpy(env.get_action_mask(seat)).unsqueeze(0).cuda()
        with torch.no_grad():
            logits, _ = (model if seat % 2 == 0 else heuristic)(obs, mask)
        # 学习方用贪心策略；对手（规则基线）也是 logits 最大化
        action = int(logits.argmax(dim=-1).item())
        _, done, info = env.step(action)
        steps += 1
        if done:
            return info.get("winner_team", -1), steps
    return -1, steps


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    ckpt_arg = sys.argv[2] if len(sys.argv) > 2 else str(HERE / "junqi_rtx5070ti_latest.pt")
    ckpt = Path(ckpt_arg)
    if not ckpt.exists():
        print(f"checkpoint 不存在: {ckpt}")
        return
    model = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    model.load_state_dict(torch.load(ckpt, map_location="cuda"))
    heuristic = T.HeuristicBotWrapper().cuda().eval()

    results = []
    for i in range(n):
        winner, steps = play_episode(model, heuristic)
        tag = "WIN" if winner == 0 else ("LOSS" if winner == 1 else "DRAW")
        results.append((i, tag, steps, winner))
        print(f"game={i} tag={tag} plies={steps} winner={winner}")

    wins = sum(1 for r in results if r[1] == "WIN")
    losses = sum(1 for r in results if r[1] == "LOSS")
    draws = sum(1 for r in results if r[1] == "DRAW")
    total = len(results)
    print("\n== 汇总")
    print(f"games={total} wins={wins} losses={losses} draws={draws}")
    print(f"win_rate={wins/total*100:.1f}%  win_rate_excl_draw={wins/max(wins+losses,1)*100:.1f}%")


if __name__ == "__main__":
    main()
