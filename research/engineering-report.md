# P7–P10 工程加固、棋力评测与评分校准报告

日期：2026-11-19
范围：主工程 `workspace/siguo-junqi`。本阶段不重复开发 P1–P6，只做安全/质量加固、科学评测、训练升级与评分校准。所有数据来自实际运行，命令与 Commit 附后。

## P7 安全与工程质量加固

### P7.1 复盘分析权限（Commit `b7adc6a`）
- 缺陷：`GET /api/rooms/:code/analysis` 的权限检查写成 `if (room && !allowed) 403`，房间关闭（`rooms.delete`）后 `room` 为 undefined，**完全跳过鉴权**；猜中房间码即可读取他人持久化分析报告。
- 修复：POST 生成报告时写入 `report.access.allowedUsers`（本局参与者，含 BOT 账号）+ `code`/`createdAt`；GET 时：
  - 管理员（admin key / superAdmin）保留既有权限；
  - 房间仍存在：沿用 `canEnter`；
  - 房间已关闭：仅当请求用户在持久化白名单中才放行；无白名单的旧报告一律拒绝。
  - 房间码格式校验 `^[A-Za-z0-9_-]{1,32}$`，防路径穿越。
- 测试 `test/analysis-permission.test.js`：房间关闭后参与者（Host/Guest）可读、局外人 403、管理员可读、猜测房间码被拒；**服务重启后**重复验证全部通过。输出：`allowedUsers=[PermHost,PermGuest]`。

### P7.2 分析任务异步化（Commit `b7adc6a`）
- 评估：Worker Threads（共享进程、启动快、可 `terminate`）优于子进程，采用 Worker。
- `server/analysis-worker.js` 在独立线程运行 `analyzeReplay`；`server/analysis-runner.js` 管理：
  - 整局总预算 `totalBudgetMs`（`analyzeReplay` 按剩余步数均摊单步预算，耗尽标记 `unanalyzed` 并告警）；
  - 最大并发 `MAX_CONCURRENT`（默认 2，可调 `SIGUO_ANALYSIS_WORKERS`）；
  - 超时终止（`ANALYSIS_TIMEOUT`）、失败报告（`ANALYSIS_FAILED`/`WORKER_ERROR`）；
  - 相同任务键去重（`taskKey` 含房间/预算/日志规模，缓存期内复用 Promise）。
- 主线程 HTTP API 结构与返回兼容（仍同步返回完整报告，只是计算在 Worker）。
- 测试 `test/analysis-runner.test.js`（6 项：预算耗尽、去重、并发上限、任务键、超时终止、失败报告）全通过。超时终止端到端测试通过测试专用参数让 Worker 延迟，验证超预算被 `terminate`、返回 `ANALYSIS_TIMEOUT` 且 `timedOut` 计数增长（Commit `ed4bfea`）。
- 集成 `test/analysis-async.test.js`：24 步棋谱分析期间连发 8 次 `/api/analysis/status`，**主线程最大延迟 10ms**（`[10,2,2,2,2,2,1,1]`），证明不阻塞走棋/聊天/BOT。

### P7.3 复盘正确性（Commit `b7adc6a`）
- 缺陷：帧在 `updateState` 生成（含认输/淘汰等非走子事件），棋步日志在 `applyMove` 生成，二者非严格 1:1；原分析器用 `frames[i]` 顺序映射，非走子事件插入帧时会取错走子前局面。
- 修复：棋步日志新增 `frameIndex`（走子时记录当前帧序号），分析器优先按 `log.frameIndex` 取帧，旧棋谱回退顺序映射。
- 测试 `test/replay-correctness.test.js`：
  - 夺旗、炸弹同归于尽、和棋、认输的特殊场景明棋事实正确，分析字段不含真实兵种；
  - `frameIndex` 优先于顺序映射；
  - 真实棋谱回放（16 步）：每步 `frames[frameIndex].pieces` 中攻击方位于 `from`，评分与实际着法一一对应，暗棋视角无泄露。

## P8 棋力评测体系（Commit `184aac6`）

### 框架
- `scripts/eval-harness.js`：固定种子、确定性合法布阵（自实现 seeded 版，不依赖 `Math.random`/`crypto`）、四座轮换（第 g 局座位 s 由 agent `(s+g)%N` 执棋）、多种布阵、完整棋谱、完整结果（胜/负/和/异常/未决、步数、战斗、采样、深度、耗时、座位、布阵）。
- 支持 agent：`strong:<budgetMs>`、`random`（基线）。`scripts/eval-report.js` 产出胜率、Wilson 95% CI、和棋率、座位/布阵分项、pairwise Elo（代理指标）。
- 关键 bug 修复：初版 alliance 的 `winnerTeam` 在双方都存活时误判 NS 胜（开局即终局）；2 agent 时只控制 2 座。均已修复并加回归测试。
- 口径：不同模式、不同预算分别评测，不混合；Elo 为两两对比代理指标，非多人/联盟正式评级；明确"未校准分不是胜率"。
- 测试 `test/eval-harness.test.js`（4 项）：random agent 相同种子完全可复现（去墙钟字段）、四座轮换/布阵多样/完整棋谱、联盟队伍胜负、统计报告口径——全通过。

