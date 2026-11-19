# 报告 05：搜索算法分析（game-02）

## 1. 结论

《Just Go》没有自研搜索代码对外暴露；棋力由 **KataGo v1.10.0** 提供。KataGo 属于 **MCTS（PUCT）+ 神经网络（policy/value）** 体系，而非 Alpha-Beta。 [已验证：GTP 日志与引擎标识]

## 2. 证据

### 2.1 引擎与版本

```text
GTP Engine starting...
KataGo v1.10.0
Using TrompTaylor rules initially, unless GTP/GUI overrides this
Using 4 CPU thread(s) for search
```

（`gtp_logs/20260116-102356-7B8BC9CC.log` 前几行）

### 2.2 搜索输出结构

`Player.log:1281` 起：

```text
info move F5 visits 25 utility -1.11674 winrate 0.000776738 scoreMean -32.7426
  scoreStdev 17.0632 scoreLead -32.7426 scoreSelfplay -32.3188 prior 0.328141
  lcb -0.0327646 utilityLcb -1.21066 order 0 pv F5 G5 G6 G7 H6 H7
info move G6 visits 6 ... order 1 pv G6 F5 F7
...
ownership -0.181787 -0.389969 ...
```

这些字段是 MCTS 的典型输出：

- `visits`：该候选的模拟次数。
- `prior`：策略网络先验概率。
- `winrate` / `scoreLead`：价值网络与搜索结果。
- `utility` / `lcb`：搜索选择用的效用与下置信界。
- `pv`：主变例。
- `ownership`：每点归属预测。

### 2.3 并行与后端

```text
Eigen (CPU) backend thread 0..3: Model version 10
Loaded neural net with nnXLen 19 nnYLen 19
Using 4 CPU thread(s) for search
```

- 4 个 CPU 搜索线程；Eigen 后端（无 GPU）。
- 网络同时支持 19×19 与 9×9（日志中两次 `Initializing neural net buffer to be size 19*19` / `9*9`）。

## 3. 算法归属

| 项 | 结论 | 依据 |
|---|---|---|
| MCTS / PUCT | 是（KataGo 默认） | `visits`、`prior`、`utility`、`lcb`、`pv` 输出 |
| Alpha-Beta | 否 | 无 depth/alpha/beta 字段；KataGo 非 AB 引擎 |
| 神经网络 | 是（policy + value + ownership 头） | `kata-raw-nn`、`prior`、`winrate`、`ownership` |
| 置换表 / Zobrist | 引擎内部实现，未在日志暴露 | — |
| 开局库 | 未发现；日志中无 book 查询 | — |
| 终局数据库 | 未发现 | — |
| 让子/贴目 | 支持（`komi`、`handicap` 字段） | GTP `komi`、存档 `Handicap` |

## 4. 搜索参数

- 对弈：`genmove`，按时间控制（单步 5–9 秒），实际访问数可达 1,706（日志最大值）。
- 分析：`kata-analyze ... 200`，固定 200 visits。
- 线程：4；是否随难度变化未知。

## 5. 未知

- `default_gtp.cfg` 的完整内容（`maxVisits`、`maxTime`、`ponderingEnabled`、`wideRootNoise`、`rootSymmetryPruning` 等）。
- 是否按难度切换 `maxVisits`/`maxTime`。
- 是否使用多网络（对弈网络 vs 分析网络）。
- KataGo 的具体版本分支与编译选项（CPU/Eigen 已确认）。
