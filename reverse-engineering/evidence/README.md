# Evidence 索引

本目录保存可复核的动态证据与工具输出。

## game-01（Just Xiangqi）

| 文件 | 内容 |
|---|---|
| `screen-01-mainmenu.png` | 首次启动，桌面+主菜单 |
| `screen-02-mainmenu-window.png` | 主菜单窗口（游玩/探析/其他） |
| `screen-03-after-click.png` | 人机对战设置页 |
| `screen-04..09-*.png` | 交互与 DPI 坐标校准过程 |
| `screen-10-difficulty-high.png` | 设置页全貌 |
| `screen-11-color-check.png` | 选择黑方 |
| `screen-12-difficulty-level.png` | 难度“专家（三级棋士）”与分档说明 |
| `screen-13-ingame.png` | 对局中：玩家黑方、AI 红方、ELO 1800 |

日志与进程证据见 `game-01/report/11-dynamic.md`：

- `Player.log`：Unity 2020.3.15f2、Mono、Steam 初始化。
- `Win32_Process`：两个 `pikafish.exe`，父进程为 `JustXiangqi.exe`，命令行指向 `StreamingAssets\AI\PikaFish\pikafish.exe`。

## game-02（Just Go）

无截图（主体已卸载）。动态证据为应用自产日志：

- `D:\SteamLibrary\steamapps\common\Just Go\gtp_logs\*.log`（4 个）
- `%LocalLow%\Studio Amateur\JustGo\Player.log`
- `RecentGames/match_1768530733.sav`、`RecentSGFs/sgf_1768530733.sgf`

## REA 工具输出

```text
$ rea --version
6.9.0

$ rea doctor
healthy: false
environment_healthy: false
node: ok 26.13.1
host: ok win32 x64
ghidra: missing_analysis_engine (GHIDRA_INSTALL_DIR not set)
hopper: missing_analysis_engine
ida-registration: missing_analysis_engine
jadx: missing_analysis_engine (REA_JADX_MCP_JAR not set)
kuna-installation: missing_analysis_engine

$ rea capabilities
open: false
evidence_records: 0
providers: native-macos (unsupported_host) ...

$ rea analyze ".../Assembly-CSharp.dll"
error: Analysis failed
code: provider_unavailable
message: "The selected analysis provider is unavailable."
candidate_ids[4]: ghidra,hopper,ida,kuna
```

本会话工具清单中没有 `mcp__rea__*` 工具，REA 未以 MCP 方式连接。

## Pikafish UCI 握手

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
option name Draw Rule type combo default None ...
option name EvalFile type string default pikafish.nnue
uciok
```

## 说明

- 截图与日志均来自本机正常使用，未做内容篡改。
- 未保存任何账号凭据、密钥或付费内容。
