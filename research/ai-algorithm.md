# 四国军棋 AI 算法说明

日期：2026-11-19
适用对象：主工程 `siguo-junqi` v2.12.2 及本次新增的评分/复盘/难度模块。
相关源码分析：`research/repo-analysis/siguo-junqi.md`；技术取舍：`research/repo-analysis/integration-plan.md`。

## 1. 信息模型：暗棋视角是唯一入口

- `bots/engine/bot.js::botView(room, seat)` 是引擎读取真实房间的**唯一边界**：己方棋子与已公开（`revealed`）棋子保留 `type`，其余一律 `type=null`。注释明确禁止私密日志、隐藏兵种、账号数据跨越该边界。
- 交战学习 `observeBotBattle` 只把**公开战果**（谁攻谁、结果）写入历史，并据此收缩各方的秘密候选集；对手真实兵种不进入记忆。
- 本次新增的 `analysis.js` 与 `replay-analysis.js` 继续遵守该边界：
  - `evaluateMoveSet` 只接受已投影的 `view`；
  - `projectFrame` 对复盘局面做等价投影；
  - 分析报告显式标注 `perspective: {analysis:'dark', truth:'open'}`；真实兵种只出现在 `truth`（赛后明棋）字段，绝不进入 `analysis` 字段。
  - 测试 `test/analysis.test.js`、`test/replay-analysis.test.js` 对「分析字段不含真实兵种」做了断言。

## 2. 概率推断与暗棋采样

1. **兵种先验** `distribution(p)`：按候选域、布阵规则（军旗仅大本营、地雷不在前三排、炸弹不在第一排、移动过的子非不可动子）与每兵种固定数量给出分布。
2. **军旗共享概率** `belief(view,p)`：每支存活军队恰有一面军旗，概率由所有可能大本营共享，不被 25 枚棋子稀释。
3. **弧一致性** `inferDomains(view)`（search.js 第 19–50 行）：最多 30 轮，用公开战果 + 每方棋子计数反复收缩各子的候选域；对不完整历史保留防御，不崩溃、不发明确定性。
4. **一致采样** `samplePosition`（第 52–85 行）：按域与剩余库存做随机加权无放回采样，并受战果一致性约束，生成一份「具体化」局面供搜索。每次采样都满足 `validateSetup` 与兵种计数（由 `test/strong-bot.test.js` 验证）。

## 3. 搜索与估值

- **走法生成** `strongMoves`：与服务端 `validateMove` 一致（公路、铁路直线、工兵铁路 BFS），由 `test/strong-bot.test.js` 的对拍测试保证一致。
- **搜索** `searchPosition`：Alpha-Beta + 深度自适应宽度（深度≥3 取前 10，否则 7）+ 浅层兑子延伸 + 超时 `TIMEOUT`。
- **估值** `evaluate`：子力价值表（军旗 16000、司令 135、军长 100、…、工兵 48、地雷 35、炸弹 65）、位置项（行营、铁路、逼近敌旗、护旗）、终局 ±50000。联盟以 `allied()` 判定南北 / 东西同队，己方子 `+`、敌方子 `-`。
- **根先验** `rootHeuristic`：概率交战收益、夺旗加分、工兵暴露惩罚、重复晃动惩罚、逼近目标、护旗 +1800、入侵者拦截等。
- **主入口** `chooseStrongMove`：多采样 Alpha-Beta；深度随采样数 `2→3→4→5`；**每批所有候选共享同一采样局面**，整批超时则丢弃；按「均值 − 0.16×标准差 + 非局面调整」选步；必吃确定军旗时直接返回。返回 `{move, samples, depth, elapsedMs}`。

## 4. 多档难度（P2）

`bots/engine/difficulty.js` 提供 5 档（入门/初级/中级/高级/大师）到 `budgetMs`、`maxSamples`、`maxDepth` 的映射，棋力随预算增大而增强（更多采样、更深搜索）。**这是工程约定，不是 ELO、不是胜率**，也不修改 `chooseStrongMove` 的公共 API。未知档位抛错，不静默回退。

## 5. 逐手评分（P3）

`bots/engine/analysis.js::evaluateMoveSet(view, actualMove, history, options)`：

- 候选集 = 根先验排序的前 N 着 + 实际着法（若不在前 N）。
- 实际着法与所有候选在**同一采样局面、同一搜索深度**下评估；批次超时整批丢弃，不产生半批次分。
- 每着输出 `mean / std / worst / samples / score`（`score = mean − 0.16×std`）。
- `scoreLoss = best.score − actual.score`；错误等级 `best / good / inaccuracy / mistake / blunder`，阈值 `30 / 100 / 350 / 1000`（启发式分，非胜率）。
- 输出 `explanation`（夺旗机会、离开护旗圈、进入大本营等）与 `calibrationNote`。
- **重要**：`prior` 只作候选排序与展示，不参与跨候选的最终分差计算，避免局面相关启发式污染公平比较。

## 6. 完整复盘（P4）

`bots/engine/replay-analysis.js::analyzeReplay(replay, options)` 读取现有 `room.replay`（frames + logs），不另造棋谱格式：

- 每步用 `projectFrame` 取得走子前暗棋视角，`publicBattles` 注入截至该步的公开战果，`historyForSeat` 提供重复晃动历史。
- 输出 `moves[]`（含 `analysis` 与 `truth`）、`curve[]`（分差曲线）、`blunders[]`（关键失误）、`summary.perSeat`（各档统计、平均损失）、`warnings`。
- CLI：`node scripts/analyze-replay.js <replay.json> [--budget-ms N] [--mode ...] [--seed N] [-o out.json]`。
- 服务端：`POST /api/rooms/:code/analysis`（仅终局、需权限，限制预算与步数），前端在复盘弹窗中提供「分析本局」按钮、分差曲线、关键失误列表与当前步评分。

## 7. 自我对弈训练（P5，环境已验证）

`neural-bot/`：`GraphPolicyValue`（GNN 策略价值网络）、`self_play.py`（`--games / --device cuda|cpu / --modes ffa|alliance`，历史最佳模型对抗）、`self_play_env.mjs`（本地 JSON-RPC 对局环境）。本次已实测 `self_play_env.mjs` 的 `reset(mode=alliance)` / `state` / `board` 正常。**阻塞**：PyTorch 未安装，GPU 训练未执行（详见评测报告）。

## 8. 诚实性声明

- 所有分值均为`未校准的启发式引擎分`，不是胜率，不换算为百分比，UI 与报告不得标注为胜率。
- 错误等级阈值是经验值，需用棋力评测数据校准后方可调整；当前不声称统计显著性。
- 公开战果是唯一可跨回合传播的交战信息；任何真实隐藏兵种只出现在赛后明棋视角。
