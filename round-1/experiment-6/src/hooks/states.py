#!/usr/bin/env python3
"""HF activation block (run after vLLM has exited; never both on the GPU).

Forward hooks on model.model.layers[i] capture the residual stream after block i.
B0  hook checks: hooked h_R == output_hidden_states[i+1][:, -1]; batched == unbatched.
B1  forced:X (20 frames) and described:X (10) prompts -> h_R at all layers; PCA(64)+multinomial LR probes:
    leave-one-frame-out accuracy (named) and named->described transfer accuracy, with shuffled-label nulls;
    l* = argmax_{8..28} (transfer - 95th pct of its null); S_R(l*) = QR basis of centred named centroids.
B2  condition states at R (all layers, 10 paraphrases x 11 conditions per task) + probe readout.
B3  teacher-forced trajectory states (prompt + first 64 generated ids) at layers {l*-4, l*, l*+4}:
    eval set = A1 top_k=10 cells (50 per T per task); fit sets = all A5 forced generations and A1 top_p samples
    (per-sample means; filtering by verified label happens in the analysis).
Outputs: states/*.npy (float16; trajectory states split into eval_<task>_l<layer>_part_NNN.npy files
< 45 MB each) + states/meta.json + results/probe_curves.json
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np  # noqa: E402
import torch  # noqa: E402

from common import (MODES, RAW, RESULTS, STATES, TASKS, model_id, read_jsonl, save_npy_parts,  # noqa: E402
                    setup_logging, write_json)
from prompts.build import build_all, chat_ids  # noqa: E402

logger = setup_logging("hooks_states")
LAYER_BAND = (8, 28)
N_PERM = 200


class Hooked:
    def __init__(self, model, layers: list[int], mode: str, n_last: int = 1):
        self.model, self.layers, self.mode, self.n_last = model, layers, mode, n_last
        self.store: dict[int, torch.Tensor] = {}
        self.handles = []
        for i in layers:
            self.handles.append(model.model.layers[i].register_forward_hook(self._mk(i)))

    def _mk(self, i):
        def fn(mod, inp, out):
            h = out[0] if isinstance(out, (tuple, list)) else out
            self.store[i] = h[:, -self.n_last:, :].detach().float().cpu()
        return fn

    def remove(self):
        for h in self.handles:
            h.remove()


def batch_forward(model, seqs: list[list[int]], pad_id: int, bs: int = 8):
    """Left-padded forward with mask-aware position ids. Yields (start, end) per batch after the forward."""
    i = 0
    while i < len(seqs):
        chunk = seqs[i:i + bs]
        L = max(len(s) for s in chunk)
        ids = torch.full((len(chunk), L), pad_id, dtype=torch.long)
        mask = torch.zeros((len(chunk), L), dtype=torch.long)
        for j, s in enumerate(chunk):
            ids[j, L - len(s):] = torch.tensor(s)
            mask[j, L - len(s):] = 1
        pos = (mask.cumsum(-1) - 1).clamp(min=0)
        try:
            with torch.no_grad():
                out = model(input_ids=ids.cuda(), attention_mask=mask.cuda(), position_ids=pos.cuda(),
                            use_cache=False)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            if bs == 1:
                raise
            bs = max(1, bs // 2)
            logger.warning(f"OOM: batch size -> {bs}")
            continue
        yield i, i + len(chunk), out
        i += len(chunk)


def collect_R(model, hk: Hooked, seqs: list[list[int]], pad_id: int, L: int) -> np.ndarray:
    res = np.zeros((len(seqs), L, model.config.hidden_size), dtype=np.float32)
    for a, b, _ in batch_forward(model, seqs, pad_id):
        for li in range(L):
            res[a:b, li] = hk.store[li][:, -1, :].numpy()
    return res


def hook_checks(model, tok, hk: Hooked, pad_id: int) -> dict:
    rows = [r for r in build_all() if r["condition"] == "baseline"][:2]
    seqs = [chat_ids(tok, r["user_message"], False) for r in rows]
    rep = {}
    diffs = []
    for s in seqs:
        ids = torch.tensor([s]).cuda()
        with torch.no_grad():
            out = model(input_ids=ids, output_hidden_states=True, use_cache=False)
        for li in range(model.config.num_hidden_layers - 1):
            a = hk.store[li][0, -1].numpy()
            b = out.hidden_states[li + 1][0, -1].float().cpu().numpy()
            diffs.append(float(np.max(np.abs(a - b)) / (np.max(np.abs(b)) + 1e-6)))
    rep["hooked_vs_hidden_states_max_rel_diff"] = max(diffs)
    rep["hooked_equals_hidden_states"] = bool(max(diffs) < 1e-3)
    unb = []
    for s in seqs:
        for _ in batch_forward(model, [s], pad_id, bs=1):
            pass
        unb.append(np.stack([hk.store[li][0, -1].numpy() for li in range(model.config.num_hidden_layers)]))
    bat = collect_R(model, hk, seqs + [chat_ids(tok, build_all()[50]["user_message"], False)], pad_id,
                    model.config.num_hidden_layers)[:2]
    rel = [float(np.max(np.abs(bat[j] - unb[j])) / (np.max(np.abs(unb[j])) + 1e-6)) for j in range(2)]
    rep["batched_vs_unbatched_max_rel_diff"] = max(rel)
    rep["batched_equals_unbatched_tol_2e-2"] = bool(max(rel) < 2e-2)
    return rep


def probe_layer(Xn: np.ndarray, yn: np.ndarray, frames: np.ndarray, Xd: np.ndarray, yd: np.ndarray,
                rng: np.random.Generator, n_perm: int) -> dict:
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xn)
    Zn = sc.transform(Xn)
    k = min(64, Zn.shape[0] - 1)
    pca = PCA(k, random_state=0).fit(Zn)
    Pn, Pd = pca.transform(Zn), pca.transform(sc.transform(Xd))
    best_c, best_s = 0.1, -1
    for C in (0.01, 0.1, 1.0):
        s = cross_val_score(LogisticRegression(C=C, max_iter=2000), Pn, yn,
                            cv=StratifiedKFold(5, shuffle=True, random_state=0)).mean()
        if s > best_s:
            best_c, best_s = C, s
    clf = LogisticRegression(C=best_c, max_iter=2000).fit(Pn, yn)
    transfer = float((clf.predict(Pd) == yd).mean())
    # leave-one-frame-out (PCA refit per fold on the training frames only)
    correct = 0
    for f in np.unique(frames):
        tr, te = frames != f, frames == f
        sc_f = StandardScaler().fit(Xn[tr])
        p_f = PCA(min(64, tr.sum() - 1), random_state=0).fit(sc_f.transform(Xn[tr]))
        c_f = LogisticRegression(C=best_c, max_iter=2000).fit(p_f.transform(sc_f.transform(Xn[tr])), yn[tr])
        correct += int((c_f.predict(p_f.transform(sc_f.transform(Xn[te]))) == yn[te]).sum())
    lofo = correct / len(yn)
    null_t = []
    for _ in range(n_perm):
        yp = rng.permutation(yn)
        c0 = LogisticRegression(C=best_c, max_iter=500).fit(Pn, yp)
        null_t.append(float((c0.predict(Pd) == yd).mean()))
    null_l = []
    for _ in range(20):
        yp = rng.permutation(yn)
        corr = 0
        for f in np.unique(frames):
            tr, te = frames != f, frames == f
            c0 = LogisticRegression(C=best_c, max_iter=300).fit(Pn[tr], yp[tr])
            corr += int((c0.predict(Pn[te]) == yp[te]).sum())
        null_l.append(corr / len(yp))
    return dict(C=best_c, transfer=transfer, lofo=lofo, null_transfer_p95=float(np.percentile(null_t, 95)),
                null_transfer_mean=float(np.mean(null_t)), null_lofo_p95=float(np.percentile(null_l, 95)),
                null_lofo_mean=float(np.mean(null_l)), clf=clf, pca=pca, sc=sc)


def main() -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    t_all = time.time()
    MODEL = model_id()
    tok = AutoTokenizer.from_pretrained(MODEL)
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else 151643
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16,
                                                 attn_implementation="sdpa").cuda().eval()
    NL = model.config.num_hidden_layers
    logger.info(f"loaded {MODEL}: {NL} layers, d={model.config.hidden_size}")
    meta: dict = {"model": MODEL, "n_layers": NL, "d": model.config.hidden_size}
    hk = Hooked(model, list(range(NL)), "R", n_last=1)
    meta["hook_checks"] = hook_checks(model, tok, hk, pad_id)
    logger.info(f"hook checks: {meta['hook_checks']}")
    prompts = build_all()
    rng = np.random.default_rng(0)
    probe_curves: dict = {}
    lstar: dict = {}
    for task in TASKS:
        named = [r for r in prompts if r["task"] == task and r["condition"].startswith("forced:")]
        desc = [r for r in prompts if r["task"] == task and r["condition"].startswith("described:")]
        cond_rows = [r for r in prompts if r["task"] == task and ":" not in r["condition"]
                     and r["condition"] != "gts_stage1"]
        Hn = collect_R(model, hk, [chat_ids(tok, r["user_message"], False) for r in named], pad_id, NL)
        Hd = collect_R(model, hk, [chat_ids(tok, r["user_message"], False) for r in desc], pad_id, NL)
        Hc = collect_R(model, hk, [chat_ids(tok, r["user_message"], False) for r in cond_rows], pad_id, NL)
        yn = np.array([r["condition"].split(":")[1] for r in named])
        fr = np.array([r["paraphrase_id"] for r in named])
        yd = np.array([r["condition"].split(":")[1] for r in desc])
        np.save(STATES / f"R_named_{task}.npy", Hn.astype(np.float16))
        np.save(STATES / f"R_described_{task}.npy", Hd.astype(np.float16))
        np.save(STATES / f"R_conditions_{task}.npy", Hc.astype(np.float16))
        meta[f"R_named_{task}"] = [dict(condition=r["condition"], paraphrase_id=r["paraphrase_id"]) for r in named]
        meta[f"R_described_{task}"] = [dict(condition=r["condition"], paraphrase_id=r["paraphrase_id"])
                                       for r in desc]
        meta[f"R_conditions_{task}"] = [dict(condition=r["condition"], paraphrase_id=r["paraphrase_id"])
                                        for r in cond_rows]
        curves = []
        fitted = {}
        t0 = time.time()
        for li in range(NL):
            n_perm = N_PERM if LAYER_BAND[0] <= li <= LAYER_BAND[1] else 50
            res = probe_layer(Hn[:, li], yn, fr, Hd[:, li], yd, rng, n_perm)
            fitted[li] = (res.pop("clf"), res.pop("pca"), res.pop("sc"))
            res["layer"] = li
            res["n_perm"] = n_perm
            curves.append(res)
            logger.info(f"{task} layer {li}: lofo={res['lofo']:.3f} transfer={res['transfer']:.3f} "
                        f"null95={res['null_transfer_p95']:.3f} ({time.time() - t0:.0f}s)")
        band = [c for c in curves if LAYER_BAND[0] <= c["layer"] <= LAYER_BAND[1]]
        margin = [c["transfer"] - c["null_transfer_p95"] for c in band]
        if max(margin) > 0:
            ls = band[int(np.argmax(margin))]["layer"]
            rule = "argmax(transfer - null95) over layers 8-28"
        else:
            m2 = [c["lofo"] - c["null_lofo_p95"] for c in band]
            good = [c["layer"] for c, m in zip(band, m2) if m >= max(m2) - 0.02]
            ls = int(np.median(good))
            rule = "fallback: middle of the within-named plateau (R subspace possibly lexical)"
        lstar[task] = int(ls)
        probe_curves[task] = dict(curves=curves, l_star=int(ls), rule=rule)
        # probe readout of condition states at l*
        clf, pca, sc = fitted[ls]
        proba = clf.predict_proba(pca.transform(sc.transform(Hc[:, ls])))
        meta[f"probe_classes_{task}"] = list(clf.classes_)
        np.save(STATES / f"R_conditions_probe_{task}.npy", proba.astype(np.float32))
        del Hn, Hd, Hc, fitted
        gc.collect()
    write_json(RESULTS / "probe_curves.json", probe_curves)
    meta["l_star"] = lstar
    hk.remove()
    # ---------------- B3 trajectory states ----------------
    eval_rows, fit_rows = [], []
    for r in read_jsonl(RAW / "A1.jsonl"):
        d = r["decoding"]
        if d["sampler"] == "topk10" and r["sample_id"] < 5:
            eval_rows.append(r)
        elif d["sampler"] == "topp095":
            fit_rows.append(("A1p", r))
    for r in read_jsonl(RAW / "A5.jsonl"):
        fit_rows.append(("A5", r))
    for task in TASKS:
        ls = lstar[task]
        layers = sorted({max(0, ls - 4), ls, min(NL - 1, ls + 4)})
        hk3 = Hooked(model, layers, "gen", n_last=64)
        ev = [r for r in eval_rows if r["task"] == task and len(r["output_token_ids"]) >= 64]
        ev.sort(key=lambda r: (r["decoding"]["T"], r["paraphrase_id"], r["sample_id"]))
        seqs = [r["prompt_token_ids"] + r["output_token_ids"][:64] for r in ev]
        arr = {li: np.zeros((len(seqs), 64, model.config.hidden_size), dtype=np.float16) for li in layers}
        first_tok_prob = []
        for a, b, out in batch_forward(model, seqs, pad_id):
            for li in layers:
                arr[li][a:b] = hk3.store[li].numpy().astype(np.float16)
            # alignment: logits at the last prompt position predict the first generated token
            logits = out.logits[:, -65, :].float()
            lp = torch.log_softmax(logits, -1).cpu().numpy()
            for j, r in enumerate(ev[a:b]):
                first_tok_prob.append(float(np.exp(lp[j, r["output_token_ids"][0]])))
            del out
        for li in layers:
            save_npy_parts(STATES / f"eval_{task}_l{li}", arr[li])  # split: each part < 45 MB
        meta[f"eval_{task}"] = dict(layers=layers, rows=[dict(key=r["key"], T=r["decoding"]["T"],
                                                               paraphrase_id=r["paraphrase_id"],
                                                               sample_id=r["sample_id"]) for r in ev],
                                    first_token_prob_median=float(np.median(first_tok_prob)),
                                    first_token_prob_p10=float(np.percentile(first_tok_prob, 10)))
        del arr
        gc.collect()
        fr_rows = [(src, r) for src, r in fit_rows if r["task"] == task and len(r["output_token_ids"]) >= 8]
        seqs = [r["prompt_token_ids"] + r["output_token_ids"][:64] for _, r in fr_rows]
        n_out = [min(64, len(r["output_token_ids"])) for _, r in fr_rows]
        means = {li: np.zeros((len(seqs), model.config.hidden_size), dtype=np.float32) for li in layers}
        for a, b, out in batch_forward(model, seqs, pad_id):
            for li in layers:
                h = hk3.store[li].numpy()
                for j in range(b - a):
                    means[li][a + j] = h[j, -n_out[a + j]:, :].mean(0)
            del out
        for li in layers:
            np.save(STATES / f"fitmeans_{task}_l{li}.npy", means[li])
        meta[f"fit_{task}"] = dict(layers=layers, rows=[dict(src=src, key=r["key"], condition=r["condition"],
                                                              T=r["decoding"]["T"]) for src, r in fr_rows])
        hk3.remove()
        logger.info(f"B3 {task}: eval {len(ev)} seqs, fit {len(fr_rows)} seqs, layers {layers}")
    meta["seconds"] = round(time.time() - t_all, 1)
    write_json(STATES / "meta.json", meta)
    logger.info(f"hooks done in {meta['seconds']}s")


if __name__ == "__main__":
    main()
