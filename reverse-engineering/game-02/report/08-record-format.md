# 报告 08：棋谱数据结构（game-02）

## 1. SGF 文件

`RecentSGFs/sgf_1768530733.sgf` 为标准 SGF FF[4]：

```text
(;FF[4]SZ[9]DT[2026-01-16]
  PB[HAYASHISHUNGENN <size=9>(19k)</size>]
  PW[傅杉铭 <size=9>(20k)</size>]
  KM[5.5]HA[0]RU[chinese]RE[W+R]
  ;B[fe];W[ee];B[dd];W[ed];...
)
```

要点：

- `SZ[9]`：9 路盘。
- `KM[5.5]`、`HA[0]`、`RU[chinese]`：贴目、让子、规则。
- `RE[W+R]`：白中盘胜。
- 坐标采用 SGF 字母对（`fe` = 列 f、行 e）。
- 玩家名内嵌 Unity 富文本 `<size>`，说明 SGF 从 UI 模型直接生成，未做清洗。

## 2. 对局存档 `.sav`

Odin JSON，根类型 `GameRecord`。字段：

| 字段 | 类型 | 示例/说明 |
|---|---|---|
| `BlackName` / `WhiteName` | string | 含富文本 |
| `BoardSize` | int | 9 |
| `GameEnvironment` | enum | 场景/环境 |
| `GameMode` | enum | 对局模式 |
| `GameResult` | enum | 本局 `2`（与 `RE[W+R]` 对应） |
| `ResultDetails` | string | `Black resigned` |
| `GameSGFFilePath` | string | 指向 `RecentSGFs/sgf_*.sgf` |
| `Moves` | `List<Point>` | 134 个 `{x,y}` |
| `Handicap` / `HandicapContents` | — | 让子设置 |
| `WhiteLeadScores` | `List<double>` | 135 项（初始 + 每手） |
| `WhiteWinRates` | `List<double>` | 逐手胜率 |

`Point` 结构：`{"x": 5, "y": 4}`。

## 3. 两种棋谱并存

- **SGF**：对外交换格式，可导入/导出、可加载职业棋谱。
- **`.sav`**：内部完整记录，额外保存引擎分析曲线（领先目数、胜率），SGF 不包含这些数据。

这与 game-01 “`.game` 内部格式 + PGN 对外导出”的设计完全同构：

| 能力 | game-01 | game-02 |
|---|---|---|
| 内部格式 | `.game`（Odin JSON） | `.sav`（Odin JSON） |
| 对外格式 | PGN（GB2312） | SGF（FF[4]） |
| 逐手分析 | `MoveAnalysis` + `Report` | `WhiteLeadScores` + `WhiteWinRates` |
| 元数据 | 双方、ELO、场景、材质、时长 | 双方、棋盘、贴目、让子、规则、结果 |
| 名局库 | `Classic/*.game`（24 局） | `RecentProMatches/*.sgf`（59 局） |

## 4. 未确认

- `GameResult` 枚举的完整取值（仅见 `2`）。
- `GameEnvironment`、`GameMode` 的枚举含义。
- SGF 是否支持分支/变化图（`(` 嵌套）——本次样本为单线。
- 职业棋谱 `.sav` 与玩家对局 `.sav` 是否同一 schema（文件名相近，未逐一解析）。
