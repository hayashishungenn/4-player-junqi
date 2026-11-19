# code/ 目录说明

`siguo-junqi/` 是本项目的可运行主工程快照，基于 MIT 许可的开源项目
[BitByBitG/siguo-junqi](https://github.com/BitByBitG/siguo-junqi)（v2.12.2，commit `f4b911a`）
修改而来，包含本项目的 P2–P6 增强（多档难度、逐手评分、复盘分析、分析 API、AI 提示、自我对弈训练记录）。

- 原项目许可证与版权声明见 `siguo-junqi/LICENSE`，此处完整保留。
- 已排除：`node_modules/`、`.git/`、`*.pt` 模型权重、`data/accounts.json` 等账号/运行数据，以及无明确许可证的参考仓库克隆。
- 运行：`cd siguo-junqi && npm ci && npm start`（Node ≥18），默认 `http://localhost:3000`。
- 分析棋谱：`node scripts/analyze-replay.js <replay.json>`。
- 自我对弈：`cd neural-bot && python self_play.py --games 6 --device cpu --modes alliance --record training.jsonl`（需自行安装 `torch>=2.2`、`requests>=2.31`、`cryptography>=42`）。

本仓库其余内容（根目录 `research/`、`reverse-engineering/`）为逆向研究、源码分析与评测文档，与主工程代码相互独立。
