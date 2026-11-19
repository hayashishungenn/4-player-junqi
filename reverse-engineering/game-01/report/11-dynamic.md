# 报告 11：动态运行观察（game-01）

## 1. 观察环境

- Windows 11 x64，Steam 在线，游戏由 `D:\SteamLibrary\steamapps\common\Just Xiangqi\JustXiangqi.exe` 启动。
- 启动方式：直接运行官方 exe；未使用调试器、未注入、未改包。
- 截图：`evidence/game-01/*.png`；日志：`%LocalLow%\Studio Amateur\JustXiangqi\Player.log`。
- 完整逐场景记录：`runtime-observations/scenarios.md`。

## 2. 任务书 12 个场景的完成度

| # | 场景 | 状态 | 证据 |
|---:|---|---|---|
| 1 | 启动和主菜单 | 已验证 | `s40-mainmenu.png`；`Player.log` |
| 2 | 新建对局 | 已验证 | `s14`、`s15`；开始后进入棋盘 |
| 3 | 不同 AI 难度 | 已验证 | `screen-12`；对局 ELO 1800 |
| 4 | 不同游戏设置 | 已验证 | 颜色/读秒/局面/材质/环境 |
| 5 | 正常走棋 | 已验证 | `s17` 选子、`s18` 走子与记谱 |
| 6 | AI 思考过程 | 已验证 | `s19`；两个 `pikafish.exe` |
| 7 | 提示功能 | 部分验证 | 残局入口/次数/灯泡/代码均有；箭头未复现 |
| 8 | 撤销功能 | 已验证 | `s20` 菜单、`s21` 回退 |
| 9 | 棋局结束 | 已验证 | `s22` 认输结算 |
| 10 | 棋谱回放 | 已验证 | `s26` 列表、`s27` 复盘 |
| 11 | 棋局分析 | 已验证 | `s28` 胜率图、`s29` 评分统计 |
| 12 | 历史对局 | 已验证 | `s26` 统计与列表 |

## 3. 启动与场景切换

`Player.log` 关键行：

```text
Mono path[0] = 'D:/SteamLibrary/steamapps/common/Just Xiangqi/JustXiangqi_Data/Managed'
Initialize engine version: 2020.3.15f2 (6cf78dc9ae1c)
Initalizing Steam Client API
Local User: 984406142:0
Failed to load the Steam App List: State = ProtocolError, ... 404
Setting up 16 worker threads for Enlighten.
```

- `Failed to load the Steam App List` 为 404，非致命，随后正常进入主菜单。
- 场景切换出现 `Unloading N unused Assets`，与 Unity 场景加载一致。
- 日志中无 AI 网络请求、无异常堆栈。

## 4. 对局与引擎进程

进入对局后：

```text
JustXiangqi.exe  PID 20740
pikafish.exe     PID 61116  ParentProcessId 20740
pikafish.exe     PID 8600   ParentProcessId 20740
CommandLine: "D:/.../StreamingAssets\AI\PikaFish\pikafish.exe"
```

- 两个引擎进程与 `InitializeGameAI()` 创建 `cchessAIDict[Pikafish_Process]` 和 `analysisAIProcess` 对应（`GameManager.cs:1163/1166`）。
- 引擎路径在游戏目录内，父进程为游戏，**排除远程 AI**。
- 对局 AI 卡片显示“专家 / 三级棋士 / 1800 ELO”，与 `AI_ELO_RATING[7]=1800` 一致。

## 5. 走子与 AI 回应

- 选中黑方 a6 卒时出现“黑 卒”提示与合法点；落子 a5 后左下记谱“1 卒9进1”。
- AI（红方）数秒内应手；右侧出现候选记谱“1 兵三进一 / 2 车九进一”。
- 说明：UI 会把引擎候选/PV 以记谱形式展示，属于分析/提示类信息。

## 6. 撤销与终局

- 暂停菜单点击“悔棋”：双方各退一步，棋盘回到走子前，候选列表清空。与 `GetUndoMoves()` 单机撤 2 步一致。
- 点击“认输”：弹出“人机练习赛 / 红方胜 / 专家 / 黑方在第 1 回合认输”，段位分 300、称号十四级棋士。

## 7. 复盘与历史

- “探析 → 游戏记录”显示统计（比赛数 2、最长连胜 1、段位分 300、执红 100%、时长 7h52m、称号十级棋士、残局 34）与两场比赛。
- 打开 108 步友谊赛进入复盘：着法列表带彩色评分点，底部有导航按钮。
- “图表”页显示红方胜率/和棋/黑方胜率的堆叠面积图；“详细信息”页按双方统计最佳着法、佳着、开局库、失算之着、错误之着、严重失误、错失良机数量。

## 8. 残局与提示

- 残局入口：推荐着法次数 1、已通过 30 关、全球排名 2055；文案说明“每关一次、可积累至后续关卡、最多 9 次”。
- 残局对局：AI“残局大师 / 棋协大师 / 2400 ELO”；右下角有灯泡按钮。
- 自动化点击灯泡未显示推荐箭头（控件位于窗口右缘，可能点击区域被裁切）；提示的代码路径与次数机制已确认，标为部分验证。

## 9. Pikafish 引擎实测（独立于游戏）

```text
$ printf 'uci\nquit\n' | pikafish.exe
id name Pikafish 2025-01-10
option name Threads type spin default 1 min 1 max 1024
option name Hash type spin default 16 min 1 max 33554432
option name MultiPV type spin default 1 min 1 max 128
option name Skill Level type spin default 20 min 0 max 20
option name UCI_LimitStrength type check default false
option name UCI_Elo type spin default 1280 min 1280 max 3133
option name Repetition Rule type combo default AsianRule ...
option name EvalFile type string default pikafish.nnue
uciok
```

- 证实引擎为 Pikafish 2025-01-10，支持 NNUE、MultiPV、Skill/Elo（游戏未使用后两者）。

## 10. 合规说明

- 未卸载、未清数据、未覆盖安装、未修改原始 exe/dll/资源。
- 未绕过 Steam 鉴权、未抓取账号数据、未分析付费内容。
- 仅观察正常启动、对局、复盘与残局入口。
