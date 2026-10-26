#!/usr/bin/env python3
"""S6: AR reconstruction (kitft/nla-qwen2.5-7b-L20-ar), the instrument gate, the layer-convention check, the
deterministic text edits and the causal deltas.

AR (mirrors nla_inference.NLACritic): the checkpoint's 21 blocks, final norm -> Identity, lm_head -> Identity,
value_head = Linear(3584, 3584, bias=False) from value_head.safetensors; input 'Summary of the following text:
<text>{explanation}</text> <summary>' tokenised with add_special_tokens=True (ids asserted to end with the sidecar's
critic_suffix_ids); prediction = value_head(h[last token]).

FVE (pre-registered): FVE_ref = 1 - mean_n ||p_n - g_n||^2 / mean_ref ||g_ref,n - mu_ref||^2 with every vector
normalised to sqrt(d) and mu_ref / denominator from the broad reference set (gate_set classes: Ultra-FineWeb,
LeetCode chat, general chat). Reported beside it: the docs formula verbatim (the set's own mean), FVE against the
training-mix denominator 0.7335, and the mean cosine per position class.

Usage: python src/nla_ar.py gate        (reference set, both conventions -> results/layer_convention.json)
       python src/nla_ar.py production  (readout gate, edits, deltas -> cache/deltas.npz, commit #3)
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (AR_ID, AR_REVISION, CACHE_DIR, DATA_DIR, D_MODEL, DOSES, FVE_PARTIAL, FVE_PASS, FVE_REF_TARGET,
                 FVE_TRAIN_DENOM, PRED_DIR, RESULTS_DIR, TASKS, TEMPLATE_IDS, model_path, read_json, read_jsonl,
                 set_ram_limit, setup_logging, sha256_text, stable_seed, utc_now, write_json, write_jsonl)

SQRT_D = float(np.sqrt(D_MODEL))
RECON = CACHE_DIR / "recon.npz"
RECON_IDX = CACHE_DIR / "recon_index.jsonl"


class AR:
    def __init__(self) -> None:
        from safetensors.torch import load_file
        from transformers import AutoModelForCausalLM, AutoTokenizer

        t0 = time.time()
        path = model_path(AR_ID, AR_REVISION)
        self.meta = yaml.safe_load(Path(path, "nla_meta.yaml").read_text())
        assert self.meta["role"] == "ar" and self.meta["d_model"] == D_MODEL
        self.mse_scale = float(self.meta["extraction"]["mse_scale"])
        assert abs(self.mse_scale - SQRT_D) < 1e-6
        self.suffix = list(self.meta["tokens"]["critic_suffix_ids"])
        self.template = self.meta["prompt_templates"]["ar"]
        self.tok = AutoTokenizer.from_pretrained(path)
        self.tok.padding_side = "right"
        bb = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                  device_map={"": 0})
        assert bb.config.num_hidden_layers == 21, bb.config.num_hidden_layers
        bb.lm_head = torch.nn.Identity()
        bb.model.norm = torch.nn.Identity()
        self.bb = bb.eval().requires_grad_(False)
        self.head = torch.nn.Linear(D_MODEL, D_MODEL, bias=False, dtype=torch.bfloat16)
        self.head.load_state_dict(load_file(str(Path(path) / "value_head.safetensors")))
        self.head = self.head.to(bb.device).eval().requires_grad_(False)
        torch.cuda.empty_cache()
        logger.info(f"AR loaded in {time.time() - t0:.0f}s (21 layers, value head); suffix {self.suffix}")

    @torch.no_grad()
    def reconstruct(self, texts: list[str], batch: int = 64) -> np.ndarray:
        out = np.zeros((len(texts), D_MODEL), dtype=np.float32)
        for s in range(0, len(texts), batch):
            part = texts[s:s + batch]
            prompts = [self.template.format(explanation=t) for t in part]
            enc = [self.tok(p, add_special_tokens=True)["input_ids"] for p in prompts]
            for ids in enc:
                assert ids[-len(self.suffix):] == self.suffix, f"critic suffix mismatch: {ids[-8:]}"
            L = max(len(x) for x in enc)
            ids = torch.full((len(enc), L), 151643, dtype=torch.long)
            mask = torch.zeros((len(enc), L), dtype=torch.long)
            for r, x in enumerate(enc):
                ids[r, :len(x)] = torch.tensor(x)
                mask[r, :len(x)] = 1
            ids, mask = ids.to(self.bb.device), mask.to(self.bb.device)
            h = self.bb.model(input_ids=ids, attention_mask=mask, use_cache=False).last_hidden_state
            last = torch.tensor([len(x) - 1 for x in enc], device=h.device)
            hl = h[torch.arange(len(enc), device=h.device), last]
            out[s:s + len(part)] = self.head(hl).float().cpu().numpy()
        return out


# ------------------------------------------------------------------------------------------------ metrics
def nrm(X: np.ndarray) -> np.ndarray:
    return X / np.linalg.norm(X, axis=-1, keepdims=True).clip(1e-12) * SQRT_D


def cos_rows(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    return (A * B).sum(-1) / (np.linalg.norm(A, axis=-1) * np.linalg.norm(B, axis=-1)).clip(1e-12)


def fve_parts(P: np.ndarray, G: np.ndarray, Gref: np.ndarray) -> dict[str, float]:
    pn, gn, rn = nrm(P), nrm(G), nrm(Gref)
    mse = ((pn - gn) ** 2).mean(-1)                      # per-vector MSE_nrm = 2(1 - cos)
    mu_ref = rn.mean(0)
    den_ref = float(((rn - mu_ref) ** 2).mean())
    mu_own = gn.mean(0)
    den_own = float(((gn - mu_own) ** 2).mean())
    return {"n": int(len(P)), "mse_nrm": float(mse.mean()), "fve_ref": float(1 - mse.mean() / den_ref),
            "fve_docs_own_mean": float(1 - mse.mean() / den_own) if den_own > 0 else None,
            "fve_train_denom": float(1 - mse.mean() / FVE_TRAIN_DENOM), "denominator_ref": den_ref,
            "denominator_own": den_own, "cos_mean": float(cos_rows(P, G).mean()),
            "cos_median": float(np.median(cos_rows(P, G)))}


def verdict(f: float) -> str:
    return "PASS" if f >= FVE_PASS else ("PARTIAL" if f >= FVE_PARTIAL else "FAIL")


def load_states() -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    idx = read_jsonl(CACHE_DIR / "states_index.jsonl")
    z = np.load(CACHE_DIR / "states_L20.npz")
    return idx, {"hs20": z["H20"], "hs21": z["H21"]}


def recon_store(ar: AR, expl: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    """Reconstruct every explanation not yet reconstructed; returns expl_id -> pred (fp32)."""
    have: dict[str, np.ndarray] = {}
    if RECON.exists():
        z = np.load(RECON)
        ids = [r["expl_id"] for r in read_jsonl(RECON_IDX)]
        have = {i: z["P"][j] for j, i in enumerate(ids)}
    todo = [e for e in expl if e["expl_id"] not in have]
    if todo:
        t0 = time.time()
        P = ar.reconstruct([e["text"] for e in todo])
        for e, p in zip(todo, P):
            have[e["expl_id"]] = p
        keys = list(have)
        np.savez(RECON, P=np.stack([have[k] for k in keys]).astype(np.float32))
        write_jsonl(RECON_IDX, [{"expl_id": k} for k in keys])
        logger.info(f"reconstructed {len(todo)} explanations in {time.time() - t0:.0f}s")
    return have


# ------------------------------------------------------------------------------------------------ gate
def stage_gate(ar: AR) -> dict[str, Any]:
    idx, H = load_states()
    row = {r["state_id"]: r for r in idx}
    expl = [e for e in read_jsonl(DATA_DIR / "explanations.jsonl") if e["kind"] in ("REF", "SMOKE")]
    pred = recon_store(ar, expl)
    out: dict[str, Any] = {"conventions": {}}
    for conv in ("hs20", "hs21"):
        es = [e for e in expl if e["convention"] == conv and e["kind"] == "REF"]
        gate = [e for e in es if e.get("gate_set")]
        P = np.stack([pred[e["expl_id"]] for e in gate])
        G = np.stack([H[conv][row[e["state_id"]]["row"]] for e in gate])
        res = {"gate_set": fve_parts(P, G, G)}
        for cls in sorted({e["ref_class"] for e in es}):
            ce = [e for e in es if e["ref_class"] == cls]
            Pc = np.stack([pred[e["expl_id"]] for e in ce])
            Gc = np.stack([H[conv][row[e["state_id"]]["row"]] for e in ce])
            res[cls] = fve_parts(Pc, Gc, G)
        sm = [e for e in expl if e["convention"] == conv and e["kind"] == "SMOKE"]
        res["smoke_cos"] = {e["expl_id"]: float(cos_rows(pred[e["expl_id"]][None],
                                                          H[conv][row[e["state_id"]]["row"]][None])[0]) for e in sm}
        out["conventions"][conv] = res
    f20 = out["conventions"]["hs20"]["gate_set"]["fve_ref"]
    f21 = out["conventions"]["hs21"]["gate_set"]["fve_ref"]
    chosen = "hs21" if f21 >= f20 + 0.05 else "hs20"
    fc = out["conventions"][chosen]["gate_set"]["fve_ref"]
    out.update({"rule": "use hidden_states[20] unless FVE_ref with hidden_states[21] is higher by >= 0.05",
                "fve_ref_hs20": f20, "fve_ref_hs21": f21, "chosen": chosen,
                "patch_block": 19 if chosen == "hs20" else 20,
                "pipeline_check": {"target": FVE_REF_TARGET, "fve_ref": fc, "within_0.10": abs(fc - FVE_REF_TARGET) <= 0.10}})
    write_json(RESULTS_DIR / "layer_convention.json", out)
    logger.info(f"layer convention: FVE_ref hs20 {f20:.3f}, hs21 {f21:.3f} -> {chosen}; pipeline check "
                f"{out['pipeline_check']}")
    return out


# ------------------------------------------------------------------------------------------------ edits
def alias_regex(aliases: list[str]) -> re.Pattern:
    parts = sorted({a.strip() for a in aliases if a.strip()}, key=len, reverse=True)
    pats = []
    for a in parts:
        p = re.escape(a)
        if re.match(r"\w", a[0]):
            p = r"(?<![\w-])" + p
        if re.match(r"\w", a[-1]):
            p = p + r"(?![\w])"
        pats.append(p)
    return re.compile("|".join(pats), re.I)


def case_like(src: str, repl: str) -> str:
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def substitute(text: str, rx: re.Pattern, repl: str) -> str:
    return rx.sub(lambda m: case_like(m.group(0), repl), text)


def unrelated_edit(text: str, lexicon_rx: re.Pattern, tok: Any, nouns: list[str]) -> tuple[str, str, str] | None:
    """Replace the first content word after the first sentence that is not in the lexicon by a neutral noun of equal
    Qwen token length. Returns (edited, old_word, new_word) or None."""
    m = re.search(r"[.!?]\s", text)
    start = m.end() if m else 0
    stop = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "be", "this", "that",
            "it", "as", "by", "at", "from", "which", "while", "its", "their", "phrase", "token", "final", "text"}
    for wm in re.finditer(r"\b[A-Za-z]{3,}\b", text[start:]):
        w = wm.group(0)
        if w.lower() in stop or lexicon_rx.search(w):
            continue
        n_w = len(tok(" " + w, add_special_tokens=False)["input_ids"])
        for nn in nouns:
            if nn.lower() == w.lower():
                continue
            if len(tok(" " + nn, add_special_tokens=False)["input_ids"]) == n_w:
                a = start + wm.start()
                new = case_like(w, nn)
                return text[:a] + new + text[a + len(w):], w, new
    return None


def stage_production(ar: AR) -> dict[str, Any]:
    import prompts as PR
    from cfg import BENCH, E8, bench_dir

    c2 = read_json(PRED_DIR / "commit2_readout.json")
    conv = read_json(RESULTS_DIR / "layer_convention.json")["chosen"]
    idx, H = load_states()
    row = {r["state_id"]: r for r in idx}
    expl = [e for e in read_jsonl(DATA_DIR / "explanations.jsonl") if e.get("convention") == conv]
    pred = recon_store(ar, expl)
    # ---------------- readout gate
    gate_ref = [e for e in expl if e["kind"] == "REF" and e.get("gate_set")]
    Gref = np.stack([H[conv][row[e["state_id"]]["row"]] for e in gate_ref])
    ro = [e for e in expl if e["kind"] in ("PREFILL", "GEN") and e["idx"] <= 3]
    gate: dict[str, Any] = {"convention": conv, "classes": {}}
    for cls in ("ALL", "READ", "SPEC", "g1", "g2", "g4", "g8", "g16"):
        es = ro if cls == "ALL" else [e for e in ro if e["pos_class"] == cls]
        if not es:
            continue
        P = np.stack([pred[e["expl_id"]] for e in es])
        G = np.stack([H[conv][row[e["state_id"]]["row"]] for e in es])
        gate["classes"][cls] = fve_parts(P, G, Gref) | {"verdict": verdict(fve_parts(P, G, Gref)["fve_ref"])}
    gate["per_task"] = {}
    for t in TASKS:
        es = [e for e in ro if e["task"] == t]
        if es:
            P = np.stack([pred[e["expl_id"]] for e in es])
            G = np.stack([H[conv][row[e["state_id"]]["row"]] for e in es])
            gate["per_task"][t] = fve_parts(P, G, Gref)
    gate["reference"] = fve_parts(np.stack([pred[e["expl_id"]] for e in gate_ref]), Gref, Gref)
    gate["verdict"] = gate["classes"]["ALL"]["verdict"]
    write_json(RESULTS_DIR / "gate.json", gate)
    logger.info(f"task gate: FVE_ref ALL {gate['classes']['ALL']['fve_ref']:.3f} -> {gate['verdict']}; "
                f"{ {k: round(v['fve_ref'], 3) for k, v in gate['classes'].items()} }")
    # per-explanation cosine (for e0 selection and the per-sample table)
    ecos = {e["expl_id"]: float(cos_rows(pred[e["expl_id"]][None], H[conv][row[e["state_id"]]["row"]][None])[0])
            for e in expl if e["state_id"] in row}
    write_json(RESULTS_DIR / "explanation_cosines.json", ecos, indent=None)
    # ---------------- edits and deltas
    by_state: dict[str, list[dict[str, Any]]] = {}
    for e in expl:
        by_state.setdefault(e["state_id"], []).append(e)
    for v in by_state.values():
        v.sort(key=lambda e: e["idx"])
    nouns_all: list[str] = []
    for t in TASKS:
        if t in ("T1", "T2"):
            continue
        nn = read_json(BENCH / bench_dir(t) / "neutral_nouns.json")
        nouns_all += [c["word"] for m in nn.values() for c in m["nouns"]]
    nouns_all = list(dict.fromkeys(nouns_all + ["house", "window", "garden", "river", "table", "chair", "music",
                                                "letter", "bottle", "mountain", "coffee", "pencil"]))
    lex = c2["lexicon"]
    edits_out, deltas, dmeta = [], {}, []
    for ct in c2["causal_plan"]:
        t, D, Y = ct["task"], ct["default"], ct["Y"]
        cat = {c["mode"]: c for c in PR.catalogue(t)}
        rxD = alias_regex(lex[t][D])
        all_aliases = [a for m in lex[t].values() for a in m]
        rx_all = alias_regex(all_aliases)
        dispD, dispY = cat[D]["display_name"], cat[Y]["display_name"]
        for w in TEMPLATE_IDS:
            for pos in ("SPEC-3", "SPEC-2", "SPEC-1", "READ"):
                sid = f"{t}|twin|-|{w}|{pos}"
                h = H[conv][row[sid]["row"]]
                hn = float(np.linalg.norm(h))
                es = by_state.get(sid, [])
                assert len(es) >= 2, f"{sid}: fewer than 2 explanations"
                named = [e for e in es if rxD.search(e["text"])]
                if named:
                    e0 = max(named, key=lambda e: ecos[e["expl_id"]])
                    cls = "SUBSTITUTION"
                    t0 = e0["text"]
                    t1 = substitute(t0, rxD, dispY)
                    e0b = next((e for e in es if e["idx"] > e0["idx"]), None) or next(e for e in es if e is not e0)
                    t0b = e0b["text"]
                else:
                    e0 = max(es, key=lambda e: ecos[e["expl_id"]])
                    cls = "INSERTION"
                    t0 = e0["text"] + f" The response will implement {dispD}."
                    t1 = e0["text"] + f" The response will implement {dispY}."
                    e0b = next((e for e in es if e["idx"] > e0["idx"]), None) or next(e for e in es if e is not e0)
                    t0b = e0b["text"] + f" The response will implement {dispD}."
                ue = unrelated_edit(t0, rx_all, ar.tok, nouns_all)
                tU = ue[0] if ue else t0 + " The weather is mild."
                rec = {"task": t, "template": w, "position": pos, "state_id": sid, "edit_class": cls,
                       "e0_id": e0["expl_id"], "e0b_id": e0b["expl_id"], "e0": t0, "e1": t1, "e0b": t0b, "eU": tU,
                       "unrelated_word": (ue[1], ue[2]) if ue else None, "Y": Y, "default": D}
                edits_out.append(rec)
        # reverse edits on ban states that name Y*
        rxY = alias_regex(lex[t][Y])
        for w in TEMPLATE_IDS:
            for pos in ("SPEC-3", "SPEC-2", "SPEC-1", "READ"):
                sid = f"{t}|ban|{D}|{w}|{pos}"
                if sid not in by_state:
                    continue
                named = [e for e in by_state[sid] if rxY.search(e["text"])]
                if named:
                    e0 = max(named, key=lambda e: ecos[e["expl_id"]])
                    edits_out.append({"task": t, "template": w, "position": pos, "state_id": sid,
                                      "edit_class": "REVERSE", "e0_id": e0["expl_id"], "e0": e0["text"],
                                      "e1": substitute(e0["text"], rxY, dispD), "Y": Y, "default": D})
    texts = sorted({x for r in edits_out for x in (r["e0"], r["e1"], r.get("e0b"), r.get("eU")) if x})
    R = dict(zip(texts, ar.reconstruct(texts)))
    unit = lambda v: v / max(float(np.linalg.norm(v)), 1e-12)
    # forced-state means for the difference-in-means direction
    for r in edits_out:
        sid = r["state_id"]
        h = H[conv][row[sid]["row"]]
        hn = float(np.linalg.norm(h))
        r0, r1 = R[r["e0"]], R[r["e1"]]
        d_edit = (unit(r1) - unit(r0)) * hn
        key = f"{r['task']}|{r['edit_class'] if r['edit_class'] == 'REVERSE' else 'TWIN'}|{r['template']}|{r['position']}"
        deltas[f"EDIT|{key}" if r["edit_class"] != "REVERSE" else f"REV|{key}"] = d_edit.astype(np.float32)
        en = float(np.linalg.norm(d_edit))
        rng = np.random.default_rng(stable_seed("rand_delta", key) % (2 ** 32))
        u = rng.standard_normal(D_MODEL).astype(np.float32)
        deltas[f"RAND|{key}"] = (unit(u) * en).astype(np.float32)
        meta = {"key": key, "edit_class": r["edit_class"], "norm_h": hn, "norm_edit": en, "ratio_edit": en / hn,
                "cos_r1_r0": float(cos_rows(r1[None], r0[None])[0]),
                "check_ratio": float(np.sqrt(max(0.0, 2 * (1 - cos_rows(r1[None], r0[None])[0]))))}
        if r["edit_class"] != "REVERSE":
            rb, rU = R[r["e0b"]], R[r["eU"]]
            deltas[f"RT|{key}"] = ((unit(rb) - unit(r0)) * hn).astype(np.float32)
            deltas[f"UNREL|{key}"] = ((unit(rU) - unit(r0)) * hn).astype(np.float32)
            fY = [H[conv][row[f"{r['task']}|forced|{r['Y']}|{ww}|{r['position']}"]["row"]] for ww in TEMPLATE_IDS]
            fD = [H[conv][row[f"{r['task']}|forced|{r['default']}|{ww}|{r['position']}"]["row"]] for ww in TEMPLATE_IDS]
            deltas[f"DIM|{key}"] = (unit(np.mean(fY, 0) - np.mean(fD, 0)) * en).astype(np.float32)
            meta.update({"ratio_rt": float(np.linalg.norm(deltas[f"RT|{key}"]) / hn),
                         "ratio_unrel": float(np.linalg.norm(deltas[f"UNREL|{key}"]) / hn),
                         "cos_edit_dim": float(cos_rows(d_edit[None], deltas[f"DIM|{key}"][None])[0]),
                         "cos_edit_rt": float(cos_rows(d_edit[None], deltas[f"RT|{key}"][None])[0])})
        dmeta.append(meta)
    np.savez(CACHE_DIR / "deltas.npz", **{k.replace("|", "__"): v for k, v in deltas.items()})
    write_jsonl(RESULTS_DIR / "edits.jsonl", edits_out)
    write_json(RESULTS_DIR / "deltas_meta.json", dmeta)
    from commit import commit
    dsha = {k: sha256_text(v.tobytes().hex()[:2_000_000]) for k, v in deltas.items()}
    c3 = {"gate_verdict": gate["verdict"], "gate_fve_ref_all": gate["classes"]["ALL"]["fve_ref"], "convention": conv,
          "patch_block": 19 if conv == "hs20" else 20, "causal_plan": c2["causal_plan"], "doses": list(DOSES),
          "cells": c2["causal_cells"], "N_per_cell": 30,
          "edits": [{k: r[k] for k in ("task", "template", "position", "edit_class", "e0", "e1", "e0b", "eU") if k in r}
                    for r in edits_out], "delta_sha256": dsha,
          "edit_classes": {t: dict(__import__("collections").Counter(r["edit_class"] for r in edits_out if r["task"] == t))
                           for t in {r["task"] for r in edits_out}}}
    rec = commit("commit3_causal", c3)
    logger.info(f"commit3: {rec['chain'][:12]}; {len(deltas)} deltas; classes {c3['edit_classes']}")
    return c3


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["gate", "production"])
    args = ap.parse_args()
    setup_logging(f"ar_{args.stage}")
    set_ram_limit(60)
    ar = AR()
    if args.stage == "gate":
        stage_gate(ar)
    else:
        stage_production(ar)
    (DATA_DIR / f"flag_ar_{args.stage}.done").write_text(utc_now())


if __name__ == "__main__":
    main()
