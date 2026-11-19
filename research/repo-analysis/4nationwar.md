# 仓库深度源码审查报告：`4nationwar`（AI 四国大战）

> 审查日期：2026-11-19
> 审查对象：`D:\4-player-junqi\workspace\4nationwar`
> 审查方式：实际打开并逐行阅读源码（非仅凭 README）
>
> ## ⚖️ 法律约束（务必先读）
>
> **本仓库许可证不明确：仓库中不存在任何 LICENSE / LICENSE.md / COPYING 文件（`git ls-files` 与文件系统均已确认）。**
>
> **因此本报告的定位是：仅参考技术思路，不复制任何代码。** 报告中出现的所有代码片段均为**短引用**，用途仅为说明算法事实与定位 bug；任何后续实现都必须在自己的工程中独立重写，不得直接拷贝、改写或搬运本仓库的源码、数据表或资源文件。在许可证澄清之前，不得将其代码纳入任何分发产物。
>
> 报告中用标记区分信息来源：
> - **【事实】** = 源码或 git 命令直接证实；
> - **【推测】** = 基于源码的合理推断，未经运行验证；
> - **【README 声明】** = 仅文档描述，源码中**未找到**对应实现。

---

## 1. 元数据、许可证与总体结论

### 1.1 版本与仓库状态

| 项目 | 结果 | 来源 |
| --- | --- | --- |
| 最新 commit | `4517e52 Just backup` | `git -C <path> log -1 --oneline` **【事实】** |
| 全部历史 | 仅 1 个 commit（`4517e52 Just backup`） | `git log --oneline -20` **【事实】** |
| 分支 | `master`（跟踪 `origin/master`） | `git branch -a` **【事实】** |
| 工作区状态 | 干净（无未提交改动） | `git status --short` **【事实】** |
| 许可证文件 | **无**（无 LICENSE / COPYING / NOTICE） | 文件系统 + `git ls-files` **【事实】** |

### 1.2 一句话结论

**【事实】** 仓库的 README 描述了一个完整的「不完全信息四人军棋 AI」设计——BoardContext 局面、MoveGenerator 走法生成、AlphaBetaSearch 搜索、BoardValue 估值、概率展开与交战历史推理。但实际源码只实现了这套设计的**前半部分**：BoardContext（局面 + 概率约束传播）、走法生成、战斗判定表、以及一个**单层的、带随机性的贪心 AI（SimpleMan）**。README 中承诺的 `AlphaBetaSearch()`、`ChessTree` 全/概率展开、置换表、剪枝、迭代加深等在源码中**完全不存在**（`gtree.cpp` 仅有 25 行骨架，`cpu.cpp` 的工厂无条件返回 `SimpleMan`）。

---

## 2. 架构、目录与构建方式

### 2.1 目录结构（源码树命令输出整理）

```
4nationwar/
├── README.md                        # 设计文档（4 KB）
├── data/jgs.tgz                     # 3.0 MB QQ 四国军棋对局录像样例包
├── player/                          # Web 端对局复盘器（jQuery + d3）
│   ├── player.html, game_001000.js
│   ├── js/{index.js,player.js,lib/*}
│   ├── css/..., images/...
├── tools/jgsParser.js               # Node.js：QQGame JQS(.jgs) 录像 → JSON
└── _ref/
    ├── data/{chess.db, db_28in1.txt, db2.pdf}   # 参考资料/布局库
    ├── desktop/                     # Qt 桌面版（GUI 层）
    │   ├── ai4.pro, ai4.qrc, main.cpp
    │   ├── mainwindow.{h,cpp}       # 主窗口 + 游戏流程驱动
    │   ├── boardscene.{h,cpp}, boardview.{h,cpp}, pieceitem.{h,cpp}
    │   └── aiagent.{h,cpp}          # QThread 包装的 AI 执行器
    └── engine/                      # 纯 C++ 游戏引擎（AI 核心）
        ├── ai4nationwar.h           # 所有枚举/常量/值表（核心数据定义）
        ├── piece.{h,cpp}, boardcontext.{h,cpp}
        ├── router.{h,cpp}           # 棋盘拓扑/路线模板
        ├── firetable.{h,cpp}        # 战斗结果判定表
        ├── cpu.{h,cpp}, simpleman.{h,cpp}, randman.{h,cpp}
        ├── player.{h,cpp}, game.{h,cpp}
        └── gtree.{h,cpp}            # 博弈树骨架（未实现）
```

