# AlphaGo 家族学习报告（Fan → Lee → Master → Zero → AlphaZero）

日期：2026-11-19
来源（实际抓取核对）：
- Wikipedia "AlphaGo" 条目：**抓取成功**（686KB，`en.wikipedia.org/wiki/AlphaGo`，加 User-Agent 绕过 SSL 问题），版本表、算法、对局史料已提取。
- Crossref API：确认 Nature 2016 论文 `10.1038/nature16961` 标题 "Mastering the game of Go with deep neural networks and tree search"（即 AlphaGo Fan/Lee 的方法论文）；Nature 2017 `10.1038/nature24270` 为 Zero 论文。
- DeepMind 官方博客（上一轮，用户提供的链接）：AlphaGo Zero 正文抓取成功。
- 诚实声明：Nature 两篇正文均因反爬（Client Challenge）未直接抓取；技术细节以 Wikipedia 公开史料 + DeepMind 官方博客 + 广为公开的论文方法为准，不冒充逐字引用。

## 1. 演进脉络（已核对的时间线）

| 版本 | 时间 | 关键对手/结果 | 技术要点 |
|---|---|---|---|
| AlphaGo Fan | 2015-10 | 5:0 胜樊麾（Fan Hui），首个全尺寸 19×19 无让子击败人类职业棋手的程序 | 策略网络 + 价值网络 + MCTS；从人类棋谱监督学习初始化，再 self-play 强化 |
| AlphaGo Lee | 2016-03 | 4:1 胜李世石（Lee Sedol），首个击败 9 段人类的围棋程序 | 同上架构增强；第 37 手「神之一手」曾让价值网络误判（Wikipedia 记载）|
| AlphaGo Master | 2016-12 ~ 2017-01 | 60 连胜；2017-05 3:0 胜柯洁（Ke Jie） | 更强网络与搜索；后被 Zero 取代 |
| AlphaGo Zero | 2017-10 | 3 天 100:0 胜 Lee 版，21 天达 Master 水平，40 天超越所有旧版 | **tabula rasa**：无人类棋谱、单网络双头、无 rollout、纯 self-play + MCTS |
| AlphaZero | 2017-12 | 24 小时击败 Stockfish（国际象棋）/ Elmo（将棋）/ AlphaGo Zero（围棋 60:40）| 单一算法泛化到多游戏；20 block 版本 Elo 5018 |
| MuZero | 后续 | — | 无需被告知规则即可学习（Wikipedia 记载）|

## 2. AlphaGo（Fan/Lee）的核心算法（2016 论文）

- **MCTS + 双网络**：蒙特卡洛树搜索由「价值网络」和「策略网络」引导，两者均为深度神经网络。
- **策略网络**：预测下一步最佳走法（监督学习人类棋谱 → 强化学习自我对局精修）。
- **价值网络**：评估局面胜者，替代/补充随机 rollout。
- **迭代精炼**：网络提升树搜索强度 → 更强走法选择 → 反哺网络，循环迭代。
- **从人类知识起步**（与 Zero 的根本差别）：Fan/Lee 版用人类棋谱监督学习冷启动；Zero 完全去掉人类知识。

> 来源：Wikipedia「Algorithm」段落原文——"As of 2016, AlphaGo's algorithm uses a combination of machine learning and tree search techniques... It uses Monte Carlo tree search, guided by a 'value network' and a 'policy network', both implemented using deep [neural networks]"

## 3. 对本项目（四国军棋 AI 陪练系统）的逐代借鉴

| AlphaGo 要素 | 本项目对应 | 状态 | 备注 |
|---|---|---|---|
| 双网络（策略+价值） | `GraphPolicyValue` 单模型双输出 | 已具备 | 与 Zero 一致的双头，比 Fan/Lee 的双网络更紧凑 |
| MCTS + 网络引导 | StrongBot 的采样 Alpha-Beta + 启发式先验 | **部分** | 本项目用 Alpha-Beta 而非 MCTS；最大差距是 GNN 未接入搜索 |
| 从人类棋谱监督冷启动 | 无（无四国军棋人类棋谱数据集） | 不适用 | 暗棋联盟无现成大数据；符合 Zero 的 tabula rasa 路线 |
| 自我对弈强化 | `self_play.py` + Champion/Challenger | 已具备框架 | 规模远小于论文，不声称棋力增长 |
| 价值网络替代 rollout | NN 估值 + 搜索估值 | 已具备 | 暗棋用概率采样而非随机 rollout，更贴合隐藏信息 |
| 迭代评测门槛 | 统计显著晋级（样本≥40/胜率≥0.55/CI下界≥0.50） | 已具备 | 比论文"每轮都更好"更保守，适合小样本 |
| Elo 评级 | pairwise Elo（ffa +94~108） | 代理指标 | 已声明非多人正式评级 |

## 4. 关键洞察：Fan/Lee → Zero 的范式转移对本项目的意义

1. **"人类知识起步" vs "tabula rasa"**：Fan/Lee 依赖人类棋谱；Zero 证明纯 self-play 可超越。本项目选择 Zero 路线（无人工特征、无开局库）——正确，因为四国暗棋没有可用的大规模人类棋谱。
2. **双网络→单网络双头**：减少训练与评估成本，本项目已采纳。
3. **搜索与学习的耦合**：这是 AlphaGo 家族持续变强的核心引擎。本项目当前 GNN 与 StrongBot 分离，是明确的技术债；下一步应把 `GraphPolicyValue` 的策略先验接入 `chooseStrongMove` 的候选排序（`rootHeuristic` 是接入点），价值头辅助叶节点评估——但必须在暗棋视角内（用 `belief`/概率，不看真实 type）。
4. **规模效应**：论文的突破建立在海量对局 + 强算力；本项目 8~60 局的 GPU 训练只是流程验证，不能类比其棋力曲线。诚实记录，不夸大。

## 5. 与上一份报告的分工

- `alphago-zero-methodology.md`：聚焦用户提供的 Zero 博客+Nature 论文链接的逐条对照。
- 本报告（`alphago-family-study.md`）：聚焦 Fan→Lee→Master→Zero→AlphaZero 的完整演进脉络与 Fan/Lee（2016 论文）的双网络+MCTS 方法，说明「从人类知识到 tabula rasa」的范式转移。
- 两份互补，均不复制任何代码或素材，仅作方法论学习与适配边界分析。
