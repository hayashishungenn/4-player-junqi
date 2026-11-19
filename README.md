# 四国军棋项目

当前阶段：**P0-R 逆向分析（《Just Xiangqi》单款）已完成**。

## 范围

用户 2026-11-19 确认：只分析象棋；《Just Go》未购买，不再安装。game-02 档案仅保留背景，不计入交付。

## 逆向档案

- 总览：[reverse-engineering/README.md](reverse-engineering/README.md)
- 交付清单与验收：[reverse-engineering/DELIVERABLES.md](reverse-engineering/DELIVERABLES.md)
- 象棋 12 份报告：[reverse-engineering/game-01/report/](reverse-engineering/game-01/report/)
- 12 场景动态记录：[scenarios.md](reverse-engineering/game-01/runtime-observations/scenarios.md)
- 截图证据：[evidence/game-01/](reverse-engineering/evidence/game-01/)
- 四国军棋可借鉴方案：[recommendations.md](reverse-engineering/comparison/recommendations.md)

## 核心结论

1. 本地无棋弈无限 APK；对象是 Steam Windows Unity 2020.3.15f2 + Mono 构建。
2. AI 三路：NativeAI（Alpha-Beta）+ ElephantEyes（C#，PVS/置换表/12,081 条开局库）+ Pikafish（UCI + NNUE）。
3. 难度 13 档（ELO 100–2800）：引擎类型 + 深度 + MultiPV 随机采样 + 开局库；不使用 Skill/Elo 限制。
4. 进入对局创建两个本地 `pikafish.exe`（对弈 + 分析），AI 完全本地。
5. 复盘：逐手 1/2.5/5 秒重算，标签 Best/Good/Book/Inaccuracy/Mistake/Blunder/Missed，动态阈值，胜率曲线与双方统计。
6. 棋谱：内部 `.game`（Odin JSON）+ PGN 导出（GB2312）；存档 ES3 AES。

## 动态验证

12 个场景中 11 个已实机验证（启动、设置、难度、走子、AI、悔棋、终局、回放、图表、评分统计、历史）。提示功能的入口/次数/按钮/代码已确认，箭头显示未在自动化点击下复现。

## 下一步

按 [recommendations.md](reverse-engineering/comparison/recommendations.md) 先定义引擎协议与棋谱格式，再接入主工程搜索/GNN；证据不足前不改现有 AI 引擎。

## 已知缺口

- APK 专项检查不适用（无 APK）。
- REA 原生分析提供者未配置，本会话无 REA MCP；.NET 分析用 ILSpy。
- 提示箭头显示、在线/热座/生涯内部界面未实机覆盖。
