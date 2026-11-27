"""四国暗棋联盟棋力配对复评（任务书：可复现评测 / 模型取舍）。

设计要点：
- 加载外层 train_junqi_5070ti.py（评测实际加载的实现，见报告）。
- 固定种子：random.seed + np.random.seed 后再 reset()，布局可复现。
- 配对：每个候选 checkpoint 用同一 seeds 序列对战同一 HeuristicBotWrapper 基线。
- 座位：偶数局模型在 team0(seat 0/2)，奇数局模型在 team1(seat 1/3)，抵消座位偏差。
- 逐局 JSONL：模型哈希、seed、座位、布局哈希、终局原因、步数、每步(seat,action)。
- 终局原因：从 step_count / no_capture_steps / winner_team 反推，分账 active-draw /
  step-limit / no-capture / flag-or-elimination。

用法：
  python eval_tournament.py --candidates <ckpt1> <ckpt2> ... --games 100 \
      --seed-base 90000 --out results/tournament.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# torch / 训练实现延迟到参数解析之后导入：无 torch 的环境仍可用 --help。
torch = None
T = None
# 最小基线注册表：名称 -> 返回实现类的工厂（调用前需先 _load_runtime()）。
BASELINE_REGISTRY = {"HeuristicBotWrapper": lambda: T.HeuristicBotWrapper()}


def _load_runtime():
    global torch, T
    import torch as _torch
    import train_junqi_5070ti as _impl
    torch, T = _torch, _impl


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoint_id(path: str) -> str:
    """唯一标识候选：用绝对路径，避免两份 workspace 副本的同名 latest.pt 被合并。"""
    return str(Path(path).expanduser().resolve())


def _git(*args: str):
    """读取 git 元数据；不在 git 仓库或 git 不可用时返回 None。"""
    try:
        return subprocess.run(
            ["git", *args], cwd=str(HERE), capture_output=True, text=True,
            timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def classify_termination(env, winner: int, max_steps: int) -> str:
    """终局原因分账（基于 env 可见状态，不改训练脚本）。"""
    if winner in (0, 1):
        # 有胜方：扛旗或全灭（引擎不区分，统一记账为 decisive）
        return "decisive"
    # winner == -1：和局，进一步区分
    if env.no_capture_steps >= 120:
        return "no_capture_draw"
    if env.step_count >= max_steps:
        return "step_limit_draw"
    return "other_draw"


def layout_hash(env) -> str:
    return hashlib.sha256(env.owner_board.tobytes() + env.piece_board.tobytes()).hexdigest()[:16]


def play_one(model_team0, model_team1, seed: int, max_steps: int = 240):
    """用固定 seed 跑一局，返回逐局记录。model_team0/team1 为可调用 (obs,mask)->logits。"""
    random.seed(seed)
    np.random.seed(seed)
    env = T.JunqiSelfPlayEnv(max_steps=max_steps)
    env.reset()
    lhash = layout_hash(env)
    trace = []
    steps = 0
    t0 = time.perf_counter()
    while steps < max_steps + 16:
        seat = env.current_seat
        obs = torch.from_numpy(env.get_obs(seat)).unsqueeze(0).cuda()
        mask = torch.from_numpy(env.get_action_mask(seat)).unsqueeze(0).cuda()
        with torch.no_grad():
            fn = model_team0 if seat % 2 == 0 else model_team1
            logits, _ = fn(obs, mask)
        action = int(logits.argmax(dim=-1).item())
        _, done, info = env.step(action)
        trace.append([seat, action])
        steps += 1
        if done:
            break
    winner = int(info.get("winner_team", -1)) if steps > 0 else -1
    return {
        "seed": seed,
        "layout_hash": lhash,
        "winner_team": winner,
        "termination": classify_termination(env, winner, max_steps),
        "plies": steps,
        "step_count": env.step_count,
        "no_capture_steps": env.no_capture_steps,
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "trace": trace,
    }


def load_model(path: str):
    m = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    m.load_state_dict(torch.load(path, map_location="cuda", weights_only=True))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", nargs="+", required=True)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--seed-base", type=int, default=90000)
    ap.add_argument("--baseline", default="HeuristicBotWrapper",
                    help=f"评测基线名称（可选: {', '.join(BASELINE_REGISTRY)}；默认 HeuristicBotWrapper）")
    ap.add_argument("--max-steps", type=int, default=240,
                    help="每局最大步数（默认 240；与历史评测保持可比）")
    ap.add_argument("--out", default=str(HERE / "results" / "derived" / "tournament.jsonl"),
                    help="输出 JSONL；默认写 results/derived/，避免覆盖被跟踪归档")
    ap.add_argument("--replay", action="store_true",
                    help="保存全部局（胜/负/和）的完整逐步 trace；默认不写 trace")
    args = ap.parse_args()

    if args.baseline not in BASELINE_REGISTRY:
        ap.error(f"未知基线 --baseline {args.baseline!r}；可选: {', '.join(BASELINE_REGISTRY)}")
    _load_runtime()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    baseline = BASELINE_REGISTRY[args.baseline]().cuda().eval()

    ckpt_hashes = {p: sha256(p) for p in args.candidates}
    impl_sha = sha256(T.__file__)
    status = _git("status", "--porcelain")
    meta = {
        "type": "meta",
        "impl_file": T.__file__,
        "torch": torch.__version__,
        "cuda": torch.cuda.is_available(),
        "baseline": args.baseline,
        "games_per_candidate": args.games,
        "seed_base": args.seed_base,
        "max_steps": args.max_steps,
        "git_commit": _git("rev-parse", "HEAD"),
        "worktree_dirty": None if status is None else bool(status),
        "cmdline": list(sys.argv),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "impl_file_sha256": impl_sha,
        "layout_generator_sha256": impl_sha,
        "eval_tournament_sha256": sha256(str(HERE / "eval_tournament.py")),
        "analyze_tournament_sha256": sha256(str(HERE / "tools" / "analyze_tournament.py")),
        "checkpoint_sha256": ckpt_hashes,
        "checkpoint_ids": {checkpoint_id(p): p for p in args.candidates},
        "model_arch": "JunqiActorCritic hidden=160 blocks=8",
        "seat_policy": "even game: model=team0; odd game: model=team1",
    }

    started = time.perf_counter()
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for ckpt in args.candidates:
            model = load_model(ckpt)
            for g in range(args.games):
                seed = args.seed_base + g
                model_on_team0 = (g % 2 == 0)
                if model_on_team0:
                    rec = play_one(model, baseline, seed, max_steps=args.max_steps)
                    model_won = rec["winner_team"] == 0
                else:
                    rec = play_one(baseline, model, seed, max_steps=args.max_steps)
                    model_won = rec["winner_team"] == 1
                row = {
                    "type": "game",
                    "checkpoint": Path(ckpt).name,
                    "checkpoint_id": checkpoint_id(ckpt),
                    "checkpoint_sha256": ckpt_hashes[ckpt][:16],
                    "checkpoint_sha256_full": ckpt_hashes[ckpt],
                    "game_idx": g,
                    "model_team": 0 if model_on_team0 else 1,
                    "model_won": model_won,
                    "model_lost": (rec["winner_team"] in (0, 1)) and not model_won,
                    **rec,
                }
                if not args.replay:
                    row.pop("trace", None)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
            del model
            torch.cuda.empty_cache()
            print(f"[{Path(ckpt).name}] {args.games} games done, "
                  f"elapsed={time.perf_counter()-started:.1f}s", flush=True)
    print(f"written: {out}")


if __name__ == "__main__":
    main()
