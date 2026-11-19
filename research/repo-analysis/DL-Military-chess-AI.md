# DL-Military-chess-AI 深度源码审查报告

> 审查对象：`D:\4-player-junqi\workspace\DL-Military-chess-AI`
> 审查日期：2026-11-19
> 审查方式：逐文件打开源码阅读（非仅读 README）
>
> **法律约束声明（先置）：该仓库无任何 LICENSE / LICENSE.txt / COPYING / NOTICE 文件，`git ls-files` 中也未跟踪任何许可文件；README 与源码中均未出现授权条款。权利状态不明，默认应视为「保留所有权利」。
> 本报告仅用于参考和提炼技术思路，不复制、不移植、不引用其代码到本项目。本报告中出现的关键代码片段均为「短引用」，仅作事实指认与定位之用；任何后续实现必须独立编写。**

---

## 0. 证据标注约定

- 【事实】：可由指定文件与行号直接验证的源码内容或仓库状态。
- 【推测】：基于源码/README 的合理推断，未在该仓库中得到直接实现证实。
- 【未实现】：README 或注释中描述，但源码中找不到对应实现，或明确标注未使用。

---

## 1. 版本、许可证、依赖与整体架构

### 1.1 版本与提交

| 项目 | 内容 |
|---|---|
| 最新 commit | `84e26a0 文件改名，以及一种可以测试模型的数据`（`git -C <path> log -1 --oneline` 输出） |
| 提交日期 | 2020-07-14（`git log --format="%h %ad %s" --date=short`） |
| 提交数量 | 【事实】`git log` 仅返回 1 条记录，即仓库为单提交快照，无后续迭代历史。 |
| 工作区状态 | 【事实】`git status --short` 无输出，工作区干净。 |

### 1.2 许可证状态

- 【事实】仓库根目录文件清单中无 `LICENSE`、`LICENSE.txt`、`COPYING`、`NOTICE` 或任何许可文件。
- 【事实】`git ls-files | findstr /i "license licence copying notice"` 无匹配（返回 `NO_LICENSE_FILE_TRACKED`）。
- 【事实】`README.md` 全文（1-87 行）未包含任何开源许可声明。
- 结论：**许可证不明确 / 无许可证**。法律上不能假定其可自由使用、修改或分发。
- **约束重申：仅参考技术思路，不复制任何代码。**

### 1.3 运行环境与依赖

- 【事实】`value_net.py:1-12` 使用**旧版独立 Keras** API：`keras.engine.topology.Input`、`keras.engine.training.Model`、`keras.layers.convolutional.Conv2D`、`keras.layers.core.Dense/Flatten/Lambda`、`keras.layers.MaxPooling2D/BatchNormalization`、`keras.regularizers.l2`、`keras.callbacks`、`keras.backend`。
- 【事实】`LossHistory.py:1-2` 依赖 `matplotlib.pyplot` 与 `keras`。
- 【事实】`train.py:1-2`、`value_net.py:11` 依赖 `numpy`、`random`（标准库）。
- 【事实】`mcts.py:122`、`mcts.py:124-135` 使用标准库 `configparser` 读写 INI 文件。
- 【事实】`playout.py:1`、`test2.py:1` 使用标准库 `subprocess` 调用外部进程。
- 【事实】`input.ini` 为 **GBK/ANSI 编码**（头部字节 `5B-6D-61-69-6E-5D-0D-0A` 即 `[main]\r\n`，中文为 GBK 字节；用 UTF-8/UTF-16 读取均乱码）。
- 【事实】仓库内**没有** `requirements.txt`、`setup.py`、`pyproject.toml`，无依赖版本锁定。
- 【推测】现代tf.keras（TensorFlow 2.x）直接运行本代码会因模块路径变更（`keras.engine.topology` 等）报错，需大幅改造。

### 1.4 整体架构（按职责分层）

| 层 | 文件 | 职责（事实依据） |
|---|---|---|
| 棋盘规则与走法生成 | `basic.py`、`help.py`、`eneSta.py` | 棋子编码、铁路/行营/山界规则、`getAccessibility`（`basic.py:174-302`）、吃子判定辅助、坐标↔隐藏棋子索引映射（`eneSta.py:1-14`） |
| 规则型局面评估 | `asses.py` | 7 项手工特征、棋子强度表、`ChessComparisons` 概率化战斗裁决（`asses.py:55-84`） |
| 走子模拟 | `simulate.py` | 在副本上执行移动/吃子/同归于尽，维护隐藏棋子位置（`simulate.py:5-51`） |
| 神经估值网络 | `value_net.py` | Keras 卷积+全连接**单一价值头**（类名虽为 `PolicyValueNet`，但无 policy 头） |
| 数据解析与训练集构建 | `inputHelp.py`、`input.py`、`train.py` | 棋谱/日记文件解析、样本双向标注、平衡采样、增量训练 |
| 搜索 | `mcts.py`、`playout.py` | 固定深度 alpha-beta + NN 叶子估值（名为 MCTS）、外部 `playout.exe` 快速走子接口 |
| 日志/可视化 | `LossHistory.py` | Keras Callback 记录 loss/acc |
| 与外部程序对接 | `input.ini`/`output.ini`/`finish`、`chess.exe` | 通过 INI 文件交换局面与着法，纯 Python 通过 `mcts.py:124-150` 主函数暴露接口 |
| 测试 | `test.py`、`test2.py` | 模型预测冒烟测试、playout.exe 子进程测试 |

