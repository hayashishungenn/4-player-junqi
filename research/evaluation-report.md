# 测试与棋力评测报告

日期：2026-11-19
范围：主工程 `workspace/siguo-junqi` v2.12.2 + 本次 P2–P6 改动。所有命令在 Git Bash/Windows 11 环境执行，输出如实摘录。

## 1. 单元测试结果

命令：`npm test`（`node --test --test-concurrency=1`），最终一次完整运行：

```text
tests 114
pass 110
fail 4
```

4 个失败均为 P0 基线既有的失败（见 `research/p0-baseline.md` 第 64–71 行），本次改动**未引入任何新增失败**：

| 既有失败测试 | 现象 |
|---|---|
| `test/admin-chat2512.test.js:30` | `renderMutedUsers` 读取 undefined 的 `username` |
| `test/auto-draw.test.js:26` | `timeout room-state` |
| `test/features-233.test.js:20` | `false !== true` |
| `test/features-245.test.js:10` | `undefined !== -100` |

新增测试（全部通过）：
- `test/analysis.test.js`（4 项）：错误等级分级、夺旗最佳着法、严重失误分差、暗棋视角一致性。
- `test/replay-analysis.test.js`（5 项）：局面投影、完整报告结构、明棋/暗棋视角分离、失误列表、空棋谱稳健性。
- `test/difficulty.test.js`（3 项）：档位单调性、id/名称解析、覆盖校验。
- `test/features-240.test.js`（既有集成测试，本次追加 1 条断言）：经加密通道验证新 `POST /api/rooms/:code/analysis` 返回 200、`perspective={analysis:'dark',truth:'open'}`、含校准声明。该测试单独运行结果 `tests 1 / pass 1 / fail 0`。
- `test/alliance-e2e.test.js`（本次新增端到端）：1 真人 + 3 AI 四方联盟，经加密通道起服、托管 3 个 BOT 程序、真人随机布阵走子，验证四方轮流（`north/east/south/west` 全部观察到）、结盟模式、12 步棋谱推进、管理员强制结束后完整棋谱（15 帧 / 30 条日志）。单独运行结果 `tests 1 / pass 1 / fail 0`，JSON 输出：`{"code":"KSNT77","plies":12,"seatsSeen":["north","east","south","west"],"finished":true,"frames":15,"logs":30}`。这覆盖了 P1「真人对三个 AI + 四方结盟 + 轮流 + 棋谱」的端到端要求。

回归过程留痕：新增 9 项测试后曾短暂出现 1 项新增失败（`analysis.test.js` 的视角一致性用 `deepEqual` 比较了依赖墙钟预算的 `samples`/分数），已改为只断言稳定语义属性（最佳着法、错误等级、视角标注、无真实兵种泄露），重跑后恢复为 4 项基线失败。

## 2. 引擎对战（棋力 smoke benchmark）

命令（脚本自述为 "smoke benchmark, not a human rating or a statistically valid win rate"）：

```text
BOT_A_MS=150 BOT_B_MS=800 BOT_GAMES=4 BOT_MAX_PLIES=70 node scripts/benchmark-bots.js
```

真实输出：

```text
{"game":1,"aSeat":"north","result":"B-win","plies":38,"battles":22,"sampledTurns":19,"elapsedMs":17258}
{"game":2,"aSeat":"south","result":"A-win","plies":40,"battles":18,"sampledTurns":19,"elapsedMs":18851}
{"game":3,"aSeat":"north","result":"move-limit-unresolved","plies":70,"battles":22,"sampledTurns":35,"elapsedMs":33250}
{"game":4,"aSeat":"south","result":"A-win","plies":48,"battles":23,"sampledTurns":23,"elapsedMs":22652}
{"aMs":150,"bMs":800,"games":4,"wins":2,"losses":1,"unresolved":1}
```

扩展评测（第二次，A=120ms / B=450ms / 12 局 / 上限 60 步），真实汇总：

```text
{"aMs":120,"bMs":450,"games":12,"wins":2,"losses":5,"unresolved":5}
```

两批合计 16 局：低预算 A 4 胜、高预算 B 6 胜、未决 6 局（已决 10 局中 B 6:4 A）。

解读（如实）：
- 两引擎均完整走完合法着法、执行暗棋采样（`sampledTurns` 19–35），无非法着法或崩溃。
- 第一批 4 局：低预算 A 胜 2、高预算 B 胜 1、1 局未决；第二批 12 局：A 胜 2、B 胜 5、5 局未决。合计已决 10 局中 B 6:4 A。
- **样本仍不够大（共 16 局、已决 10 局）、未固定布局、未计算置信区间，不能得出"高预算棋力更强"的结论**；这与脚本自身的免责声明一致。本结果仅作为引擎可运行、对战链路完整的证据，不作为棋力排名或胜率估计。
- 要得到可信棋力对比，需固定布局、增加对局数（建议 ≥100）、交替先手并记录置信区间；本次未执行。
- 棋力 smoke 之外，P5 自我对弈的棋力统计见 `research/training-report.md`（6 局联盟自我对弈，全和棋）。

## 3. 逐手评分一致性验证

