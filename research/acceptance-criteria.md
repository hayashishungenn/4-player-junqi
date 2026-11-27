# 正式验收口径（归档）

用户 2026-11-26 确认，65% 主口径 = W/N（含和局）。

- 归档日期：2026-11-26；归属任务：P0-01；依据 `research/next-phase-task-book.md` §1（口径与术语）、§4（用户决策）、§5（可追溯性规范）。
- 本文件是**判定契约**，不是结果报告；任何状态改为"通过"必须附产物路径与 sha256。
- 依据文件 sha256：`research/next-phase-task-book.md` = `a49fa84b235eb96079e80425cec555301d112d5095ec7d4f7241c2ea8e39440b`（P0 状态回填前的冻结基准版本；回填后版本见任务书附录 D）；`research/p0-baseline.md` = `0de254dfc80f0046af4b00e8ca747230b1af6afd1a7236a002f568dcd7bd612c`。
- 本次只冻结口径文字：不改脚本阈值、不改历史数据、不启动训练。

## 1. 两种胜率公式与分母要求

### 1.1 主口径（唯一 65% 验收线）

- 公式：`W/N`。W = 模型胜局数；N = 总局数（胜 + 负 + 三类和局，即 decisive / step_limit_draw / no_capture_draw 的全部）。
- 判定：`W/N >= 0.65` 才叫达到 65%；不得用任何排除和局的数字替代。
- 当前实测（`results/summary.json`、`results/tournament.jsonl:1-301`）：
  - `junqi_best_iter240.pt`：20/100 = 20.0%（80 和局，decisive/step_limit/no_capture = 20/73/7）。
  - `junqi_pool20_iter248.pt`：22/100 = 22.0%（77 和局，23/70/7）。
  - `junqi_iter688.pt`：25/100 = 25.0%（73 和局，27/72/1）。
- 最优 Wilson 95% 上界 34.3%，当前主口径距离 65% 很远；P0-01 已归档，按本契约当前判定为**未达标**，后续新产物须重新判定。

### 1.2 辅助口径（仅诊断）

- 公式：`W/(W+L)`。每次报告**必须同时写出 W+L 与 N**（例如"25/27，W+L=27，N=100"），不得只写百分比。
- 当前值：20/20（W+L=20，N=100）、22/23（W+L=23，N=100）、25/27（W+L=27，N=100）。
- `junqi_iter688.pt` 的 92.6% = 25/27，分母仅 27 局；**不得据此宣布达标**。它在主口径下仍是 25/100 = 25.0%。

### 1.3 20/100 与 20/20 的差别（必须写清）

- 20/100：100 局里赢 20 局，含和局主口径，分母 N=100；这是验收用数。
- 20/20：只在 20 局有胜负的 decisive 局里赢 20 局，分母 W+L=20；这是条件化诊断数。
- 二者描述的是同一批棋的不同子集，数值 100% 与 20.0% 不矛盾，也不能互相换算宣布达标。同理 25/27 与 25/100 不可混用。
- 历史 24–26%（`research/training-report.md:108,213,218,232-233`）无 seed、命令行与哈希，只能标注"统计相容但不可对齐"，不得拼接进新结论。

## 2. 可区分判据（看新数据前冻结）

- 宣布两个候选"可区分"须**同时**满足：配对 bootstrap 95% CI 不含 0，**且** McNemar 双侧 p < 0.05（按实测不一致对 b+c 计数）。
- 任一条件不满足，只能写"并列 / 功效不足"；若 CI 半宽仍 > 5pp，也不得宣称"等同"。
- 多重比较：三个候选两两比较必须注明"未做多重比较校正"并报告未校正 CI，或预先声明 Holm（/Bonferroni）校正后按校正结果判定；不得事后挑显著对。
- 当前 100 局数据已由 P0-02 落盘机器可读 `pairwise_ci`（bootstrap B=10000、rng=0、精确二项 McNemar p）：三组两两差 −2[−13,+9]、−5[−15,+5]、−3[−15,+9] 均含 0；McNemar p=0.860/0.442/0.743，复判仍为两两不可区分。
- 配对设计约束：同 seed（seed_base=90000，逐局 seed=90000+g）、同布局哈希、座位奇偶轮换；不同 seed 集的评测不得合并为同一结论。1094 局/候选是独立比例功效参照，不适用于本配对设计。

## 3. collapse 判据（看新数据前冻结）