**【事实】** 以上来自 `Get-ChildItem -Recurse` 完整输出（已排除 `.git`）。

### 2.2 分层架构

**【事实】** 代码分为三层：

1. **引擎层 `_ref/engine/`**：与 UI 无关的纯 C++。`Game` 是门面，持有 4 个 `Player`；每个 `Player` 持有一份 `BoardContext`（自己的棋盘视图）与一个 `CPU`；`CPU` 用 `generateMoves()` + `BoardContext::clone()` + `updateWith*()` 做决策。
2. **桌面 UI 层 `_ref/desktop/`**：Qt `QGraphicsScene/View` 绘制棋盘，`MainWindow` 驱动回合流转，`AIAgent`（QThread）异步调用 `Game::doAI()`。
3. **Web 复盘层 `player/` + `tools/jgsParser.js`**：与引擎无代码耦合，独立解析 QQ 军棋录像并回放。

### 2.3 依赖与构建

- **【事实】** 唯一构建描述是 qmake 工程 `_ref/desktop/ai4.pro`：
  ```
  TEMPLATE = app
  TARGET   = ai4
  CONFIG  += qt warn_on debug console
  ```
  它把 `main.cpp`、`mainwindow.cpp` 等 6 个 UI 源文件和 `../engine/*.cpp` 共 10 个引擎源文件一起编译，并嵌入 `ai4.qrc` 资源（棋子 PNG）。
- **【事实】** 所有 UI 头文件 `#include <QtGui>`，`main.cpp` 使用 `QApplication app(...)` 且 `mainwindow.cpp:68` 调用 `QApplication::desktop()`。这是 **Qt4 风格**（Qt5+ 需 `<QtWidgets>` 且 `desktop()` 已废弃）。**【推测】** 工程应基于 Qt4 早期版本，现代 Qt5/Qt6 环境无法直接编译，需迁移。
- **【事实】** Node 工具 `tools/jgsParser.js` 仅用内置 `fs`，无 npm 依赖；Web 复盘器依赖随仓库附带的 jQuery / d3 / bootstrap 压缩文件。
- **【事实】** 没有 CMake、没有 `Makefile`、没有 CI 配置、没有 `README` 之外的构建说明。
- **【事实】** 依赖清单（引擎）：C++ 标准库 `<vector>` `<string>` `<iostream>` `<stdlib.h>`；无第三方 AI/数学库。

### 2.4 测试用例

**【事实】** 仓库中**没有任何自动化测试框架或测试文件**。唯一的"测试"入口是桌面版菜单 `test` 动作：

- `_ref/desktop/mainwindow.cpp:470-473`：`MainWindow::test()` 调用 `gameControler->checkBoard()` 并把返回值打印到 stdout。
- `_ref/engine/game.cpp:131-172`：`checkBoard()` 遍历 8×20 全盘，交叉校验 4 个 `BoardContext` 视图的一致性（空格/颜色/坐标），返回 `0` 正常、`-1/-2/-3` 各类不一致。
- Web 端 `player/js/index.js:21-30` 在页面加载时 `loadGame(game1000)`，属于演示而非断言测试。

这是手工调试钩子，不是可重复的测试套件。**【推测】** 项目处于原型/备份阶段（与唯一 commit 名 "Just backup" 一致）。

---

## 3. 核心模块逐一分析

### 3.1 局面表示：`BoardContext`（`_ref/engine/boardcontext.h` / `.cpp`）

#### 3.1.1 数据结构

**【事实】** `boardcontext.h:8-73`：

- `Move`：仅 4 个 `unsigned int`：`fromY, fromX, toY, toX`（无棋子身份、无时间戳）。
- `ProbInfo`：`pseudoValue`（预留）、`valueTable`（**候选角色位掩码**）、`leftCapture` / `rightCapture`（历史交战位图）、`capturedBy` / `firedBy`（记录被谁吃/炸）、`moved`（移动步数）。
- `BoardContext` 三个核心成员（`:70-72`）：
  ```cpp
  Piece *mainBoard[8][20];   // 8×20 逻辑棋盘，NULL=空，否则指向 allPieces
  Piece allPieces[100];      // 4 国 × 25 子，固定下标 color*25 + i
  ProbInfo probMatrix[100];  // 与 allPieces 一一对应的概率/历史信息
  ```
