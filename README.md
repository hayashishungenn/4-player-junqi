# 四国军棋项目

当前阶段：**P0-R 逆向分析已完成（game-01 完整 / game-02 受安装包缺失限制）**。

## 逆向档案

- 总览：[reverse-engineering/README.md](reverse-engineering/README.md)
- 交付清单与验收核对：[reverse-engineering/DELIVERABLES.md](reverse-engineering/DELIVERABLES.md)
- 中国象棋（Just Xiangqi）：[reverse-engineering/game-01/report/](reverse-engineering/game-01/report/)
- 围棋（Just Go）：[reverse-engineering/game-02/report/](reverse-engineering/game-02/report/)
- 双游戏对比与四国军棋方案：[reverse-engineering/comparison/](reverse-engineering/comparison/)

## 核心结论

1. 本地不存在棋弈无限 APK；两款对象是 Steam Windows Unity/Mono 构建。
2. 《Just Xiangqi》AI = NativeAI（Alpha-Beta）+ ElephantEyes（C#，PVS/置换表/开局库）+ Pikafish（UCI+NNUE）三路混合。
3. 《Just Go》AI = KataGo v1.10.0（GTP，b40c256 NN，Eigen CPU，4 线程）+ 200 visits 局面分析。
4. 两者不共用 AI/估值/难度；共用 Unity/Odin/ES3/Steam 产品骨架。
5. 难度设计可借鉴点：13 档 + 引擎/深度/MultiPV 随机/开局库；提示有成本；复盘逐手标签 + 曲线；内外部棋谱格式分离。

## 下一步

先按 [recommendations.md](reverse-engineering/comparison/recommendations.md) 定义引擎协议与棋谱格式，再接入主工程搜索引擎；在证据不足前不大改现有 AI。

## 已知缺口

- 《Just Go》安装主体已卸载，C# 层与难度配置无法反编译。
- REA 原生分析提供者（Ghidra/IDA/Hopper/JADX）未配置，且本会话未连接 REA MCP。
- game-01 对局内交互/复盘 UI 未实机截图。
