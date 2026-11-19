#!/usr/bin/env python3
"""A/B 对比：逐样本 forward vs 批量 forward_batch 的 GPU 训练吞吐。"""
import random
import time

import torch

from neural_bot import Encoder, GraphPolicyValue


def make_batch(encoder, n_samples, device):
    """构造 n_samples 个随机样本（复用同一局面结构，聚焦计算吞吐）。"""
    board = encoder.board
    nodes = board["nodes"]
    types = list(board["pieceInfo"].keys()) + ["unknown"]
    feats_list, acts_list, masks, choices = [], [], [], []
    for i in range(n_samples):
        f = torch.zeros(len(nodes), encoder.feature_size)
        for j in range(len(nodes)):
            f[j, 0] = 1
        # 随机放 3 枚棋子
        for k in range(3):
            node = random.randrange(len(nodes))
            f[node, 0:5] = 0
            f[node, 1 + random.randrange(len(types))] = 1
        m = random.randint(4, 12)
        a = torch.randint(0, len(nodes), (m, 2))
        feats_list.append(f)
        acts_list.append(a)
        masks.append([True] * m)
        choices.append(random.randrange(m))
    max_a = max(len(a) for a in acts_list)
    pad = torch.zeros(max_a, 2, dtype=torch.long)
    padded = []
    mask_rows = []
    for a, mask in zip(acts_list, masks):
        if len(a) < max_a:
            padded.append(torch.cat([a, pad[:max_a - len(a)]]))
            mask_rows.append(mask + [False] * (max_a - len(a)))
        else:
            padded.append(a)
            mask_rows.append(mask)
    features = torch.stack(feats_list).to(device)
    actions = torch.stack(padded).to(device)
    action_mask = torch.tensor(mask_rows, dtype=torch.bool, device=device)
    choice_t = torch.tensor(choices, device=device)
    return features, actions, action_mask, choice_t, acts_list, choices


def bench_loop(model, adjacency, features, actions_per_sample, choices, epochs=3):
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
    start = time.perf_counter()
    for _ in range(epochs):
        for i in range(features.shape[0]):
            f = features[i:i+1].squeeze(0)
            a = actions_per_sample[i].to(features.device)
            logits, value = model(f, adjacency, a)
            loss = logits.mean() + value
            opt.zero_grad(); loss.backward(); opt.step()
    if features.device.type == "cuda":
        torch.cuda.synchronize()
    return time.perf_counter() - start


def bench_batch(model, adjacency, features, actions, mask, choice_t, epochs=3):
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
    start = time.perf_counter()
    for _ in range(epochs):
        log_probs, value = model.forward_batch(features, adjacency, actions, mask)
        probs = log_probs.exp()
        chosen = log_probs.gather(1, choice_t.unsqueeze(1)).squeeze(1)
        entropy = -(probs * log_probs).masked_fill(~mask, 0.0).sum(1)
        loss = (chosen + .01 * entropy + value).mean()
        opt.zero_grad(); loss.backward(); opt.step()
    if features.device.type == "cuda":
        torch.cuda.synchronize()
    return time.perf_counter() - start


def main():
    random.seed(11)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    nodes = [{"id": f"n{i}", "x": i % 9, "y": i // 9, "kind": "station", "seat": None} for i in range(160)]
    board = {"nodes": nodes, "roads": [], "pieceInfo": {t: {"count": 1} for t in
             ["flag", "commander", "army", "engineer", "bomb", "mine", "platoon"]}}
    encoder = Encoder(board, device)
    model = GraphPolicyValue(encoder.feature_size, 128).to(device)
    features, actions, mask, choice_t, acts_list, choices = make_batch(encoder, 96, device)
    t_loop = bench_loop(model, encoder.adjacency, features, acts_list, choices, epochs=3)
    t_batch = bench_batch(model, encoder.adjacency, features, actions, mask, choice_t, epochs=3)
    import json
    print(json.dumps({
        "device": str(device), "samples": features.shape[0], "epochs": 3,
        "loop_s": round(t_loop, 3), "batch_s": round(t_batch, 3),
        "speedup": round(t_loop / max(1e-9, t_batch), 2),
        "peak_mem_MB": round(torch.cuda.max_memory_allocated()/1e6, 1) if device.type == "cuda" else None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
