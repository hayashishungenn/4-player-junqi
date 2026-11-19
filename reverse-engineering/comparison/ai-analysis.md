# AI 棋力与搜索机制研究报告（象棋为主）

> **范围说明**：《Just Go》未购买、已排除。本文第 3 节及对比表中涉及围棋的内容仅来自残留日志，作背景参考；正式结论以《Just Xiangqi》为准。

## 1. 概述

《Just Xiangqi》的棋力由三代技术叠加而成：NativeAI（拟人低手）、ElephantEyes（传统搜索）、Pikafish（NNUE 现代引擎）。难度不是“削弱引擎”，而是组合引擎类型、搜索深度、候选随机采样与开局库。

| | Just Xiangqi | Just Go |
|---|---|---|
| 引擎 | 自研 NativeAI / ElephantEyes C# / Pikafish | KataGo v1.10.0 |
| 搜索 | Alpha-Beta（浅层）→ PVS/迭代加深/静态搜索 | MCTS/PUCT |
| 估值 | 子力+位置表 → 预计算知识表 → NNUE | policy/value 网络 |
| 分析 | 独立进程 MultiPV + WDL | kata-analyze 200 visits + ownership |
| 难度 | 13 档，显式配置 | 未知 |

**不能把两者统称为“象棋/围棋 AI 都是搜索 + 估值”**：中国象棋侧存在三代技术叠加，围棋侧是单一神经 MCTS。

## 2. Just Xiangqi 的三级棋力

### 2.1 第一级：NativeAI（拟人低手）

- 深度 0：随机走法（排除送将）。
- 深度 2：Alpha-Beta + 子力/位置表。
- 作用：新手档（0–1 级）的“会犯错但不像机器”的对手。

### 2.2 第二级：ElephantEyes（传统棋力）

- 迭代加深 + PVS + 静态搜索 + 空着裁剪 + 置换表 + 杀手/历史排序。
- 12,081 条内置开局库。
- 深度 1–5，承担 2–6 级的主力。
- 这是开源 ElephantEyes 的 C# 移植；棋力可预期、资源占用低。

### 2.3 第三级：Pikafish（现代棋力）

- Pikafish 2025-01-10 + NNUE。
- 深度 1–17，承担 3 级以上的混合档与 7–12 级主力。
- 特点：搜索快、估值强；但游戏只给 `go depth N`，不设线程/哈希，默认单线程。

### 2.4 难度不是“削弱引擎”

游戏没有使用 Pikafish 的 `Skill Level`/`UCI_LimitStrength`，而是：

```text
难度 = 引擎选择 + 搜索深度 + MultiPV 随机采样 + 开局库
```

随机采样规则：在前 `Randomness` 条候选中随机选；若最佳是杀棋或分差 >100 厘兵，则强制回最佳。这样既保留“会失误”的拟人感，又避免明显送子。 [已验证]

## 3. Just Go（背景，不计入交付）

> 该产品未购买、主体已卸载；以下仅来自残留 GTP 日志，不能作为对比结论。

- KataGo v1.10.0，b40c256 网络，Eigen CPU 4 线程。
- 对弈：`genmove`，时间控制，单步 5–9 秒，访问数可达 1,706。
- 分析：`kata-analyze 200 ownership true`，固定 200 visits，输出候选、胜率、目差、归属。
- 难度机制不可见；从引擎能力看，最可能通过访问数/时间或搜索噪声调节，但**无证据**。

## 4. 搜索机制细节对比

| 机制 | game-01 | game-02 |
|---|---|---|
| 迭代加深 | 有（ElephantEyes；Pikafish 内部） | MCTS 按访问数扩展，非传统 ID |
| Alpha-Beta/PVS | 有 | 无 |
| 静态搜索 | 有 | 不适用（MCTS  rollout/价值网络） |
| 置换表 | 有（约 100 万槽，2 层） | 引擎内部（未暴露） |
| Zobrist | 有（预生成表） | 引擎内部 |
| 空着裁剪 | 有（NULL_DEPTH=2） | 不适用 |
| 杀手/历史排序 | 有 | 不适用 |
| 开局库 | 有（两套） | 未发现 |
| 神经网络 | NNUE（Pikafish） | policy+value+ownership |
| 多候选输出 | MultiPV 3/5 | kata-analyze 多 move |
| 胜率输出 | `wdl` | `winrate` |
| 目/分差 | `cp`（厘兵） | `scoreLead`（目） |

## 5. 棋力上限与可信度

- game-01 最高档 depth 16/17 + NNUE，理论上远超人类；但默认单线程、无开局库（高档），实际棋力未做对局标定。 [未知]
- game-02 使用职业级 KataGo 网络，但 CPU Eigen 后端 + 4 线程，单步 5–9 秒，棋力仍很强；具体段位未标定。 [未知]
- 两者的 ELO 标签（100–2800）是产品化段位，不是引擎实测 Elo。 [有证据支持：ELO 表与难度配置人为对应]

## 6. 对四国军棋的启示

1. 四国军棋是不完全信息、四人协作/对抗，不能直接套用象棋/围棋搜索；但“多档引擎 + 有偏采样”的难度设计可直接借鉴。
2. 若主工程已有 GNN/自我对弈，应把“强 AI”作为分析/评分后端，把“弱 AI”作为陪练前端，二者分离。
3. 难度不应靠降低网络精度（会显得“傻”），而应靠候选采样与搜索预算，配合“不可送子”的安全阈值。
4. 分析功能应独立于对弈引擎，避免复盘占用对弈资源。

## 7. 证据索引

- game-01：`game-01/report/04-ai-decision-chain.md`、`05-search-algorithm.md`、`06-evaluation.md`、`07-difficulty.md`
- game-02：`game-02/report/04-ai-decision-chain.md`、`05-search-algorithm.md`、`06-evaluation.md`