- `Piece`（`piece.h:12-21`）：`color`、`role`、`isAlive`、`y`、`x`。即局面 =
  **当前排布**（mainBoard + allPieces）+ **历史与置信度**（probMatrix）。这与 README 第 21、30-33 行的设计一致。

#### 3.1.2 初始化与坐标

**【事实】** `reset()`（`boardcontext.cpp:18-112`）把 8×20 全部置 NULL，然后为每国 25 子按固定位置放置，**全部初始为 `PR_UNKNOW`（暗子）**：

- 后排两行 `y=6..7, x=0..4`（10 子，含地雷/炸弹候选）；
- 前排 `y=2, x=0..4`（5 子）；
- 左右两翼 `y=3..5, x=0 / x=4`（6 子）；
- 中心四营 `(3,2),(4,1),(4,3),(5,2)`（4 子）。

初始化 `ProbInfo`（`:78-110`）：`moved=0`、四个历史字段清零，`valueTable` 按**位置先验**赋值：

| 位置类别 | valueTable 掩码 | 含义（【事实】常量见 `ai4nationwar.h:197-201`） |
| --- | --- | --- |
| 默认（普通格） | `EPR_MOVEABLE = 0x001FFFFF` | 可动子（排除炸弹、地雷、军旗） |
| 铁路上行 / 第一线 | `EPR_FIRST_ROW = 0x0007FFFF` | 仅普通可动子 |
| 铁路下行 / 最后两行 | `EPR_LAST_TWO_ROWS = 0x00FFFFFF` | 含炸弹、地雷（排除军旗） |
| 大本营 | `EPR_ALL = 0x01FFFFFF` | 所有角色 |

**【事实】** 该文件开头注释（`:8-16`）直接给出了这些先验的概率推导（如 `p(flag, base)=50%`、`P(bomp, downtwo)=4.1667%` 等），说明作者把"位置 → 角色概率"手工编码进了位掩码初值。

**【推测】** `reset()` 中 `:99-104` 的条件里 `POS_RAIL_RD` 出现两次（`:100` 已是 `POS_RAIL_LD`，`:101` 又写 `POS_RAIL_RD`），疑似笔误，本应是某种去重或遗漏了另一铁路位置；影响范围有限。

#### 3.1.3 深拷贝与视图隔离

**【事实】** `clone()`（`:115-134`）逐字节复制 `allPieces[i]` 与 `probMatrix[i]`，并按 `isAlive` 重建 `mainBoard[y][x]` 指针，使其指向**新对象自己的** `allPieces`。这是博弈树节点展开与 AI 假设模拟的基础。

**【事实】** `getProbInfo(Piece *p)`（`:40-42`）用 `p - &allPieces[0]` 指针差直接换算下标——依赖"棋子对象始终来自 `allPieces` 数组"这一不变量。

**【事实】** 每个 `Player` 拥有独立 `BoardContext`（`player.cpp:18`），`Game::doUpdate()`（`game.cpp:75-81`）把同一个 `ACTION_RESULT` 广播给全部 4 家。这是"每个玩家维护自己的信息集"的设计，可封装不完全信息视角；但当前实现中 4 份 BoardContext 初始布局完全相同（桌面演示用固定布局），**并未真正做信息隐藏**。**【推测】** 这是原型未完成的环节。

---

### 3.2 走法生成：`generateMoves`（README 中的 MoveGenerator）

**【事实】** `boardcontext.cpp:148-232`，两个重载：

1. `generateMoves(color, fromPiece, allMoves)`（`:148-212`）：
   - `friendColor = (color + 2) % 4`（对家为友军）；
   - 调用 `Router::queryFreePath(y, x)` 取得该格的**预生成路线模板** `Path`；
   - 每条 `Road` 的 `steps` 是扁平的 `(y,x)` 序列。沿序列逐格检查：目标为空**或**为敌军（既非己方也非友军）时可落子；遇障碍即 `break`（不能越过）；
   - 军营规则（`:168-172`）：`new_y >= 3 && POSTABLE[..] & POS_CAMP_MASK` 时禁止进入军营；
   - 若一条铁路线走到尽头未遇阻挡（`doBranch == true`），继续展开该 `Road::branches`（铁路拐弯/跨区支线，`:190-209`）。

