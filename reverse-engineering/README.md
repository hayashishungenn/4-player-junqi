# 棋弈无限逆向分析档案（单款：Just Xiangqi）

日期：2026-11-19
分析对象：用户本机 Steam 安装的《Just Xiangqi》（棋弈无限：中国象棋，AppID 2248180）。

## 0. 范围（2026-11-19 更新）

用户明确指示：**只分析象棋，《Just Go》未购买，不再安装**。

- 正式交付：`game-01/` 全部内容 + `comparison/` 中与象棋相关的结论与方案。
- `game-02/` 仅保留卸载后的残留背景材料，**不计入交付**，详见 `game-02/README.md`。
- 不再尝试通过 Steam 安装或第三方渠道获取《Just Go》。

## 1. 与任务书 APK 前提的偏差

本机没有棋弈无限 APK；《Just Xiangqi》是 **Steam Windows x64 + Unity 2020.3.15f2 + Mono** 构建。

| 任务书假设 | 实际 |
|---|---|
| APK/XAPK/APKS/AAB | 无。Steam 安装目录（2.0 GB） |
| AndroidManifest / 四大组件 / 权限 | 不适用 |
| DEX / JNI / ABI | 无；原生组件仅 `steam_api64.dll` |
| MuMu 运行 | 不适用；模拟器内未安装该游戏 |
| Split APK | 不适用 |

全盘检索 `*.apk/*.xapk/*.apks/*.aab` 只发现无关包；MuMu 内第三方包仅 `com.blade.port`、`com.xingin.xhs`。

## 2. 核心结论

1. **AI 三路混合**：
   - `NativeAI`：Alpha-Beta 浅层搜索 + 子力/位置表，depth 0 随机。
   - `SharpElephantEyes`：C# 移植的 ElephantEyes，迭代加深 + PVS + 静态搜索 + 约 100 万槽置换表 + 空着裁剪 + 杀手/历史排序 + 12,081 条内置开局库。
   - `Pikafish 2025-01-10`：外部 UCI 进程 + 45.5 MB NNUE，`go depth N`，只设 MultiPV。
2. **难度 13 档**（ELO 100–2800）：引擎类型 + 深度 + MultiPV 前 N 随机 + 开局库；不使用 Pikafish 的 Skill/Elo。
3. **本地 AI**：进入对局创建两个 `pikafish.exe`（对弈 + 分析），父进程为游戏，路径在安装目录。
4. **复盘/陪练**：独立分析进程，逐手 1/2.5/5 秒三档；标签 Best/Good/Book/Inaccuracy/Mistake/Blunder/Missed；动态阈值；提示有次数成本；残局/训练/生涯辅助构成闭环。
5. **棋谱**：内部 `.game`（Odin JSON）+ 导出 PGN（GB2312）；存档 ES3 AES（密钥硬编码）。

## 3. 动态验证

12 个场景中 11 个已实机验证：

- 启动/主菜单、新建对局、难度切换、设置、走子、AI 回应、悔棋、认输终局、复盘回放、胜率图、逐手评分统计、历史对局。
- 提示功能：入口、次数规则、灯泡按钮、代码路径均确认；**箭头显示未能在自动化点击下复现**，标为部分验证。

详见 `game-01/report/11-dynamic.md` 与 `game-01/runtime-observations/scenarios.md`。

## 4. 工具与限制

- REA：`rea@6.9.0`，Node 26.13.1；`rea doctor` 报 `healthy:false`，Ghidra/IDA/Hopper/JADX 均未配置，本会话无 REA MCP。
- `rea analyze` 对 .NET 程序集返回 `provider_unavailable`；.NET 反编译使用 `ilspycmd 11.2.0.10050`。
- 未把 ILSpy 结果冒充 REA Evidence；APK 专用能力在本对象上不可执行。
- 原始安装包未修改；关键哈希见 `game-01/inventory/hashes.txt`。

## 5. 目录

```text
reverse-engineering/
├── evidence/                    截图与工具输出
├── game-01/
│   ├── original/                原始包保护说明（原地只读）
│   ├── inventory/               环境、包清单、哈希、资源
│   ├── static-analysis/         类索引（反编译产物不入库）
│   ├── runtime-observations/    12 场景逐项记录
│   └── report/                  12 份专项报告
├── game-02/                     已排除（残留背景，不计入交付）
├── comparison/                  架构、AI、功能矩阵、陪练设计、四国军棋方案
└── DELIVERABLES.md              交付对照与验收
```

## 6. 一句话结论

《Just Xiangqi》用“传统搜索 + 开源引擎移植 + 现代 NNUE 外部进程”叠出 13 档难度，并把“随机候选采样”而不是“削弱引擎”作为拟人化手段；其复盘的逐手评分、动态阈值、提示成本与内外部棋谱分离，是四国军棋陪练系统最值得借鉴的部分。
