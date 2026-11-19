# Just Xiangqi 架构逆向

## 1. 身份与构建

| 项 | 值 |
|---|---|
| Steam AppID / BuildID | 2248180 / 17661943 |
| 安装路径 | `D:\SteamLibrary\steamapps\common\Just Xiangqi` |
| 引擎 | Unity 2020.3.15f2 |
| 脚本后端 | Mono（非 IL2CPP） |
| 主程序 | `JustXiangqi.exe`（653 KB） |
| 主逻辑 | `JustXiangqi_Data/Managed/Assembly-CSharp.dll` |
| 托管程序集 | 124 个 |
| AI 资源 | `StreamingAssets/AI/PikaFish/`（8 个变体 + 45.5 MB NNUE） |
| 名局 | `StreamingAssets/Classic/*.game`（24） |
| 存档 | `%LocalLow%\Studio Amateur\JustXiangqi` |

证据：`Player.log` 首行、目录清单、哈希见 `reverse-engineering/game-01/inventory/`。

## 2. 分层

```text
Unity 表现层（UGUI、DOTween、Michsky UI、GraphAndChart、I2.Loc）
C# 业务层（Assembly-CSharp）
  ├─ GameManager：对局主控、AI 调度、提示、复盘、导出
  ├─ ChessBoard / ChessPiece / 棋子规则类
  ├─ GameRecord / MoveAnalysis / CareerMode*
  └─ AIConfiguration / NativeAI / ElephantEyesAI / ProcessManager
引擎层
  ├─ SharpElephantEyes：C# 移植的 ElephantEyes（搜索 + 开局库）
  └─ Pikafish 2025-01-10：外部 UCI 进程 + NNUE
平台层
  ├─ Steamworks（Heathen.Steamworks / steam_api64.dll）
  ├─ Photon Realtime/Chat（在线对局）
  └─ ES3（AES 加密存档）、Odin Serializer（棋谱 JSON）
```

## 3. 运行时进程模型

- 进入人机/生涯/训练/残局模式时 `InitializeGameAI()` 创建：
  - `NativeAI`（Easy/Medium）
  - `ElephantEyesAI`
  - 两个 `ProcessManager`：对弈引擎 + 分析引擎，分别启动 `pikafish.exe`。
- 动态验证：`JustXiangqi.exe` 为父进程，两个 `pikafish.exe` 子进程，命令行指向安装目录。
- 对弈决策在线程池执行，主线程只做动画与状态机。

## 4. 数据流

```text
用户操作 → ChessBoard 更新（Moves / PreviousFens）
        → GameManager 判定终局/禁手
        → MakeNextMoveByAI → 引擎 → 4 字符着法
        → 动画 → 下一回合
        → GameRecord 写入（MoveAnalysis / Report）
```

## 5. 存档与棋谱

| 数据 | 格式 |
|---|---|
| 设置/进度 | ES3 + AES（密钥硬编码，报告不复述） |
| 棋谱 | `.game` Odin JSON（UTF-8 BOM、CRLF、裸 GUID） |
| 导出 | PGN，GB2312 编码 |
| 生涯/历史 | Odin JSON（`CareerSaves/`、`MyGameHistory/`） |

## 6. 可迁移 vs 象棋专属

| 设计 | 可迁移到四国军棋 | 说明 |
|---|---|---|
| 引擎进程化、文本协议 | 是 | 隔离崩溃、可替换引擎、分析独立 |
| 内外部格式分离 | 是 | 内部存分析，外部导出标准格式 |
| Odin/ES3 存档模式 | 部分 | 需换成自有 schema，避免依赖商业库 |
| Unity 场景/UI 组织 | 思路可借鉴 | 不复制资源与代码 |
| 象棋规则/棋盘/走法 | 否 | 四国军棋须自有规则引擎 |
| Pikafish/NNUE | 否 | 棋种不同，仅借鉴“强引擎做分析后端” |

## 7. 证据索引

- 包结构：`reverse-engineering/game-01/report/01-package-structure.md`
- 架构与类索引：`02-technical-architecture.md`、`03-key-classes.md`、`static-analysis/full-class-index.md`
- REA：`evidence/game-01/rea-evidence-summary.md`