- 【事实】仓库附带 `chess.exe`（二进制），但**未附带** `playout.exe`，也未附带 `model0.pkl`（`mcts.py:8` 与 `test.py:4` 都硬编码加载它）。
- 【事实】README 第 37、47 行说明极大极小模块来自 Gitee 仓库 `Chess-AI`，神经网络模块来自 `DL Chess AI`，本仓库是集成与军棋化改造。论文成果：CCDC2020（README:77）。

---

## 2. 逐文件阅读记录（关键实现与行号）

### 2.1 `value_net.py`（118 行）——神经估值网络

- 【事实】`PolicyValueNet.__init__`（44-50）：`l2_const = 1e-4`；若传入 `model_file` 则 `load_model(model_file, custom_objects={"Recall":Recall})`，否则 `create_net()`。
- 【事实】双输入（54-55）：
  - `board = Input((1, 21, 21))` —— 单通道、channels_first、21×21。
  - `otherFeature = Input((10,))` —— 注释：`目前手数，我方棋子数，敌方棋子数，局面评估7项`（3 + 7 = 10）。
- 【事实】拼接函数 `toModelBoard`（14-27）：把 `board`（12×5=60 个值）与 `probMap` 展平后相加拼接，零填充至 `21*21=441`，reshape 成 `(21,21)`，返回长度为 1 的列表。
- 【事实】`Recall` 自定义指标（30-35）：`tp = sum(round(clip(y_true*y_pred,0,1)))`，`pp = sum(round(clip(y_true,0,1)))`，`recall = tp/(pp+eps)`。
- 【事实】训练回调（37-41）：`EarlyStopping(monitor="val_loss", patience=70)`、`ReduceLROnPlateau(monitor="val_loss", factor=0.7, verbose=1, patience=5)`；`ModelCheckpoint` 被注释掉。
- 【事实】`train`（86-90）：`model.fit([board, otherFeature], isWin, batch_size=..., epochs=..., callbacks=callback_list, validation_split=0.3)`；内部 `history = LossHistory.LossHistory()` **创建后未传入 callbacks**。
- 【事实】`predict`（92-99）：`otherFeature=[rounds,myChessNum,eneChessNum]+list(estResult)`，经 `toModelBoard` 构造 21×21，返回 `model.predict([x1Data,x2Data])[0]`。
- 【事实】`get_param`/`save_model`（112-117）：直接取 `model.get_weights()` / `model.save()`。

### 2.2 `train.py`（86 行）——样本结构与训练循环

- 【事实】`makeCompleteProbMap`（11-15）：对 25 行 `probMap`，每行追加 `posList[i][0]`、`posList[i][1]`，使 25×12 → 25×14；注释明确警告「会改变原来的 probMap」。
- 【事实】`situation`（17-31）：
  - `self.board = np.array(board)`，强制 shape 校验 `(12,5)`；
  - `self.probMap = np.array(makeCompleteProbMap(probMap,posList)).T` → **14×25（转置）**；
  - 依 `isWin` 把样本加入全局 `winList` 或 `loseList`。
- 【事实】`train`（33-60）：外层 `totEpoch` 轮；每轮 shuffle 胜负表，取 `total_size = min(len(win),len(lose))`，按 `add(win,1)` / `add(lose,0)` **一胜一负配对**保证平衡；调用 `modelObj.train(...)`；每轮另存 `modelN.pkl` 并递增 `trainNum`。
- 【事实】`test`（62-86）：交替随机抽取胜负样本各半，调用 `modelObj.test(...)` 统计正负样本判对数量。

### 2.3 `mcts.py`（150 行）——「蒙特卡洛树搜索」接口

