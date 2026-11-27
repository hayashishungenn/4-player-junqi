# 旧报告账目与证据订正表（2026-11-26）

对应任务：P0-05（`research/next-phase-task-book.md` §3 / 附录 C）。本表只订正文档表述与证据标注，不改实验数据、不改既有测试断言、不改被订正的原报告，也不改动任何 `results/*.json(l)`。

## 计算口径

- "订正前文件 sha256"用当前磁盘文件实测（`sha256sum`）；因原报告按要求保持只读，"订正后 sha256"列统一写"待填"，待实际订正落地后再回填。
- "已复核"用于 E-05/E-06：E-05 由 P0-04b 产物 `results/derived/repro_check_8.json`（16 局、`diff_count=0`）复核；E-06 按 `tools/audit_replays.py:229-253` 同算法对同一局（iter248 / seed90001）定向复核为 74 次，证据 `results/derived/audit_seed90001.json`；坐标修复前的 38 次作废，不把新分层样本 857 次（不同样本）当作同一局的修正值。
- 输入文件 sha256：
  - `research/training-report.md` = `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527`
  - `research/model-review-report.md` = `0b0013c852953a857b7e134b910a57fc31a44c4e62f972de390d697c1bd3090e`
  - `research/next-phase-task-book.md` = `a49fa84b235eb96079e80425cec555301d112d5095ec7d4f7241c2ea8e39440b`（P0 状态回填前的冻结基准版本；回填后版本见任务书附录 D）
- 实测事实：`results/smoke.jsonl` 不存在；`formations_top200.json` 与 `formations_top200_v2.json` 各含 40 套 formations、40 个 top_indices，位于被 `.gitignore:18` 忽略的 `workspace/siguo-junqi/junqi_env/`。`c1732af` 提交时间为 2026-11-24，三份冻结权重为 2026-11-19 产物（pre-fix）。
- P0 新证据 sha256：`eval_tournament.py` = `abc9c30a797b6459c0baf95c983f17f2b3fceb031d2ae0ec319e0cc1502eab90`；`tools/analyze_tournament.py` = `d515c43773ed6b18cd144f4d2797031171455b3eb51dda6f902c73626ac1c6c7`；`tools/audit_replays.py` = `0b9cca5ba9306baefbaf200b4a2814d40e951654d2d56be8925ab76e69989460`；`results/derived/repro_check_8.json` = `62819050d12e6f3af6442be0ec19d1e4112bb3f3a09910bdcfb527627fc6d86a`；`results/derived/audit_seed90001.json` = `0a08895cca49456a6a74abe31c4888777b261930a08de2657d87e7e4a60f747d`；`results/derived/replay_audit_stratified.json` = `c2434b8c2c380eb051fe618b540404ebfb7e09b18427dcee6bb0c14aa1c7ea2e`。

## 逐行订正表

