# 报告 11：动态运行观察（game-02）

## 1. 观察来源

本次**无法重新运行** game-02（主体已卸载）。动态证据来自用户 2026-01-16 的正常运行残留：

- `%LocalLow%\Studio Amateur\JustGo\Player.log`（7,096 行，718 KB）。
- `D:\SteamLibrary\steamapps\common\Just Go\gtp_logs\` 4 个日志（共 432 KB）。
- `RecentSGFs/sgf_1768530733.sgf`、`RecentGames/match_1768530733.sav`。
- 59 个职业棋谱文件。

这些是应用自身产生的日志，非本次伪造。分析过程未修改它们。

## 2. 四次引擎会话

| 日志 | 开始时间 | 规模 | 内容 |
|---|---|---:|---|
| `20260116-102356-7B8BC9CC.log` | 10:23:56 | 5.6 KB | 引擎启动、19 路→9 路切换、boardsize |
| `20260116-102459-11CC525B.log` | 10:24:59 | 4.6 KB | 同上，较短 |
| `20260116-102532-923AB239.log` | 10:25:32 | 141 KB | 完整对局：play/genmove 交错 |
| `20260116-102532-DD5B56EE.log` | 10:25:32 | 278 KB | 分析会话：kata-analyze/raw-nn |

同时间启动两个引擎，与 game-01 的“对弈引擎 + 分析引擎”分离设计一致。 [有证据支持]

## 3. 对局过程

```text
10:25:33 kata-set-rules suicide false
10:25:40 play B F5
10:25:41 genmove W
10:25:47 play B D6
10:25:47 genmove W
10:25:54 play B F4
...
```

- 玩家（黑）落子 → AI（白）`genmove`，间隔 6–8 秒。
- 共 67 次 `genmove W`，与 SGF 中白方手数一致（134 手，双方各 67）。
- 结果 `Black resigned`，SGF `RE[W+R]` 一致。

## 4. 分析过程

```text
10:31:26 kata-analyze Black 200 ownership true
10:31:28 kata-analyze Black 200 ownership true
...
```

- 68 次分析调用，约每 2–3 秒一次。
- 同时有 135 次 `kata-raw-nn 1`，对应每一步取一次网络原始输出。
- `Player.log` 中 122 行 `katago:info`，包含 `visits/winrate/scoreLead/pv/ownership`。

## 5. 设备与性能

```text
GfxDevice: NVIDIA GeForce RTX 5070 Ti Laptop GPU
Renderer: Direct3D 11.0
Using 4 CPU thread(s) for search
Eigen (CPU) backend thread 0..3
```

- 引擎**未使用 GPU**，即使机器有独显；Eigen CPU 后端。
- 4 线程搜索，单步 5–9 秒可达 1,706 visits。

## 6. 网络

- 下载职业棋谱：`justgoprod.blob.core.windows.net/recent-pro-matches/...sgf`。
- 未发现 AI 相关远程调用。

## 7. 与任务书 12 场景的完成度

| # | 场景 | 状态 |
|---:|---|---|
| 1 | 启动和主菜单 | 有历史日志，无本次实机 |
| 2 | 新建对局 | 有 GTP 记录（boardsize/komi/play） |
| 3 | 不同 AI 难度 | **无证据** |
| 4 | 不同游戏设置 | 部分（棋盘 9、贴目 5.5、规则） |
| 5 | 正常走棋 | 有（play 序列） |
| 6 | AI 思考过程 | 有（genmove 间隔、info 输出） |
| 7 | 提示功能 | 推测复用 kata-analyze，无直接证据 |
| 8 | 撤销功能 | 无证据 |
| 9 | 棋局结束 | 有（Black resigned / W+R） |
| 10 | 棋谱回放 | 有 SGF 与 .sav，无界面证据 |
| 11 | 棋局分析 | 有（kata-analyze 200 + ownership） |
| 12 | 历史对局 | 有 `RecentGames/`、`RecentProMatches/` |

## 8. 合规

- 仅读取用户本机已有日志与棋谱；未重新下载、未修改、未上传。
- 日志中的 Azure 共享密钥片段未复制到本报告。