2. `generateMoves(color, allMoves)`（`:213-232`）：遍历该色 25 子，跳过：已死亡、`PR_FLAG`、`PR_MINE`、位于大本营（`(y==7 && x%5 in {1,3})`）的子，再逐子调用上一重载。

**【事实】** `checkMove()`（`:234-252`）复用上述生成结果做全等匹配，供 `Game::doAction()`（`game.cpp:32-36`）做合法性校验。

#### 路线模板 `Router`（`router.cpp`）

**【事实】** `queryFreePath(y,x)`（`:10-29`）按 `y>=2`（主盘）/`y<2`（中心）分流到 `buildMainBoardPath` / `buildCenterBoardPath`，结果缓存在 `pathsCache[8][20]`（静态，仅初始化一次）。`Road::steps` 存逐格序列，`Road::branches` 存铁路分叉（`:335-654` 的 `buildMainBoardPath2` 中可见 `'leftRoad'`、`'forwardRoad'` 经 `L1_TABLE` 接入中心区的编码）。

**【事实/观察】** 生成逻辑**不检查棋子角色**——所有可动子使用同一套含铁路长线的模板。**【推测】** 这意味着非工兵也可能沿铁路长距离移动，与标准军棋"只有工兵可随意走铁路"的规则存在差异；README 第 57-59 行明确提到"必须提前考虑工兵的路线裁剪"，但源码未实现该裁剪。

---

### 3.3 战斗判定与暗棋概率处理

#### 3.3.1 角色与战斗表

**【事实】** `ai4nationwar.h:53-68` 定义 `PIECE_ROLE`（数值越小军衔越高）：`PR_MINER=0`（工兵）、`PAI=1`（排长）、`LIAN=2`（连长）、`YING=3`（营长）、`TUAN=4`（团长）、`LV=5`（旅长）、`SHI=6`（师长）、`JUN=7`（军长）、`LING=8`（司令）、`BOMB=9`、`MINE=10`、`FLAG=11`、`UNKNOW=13`。每种角色的**数量**由 `SEQ_TABLE2[]`（`:220-246`）编码：工兵/排长/连长各 3、营长/团长/旅长/师长各 2、军长/司令各 1、炸弹 2、地雷 3、军旗 1。

**【事实】** `firetable.cpp:5-47` 的 `initFireTable()` 构造 13×13 判定矩阵：

```cpp
if (i < j) fireTable[i][j] = AI4::AR_LOST;     // 军衔低者败
if (i == j) fireTable[i][j] = AI4::AR_FIRE;    // 同归于尽
if (i > j) fireTable[i][j] = AI4::AR_CAPTURE;  // 军衔高者胜
...
fireTable[PR_MINER][PR_MINE] = AI4::AR_CAPTURE;  // 工兵挖雷
fireTable[PR_BOMB][i] = fireTable[i][PR_BOMB] = AR_FIRE;  // 炸弹同归于尽
```

**【事实】** `Game::doAction()`（`game.cpp:32-67`）在此表之上映射特殊结果：`LING_LING`（司令撞司令）、`LING_BOMP` / `BOMP_LING`（工兵炸炸弹/反之）、`LING_MINE`（工兵挖雷）、`AR_FLAG`（夺旗）。

#### 3.3.2 暗子的候选集位掩码

**【事实】** `ai4nationwar.h:161-202` 的 `ESTIMATE_PIECE_ROLE` 用 32 位整数的**每一位（或每几位组合）表示一种角色是否仍为候选**：如 `EPR_MINER1/2/3`（三位表示三个工兵个体）、`EPR_PAIS`、`EPR_LIANS` … `EPR_JUN`、`EPR_LING`、`EPR_BOMB1/2`、`EPR_MINE1/2/3`、`EPR_FLAG`。`SEQ_TABLE[]`（`:205-218`）把角色映射到对应掩码。`SEQ_TABLE2[i]` 则把位序号 `i` 反查回角色（`simpleman.cpp:47-53` 使用）。

