#!/usr/bin/env python3
"""GPU 训练吞吐与显存基准（P9.1）。

测量：设备识别、CUDA 运算、训练 step 吞吐、峰值显存，并对比 CPU/GPU。
只做计算基准，不改动任何模型权重，不写大文件。
"""
from __future__ import annotations

import argparse
import sys
import time

import torch

from neural_bot import GraphPolicyValue

FEATURE = 64
NODES = 160
HIDDEN = 128
BATCH_ACTIONS = 256


def bench(device, steps=200):
    dev = torch.device(device)
    model = GraphPolicyValue(FEATURE, HIDDEN).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-4)
    features = torch.randn(NODES, FEATURE, device=dev)
    adj = torch.eye(NODES, device=dev) / NODES
    actions = torch.randint(0, NODES, (BATCH_ACTIONS, 2), device=dev)

    if dev.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(dev)
    # 预热
    for _ in range(5):
        logits, value = model(features, adj, actions)
        loss = logits.mean() + value
        opt.zero_grad(); loss.backward(); opt.step()
    if dev.type == 'cuda':
        torch.cuda.synchronize(dev)

    start = time.perf_counter()
    for _ in range(steps):
        logits, value = model(features, adj, actions)
        loss = logits.mean() + value
        opt.zero_grad(); loss.backward(); opt.step()
    if dev.type == 'cuda':
        torch.cuda.synchronize(dev)
    elapsed = time.perf_counter() - start

    result = {
        'device': str(dev),
        'steps': steps,
        'elapsed_s': round(elapsed, 4),
        'steps_per_s': round(steps / elapsed, 2),
        'ms_per_step': round(elapsed / steps * 1000, 3),
    }
    if dev.type == 'cuda':
        result['peak_allocated_MB'] = round(torch.cuda.max_memory_allocated(dev) / 1e6, 2)
        result['peak_reserved_MB'] = round(torch.cuda.max_memory_reserved(dev) / 1e6, 2)
    return result


def main():
    p = argparse.ArgumentParser(description='GPU 训练吞吐与显存基准')
    p.add_argument('--steps', type=int, default=200)
    p.add_argument('--only', choices=['cpu', 'cuda', 'both'], default='both')
    args = p.parse_args()
    report = {
        'torch_version': torch.__version__,
        'cuda_available': torch.cuda.is_available(),
        'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'compute_capability': str(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
        'results': [],
    }
    targets = []
    if args.only in ('cpu', 'both'):
        targets.append('cpu')
    if args.only in ('cuda', 'both') and torch.cuda.is_available():
        targets.append('cuda')
    for t in targets:
        report['results'].append(bench(t, args.steps))
    import json
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if len(report['results']) == 2:
        cpu, cuda = report['results'][0], report['results'][1]
        print(f"\n加速比(CPU/GPU ms per step): {cpu['ms_per_step'] / max(1e-9, cuda['ms_per_step']):.2f}x", file=sys.stderr)


if __name__ == '__main__':
    main()
