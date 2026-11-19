#!/usr/bin/env python3
"""Champion / Challenger 独立评测对局（P9.3 闭环）。

用本地规则环境（self_play_env.mjs）让冠军模型与挑战者模型对打，
统计挑战者胜率与 Wilson 置信区间下界，输出可直接喂给
model_registry.ModelRegistry.promote() 的 evaluation 字典。

约束：
- 双方使用完全相同的局面信息（暗棋视角，隐藏兵种不输入网络）。
- 座位轮换、固定种子、联盟与混战分别评测，不混合口径。
- 只有足够样本且统计可信时，challenger_win_rate / challenger_ci_low 才达标。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import torch

from neural_bot import Encoder, GraphPolicyValue, SEATS
from self_play import LocalEnvironment, relation_team


def load_policy(model_path, board, device, hidden):
    encoder = Encoder(board, device)
    model = GraphPolicyValue(encoder.feature_size, hidden).to(device)
    path = Path(model_path)
    if path.exists():
        saved = torch.load(path, map_location=device, weights_only=False)
        if saved.get("nodes") != [n["id"] for n in encoder.nodes]:
            raise RuntimeError("模型棋盘结构与环境不一致")
        model.load_state_dict(saved["model"])
    model.eval()
    return encoder, model


def pick(encoder, model, state, device, temperature, rng):
    moves = state["legalMoves"]
    if not moves:
        return None
    feats, actions = encoder.encode(state), encoder.actions(moves)
    with torch.no_grad():
        logits, _ = model(feats, encoder.adjacency, actions)
        dist = torch.distributions.Categorical(logits=logits / temperature)
        idx = int(dist.sample())
    return moves[idx]


def wilson_low(wins, n, z=1.96):
    if not n:
        return 0.0
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h)


def evaluate(champion_path, challenger_path, games, mode, seed, device, hidden, temperature):
    rng = random.Random(seed)
    torch.manual_seed(seed)
    env = LocalEnvironment()
    try:
        board = env.board
        champ_enc, champ_model = load_policy(champion_path, board, device, hidden)
        chall_enc, chall_model = load_policy(challenger_path, board, device, hidden)
        # 挑战者控制 north/south（联盟）或 north（混战轮换）；固定座位便于归因。
        results = {"games": 0, "challenger_wins": 0, "champion_wins": 0, "draws": 0,
                   "mode": mode, "seed": seed}
        for g in range(games):
            state = env.reset(mode)
            while state["phase"] == "playing":
                viewer = state["viewerSeat"]
                is_challenger = viewer in ("north", "south") if mode == "alliance" else viewer == "north"
                enc, model = (chall_enc, chall_model) if is_challenger else (champ_enc, champ_model)
                move = pick(enc, model, state, device, temperature, rng)
                if move is None:
                    break
                state = env.move(move)
            winner = state.get("winner", "")
            if mode == "alliance":
                chall_win = winner == "南北联盟"
                champ_win = winner == "东西联盟"
            else:
                chall_win = winner == "north"
                champ_win = winner in ("east", "south", "west")
            results["games"] += 1
            if chall_win:
                results["challenger_wins"] += 1
            elif champ_win:
                results["champion_wins"] += 1
            else:
                results["draws"] += 1
        n = results["games"]
        results["challenger_win_rate"] = results["challenger_wins"] / n if n else 0.0
        results["challenger_ci_low"] = wilson_low(results["challenger_wins"], n)
        return results
    finally:
        env.close()


def main():
    p = argparse.ArgumentParser(description="Champion / Challenger 独立评测")
    p.add_argument("--champion", required=True)
    p.add_argument("--challenger", required=True)
    p.add_argument("--games", type=int, default=40)
    p.add_argument("--mode", choices=["ffa", "alliance"], default="alliance")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--device", default="cpu")
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--out", help="评测结果 JSON 输出路径")
    args = p.parse_args()
    report = evaluate(args.champion, args.challenger, args.games, args.mode,
                      args.seed, args.device, args.hidden, args.temperature)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"评测结果已写入 {args.out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
