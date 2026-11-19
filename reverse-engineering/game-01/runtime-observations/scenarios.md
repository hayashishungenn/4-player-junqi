# game-01 动态观察记录（12 场景）

日期：2026-11-19。对象：《Just Xiangqi》Steam 版，Windows 11，150% DPI。
操作方式：官方 exe 启动；DPI 感知鼠标点击；窗口截图。未使用调试器/注入/改包。

截图目录：`../evidence/game-01/`。日志：`%LocalLow%\Studio Amateur\JustXiangqi\Player.log`。

---

## 场景 1：启动和主菜单

- **操作**：运行 `JustXiangqi.exe`，等待 20 秒。
- **观察**：出现 JUST XIANGQI 主界面，左侧导航“游玩/探析/其他”，游玩页 5 张卡片：生涯模式、人机对战、在线比赛、热座模式、残局挑战。
- **截图**：`s40-mainmenu.png`、`screen-02-mainmenu-window.png`。
- **日志**：`Player.log` 记录 Unity 2020.3.15f2、Mono、Steam 初始化；`Failed to load the Steam App List ... 404` 非致命。
- **代码**：`TitleManager`（标题/导航），`GameManager` 场景初始化。
- **结论**：启动链正常，主菜单为单页卡片式入口。[已验证]

## 场景 2：新建对局

- **操作**：点击“人机对战”卡片 → 设置页 → 点击“开始”。
- **观察**：设置页含玩家名、执子颜色、读秒、难度、练习模式、初始局面、棋子类型、对局环境；点击开始后进入 3D 棋盘对局。
- **截图**：`s14-reenter-setup.png`、`s15-ingame-full.png`、`screen-03-after-click.png`。
- **日志**：场景卸载/加载记录；进入对局后 `pikafish.exe` 子进程出现。
- **代码**：`GameManager.InitializeGameAI()`（`GameManager.cs:1157`），`Restart`/场景加载。
- **结论**：设置到对局的跳转正常，AI 在进入对局时初始化。[已验证]

## 场景 3：不同 AI 难度

- **操作**：在难度行连续点击右箭头 6 次（默认“初学者” → “专家（三级棋士）”）；开始对局。
- **观察**：设置页显示“专家（三级棋士）”；对局右上角 AI 卡片显示“专家 / 三级棋士 / 1800 ELO”。难度说明面板列出四档人群：普通爱好者、县级、省级、国家/世界级。
- **截图**：`screen-12-difficulty-level.png`、`s15-ingame-full.png`。
- **日志**：无难度日志；ELO 与 `AI_ELO_RATING[7]=1800` 一致。
- **代码**：`Constants.AI_CONFIGURATIONS`（`Constants.cs:1919`）、`Utils.GetAINameByLevel`（`Utils.cs:449`）。
- **结论**：13 档难度在 UI 与代码中一致；档 7 = 专家 = 1800。[已验证]

## 场景 4：不同游戏设置

- **操作**：切换执子颜色为黑方；查看读秒（无时间限制）、初始局面（飞相局）、棋子类型（工艺树脂）、对局环境（起居室）。
- **观察**：右侧说明与预览随选项变化；设置被记住（重启后仍为黑方/专家）。
- **截图**：`s14-reenter-setup.png`、`screen-11-color-check.png`、`screen-10-difficulty-high.png`。
- **日志**：设置写入 ES3（`GlobalVariable.InitializeES3Settings`）。
- **代码**：`GameManager` 设置项读取、`GlobalVariable.AILevel`。
- **结论**：设置项完整且持久化。[已验证]

## 场景 5：正常走棋

- **操作**：选中黑方 a6 卒（点击棋子下半部），出现“黑 卒”提示与合法点；点击前进点 a5。
- **观察**：棋子移动，左下出现记谱“1 卒9进1”。
- **截图**：`s16-select-piece.png`、`s17-select-piece2.png`、`s18-after-my-move.png`。
- **日志**：无错误。
- **代码**：`ChessBoard.MovePiece`、`ChessBoard.Moves.Add`、`Utils.GetNotationByMove`。
- **结论**：点击选中 + 目标点走子可用；记谱即时生成。[已验证]

## 场景 6：AI 思考过程

- **操作**：完成黑方走子后等待 AI 回应。
- **观察**：AI（红方）数秒内走子；右侧出现两条候选记谱“1 兵三进一 / 2 车九进一”；`pikafish.exe` 两个进程常驻（父子关系见报告 11）。
- **截图**：`s19-ai-thinking.png`、`s19-right-panel.png`。
- **日志**：无引擎错误；进程命令行指向 `StreamingAssets\AI\PikaFish\pikafish.exe`。
- **代码**：`MakeNextMoveByAI`（`GameManager.cs:3588`）、`ProcessManager.GetNextMove`（`ProcessManager.cs:99`）。
- **结论**：AI 为本地 UCI 引擎；对局引擎与分析引擎双进程；UI 会展示候选着法。[已验证]

## 场景 7：提示功能

- **操作**：进入“残局挑战”→ 开始第 1 关 → 点击右下角灯泡按钮（多次）；查看暂停菜单。
- **观察**：
  - 残局入口文案明确：“每一关都会为你提供一次着法推荐的机会，并可积累至后续关卡，最多 9 次”；界面显示“推荐着法次数 1”。
  - 残局对局中右下角存在灯泡按钮；暂停菜单含继续/认输/悔棋/跳过关卡/重新开始/返回主界面。
  - 自动化点击灯泡未观察到箭头出现（可能因控件位于窗口右边缘、点击区域被裁切）。
