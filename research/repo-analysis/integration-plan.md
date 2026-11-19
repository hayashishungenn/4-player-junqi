# 四仓库技术整合方案

日期：2026-11-19
输入：四份源码分析报告（`siguo-junqi.md` / `open_junqi.md` / `4nationwar.md` / `DL-Military-chess-AI.md`）与 `research/p0-baseline.md`、Just Xiangqi 逆向报告。
结论先行：**主工程 `siguo-junqi` 的暗棋 AI 引擎在算法完备性上强于三个参考项目**，整合以「自研引擎为主、选择性吸收思路」为原则；两个无许可证仓库仅参考技术思路，不复制代码。

## 1. 许可证与复用边界（先决约束）

| 仓库 | 许可证 | 复用方式 |
|---|---|---|
| siguo-junqi（主工程） | MIT | 直接修改、扩展 |
| open_junqi | MIT | 可复用代码，须保留 `Copyright (c) 2026 Junqi AI Project` 与 MIT 全文；本方案仅吸收思路，不复制 |
| 4nationwar | **无 LICENSE 文件** | **仅参考技术思路，不复制任何代码** |
| DL-Military-chess-AI | **无 LICENSE 文件** | **仅参考技术思路，不复制任何代码** |

## 2. 四项目算法横向结论（源码证实）

- **主工程**：真暗棋采样（`samplePosition`，受战果一致性 + 库存约束）+ 弧一致性域推断（`inferDomains`）+ 联盟 Alpha-Beta（`allied`/`terminal`/`evaluate`）+ 自适应深度 2→5 + 根先验。是唯一完整处理「隐藏信息、对家结盟、概率交战」三者组合的引擎。
- **open_junqi**：联盟 Alpha-Beta（`are_allied` → Max/Min，团队差分叶评估）+ Beam Search（每层排序后截 top-8）+ 9 项加权评分。但**本地决策算法实际全知（读取真实棋子身份），只有 LLM 对话层做信息隐藏**——这正是陪练系统必须避免的反模式。另有搜索轮转顺序（1,2,3,4）与真实规则（1,4,3,2）不一致、TT 无 alpha/beta 界标志等缺陷。
- **4nationwar**：README 承诺的 AlphaBetaSearch / 置换表 / 剪枝 / 博弈树**在源码中完全不存在**；实际 `cpu.cpp` 无条件返回 `SimpleMan`，是 1-ply 随机贪心 + 暗子候选均匀平均。可借鉴的是 `BoardContext` 的**位掩码候选角色 + 交战历史约束传播 + 数量消元**，与主工程 `inferDomains` 思路同源，但主工程实现更完整。
- **DL-Military-chess-AI**：Keras 卷积估值网（32→16→4→1）+ 25×12「隐藏身份概率表」特征；但**self-play 未实现**（唯一数据入口 `input.py` 读现成棋谱），`mcts.py` 实为固定 4 层极大极小（无 UCB/访问计数），且有多项代码缺陷。概率矩阵编码思路可供主工程 GNN 输入参考。

## 3. 值得吸收的思路（按优先级）

1. **团队差分叶评估**（open_junqi）：以「联盟总收益 - 敌方总收益」作叶节点，主工程 `evaluate` 已用 `sign=friendly?1:-1` 实现等价逻辑，保持现状即可，无需引入其代码。
2. **概率身份特征编码**（DL）：GNN 输入可增加「每子兵种概率向量」通道。主工程 `belief`/`distribution` 已产出该概率，接线成本低。属 P5 增强，非必需。
3. **位掩码域表示**（4nationwar）：主工程用 `Set` 表示域，语义等价且更易调试，不替换。
4. **候选 Beam 截断**（open_junqi top-8）：主工程已用 `slice(0, width)` / `slice(0, 28)` 实现同类截断，保持现状。
5. **反面教材——禁止全知**：open_junqi 本地决策全知的做法绝不可引入；主工程 `botView` 的单一边界（bot.js 第 6–8 行注释）是正确的安全模型，逐手评分与复盘分析必须继续走该边界。

## 4. 与 Just Xiangqi 逆向结论的对接

`reverse-engineering/comparison/recommendations.md` 提出：先定义引擎协议与棋谱格式，再接入搜索/GNN。落地方式：
- **逐手评分标签**：象棋用 Best/Good/Book/Inaccuracy/Mistake/Blunder/Missed；本系统采用 `best/good/inaccuracy/mistake/blunder`（见 `bots/engine/analysis.js` 的 `ERROR_THRESHOLDS`），暂不含 Book（四国军棋无等价开局库）与 Missed（与 Blunder 合并）。**阈值基于本引擎启发式分，不是胜率**。
- **动态阈值**：象棋按局面动态调阈值；本系统首版用固定阈值，后续可依据棋力评测数据校准（不冒充胜率）。
- **醒棋谱格式**：象棋 `.game`（Odin JSON）+ PGN；本系统复用现有 `room.replay`（frames + logs，JSON），不另造格式。
- **明棋/暗棋视角切换**：象棋复盘可看双方；本系统复盘 API 对进行中房间脱敏、终局房间开放完整日志，符合安全模型。

## 5. 开发落地顺序（与本次实施对应）

1. **P3 逐手评分（已完成）**：`bots/engine/analysis.js`，统一暗棋视角与采样条件；4 项测试通过，commit `5ac3e23`。
2. **P4 复盘分析器（进行中）**：读取 `room.replay.logs`+frames，生成评分曲线/关键失误/最佳着法/整局报告；实战暗棋视角与赛后明棋视角分离。
3. **P2 难度分级**：以 `budgetMs`（及采样/深度上限）包装多档难度，不新增依赖、不改公共 API。
4. **P5 训练环境**：建立独立 venv 安装 CUDA PyTorch，验证 `self_play.py` 的 `--modes alliance` 与历史最佳对抗；不提交权重。
5. **P6 界面**：在现有 `public/app.js` 复盘入口接入评分曲线与失误列表。

## 6. 风险与未决

- 三个参考项目均无可用于「复制代码」的充分授权（两个无 LICENSE，MIT 项目本方案也只吸收思路），整合不得演变为代码搬运。
- 引擎分为未校准启发式分，任何 UI/报告都不得标注为「胜率」。
- open_junqi 搜索轮转错误提示：接入任何新走法生成逻辑前必须用 `validateMove` 对齐顺序，主工程 `strongMoves` 已有测试覆盖（`test/strong-bot.test.js`），保持该测试为回归闸门。
