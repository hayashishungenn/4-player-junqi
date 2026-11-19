#!/usr/bin/env python3
"""GNN 自我对弈信息边界回归测试（P9.2）。

验证真实 self_play_env 输出的局面中，对手未公开棋子的 type 一律为 None，
即真实隐藏兵种在进入策略网络之前已被投影层剥离。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from self_play import LocalEnvironment


class TestInfoBoundary(unittest.TestCase):
    def test_hidden_enemy_types_stripped(self):
        env = LocalEnvironment()
        try:
            for mode in ("alliance", "ffa"):
                state = env.reset(mode)
                viewer = state["viewerSeat"]
                hidden = [p for p in state["pieces"]
                          if p["owner"] != viewer and not p.get("revealed")]
                self.assertGreater(len(hidden), 0, f"{mode}: 应有对手暗子")
                for piece in hidden:
                    self.assertIsNone(piece.get("type"),
                                      f"{mode}: 对手暗子 {piece['id']} 不应携带真实兵种")
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
