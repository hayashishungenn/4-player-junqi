# 报告 02：技术架构（game-01）

## 1. 分层

```text
表现层（Unity 2020.3 / UGUI / DOTween / Michsky UI / GraphAndChart）
  ├─ TitleManager / HomeManager / GameManager / TutorialManager / CareerModeManager
业务层（C#，Assembly-CSharp）
  ├─ ChessBoard / ChessPiece / 规则（将军、长将、长捉、重复局面）
  ├─ GameRecord / MoveAnalysis / CareerMode*（棋谱、复盘、生涯、训练）
  └─ AIConfiguration / AIOptions / NativeAI / ElephantEyesAI / ProcessManager
引擎层
  ├─ SharpElephantEyes（C# 移植的 ElephantEyes，含内置开局库与置换表）
  └─ Pikafish 2025-01-10（外部 UCI 进程 + NNUE）
平台层
  ├─ Steamworks（Heathen.Steamworks / steam_api64.dll）
  ├─ Photon Realtime / Chat（联机对局与聊天）
  └─ Easy Save 3（AES 加密存档）、Odin Serializer（棋谱 JSON）
```

## 2. 关键外部依赖

| 程序集 | 作用 | 证据 |
|---|---|---|
| `Photon3Unity3D` / `PhotonRealtime` / `PhotonChat` / `PhotonUnityNetworking` | 在线对战、房间、聊天 | `Managed/` 目录 |
| `Heathen.Steamworks` | Steam 初始化、成就、云存档 | `Managed/`；`Player.log` 中 `Initalizing Steam Client API` |
| `Sirenix.Serialization` / `OdinInspector` | 棋谱与生涯数据的 Odin JSON 序列化 | `.game` 文件 `$type` 标记 |
| `ES3`（Easy Save 3） | 设置/进度加密存档 | `GlobalVariable.cs:78` |
| `I2.Loc` | 多语言（简中/繁中/英） | `Utils.GetAINameByLevel` 走 `LocalizationManager` |
| `GraphAndChart` / `E2C` | 复盘胜率/评分曲线 | `GameManager.cs:1496-1537` |

## 3. 主要游戏模式

`CCEnum.GameMode`（`CCEnum.cs:10`）：`Local_SinglePlayer`、`Local_MultiPlayer`、`Local_Review`、`Local_CareerMode_SinglePlayer`、`Local_CareerMode_AIBattle`、`Local_CareerMode_Training`、`Online_MultiPlayer`、`Title_Home`、`CareerMode_Home`、`Tutorial`、`Credits`、`Local_Endgame`、`Local_FreeMode`。

AI 只在以下模式初始化：`Local_SinglePlayer`、`Local_CareerMode_SinglePlayer`、`Local_CareerMode_AIBattle`、`Local_CareerMode_Training`、`Local_Endgame`（`GameManager.cs:1159`）。联机模式不使用本地 AI 决策。 [已验证]

## 4. 存档与数据

| 数据 | 位置 | 格式 |
|---|---|---|
| 设置/进度 | `%LocalLow%\Studio Amateur\JustXiangqi\SaveFileOfficial.es3` | ES3 + AES（密钥硬编码于代码，报告不复述） |
| 生涯存档 | `CareerSaves/*.sav`、`Careers/` | Odin JSON |
| 对局历史 | `MyGameHistory/` | Odin JSON |
| 内置名局 | `StreamingAssets/Classic/*.game` | Odin JSON（UTF-8 BOM、CRLF、裸 GUID） |
| 导出棋谱 | 用户选择路径 | PGN 文本，GB2312 编码（`Utils.cs:1334`、`GameManager.cs:4333`） |

## 5. 网络行为

- 在线对局走 Photon；Steam 提供身份与成就。
- `Player.log` 记录 `Failed to load the Steam App List: ... 404`，属非致命错误，游戏继续运行。
- 未观察到 AI 走子相关的网络请求；AI 为本地进程。 [已验证：两个 `pikafish.exe` 子进程由游戏进程直接创建]

## 6. 运行架构要点

- 进入对局场景时 `InitializeGameAI()` 创建 3 个本地 AI 对象 + 2 个 Pikafish 进程（对局 AI、分析 AI）。
- AI 走子在线程池中执行（`Task.Run`），主线程只负责动画与状态机（`PlayAIMoveAnimation`）。
- 分析 AI 与对局 AI 分离，保证复盘/提示不会干扰对局引擎状态（两个独立进程）。
