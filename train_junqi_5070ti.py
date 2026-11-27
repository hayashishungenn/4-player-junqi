import copy
import ctypes
import multiprocessing as mp
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# =====================================================================
# 1. 全局常量与棋盘拓扑 (17x17 十字网格, 129 有效站点)
# =====================================================================
NUM_PIECE_TYPES = 12
# 0:司令, 1:军长, 2:师长, 3:旅长, 4:团长, 5:营长, 6:连长, 7:排长, 8:工兵, 9:地雷, 10:炸弹, 11:军旗
PIECE_COUNTS = [1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 2, 1]
PIECE_RANKS = {0: 9, 1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
ROTATE_K = {0: 0, 1: 3, 2: 2, 3: 1}
UNROTATE_K = {0: 0, 1: 1, 2: 2, 3: 3}
MAX_ACTIONS = 289 * 289  # 83,521


def build_board_topology():
    valid_mask = np.zeros((17, 17), dtype=np.bool_)
    rail_mask = np.zeros((17, 17), dtype=np.bool_)
    camp_mask = np.zeros((17, 17), dtype=np.bool_)
    hq_mask = np.zeros((17, 17), dtype=np.bool_)

    valid_mask[11:17, 6:11] = True
    valid_mask[6:11, 11:17] = True
    valid_mask[0:6, 6:11] = True
    valid_mask[6:11, 0:6] = True
    valid_mask[7:10, 7:10] = True

    rail_mask[7:10, 7:10] = True
    for r in [11, 15, 1, 5]:
        rail_mask[r, 6:11] = True
    for c in [6, 10]:
        rail_mask[11:16, c] = True
        rail_mask[1:6, c] = True
    for c in [11, 15, 1, 5]:
        rail_mask[6:11, c] = True
    for r in [6, 10]:
        rail_mask[r, 11:16] = True
        rail_mask[r, 1:6] = True

    base_camps = [(12, 7), (12, 9), (13, 8), (14, 7), (14, 9)]
    base_hqs = [(16, 7), (16, 9)]
    for k in range(4):
        tmp_c = np.zeros((17, 17), dtype=np.bool_)
        tmp_h = np.zeros((17, 17), dtype=np.bool_)
        for r, c in base_camps:
            tmp_c[r, c] = True
        for r, c in base_hqs:
            tmp_h[r, c] = True
        camp_mask |= np.rot90(tmp_c, k=k)
        hq_mask |= np.rot90(tmp_h, k=k)

    adj = {(r, c): [] for r in range(17) for c in range(17) if valid_mask[r, c]}
    for r, c in adj:
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if (nr, nc) in adj:
                adj[(r, c)].append((nr, nc))
        if camp_mask[r, c]:
            for dr in [-1, 1]:
                for dc in [-1, 1]:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) in adj:
                        adj[(r, c)].append((nr, nc))
                        if (r, c) not in adj[(nr, nc)]:
                            adj[(nr, nc)].append((r, c))

    arc_rails = [((11, 6), (10, 5)), ((11, 10), (10, 11)), ((5, 6), (6, 5)), ((5, 10), (6, 11))]
    for u, v in arc_rails:
        adj[u].append(v)
        adj[v].append(u)

    return valid_mask, rail_mask, camp_mask, hq_mask, adj


# =====================================================================
# 2. 贝叶斯暗棋信念追踪器
# =====================================================================
class BayesianBeliefTracker:
    def __init__(self, hq_mask: np.ndarray):
        self.hq_mask = hq_mask
        self.beliefs = np.zeros((4, 17, 17, NUM_PIECE_TYPES), dtype=np.float32)

    def reset_player(self, seat: int, piece_positions: List[Tuple[int, int]]):
        self.beliefs[seat].fill(0.0)
        prior = np.array(PIECE_COUNTS, dtype=np.float32) / 25.0
        k = ROTATE_K[seat]
        for r, c in piece_positions:
            rot_grid = np.zeros((17, 17), dtype=np.bool_)
            rot_grid[r, c] = True
            local_r, _ = np.argwhere(np.rot90(rot_grid, k=k))[0]
            p = prior.copy()
            p[11] = 0.5 if self.hq_mask[r, c] else 0.0
            if local_r == 11:
                p[10] = 0.0
            if local_r < 15:
                p[9] = 0.0
            p /= (p.sum() + 1e-8)
            self.beliefs[seat, r, c] = p

    def on_move(self, seat: int, src: Tuple[int, int], dst: Tuple[int, int], turned_corner: bool):
        p = self.beliefs[seat, src[0], src[1]].copy()
        p[9] = 0.0
        p[11] = 0.0
        if turned_corner:
            eng = p[8]
            p.fill(0.0)
            p[8] = max(eng, 1.0)
        p /= (p.sum() + 1e-8)
        self.beliefs[seat, src[0], src[1]].fill(0.0)
        self.beliefs[seat, dst[0], dst[1]] = p

    def on_combat(self, winner_seat: int, pos: Tuple[int, int], loser_type: int, is_draw: bool):
        if is_draw:
            self.beliefs[:, pos[0], pos[1]].fill(0.0)
            return
        p = self.beliefs[winner_seat, pos[0], pos[1]].copy()
        if loser_type == 9:
            p.fill(0.0)
            p[8] = 1.0
        elif loser_type in PIECE_RANKS:
            loser_rank = PIECE_RANKS[loser_type]
            for t, rank in PIECE_RANKS.items():
                if rank <= loser_rank:
                    p[t] = 0.0
            p[9] = p[10] = p[11] = 0.0
        p /= (p.sum() + 1e-8)
        self.beliefs[winner_seat, pos[0], pos[1]] = p

    def on_commander_dead(self, seat: int, true_flag_pos: Tuple[int, int]):
        self.beliefs[seat, :, :, 11] = 0.0
        self.beliefs[seat, true_flag_pos[0], true_flag_pos[1]].fill(0.0)
        self.beliefs[seat, true_flag_pos[0], true_flag_pos[1], 11] = 1.0


