# 报告 09：复盘、提示与陪练功能（game-02）

## 1. 可观察的功能

| 功能 | 证据 | 结论 |
|---|---|---|
| 逐手分析 | `kata-analyze Black 200 ownership true` × 68 | 有，按 200 visits 采样 |
| 势力/归属显示 | `ownership true` + 80 个浮点输出 | 有，用于棋盘着色 |
| 胜率曲线 | `WhiteWinRates` 数组 | 有，逐手保存 |
| 领先目数曲线 | `WhiteLeadScores` 数组 | 有，逐手保存 |
| 棋谱保存 | SGF + `.sav` | 有 |
| 职业棋谱库 | `RecentProMatches` 59 个 SGF/sav | 有，在线更新 |
| 引擎原始输出 | `kata-raw-nn 1` × 135 | 有，可能用于高级分析/调试 |

## 2. 分析调用节奏

GTP 日志显示 `kata-analyze` 连续调用 68 次，间隔约 2–3 秒：

```text
10:31:26 kata-analyze Black 200 ownership true
10:31:28 kata-analyze Black 200 ownership true
10:31:30 kata-analyze Black 200 ownership true
...
```

推测业务层在复盘/分析界面按固定节流刷新，而不是每次点击都调用。 [推测]

## 3. 提示（Hint）

- 未在日志中发现独立的“提示”命令；最可能复用 `kata-analyze` 的候选着法（`info move` 多条 + `pv`）。
- 界面是否显示推荐点/箭头未知。
- 不能把 `genmove` 当作提示：日志中 `genmove` 只出现在 AI 回合。

## 4. 撤销、训练、残局

- 撤销：KataGo GTP 支持 `undo`，但日志中未出现，无法确认游戏是否使用。 [未知]
- 训练/课程：存在 `Careers`、`CareerSaves`，但内容为生涯进度，非棋力训练题库。 [有证据支持]
- 残局题库：未发现对应文件。

## 5. 陪练设计要点（可借鉴）

1. **分析与对弈共用同一引擎、不同调用模式**：对弈 `genmove`（时间控制），分析 `kata-analyze`（固定 200 visits）。这与 game-01 的双进程分离不同，但同样避免分析拖慢对弈。
2. **逐手存储分析曲线**：胜率与目差直接落盘，复盘时无需重新计算即可画曲线；重算只在用户主动触发时进行。
3. **ownership 可视化**：把神经网络的归属预测转成势力图，比单纯胜率更直观。
4. **职业棋谱在线更新**：用 Azure Blob 拉取 SGF，形成“名局库”内容运营能力。

## 6. 未知

- 复盘界面是否支持分支、试下、逐手评分标签。
- 提示是否有次数/付费限制。
- 是否提供“AI 让子/指导棋”模式。
