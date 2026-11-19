# game-01 环境与工具核查

核查日期：2026-11-19。所有命令均为只读检查。

## 1. 工具链

| 检查项 | 结果 | 证据 |
|---|---|---|
| Node.js | v26.13.1 | `node -v`；REA 要求 26+，满足 |
| npm | 11.20.0 | `npm -v` |
| REA | `rea@6.9.0`，路径 `C:\Users\Hayas\AppData\Roaming\npm\rea` | `rea --version`、`which rea` |
| REA doctor | `healthy: false`、`environment_healthy: false` | `rea doctor` |
| Ghidra | 未配置（`GHIDRA_INSTALL_DIR` 未设置，要求 12.x ≥12.1） | `rea doctor` |
| Hopper | 缺失（Windows 不适用） | `rea doctor` |
| IDA | 未注册 MCP | `rea doctor` |
| Kuna | 未配置 | `rea doctor` |
| JADX | 未配置：`REA_JADX_MCP_JAR` 为空，需自备 jadx-headless-mcp 0.7.1 JAR | `rea doctor` |
| REA skill | 副本过期：`C:\Users\Hayas\.agents\skills\reverse-engineer-anything` | `rea doctor` |
| REA MCP | **本会话未连接**：可用工具列表中无任何 `mcp__rea__*` 工具 | 会话工具清单 |
| JDK | Temurin 21.0.13+9，含 `javac`（完整 JDK，非 JRE） | `java -version`、`javac -version` |
| ilspycmd | 11.2.0.10050（全局 dotnet tool） | `ilspycmd --version` |
| dotnet SDK | 11.0.100 | `dotnet --version` |
| ADB | 1.0.41 / 37.0.1，路径为 Android SDK platform-tools | `adb version` |
| MuMu | MuMu 15.0 实例存在，可启动；`MuMuManager.exe control -v 0 launch` 成功 | `MuMuManager info -v 0` |
| MuMu ADB | `127.0.0.1:16384` 连接成功，型号 22041211A，Android 15 / SDK 35，ABI `x86_64,arm64-v8a,x86` | `adb connect`、`getprop` |
| MuMu 第三方包 | 仅 `com.blade.port`、`com.xingin.xhs` | `pm list packages -3` |

## 2. REA 能力边界（实测）

```text
rea capabilities
  open: false
  investigation.evidence_records: 0
  providers: native-macos / ...
rea analyze "…/Assembly-CSharp.dll"
  error: Analysis failed
  code: provider_unavailable
  candidate_ids: ghidra,hopper,ida,kuna
```

结论：REA 在本机可用于 ADB、APK 资源解码等路径（若存在 APK），但**原生/PE 分析提供者全部不可用**，且本对象为 .NET 程序集，不属于 REA 的原生分析路径。因此 .NET 静态分析改用 ILSpy，报告中不把 ILSpy 结果冒充 REA Evidence。

## 3. 运行环境

- 操作系统：Windows 11 x64（win32 10.0.26300）。
- 显示：主屏逻辑 1707×1067（150% DPI），游戏窗口物理 1942×1256。
- GPU：NVIDIA RTX 5070 Ti Laptop（日志记录）。
- Steam 正在运行；Just Xiangqi 由 Steam 安装。

## 4. 无法执行的检查项（如实记录）

- APK 的 `AndroidManifest.xml`、Activity/Service/Receiver/Provider、权限、DEX、JNI、ABI 分布、Split APK：**不适用**，因为对象不是 Android 包。
- JADX 反编译：无 APK，且 JADX 未配置。
- MuMu 内运行两款游戏：MuMu 内未安装这两款 App，且对象是 Windows 构建。
