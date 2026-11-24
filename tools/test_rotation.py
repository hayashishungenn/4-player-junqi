"""坐标系一致性回归测试。

运行：python tools/test_rotation.py
依赖：与训练脚本相同（numpy + torch），但不需要 CUDA。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import train_junqi_5070ti as T  # noqa: E402


def test_rot_point_matches_np_rot90():
    """_rot_point 必须与 np.rot90 的坐标变换一致。"""
    for seat in range(4):
        k = T.ROTATE_K[seat]
        grid = np.zeros((17, 17), dtype=np.int32)
        r, c = 7, 11
        grid[r, c] = 1
        rotated = np.rot90(grid, k=k)
        rr, cc = T.JunqiSelfPlayEnv._rot_point((r, c), k)
        assert rotated[rr, cc] == 1, (seat, k, (r, c), (rr, cc))
    print('PASS: _rot_point 与 np.rot90 一致')


def test_belief_encoding_matches_tracker():
    """obs 的 belief 通道必须等于 tracker.beliefs 按 ROTATE_K[seat] 旋转。"""
    random.seed(1)
    np.random.seed(1)
    env = T.JunqiSelfPlayEnv()
    env.reset()
    for seat in range(4):
        obs = env.get_obs(seat)
        k = T.ROTATE_K[seat]
        enemies = [(seat + 1) % 4, (seat + 3) % 4]
        for ei, en in enumerate(enemies):
            tr = env.tracker.beliefs[en]
            expected = np.stack([np.rot90(tr[:, :, t], k=k) for t in range(12)], axis=0)
            actual = obs[28 + ei * 12:28 + (ei + 1) * 12]
            assert np.allclose(expected, actual, atol=1e-6), (seat, en)
    print('PASS: obs belief 编码与 tracker 旋转一致')


def test_old_indexing_was_wrong():
    """回归：用原始坐标索引旋转后的 obs 是错的（修复前的缺陷）。"""
    random.seed(1)
    np.random.seed(1)
    env = T.JunqiSelfPlayEnv()
    env.reset()
    for seat in (1, 2, 3):  # seat 0 无旋转，不会暴露问题
        obs = env.get_obs(seat)
        block = obs[28:40]
        en = (seat + 1) % 4
        tr = env.tracker.beliefs[en]
        pos = np.argwhere((env.owner_board == en) & (env.piece_board >= 0))
        r, c = (int(x) for x in pos[0])
        assert not np.allclose(tr[r, c], block[:, r, c]), seat
    print('PASS: 修复前的坐标错配已被复现（证明修复必要）')


if __name__ == '__main__':
    test_rot_point_matches_np_rot90()
    test_belief_encoding_matches_tracker()
    test_old_indexing_was_wrong()
    print('all rotation tests passed')
