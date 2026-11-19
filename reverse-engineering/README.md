# 棋弈无限双游戏逆向分析档案

日期：2026-11-19
分析对象：用户本机 Steam 安装的《Just Xiangqi》（棋弈无限：中国象棋）与《Just Go》（棋弈无限：围棋）。

## 0. 与任务书前提的偏差（必须先读）

任务书按 Android APK 设计，但本机实际情况是：

| 项目 | 任务书假设 | 实际发现 |
|---|---|---|
| 包格式 | APK / XAPK / APKS / AAB | 无。两款均为 Steam 发行的 Windows x64 游戏 |
| 技术栈 | Java/Kotlin、DEX、JNI、ABI | Unity + Mono（C# 程序集），无 DEX、无 JNI |
| 运行环境 | MuMu 模拟器 | 原生 Windows 运行；MuMu 内无这两款 App |
| Split APK | 需要识别 | 不适用 |
| Android SDK/ABI | 需要记录 | 不适用（仅有 x86_64 的 `steam_api64.dll`） |

全盘检索结果（`C:` 浅层 + `C:\Users` 6 层 + `D:` 6 层，`*.apk/*.xapk/*.apks/*.aab`）只发现无关包（BladeUnity、小红书、Telegram 客户端等），**不存在棋弈无限 APK**。MuMu 实例（Android 15 / SDK 35）内第三方包只有 `com.blade.port` 与 `com.xingin.xhs`。

因此本档案按“Windows Unity 构建”执行同等粒度的静态与动态分析，并在所有报告中保留“APK 前置项不适用”的明确说明，不以猜测填补。

## 1. 两款游戏的实际身份

| 项 | game-01 | game-02 |
|---|---|---|
| 名称 | Just Xiangqi（棋弈无限：中国象棋） | Just Go（棋弈无限：围棋） |
| 发行 | Studio Amateur | Studio Amateur |
| Steam AppID | 2248180 | 1862520 |
| 安装路径 | `D:\SteamLibrary\steamapps\common\Just Xiangqi` | `D:\SteamLibrary\steamapps\common\Just Go` |
| 安装状态 | 完整安装，2,129,099,409 字节，buildid 17661943 | **主体已卸载**，仅剩 `gtp_logs`（432 KB）；运行残留数据在 `%LocalLow%\Studio Amateur\JustGo` |
| Unity | 2020.3.15f2 (6cf78cb77498) | 2021.3.29f1 (204d6dc9ae1c) |
| 脚本后端 | Mono | Mono |
| 棋 AI | NativeAI + SharpElephantEyes(C#) + Pikafish 2025-01-10(UCI+NNUE) | KataGo v1.10.0（GTP + Eigen CPU） |
| 对局记录 | Odin JSON `.game` + ES3 加密存档 + PGN 导出 | Odin JSON `.sav` + SGF 导入导出 |
| 在线 | Photon（Realtime/Chat）+ Steamworks | Steamworks + Azure Blob 赛事 SGF 下载 |

## 2. 证据分级

所有结论标注四档：

- **[已验证]**：有可复现的静态代码或运行证据，且已排除同名/死代码误判。
- **[有证据支持]**：有直接证据，但未覆盖全部调用路径或边界条件。
- **[推测]**：由相邻证据推断，尚无直接实现证明。
- **[未知]**：无证据；不编造。

## 3. 工具与限制

- REA：`rea@6.9.0`（Node 26.13.1，满足 ≥26）。`rea doctor` 报 `healthy:false`；`ghidra/hopper/ida/kuna` 均未配置，JADX 未配置（`REA_JADX_MCP_JAR` 为空）。
- 本会话未挂载 REA MCP 工具，REA 仅以 CLI 使用；`rea analyze` 对 .NET 程序集返回 `provider_unavailable`。
- 因此 Android 专用能力（APK 解码、JADX、MuMu ADB 观察）在本对象上不可执行，已在各报告中如实记录。
- .NET 反编译使用全局工具 `ilspycmd 11.2.0.10050`（完整 JDK 21 仅用于 ADB/JADX 前置检查，实际未参与 .NET 反编译）。
- 原始安装包未被修改；运行观察只启动官方可执行文件，未改包、未卸载、未清数据。

## 4. 目录

```text
reverse-engineering/
├── evidence/                    截图、日志摘录、UCI/GTP 实测输出
├── game-01/
│   ├── inventory/               环境核查、包清单、哈希、资源清单
│   ├── static-analysis/         反编译产物（已在 .gitignore 排除）、类索引
│   └── report/                  12 份专项报告
├── game-02/
│   ├── inventory/               残留证据清单（二进制缺失）
│   └── report/                  12 份专项报告（含未知标注）
└── comparison/                  架构、AI、功能矩阵、陪练设计、四国军棋方案
```

## 5. 一句话结论

两款产品共享同一套 Unity/Mono 工程范式、Odin 序列化存档、Studio Amateur 发行体系；但 AI 路线完全不同：中国象棋是“自研浅层搜索 + ElephantEyes 开局库 + Pikafish/NNUE 外部进程”的三级混合，围棋是“KataGo/NNUE 单引擎 + GTP 包装”。难度并非通过削弱引擎棋力实现，而是通过搜索深度、候选随机性、开局库与局面分析采样量组合实现——这一点对四国军棋 AI 陪练最具借鉴价值。
