# 自我对弈训练执行报告

日期：2026-11-19
对象：`workspace/siguo-junqi/neural-bot`（GraphPolicyValue GNN + 自我对弈训练器）。

## 1. 环境阻塞的解决（原评测报告记为阻塞，现已解除）

原状态：系统 Python 3.14.3 由 uv 管理（禁止全局安装），且环境代理 `127.0.0.1:7899` 未启动，pip 报 `WinError 10061 / ProxyError`，无法安装 torch。

解决方式（未修改系统环境、未改仓库依赖）：
1. 在临时目录建立独立 venv（`%TEMP%\junqi-venv`），不入库。
2. **清空代理环境变量**后，PyTorch CPU 源 `https://download.pytorch.org/whl/cpu` 与清华 PyPI 镜像均可直连。
3. 安装：`torch-2.15.0+cpu`、`requests`、`cryptography`、`numpy` 及其依赖。
4. 训练器新增 `--record` 参数：每局写一行 JSONL（时间戳、局序、模式、胜者、步数、loss、累计局数、设备、模型），结束写 `*-summary.json`（各模式局数、胜者分布、平均 loss）。记录输出到临时目录，不提交。

## 2. 实际执行的自我对弈

命令（在 `neural-bot/` 下，CPU）：

```text
python self_play.py --games 6 --device cpu --modes alliance \
  --record %TEMP%\junqi-training.jsonl --save-every 2 --warmup-games 0 --epochs 1
```

真实结果（`training-summary.json`，UTF-8 解码）：

```json
{
  "games": 6,
  "by_mode": { "alliance": 6 },
  "winners": { "和棋": 6 },
  "loss_sum": -4.616059571504593,
  "avg_loss": -0.769343
}
```

逐局记录（局序 / 模式 / 胜者 / 步数 / loss）：

| 局 | 模式 | 胜者 | 步数 | loss |
|---|---|---|---|---|
| 1 | alliance | 和棋 | 256 | -1.528765 |
| 2 | alliance | 和棋 | 96 | -1.021297 |
| 3 | alliance | 和棋 | 187 | -0.984266 |
| 4 | alliance | 和棋 | 108 | -0.358639 |
| 5 | alliance | 和棋 | 262 | -0.413794 |
| 6 | alliance | 和棋 | 253 | -0.309299 |

模型：`model.pt`（约 1.47 MB），由 `neural-bot/.gitignore` 的 `*.pt` 规则排除，**未提交**（符合"不得提交大体积训练权重"）。临时的对局历史/账号数据目录亦未提交。

## 3. 结果解读（如实，不做夸大）

- 训练链路完整跑通：本地规则进程（`self_play_env.mjs`）↔ 编码器 ↔ GNN ↔ AdamW ↔ 模型保存，四方联盟模式全部正常。
- 6 局全部为和棋：未训练/仅 6 局训练的策略倾向于保守走子，触发了自我对弈环境的自动和棋条件（连续无战损或步数上限）。步数 96–262 说明对局确实推进而非立即终止。
- 平均 loss 从首局 -1.53 到末局 -0.31（有波动），样本太小，**不能据此声称棋力提升**；此处仅证明优化步骤可执行、损失可回传。
- 棋力统计目前只有"胜者分布 + 决策步数 + loss"，尚未做"历史最佳模型对抗的 Elo/胜率曲线"（代码具备历史最佳模型加载逻辑，但 6 局不足以评估）。此项列为后续工作。

## 4. 未决事项

- 未运行 CUDA 训练（本机为 CPU 版 torch；GPU 为 RTX 5070 Ti，需安装 CUDA 版 torch）。
- 未做 1000+ 局的大规模训练与"历史最佳对抗"棋力曲线。
- 训练记录写入临时目录；若需长期留存，应配置固定 `--record` 路径并纳入运维（不入库）。
