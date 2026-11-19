# 报告 04：AI 决策调用链（game-01）

## 1. 总链

```text
玩家点击/拖拽棋子
  → ChessBoard 更新棋盘、PreviousFens、Moves
  → GameManager 判定终局/禁手
  → MakeNextMoveByAI()                        GameManager.cs:3588
      → 先查“一步杀” GetSimpleKillMove()       （命中则直接走，不进引擎）
      → 选择难度配置 Constants.AI_CONFIGURATIONS[level]
      → 取当前步数的 AIOptions（含开局步数覆盖）
      → 按 Type 分派：
          Native_Easy / Native_Medium  → NativeAI.GetNextMove
          ElephantEyes_Local          → ElephantEyesAI.GetNextMove
          Pikafish_Process            → ProcessManager.GetNextMove
      → 返回 4 字符坐标着法
  → PlayAIMoveAnimation()                     动画与思考时长模拟
  → ChessBoard 落子，进入下一回合
```

## 2. 入口与前置

`MakeNextMoveByAI` 先执行 `chessBoard.GetSimpleKillMove(currentPieceColor)`：若存在可立即吃将的着法，直接采用，不调用搜索引擎（`GameManager.cs:3590`）。这是一条独立于三引擎的“战术捷径”。 [已验证]

难度键的选择：

- 普通单机/残局：`defaultAILevel`。
- 生涯 AI 对战：玩家回合用 `defaultAILevel`，对手用 `opponentAILevel`（`GameManager.cs:3597-3599`）。
- 生涯单机：按 `CareerModePlayer.GetAILevel(gamePhase)` 动态取级（`GameManager.cs:3600-3605`）。

## 3. 配置选择

```csharp
List<AIConfiguration> list = (生涯三模式 ? Constants.CAREER_MODE_AI_CONFIGURATIONS : Constants.AI_CONFIGURATIONS)[key];
if (!cachedAIConfigs.ContainsKey(key))
    cachedAIConfigs[key] = Random.Range(0, list.Count);
AIOptions param = list[cachedAIConfigs[key]].GetAIOptionsByStep(chessBoard.Moves.Count / 2 + 1);
```

要点：

- 同一难度可挂多套配置，进入对局时随机抽一套并缓存整局（`GameManager.cs:3607-3611`）。
- `GetAIOptionsByStep` 允许“前 N 步使用指定 AI”（如 0–3 步走开局库），之后回落到默认参数（`AIConfiguration.cs:12-17`）。

## 4. 三个分支

### 4.1 NativeAI

```csharp
((NativeAI)process).SetBoard(chessBoard);
text = await Task.Run(() => ((NativeAI)process).GetNextMove(param.Depth, currentPieceColor));
```

- 先深拷贝棋盘（`SerializationUtility.CreateCopy`），避免搜索污染实时棋盘。
- `depth == 0` 走 `GetRandomMove`：枚举所有走法，过滤“走后立即被将死”的着法，再随机取一（`NativeAI.cs:83-96`）。
- `depth > 0` 走根节点枚举 + `AlphaBeta(depth-1, ...)`（`NativeAI.cs:98-119`）。

### 4.2 ElephantEyes

```csharp
((ElephantEyesAI)process).SetFenPosition(FEN + " " + side);
((ElephantEyesAI)process).SetBanMoves(banMoves);
text = await Task.Run(() => ((ElephantEyesAI)process).GetNextMove(param.Depth, param.UseBookMoves));
```

- `UseBookMoves` 为真时先查 `Book`：命中则从所有书中着法随机选一条（`ElephantEyesAI.cs:36-43`）。
- 未命中则提交内部 UCCI `analyze` 命令，等待 `is_analyzing` 结束，返回 `best_move`（`ElephantEyesAI.cs:44-54`）。
- `banMoves` 来自长将/长捉/重复局面列表（`GameManager.cs:3610-3614`）。

### 4.3 Pikafish

```csharp
PromptInput("position fen " + fen + " " + side);
List<MoveAnalysis> list = await Task.Run(() => pm.GetNextMove(param.Depth, banMoves));
MoveAnalysis best = list.First();
int index = Random.Range(0, Math.Min(list.Count, param.Randomness));
MoveAnalysis chosen = list[index];
if (best.IsMateInNSteps || Math.Abs(best.CentipawnValue - chosen.CentipawnValue) > 100)
    chosen = best;
```

关键行为：

- `ProcessManager.GetNextMove` 发送 `go depth N`；若 2 秒内没有 `bestmove`，补发 `stop`（`ProcessManager.cs:101-109`）。
- 解析只保留 `info depth N` 行，提取 `multipv`、`cp`、`mate`、`pv`、`wdl`（`ProcessManager.cs:160-214`）。
- **难度随机化**：在 MultiPV 前 `Randomness` 条中随机选一条；若最佳着法是杀棋，或与随机着法的分值差超过 100 厘兵，则强制回到最佳着法（`GameManager.cs:3658-3672`）。
- `UseBookMoves` 为真且当前 FEN 在 `Book/Openings` 中时，直接随机取书着（`GameManager.cs:3635-3643`）。
- 若返回列表为空，则 `Resign(currentPieceColor)`（`GameManager.cs:3677-3681`）。

## 5. 动态验证

启动《Just Xiangqi》，进入“人机对战”，点击“开始”后观察进程：

```text
JustXiangqi.exe  PID 20740
pikafish.exe     PID 61116  Parent 20740
pikafish.exe     PID 8600   Parent 20740
CommandLine: "D:/SteamLibrary/steamapps/common/Just Xiangqi/JustXiangqi_Data/StreamingAssets\AI\PikaFish\pikafish.exe"
```

两个子进程分别对应 `cchessAIDict[Pikafish_Process]` 与 `analysisAIProcess`（`GameManager.cs:1163/1166`）。 [已验证]

## 6. 本地 AI 与远程 AI 的区分

- AI 决策完全在本地：C# 搜索、C# ElephantEyes、本地 `pikafish.exe`。
- 网络只用于 Photon 联机、Steam 身份/成就；未发现“把 FEN 上传服务器、返回着法”的接口。
- 因此不存在“客户端请求接口冒充 AI 算法”的情况；反过来，也不能把 Photon 的房间同步误认为 AI。 [已验证]

## 7. 未证实部分

- Pikafish 的多线程/哈希设置：代码只设置 `MultiPV`，未设置 `Threads`/`Hash`，因此使用引擎默认值（Threads=1、Hash=16）。 [有证据支持：`rg "setoption"` 仅命中 MultiPV / ShowWDL]
- `GetSimpleKillMove` 的完整实现细节未逐行审计。 [有证据支持]
- 动画时长与“思考时间”的映射只影响观感，不参与决策。 [已验证：`PlayAIMoveAnimation` 只读 `thinkingTimeSpan` 做等待]