# =====================================================================
# 3. 四国军棋仿真环境 (带 2v2 团队奖励共享)
# =====================================================================
class JunqiSelfPlayEnv:
    ARC_PAIRS = {
        ((11, 6), (10, 5)), ((10, 5), (11, 6)),
        ((11, 10), (10, 11)), ((10, 11), (11, 10)),
        ((5, 6), (6, 5)), ((6, 5), (5, 6)),
        ((5, 10), (6, 11)), ((6, 11), (5, 10)),
    }

    def __init__(self, max_steps: int = 240):
        self.max_steps = max_steps
        self.valid_mask, self.rail_mask, self.camp_mask, self.hq_mask, self.adj = build_board_topology()
        self.tracker = BayesianBeliefTracker(self.hq_mask)
        self.reset()

    def _generate_random_valid_layout(self, seat: int) -> Dict[Tuple[int, int], int]:
        k = UNROTATE_K[seat]
        slots = [
            (r, c) for r in range(11, 17) for c in range(6, 11)
            if (r, c) not in [(12, 7), (12, 9), (13, 8), (14, 7), (14, 9)]
        ]
        pieces = [t for t, cnt in enumerate(PIECE_COUNTS) for _ in range(cnt)]

        layout_local = {}
        hq_choice = random.choice([(16, 7), (16, 9)])
        layout_local[hq_choice] = 11
        slots.remove(hq_choice)
        pieces.remove(11)

        mine_slots = random.sample([s for s in slots if s[0] >= 15], 3)
        for ms in mine_slots:
            layout_local[ms] = 9
            slots.remove(ms)
            pieces.remove(9)

        bomb_slots = random.sample([s for s in slots if s[0] > 11], 2)
        for bs in bomb_slots:
            layout_local[bs] = 10
            slots.remove(bs)
            pieces.remove(10)

        random.shuffle(pieces)
        for s, p in zip(slots, pieces):
            layout_local[s] = p

        global_layout = {}
        for (lr, lc), p_type in layout_local.items():
            grid = np.full((17, 17), -1, dtype=np.int8)
            grid[lr, lc] = p_type
            gr, gc = np.argwhere(np.rot90(grid, k=k) >= 0)[0]
            global_layout[(int(gr), int(gc))] = p_type
        return global_layout

    def reset(self):
        self.owner_board = np.full((17, 17), -1, dtype=np.int8)
        self.piece_board = np.full((17, 17), -1, dtype=np.int8)
        self.alive_players = [True, True, True, True]
        self.commander_dead = [False, False, False, False]
        self.flag_pos = {}
        self.last_move_src = None
        self.last_move_dst = None
        self.step_count = 0
        self.no_capture_steps = 0

        for seat in range(4):
            layout = self._generate_random_valid_layout(seat)
            for (r, c), p_type in layout.items():
                self.owner_board[r, c] = seat
                self.piece_board[r, c] = p_type
                if p_type == 11:
                    self.flag_pos[seat] = (r, c)
            self.tracker.reset_player(seat, list(layout.keys()))

        self.current_seat = 0
        return self.get_obs(0), self.get_action_mask(0)

    def _get_reachable_targets(self, seat: int, src: Tuple[int, int]) -> List[Tuple[Tuple[int, int], bool]]:
        p_type = self.piece_board[src]
        if p_type in (9, 11) or self.hq_mask[src]:
            return []

        targets = {}
        for nxt in self.adj[src]:
            occ = self.owner_board[nxt]
            if occ == -1:
                targets[nxt] = False
            elif (occ % 2) != (seat % 2) and not self.camp_mask[nxt]:
                targets[nxt] = False

        if self.rail_mask[src]:
            if p_type == 8:
                visited = {src}
                queue = deque([(src, None, False)])
                while queue:
                    curr, prev_dir, turned = queue.popleft()
                    for nxt in self.adj[curr]:
                        if nxt in visited or not self.rail_mask[nxt]:
                            continue
                        if abs(nxt[0] - curr[0]) == 1 and abs(nxt[1] - curr[1]) == 1:
                            if (curr, nxt) not in self.ARC_PAIRS:
                                continue
                        cur_dir = (nxt[0] - curr[0], nxt[1] - curr[1])
                        new_turned = turned or (prev_dir is not None and cur_dir != prev_dir)
                        occ = self.owner_board[nxt]
                        if occ == -1:
                            visited.add(nxt)
                            targets[nxt] = new_turned
                            queue.append((nxt, cur_dir, new_turned))
                        elif (occ % 2) != (seat % 2) and not self.camp_mask[nxt]:
                            visited.add(nxt)
                            targets[nxt] = new_turned
            else:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    cr, cc = src[0] + dr, src[1] + dc
                    while 0 <= cr < 17 and 0 <= cc < 17 and self.rail_mask[cr, cc]:
                        occ = self.owner_board[cr, cc]
                        if occ == -1:
                            targets[(cr, cc)] = False
                        else:
                            if (occ % 2) != (seat % 2) and not self.camp_mask[cr, cc]:
                                targets[(cr, cc)] = False
                            break
                        cr += dr
                        cc += dc

        return list(targets.items())

    @staticmethod
    def _rot_point(pt: Tuple[int, int], k: int) -> Tuple[int, int]:
        r, c = pt
        if k == 0:
            return r, c
        elif k == 1:
            return 16 - c, r
        elif k == 2:
            return 16 - r, 16 - c
        else:
            return c, 16 - r

    def get_action_mask(self, seat: int) -> np.ndarray:
        mask = np.zeros(MAX_ACTIONS, dtype=np.bool_)
        if not self.alive_players[seat]:
            return mask
        k = ROTATE_K[seat]
        for r, c in np.argwhere(self.owner_board == seat):
            src = (int(r), int(c))
            sr, sc = self._rot_point(src, k)
            s_base = (sr * 17 + sc) * 289
            for dst, _ in self._get_reachable_targets(seat, src):
                er, ec = self._rot_point(dst, k)
                mask[s_base + er * 17 + ec] = True
        return mask

    def get_obs(self, seat: int) -> np.ndarray:
        k = ROTATE_K[seat]
        ally = (seat + 2) % 4
        enemy_a = (seat + 1) % 4
        enemy_b = (seat + 3) % 4

        obs = np.zeros((60, 17, 17), dtype=np.float32)
        obs[0] = np.rot90(self.valid_mask, k=k)
        obs[1] = np.rot90(self.rail_mask, k=k)
        obs[2] = np.rot90(self.camp_mask, k=k)
        obs[3] = np.rot90(self.hq_mask, k=k)

        for t in range(NUM_PIECE_TYPES):
            obs[4 + t] = np.rot90((self.owner_board == seat) & (self.piece_board == t), k=k)
            obs[16 + t] = np.rot90((self.owner_board == ally) & (self.piece_board == t), k=k)
            obs[28 + t] = np.rot90(self.tracker.beliefs[enemy_a, :, :, t], k=k)
            obs[40 + t] = np.rot90(self.tracker.beliefs[enemy_b, :, :, t], k=k)

        if self.last_move_src is not None:
            sr, sc = self._rot_point(self.last_move_src, k)
            er, ec = self._rot_point(self.last_move_dst, k)
            obs[52, sr, sc] = 1.0
            obs[53, er, ec] = 1.0

        obs[56] = float(self.commander_dead[seat])
        obs[57] = float(self.commander_dead[ally])
        obs[58] = float(self.commander_dead[enemy_a] or self.commander_dead[enemy_b])
        obs[59] = min(self.no_capture_steps / 80.0, 1.0)
        return obs

    def _eliminate_player(self, seat: int):
        self.alive_players[seat] = False
        m = (self.owner_board == seat)
        self.owner_board[m] = -1
        self.piece_board[m] = -1
        self.tracker.beliefs[seat].fill(0.0)

    def step(self, action_id: int, shaping_weight: float = 1.0):
        seat = self.current_seat
        team = seat % 2
        self.step_count += 1
        reward = -0.005

        mask = self.get_action_mask(seat)
        if not mask.any():
            if self.alive_players[seat]:
                self._eliminate_player(seat)
        else:
            s_idx, e_idx = divmod(int(action_id), 289)
            sr, sc = divmod(s_idx, 17)
            er, ec = divmod(e_idx, 17)
            uk = UNROTATE_K[seat]
            src = self._rot_point((sr, sc), uk)
            dst = self._rot_point((er, ec), uk)

            turned = any(t for pos, t in self._get_reachable_targets(seat, src) if pos == dst)
            att_type = int(self.piece_board[src])
            def_owner = int(self.owner_board[dst])
            def_type = int(self.piece_board[dst])

            self.last_move_src, self.last_move_dst = src, dst

            if def_owner == -1:
                self.owner_board[src], self.piece_board[src] = -1, -1
                self.owner_board[dst], self.piece_board[dst] = seat, att_type
                self.tracker.on_move(seat, src, dst, turned)
                self.no_capture_steps += 1
            else:
                self.no_capture_steps = 0
                self.tracker.on_move(seat, src, dst, turned)
                outcome, step_bonus = self._resolve_combat(att_type, def_type)
                reward += step_bonus * shaping_weight

                if outcome == "WIN":
                    self.owner_board[src], self.piece_board[src] = -1, -1
                    self.owner_board[dst], self.piece_board[dst] = seat, att_type
                    self.tracker.beliefs[def_owner, dst[0], dst[1]].fill(0.0)
                    self.tracker.on_combat(seat, dst, def_type, is_draw=False)
                    if def_type == 0:
                        self.commander_dead[def_owner] = True
                        self.tracker.on_commander_dead(def_owner, self.flag_pos[def_owner])
                    elif def_type == 11:
                        reward += 3.0
                        self._eliminate_player(def_owner)
                elif outcome == "LOSE":
                    self.owner_board[src], self.piece_board[src] = -1, -1
                    self.tracker.beliefs[seat, dst[0], dst[1]].fill(0.0)
                    self.tracker.on_combat(def_owner, dst, att_type, is_draw=False)
                    if att_type == 0:
                        self.commander_dead[seat] = True
                        self.tracker.on_commander_dead(seat, self.flag_pos[seat])
                else:
                    self.owner_board[src], self.piece_board[src] = -1, -1
                    self.owner_board[dst], self.piece_board[dst] = -1, -1
                    self.tracker.on_combat(seat, dst, def_type, is_draw=True)
                    if att_type == 0:
                        self.commander_dead[seat] = True
                        self.tracker.on_commander_dead(seat, self.flag_pos[seat])
                    if def_type == 0:
                        self.commander_dead[def_owner] = True
                        self.tracker.on_commander_dead(def_owner, self.flag_pos[def_owner])

        team0_alive = self.alive_players[0] or self.alive_players[2]
        team1_alive = self.alive_players[1] or self.alive_players[3]
        done = False
        winner_team = -1

        if not team0_alive:
            done, winner_team = True, 1
        elif not team1_alive:
            done, winner_team = True, 0
        elif self.step_count >= self.max_steps or self.no_capture_steps >= 120:
            done, winner_team = True, -1

        if done and winner_team != -1:
            reward += 10.0 if winner_team == team else -10.0

        for _ in range(4):
            self.current_seat = (self.current_seat + 1) % 4
            if self.alive_players[self.current_seat]:
                break

        return reward, done, {"acting_team": team, "winner_team": winner_team}

    @staticmethod
    def _resolve_combat(att: int, dfd: int) -> Tuple[str, float]:
        if dfd == 11:
            return "WIN", 0.0
        if att == 10 or dfd == 10:
            return "DRAW", (0.4 if (att == 10 and dfd in (0, 1)) else 0.05)
        if dfd == 9:
            return ("WIN", 0.25) if att == 8 else ("LOSE", -0.1)
        r_att, r_dfd = PIECE_RANKS[att], PIECE_RANKS[dfd]
        if r_att > r_dfd:
            # 密集奖励信号改 10 倍强度，让 PPO 学会"主动猎杀"而非"躲避保守"
            val_map = {0: 8.0, 1: 5.0, 2: 3.0, 3: 2.0, 4: 1.5, 5: 1.0, 6: 0.8, 7: 0.5, 8: 0.5}
            return "WIN", val_map[dfd]
        elif r_att < r_dfd:
            return "LOSE", -0.05
        return "DRAW", 0.02


