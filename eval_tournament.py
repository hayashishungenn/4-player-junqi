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
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train_junqi_5070ti as T  # noqa: E402


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
    ap.add_argument("--baseline", default="HeuristicBotWrapper")
    ap.add_argument("--out", default=str(HERE / "results" / "tournament.jsonl"))
    ap.add_argument("--replay", action="store_true", help="额外保存和局/败局的完整逐步回放")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    baseline = T.HeuristicBotWrapper().cuda().eval()

    ckpt_hashes = {p: sha256(p) for p in args.candidates}
    meta = {
        "type": "meta",
        "impl_file": T.__file__,
        "torch": torch.__version__,
        "cuda": torch.cuda.is_available(),
        "baseline": args.baseline,
        "games_per_candidate": args.games,
        "seed_base": args.seed_base,
        "max_steps": 240,
        "checkpoint_sha256": ckpt_hashes,
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
                    rec = play_one(model, baseline, seed)
                    model_won = rec["winner_team"] == 0
                else:
                    rec = play_one(baseline, model, seed)
                    model_won = rec["winner_team"] == 1
                row = {
                    "type": "game",
                    "checkpoint": Path(ckpt).name,
                    "checkpoint_sha256": ckpt_hashes[ckpt][:16],
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
