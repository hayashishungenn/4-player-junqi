"""评测：刚训练的 JunqiActorCritic（team0 = 学习方）对战内置规则基线 HeuristicBotWrapper（team1）。

用途：量化当前 checkpoint 的真实胜率，对应任务书阶段三验收线（胜率≥65%）。
用法：
    python evaluate_5070ti.py [n_games] [checkpoint_path]            # 贪心 argmax
    python evaluate_5070ti.py [n_games] [checkpoint_path] --sample [T]  # 按温度采样
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
    args = sys.argv[1:]
    nums = [a for a in args if not a.startswith("--") and _is_number(a) or a.isdigit()]
    # 简单解析：若参数以数字开头当 n_games，其余按顺序：[n_games] [checkpoint] [--sample] [T]
    n_games = 32
    ckpt_path = HERE / "junqi_rtx5070ti_latest.pt"
    sample = "--sample" in args
    flags = [a for a in args if not a.startswith("--")]
    if flags:
        try:
            n_games = int(flags[0]); rest = flags[1:]
        except ValueError:
            rest = flags
        else:
            if rest:
                ckpt_path = Path(rest[0])
    if not ckpt_path.exists():
        print(f"checkpoint 不存在: {ckpt_path}")
        return
    temperature = 1.0
    if sample:
        tail = [a for a in args if _looks_float(a)]
        if len(tail) >= 2:
            temperature = float(tail[-1])

    model = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    model.load_state_dict(torch.load(str(ckpt_path), map_location="cuda"))
    heuristic = T.HeuristicBotWrapper().cuda().eval()

    results = []
    for i in range(n_games):
        winner, steps = play_episode(model, heuristic, sample=sample, temperature=temperature)
        tag = "WIN" if winner == 0 else ("LOSS" if winner == 1 else "DRAW")
        results.append((i, tag, steps, winner))
        print(f"game={i} tag={tag} plies={steps} winner={winner}")

    wins = sum(1 for r in results if r[1] == "WIN")
    losses = sum(1 for r in results if r[1] == "LOSS")
    draws = sum(1 for r in results if r[1] == "DRAW")
    total = len(results)
    print("\n== 汇总")
    mode = "sample" if sample else "argmax"
    print(f"games={total} wins={wins} losses={losses} draws={draws} (mode={mode}, T={temperature})")
    print(f"win_rate={wins/total*100:.1f}%  win_rate_excl_draw={wins/max(wins+losses,1)*100:.1f}%")


def _is_number(s: str) -> bool:
    try:
        float(s); return True
    except ValueError:
        return False


def _looks_float(s: str) -> bool:
    try:
        float(s); return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()
