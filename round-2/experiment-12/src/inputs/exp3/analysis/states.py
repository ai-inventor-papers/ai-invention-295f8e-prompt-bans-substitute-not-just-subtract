"""S12 (HF process, after vLLM exited): residual-stream states at 8 positions x decoder blocks 8..28.

Position k = state that predicts generated token k = absolute index prompt_len - 1 + k.
Positions: R (k=0), k=8, 16, 32, 64, k_fork, k_pre = commit_idx, k_post = commit_idx + 1.
"""

from __future__ import annotations

import json
import time

import numpy as np
from loguru import logger

from common import GEN_DIR, LOG_DIR, ROOT, STATE_DIR, SUM_DIR, read_jsonl

LAYERS = list(range(8, 29))
POS_NAMES = ["R", "k8", "k16", "k32", "k64", "k_fork", "k_pre", "k_post"]


class StopForward(Exception):
    pass


PART_SIZE = 60  # samples per part: 60 x 8 x 21 x 4096 float16 = 83 MB (< 100 MB GitHub limit)


def save_state_parts(task: str, X: np.ndarray, mask: np.ndarray, ks: np.ndarray) -> None:
    for old in STATE_DIR.glob(f"{task}_part_*.npz"):
        old.unlink()
    for i, a in enumerate(range(0, len(X), PART_SIZE)):
        np.savez(STATE_DIR / f"{task}_part_{i + 1:03d}.npz", X=X[a:a + PART_SIZE], mask=mask[a:a + PART_SIZE],
                 ks=ks[a:a + PART_SIZE])


def load_state_parts(task: str) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    parts = sorted(STATE_DIR.glob(f"{task}_part_*.npz"))
    if not parts:
        return None
    ds = [np.load(f) for f in parts]
    return (np.concatenate([d["X"] for d in ds]), np.concatenate([d["mask"] for d in ds]),
            np.concatenate([d["ks"] for d in ds]))


def _fork_index_map() -> tuple[dict, dict]:
    """first confirmed fork per base path (provisional), and per task x condition median."""
    p = SUM_DIR / "gen2_provisional.json"
    first, med = {}, {}
    if not p.exists():
        return first, med
    prov = json.loads(p.read_text())
    for c in prov.get("candidates", []):
        if c.get("confirmed"):
            bp = c["bp_id"]
            first[bp] = min(first.get(bp, 10 ** 9), int(c["t"]))
    by = {}
    for bp, t in first.items():
        task, cond, _ = bp.split("|")
        by.setdefault((task, cond), []).append(t)
    med = {k: int(np.median(v)) for k, v in by.items()}
    return first, med


