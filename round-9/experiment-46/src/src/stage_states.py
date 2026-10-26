#!/usr/bin/env python3
"""Stage 1 (M-name reproduction) and Stage 5 (M-desc, M-lex, ban, M-code states) on the truncated decoders.

Reuses iteration 8's states.py unchanged (load_truncated with _skip_upper_layers, CPU embedding table, forward hooks,
hook_check, spec_span, smean_states). S-mean states are read with batch 1 (no padding effects), as iteration 8 did.
The S-mean span lies in the user turn, so the thinking switch of the chat template (which only changes the
assistant prefix) cannot change it: asserted on the first prompts of every family.
"""

from __future__ import annotations

import ast
import gc
import io
import re
import time
import tokenize
from typing import Any

import numpy as np
from loguru import logger

import geometry
import prompts_tp
import states
from common import CANON_ORDER, deviation, read_json, read_jsonl, sha256_text, timing, utc_now, write_json
from tpg import DATA, IN_E44, K_VERDICT, MODELS, NB5, RESULTS, REPRO_GATE, STATES_DIR, B5


# ---------------------------------------------------------------------------------------------- model handling
def load(model_tag: str) -> tuple[Any, Any, dict[str, Any]]:
    import torch

    cfg = MODELS[model_tag]
    model, tok, info = states.load_truncated(cfg["repo"], cfg["precision"], cfg["n_keep"], revision=cfg["revision"])
    tok.padding_side = "right"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    info["gpu_name"] = torch.cuda.get_device_name(0)
    return model, tok, info


def unload(model: Any) -> None:
    import torch

    del model
    gc.collect()
    torch.cuda.empty_cache()


def smean_family(model: Any, tok: Any, prompts: list[str], blocks: list[int], name: str) -> tuple[np.ndarray, dict]:
    """S-mean states of a prompt family (user turn = prompt; SPEC span), batch 1, float32 -> caller casts."""
    spec = prompts_tp.SPEC()
    texts = [prompts_tp.render_chat(tok, p, True) for p in prompts]
    # the span is identical with the thinking switch off (it lies in the user turn)
    chk = []
    for p in prompts[:3]:
        a = states.spec_span(tok, prompts_tp.render_chat(tok, p, True), spec)
        b = states.spec_span(tok, prompts_tp.render_chat(tok, p, False), spec)
        ta = tok(prompts_tp.render_chat(tok, p, True), add_special_tokens=False)["input_ids"]
        tb = tok(prompts_tp.render_chat(tok, p, False), add_special_tokens=False)["input_ids"]
        chk.append({"span_equal": a[0] == b[0], "prefix_equal": ta[:max(a[0]) + 1] == tb[:max(b[0]) + 1],
                    **a[1]})
    assert all(c["span_equal"] and c["prefix_equal"] and c["decoded_equals_spec"] for c in chk), chk
    t0 = time.time()
    X = states.smean_states(model, tok, texts, spec, blocks, batch=1)
    dt = time.time() - t0
    timing(f"smean_{name}", dt, len(texts))
    logger.info(f"S-mean {name}: {X.shape} in {dt:.0f}s ({dt / max(len(texts), 1):.2f}s/prompt)")
    ids = [tok(t, add_special_tokens=False)["input_ids"] for t in texts]
    return X, {"span_checks": chk, "seconds": round(dt, 1), "n": len(texts),
               "n_tokens": [len(i) for i in ids], "prompt_sha256": [sha256_text(p) for p in prompts]}


