import torch, time
torch.set_num_threads(4)
D = 2560
g = torch.Generator().manual_seed(0)
Q = torch.linalg.qr(torch.randn(D, 2, generator=g))[0]
Wout = torch.randn(3, 2, generator=g) * 3.0
def readout(x): return torch.log_softmax((x @ Q) @ Wout.T, -1)
for ntr in (1024, 4096):
    n = ntr + 1024
    X = torch.randn(n, D, generator=g); Xs = torch.randn(n, D, generator=g)
    tgt = readout(Xs).exp()
    for lr, steps, bs in ((2e-3, 400, 64), (2e-2, 400, 256), (2e-2, 800, 512)):
        W = torch.randn(D, 2, generator=torch.Generator().manual_seed(7)).requires_grad_(True)
        opt = torch.optim.Adam([W], lr=lr); t = time.time()
        for s in range(steps):
            ix = torch.randint(0, ntr, (bs,), generator=torch.Generator().manual_seed(s))
            R = torch.linalg.qr(W)[0]
            xn = X[ix] + ((Xs[ix] - X[ix]) @ R) @ R.T
            loss = (tgt[ix] * (tgt[ix].clamp(min=1e-9).log() - readout(xn))).sum(-1).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        R = torch.linalg.qr(W.detach())[0]
        xn = X[ntr:] + ((Xs[ntr:] - X[ntr:]) @ R) @ R.T
        kl = float((tgt[ntr:] * (tgt[ntr:].clamp(min=1e-9).log() - readout(xn))).sum(-1).mean())
        print(ntr, lr, steps, bs, [round(c, 3) for c in torch.linalg.svdvals(Q.T @ R).tolist()], round(kl, 4), round(float(loss.detach()), 4), f"{time.time()-t:.1f}s", flush=True)
