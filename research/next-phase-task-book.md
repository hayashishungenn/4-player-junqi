# 下一阶段任务书（草案 v3）

日期：2026-11-26
对象：外层 GPU 自我对弈训练链路（`train_junqi_5070ti.py` 及其 300 局配对复评产物）、主工程 `code/siguo-junqi/` 的 BOT 接入边界。
定位：**验收契约与证据目录**，不是结果报告。本任务书只规定"做什么、怎么算达标、拿什么证据"，不预写通过结论。§0 是历史基线观测，不是待验收结论；状态改为通过必须有对应产物路径与 sha256。

依据：
- `research/model-review-report.md:3-29,31-45,56-75`：统一协议复评与模型取舍结论。
- `research/training-report.md:175-193,208-234,236-252`：阶段完成度矩阵、历史胜率矩阵与未完成项。
- `results/tournament.jsonl`（301 行 = 1 meta + 300 game，已入库）、`results/summary.json`、`results/replay_audit.json`。
- 2026-11-26 的模型效果分析（12 代理并行复核 + 逐条对质）：历史 24–26% 与统一 20–25% 统计相容但不可对齐；collapse、信息泄漏、产品效果均缺直接测量。

## 0. 历史基线观测（非新验收结论）

| checkpoint (sha256 前 8) | 含和局胜率 W/N | 排除和局 W/(W+L) | 和局率 | 终局 decisive/step_limit/no_capture |
|---|---|---|---|---|
| `junqi_best_iter240.pt` (d2d37c1b) | 20/100 | 20/20 | 80% | 20/73/7 |
| `junqi_pool20_iter248.pt` (7d330eb3) | 22/100 | 22/23 | 77% | 23/70/7 |
| `junqi_iter688.pt` (260d3cd1) | 25/100 | 25/27 | 73% | 27/72/1 |

证据：`results/summary.json`、`results/tournament.jsonl:1-301`、`tools/analyze_tournament.py:41-80`；复算命令见附录 A。

三点判定：
1. 三模型对弱贪心基线在**决定性局**中均为 20/20、22/23、25/27；精确二项双侧 p≈1.9e-6/5.7e-6/5.6e-6（由 `results/tournament.jsonl` 复算，命令见附录 A）。这尚未检验对**生产引擎**的优势。三候选两两不可区分（McNemar p=0.860/0.442/0.743；配对 bootstrap 差 −2[−13,+9]、−5[−15,+5]、−3[−15,+9] 均含 0）；"三者等价"与"iter688 更优"都未获支持。
2. 按 §1 的 W/N 公式当前观测为 20–25%；最优 Wilson 95% 上界 34.3%。P0-01 已归档，按 `research/acceptance-criteria.md` 当前判定为**未达标**；排除和局 92.6% 的分母只有 27 局，不得单独宣布达标。
3. 不上线：git 跟踪范围内无权重文件；本机虽有 123 个 2026-11-19 的 `.pt`（被 `.gitignore:28` 忽略），均为 pre-`c1732af` 产物。站内人机**提示接口**用 `chooseStrongMove`（`server/server.js:700-715`，`:711` 明确 BOT 不可用）；可粘贴的托管 BOT 程序入口是 `public/bot-studio-bot.js:880-889`（`chooseStrongMove` 在 `:888`），服务端经 `server/hosted-bots.js:114-132` → `server/bot-api.js:134-166` `applyMove`（`public/hosted-reference.js:864` 也有 `act()`，但无引用、非默认入口）。仓库内已有 `neural-bot/neural_bot.py:34-38,207-214` 等 BOT API 适配器，但**未接入默认走子**，且外层 raw `state_dict` 与 `neural_bot.py:220-235` 期望的字典不兼容。

## 1. 口径与术语（P0-01 冻结对象）

| 术语 | 定义 | 当前值与证据 | 约束 |
|---|---|---|---|
| 含和局胜率（主口径） | `W/N`，N 为总局数 | 20/100、22/100、25/100（`results/summary.json`） | **65% 验收线以此为准**（用户 2026-11-26 确认） |
| 排除和局胜率（辅助） | `W/(W+L)`，必须同时写出分子分母与 N | 20/20、22/23、25/27（同上） | 只作诊断，不得单独宣布达标 |
| decisive / step_limit_draw / no_capture_draw | 有胜方 → decisive；无胜方先看 `no_capture_steps>=120` 再看 `step_count>=max_steps` | 分类实现 `eval_tournament.py:43-53` | 三者分别计数落盘 |
| 可复现 | 同 seed/布局哈希/座位/动作序列重放一致 | `tools/audit_replays.py:93-124` 的 `trace_match` | 只证明重放一致，**不等于无作弊** |
| collapse | 预注册判据：连续 3 个快照 `W/N` 下降且累计 ≥5pp，且相邻快照差的 CI 上界 <0（统计支持下降）；未满足只能写"证据不足" | 旧报告的非单调数据条件不同（`research/training-report.md:125-137`） | 判据在看新数据前冻结 |
| 可区分 | 配对 bootstrap 95%CI 不含 0 **且** McNemar 双侧 p<0.05 | `tools/analyze_tournament.py` 已落盘 `pairwise_ci`（B=10000、rng=0、精确二项 p） | 判据已冻结；当前三组均不可区分；未做多重比较校正 |
| 多重比较 | 三个候选两两比较 | 尚未校正 | 报告未校正 CI 并注明风险，或预先声明 Holm 校正 |

## 2. 冻结基线与不变量（所有对战类任务共用）

| 项 | 冻结值 | 证据 |
|---|---|---|
| 评测实现 | `D:\4-player-junqi\train_junqi_5070ti.py`（外层）；同时记录 `eval_tournament.py` 与 `tools/analyze_tournament.py` 的 sha256 | P0-02 后 meta 同时写 `impl_file_sha256`、`eval_tournament_sha256`、`analyze_tournament_sha256`、`layout_generator_sha256` |
| 基线 | `HeuristicBotWrapper`，名称写进 meta | P0-02 后由 `BASELINE_REGISTRY` 实例化；未知 `--baseline` 直接报错，默认行为不变 |
| 种子 | `seed_base=90000`，每局 `seed=seed_base+g` | `eval_tournament.py:135-139` |
| 座位 | 偶数局模型 team0，奇数局 team1 | `eval_tournament.py:139` |
| 动作 | 模型与基线均 `logits.argmax` | `eval_tournament.py:74-77` |
| 上限 | `max_steps=240`（P0-02 已参数化为 `--max-steps`，默认值仍冻结为 240） | `eval_tournament.py` meta 写入实际值 |
| 架构 | `JunqiActorCritic(hidden_dim=160, num_blocks=8)`，raw state_dict | `eval_tournament.py:97-99`；`train_junqi_5070ti.py:629-664,982-983` |
| 三个候选 | 完整 sha256 写入 meta；旧值 d2d37c1b… / 7d330eb3… / 260d3cd1… | `results/tournament.jsonl:1` |
| 布局生成 | 评测侧没有 formations 参数：布局由 `JunqiSelfPlayEnv.reset()` 的全局随机 + seed 决定；冻结布局生成器源码 sha256 + `seed_base` + 逐局 `layout_hash`；formations JSON 只属训练侧可选变量（D6） | `train_junqi_5070ti.py:164-200,202`；`eval_tournament.py:56-57,62-65` |

