# 报告 09：复盘、提示与陪练功能（game-01）

## 1. 复盘（Review）

### 1.1 入口

- 主页“探析”区可加载 `.game`/PGN（`TitleManager.LoadReviewMode`，`TitleManager.cs:779`）。
- 生涯/最近对局走 `CareerModeManager.ReviewMatch(record, path)`（`CareerModeManager.cs:888`），设置 `GameMode.Local_Review`。
- 复盘模式 `gameMode == Local_Review` 时，棋盘交互由回放控制器接管（`GameManager.MoveTo/NextMove/PrevMove`）。

### 1.2 逐手分析流程

```text
进入复盘
  → 为每一步构造 FEN（PreviousFens[i] + 行棋方）
  → reportAIProcess（独立 Pikafish 进程）：
       setoption name UCI_ShowWDL value true
       position fen <fen> <side>
       go / stop（按复盘强度等待 1s / 2.5s / 5s）
  → 解析 info depth 行的 cp / mate / pv / wdl
  → MoveAnalysis 列表（每步一条）
  → GenerateGameReport() 生成 Report 标签
  → 图表：胜率曲线、评分曲线（GraphAndChart）
```

证据：`GameManager.cs:1621-1652`（复算循环）、`Constants.cs:1861-1876`（时长表）、`ProcessManager.cs:83-97`（go/stop + MultiPV 提取）、`GameManager.cs:1496-1537`（图表数据）。

### 1.3 三档复算强度

| 档 | 枚举 | 每步思考时间 |
|---|---|---:|
| 快速 | `ReviewReanalyzeMode.Fast` | 1000 ms |
| 标准 | `ReviewReanalyzeMode.Standard` | 2500 ms |
| 专业 | `ReviewReanalyzeMode.Professional` | 5000 ms |

`Constants.REANALYSIS_DURATION_TIME_IN_MS`（`Constants.cs:1861`）。 [已验证]

### 1.4 着法评分标签

`CCEnum.ReportMoveType`：`BestMove, Good, Book, Inaccuracy, Mistake, Blunder, Missed, Unknown`（`CCEnum.cs:265`）。

判定规则（`GenerateGameReport`，`GameManager.cs:2748-2905`）：

1. **开局库**：前 20 步内、当前 FEN+着法在 `Book/Openings` 中 → `Book`；开局库结束后前面连续的书着统一标 `Book`。
2. **完全命中**：引擎首选着法 == 实际着法 → `BestMove`。
3. **杀棋情形**：
   - 下一步有杀：我方也有杀且步数不劣 → `BestMove`；错过 → `Missed`；被杀 → `Blunder`/`Mistake`/`Inaccuracy`（按 LoseRate 900/800/700 分档）。
   - 我方本可杀但走了非杀 → `Missed`。
4. **普通情形**：以“下一步最佳分值 - 本步实际分值”的损失为依据：
   - `|cp| <= 1000`：绝对阈值 50 / 200 / 700 / 1000 厘兵 → `BestMove` / `Good` / `Inaccuracy` / `Mistake`，超出为 `Blunder`。
   - `|cp| > 1000`：相对阈值，`base = |cp|*0.01 + 10`，`Good=base`、`Inaccuracy=2.5*base`、`Mistake=4*base`、超出为 `Blunder`；`BestMove` 固定 3%。
   - 当本步分值 `< -100` 时，阈值乘以 1.5（劣势方容错更大）。

`GenerateMoveThresholds`（`GameManager.cs:2882-2905`）。 [已验证]

### 1.5 展示

- 每一步在棋盘上放置图标：`MyMoveIcon` + `StartPointIcon`，颜色/图标来自 `ReviewMoveTypeLargeSprites`（`GameManager.cs:4288-4310`）。
- 推荐着法用箭头：`ShowRecommendedMoveArrow`（`GameManager.cs:4260`）。
- 悬浮文案按分值档：绝杀/杀 N 步/均势/红方小优·中优·大优/黑方对应/和棋率/胜率（`Constants.cs:461-481`）。

## 2. 提示（Hint）

### 2.1 对局内提示

- `RequestMoveAnalysis(color, 1000f)`：分析 AI 对当前局面思考 1 秒，取 MultiPV 第一条，显示箭头（`GameManager.cs:2375`）。
- `AddMoveAnalysisAsync`：每步后台记录 `bestMoveAnalysis` 与 `multiMoveAnalysis`，供“提示多着法”面板使用（`GameManager.cs:2400-2420`）。
- `ShowCareerModeHintMoves`：展示前若干候选着法按钮，点击后显示箭头（`GameManager.cs:5397`）。
- 同一回合重复点击不重复扣次数（`isRepeatedActionInSameTurn`，`GameManager.cs:641-650`）。

### 2.2 提示成本

