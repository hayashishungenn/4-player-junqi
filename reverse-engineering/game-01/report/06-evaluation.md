# 报告 06：局面估值分析（game-01）

## 1. 三套估值并存

| 引擎 | 估值方式 | 证据 |
|---|---|---|
| NativeAI Easy | 纯子力差 | `NativeAI.cs:186-207` |
| NativeAI Medium | 子力 + 位置表（炮/马/车/兵） | `NativeAI.cs:209-248` |
| SharpElephantEyes | 位置知识 + 子力（`Position.Evaluate` 或 `Material`），带 alpha/beta 窗口 | `Search.cs:158-166` |
| Pikafish | NNUE 神经网络（`pikafish.nnue`，45.5 MB） | 文件与 UCI 启动参数 |

## 2. NativeAI 子力价值

```csharp
private int[] PieceValues = new int[7] { 2500, 23, 23, 108, 233, 101, 44 };
```

按 `CCEnum.PieceType` 顺序：General 2500、Advisor 23、Elephant 23、Horse 108、Chariot 233、Cannon 101、Solider 44。将的价值远高于其他子力，等价于“将被吃即败”的极大惩罚。 [已验证]

## 3. NativeAI 位置表

四张 10×9 表：`CannonPositions`、`HorsePositions`、`ChariotPositions`、`SoliderPositions`（`NativeAI.cs:16-70`）。

- 红方直接取 `[x,y]`；黑方先做 `(9-x, y)` 镜像（`NativeAI.cs:239`）。
- 士/象/将无位置表，返回 -1，即只计子力。
- `ImprovedEvaluate` 将子力与位置分相加，位置分乘以 8：

```csharp
int num2 = redMaterial + redPosition * 8;
int num3 = blackMaterial + blackPosition * 8;
return (pieceColor == Red) ? num2 - num3 : num3 - num2;
```

位置分数量级（兵最高 120、车最高 26）远小于子力（车 233），乘 8 后位置因素可达到与子力同一量级。 [已验证]

## 4. SharpElephantEyes 估值

- `Search.Evaluate(pos, alpha, beta)`：若 `search.bKnowledge` 为真，调用 `pos.Evaluate(alpha, beta)`，否则只用 `pos.Material()`（`Search.cs:158-166`）。
- `Position.cs`（74 KB）内含预计算评估表（`PreEvalStruct`，`Pregen.cs:157`）与知识评估，包含棋子位置、兵过河、车炮机动等传统特征。具体权重未逐项逆向（表由 `Pregen` 预生成）。 [有证据支持]
- 评估发生在静态搜索的叶子节点，配合 `HarmlessPruning` 做无害裁剪（`Search.cs:139-156`）。

## 5. Pikafish / NNUE

- `pikafish.nnue` 45.5 MB，随包分发；启动时由引擎自动加载（UCI 选项 `EvalFile` 默认 `pikafish.nnue`）。
- 网络结构与训练数据未在包内暴露；无法从二进制恢复其训练细节。 [未知]
- 输出为 `score cp` 或 `score mate`，复盘功能直接消费该分值（`ProcessManager.ExtractPVValues`）。

## 6. 评分的“人类可读”转换

复盘界面把厘兵分转换为胜率/优势档：

- `MoveAnalysis.CentipawnValue` 直接来自 UCI `cp`。
- `WinRate/DrawRate/LoseRate` 来自 `UCI_ShowWDL` 的 `wdl` 三元组（`ProcessManager.cs:203-210`）。
- 棋盘悬浮文案按分值分档：`ReviewMove_HoverOver_CheckMate`、`MateInNStep`、`Even`、`Red_SmallAdv/MediumAdv/LargeAdv`、`Black_*`、`DrawRate`、`WinRate`（`Constants.cs:461-481`）。

## 7. 未证实

- SharpElephantEyes 的具体特征权重表未展开为可读数据；只能确认存在预计算评估表与知识开关。
- Pikafish NNUE 的网络架构、输入特征、训练集：包内无元数据，标记未知。
- 子力价值 2500/23/23/108/233/101/44 的来源与调参过程未知。

## 8. REA / Ghidra 证据

- 网络文件：`pikafish.nnue` @ `0x140136b80`；`EvalFile` @ `0x140136cf5`。
- NNUE 类：`N9Stockfish18LazyNumaReplicatedINS_4Eval4NNUE7NetworkEEE` @ `0x140138e18`。
- 运行提示：`NNUE evaluation` @ `0x140138162`、`info string NNUE evaluation using ` @ `0x1401397f8`。
- 与游戏侧 `pikafish.nnue`（45.5 MB）文件、UCI 选项 `EvalFile` 一致。

详见 `evidence/game-01/rea-evidence-summary.md`。