# ---------------------------------------------------------------------------------------------- Stage 1: M-name
def stage_mname(model_tag: str = "32b", n: int = 0) -> None:
    import torch

    cfg = MODELS[model_tag]
    items = prompts_tp.forced_set()
    if n:
        items = items[:n]
    model, tok, info = load(model_tag)
    texts = [prompts_tp.render_chat(tok, it["prompt"], True) for it in items]
    hc = states.hook_check(model, tok, texts[:2])
    logger.info(f"hook check {hc}")
    assert hc["pass"], f"hook check failed {hc}"
    X, meta = smean_family(model, tok, [it["prompt"] for it in items], cfg["ext_blocks"], f"mname_{model_tag}")
    # attention-kernel sensitivity: 10 prompts with eager attention (same weights)
    sens: dict[str, Any] = {}
    try:
        idx = list(range(0, len(items), max(1, len(items) // 10)))[:10]
        model.set_attn_implementation("eager")
        Xe = states.smean_states(model, tok, [texts[i] for i in idx], prompts_tp.SPEC(), cfg["ext_blocks"], batch=1)
        model.set_attn_implementation("sdpa")
        bi = cfg["ext_blocks"].index(cfg["ref_block"])
        a, b = X[idx, bi].astype(np.float64), Xe[:, bi].astype(np.float64)
        cos = (a * b).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
        sens = {"n": len(idx), "block": cfg["ref_block"], "cosine_min": float(cos.min()),
                "cosine_median": float(np.median(cos)), "max_abs_diff": float(np.abs(a - b).max())}
    except (AttributeError, ValueError, RuntimeError, TypeError) as e:
        sens = {"skipped": f"{type(e).__name__}: {e}"}
    logger.info(f"sdpa vs eager: {sens}")
    tag = "full" if not n else f"n{n}"
    np.savez_compressed(STATES_DIR / f"mname_{model_tag}{'' if not n else '_' + tag}.npz",
                        smean=X.astype(np.float16), blocks=np.array(cfg["ext_blocks"]),
                        algorithm=np.array([it["algorithm"] for it in items]),
                        group=np.array([it["group"] for it in items]),
                        template=np.array([it["template"] for it in items]),
                        alias=np.array([it["alias"] for it in items]),
                        prompt_sha256=np.array(meta["prompt_sha256"]))
    rec = {"model": cfg, "load": info, "hook_check": hc, "span_checks": meta["span_checks"],
           "seconds": meta["seconds"], "n": len(items), "sdpa_vs_eager": sens, "utc": utc_now(),
           "gpu": torch.cuda.get_device_name(0)}
    write_json(RESULTS / f"states_mname_{model_tag}{'' if not n else '_' + tag}.json", rec)
    unload(model)
    if not n:
        repro_check(model_tag)


def _class_matrix_from_geo(geo: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return geometry.class_matrix(geo, labels, CANON_ORDER)


def load_e44_smean(name: str) -> dict[str, Any]:
    """Iteration-8 state file; files over the 100 MB repository limit are stored split by block range
    (<name>_part1.npz, <name>_part2.npz, ...) and concatenated here."""
    p = IN_E44 / "states" / name
    if p.exists():
        z = np.load(p)
        return {k: z[k] for k in z.files}
    parts = sorted((IN_E44 / "states").glob(name.replace(".npz", "_part*.npz")))
    if not parts:
        raise FileNotFoundError(p)
    zs = [np.load(q) for q in parts]
    d = {k: zs[0][k] for k in zs[0].files if k not in ("smean", "part_blocks")}
    d["smean"] = np.concatenate([z["smean"] for z in zs], axis=1)
    assert d["smean"].shape[1] == len(d["blocks"])
    return d


def repro_check(model_tag: str = "32b") -> dict[str, Any]:
    """Compare new M-name states with iteration 8's cached states (cosines, geodesic Spearman, classes)."""
    from scipy.stats import spearmanr

    cfg = MODELS[model_tag]
    z = np.load(STATES_DIR / f"mname_{model_tag}.npz")
    X = z["smean"].astype(np.float64)
    labels = z["algorithm"]
    blocks = [int(b) for b in z["blocks"]]
    ref_name = "smean_C6_nf4.npz" if model_tag == "32b" else "smean_C1_bf16.npz"
    zr = load_e44_smean(ref_name)
    F = zr["kind"] == "forced"
    Xr = zr["smean"][F].astype(np.float64)
    assert list(zr["algorithm"][F]) == list(labels), "prompt order differs from iteration 8"
    rblocks = [int(b) for b in zr["blocks"]]
    out: dict[str, Any] = {"model": model_tag, "reference": ref_name, "utc": utc_now()}
    cos_by_block = {}
    for b in blocks:
        if b in rblocks:
            a, r = X[:, blocks.index(b)], Xr[:, rblocks.index(b)]
            c = (a * r).sum(1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(r, axis=1))
            cos_by_block[b] = {"min": float(c.min()), "median": float(np.median(c))}
    out["cosine_by_block"] = cos_by_block
    L = cfg["ref_block"] if model_tag == "32b" else 17
    iu = np.triu_indices(10, 1)
    res_k = {}
    for k in (5, 10, 15):
        geo_new, info = geometry.geodesics(X[:, blocks.index(L)], k)
        geo_ref, _ = geometry.geodesics(Xr[:, rblocks.index(L)], k)
        Mn, Mr = _class_matrix_from_geo(geo_new, labels), _class_matrix_from_geo(geo_ref, labels)
        Mn_s, Mr_s = (Mn + Mn.T) / 2, (Mr + Mr.T) / 2
        rho = float(spearmanr(Mn_s[iu], Mr_s[iu]).statistic)
        g_new, near_new = geometry.g_values(geo_new, labels, B5, NB5)
        g_ref, near_ref = geometry.g_values(geo_ref, labels, B5, NB5)
        cl_new, _ = geometry.classify(g_new)
        cl_ref, _ = geometry.classify(g_ref)
        res_k[k] = {"spearman_class_geodesic": rho, "classes_new": cl_new, "classes_ref": cl_ref,
                    "classes_equal": cl_new == cl_ref, "g_new": g_new, "g_ref": g_ref,
                    "components": info["components_before_join"]}
    out["by_k"] = res_k
    if model_tag == "32b":
        zg = np.load(IN_E44 / "states" / "geo_C6_nf4.npz")
        Mg = _class_matrix_from_geo(zg["geo_k15"], zg["labels"])
        geo_new, _ = geometry.geodesics(X[:, blocks.index(31)], 15)
        Mn = _class_matrix_from_geo(geo_new, labels)
        rho = float(spearmanr(((Mn + Mn.T) / 2)[iu], ((Mg + Mg.T) / 2)[iu]).statistic)
        land = read_json(IN_E44 / "results" / "landing.json")["primary"]
        g_new, _ = geometry.g_values(geo_new, labels, B5, NB5)
        cl_new, _ = geometry.classify(g_new)
        out["G_repro"] = {"spearman_vs_geo_C6_nf4_k15_block31": rho, "gate": REPRO_GATE,
                          "pass": rho >= REPRO_GATE and cl_new == land["classes"],
                          "classes_new": cl_new, "classes_e44": land["classes"], "g_new": g_new, "g_e44": land["g"],
                          "max_abs_g_diff": max(abs(g_new[a] - land["g"][a]) for a in NB5)}
        logger.info(f"G-repro: rho={rho:.4f} classes equal={cl_new == land['classes']} -> {out['G_repro']['pass']}")
        if not out["G_repro"]["pass"]:
            band = "0.85-0.95: proceed with new states" if rho >= 0.85 else "< 0.85: iteration 8 did not reproduce"
            deviation("F1-repro", f"M-name reproduction rho={rho:.3f} ({band})")
    write_json(RESULTS / f"repro_mname_{model_tag}.json", out)
    return out


__all__ = ["stage_mname", "repro_check", "load", "unload", "smean_family", "ast", "io", "re", "tokenize",
           "read_jsonl", "DATA", "K_VERDICT"]


# ---------------------------------------------------------------------------------------------- Stage 5
def _commit_done(label: str) -> bool:
    from common import commit_time

    return commit_time(label) is not None


def ban_prompts() -> list[dict[str, Any]]:
    return [prompts_tp.ban_prompt(B5, w, i, "ban") for i, w in enumerate(("W1", "W2", "W3", "W4", "W5", "P6", "P7"))]


def extract_mlex(model: Any, tok: Any, model_tag: str) -> None:
    assert _commit_done("COMMIT1a"), "M-lex states require COMMIT #1a"
    cfg = MODELS[model_tag]
    ml = read_json(DATA / "mlex_prompts.json")["rows"]
    Xa, ma = smean_family(model, tok, [r["prompt"] for r in ml], cfg["ext_blocks"], f"mlex_alias_{model_tag}")
    Xt, mt = smean_family(model, tok, [r["twin_prompt"] for r in ml], cfg["ext_blocks"], f"mlex_twin_{model_tag}")
    assert ma["n_tokens"] == mt["n_tokens"], "alias/twin token counts differ"
    np.savez_compressed(STATES_DIR / f"mlex_{model_tag}.npz", alias=Xa.astype(np.float16), twin=Xt.astype(np.float16),
                        delta=(Xa - Xt).astype(np.float16), blocks=np.array(cfg["ext_blocks"]),
                        algorithm=np.array([r["algorithm"] for r in ml]), group=np.array([r["group"] for r in ml]),
                        template=np.array([r["template"] for r in ml]), alias_index=np.array([r["alias_index"] for r in ml]))
    write_json(RESULTS / f"states_mlex_{model_tag}.json", {"alias": {k: v for k, v in ma.items() if k != "n_tokens"},
                                                           "twin": {k: v for k, v in mt.items() if k != "n_tokens"},
                                                           "token_counts_equal": True, "utc": utc_now()})


def extract_ban(model: Any, tok: Any, model_tag: str) -> None:
    cfg = MODELS[model_tag]
    items = ban_prompts()
    X, m = smean_family(model, tok, [it["prompt"] for it in items], cfg["ext_blocks"], f"ban_{model_tag}")
    np.savez_compressed(STATES_DIR / f"ban_{model_tag}.npz", smean=X.astype(np.float16),
                        blocks=np.array(cfg["ext_blocks"]), template=np.array([it["template"] for it in items]))


def extract_mdesc(model: Any, tok: Any, model_tag: str) -> None:
    assert _commit_done("COMMIT1b"), "M-desc states require COMMIT #1b"
    cfg = MODELS[model_tag]
    rows = read_json(DATA / "mdesc_prompts.json")["rows"]
    X, m = smean_family(model, tok, [r["prompt"] for r in rows], cfg["ext_blocks"], f"mdesc_{model_tag}")
    np.savez_compressed(STATES_DIR / f"mdesc_{model_tag}.npz", smean=X.astype(np.float16),
                        blocks=np.array(cfg["ext_blocks"]), algorithm=np.array([r["algorithm"] for r in rows]),
                        group=np.array([r["group"] for r in rows]), template=np.array([r["template"] for r in rows]),
                        desc_index=np.array([r["desc_index"] for r in rows]),
                        desc_id=np.array([r["desc_id"] for r in rows]))
    write_json(RESULTS / f"states_mdesc_{model_tag}.json", {k: v for k, v in m.items() if k != "n_tokens"})


def stage_states(*args: str) -> None:
    """args: model tag ('32b' | '8b') then any of mname, mlex, ban, mdesc, mcode (default: all available)."""
    model_tag = args[0] if args else "32b"
    which = list(args[1:]) or ["mlex", "ban", "mdesc", "mcode"]
    model, tok, info = load(model_tag)
    hc = states.hook_check(model, tok, [prompts_tp.render_chat(tok, prompts_tp.forced_prompt("bfs", 0, 0)["prompt"],
                                                                True)])
    assert hc["pass"], hc
    write_json(RESULTS / f"load_{model_tag}_{'_'.join(which)}.json", {"load": info, "hook_check": hc, "utc": utc_now()})
    for w in which:
        t0 = time.time()
        if w == "mname":
            X, meta = smean_family(model, tok, [it["prompt"] for it in prompts_tp.forced_set()],
                                   MODELS[model_tag]["ext_blocks"], f"mname_{model_tag}")
            items = prompts_tp.forced_set()
            np.savez_compressed(STATES_DIR / f"mname_{model_tag}.npz", smean=X.astype(np.float16),
                                blocks=np.array(MODELS[model_tag]["ext_blocks"]),
                                algorithm=np.array([it["algorithm"] for it in items]),
                                group=np.array([it["group"] for it in items]),
                                template=np.array([it["template"] for it in items]),
                                alias=np.array([it["alias"] for it in items]),
                                prompt_sha256=np.array(meta["prompt_sha256"]))
        elif w == "mlex":
            extract_mlex(model, tok, model_tag)
        elif w == "ban":
            extract_ban(model, tok, model_tag)
        elif w == "mdesc":
            extract_mdesc(model, tok, model_tag)
        elif w == "mcode":
            import stage_mcode

            stage_mcode.extract_mcode(model, tok, model_tag)
        logger.info(f"{w} {model_tag} done in {time.time() - t0:.0f}s")
    unload(model)
    if "mname" in which and model_tag == "8b":
        repro_check("8b")
