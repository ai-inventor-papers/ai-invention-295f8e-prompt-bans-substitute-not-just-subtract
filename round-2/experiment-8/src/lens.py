#!/usr/bin/env python3
"""S6: logit lens (+ tuned lens) at the commitment token.

Commitment position: in each arm-(b) default program from S4 (BFS on T1, Dijkstra on T2) the token before the first
token overlapping the X signature vocabulary. The program prefix is teacher-forced under the ban prompt and its
neutral twin (same template and noun); per layer l = 0..36 the residual at that position is read through
final_norm -> lm_head. VETO LAYER = first l with ln rank_ban - ln rank_neu >= 1 for the banned set at every l' >= l;
SUBSTITUTE RISE LAYER = first l from which ln rank_neu(sub) - ln rank_ban(sub) >= 1 at every later layer.
The same readout runs on arm-(a) substitute programs at their first substitute-signature token.
Tuned lens: affine translators at layers 3, 6, ..., 33 trained on KL(final || lens) over held-in program tokens,
accepted per layer only where held-out KL beats the logit lens.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (DATA_DIR, N_LAYERS, PROMPTS_DIR, RESULTS_DIR, SIGNATURE_VOCAB, SUB_KEY, TASKS, X_KEY, read_jsonl,
                 write_json)

TL_LAYERS = list(range(3, 34, 3))
MAX_PROGS = 60


def _lens_set(tok: Any, key: str) -> list[int]:
    """Distinctive first subwords of a signature vocabulary (decoded length >= 4 after stripping, no 'range')."""
    ids = set()
    for wd in SIGNATURE_VOCAB[key]:
        base = wd.split("(")[0].strip()
        if base in ("range", "") or len(base) < 4:
            continue
        for v in (base, " " + base, "." + base, "(" + base):
            tid = tok(v, add_special_tokens=False)["input_ids"][0]
            if len(tok.decode([tid]).strip(" .(")) >= 4:
                ids.add(tid)
    return sorted(ids)


def _first_overlap(tok: Any, token_ids: list[int], vocab: list[str]) -> int | None:
    """Index of the first generated token overlapping an exact occurrence of a signature pattern."""
    words = []
    for w in vocab:
        if w == "pop()":
            words.append(".pop()")
        elif w.startswith("range("):
            words += [w, w.replace(" ", "")]
        else:
            words.append(w)
    text, spans = "", []
    for t in token_ids:
        s = len(text)
        text += tok.decode([t])
        spans.append((s, len(text)))
    occ = []
    for w in words:
        occ += [(m.start(), m.end()) for m in re.finditer(re.escape(w), text)]
    if not occ:
        return None
    first = min(a for a, _ in occ)
    for i, (s, e) in enumerate(spans):
        if e > first:
            return i
    return None


@torch.no_grad()
def _hidden_at(model: Any, ids: list[int]) -> torch.Tensor:
    out = model.model(input_ids=torch.tensor([ids], device=model.device), output_hidden_states=True)
    hs = out.hidden_states
    H = torch.stack([h[0, -1] for h in hs]).float()  # [37, d]
    return H, out.last_hidden_state[0, -1].float()


@torch.no_grad()
def _lens_logprobs(model: Any, H: torch.Tensor, last_normed: torch.Tensor) -> torch.Tensor:
    """Logit lens: final_norm(h_l) -> lm_head (the last layer's hidden state is already normed in HF Qwen3)."""
    normed = model.model.norm(H.to(torch.bfloat16)).float()
    if torch.allclose(H[-1], last_normed, atol=1e-3):
        normed[-1] = last_normed
    logits = model.lm_head(normed.to(torch.bfloat16)).float()
    return torch.log_softmax(logits, -1)


def _readout(lp: torch.Tensor, S: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """per layer: logsumexp over set, ln(best rank) of set (rank 1 = top)."""
    lps = torch.logsumexp(lp[:, S], dim=-1).cpu().numpy()
    best = lp[:, S].max(-1).values
    rank = (lp > best[:, None]).sum(-1).float() + 1
    return lps, torch.log(rank).cpu().numpy()


def _layer_of(d: np.ndarray, thr: float = 1.0) -> int | None:
    ok = d >= thr
    for l in range(len(d)):
        if ok[l:].all():
            return l
    return None


def collect(model: Any, tok: Any, fp: dict[str, Any], samples: list[dict[str, Any]]) -> dict[str, Any]:
    recs = []
    for t in TASKS:
        X, SUB = X_KEY[t], SUB_KEY[t]
        sx, ss = _lens_set(tok, X), _lens_set(tok, SUB)
        logger.info(f"lens sets {t}: X={[tok.decode([i]) for i in sx]} SUB={[tok.decode([i]) for i in ss]}")
        for mode, arm, lab, vkey in (("default", "b", X, X), ("substitute", "a", SUB, SUB)):
            progs = [s for s in samples if s["task"] == t and s["condition"] == arm and s["label"] == lab][:MAX_PROGS]
            for s in progs:
                c = _first_overlap(tok, s["token_ids"], SIGNATURE_VOCAB[vkey])
                if c is None or c == 0:
                    continue
                tw = fp["tasks"][t]["templates"][s["template"]]
                slot = s.get("noun_slot") if s.get("noun_slot") in ("A", "B") else "A"
                prefix = s["token_ids"][:c]
                Hb, lb = _hidden_at(model, tw["ban"]["ids"] + prefix)
                Hn, ln = _hidden_at(model, tw[f"neutral_{slot}"]["ids"] + prefix)
                lpb, lpn = _lens_logprobs(model, Hb, lb), _lens_logprobs(model, Hn, ln)
                r = {"task": t, "mode": mode, "template": s["template"], "sample_id": s["sample_id"], "pos": c,
                     "commit_token": tok.decode([s["token_ids"][c]])}
                for name, S in (("X", sx), ("SUB", ss)):
                    a1, r1 = _readout(lpb, S)
                    a2, r2 = _readout(lpn, S)
                    r[f"{name}_logp_ban"], r[f"{name}_lnrank_ban"] = a1.tolist(), r1.tolist()
                    r[f"{name}_logp_neu"], r[f"{name}_lnrank_neu"] = a2.tolist(), r2.tolist()
                r["veto_layer"] = _layer_of(np.array(r["X_lnrank_ban"]) - np.array(r["X_lnrank_neu"]))
                r["sub_rise_layer"] = _layer_of(np.array(r["SUB_lnrank_neu"]) - np.array(r["SUB_lnrank_ban"]))
                r["_H"] = (Hb[TL_LAYERS].cpu().numpy(), Hn[TL_LAYERS].cpu().numpy())
                recs.append(r)
    return {"records": recs}


def summarise(recs: list[dict[str, Any]], prefix: str = "") -> dict[str, Any]:
    rng = np.random.default_rng(3)
    out = {}
    for t in TASKS:
        for mode in ("default", "substitute"):
            R = [r for r in recs if r["task"] == t and r["mode"] == mode]
            if not R:
                continue
            ent: dict[str, Any] = {"n": len(R)}
            for key in ("veto_layer", "sub_rise_layer"):
                v = [r[prefix + key] for r in R if r.get(prefix + key) is not None]
                ent[key] = {"n_defined": len(v), "n_never": len(R) - len(v),
                            "median": float(np.median(v)) if v else None,
                            "iqr": [float(np.percentile(v, 25)), float(np.percentile(v, 75))] if v else None,
                            "histogram": {int(k): int(c) for k, c in zip(*np.unique(v, return_counts=True))} if v else {}}
            for name in ("X", "SUB"):
                for q in ("lnrank", "logp"):
                    d = np.array([np.array(r[f"{prefix}{name}_{q}_ban"]) - np.array(r[f"{prefix}{name}_{q}_neu"])
                                  for r in R])
                    bs = np.stack([d[rng.integers(0, len(d), len(d))].mean(0) for _ in range(500)])
                    ent[f"{name}_{q}_ban_minus_neu_mean"] = d.mean(0).tolist()
                    ent[f"{name}_{q}_ban_minus_neu_ci"] = [np.percentile(bs, 2.5, 0).tolist(),
                                                          np.percentile(bs, 97.5, 0).tolist()]
            out[f"{t}_{mode}"] = ent
    return out


# ------------------------------------------------------------------------------------------------ tuned lens
@torch.no_grad()
def tl_data(model: Any, fp: dict[str, Any], samples: list[dict[str, Any]], n_train: int = 80000,
            n_held: int = 20000) -> dict[str, Any]:
    progs = read_jsonl(DATA_DIR / "frlp_programs.jsonl")
    seqs = []
    for p in progs:
        fr = fp["tasks"][p["task"]]["forced"][p["algorithm"]]
        pr = fr["paraphrases"][p["prompt_index"]] if p["prompt_kind"] == "paraphrase" else fr["descriptive"]
        seqs.append((pr["ids"], p["gen_token_ids"]))
    for s in samples:
        tw = fp["tasks"][s["task"]]["templates"][s["template"]]
        if s["condition"] == "a":
            seqs.append((tw["ban"]["ids"], s["token_ids"]))
    rng = np.random.default_rng(0)
    order = rng.permutation(len(seqs))
    Hs = {l: [] for l in TL_LAYERS}
    F = []
    n = 0
    for i in order:
        pids, gids = seqs[i]
        ids = pids + gids
        out = model.model(input_ids=torch.tensor([ids], device=model.device), output_hidden_states=True)
        sl = slice(len(pids), len(ids))
        for l in TL_LAYERS:
            Hs[l].append(out.hidden_states[l][0, sl].to(torch.float16).cpu())
        F.append(out.last_hidden_state[0, sl].to(torch.float16).cpu())
        n += len(gids)
        if n >= n_train + n_held:
            break
    Hc = {l: torch.cat(v)[:n_train + n_held] for l, v in Hs.items()}
    Fc = torch.cat(F)[:n_train + n_held]
    return {"H": Hc, "F": Fc, "n_train": min(n_train, len(Fc) - n_held), "n_total": len(Fc)}


def train_tuned_lens(model: Any, data: dict[str, Any], epochs: int = 3, bs: int = 1024,
                     time_box_s: float = 1500) -> dict[str, Any]:
    t0 = time.time()
    for prm in model.parameters():
        prm.requires_grad_(False)
    W = model.lm_head.weight  # frozen, bf16
    norm = model.model.norm
    nt = data["n_train"]
    res = {}
    translators = {}
    for l in TL_LAYERS:
        if time.time() - t0 > time_box_s:
            res[l] = {"skipped": "time box"}
            continue
        d = W.shape[1]
        A = torch.nn.Linear(d, d, bias=True, device=model.device, dtype=torch.float32)
        torch.nn.init.eye_(A.weight)
        torch.nn.init.zeros_(A.bias)
        opt = torch.optim.AdamW(A.parameters(), lr=1e-4, weight_decay=1e-3)
        H, Fh = data["H"][l], data["F"]

        def kl_batch(h: torch.Tensor, f: torch.Tensor, lens: bool = True) -> torch.Tensor:
            with torch.no_grad():
                tgt = torch.log_softmax((f.to(model.device).to(torch.bfloat16) @ W.T).float(), -1)
            x = h.to(model.device).float()
            z = A(x) if lens else x
            lp = torch.log_softmax((norm(z.to(torch.bfloat16)) @ W.T).float(), -1)
            return (tgt.exp() * (tgt - lp)).sum(-1).mean()

        for ep in range(epochs):
            perm = torch.randperm(nt)
            for s in range(0, nt, bs):
                idx = perm[s:s + bs]
                loss = kl_batch(H[idx], Fh[idx])
                opt.zero_grad()
                loss.backward()
                opt.step()
        with torch.no_grad():
            hk, lk = [], []
            for s in range(nt, data["n_total"], bs):
                hk.append(float(kl_batch(H[s:s + bs], Fh[s:s + bs], True)))
                lk.append(float(kl_batch(H[s:s + bs], Fh[s:s + bs], False)))
        res[l] = {"heldout_kl_tuned": float(np.mean(hk)), "heldout_kl_logit": float(np.mean(lk)),
                  "accepted": bool(np.mean(hk) < np.mean(lk))}
        translators[l] = A
        logger.info(f"tuned lens L{l}: held-out KL tuned {np.mean(hk):.3f} vs logit {np.mean(lk):.3f}")
    return {"layers": res, "translators": translators, "seconds": time.time() - t0}


@torch.no_grad()
def tuned_readout(model: Any, tok: Any, recs: list[dict[str, Any]], translators: dict[int, Any],
                  accepted: list[int]) -> None:
    W = model.lm_head.weight
    for r in recs:
        Hb, Hn = r["_H"]
        for name, key in (("X", X_KEY[r["task"]]), ("SUB", SUB_KEY[r["task"]])):
            S = _lens_set(tok, key)
            for side, H in (("ban", Hb), ("neu", Hn)):
                lps, lr = [], []
                for li, l in enumerate(TL_LAYERS):
                    if l not in accepted:
                        lps.append(np.nan)
                        lr.append(np.nan)
                        continue
                    z = translators[l](torch.tensor(H[li], device=model.device).float())
                    lp = torch.log_softmax((model.model.norm(z.to(torch.bfloat16)) @ W.T).float(), -1)
                    a, rr = _readout(lp[None], S)
                    lps.append(float(a[0]))
                    lr.append(float(rr[0]))
                r[f"tl_{name}_logp_{side}"], r[f"tl_{name}_lnrank_{side}"] = lps, lr
        d = np.array(r["tl_X_lnrank_ban"]) - np.array(r["tl_X_lnrank_neu"])
        dd = np.where(np.isfinite(d), d, -np.inf)
        idx = _layer_of(dd)
        r["tl_veto_layer"] = TL_LAYERS[idx] if idx is not None else None
        d2 = np.array(r["tl_SUB_lnrank_neu"]) - np.array(r["tl_SUB_lnrank_ban"])
        idx2 = _layer_of(np.where(np.isfinite(d2), d2, -np.inf))
        r["tl_sub_rise_layer"] = TL_LAYERS[idx2] if idx2 is not None else None


def stage_lens(run_tuned: bool = True) -> dict[str, Any]:
    from engine import load_model

    fp = json.loads((PROMPTS_DIR / "frozen_prompts.json").read_text())
    samples = read_jsonl(DATA_DIR / "samples.jsonl")
    tok, model = load_model()
    t0 = time.time()
    col = collect(model, tok, fp, samples)
    recs = col["records"]
    out: dict[str, Any] = {"logit_lens": summarise(recs), "n_records": len(recs),
                           "layer_convention": "hidden_states[l], l = 0 (embeddings) .. 36 (final, normed)",
                           "seconds_logit_lens": time.time() - t0}
    if run_tuned:
        try:
            data = tl_data(model, fp, samples)
            tl = train_tuned_lens(model, data)
            acc = [l for l, v in tl["layers"].items() if v.get("accepted")]
            tuned_readout(model, tok, recs, tl["translators"], acc)
            out["tuned_lens"] = {"layers": {str(k): v for k, v in tl["layers"].items()}, "accepted_layers": acc,
                                 "n_train_tokens": data["n_train"], "n_heldout_tokens": data["n_total"] - data["n_train"],
                                 "seconds": tl["seconds"], "readout": _tl_summary(recs)}
            del data
        except torch.cuda.OutOfMemoryError as e:
            logger.error(f"tuned lens OOM, dropped (F7 drop order item 2): {e}")
            out["tuned_lens"] = {"dropped": "OOM"}
    out["records"] = [{k: v for k, v in r.items() if k != "_H"} for r in recs]
    write_json(RESULTS_DIR / "lens.json", out)
    logger.info(f"lens done: {len(recs)} records; {json.dumps(out['logit_lens'])[:600]}")
    return out


def _tl_summary(recs: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for t in TASKS:
        for mode in ("default", "substitute"):
            R = [r for r in recs if r["task"] == t and r["mode"] == mode]
            v = [r["tl_veto_layer"] for r in R if r.get("tl_veto_layer") is not None]
            s = [r["tl_sub_rise_layer"] for r in R if r.get("tl_sub_rise_layer") is not None]
            out[f"{t}_{mode}"] = {"n": len(R), "veto_median": float(np.median(v)) if v else None, "veto_n": len(v),
                                  "sub_rise_median": float(np.median(s)) if s else None, "sub_rise_n": len(s)}
    return out
