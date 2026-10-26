import torch, time
torch.set_num_threads(4)
D, n = 2560, 384
g = torch.Generator().manual_seed(0)
Q = torch.linalg.qr(torch.randn(D, 2, generator=g))[0]
Wout = torch.randn(3, 2, generator=g) * 3.0
def readout(x): return torch.log_softmax((x @ Q) @ Wout.T, -1)
X = torch.randn(n, D, generator=g); Xs = torch.randn(n, D, generator=g)
tgt = readout(Xs).exp()
def run(lr, steps, scale, opt_name="adam", loss_kind="kl"):
    W = (torch.randn(D, 2, generator=torch.Generator().manual_seed(7)) * scale).requires_grad_(True)
    opt = torch.optim.Adam([W], lr=lr) if opt_name == "adam" else torch.optim.SGD([W], lr=lr)
    for s in range(steps):
        R = torch.linalg.qr(W)[0]
        xn = X[:256] + ((Xs[:256] - X[:256]) @ R) @ R.T
        lq = readout(xn)
        loss = (tgt[:256] * (tgt[:256].clamp(min=1e-9).log() - lq)).sum(-1).mean()
        opt.zero_grad(); loss.backward(); opt.step()
    R = torch.linalg.qr(W.detach())[0]
    xn = X[256:] + ((Xs[256:] - X[256:]) @ R) @ R.T
    kl = float((tgt[256:] * (tgt[256:].clamp(min=1e-9).log() - readout(xn))).sum(-1).mean())
    return [round(c, 3) for c in torch.linalg.svdvals(Q.T @ R).tolist()], round(kl, 4), round(float(loss), 4)
for cfg in [(2e-2, 300, 1.0), (2e-3, 400, 1.0), (2e-3, 400, 0.01), (2e-2, 300, 0.01), (1e-1, 300, 1.0), (2e-2, 1000, 1.0)]:
    t = time.time(); print(cfg, run(*cfg), f"{time.time()-t:.1f}s", flush=True)
