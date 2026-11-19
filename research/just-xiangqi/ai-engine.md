# Just Xiangqi AI 引擎逆向

## 1. 三路引擎

| 引擎 | 实现 | 使用档位 | 证据 |
|---|---|---|---|
| NativeAI | 自研 Alpha-Beta + 子力/位置表 | 0–1 | `NativeAI.cs` |
| SharpElephantEyes | C# 移植 ElephantEyes：迭代加深 + PVS + 静态搜索 + 置换表 + 空着裁剪 + 杀手/历史 + 12,081 条开局库 | 2–6 | `Search.cs`、`Book.cs` |
| Pikafish | 外部 UCI 进程 + NNUE | 3 起混合、7–12 主力 | `ProcessManager.cs`、REA |

## 2. 决策链

```text
点击/拖拽 → ChessBoard 更新
→ MakeNextMoveByAI (GameManager.cs:3588)
   → GetSimpleKillMove 一步杀捷径
   → 取难度配置 AIOptions
   → NativeAI / ElephantEyes / Pikafish 分支
→ 4 字符着法 → 动画 → 落子
```

- 对局与分析各一个 `pikafish.exe`；分析进程设置 `UCI_ShowWDL`，复盘/训练 MultiPV=3，其余 MultiPV=5。
- Pikafish 分支：`position fen` + `go depth N`；2 秒无 `bestmove` 补 `stop`。

## 3. 搜索机制

### NativeAI
- depth 0：随机走法（过滤送将）。
- depth 2：根节点枚举 + Alpha-Beta，子力差或子力+位置表。

### ElephantEyes
- 迭代加深 1..N，支持时间/节点预算。
- `SearchPV` 全窗口、`SearchCut` 零窗口（PVS）。
- 静态搜索 `SearchQuiesc`；空着裁剪 `NULL_DEPTH=2`。
- 置换表 `NewHash(24)`：约 100 万槽，2 层，双 32 位 Zobrist 锁。
- 着法排序：Hash → 好吃 → 杀手1/2 → 非吃 → 其余，带 65,536 项历史表。
- 开局库：12,081 条 `(ZobristLock, move, value)`；另有文本 `Book/Openings`。

### Pikafish
- Stockfish 系 PVS/迭代加深 + NNUE；REA/Ghidra 证实 `TranspositionTable`、`SearchManager`、`Thread`、`Eval::NNUE::Network`。
- 默认 Threads=1、Hash=16 MB（游戏未设置）；只设 MultiPV。

## 4. 难度机制

- 13 档（0–12），ELO 100–2800；生涯另 16 档。
- 降级方式：引擎类型 + 深度 + **MultiPV 前 N 随机采样** + 开局库。
- 随机采样：`Random.Range(0, min(count, Randomness))`；若最佳为杀棋或分差 >100 厘兵，强制回最佳。
- 同档可挂多套配置，开局随机抽一套并整局固定。
- 未使用 Pikafish `Skill Level` / `UCI_LimitStrength`（REA 证实引擎具备该选项，但客户端未调用）。

## 5. REA Evidence

| 结论 | 证据 |
|---|---|
| Stockfish 系实现 | `TranspositionTable::clear` RTTI @ `0x14014a518`；`SearchManager` @ `0x140149a96` |
| NNUE | `pikafish.nnue` @ `0x140136b80`；`Eval::NNUE::Network` @ `0x140138e18` |
| UCI | `setoption` @ `0x14014aaf2`；`info depth ` @ `0x14014b0e0`；` multipv ` @ `0x14014b10c` |
| 分析/对弈双实例 | 运行时两个 `pikafish.exe`，父进程为游戏 |

完整 evidence_id 与地址见 `reverse-engineering/evidence/game-01/rea-evidence-summary.md`。

## 6. 对四国军棋的可迁移点

1. 强引擎只做分析与评分后端，陪练 AI 用可控预算 + 候选采样。
2. 同档多配置 + 整局固定，制造风格差异。
3. 候选随机必须配“安全阈值”，防止送子/送旗。
4. 分析与对弈引擎实例分离，复盘不污染对局。
5. 象棋的 Alpha-Beta/NNUE 不能直接用于不完全信息四人博弈；四国需信念采样与团队价值。
