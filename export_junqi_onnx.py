"""把 JunqiActorCritic 检查点导出为 ONNX 并测量 batch=1 单步推理延迟。

目标：GPU 单步推理 <5ms（任务书阶段五验收标准）。
输出：junqi_actor_critic.onnx（不入库）。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train_junqi_5070ti as T  # noqa: E402


def main():
    ckpt_path = HERE / "junqi_rtx5070ti_latest.pt"
    onnx_path = HERE / "junqi_actor_critic.onnx"

    model = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    model.load_state_dict(torch.load(ckpt_path, map_location="cuda:0"))

    dummy_obs = torch.zeros(1, 60, 17, 17, device="cuda")
    dummy_mask = torch.ones(1, T.MAX_ACTIONS, dtype=torch.bool, device="cuda")

    torch.onnx.export(
        model, (dummy_obs, dummy_mask), str(onnx_path),
        input_names=["obs", "action_mask"], output_names=["logits", "value"],
        opset_version=17, dynamo=False,
    )
    print(f"[ONNX] 已导出 {onnx_path.name}")

    # PyTorch 原生延迟
    for _ in range(30):
        model(dummy_obs, dummy_mask)
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    N = 200
    with torch.no_grad():
        for _ in range(N):
            model(dummy_obs, dummy_mask)
    torch.cuda.synchronize()
    pt_ms = (time.perf_counter() - t0) / N * 1000

    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(onnx_path), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        obs_np = np.zeros((1, 60, 17, 17), dtype=np.float32)
        mask_np = np.ones((1, T.MAX_ACTIONS), dtype=bool)
        for _ in range(30):
            sess.run(None, {"obs": obs_np, "action_mask": mask_np})
        t0 = time.perf_counter()
        for _ in range(N):
            sess.run(None, {"obs": obs_np, "action_mask": mask_np})
        ort_ms = (time.perf_counter() - t0) / N * 1000
        prov = sess.get_providers()
    except ImportError:
        ort_ms = float("nan")
        prov = "onnxruntime 未安装"

    print(f"[延迟] PyTorch cuda batch=1: {pt_ms:.2f} ms (目标 <5ms)")
    print(f"[延迟] ONNXRuntime {prov}: {ort_ms:.2f} ms")


if __name__ == "__main__":
    main()
