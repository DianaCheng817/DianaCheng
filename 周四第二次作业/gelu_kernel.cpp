/**
 * @file gelu_kernel.cpp
 * @brief GeluKernel —— GELU 激活函数算子核函数工程（AscendC / CANN 9.0.0，vector 模式）
 *
 * 【周四第二次作业】GeluKernel 算子赛题
 *
 * 数学定义：
 *   GELU(x) = x * Phi(x) = x * 0.5 * (1 + erf(x / sqrt(2)))
 *
 * 输入约束：
 *   - 输入张量形状 (..., N)，N ∈ [1, 10240]，任意多维，仅支持 float16 / float32
 *   - N 可能为非 32 的整倍数（内存非对齐场景）
 *   - 输出与输入形状、数据类型一致
 *
 * 精度要求：
 *   - float32：相对误差 < 1e-4，绝对误差 < 1e-4
 *   - float16：相对误差 < 1e-3，绝对误差 < 1e-3
 *
 * 实现要点：
 *   1. erf 采用 Abramowitz-Stegun 7.1.26 有理近似（最大绝对误差 ~1.5e-7，
 *      远优于 fp32 的 1e-4 与 fp16 的 1e-3 精度要求）：
 *        erf(u) ≈ 1 - (a1*t + a2*t^2 + a3*t^3 + a4*t^4 + a5*t^5) * exp(-u^2)
 *        t = 1 / (1 + p*u)
 *        a1=0.254829592  a2=-0.284496736  a3=1.421413741
 *        a4=-1.453152027 a5=1.061405429   p=0.3275911
 *   2. 利用对称性去掉符号分支：
 *        x * erf(x/sqrt2) = |x| * erf(|x|/sqrt2)
 *        GELU(x) = 0.5*(x + |x|) - 0.5*|x|*f
 *        其中 f = (a1*t + ... + a5*t^5) * exp(-u^2)，u = |x|/sqrt(2)
 *   3. float16 输入先提升为 float32 计算，结果再转回 float16，保证精度。
 *   4. 数据分块（双缓冲）+ 尾部块按实际元素数搬运，兼容非 32 对齐场景。
 */

#include "kernel_operator.h"
#include <type_traits>

using namespace AscendC;

constexpr int32_t BUFFER_NUM = 2;    // 双缓冲
constexpr int32_t BLOCK_LEN = 256;   // 每个 tile 的元素个数（32B 对齐：fp32=8 个/块，256=32 块）

// GELU 系数
constexpr float SQRT2_INV = 0.7071067811865476f;   // 1/sqrt(2)
constexpr float P_COEF = 0.3275911f;               // erf 近似参数 p
constexpr float A1 = 0.254829592f;
constexpr float A2 = -0.284496736f;
constexpr float A3 = 1.421413741f;
constexpr float A4 = -1.453152027f;
constexpr float A5 = 1.061405429f;

// 由 host 侧通过 tiling GM 下发的参数
struct GeluTiling {
    int32_t totalLength;  // 张量总元素数
    int32_t blockDim;     // 使用的核数
    int32_t dtype;        // 0=float32，1=float16
};

template <typename T>
class KernelGelu {
public:
    __aicore__ inline KernelGelu() {}

    __aicore__ inline void Init(GM_ADDR x, GM_ADDR y, int32_t coreStart, int32_t coreCount)
    {
        // 本核负责 [coreStart, coreStart + coreCount) 个元素
        this->coreStart = coreStart;
        this->coreCount = coreCount;
        this->tileNum = (coreCount + BLOCK_LEN - 1) / BLOCK_LEN;

        xGm.SetGlobalBuffer((__gm__ T *)x, coreStart + coreCount);
        yGm.SetGlobalBuffer((__gm__ T *)y, coreStart + coreCount);

        // 输入/输出队列（类型 T：half 或 float）
        pipe.InitBuffer(inQueue, BUFFER_NUM, BLOCK_LEN * sizeof(T));
        pipe.InitBuffer(outQueue, BUFFER_NUM, BLOCK_LEN * sizeof(T));

        // float32 计算工作区
        pipe.InitBuffer(xfBuf, BLOCK_LEN * sizeof(float));   // 提升后的输入 x
        pipe.InitBuffer(zBuf, BLOCK_LEN * sizeof(float));    // z = x/sqrt2
        pipe.InitBuffer(uBuf, BLOCK_LEN * sizeof(float));    // |z|
        pipe.InitBuffer(bBuf, BLOCK_LEN * sizeof(float));    // 1 + p*u
        pipe.InitBuffer(tBuf, BLOCK_LEN * sizeof(float));    // t = 1/(1+p*u)
        pipe.InitBuffer(pBuf, BLOCK_LEN * sizeof(float));    // Horner 多项式
        pipe.InitBuffer(eBuf, BLOCK_LEN * sizeof(float));    // exp(-u^2)
        pipe.InitBuffer(gBuf, BLOCK_LEN * sizeof(float));    // 通用中间量
        pipe.InitBuffer(fBuf, BLOCK_LEN * sizeof(float));    // f = q*e / 输出
        pipe.InitBuffer(xaBuf, BLOCK_LEN * sizeof(float));   // |x|
    }

    __aicore__ inline void Process()
    {
        for (int32_t i = 0; i < tileNum; i++) {
            CopyIn(i);
            Compute(i);
            CopyOut(i);
        }
    }

private:
    // 本 tile 的实际元素个数（尾部可能不足 BLOCK_LEN）
    __aicore__ inline int32_t TileLen(int32_t progress) const
    {
        int32_t remain = coreCount - progress * BLOCK_LEN;
        return remain > BLOCK_LEN ? BLOCK_LEN : remain;
    }

