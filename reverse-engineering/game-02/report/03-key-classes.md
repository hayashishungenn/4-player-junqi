# 报告 03：关键类与方法清单（game-02）

## 1. 可确认的类

由于 `Assembly-CSharp.dll` 随主体卸载而缺失，无法进行 ILSpy 反编译。仅能从 Odin 存档的 `$type` 标记确认以下类型存在：

| 类型 | 证据 | 可确认字段 |
|---|---|---|
| `GameRecord`（Assembly-CSharp） | `RecentGames/match_1768530733.sav` 的 `"$type": "0|GameRecord, Assembly-CSharp"` | `BlackName`、`WhiteName`、`BoardSize`、`GameEnvironment`、`GameMode`、`GameResult`、`ResultDetails`、`GameSGFFilePath`、`Moves`、`Handicap`、`HandicapContents`、`WhiteLeadScores`、`WhiteWinRates` |
| `Point`（Assembly-CSharp） | 同文件 `"$type": "2|Point, Assembly-CSharp"` | `x`、`y` |

## 2. 可推断的控制器职责（无类名证据）

根据 GTP 命令序列与日志，业务层至少存在以下职责模块 [推测]：

| 职责 | 依据 |
|---|---|
| 引擎进程管理 | 启动 `katago.exe`，重定向 stdin/stdout |
| GTP 会话控制 | 发送 `boardsize`、`komi`、`kata-set-rules`、`play`、`genmove`、`kata-analyze`、`kata-raw-nn` |
| 棋谱解析/生成 | 读写 SGF、`GameSGFFilePath` |
| 分析曲线 | 保存 `WhiteLeadScores`、`WhiteWinRates` |
| 赛事下载 | Azure Blob 列表与 SGF 下载 |
| UI 棋盘/棋子 | Unity 场景与材质（无直接证据） |

## 3. 不能声称的内容

- 不能列出 game-02 的类名、方法名、命名空间或继承关系。
- 不能确认难度系统的实现方式、提示 UI 的调用链、复盘评分算法。
- 不能把 game-01 的类结构套用到 game-02；两者只有发行方与引擎封装范式相似。

上述内容均标记为**未知**，需重新安装游戏后补充反编译。

## 4. 与任务书关键词的对应

| 关键词 | game-02 状态 |
|---|---|
| ChessEngine / GameEngine / AIEngine | 未知（二进制缺失）；AI 由 KataGo 承担 |
| Search / Evaluate | 在 KataGo 内部，接口为 GTP `genmove` / `kata-analyze` |
| Board / Position / Move | 业务层应有，但类名未知；存档用 `Point{x,y}` |
| Hint / Analysis | 外部行为可见：`kata-analyze` + ownership |
| Undo | 未知（GTP 有 `undo`，日志中未出现） |
| Replay / Record | SGF + `GameRecord` + 胜率/领先曲线 |
| Difficulty | 未知（配置在缺失的 `default_gtp.cfg` 与业务层） |
| Training | 未知；存在生涯/职业棋谱栏目 |
