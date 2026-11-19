#!/usr/bin/env python3
"""model_registry 单元测试：版本不可覆盖、晋级门槛、历史模型保留。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model_registry import ModelRegistry


class TestModelRegistry(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.registry = ModelRegistry(self.dir.name)
        self.weight = Path(self.dir.name) / "current.pt"
        self.weight.write_bytes(b"fake-weight-v1")

    def tearDown(self):
        self.dir.cleanup()

    def test_version_snapshots_do_not_overwrite(self):
        v1 = self.registry.save_snapshot(self.weight, {"trained_games": 100, "modes": ["alliance"]})
        self.assertEqual(v1["version"], 1)
        self.weight.write_bytes(b"fake-weight-v2-different")
        v2 = self.registry.save_snapshot(self.weight, {"trained_games": 200, "modes": ["ffa"]})
        self.assertEqual(v2["version"], 2)
        self.assertNotEqual(v1["weight_sha256"], v2["weight_sha256"])
        versions = self.registry.list_versions()
        self.assertEqual([v["version"] for v in versions], [1, 2])
        # 历史版本权重内容保持不变。
        v1_weight = Path(self.dir.name) / v1["weight_file"]
        self.assertEqual(v1_weight.read_bytes(), b"fake-weight-v1")

    def test_promotion_requires_significant_evidence(self):
        self.registry.save_snapshot(self.weight, {"trained_games": 40})
        weak = {"games": 10, "challenger_win_rate": 0.9, "challenger_ci_low": 0.7}
        result = self.registry.promote(1, weak, "样本太少", "abc123")
        self.assertFalse(result["promoted"])
        self.assertIsNone(self.registry.get_champion())
        strong = {"games": 60, "challenger_win_rate": 0.62, "challenger_ci_low": 0.51}
        result = self.registry.promote(1, strong, "统计显著提升", "def456")
        self.assertTrue(result["promoted"])
        champ = self.registry.get_champion()
        self.assertEqual(champ["version"], 1)
        self.assertEqual(champ["git_commit"], "def456")
        self.assertEqual(champ["promotion_reason"], "统计显著提升")

    def test_low_win_rate_rejected(self):
        self.registry.save_snapshot(self.weight, {"trained_games": 50})
        result = self.registry.promote(1,
            {"games": 100, "challenger_win_rate": 0.48, "challenger_ci_low": 0.40},
            "棋力未提升", "xxx")
        self.assertFalse(result["promoted"])
        self.assertIsNone(self.registry.get_champion())


if __name__ == "__main__":
    unittest.main(verbosity=2)