| # | 旧文件:旧行号 | 新文件:新行号 | 原文摘要 | 问题 | 订正后的精确字符串 | 订正前文件 sha256 | 订正后 sha256 |
|---|---|---|---|---|---|---|---|
| E-01 | `research/training-report.md:218` | 本表 E-01 行（原报告不改） | `25.0% (50/200: 50胜 1负 149平)` | 24W1L75D + 26W2L72D = 50W3L147D，总 200 局成立但胜负平分项与两次独立抽检之和矛盾 | `25.0% (50/200: 50胜 1负 149平)【口径不明：两次 100 局之和为 50胜 3负 147平，与该行不一致；原始逐局日志缺失，不能判定哪一记录正确，须查原始日志后再订正】` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-02 | `research/training-report.md:184` | 本表 E-02 行（原报告不改） | `\| 阶段二布阵库 Top-200 \| ≥200套差异化布阵 \| ✅ 已入库（heuristic-fitness） \|` | 实为各 40 套且位于被 `.gitignore:18` 忽略的 workspace，未入库，"已入库"不实 | `\| 阶段二布阵库 Top-200 \| ≥200套差异化布阵 \| ❌ 未入库：实际各 40 套，位于被 .gitignore:18 忽略的 workspace/siguo-junqi/junqi_env/；按 D6 决策补建或订正表述 \|` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-03 | `research/training-report.md:188` | 本表 E-03 行（原报告不改） | `\| 阶段五 Top-200 差异化布阵 \| ≥200套 \| ✅ 已入库（确定性排序稳定、fit_mean=54.46） \|` | Top-200 目标未达成；fit_mean=54.46 只是 40 套样本的统计，不得当作 200 套证据 | `\| 阶段五 Top-200 差异化布阵 \| ≥200套 \| ❌ 未入库：实际各 40 套且 workspace/ 被 .gitignore:18 忽略；fit_mean=54.46 仅为 40 套样本统计；按 D6 决策处理 \|` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-04 | `research/training-report.md:197` | 本表 E-04 行（原报告不改） | `Top-200 候选满足「实战均胜率 ≥ Heuristic Bot 与 Bot 自打同时 ≥ Heuristic Bot 与 random uniform」差值，输出 formations_top200_v2.json` | 文件名写 top200，实际只包含 40 套，且文件在被忽略目录，未入库 | `Top-40 候选满足「实战均胜率 ≥ Heuristic Bot 与 Bot 自打同时 ≥ Heuristic Bot 与 random uniform」差值，输出 formations_top200_v2.json（实际 40 套，位于被 .gitignore:18 忽略的 workspace/siguo-junqi/junqi_env/，未入库）` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-05 | `research/model-review-report.md:37` | 本表 E-05 行（原报告不改） | `\| 8 局小样能复现、能跑完整局 \| ✅ \| results/smoke.jsonl（trace 完整）；核心字段重跑一致 \|` | `results/smoke.jsonl` 实测不存在，该行把不存在的证据标为通过 | `\| 8 局小样能复现、能跑完整局 \| ⚠️ 证据缺失（旧路径）→ 已由 P0-04b 新证据复核 \| results/smoke.jsonl 不存在（已核对）；新证据 results/derived/smoke_8.jsonl（sha256 77afd1d6…）、smoke_8_repeat.jsonl（b9024560…）、stats_8.json（86b18ee3…）、repro_check_8.json（62819050…，n=16、diff_count=0）；原报告未修改 \|` | `0b0013c852953a857b7e134b910a57fc31a44c4e62f972de390d697c1bd3090e` | 待填 |
| E-06 | `research/model-review-report.md:62-63` | 本表 E-06 行（原报告不改） | `12 局回放中 9 局出现（iter248 seed90001 达38次）` | "38 次"为 belief 坐标修复前的过期计数，不得再作为已核事实；新分层样本未包含 seed90001，不能用分层样本总量替代 | `12 局回放中 9 局出现（iter248 seed90001 的精确命中次数：按当前 tools/audit_replays.py:229-253 同算法定向复核为 74 次，证据 results/derived/audit_seed90001.json，sha256 0a08895c…，trace_match=true；坐标修复前的 38 次计数已作废，两者口径/坐标不同，不解读为泄漏增加；另 P0-03 分层样本 33 局独立计得 857 次，样本不同不可互换；未完成逐点归因前不得定性）` | `0b0013c852953a857b7e134b910a57fc31a44c4e62f972de390d697c1bd3090e` | 待填 |
| E-07 | `research/training-report.md:125-137` | 本表 E-07 行（原报告不改） | `胜率非单调：200 迭代时 22.5%，随后继续训练反而坍缩到 0%……说明探索塌陷信号（贪婪 argmax 选无吃子平局）仍是局所最大值` | 不同种子/配置散点被写成 collapse 因果；未做连续 3 快照 ≥5pp 且相邻差 CI 上界 <0 的预注册测量 | `胜率非单调：200 迭代时 22.5%，另一配置观测到 0%（不同种子/配置的散点）；collapse 未测量，按 §1 判据记为证据不足，不得写因果结论` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-08 | `research/training-report.md:139` | 本表 E-08 行（原报告不改） | `之后 Rew 普遍转正 (+0.01~+0.07)，验证 commander+司令/军长/主力 这些 sparse 奖励已被模型吸收到模型权重，但 win-rate 起伏说明价值函数脆弱` | "Rew 转正已被模型吸收"为无产物支持的归因，与胜率起伏并列时未测量 | `之后 Rew 普遍转正 (+0.01~+0.07)（旧叙述，无可复核日志产物）；Rew 转正归因与胜率相关结论未测量，不写为已验证事实` | `c1998417ed2a321e933ca160f8c79f4dcf50c98f9bdd7f3ebfe3a2b315077527` | 待填 |
| E-09 | `research/training-report.md:229`；`results/tournament.jsonl:1` | 本表 E-09 行（原报告不改） | `junqi_best_iter240.pt` 被当作可评价修复效果的 checkpoint | 2026-11-19 产物，早于 2026-11-24 的 `c1732af`，属 pre-fix 权重 | `junqi_best_iter240.pt（sha256 d2d37c1b32828601c62879c15ca6c00db2e87ac66222a0741975ffeddf48c6b0，2026-11-19 产物）为 pre-c1732af 旧权重；不得用于评价 c1732af 的 GAE/PPO 修复效果` | `d2d37c1b32828601c62879c15ca6c00db2e87ac66222a0741975ffeddf48c6b0` | 待填 |
| E-10 | `research/training-report.md:105-109,218`；`results/tournament.jsonl:1` | 本表 E-10 行（原报告不改） | `junqi_pool20_iter248.pt` 被当作峰值稳定复现证据 | 2026-11-19 产物，早于 2026-11-24 的 `c1732af`，属 pre-fix 权重 | `junqi_pool20_iter248.pt（sha256 7d330eb39cf5c4530e02afbe2e6cdedeeb730e958f4e234fc793dfa7f55bba11，2026-11-19 产物）为 pre-c1732af 旧权重；不得用于评价 c1732af 的 GAE/PPO 修复效果` | `7d330eb39cf5c4530e02afbe2e6cdedeeb730e958f4e234fc793dfa7f55bba11` | 待填 |
| E-11 | `research/training-report.md:219,228`；`results/tournament.jsonl:1` | 本表 E-11 行（原报告不改） | `junqi_iter688.pt` 被当作长训最终 checkpoint 比较 | 2026-11-19 产物，早于 2026-11-24 的 `c1732af`，属 pre-fix 权重 | `junqi_iter688.pt（sha256 260d3cd1112e47491616c3a7c16d025c12c084bab8567644a0d238f0e4ad40aa，2026-11-19 产物）为 pre-c1732af 旧权重；不得用于评价 c1732af 的 GAE/PPO 修复效果` | `260d3cd1112e47491616c3a7c16d025c12c084bab8567644a0d238f0e4ad40aa` | 待填 |

## 回填规则

- E-05 已由 P0-04b 产物 `repro_check_8.json`（`diff_count=0`）复核；E-06 已按同算法对同一局定向复核为 74 次（`audit_seed90001.json`）。P0-03 分层样本的 857 次属不同样本，只作独立计数，不作 E-06 的修正值。
- E-02/E-03/E-04 的最终去向取决于 D6：补建 ≥200 套入库，或正式把文档订正为 40 套。D6 未决前不得写"已入库"。
- 原报告按要求保持只读，故"订正后 sha256"列保持"待填"（表示原报告未修改，非信息缺失）；新证据产物的 sha256 已写入 E-05/E-06 的订正字符串与本文件计算口径节。本表自身不触发原报告改动。
