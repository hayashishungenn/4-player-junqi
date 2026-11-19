# 报告 12：已证实与未证实事项（game-02）

## 1. 已验证

| 结论 | 证据 |
|---|---|
| 产品为 Steam AppID 1862520 的《Just Go》 | `Player.log` Steam 初始化行 |
| Unity 2021.3.29f1 + Mono Windows 构建 | `Player.log:1-3` |
| AI 为 KataGo v1.10.0 外部进程 | GTP 日志首行；`Player.log:1201` |
| 使用 GTP 协议（genmove/play/analyze/komi/boardsize） | 4 个 GTP 日志的命令统计 |
| 网络为 `kata1-b40c256-s10032125184-d2445637108` | 启动命令行；GTP 日志 |
| Eigen CPU 后端、4 搜索线程 | GTP 日志 |
| 分析固定 200 visits + ownership | `kata-analyze Black 200 ownership true` × 68 |
| 对弈为时间控制，单步约 5–9 秒 | GTP 时间戳 |
| AI 完全本地，不走网络 | 进程启动 + 无远程走子调用 |
| 棋谱为 SGF FF[4]，9 路、贴目 5.5、中国规则 | SGF 文件 |
| 内部存档为 Odin JSON `GameRecord` | `.sav` 的 `$type` |
| 逐手保存领先目数与胜率 | `WhiteLeadScores` 135 项 / `WhiteWinRates` |
| 职业棋谱在线更新（Azure Blob） | `Player.log` 请求 URL |
| 对弈与分析使用两个独立引擎会话 | 同一时刻两份 GTP 日志 |

## 2. 有证据支持但未完整验证

| 结论 | 缺口 |
|---|---|
| 提示功能复用 `kata-analyze` | 未找到提示专用命令，属合理推断 |
| 分析面板按 2–3 秒节流刷新 | 由调用间隔推断，未见 UI 代码 |
| `kata-raw-nn` 用于高级分析/调试 | 调用次数与手数一致，用途未证实 |
| 生涯模式与普通对局共用 `GameRecord` | 仅见字段，未解析生涯存档 |
| 同一网络支持 19/9 路 | 日志有初始化缓冲，未验证两种尺寸棋力 |

## 3. 推测

| 结论 | 依据 |
|---|---|
| 难度通过 `maxVisits`/`maxTime` 调节 | KataGo 常规做法；配置缺失 |
| 界面存在势力图 | `ownership true` 输出必须有消费方 |
| 复盘支持逐手浏览 | 胜率/目差按手存储 |

## 4. 未知

| 项 | 原因 |
|---|---|
| 业务层类结构、方法、难度表 | `Assembly-CSharp.dll` 缺失 |
| `default_gtp.cfg` 全部参数 | 文件缺失 |
| 难度档位数量与命名 | 无界面/配置证据 |
| 撤销、提示、训练的具体实现 | 无代码、无日志 |
| 是否使用 GPU 变体/多网络 | 目录缺失 |
| 胜负判定与贴目之外的规则细节 | 仅见 `RU[chinese]`、`suicide false` |

## 5. 与任务书要求的差距

- APK 相关检查项：不适用（非 Android）。
- 12 项交付中，包结构、技术架构、AI 链、搜索、估值、棋谱、复盘有实证；关键类清单、难度机制、UI 截图、动态场景受“二进制缺失”限制，已如实标注。
- 未用 game-01 的结构替代 game-02 的证据。

## 6. 合规

- 仅分析用户本机残留日志与棋谱。
- 未恢复、未下载、未修改游戏主体。
- 未复制任何商业素材或代码到四国军棋工程。
