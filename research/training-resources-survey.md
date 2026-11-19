# 棋类 AI 训练全网资源调研与联盟训练方法借鉴

日期：2026-11-19
背景：在已有 `reference-projects.md`（通用评测参考）、`alphago-zero-methodology.md`、`alphago-family-study.md` 基础上，继续全网检索**棋类 AI 训练**相关资源，重点找与本项目四国军棋（隐藏信息 + 对家联盟 + 多人）训练直接相关的框架与方法。

## 检索方式与诚实声明
- `websearch` 工具返回 402（配额）、DuckDuckGo Lite 人机验证、Bing 返回 JS 干扰页 —— 均无法用。
- 改用平台官方 API：`gh` CLI 搜索 GitHub repos（10+ 关键词，含中文"四国军棋 人工智能"）、GitHub contents/tree API 读源码、HuggingFace/Kaggle API（前次已用）。
- Wikipedia AlphaGo 条目抓取成功（上一轮）。
- 已克隆 3 个项目到 `workspace/refs/`（被外层 .gitignore 排除，不入库）；RL-CCA 因 index-pack 错误克隆失败，改用 GitHub API 读其 README/源码树。

## 1. 检索到的相关项目（GitHub，实时 API）

| 项目 | Stars | 许可 | 与训练的相关性 |
|---|---:|---|---|
| `AnwarDebes/RL-CCA` (NEXUS) | 1 | **无 LICENSE** | **极高**：2-6 人中国跳棋，AlphaZero 训练循环 + Gumbel MCTS + per-player value + coalition-belief；`flagship_coalition_mcts/` 子项目专门解决多人结盟 |
| `grzhx/azul-alpha-zero` | 1 | 无 LICENSE | 高：C++20 + GPU 纯 self-play，Max-N 多人，历史对手冻结 |
| `joaoaapinho/quorizero` | 1 | Apache-2.0 | 高：JAX 全流程 GPU self-play，Gumbel AlphaZero + KataGo ResNet，560 迭代/192 万局/26.7 GPU 小时，晋级闸门 |
| `2023Heng/alphazero-style-board-games-framework` | 0 | NOASSERTION | 中：Python 3.11+ PyTorch self-play 框架，requirements 用 PyTorch CUDA wheel |
| `gustavecortal/pylos` | 1 | MIT | 中：小 Transformer + Gumbel AlphaZero self-play |
| `mykun123/Four-Nations-Chinese-Chess-` | 1 | — | **极高（领域）**：四人军棋网页游戏，FFA/Team Battle/Team Stratagem + AI 对手，与本项目同领域 |
| `Gawaa/Using-AlphaZero-to-Play-Chinese-Chess` | 1 | — | 高（领域）：AlphaXiangqi，把 AlphaGo Zero/AlphaZero 方法移植到中国象棋 |
| `shehio/engine-distillation` | 0 | — | 中：Stockfish 蒸馏 + self-play + MuZero 消融，含负面结果 |
| `bmboucher/wingspan`、`BY571/abalone-rl`、`RayKMAllen/gamesolver` | 0-2 | — | 低：棋盘游戏 self-play agent 参考 |

## 2. 重点方法：CD-MCTS（联盟分布 MCTS，来自 RL-CCA）

该项目明确解决「AlphaZero 为 2 人零和游戏设计，3-6 人时价值与对手模型都失效」——与本项目四国军棋（南北/东西结盟 + FFA）同构。其方法（来自 README，已实际读取）：

1. **排名分布价值头（Plackett-Luce）**：网络输出每个玩家的强度 θ∈R^N，用 N 个数字描述 N! 种名次分布；冠军边际是 softmax(θ)。→ 本项目 FFA 用 pairwise Elo + 单一 value 标量，这是可借鉴的升级：价值头改为 multi-head 输出四人/两联盟的胜率分布。
2. **联盟信念头（coalition-belief）**：网络输出两两结盟 logits A 和浓度 β，推断「哪些对手在联合针对 p」，用 self-play 中「实际谁排在 p 前面」训练。→ 本项目联盟是固定规则（南北/东西），但暗棋中「谁在针对我」是动态的，这个 head 的思想可用于**动态威胁评估**。
3. **无遗憾动作选择**：用 EXP-IX Hedge 替代 PUCT，按联盟信念偏移采样。
4. **向量 backup**：全 N×N 名次边际矩阵回传，之后可套任意效用函数无需重搜。

