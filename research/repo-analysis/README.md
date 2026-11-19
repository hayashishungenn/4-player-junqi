# 四仓库源码分析（阶段二）

本目录收录四个 GitHub 项目的深度源码审查报告与技术整合方案，均基于实际读取源码（非仅 README）。

| 文件 | 仓库 | 许可证 | 报告要点 |
|---|---|---|---|
| `siguo-junqi.md` | BitByBitG/siguo-junqi（主工程） | MIT | 规则内核、暗棋采样/弧一致性/联盟搜索、BOT API、复盘、神经训练、P1–P6 现状映射 |
| `open_junqi.md` | jmctsh/open_junqi | MIT | 联盟 Alpha-Beta、Beam Search、9 项评分、历史模块；本地决策全知为反面教材 |
| `4nationwar.md` | Teaonly/4nationwar | 无 LICENSE | AlphaBetaSearch 实为 1-ply 贪心；BoardContext 位掩码约束传播可借鉴 |
| `DL-Military-chess-AI.md` | sg-first/DL-Military-chess-AI | 无 LICENSE | 概率矩阵 + 卷积估值；self-play/MCTS 未真正实现 |
| `integration-plan.md` | — | — | 许可证边界、横向结论、吸收思路、与象棋逆向结论对接、开发顺序、风险 |

法律约束：两个无 LICENSE 仓库**仅参考技术思路，不复制任何代码**；MIT 仓库本方案也只吸收思路。逐手评分分值为未校准启发式分，不冒充胜率。
