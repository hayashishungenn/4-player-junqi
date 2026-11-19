# 报告 07：AI 难度机制（game-02）

## 1. 结论

game-02 的难度实现**无法从现有证据完整还原**：主体二进制与 `default_gtp.cfg` 均已缺失。可确认的只有运行时行为：对弈走子 `genmove` 单步约 5–9 秒、访问数最高 1,706；分析固定 200 visits；固定 4 个搜索线程。 [已验证：日志；未知：难度映射]

## 2. 可确认的运行时参数

| 参数 | 值 | 证据 |
|---|---|---|
| 棋盘 | 9 路（本次对局） | `Controller: boardsize 9` |
| 贴目 | 5.5 | `Controller: komi 5.5`；SGF `KM[5.5]` |
| 规则 | 中国规则 | SGF `RU[chinese]`；`kata-set-rules suicide false` |
| 搜索线程 | 4 | `Using 4 CPU thread(s) for search` |
| 分析访问数 | 200 | `kata-analyze Black 200 ownership true` |
| 对弈访问数 | 动态，最高 1,706 | `Player.log` 的 `visits N` |
| 对弈单步耗时 | 约 5–9 秒 | GTP 日志时间戳 |
| 后端 | Eigen CPU | `Eigen (CPU) backend` |

## 3. 难度可能的实现方式（推测）

KataGo 生态中常见的降级手段：

1. 降低 `maxVisits` 或 `maxTime`（最常用）。
2. 提高 `wideRootNoise` / 降低 `cpuct`，增加探索随机性。
3. 使用较弱网络或让子。
4. 对候选着法做随机采样。

本作的界面与配置不可见，无法确认采用哪一种。**不把上述任何一条写成已验证结论。**

## 4. 与 game-01 的对比（仅就可见证据）

| 项 | game-01 | game-02 |
|---|---|---|
| 难度档位 | 13 档（代码可读） | 未知 |
| 降级手段 | 引擎类型 + 深度 + MultiPV 随机 + 开局库 | 未知（推测为访问数/时间） |
| 分析采样 | 1s/2.5s/5s，MultiPV 3/5 | 固定 200 visits + ownership |
| 引擎可调 Skill/Elo | Pikafish 支持但未使用 | KataGo 无 Skill/Elo 选项 |

## 5. 若需补齐

需重新安装《Just Go》，取得：

- `JustGo_Data/Managed/Assembly-CSharp.dll`（难度配置表）。
- `JustGo_Data/StreamingAssets/AI/Katago_CPU/default_gtp.cfg`（搜索参数）。
- 可能的 `Katago_GPU` 目录与多网络文件。

在此之前，game-02 难度结论保持“未知”。
