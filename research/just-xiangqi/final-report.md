# Just Xiangqi 逆向最终报告

## 1. 结论摘要

1. 《Just Xiangqi》是 Unity 2020.3.15f2 + Mono 的 Windows 商业游戏，不是 Android APK，也没有 DEX/JNI。
2. AI 为三路混合：NativeAI（浅层 Alpha-Beta）、SharpElephantEyes（C# ElephantEyes：PVS/静态搜索/置换表/空着裁剪/12,081 条开局库）、Pikafish（UCI + NNUE）。
3. 对弈与分析各起一个本地 `pikafish.exe`；AI 完全本地，无远程决策接口。
4. 难度 13 档（ELO 100–2800）+ 生涯 16 档；用“引擎类型 + 深度 + MultiPV 前 N 随机 + 开局库”，不使用 Skill/Elo 限制。
5. 复盘：逐手 1/2.5/5 秒重算，标签 Best/Good/Book/Inaccuracy/Mistake/Blunder/Missed，动态阈值，胜率曲线与双方统计。
6. 棋谱：内部 `.game`（Odin JSON）+ PGN 导出（GB2312）；存档 ES3 AES。

## 2. 证据等级

| 结论 | 等级 | 证据 |
|---|---|---|
| Unity 2020.3.15f2 + Mono | 已验证 | `Player.log`、目录 |
| 三路 AI 与调用链 | 已验证 | `GameManager.cs:1157/3588`、`NativeAI.cs`、`Search.cs`、`ProcessManager.cs` |
| 两个本地 pikafish 进程 | 已验证 | 运行时进程树与命令行 |
| Pikafish 为 Stockfish 系 + NNUE | 已验证（REA） | `rea analyze/search`，`TranspositionTable`/`Eval::NNUE::Network` 符号 |
| 难度 13 档与随机采样 | 已验证 | `Constants.cs`、`GameManager.cs:3658`、实机 ELO 1800 |
| 生涯 16 档 | 有证据支持 | `CAREER_MODE_AI_CONFIGURATIONS` 解析 |
| 复盘标签/阈值 | 已验证 | `GenerateGameReport`、实机统计页 |
| 提示箭头显示 | 部分验证 | 入口/次数/按钮/代码确认；自动化点击未复现 |
| 在线/热座/生涯内部界面 | 未覆盖 | 仅入口 |
| NNUE 训练细节 | 未知 | 无元数据 |
| UnityPlayer 深分析 | 未完成 | 28 MB，Ghidra 330s 超时；已提高超时重试 |

## 3. 可迁移 / 不可迁移

### 可迁移
- 引擎进程化与文本协议、分析与对弈分离。
- 13 档难度 + 同档多配置 + 整局固定。
- MultiPV 候选随机 + 安全阈值（防送子）。
- 逐手评分标签 + 动态阈值 + 置信度。
- 提示次数成本、防重复扣费。
- 内部棋谱 + 标准导出、复盘三视图。
- 残局题库 + 训练反馈 + 生涯辅助技能闭环。

### 不可迁移
- 中国象棋规则、棋盘、走法生成。
- Pikafish/NNUE 模型与象棋估值。
- 完全信息 Alpha-Beta 直接用于四国暗棋。
- 商业代码、素材、音效、商标、私有接口。

## 4. 对四国军棋的具体影响

1. 规则引擎必须自研，统一服务端/搜索/训练三处规则来源。
2. 评分必须基于“走子前信息集”的采样，不能用赛后真实棋子；增加 `confidence`。
3. 联盟价值用“本队胜率/期望”，不是单人胜负；队友意图作为联合动作。
4. 低难度用预算 + 候选采样，并强制过滤送军旗/送大子。
5. 分析与对弈分离；复盘不阻塞对局。

## 5. 证据索引

- `reverse-engineering/game-01/report/01..12`
- `reverse-engineering/game-01/runtime-observations/scenarios.md`
- `reverse-engineering/evidence/game-01/`（41 张截图 + REA 原始输出）
- `reverse-engineering/game-01/static-analysis/class-index.md`、`full-class-index.md`

## 6. 后续补齐

- 提高 `REA_GHIDRA_STARTUP_TIMEOUT_MS` 完成 `UnityPlayer.dll` 分析。
- 如需提示箭头实机证据，需人工在对局中点击并录屏。
- 在线/热座/生涯内部界面可在后续补充，不影响核心陪练设计。
