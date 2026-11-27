"""回放抽查（任务书第3步 / P0-03）：分层抽样、复现性、平局来源、暗棋信息隔离、旗通道行和对照。

从 tournament.jsonl 按 checkpoint × termination 分层确定性地抽样，逐局重放：
1) 对照 trace 验证动作序列复现；
2) 记录终局原因、step_count、no_capture；
3) 每步检查 obs 的敌方 belief 通道（28:52）：
   - 概率合法（每行 0 或 1，无负值）——不可能兵种严格归 0
   - 信息隔离：belief 峰值不得系统性精确指向敌方真实棋子位置（亮旗除外）
   - 观测编码：obs 中的 belief 必须等于 tracker.beliefs 按 ROTATE_K[seat] 旋转的结果
4) 包装 env.tracker.on_commander_dead，记录旗通道（第 11 通道）清零前后的行和。

坐标系约定：obs 已按当前座位旋转，tracker.beliefs 与 owner_board/piece_board
同为原始全局坐标。所有概率与泄漏检查均使用 tracker，避免坐标混用。

注意：trace_match 只证明可复现，不证明无作弊。
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOURN = ROOT / 'results' / 'tournament.jsonl'
AUDIT_OUT = ROOT / 'results' / 'replay_audit.json'
TERMINATION_CLASSES = ('decisive', 'step_limit_draw', 'no_capture_draw', 'other_draw')
DISCLAIMER = 'trace_match 只证明可复现，不证明无作弊'


def _same_path(a: Path, b: Path) -> bool:
    """同一路径判定（兼容 Windows 大小写差异与符号链接）。"""
    if a.exists() and b.exists():
        try:
            return a.samefile(b)
        except OSError:
            pass
    return str(a).lower() == str(b).lower()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='分层回放审计：输出 meta + reports 的 JSON 对象。')
    parser.add_argument('--data', type=Path, default=TOURN,
                        help=f'输入 tournament.jsonl（默认 {TOURN}）')
    parser.add_argument('--out', type=Path, required=True,
                        help='输出 JSON 路径；拒绝写入被 git 跟踪的 results/replay_audit.json')
    parser.add_argument('--per-class', type=int, default=4,
                        help='每个 checkpoint 每个 termination 类别的抽样局数（默认 4）')
    parser.add_argument('--per-ckpt', type=int, default=3,
                        help='抽查的 checkpoint 数（默认 3）')
    parser.add_argument('--sample-seed', type=int, default=20261126,
                        help='分层抽样随机种子（默认 20261126）')
    args = parser.parse_args(argv)
    if args.per_class < 0 or args.per_ckpt < 0:
        parser.error('--per-class 与 --per-ckpt 必须为非负整数')
    out = args.out.expanduser().resolve()
    if _same_path(out, AUDIT_OUT.resolve()):
        parser.error(
            f'拒绝写入被 git 跟踪的归档文件 {AUDIT_OUT}；请改用 --out 指向 results/derived/ 下的新文件')
    if _same_path(out, args.data.expanduser().resolve()):
        parser.error('拒绝把审计结果写入输入数据文件')
    return args, out


# 先解析参数：--help 不需要加载 torch / numpy / 模型实现
args, OUT = parse_args()

import numpy as np  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(ROOT))
import train_junqi_5070ti as T  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def ckpt_id(g: dict) -> str:
    """优先用评测器写入的绝对路径 checkpoint_id；旧产物回退到 basename。"""
    return g.get('checkpoint_id') or g['checkpoint']


def termination_class(g: dict) -> str:
    """把一局归入四个互斥终止类别；decisive = model_won 或 model_lost。"""
    term = g.get('termination')
    if term == 'decisive' or g.get('model_won') or g.get('model_lost'):
        return 'decisive'
    if term == 'step_limit_draw':
        return 'step_limit_draw'
    if term == 'no_capture_draw':
        return 'no_capture_draw'
    return 'other_draw'


def install_flag_channel_probe(env):
    """包装 tracker.on_commander_dead，记录每次调用前后第 11 通道行和。

    返回 (events, error)：成功时 events 为列表、error 为 None；
    签名/结构不符时返回 (None, 原因)，输出 meta 会写 not_implemented。
    """
    tracker = getattr(env, 'tracker', None)
    original = getattr(tracker, 'on_commander_dead', None)
    if not callable(original):
        return None, 'env.tracker.on_commander_dead 不存在或不可调用'
    try:
        sig = inspect.signature(original)
    except (TypeError, ValueError) as exc:
        return None, f'无法读取 on_commander_dead 签名: {exc}'
    required = [
        p for p in sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
        and p.default is inspect.Parameter.empty
    ]
    if len(required) != 2:
        return None, f'on_commander_dead 签名 {sig} 不是 (seat, true_flag_pos) 两个必填位置参数'
    beliefs = getattr(tracker, 'beliefs', None)
    if beliefs is None or getattr(beliefs, 'ndim', 0) != 4 or beliefs.shape[-1] <= 11:
        return None, (f'env.tracker.beliefs 形状 {getattr(beliefs, "shape", None)} '
                      '不符合 [seat, r, c, >=12]')

    events = []

    def wrapped(dead_seat, true_flag_pos):
        before = float(tracker.beliefs[dead_seat, :, :, 11].sum())
        result = original(dead_seat, true_flag_pos)
        after = float(tracker.beliefs[dead_seat, :, :, 11].sum())
        events.append({
            'seat': int(dead_seat),
            'before_rowsum': before,
            'after_rowsum': after,
        })
        return result

    try:
        tracker.on_commander_dead = wrapped
    except Exception as exc:
        return None, f'包装 on_commander_dead 失败: {type(exc).__name__}: {exc}'
    return events, None


data_path = args.data.expanduser().resolve()
rows = [json.loads(l) for l in data_path.open(encoding='utf-8')]
games = [r for r in rows if r['type'] == 'game']

# 分层抽样：每个 checkpoint 每类 --per-class 局；样本不足则全取并记 shortfall
rng = random.Random(args.sample_seed)
all_checkpoints = sorted(set(ckpt_id(g) for g in games))
selected_checkpoints = rng.sample(all_checkpoints,
                                  min(args.per_ckpt, len(all_checkpoints)))
selected_checkpoints.sort()
sample_counts = {ck: {cls: 0 for cls in TERMINATION_CLASSES}
                 for ck in selected_checkpoints}
shortfalls = {}
if len(selected_checkpoints) < args.per_ckpt:
    shortfalls['__checkpoints__'] = {
        'requested': args.per_ckpt,
        'sampled': len(selected_checkpoints),
        'shortfall': args.per_ckpt - len(selected_checkpoints),
        'reason': f'输入数据仅有 {len(all_checkpoints)} 个 checkpoint',
    }

selected = []
for ck in selected_checkpoints:
    for cls in TERMINATION_CLASSES:
        pool = [g for g in games
                if ckpt_id(g) == ck and termination_class(g) == cls]
        n = min(args.per_class, len(pool))
        picked = rng.sample(pool, n) if n else []
        sample_counts[ck][cls] = len(picked)
        if len(picked) < args.per_class:
            shortfalls.setdefault(ck, {})[cls] = {
                'requested': args.per_class,
                'sampled': len(picked),
                'shortfall': args.per_class - len(picked),
                'reason': ('该类别在输入数据中无可用局' if not pool else
                           f'该类别仅有 {len(pool)} 局，少于 --per-class={args.per_class} 配额'),
            }
        selected.extend(picked)

if not selected:
    raise SystemExit('没有可抽查的局（请检查 --data / --per-ckpt / --per-class）')
missing_trace = [g['seed'] for g in selected if 'trace' not in g]
if missing_trace:
    raise SystemExit(
        f'缺少 trace 字段的局数: {len(missing_trace)}（seed 示例: {missing_trace[:3]}）。'
        '请用 eval_tournament.py --replay 重新生成 tournament.jsonl。'
    )
print(f'抽查局数: {len(selected)}')
print(f'抽样种子: {args.sample_seed}; checkpoint 数: {len(selected_checkpoints)}; '
      f'shortfall 条目: {sum(len(v) if isinstance(v, dict) else 1 for v in shortfalls.values())}')


def load_model(path):
    m = T.JunqiActorCritic(hidden_dim=160, num_blocks=8).cuda().eval()
    m.load_state_dict(torch.load(ROOT / path, map_location='cuda', weights_only=True))
    return m


models = {}
for ck in set(ckpt_id(g) for g in selected):
    models[ck] = load_model(ck)
baseline = T.HeuristicBotWrapper().cuda().eval()

flag_probe_error = None
reports = []
for g in selected:
    seed = g['seed']
    random.seed(seed); np.random.seed(seed)
    env = T.JunqiSelfPlayEnv(max_steps=240); env.reset()
    flag_events, flag_error = install_flag_channel_probe(env)
    if flag_events is None and flag_probe_error is None:
        flag_probe_error = flag_error
    replay_trace = []
    belief_viol = 0
    belief_encoding_mismatch = 0
    belief_peak_exact = 0     # belief 峰值精确命中敌方真实棋子（非亮旗）次数
    belief_rows_checked = 0
    steps = 0
    while steps < 256:
        seat = env.current_seat
        obs = env.get_obs(seat)
        # ---- 暗棋信息隔离检查 ----
        # obs 的 belief 通道经 ROTATE_K[seat] 旋转；tracker.beliefs 与棋盘同为原始坐标。
        b = obs[28:52]  # [24,17,17]（已旋转）
        enemies = [(seat + 1) % 4, (seat + 3) % 4]
        k = T.ROTATE_K[seat]
        for ei, en in enumerate(enemies):
            tr = env.tracker.beliefs[en]  # [17,17,12] authoritative, 原始坐标
            sums = tr.sum(axis=2)
            nz = sums[sums > 1e-6]
            if np.any(np.abs(nz - 1.0) > 1e-3):
                belief_viol += 1
            belief_rows_checked += len(nz)

            # 观测编码一致性：obs 应等于 tr 的旋转结果
            expected = np.stack([np.rot90(tr[:, :, t], k=k) for t in range(12)], axis=0)
            if not np.allclose(expected, b[ei * 12:(ei + 1) * 12], atol=1e-6):
                belief_encoding_mismatch += 1

            for t in range(12):
                if t == 11:
                    continue  # 军旗亮旗是合法公开
                mask_pos = (env.owner_board == en) & (env.piece_board == t)
                if not mask_pos.any():
                    continue
                vals = tr[:, :, t][mask_pos]  # 原始坐标直接索引
                if np.any(vals > 0.999):
                    belief_peak_exact += 1
        # ---- 走子 ----
        obs_t = torch.from_numpy(obs).unsqueeze(0).cuda()
        mask_t = torch.from_numpy(env.get_action_mask(seat)).unsqueeze(0).cuda()
        with torch.no_grad():
            fn = models[ckpt_id(g)] if (g['model_team'] == 0 and seat % 2 == 0) or \
                                        (g['model_team'] == 1 and seat % 2 == 1) else baseline
            lg, _ = fn(obs_t, mask_t)
        a = int(lg.argmax(-1))
        _, done, info = env.step(a)
        replay_trace.append([seat, a])
        steps += 1
        if done:
            break
    match = replay_trace == g['trace']
    reports.append({
        'checkpoint': g['checkpoint'], 'checkpoint_id': ckpt_id(g),
        'seed': seed, 'model_team': g['model_team'],
        'winner': info.get('winner_team', -1), 'termination': g['termination'],
        'trace_match': match, 'replay_plies': len(replay_trace), 'recorded_plies': g['plies'],
        'belief_prob_violations': belief_viol,
        'belief_encoding_mismatches': belief_encoding_mismatch,
        'belief_exact_match_nonflag': belief_peak_exact,
        'belief_rows_checked': belief_rows_checked,
        'flag_channel_rowsum_events': flag_events if flag_events is not None else [],
    })

print('\n=== 回放抽查结果 ===')
for r in reports:
    print(f"  {r['checkpoint']:26s} seed={r['seed']} team={r['model_team']} "
          f"term={r['termination']:18s} trace_match={r['trace_match']} "
          f"plies={r['replay_plies']}/{r['recorded_plies']} "
          f"belief_viol={r['belief_prob_violations']} enc_mismatch={r['belief_encoding_mismatches']} "
          f"exact_nonflag={r['belief_exact_match_nonflag']}")

n_match = sum(1 for r in reports if r['trace_match'])
print(f'\ntrace 复现: {n_match}/{len(reports)}')
print(f'belief 概率违规局数: {sum(1 for r in reports if r["belief_prob_violations"]>0)}/{len(reports)}')
print(f'belief 观测编码不一致局数: {sum(1 for r in reports if r["belief_encoding_mismatches"]>0)}/{len(reports)}')
print(f'非亮旗 belief 精确命中敌方真实棋子的局数: '
      f'{sum(1 for r in reports if r["belief_exact_match_nonflag"]>0)}/{len(reports)}')
print(f'旗通道清零前后行和对照: '
      f'{"已记录" if flag_probe_error is None else "not_implemented: " + flag_probe_error}; '
      f'事件数={sum(len(r["flag_channel_rowsum_events"]) for r in reports)}')

meta = {
    'sample_seed': args.sample_seed,
    'per_class': args.per_class,
    'per_ckpt': args.per_ckpt,
    'sample_counts': sample_counts,
    'shortfalls': shortfalls,
    'input_file': str(data_path),
    'input_sha256': sha256_file(data_path),
    'disclaimer': DISCLAIMER,
    'selected_checkpoints': selected_checkpoints,
    'flag_channel_rowsum': {
        'implemented': flag_probe_error is None,
        'definition': ('每次 env.tracker.on_commander_dead(seat, true_flag_pos) 调用前/后'
                       ' env.tracker.beliefs[seat, :, :, 11].sum()'),
        'report_field': 'flag_channel_rowsum_events',
    },
}
if flag_probe_error is not None:
    meta['not_implemented'] = {'flag_channel_rowsum': flag_probe_error}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps({'meta': meta, 'reports': reports}, ensure_ascii=False, indent=2),
    encoding='utf-8')
try:
    shown = OUT.relative_to(ROOT)
except ValueError:
    shown = OUT
print(f'written: {shown}')
