# 三平台相关参考项目调研（GitHub / HuggingFace / Kaggle）

日期：2026-11-19
背景：为 P8 棋力评测、P9 训练升级、P10 评分校准寻找可借鉴的现成方案。遵循 AGENTS.md「先查成品、避免重复造轮子」。
检索方式：`websearch` 返回 422/402（配额限制），`webfetch`/DuckDuckGo Lite 触发人机验证；最终使用 **gh CLI 搜索 GitHub**、**HuggingFace Hub API**、**Kaggle datasets API**（均清空未启动的代理 `127.0.0.1:7899` 后直连成功）。所有结果来自 API 实时返回，非凭记忆。

## 1. GitHub（gh search repositories，实时返回）

| 项目 | Stars | 许可 | 相关性 |
|---|---:|---|---|
| `suragnair/alpha-zero-general` | 4533 | （查 README） | **高**：任意棋盘游戏的 AlphaZero 实现，含 `Arena.playGames(num)` 双人对战评测（返回 oneWon/twoWon/draws）、多种游戏（Othello/Gobang/Connect4）；直接对应本项目 P8 对战评测与 P9 self-play。 |
| `blanyal/alpha-zero` | 94 | — | 中：Othello/Connect4/TicTacToe 的 AlphaZero 实现，self-play 训练参考。 |
| `Yoshie2000/PlentyChess` | 162 | GPL-3.0 | 中：NNUE 估值的 UCI 引擎（最近仍活跃），可参考引擎对战协议。 |
| `connormcmonigle/seer-nnue` | 147 | GPL-3.0 | 中：NNUE 估值 UCI 引擎。 |
| `HankSheehan/EloPy` | 54 | — | **高**：Python Elo 评级库，可参考对多人/联盟对局的评级扩展思路。 |
| `Mezghenna-Mohanned/ML-Chess-Engine` | 82 | 无 LICENSE | 低：声称 +2500 Elo 的 ML 引擎，无许可，仅思路参考。 |

`Arena.playGames` 的实际结构（读取 `Arena.py` 确证）：`playGame()` 返回 winner/draw；`playGames(num)` 交替双方先手、累计 `oneWon/twoWon/draws`。这与本项目 `eval-harness.js` 的座位轮换 + 胜负统计思路一致，可视为对现有实现的独立印证。

## 2. HuggingFace Hub（api/datasets、api/models、api/spaces）

| 资源 | 下载/热度 | 相关性 |
|---|---:|---|
| `Lichess/standard-chess-games` | 161778 | **高**：大规模真实棋谱，可用于评分校准的「实战棋步→结果」相关性研究（P10）。 |
| `Lichess/chess-openings` | 1648 | 中：开局统计，可作走法覆盖率的外部参照。 |
| `patrickfrank1/chess-pgn-games` | 982 | 中：PGN 棋谱，评估棋谱格式互通。 |
| `shtoshni/gpt2-chess-uci` | 365 | 低：UCI 走法生成模型。 |
| Space `nathanael-fijalkow/chess-post-training` | likes 11 | 低：训练后分析展示参考。 |

## 3. Kaggle（api/v1/datasets/list）

| 数据集 | 相关性 |
|---|---|
| `ronakbadhe/chess-evaluations` | **高**：带引擎评估分的局面数据集，可用于校准「引擎分↔结果」映射（P10）。 |
| `koryakinp/chess-positions` | 中：局面 + 结果标签，可做评分-胜负相关性外部验证。 |
| `datasnaek/chess`、`arevel/chess-games` | 中：Lichess 对局数据，棋步频率baseline。 |
| `surajjha101/fide-chess-rankings-updated` | 低：FIDE 排名，评级体系背景。 |

Kaggle competitions API 返回 401（需登录凭证），未获取竞赛数据——如实记录，未伪造。

## 4. 对本项目的借鉴结论（不复制代码）

1. **对战评测框架**：`alpha-zero-general` 的 Arena（交替先手 + 胜负和统计）与本项目 `eval-harness.js` 一致，印证本项目四座轮换/胜负统计的设计合理；本项目额外做了联盟模式、布阵多样性、Wilson CI、pairwise Elo、座位/布阵分项，覆盖更全。
2. **评级体系**：`EloPy` 提示标准 Elo 面向 1v1；本项目 4 人/联盟场景用 pairwise Elo 代理已在报告中明确口径，避免冒用「正式评级」。
3. **评分校准数据**：HuggingFace `Lichess/standard-chess-games` 与 Kaggle `chess-evaluations` 提供「引擎分↔真实结果」的外部数据可能——但本项目是**四国暗棋**（隐藏信息、联盟），与国际象棋明棋不同，外部明棋数据只能借鉴方法，不能直接用其分值或结论。P10 当前校准基于本项目自身局面与搜索，符合信息边界。
4. **许可边界**：GPL-3.0（PlentyChess/seer-nnue）与无 LICENSE（ML-Chess-Engine）项目**仅作思路参考，不复制代码**；MIT/开源项目同样只吸收设计。本项目主工程 MIT，保持兼容。

## 5. 未采纳/限制
- websearch 工具 402、DuckDuckGo 人机验证：改用平台官方 API 完成检索，结果可审查（命令记录在对话中）。
- Kaggle 竞赛需凭证、HuggingFace 大数据集未下载（仅元数据）：未获取训练数据，未用于本项目，不影响现有交付。
- 这些项目均为国际象棋/通用棋盘游戏，**没有直接的四国军棋暗棋评测框架**；本项目 P8/P9/P10 系基于主工程自研，参考项目仅作方法论印证。
