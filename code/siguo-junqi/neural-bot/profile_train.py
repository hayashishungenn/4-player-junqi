#!/usr/bin/env python3
"""训练阶段耗时剖析：分解对局生成、编码、GPU 训练各阶段时间。"""
import random
import sys
import time

import torch

from neural_bot import Encoder, GraphPolicyValue, SEATS
from self_play import LocalEnvironment, relation_team


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    env = LocalEnvironment()
    board = env.board
    encoder = Encoder(board, device)
    model = GraphPolicyValue(encoder.feature_size, 128).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
    rng = random.Random(7)
    games = 6
    t_gen = t_enc = t_train = t_cuda_sync = 0.0
    total_samples = 0
    for g in range(games):
        # 阶段1：对局生成（Node 子进程逐手通信）
        s = time.perf_counter()
        state = env.reset("alliance")
        trajectories = {seat: [] for seat in SEATS}
        while state["phase"] == "playing":
            moves = state["legalMoves"]
            if not moves:
                break
            viewer = state["viewerSeat"]
            feats, actions = encoder.encode(state), encoder.actions(moves)
            model.eval()
            with torch.no_grad():
                logits, _ = model(feats, encoder.adjacency, actions)
                idx = int(torch.distributions.Categorical(logits=logits).sample())
            trajectories[viewer].append({"state": state, "moves": moves, "choice": idx})
            state = env.move(moves[idx])
        if device.type == "cuda":
            torch.cuda.synchronize()
        t_gen += time.perf_counter() - s
        # 阶段2：编码所有样本
        samples = [(seat, step, item) for seat, tr in trajectories.items()
                   for step, item in enumerate(tr)]
        total_samples += len(samples)
        s = time.perf_counter()
        for _, _, item in samples:
            encoder.encode(item["state"])
            encoder.actions(item["moves"])
        if device.type == "cuda":
            torch.cuda.synchronize()
        t_enc += time.perf_counter() - s
        # 阶段3：逐样本训练（当前实现）
        s = time.perf_counter()
        model.train()
        for seat, step, item in samples:
            f, a = encoder.encode(item["state"]), encoder.actions(item["moves"])
            logits, value = model(f, encoder.adjacency, a)
            loss = logits.mean() + value
            opt.zero_grad(); loss.backward(); opt.step()
        if device.type == "cuda":
            torch.cuda.synchronize()
        t_train += time.perf_counter() - s
    env.close()
    total = t_gen + t_enc + t_train
    print({
        "device": str(device), "games": games, "samples": total_samples,
        "total_s": round(total, 2),
        "game_gen_s": round(t_gen, 2), "game_gen_pct": round(t_gen / total * 100, 1),
        "encode_s": round(t_enc, 2), "encode_pct": round(t_enc / total * 100, 1),
        "train_s": round(t_train, 2), "train_pct": round(t_train / total * 100, 1),
        "train_ms_per_sample": round(t_train / max(1, total_samples) * 1000, 3),
    })


if __name__ == "__main__":
    main()
