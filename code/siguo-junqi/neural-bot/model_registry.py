#!/usr/bin/env python3
"""Champion / Challenger 模型注册体系（P9.3）。

设计约束：
- 历史模型不得被覆盖：每个版本写入 versions/vNNNN/ 独立目录，权重与元数据一起保存。
- 只有 Challenger 在独立评测中表现出统计上可信的提升，才允许晋级 Champion。
- 保存：模型版本、权重、训练参数、训练局数、评测结果、晋级原因、对应 Git Commit。
- 权重文件（*.pt）由 .gitignore 排除，不入库；这里只管理磁盘上的版本目录。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

CHAMPION_FILE = "champion.json"
VERSIONS_DIR = "versions"


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ModelRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.versions_dir = self.root / VERSIONS_DIR
        self.champion_path = self.root / CHAMPION_FILE
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _next_version(self) -> int:
        nums = []
        for entry in self.versions_dir.glob("v*"):
            if entry.is_dir() and entry.name[1:].isdigit():
                nums.append(int(entry.name[1:]))
        return max(nums, default=0) + 1

    def save_snapshot(self, model_path: str | Path, meta: dict) -> dict:
        """把当前权重复制为不可变版本快照，返回版本元数据。"""
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        version = self._next_version()
        target_dir = self.versions_dir / f"v{version:04d}"
        target_dir.mkdir(parents=True)
        weight = target_dir / "model.pt"
        shutil.copy2(model_path, weight)
        record = dict(meta)
        record.update({
            "version": version,
            "weight_file": str(weight.relative_to(self.root)).replace("\\", "/"),
            "weight_sha256": _sha256(weight),
            "saved_at": record.get("saved_at"),
        })
        _atomic_json(target_dir / "meta.json", record)
        return record

    def list_versions(self) -> list[dict]:
        out = []
        for entry in sorted(self.versions_dir.glob("v*")):
            meta_file = entry / "meta.json"
            if meta_file.exists():
                out.append(json.loads(meta_file.read_text(encoding="utf-8")))
        return out

    def get_champion(self) -> dict | None:
        if not self.champion_path.exists():
            return None
        return json.loads(self.champion_path.read_text(encoding="utf-8"))

    @staticmethod
    def is_significant(evaluation: dict, min_games: int = 40, min_win_rate: float = 0.55,
                       min_ci_low: float = 0.50) -> tuple[bool, str]:
        """统计晋级门槛：样本充足、胜率过半且 Wilson 下界高于 0.5。"""
        games = int(evaluation.get("games", 0))
        if games < min_games:
            return False, f"样本不足：{games} < {min_games}"
        rate = float(evaluation.get("challenger_win_rate", evaluation.get("win_rate", 0)))
        if rate < min_win_rate:
            return False, f"胜率不足：{rate:.3f} < {min_win_rate}"
        ci_low = float(evaluation.get("challenger_ci_low", evaluation.get("win_rate_ci_low", 0)))
        if ci_low < min_ci_low:
            return False, f"置信区间下界不足：{ci_low:.3f} < {min_ci_low}"
        return True, "样本、胜率与置信区间下界均达到晋级门槛"

    def promote(self, challenger_version: int, evaluation: dict, reason: str,
                git_commit: str, enforce: bool = True) -> dict:
        """评审 Challenger 并（在统计显著时）晋级为 Champion。"""
        versions = {v["version"]: v for v in self.list_versions()}
        if challenger_version not in versions:
            raise ValueError(f"未知版本 {challenger_version}")
        ok, detail = self.is_significant(evaluation)
        if enforce and not ok:
            return {"promoted": False, "reason": detail, "challenger_version": challenger_version}
        record = dict(versions[challenger_version])
        record.update({
            "evaluation": evaluation,
            "promotion_reason": reason,
            "git_commit": git_commit,
            "promoted_at": record.get("saved_at"),
        })
        _atomic_json(self.champion_path, record)
        return {"promoted": True, "reason": reason, "challenger_version": challenger_version,
                "champion": record}
