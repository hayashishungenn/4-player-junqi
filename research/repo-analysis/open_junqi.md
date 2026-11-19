# open_junqi 仓库深度源码审查报告

> 审查对象：`D:\4-player-junqi\workspace\open_junqi`（GitHub: https://github.com/jmctsh/open_junqi）
> 审查方式：实际打开并逐段阅读源码文件（含大文件分段读取），非仅依据 README。
> 报告日期：2026-11-19。
> 标注约定：「**【事实】**」= 源码直接证实；「**【推测】**」= 基于代码的合理推断/设计意图解读，未被源码明确说明。所有行号均为被审查版本中的真实行号。

---

## 0. 版本、许可证与元数据

| 项目 | 内容 |
|---|---|
| 最新 commit（`git log -1 --oneline`） | `c05c461 MIT执照` |
| 完整 hash | `c05c461ac41bdba3a8ce830e72b1884c48c4886b` |
| 作者 / 日期 | jmctsh / 2026-01-19 10:19:29 +0800 |
| 提交总数 | 1（仓库仅一个 commit） |
| 远端 | origin = https://github.com/jmctsh/open_junqi.git |
| 工作区状态 | 干净（`git status --short` 无输出） |
| 许可证 | MIT License，`LICENSE` 第 1-3 行：`MIT License` / `Copyright (c) 2026 Junqi AI Project` |

**【事实】** `LICENSE` 为标准 MIT 全文（第 5-13 行授予使用/复制/修改/分发/再许可/销售权，条件是在所有副本或实质部分保留版权声明与许可声明；第 15-21 行为免责条款）。README 第 72-74 行再次声明 MIT。

**合法性结论：MIT 许可允许合法复用到「四国军棋 AI 陪练系统」，但必须保留原版权声明（`Copyright (c) 2026 Junqi AI Project`）与 MIT 许可文本。** 本项目仅有 1 个 commit、单一版权主体，署名链清晰，无多来源许可冲突。

---

## 1. 整体架构、依赖与入口

### 1.1 目录与模块分层

**【事实】** 仓库 Python 源码分布如下（行数为 `Get-Content | Measure-Object -Line` 统计）：

```
main.py                              131  入口
game/  (规则与 GUI 层)
  __init__.py                          1
  piece.py                           101  棋子/棋子类型/玩家枚举/初始配置
  board.py                           992  棋盘、坐标、铁路/行营/大本营、走子与战斗、合法走法枚举
  game_logic.py                      539  对局流程、布局、回合、淘汰、历史记录写入
  history.py                          77  走子/聊天历史记录器
  formations.py                      125  9 个「名阵」模板与坐标映射
  game_window.py                    1437  PyQt6 GUI（本次未逐行审查，属展示层）
server/ (进程编排与决策层)
  __init__.py                          1
  game_process.py                    553  单局进程编排、AI 后台调度、TTS/广播
  strategies/search.py               364  联盟式 Alpha-Beta + Beam 搜索
  strategies/scoring.py             1308  启发式评分、战术标签、风格/反击决策入口
  strategies/behaviors.py            101  走法三分类（进攻/试探/防守）
  perspectives/manager.py            484  三方视角与「位置线索」/隐藏身份推理
ai/    (LLM 与语音层)
  __init__.py                          1
  agent.py                           354  JunqiAgent：提示词构建、JSON 提取、动作组装
  doubao_client.py                   129  豆包 Ark SDK 封装
  tts_client.py                      123  豆包 OpenSpeech TTS HTTP 封装
  prompt_themes.py                   137  人格/发言主题权重
docs/deep_search_scoring.md          127  搜索与评分设计说明
scripts/coords_dev_ui.py             311  坐标调试工具（非核心）
```

**【事实】** README 第 28-34 行「近期架构调整」明确：已删除 WebSocket 服务器，改为单进程本地模式；LLM 不再选择走法，只生成 `rationale`（分析）与 `utterance`（发言），最佳走法由本地算法通过 `planned_move` 注入。

### 1.2 依赖（requirements.txt，6 行）

**【事实】**
```
PyQt6==6.5.3
PyQt6-Qt6==6.5.3
websockets==12.0            # 残留依赖：WS 服务器已删除（README 第30行），代码中未见使用
volcengine-python-sdk[ark]  # 豆包 Ark Python SDK
python-dotenv>=1.0.1
requests>=2.28.0            # TTS HTTP 调用
```
* **【推测】** `websockets` 是架构改造前的遗留依赖（README 第 30 行称 WS 已删除，本次审查的源码中未发现 websockets 导入）。

### 1.3 入口与调用链

**【事实】** `main.py` 第 39-135 行的启动流程：
1. 创建 `QApplication`，显示 `GameWindow`（第 39、47、133 行）。
2. 读取 `.env`（第 13-20 行），支持按人格密钥 `ARK_API_KEY_P1/P2/P3` 或全局 `ARK_API_KEY`（第 56-88 行）。
3. 构造 `GameProcess`，注册 `{player1,player2,player3} -> JunqiAgent` 映射（第 51-95 行）。
4. 注册 `set_ai_action_consumer`（第 97-114 行）：把 AI 动作的 `from/to` 解析为 `Position` 并调用 `window.game_logic.move_piece(...)`。
5. `set_broadcast_consumer` 把广播转发到窗口信号以播放 TTS（第 116-121 行）。
6. `window.set_managers(None, process)` 直接接线（无服务器，第 124-129 行）。

