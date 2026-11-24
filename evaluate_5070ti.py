"""评测：训练好的 JunqiActorCritic（team0 = 学习方）对战规则基线 HeuristicBotWrapper（team1）。

用途：量化 checkpoint 的真实胜率，对应任务书阶段三验收线（胜率≥65%）。
用法：
    python evaluate_5070ti.py --games 32 --ckpt junqi_rtx5070ti_latest.pt
    python evaluate_5070ti.py --games 32 --ckpt junqi_best_iter240.pt \
        --sample --temperature 0.5 --seed 90000
不依赖共享内存 worker，单进程单局板评估即可。
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train_junqi_5070ti as T  # noqa: E402


def play_episode(model, heuristic, max_steps: int = 240, sample: bool = False, temperature: float = 1.0):
    env = T.JunqiSelfPlayEnv(max_steps=max_steps)
    env.reset()
    steps = 0
    while steps < max_steps + 16:
        seat = env.current_seat
        obs = torch.from_numpy(env.get_obs(seat)).unsqueeze(0).cuda()
        mask = torch.from_numpy(env.get_action_mask(seat)).unsqueeze(0).cuda()
        with torch.no_grad():
            logits, _ = (model if seat % 2 == 0 else heuristic)(obs, mask)
        if sample:
            probs = (logits.float() / temperature).softmax(-1)
            action = int(torch.multinomial(probs, 1).item())
        else:
            action = int(logits.argmax(dim=-1).item())
        _, done, info = env.step(action)
        steps += 1
        if done:
            return info.get("winner_team", -1), steps
    return -1, steps


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--games', type=int, default=32, help='对局数（默认 32）')
    ap.add_argument('--ckpt', default=str(HERE / 'junqi_rtx5070ti_latest.pt'), help='checkpoint 路径')
    ap.add_argument('--sample', action='store_true', help='按温度采样而非贪心 argmax')
    ap.add_argument('--temperature', type=float, default=1.0, help='采样温度（默认 1.0）')
    ap.add_argument('--seed', type=int, default=None, help='固定随机种子使评测可复现')
    ap.add_argument('--max-steps', type=int, default=240, help='单局步数上限（默认 240）')
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)

    ckpt_path = Path(args.ckpt)
    if not ckpt_path.exists():
        print(f"checkpoint 不存在: {ckpt_path}")
        return

    model = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    model.load_state_dict(torch.load(str(ckpt_path), map_location="cuda", weights_only=True))
    heuristic = T.HeuristicBotWrapper().cuda().eval()

    results = []
    for i in range(args.games):
        winner, steps = play_episode(
            model, heuristic, max_steps=args.max_steps,
            sample=args.sample, temperature=args.temperature,
        )
        tag = "WIN" if winner == 0 else ("LOSS" if winner == 1 else "DRAW")
        results.append((i, tag, steps, winner))
        print(f"game={i} tag={tag} plies={steps} winner={winner}")

    wins = sum(1 for r in results if r[1] == "WIN")
    losses = sum(1 for r in results if r[1] == "LOSS")
    draws = sum(1 for r in results if r[1] == "DRAW")
    total = len(results)
    print("\n== 汇总")
    mode = "sample" if args.sample else "argmax"
    print(f"games={total} wins={wins} losses={losses} draws={draws} "
          f"(mode={mode}, T={args.temperature}, seed={args.seed})")
    print(f"win_rate={wins/total*100:.1f}%  win_rate_excl_draw={wins/max(wins+losses,1)*100:.1f}%")


if __name__ == "__main__":
    main()
