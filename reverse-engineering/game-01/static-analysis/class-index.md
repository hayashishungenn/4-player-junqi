# game-01 关键类与方法索引

反编译方式：`ilspycmd -p` 反编译 `Assembly-CSharp.dll`，得到 690 个 `.cs`。全量类型声明（class/struct/enum/interface，含嵌套）共 964 条，见 `full-class-index.md`；其中 `class` 声明 744 条。以下行号均指 `static-analysis/decompiled/` 下的文件。

## 1. AI 与搜索

| 类 | 文件:行 | 关键成员 | 作用 |
|---|---|---|---|
| `NativeAI` | `NativeAI.cs:6` | `GetRandomMove` :83；`GetNextMove` :98；`AlphaBeta` :121；`Evaluate` :186；`ImprovedEvaluate` :209；`GetPiecePositionValue` :237 | 纯 C# 浅层搜索；Easy/Medium 两档 |
| `SharpElephantEyes.ElephantEyesAI` | `SharpElephantEyes/ElephantEyesAI.cs:8` | 构造 :14（`PregenInit`/`Hash.NewHash(24)`/`Ucci.Init`）；`GetNextMove` :34；`SetBanMoves` :57；`SetFenPosition` :65 | ElephantEyes 移植版封装；先查书，再 UCCI 搜索 |
| `SharpElephantEyes.Search` | `SharpElephantEyes/Search.cs:7` | `SearchMain` :616；`SearchRoot` :531；`SearchPV` :398；`SearchCut` :286；`SearchQuiesc` :222；`SearchUnique` :597 | 迭代加深 + Alpha-Beta/PVS + 静态搜索 |
| `SharpElephantEyes.Ucci` | `SharpElephantEyes/Ucci.cs:7` | `SetPosition` :67；`Analyze` :92；`GetTopMoves` :106；`GetBookMoves` :149；`BanMoves` :79 | 内部 UCCI 命令层与线程循环 |
| `SharpElephantEyes.Book` | `SharpElephantEyes/Book.cs:5` | `BookStruct` :7；表 12,081 条 :20 | 内置开局库 |
| `SharpElephantEyes.Hash` | `SharpElephantEyes/Hash.cs:5` | `NewHash`、`ProbeHash`、`RecordHash`、`ClearHash` | 置换表 |
| `ProcessManager` | `ProcessManager.cs:10` | 构造 :30；`GetMoveAnalyses` :83；`GetNextMove` :99；`ExtractMultiPVValues` :132；`ExtractPVValues` :166 | 启动并驱动 Pikafish 子进程，解析 UCI 输出 |

## 2. 对局与棋盘

| 类 | 文件:行 | 关键成员 | 作用 |
|---|---|---|---|
| `GameManager` | `GameManager.cs:31` | `InitializeGameAI` :1157；`MakeNextMoveByAI` :3588；`AddMoveAnalysisAsync` :2400；`RequestEndgameMoveAnalysis` :5325；`GenerateGameReport` :2748；`GenerateMoveThresholds` :2882；`UndoMove` :2519；`ShowCareerModeHintMoves` :5397；`DownloadRecord` :4322；`OnSaveFileComplete` :4328 | 对局主控、AI 调度、提示/复盘/撤销/导出 |
| `ChessBoard` | `ChessBoard.cs:5` | `PreviousFens` :42；`Moves.Add` :220；`UndoPiece`；`GetAvailableMoves` | 棋盘状态、FEN 历史、着法历史、规则判定 |
| `ChessPiece` | `ChessPiece.cs:4` | `PieceType`、`PieceColor`、`CurrentLocation` | 棋子组件 |
| `GameRecord` | `GameRecord.cs:6` | 字段：`Id`、`EventName`、`RedPlayerName`、`BlackPlayerName`、`RedPlayerEloScore`、`BlackPlayerEloScore`、`GameResult`、`PieceMaterial`、`StartingPieceColor`、`GameScene`、`GameTime`、`MatchDate`、`MatchDuration`、`BoardStartFen`、`Moves`、`MoveNotations`、`MoveAnalysis`、`Report` | 棋谱与复盘数据模型 |
| `MoveAnalysis` | `MoveAnalysis.cs:5` | `Move`、`WinRate`、`DrawRate`、`LoseRate`、`IsMateInNSteps`、`StepsToMate`、`CentipawnValue`、`Sequence` | 单步分析结果 |

## 3. 难度与配置

| 类/字段 | 文件:行 | 说明 |
|---|---|---|
| `AIOptions` | `AIOptions.cs:3` | `Type`、`Depth`、`Randomness`（默认 1）、`UseBookMoves`（默认 true） |
| `AIConfiguration`（抽象） | `AIConfiguration.cs:4` | `Parameters`、`RotationStrategy`、`PredefinedAI`（按 `StepRange` 覆盖） |
| `StaticAIConfiguration` / `StepBasedAIConfiguration` / `ProbabilityBasedAIConfiguration` | 同名文件 | 三种难度轮换策略 |
| `Constants.AI_ELO_RATING` | `Constants.cs:1913` | 13 档 ELO：100/200/400/600/900/1200/1500/1800/2000/2150/2400/2550/2800 |
| `Constants.AI_CONFIGURATIONS` | `Constants.cs:1919` | 13 级（0–12）配置表 |
| `Utils.GetAINameByLevel` | `Utils.cs:449` | 0–12 英文名（Newcomer…Grandmaster），经 I2.Loc 翻译为“十五级棋士…特级大师” |

## 4. 存档、复盘与 UI

| 类/方法 | 文件:行 | 说明 |
|---|---|---|
| `GlobalVariable.InitializeES3Settings` | `GlobalVariable.cs:78` | ES3 AES 加密存档，密钥硬编码在代码中（本报告不复述密钥） |
| `GlobalVariable.InitializeOpenings` | `GlobalVariable.cs:82` | 开局库加载 |
| `Utils.WriteToPGN` | `Utils.cs:1334` | 导出 PGN，中文记谱，GB2312 编码 |
| `CareerModeManager.ReviewMatch` | `CareerModeManager.cs:888` | 进入 `Local_Review` 复盘模式 |
| `TitleManager.LoadReviewMode` | `TitleManager.cs:779` | 从文件加载复盘 |
| `HomeManager.ReviewLastGame` | `HomeManager.cs:349` | 最近对局复盘入口 |
| `TutorialManager` | `TutorialManager.cs:16` | 新手教学（自走/交互/自对弈） |
| `CareerModeTraining` | `CareerModeTraining.cs:6` | 训练/残局关卡、提示次数 |