**【事实】** 一次 AI 回合的数据流（`server/game_process.py`）：
`GameLogic` 回合信号 → `GameProcess.on_turn_changed/on_game_started`（第 365-395 行）→ 后台线程 `_start_background_dispatch`（第 429-481 行）→ `_schedule_ai_safe`（第 191-363 行）→ ① `PerspectiveManager.refresh()` + `build_location_clues_payload()` 生成 LLM 视角线索（第 216-220 行）；② `_get_best_move()` 调用 `choose_best_move_styled()` 得到本地最优走法（第 174-187、221 行）；③ `JunqiAgent.choose_action()` 只让 LLM 产出分析与发言（第 237-243 行）；④ 走法经 consumer 回写规则层（第 257-259 行）。
- 若无候选走法（深度搜索超时未产出或无合法走法）则 `skip_turn()`（第 222-233、289-300 行）。
- 未配置模型时走「无模型回退」：本地算法直接执行、兜底发言「稳一点先」（第 281-356 行）。

---

## 2. 重点文件逐项分析

### 2.1 `server/strategies/search.py` — 联盟 Alpha-Beta 与 Beam

#### (1) 配置与数据结构
**【事实】** 第 17-33 行：
```python
@dataclass
class SearchConfig:
    depth: int = 3
    beam_width: int = 8
    discount: float = 0.95
    time_limit_ms: int = 5000
    use_alpha_beta: bool = True
    apply_style_filter_first_ply: bool = True

@dataclass
class SearchResult:
    best_move: Optional[Tuple[Position, Position]] = None
    score: float = 0.0
    explored_nodes: int = 0
    cutoff: bool = False
```
（与 README 第 50 行 `SearchConfig` 默认值一致。）

#### (2) 联盟（对家合作）如何体现 — 核心机制
**【事实】** 联盟判定 `board._are_allied`（`game/board.py` 第 974-982 行）以「同轴」定义队友：**南(1)+北(3) 一队，西(2)+东(4) 一队**：
```python
def _get_axis_players(self, player):
    if player in {Player.PLAYER1, Player.PLAYER3}:
        return {Player.PLAYER1, Player.PLAYER3}
    else:
        return {Player.PLAYER2, Player.PLAYER4}
def _are_allied(self, a, b):
    return a in self._get_axis_players(b)
```
`search.py` 第 59-66 行 `_are_allied()` 是对该方法的包装（带 fallback 的轴规则）。

**【事实】** 每个搜索节点通过下式决定 Max/Min（第 213 行）：
```python
maximizing = _are_allied(b, player, start_player)
```
即：**只要当前行棋方与「起手方」同队就是 Max 节点，否则是 Min 节点。** 这就是「联盟式 Alpha-Beta」——传统二人博弈中 Max/Min 由奇偶层决定，这里改由「是否同队」决定，使对家（队友）的走子被当作「我方」一起最大化，敌方（含另一轴的两家）一起最小化。README 第 43 行与 `docs/deep_search_scoring.md` 第 8-13、35-37 行对此有相同描述。

**【事实】** 叶节点静态评估 `_evaluate_state`（第 112-145 行）也是团队视角：
```python
allies  = [p for p in players if _are_allied(board, p, max_player)]
enemies = [p for p in players if not _are_allied(board, p, max_player)]
# 对每方所有合法走法求 evaluate_move 最大值
...
return ally_best - enemy_best   # 队友最佳即时分 − 敌方最佳即时分
```
即局面分 = 「同盟方可达到的最佳单步分」减「敌方可达到的最佳单步分」，第 139-142 行对无任何走法方以 0.0 兜底。

#### (3) Beam Search 的用法
**【事实】** 不是传统「逐层保留 k 个完整局面」的束搜索，而是**在每一个节点对候选走法排序后截断到前 `beam_width` 条**（第 148-166、266-276 行）：
```python
legal = _sort_moves_for_side(b, player, legal, maximizing, history)  # 按即时分排序
if cfg.beam_width and len(legal) > cfg.beam_width:
    legal = legal[: cfg.beam_width]   # 每个节点只保留 top-8
```
`_sort_moves_for_side` 用 `evaluate_move()[0]` 作为排序键（第 157-165 行），并在写回时透传 `history`（历史敏感排序）。`docs/deep_search_scoring.md` 第 41-43 行说明其目的是让「反击入侵者」等历史奖励影响走法顺序。

