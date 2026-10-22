#!/usr/bin/env python3
"""Fused W8A16 GEMM for engine b on the 16 GB card: y = bf16( (x_bf16 @ codes^T in fp32) * s_w ).

codes: the e4m3 weight codes [N, K] of the vendored FP8Linear (row-major); every e4m3 value is exactly representable
in bf16, so converting a code tile to bf16 in registers is exact and each product x * code is exact in fp32 (8-bit x
4-bit significands). tl.dot accumulates in fp32. This is the same math as torch.mm(x, codes.bf16().T,
out_dtype=float32) * s_w with one final rounding; only the fp32 summation order differs (validated against it and
against an fp64 reference before use). It reads 1 byte per weight instead of casting the whole matrix to bf16 per call.
"""

from __future__ import annotations

import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 64, "BLOCK_K": 256}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 16, "BLOCK_N": 32, "BLOCK_K": 256}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 32, "BLOCK_N": 64, "BLOCK_K": 128}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64}, num_warps=8, num_stages=3),
    ],
    key=["M_BUCKET", "N", "K"],
)
@triton.jit
def _w8a16_kernel(x_ptr, w_ptr, s_ptr, y_ptr, M, N, K, M_BUCKET,
                  stride_xm, stride_xk, stride_wn, stride_wk, stride_ym, stride_yn,
                  BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    rk = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k0 in range(0, K, BLOCK_K):
        kk = k0 + rk
        a = tl.load(x_ptr + rm[:, None] * stride_xm + kk[None, :] * stride_xk,
                    mask=(rm[:, None] < M) & (kk[None, :] < K), other=0.0)
        b = tl.load(w_ptr + rn[None, :] * stride_wn + kk[:, None] * stride_wk,
                    mask=(rn[None, :] < N) & (kk[:, None] < K), other=0.0)
        acc = tl.dot(a, b.to(tl.bfloat16), acc, out_dtype=tl.float32)
    s = tl.load(s_ptr + rn, mask=rn < N, other=0.0)
    acc = acc * s[None, :]
    tl.store(y_ptr + rm[:, None] * stride_ym + rn[None, :] * stride_yn, acc.to(tl.bfloat16),
             mask=(rm[:, None] < M) & (rn[None, :] < N))


def w8a16_mm(x2: torch.Tensor, codes: torch.Tensor, w_scale: torch.Tensor) -> torch.Tensor:
    """x2 [M, K] bf16; codes [N, K] float8_e4m3fn (any strides); w_scale [1, N] fp32 -> [M, N] bf16."""
    M, K = x2.shape
    N = codes.shape[0]
    y = torch.empty((M, N), device=x2.device, dtype=torch.bfloat16)
    s = w_scale.reshape(-1).contiguous()
    mb = 16 if M <= 16 else (32 if M <= 32 else (64 if M <= 64 else 128))

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))
    _w8a16_kernel[grid](x2, codes, s, y, M, N, K, mb, x2.stride(0), x2.stride(1), codes.stride(0), codes.stride(1),
                        y.stride(0), y.stride(1))
    return y
