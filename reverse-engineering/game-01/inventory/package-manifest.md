# game-01 包清单（Just Xiangqi）

## 1. 身份

| 字段 | 值 | 证据 |
|---|---|---|
| 完整路径 | `D:\SteamLibrary\steamapps\common\Just Xiangqi` | 文件系统 |
| 文件格式 | Windows x64 Unity 游戏目录（Steam 安装） | `JustXiangqi.exe` + `JustXiangqi_Data` + `UnityPlayer.dll` + `MonoBleedingEdge` |
| 总大小 | 2,129,099,409 字节（`du -sh` 2.0G；文件 276 个，目录 33 个） | `find`/`du`、Steam ACF `SizeOnDisk` |
| Steam AppID | 2248180 | `appmanifest_2248180.acf` |
| Steam buildid | 17661943 | 同上 |
| 产品名 | Just Xiangqi（Steam 名），中文商店名“棋弈无限：中国象棋” | ACF `name`、桌面快捷方式 |
| 开发者标识 | Studio Amateur | `JustXiangqi_Data/app.info` |
| 应用版本 | 未在包内声明（`app.info` 仅两行：Studio Amateur / JustXiangqi） | `app.info` |
| 签名 | 不适用（Steam 分发，无 APK 签名）；存在 `Plugins/x86_64/steam_api64.dll` | 目录清单 |
| 目标 Android SDK | 不适用 | — |
| CPU ABI | 不适用；原生组件仅 Windows x86_64 | `Plugins/x86_64` |
| Split APK | 不适用 | — |
| 额外资源包 | 无独立资源包；资源在 `JustXiangqi_Data` 与 `StreamingAssets` | 目录清单 |

## 2. SHA-256（关键文件）

完整清单见 `inventory/hashes.txt`。

| 文件 | SHA-256 |
|---|---|
| `JustXiangqi.exe` | `fdff63249900060815bb3832133007d880f2116f2ba00ea725961ad981e69ca8` |
| `UnityPlayer.dll` | `a352ed5b3c5ab93956cb5a663a6415e665e7341340211fd186b2f5890553c954` |
| `Managed/Assembly-CSharp.dll` | `a0edd987a34910df8ff0589e39848a92dc61a133cedc5eaa7acf938321e5825e` |
| `Managed/Assembly-CSharp-firstpass.dll` | `dd04022876e252992e218d651e24eeb4e9c285d4dc22d722fd5cec155cfd7c87` |
| `StreamingAssets/AI/PikaFish/pikafish.exe` | `8fedd65c00d15b20265148cd102856ce20d4cdb9e9fdef93553ca74433845961` |
| `StreamingAssets/AI/PikaFish/pikafish.nnue` | `53f62e990716187e59510898749cf59bcb680c4da0b80c23005cec3eda321cc6` |

## 3. 包结构

```text
Just Xiangqi/
├── JustXiangqi.exe                 653,824 B   Mono 启动器
├── UnityPlayer.dll              28,082,264 B   Unity 2020.3.15f2
├── UnityCrashHandler64.exe
├── WinPixEventRuntime.dll
├── MonoBleedingEdge/                           Mono 运行时
└── JustXiangqi_Data/
    ├── app.info                   26 B
    ├── boot.config                120 B
    ├── globalgamemanagers / level0..8 / resources.assets*
    ├── Managed/                   124 个 .NET 程序集
    ├── Plugins/x86_64/            steam_api64.dll
    ├── Resources/                 Unity 资源（含 Book/Openings、Book/Endgames）
    └── StreamingAssets/
        ├── AI/
        │   ├── PikaFish/          8 个 pikafish 变体 + pikafish.nnue（45.5 MB）
        │   └── PikaFish_Deprecated/
        └── Classic/               24 个 ClassicMatch_*.game
```

## 4. 技术框架判定 [已验证]

- Unity 2020.3.15f2，Mono 后端：`MonoBleedingEdge`、`Managed/*.dll`、`Player.log` 首行。
- 无 `libil2cpp.so`、无 `global-metadata.dat`，排除 IL2CPP。
- 无 DEX、无 `AndroidManifest.xml`，排除 Android 原生/Java 路线。
- 第三方库（程序集名）：Photon3Unity3D / PhotonRealtime / PhotonChat / PhotonUnityNetworking（联机）、Heathen.Steamworks（Steam）、Sirenix.OdinInspector/Serialization（序列化与编辑器）、I2.Loc（本地化）、Easy Save 3（ES3，加密存档）、GraphAndChart/E2C（复盘图表）、DOTween/LeanTween（动画）。

## 5. 与 APK 前置项的对照

任务书要求的 manifest、四大组件、权限、DEX 方法数、JNI、ABI 分布、Split APK 检查在本对象上均不适用；对应替代证据为：Unity 场景列表（`level0..8`）、124 个托管程序集、`StreamingAssets` 资源、`Player.log` 运行日志。原始安装目录未被修改（只读打开与哈希计算）。