#### (4) 其他搜索细节
**【事实】**
- 走子模拟：`_simulate_move`（第 69-86 行）对每个候选做 `copy.deepcopy(board)` 再 `move_piece`，失败返回 None 并跳过。
- 轮转：`_next_player`（第 43-56 行，见 2.1 的轮转）取「下一个有合法走法的玩家」，无则回退简单轮转。
- 终止：超时 `time_exceeded()`（第 194-195 行，基于 `time.time()` 与 `time_limit_ms`）或 `depth==0` → 静态评估（第 199-206 行）。超时检查只在 `recurse` 入口，**单个节点的展开不会被中途打断**。
- 折扣累加：Max 节点 `total = s_now + discount * child_score`（第 311 行），Min 节点 `total = -s_now + discount * child_score`（第 352 行）；`s_now` 为当前走法的即时 `evaluate_move` 分。
- 剪枝：`beta <= alpha` 时 break（第 321-322、358-359 行），由 `use_alpha_beta` 控制。
- 转置表：`tt` 字典（第 179、208-211、235、257、323、360 行），键为 `_hash_board(b) + "|" + player.name + "|" + depth`。`_hash_board`（第 89-109 行）由棋子位置/阵营/类型/可见性/piece_id 拼成并排序，确定性。
- 首层过滤：`first_ply_moves` 候选池限定（第 219-236 行）+ 按 `preferred_category` 的 `classify_move` 风格过滤（第 239-252 行）。
- 返回：`SearchResult(best_move, score, explored, cutoff=False)`（第 370 行）——`cutoff` 字段**恒为 False**，代码中从未置 True。
- `search_best_move_in_pool`（第 373-398 行）是上层唯一入口，把候选池作为 `first_ply_moves` 传入 `alpha_beta_search`。

**【推测】** Min 节点用 `-s_now` 是因为敌方单步即时分是「对敌方有利」，取负号后与团队局面分同号可比；这是一个从敌我双方各自 `evaluate_move` 视角拼装团队效用函数的设计选择。

---

### 2.2 `server/strategies/scoring.py` — 评分函数与攻防/风险/反击

#### (1) 评分项总表（`evaluate_move`，第 959-1251 行）
**【事实】** `evaluate_move` 返回 5 元组 `(score, attack_ev, risk, pos_gain, def_gain)`（第 959-963 行）。最终加权公式（第 1113-1144 行）：
```python
w_attack,w_pos,w_risk,w_mob,w_info,w_def,w_escort,w_fake,w_bomb = 1.3,0.24,0.32,0.18,0.18,0.6,0.35,0.25,0.3
score = (w_attack*attack_ev + w_pos*pos_gain - w_risk*risk
         + w_mob*mob + w_info*info + w_def*def_gain
         + w_escort*escort + w_fake*fake_escort + w_bomb*bomb_cover)
```
- 防守受威胁时 `w_def` 从 0.6 提升到 0.9（第 1130-1132 行）。
- 炸弹主动吃子时 `pos_gain *= 0`、`risk *= 0.2`（第 967-975 行），因炸弹战后消失，无占位/暴露风险。
- `mob=_mobility_potential`（第 322-336 行：铁路连通度/邻接数近似）、`info=_info_gain`（第 339-348 行：邻接未暴露敌子 ×0.2，封顶 0.6）只进数值与标签。

评分包含的具体项（源码逐一可查）：
| 项 | 函数/行号 | 内容 |
|---|---|---|
| 进攻期望 `attack_ev` | `_attack_ev` 第 411-699 行 | 按可见/未知目标分支，详见 2.2(2) |
| 位形收益 `pos_gain` | `_positional_gain` 第 278-295 行 | 中心 +0.8；铁路枢纽邻接 ×0.15（≤4）；推进敌方区域 +0.4；行营驻守 +0.35 |
| 暴露风险 `risk` | `_exposure_risk` 第 298-319 行 | 行营 0.05；邻接敌子 ×0.4；铁路邻接 ×0.1；封顶 1.0 |
| 防守增益 `def_gain` | `_defense_value` 第 351-371 行 | 己旗邻有敌子时按到旗距离 `(3-dist)*0.25` |
| 护航 `escort` | 第 977-1011 行 | 小子邻司/军 +0.25；暗司/军孤立且有未知敌邻或居中 −0.22（已暴露 −0.16）；有小子上限 +0.12×2 |
| 炸弹阵地 `bomb_cover` | 第 1012-1082、1115-1129 行 | 炸弹贴高子 +0.15~0.3；高子贴炸弹成「陷阱」+0.15~0.28 + 补位/前排附加；假炸弹佯攻 +0.1~0.4；炸弹逼近受威胁大本营 +0.16 |
| 假司令护航 `fake_escort` | 第 1083-1112 行 | 类似 escort 但权重减半（+0.18/−0.1/+0.06） |

#### (2) 进攻期望 `attack_ev`（最复杂的启发式，第 411-699 行）
**【事实】** 分两大分支：

