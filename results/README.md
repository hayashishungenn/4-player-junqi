# 评测环境重建与复评运行说明

## 背景
原 `junqi-train-venv` 的 site-packages 二进制模块（torch 扩展 / lib dll 等）在一次磁盘清理中被清空，
仅剩源码目录。评测改用 base Python + 独立依赖目录，不依赖易失的 venv。

## 依赖版本（已实测，来自 `torch 2.10.0+cu128` 训练环境）
- Python 3.12.12（uv 管理的 base：`%APPDATA%\uv\python\cpython-3.12.12-windows-x86_64-none`）
- torch 2.10.0+cu128（CUDA 12.8，RTX 5070 Ti Laptop，compute capability 12.0）
- numpy 2.5.5 / numba 0.68.1 / llvmlite 0.50.0
- gymnasium 1.4.0 / pettingzoo 1.27.0 / onnx 1.23.2 / ml_dtypes 0.7.0

## 重建依赖（若当前环境缺失）
```powershell
$base = "$env:APPDATA\uv\python\cpython-3.12.12-windows-x86_64-none\python.exe"
$dep  = "$env:TEMP\junqi-eval-venv\site-deps"
$env:HTTP_PROXY=''; $env:HTTPS_PROXY=''; $env:ALL_PROXY=''
& $base -m pip install --target $dep `
  "torch==2.10.0" --index-url https://download.pytorch.org/whl/cu128
& $base -m pip install --target $dep `
  numpy==2.5.5 numba==0.68.1 llvmlite==0.50.0 gymnasium==1.4.0 `
  pettingzoo==1.27.0 onnx==1.23.2 ml_dtypes==0.7.0
```

## 运行复评（配对、固定种子、逐局 JSONL）
```powershell
$base = "$env:APPDATA\uv\python\cpython-3.12.12-windows-x86_64-none\python.exe"
$dep  = "$env:TEMP\junqi-eval-venv\site-deps"
$env:PYTHONPATH = "$dep;D:\4-player-junqi"
$env:OMP_NUM_THREADS = '1'
& $base D:\4-player-junqi\eval_tournament.py `
  --candidates junqi_best_iter240.pt junqi_pool20_iter248.pt junqi_iter688.pt `
  --games 100 --seed-base 90000 `
  --out D:\4-player-junqi\results\tournament.jsonl --replay
```

## 复现性验证（已实测）
- 同一 `--seed-base` 重跑，逐局核心字段（seed / 座位 / winner / 终局原因 / 步数 / 布局哈希）**完全一致**。
- 种子控制：`random.seed(seed)` + `np.random.seed(seed)` 后再 `env.reset()`，布局可复现
  （因为 `JunqiSelfPlayEnv.reset()` 用全局 `random` 生成布阵且无 seed 参数）。
- 模型加载：`evaluate_tournament.py` 的 `HERE` 路径导入外层 `train_junqi_5070ti.py`（评测实际实现），
  已核实 `T.__file__ = D:\4-player-junqi\train_junqi_5070ti.py`；`code/siguo-junqi` 无此脚本副本。
