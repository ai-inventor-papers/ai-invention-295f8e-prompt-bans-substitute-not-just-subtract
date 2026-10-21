"""Probe which FP8 scaled-matmul variants torch supports on this GPU (sm_89) and their speed."""
import time, torch
print(torch.__version__, torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
dev = "cuda"
M, K, N = 10, 4096, 12288
x = torch.randn(M, K, device=dev, dtype=torch.bfloat16)
w = torch.randn(N, K, device=dev, dtype=torch.bfloat16) * 0.02
ref = x @ w.T
# rowwise: per-token act scale, per-channel weight scale
wa = w.abs().amax(dim=1, keepdim=True).float() / 448.0
wq = (w.float() / wa).to(torch.float8_e4m3fn)
xa = x.abs().amax(dim=1, keepdim=True).float().clamp(min=1e-12) / 448.0
xq = (x.float() / xa).to(torch.float8_e4m3fn)
for name, sa, sb in [("rowwise", xa, wa.T.contiguous()), ("tensorwise", xa.max().reshape(()), wa.max().reshape(()))]:
    try:
        if name == "tensorwise":
            xq2 = (x.float() / sa).to(torch.float8_e4m3fn); wq2 = (w.float() / sb).to(torch.float8_e4m3fn)
        else:
            xq2, wq2 = xq, wq
        out = torch._scaled_mm(xq2, wq2.T, scale_a=sa, scale_b=sb, out_dtype=torch.bfloat16)
        rel = ((out.float() - ref.float()).norm() / ref.float().norm()).item()
        torch.cuda.synchronize(); t = time.time()
        for _ in range(200):
            out = torch._scaled_mm(xq2, wq2.T, scale_a=sa, scale_b=sb, out_dtype=torch.bfloat16)
        torch.cuda.synchronize(); dt = (time.time() - t) / 200
        print(f"{name}: OK rel_err={rel:.4f} time={dt*1e3:.3f} ms  ({N*K/dt/1e9:.0f} GB/s fp8 weight read)")
    except Exception as e:
        print(f"{name}: FAIL {type(e).__name__}: {str(e)[:300]}")
torch.cuda.synchronize(); t = time.time()
for _ in range(200):
    out = x @ w.T
torch.cuda.synchronize(); dt = (time.time() - t) / 200
print(f"bf16 matmul time={dt*1e3:.3f} ms ({N*K*2/dt/1e9:.0f} GB/s)")