公共命令前缀（来自 `results/README.md:26-30`；下文所有 `$base` 命令均需先设置）：

```powershell
$base = "$env:APPDATA\uv\python\cpython-3.12.12-windows-x86_64-none\python.exe"
$dep  = "$env:TEMP\junqi-eval-venv\site-deps"
$env:PYTHONPATH = "$dep;D:\4-player-junqi"
$env:OMP_NUM_THREADS = '1'
New-Item -ItemType Directory -Force -Path D:\4-player-junqi\results\derived | Out-Null
```

所有派生结果写入 `D:\4-player-junqi\results\derived\`（本地产物，不入库；`.gitignore:22` 已忽略）；历史 `results/*.json(l)` 只读归档。

## 3. 阶段任务表

| ID | 阶段 | 目标 | 依赖 | 初始状态 |
|---|---|---|---|---|
| P0-01 | P0 | 冻结口径与 65% 分母 | 无 | ✅ 已归档（2026-11-26，`research/acceptance-criteria.md`） |
| P0-02 | P0 | 评测器与统计落盘加固 | P0-04a | ✅ 已完成（脚本加固 + 100 局复算 + 8 局双跑 diff_count=0） |
| P0-03 | P0 | 回放审计分层抽样与过期证据刷新 | P0-04b | ✅ 已执行（33 局分层审计 + seed90001 定向复核；iter688 no_capture 仅 1 局已标注不足） |
| P0-04a/b | P0 | a: torch 环境重建；b: 8 局冒烟 | a: 用户批准；b: P0-02 + a | ✅ a/b 均已完成（CUDA 环境 manifest + 16 局冒烟） |
| P0-05 | P0 | 旧报告账目与证据订正 | 文档项无依赖；38 次命中复算项依赖 P0-03 | ✅ 订正表已产出；E-05/E-06 已回填，E-02/03/04 仍待 D6 |
| P1-01 | P1 | 300 局/候选配对复评与功效判定 | P0-01（仅判定）、P0-02/03/04b/05 + D4 | 待决策 |
| P1-02 | P1 | c1732af 修复后基线重训 | P0-04a + GPU 独占 + D8 | ✅ 已完成（400 迭代、41 份权重、冻结权重未动） |
| P1-03 | P1 | val_map ×10→×1 单变量对照 | P1-02 + D8 | 待决策 |
| P1-04 | P1 | collapse 量化（只加评测快照） | P1-02 + P0-04b | 未开始 |
| P2-01 | P2 | 产品接入门禁与上线决策 | P1-01 + 用户决策 | 待决策 |

### P0-01 冻结口径与 65% 分母

- **目标**：把"65% 达成与否"变成单一可判定公式，消除排除和局口径造成的假达标。
- **只改一项**：仅文档口径文字，不动脚本阈值、不动历史数据。
- **验收线**：正式验收表写明"65% = W/N（含和局）"，并同时列出 `W/(W+L)` 及各自分母；明确当前 20/100 与 20/20 的差别；新报告不得引用排除和局 92.6% 宣布达标。口径已由用户确认，不构成阻塞。
- **产物**：`D:\4-player-junqi\research\acceptance-criteria.md`，记录确认日期与 sha256。
- **状态更新（2026-11-26）**：✅ 完成；日期 = 2026-11-26；证据路径 = `research/acceptance-criteria.md`；sha256 = `dd3efd6cd25efc673d5eb3dd16cb6c3fc20f8f4d68bb7cf8fc7fb8357fa800e3`；操作者 = Claude Code（本机，用户确认口径）。当前按 W/N 判定 20–25% 未达标；W/(W+L) 仅诊断。

### P0-02 评测器与统计落盘加固

- **目标**：修复让数字不可信的接口缺陷，并让统计结果机器可读。
- **只改一项**：先改 `eval_tournament.py` 的 CLI/meta，再单独提交 `tools/analyze_tournament.py` 的落盘；对战逻辑与终局分类不动。
- **验收线**：
  - `--baseline` 真正参与实例化或遇未知名称直接报错（现状 `eval_tournament.py:115` 硬编码、`:123` 只写 meta）。
  - `--replay` 帮助文本与实现一致（现状 `:110` 声称只存和局/败局，`:156-157` 实际保留全部 trace）。
  - `max_steps` 参数化且 meta 写实际值（现状 `:60,126` 为 240 硬编码）。
  - meta 增加 `git_commit`、工作区 dirty 标记、`cmdline`、python/torch/numpy 版本、`impl_file` sha256，并同时写入 `eval_tournament.py`、`tools/analyze_tournament.py` 的 sha256，以及布局生成器源码 sha256（评测侧不使用 formations JSON）。
  - `tools/analyze_tournament.py:18,85` 的 `--out` 默认值改为必填或指向 `results/derived/`，禁止再默认写回被跟踪的 `results/summary.json`；写盘前创建父目录（`:85` 当前不会 mkdir）。
  - `pairwise_ci` 占位字符串改为机器可读 JSON：`bootstrap_B=10000`、`rng_seed`、每个两两差的 `ci_lo/ci_hi`、`mcnemar_b/c/p`、`decisive_diff_ci`、`step_limit_diff_ci`、`termination_counts`、`seat_split`，以及 `per_ckpt` 的 W/N、decisive 率、step_limit 率的 bootstrap/Wilson CI（供 P1-04 使用）；终局率配对 bootstrap 与胜局 bootstrap 使用同一 B 与 seed。
  - 同 seed 8 局两次运行的核心字段（seed/座位/winner/终局/步数/布局哈希）完全一致。
- **命令**（两个候选才能触发两两统计；两次运行验证可复现）：
  ```powershell
  & $base D:\4-player-junqi\eval_tournament.py --candidates D:\4-player-junqi\junqi_best_iter240.pt D:\4-player-junqi\junqi_iter688.pt --games 8 --seed-base 90000 --out D:\4-player-junqi\results\derived\smoke_8.jsonl --replay
  & $base D:\4-player-junqi\eval_tournament.py --candidates D:\4-player-junqi\junqi_best_iter240.pt D:\4-player-junqi\junqi_iter688.pt --games 8 --seed-base 90000 --out D:\4-player-junqi\results\derived\smoke_8_repeat.jsonl --replay
  & $base D:\4-player-junqi\tools\analyze_tournament.py --data D:\4-player-junqi\results\derived\smoke_8.jsonl --out D:\4-player-junqi\results\derived\stats_8.json
  PYTHONIOENCODING=utf-8 python -c "import json,pathlib; p=pathlib.Path('D:/4-player-junqi/results/derived'); k=('seed','model_team','winner_team','termination','plies','layout_hash'); f=lambda q:[{x:r[x] for x in k} for r in map(json.loads,(p/q).read_text(encoding='utf-8').splitlines()) if r['type']=='game']; a,b=f('smoke_8.jsonl'),f('smoke_8_repeat.jsonl'); (p/'repro_check_8.json').write_text(json.dumps({'n':len(a),'diff_count':sum(x!=y for x,y in zip(a,b))}),encoding='utf-8')"
  ```
- **验收判定**：`repro_check_8.json` 的 `diff_count == 0`。
- **产物**：`results/derived/smoke_8.jsonl`、`smoke_8_repeat.jsonl`、`stats_8.json`、`repro_check_8.json` 及各自 sha256。
- **状态更新（2026-11-26）**：✅ 完成；日期 = 2026-11-26；证据路径/sha256 = `eval_tournament.py`（`abc9c30a797b6459c0baf95c983f17f2b3fceb031d2ae0ec319e0cc1502eab90`）、`tools/analyze_tournament.py`（`d515c43773ed6b18cd144f4d2797031171455b3eb51dda6f902c73626ac1c6c7`）、`results/derived/smoke_8.jsonl`（`77afd1d64902b370aed4fde07f4a19cc0837c9649e40c452e2c84a40276e6f9e`）、`smoke_8_repeat.jsonl`（`b90245609ff6259c74da10d89d1892f44a073f880ddc063b5acb3ead06a84d63`）、`stats_8.json`（`86b18ee34b2815fe1fd3bed1b615a8193fad24d545c360fb9c933283a624ca98`）、`repro_check_8.json`（`62819050d12e6f3af6442be0ec19d1e4112bb3f3a09910bdcfb527627fc6d86a`，n=16、diff_count=0）、`summary_100_verify.json`（`04bcbaed922ceb399860921b2b524e0d5c239f1eb0789d4b17f60fc9f205e12c`，100 局复算数字不变）；操作者 = Claude Code（本机）。`--baseline` 注册表已修复为实例化，`--max-steps` 已参数化；未改对战逻辑与终局分类；100 局配对统计仍为两两不可区分（McNemar p=0.860/0.442/0.743）。

### P0-03 回放审计分层抽样与过期证据刷新

- **目标**：补齐决定性局覆盖，作废坐标修复前的过期命中数。
- **只改一项**：只改 `tools/audit_replays.py` 的抽样与输出，不改 belief 判定算法（现算法见 `:75-101`）。
- **验收线**：
  - 新增 argparse `--data/--out/--per-class/--per-ckpt/--sample-seed`；`--per-class` 定义为"每个 checkpoint 每类局数"，`--per-ckpt` 为候选数。
  - 分层抽样：每个 checkpoint 的 decisive ≥4 局、step_limit_draw ≥4 局、no_capture_draw ≥1 局（`junqi_iter688.pt` 全样本仅 1 局，样本不足须在产物中注明），覆盖 3 个 checkpoint（现状 `:33-38` 的 `pool[:4]` 只抽 12 局且全为和局；300 局中有 70 局 decisive）。
  - 产物顶层含 `sample_counts`（键为 checkpoint×termination）与 `sample_seed`，判定条件为每格达到配额；输出保留 `:121` 的 `belief_encoding_mismatches` 与 `trace_match`，附文字"trace_match 只证明可复现，不证明无作弊"。
  - 新增"旗通道清零前后行和对照"输出，用于排查 belief 行和 0.6575 的成因（旧报告的剪枝归因同样待订正）。
  - 不覆盖已入库的 `results/replay_audit.json`：执行前后分别记录 `Get-FileHash results\replay_audit.json` 并判定一致（现状 `:141-143` 直接覆盖写）。
- **命令**：`& $base D:\4-player-junqi\tools\audit_replays.py --data D:\4-player-junqi\results\tournament.jsonl --out D:\4-player-junqi\results\derived\replay_audit_stratified.json --per-class 4 --per-ckpt 3 --sample-seed 20261126`
- **产物**：`results/derived/replay_audit_stratified.json`（含 sha256 与执行前后旧文件哈希）。
- **状态更新（2026-11-26）**：✅ 完成；日期 = 2026-11-26；证据路径/sha256 = `tools/audit_replays.py`（`0b9cca5ba9306baefbaf200b4a2814d40e951654d2d56be8925ab76e69989460`）、`results/derived/replay_audit_stratified.json`（`c2434b8c2c380eb051fe618b540404ebfb7e09b18427dcee6bb0c14aa1c7ea2e`）、`results/derived/audit_seed90001.json`（`0a08895cca49456a6a74abe31c4888777b261930a08de2657d87e7e4a60f747d`）；被跟踪的 `results/replay_audit.json` 当前磁盘 sha256 = `7397d2f4612f4bb082162b85aeb63e8fe252d9558fb373353f16b6e9376d912a`，`git diff -- results/` 为空且脚本 `--out` 指向 `results/derived/` 并拒绝写归档路径，归档未被覆盖；操作者 = Claude Code（本机）。33 局（12/12/9）trace 复现 33/33、编码不一致 0、非亮旗精确命中 857 次（31/33 局）、旗通道事件 89 次；iter688 的 no_capture 仅 1 局，产物 `shortfalls` 已记 3 局缺口，other_draw 三类均为 0（输入无该类别）。同 seed 定向复核：iter248/seed90001 当前算法为 74 次（旧 38 次作废；不同样本不可互换）。仍附免责声明：trace_match 只证明可复现，不证明无作弊。

### P0-04a/b torch 环境重建 + 8 局冒烟

- **P0-04a 目标**：恢复可运行 CUDA 复评环境（与脚本修复无关，可先行）。
- **只改一项**：只重建本机依赖目录并记录版本；不改代码、不动模型文件。
- **验收线**：`torch.__version__ == 2.10.0+cu128`、`torch.cuda.is_available() == True`；记录 python/numpy 版本与依赖目录哈希。
- **命令**（代理清空不可省，见 `results/README.md:17`、`research/training-report.md:8-12`）：
  ```powershell
  $env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''
  & $base -m pip install --target $dep "torch==2.10.0" --index-url https://download.pytorch.org/whl/cu128
  & $base -m pip install --target $dep numpy==2.5.5 numba==0.68.1 llvmlite==0.50.0 gymnasium==1.4.0 pettingzoo==1.27.0 onnx==1.23.2 ml_dtypes==0.7.0
  & $base -c "import torch,numpy;print(torch.__version__,torch.cuda.is_available(),numpy.__version__)"
  ```
- **P0-04b 目标**：用 P0-02 修复后的脚本执行 8 局冒烟，验收 trace 完整、同 seed 核心字段一致。
- **依赖**：a 依赖用户批准 GPU/网络；b 依赖 P0-02 + a。
- **产物**：a → `results/derived/env_manifest.json`；b → P0-02 的 `smoke_8*.jsonl` / `stats_8.json`。
- **状态更新（2026-11-26）**：✅ 完成；日期 = 2026-11-26；证据路径/sha256 = `results/derived/env_manifest.json`（`ab839f16290bad10bf9db02dcf7fbda88e23d2e056cfcd5bf1405fe6b9eb968d`，python 3.12.12 / torch 2.10.0+cu128 / cuda=True / GPU RTX 5070 Ti Laptop / numpy 2.5.5 / git fe994ed）、`repro_check_8.json`（`62819050d12e6f3af6442be0ec19d1e4112bb3f3a09910bdcfb527627fc6d86a`，n=16、diff_count=0）；操作者 = Claude Code（本机）。依赖安装于全新目录 `%TEMP%\junqi-eval-venv\site-deps-20261126`，未删除任何既有依赖；pip 报 fiftyone/voxel51-eta 全局依赖冲突，与评测链无关。未启动训练；GPU 独占时段仍按 D2。

### P0-05 旧报告账目与证据订正

- **目标**：消除"报告称通过但证据缺失/自相矛盾"的条目。
- **只改一项**：仅文档表述与证据标注，不改实验数据、不改既有测试断言。
- **验收线**：产出逐行订正表，每行含旧文件:旧行号、新文件:新行号、订正后的精确字符串、订正前后文件 sha256。文档即可订正的项先行；"38 次命中"一项待 P0-03 产物落盘后按 `belief_exact_match_nonflag` 复算填入，修正值未定，未产出前写"待复核"。
- **覆盖项**：`research/training-report.md:218` 的 50W3L147D ≠ 50W1L149D；`:184,188,197` 的"Top-200 ≥200 套已入库"与实际各 40 套且位于被忽略的 workspace 冲突；`research/model-review-report.md:37` 引用的 `results/smoke.jsonl` 不存在；`:62` 的"38 次精确命中"过期；collapse 与 Rew 转正叙述标注"未测量"；三个旧 `.pt` 标注 pre-`c1732af`。
- **产物**：`D:\4-player-junqi\research\report-errata-20261126.md`（含 sha256）。
- **状态更新（2026-11-26）**：✅ 完成（11 行订正表）；日期 = 2026-11-26；证据路径/sha256 = `research/report-errata-20261126.md`（`24073659666cb6d5629f1c9715f385a4999ad2b1d7caab7c1e5c9b539010f20f`）、`research/acceptance-criteria.md`（`dd3efd6cd25efc673d5eb3dd16cb6c3fc20f8f4d68bb7cf8fc7fb8357fa800e3`）；操作者 = Claude Code（本机）。E-05 已回填 smoke/diff_count 证据，E-06 已回填同 seed 定向复核 74 次并注明旧 38 次作废与分层样本 857 次不可互换；原报告保持只读。E-02/E-03/E-04 的 Top-200 最终去向仍待 D6，不以本状态替代用户决策。

### P1-01 300 局/候选配对复评与功效判定

- **目标**：在冻结条件下把每候选从 100 局提到 300 局，判定三模型是否可区分。
- **只改一项**：只改 `--games`（100→300），其余条件与 `results/README.md:31-35` 完全一致。
- **验收线**：
  - 双口径同时报告：`W/N` 与 `W/(W+L)`，后者必须同时写出 W+L 与 N；禁止只写 92.6% 称达标。
  - 判据预注册：CI 不含 0 且 McNemar p<0.05 才可宣布可区分；否则写"并列/功效不足"；若 CI 半宽仍 >5pp，不得宣称"等同"。
  - 座位拆分、终局分布、逐局布局哈希、git commit、cmdline、三个脚本 sha256、完整 checkpoint sha256 全部落盘。
  - 运行可先行；**正式达标判定**需 P0-01 产物 `research/acceptance-criteria.md`。
  - 运行前按实测不一致对 `b+c`（历史三组为 32/27/37 对/100，不是单向 b 或 c）做 McNemar 功效计算；若 300 局功效不足，须在报告中写明"缩窄区间但不足以判定"而非"不可区分"。
- **命令**：
  ```powershell
  & $base D:\4-player-junqi\eval_tournament.py --candidates D:\4-player-junqi\junqi_best_iter240.pt D:\4-player-junqi\junqi_pool20_iter248.pt D:\4-player-junqi\junqi_iter688.pt --games 300 --seed-base 90000 --out D:\4-player-junqi\results\derived\tournament_300.jsonl --replay
  & $base D:\4-player-junqi\tools\analyze_tournament.py --data D:\4-player-junqi\results\derived\tournament_300.jsonl --out D:\4-player-junqi\results\derived\summary_300.json
  ```
- **产物**：`results/derived/tournament_300.jsonl`、`summary_300.json` 及各自 sha256。
- **状态更新（2026-11-27）**：✅ 完成；日期 = 2026-11-27；证据路径/sha256 = `results/derived/manifest_p1-01.json`（`d6b2c322642c4bf9dda1010ced8e0ab5ede2cb8a7d89ff2bb67831fe41f82a42`）、`tournament_300.jsonl`（`c203bdc0436f058d28675f67c8dc5c615fd1db82edb8e30f48c9395b2aa90c25`，1501 行）、`summary_300.json`（`40f53e775e6742df6469c9273c4c343dc47b4243090cd048ae741f4f81e7409c`）、`audit_300.json`（`c2f19a57c5902a385d151c665681131478bfde69ee0355ad6a9ad7e3ed385dcc`）、`research/p1-01-result.md`（`500c6ae99fde3bcceeb60a2a406b9114757575ecd162d190f4c73456c9f63991`）；操作者 = Claude Code（本机，用户授权 GPU 时段）。主口径 `W/N`：iter240 60/300=20.0%、pool248 75/300=25.0%、iter688 59/300=19.7%、iter400 118/300=39.3%、iter800 60/300=20.0%，全部未达 65%（最优 Wilson 上界 45.0%）。Holm 校正后 `iter400` 显著优于其余四候选，其中 `iter400 − iter800 = +19.33pp`、CI [+12.67, +26.00]、McNemar b/c=87/29、Holm p=5.18e−07；`iter800` 与三份 pre-fix 两两不可区分。回放审计 56 局 trace 56/56、编码不一致 0、旗通道事件 146；belief 行和违规 50/56、非亮旗精确命中 1750 次（51/56 局），未逐点归因前不得定性为信息泄漏。结论：停止盲目续训，以 iter400 为 post-fix 基线转稳定性改造与 P1-04；两个快照不足以判定 collapse，仅记录显著回退。

### P1-02 c1732af 修复后基线重训

- **目标**：产出修复后的 post-fix checkpoint，解除"所有权重都是旧代码产物"的阻塞。
- **只改一项**：只换代码版本（pre-fix → post-fix），并冻结一个**已验证可跑**的训练配置（见 D8）；评测条件不变；不新增 argparse。默认配置 24 env×512 steps×batch 2048（`train_junqi_5070ti.py:1000-1005`）已实测 OOM（`research/training-report.md:166-170`），不得直接使用。
- **D8 注入方式**：该脚本无 argparse/环境变量/YAML 入口，配置硬编码在 `:1000-1005` 的 `GPUTrainConfig`；必须在**隔离工作副本**中显式修改这些字段并保存 diff 与改后文件 sha256，manifest 中校验实际生效值。不得在含冻结候选的目录直接运行（`:982-983` 会覆盖同名 `.pt`）。
- **验收线**：新 `.pt` 的 sha256 与 d2d37c1b/7d330eb3/260d3cd1 均不同；由运行包装（不改训练脚本）写出 manifest，含 `git rev-parse HEAD`、`GPUTrainConfig` 全字段实际值、seed、开始/结束时间、完整命令行；stdout 重定向到日志。旧快照不得用于评价修复效果。
- **命令**：
  ```powershell
  # <隔离副本> = 已在其中按 D8 修改 GPUTrainConfig 并保存 diff/sha256 的工作副本
  & $base <隔离副本>\train_junqi_5070ti.py *> D:\4-player-junqi\results\derived\train_p1-02.log
  ```
  在隔离目录运行前先校验三份冻结候选的 sha256 未变化；运行前后用 `git rev-parse HEAD`、`Get-FileHash` 与 `Get-Date` 写入 manifest。命令中的 `<隔离副本>` 在执行时替换为实际绝对路径并原样写入 manifest 的 `cmdline`。
- **产物**：新 `.pt` 全路径 + `results/derived/manifest_p1-02.json` + `train_p1-02.log`（含 sha256）。
- **状态更新（2026-11-26）**：✅ 完成；日期 = 2026-11-26；证据路径/sha256 = `results/derived/manifest_p1-02.json`（`9f5cd4ad692b627f7ffc9652e6744ccd92b25d3135c7f5987a09f383dc42b67a`）、`results/derived/train_p1-02.log`（`1d51c20602ad7e7c6560c923689fa206d3898ba68b3e3a3ac523811d6df35ce4`，UTF-8 解码副本 `710e9f10a830832e7f0f4c2da3157d45c614dc9b2a8b973e670bb916ef2f5f40`）、`workspace/train-p1-02/config.patch`（`637b4d967c59aceeccb010cdc37f63cc1713fc50159291cf859aad550e38adf6`）、`workspace/train-p1-02/train_junqi_5070ti.py`（`af9f5736bc6d555c4b0fd12ed70e680ccbcc55187dc535d0f1e444ebac4ce2cf`）；操作者 = Claude Code（本机，用户确认目标/配置/时段后启动）。实际运行 21:18:48→21:26:36（+08:00），退出码 0，400/400 迭代，峰值显存 5.36GB（未 OOM），SPS 约 250–466；`torch.compile` 因 TritonMissing 回退 eager。产物 41 份权重（iter010…iter400 + latest），全在 git 忽略的 `workspace/train-p1-02/`；最终候选 `junqi_iter400.pt` sha256 = `0cf0b9bd1be35a422f1759b25ef3ae3c57e152c9a601c72e42cc11d9741b0a19`，`junqi_rtx5070ti_latest.pt` sha256 = `f83ae9d5ccb9850fa21aae132945799bd08648c5c0319b876328978ce11196aa`（文件字节不同但 state_dict 逐键 `torch.equal` 全等，文件哈希差异来自 torch.save 序列化元数据）。两者 sha 与三份 pre-fix 候选均不同；manifest 记录训练前后三份冻结权重 sha 一致（`frozen_checkpoints_unchanged=true`），`git diff -- results/` 为空。未结束任何非本会话进程；明早 9 点看门狗未触发。
- **续训状态更新（2026-11-27，P1-02b）**：日期 = 2026-11-27；证据路径/sha256 = `results/derived/manifest_p1-02b-retry2.json`（`aadf2732c09b1b2e5572dffdfea2d8e115095f9b6e5c08261c3245299c34ba44`）、`train_p1-02b-retry2.log`（`a0cf8c9a865ab1e9c46aebb0a650ac35981605d604d59b560ca6c6c416758479`）、`workspace/train-p1-02b/resume_fixed.patch`（`5880adedcf19a8a8971a3253ad3538aed42e9964a61c4867e92c12bca4301a9e`）、`workspace/train-p1-02b/train_junqi_5070ti.py`（`3e411f25aae8e8575fbf7e1119684db94a78c811dd509cdc09caa03193d2a2a9`）；操作者 = Claude Code（本机，用户确认“从 iter400 继续 / 再 400 迭代 / 现在启动”后执行）。400/400 迭代、退出码 0、09:39:30→09:48:58（+08:00）、峰值 5.36GB；41 份新快照 `junqi_iter410.pt`…`junqi_iter800.pt` 在 git 忽略的 `workspace/train-p1-02b/`，末份 `junqi_iter800.pt` sha256 = `d09bff62f06330432a974310be0dee732b4301efb2589682a9d995bab620ca14`，与 `junqi_rtx5070ti_latest.pt` 逐键全等；全部新快照 finite，恢复源 iter400 与三份冻结权重 sha 前后一致。
  初期两次失败如实留证：首次因只恢复 policy 权重、scheduler 仍从 LR=3e-4 起，第 1 迭代 `PG=inf`、第 2 迭代 `Categorical.sample()` 的 multinomial `_assert_async` 触发 `TensorCompare.cu:109`（`manifest_p1-02b-failed.json` `32b99b87…`、`train_p1-02b-failed.log` `ce05fb31…`）；修复门禁代码笔误后的第二次失败为 `AttributeError: 'dict' object has no attribute 'grad'`（`6f679ec1…` / `cfdae4a3…`）。最终修复：LR 校正到 1e-5、`last_epoch=400`、`logp` 差 clamp ±20、非有限 loss/梯度/grad_norm 门禁。
  **manifest 字段订正（2026-11-27）**：`results/derived/manifest_p1-02b-retry2.json`（sha256 `aadf2732c09b1b2e5572dffdfea2d8e115095f9b6e5c08261c3245299c34ba44`）的 `config_actual.lr=3e-4` 是 `GPUTrainConfig` 的 dataclass 默认值，并非本次实际生效值；`workspace/train-p1-02b/resume_fixed.patch` 与日志首行 `[RESUME] ... lr=1e-5; last_epoch=400` 证明有效 LR 为 **1e-5**、`scheduler.last_epoch=400`。历史 manifest 保持只读，另在 `results/derived/manifest_p1-02b-retry2-corrected.json`（不入库）记录 `corrected_from_sha256` 与订正原因；后续引用有效 LR 时以订正文件为准，不得把 3e-4 写成续训实际配置。
  **质量警示（须带进 P1-01 解读）**：修复后日志无 `inf/nan`、无 `[SKIP]`，但 PG 量级多次达 1e4–1e6（clamp 饱和所致），说明该续训在统计意义上并不稳定；`junqi_iter800.pt` 只可作为“可评测的 post-fix 快照”，不得直接宣称训练收敛或效果优于 iter400。

### P1-03 val_map ×10→×1 单变量对照

- **目标**：检验"吃子奖励放大导致保守胶着"这一由回放间接支持的假设。
- **只改一项**：仅 `train_junqi_5070ti.py:426-441` 的 `val_map`（`:437` 表，×10→×1）；seed、迭代数、snapshot_interval、网络结构、训练配置（D8）、argmax 推理全部与 P1-02 相同。
- **验收线**：300 局配对中 `decisive_diff_ci` 不含 0 且方向为上升、`step_limit_diff_ci` 不含 0 且方向为下降；双口径胜率报告；若不显著，写"假设未获支持"。禁止改 `max_steps`（215/230 和局是 step_limit，且压哨胜局多）、禁止改网络结构。
- **命令**：训练命令同 P1-02（改动 val_map 后另存 checkpoint）；评测：
  ```powershell
  & $base D:\4-player-junqi\eval_tournament.py --candidates D:\4-player-junqi\<postfix_valmap1>.pt D:\4-player-junqi\<postfix_baseline>.pt --games 300 --seed-base 90000 --out D:\4-player-junqi\results\derived\tournament_valmap.jsonl --replay
  & $base D:\4-player-junqi\tools\analyze_tournament.py --data D:\4-player-junqi\results\derived\tournament_valmap.jsonl --out D:\4-player-junqi\results\derived\stats_valmap.json
  ```
  文件名在 P1-02/03 落盘后按实际填入并把 sha256 写入附录 A。
- **产物**：新 `.pt`、`results/derived/tournament_valmap.jsonl`、`stats_valmap.json` 及各自 sha256。

### P1-04 collapse 量化（只加评测快照）

- **目标**：把"长训 collapse"从叙事变为快照序列测量。
- **只改一项**：只增加评测候选快照，不改训练/模型。
- **验收线**：每个快照 ≥100 局，输出 iter → `W/N`、`W/(W+L)`、decisive 率、step_limit_draw 率及 CI（读 `stats_collapse_scan.json` 的 bootstrap 字段）；按 §1 预注册判据判定，不满足写"未观测到/证据不足"。缺 entropy 日志时（`train_junqi_5070ti.py:938` 已计算但 `:985-992` 不打印）不得用 entropy 叙事补位。
- **命令**（快照文件名落盘后填全；seed 与 §2 冻结值一致）：
  ```powershell
  & $base D:\4-player-junqi\eval_tournament.py --candidates <postfix_s010>.pt <postfix_s020>.pt <postfix_s030>.pt --games 100 --seed-base 90000 --out D:\4-player-junqi\results\derived\collapse_scan.jsonl --replay
  & $base D:\4-player-junqi\tools\analyze_tournament.py --data D:\4-player-junqi\results\derived\collapse_scan.jsonl --out D:\4-player-junqi\results\derived\stats_collapse_scan.json
  ```
- **产物**：`collapse_scan.jsonl`、`stats_collapse_scan.json` 及各自 sha256。

### P2-01 产品接入门禁与上线决策

- **目标**：决定模型是否进入主工程 BOT 工作流；本任务只产出决策，不切生产流量。
- **只改一项**：只做设计与决策，不改服务器默认走子；若选接入，需另立实施任务。
- **验收线**：决策文件字段固定为 `decision ∈ {不接入, 仅实验分支, 正式上线}`、判据、证据路径 + sha256；若接入，须各有一节写 schema 映射、严格暗棋投影回归、灰度与回滚方案；若不上线，按 §1 公式复算后填写 W/N 与判定。现状如实写入：提示接口 `server.js:700-715`（`:711` 明确 BOT 不可用）；可粘贴托管程序 `public/bot-studio-bot.js:880-889` → `server/hosted-bots.js:114-132` → `server/bot-api.js:134-166` `applyMove`；站内启发式实现 `bots/engine/search.js:278-337`；已有适配器 `neural-bot/neural_bot.py:34-38,207-214`，但外层 raw `state_dict` 与 `:220-235` 期望字典不兼容；`train_junqi_5070ti.py:316` 的 obs[16:28] 暴露盟友真兵种，与 `BOT_API.md:171` 冲突。
- **信息边界用例**：在 `code/siguo-junqi/neural-bot/test_info_boundary.py` 新增 `test_ally_type_hidden`，断言 ally type 在公开观测中为 null/空；这是本任务唯一允许的代码改动。
- **测试基线**：`cd code/siguo-junqi && npm test` 的失败测试名集合须与 `research/p0-baseline.md:64-71` 列出的 4 项既有基线一致且无新增失败（`README.md:40` 只记数量；不以退出码判定，不改断言）。
- **产物**：`D:\4-player-junqi\research\product-gate-decision.md`（含 sha256）。

## 4. 前置条件与用户决策

| ID | 关联任务 | 需拍板事项 | 未决后果 |
|---|---|---|---|
| D1 65% 口径 | P0-01、P1-01、P2-01 | 已确认含和局为主；已由 `research/acceptance-criteria.md` 归档 | 排除和局 92.6% 被误读为达标 |
| D2 GPU 独占 | P0-04a/b、P1-01/02/03/04 | 是否释放桌面占用并给出时段（历史多次 OOM）；P0 冒烟已完成，P1 仍待 | 数据不可比、中途抢占导致作废 |
| D3 环境重建 | P0-04a、P0-03 | 已于 2026-11-26 执行（见 P0-04a 状态与 `env_manifest.json`）；后续如需新依赖仍须批准 | 审计与复评已可运行 |
| D4 算力预算 | P1-01/02/03/04 | 是否批准 300–500 局/候选（900–1500 局）与多日训练 | 维持 100 局则 CI 跨 0，无法做取舍 |
| D5 旧资产处置 | P0-05、P1-02 | 旧三份 `.pt` 是否冻结为 pre-fix 归档 | 修复效果被错误归因到旧权重 |
| D6 布阵库入库 | P0-05 | Top-200 实际 40 套且 workspace 被忽略：补建 ≥200 套入库，还是订正文档为 40 套 | 报告继续声称"≥200 套已入库" |
| D7 是否上线 | P2-01 | 未达 65% 时是否允许实验分支接入、正式上线门槛 | 误用未显著模型或暗棋口径合规问题 |
| D8 重训配置 | P1-02/03/04 | 已确认并执行：2 env×64 steps×batch128 / 400 迭代（隔离副本，见 P1-02 状态） | P1-02 已完成；P1-03/04 沿用该配置做单变量对照 |

## 5. 可追溯性规范

每个 run 必须有一份 manifest，与产物同目录：

`run_id`、`task_id`、时间戳、`git rev-parse HEAD`、工作区是否 dirty、完整 `cmdline`、python/torch/numpy 版本与 GPU 型号、`impl_file`、三个脚本（`train_junqi_5070ti.py`、`eval_tournament.py`、`tools/analyze_tournament.py`）各自完整 sha256、每个 checkpoint 全路径与完整 sha256、`seed_base`、`games`、`seat_policy`、baseline 名称与实现 sha256、`max_steps`、布局生成器源码 sha256（评测侧不使用 formations JSON；训练侧若冻结布阵库另记路径与 sha256）、逐局 `layout_hash`、产物路径与各自 sha256、操作者与机器说明。现成基础已在 P0-02 补全（`eval_tournament.py` meta 含 git/dirty/cmdline/版本/三个脚本 sha256 等；`tools/analyze_tournament.py` 落盘 `pairwise_ci`），P1 运行仍须按本节逐项核对 manifest 完整。

历史 24–26% 数字缺 seed/命令行/哈希，只能标注"统计相容但不可对齐"，不得拼接进新结论（`research/training-report.md:108,213,218,232-233`）。所有统计命令显式 `--out` 到 `results/derived/`；P0-02 负责把 `tools/analyze_tournament.py:18,85` 的默认写回行为改掉。派生产物与权重不入库（`.gitignore:18` workspace、`:22` results/derived/、`:28-30` 权重规则）；`results/derived/` 已在当前工作区忽略，无需重复新增。

## 6. 统计与功效

- 沿用配对设计：同 seed + 座位奇偶轮换 + 同布局哈希；不同 seed 集的评测不得合并成同一结论。
- 两种胜率同时报分子/分母；配对差异已由 `tools/analyze_tournament.py` 落盘 bootstrap CI（B=10000、rng=0）与精确二项 McNemar 计数/p 值；终局率配对 CI 同批落盘（P0-02 已修 `decvec` 漏算胜局的缺陷），`pairwise_ci` 不再是占位字符串。
- 1094 局/候选是**独立比例** 20% vs 25% 达 80% 功效的参照值，不适用于冻结的配对设计；P1-01 运行前须按实测不一致对 `b+c`（历史三组为 (15,17)、(11,16)、(20,17)，合计 32/27/37 对/100）做 McNemar 功效计算，未算出前不得用 1094 为 300 局辩护。
- 300 局的目标是缩窄区间；若 CI 半宽仍 >5pp，只能写"区间缩窄但样本不足"，不得宣称"等同"或"可区分"。
- 三个候选两两比较须注明未做多重比较校正，或预先声明 Holm/Bonferroni 校正。
- 报告基于 `results/derived/` 下的产物路径与 sha256 引用数字，不在正文手抄易错统计值。

## 7. 信息边界与合规

- `train_junqi_5070ti.py:302-318` 的 `obs[16:28]` 暴露盟友真实兵种；`BOT_API.md:167,171` 要求盟友暗子 `type=null`、战报只含 id+outcome，服务端落实于 `server/bot-api.js:112-113,131-132`。任何产品接入必须做严格暗棋投影与回归（`code/siguo-junqi/neural-bot/test_info_boundary.py:15`，P2-01 新增盟友用例），且改输入编码属于新单变量实验，会使旧 checkpoint 不可比。
- `train_junqi_5070ti.py:141-144` 的 `on_commander_dead` 清零全部旗通道并注入真旗位，是 belief 行和异常的**疑似来源之一**；旧报告的"剪枝后未归一化"归因同样待订正。0.6575 的成因需按 P0-03 的旗通道清零前后行和对照逐点归因，不得先定性。
- `trace_match` 只写"可复现"；"非亮旗 belief 精确命中"须区分合法推理（工兵转弯/战斗收缩）与真值泄漏，未完成逐点归因前不得定性。
- `obs[59]` 用 `no_capture_steps/80`（`:329`），判和阈值已为 120（`:413`）；修该项属独立实验，不得混入 P1-03。
- "基线反事实归一后 2880 步仅 1 步动作改变"尚无可复核产物，作为**待复核假设**，不得作为已验证事实写入结论。

## 8. 不做清单

1. 不改 `max_steps` 治和棋：215/230 和局是 step_limit，且压哨胜局多；改上限会破坏可比性。
2. 不复用无 seed/命令行/哈希的历史 24–26% 作为新结论证据。
3. 不写未经快照序列测量的 collapse 因果、不把 loss 下降当作收敛证明。
4. 不把排除和局 92.6% 当作 65% 达标。
5. 不新增 npm test 失败、不修改既有 4 项失败断言（`README.md:40`）。
6. 不提交权重、派生评测数据、workspace 目录；不预设任何状态为"通过"。
7. 不把不存在的 `results/smoke.jsonl` 当已存在证据。
8. 不复用坐标修复前的"38 次精确命中"；同 seed 定向复核为 74 次（`results/derived/audit_seed90001.json`），分层样本 857 次属不同样本；未完成逐点归因前不得写"信息泄漏"。
9. 不把"Top-200 ≥200 套已入库"与"50W1L149D"当已核事实。
10. 不把 2026-11-19 的 `.pt` 当 post-fix 权重评价 `c1732af` 效果。
11. 不使用默认 24 env×512 steps×batch 2048 直接重训（本机已实测 OOM）。

## 9. 风险与开放问题

| 风险 | 影响任务 | 谁拍板 |
|---|---|---|
| GPU 被桌面进程占用、多次 OOM | P0-04a/b、P1-01/02/03/04 | 用户（D2） |
| torch 依赖目录残缺、重建可能失败 | P0-03、P1 全部 | 用户（D3） |
| 排除和局口径误判达标 | P0-01、P1-01、P2-01 | 用户（D1） |
| 旧 `.pt` 全为 pre-fix，修复效果不可归因 | P0-05、P1-02 | 用户（D5） |
| `--baseline` 假参数导致换基线后数据不可比 | P0-02、P1-01 | 执行者按 P0-02 修复 |
| 算力预算未批（D4） | P1-01/02/03/04 无法启动 | 用户（D4） |
| 重训配置未冻结（D8），默认配置 OOM | P1-02/03/04 | 用户（D8） |
| collapse 判据与快照序列未产出 | P1-04 不得下因果结论 | 执行者 |
| 历史 24–26% 无 seed/cmdline/hash | P0-05、P1-01 不得拼接 | 执行者 |
| argmax（评测）与采样（产品）推理策略不同 | P2-01 | 用户（D7） |
| 严格暗棋投影会改变模型输入，需重训 | P2-01 | 用户（D7） |
| 过期证据残留（38 次命中、`smoke.jsonl` 缺失） | P0-05 | 执行者按 P0-03/05 订正 |
| Top-200 实际 40 套、布阵库未入库 | P0-05、P1-03 | 用户（D6） |
| raw state_dict 与 GraphPolicyValue 不兼容，接入可能只产出可行性结论 | P2-01 | 用户（D7） |

## 附录 A 命令速查

- 统计复算（在 §2 公共前缀下执行，目录已由前缀创建；必须显式 `--out`）：`& $base D:\4-player-junqi\tools\analyze_tournament.py --data D:\4-player-junqi\results\tournament.jsonl --out D:\4-player-junqi\results\derived\summary_recheck.json`
- 决定性局精确二项双侧 p 复算：
  ```bash
  PYTHONIOENCODING=utf-8 python - <<'PY'
  from math import comb
  for w,n in [(20,20),(22,23),(25,27)]:
      print(2*sum(comb(n,k) for k in range(w,n+1))/2**n)
  PY
  ```
- 8 局冒烟、300 局复评、分层审计、重训与消融：见对应任务卡；公共前缀见 §2。
- 单向测试基线：`cd code/siguo-junqi && npm test`（114/110/4，`README.md:40`）；`python -m unittest discover -s workspace/siguo-junqi/junqi_env -p 'test_*.py'`（56 项）。

## 附录 B 产物字段

- `results/derived/tournament_*.jsonl`：meta 行（见 §2 + §5 manifest）+ game 行（`checkpoint`、`checkpoint_sha256`、`game_idx`、`model_team`、`model_won`、`model_lost`、`seed`、`layout_hash`、`winner_team`、`termination`、`plies`、`step_count`、`no_capture_steps`、`elapsed_s`、`trace`；字段定义 `eval_tournament.py:84-94,146-155`）。
- `results/derived/summary_*.json`：至少含 `n/wins/losses/draws/decisive` + 机器可读 `pairwise_ci`（含终局率差 CI）、终局分布、座位拆分（P0-02 扩展）。
- `results/derived/replay_audit_*.json`：`sample_counts`、`sample_seed`、`trace_match`、`belief_prob_violations`、`belief_encoding_mismatches`、`belief_exact_match_nonflag`、`belief_rows_checked`、旗通道清零前后行和对照（`tools/audit_replays.py:116-124` + P0-03 扩展）。

## 附录 C 旧报告订正对照（P0-05 输入）

| 原文/位置 | 问题 | 订正方向 |
|---|---|---|
| `research/training-report.md:218` | 24W1L75D + 26W2L72D = 50W3L147D ≠ 50W1L149D | 更正合计或标注口径差异 |
| `research/training-report.md:184,188,197` | Top-200 ≥200 套已入库 | 实际 `formations_top200.json`/`_v2.json` 各 40 套且 workspace 被忽略；补建或订正表述 |
| `research/model-review-report.md:37` | 引用 `results/smoke.jsonl` | 文件不存在，删除或重新产出 |
| `research/model-review-report.md:62-63` | "38 次精确命中" | 坐标修复前计数作废；同 seed 定向复核 74 次（`results/derived/audit_seed90001.json`），分层样本 857 次样本不同不可互换；逐点归因前不得定性 |
| `research/training-report.md:125-137,139` | collapse / Rew 转正被当作已证事实 | 标注条件不同、未测量 |
| 全部三份 `.pt` | 11-19 产物，早于 11-24 的 `c1732af` | 标 pre-fix，不用于评价 GAE/PPO 修复效果 |

## 附录 D 变更记录

- 2026-11-26 v1：草案建立，基线证据来自 300 局配对复评与 12 代理对质分析；用户确认范围（完整 P0→P1→P2）、落点、65% 口径与脚本修复前置。
- 2026-11-26 v2：三代理审查后修订——修正 P2 走子链路与适配器现状、拆开 P0-04a/b 消除循环依赖、补齐产物与命令、修正过期行号、把 398/2880 等待复核数字降级、加入 D8 重训配置。
- 2026-11-26 v3：二次复核后修订——修正托管 BOT 入口、no_capture 配额改为 ≥1、D8 配置注入到隔离工作副本、McNemar 不一致对改为 b+c 合计、补复现对比产物、去掉不可验收的 formations meta、统一"38 次命中待复核"表述（此版 sha256 = `a49fa84b235eb96079e80425cec555301d112d5095ec7d4f7241c2ea8e39440b`，为 `acceptance-criteria.md` / `report-errata-20261126.md` 引用的冻结基准）。
- 2026-11-26 v4：P0 执行回填——P0-01/02/03/04a/04b/05 均标记完成并附证据路径、sha256、操作者；修正 §1/§2/§5/§6/§8 中被 P0 改动作废的"当前状态"描述；E-06 同 seed 定向复核为 74 次；P1/P2 仍为待决策，未启动训练、未提交权重或派生产物。本文件为状态回填后版本，按定义不能自引用 sha256。
- 2026-11-26 v5：P1-02 执行回填——在 git 忽略的 `workspace/train-p1-02/` 隔离副本中以 2×64×128/400 迭代完成 post-fix 重训（退出码 0、峰值 5.36GB），新增 `junqi_iter400.pt`（sha `0cf0b9bd…41b0a19`）与 41 份产物；D8 标为已执行，P0-01/P0-05 状态中的 `acceptance-criteria.md` sha 同步到 D8 更新后的版本。P1-01/03/04、P2-01 仍待决策。
- 2026-11-27 v6：P1-02b 续训回填——从 `junqi_iter400.pt` 恢复再跑 400 迭代（iter410–800），两次失败证据保留，最终以 LR 校正 + logp clamp + 非有限门禁跑完；标记 PG 量级 1e4–1e6 的质量警示，禁止把 iter800 当作收敛或优于 iter400 的结论。P1-01/03/04、P2-01 仍待决策。
- 状态变更须在对应任务卡追加"日期 / 证据路径 / sha256 / 操作者"四字段。