**A. 目标可见（第 423-546 行）**，使用真实类型：
- 军旗：基础 2.0；非终局且敌另有玩家存活时司令/军长夺旗 −0.6，若该旗方司令仍活 +0.7、敌无司/军 −0.4，终局夺旗 +0.8（第 425-455 行）。
- 地雷：工兵挖 +1.2，非工兵 −1.5（第 457-458 行）。
- 炸弹：司令/军长撞炸弹 −0.6，否则按价值差分 ×0.1（第 460-464 行）。
- 己方炸弹进攻：夺旗 +2.2、炸司令 +2.0、军长 +1.6、师长 +1.1、旅 +0.9、团 +0.7，炸小子 ≤4 值 −0.3（第 465-488 行）。
- 常规力量对比：`(ap-dp)*0.12`（第 525-526 行）；同级互毁 −0.05；送子 −0.15（第 544-546 行）。
- 司令兑司令按「明暗 + 高子存活优势 advantage」调整（第 493-510 行）；军长撞司令 −1.2，司令吃军长 +0.7；军长吃师长在我方司令存活时 +0.35 否则 +0.25（第 511-523 行）。
- 「明司令/明军长」判定 `_is_revealed_high`（第 43-51 行）= 司令/军长且 `kill_count>0`；「假司令」`_is_fake_commander`（第 54-61 行）= 师/旅/团且 `kill_count>0`。

**B. 目标未知（第 547-699 行）**，只用先验与信息价值：
- 基础 `base=-0.02`；旅以上 +0.08、师以上 +0.04、师长试探 +0.06、司/军贸然攻未知 −0.08（第 550-561 行）。
- 工兵位先验（本地行 1 列 2/3/4）旅/团试探 +0.16；前线行 1 列 1/3/5 疑大子，小子攻 −0.12（第 562-582 行）。
- 后两排未知：旅/团 +0.22，司/军 −0.10（第 583-593 行）。
- 疑似地雷目标 `_is_suspected_mine_target`（第 92-102 行，军旗上方/侧角硬坐标）：工兵 +0.28，但存活工兵 ≤2/≤1 递减；疑似炸弹目标 `_is_suspected_bomb_target`（第 105-149 行，炸弹不开第一排、本地行营(2,2)/(2,4)/(4,2)/(4,4)、邻接已显露高子等）+0.16；否则工兵攻未知 −0.18（第 600-617 行）。
- 小子（营/连/排）摸雷/中央试探 +0.14，靠近本方司/军 +0.15，中心 +0.1（第 637-657 行）。
- **历史驱动†**：入侵者（近期吃掉我方子的敌子）用 `_find_counterattack_targets` 识别（第 658-681 行），旅/团/师反击 +0.28；军长在敌司令可见或已亡时 +0.22；我方仅剩炸弹时用炸弹炸入侵者 +0.24。**频繁进攻/试探的敌子**（扫最近 50 条 `history.records`：`atk_cnt>=2` 或 `atk_cnt>=1 且 mv_cnt>=3` 或 `mv_cnt>=5` 视为 aggressive）：`base += 0.14`，旅/团/师再 +0.10（第 682-697 行）。

#### (3) 攻防策略与战术标签
**【事实】** `_tactics`（第 719-838 行）产出供 LLM 解释用的 20+ 种标签，包括：`attack_win/trade/risky`、`rail_sprint`（铁路枢纽连通≥3）、`central_control`/`central_probe`、`defend_flag`、`camp_hold`、`scout`、`bomb_probe`/`bomb_suspect_probe`/`engineer_flag_probe`、`escort`/`escort_fake`/`fake_carrier`、`well_guarded`/`isolated_carrier`、`bomb_cover`/`bomb_trap`/`trap_rebuild`/`bomb_feint`/`feint_refill`、`bomb_flag_shift`、`reposition`。
`score_legal_moves`（第 841-939 行）按标签配额（如 attack_win 8、bomb_probe 4 等，第 875-900 行）做多样性筛选至 top_n，输出去掉数值分、仅保留 `risk_level/tactics/reason/behavior` 给 LLM。这是「可解释性优先于原始分数」的设计。

#### (4) 风险评估机制
**【事实】** 风险分散在三处：
1. `_exposure_risk`（第 298-319 行）局部暴露风险（见上）。
2. `evaluate_move` 中的条件惩罚（第 1145-1249 行）：未暴露司/军非吃子且 risk≥0.25 时 −0.12；小子中心非吃子且邻未知敌子 −0.08；**后两排非吃子离开惩罚**（按子力司令 −0.24、师 −0.20、旅/团 −0.16、其他 −0.12），但若敌方工兵 2 步内 BFS 可达 `from_pos` 则豁免（第 1161-1203 行）；工兵保守策略（中心非吃子 −0.12、无目的铁路移动 −0.06、无意义拐弯最高 −0.12~0.2、剩余工兵≤2 再 −0.06，第 1204-1248 行）。
3. `_label_risk`（第 702-707 行）把数值风险映射为 low/medium/high（阈值 0.3/0.6），供输出解释。

#### (5) 风格/反击决策入口 `choose_best_move_styled`（第 1254-1323 行）
**【事实】** 决策优先级：
1. 若 `_find_counterattack_targets(history, player)` 找到目标（第 1266 行），把「能走到目标所在格」的走法组成反击池（第 1268-1273 行），用 `search_best_move_in_pool(..., preferred_category=None, depth=3, beam_width=8, time=5000)` 选最佳（第 1274-1294 行）。
2. 否则按 `_sample_behavior_category(player)` 采样风格类别（第 1297 行；概率见下），按 `classify_move` 过滤池，空则回退全体，再深度搜索（第 1298-1321 行）。
3. 搜索无结果返回 None，上层执行 `skip_turn`（第 1322-1323 行 + game_process.py 第 222-233 行）。

