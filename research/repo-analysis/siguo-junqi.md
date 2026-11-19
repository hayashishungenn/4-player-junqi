# 主工程源码分析：BitByBitG/siguo-junqi

日期：2026-11-19
仓库：`D:\4-player-junqi\workspace\siguo-junqi`
分支：`master`  commit：`f4b911aebc303a63ceeacd20890714c60203a13e`（见 research/p0-baseline.md）
许可证：MIT（`LICENSE` 文件存在）——可合法复用，复用时保留版权与许可声明。

> 证据约定：行号来自上述 commit 的工作副本。带「源码证实」的为直接读取代码所得；带「推断」的为基于代码的判断，未经实机验证。GB2312 编码文件（RULES.md / BOT_API.md）按 GB2312 解码后阅读。

## 1. 架构与依赖（源码证实）

- `package.json`：v2.12.2，ESM（`type: module`），Node ≥18。运行依赖仅 express 4 / socket.io 4 / quickjs-emscripten 0.32 / marked / dompurify / katex；开发依赖 socket.io-client。**无游戏逻辑第三方依赖**——规则与 AI 全部自研。
- 服务入口 `server/server.js`（约 126 KB）：HTTP(S) + Socket.IO，账号、房间、聊天、Rating、棋谱托管、多游戏（军棋 / 斗地主 / 德州扑克）。
- 规则内核 `server/game.js`：纯函数，棋盘构建、布阵校验、走法校验、交战结算、胜负关系。被浏览器端与 BOT 端共用（构建脚本把它打包进参考 BOT）。
- AI 引擎 `bots/engine/{bot.js,search.js}`：暗棋采样 + 概率推断 + 联盟搜索。
- BOT 运行时 `bots/client-runtime.js`、`bots/reference-bot.mjs`、`bots/siguo-junqi-bot.mjs`：以 Worker 运行搜索，通过 BOT API 连接服务器。
- 神经训练 `neural-bot/`：`neural_bot.py`（GNN 策略价值网络 + BOT 客户端）、`self_play.py`（自我对弈训练）、`self_play_env.mjs`（本地对局环境）。
- 测试 `test/` 34 个文件（基线 `npm test` 101 项，97 通过 / 4 失败，详见 p0-baseline.md）。
- 构建 `scripts/build-reference-bot.js` 把 5 个引擎文件拼成单文件 BOT；`benchmark-bots.js` 做棋力对战。

## 2. 规则内核 server/game.js（源码证实）

- 棋盘 `BOARD`（第 55–185 行）：每方 6×5 阵地 + 中央 9 宫格；`neighbors`（公路）、`railNeighbors`/`straightRailLines`（铁路直线，含四角弯道视作连续直道）、`kind`（hq/camp/rail）、`seat` 归属。
- 棋子 `PIECE_INFO`（第 19 行）：12 类，含 count / rank / immobile。军旗 1、地雷 3、炸弹 2、工兵 3；司令 9 … 连长 3 等。
- `createArmy`（第 202 行）/ `validateSetup`（第 272 行）：25 子合法阵型；行营必须空、军旗在底线大本营、地雷仅最后两排、炸弹不在第一排。
- `validateMove`（第 342 行）：公路单步、铁路直线多步、工兵铁路转弯 BFS、盟友不可进入、行营不可进（除空营）、返回 `{ok,attacker,defender,engineerTurn}`。
- `resolveBattle`（第 390 行）：大小比较、炸弹同归、地雷不可被普通子吃、工兵挖雷、攻守同归等结算。
- `sameTeam`（第 379 行）：`alliance` 模式下南北 / 东西互为盟友。
- `revealFlagWhenCommanderDies`（第 455 行）：司令阵亡公开军旗。
- 斗地主 `createLandlordDeal`/`completeLandlordDeal`/`createLandlordArmies`（第 424–455 行）：独立变体，不在本次四国暗棋交付范围。

## 3. AI 引擎 bots/engine（源码证实）

### 3.1 隐藏信息边界（关键安全设计）
- `botView(room, seat)`（bot.js 第 8–22 行）：**唯一**允许引擎读取真实房间的边界。对非己方且未 `revealed` 的棋子 `type=null`；附上 `candidates`（弧一致性推断域）、公开战报 `battles`。注释明确「No private logs, hidden ranks, account data or setup-order information cross it」。
- `observeBotBattle`（bot.js 第 24–41 行）：只把**公开战果**写入历史，并据战果收缩各 BOT 的秘密候选集；绝不让对手的真实兵种进入记忆。
- 估值/搜索全程使用 `view.pieces[].type`，对暗子为 null，靠 `belief`/`distribution` 的概率推断。符合「禁止将真实隐藏棋子身份泄露给 AI」。

