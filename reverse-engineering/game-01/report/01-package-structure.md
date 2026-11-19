# 报告 01：包结构分析（game-01 Just Xiangqi）

## 1. 结论

对象是 **Unity 2020.3.15f2 + Mono** 的 Windows x64 商业游戏，不是 Android APK。包内没有 `AndroidManifest.xml`、DEX、JNI、Split APK；AI 由本地可执行文件与本地 C# 代码组成，棋谱与资源以 Unity 资源与 `StreamingAssets` 分发。 [已验证]

## 2. 结构明细

- 文件 276 个、目录 33 个，总 2,129,099,409 字节。
- 顶层：`JustXiangqi.exe`（653 KB Mono 启动器）、`UnityPlayer.dll`（28 MB）、`MonoBleedingEdge/`、`JustXiangqi_Data/`。
- `JustXiangqi_Data/Managed/`：124 个托管程序集，主逻辑在 `Assembly-CSharp.dll`（反编译 690 文件 / 744 类）。
- `JustXiangqi_Data/StreamingAssets/AI/PikaFish/`：8 个 Pikafish 变体 + 45.5 MB `pikafish.nnue`。
- `JustXiangqi_Data/StreamingAssets/Classic/`：24 个 `ClassicMatch_*.game`。
- `JustXiangqi_Data/Plugins/x86_64/steam_api64.dll`：唯一原生插件。
- `Resources/`：Unity 资源，含 `Book/Openings`、`Book/Endgames` 文本资源。

## 3. Unity 场景

`level0` … `level8` 共 9 个场景文件（`level0` 566 KB 至 `level3` 3.2 MB），对应标题、生涯、对局、复盘等界面。场景名未在包内明文保存，具体映射未验证 [未知]。

## 4. 任务书 APK 检查项对照

| 检查项 | 结果 |
|---|---|
| AndroidManifest.xml | 不存在（非 Android 包） |
| Activity / Service / Receiver / Provider | 不适用 |
| 权限声明 | 不适用；Steam 平台能力由 `steam_api64.dll` 提供 |
| 类/方法数量 | 744 个类声明（ILSpy 统计）；方法级数量未逐一统计 |
| 资源文件 | `resources.assets`（23 MB）+ `resources.assets.resS`（86 MB）+ `resources.resource`（222 MB） |
| 图片/音频 | 在 Unity 资源包内，未逐项导出 |
| 配置文件 | `app.info`、`boot.config`、`globalgamemanagers` |
| DEX | 无 |
| Native Library | 仅 `steam_api64.dll`；另有 8 个 Pikafish exe（独立进程，非 JNI 库） |
| ABI 分布 | 仅 Windows x86_64 |
| JNI 声明 | 无 |
| 多 Split APK | 不适用 |
| 额外资源包 | 无独立包；`StreamingAssets` 为外置资源目录 |

## 5. 技术判定依据

- `Player.log:3`：`Initialize engine version: 2020.3.15f2 (6cf78cb77498)`。
- `Player.log:1`：`Mono path[0] = .../JustXiangqi_Data/Managed`。
- 目录中存在 `MonoBleedingEdge`，不存在 `GameAssembly.dll`/`global-metadata.dat`，排除 IL2CPP。
- 存在 `Assembly-CSharp.dll`，可用 ILSpy 完整反编译为 C# 工程。

## 6. 原始文件完整性

分析过程仅读取与哈希，未修改、未覆盖、未卸载。关键哈希见 `inventory/hashes.txt`。

## 7. REA 发布面审计

`rea audit-release-exposure` 对三个 PE 产物均成功返回 Evidence（15 项检查）：

| 产物 | evidence_id |
|---|---|
| `JustXiangqi.exe` | `ev_2457f011057401d8735469cdc6a68c764a89cb82bc78028363240e035e728d12` |
| `UnityPlayer.dll` | `ev_b5b0218263106822c8d112f75ef9301933fc7f8d20afeafdd61186518cc126eb` |
| `Assembly-CSharp.dll` | `ev_9e0391860752e94f30c3b176d1442b86d901044f54f29641116ff777968a4132` |

结果要点：

- `native.pdb_path: exposed`：三个产物均残留 CodeView PDB 路径（severity low）。
- `JustXiangqi.exe` 路径指向 Unity 官方构建机 `buildslave\unity\...\WindowsPlayer_Master_mono_x64.pdb`。
- `Assembly-CSharp.dll` 路径为 `C:\Unity\ChineseChess_Windows\Temp\Assembly-CSharp.pdb`，**泄漏原始工程名 `ChineseChess_Windows`**。
- `native.debug_companions: not_observed`：未随包附带 PDB 文件。
- `android.manifest: not_assessed`：非 APK，符合预期。

完整输出见 `evidence/game-01/rea-audit-*.txt`。这是本次能够实际执行的 REA 证据链；REA 的原生反编译提供者（Ghidra/IDA）仍未配置。