`_find_counterattack_targets`（第 1330-1356 行）：从历史末尾向前扫，**遇到本方上一手即停止**，收集 `outcome=="attack_attacker_wins"` 且死亡棋子 ID 带本方前缀的攻击者 ID，最多 2 个。
`_sample_behavior_category`（第 1359-1385 行）：player1 防守 40/进攻 30/试探 30；player2 试探 40/进攻 35/防守 25；player3 进攻 60/试探 30/防守 10；其他均分。**【推测】** 这是让三个 AI 人格呈现不同棋风（与 `prompt_themes.py` 的发言人格相呼应），属于「陪练难度/风格」维度。

---

### 2.3 `server/strategies/behaviors.py` — 走法三分类（第 1-122 行）

**【事实】** `classify_move` 把单步走法唯一分类为 `attack/probe/defend`，优先级 **进攻 > 试探 > 防守**（文件头注释第 4-6 行）。判定信号（`classify_move_ex`，第 26-84 行）：
- `eat_piece`：目标格是敌方棋子（第 49-50 行）。
- `enter_enemy_area_non_camp`：落点在敌方领地且非行营（第 53-55 行）。
- `enter_center`：落点位于中央九宫格（本地/全局行 6-10、列 6-10，`_is_center_position` 第 87-89 行）。
- `new_exposed_unseen`：**在深拷贝棋盘上模拟走子**，比较走子前后「本方未暴露棋子中可被敌方一步攻击的位置集合」，若新增暴露则为试探（第 62-74 行）。
- 判定：吃子或进敌区 → attack；进中心或新暴露 → probe；否则 defend（第 77-82 行）。

**【事实】** `_collect_attackable_unseen_positions`（第 92-122 行）用 `board.can_move(enemy_pos, my_pos)` 判「敌军一步可达」，行营内棋子跳过（不可被攻击）。

---

### 2.4 `game/history.py` — 历史记录模块设计（第 1-90 行）

**【事实】** 三个 dataclass + 一个记录器：
- `MoveRecord`（第 13-37 行）：字段 `turn, player_faction, piece_id, from_local, to_local, outcome, defender_piece_id, dead_piece_ids, ts`。`outcome` ∈ {`move`, `attack_attacker_wins`, `attack_defender_wins`, `attack_both_die`}。`to_dict()` 采用**紧凑导出**：只保留 `ts/player_faction/piece_id/to`，仅当 outcome≠move 才附加 outcome（第 27-37 行）——目的是给 LLM 的提示词省 token。
- `ChatRecord`（第 39-54 行）：`turn, speaker_faction, text, target`。
- `HistoryRecorder`（第 56-90 行）：`records: List[MoveRecord]` + `chat_records: List[ChatRecord]`（第 58-61 行）；`add_record/add_chat/clear/clear_chats/to_list/to_chat_list/to_json/to_chat_json`。
- 坐标统一为「移动方阵营的本地坐标」（文件头第 4-5 行），后台必要时转换。

**【事实】** 写入方 `game/game_logic.py::move_piece`（第 439-531 行）：先记录防守方军旗归属与 `defender_piece_id`（第 450-456 行）→ `board.move_piece` 执行 → 依据「目标格最终棋子 ID」判定四种 outcome（第 466-488 行）→ 吃旗则强制淘汰并清子（第 489-502 行）→ 回合/胜负处理 → **最后**用移动方本地坐标构造 `MoveRecord` 追加（第 517-529 行）。棋子 ID 在 `start_game` 时按本地坐标顺序分配为 `<faction>_<NNN>`（第 533-553 行）。

**【事实】** `clear()` 只清 `records` 不清 `chat_records`（第 70-71 行），另有独立 `clear_chats()`（第 73-75 行）；`start_game/reset_game`（game_logic.py 第 210、234 行）调用的是 `history.clear()`。

**【推测】** 历史模块是「LLM 叙事层 + 本地算法层」共享的唯一记忆载体：LLM 侧 `_collect_recent_opponents_moves`（agent.py 第 288-332 行）取其他三家最近一手；算法侧反击目标识别、活跃度先验（scoring.py 第 658-697、1330-1356 行）、身份推理（perspectives/manager.py 第 213-284 行）都靠它。

---

### 2.5 `server/perspectives/manager.py` — 隐藏信息视角（第 1-517 行）