- 夺旗测试局面（f 为公开军旗）：实际着法即引擎最佳，得分 `+50000`，分差 `0`，等级 `best`；48 次采样结果一致（`std=0`）。
- 离开夺旗点的劣着：得分约 `-49999`，与最佳分差 `>1000`，等级 `blunder`，解释含「大本营」与「引擎分不是胜率」声明。
- 暗棋局面（f 未公开）：分析字段不含 `flag`/`engineer`/`type` 等真实兵种信息；明棋 `truth` 字段保留真实兵种。两种真实身份（flag/mine）产生完全相同的暗棋视角投影。
- 结论：**比较候选时的信息视角与采样条件一致**；引擎分明确为未校准启发式分，未冒充胜率。

## 4. 服务器与 API 验证

- 启动：`PORT=3199 node server/server.js` → 输出「四国军棋已启动：http://localhost:3199」；`GET /` → HTTP 200，47,340 bytes。
- 站点既有安全机制：未持加密通道的 `/api/` 请求返回 `426`（`server/secure.js:62`），新 API 与既有 replay API 遵循同样规则。
- 新 API 经加密客户端（`test/encrypted-client.js`）验证可用（见第 1 节 features-240）。

## 5. P5 自我对弈训练（已执行，阻塞已解除）

阻塞已解除（详见 `research/training-report.md`）：清空未启动的代理环境变量后，PyTorch CPU 源与清华镜像可直连；在临时 venv 安装 `torch-2.15.0+cpu` 等依赖，未修改系统/仓库依赖。

已验证并执行：
- `neural-bot/self_play_env.mjs`（本地 JSON-RPC 对局环境）实测 alliance 模式的 reset/state/board 均正常。
- 实际运行 6 局联盟自我对弈（CPU，`--modes alliance --games 6`）：全部正常终局，6 局均为和棋（未训练策略触发自动和棋），步数 96–262，平均 loss -0.769343。训练记录与汇总已产出（写临时目录，不入库）。
- `model.pt`（约 1.47 MB）被 `neural-bot/.gitignore` 的 `*.pt` 排除，未提交。
- 训练器新增 `--record`：每局写 JSONL、结束写汇总，构成 P6 的训练记录能力。
- 未执行：CUDA 训练（本机装 CPU 版 torch）、1000+ 局大规模训练、历史最佳模型对抗棋力曲线（6 局不足以评估）。

<details><summary>原阻塞记录（现已解除，保留作审计）</summary>

原状态：系统 Python 3.14.3 无 torch、由 uv 管理禁止全局安装，且代理 127.0.0.1:7899 未启动导致 pip 报 WinError 10061 / ProxyError，无法安装 torch。当时 P5 仅完成环境验证与代码审查。

</details>

已验证：
- `neural-bot/self_play_env.mjs`（本地 JSON-RPC 对局环境，Python 训练器通过子进程调用）实测 `reset(mode=alliance)` / `state` / `board` 均返回 `{"ok":true,...}`，四方初始化、明棋/暗棋投影正常。
- `self_play.py` / `neural_bot.py` 源码具备 `--games`、`--device cuda|cpu`、`--modes ffa|alliance`、模型版本与历史最佳对抗（`research/repo-analysis/siguo-junqi.md` 第 6 节）。

<del>以下为解除前的旧记录，已被上方内容取代：</del>

- 系统 Python 3.14.3 无 torch：`python -c "import torch"` → `ModuleNotFoundError`。
- Python 由 uv 管理，禁止全局安装（`externally-managed-environment`）；建临时 venv 后 `pip install torch --dry-run` 因代理不可达失败：
  ```text
  ProxyError('Cannot connect to proxy.', ... WinError 10061 ...)
  ERROR: Could not find a version that satisfies the requirement torch
  ```
（以上旧记录已由第 5 节开头的解除说明取代。）

## 6. 交付物与 Commit 索引

外层仓库（`D:\4-player-junqi`）：
- `160bfca` 阶段二：四仓库深度源码分析报告与技术整合方案
- `863cc2f` 修订 P0 基线：UnityPlayer 分析重试被中断
- `research/ai-algorithm.md` / `research/evaluation-report.md`（本报告）待提交

主工程仓库（`D:\4-player-junqi\workspace\siguo-junqi`）：
- `5ac3e23` P3 逐手评分引擎
- `72ca8c5` P4 复盘分析器
- `933cad6` P2 多档难度
- `e7952cb` P6 界面与 API（分析 API + 复盘 UI）
- `6db230a` P4 自动播放 + 分析持久化、P6 AI 提示、`alliance-e2e` 端到端测试
- `62d7ab9` P5 训练记录（每局 JSONL + 棋力统计汇总）

## 7. 未完成与风险

1. 4 个基线测试失败未修复（既有缺陷/环境依赖，不擅自改断言）。
2. 棋力评测为 16 局 smoke（已决 10 局），仍不具统计显著性；未做 100+ 局固定布局评测。
3. P5 已在 CPU 上跑通 6 局联盟自我对弈，但未做 CUDA 训练、1000+ 局大规模训练与历史最佳模型对抗棋力曲线；训练记录写临时目录未入库。
4. 新分析 API 为同步计算，已限制预算（≤250ms/步）与步数（≤80 步）；超长棋谱只分析前 N 步，UI 有「分析中」提示。
5. AI 提示为同步搜索（预算 600ms），仅暗棋对局、当前回合真人可用；返回着法不含真实兵种，符合信息边界。