# =====================================================================
# 4. 共享内存异步多进程采样器 (Windows Spawn 安全 + 零拷贝)
# =====================================================================
def _env_worker_process(
    worker_id: int,
    conn: mp.connection.Connection,
    shm_obs_raw,
    shm_mask_raw,
    shm_seat_raw,
    shm_opp_idx_raw,
    shm_rew_raw,
    shm_done_raw,
    shm_ready_raw,
    num_envs: int,
):
    """独立子进程: 运行环境规则引擎并直接写入共享内存"""
    np.random.seed(1000 + worker_id)
    random.seed(1000 + worker_id)

    obs_buf = np.frombuffer(shm_obs_raw, dtype=np.float32).reshape((num_envs, 60, 17, 17))
    mask_buf = np.frombuffer(shm_mask_raw, dtype=np.bool_).reshape((num_envs, MAX_ACTIONS))
    seat_buf = np.frombuffer(shm_seat_raw, dtype=np.int32)
    opp_idx_buf = np.frombuffer(shm_opp_idx_raw, dtype=np.int32)
    rew_buf = np.frombuffer(shm_rew_raw, dtype=np.float32)
    done_buf = np.frombuffer(shm_done_raw, dtype=np.bool_)
    ready_buf = np.frombuffer(shm_ready_raw, dtype=np.bool_)

    env = JunqiSelfPlayEnv()
    acc_team0_rew = 0.0

    def _sync_reset(pool_size: int):
        nonlocal acc_team0_rew
        obs, mask = env.reset()
        acc_team0_rew = 0.0
        obs_buf[worker_id] = obs
        mask_buf[worker_id] = mask
        seat_buf[worker_id] = env.current_seat
        opp_idx_buf[worker_id] = random.randint(0, max(pool_size - 1, 0))

    while True:
        cmd, payload = conn.recv()
        if cmd == "CLOSE":
            conn.close()
            break
        elif cmd == "RESET":
            pool_size = payload
            _sync_reset(pool_size)
            ready_buf[worker_id] = False
            conn.send(True)
        elif cmd == "STEP":
            action_id, shaping_weight, pool_size = payload
            acting_team = env.current_seat % 2

            # 处理无合法动作的空步淘汰
            if not mask_buf[worker_id].any():
                rew, done, info = env.step(0, shaping_weight)
            else:
                rew, done, info = env.step(action_id, shaping_weight)

            if acting_team == 0:
                acc_team0_rew = rew
            else:
                # 对手动作结束终局时，将胜负奖惩同步给 Team 0
                if done and info["winner_team"] != -1:
                    acc_team0_rew += 10.0 if info["winner_team"] == 0 else -10.0

            if done:
                rew_buf[worker_id] = acc_team0_rew
                done_buf[worker_id] = True
                ready_buf[worker_id] = True
                _sync_reset(pool_size)
            elif env.current_seat % 2 == 0:
                # 完整经过一轮交锋回到 Team 0，确认一条完整转移样本
                rew_buf[worker_id] = acc_team0_rew
                done_buf[worker_id] = False
                ready_buf[worker_id] = True
                obs_buf[worker_id] = env.get_obs(env.current_seat)
                mask_buf[worker_id] = env.get_action_mask(env.current_seat)
                seat_buf[worker_id] = env.current_seat
            else:
                # 仍在对手回合，暂不触发 Team 0 样本落盘
                ready_buf[worker_id] = False
                obs_buf[worker_id] = env.get_obs(env.current_seat)
                mask_buf[worker_id] = env.get_action_mask(env.current_seat)
                seat_buf[worker_id] = env.current_seat

            conn.send(True)


