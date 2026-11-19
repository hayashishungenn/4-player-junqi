# 交付物对照清单

## 1. 任务书要求的每款游戏 12 项

| # | 交付物 | game-01 | game-02 |
|---:|---|---|---|
| 1 | APK 包结构报告 | `game-01/report/01-package-structure.md`（Windows Unity 包结构，APK 项不适用） | `game-02/report/01-package-structure.md`（主体缺失，基于日志恢复） |
| 2 | 技术架构报告 | `02-technical-architecture.md` | `02-technical-architecture.md` |
| 3 | 关键类与方法清单 | `03-key-classes.md` + `static-analysis/class-index.md` | `03-key-classes.md`（仅可确认类型） |
| 4 | AI 决策调用链 | `04-ai-decision-chain.md` | `04-ai-decision-chain.md` |
| 5 | 搜索算法分析 | `05-search-algorithm.md` | `05-search-algorithm.md` |
| 6 | 局面估值分析 | `06-evaluation.md` | `06-evaluation.md` |
| 7 | AI 难度机制 | `07-difficulty.md` | `07-difficulty.md` |
| 8 | 棋谱数据结构 | `08-record-format.md` | `08-record-format.md` |
| 9 | 复盘功能分析 | `09-review.md` | `09-review.md` |
| 10 | UI 功能截图 | `10-ui-screenshots.md` + `evidence/game-01/*.png` | `10-ui-screenshots.md`（无截图，说明原因） |
| 11 | 动态运行观察 | `11-dynamic.md` | `11-dynamic.md`（历史日志） |
| 12 | 已证实/未证实清单 | `12-verified-unverified.md` | `12-verified-unverified.md` |

## 2. 两款合并交付物

| 任务书名称 | 文件 |
|---|---|
| 双游戏技术架构对比报告 | `comparison/architecture.md` |
| AI 棋力与搜索机制研究报告 | `comparison/ai-analysis.md` |
| 棋类陪练功能分析报告 | `comparison/training-design.md` |
| 四国军棋可借鉴技术方案 | `comparison/recommendations.md` |
| 功能对照表 | `comparison/feature-matrix.md` |

## 3. 前置与环境

| 项 | 文件 |
|---|---|
| 目录结构 | `README.md`、各级目录 |
| 环境/工具核查 | `game-01/inventory/environment-check.md` |
| 包身份与哈希 | `game-01/inventory/package-manifest.md`、`game-02/inventory/package-manifest.md`、`inventory/hashes.txt` |
| 资源清单 | `game-01/inventory/assets.md` |
| 原始包保护说明 | `game-01/original/README.md`、`game-02/original/README.md` |
| 动态证据索引 | `evidence/README.md` |

## 4. 验收标准逐项核对

| 验收项 | 状态 | 说明 |
|---|---|---|
| 两款游戏均完成独立包分析 | 部分完成 | game-01 完整；game-02 主体已卸载，仅日志/存档级分析，已标注未知 |
| 主要技术框架已确认 | 是 | Unity 2020.3.15f2 / 2021.3.29f1，Mono |
| AI 相关代码路径已追踪 | game-01 是；game-02 协议级 | Pikafish UCI / KataGo GTP |
| 动态行为已观察 | game-01 是；game-02 历史日志 | 12 场景完成度见各自报告 11 |
| 本地/远程 AI 已区分 | 是 | 两者均本地 |
| 功能对照表已建立 | 是 | `comparison/feature-matrix.md` |
| 报告有实际证据 | 是 | 代码行号、哈希、截图、进程、日志 |
| 未确认内容如实标注 | 是 | 统一使用 [已验证]/[有证据支持]/[推测]/[未知] |
| 原始安装包未被修改 | 是 | 只读与哈希 |

## 5. 已知缺口

1. **无 APK**：任务书假设的两款 Android 安装包在本机不存在；对象为 Steam Windows 构建。所有 APK 专项检查项不适用，未伪造结果。
2. **game-02 主体缺失**：无法反编译 C#、无法查看难度配置与 UI；相关结论为未知。
3. **REA 原生分析不可用**：无 Ghidra/IDA/Hopper/JADX，且本会话无 REA MCP；.NET 分析改用 ILSpy。
4. **game-01 动态场景**：12 项中 5/7/8/9/10/11/12 未实机触发，仅代码级还原。
5. **未做二进制相似度比对**：两款游戏的“共用 UI 框架”只能标为推测。

## 6. 下一步（需授权/补充材料）

- 若需完整 game-02 静态分析：重新安装《Just Go》或提供安装目录副本。
- 若需 game-01 对局内截图：允许自动化操作棋子，或人工按清单截图。
- 若需更强原生分析：安装 Ghidra 12.x 并设置 `GHIDRA_INSTALL_DIR`。
