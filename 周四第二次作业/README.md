# 【周四第二次作业】GeluKernel —— GELU 算子核函数工程（初步代码）

## 一、赛题来源与要求

来源：CANNJudge 开放题库 `s2/gelukernel`（算子核函数工程 beta，CANN 9.0.0，vector 模式）

实现 GELU（高斯误差线性单元）激活函数算子：

- **数学定义**：`GELU(x) = x × Φ(x) = x × 0.5 × (1 + erf(x / √2))`
- **输入**：张量 `(..., N)`，`N ∈ [1, 10240]`，任意多维；仅支持 `float16` / `float32`
- **非对齐场景**：`N` 可能为非 32 的整倍数
- **输出**：与输入同形状、同数据类型
- **精度要求**：
  - `float32`：相对误差 < 1e-4，绝对误差 < 1e-4
  - `float16`：相对误差 < 1e-3，绝对误差 < 1e-3

## 二、实现思路（gelu_kernel.cpp）

采用标准 AscendC 向量算子三段式（CopyIn → Compute → CopyOut）+ 双缓冲。

### 1. erf 的高精度近似

AscendC 向量指令没有直接 erf，采用 Abramowitz-Stegun 7.1.26 有理近似
（最大绝对误差约 1.5e-7，远优于 fp32 1e-4 / fp16 1e-3 的要求）：

```
erf(u) ≈ 1 - (a1·t + a2·t² + a3·t³ + a4·t⁴ + a5·t⁵) · exp(-u²)
t = 1 / (1 + p·u)
a1=0.254829592  a2=-0.284496736  a3=1.421413741  a4=-1.453152027  a5=1.061405429  p=0.3275911
```

### 2. 用对称性消去符号分支

`x·erf(x/√2) = |x|·erf(|x|/√2)`，于是：

```
GELU(x) = 0.5·(x + |x|) - 0.5·|x|·f
f = (a1·t + ... + a5·t⁵)·exp(-u²)，u = |x|/√2
```

全程无 if 分支、无符号判断，向量化友好；`x=0`、大正/大负值均自然正确。

### 3. float16 提升为 float32 计算

`half` 输入先 `Cast` 成 `float32` 计算，结果 `CAST_RINT` 舍入回 `half`，保证 fp16 精度。

### 4. 非对齐（尾部）处理

按块（`BLOCK_LEN=256` 元素）分块；尾部块按实际剩余元素数 `DataCopy` 搬运，
兼容 `N` 非 32 整倍数场景。多核按 `blockDim` 均分元素区间，每个核处理
`[coreStart, coreStart+coreCount)` 一段。

### 5. 入口与 tiling

```cpp
extern "C" __global__ __aicore__ void gelu_kernel(GM_ADDR x, GM_ADDR y,
                                                  GM_ADDR workspace, GM_ADDR tiling);
```

`tiling` 为 `GeluTiling{totalLength, blockDim, dtype}`，由 host 下发。
> 若判题平台提供的 npu_kernel_dev 模板入口签名不同（如参数顺序、是否含 tiling），
> 只需按平台模板调整入口与 Init 的参数传递，Compute 内计算逻辑无需改动。

## 三、目录结构

```
周四第二次作业/
├── gelu_kernel.cpp   # AscendC 核函数实现（float16/float32、双缓冲、非对齐）
├── verify_gelu.py    # 本地精度验证脚本（numpy，模拟核函数计算路径）
└── README.md         # 本说明
```

## 四、本地验证

依赖：Python 3 + numpy（无需 CANN 环境即可验证数学与精度路径）

```bash
python verify_gelu.py
```

验证内容：
- 赛题三个示例（对照高精度 erf 参考值；示例表为 4 位小数展示，示例3 表格数值与
  严格 erf-GELU 略有出入，属页面文案，以判题数值比对为准）
- 随机测试：1/2/3/4 维、`N=1/33/100/999/10240`（含非 32 对齐）、`[-6,6]` 与边界大值
- 精度统计：fp32 最大绝对误差 ~3e-7（阈值 1e-4）；fp16 最大绝对误差 ~9.8e-4（阈值 1e-3）

实测结果（本机）：

```
[fp32 (10240,)] max_abs=3.299e-07  fail=0/10240
[fp16 (10240,)] max_abs=9.763e-04  fail=0/10240
全部用例通过 ✔
```

## 五、在 CANN 环境构建（参考）

在昇腾 NPU 环境（安装 CANN 9.0.0）中，按标准算子工程编译：

```bash
# 方式一：msOpGen 生成工程后替换 op_kernel 目录中的核函数实现
msopgen gen -i gelu.json -c ai_core-<soc> -out ./gelu_impl
# 方式二：Kernel Launch 直接编译核函数（关键宏示例）
g++ --std=c++17 -D__CCE_KT_TEST__ -I $ASCEND_HOME/include ...
```

> 本仓库为“初步代码”：先保证数学正确、结构清晰、可读可维护；
> 后续可按判题反馈优化 tiling 粒度、指令吞吐（如合并 Horner 为 FMA、
> 增大块长减少搬运次数等）。

## 六、提交信息

- 作业标注：**周四第二次作业**
- 仓库：GitCode `DianaCheng/f25011102`（本目录 `周四第二次作业/`）