- 【事实】模块级（8-13）：`model = value_net.PolicyValueNet('model0.pkl')`（**导入即加载模型**）、`searchLayerNum=4`、`openMCTS=False`、`_n_qc=1`。
- 【事实】`TreeNode`（15-26）：字段 `parent/move/cMap/probTable/posList/isEne/layer/children/_n_visits=1`。
- 【事实】`estimation`（29-40）：叶子层（`layer==searchLayerNum`）才调用 NN：`probMap = help.copy2DList(probTable)`（**裸名 `probTable`，非 `self.probTable`**），`train.makeCompleteProbMap(...)`，`basic.caluChessNum(...)`，`asses.valueEstimation(self)`，`model.predict(...)` 得 `self.nnQ`，返回 `-self.nnQ`；非叶子层调用 `extend`。
- 【事实】`select`（43-47）：敌方层 `min(children, key=nnQ)`，我方层 `max(children, key=nnQ)` —— 极大极小选择，**未使用访问次数/UCB**。
- 【事实】`extend`（50-74）：遍历 12×5，对当前方棋子取 `getAccessibility`，对每个落点 `simulate.simMove` 生成子节点，`newNode.nnQ = -newNode.estimation(-beta,-alpha)`，带 `alpha>=beta` 剪枝。
- 【事实】`MCTS.__init__`（87-115）：通过前后棋子数变化推断吃子步数（`basic.eneBeatHand`/`usBeatHand`），重置 `basic.handNum` 与 `_n_qc`，创建根节点 `TreeNode(False, cMap, probTable, posList)`。
- 【事实】`get_best_move`（117-120）：`root.extend(-100000,100000)` 后 `root.select(False).move` 取 `(p1,p2)`。
- 【事实】`__main__`（124-150）：读 `input.ini`，解析三项棋盘数据，构造 MCTS，写 `output.ini`（oldi/oldj/newi/newj），并创建空文件 `finish` 作为完成信号。

### 2.4 `simulate.py`（51 行）——走子模拟

- 【事实】`simMove(node,x1,y1,x2,y2,isEne)`（5-51）：`x` 为列、`y` 为行（由 `cMap[y][x]` 索引可知）。
  - 目标为空（9-15）：移动棋子；若为敌方（隐藏子）走子，用 `eneSta.findChess` 更新该隐藏子位置；返回 `(cMap, True, posList)`。
  - 目标有子（16-51）：调用 `asses.ChessComparisons(...)`，`result==0` 防守方胜、`==1` 攻方胜、`==2` 同归于尽；按 `isEne` 分支更新 cMap 与 posList（死亡用 `eneSta.setDie` 置 `[-1,-1]`）；返回 `(cMap, False, posList)`。
- 【事实】返回的布尔 `isMove` 语义：`True` = **未吃子**（安静着法），`False` = 吃子；与 `basic.py:390-395` 中 `if isMove: count+=1 else: break #吃子了` 的磨棋判定一致。

### 2.5 `playout.py`（40 行）——外部快速走子接口

- 【事实】`tableToStr`（3-10）：把二维表转成单行字符串，行分隔符为 `nr`。
- 【事实】`_playout(node)`（17-40）：`subprocess.Popen('playout.exe', ...)`，依次写入 `node.isEne`、`cMap`、`probTable`、`posList`；循环读子进程输出，若行首为 `G` 则解析 4 个坐标，在 `node.children` 中按 `i.move` 匹配后返回子节点，否则抛异常「Can't find the desired child node」。
- 【事实】`playout.exe` 不在仓库中；`mcts.py:11` 有 `openMCTS=False`。
- 【推测】`playout.py:35` 的 `oldi,newi,_ = i.move` 与 `mcts.py:67` 的 `move=((i,j),(newi,newj),isMove)` 解包后 `oldi` 为元组，与解析出的整数坐标元组比较，是否能匹配存疑（取决于 playout.exe 输出坐标顺序），属潜在缺陷。

### 2.6 `basic.py`（418 行）——棋盘规则

- 【事实】编码约定（1-7）：我方 `1司令,2军长,3师长,4旅长,5团长,6营长,7连长,8排长,9工兵,10地雷,11炸弹,12军旗`；敌方 `13未知棋子,14敌方军旗`；`0` 为空。
- 【事实】地形判定（38-123）：山界前后、行营、大本营、铁路横纵线、工兵铁路等均以 `i*5+j` 的线性索引硬编码。
- 【事实】`getAccessibility`（174-302）：按前后左右 + 铁路滑行 + 行营斜向进出生成合法落点，区分我方/敌方与是否可移动（`IsEneMovingChess` 用概率表排除军旗/地雷，`basic.py:164-172`）。
- 【事实】棋子→概率表列索引常量（317-329）：`junqi=0, gongbing=1, paizhang=2, lianzhang=3, yingzhang=4, tuanzhang=5, lvzhang=6, shizhang=7, junzhang=8, siling=9, dilei=10, zhadan=11`。
- 【事实】`caluChessNum`（305-314）：统计双方棋子数。
- 【事实】`game_end`（352-418）：军旗被吃/棋子耗尽判胜；`_maxMoveNum=31`（349）步无吃子判「磨棋」，沿 `parent` 链回溯统计连续未吃子步数并判胜方。
- 【事实】`game_end:375` 使用 `node.probTable[junqi] == 1`，其中 `junqi=0` 是常量，即 `probTable[0]`（一个列表）与整数 `1` 比较，恒为 `False` —— 该「敌方军旗已确定」分支实际不会触发（潜在缺陷）。