def run_states() -> None:
    import torch
    from transformers import AutoModelForCausalLM

    prompts = json.loads((ROOT / "prompts" / "prompts.json").read_text())
    pools = read_jsonl(GEN_DIR / "pools.jsonl")
    first, med = _fork_index_map()
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", torch_dtype=torch.bfloat16,
                                                 attn_implementation="sdpa").cuda().eval()
    logger.info(f"HF model loaded in {time.time() - t0:.0f}s")
    layers = model.model.layers
    checks = {}
    for task in ("T1", "T2"):
        rows = [r for r in pools if r["task"] == task and r["arm"] in ("G1", "G2")]
        n = len(rows)
        X = np.zeros((n, len(POS_NAMES), len(LAYERS), model.config.hidden_size), dtype=np.float16)
        mask = np.zeros((n, len(POS_NAMES)), dtype=bool)
        ks = np.full((n, len(POS_NAMES)), -1, dtype=np.int32)
        items = []
        for i, r in enumerate(rows):
            P = prompts[f"{task}|{r['condition']}|{r['paraphrase_id']}"]["prompt_token_ids"]
            g = r["gen_token_ids"]
            bp = f"{task}|{r['condition']}|{r['paraphrase_id']}"
            kf = first.get(bp, med.get((task, r["condition"])))
            kp = r["commit_idx"]
            kk = [0, 8, 16, 32, 64, kf, kp, None if kp is None else kp + 1]
            pos = []
            for j, k in enumerate(kk):
                if k is not None and 0 <= k <= len(g):
                    mask[i, j] = True
                    ks[i, j] = k
                    pos.append(len(P) - 1 + k)
                else:
                    pos.append(len(P) - 1)
            maxk = max([k for k in kk if k is not None and k <= len(g)] + [0])
            items.append((i, P + g[:maxk], pos))
        bs = 8
        i0 = 0
        while i0 < len(items):
            batch = items[i0:i0 + bs]
            L = max(len(x[1]) for x in batch)
            ids = torch.zeros((len(batch), L), dtype=torch.long)
            att = torch.zeros((len(batch), L), dtype=torch.long)
            for b, (_, seq, _) in enumerate(batch):
                ids[b, :len(seq)] = torch.tensor(seq)
                att[b, :len(seq)] = 1
            pos_t = torch.tensor([x[2] for x in batch], dtype=torch.long).cuda()
            cap = {}

            def mk(li):
                def hook(mod, inp, out):
                    h = out[0] if isinstance(out, tuple) else out
                    cap[li] = h[torch.arange(h.shape[0], device=h.device)[:, None], pos_t].float().cpu().numpy()
                    if li == LAYERS[-1]:
                        raise StopForward()
                return hook

            hs = [layers[li].register_forward_hook(mk(li)) for li in LAYERS]
            try:
                with torch.no_grad():
                    model.model(input_ids=ids.cuda(), attention_mask=att.cuda())
            except StopForward:
                pass
            except torch.cuda.OutOfMemoryError:
                for h in hs:
                    h.remove()
                torch.cuda.empty_cache()
                bs = max(1, bs // 2)
                logger.warning(f"OOM: batch -> {bs}")
                continue
            finally:
                for h in hs:
                    h.remove()
            for b, (i, _, _) in enumerate(batch):
                for li_idx, li in enumerate(LAYERS):
                    X[i, :, li_idx, :] = cap[li][b].astype(np.float16)
            i0 += len(batch)
        # sanity: R states identical across samples of one prompt
        cos = []
        for (cond, pid) in {(r["condition"], r["paraphrase_id"]) for r in rows}:
            idx = [i for i, r in enumerate(rows) if r["condition"] == cond and r["paraphrase_id"] == pid]
            a = X[idx, 0, -1, :].astype(np.float32)
            a0 = a[0]
            for v in a[1:]:
                cos.append(float(v @ a0 / (np.linalg.norm(v) * np.linalg.norm(a0) + 1e-9)))
        checks[f"{task}_R_cos_min"] = float(np.min(cos)) if cos else None
        checks[f"{task}_positions_in_range"] = bool(all(0 <= p for _, s, ps in items for p in ps))
        meta = {"rows": [{"arm": r["arm"], "condition": r["condition"], "paraphrase_id": r["paraphrase_id"],
                          "sample_id": r["sample_id"], "label": r["label"], "commit_idx": r["commit_idx"]}
                         for r in rows], "layers": LAYERS, "positions": POS_NAMES}
        save_state_parts(task, X, mask, ks)
        (STATE_DIR / f"{task}_meta.json").write_text(json.dumps(meta))
        logger.info(f"{task}: states {X.shape} saved; R cos min {checks[f'{task}_R_cos_min']}")
        del X
    # next-token distributions (T=1.0) at fork candidates and control positions (full softmax; top-20 renormalised)
    items_p = SUM_DIR / "next_token_items.json"
    if items_p.exists():
        items = json.loads(items_p.read_text())
        base = {f"{r['task']}|{r['condition']}|{r['paraphrase_id']}": r for r in pools
                if r["sample_id"] == 0 and r["arm"] in ("G1", "G2")}
        from transformers import AutoTokenizer
        tk = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
        res = []
        for it in items:
            r = base[it["bp_id"]]
            task, cond, pid = it["bp_id"].split("|")
            P = prompts[f"{task}|{cond}|{pid}"]["prompt_token_ids"]
            g = r["gen_token_ids"]
            p = int(it["p"])
            with torch.no_grad():
                hs = model.model(input_ids=torch.tensor([P + g[:p]]).cuda()).last_hidden_state[0, -1]
                logits = model.lm_head(hs).float()
                lp = torch.log_softmax(logits, -1)
            top = torch.topk(lp, 20)
            q = torch.softmax(top.values, -1).cpu().numpy()
            full_p = lp.exp()
            ent_full = float(-(full_p * lp).sum().item() / np.log(2))
            res.append({"bp_id": it["bp_id"], "p": p, "kind": it["kind"],
                        "entropy_bits_top20": float(-(q * np.log2(np.clip(q, 1e-12, 1))).sum()),
                        "entropy_bits_full": ent_full, "top20_mass": float(top.values.exp().sum().item()),
                        "actual_token": tk.decode([g[p]]) if p < len(g) else None,
                        "actual_token_prob": float(full_p[g[p]].item()) if p < len(g) else None,
                        "top": [(tk.decode([int(i)]), float(v)) for v, i in zip(top.values[:10].tolist(),
                                                                                  top.indices[:10].tolist())]})
        (SUM_DIR / "next_token.json").write_text(json.dumps(res, indent=1))
        logger.info(f"next-token distributions: {len(res)} positions")
    # sanity: LM-head argmax vs generated token on 5 T=0.3 samples
    agree = []
    rows03 = [r for r in pools if r["arm"] == "G3_T0.3"][:5]
    for r in rows03:
        P = prompts[f"{r['task']}|baseline|{r['paraphrase_id']}"]["prompt_token_ids"]
        g = r["gen_token_ids"][:40]
        with torch.no_grad():
            out = model(input_ids=torch.tensor([P + g]).cuda())
        logits = out.logits[0, len(P) - 1: len(P) - 1 + len(g)]
        pred = logits.argmax(-1).cpu().numpy()
        agree.append(float(np.mean(pred == np.array(g))))
    checks["lm_head_argmax_agreement_T0.3"] = agree
    (LOG_DIR / "test_states.json").write_text(json.dumps(checks, indent=1))
    logger.info(f"S12 checks: {checks}")
