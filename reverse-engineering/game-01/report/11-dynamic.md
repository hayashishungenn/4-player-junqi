# 报告 11：动态运行观察（game-01）

## 1. 观察环境

- Windows 11 x64，Steam 在线，游戏由 `D:\SteamLibrary\steamapps\common\Just Xiangqi\JustXiangqi.exe` 启动。
- 启动方式：直接运行官方 exe（Steam 已在运行），未使用调试器、未注入、未改包。
- 截图：`evidence/game-01/*.png`；日志：`%LocalLow%\Studio Amateur\JustXiangqi\Player.log`。

## 2. 任务书 12 个场景的完成度

| # | 场景 | 状态 | 证据 |
|---:|---|---|---|
| 1 | 启动和主菜单 | 已观察 | `screen-01/02`；`Player.log` |
| 2 | 新建对局 | 已观察（设置页→开始） | `screen-03/10/13` |
| 3 | 不同 AI 难度 | 已观察（0→专家） | `screen-12`；配置表见报告 07 |
| 4 | 不同游戏设置 | 部分观察（颜色、难度、局面、材质、场景） | `screen-11/12` |
| 5 | 正常走棋 | **未执行**（需拖拽/点击棋子，未稳定自动化） | — |
| 6 | AI 思考过程 | 部分观察（进程创建、思考耗时逻辑） | 两个 `pikafish.exe`；`PlayAIMoveAnimation` |
| 7 | 提示功能 | **未实机触发**，代码路径已还原 | 报告 09 |
| 8 | 撤销功能 | **未实机触发**，代码路径已还原 | 报告 09 |
| 9 | 棋局结束 | **未执行** | — |
| 10 | 棋谱回放 | **未执行**，格式与入口已分析 | 报告 08/09 |
| 11 | 棋局分析 | **未执行**，复算流程已还原 | 报告 09 |
| 12 | 历史对局 | **未执行**，存档路径已确认 | `MyGameHistory/` |

结论：动态证据足以证明“启动—设置—进入对局—本地引擎拉起”这条主链，以及 AI 完全本地运行；对局内交互与复盘 UI 依赖静态代码证据，未用截图冒充。

## 3. 启动与场景切换

`Player.log` 关键行：

```text
Mono path[0] = 'D:/SteamLibrary/steamapps/common/Just Xiangqi/JustXiangqi_Data/Managed'
Initialize engine version: 2020.3.15f2 (6cf78cb77498)
Initalizing Steam Client API
Local User: 984406142:0
Initalizing Steam Input System
Failed to load the Steam App List: State = ProtocolError, ... 404
Setting up 16 worker threads for Enlighten.
```

- `Failed to load the Steam App List` 为 404，非致命，随后正常进入主菜单。
- 场景切换时出现 `Unloading N unused Assets`，与 Unity 场景加载一致。
- 日志中无 AI 网络请求、无异常堆栈。

## 4. 进入对局时的进程证据

在设置页选择“专家（三级棋士）”、执黑，点击“开始”，10 秒后：

```text
JustXiangqi.exe  PID 20740
pikafish.exe     PID 61116  ParentProcessId 20740
pikafish.exe     PID 8600   ParentProcessId 20740
CommandLine: "D:/.../StreamingAssets\AI\PikaFish\pikafish.exe"
```

- 两个引擎进程与 `InitializeGameAI()` 创建 `cchessAIDict[Pikafish_Process]` 和 `analysisAIProcess` 完全对应（`GameManager.cs:1163/1166`）。
- 引擎进程由游戏进程直接创建，路径位于游戏目录，**排除远程 AI**。
- 对局界面显示 AI 为“专家 三级棋士 ELO 1800”，与 `AI_ELO_RATING[7]=1800` 一致，交叉验证难度表。

## 5. Pikafish 引擎实测（独立于游戏）

直接向 `pikafish.exe` 发送 UCI 命令：

```text
$ printf 'uci\nquit\n' | ./pikafish.exe
id name Pikafish 2025-01-10
option name Threads type spin default 1 min 1 max 1024
option name Hash type spin default 16 min 1 max 33554432
option name MultiPV type spin default 1 min 1 max 128
option name Skill Level type spin default 20 min 0 max 20
option name UCI_LimitStrength type check default false
option name UCI_Elo type spin default 1280 min 1280 max 3133
option name Repetition Rule type combo default AsianRule var ...
option name EvalFile type string default pikafish.nnue
uciok
```

- 证实引擎为 Pikafish 2025-01-10，支持 NNUE、MultiPV、Skill/Elo 限制（但游戏未使用 Skill/Elo）。
- 与 `ProcessManager` 的解析逻辑（`info depth / cp / mate / pv / wdl`）一致。

## 6. 资源与状态观察

- `StreamingAssets/AI/PikaFish/` 与 `Classic/` 可读，未被加密或打包。
- 存档 `SaveFileOfficial.es3` 为 AES 加密；`CareerSaves/*.sav` 与 `Classic/*.game` 为明文 Odin JSON。
- 运行后 `Player.log`、`Player-prev.log` 正常滚动，无崩溃转储。

## 7. 未执行的操作（合规说明）

- 未卸载、未清数据、未覆盖安装、未修改原始 exe/dll/资源。
- 未绕过 Steam 鉴权、未抓取账号数据、未分析付费内容。
- 仅观察正常启动与本地对局入口。
