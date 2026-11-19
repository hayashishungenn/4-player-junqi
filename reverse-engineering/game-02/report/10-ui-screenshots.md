# 报告 10：UI 功能截图（game-02）

## 1. 现状

**无法提供截图**：游戏主体已从本机卸载，缺失 `JustGo.exe` 与 `JustGo_Data`，无法启动；`gtp_logs` 与用户数据目录不包含界面图像。

## 2. 可替代的界面证据

| 证据 | 位置 | 能说明的界面能力 |
|---|---|---|
| SGF `PB/PW` 含 `<size=9>` 富文本 | `RecentSGFs/sgf_1768530733.sgf` | 界面使用 Unity 富文本显示玩家名与段位 |
| `WhiteLeadScores` / `WhiteWinRates` | `RecentGames/*.sav` | 复盘界面存在形势/胜率曲线 |
| `ownership` 输出 | `Player.log` | 棋盘势力图/归属着色 |
| `kata-analyze` 连续调用 | `gtp_logs` | 分析面板定时刷新 |
| `RecentProMatches` 59 个 SGF | 用户目录 | 职业棋谱浏览/选择界面 |
| `Careers/career.sav` | 用户目录 | 生涯/剧情模式 |
| `SaveFileOfficial_beta.es3` | 用户目录 | 设置/进度存档界面 |

## 3. 不能声称的内容

- 不能描述主菜单、对局 HUD、复盘面板的具体布局与配色。
- 不能确认提示按钮、撤销按钮、难度选择器的存在形式。
- 上述内容在 game-01 截图中可见的同类设计，不能直接套用到 game-02。

## 4. 补齐条件

重新安装《Just Go》后，可按 game-01 的方法（窗口截图 + DPI 感知点击）补齐：

1. 主菜单/模式选择。
2. 对局设置（棋盘、贴目、让子、难度）。
3. 对局中 HUD、AI 思考、提示。
4. 复盘/分析面板、胜率曲线、势力图。
5. 职业棋谱库、生涯界面。
