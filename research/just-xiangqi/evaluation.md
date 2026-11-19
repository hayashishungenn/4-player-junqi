# Just Xiangqi 估值与评分

## 1. 三层估值

| 层 | 方法 | 证据 |
|---|---|---|
| NativeAI Easy | 纯子力差 | `NativeAI.cs:186` |
| NativeAI Medium | 子力 + 炮/马/车/兵位置表 | `NativeAI.cs:16-70`、`:209` |
| ElephantEyes | 预计算知识表 `PreEval`；可退回 `Material()` | `Search.cs:158-166`、`Pregen.cs:157` |
| Pikafish | NNUE 网络 | `pikafish.nnue`、REA 符号 |

## 2. NativeAI 权重

```csharp
PieceValues = { 2500, 23, 23, 108, 233, 101, 44 }
// General, Advisor, Elephant, Horse, Chariot, Cannon, Solider
```

- 将 2500，车 233，炮 101，马 108，兵 44，士/象 23。
- 位置表 10×9；黑方镜像 `(9-x, y)`。
- `ImprovedEvaluate = 子力 + 位置 * 8`，位置因素可接近子力量级。
- 士/象/将无位置表，返回 -1。

## 3. ElephantEyes

- `Search.Evaluate(pos, alpha, beta)`：`bKnowledge` 为真时用 `pos.Evaluate`，否则 `pos.Material()`。
- 评估在静态搜索叶子执行；具体权重由 `Pregen` 预生成，未逐项展开。
- 置换表存 alpha/beta 分值，用于剪枝与着法排序。

## 4. NNUE

- 网络文件 45.5 MB，UCI `EvalFile` 默认 `pikafish.nnue`。
- REA/Ghidra 证据：`Eval::NNUE::Network` RTTI、`NNUE evaluation` 输出字符串。
- 网络结构/训练数据未在包内暴露，标为未知。

## 5. 复盘评分

- 引擎输出：`cp`（厘兵）、`mate`（步数）、`wdl`（胜/和/负千分比）。
- 标签：`BestMove / Good / Book / Inaccuracy / Mistake / Blunder / Missed / Unknown`。
- 阈值：
  - `|cp| <= 1000`：绝对 50 / 200 / 700 / 1000。
  - `|cp| > 1000`：相对百分比，`base=|cp|*0.01+10`，Good=base、Inaccuracy=2.5×、Mistake=4×。
  - 本步 `cp < -100` 时阈值 ×1.5（劣势方更宽容）。
  - 杀棋单独判定：漏杀、被杀、杀步数比较。
  - 前 20 步命中开局库标 `Book`。
- 界面把分值映射为“绝杀/杀 N 步/均势/小优/中优/大优/和棋率/胜率”。

## 6. 对四国军棋的启示

1. 评分标签比原始分数更可用；但四国军棋必须从“走子前信息集”计算，不能用赛后真实棋子。
2. 阈值应随优势变化，并增加置信度（采样方差）。
3. 杀棋/夺旗等战术必须单独判定，不能混入普通失误。
4. 未校准前不显示胜率，只显示相对评分与置信度。
