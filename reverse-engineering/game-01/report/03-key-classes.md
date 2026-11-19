# 报告 03：关键类与方法清单（game-01）

## 1. 任务书关键词与实际类名对照

任务书给出的是搜索关键词，不是目标包一定存在的类名。实际对照如下：

| 关键词 | 实际类/文件 | 是否承担该职责 | 证据 |
|---|---|---|---|
| ChessEngine / GameEngine | 无同名类；职责分散在 `GameManager`、`ChessBoard`、棋子类 | — | `rg "class ChessEngine|class GameEngine"` 无结果 |
| AIEngine | 无同名类；`NativeAI`、`ElephantEyesAI`、`ProcessManager` | 是 | 见下 |
| Search | `SharpElephantEyes.Search` | 是 | `Search.cs:7` |
| Evaluate | `NativeAI.Evaluate/ImprovedEvaluate`、`Position.Evaluate`、NNUE | 是 | `NativeAI.cs:186/209`；`Search.cs:158` |
| Strategy | 无同名类；`AIConfiguration` 的三种轮换策略 | 部分 | `AIConfiguration.cs` |
| Board / Position | `ChessBoard`、`SharpElephantEyes.Position` | 是 | `ChessBoard.cs:5`、`Position.cs:5` |
| Move | `SharpElephantEyes.Position.MoveStruct`、`MoveAnalysis`、`Constants.Point` | 是 | `Position.cs:34`、`MoveAnalysis.cs:5` |
| Hint | `GameManager.RequestMoveAnalysis`、`ShowCareerModeHintMoves`、`HintMoveButtons` | 是 | `GameManager.cs:2375/5397` |
| Undo | `GameManager.UndoMove` / `PerformUndoMoveCoroutine` | 是 | `GameManager.cs:2519` |
| Replay / Record | `GameRecord`、`CareerModeManager.ReviewMatch`、`Utils.WriteToPGN` | 是 | `GameRecord.cs:6`、`CareerModeManager.cs:888` |
| Analysis | `MoveAnalysis`、`GenerateGameReport`、分析 AI 进程 | 是 | `GameManager.cs:2748` |
| Difficulty | `Constants.AI_CONFIGURATIONS`、`AI_ELO_RATING` | 是 | `Constants.cs:1913` |
| Training | `CareerModeTraining`、`Local_CareerMode_Training`、`Local_Endgame` | 是 | `CareerModeTraining.cs:6` |

## 2. 核心类职责

### 2.1 `GameManager`

对局总控，约 6,000 行。职责包括：

- AI 初始化与调度：`InitializeGameAI`（1157）、`MakeNextMoveByAI`（3588）。
- 分析/提示：`AddMoveAnalysisAsync`（2400）、`RequestEndgameMoveAnalysis`（5325）、`ShowCareerModeHintMoves`（5397）。
- 复盘评分：`GenerateGameReport`（2748）、`GenerateMoveThresholds`（2882）。
- 撤销：`UndoMove`（2519）、`GetUndoMoves`（2507，单机/复盘撤 1 步，其余撤 2 步）。
- 导出：`DownloadRecord`（4322）、`OnSaveFileComplete`（4328，GB2312 PGN）。

### 2.2 `ChessBoard`

棋盘状态与规则：

- `PreviousFens`（42）：每步后的 FEN 历史，用于重复局面、长将/长捉判定、AI 输入。
- `Moves`（220）：4 字符坐标着法序列（如 `h2e2`）。
- 长将/长捉/重复局面会生成 `ForbiddenMoves` / `DrawMoves`，并在 AI 调用时作为 banMoves 传入（`GameManager.cs:3610-3614`）。

### 2.3 三种 AI 实现

| 实现 | 入口 | 决策方式 |
|---|---|---|
| `NativeAI` | `GetNextMove(depth, color)` | 自研 Alpha-Beta；Easy 用子力差，Medium 用子力+位置表；depth=0 时随机走法 |
| `ElephantEyesAI` | `GetNextMove(depth, useBookMoves)` | 先查内置开局库；否则 UCCI 分析，内部 `Search` 迭代加深 |
| `ProcessManager` | `GetNextMove(depth, bannedMoves)` | 启动 Pikafish，`position fen` + `go depth N`，解析 MultiPV |

### 2.4 数据模型

- `GameRecord`：棋谱元数据 + `Moves` + `MoveNotations` + `MoveAnalysis` + `Report`。
- `MoveAnalysis`：`Move`、`WinRate/DrawRate/LoseRate`、`IsMateInNSteps/StepsToMate`、`CentipawnValue`、`Sequence`。
- `AIOptions`：`Type`、`Depth`、`Randomness`、`UseBookMoves`。

## 3. 规则实现

棋子规则按类型分文件：`Advisor.cs`、`Bishop.cs`、`Cannon.cs`、`Horse.cs`、`Chariot.cs`、`Solider.cs`、`General.cs`（均在反编译根目录），每个类实现 `IsValidPos`、`IsValidMove`、`CreateMoves`。`BaseChessBoard.cs` 与 `ChessBoard.cs` 负责落子、吃子、悔棋与终局判定。

## 4. 未发现/未证实的类

- 未发现名为 `TranspositionTable`、`ZobristHash`、`NeuralNetwork` 的业务类；置换表与 Zobrist 在 `SharpElephantEyes.Hash`/`Pregen`/`ZobrInit` 中，NNUE 由 Pikafish 内部实现。
- 未发现独立的“服务器 AI 客户端”类；联机只同步走子与房间状态。
- `PikaFish_Deprecated` 目录无代码引用（[推测] 历史兼容）。