    __aicore__ inline void CopyIn(int32_t progress)
    {
        LocalTensor<T> inLocal = inQueue.AllocTensor<T>();
        int32_t offset = coreStart + progress * BLOCK_LEN;
        int32_t len = TileLen(progress);
        // 按元素数拷贝，兼容尾部非 32 对齐
        DataCopy(inLocal, xGm[offset], len);
        inQueue.EnQue(inLocal);
    }

    __aicore__ inline void Compute(int32_t progress)
    {
        LocalTensor<T> inLocal = inQueue.DeQue<T>();
        LocalTensor<T> outLocal = outQueue.AllocTensor<T>();

        LocalTensor<float> xf = xfBuf.Get<float>();
        LocalTensor<float> z = zBuf.Get<float>();
        LocalTensor<float> u = uBuf.Get<float>();
        LocalTensor<float> b = bBuf.Get<float>();
        LocalTensor<float> t = tBuf.Get<float>();
        LocalTensor<float> p = pBuf.Get<float>();
        LocalTensor<float> e = eBuf.Get<float>();
        LocalTensor<float> g = gBuf.Get<float>();
        LocalTensor<float> f = fBuf.Get<float>();
        LocalTensor<float> xa = xaBuf.Get<float>();

        // 1) x -> float32（half 提升精度；float 直接搬入）
        if constexpr (std::is_same_v<T, half>) {
            Cast(xf, inLocal, RoundMode::CAST_NONE);
        } else {
            DataCopy(xf, inLocal, BLOCK_LEN);
        }

        // 2) z = x / sqrt(2)
        Muls(z, xf, SQRT2_INV);

        // 3) u = |z|
        Abs(u, z);

        // 4) b = 1 + p*u ; t = 1/b
        Muls(b, u, P_COEF);
        Adds(b, b, 1.0f);
        Rec(t, b);

        // 5) Horner 求 q = a1*t + a2*t^2 + a3*t^3 + a4*t^4 + a5*t^5
        //    q = t*(a5*t^4 + a4*t^3 + a3*t^2 + a2*t + a1)，从高次项往低次迭代
        Duplicate(p, A5);
        Mul(z, p, t);    Adds(p, z, A4);
        Mul(z, p, t);    Adds(p, z, A3);
        Mul(z, p, t);    Adds(p, z, A2);
        Mul(z, p, t);    Adds(p, z, A1);
        Mul(z, p, t);    // z = q = poly * t

        // 6) e = exp(-u^2)
        Mul(e, u, u);
        Muls(e, e, -1.0f);
        Exp(g, e);
        DataCopy(e, g, BLOCK_LEN);   // e = exp(-u^2)

        // 7) f = q * e
        Mul(f, z, e);

        // 8) xa = |x|
        Abs(xa, xf);

        // 9) GELU(x) = 0.5*(x + |x|) - 0.5*|x|*f
        Add(e, xf, xa);      // 复用 e：x + |x|
        Muls(e, e, 0.5f);    // t1 = 0.5*(x + |x|)
        Muls(u, xa, 0.5f);   // 复用 u：0.5*|x|
        Mul(z, u, f);        // t2 = 0.5*|x|*f
        Sub(f, e, z);        // y

        // 10) 写回输出（float -> half 需舍入）
        if constexpr (std::is_same_v<T, half>) {
            Cast(outLocal, f, RoundMode::CAST_RINT);
        } else {
            DataCopy(outLocal, f, BLOCK_LEN);
        }

        outQueue.EnQue(outLocal);
        inQueue.FreeTensor(inLocal);
    }

    __aicore__ inline void CopyOut(int32_t progress)
    {
        LocalTensor<T> outLocal = outQueue.DeQue<T>();
        int32_t offset = coreStart + progress * BLOCK_LEN;
        int32_t len = TileLen(progress);
        DataCopy(yGm[offset], outLocal, len);
        outQueue.FreeTensor(outLocal);
    }

private:
    TPipe pipe;
    TQue<QuePosition::VECIN, BUFFER_NUM> inQueue;
    TQue<QuePosition::VECOUT, BUFFER_NUM> outQueue;
    GlobalTensor<T> xGm, yGm;
    TBuf<TPosition::VECCALC> xfBuf, zBuf, uBuf, bBuf, tBuf, pBuf, eBuf, gBuf, fBuf, xaBuf;
    int32_t coreStart = 0;
    int32_t coreCount = 0;
    int32_t tileNum = 0;
};

/**
 * @brief GELU 算子入口：读取 tiling，将 totalLength 个元素均分到 blockDim 个核上
 * @param x 输入张量 GM 地址
 * @param y 输出张量 GM 地址
 * @param workspace 工作区（本实现未使用）
 * @param tiling tiling 参数 GM 地址（GeluTiling）
 */
extern "C" __global__ __aicore__ void gelu_kernel(GM_ADDR x, GM_ADDR y,
                                                  GM_ADDR workspace, GM_ADDR tiling)
{
    GeluTiling t = *(GeluTiling *)tiling;
    int32_t blockDim = t.blockDim > 0 ? t.blockDim : 1;
    int32_t blockIdx = GetBlockIdx();

    // 每个核负责的元素区间（张量按一维展开处理）
    int32_t perCore = (t.totalLength + blockDim - 1) / blockDim;
    int32_t coreStart = blockIdx * perCore;
    int32_t coreCount = (coreStart + perCore) > t.totalLength ? (t.totalLength - coreStart)
                                                              : perCore;
    if (coreCount <= 0) {
        return;
    }

    if (t.dtype == 1) {
        KernelGelu<half> op;
        op.Init(x, y, coreStart, coreCount);
        op.Process();
    } else {
        KernelGelu<float> op;
        op.Init(x, y, coreStart, coreCount);
        op.Process();
    }
}