**【事实】** 因此"暗棋概率"在代码里**不是浮点数权重**，而是"候选角色集合"的位掩码集合，通过按位与不断收缩。README 第 44-55 行设计的"三项概率表 + 加权反向传播"在源码中**没有实现**。

#### 3.3.3 交战历史如何记录与利用

这是整个引擎最有价值的部分。

**【事实】记录**（`boardcontext.cpp`）：

- `updateWithCapture()`（`:306-338`）：攻击方胜、防守方死。随后：
  ```cpp
  probMatrix[from].valueTable &= AI4::EPR_MOVEABLE;
  probMatrix[from].valueTable &= queryCaptureByValue(probMatrix[to].valueTable);
  probMatrix[to].valueTable   &= queryCaptureValue(oldValue1);
  ```
  并按两国相对方位把对手下标记入 `leftCapture` 或 `rightCapture` 位图（`:330-336`）：
  ```cpp
  if ((allPieces[to].color + 4 - allPieces[from].color) % 4 == 1)
      probMatrix[from].leftCapture |= 1 << (to%25);
  else if (... % 4 == 3)
      probMatrix[from].rightCapture |= 1 << (to%25);
  ```
- `updateWithLost()`（`:340-367`）：镜像逻辑（我方败）。
- `updateWithFire()`（`:369-399`）：双方死亡；若一方可能是炸弹，则从双方候选集中**删去工兵位**（`& ~EPR_LING`）；否则用对方候选集做交集；写 `firedBy`。
- `updateWithLingBomp/LingLing/BompLing/LingMine()`（`:401-502`）：特殊结局直接把身份坐实（`p->role = PR_LING / PR_BOMB / PR_MINE`）并把 `valueTable` 收窄到单一类别。
- `updateWithMove()`（`:287-304`）：每走一步 `moved++`；暗子移动后其候选集去掉地雷/炸弹/军旗位（`&= EPR_MOVEABLE`）——**"动过的子不可能是地雷/炸弹/军旗"**这一常识被编码为约束。

**【事实】推理（约束传播）**：

- `queryCaptureValue()`（`:508-556`）与 `queryCaptureByValue()`（`:558-599`）是两张"谁能吃谁"的反向映射：给定敌方候选集，返回"能战胜它的角色集合"与"能战胜它的角色的集合"。例如敌方候选含 `EPR_MINERS` → 能制服它的集合加入 `EPR_MINES`（地雷克工兵）；敌方含 `EPR_JUN` → `queryCaptureByValue` 加入 `EPR_LING`（只有司令能吃军长）。
- `updateProbTreeWithTopUpdate()`（`:601-632`）是**传播核心**：当某子候选集收缩后，遍历它 `leftCapture`/`rightCapture` 中记录的所有历史交战对手，对仍为暗子的对手执行 `valueTable &= captureValue`，若发生变化则**递归传播**——形成沿交战历史图的约束传播链。
- `checkProbValue()`（`:646-733`）：若某暗子候选集收缩为单一角色类别，就把 `role` 坐实，并调用 `setupProbValue()`。
- `setupProbValue()`（`:635-644`）：**数量消元**——确定某子为角色 X 后，对同阵营其余所有暗子执行 `valueTable |= ~value`，即从它们的候选集中删除 X（利用"每种棋子数量固定"的先验）。

**【事实】** 这套机制等价于一个**位掩码上的约束满足问题（CSP）/信念传播**：变量=棋子，域=候选角色位集，约束=交战结果 + 移动事实 + 棋子数量，传播=沿历史边迭代收缩域。

---

### 3.4 估值函数（README 中的 BoardValue）

**【事实】** README 第 24 行声明存在 `BoardValue()`，但源码中真正的估值只有 `simpleman.cpp:9-35` 的静态函数 `simpleBoardValue()`：

```cpp
float value = 0.0;
for (int i = 0; i < 100; i++) {
    Piece* p = ctx->getPiece(i);
    if (p->isAlive) {
        if (p->color == color)             value += AI4::VALUE_TABLE[p->role];
        else if (p->color == friendColor)  value += (p->role==PR_UNKNOW) ? 5 : VALUE_TABLE[p->role];
        else                               value -= (p->role==PR_UNKNOW) ? 15 : VALUE_TABLE[p->role];
    }
}
```

