# REA Evidence 汇总（game-01）

工具链：`rea@6.9.0` + Ghidra 12.2（`D:/tools/ghidra_12.2_PUBLIC`）+ Temurin JDK 25.0.5。
所有分析为只读导入，原始文件未修改。

## 1. pikafish.exe

### 1.1 二进制概览

| 项 | 值 |
|---|---|
| evidence_id | `ev_a16b99431fe74339b39318e46ccfd76b9573805b9ee3646d9adcf78879f957b3` |
| SHA-256 | `8fedd65c00d15b20265148cd102856ce20d4cdb9e9fdef93553ca74433845961` |
| 格式 / 架构 | PE / x86_64 |
| 段数 | 9（`.text` 1,179,648 B；`.data` 35,102,720 B） |
| 过程数 | 2,924 |
| 字符串数 | 1,740 |

### 1.2 关键字符串与符号（`rea search` 正则匹配）

| 地址 | 字符串/符号 | 证明 |
|---|---|---|
| `0x140136b80` | `pikafish.nnue` | 默认 NNUE 文件名 |
| `0x140136cf5` | `EvalFile` | UCI 网络文件选项 |
| `0x140138162` | `NNUE evaluation` | NNUE 评估输出 |
| `0x1401397f8` | `info string NNUE evaluation using ` | 运行时 NNUE 加载提示 |
| `0x140138e18` | `N9Stockfish18LazyNumaReplicatedINS_4Eval4NNUE7NetworkEEE` | Stockfish `Eval::NNUE::Network` 的 NUMA 复制类 |
| `0x140149a48` | `Skill Level` | UCI 棋力选项 |
| `0x14014a518` | `...Stockfish18TranspositionTable5clearERNS2_10ThreadPoolE...` | 置换表类与 `clear(ThreadPool&)` |
| `0x14014a96` | `N9Stockfish6Search13SearchManagerE` | `Search::SearchManager` |
| `0x14014a1b8` | `N9Stockfish6Search14ISearchManagerE` | 搜索管理器接口 |
| `0x14014a218` | `N9Stockfish6Search17NullSearchManagerE` | 空搜索管理器 |
| `0x14014aaf2` | `setoption` | UCI 选项命令 |
| `0x14014b0e0` | `info depth ` | UCI 搜索信息 |
| `0x14014b10c` | ` multipv ` | MultiPV 输出 |
| `0x1401353b8` | `setoption name Threads value ` | 线程选项 |
| `0x1401353d6` | `setoption name Hash value ` | 置换表大小选项 |

### 1.3 证据结论

- Pikafish 是 **Stockfish 系引擎**：二进制中包含 `Stockfish` 命名空间的 `TranspositionTable`、`SearchManager`、`Thread`、`Eval::NNUE::Network` 等 RTTI/符号残留。
- 评估为 **NNUE**：存在网络文件名、`EvalFile` 选项、`NNUE evaluation` 输出字符串。
- 搜索具备 **置换表**：`TranspositionTable::clear(ThreadPool&)` 符号与 `Hash` 选项。
- 具备 **MultiPV、Threads、Skill Level** 等 UCI 能力；游戏侧只使用 MultiPV，未设置 Skill/Elo（见报告 04/07）。
- 这与代码级结论（`ProcessManager` 解析 `info depth/cp/mate/pv/wdl`）互相印证。

## 2. UnityPlayer.dll

（分析进行中；完成后补充 evidence_id、段/过程/字符串数与关键符号。）

## 3. 能力边界

- REA 通过 Ghidra 只做只读导入；`analysis_profile` 记录 `import_mode: ephemeral-source-immutable`。
- Ghidra 报告 PDB 引用存在但加载状态未知，原符号可能缺失；因此函数名多来自 C++ RTTI/异常表与字符串，而非完整符号表。
- 未执行目标程序；分析在导入后由 Ghidra 自动分析完成。
