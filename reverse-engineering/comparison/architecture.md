# 双游戏技术架构对比报告

## 1. 结论

两款游戏是同一发行方（Studio Amateur）在同一 Unity/Mono 技术范式下开发的两个独立产品：

- **共用的是“产品骨架”**：Unity + Mono、Odin 序列化、ES3 加密存档、外部引擎进程、SGF/PGN 交换格式、Steam 接入、统一用户数据目录。
- **不共用的是“棋 AI 与规则核心”**：中国象棋是自研 C# 引擎 + ElephantEyes + Pikafish 三路混合；围棋是 KataGo 单引擎。
- 没有证据表明两款游戏共用同一套 AI、难度配置或估值代码；把“同为棋类”误判为“同引擎”会得出错误结论。

## 2. 并排对照

| 维度 | game-01 Just Xiangqi | game-02 Just Go |
|---|---|---|
| Steam AppID | 2248180 | 1862520 |
| Unity | 2020.3.15f2 | 2021.3.29f1 |
| 脚本后端 | Mono | Mono |
| 安装体积 | 2.0 GB（276 文件） | 主体已卸载；残留日志 432 KB |
| 状态管理 | `GameManager` 单一大类（约 6,000 行） | 未知（二进制缺失） |
| AI 引擎 | NativeAI + ElephantEyes(C#) + Pikafish(UCI) | KataGo(GTP) |
| 引擎协议 | UCI（`position/go depth/stop`） | GTP（`play/genmove/kata-analyze`） |
| 神经网络 | Pikafish NNUE 45.5 MB | KataGo b40c256 |
| 搜索范式 | Alpha-Beta/PVS + 静态搜索 + 置换表 | MCTS/PUCT + policy/value |
| 难度实现 | 引擎类型 + 深度 + MultiPV 随机 + 开局库 | 未知（推测访问数/时间） |
| 开局库 | 两套：文本 `Book/Openings` + 内置 12,081 条 | 未发现 |
| 棋谱内部格式 | `.game`（Odin JSON） | `.sav`（Odin JSON） |
| 交换格式 | PGN（GB2312） | SGF（FF[4]） |
| 逐手分析 | `MoveAnalysis`（cp/mate/wdl）+ `Report` | `WhiteLeadScores` + `WhiteWinRates` |
| 分析引擎 | 独立 Pikafish 进程，MultiPV 3/5 | 同一 KataGo，`kata-analyze 200` |
| 名局库 | 本地 `Classic/*.game`（24） | 在线 Azure Blob SGF（59 缓存） |
| 在线对战 | Photon Realtime/Chat | 未知（日志未见 Photon 程序集） |
| 平台 | Steamworks | Steamworks |
| 加密存档 | ES3 AES（硬编码密钥） | ES3（`SaveFileOfficial_beta.es3`） |

## 3. 共用性判定

| 功能 | 是否共用 | 判定依据 |
|---|---|---|
| Unity/Mono 技术栈 | 是（同范式，不同版本） | 两者 `Player.log` 与目录结构 |
| Odin 序列化 | 是（同 schema 风格） | `.game` 与 `.sav` 的 `$id/$type/$rlength` |
| ES3 加密存档 | 是（同产品线惯例） | 两者均有 `.es3` 文件 |
| 账号/Steam 接入 | 是（同一平台方案） | 两者均初始化 Steam API |
| UI 框架组件 | 可能共用部分 Unity 插件，但无程序集证据 | 两版本均见 Michsky/I2.Loc 等（game-02 仅由存档/日志推断） [推测] |
| AI 引擎 | **否** | Pikafish vs KataGo |
| 搜索算法 | **否** | Alpha-Beta vs MCTS |
| 局面估值 | **否** | NNUE vs KataGo NN |
| 难度配置 | **否**（game-02 未知，不能假定相同） | game-01 有明确 13 档表；game-02 无证据 |
| 棋谱系统 | 否（设计同构，实现独立） | 不同格式与字段 |
| 提示/分析组件 | 否（同思路，不同协议） | UCI MultiPV vs GTP kata-analyze |
| 网络通信 | 否（game-01 Photon；game-02 未见） | 程序集与日志 |

## 4. 架构启示

1. **“外部引擎进程”是可复用架构模式**：两款游戏都把强 AI 放在独立进程，通过文本协议通信，主程序只做局面转换与结果解析。好处是引擎可替换、崩溃隔离、分析与对弈可分离。
2. **交换格式与内部格式分离**：内部保留分析数据，对外只导出标准格式（PGN/SGF）。这使复盘功能不被交换格式限制。
3. **产品骨架可复用，棋种核心不可复用**：UI、存档、平台接入可抽象为通用层；规则、搜索引擎、估值必须按棋种重写。

## 5. 限制

- game-02 主体缺失，架构结论多来自日志与存档，无法验证 C# 层。
- 未做二进制相似度比较（如程序集哈希、代码段指纹），因此“共用 UI 框架”只能标为推测。
