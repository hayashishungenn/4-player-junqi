# 交付物对照清单（单款：Just Xiangqi）

## 0. 范围

用户 2026-11-19 指示：只分析象棋，《Just Go》未购买、不再安装。以下验收仅针对《Just Xiangqi》。

## 1. 每款游戏 12 项（game-01）

| # | 交付物 | 文件 | 状态 |
|---:|---|---|---|
| 1 | 包结构报告 | `game-01/report/01-package-structure.md` | 完成（Windows Unity 包；APK 项不适用） |
| 2 | 技术架构报告 | `game-01/report/02-technical-architecture.md` | 完成 |
| 3 | 关键类与方法清单 | `game-01/report/03-key-classes.md` + `static-analysis/class-index.md` | 完成 |
| 4 | AI 决策调用链 | `game-01/report/04-ai-decision-chain.md` | 完成 |
| 5 | 搜索算法分析 | `game-01/report/05-search-algorithm.md` | 完成 |
| 6 | 局面估值分析 | `game-01/report/06-evaluation.md` | 完成 |
| 7 | AI 难度机制 | `game-01/report/07-difficulty.md` | 完成 |
| 8 | 棋谱数据结构 | `game-01/report/08-record-format.md` | 完成 |
| 9 | 复盘功能分析 | `game-01/report/09-review.md` | 完成 |
| 10 | UI 功能截图 | `game-01/report/10-ui-screenshots.md` + `evidence/game-01/*.png` | 完成（29 张） |
| 11 | 动态运行观察 | `game-01/report/11-dynamic.md` + `runtime-observations/scenarios.md` | 完成（12 场景，提示部分验证） |
| 12 | 已证实/未证实清单 | `game-01/report/12-verified-unverified.md` | 完成 |

## 2. 合并交付物

原任务书要求双游戏对比；围棋排除后，保留象棋结论，对比文件降级为背景参考：

| 文件 | 处理 |
|---|---|
| `comparison/architecture.md` | 象棋架构为主；game-02 仅作背景，标注未购买 |
| `comparison/ai-analysis.md` | 象棋三引擎为主；game-02 段落标注背景 |
| `comparison/feature-matrix.md` | game-02 列改为“未购买（排除）” |
| `comparison/training-design.md` | 以象棋陪练设计为主 |
| `comparison/recommendations.md` | 四国军棋可借鉴方案（有效） |

## 3. 前置与环境

| 项 | 文件 |
|---|---|
| 目录结构 | `README.md` |
| 环境/工具核查 | `game-01/inventory/environment-check.md` |
| 包身份与哈希 | `game-01/inventory/package-manifest.md`、`hashes.txt` |
| 资源清单 | `game-01/inventory/assets.md` |
| 原始包保护 | `game-01/original/README.md` |
| 动态证据索引 | `evidence/README.md` |

## 4. 验收核对

| 验收项 | 状态 | 说明 |
|---|---|---|
| 完成独立包分析 | 是（象棋） | 身份、哈希、结构、程序集、资源 |
| 主要技术框架确认 | 是 | Unity 2020.3.15f2 + Mono |
| AI 代码路径追踪 | 是 | 三路引擎与调用链 |
| 动态行为观察 | 是（11/12） | 提示箭头未复现，其余实机验证 |
| 本地/远程 AI 区分 | 是 | 两个本地 pikafish 进程 |
| 功能对照表 | 是 | 见 feature-matrix |
| 报告有实际证据 | 是 | 代码行号、哈希、截图、进程、日志 |
| 未确认内容标注 | 是 | 四档标注 |
| 原始包未修改 | 是 | 只读与哈希 |

## 5. 已知缺口

1. **无 APK**：APK 专项检查项不适用，未伪造结果。
2. **REA 主线受限**：无 Ghidra/IDA/Hopper/JADX，且无 REA MCP；.NET 分析用 ILSpy，未冒充 REA Evidence。
3. **提示箭头**：入口/次数/按钮/代码确认，但自动化点击未触发箭头显示。
4. **未覆盖界面**：在线比赛、热座、生涯内部、自由摆谱、上传棋谱。
5. **二进制相似度**：未做两款游戏比对（围棋已排除）。