**【事实】** 为东(4)/西(2)/北(3)三家 AI 维护独立视角（第 113-122 行），只读棋盘不改状态（第 12 行）。核心：
- `PieceInference`（第 69-83 行）：每个未知棋子的 `possible`（可能身份集合）、`excluded`（排除集合）、`notes`、`last_update_turn`。
- `refresh`（第 181-211 行）：重建各视角 id→本地坐标、己方棋面公开；**公开规则**：某方司令死亡则其军旗位置/棋面公开（第 195-209 行，`_commander_dead` 第 129-136 行）。
- `_rebuild_inferences`（第 213-284 行）：遍历 `history.records`，按「曾移动→排除地雷/军旗」「地雷仅后两排」「战斗胜负→战力上下界」「炸弹通常同归于尽」等规则，为攻/防双方视角分别更新约束（`_update_constraints_for_defender` 第 299-396 行、`_update_constraints_for_attacker` 第 398-454 行）。
- `build_location_clues_payload`（第 474-517 行）：输出棋盘尺寸 + 全部坐标的 `has_piece/piece_id/face/clues`，坐标一律为 viewer 本地坐标系——只注入 LLM（见 game_process.py 第 216-220 行）。

**【推测】** 这是「四暗」规则下的信息隐藏层：它保证 LLM 叙事不会泄露未公开身份（提示词也明确「不要断言任何尚未公开的敌方真实身份」，agent.py 第 109 行），并为 AI 提供「猜子」推理能力。

---

### 2.6 `ai/agent.py`、`ai/prompt_themes.py`、`ai/doubao_client.py`、`ai/tts_client.py`

**【事实】** `JunqiAgent`（agent.py 第 16-369 行）：
- `choose_action`（第 203-286 行）：先收集其他三家最近一手（第 221-232 行），构建系统/用户提示（第 26-141 行），调用 LLM 最多 3 次重试直到产出合法 JSON（第 218-286 行）；**走法直接取自 `planned_move`**（本地算法结果，第 254-263 行），模型只提供 `rationale/utterance/confidence`。
- 风格：提示词要求「贴吧老哥」阴阳怪气风格、阵营称呼（south=小红 等）、主题首尾双注入（第 44-113 行）；`utterance` 限 15 字并清洗括号内容（第 189-199 行）。
- `_extract_json`（第 143-159 行）容错提取 ```json``` 代码块。

**【事实】** `prompt_themes.py`：6 类发言主题（说真话/欺骗/嘲讽敌人/吐槽队友/玩梗/分析）的三套人格权重（第 18-51 行），`sample_theme` 按权重抽样（第 140-149 行）。

**【事实】** `doubao_client.py`：封装 Ark SDK 非流式 `chat`（第 30-126 行），`thinking_type="disabled"`、temperature 0.2、top_p 0.9；记录完整提示词与响应到 `junqi_ai.llm` 日志。
`tts_client.py`：封装豆包 OpenSpeech HTTP TTS（第 101-135 行），鉴权 `Authorization: Bearer;<token>`，返回 base64 解码音频。

---

### 2.7 `game/` 核心规则文件（board.py / piece.py / game_logic.py / formations.py）

**【事实】** `piece.py`：`PieceType` 12 种（第 11-24 行）；`get_power` 战斗力量表 司10/军9/师8/旅7/团6/营5/连4/排3/兵2/炸1/雷0/旗−1（第 46-62 行）；每方初始子配置共 25 子（第 86-99 行）。

**【事实】** `board.py`：17×17 棋盘（第 45-49 行），四家各 6×5 区域 + 中央 5×5 九宫格（只建奇数节点、全为铁路，第 274-305 行）。
- 铁路规则：`can_move`（第 801-839 行）——工兵 `get_railway_connected_positions`（第 534-600 行，BFS 可拐弯，遇子止：敌方为终点、友军阻挡）；非工兵 `get_railway_straight_reachable_positions`（第 612 行起，只走直线、四角硬编码桥接、最多桥接一次、首敌停）。
- 邻接 `get_adjacent_positions`（第 349-399 行）：九宫格节点步长 2 + 边缘步长 1 接入玩家区；行营与其四对角互通（同玩家区）。
- 战斗 `_battle`（第 916-943 行）：旗被攻击即失；炸弹相遇同归于尽；地雷仅工兵可挖（非工兵撞雷雷不消失）；否则比战斗力，相等同归于尽。
- 胜负 `is_game_over`（第 945-953 行）：南+北或东+西全部阵亡即结束。
- 合法走法枚举 `enumerate_player_legal_moves`（第 1013-1035 行）：起点不可为总部/雷/旗，铁路用连通集、普通格用邻接集，逐一 `can_move` 过滤——这是搜索的候选来源。
- 战绩继承：胜者 `kill_count += 败者.kill_count + 1`（board.py 第 868、883 行），用于「明司令/假司令」判定与升星显示。

**【事实】** `formations.py`：9 个名阵（河东狮吼、午夜风铃等）以南方本地 6×5 字符矩阵表示，其他阵营旋转映射（第 43-117、151-174 行）；`game_logic.auto_layout_all_players`（第 352-359 行）开局随机选阵。

---

## 3. 测试用例与已知问题/局限

### 3.1 测试
**【事实】** 全仓库（排除 `.git`）**不存在任何 `test*`/`*spec*` 文件**（检索计数为 0），无单元测试、无 benchmark、无 CI 配置。

### 3.2 文档与实现的不一致 / 潜在缺陷