### 2.7 `asses.py`（195 行）——规则评估与战斗裁决

- 【事实】`codeToStrength`（6-12）：炸弹按师长 strength，地雷按团长 strength。
- 【事实】`codeToStrength2`（14-34，注释 19.8.5 update）：`军旗=12, 炸弹/师长=22, 团长/地雷=18, 工兵=10, 排长=12, 连长=14, 营长=16, 旅长=20, 军长=24, 司令=30`；第 16 行注释称「军棋子力值应为0，在大本营的棋子-12」但代码返回 12（注释与实现不一致）。
- 【事实】`getChessStrength`（36-44）：对隐藏敌方子 `chess`，用 `Σ codeToStrength(i)*probTable[chess][i] / Σ probTable[chess][i]` 计算**期望子力**。
- 【事实】`isDetermine`（46-53）：若该隐藏子概率分布恰有一个非零项，返回其类型；否则 `-1`（未确定）。
- 【事实】`ChessComparisons`（55-84）：返回 `0/1/2`（实际敌方胜 / 实际我方胜 / 同归于尽）；包含工兵-地雷、炸弹-任意子同归于尽等特判；未确定时用期望子力比较。
- 【事实】`valueEstimation`（180-195）：返回 7 元组 `(ff1,...,ff7)`，对应 `asses.py:55` 注释 `局面评估7项`：子力、位置价值、机动价值、后三排护旗价值、相邻影响、越岭价值、吃敌方军旗 +1000。

### 2.8 `input.py`（59 行）——训练数据生成入口

- 【事实】`os.walk(r"D:/日记")` 遍历目录（6），按 `@` 拆分局内着法、`$` 拆分字段（12-44）；末段为胜负标记（18-20）。
- 【事实】每个局面字段：`[0]棋盘 [1]概率表 [2]坐标表 [3]双方子数 [4]回合数 [5]评估7项`（23-44），经 `inputHelp` 解析后构造 `train.situation(...)`（45）。
- 【事实】胜负标注（28-31）：**整局所有局面共享对局最终胜负标签**，无逐步回报折扣。
- 【事实】训练超参（52-59）：`epoch=2000`、`batch_size = winNum*2`、`totEpoch = int((winNum+loseNum)/batch_size)`，最后 `save_model('model0.pkl')`。
- 【事实】这是仓库中唯一实际的数据生成/训练入口；**没有真正的自对弈对局生成代码**。

### 2.9 `inputHelp.py`（40 行）——文本解析

- 【事实】`inputMap`（1-16）：按分隔符切 12 行×5 列；`isFirst` 控制首行偏移；把 `\x00` 视为 `0`。
- 【事实】`inputProb`（18-26）：切 25 行×12 列浮点（概率矩阵）。
- 【事实】`inputPos`（28-36）：切 25 行×2 列整数（隐藏子坐标）。
- 【事实】`inputRounds`（38-40）：取第一个整数为回合数。
- 【事实】`mcts.py:133-135` 用 `splitToken='-n'` 调用这三个函数，与 `input.ini` 中 `-n` 行分隔符一致。

### 2.10 `LossHistory.py`（42 行）——回调

- 【事实】继承 `keras.callbacks.Callback`，`on_batch_end`/`on_epoch_end` 记录 loss/acc/val_loss/val_acc（5-22），`loss_plot` 用 matplotlib 绘图（24-42）。
- 【事实】如 2.1 所述，`value_net.train` 创建它却未挂到 `model.fit` 的 callbacks，因此**训练时不会真正记录**。

### 2.11 `README.md`（87 行）

- 【事实】第 6 行：三層决策模型 = 规则暗棋推理 + 局面特征提取 + 神经网络局面评估 + 博弈树搜索；通过棋谱和自我对弈训练。
- 【事实】第 57-59 行：棋盘与概率矩阵拼接为 21×21 零填充；网络参考 AlphaGomoku（AlphaZero 小型化实现）；卷积「先扩大后缩小」再 Flatten 与一维特征拼接，强调规则特征的辅助作用；Sigmoid 输出胜率。
- 【事实】第 63 行：训练流程 = 未训练模型与其它 AI 对局 → 保存棋谱标注胜负 → 拆局面打标签 → 增量训练（新数据加入旧数据）→ 基于历史最佳模型 → 胜率达阈值后加入随机自对局混合训练。
- 【事实】第 72 行：「蒙特卡洛搜索模块的实现（当前未使用）」。