- 只有同时满足以下两条才可写"观测到 collapse"：
  1. 连续 **3 个快照**的 `W/N` 逐次下降且相对首快照累计下降 **≥5 个百分点**；
  2. 相邻快照差的 bootstrap 95% **CI 上界 < 0**（统计支持该步下降）。
- 不满足任一条，只能写"未观测到 / 证据不足"，不得写因果结论；缺 entropy 日志时不得用 entropy 叙事补位。
- 每个快照 ≥100 局，同时输出 `W/N`、`W/(W+L)`（带 W+L 与 N）、decisive 率、step_limit_draw 率及 CI；终局率配对 bootstrap 与胜局 bootstrap 用同一 B=10000 与固定 rng seed。
- `research/training-report.md:125-137,139` 的非单调胜率与 Rew 叙述条件不同、无快照序列测量，按本判据记"证据不足 / 未测量"。不改 `max_steps`（215/230 和局为 step_limit，压哨胜局多）。

## 4. 可复现、无作弊与信息边界

- 可复现 = 同 seed / 布局哈希 / 座位 / 动作序列重放一致，`tools/audit_replays.py` 的 `trace_match` 只证明这一点，**不等于无作弊**；报告须原样附此免责声明。
- `belief_exact_match_nonflag` 的命中须区分合法推理（工兵转弯、战斗收缩）与真值泄漏；未逐点归因前不得定性。坐标修复前的"38 次精确命中"作废：按 `tools/audit_replays.py:229-253` 同算法对同一局（iter248 / seed90001）定向复核为 **74 次**，证据 `results/derived/audit_seed90001.json`（sha256 `0a08895cca49456a6a74abe31c4888777b261930a08de2657d87e7e4a60f747d`，`trace_match=true`、编码不一致 0）；两次计数口径/坐标不同，不解读为"泄漏增加"。另 P0-03 分层样本 33 局独立计得 857 次（31/33 局，证据 `results/derived/replay_audit_stratified.json`），样本不同，不得与 74/38 互换。
- 信息边界：`train_junqi_5070ti.py:302-318` 的 `obs[16:28]` 暴露盟友真实兵种，与 `code/siguo-junqi/BOT_API.md:171` 冲突——该行规定己方与已公开身份有真实 type，**其他方向包括盟友的暗子 type 均为 null**，战报只含 id 与 outcome（`BOT_API.md:167`）。
- 产品接入必须做严格暗棋投影与回归（`neural-bot/test_info_boundary.py` 新增 `test_ally_type_hidden`）；改输入编码属新单变量实验，旧 checkpoint 不可比。外层 raw `state_dict` 与 `neural_bot.py:220-235` 的期望字典不兼容，现状只支持可行性结论。
- 站点 belief 行和 0.6575 的成因：P0-03 已实现"旗通道清零前后行和对照"（89 次 `on_commander_dead` 事件，样例 before≈0.68493 → after=1.0，证据 `results/derived/replay_audit_stratified.json`），说明军旗通道清零是行和不为 1 的一个已验证来源；旧报告的"剪枝后未归一化"单一归因仍无逐点产物支持，不得定性为唯一成因。

## 5. 测试基线、产物与可追溯性

