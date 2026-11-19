# 报告 04：AI 决策调用链（game-02）

## 1. 总链（由 GTP 日志恢复）

```text
用户点击棋盘交叉点
  → 业务层把落子转换为 GTP 坐标并落后
  → 若轮到 AI：
       genmove <color>
       → KataGo 搜索（MCTS + NN）
       → 返回坐标（如 D1）
  → 业务层把结果映射回棋盘、播放动画
  → 记录 Move、WhiteLeadScores、WhiteWinRates
```

证据：`gtp_logs/20260116-102532-923AB239.log` 中成对出现 `play B F5` → `genmove W`，间隔约 6–8 秒；`Player.log` 同步出现 `katago:info move ... visits ... pv ...` 输出。

## 2. GTP 命令清单（4 个日志汇总）

| 命令 | 次数 | 作用 |
|---|---:|---|
| `boardsize 9` | 4 | 设定 9 路棋盘 |
| `komi 5.5` | 4 | 贴目 |
| `kata-set-rules suicide false` | 1+ | 规则设置 |
| `play B/W <coord>` | 多次 | 落子同步 |
| `genmove W` | 67 | AI 走子 |
| `kata-analyze Black 200 ownership true` | 68 | 局面分析：200 visits + 归属图 |
| `kata-raw-nn 1` | 135 | 直接取神经网络原始输出 |

## 3. 本地/远程判定

- `katago.exe` 由游戏进程启动，GTP 通过标准输入输出交互（`Player.log:1201`）。
- 未发现把棋盘上传服务器再取回着法的接口；Azure Blob 仅用于下载职业棋谱 SGF。
- 结论：**AI 完全本地**。 [已验证]

## 4. 分析调用的语义

`kata-analyze <color> 200 ownership true`：

- 颜色参数表示“从哪一方的视角分析”；日志中固定为 `Black`。
- `200` 为访问次数上限，即每次分析约 200 次 MCTS 模拟。
- `ownership true` 要求返回每个交叉点的归属概率（-1..1），用于界面上的势力图/胜率着色。
- 连续 68 次调用、间隔约 2–3 秒，符合“每步后台分析 + 界面刷新”的节流模式。

## 5. 思考时长

- `genmove` 间隔约 5–9 秒（`10:25:41`→`10:25:47`→`10:25:54`…），说明对弈使用时间控制而非固定访问数；具体时间参数在缺失的 `default_gtp.cfg` 与业务层。
- `kata-analyze` 固定 200 visits，用于快速分析，不追求极限棋力。

## 6. 未知

- 业务层如何选择 `genmove` 的时间/访问上限（`maxTime`、`maxVisits`）。
- 是否有“让子/难度”对 GTP 参数的不同设置。
- 是否使用 `kata-genmove_analyze`（日志中未出现）。
- 是否对 AI 着法做随机化或降级（日志只显示 `genmove` 结果）。
