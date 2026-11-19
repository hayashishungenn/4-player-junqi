# Just Xiangqi 棋谱与复盘

## 1. 棋谱模型

`GameRecord` 字段：Id、EventName、双方名称/ELO、GameResult、PieceMaterial、StartingPieceColor、GameScene、GameTime、MatchDate、MatchDuration、BoardStartFen、Moves、MoveNotations、MoveAnalysis、Report。

- 着法：4 字符坐标（`h2e2`），与 UCCI 兼容。
- 记谱：按语言预生成（简中/繁中/英）。
- 分析：每步 `CentipawnValue`、`WinRate/DrawRate/LoseRate`、`IsMateInNSteps/StepsToMate`、`Sequence`。
- 评分：每步一个 `ReportMoveType`。

## 2. 文件格式

- 内部：`.game`，Odin JSON（`$id/$type/$rlength/$rcontent`；GUID 裸写、DateTime/TimeSpan 用 tick）。
- 外部：PGN，中文记谱，GB2312 编码（`Utils.WriteToPGN`）。
- 名局：`StreamingAssets/Classic/*.game`（24 局）。
- 存档：ES3 AES；生涯/历史另存 Odin JSON。

## 3. 复盘

- 入口：探析 → 游戏记录；或生涯/最近对局。
- 逐手分析：独立 Pikafish 进程，`UCI_ShowWDL=true`，每步等待 1s / 2.5s / 5s（快速/标准/专业）。
- 三页 UI：复盘（棋盘 + 着法列表 + 颜色评分点 + 导航）、图表（胜率/和棋/黑胜堆叠图）、详细信息（双方七类标签计数）。
- 实机验证：`reverse-engineering/evidence/game-01/s27..s29`。

## 4. 提示

- 残局/训练：`EndgameHintMoveButton` → `RequestEndgameMoveAnalysis`（1 秒分析，MultiPV 首条）→ 箭头。
- 条件：`WaitingInput` + 本回合未提示 + 次数 >0。
- 次数：初始 3，每过一关 +1，上限 9；写回 ES3。
- 生涯：提示/撤销/分析三种辅助技能计数。

## 5. 撤销

- 单机/生涯撤 2 步（回到自己回合）；本地多人/复盘撤 1 步。
- 挑战模式禁用。
- 撤销同时回退 FEN、走子历史与被吃子，并移除对应分析记录。

## 6. 训练

- 残局题库 `Book/Endgames`；训练关卡 `CareerModeTraining`（AI 等级下限 10）。
- 反馈按钮、提示次数、关卡通过记录。
- 生涯辅助技能形成“练习—提示—复盘”闭环。

## 7. 对四国军棋的迁移建议

| 设计 | 迁移方式 |
|---|---|
| 内部 JSON + 外部标准格式 | 自有 `record.json` + 可选 SGF 风格导出 |
| 逐手分析数组 | `perMove: {score, wdl, label, conf}` |
| 三页复盘 | 复盘/曲线/统计三视图 |
| 提示次数 | 训练关消耗，普通局可配置 |
| 撤销 2 步 | 四国按“一回合”定义回退 |
| 实战/明棋视角 | 新增 `viewMode: actual/revealed`，评分必须标注信息集 |

## 8. 证据

- `reverse-engineering/game-01/report/08-record-format.md`
- `09-review.md`
- 实机截图 `s26`–`s29`、`s41`–`s48`