- 主工程基线：`cd code/siguo-junqi && npm test` → **114 项 / 110 通过 / 4 失败**（`README.md:40`）；失败测试名集合须与 `research/p0-baseline.md:64-71` 一致：`test/admin-chat2512.test.js:30`、`test/auto-draw.test.js:26`、`test/features-233.test.js:20`、`test/features-245.test.js:10`。按测试名判定，不以退出码判定，不改断言，不新增失败。
- Python 基线：`python -m unittest discover -s workspace/siguo-junqi/junqi_env -p 'test_*.py'`（56 项）。
- 所有统计命令显式 `--out` 到 `D:\4-player-junqi\results\derived\`；派生产物与权重**不入库**：`.gitignore:18` 忽略 workspace/，`:22` 忽略 results/derived/，`:28-30` 忽略 *.pt / *.pth / *.onnx。历史 `results/*.json(l)` 只读归档，禁止改动。
- 每次 run 按 §5 写 manifest：run_id、task_id、时间戳、git HEAD、dirty 标记、完整 cmdline、python/torch/numpy 版本与 GPU、三个脚本各自完整 sha256、每个 checkpoint 全路径与完整 sha256、seed_base、games、seat_policy、baseline 名称与实现 sha256、max_steps、布局生成器源码 sha256、逐局 layout_hash、产物路径与各自 sha256、操作者与机器。缺字段不得宣布验收通过。

## 6. 冻结的评测条件（配套不变量）

- 评测实现：`D:\4-player-junqi\train_junqi_5070ti.py`（外层）；meta 须同时记录 `eval_tournament.py` 与 `tools/analyze_tournament.py` 各自完整 sha256（现只写 `impl_file`，由 P0-02 补全）。
- 基线：`HeuristicBotWrapper`，名称写进 meta；P0-02 已改为从注册表实例化，未知 `--baseline` 名称直接报错，默认行为不变。
- 种子：`seed_base=90000`，每局 `seed=90000+g`；座位：偶数局模型 team0，奇数局 team1。
- 动作：模型与基线均 `logits.argmax`；`max_steps=240` 在参数化后仍冻结为 240。
- 架构：`JunqiActorCritic(hidden_dim=160, num_blocks=8)`，raw state_dict，完整 sha256 写入 meta。
- 三候选完整 sha256（冻结值，来自 `results/tournament.jsonl:1`）：
  - `junqi_best_iter240.pt` = `d2d37c1b32828601c62879c15ca6c00db2e87ac66222a0741975ffeddf48c6b0`
  - `junqi_pool20_iter248.pt` = `7d330eb39cf5c4530e02afbe2e6cdedeeb730e958f4e234fc793dfa7f55bba11`
  - `junqi_iter688.pt` = `260d3cd1112e47491616c3a7c16d025c12c084bab8567644a0d238f0e4ad40aa`
- 布局：评测侧没有 formations 参数，由 `JunqiSelfPlayEnv.reset()` 全局随机 + seed 决定；冻结布局生成器源码 sha256 + `seed_base` + 逐局 `layout_hash`。formations JSON 只属训练侧可选变量（D6），不得当作评测侧已冻结的布阵证据。
- 三份候选均为 2026-11-19 pre-`c1732af` 产物；不得用它们评价 2026-11-24 的 GAE / PPO 修复效果（D5）。

## 7. 决策清单 D1–D8（状态）

| ID | 事项 | 状态 | 关联任务 / 未决后果 |
|---|---|---|---|
| D1 | 65% 口径 | **已确认**（用户 2026-11-26；本文件归档） | P0-01 / P1-01 / P2-01；否则 92.6% 被误读为达标 |
| D2 | GPU 独占 | 待决 | P0-04a/b、P1 全部；抢占致数据作废 |
| D3 | 环境重建 | 已执行（2026-11-26，P0-04a；`results/derived/env_manifest.json`） | P0-04a / P0-03；审计与复评已可运行（GPU 时段仍按 D2） |
| D4 | 算力预算 | 待决 | P1-01/02/03/04；100 局 CI 跨 0 无法取舍 |
| D5 | 旧资产处置 | 待决 | P0-05、P1-02；修复效果被错误归因 |
| D6 | 布阵库入库 | 待决 | P0-05、P1-03；实际各 40 套且 workspace 被忽略 |
| D7 | 是否上线 | 待决 | P2-01；暗棋口径合规与推理策略差异待定 |
| D8 | 重训配置 | 已执行（2026-11-26；2 env×64 steps×batch128 / 400 迭代，隔离副本，`results/derived/manifest_p1-02.json`） | P1-02 已完成；P1-03/04 仍按此配置做单变量对照 |

状态变更须在对应任务卡追加"日期 / 证据路径 / sha256 / 操作者"四字段；本文件不预设任何任务为"通过"。

## 8. 判定输出格式

- 每条结论须含：公式、分子/分母、证据路径 + sha256、CI 上下界、McNemar b/c/p、多重比较方式、判定词（达标 / 未达标 / 证据不足）。
- 当前示例：主口径 25/100 = 25.0%（N=100），未达 65%；辅助口径 25/27（W+L=27，N=100）不得单独宣布达标。
- 可区分判定写清 CI 与 p；不可区分写"并列 / 功效不足"，CI 半宽 >5pp 时不得写"等同"。
- collapse 未满足预注册判据写"证据不足"；Rew、entropy 等叙事不作为达标或 collapse 证据。
- 是否上线归 P2-01（D7）；本文件只冻结口径与判据，不预设产品结论。