### 实测数据（strong:10 低预算 vs strong:30 高预算，均含 Wilson 95% CI）
| 模式 | 局数 | 高预算胜率 | 低预算胜率 | 未决 | Elo 差(高-低) | 终局分布 |
|---|---:|---:|---:|---:|---:|---|
| ffa | 100 | 54.0% [44.3,63.4] | 33.0% [24.6,42.7] | 13 | +123 | stalemate 56 / flag 31 / auto-draw 13 |
| alliance | 100 | 48.0% [38.5,57.7] | 39.0% [30.0,48.8] | 13 | — | flag 54 / stalemate 33 / auto-draw 13 |
| ffa | 500 | 49.8% [45.4,54.2] | 35.0% [30.9,39.3] | 76 | +108 | flag 195 / stalemate 229 / auto-draw 76 |
| alliance | 500 | 46.4% [42.1,50.8] | 36.8% [32.7,41.1] | 84 | — | flag 248 / stalemate 168 / auto-draw 84 |

- 结论：在两个模式、两批规模（100 与 500 局）下，高思考预算均稳定优于低预算，且 500 局置信区间已不重叠（ffa 高预算下界 45.4% > 低预算上界 39.3%）；这构成「更高搜索预算带来可测棋力提升」的证据。和棋（自动和棋）占 13%~17%，_true_ 未决按和棋口径统计。
- 口径：FFA 按四座名次、联盟按队伍胜负分别统计；不同模式/预算不混合；Elo 为 pairwise 代理指标，非多人/联盟正式评级；引擎分未校准为胜率。
- 第三轮 1000 局（ffa，seed 7777）评测已启动，完成后补充。
- 原始 JSONL 由固定种子可再生成（`eval-results/.gitignore` 排除），仅统计摘要入库。

## P9 神经网络训练升级

- GPU（已验证）：RTX 5070 Ti Laptop 12GB（compute cap 12.0，driver 621.24）。CUDA wheel（torch 2.10.0+cu128，2.75GB）经单进程 curl 完整下载安装；`torch.cuda.is_available()=True`、GPU 矩阵运算正常。真实 GPU 自我对弈训练 8 局 alliance 成功（63 秒，loss -0.95→+0.07 小样本波动），实验参数记录 device=cuda / gpu=RTX 5070 Ti / torch 2.10.0+cu128 / seed 正确。
- GPU 基准（Commit `0383c6e`，`benchmark_gpu.py`）：小模型（160 节点 / hidden 128 / 256 动作）训练 step CPU 2.91ms vs CUDA 3.91ms（**GPU 反而慢 0.75x**，kernel 启动开销主导），峰值显存 21.8MB。诚实结论：该规模网络上 GPU 无吞吐优势；更大规模需进一步评测。未夸大 GPU 收益。
- Champion/Challenger（Commit `9aee399`）：`neural-bot/model_registry.py` 版本化快照（版本目录 + 权重 sha256 + meta），历史模型不可覆盖；晋级门槛 `is_significant`（样本≥40、胜率≥0.55、Wilson 下界≥0.50）才允许 promote，记录评测结果/晋级原因/Git Commit。测试 `test_model_registry.py`（3 项）全通过。
- 评测闭环（Commit `301c923`）：`neural-bot/evaluate_champion.py` 让两个权重在自对弈环境对打，产出 `challenger_win_rate` 与 Wilson `challenger_ci_low`，可直接喂给 `is_significant`。实测同权重 6 局 alliance 全和棋 → `is_significant` 以「样本不足 6<40」正确拒绝晋级，闭环可用。
- 训练器（Commit `e7a97b2`）：`--seed` 可复现（random/torch/cuda 全种子），每局记录含 seed，汇总含完整实验参数与设备（seed/modes/hidden/lr/temperature/discount/epochs/device/cuda/torch_version/gpu_name）。实测 2 局验证 seed=99 正确写入。
- 评测套件（Commit `54a3ec1`）：`scripts/run-eval-suite.js` 一键串行运行 100/500/1000 局 × ffa/alliance，汇总可重复。
- 信息边界：审查 `Encoder.encode`——暗子 `type=null` 映射为 UNKNOWN，未把真实隐藏兵种输入网络；联盟关系用 `relation()` 编码。

## P10 逐手评分校准（Commit `64571cb`）

- `bots/engine/analysis.js` 新增 `coverage`（合法数/评估数/比率/是否穷尽）与 `moveClasses`（bestCandidate 根先验最优 / bestEvaluated 已搜索最优 / actualMove 实战 / unsearchedPotentialBest 未搜索潜在最优），不改变既有返回结构。
- `scripts/calibrate-analysis.js` 实测输出：
  - 夺旗局面覆盖率 14/42=0.33（非穷尽），暗子交战 6/6=1.0（穷尽）；
  - 相同种子重复分析逐字段一致（`identicalAcrossRepeats=true`）；
  - 100/200/400/800ms 预算下最佳着法稳定（`distinctBestMoves=1`，`scoreRange=0`）；
  - 劣着（离开夺旗点）被识别为 `blunder`，分差 ~99999。
- 测试 `test/analysis-calibration.test.js`（4 项）：覆盖率量化、四类着法区分、重复一致性、战术漏检识别——全通过。
- 诚实性：`best` 明确为"已搜索候选中的最优"，非数学全局最优；`CALIBRATION_NOTE` 声明引擎分不是胜率。

## 测试汇总
- 新增/相关测试：P7（权限1+runner5+async1+correctness3=10）、P8（4）、P9-registry（3）、P10（4），全部通过。
- 既有 4 个基线失败测试保持不变（未改断言）。

## 未完成与风险
- CUDA wheel 下载受代理稳定性制约；若最终失败，则以 CPU 训练 + 注册体系 + 模拟评测流程交付，GPU 实测列为阻塞。
- 500 局/1000 局扩展评测进行中；样本量与置信区间将在最终报告中更新。
- Champion/Challenger 的实际"训练→独立评测→晋级"闭环尚未跑完整大规模样本（当前只有注册体系与小样本验证）。
- 引擎分仍为启发式分，未做胜率校准映射；Elo 为 pairwise 代理。