### 3.2 概率推断
- `distribution(p)`（bot.js 第 44–58 行）：按候选域 + 布阵规则（军旗仅大本营、地雷不在前排、炸弹不在第一排、移动过的子非不可动子）给出兵种先验分布。
- `inferDomains(view)`（search.js 第 19–50 行）：弧一致性，最多 30 轮；用公开战果 + 每方棋子计数（每兵种固定 count）反复收缩域，保留不完整历史下不崩溃的防御（第 28–29 行）。
- `belief(view,p)`（bot.js 第 71–81 行）：每支存活军队恰有 1 面军旗，概率由所有可能大本营共享而非被 25 子稀释；已公开军旗则其余为 0。
- `samplePosition`（search.js 第 52–85 行）：按域与剩余库存做随机加权无放回采样，受战果一致性约束，生成一份「具体化」局面供搜索；有 14000 次访问上限与 deadline。

### 3.3 搜索与估值
- `strongMoves`（search.js 第 95–126 行）：与服务端一致的快速走法生成（公路、铁路直线、工兵 BFS），过滤盟友/行营。
- `simulateStrongMove`（第 128–140 行）：结算交战、夺旗消亡、司令阵亡公开军旗、轮转。
- `evaluate`（第 158–183 行）：子力价值表（第 11–12 行，军旗 16000，司令 135 …工兵 48）、位置项（行营 +7、铁路 +2/+6、逼近敌旗 `*0.6`、护旗 +3）、终局 ±50000。**这是启发式评估分，不是胜率**。
- `searchPosition`（第 207–239 行）：Alpha-Beta + 深度自适应宽度（depth≥3 取前 10，否则 7）+ 浅层兑子延伸（exchanges）+ 超时抛 `TIMEOUT`。
- `rootHeuristic`（第 241–276 行）：根步先验，含概率交战收益、夺旗 +2400/+1000000、工兵暴露惩罚（第 83–93 行）、重复晃动惩罚、逼近目标、护旗 +1800、入侵者拦截等。
- `chooseStrongMove`（第 278–337 行）：主入口。流程：合法步 → 推断域 → 根先验排序 → 必吃旗直返 → 候选（前 28 + 每个可动子至少一着）→ 多采样 Alpha-Beta，深度随采样数 `2→3→4→5`（第 314 行），每批所有候选共享同一采样局面（第 322 行「Commit complete batches」），按 `均值 - 0.16×标准差 + 非局面调整` 选步。返回 `{move, samples, depth, elapsedMs}`。
- `scoreStrongSetup`/`createStrongArmy`（第 339–385 行）：布阵评分与模拟退火 + 随机重启生成强阵。

### 3.4 难度（源码证实）
- 引擎本身**没有显式难度档位/ELO**；难度由 BOT 客户端的 `thinkTimeMs` → `budgetMs` 时间预算间接控制（`bots/client-runtime.js` 第 82 行 `Math.min(4000, configured, remaining-700)`）。时间越长采样越多、深度越高，棋力越强。
- 对战评测 `scripts/benchmark-bots.js` 以不同 `budgetMs` 比对两名引擎（第 14、30、33 行）。
- 参考 BOT 文档（`BOT_API.md`）另述账号侧 Rating 16 档，与本地搜索难度不是同一机制。

## 4. 复盘与棋谱（源码证实）
- `server/server.js` 第 2002 行：`room.replay = {version:1, code, startedAt, frames:[], logs:[]}`。
- 第 1101–1109 行：每次 `updateState` 追加局面帧（去重），终局写 `winner/completed/finishedAt/ratingChanges`。
- 第 1426–1428 行 `applyMove`：每步写入 `replay.logs`，含 `{seat,username,from,to,attacker:{id,type},defender:{id,type,owner},outcome,engineerTurn,path}`——**含真实兵种，为赛后明棋视角**；进行中的 API（第 605–614 行）按观看者过滤 type，保持暗棋视角。
- `GET /api/rooms/:code/replay`（第 592–617 行）：进行中仅返回脱敏帧；终局返回完整 replay（权限校验后可含聊天）。
- 前端 `public/app.js` `openReplay`（第 941 行起）：拉取 replay 并渲染棋盘、图表、统计；`boardControls`（第 687–689 行）提供「查看之前侧」「战报」「分享」入口。
- **缺口**：现有复盘是「局面帧 + 事件日志」，**没有逐手引擎评分、评分曲线、关键失误标注、最佳着法对比、错误等级、整局文字报告**。