- **截图**：`s41-endgame-list.png`、`s42-endgame-ingame.png`、`s43/44/45-endgame-hint*.png`、`s46-endgame-pause.png`、`s47-hint-fast.png`、`s48-hint-hover.png`。
- **日志**：无提示相关错误。
- **代码**：`RequestEndgameMoveAnalysis`（`GameManager.cs:5325`）、`ShowRecommendedMoveArrow`（`GameManager.cs:4260`）、`EndgameHintMoveButton`。
- **结论**：提示功能的入口、次数规则、UI 位置与代码路径均已确认；箭头显示未能在自动化下复现，标为“部分验证”。[有证据支持]

## 场景 8：撤销功能

- **操作**：ESC 打开暂停菜单 → 点击“悔棋”。
- **观察**：棋盘回到双方走子前（黑卒与红方应手同时回退），右侧候选列表清空。
- **截图**：`s20-esc-menu.png`、`s21-after-undo.png`。
- **日志**：无错误。
- **代码**：`UndoMove`（`GameManager.cs:2519`）、`GetUndoMoves()`（单机撤 2 步，`GameManager.cs:2507`）。
- **结论**：撤销按 2 步（一回合）执行，与代码一致。[已验证]

## 场景 9：棋局结束

- **操作**：ESC → “认输”。
- **观察**：弹出终局面板：“人机练习赛 / 红方胜 / 专家 / 黑方在第 1 回合认输”；显示段位分 300、称号“十四级棋士”。
- **截图**：`s22-after-resign.png`。
- **日志**：无错误。
- **代码**：`PostGameActions`、`CalculateEloScore`、`GameOverEloScore`。
- **结论**：认输触发正常终局与段位结算。[已验证]

## 场景 10：棋谱回放

- **操作**：主界面“探析”→“游戏记录”→ 选择 108 步的友谊赛。
- **观察**：进入复盘棋盘；右侧“复盘/图表/详细信息”三页；着法列表带彩色圆点（评分标签）；底部有前进/后退/首尾等导航按钮。
- **截图**：`s26-game-records.png`、`s27-review-open.png`。
- **日志**：无错误。
- **代码**：`CareerModeManager.ReviewMatch`（`CareerModeManager.cs:888`）、`TitleManager.LoadReviewMode`（`TitleManager.cs:779`）、`MoveTo/NextMove/PrevMove`。
- **结论**：回放可用，着法列表与评分颜色对应 `ReportMoveType`。[已验证]

## 场景 11：棋局分析

- **操作**：在复盘页切换“图表”和“详细信息”。
- **观察**：
  - 图表页：胜率图/分差切换；堆叠面积图显示红方胜率、和棋概率、黑方胜率，横轴为步数。
  - 详细信息页：按红/黑分别统计“最佳着法、佳着、开局库、失算之着、错误之着、严重失误、错失良机”数量；显示双方棋手、赛事、结果、时长、日期。
- **截图**：`s28-review-chart.png`、`s29-review-details.png`。
- **日志**：无错误。
- **代码**：`GenerateGameReport`（`GameManager.cs:2748`）、`ReportMoveType`（`CCEnum.cs:265`）、`GraphAndChart` 数据绑定（`GameManager.cs:1496`）。
- **结论**：逐手评分标签与胜率曲线均有实机证据。[已验证]

## 场景 12：历史对局

- **操作**：探析 → 游戏记录。
- **观察**：统计卡（比赛数 2、最长连胜 1、段位分 300、执红 100%、游玩时长 7 小时 52 分、称号十级棋士、完成残局 34）；列表含“人机练习赛（1 步）”与“友谊赛（108 步）”，可收藏。
- **截图**：`s26-game-records.png`。
- **日志**：`MyGameHistory/` 目录。
- **代码**：`HomeManager.ReviewLastGame`（`HomeManager.cs:349`）、`GameRecord`。
- **结论**：历史对局列表、统计与收藏均可用。[已验证]

---

## 说明

用户于 2026-11-19 要求不再启动游戏，后续以安装目录静态逆向为准。以上为停止前已完成的实机记录；提示箭头的动态复现未继续。

## 完成度

| # | 场景 | 状态 |
|---:|---|---|
| 1 | 启动/主菜单 | 已验证 |
| 2 | 新建对局 | 已验证 |
| 3 | 不同难度 | 已验证 |
| 4 | 不同设置 | 已验证 |
| 5 | 正常走棋 | 已验证 |
| 6 | AI 思考 | 已验证 |
| 7 | 提示 | 部分验证（入口/次数/代码确认；箭头未复现） |
| 8 | 撤销 | 已验证 |
| 9 | 棋局结束 | 已验证 |
| 10 | 棋谱回放 | 已验证 |
| 11 | 棋局分析 | 已验证 |
| 12 | 历史对局 | 已验证 |

## 日志摘录

```text
Mono path[0] = 'D:/SteamLibrary/steamapps/common/Just Xiangqi/JustXiangqi_Data/Managed'
Initialize engine version: 2020.3.15f2 (6cf78cb77498)
Initalizing Steam Client API
Local User: 984406142:0
```

对局中的引擎进程：

```text
JustXiangqi.exe  PID 20740
pikafish.exe     PID 61116  Parent 20740
pikafish.exe     PID 8600   Parent 20740
CommandLine: "...\StreamingAssets\AI\PikaFish\pikafish.exe"
```