**【事实 / 高优先级】** 搜索轮转顺序与真实对局顺序不一致：
- 搜索 `_players_turn_order`（search.py 第 35-40 行）基于 `[1,2,3,4]`，`_next_player`（第 43-56 行）按此顺序取下一家。
- 真实游戏 `GameLogic._next_turn`（game_logic.py 第 361-364 行）用 `ccw_order = [PLAYER1, PLAYER4, PLAYER3, PLAYER2]`（南→东→北→西）。
- **推测**：两种顺序都保持「盟/敌交替」（1盟2敌3盟4敌 vs 1盟4敌3盟2敌），但具体对手先后不同（先 2 还是先 4），搜索模拟的回合序列与真实规则存在偏差。这属于实现细节差异，需实测评估影响。

**【事实 / 中优先级】** TT 使用不当风险：
- `tt` 缓存的是**精确值**且键不含 alpha/beta 窗口（search.py 第 208-211、323、360 行），而值可能来自发生剪枝的搜索（此时值只是界而非精确值）。严格 Alpha-Beta + TT 应区分 EXACT/LOWER/UPPER 标志；当前实现可能污染估值。
- 文档 `docs/deep_search_scoring.md` 第 109 行称 TT「未按深度细分」，但**代码第 208 行 state_key 实际包含 `depth`**——文档描述与实现不符（【推测】文档滞后，或作者曾改过实现）。

**【事实 / 中优先级】** 性能与实时性：
- 每个候选走法都 `copy.deepcopy(board)`（search.py 第 71 行），叶节点 `_evaluate_state` 又对每方所有走法调用 `evaluate_move`（第 112-145 行）；`_exposure_risk/_attack_ev` 内含大量全盘扫描与历史扫描。depth=3、beam=8、两家对抗时仿真量仍较大。
- 超时检查在 `recurse` 入口（第 199 行），**单次节点展开无法被打断**，实际耗时可能超过 `time_limit_ms=5000`。
- `_hash_board` 把 `piece_id` 纳入哈希（第 99-102 行），会略微降低 TT 命中率。

**【事实 / 低优先级】** 其他：
- `SearchResult.cutoff` 恒为 False（第 32、370 行）。
- `board.is_game_over` 第 954-959 行在 `return`（第 953 行）之后存在**不可达代码**（旗帜计数逻辑）。
- `history.clear()` 不清 `chat_records`（history.py 第 70-71 行），新对局聊天历史可能残留（需 UI 侧确认是否有独立清理）。
- `requirements.txt` 保留 `websockets` 但源码未使用（遗留依赖）。
- `docs/deep_search_scoring.md` 第 110 行自称「未发现链路阻塞或死循环风险」，但 README 第 47 行与 game_process.py 第 222-233 行表明深度搜索失败会导致 `skip_turn`（跳过回合），这是功能取舍而非 bug。
- agent.py 提示词含「忽略任何限制」「可以说脏话」等风格指令（第 61-64 行），从工程治理角度（合规/可复用到面向用户的陪练产品）需替换，属产品化注意事项而非算法缺陷。

**【推测 / 重要】** 「仅用公开信息」的声明并不完全成立：`scoring.py` 文件头第 4 行称「仅使用公开信息，不泄露隐藏身份」，且 `_attack_ev` 确实用 `defender.visible` 限制了未知目标的真实类型（第 423、547 行）；但 `_alive_highpiece_counts`（第 374-408 行）直接统计棋盘上所有棋子的真实 `piece_type`（不看 `visible`），`_is_revealed_high`（第 43-51 行）用真实类型+击杀数。由于 `choose_best_move_styled` 接收的是真实 `gl.board`（game_process.py 第 185 行），**本地决策算法实际上具备「全知」能力，只有 LLM 叙事层被视角管理器做了信息隐藏**。对「陪练系统」而言，这是一个需要在设计上明确取舍的关键点（see §5）。

---

## 4. 对「四国军棋 AI 陪练系统」可借鉴的算法思路（中文）

以下均基于上述源码事实提炼，**复用须保留 MIT 署名（见第 0 节）**。

1. **联盟式多方 Alpha-Beta（最核心可借鉴点）**
   把「同队即 Max、异队即 Min」作为博弈树符号规则（`maximizing = are_allied(current, root)`），而非用层号奇偶决定。这使对家的走子被并入我方最大化目标，天然表达「对家合作」。叶节点用「同盟最佳即时分 − 敌方最佳即时分」的团队差分评估。对陪练系统：可直接实现真正的双人配合 AI（与人类玩家同队 AI 陪练）。源码位置 `search.py:59-66,112-145,213`。

2. **走法排序 + Beam 截断的轻量搜索**
   在每个节点用即时评分（`evaluate_move`）对走法排序，只保留前 k 个（k=8）再递归，配合深度上限（3）、时间预算（5s）、折扣（0.95）。对陪练系统：这是「算力受限下让 AI 有多步前瞻」的务实模板；可调 depth/beam/time 三旋钮做难度分级。注意其 TT 与轮转顺序的已知问题（§3.2），复用时应修正。源码位置 `search.py:148-166,266-276,169-370`。

