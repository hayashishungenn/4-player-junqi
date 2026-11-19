# P0 基线报告

日期：2026-11-19
执行环境：Windows 11 x64，Git Bash，Node v26.13.1，npm 11.20.0，Python 3.14.3，REA 6.9.0。

## 1. Just Xiangqi 定位（只读）

| 项 | 值 |
|---|---|
| 安装路径 | `D:\SteamLibrary\steamapps\common\Just Xiangqi` |
| AppID / BuildID | 2248180 / 17661943 |
| 大小 | 2,129,099,409 B，276 文件 |
| 技术栈 | Unity 2020.3.15f2 + Mono（非 IL2CPP） |
| 主程序 SHA-256 | `fdff6324…69ca8`（完整值见 `reverse-engineering/game-01/inventory/hashes.txt`） |
| AI 组件 | `StreamingAssets/AI/PikaFish/pikafish.exe` + `pikafish.nnue` |
| 原始文件 | 未修改，仅读取/哈希 |

安装清单由 `steamapps/appmanifest_2248180.acf` 与文件系统核对，未凭文件名猜测。

## 2. REA 环境

| 项 | 状态 |
|---|---|
| REA | 6.9.0 |
| Node | 26.13.1（满足 ≥26） |
| REA MCP | 未连接（会话无 `mcp__rea__*` 工具） |
| Ghidra | 已安装 12.2（`D:\tools\ghidra_12.2_PUBLIC`），`rea doctor` 为 healthy |
| JDK | Temurin 21（系统）+ Temurin 25.0.5（`D:\tools\jdk-25.0.5+8`，Ghidra 12.2 要求） |
| JADX | 未配置（无 APK，不影响本对象） |
| ADB / MuMu | ADB 37.0.1 正常；MuMu 可启动，但对象为 Windows 构建 |
| 已执行 | `rea analyze pikafish.exe` 成功（2,924 过程 / 1,740 字符串）；`rea search` 命中 NNUE/Stockfish/TranspositionTable；`UnityPlayer.dll` 28 MB 首次 330s 超时；提高超时的重试被中断，尚未完成 |
| 补充证据 | `reverse-engineering/evidence/game-01/rea-*.txt`、`rea-evidence-summary.md` |

## 3. 四个 GitHub 仓库

克隆目录：`workspace/`（已在根 `.gitignore` 排除，各自保留独立 `.git`）。

| 仓库 | 目录 | 分支 | Commit | 许可证 | 工作区 |
|---|---|---|---|---|---|
| BitByBitG/siguo-junqi | `workspace/siguo-junqi` | master | `f4b911aebc303a63ceeacd20890714c60203a13e` | MIT | clean |
| jmctsh/open_junqi | `workspace/open_junqi` | main | `c05c461ac41bdba3a8ce830e72b1884c48c4886b` | MIT | clean |
| Teaonly/4nationwar | `workspace/4nationwar` | master | `4517e5252368c29f8a2d430ef06cee533e9dc397` | 无 LICENSE 文件 | clean |
| sg-first/DL-Military-chess-AI | `workspace/DL-Military-chess-AI` | master | `84e26a0aae0d8902c48638ff9615e79446e1e1c8` | 无 LICENSE 文件 | clean |

### 3.1 主工程结构

- `package.json`：v2.12.2，ESM，Node ≥18；依赖 express/socket.io/quickjs-emscripten/marked/dompurify/katex。
- 服务入口：`server/server.js`（PORT 默认 3000；`SIGUO_DATA_DIR`、`SIGUO_HISTORY_DIR` 可覆盖）。
- BOT：`bots/engine/bot.js`（110 行）、`bots/engine/search.js`（385 行）、`bots/reference-bot.mjs`（950 行）、`bots/siguo-junqi-bot.mjs`（1008 行）。
- 规则：`RULES.md`、`BOT_API.md`。
- 神经网络：`neural-bot/neural_bot.py`（402 行）、`self_play.py`（209 行）、`self_play_env.mjs`（98 行）。
- 测试：`test/` 34 个文件。

### 3.2 主工程基线测试

执行：`npm ci` → `npm test`（`node --test --test-concurrency=1`）。

```text
tests 101
pass 97
fail 4
```

失败项（均可在单独重跑时复现）：

| 测试 | 现象 |
|---|---|
| `test/admin-chat2512.test.js:30` | `renderMutedUsers` 读取 undefined 的 `username` |
| `test/auto-draw.test.js:26` | `timeout room-state`（5.6s） |
| `test/features-233.test.js:20` | `false !== true`（第 75 行） |
| `test/features-245.test.js:10` | `undefined !== -100`（第 25 行） |

基线结论：主工程可运行，但存在 4 个既有失败测试；后续修改前先判定其是否为环境依赖或真实缺陷，不擅自改断言。

完整输出：`research/baseline/siguo-junqi-tests.log`。

### 3.3 启动验证

```text
PORT=3100 SIGUO_DATA_DIR=... SIGUO_HISTORY_DIR=... node server/server.js
→ 四国军棋已启动：http://localhost:3100
→ curl /  HTTP 200, 47,340 bytes
```

## 4. Python / 训练环境

- `python 3.14.3`；`torch` **未安装**（`ModuleNotFoundError`）。
- 主工程要求：`torch>=2.2`、`requests>=2.31`、`cryptography>=42`。
- GPU：NVIDIA RTX 5070 Ti Laptop；CUDA 版本待安装 PyTorch 后确认。
- P7 训练前需建立独立 venv 并安装 CUDA 版 PyTorch，不升级主工程 Node 依赖。

## 5. 参考工程结构（P2 输入）

- `open_junqi`：Python/PyQt6，`server/strategies/{search,scoring,behaviors}.py`、`game/history.py`、`docs/deep_search_scoring.md`。
- `4nationwar`：C++/Qt，`_ref/engine/boardcontext.*`、`gtree.*`、`desktop/aiagent.*`。
- `DL-Military-chess-AI`：Python，`value_net.py`、`train.py`、`mcts.py`、`simulate.py`。

## 6. P0 验收

| 项 | 状态 |
|---|---|
| Just Xiangqi 已定位 | 是 |
| REA 环境已检查并可用 | 是（Ghidra 12.2 + JDK 25；pikafish 已分析） |
| 四个仓库已获取并记录版本 | 是 |
| 主工程可启动 | 是（HTTP 200） |
| 基线报告 | 本文件 + 测试日志 |

## 7. 已知阻塞

- `UnityPlayer.dll` 体积大，Ghidra 默认 330s 超时；已提高超时重试，结果需单独确认。
- 主工程 4 个基线测试失败。
- PyTorch 未安装，P7 前需配置。
- BOT API 依赖账号/服务器，后续联调需本地启动服务并创建 BOT 账号。