（注意：未知敌方子一律按 `-15` 计，未知友军按 `+5` 计——体现对不确定性的风险折扣。）

**【事实】** `VALUE_TABLE[]`（`ai4nationwar.h:146-159`）：军旗 200、司令 100、军长 40、师长 30、炸弹 30、旅长 20、工兵 15、地雷 10、团长 6、营长 4、连长 2、排长 1。

**【推测】** 该估值非常粗糙：只有子力总和，**不含位置价值、棋子协同、军旗安全、工兵控制等项**；且敌方暗子用固定 `-15`，没有随候选集概率变化。README 第 24 行的 `BoardValue()` 显然设想得更复杂，但未落地。

---

### 3.5 搜索实现（README 中的 AlphaBetaSearch）

这是本次审查最需要与 README 划清界限的部分。

**【README 声明】** 第 22-26 行：`MoveGenerator` 反复迭代生成 `ChessTree`，有"优化过的 Alpha/Beta 树搜索算法 `AlphaBetaSearch()`"；第 39-59 行描述了"全展开 / 概率展开 / 加权三子节点合并 / 工兵裁剪"。

**【事实 —— 源码中并不存在】**

- 全仓库 `.h/.cpp/.js` 搜索（见第 2 节的 grep）**没有任何** `AlphaBeta`、`alphaBeta`、`Transposition`、`iterative`、`depth`、`MAX_DEPTH` 等符号；唯一出现 `AlphaBeta` 的位置是 README 的文字。
- `_ref/engine/simpleman.cpp:65-134` 的 `SimpleMan::doAction()` 是实际决策函数，**只有一层（1-ply）**：
  1. 生成全部走法（`:66-67`），空则投降（`:68-70`）；
  2. **空格走法**（`:79-87`）：`clone()` → `updateWithMove()` → `simpleBoardValue()`，并加了随机条件 `rand() % 10 == 1` 才采纳；
  3. **吃子走法**（`:88-129`）：`simpleProbValue()` 枚举目标暗子的所有候选角色，对每个战斗结果克隆局面并调用相应 `updateWith*()`，求 `simpleBoardValue()` 后**取算术平均**（`:93-123`），即"期望展开"；
  4. 取最大估值走法返回。

- `simpleProbValue()`（`:37-55`）的暗棋展开是**均匀平均**，没有 README 所说的"三项概率权重"：
  ```cpp
  if (probTo.valueTable & (1<<i)) {
      AI4::PIECE_ROLE r = AI4::SEQ_TABLE2[i];
      results.push_back(fireTable[pFrom->role][r]);   // 每个候选角色一票
  }
  ```

- `gtree.cpp` 全文 25 行（`:3-22`）：`GameTree` 只实现了构造/析构和 `addMove()`（仅当目标为空时 `clone()` 出一个子节点）；头文件里的 `GameBranch captured_/losted_/fired_`、`value_`、`weight_`、`mchild_` **全部未被使用**。**【事实】** 博弈树是一个空壳。

- `cpu.cpp:6-11` 的工厂无视参数、无条件返回 `SimpleMan`：
  ```cpp
  CPU* CPU::createCPU(std::string &name, void *parameter) {
      name = name; parameter = parameter;   // 自赋值，形同虚设
      CPU *cpu = new SimpleMan();
      return cpu;
  }
  ```
  **【事实】** `mainwindow.cpp:42` 请求 `"Random"` 但实际得到的仍是 `SimpleMan`；`randman.cpp` 的 `RandomMan` 是死代码。

**结论**【事实】：**没有搜索深度、没有置换表、没有 α-β 剪枝、没有迭代加深、没有加权概率分支**。README 描述的是"目标设计"，源码是"未完成的原型"。这一区分是本报告的核心发现之一。

---

## 4. 游戏流程与 UI 层（简要）

**【事实】** `mainwindow.cpp:37-56` 创建 1 名人类玩家（南）+ 3 名 CPU（西/北/东）；`restart()`（`:222-336`）用硬编码的 100 字符十六进制串 `sample`（`:109-113`）给所有棋子赋**明确的**角色（即桌面演示是"明棋"模式），并把位置在逻辑坐标 8×20 与屏幕网格间转换（`board2Scene` `:115-165`、`scene2Board` `:167-220`）。

