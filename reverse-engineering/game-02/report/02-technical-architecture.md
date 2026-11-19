# 报告 02：技术架构（game-02）

## 1. 分层（由日志与残留数据恢复）

```text
表现层：Unity 2021.3.29f1（UGUI，3D 棋盘/棋子，场景与材质系统）
业务层：C#（Assembly-CSharp，二进制缺失，类结构未知）
  ├─ GameRecord（存档/棋谱模型，$type 可见）
  ├─ Point（棋盘坐标，$type 可见）
  └─ GTP 控制器（发起 genmove / kata-analyze / play）
引擎层：KataGo v1.10.0（外部进程）
  ├─ GTP 协议
  ├─ Eigen CPU 后端，4 搜索线程
  └─ NN：kata1-b40c256（40 block × 256 channel）
平台层：Steamworks（AppID 1862520）、Azure Blob（赛事 SGF 下载）
```

## 2. 引擎启动方式

`Player.log:1201`：

```text
Running ...\AI\Katago_CPU\katago.exe with arguments
  gtp
  -model "...\AI\Katago\networks\Analysis\kata1-b40c256-s10032125184-d2445637108.bin.gz"
  -config "...\AI\Katago_CPU\default_gtp.cfg"
```

- 使用 **GTP**（Go Text Protocol），不是 UCI。
- 模型固定指向 `networks/Analysis/`，说明“分析网络”与“对弈网络”可能共用同一文件；是否存在独立对弈网络未验证。 [未知]
- 使用 CPU Eigen 后端，未启用 GPU/CUDA/TensorRT（`Eigen (CPU) backend thread 0..3`）。 [已验证]

## 3. 网络行为

`Player.log` 显示大量 Azure Blob 请求：

```text
Authorized request url:https://justgoprod.blob.core.windows.net/recent-pro-matches?comp=list&restype=container
.../recent-pro-matches/20260114-Ding_Hao-Chen_Xian.sgf
```

- 用途：下载职业棋赛 SGF，供“职业棋谱”栏目浏览/复盘。
- 鉴权：请求头含 `SharedKey` 授权（日志中可见签名串）。
- 与 AI 无关：AI 走子不经过网络。 [已验证：GTP 本地进程 + 日志中无远程走子接口]

## 4. 数据与存档

| 数据 | 路径 | 格式 |
|---|---|---|
| 设置/进度 | `SaveFileOfficial_beta.es3` | ES3 加密（1456 B） |
| 生涯 | `Careers/career.sav`、`CareerSaves/*.sav` | Odin JSON |
| 最近对局 | `RecentGames/match_*.sav` | Odin JSON（`GameRecord`） |
| 棋谱 | `RecentSGFs/*.sgf` | SGF FF[4] |
| 职业棋谱 | `RecentProMatches/*.sgf` + `*.sav` | SGF + Odin JSON |
| 引擎日志 | `gtp_logs/*.log` | 纯文本 |

## 5. 与 game-01 的架构相似点（初步）

- 同一发行方、同一 Unity/Mono 范式、同一 Odin 序列化（`$id/$type/$rlength/$rcontent`）。
- 同一用户数据根目录 `%LocalLow%\Studio Amateur\`。
- 同一“外部引擎进程 + GTP/UCI 协议”思路。

差异：game-02 只有 KataGo 一条引擎路径；game-01 有三条（自研 C#、ElephantEyes、Pikafish）。详细对照见 `comparison/architecture.md`。

## 6. 未知

- C# 业务层的类结构、难度实现、UI 控制器：二进制缺失，无法反编译。
- `default_gtp.cfg` 的具体参数（线程、访问上限、规则、宽搜索等）：文件缺失。
- 是否内置对弈专用网络：未知。
