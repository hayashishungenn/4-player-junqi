# 报告 12：已证实与未证实事项（game-01）

## 1. 已验证

| 结论 | 证据 |
|---|---|
| 对象为 Unity 2020.3.15f2 + Mono 的 Windows 构建，不是 APK | `Player.log:3`；`MonoBleedingEdge`；无 DEX/IL2CPP |
| 主逻辑在 `Assembly-CSharp.dll`，744 个类 | ILSpy 反编译，690 个文件 |
| AI 有三条本地路径：NativeAI / ElephantEyes / Pikafish 子进程 | `GameManager.cs:1157-1172`、`:3616-3684` |
| 对局时创建两个 Pikafish 进程（对弈 + 分析） | `tasklist`、`Win32_Process` 命令行与父进程 |
| Pikafish 版本 2025-01-10，NNUE 45.5 MB | 直接 UCI 握手输出 |
| 游戏只设置 `MultiPV` 与 `UCI_ShowWDL`，不使用 Skill/Elo 限制 | `rg "setoption"` 全量结果 |
| 难度为 13 档，ELO 100–2800 | `Constants.cs:1913`；UI 截图 |
| 难度随机化来自 MultiPV 前 N 条的有偏采样，100 厘兵阈值回退 | `GameManager.cs:3658-3672` |
| 前 3 步可用开局库（档 0/1） | `AIConfiguration.PredefinedAI`；`Constants` 档 0/1 |
| ElephantEyes 使用迭代加深 + Alpha-Beta/PVS + 静态搜索 + 置换表 + 空着裁剪 + 杀手/历史排序 | `Search.cs`、`MoveSort.cs`、`Hash.cs` |
| 置换表约 100 万槽，2 层，双 32 位 Zobrist 锁 | `Hash.cs:56-66` |
| 内置开局库 12,081 条 | `Book.cs:20` |
| 复盘逐手分析每步 1s/2.5s/5s 三档 | `Constants.cs:1861-1876` |
| 评分标签阈值（Book/Best/Good/Inaccuracy/Mistake/Blunder/Missed） | `GameManager.cs:2748-2905` |
| 棋谱为 Odin JSON，着法 4 字符坐标，支持多语言记谱 | `GameRecord.cs`；`ClassicMatch_1.game` |
| PGN 导出使用 GB2312 与中文记谱 | `Utils.cs:1334`；`GameManager.cs:4333` |
| 撤销 1/2 步规则与挑战模式禁用 | `GameManager.cs:2507-2517`、`:2497` |
| 存档 AES 加密且密钥硬编码 | `GlobalVariable.cs:78`（密钥值不在本报告复述） |

## 2. 有证据支持但未完整验证

| 结论 | 缺口 |
|---|---|
| Pikafish 使用默认 1 线程 / 16 MB Hash | 代码未设置，但未读取引擎运行时内部状态 |
| `Book/Openings` 文本库的规模与覆盖率 | 只确认加载逻辑与字段格式，未导出统计 |
| `MoveAnalysis` 与 `Report` 在正常对局中每步都会写入 | 代码路径存在，未实机打完整局验证 |
| 名局 `.game` 可在“探析”中直接回放 | 入口代码存在，未实机操作 |
| 生涯模式 16 档配置逐一参数 | 只确认键范围 1–16，未展开全部 |
| 在线模式与本地 AI 完全隔离 | 未见 AI 请求，但未抓包 |

## 3. 推测

| 结论 | 依据 |
|---|---|
| `PikaFish_Deprecated` 仅为历史兼容保留 | 无代码引用；目录命名 |
| 场景 `level0..8` 对应标题/生涯/对局/复盘等 | 场景数量与 UI 流程吻合，未逐一加载验证 |
| 位置表权重经过人工调参 | 数值形态典型，但无版本记录 |

## 4. 未知

| 项 | 原因 |
|---|---|
| Pikafish NNUE 的网络结构、特征、训练数据 | 仅有二进制网络文件，无元数据 |
| SharpElephantEyes 预计算评估表的完整权重 | 表由 `Pregen` 生成，未逐项展开 |
| 难度与 ELO 的标定方法 | 无文档 |
| 生涯剧情与 AI 等级的对应设计意图 | 无文档 |
| 服务器端是否存在其他服务 | 未抓包；仅见 Steam/Photon/Azure 相关库 |

## 5. 与任务书要求的差距

- APK 包结构、Manifest、四大组件、权限、DEX、JNI、ABI、Split APK：**对象不存在，无法验证**，不是分析遗漏。
- MuMu 内运行：模拟器内未安装该游戏，且对象为 Windows 构建。
- 12 个动态场景中 5/7/8/9/10/11/12 未实机触发，仅完成代码级还原；未用推测冒充实测。

## 6. 合规

- 未复制商业源代码、素材、商标或私有接口到四国军棋工程。
- 本档案仅记录机制与设计思路，代码引用为分析用途。
- 原始安装包未被修改。