**【事实】** 回合流转：`onPieceMove()`（`:373-404`）→ `Game::doAction()`（判定）→ `Game::doUpdate()`（广播到 4 份 BoardContext）→ `AIAgent` 异步执行 → `onAIFinish()`（`:338-371`）→ `state = (state+3)%4` 切到下家。

**【事实】** `_ref/desktop/aiagent.cpp:17-24` 的 `run()` 先 `QThread::msleep(1000)` 再调用 AI，即每步 AI 有 1 秒人为延迟；`:6-15` 的 `ExecuteAI()` 中 `inProcessing` 先置 `false` 再在 `run()` 末尾置 `true`，语义反常。**【推测】** 由于 `MainWindow` 每回合都 `new AIAgent()`（`:368`、`:401`）且未删除，这里存在状态机混乱与内存泄漏（旧 `AIAgent` 对象不断累积）。

**【事实】** Web 复盘器：`tools/jgsParser.js` 解析 QQGame JQS 文件头 `"QQGame JQS"`（`:7`）、17×17 布局（`:74-133`）、棋步/事件记录（`:177-257`），输出 JSON；`player/js/player.js` + `index.js` 用 jQuery 渲染并提供前进/后退/重置。数据样例在 `data/jgs.tgz`（3.0 MB）。

---

## 5. 已知问题与局限汇总

| # | 问题 | 性质 | 证据 |
| --- | --- | --- | --- |
| 1 | **无 LICENSE 文件**，许可证不明确 | 法律 | 文件系统 + `git ls-files` |
| 2 | README 承诺的 AlphaBetaSearch / 加权概率展开 / 置换表 / 剪枝 / 深度搜索**全部未实现** | 功能缺口 | grep + `simpleman.cpp` + `gtree.cpp` |
| 3 | `CPU::createCPU` 无条件返回 `SimpleMan`，`RandomMan` 死代码；参数被自赋值忽略 | bug | `cpu.cpp:6-11` |
| 4 | `GameTree` 是空壳，`mchild_/weight_/value_` 未用 | 未完成 | `gtree.cpp:3-22`, `gtree.h:16-30` |
| 5 | `AR_LING_LING` 被错误地当成 `AR_LING_BOMP` 处理 | bug | `simpleman.cpp:110-111`，`player.cpp:95-97`（与 `game.cpp:48-54` 的正确区分不一致） |
| 6 | `boardcontext.cpp:99-104` 重复 `POS_RAIL_RD` 条件 | 疑似笔误 | 源码原文 |
| 7 | 暗棋展开用**均匀平均**，未使用 README 设计的概率权重 | 设计落差 | `simpleman.cpp:37-55, 93-123` |
| 8 | 估值仅子力和，敌方暗子固定 `-15`，无位置/协同项 | 简化 | `simpleman.cpp:9-35` |
| 9 | 桌面演示用固定明棋布局（`sample`），4 个 `BoardContext` 完全相同，未真正做信息隐藏 | 未完成 | `mainwindow.cpp:109-113, 222-336` |
| 10 | 走法生成不区分工兵铁路权限，无工兵路线裁剪 | 规则偏差 | `boardcontext.cpp:148-212`; README:57-59 |
| 11 | Qt4 风格（`<QtGui>`、`QApplication::desktop()`），现代 Qt 难编译 | 兼容性 | 各 UI 头 + `main.cpp` |
| 12 | `AIAgent::inProcessing` 语义反常、每回合 new 且不 delete | bug/泄漏 | `aiagent.cpp`, `mainwindow.cpp:368,401` |
| 13 | 无自动化测试、无 CI、无构建文档 | 工程化 | 目录树 |
| 14 | `fireTable[?][PR_UNKNOW]` 未初始化（值 0=AR_MOVED），若引入真暗棋会误判 | 潜在 bug | `firetable.cpp:11-39`（仅填 0..11），`game.cpp:46`。**【推测】**，因当前演示均明棋故未触发 |

---

## 6. 可借鉴的算法思路（中文，仅思路层面）