**适配边界**：RL-CCA 是中国跳棋（完全信息、随机对手结盟）；本项目四国军棋还有隐藏信息（暗子），不能把完整局面输入网络——必须与 `belief`/概率矩阵结合（P9.2 已验证暗子零泄露的信息边界）。且 RL-CCA **无 LICENSE**，仅参考技术思路，**不复制任何代码**。

## 3. 训练工程实践（来自已克隆项目 README，已读）

| 实践 | 来源 | 对本项目启示 |
|---|---|---|
| GPU 全链路 self-play（规则/搜索/网络都在 GPU） | quorizero (JAX)、azul (C++) | 本项目 Node 规则进程串行占 56% 时间，是 GPU 利用率瓶颈；可借鉴「规则引擎 GPU 化/并行环境」 |
| 历史对手冻结为版本 | azul、quorizero | 与本项目 Champion/Challenger 注册一致，已具备 |
| 晋级闸门（新模型过 gate 才部署） | quorizero | 与本项目 `is_significant` 门槛一致，已具备 |
| W&B 追踪 self-play/训练/评测 + 版本化 checkpoint | quorizero | 本项目用 JSONL 记录，可借鉴更系统的可视化（未引入外部依赖，符合工程约束）|
| PyTorch CUDA wheel index 配置 | alphazero-style 框架 | 与本项目 CUDA venv 安装方式一致，已验证 |
| 消融阶梯（A0 标量→A3 全 CD-MCTS） | RL-CCA | **可借鉴**：对本项目联盟 AI 做「单标量 value vs 多人分布 value」的消融评测 |
| 负面结果公开（2400 代未稳定提升） | azul | 诚实记录，不夸大；与本项目「不声称棋力提升」一致 |

## 4. 领域专用发现

- `mykun123/Four-Nations-Chinese-Chess-`：四人军棋网页游戏，Team Stratagem 模式 + AI 对手——与本项目同领域，可关注其 AI 实现思路（未深入读源码，仅 README 元数据）。
- `Gawaa/Using-AlphaZero-to-Play-Chinese-Chess`：AlphaXiangqi，把 AlphaGo Zero 方法移植到中国象棋——印证「无人类知识 self-play 适用于中式棋盘」的可行性。

## 5. 对本项目训练升级的可执行建议（不复制代码）

1. **价值头升级（高优先）**：当前 `GraphPolicyValue` 是单标量 value；借鉴 Plackett-Luce，改为输出四人（或两联盟）的强度向量，训练目标用名次/队伍胜负分布——这是多人/联盟博弈的正确价值建模。
2. **联盟信念辅助头（中优先）**：在暗棋视角下增加「谁在针对我」的动态联盟概率（用公开战报 + 阵营规则训练），辅助搜索的威胁评估，不泄露真实身份。
3. **并行 self-play 环境（高优先，解决 GPU 利用率）**：当前 Node 规则进程串行占 56% 时间；借鉴多环境并行，把对局生成并行化，让 GPU 持续有数据。
4. **消融评测**：按 RL-CCA 的阶梯，对本项目做「单 value vs 多人 value vs +联盟 head」的 A/B，用已建立的 100/500/1000 局评测体系验证。

## 6. 许可边界
- MIT（pylos）、Apache-2.0（quorizero）可合法复用但本项目只吸收思路；
- RL-CCA、azul 无 LICENSE，alphazero-style NOASSERTION —— **仅参考技术思路，不复制任何代码**；
- 所有参考项目均非四国军棋暗棋，方法需适配信息边界（暗子投影）后方可借鉴。

## 7. 未解决
- 未找到现成的「四国军棋 + 暗棋 + 联盟 + self-play 训练」完整开源框架（检索了 10+ 关键词）——本项目 P9 训练体系仍需自研，参考项目仅提供方法论与工程实践。
- RL-CCA 的 CD-MCTS 具体公式以 README 为准（已读取），未逐行读其 5400 行源码（clone 失败 + 无 LICENSE，避免复制风险）。