class SharedMemVecEnv:
    def __init__(self, num_envs: int):
        self.num_envs = num_envs
        ctx = mp.get_context("spawn")

        self.shm_obs_raw = ctx.RawArray(ctypes.c_float, num_envs * 60 * 17 * 17)
        self.shm_mask_raw = ctx.RawArray(ctypes.c_bool, num_envs * MAX_ACTIONS)
        self.shm_seat_raw = ctx.RawArray(ctypes.c_int32, num_envs)
        self.shm_opp_idx_raw = ctx.RawArray(ctypes.c_int32, num_envs)
        self.shm_rew_raw = ctx.RawArray(ctypes.c_float, num_envs)
        self.shm_done_raw = ctx.RawArray(ctypes.c_bool, num_envs)
        self.shm_ready_raw = ctx.RawArray(ctypes.c_bool, num_envs)

        self.obs = np.frombuffer(self.shm_obs_raw, dtype=np.float32).reshape((num_envs, 60, 17, 17))
        self.mask = np.frombuffer(self.shm_mask_raw, dtype=np.bool_).reshape((num_envs, MAX_ACTIONS))
        self.seat = np.frombuffer(self.shm_seat_raw, dtype=np.int32)
        self.opp_idx = np.frombuffer(self.shm_opp_idx_raw, dtype=np.int32)
        self.rew = np.frombuffer(self.shm_rew_raw, dtype=np.float32)
        self.done = np.frombuffer(self.shm_done_raw, dtype=np.bool_)
        self.ready = np.frombuffer(self.shm_ready_raw, dtype=np.bool_)

        self.conns = []
        self.procs = []
        for i in range(num_envs):
            parent_conn, child_conn = ctx.Pipe()
            p = ctx.Process(
                target=_env_worker_process,
                args=(
                    i, child_conn,
                    self.shm_obs_raw, self.shm_mask_raw, self.shm_seat_raw,
                    self.shm_opp_idx_raw, self.shm_rew_raw, self.shm_done_raw,
                    self.shm_ready_raw, num_envs
                ),
                daemon=True,
            )
            p.start()
            child_conn.close()
            self.conns.append(parent_conn)
            self.procs.append(p)

    def reset_all(self, pool_size: int):
        for conn in self.conns:
            conn.send(("RESET", pool_size))
        for conn in self.conns:
            conn.recv()

    def step_all(self, actions: np.ndarray, shaping_weight: float, pool_size: int):
        for i, conn in enumerate(self.conns):
            conn.send(("STEP", (int(actions[i]), shaping_weight, pool_size)))
        for conn in self.conns:
            conn.recv()

    def close(self):
        for conn in self.conns:
            try:
                conn.send(("CLOSE", None))
            except Exception:
                pass
        for p in self.procs:
            p.join(timeout=2)


