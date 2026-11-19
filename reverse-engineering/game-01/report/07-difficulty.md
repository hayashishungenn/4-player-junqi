# 报告 07：AI 难度机制（game-01）

## 1. 难度总览

- 普通对局 **13 档**（`0..12`），ELO 从 100 到 2800（`Constants.cs:1913`）。
- 生涯模式另有一套 **16 档**（`1..16`）配置字典 `CAREER_MODE_AI_CONFIGURATIONS`，按剧情阶段取级。
- 难度**不是**通过 Pikafish 的 `Skill Level` / `UCI_LimitStrength` 实现；代码从未设置这两个选项（`rg "setoption"` 仅命中 `MultiPV`、`UCI_ShowWDL`）。 [已验证]
- 难度由四个旋钮组合：**引擎类型**、**搜索深度**、**候选随机性 `Randomness`**、**是否用开局库**。

## 2. 13 档配置（普通对局）

| 档位 | 代码英文名 | ELO | 主配置 | 深/随机 | 前 3 步特殊配置 |
|---:|---|---:|---|---|---|
| 0 | Newcomer | 100 | Native_Easy depth 0 → Native_Easy depth 2 | 0 / 1 | ElephantEyes depth 2 + 开局库 |
| 1 | Beginner | 200 | Native_Medium depth 2 | 2 / 1 | ElephantEyes depth 2 + 开局库 |
| 2 | Novice | 400 | ElephantEyes depth 1 | 1 / 1 | — |
| 3 | Apprentice | 600 | Pikafish depth 1 或 2，或 ElephantEyes 2（三套随机抽一） | 1–2 / 3 | — |
| 4 | Learner | 900 | ElephantEyes 3 或 Pikafish 3 | 3 / 3 | — |
| 5 | Amateur | 1200 | ElephantEyes 4 或 Pikafish 4 | 4 / 3 | — |
| 6 | Intermediate | 1500 | ElephantEyes 5 或 Pikafish 5 | 5 / 3 | — |
| 7 | Qualified（界面验证为“专家 / 三级棋士”） | 1800 | Pikafish 6（两套，随机 2/3） | 6 / 2–3 | — |
| 8 | Proficient | 2000 | Pikafish 7（两套，随机 2） | 7 / 2 | — |
| 9 | Experienced | 2150 | Pikafish 8 或 9 | 8–9 / 1 | — |
| 10 | Expert | 2400 | Pikafish 10 或 11 | 10–11 / 1 | — |
| 11 | Master | 2550 | Pikafish 13 或 14 | 13–14 / 1 | — |
| 12 | Grandmaster | 2800 | Pikafish 16 或 17 | 16–17 / 1 | — |

数据来源：对 `Constants.cs:1919` 起的 `AI_CONFIGURATIONS` 做结构化解析；英文名来自 `Utils.GetAINameByLevel`（`Utils.cs:449`）；ELO 来自 `AI_ELO_RATING`。

**中文名称的验证度**：只直接验证了“档 7 = 专家 / 三级棋士 / ELO 1800”（截图与 `AI_ELO_RATING[7]` 一致）。其余档位的中文“棋士等级”文案由 I2.Loc 运行时翻译，未逐档截图核对，标为 [有证据支持] 而非已验证。

## 3. 界面上的难度分档

实际运行截图（`evidence/game-01/screen-12-difficulty-level.png`）显示官方分档说明：

- 普通象棋爱好者：新手、初学者、入门、学徒。
- 县级棋手：进阶、业余、熟手、专家。
- 省级棋手：职业、地方大师、棋协大师。
- 国家/世界级棋手：国家大师、特级大师。

与 13 档一一对应。 [已验证：截图 + 代码]

## 4. 随机性机制

`AIOptions.Randomness` 表示“从 MultiPV 前 N 条中随机选一条”：

```csharp
int index = Random.Range(0, Math.Min(list.Count, param.Randomness));
MoveAnalysis chosen = list[index];
if (best.IsMateInNSteps || Math.Abs(best.CentipawnValue - chosen.CentipawnValue) > 100)
    chosen = best;   // 杀棋或分差>100厘兵时回退最佳着法
```

- 低档位（3–6）Randomness 为 3，相当于在前三候选里“故意不选最优”。
- 高档位（7–8）Randomness 为 2。
- 9 档以上 Randomness 缺省为 1，即总是选第一候选，纯靠深度提升棋力。

这是“拟人化失误”的核心实现：**不削弱引擎，只在候选着法里做有偏采样**，同时用 100 厘兵阈值防止明显送子。 [已验证]

## 5. 多配置随机

同一档位可挂多套 `AIConfiguration`。进入对局时：

```csharp
if (!cachedAIConfigs.ContainsKey(key))
    cachedAIConfigs[key] = Random.Range(0, list.Count);
```

整局固定使用抽中的那套，避免同一局内风格跳变。 [已验证]

## 6. 开局库与步数覆盖

- `AIConfiguration.PredefinedAI` 用 `StepRange(0,3)` 指定前 3 步使用 `ElephantEyes_Local + UseBookMoves`，之后回落到默认配置（`AIConfiguration.cs:12-17`；档 0、1）。
- Pikafish 分支也可用 `Book/Openings`：若当前 FEN 在库中，直接随机取书着，不启动搜索（`GameManager.cs:3635-3643`）。
- 复盘评分把前 20 步内、且与开局库一致的着法标记为 `Book`（`GameManager.cs:2760-2767`）。

## 7. 生涯模式

- `CareerModePlayer.GetAILevel(gamePhase)` 按剧情阶段返回等级（`CareerModePlayer.cs:209`）。
- 训练模式最低 10 级（`CareerModeTraining.cs:34`：`Math.Max(..., 10)`），默认 15 级（`Constants.cs`：`DEFAULT_TRAINING_MODE_AI_LEVEL = 15`）。
- 生涯配置键为 1–16；其 ELO 展示改用角色自带的 `EloScore`，不查 `AI_ELO_RATING` 数组（避免 13 项数组越界）。

## 8. 未知与限制

- `CAREER_MODE_AI_CONFIGURATIONS` 的 16 档逐档参数未展开列表（结构同普通表，量较大）。
- Pikafish 的实际棋力上限未做对局测试；档 12 为 depth 16/17，配合默认 1 线程。
- 难度与胜率的标定过程（为何 1800 ELO 对应 depth 6）无文档，属设计选择。 [未知]