> 以下均为从源码中**抽象出的设计思想**。根据第 1 节的法律约束，仅作技术思路参考，不复制任何代码。

1. **用位掩码表示不完全信息下的"候选角色集合"**。把每个暗子的可能身份编码为一个 bitmask（每个/每类棋子占一位），所有推理都化为按位与/或/取反。这比维护浮点概率分布更省内存、更快，且天然支持"排除某个角色"的确定性推理。适合任何"隐藏身份 + 逐步揭示"的博弈（如军棋、狼人杀类推理）。

2. **把"交战历史"建模成可传播的约束图**。每次吃/撞，在双方记录一条带方位的边（`leftCapture`/`rightCapture` 位图）。当任一方的候选集收缩时，沿这些历史边把"能战胜它的角色集合"传播给对手，递归迭代直到不动点。这是把**贝叶斯/信念更新**工程化为**CSP 约束传播**的实用做法——历史不是仅用于复盘，而是直接服务于当前决策。

3. **利用"棋子数量固定"做全局消元**。一旦某个暗子身份坐实，立即从所有同阵营暗子的候选集中删除该角色。这是经典的"全不同/计数约束"传播，能显著加速收敛。

4. **位置先验 + 行为后验**：初始按布子区域给不同候选集（前排排除雷/炸、后排/大本营放宽）；棋子一旦移动就排除"地雷/炸弹/军旗"。把规则常识（"雷不能动"）转化为集合收缩，比纯统计更可靠。

5. **路径模板 + 运行时占用扫描的走法生成**。不规则棋盘（军棋十字+铁路+行营）的拓扑被预计算成 `8×20` 的 `Path/Road/steps/branches` 缓存；生成走法时只做"能否落入该格"的轻量检查，不重复推演拓扑。这是"空间换时间"在棋盘表示上的典型应用，可迁移到任何不规则图棋盘。

6. **面对隐藏信息，用"期望展开"替代全展开**。对一次撞子，不枚举所有组合分支，而是枚举目标暗子的候选角色、对每种战斗结局模拟一次并估值，再取平均。虽然原型是均匀平均（未加权），但框架本身可扩展为"按候选集大小/数量先验加权"的期望极小极大，或作为蒙特卡洛采样的骨架。

7. **多方信息集封装**：让每个玩家持有自己的棋盘视图，由裁判（`Game`）向所有视图广播同一个客观事件结果，各视图独立更新自己的置信度。这是多人不完全信息游戏状态同步的清晰架构。

8. **战斗规则集中查表**：把 12 种角色的胜负关系写成一张小矩阵 + 少量特例覆盖（工兵挖雷、炸弹同归、军旗），避免把规则散落在条件分支里，便于校验和扩展。

9. **（反例借鉴）搜索层必须真实落地**：本项目 README 与代码严重脱节——设计书写了 α-β、置换表、加权概率分支，代码却只有一层贪心。工程启示：算法叙事要与可运行实现逐一对照，未实现部分应显式标注，避免"文档幻觉"。

---

## 7. 附：本次实际阅读的文件清单

- `README.md`
- `_ref/engine/`：`ai4nationwar.h`、`piece.h`、`piece.cpp`、`boardcontext.h`、`boardcontext.cpp`、`router.h`、`router.cpp`、`firetable.h`、`firetable.cpp`、`cpu.h`、`cpu.cpp`、`simpleman.h`、`simpleman.cpp`、`randman.h`、`randman.cpp`、`gtree.h`、`gtree.cpp`、`game.h`、`game.cpp`、`player.h`、`player.cpp`
- `_ref/desktop/`：`ai4.pro`、`ai4.qrc`、`main.cpp`、`aiagent.h`、`aiagent.cpp`、`mainwindow.h`、`mainwindow.cpp`、`boardscene.h`、`boardview.h`、`pieceitem.h`
- `tools/jgsParser.js`、`player/js/player.js`（前 40 行）、`player/js/index.js`
- 数据文件仅核对大小：`data/jgs.tgz`、`_ref/data/{chess.db,db_28in1.txt,db2.pdf}`

未修改 `workspace/` 下任何源码文件；本报告为唯一新建文件。

**再次声明：本仓库无明确许可证，报告仅参考技术思路，不复制任何代码。**
