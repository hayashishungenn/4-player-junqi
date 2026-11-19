# 四国军棋 AI 陪练与复盘系统

日期：2026-11-19。主工程固定为 MIT 许可的 `BitByBitG/siguo-junqi`（v2.12.2），在其现有架构上做最小必要修改。本目录为外层档案仓库；主工程代码位于 `workspace/siguo-junqi`（独立 git，已排除大文件与依赖目录）。

## 实现内容

| 阶段 | 内容 | 状态 |
|---|---|---|
| 环境 / P0 基线 | 定位 Just Xiangqi（AppID 2248180），克隆四仓库，跑通主工程测试与启动 | 完成 |
| 逆向 P0-R | Just Xiangqi 包结构、AI 三路、难度、棋谱、复盘、UI 动态验证（12 场景中 11 项实机） | 完成 |
| 阶段二 | 四仓库逐行源码审查（含许可证与法律边界）、技术整合方案 | 完成 |
| P1 四国暗棋 | 暗棋 / 对家结盟 / 自动与手动布阵 / 四方轮流 / 胜负判定（主工程既有） | 已具备 |
| P2 AI 增强 | 暗棋采样、弧一致性推断、联盟搜索、工兵/军旗战术（既有）+ 新增 5 档难度模块 | 完成增强 |
| P3 逐手评分 | 统一暗棋视角与采样条件的最佳着法、候选评分、分差、错误等级、深度、采样数、风险解释 | 新增完成 |
| P4 完整复盘 | 基于现有 replay 的评分曲线、关键失误、各档统计、整局报告、明棋/暗棋视角分离 | 新增完成 |
| P5 自我对弈 | GNN 策略价值网、自我对弈 CLI、四方/联盟模式、CUDA 参数（既有）；本地环境实测可用 | 代码具备，训练阻塞 |
| P6 界面/API | 服务端分析 API、复盘弹窗的分析按钮/分差曲线/失误列表、当前步评分 | 新增完成 |

## 关键文件

逆向与档案：
- `reverse-engineering/README.md`、`reverse-engineering/DELIVERABLES.md`、`reverse-engineering/game-01/report/`（12 份）、`reverse-engineering/comparison/recommendations.md`
- `research/repo-analysis/`：四份源码分析报告 + `integration-plan.md`
- `research/ai-algorithm.md`：AI 算法说明；`research/evaluation-report.md`：测试与棋力评测
- `research/p0-baseline.md`：基线与既有失败测试

主工程新增/修改（`workspace/siguo-junqi`）：
- `bots/engine/analysis.js`：逐手评分引擎（P3）
- `bots/engine/replay-analysis.js`：复盘分析器（P4）
- `bots/engine/difficulty.js`：多档难度（P2）
- `scripts/analyze-replay.js`：复盘分析 CLI
- `server/server.js`：新增 `POST /api/rooms/:code/analysis`（P6）
- `public/app.js`：复盘弹窗分析 UI（P6）
- `test/analysis.test.js`、`test/replay-analysis.test.js`、`test/difficulty.test.js`；`test/features-240.test.js` 追加集成断言

## 验证结果

- 主工程测试：`npm test` → **113 项 / 109 通过 / 4 失败**，4 项均为 P0 基线既有失败，无新增回归。
- 新模块测试：逐手评分 4 项、复盘 5 项、难度 3 项、加密通道 API 集成断言 1 项，全部通过。
- 服务器启动：`PORT=3199 node server/server.js` → HTTP 200（47,340 bytes）；新 API 经加密客户端验证返回 200 与正确结构。
- 复盘 CLI 端到端：`node scripts/analyze-replay.js tmp-replay.json --budget-ms 400 --mode ffa` 成功输出报告与整局摘要。
- 棋力 smoke benchmark：`BOT_A_MS=150 BOT_B_MS=800 BOT_GAMES=4` → A 2 胜 / B 1 胜 / 1 未决（4 局样本，不具统计显著性，详见评测报告）。
- 本地自我对弈环境：`self_play_env.mjs` 的 `reset(mode=alliance)` / `state` / `board` 正常。

## Commit Hash

外层档案仓库：
- `160bfca` 阶段二：四仓库深度源码分析报告与技术整合方案
- `863cc2f` 修订 P0 基线：UnityPlayer 分析重试被中断
- （本 README 与评测/算法文档随最终文档提交）

主工程仓库 `workspace/siguo-junqi`：
- `5ac3e23` P3 逐手评分引擎
- `72ca8c5` P4 复盘分析器
- `933cad6` P2 多档难度
- `e7952cb` P6 界面与 API

## 未完成事项

1. P5 PyTorch 训练未执行：Python 3.14.3 由 uv 管理且 pip 代理不可达（`ProxyError WinError 10061`），无法安装 torch；无模型权重产出。
2. 4 个基线既有测试失败未修复（环境依赖/既有缺陷，未改断言）。
3. 棋力评测仅 4 局 smoke，未做 100+ 局固定布局统计评测。
4. 逆向阶段 `UnityPlayer.dll` 深度分析重试被中断，未完成；提示箭头显示等少量场景未实机复现。

## 风险

- 两个参考仓库（4nationwar、DL-Military-chess-AI）无 LICENSE，仅参考思路未复制代码；MIT 的 open_junqi 同样只吸收思路。
- 所有引擎分均为**未校准启发式分**，不是胜率、不换算百分比；错误等级阈值为经验值，需棋力数据校准。
- 分析时严格使用暗棋视角；真实隐藏兵种只出现在赛后明棋 `truth` 字段，不进入 `analysis` 字段。新分析 API 为同步计算，已限制预算与步数。
- 棋谱与账号数据仅存本地临时目录用于验证，未提交；未推送远程、未切换分支、未重写历史。
