# 报告 08：棋谱数据结构（game-01）

## 1. 数据模型 `GameRecord`

`GameRecord.cs:6-57`，`[Serializable]`，字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `Id` | `Guid` | 对局唯一 ID |
| `EventName` | string | 赛事/模式名，如 `ClassicMatch_1` |
| `RedPlayerName` / `BlackPlayerName` | string | 双方名称（可含富文本 `<size>`） |
| `RedPlayerEloScore` / `BlackPlayerEloScore` | int | -1 表示未知 |
| `GameResult` | enum | `GameGoesOn/RedWin/BlackWin/Draw/Unknown` |
| `PieceMaterial` | enum | 棋子材质 |
| `StartingPieceColor` | enum | 先行方 |
| `GameScene` | enum | 场景（茶馆/学校/客厅/赛场） |
| `GameTime` | enum | 时限档 |
| `MatchDate` | DateTime | 对局日期 |
| `MatchDuration` | TimeSpan | 时长 |
| `BoardStartFen` | string | 起始局面 FEN（支持让子/残局） |
| `Moves` | `List<string>` | 着法序列，4 字符坐标 |
| `MoveNotations` | `Dictionary<string, List<string>>` | 按语言的记谱（简中/繁中/英） |
| `MoveAnalysis` | `List<MoveAnalysis>` | 每步引擎分析 |
| `Report` | `List<ReportMoveType>` | 每步评分标签 |

## 2. 着法编码

- 4 字符：起点列 `a..i` + 起点行 `0..9` + 终点列 + 终点行，例如 `h2e2`、`h0g2`。
- 与 UCCI 坐标一致，可直接作为 `position fen ... moves ...` 的输入。
- `ChessBoard.Moves` 与 `PreviousFens` 同步增长，FEN 用于重复局面与复盘定位。

## 3. 文件格式 `.game`

- 编码：UTF-8 with BOM，CRLF。
- 序列化器：Odin Serializer（`"$id"`、`"$type": "0|GameRecord, Assembly-CSharp"`、`"$rlength"`、`"$rcontent"`）。
- 非标准 JSON：`Guid` 裸写、`DateTime`/`TimeSpan` 用 `{"$type": "...", 0}` 表示 tick。
- 因此通用 JSON 解析器会失败，需要容错预处理（本次分析用正则包裹裸 GUID 后解析）。

示例（`StreamingAssets/Classic/ClassicMatch_1.game`）：

```json
{
  "$id": 0,
  "$type": "0|GameRecord, Assembly-CSharp",
  "Id": 316b1a62-0161-4061-aea4-b4f7c7cccc4d,
  "EventName": "ClassicMatch_1",
  "GameResult": 1,
  "BoardStartFen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR",
  "Moves": { "$rlength": 25, "$rcontent": ["h2e2","h7e7", ...] },
  "MoveNotations": { ... }
}
```

## 4. 存档

| 数据 | 路径 | 格式 |
|---|---|---|
| 设置/进度 | `SaveFileOfficial.es3` | ES3 AES 加密（密钥硬编码） |
| 生涯 | `CareerSaves/*.sav`、`Careers/career.sav` | Odin JSON |
| 对局历史 | `MyGameHistory/` | Odin JSON |
| 最近对局 | `RecentGames/`（具体文件名未逐一验证） | Odin JSON |
| 内置名局 | `StreamingAssets/Classic/*.game` | 同上 |

## 5. 导出 PGN

`Utils.WriteToPGN(record, stepsPerLine)`（`Utils.cs:1334-1373`）：

```text
[Game "Chinese Chess"]
[Event "..."]
[Date "yyyy-MM-dd"]
[Red "..."]
[Black "..."]
[Result "1-0" | "0-1" | "*"]
[FEN "<BoardStartFen> w|b"]
1. 炮二平五 马8进7 ...
```

- 着法取 `MoveNotations["Chinese (Simplified)"]`，数字转为全角（`ConvertNarrowNumbers`）。
- 落盘编码 GB2312（`GameManager.cs:4333`），兼容国内棋谱软件。
- 只导出记谱，不导出引擎逐手评分（`MoveAnalysis` 不进入 PGN）。

## 6. 观察

- 棋谱系统与 UI 强耦合：`GameRecord` 同时服务存档、复盘、分析图表与导出，没有独立的“棋谱引擎”。
- `MoveNotations` 预存多语言，说明记谱在落子时即时生成，而非导出时计算。
- 名局文件直接放在 `StreamingAssets`，可被玩家替换/扩展（无签名校验）。 [有证据支持]