### 2.12 `input.ini`（GBK 文本，约 3125 字节）

- 【事实】结构为 `[main]` + 4 个键：`cMap`、`probTable`、`posList`、`handNum`。
- 【事实】`cMap` 为 12 行×5 列，`-n` 分隔，含 `13`（未知敌子）、`0`（空）及 `1-12` 我方子编码；`handNum=3`。
- 【事实】`probTable` 为 25 行×12 列浮点；绝大多数行为同一先验分布 `0.04,0.12,0.12,0.12,0.08×4,0.04,0.04,0.12,0.08`；其中一行（对应已交战目标）为 `0,0,...,0.285714,0.142857,0.142857,0.428571,0`（旅长/团长/营长/连长的后验）。
- 【事实】`posList` 为 25 行×2 列坐标，其中 `4 1`、`5 1..4` 等反映部分隐藏子已定位。

### 2.13 `test.py`（12 行）

- 【事实】加载 `model0.pkl` 并 `summary()`；构造全 `13` 的 cMap、全 `0.5` 的 25×12 概率表、全 0 的 posList，`probMap = train.makeCompleteProbMap(...)`（**未转置**），调用 `model.predict(cmap, probMap, 20, 49, 1, (100,)*7)`。
- 【事实】`myChessNum=49` 明显超出棋盘 60 格中我方可占的合理范围，且 `probMap` 方向与训练时的 `.T` 不一致（见 2.2）——仅作 predict 形状冒烟测试，非有效性测试。

### 2.14 `test2.py`（40 行）

- 【事实】`subprocess.Popen('playout.exe')`，写入随机 12×5 矩阵三次（行分隔符为 `-n`，与 `playout.py` 的 `nr` 不同），读取以 `G` 开头的响应，按 `line[3],line[4]` 与 `line[5],line[6]` 解析起止坐标后打印。

---

## 3. 重点问题回答

### 3.1 神经估值网络结构（层数/激活/输入/输出）

【事实】`value_net.py:53-83`：

- 输入：`board=(1,21,21)`（channels_first）+ `otherFeature=(10,)`。
- 卷积主干（全部 `kernel 3×3`、`padding=same`、`activation=relu`、L2=1e-4、channels_first）：
  1. `Conv2D(32)` (57-58)
  2. `MaxPooling2D(2×2)` (64) → 约 10×10
  3. `Conv2D(16)` (65-66)
  4. `Conv2D(4)` (67-68)
  5. `Conv2D(1)` (69-70)
  6. `MaxPooling2D(2×2)` (71) → 约 5×5 → `Flatten()` = 25 维 (74)
  - 另有被注释掉的 `BatchNormalization` 与 64/128 通道卷积层（59-63）。
- 估值头：`Lambda` 拼接 `25 + 10 = 35` 维（75，`output_shape=(35,)` 与注释/计算一致）→ `BatchNormalization`(76) → `Dense(16, relu)`(77) → `Dense(8, relu)`(78，注释说明「原来是线性层，改成 relu」) → `Dense(1, sigmoid)`(79)。
- 输出：单个 `[0,1]` 标量，即局面胜率估计。
- 编译：`Adam`、`binary_crossentropy`、指标 `["acc", Recall]`（83）。
- L2 正则系数 `1e-4`（45），作用于所有 Dense/Conv 层。
- 早停 patience=70、学习率衰减 `ReduceLROnPlateau(factor=0.7, patience=5)`（37-41）。

【关键事实】类名 `PolicyValueNet` 具有误导性：**源码只有 value head，没有任何 policy head，也不输出着法概率分布**（对比 AlphaZero 的 (p, v) 双头）。它是「穷举走法 + 神经网络只做叶子估值」的架构。

### 3.2 概率矩阵如何表示棋子身份

【事实】综合 `basic.py:317-329`、`inputHelp.py:18-26`、`asses.py:36-53`：

- `probTable` 形状 **25×12**。25 行对应一方的 25 个（隐藏）棋子的逻辑编号；12 列对应 12 种棋子类型，列索引常量为 `junqi=0, gongbing=1, paizhang=2, lianzhang=3, yingzhang=4, tuanzhang=5, lvzhang=6, shizhang=7, junzhang=8, siling=9, dilei=10, zhadan=11`。
- 每行是一个概率分布（示例 `input.ini` 中先验行 `[0.04,0.12,0.12,0.12,0.08,0.08,0.08,0.08,0.04,0.04,0.12,0.08]`，总和为 1；交战后出现的后验行 `[0,...,0.285714,0.142857,0.142857,0.428571,0]`）。
- `posList`（25×2）记录每个隐藏棋子在 12×5 棋盘上的位置；`eneSta.findChess(x,y,posList)` 反向查「某坐标上是 25 个隐藏子中的哪一个」，`setDie` 用 `[-1,-1]` 标记阵亡。
- `asses.isDetermine` 把「某一行只有一个非零概率」解释为身份已确定；`asses.getChessStrength` 用期望子力表达未确定身份。
- `train.makeCompleteProbMap` 把 `posList[i]` 的两个坐标追加到第 i 行，使每行变成「12 类概率 + 2 个位置坐标」= 14 列；随后 `train.situation` 转置成 14×25。

