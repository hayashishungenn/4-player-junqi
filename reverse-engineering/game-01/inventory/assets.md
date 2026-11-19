# game-01 资源清单（AI 与棋谱）

## 1. StreamingAssets/AI

| 路径 | 大小 | 说明 |
|---|---:|---|
| `AI/PikaFish/pikafish.exe` | 1,512,448 | 默认 UCI 引擎（含多指令集分派） |
| `AI/PikaFish/pikafish-avx2.exe` | 1,510,400 | AVX2 变体 |
| `AI/PikaFish/pikafish-avx512.exe` | 1,464,832 | AVX-512 变体 |
| `AI/PikaFish/pikafish-avx512f.exe` | 1,472,512 | AVX-512F 变体 |
| `AI/PikaFish/pikafish-avxvnni.exe` | 1,455,616 | AVX-VNNI 变体 |
| `AI/PikaFish/pikafish-bmi2.exe` | 1,456,640 | BMI2 变体 |
| `AI/PikaFish/pikafish-sse41-popcnt.exe` | 1,508,352 | SSE4.1/POPCNT 变体 |
| `AI/PikaFish/pikafish-vnni512.exe` | 1,462,784 | VNNI-512 变体 |
| `AI/PikaFish/pikafish.nnue` | 45,508,991 | NNUE 评价网络 |
| `AI/PikaFish_Deprecated/*` | ~100 MB | 旧版引擎与旧网络，代码中未见引用（[推测] 仅保留兼容） |

代码只启动 `pikafish.exe`（`GameManager.cs:1163`、`:1166`），未见按 CPU 指令集选择变体的逻辑 [已验证：`rg "pikafish-"` 无结果]。

## 2. StreamingAssets/Classic

24 个 `ClassicMatch_1..24.game`，合计约 3.0 MB，内容为 Odin 序列化的 `GameRecord` JSON（UTF-8 BOM、CRLF、GUID 未加引号）。示例 `ClassicMatch_1.game`：

- `BoardStartFen`：`rnbakabnr/9/1c5c1/p1p1p1p1p/9/P1P1P1P1P/1C5C1/9/RNBAKABNR`
- `$rlength` = 25，着法为 4 字符坐标（`h2e2`、`h7e7`、`h0g2` …）
- `MoveNotations`：按语言的记谱字典（含 `Chinese (Simplified)`）
- `GameResult`、`PieceMaterial`、`GameScene`、`GameTime`、`MatchDate`、`MatchDuration`

这些文件是“名局/经典对局”播放数据，不参与 AI 搜索。

## 3. Resources 内的书库

| 资源 | 引用位置 | 用途 |
|---|---|---|
| `Book/Openings` | `GlobalVariable.cs:82-104`，`Resources.Load("Book/Openings")` | 开局库。逐行按空格切分：`[0]` 着法、`[2]` FEN、`[3]` 行棋方、`[7]` 步数；构建 `Dictionary<"FEN side", List<move>>` 与按颜色的 `HashSet<FEN>` |
| `Book/Endgames` | `GlobalVariable.cs:106-109` | 残局/练习题列表，训练与残局模式使用 |

另有代码内置开局库 `SharpElephantEyes/Book.cs`：`book = new BookStruct[12081]`（第 20 行），每条为 `(uint dwZobristLock, ushort wmv, ushort wvl)`。

## 4. 原生组件

仅 `JustXiangqi_Data/Plugins/x86_64/steam_api64.dll`（Steamworks）。无 JNI、无 ARM 库、无其他 `.so`。
