# 报告 01：包结构分析（game-02 Just Go）

## 1. 结论

《Just Go》是与《Just Xiangqi》同发行方（Studio Amateur）的 Unity 2021.3.29f1 + Mono Windows 构建。**安装主体已从本机卸载**，仅剩 `gtp_logs` 与用户数据目录。因此无法执行与 game-01 同等粒度的程序集反编译；包结构结论主要来自运行日志中记录的绝对路径。 [已验证：日志；未知：二进制清单]

## 2. 从日志恢复的构建结构

`Player.log` 记录的路径可还原出：

```text
Just Go/
├── JustGo.exe                              （推断）
├── UnityPlayer.dll
├── MonoBleedingEdge/
└── JustGo_Data/
    ├── Managed/                            托管程序集（Mono）
    ├── StreamingAssets/
    │   └── AI/
    │       ├── Katago/
    │       │   └── networks/Analysis/kata1-b40c256-s10032125184-d2445637108.bin.gz
    │       └── Katago_CPU/
    │           ├── katago.exe
    │           └── default_gtp.cfg
    └── ...
```

证据：

```text
Mono path[0] = 'D:/SteamLibrary/steamapps/common/Just Go/JustGo_Data/Managed'
Initialize engine version: 2021.3.29f1 (204d6dc9ae1c)
Running ...\StreamingAssets\AI\Katago_CPU\katago.exe with arguments gtp
  -model "...\AI\Katago\networks\Analysis\kata1-b40c256-s10032125184-d2445637108.bin.gz"
  -config "...\AI\Katago_CPU\default_gtp.cfg"
```

（`Player.log:1-3`、`:1201`）

## 3. 与 APK 检查项的对照

| 检查项 | 结果 |
|---|---|
| AndroidManifest / 四大组件 / 权限 | 不适用（非 Android） |
| 类与方法数量 | 无法统计（`Assembly-CSharp.dll` 不存在） [未知] |
| 资源 / 图片 / 音频 | 无法枚举（主体已删除） [未知] |
| DEX | 无 |
| Native Library | `katago.exe`（独立进程）、`UnityPlayer.dll`；均非 JNI |
| ABI | Windows x86_64 |
| Split APK | 不适用 |

## 4. 可确认的包内组件

| 组件 | 证据 | 说明 |
|---|---|---|
| KataGo v1.10.0 | GTP 日志首行 | 围棋引擎 |
| `kata1-b40c256-s10032125184-d2445637108.bin.gz` | 启动命令行、GTP 日志 | 40 层 256 通道网络，训练步数 10,032,125,184 |
| `default_gtp.cfg` | 启动命令行、GTP 日志 | GTP 配置（文件缺失，内容未知） |
| Eigen CPU 后端 | GTP 日志 `Eigen (CPU) backend thread 0..3` | 未使用 GPU |
| 4 个搜索线程 | `Using 4 CPU thread(s) for search` | 固定 4 线程 |
| SGF 支持 | `RecentSGFs/*.sgf`、`GameSGFFilePath` | 标准 SGF FF[4] |

## 5. 完整性

原始残留未被修改；未尝试恢复已卸载的二进制；未使用安装包下载源。若需完整静态分析，需要重新安装该游戏或提供安装目录副本。