## 5. BOT API 与对局接入（源码证实）
- `BOT_API.md`（GB2312）：账号注册、权限（2.5.8）、两种接入方式（直连后台 / 外部独立服务器，第 27 行）、提交着法字段（第 154–175 行）、托管接口（第 218 行）。
- `server/bot-api.js`（约 13 KB）与 `server/hosted-bots.js`（约 12 KB）：BOT 账号鉴权、任务队列、5 秒超时判负、自动和棋（连续 16 步无战损 / 总步数上限，见 RULES.md）。
- `bots/client-runtime.js`：Worker 中运行 `chooseStrongMove`，超时回退 `state.legalMoves[0]`（第 83 行）。这是「真人对 3 AI」的落地路径：真人玩家 + 三个 BOT 账号分占四席。

## 6. 神经自我对弈 neural-bot（源码证实）
- `GraphPolicyValue`（neural_bot.py 第 82 行）：GNN 策略价值网络；`Encoder`（第 105 行）局面编码，`GameMemory`（第 157 行）轨迹记忆，`NeuralBot`（第 165 行）推理与 BOT 客户端。
- `self_play.py`：`LocalEnvironment`（第 14 行）直接调用 `server/game.js`（无需网站）；`Trainer`（第 50 行）自我对弈训练；CLI（第 189 行）支持 `--games`、`--device cuda/cpu`、`--modes ffa/alliance`。
- `README.md`（GB2312）：模型版本（`model.pt` 备份、每 100 局确认、历史最佳模型自动加入对阵）、随机布阵、CUDA 训练均已描述。**P5 功能代码层面已具备**；阻塞是 PyTorch 未安装（见 p0-baseline.md）。

## 7. 测试与已知问题（源码证实）
- `test/strong-bot.test.js`：覆盖 `inferDomains/samplePosition/strongMoves/simulateStrongMove/chooseStrongMove/createStrongArmy`，含夺旗、救旗、困毙、根先验、候选一致性等断言（第 82、93、96、116 行）。
- `test/bot.test.js`：BOT 基础行为。
- 基线 4 个失败测试（p0-baseline.md 第 64–71 行）：`admin-chat2512`（渲染 undefined username）、`auto-draw`（room-state 超时）、`features-233`、`features-245`。为既有缺陷/环境依赖，尚未判定，不擅自改断言。

## 8. P1–P6 现状映射（推断，未实机逐项确认）

| 阶段 | 现状 | 依据 |
|---|---|---|
| P1 四国暗棋 / 联盟 / 布阵 / 轮流 / 胜负 | 已实现 | RULES.md、`game.js`、`sameTeam`、`alliance` / `machine_random` 模式、自动和棋 |
| P2 AI 增强（暗棋采样/概率/联盟/工兵/军旗） | 已实现，可微调 | 第 3 节 |
| P3 逐手评分（最佳/候选/分差/错误等级/采样/解释） | **缺失** | 无独立评分模块；`chooseStrongMove` 仅内部候选统计 |
| P4 完整复盘（评分曲线/失误/最佳/报告） | **部分**：有帧+日志，无分析 | 第 4 节 |
| P5 自我对弈训练（联盟/随机布阵/版本/CUDA/历史最佳） | 代码已具备 | 第 6 节，阻塞于 PyTorch 环境 |
| P6 界面 / 提示 / 训练记录 / 本地运行 | 已有基础界面 | `public/app.js`、`bot-studio.html`、`bot-api.html` |

## 9. 最小必要修改建议（供整合方案采用）
1. 新增独立分析模块 `bots/engine/analysis.js`，复用 `botView`/`inferDomains`/`chooseStrongMove` 的采样与搜索框架，对每一步输出评分报告；**不修改现有引擎行为**。
2. 复盘分析器读取 `room.replay.logs` 与帧，生成评分曲线/关键失误/最佳着法/整局报告；严格区分「实战暗棋视角」（分析时用 `botView` 投影）与「赛后明棋视角」（日志真实 type 仅用于展示）。
3. 引擎分明确标注为「未校准启发式分」，不命名或换算为「胜率」。
4. 难度档位以 `budgetMs`（及可选采样/深度上限）包装，不新增第三方依赖，不改公共 API。