# =====================================================================
# 5. GPU 神经网络架构: ResNet-8 + SE 通道注意力
# =====================================================================
class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, channels // reduction),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.fc(x).unsqueeze(-1).unsqueeze(-1)


class ResSEBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.se = SEBlock(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = F.relu(self.bn1(self.conv1(x)), inplace=True)
        out = self.se(self.bn2(self.conv2(out)))
        return F.relu(out + x, inplace=True)


class JunqiActorCritic(nn.Module):
    def __init__(self, in_channels: int = 60, hidden_dim: int = 160, num_blocks: int = 8):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, hidden_dim, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.blocks = nn.Sequential(*[ResSEBlock(hidden_dim) for _ in range(num_blocks)])

        self.policy_head = nn.Sequential(
            nn.Conv2d(hidden_dim, 32, kernel_size=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(32 * 17 * 17, 512),
            nn.ReLU(inplace=True),
            nn.Linear(512, MAX_ACTIONS),
        )

        self.value_head = nn.Sequential(
            nn.Conv2d(hidden_dim, 16, kernel_size=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Flatten(),
            nn.Linear(16 * 17 * 17, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, 1),
            nn.Tanh(),
        )

    def forward(self, obs: torch.Tensor, action_mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        feat = self.blocks(self.stem(obs))
        logits = self.policy_head(feat).float().masked_fill(~action_mask, -1e9)
        value = self.value_head(feat).float().squeeze(-1)
        return logits, value


class HeuristicBotWrapper(nn.Module):
    """内置快速规则启发式陪练 (偏好吃子与向前推进，防止自博弈遗忘)"""

    def __init__(self):
        super().__init__()
        self.dummy = nn.Parameter(torch.zeros(1), requires_grad=False)

    def forward(self, obs: torch.Tensor, action_mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # obs[:, 28:52] 为敌方A/B存在概率之和，作为落点攻击热力引导
        enemy_presence = obs[:, 28:52].sum(dim=1).flatten(1)  # [B, 289]
        # 奖励向前推进 (行号越小越靠近上方敌阵)
        row_bonus = torch.linspace(1.5, 0.0, 17, device=obs.device).repeat_interleave(17).unsqueeze(0)
        dst_scores = enemy_presence * 4.0 + row_bonus  # [B, 289]
        # 广播至 [B, 289, 289] -> [B, 83521]
        logits = dst_scores.unsqueeze(1).expand(-1, 289, -1).reshape(obs.size(0), MAX_ACTIONS)
        masked_logits = logits.masked_fill(~action_mask, -1e9)
        return masked_logits, torch.zeros(obs.size(0), device=obs.device)


# =====================================================================
# 6. RTX 5070 Ti Laptop GPU 批量训练引擎
# =====================================================================
@dataclass
class GPUTrainConfig:
    num_envs: int = 24               # 匹配多核笔记本 CPU，最大化无阻塞采样
    steps_per_env: int = 512         # 单轮收集 24 * 512 = 12,288 帧 (约占 1.8GB 显存)
    batch_size: int = 2048           # 吃满 RTX 5070 Ti Tensor Core 大批次并行
    ppo_epochs: int = 4
    total_iterations: int = 400
    lr: float = 3e-4
    gamma: float = 0.995
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef_start: float = 0.02
    ent_coef_end: float = 0.005
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    pool_max_size: int = 20
    opponent_pool_enabled: bool = False  # 阶段三：固定对手 = 启发式规则基线
    snapshot_interval: int = 10
    logp_clamp: float = 20.0             # ratio 上界；达到边界的样本比例单独记录
    kl_target: float = 0.02              # approx KL 早停阈值；触发后跳过剩余 minibatch


class HighThroughputSelfPlayTrainer:
    def __init__(self, cfg: GPUTrainConfig):
        self.cfg = cfg
        assert torch.cuda.is_available(), "未检测到 CUDA GPU，请检查 PyTorch CUDA 环境！"
        self.device = torch.device("cuda:0")

        # 开启 Blackwell / Ampere+ 硬件加速标志
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.set_float32_matmul_precision("high")

        self.amp_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        self.scaler = torch.amp.GradScaler("cuda", enabled=(self.amp_dtype == torch.float16))

        self.vec_env = SharedMemVecEnv(cfg.num_envs)
        self.policy = JunqiActorCritic(hidden_dim=160, num_blocks=8).to(self.device)

        # 尝试启用 PyTorch 2.x 图编译；torch.compile 为惰性编译，Windows 缺 Triton 时
        # 真正崩溃发生在首次前向。这里用热身前向探测，失败则安全回退 eager。
        self.compiled_policy = self.policy
        try:
            compiled = torch.compile(self.policy, mode="reduce-overhead")
            with torch.no_grad():
                dummy_obs = torch.zeros(1, 60, 17, 17, device=self.device)
                dummy_mask = torch.ones(1, MAX_ACTIONS, dtype=torch.bool, device=self.device)
                compiled(dummy_obs, dummy_mask)
            self.compiled_policy = compiled
        except Exception as e:
            print(f"[WARN] torch.compile 不可用，回退 eager 模式 ({type(e).__name__})")

        self.optimizer = torch.optim.AdamW(self.policy.parameters(), lr=cfg.lr, weight_decay=1e-4, fused=True)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=cfg.total_iterations, eta_min=1e-5
        )

        # 对手池: 索引 0 永久保留规则启发式 Bot，其余存放历史策略快照
        self.opponent_pool: List[nn.Module] = [HeuristicBotWrapper().to(self.device).eval()]
        self._push_snapshot()

        # 预分配锁页主机内存 (Pinned Memory)，加速 H2D 异步拷贝
        self.pin_obs = torch.empty((cfg.num_envs, 60, 17, 17), dtype=torch.float32, pin_memory=True)
        self.pin_mask = torch.empty((cfg.num_envs, MAX_ACTIONS), dtype=torch.bool, pin_memory=True)

        # 预分配 GPU 显存滚动缓冲区 (驻留 12GB 显存内，零额外分配开销)
        T, N = cfg.steps_per_env, cfg.num_envs
        self.buf_obs = torch.zeros((T, N, 60, 17, 17), dtype=torch.float16, device=self.device)
        self.buf_mask = torch.zeros((T, N, MAX_ACTIONS), dtype=torch.bool, device=self.device)
        self.buf_actions = torch.zeros((T, N), dtype=torch.long, device=self.device)
        self.buf_logprobs = torch.zeros((T, N), dtype=torch.float32, device=self.device)
        self.buf_values = torch.zeros((T, N), dtype=torch.float32, device=self.device)
        self.buf_rewards = torch.zeros((T, N), dtype=torch.float32, device=self.device)
        self.buf_dones = torch.zeros((T, N), dtype=torch.float32, device=self.device)

    def _push_snapshot(self):
        # 用 state_dict 克隆重建快照模型，避免整模型 deepcopy 同时双份驻留显存（+3~4GB）
        snap = JunqiActorCritic(hidden_dim=160, num_blocks=8).to(self.device)
        snap.load_state_dict(copy.deepcopy(self.policy.state_dict()))
        snap.eval()
        for p in snap.parameters():
            p.requires_grad_(False)
        if len(self.opponent_pool) >= self.cfg.pool_max_size:
            # 保留索引 0 的规则 Bot，淘汰最早的历史模型
            self.opponent_pool.pop(1)
        self.opponent_pool.append(snap)

    @torch.no_grad()
    def _batched_inference(self) -> Tuple[np.ndarray, torch.Tensor, torch.Tensor, torch.Tensor]:
        """将 24 个并发环境按阵营与对手快照分组，在 RTX 5070 Ti 上一次性批量前向推理"""
        self.pin_obs.copy_(torch.from_numpy(self.vec_env.obs))
        self.pin_mask.copy_(torch.from_numpy(self.vec_env.mask))
        gpu_obs = self.pin_obs.to(self.device, non_blocking=True)
        gpu_mask = self.pin_mask.to(self.device, non_blocking=True)

        N = self.cfg.num_envs
        actions = torch.zeros(N, dtype=torch.long, device=self.device)
        logprobs = torch.zeros(N, dtype=torch.float32, device=self.device)
        values = torch.zeros(N, dtype=torch.float32, device=self.device)

        seats = self.vec_env.seat
        learner_idx = np.where(seats % 2 == 0)[0]
        opp_indices = np.where(seats % 2 == 1)[0]

        # 1. 学习阵营批量前向推理
        if len(learner_idx) > 0:
            idx_t = torch.from_numpy(learner_idx).to(self.device, non_blocking=True)
            sub_mask = gpu_mask[idx_t]
            valid_rows = sub_mask.any(dim=1)
            if valid_rows.any():
                v_idx = idx_t[valid_rows]
                with torch.amp.autocast("cuda", dtype=self.amp_dtype):
                    logits, vals = self.compiled_policy(gpu_obs[v_idx], gpu_mask[v_idx])
                dist = torch.distributions.Categorical(logits=logits)
                acts = dist.sample()
                actions[v_idx] = acts
                logprobs[v_idx] = dist.log_prob(acts)
                values[v_idx] = vals

        # 2. 对手阵营按快照 ID 分组批量推理
        if len(opp_indices) > 0:
            opp_ids = self.vec_env.opp_idx[opp_indices]
            for pool_id in np.unique(opp_ids):
                group = opp_indices[opp_ids == pool_id]
                idx_t = torch.from_numpy(group).to(self.device, non_blocking=True)
                sub_mask = gpu_mask[idx_t]
                valid_rows = sub_mask.any(dim=1)
                if valid_rows.any():
                    v_idx = idx_t[valid_rows]
                    opp_model = self.opponent_pool[int(pool_id)]
                    with torch.amp.autocast("cuda", dtype=self.amp_dtype):
                        logits, _ = opp_model(gpu_obs[v_idx], gpu_mask[v_idx])
                    dist = torch.distributions.Categorical(logits=logits)
                    actions[v_idx] = dist.sample()

        return actions.cpu().numpy(), gpu_obs, logprobs, values

    def collect_rollout(self, shaping_weight: float) -> Tuple[float, float]:
        """并行推进 24 个环境，直至每个环境各自收满 steps_per_env 条有效 Team 0 轨迹"""
        self.policy.eval()
        T, N = self.cfg.steps_per_env, self.cfg.num_envs
        env_cursors = np.zeros(N, dtype=np.int32)
        pending_step = [None] * N
        # 每条轨迹末端（cursor 达到 T）的 Team 0 状态，供 GAE 做 bootstrap。
        bootstrap_obs = torch.zeros((N, 60, 17, 17), dtype=torch.float32, device=self.device)
        bootstrap_mask = torch.zeros((N, MAX_ACTIONS), dtype=torch.bool, device=self.device)
        pool_size = len(self.opponent_pool) if self.cfg.opponent_pool_enabled else 1

        t0 = time.perf_counter()
        total_env_ticks = 0

        while np.min(env_cursors) < T:
            actions_np, gpu_obs, logprobs, values = self._batched_inference()

            # 暂存本轮发起动作的 Team 0 状态
            for i in range(N):
                if self.vec_env.seat[i] % 2 == 0 and env_cursors[i] < T:
                    pending_step[i] = (
                        gpu_obs[i].half(),
                        self.pin_mask[i].to(self.device, non_blocking=True),
                        int(actions_np[i]),
                        float(logprobs[i].item()),
                        float(values[i].item()),
                    )

            self.vec_env.step_all(actions_np, shaping_weight, pool_size)
            total_env_ticks += N

            # 将完成完整交锋周期的 Team 0 样本写入显存缓冲区
            for i in range(N):
                if self.vec_env.ready[i] and pending_step[i] is not None and env_cursors[i] < T:
                    c = env_cursors[i]
                    obs_i, mask_i, act_i, logp_i, val_i = pending_step[i]
                    self.buf_obs[c, i] = obs_i
                    self.buf_mask[c, i] = mask_i
                    self.buf_actions[c, i] = act_i
                    self.buf_logprobs[c, i] = logp_i
                    self.buf_values[c, i] = val_i
                    self.buf_rewards[c, i] = float(self.vec_env.rew[i])
                    self.buf_dones[c, i] = float(self.vec_env.done[i])
                    env_cursors[i] += 1
                    pending_step[i] = None
                    if env_cursors[i] == T:
                        # ready 时 worker 已写入回到 Team 0 的观测；done 时为新局观测，
                        # 但对应 buf_dones=1，bootstrap 值会被 GAE 的 non_terminal 屏蔽。
                        bootstrap_obs[i] = torch.from_numpy(self.vec_env.obs[i]).to(self.device)
                        bootstrap_mask[i] = torch.from_numpy(self.vec_env.mask[i]).to(self.device)

        elapsed = time.perf_counter() - t0
        sps = total_env_ticks / max(elapsed, 1e-6)
        mean_rew = float(self.buf_rewards.mean().item())
        self.bootstrap_obs = bootstrap_obs
        self.bootstrap_mask = bootstrap_mask
        return sps, mean_rew

    def update_ppo(self, ent_coef: float) -> Dict[str, float]:
        """在 RTX 5070 Ti 显存内直接计算 GAE 并执行大批次混合精度 PPO 更新"""
        T, N = self.cfg.steps_per_env, self.cfg.num_envs

        # 轨迹末端 bootstrap 与采样同模式（eval / running stats），避免 value 口径漂移
        self.policy.eval()
        with torch.no_grad(), torch.amp.autocast("cuda", dtype=self.amp_dtype):
            _, last_values = self.compiled_policy(self.bootstrap_obs, self.bootstrap_mask)

        # 1. GPU 原地并行计算多环境 GAE
        advantages = torch.zeros_like(self.buf_rewards)
        last_gae = torch.zeros(N, dtype=torch.float32, device=self.device)
        for t in reversed(range(T)):
            non_terminal = 1.0 - self.buf_dones[t]
            next_val = self.buf_values[t + 1] if t + 1 < T else last_values
            delta = self.buf_rewards[t] + self.cfg.gamma * next_val * non_terminal - self.buf_values[t]
            last_gae = delta + self.cfg.gamma * self.cfg.gae_lambda * non_terminal * last_gae
            advantages[t] = last_gae

        returns = advantages + self.buf_values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # 扁平化为 [T * N, ...]
        flat_obs = self.buf_obs.view(T * N, 60, 17, 17)
        flat_mask = self.buf_mask.view(T * N, MAX_ACTIONS)
        flat_act = self.buf_actions.view(T * N)
        flat_adv = advantages.view(T * N)
        flat_ret = returns.view(T * N)

        total_samples = T * N

        # old_logp 用 train 模式按 batch_size 分块重算：采样在 eval（running stats）、
        # 更新在 train（batch stats），直接沿用 buf_logprobs 会让 BatchNorm 统计差异
        # 混入 importance ratio。分块使两侧 batch 规模一致，同时控制显存峰值。
        self.policy.train()
        with torch.no_grad():
            old_logp_parts = []
            for start in range(0, total_samples, self.cfg.batch_size):
                mb = slice(start, start + self.cfg.batch_size)
                with torch.amp.autocast("cuda", dtype=self.amp_dtype):
                    logits, _ = self.compiled_policy(flat_obs[mb].float(), flat_mask[mb])
                old_logp_parts.append(torch.distributions.Categorical(logits=logits).log_prob(flat_act[mb]))
            flat_old_logp = torch.cat(old_logp_parts)

        total_pg, total_vf, steps = 0.0, 0.0, 0
        total_kl, total_clip, total_entropy = 0.0, 0.0, 0.0
        total_grad_norm, total_sat = 0.0, 0.0
        early_stop = False

        for _ in range(self.cfg.ppo_epochs):
            if early_stop:
                break
            perm = torch.randperm(total_samples, device=self.device)
            for start in range(0, total_samples, self.cfg.batch_size):
                mb = perm[start:start + self.cfg.batch_size]
                with torch.amp.autocast("cuda", dtype=self.amp_dtype):
                    logits, vals = self.compiled_policy(flat_obs[mb].float(), flat_mask[mb])

                dist = torch.distributions.Categorical(logits=logits)
                new_logp = dist.log_prob(flat_act[mb])
                entropy = dist.entropy().mean()

                log_ratio = new_logp - flat_old_logp[mb]
                clamped_log_ratio = torch.clamp(
                    log_ratio, -self.cfg.logp_clamp, self.cfg.logp_clamp)
                ratio = torch.exp(clamped_log_ratio)
                # k3 approx KL，用 clamp 后的 ratio/log 比避免 exp 溢出污染日志
                approx_kl = (ratio - 1.0 - clamped_log_ratio).mean()
                clip_fraction = ((ratio < 1.0 - self.cfg.clip_range) |
                                 (ratio > 1.0 + self.cfg.clip_range)).float().mean()
                sat_fraction = (log_ratio.abs() >= self.cfg.logp_clamp).float().mean()

                s1 = ratio * flat_adv[mb]
                s2 = torch.clamp(ratio, 1.0 - self.cfg.clip_range, 1.0 + self.cfg.clip_range) * flat_adv[mb]
                pg_loss = -torch.min(s1, s2).mean()
                vf_loss = F.mse_loss(vals, flat_ret[mb])
                loss = pg_loss + self.cfg.vf_coef * vf_loss - ent_coef * entropy

                self.optimizer.zero_grad(set_to_none=True)
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                grad_norm = nn.utils.clip_grad_norm_(self.policy.parameters(), self.cfg.max_grad_norm)
                self.scaler.step(self.optimizer)
                self.scaler.update()

                total_pg += float(pg_loss.item())
                total_vf += float(vf_loss.item())
                total_kl += float(approx_kl.item())
                total_clip += float(clip_fraction.item())
                total_entropy += float(entropy.item())
                total_grad_norm += float(grad_norm.item())
                total_sat += float(sat_fraction.item())
                steps += 1

                if float(approx_kl.item()) > self.cfg.kl_target:
                    early_stop = True
                    break

        self.scheduler.step()
        denom = max(steps, 1)
        return {
            "pg": total_pg / denom,
            "vf": total_vf / denom,
            "approx_kl": total_kl / denom,
            "clip_fraction": total_clip / denom,
            "entropy": total_entropy / denom,
            "grad_norm": total_grad_norm / denom,
            "logp_clamp_saturation": total_sat / denom,
            "early_stop": early_stop,
        }

    def train(self):
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"============================================================")
        print(f"GPU: {gpu_name} ({vram_gb:.1f} GB VRAM) | 精度: {self.amp_dtype}")
        print(f"并行进程: {self.cfg.num_envs} | 单轮样本: {self.cfg.num_envs * self.cfg.steps_per_env} | Batch: {self.cfg.batch_size}")
        print(f"============================================================")

        self.vec_env.reset_all(len(self.opponent_pool))

        try:
            for it in range(1, self.cfg.total_iterations + 1):
                progress = it / self.cfg.total_iterations
                shaping_w = max(0.3, 1.0 - 0.4 * progress)
                ent_coef = self.cfg.ent_coef_start + (self.cfg.ent_coef_end - self.cfg.ent_coef_start) * progress

                sps, mean_rew = self.collect_rollout(shaping_w)
                m = self.update_ppo(ent_coef)
                if m["early_stop"]:
                    print(f"[EARLYSTOP] iter={it:03d} approx_kl={m['approx_kl']:.4f} "
                          f"target={self.cfg.kl_target}", flush=True)

                if it % self.cfg.snapshot_interval == 0:
                    self._push_snapshot()
                    torch.save(self.policy.state_dict(), f"junqi_iter{it:03d}.pt")
                    torch.save(self.policy.state_dict(), "junqi_rtx5070ti_latest.pt")

                if it % 2 == 0 or it == 1:
                    alloc_vram = torch.cuda.max_memory_allocated(0) / (1024 ** 3)
                    print(
                        f"[Iter {it:03d}/{self.cfg.total_iterations}] "
                        f"SPS={sps:6.0f} | Rew={mean_rew:+.4f} | "
                        f"PG={m['pg']:.4f} | VF={m['vf']:.4f} | "
                        f"KL={m['approx_kl']:.4f} | Clip={m['clip_fraction']:.3f} | "
                        f"Ent={m['entropy']:.4f} | GNorm={m['grad_norm']:.3f} | "
                        f"ClampSat={m['logp_clamp_saturation']:.3f} | "
                        f"Pool={len(self.opponent_pool):02d} | PeakVRAM={alloc_vram:.2f}GB"
                    )
        finally:
            self.vec_env.close()


if __name__ == "__main__":
    # Windows 多进程强制要求在 __main__ 保护块下启动
    mp.freeze_support()
    config = GPUTrainConfig(
        num_envs=24,          # 若 CPU 核心 >= 16 可调至 32，进一步提升采样 SPS
        steps_per_env=512,
        batch_size=2048,
        total_iterations=400,
    )
    trainer = HighThroughputSelfPlayTrainer(config)
    trainer.train()