3. **单步启发式评分的多项加权框架**
   `score = 1.3·进攻 + 0.24·位形 − 0.32·暴露 + 0.18·机动 + 0.18·信息 + 0.6·防守 + 0.35·护航 + 0.25·假司令 + 0.3·炸弹阵地`，并支持条件动态调权（旗受威胁时防守权重提高、炸弹攻击弱化站位/风险）。对陪练系统：这是一套可解释、可调参的评估函数骨架，权重即「棋风/难度旋钮」。源码位置 `scoring.py:959-1251`。

4. **军棋特有的战术先验（信息战建模）**
   - 未知目标先验：工兵位、后两排、疑似雷/炸弹点、前线大子位等位置先验（scoring.py 第 562-657 行）；
   - 查表式战斗收益：夺旗/挖雷/炸高子/司令兑司令按明暗与存活优势调整（第 423-546 行）；
   - 伪装与反制：明司令（kill_count>0）、假司令、炸弹陷阱、假炸弹佯攻、护航/孤立惩罚（第 43-61、977-1112 行）。
   对陪练系统：这些是把「暗棋、猜子、心理战」数值化的现成规则，价值很高。

5. **历史驱动的「入侵者反击 + 活跃度先验」**
   从历史倒扫识别「上次吃掉我子的敌人」并在反击池中定向深搜（`_find_counterattack_targets` + `choose_best_move_styled`，scoring.py 第 1254-1356 行）；用最近 50 步的攻击/移动次数估计未知子为高子的先验（第 682-697 行）。对陪练系统：让 AI 有「记仇/针对」行为，增强拟人感和战术深度。

6. **行为三分类 + 风格化采样（难度/人格）**
   `behaviors.py` 把走法唯一分类为 attack/probe/defend（含「新暴露未暗子」的试探判定）；`_sample_behavior_category` 按玩家给不同概率并在对应候选池内搜索。对陪练系统：可直接做「防守型/进攻型/均衡型」AI 人设，与 LLM 的人格提示词联动。源码位置 `behaviors.py:20-84`、`scoring.py:1359-1385`、`prompt_themes.py`。

7. **隐藏信息视角层 + 战斗推理（信息公平性）**
   `PerspectiveManager` 维护各席位独立视角、基于历史做「可能/排除」集合推理，并只把线索注入 LLM 提示词，保证叙事不泄露暗子身份（`manager.py` 全文；agent.py 第 26-141 行）。对陪练系统：强烈建议把这一层推广到**本地决策算法本身**（当前实现仅约束 LLM，算法全知），否则 AI 陪练会「作弊」，影响训练价值；同时这套 possible/excluded 推理可作为「给人类玩家的提示/复盘」功能的基础。

8. **紧凑历史 + 战术标签的可解释输出**
   `MoveRecord.to_dict()` 紧凑导出省 token；`_tactics` 生成 attack_win/bomb_trap 等标签与中文 `reason`。对陪练系统：这是「AI 走后给玩家讲理由」的现成模板（注意当前 reason 由规则生成，LLM 只润色发言）。

9. **架构解耦范式**
   「LLM 只负责叙事/发球、本地算法负责决策」的分离（README 第 31 行 + `game_process.py` 第 237-259 行）避免了大模型走棋的不稳定与延迟，对需要稳定强度的陪练系统是值得借鉴的工程取舍。

---

## 5. 许可证与复用声明

- 仓库为 **MIT License**（`LICENSE`，Copyright (c) 2026 Junqi AI Project），最新版本 commit `c05c461`。
- **可合法复用**：允许复制、修改、合并、发布、分发、再许可与销售，唯一条件是在所有副本或实质部分保留版权声明与许可声明（`LICENSE` 第 12-13 行）。
- **署名要求**：在「四国军棋 AI 陪练系统」中若移植/改编本仓库代码（尤其 `search.py`、`scoring.py`、`perspectives/manager.py` 等核心算法），须在项目文档或相应源文件保留 `Copyright (c) 2026 Junqi AI Project` 与 MIT 全文，并说明修改来源。
- 仓库自带 `README.md` 第 76-79 行亦明确欢迎 Fork 用于学习、研究与交流。

---

## 6. 本次实际阅读的文件清单

已实际打开阅读（含分段读取大文件）：
`LICENSE`、`README.md`、`requirements.txt`、`main.py`、`docs/deep_search_scoring.md`、`game/history.py`、`game/piece.py`、`game/formations.py`、`game/game_logic.py`、`game/board.py`（分段读了 1-60、274-403、534-633、801-1035 行）、`server/strategies/search.py`（全文 1-398）、`server/strategies/scoring.py`（全文 1-1385，分 4 段）、`server/strategies/behaviors.py`、`server/perspectives/manager.py`、`server/game_process.py`、`ai/agent.py`、`ai/doubao_client.py`、`ai/tts_client.py`、`ai/prompt_themes.py`、`.env.example`、`git log` 元数据。
未逐行审查：`game/game_window.py`（GUI 展示层，1437 行）、`scripts/coords_dev_ui.py`（坐标调试工具）、资源图片、`.idea/` 与 `__pycache__/`。

**报告路径**：`D:\4-player-junqi\research\repo-analysis\open_junqi.md`