- 生涯单机：`SkillCountText[HintMove]` 递减（`GameManager.cs:5425-5432`）。
- 残局模式：`hintMoveCount` 递减并显示（`GameManager.cs:5330-5345`）。
- 训练模式：`currentTraining.HintMoveCount` 递减。

### 2.3 分析 AI 配置

- `analysisAIProcess` 独立进程，`setoption name UCI_ShowWDL value true`。
- 复盘/训练/残局等“稳定分析”场景 MultiPV=3；其余 MultiPV=5（`GameManager.cs:1166-1171`、`IsStableAnalysisAI`）。

## 3. 撤销（Undo）

- `GetUndoMoves()`：本地多人/复盘撤 1 步；单机/生涯撤 2 步（回到自己回合）（`GameManager.cs:2507-2517`）。
- 生涯挑战模式禁用撤销（`GameManager.cs:2497-2500`）。
- 撤销会恢复被吃子、棋盘状态、FEN 与走子历史，并同步移除对应的分析记录（`GameManager.cs:2578-2581`）。

## 4. 训练与残局（陪练）

| 功能 | 实现 | 证据 |
|---|---|---|
| 残局题库 | `Resources/Book/Endgames` 文本列表 | `GlobalVariable.cs:106-109` |
| 残局模式 | `GameMode.Local_Endgame`，固定 AI 等级与提示次数 | `GameManager.cs:896-898` |
| 训练关卡 | `CareerModeTraining`，`GetTrainingAILevel() = max(level, 10)` | `CareerModeTraining.cs:28-35` |
| 训练反馈 | `TrainingFeedback` 按钮与 `UpdateTrainingFeedback` | `GameManager.cs:5240-5265` |
| 残局记录 | `EndgameRecords`：`FEN color level 结果 skipped 时间` | `GameManager.cs:5280-5315` |
| 生涯辅助技能 | `CareerModeAssistSkill.HintMove / Undo / Analysis` 计数 | `GameManager.cs:623-650` |
| 新手教学 | `TutorialManager`：动画/交互/自对弈 | `TutorialManager.cs:16`、`CCEnum.TutorialType` |

## 5. 设计要点

- **分析与对弈隔离**：两个 Pikafish 进程，复盘重算不会污染对局引擎的置换表与 PV。
- **评分与人类语言解耦**：引擎只给 cp/mate/wdl，UI 层再映射为“优/劣/失误/漏杀”。
- **提示有成本**：生涯/残局/训练都用次数限制提示，形成“练习—反馈—约束”的陪练闭环。
- **不虚构服务器分析**：全部评分来自本地引擎。 [已验证]

## 6. 提示功能的静态补充（不依赖运行）

### 6.1 触发条件

`IsEndgameHintMoveAvailable()`（`GameManager.cs:5523-5552`）要求同时满足：

1. 模式为 `Local_CareerMode_Training` 或 `Local_Endgame`。
2. `gameState == WaitingInput`（轮到我方）。
3. 本回合未使用过提示（`isRepeatedActionInSameTurn[HintMove] == false`）。
4. 次数未耗尽：训练看 `currentTraining.HintMoveCount`；残局看 `hintMoveCount`。

任一条不满足，`EndgameHintMoveButton` 直接置灰（`GameManager.cs:2019`）。

### 6.2 调用链

```text
EndgameHintMoveButton.onClick
  → RequestEndgameMoveAnalysis(currentPieceColor, 1000f)     GameManager.cs:5320
      → 若本回合已提示过：只重置标记，不再请求
      → 否则扣减次数（训练/残局各自字段）
      → analysisAIProcess: position fen <当前局面> <行棋方>
      → GetMoveAnalyses(1000f)：go → 等 1s → stop → 取 MultiPV 第一条
      → ShowRecommendedMoveArrow(move)                      GameManager.cs:4260
          → 箭头精灵 "Arrows/Arrow_{dx}_{dy}"
          → 起点/终点图标 + Show_Vertical / Show_Horizontal 动画
```

### 6.3 次数规则

- 初始值：`Utils.LoadGameData("EndgameHintMoveCount", 3)`（`GameManager.cs:897`）。
- 每通过一关：`hintMoveCount = Math.Min(9, hintMoveCount + 1)`（`GameManager.cs:5238`）。
- 使用一次：`--hintMoveCount` 并写回 ES3（`GameManager.cs:5343`、`:3863`、`:3915`）。
- 界面文案与数值一致：残局入口显示“推荐着法次数 1”“最多 9 次”。

### 6.4 动态未复现的原因分析

- 首次点击后 `isRepeatedActionInSameTurn[HintMove]` 被置为 true；在未走子的同一回合内再次点击会被条件 3 拦截，按钮置灰。
- 箭头动画为短时播放（`Show_Vertical/Horizontal`），若首次点击已触发，后续截图可能错过动画；但计数应已扣减。
- 由于用户要求不再启动游戏，未进一步核对计数变化；该点保留为“有证据支持、未完整验证”。
