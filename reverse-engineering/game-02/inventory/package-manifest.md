# game-02 包清单（Just Go）

## 1. 身份

| 字段 | 值 | 证据 |
|---|---|---|
| 名称 | Just Go（棋弈无限：围棋） | Steam AppID 与日志 |
| Steam AppID | 1862520 | `Player.log`：`Steam API has been initialized with App ID: 1862520` |
| 安装路径（历史） | `D:\SteamLibrary\steamapps\common\Just Go` | `Player.log:1-3` |
| 当前状态 | **主体已卸载**：目录仅剩 `gtp_logs/`（4 个日志，432 KB） | 文件系统 |
| 运行残留 | `%LocalLow%\Studio Amateur\JustGo`（约 745 KB + 59 个赛事文件） | 文件系统 |
| 格式 | Windows x64 Unity 构建（非 APK） | 日志路径 `JustGo_Data/Managed`、`MonoBleedingEdge` |
| Unity | 2021.3.29f1 (204d6dc9ae1c) | `Player.log:3` |
| 脚本后端 | Mono | `Mono path[0] = .../JustGo_Data/Managed` |
| 签名 | 不适用（Steam 分发） | — |
| 目标 Android SDK / ABI / Split APK | 不适用 | — |
| 额外资源包 | 运行期下载赛事 SGF（Azure Blob），非安装包 | `Player.log` 中的 `justgoprod.blob.core.windows.net` |

## 2. 可计算哈希

| 文件 | SHA-256 |
|---|---|
| `gtp_logs/20260116-102532-923AB239.log` | `c78a60e160edce40416871d6b4bd98228ded03fd07be55be95356e165c8b3c69` |
| `gtp_logs/20260116-102532-DD5B56EE.log` | `e5db543841ac0f38d3456a43b38f00aa89aa48c05324067fac9a723c01470461` |

（其余日志、SGF、存档哈希见 `hashes.txt` 的 game-01 部分；本机未对全部小文件逐一计算。）

## 3. 目录结构（残留）

```text
D:\SteamLibrary\steamapps\common\Just Go\
└── gtp_logs\
    ├── 20260116-102356-7B8BC9CC.log     5.6 KB
    ├── 20260116-102459-11CC525B.log     4.6 KB
    ├── 20260116-102532-923AB239.log   141 KB
    └── 20260116-102532-DD5B56EE.log   278 KB

%LocalLow%\Studio Amateur\JustGo\
├── Player.log                          718 KB / 7,096 行
├── BackupSaves\BackupSave_*.es3
├── Careers\career.sav
├── CareerSaves\career_*.sav
├── RecentGames\match_1768530733.sav    21 手以上，实际 134 手
├── RecentProMatches\                   59 个文件（SGF + sav）
├── RecentSGFs\sgf_1768530733.sgf
└── SaveFileOfficial_beta.es3
```

## 4. 技术判定

- Unity 2021.3.29f1 + Mono：`Player.log` 首三行。
- AI 为外部 KataGo 进程：`Player.log:1201` 完整启动命令行。
- 无 APK、无 DEX、无 JNI；不在 MuMu 内安装。
- 原始残留文件未被修改；仅读取日志与棋谱。

## 5. 缺失说明

由于主体已卸载，无法获得 `Assembly-CSharp.dll`、`StreamingAssets/AI/Katago*`、`default_gtp.cfg` 与 KataGo 可执行文件本体。所有涉及内部类结构、难度配置、界面实现的结论均标注为未知或推测，详见各报告。