【事实/缺陷线索】`value_net.toModelBoard` 把 12×5 棋盘（60）与 **14×25 概率图（350）** 展平拼接，共 410 个有效值，零填充到 21×21=441。即 21×21 并非棋盘尺寸，而是「棋盘 + 概率图」的容器，`value_net.py:14` 注释「传入的probMap视为转置完的」与此吻合。

### 3.3 局面特征如何编码

【事实】最终送入网络的是两路输入：

1. **21×21 单通道张量**（`value_net.py:14-27`, `54`）：
   - 前 60 个位置：`cMap` 按行展平（12×5），编码见 2.6；
   - 接下来 350 个位置：`probMap`（14×25，由 25×(12类概率+2坐标) 转置而来）展平；
   - 剩余 31 个位置补 0。
2. **10 维一维向量**（`value_net.py:55`, `92-94`）：`[handNum, myChessNum, eneChessNum] + [ff1..ff7]`，其中 `ff1..ff7` 来自 `asses.valueEstimation`（2.7）。

【事实】7 项手工特征的计算（asses.py:180-195）依赖：`codeToStrength2` 子力表、`valueLocation` 位置分（铁路 5 / 大本营 -12 / 我方行营 8 / 敌方行营 10 / 其他 4，`asses.py:113-123`）、`valueMotivation`（子力/4，工兵/9，`asses.py:125-129`）、`valuelast3line`（15/到军旗步数，`asses.py:137-141`）、`valueNear`（相邻敌我最大子力影响，`asses.py:156-178`）、`valuecrosshill`（越岭价值，`asses.py:148-154`）、`ff7`（敌方军旗确定阵亡 +1000，`asses.py:186-188`）。

### 3.4 自我对弈（self-play）如何实现

【结论：源码层面未实现真正的 self-play 对局生成。】

- 【事实】唯一的数据生成入口 `input.py` 是**读取已经存在的棋谱/日记文件**（`D:/日记`），并按对局胜负给所有局面打标签（2.8）。它不驱动任何对局，也不生成新棋谱。
- 【事实】`playout.py` / `test2.py` 调用的是外部 `playout.exe`（不在仓库内），`mcts.py:11` 明确 `openMCTS=False`，README:72 也写明「蒙特卡洛搜索模块当前未使用」。
- 【事实】README:63 描述的「胜率阈值后随机自对局混合训练（对手随机选其它 AI 或历史模型）」在 Python 源码中**找不到对应实现**；属于【未实现】的设计描述（或实现在仓库外的其它 Gitee 项目中）。
- 【推测】完整系统应是「外部对局工具 ↔ INI 文件 ↔ 本仓库 MCTS 接口」的拼接式架构：外部程序写 `input.ini`，Python 算出着法写 `output.ini` 并创建 `finish`，对局结束后另由外部工具保存棋谱，再由 `input.py` 批量转成训练样本。此流程可由 `mcts.py:124-150`、`input.py:6-45` 与 `chess.exe` 的存在佐证，但仓库内无端到端脚本。

### 3.5 训练策略（损失/优化器/学习率/迭代）

【事实】

- 损失：`binary_crossentropy`（`value_net.py:83`）；优化器：`Adam`（默认学习率，未显式设定）；监控 `val_loss`，`validation_split=0.3`（`value_net.py:89`）。
- 正则：所有权重的 L2=1e-4（45、58、66、68、70、77-79）。
- 回调：`EarlyStopping(patience=70)`、`ReduceLROnPlateau(factor=0.7, patience=5)`（37-41）。
- 迭代（`input.py:52-59`）：内层 `epoch=2000`；外层 `totEpoch = int((winNum+loseNum)/batch_size)`，`batch_size = winNum*2`；每轮外层调用一次 2000-epoch 的 `fit` 并保存一个 `modelN.pkl`。
- 采样（`train.py:33-56`）：胜负样本各取 `min(win,lose)` 个并一一配对，保证 1:1 平衡（README:65「解决数据不平衡问题 待完善」——README 自认该节未完成）。
- 增量训练：README:63 描述「新数据加入旧数据、基于历史最佳模型继续训练」；源码中 `train.situation` 持续向全局列表追加样本，外层循环反复 `fit`，可视为增量训练的粗略实现。
- 指标：`acc` 与自定义 `Recall`（30-35）。

