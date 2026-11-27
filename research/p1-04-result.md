# P1-04 结果：三快照 collapse 量化扫描（2026-11-27）

状态：**已完成；按预注册判据记为「证据不足 / 未观测到 collapse」**。判据见 `research/acceptance-criteria.md` §3 与 `research/p1-01-preregistration.md`。本文件不改写历史 `results/*.json(l)`。

## 1. 证据与哈希

- `results/derived/manifest_p1-04.json` = `e0043b4b6fe21a348cacfa8709ca278cb75fbb9227f07389394857ea07378f1e`
- `results/derived/collapse_scan.jsonl` = `a07075848e830e1eed056fcb1878c1a2ebfc9ab54ce231dc9f0f453bb94c92ff`（301 行 = 1 meta + 3×100 局）
- `results/derived/stats_collapse_scan.json` = `826bd221571ffe5f03015ff78b2dd0c21a18ddda647fee2c3164a3cb92b7db0f`
- 日志：`collapse_eval.log` = `59d2c2f2ac10ad7a75b3ff626481a12eaa0e75f6e62fb427ff97ff2fc354c026`；`collapse_analyze.log` = `a2a0b7b848379ec3714624d4345858f93ea0f373bf05da0e524b9afed04643b7`
- git HEAD = `3c7e0cf`（含 PPO 诊断日志提交），`worktree_dirty=false`；`git diff -- results/` 为空。

冻结条件：`iter400/iter600/iter800`，每快照 100 局，`seed_base=90000`、逐局 `seed=90000+g`、`max_steps=240`、argmax、`HeuristicBotWrapper`、座位奇偶轮换、bootstrap B=10000/rng=0。训练脚本因稳定性改造 sha 已变，但评测逻辑与权重未变；本文件只比较本次三快照，不与 300 局样本合并。操作者 = Claude Code（本机，用户授权 GPU 时段）。

## 2. 逐快照主口径

| 快照 | W/N | Wilson 95% CI | W/(W+L)（W+L, N） | decisive | step_limit_draw | no_capture_draw |
|---|---|---|---|---|---|---|
| `iter400` | 45/100 = **45.0%** | [35.6%, 54.8%] | 45/49（49, 100） | 49 | 51 | 0 |
| `iter600` | 35/100 = **35.0%** | [26.4%, 44.7%] | 35/37（37, 100） | 37 | 61 | 2 |
| `iter800` | 19/100 = **19.0%** | [12.5%, 27.8%] | 19/21（21, 100） | 21 | 79 | 0 |

三快照 `W/N` 逐次下降，累计下降 **26.0pp**（≥5pp）。step_limit_draw 率逐次上升 **51% → 61% → 79%**，decisive 率相应下降。

## 3. 相邻快照配对差（统计脚本输出为「前 − 后」）

| 比较 | obs（百分点） | CI95（前−后） | 换算为「后−前」CI95 | 上界 | b/c | Holm p | 是否支持该步下降 |
|---|---|---|---|---|---|---|---|
| iter400 − iter600 | +10.00 | [−1.00, +21.00] | [−21.00, +1.00] | +1.00 | 22/12 | 0.121 | **否**（CI 含 0） |
| iter600 − iter800 | +16.00 | [+5.00, +27.00] | [−27.00, −5.00] | −5.00 | 25/9 | 0.0181 | **是**（CI 上界<0） |

## 4. 冻结判据判定

预注册 collapse 判据要求**同时**满足：

1. 连续 3 快照 `W/N` 逐次下降且相对首快照累计下降 ≥5pp → **满足**（45%→35%→19%，累计 26pp）。
2. 相邻快照差的 bootstrap 95% CI 上界 <0（统计支持该步下降）→ **不满足**：`iter400→iter600` 的「后−前」CI 上界为 +1.00，跨 0；只有 `iter600→iter800` 上界 −5.00 支持下降。

**判定：未观测到 collapse / 证据不足**（按冻结判据不得写“观测到 collapse”，也不得写因果结论）。可如实写：三快照呈单调下降且末步统计显著，首步样本不足、CI 跨 0；无 entropy 日志时不以 entropy 叙事补位。当前稳定性改造已加入 `approx_kl/clip_fraction/entropy/grad_norm/ratio` 饱和日志，后续重训才有日志证据可做归因。

## 5. 后续

- 不因本结果直接写“训练坍缩”因果；`iter800` 显著回退已在 `research/p1-01-result.md` 用 300 局样本证实，本次 100 局扫描只是独立复核方向与终局分布。
- 下一步按计划做训练稳定性单变量实验（日志基线 → KL 早停阈值 → 完整 resume），任何新训练需单独 GPU 授权与 manifest。
- 65% 主口径仍未达；本次最高 45.0%，Wilson 上界 54.8%。
