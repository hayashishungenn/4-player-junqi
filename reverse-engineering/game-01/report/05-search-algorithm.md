# 报告 05：搜索算法分析（game-01）

## 1. 结论

《Just Xiangqi》同时包含**两套传统搜索实现**与**一个外部 NNUE 引擎**：

| 引擎 | 算法家族 | 是否参与实战 | 证据 |
|---|---|---|---|
| NativeAI | 定深 Alpha-Beta（带简单剪枝）+ 随机走法 | 是（低难度） | `NativeAI.cs:98-184` |
| SharpElephantEyes | 迭代加深 + Alpha-Beta/PVS + 静态搜索 + 置换表 + 空着裁剪 + 历史/杀手着法 + 开局库 | 是（中低难度） | `Search.cs`、`MoveSort.cs`、`Hash.cs` |
| Pikafish 2025-01-10 | Stockfish 系 PVS/迭代加深 + NNUE + 置换表 + 多规则支持 | 是（高难度与全部复盘分析） | 外部 exe，UCI 输出 |

未发现 MCTS、Beam Search、神经网络估值参与 C# 引擎；NNUE 仅存在于 Pikafish。 [已验证]

## 2. NativeAI

- 根节点：枚举己方全部走法，逐个落子，调用 `AlphaBeta(depth-1, -∞, +∞, false)`（`NativeAI.cs:107-117`）。
- Alpha-Beta：标准 fail-hard 实现，`beta <= alpha` 时截断（`NativeAI.cs:121-167`）。
- 无置换表、无迭代加深、无静态搜索、无着法排序。
- `depth == 0` 完全随机（过滤送将着法），`depth == 2` 为两层的子力/位置评估。

## 3. SharpElephantEyes

### 3.1 迭代加深

`SearchMain(nDepth)` 从 1 层循环到目标深度，每层调用 `SearchRoot(j)`；根据时间/节点数、PV 稳定性（`nUnchanged >= 4`）提前收缩预算（`Search.cs:616-700`）。支持三种 `nGoMode`：无限、按节点、按时间。

### 3.2 Alpha-Beta / PVS

- `SearchPV(alpha, beta, depth, pv)`：全窗口主变例搜索（`Search.cs:398`）。
- `SearchCut(beta, depth)`：零窗口探测（`Search.cs:286`）。
- 内部迭代加深（IID）：`IID_DEPTH = 2`，在 PV 节点先以 `depth/2` 搜索取得着法（`Search.cs:121`、`:436-447`）。
- 静态搜索：`SearchQuiesc`（`Search.cs:222`），只扩展吃子，配合 `HarmlessPruning`（无害裁剪）。
- 唯一着法提前结束：`SearchUnique(-9799, j)`（`Search.cs:597`）。

### 3.3 空着裁剪

```csharp
if (search.bNullMove && !bNoNull && search.pos.LastMove().ChkChs <= 0 && search.pos.NullOkay())
{
    num = -SearchCut(1 - vlBeta, nDepth - 2 - 1, bNoNull: true);
    ...
}
```

`NULL_DEPTH = 2`，被将军时不启用（`Search.cs:317-335`、`:127`）。

### 3.4 置换表

- `Hash.NewHash(24)`：`nHashMask = (1 << 24) / 16 - 1 = 1,048,575`，约 100 万槽（`Hash.cs:56-66`、`ElephantEyesAI.cs:18`）。
- 每个槽保存两层（`HASH_LAYERS = 2`）：`wmv`、`alpha/beta` 深度与分值、双 32 位 Zobrist 锁（`Hash.cs:5-34`）。
- 查询/写入：`ProbeHash`、`RecordHash`；节点类型 `HASH_BETA/HASH_ALPHA/HASH_PV`（`Search.cs:301/377/394`）。

### 3.5 Zobrist

- `ZobrInit.cs`（537 KB）为预生成的 Zobrist 随机表；`Pregen.ZobristStruct` 保存 `dwKey/dwLock0/dwLock1`（`Pregen.cs:35`）。
- 走子/吃子时增量更新，用于置换表与开局库索引。

### 3.6 着法排序

`MoveSort` 采用分阶段排序（`MoveSort.cs:348-360`）：

```text
PHASE_HASH → PHASE_GEN_CAP → PHASE_GOODCAP → PHASE_KILLER1 → PHASE_KILLER2
→ PHASE_GEN_NONCAP → PHASE_REST
```

配合 65,536 项历史表 `nHistory`（`MoveSort.cs:346`）、杀手着法数组 `wmvKiller[64,2]`（`Search.cs:94`）、Shell 排序（`MoveSort.cs:107`）。

### 3.7 开局库

- 内置 12,081 条 `(ZobristLock, move, value)`（`Book.cs:20`）。
- `Ucci.GetBookMoves()` → `Book.get_book_moves(pos)`（`Ucci.cs:149-152`）；命中后按权重/随机选一条（`ElephantEyesAI.cs:36-43`）。
- 另有文本开局库 `Book/Openings`，由 `GlobalVariable` 加载，供 Pikafish 分支与复盘“Book”标注使用（`GlobalVariable.cs:82-104`）。

### 3.8 规则相关搜索约束

- 重复局面/长将/长捉：`ChessBoard` 生成 `ForbiddenMoves`、`DrawMoves`，作为 `banMoves` 传入引擎（`GameManager.cs:3610-3614`；`Ucci.BanMoves` `Ucci.cs:79`）。
- 引擎内部也有 `IsDraw()`、`RepStatus(3)` 检查（`Search.cs:619-624`）。

## 4. Pikafish

- 版本：`Pikafish 2025-01-10`（UCI `id name`）。
- 搜索：调用方只发 `go depth N`，引擎内部执行迭代加深/PVS/NNUE；`ProcessManager` 不干预。
- 超时保护：2 秒未返回 `bestmove` 则 `stop`（`ProcessManager.cs:103-109`）。
- 规则支持：UCI 选项含 `Repetition Rule`（AsianRule/ChineseRule/SkyRule/ComputerRule/YitianRule/AllowChase）与 `Draw Rule`；游戏代码未设置这些选项，使用默认 `AsianRule` / `None`。 [已验证：仅 `setoption MultiPV` 与 `setoption UCI_ShowWDL` 出现在代码中]
- 搜索资源：未设置 `Threads`/`Hash`，使用默认 1 线程、16 MB 置换表。 [有证据支持]

## 5. 未发现/未使用

| 算法 | 结论 |
|---|---|
| MCTS | 未发现（C# 与 Pikafish 均非 MCTS） |
| Beam Search | 未发现 |
| 神经网络估值（C# 内） | 未发现；NNUE 在 Pikafish 内部 |
| 终局数据库 | 未发现独立残局库；残局以题目列表 `Book/Endgames` 形式存在 |
| 定式库 | 开局库承担该角色（两套：文本 + 内置二进制表） |