【事实/已知缺陷】`value_net.py:87` 注释：`fix:目前所有胜利的局面值都为1，实际应当根据Q值更新公式给予远距离的局面一些折扣？` —— 作者明确指出**回报未做时间折扣**是待修复问题（与 2.8 的全局同标签对应）。

### 3.6 MCTS 如何与神经网络结合

【结论：名为 MCTS，实为「固定深度 4 层的极大极小 + alpha-beta 剪枝 + 神经网络叶子估值」。】

- 【事实】`mcts.py:29-40`：搜索到 `searchLayerNum=4` 层时，用 `asses.valueEstimation` 抽取 7 项规则特征 + 棋子数 + 手数，连同棋盘/概率图送入 `model.predict` 得到 `nnQ`（胜率）；返回 `-nnQ` 以配合 negamax 符号翻转。
- 【事实】`mcts.py:50-74`：非叶子节点完全展开（`for 12×5`），用 `simulate.simMove` 走子生成子节点，递归估值 `newNode.nnQ = -newNode.estimation(-beta,-alpha)`，并用 `alpha>=beta` 剪枝。
- 【事实】`mcts.py:43-47`：节点选择只按 `nnQ`（敌方 min / 我方 max），**没有 UCT/UCB 公式、没有访问次数驱动的探索**；`_n_qc=1` 与 `openMCTS=False`（11-13）说明 Monte-Carlo 部分未启用。
- 【事实】`TreeNode._n_visits` 被初始化但从未递增使用（26）。
- 【推测】`nnQ` 的符号约定：网络统一输出「对我方有利的胜率」，叶子返回 `-nnQ` 是为了在父节点以 `-estimate` 调用时负负得正（代码 38 行注释「负负得正」），从而与 min/max 层选择保持一致。
- 【事实/缺陷线索】`mcts.py:32` 在 `estimation` 中使用裸名 `probTable` 而非 `self.probTable`；当以 `python mcts.py` 运行时该名解析到 `__main__` 块（132-135）赋值的模块级变量（即 `input.ini` 读入的**根节点**概率表），导致所有叶子估值可能共享根节点概率表而非各自节点的概率表。

---

## 4. 测试用例与已知问题

### 4.1 测试用例

| 文件 | 内容 | 性质 |
|---|---|---|
| `test.py:1-12` | 加载 `model0.pkl`，打印 `summary()`，用全 13 棋盘 + 全 0.5 概率表调用 `predict(20, 49, 1, (100,)*7)` | predict 冒烟测试；含 `myChessNum=49` 与 `probMap` 未转置等不合理输入 |
| `test2.py:1-40` | 启动 `playout.exe`，发送随机 12×5 矩阵三次，解析 `G` 响应坐标 | 外部进程接口测试；依赖仓库外的 `playout.exe`；分隔符 `-n` 与 `playout.py` 的 `nr` 不一致 |

【事实】仓库中无自动化测试框架（pytest/unittest）、无断言、无 CI 配置；两者都是手工执行脚本。

### 4.2 已知问题 / 局限（均以源码或 README 为依据）

1. 【事实】无 LICENSE，法律权属不明（见 §1.2）。
2. 【事实】无 `model0.pkl`、`playout.exe`，`mcts.py`/`test.py`/`playout.py` 开箱即失败。
3. 【事实】`value_net.py:87` 自认：所有胜局标签为 1，未做 Q 值/时间折扣。
4. 【事实】README:65-67「解决数据不平衡问题：待完善」、README:8-10「暗棋推理：待完善」——核心章节未完成。
5. 【事实】`value_net.py:88-89` 创建 `LossHistory` 却未挂入 callbacks，loss 记录失效。
6. 【事实】类名 `PolicyValueNet` 无 policy 头；与 README 所述 AlphaZero 风格存在落差（README 只说输出胜率，未承诺 policy，但类名易误导）。
7. 【事实】`mcts.py:11` `openMCTS=False`、README:72「蒙特卡洛模块当前未使用」——所谓 MCTS 实际未做随机模拟/UCB。
8. 【事实】`mcts.py:32` 疑似使用根节点概率表（裸名 `probTable`）。
9. 【事实】`basic.py:375` `probTable[junqi] == 1` 列表与整数比较恒假，军旗确定判胜分支失效。
10. 【事实】`asses.py:16` 注释称军旗子力应为 0/大本营 -12，但 `codeToStrength2` 返回 12。
11. 【事实】`asses.py:4` 全局 `eneMax` 被 `valueNear` 与 `valuecrosshill` 共享并覆盖（`asses.py:158-159`、`148-154`），存在跨调用状态污染风险。
12. 【事实】`test.py:10` 概率图未转置，与训练/推理路径不一致；`myChessNum=49` 异常。
13. 【事实】`playout.py` 与 `test2.py` 的行分隔符（`nr` vs `-n`）及坐标解析方式不一致，互操作性存疑。
14. 【事实】旧版 Keras API，缺少依赖版本声明，现代环境难以直接复现。
15. 【推测】21×21 拼接张量中大量零填充与「棋盘 60 + 概率图 350」的非均匀布局，可能不利于卷积学习空间局部性（属设计评价，非源码缺陷）。

