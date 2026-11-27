# P1-01 预注册：5 候选 × 300 局配对复评（2026-11-27）

状态：**预注册（运行前冻结）**。本文件只冻结判据与流程，不报告结果；未取得 GPU 时段与显式执行授权前不得运行。依据 `research/acceptance-criteria.md`、`research/next-phase-task-book.md` §1/§2/§5/§6 与 2026-11-27 用户确认的“先评测再改训练、5 候选×300 局”。

## 1. 冻结条件

| 项 | 冻结值 |
|---|---|
| 候选 | 三份 pre-fix + `workspace/train-p1-02/junqi_iter400.pt` + `workspace/train-p1-02b/junqi_iter800.pt`（共 5） |
| 局数 | 每候选 300 局，共 1500 局 |
| 种子 | `seed_base=90000`，逐局 `seed=90000+g` |
| 最大步数 | `max_steps=240`；不得为减少和局而改上限 |
| 动作 | 模型与基线均 `logits.argmax` |
| 基线 | `HeuristicBotWrapper`（注册表唯一名称） |
| 座位 | 偶数局模型 team0，奇数局 team1 |
| 统计 | 配对 bootstrap `B=10000`、`rng=0`；精确二项双侧 McNemar |
| 多重比较 | 10 个两两比较，预先声明 Holm；阈值 `0.005/0.00556/0.00625/0.00714/0.00833/0.01/0.0125/0.0167/0.025/0.05`；同时保留未校正 CI/p |
| 产物 | `results/derived/tournament_300.jsonl`、`summary_300.json`、`audit_300.json`、`eval_300.log`、`analyze_300.log`、`audit_300.log`、`manifest_p1-01.json` |

候选完整 sha256：

- `junqi_best_iter240.pt` = `d2d37c1b32828601c62879c15ca6c00db2e87ac66222a0741975ffeddf48c6b0`
- `junqi_pool20_iter248.pt` = `7d330eb39cf5c4530e02afbe2e6cdedeeb730e958f4e234fc793dfa7f55bba11`
- `junqi_iter688.pt` = `260d3cd1112e47491616c3a7c16d025c12c084bab8567644a0d238f0e4ad40aa`
- `workspace/train-p1-02/junqi_iter400.pt` = `0cf0b9bd1be35a422f1759b25ef3ae3c57e152c9a601c72e42cc11d9741b0a19`
- `workspace/train-p1-02b/junqi_iter800.pt` = `d09bff62f06330432a974310be0dee732b4301efb2589682a9d995bab620ca14`

## 2. 判定规则（看数据前冻结）

- 65% 主验收只看 `W/N`（含和局）；`W/(W+L)` 仅诊断，每次必须同时写 `W+L` 与 `N`。
- 两候选“可区分”须**同时**满足：配对 bootstrap 95% CI 不含 0，且 McNemar 双侧 p 经 Holm 校正后 `<0.05`。
- 否则写“并列 / 功效不足”。CI 半宽 `>5pp` 时不得写“等同”。
- 可区分只说明差异有统计支持；`iter800` 不得默认优于 `iter400`，方向必须来自实测 CI。即便方向为正，仍标注“可评测快照，非收敛”（PG 曾达 1e4–1e6）。
- 跨版本比较只使用本次同 seed / 布局哈希 / `max_steps` 的产物；不得与历史 100 局或 24–26% 数字拼接。
- 输出每条结论固定格式：公式；分子/分母；证据路径 + sha256；CI 上下界与半宽；McNemar `b/c/p` 与 Holm 后 p；多重比较方式；判定词（达标/未达标/可区分/并列-功效不足/证据不足）。

## 3. 运行前功效实算（2026-11-27）

历史 100 局实测不一致对为 `(b,c)=(15,17)`、`(11,16)`、`(20,17)`，合计 `b+c=32/27/37`。按同效应量放大到 300 局并用精确二项双侧拒绝域计算：

| 对 | 放大后 (b,c) | b+c | 精确功效 |
|---|---|---|---|
| 1 | (45,51) | 96 | 0.0315 |
| 2 | (33,48) | 81 | 0.0448 |
| 3 | (60,51) | 111 | 0.0363 |

三组功效均远低于 0.8：300 局只能**缩窄区间**，不足以对这些历史小效应作“可区分/等同”判定。跨版本对（post-fix vs pre-fix）无先验 b/c，运行前标注“功效未知”，运行后只给描述性事后功效，不参与判定。禁止用 1094 局独立比例功效为 300 局配对设计辩护。

## 4. 结果分叉（预先声明）

1. post-fix 对 pre-fix 可区分且方向为正：胜出快照作为后续单变量实验基线；仍按 `W/N` 判 65%，未达就是未达；转训练稳定性改造，不盲目加迭代。
2. 不可区分或方向为负：不宣称修复带来棋力提升；停止继续续训；转 collapse 快照扫描与日志改造。
3. CI 半宽仍 >5pp：写“区间缩窄但样本不足”；扩局数须重新申请算力预算。
4. 65% 仍远未达（Wilson 上界也低于 0.65）：不启动任何“再训 400/800 迭代”；把“当前训练范式不足”列为新决策点交用户。

## 5. 运行前/后检查

- 运行前：`git status --short`、`git rev-parse HEAD`、`git diff -- results/` 为空；确认三个脚本与五个权重 sha256；确认 `--out` 全部指向 `results/derived/`。
- manifest `manifest_p1-01.json` 字段：`run_id/task_id=P1-01`、日期、操作者、机器与 GPU 型号、git HEAD/dirty、完整 cmdline、python/torch/numpy 版本、train/eval/analyze/audit 四脚本完整 sha256、5 候选全路径与完整 sha256、基线名与实现独立 sha256、`seed_base/games/seat_policy/max_steps`、逐局 `layout_hash`、三份产物路径与 sha256。缺字段不得宣布验收通过。
- 运行后：核对 1500 局行数、每候选 300 局、10 组两两 CI/p、座位拆分、终局分布、审计 trace 与免责声明；`git diff -- results/` 仍为空。

## 6. 免责声明

`trace_match` 只证明可复现，不证明无作弊；非亮旗 belief 精确命中未逐点归因前不得定性为信息泄漏。派生产物与权重不入库。任何 GPU 占用、提交与推送仍需执行时单独取得用户授权；权限被拦截即停止并报告，不绕过。
