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
| `s14`–`s19` | 设置、开局、选子、走子、AI 回应 |
| `s20`–`s22` | 暂停菜单、悔棋、认输终局 |
| `s24`–`s29` | 主菜单、探析、游戏记录、复盘、胜率图、评分统计 |
| `s40`–`s48` | 重启主菜单、残局入口、残局对局、提示按钮、残局暂停 |

日志与进程证据见 `game-01/report/11-dynamic.md`：

- `Player.log`：Unity 2020.3.15f2、Mono、Steam 初始化。
- `Win32_Process`：两个 `pikafish.exe`，父进程为 `JustXiangqi.exe`，命令行指向 `StreamingAssets\AI\PikaFish\pikafish.exe`。

## game-02（Just Go，已排除）

用户确认未购买、不再安装。以下残留日志仅作背景，不计入交付：

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

### REA 发布面审计（可执行部分）

对三个关键 PE 产物执行 `rea audit-release-exposure`，均成功返回 Evidence：

| 产物 | evidence_id | 检查项 |
|---|---|---|
| `JustXiangqi.exe` | `ev_2457f011057401d8735469cdc6a68c764a89cb82bc78028363240e035e728d12` | 15 |
| `UnityPlayer.dll` | `ev_b5b0218263106822c8d112f75ef9301933fc7f8d20afeafdd61186518cc126eb` | 15 |
| `Assembly-CSharp.dll` | `ev_9e0391860752e94f30c3b176d1442b86d901044f54f29641116ff777968a4132` | 15 |

完整输出：`game-01/rea-audit-*.txt`。

关键发现：

- 三个产物均 `native.pdb_path: exposed`（severity low，confidence observed）。
- `JustXiangqi.exe` 泄漏 Unity 构建路径：`C:\buildslave\unity\build\artifacts\WindowsPlayer\Win64_VS2019_nondev_m_r\WindowsPlayer_Master_mono_x64.pdb`。
- `Assembly-CSharp.dll` 泄漏原始工程名：`C:\Unity\ChineseChess_Windows\Temp\Assembly-CSharp.pdb`。
- `native.debug_companions` 均为 `not_observed`（未随包附带 PDB）。
- `android.manifest` 为 `not_assessed`（非 APK，符合预期）。

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