---

## 5. 可借鉴算法思路（中文描述；仅思路，不复制代码）

> 以下均为对技术思想的抽象概括，不涉及本仓库具体代码复制。

1. **不完全信息概率化表示**：把每个隐藏敌方棋子建模为「对 12 种身份的概率分布 + 其在棋盘上的位置」，并随交战信息更新后验。这种「概率身份表 + 位置表」的双表结构，是把不完全信息博弈转化为可学习输入的一种实用编码方式。

2. **概率期望子力战斗裁决**：当敌方身份未确定时，不采样单一身份，而是用各身份子力的概率加权期望值参与大小比较，从而让战斗结果可微/可预期，减少随机性；当身份唯一确定时退化为确定比较。可借鉴到任何「带隐藏信息的对抗推演」中。

3. **规则特征 + 神经网络的混合估值**：先用手工规则抽取若干有明确博弈含义的标量特征（子力、位置、机动、护旗、相邻威胁、越岭、军旗状态），再让卷积分支处理棋盘/概率图的空间模式，最后在拼接层融合。卷积分支「先扩大通道再压缩到很小特征图」的做法，可避免空间输入在全连接层淹没规则特征，强调规则的辅助作用。

4. **固定深度搜索 + 神经叶子评估**：不追求 MCTS 的随机模拟，而是把博弈树展开到固定层数，叶子用学习到的估值网络打分，配合 alpha-beta 剪枝和 negamax 符号翻转。这在状态空间大、难以做充分随机模拟的博弈中，是一种「用学习估值替代手工评估函数」的低成本改造路径。

5. **Negamax 符号约定**：网络统一输出「当前视角对我方有利的胜率」，在父子节点传递时通过取负实现极大/极小交替，可简化双视角实现。

6. **胜负样本 1:1 平衡采样**：胜负局长度往往不同，训练时按 `min(胜局数, 负局数)` 各取等量样本配对，可缓解类别不平衡导致的偏置。

7. **增量/课程式训练**：新对局数据加入历史数据、基于历史最佳模型继续训练、胜率达阈值后引入更强/随机对手混合训练。这一「逐步加难度、保留历史数据防振荡」的思想具有普适性（README 引用了 ordered incremental training 相关文献）。

8. **磨棋（长将/无进展）判胜机制**：记录最近一次吃子的手数，若连续若干步无吃子则沿搜索树父链回溯，判定「磨棋」责任方。这是从棋规层面解决评估函数难以判断「谁在消极拖延」的工程技巧。

9. **INI 文件 + 完成信号文件的进程间接口**：与外部 C++ 对局程序通过文本 INI 交换局面和着法，用空文件 `finish` 作完成标志。这是异构系统（Python AI ↔ 对局引擎）松耦合集成的一种简易做法。

10. **对称奖励设计的反思**：该项目自认「所有胜局标签同为 1、未做时间折扣」是缺陷。可借鉴的教训是：对长序列决策，应把终局回报按步数折扣分配到早期局面（类似 TD / Monte-Carlo return 的折扣思想），否则早期局面难以学到「如何走向胜利」。

---

## 6. 结论

- 该项目是 2020 年的单提交研究性原型，把「概率化暗棋推理 + 手工特征 + 小型卷积估值网络 + 固定深度极大极小搜索」组合成四国军棋 AI，并配有与外部对局引擎对接的接口；配套论文发表于 CCDC2020。
- 源码与 README 存在多处不一致与未完成项（真实 self-play 未实现、MCTS 名不副实、数据不平衡章节待完善、多个确定性缺陷、缺关键模型/可执行文件、旧版 Keras 依赖）。
- **最重要的是：仓库无许可证，法律权属不明。对上述内容只能参考技术思路，不复制任何代码；任何借鉴都必须在独立实现的前提下进行，并保留本报告的约束声明。**

---

## 附：本次实际打开并阅读的文件清单

`value_net.py`、`train.py`、`mcts.py`、`simulate.py`、`playout.py`、`basic.py`、`asses.py`、`input.py`、`inputHelp.py`、`LossHistory.py`、`test.py`、`test2.py`、`README.md`、`input.ini`（以 GBK 解码读取），另补充阅读 `help.py`、`eneSta.py` 以厘清依赖。未改动 workspace 下任何源码文件。
