#!/usr/bin/env python3
"""HF FP8 engine stages: S4 smoke tests (U1-U5, U7), S6 engine check, S7 the 2x2 (thinking off), S8 optional arms.

Every batch has exactly B rows of ONE (task, template) (B fixed per task, results/batch_sizes.json), prune=False,
so a slot's noise stream and the batch shape are identical in every condition (exact CRN coupling, verified by U1 and
by the filler repeats). Prefill groups: the clean twin, or PN(d, alpha) = exp17 make_edits('RAND') with u = D_d at
block outputs 12-23 and positions S = [p1, spec_end), prefill only. Rows stream to data/samples_raw.jsonl (resumable).
"""

from __future__ import annotations

import gc
import json
import time
from collections import defaultdict
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (D_MODEL, DATA_DIR, MODEL_ID, MODEL_REVISION, N_LAYERS, QUANT, RESULTS_DIR, ROOT, TEMPLATE_IDS,
                 V_BLOCKS, append_jsonl, read_json, read_jsonl, sha256_text, stable_seed, utc_now, write_json)
from cfg4 import (KV_BYTES_PER_TOKEN, MAX_NEW4, MINP_P, MINP_T, PN_ALPHAS, PN_SEEDS, PN_TEMPS, SEED_K, TEMPS, TOPK_K,
                  TOPK_T, TPN_ALPHA, TPN_MAX_NEW, TPN_T, MemWatch, cond_nopn, cond_pn, fmt_t, wall_guard)
from engine import load_model, prefill, u_stream
from engine4 import _inverse_cdf, gumbel_pick, mask_probs, sample4
from hooks import make_edits
from prompts import load_prompts

RAW = DATA_DIR / "samples_raw.jsonl"
RAW_SMOKE = DATA_DIR / "raw_smoke_hf.jsonl"
REALISED = DATA_DIR / "realised_norms.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
BSIZES = RESULTS_DIR / "batch_sizes.json"
T0F = RESULTS_DIR / "t0.json"
NORM_BLOCKS = list(range(12, N_LAYERS))
SITE = "spec_blocks12-23_prefill"
_MODEL: dict[str, Any] = {}


# ------------------------------------------------------------------------------------------------ model / B
def get_model() -> tuple[Any, Any]:
    if "m" not in _MODEL:
        from memwatch import MemWatchRSS
        MemWatchRSS(26.0).start()
        tok, model = load_model(fp8=True)
        _MODEL.update(m=model, t=tok)
    return _MODEL["t"], _MODEL["m"]


def batch_sizes(model: Any, prompts: dict) -> dict[str, int]:
    """B per task = largest of {20, 10, 5} with B * (P + max_new + 1) * 147,456 <= 0.85 * free VRAM after loading.
    Decided once and persisted (the batch shape must be constant across every stage and process)."""
    if BSIZES.exists():
        return read_json(BSIZES)["B"]
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info(0)
    cap = torch.cuda.get_device_properties(0).total_memory * 0.97 - torch.cuda.memory_allocated(0)
    budget = 0.85 * min(free, cap)
    out, detail = {}, {}
    for key, task, max_new, thinking in (("T2", "T2", MAX_NEW4["T2"], False), ("T03", "T03", MAX_NEW4["T03"], False),
                                         ("T1", "T1", MAX_NEW4["T1"], False), ("T2think", "T2", TPN_MAX_NEW, True)):
        pmax = max(prompts[(task, w, "twin")]["P"] for w in TEMPLATE_IDS)
        lmax = pmax + max_new + 1
        b = next((b for b in (20, 10, 5) if b * lmax * KV_BYTES_PER_TOKEN <= budget), 5)
        out[key] = b
        detail[key] = {"Pmax": pmax, "max_new": max_new, "Lmax": lmax, "kv_bytes_at_B": b * lmax * KV_BYTES_PER_TOKEN}
    write_json(BSIZES, {"B": out, "free_vram_after_load": free, "budget_0.85": budget, "detail": detail,
                        "utc": utc_now()})
    logger.info(f"batch sizes {out} (free after load {free / 1e9:.2f} GB, budget {budget / 1e9:.2f} GB)")
    return out


# ------------------------------------------------------------------------------------------------ context
def unit_norms(task: str, engine_check: bool = False) -> np.ndarray:
    if task == "T03" and not engine_check:
        return np.load(ROOT / "inputs/exp13/results/tensors/norms_T03.npz")["norm"]
    return np.load(ROOT / "directions" / f"norms_{task}.npy")


def direction(seed: int) -> np.ndarray:
    p = ROOT / "directions" / f"rand_{seed}.npy"
    if not p.exists():
        x = np.random.Generator(np.random.PCG64(seed)).standard_normal(D_MODEL)
        np.save(p, (x / np.linalg.norm(x)).astype(np.float32))
    return np.load(p)


def thinking_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True, add_generation_prompt=True,
                                  enable_thinking=True)
    return list(ids["input_ids"] if isinstance(ids, dict) else ids)


class Ctx4:
    """Per task: clean twin prefill per template (S and R states captured at blocks 12-35) and PN prefills."""

    def __init__(self, model: Any, tok: Any, prompts: dict, task: str, thinking: bool = False,
                 engine_check: bool = False):
        self.model, self.tok, self.task, self.thinking = model, tok, task, thinking
        dev = model.device
        self.pr = {}
        for w in TEMPLATE_IDS:
            r = prompts[(task, w, "twin")]
            ids = r["ids"]
            if thinking:
                on = thinking_ids(tok, r["user_text"])
                assert ids[:len(on)] == on, "thinking-on prompt must be a prefix of the thinking-off prompt"
                ids = on
            self.pr[w] = {"ids": ids, "a": r["p1"], "b": r["spec_end"], "P": len(ids),
                          "sha": sha256_text(json.dumps(ids))}
        n = unit_norms(task, engine_check)
        self.unit_src = "exp17 norms" if (task != "T03" or engine_check) else "exp13 norms (protocol v4)"
        self.n = {l: torch.tensor(n[j], device=dev) for j, l in enumerate(V_BLOCKS)}
        self.dirs: dict[int, torch.Tensor] = {}
        self.clean_cache: dict[str, dict[str, Any]] = {}

    def u(self, seed: int) -> torch.Tensor:
        if seed not in self.dirs:
            self.dirs[seed] = torch.tensor(direction(seed), device=self.model.device)
        return self.dirs[seed]

    def _cap(self, a: int, b: int, P: int, cap: dict, capR: dict):
        def mk(l):
            def g(h):
                cap[l] = h[0, a:b].float().clone()
                capR[l] = h[0, P - 1].float().clone()
            return g
        return {l: mk(l) for l in NORM_BLOCKS}

    def clean(self, w: str) -> dict[str, Any]:
        if w not in self.clean_cache:
            p = self.pr[w]
            cap, capR = {}, {}
            pre = prefill(self.model, p["ids"], capture=self._cap(p["a"], p["b"], p["P"], cap, capR))
            self.clean_cache[w] = {"pre": pre, "S": cap, "R": capR}
        return self.clean_cache[w]

    def pn(self, w: str, seed: int, alpha: float, counter: dict | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        p = self.pr[w]
        twin = self.clean(w)
        a, b, P = p["a"], p["b"], p["P"]
        uu = self.u(seed)
        log: dict[int, list[float]] = {}
        edits = make_edits("RAND", a, b, {l: uu for l in V_BLOCKS}, self.n, {l: twin["S"][l] for l in V_BLOCKS},
                           alpha=alpha, log=log)
        if counter is not None:
            def wrap(f):
                def g(h):
                    counter["n"] = counter.get("n", 0) + 1
                    return f(h)
                return g
            edits = {l: wrap(f) for l, f in edits.items()}
        cap, capR = {}, {}
        pre = prefill(self.model, p["ids"], edits=edits, capture=self._cap(a, b, P, cap, capR))
        rel = {}
        for l in V_BLOCKS:
            comp = (cap[l] - twin["S"][l]) @ uu
            tgt = alpha * self.n[l]
            rel[l] = float(((comp - tgt).abs() / tgt.abs().clamp(min=1e-6)).mean())
        rec = {"task": self.task, "w": w, "dir_seed": seed, "alpha": alpha, "thinking": self.thinking,
               "unit": self.unit_src, "rel_err_along_u": rel,
               "disp_S_mean_norm": {l: float((cap[l] - twin["S"][l]).norm(dim=-1).mean()) for l in NORM_BLOCKS},
               "disp_R_norm": {l: float((capR[l] - twin["R"][l]).norm()) for l in NORM_BLOCKS},
               "target_norm_mean": {l: float(alpha * self.n[l].mean()) for l in V_BLOCKS}, "utc": utc_now()}
        return pre, rec

    def free(self) -> None:
        self.clean_cache.clear()
        gc.collect()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ rows
def spec(arm: str, k: int, T: float, group: Any = "clean", top_k: int = 0, min_p: float = 0.0,
         coupling: str = "invcdf", tier: int = 0, filler: bool = False, ns: str | None = None) -> dict[str, Any]:
    return {"arm": arm, "k": k, "T": T, "group": group, "top_k": top_k, "min_p": min_p, "coupling": coupling,
            "tier": tier, "filler": filler, "ns": ns}


def done_keys() -> set[tuple[str, str, str, int]]:
    return {(r["task"], r["template"], r["arm"], int(r["sample_id"])) for r in read_jsonl(RAW)}


def run_batch4(ctx: Ctx4, w: str, specs: list[dict[str, Any]], block_id: str, max_new: int, B: int,
               raw_file=RAW, force_len: bool = False, extra: dict | None = None) -> list[dict[str, Any]]:
    assert len(specs) == B, f"batch must have exactly B={B} rows, got {len(specs)}"
    task, tok, model = ctx.task, ctx.tok, ctx.model
    t0 = time.time()
    groups: dict[Any, dict[str, Any]] = {}
    recs: dict[Any, dict[str, Any]] = {}
    for s in specs:
        g = s["group"]
        if g not in groups:
            if g == "clean":
                groups[g] = {"pre": ctx.clean(w)["pre"], "rows": [], "specs": []}
            else:
                _, seed, alpha = g
                pre, rec = ctx.pn(w, seed, alpha)
                groups[g] = {"pre": pre, "rows": [], "specs": []}
                recs[g] = rec
        key = (s["ns"], task, w, s["k"]) if s["ns"] else (task, w, s["k"])
        groups[g]["rows"].append({"u": u_stream(*key, n=max_new) if s["coupling"] == "invcdf" else None,
                                  "T": s["T"], "top_k": s["top_k"], "min_p": s["min_p"], "coupling": s["coupling"],
                                  "gseed": stable_seed(*key, "gumbel")})
        groups[g]["specs"].append(s)
    if recs:
        append_jsonl(REALISED, [{**r, "block_id": block_id} for r in recs.values()])
    glist = list(groups.values())
    res = sample4(model, glist, max_new, force_len=force_len)
    out = []
    pos = 0
    p = ctx.pr[w]
    for g in glist:
        for s in g["specs"]:
            r = res[pos]
            key = (s["ns"], task, w, s["k"]) if s["ns"] else (task, w, s["k"])
            rec = recs.get(s["group"])
            text = tok.decode(r["token_ids"], skip_special_tokens=True)
            row = {"task": task, "template": w, "arm": s["arm"], "condition": s["arm"], "sample_id": s["k"],
                   "slot": "|".join(str(x) for x in key), "seed": stable_seed(*key),
                   "token_seed": stable_seed(*key) if s["coupling"] == "invcdf" else stable_seed(*key, "gumbel"),
                   "family": "pn" if s["group"] != "clean" else "nopn", "site": SITE if s["group"] != "clean" else None,
                   "alpha": s["group"][2] if s["group"] != "clean" else None,
                   "direction_seed": s["group"][1] if s["group"] != "clean" else None,
                   "temperature": s["T"], "top_k": s["top_k"], "min_p": s["min_p"], "coupling": s["coupling"],
                   "thinking": ctx.thinking, "repeat": s["filler"], "model": MODEL_ID, "model_revision": MODEL_REVISION,
                   "quant": QUANT, "engine": "hf-fp8-w8a8 (exp17 engine + engine4.sample4)", "unit": ctx.unit_src,
                   "prompt_sha256": p["sha"], "B": B, "batch_pos": pos, "max_new": max_new, "block_id": block_id,
                   "disp_S_mean_b23": rec["disp_S_mean_norm"][23] if rec else 0.0,
                   "disp_S_mean_b35": rec["disp_S_mean_norm"][35] if rec else 0.0,
                   "disp_R_b35": rec["disp_R_norm"][35] if rec else 0.0,
                   "rel_err_along_u_max": max(rec["rel_err_along_u"].values()) if rec else None,
                   "text": text, "token_ids": r["token_ids"], "n_tokens": r["n_tokens"], "n_new_tokens": r["n_tokens"],
                   "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"], "utc": utc_now(),
                   **(extra or {})}
            out.append(row)
            pos += 1
    append_jsonl(raw_file, out)
    dt = time.time() - t0
    append_jsonl(TIMING, [{"block_id": block_id, "task": task, "w": w, "B": B, "seconds": dt,
                           "steps": res[0]["steps"], "max_new": max_new, "utc": utc_now()}])
    logger.info(f"{block_id} {task}/{w}: {dt:.1f}s, {res[0]['steps']} steps, max len "
                f"{max(r['n_tokens'] for r in res)}, arms {sorted({s['arm'] for s in specs})[:4]}...")
    return out


# ------------------------------------------------------------------------------------------------ layouts
def layout_2x2(B: int) -> list[list[dict[str, Any]]]:
    """Committed layout (prereg layout_rule): 120 rows per (task, template), tier 0 first, sorted by (-T, filler,
    group, slot); filler rows follow their originals so each repeat has different batch-mates."""
    rows = []
    for k in SEED_K:
        for t in TEMPS:
            rows.append(spec(cond_nopn(t), k, t))
        rows.append(spec(f"TOPK{TOPK_K}_T{fmt_t(TOPK_T)}", k, TOPK_T, top_k=TOPK_K))
        rows.append(spec("FILLER_T1.0", k, 1.0, filler=True))
    for d in PN_SEEDS:
        for a in PN_ALPHAS:
            for k in SEED_K:
                for t in PN_TEMPS:
                    rows.append(spec(cond_pn(d, a, t), k, t, group=("pn", d, a), tier=0 if a == 1.0 else 1))
    rows.sort(key=lambda r: (r["tier"], -r["T"], r["filler"], r["group"] != "clean", str(r["group"]), r["k"],
                             r["top_k"]))
    batches = [rows[i:i + B] for i in range(0, len(rows), B)]
    assert all(len(b) == B for b in batches), "120 rows must divide into batches of B"
    for b in batches:   # filler rows never share a batch with their originals
        fill = {r["k"] for r in b if r["filler"]}
        orig = {r["k"] for r in b if r["arm"] == "NOPN_T1.0"}
        assert not (fill & orig), "filler repeat shares a batch with its original"
    return batches


def pad(rows: list[dict[str, Any]], B: int, arm: str, T: float, coupling: str = "invcdf",
        start_k: int = 4) -> list[list[dict[str, Any]]]:
    batches = [rows[i:i + B] for i in range(0, len(rows), B)]
    if batches and len(batches[-1]) < B:
        k = start_k
        while len(batches[-1]) < B:
            batches[-1].append(spec(arm, k, T, coupling=coupling))
            k += 1
    return batches


# ------------------------------------------------------------------------------------------------ S4 smoke
def run_smoke() -> dict[str, Any]:
    tok, model = get_model()
    prompts = load_prompts()
    Bs = batch_sizes(model, prompts)
    res: dict[str, Any] = {"utc": utc_now(), "B": Bs}
    ctx = Ctx4(model, tok, prompts, "T2")
    B = Bs["T2"]
    mx = MAX_NEW4["T2"]
    # U1: same slot, different positions and batch-mates
    a = [spec("SMOKE_T1.0", k, 1.0, ns="smoke") for k in range(B)]
    b = [spec("SMOKE_T1.0", 1, 1.0, ns="smoke")] + [spec("SMOKE_T1.0", 100 + k, 1.0, ns="smoke")
                                                     for k in range(B - 2)] + [spec("SMOKE_T1.0", 0, 1.0, ns="smoke")]
    ra = run_batch4(ctx, "W1", a, "smoke:U1a", mx, B, raw_file=RAW_SMOKE)
    rb = run_batch4(ctx, "W1", b, "smoke:U1b", mx, B, raw_file=RAW_SMOKE)
    by_a = {r["sample_id"]: r for r in ra}
    by_b = {r["sample_id"]: r for r in rb}
    u1 = []
    for k in (0, 1):
        x, y = by_a[k]["token_ids"], by_b[k]["token_ids"]
        d = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), None)
        u1.append({"slot": k, "identical": x == y, "first_divergence": d, "n_tokens": (len(x), len(y)),
                   "positions": (by_a[k]["batch_pos"], by_b[k]["batch_pos"])})
    res["U1_crn_exactness"] = {"pass": all(z["identical"] for z in u1), "rows": u1}
    # U2: per-row temperature: slot 0 at T1.0 in a mixed-T batch == same row in the all-T1.0 batch (U1a)
    mix_T = [1.0] + [TEMPS[i % 4] if TEMPS[i % 4] != 1.0 else 1.3 for i in range(1, B)]
    c = [spec("SMOKE_MIX", k, mix_T[k], ns="smoke") for k in range(B)]
    rc = run_batch4(ctx, "W1", c, "smoke:U2", mx, B, raw_file=RAW_SMOKE)
    res["U2_per_row_temperature"] = {"pass": rc[0]["token_ids"] == by_a[0]["token_ids"],
                                     "n_tokens": rc[0]["n_tokens"]}
    # U3: hook
    counter: dict[str, int] = {}
    pre_e, rec = ctx.pn("W1", PN_SEEDS[0], 1.0, counter=counter)
    n_prefill_calls = counter.get("n", 0)
    g = [{"pre": pre_e, "rows": [{"u": u_stream("smoke", "T2", "W1", k, n=8), "T": 1.0, "top_k": 0, "min_p": 0.0,
                                  "coupling": "invcdf", "gseed": 0} for k in range(B)]}]
    sample4(model, g, 8)
    pre0, _ = ctx.pn("W1", PN_SEEDS[0], 0.0)
    d0 = float((pre0["r_logits"] - ctx.clean("W1")["pre"]["r_logits"]).abs().max())
    rel_max = max(rec["rel_err_along_u"].values())
    pre2, rec2 = ctx.pn("W1", PN_SEEDS[0], 2.0)
    rel_max2 = max(rec2["rel_err_along_u"].values())
    res["U3_hook"] = {"pass": rel_max < 1e-3 and rel_max2 < 1e-3 and d0 == 0.0 and n_prefill_calls == 12
                      and counter.get("n", 0) == 12,
                      "rel_err_along_u_max_alpha1": rel_max, "rel_err_along_u_max_alpha2": rel_max2,
                      "alpha0_r_logits_max_abs_diff": d0, "hook_calls_prefill": n_prefill_calls,
                      "hook_calls_after_8_decode_steps": counter.get("n", 0),
                      "disp_S_mean_by_block_alpha1": rec["disp_S_mean_norm"]}
    del pre_e, pre0, pre2
    # U4: masks
    gen = torch.Generator(device="cuda").manual_seed(4)
    lg = torch.randn(3, 50, generator=gen, device="cuda", dtype=torch.float64) * 2
    Tv = torch.tensor([[0.7], [1.0], [1.3]], device="cuda", dtype=torch.float64)
    kk = torch.tensor([5, 0, 0], device="cuda")
    mp = torch.tensor([[0.0], [0.1], [0.0]], device="cuda", dtype=torch.float64)
    pr = mask_probs(lg, Tv, kk, mp, True, True, 5)
    ref2 = torch.softmax(lg[2] / 1.3, -1)
    p1 = torch.softmax(lg[1], -1)
    keep1 = p1 >= 0.1 * p1.max()
    u4 = {"topk_nonzero": int((pr[0] > 0).sum()), "sums": [float(x) for x in pr.sum(-1)],
          "minp_ok": bool(((pr[1] > 0) == keep1).all()) and bool((pr[1][keep1] >= 0.1 * pr[1].max() - 1e-12).all()),
          "nomask_max_abs_diff": float((pr[2] - ref2).abs().max())}
    u4["pass"] = (u4["topk_nonzero"] == 5 and all(abs(s - 1) < 1e-9 for s in u4["sums"]) and u4["minp_ok"]
                  and u4["nomask_max_abs_diff"] < 1e-12)
    res["U4_masks"] = u4
    # U5: sampler marginals (200,000 draws per sampler, chi-square p > 0.01)
    from scipy.stats import chisquare
    V, N, T = 40, 200_000, 0.7
    lg1 = torch.randn(1, V, generator=gen, device="cuda", dtype=torch.float64) * 1.5
    u5 = {}
    for tk in (0, 10):
        probs = mask_probs(lg1, torch.full((1, 1), T, device="cuda", dtype=torch.float64),
                           torch.tensor([tk], device="cuda"), torch.zeros((1, 1), device="cuda", dtype=torch.float64),
                           tk > 0, False, max(tk, 1))
        exp_p = probs[0].cpu().numpy()
        U = torch.rand(N, generator=gen, device="cuda", dtype=torch.float64)
        inv = _inverse_cdf(probs.expand(N, -1).contiguous(), U).cpu().numpy()
        q = torch.empty(N, V, device="cuda", dtype=torch.float64).exponential_(generator=gen)
        gum = torch.argmax(probs / q, dim=-1).cpu().numpy()
        for name, draws in (("invcdf", inv), ("gumbel", gum)):
            cnt = np.bincount(draws, minlength=V)
            m = exp_p * N >= 5
            obs = np.append(cnt[m], cnt[~m].sum())
            ex = np.append(exp_p[m] * N, exp_p[~m].sum() * N)
            if ex[-1] < 5:
                obs, ex = obs[:-1], ex[:-1]
                ex = ex * obs.sum() / ex.sum()
            p = float(chisquare(obs, ex).pvalue)
            u5[f"{name}_topk{tk}"] = {"chi2_p": p, "outside_support": int(cnt[exp_p == 0].sum())}
    res["U5_marginals"] = {"pass": all(v["chi2_p"] > 0.01 and v["outside_support"] == 0 for v in u5.values()), **u5}
    ctx.free()
    # U7: memory, longest prompt (T1), full B, forced to max_new
    torch.cuda.reset_peak_memory_stats()
    c1 = Ctx4(model, tok, prompts, "T1")
    wl = max(TEMPLATE_IDS, key=lambda w: c1.pr[w]["P"])
    B1 = Bs["T1"]
    run_batch4(c1, wl, [spec("SMOKE_FORCED", k, 1.0, ns="smoke") for k in range(B1)], "smoke:U7", MAX_NEW4["T1"], B1,
               raw_file=RAW_SMOKE, force_len=True)
    peak = torch.cuda.max_memory_allocated()
    tot = torch.cuda.get_device_properties(0).total_memory
    res["U7_memory"] = {"pass": peak / tot < 0.92, "peak_allocated_gb": peak / 1e9, "fraction_of_total": peak / tot,
                        "task": "T1", "template": wl, "B": B1, "max_new": MAX_NEW4["T1"]}
    c1.free()
    res["all_pass"] = all(v.get("pass") for k, v in res.items() if isinstance(v, dict) and "pass" in v)
    write_json(RESULTS_DIR / "unit_tests_gpu.json", res)
    logger.info(f"smoke tests: all_pass={res['all_pass']} "
                f"{({k: v.get('pass') for k, v in res.items() if isinstance(v, dict) and 'pass' in v})}")
    return res


# ------------------------------------------------------------------------------------------------ S6 engine check
def run_engine_check(minutes: float | None = None) -> None:
    tok, model = get_model()
    prompts = load_prompts()
    Bs = batch_sizes(model, prompts)
    done = done_keys()
    t_end = time.time() + (minutes or 60) * 60
    for task, rseed in (("T03", 9002), ("T2", 9004)):
        B = Bs[task]
        ctx = Ctx4(model, tok, prompts, task, engine_check=True)
        rows = [spec("EC_NEUTRAL_T1.0", k, 1.0) for k in range(10)] + \
               [spec(f"EC_RAND{rseed}_a1.0_T1.0", k, 1.0, group=("pn", rseed, 1.0)) for k in range(10)]
        for w in TEMPLATE_IDS:
            for bi in range(0, 20, B):
                bspec = rows[bi:bi + B]
                if all((task, w, s["arm"], s["k"]) in done for s in bspec):
                    continue
                if time.time() > t_end:
                    logger.warning("engine check: time guard reached")
                    return
                run_batch4(ctx, w, bspec, f"EC:{task}:{w}:b{bi // B}", MAX_NEW4[task], B)
            ctx.free()
    logger.info("engine check sampling done")


# ------------------------------------------------------------------------------------------------ S7 the 2x2
def _extrapolate(tasks: list[str], Bs: dict[str, int], drop: list[str]) -> dict[str, Any]:
    tb = [r for r in read_jsonl(TIMING) if r["block_id"].startswith("G2:")]
    if not tb:
        return {}
    s_per_row = float(np.sum([r["seconds"] for r in tb]) / np.sum([r["B"] for r in tb]))
    done = done_keys()
    n_left = 0
    for t in tasks:
        for w in TEMPLATE_IDS:
            for b in layout_2x2(Bs[t]):
                if not all((t, w, s["arm"], s["k"]) in done for s in b):
                    n_left += len(b)
    g3_rows = 220 * 2 + 60 + 40
    est = s_per_row * n_left
    elapsed = wall_guard(T0F)
    guard_g2 = 4.0 * 3600 - elapsed
    out = {"utc": utc_now(), "seconds_per_row_measured": s_per_row, "rows_done_G2": len(tb) and sum(r["B"] for r in tb),
           "rows_left_core": n_left, "est_seconds_core": est, "est_seconds_G3": s_per_row * g3_rows,
           "seconds_to_G2_guard": guard_g2, "elapsed_since_t0": elapsed, "drop_applied": drop}
    write_json(RESULTS_DIR / "timing_extrapolation.json", out)
    logger.info(f"extrapolation: {s_per_row:.2f} s/row; core left {n_left} rows ~{est / 60:.0f} min; G3 ~"
                f"{s_per_row * g3_rows / 60:.0f} min; G2 guard in {guard_g2 / 60:.0f} min")
    return out


def run_grid(tasks: list[str], minutes: float | None = None) -> None:
    tok, model = get_model()
    prompts = load_prompts()
    Bs = batch_sizes(model, prompts)
    drop: list[str] = []
    dropf = RESULTS_DIR / "drop_decisions.json"
    if dropf.exists():
        drop = read_json(dropf)["drop"]
    t_end = time.time() + minutes * 60 if minutes else None
    n_rows = 0
    extrap_done = {"stage10": False, "stage100": False}
    for tier in (0, 1):
        for task in tasks:
            if tier == 1 and task == "T1" and "alpha-2 PN block on T1" in drop:
                logger.warning("alpha-2 PN block on T1 dropped (drop order item 5)")
                continue
            B = Bs[task]
            ctx = Ctx4(model, tok, prompts, task)
            for w in TEMPLATE_IDS:
                done = done_keys()
                for bi, b in enumerate(layout_2x2(B)):
                    btier = min(s["tier"] for s in b)
                    if btier != tier or all((task, w, s["arm"], s["k"]) in done for s in b):
                        continue
                    if t_end and time.time() > t_end:
                        logger.warning("grid: --minutes guard reached")
                        return
                    run_batch4(ctx, w, b, f"G2:{task}:{w}:b{bi}", MAX_NEW4[task], B)
                    n_rows += B
                    if not extrap_done["stage10"]:
                        extrap_done["stage10"] = True
                        _extrapolate(tasks, Bs, drop)
                    if n_rows >= 100 and not extrap_done["stage100"]:
                        extrap_done["stage100"] = True
                        ex = _extrapolate(tasks, Bs, drop)
                        if ex and ex["est_seconds_core"] + ex["est_seconds_G3"] > ex["seconds_to_G2_guard"]:
                            for item in ("optional (ii)", "optional (i)", "(iii) Gumbel replicate", "(iv) min-p cell"):
                                if item not in drop:
                                    drop.append(item)
                            if ex["est_seconds_core"] > ex["seconds_to_G2_guard"]:
                                drop.append("alpha-2 PN block on T1")
                            write_json(dropf, {"drop": drop, "utc": utc_now(), "extrapolation": ex})
                            logger.warning(f"drop order applied: {drop}")
                ctx.free()
    logger.info("grid done")


# ------------------------------------------------------------------------------------------------ S8 optional
def select_tpn_dirs() -> list[int]:
    """Committed rule: the 3 of 6 directions with the highest alpha-2 T0.7 off-default share on T2 (thinking off);
    ties broken by seed."""
    labs = {r["key"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    share = {}
    for d in PN_SEEDS:
        arm = cond_pn(d, 2.0, 0.7)
        rr = [l for k, l in labs.items() if l["task"] == "T2" and l["arm"] == arm]
        att = [l for l in rr if l["label"] not in ("invalid", "disputed", "unresolved")]
        share[d] = sum(l["label"] != "dijkstra" for l in att) / max(len(att), 1)
    order = sorted(PN_SEEDS, key=lambda d: (-share[d], d))
    write_json(RESULTS_DIR / "tpn_direction_selection.json", {"share_off_a2_T0.7_T2": share, "selected": order[:3],
                                                               "utc": utc_now()})
    return order[:3]


def run_optional(arms: list[str], minutes: float | None = None) -> None:
    tok, model = get_model()
    prompts = load_prompts()
    Bs = batch_sizes(model, prompts)
    drop = read_json(RESULTS_DIR / "drop_decisions.json")["drop"] if (RESULTS_DIR / "drop_decisions.json").exists() else []
    t_end = time.time() + (minutes or 60) * 60
    for arm in arms:
        if arm == "iii" and "(iii) Gumbel replicate" not in drop:
            for task in ("T2", "T03"):
                B = Bs[task]
                ctx = Ctx4(model, tok, prompts, task)
                for w in TEMPLATE_IDS:
                    rows = []
                    for k in SEED_K:
                        for t in TEMPS:
                            rows.append(spec("GB_" + cond_nopn(t), k, t, coupling="gumbel"))
                        rows.append(spec(f"GB_TOPK{TOPK_K}_T{fmt_t(TOPK_T)}", k, TOPK_T, top_k=TOPK_K, coupling="gumbel"))
                        for d in PN_SEEDS:
                            rows.append(spec("GB_" + cond_pn(d, 1.0, 1.0), k, 1.0, group=("pn", d, 1.0),
                                             coupling="gumbel"))
                    rows.sort(key=lambda r: (-r["T"], r["group"] != "clean", str(r["group"]), r["k"]))
                    done = done_keys()
                    for bi, b in enumerate(pad(rows, B, "GB_PAD_T1.0", 1.0, coupling="gumbel")):
                        if all((task, w, s["arm"], s["k"]) in done for s in b):
                            continue
                        if time.time() > t_end:
                            logger.warning("optional: time guard reached")
                            return
                        run_batch4(ctx, w, b, f"G3iii:{task}:{w}:b{bi}", MAX_NEW4[task], B)
                    ctx.free()
        elif arm == "iv" and "(iv) min-p cell" not in drop:
            for task in ("T2", "T03", "T1"):
                B = Bs[task]
                ctx = Ctx4(model, tok, prompts, task)
                for w in TEMPLATE_IDS:
                    rows = [spec(f"MINP_T{fmt_t(MINP_T)}", k, MINP_T, min_p=MINP_P) for k in SEED_K]
                    done = done_keys()
                    for bi, b in enumerate(pad(rows, B, "PAD_T1.0", 1.0)):
                        if all((task, w, s["arm"], s["k"]) in done for s in b):
                            continue
                        if time.time() > t_end:
                            logger.warning("optional: time guard reached")
                            return
                        run_batch4(ctx, w, b, f"G3iv:{task}:{w}:b{bi}", MAX_NEW4[task], B)
                    ctx.free()
        elif arm == "ii" and "optional (ii)" not in drop:
            from lexicon import first_approach
            dirs = select_tpn_dirs()
            B = Bs["T2think"]
            ctx = Ctx4(model, tok, prompts, "T2", thinking=True)
            off_ctx = Ctx4(model, tok, prompts, "T2")
            diffs = {}
            for w in TEMPLATE_IDS:   # causal masking check: S states of the thinking-on vs -off clean prefill
                a, b_ = ctx.pr[w]["a"], ctx.pr[w]["b"]
                s_on = ctx.clean(w)["S"]
                s_off = off_ctx.clean(w)["S"]
                diffs[w] = max(float((s_on[l] - s_off[l]).abs().max()) for l in V_BLOCKS)
                off_ctx.free()
            write_json(RESULTS_DIR / "tpn_causal_mask_check.json", {"max_abs_diff_S_blocks12_23": diffs,
                       "note": "exact 0 requires identical GEMM shapes; FP8 prefill of different lengths may differ"})
            for w in TEMPLATE_IDS:
                rows = []
                for k in (0, 1):
                    rows.append(spec(f"TPN_NOPN_T{fmt_t(TPN_T)}", k, TPN_T))
                    for d in dirs:
                        rows.append(spec(f"TPN_{cond_pn(d, TPN_ALPHA, TPN_T)}", k, TPN_T, group=("pn", d, TPN_ALPHA)))
                done = done_keys()
                for bi, b in enumerate(pad(rows, B, f"TPN_PAD_T{fmt_t(TPN_T)}", TPN_T, start_k=2)):
                    if all(("T2", w, s["arm"], s["k"]) in done for s in b):
                        continue
                    if time.time() > t_end:
                        logger.warning("optional: time guard reached")
                        return
                    out = run_batch4(ctx, w, b, f"G3ii:T2:{w}:b{bi}", TPN_MAX_NEW, B)
                    for r in out:
                        r["first_approach"] = first_approach(r["text"])[0]
                    append_jsonl(DATA_DIR / "tpn_first_approach.jsonl",
                                 [{"template": r["template"], "arm": r["arm"], "sample_id": r["sample_id"],
                                   "first_approach": r["first_approach"]} for r in out])
                ctx.free()
    logger.info(f"optional arms done: {arms}")


# ------------------------------------------------------------------------------------------------ unit sensitivity
def run_unit_sensitivity() -> dict[str, Any]:
    """Recompute n[l,p] = mean over W1-W5 of ||h_ban - h_twin|| (block outputs 12-23, positions S) from batch-1
    prefills of the 5 ban/twin pairs per task, on THIS engine (FP8 W8A8; bf16 does not fit the 16 GB card, so this
    replaces the plan's bf16 recompute -- logged deviation), and report the median ratio to the protocol unit."""
    tok, model = get_model()
    prompts = load_prompts()
    out: dict[str, Any] = {"engine": "hf-fp8-w8a8, batch-1 prefill", "utc": utc_now()}
    for task in ("T1", "T2", "T03"):
        ns = []
        for w in TEMPLATE_IDS:
            caps = {}
            for kind in ("ban", "twin"):
                p = prompts[(task, w, kind)]
                a, b = p["p1"], p["spec_end"]
                cap: dict[int, torch.Tensor] = {}

                def mk(l, cap=cap, a=a, b=b):
                    def g(h):
                        cap[l] = h[0, a:b].float().clone()
                    return g
                prefill(model, p["ids"], capture={l: mk(l) for l in V_BLOCKS})
                caps[kind] = cap
            ns.append(np.stack([(caps["ban"][l] - caps["twin"][l]).norm(dim=-1).cpu().numpy() for l in V_BLOCKS]))
        n_here = np.mean(ns, axis=0)
        proto = unit_norms(task)
        r = n_here / proto
        out[task] = {"median_ratio_per_block": [float(x) for x in np.median(r, axis=1)],
                     "overall_median_ratio": float(np.median(r)), "protocol_unit": "exp13 norms_T03.npz" if
                     task == "T03" else f"exp17 norms_{task}.npy"}
        if task == "T03":
            r17 = n_here / unit_norms(task, engine_check=True)
            out[task]["overall_median_ratio_to_exp17_unit"] = float(np.median(r17))
        logger.info(f"unit sensitivity {task}: median ratio this-engine / protocol = {out[task]['overall_median_ratio']:.3f}")
    write_json(RESULTS_DIR / "unit_sensitivity.json", out)
    torch.cuda.empty_cache()
    return out


def run_hf_chain(tasks: list[str], arms: list[str], minutes: float | None = None) -> None:
    """One process (one model load): smoke -> unit sensitivity -> engine check -> 2x2 -> optional arms."""
    try:
        run_smoke()
    except (RuntimeError, AssertionError, torch.cuda.OutOfMemoryError) as e:
        logger.exception(f"smoke tests crashed: {e}")
        write_json(RESULTS_DIR / "unit_tests_gpu_error.json", {"error": repr(e), "utc": utc_now()})
    try:
        run_unit_sensitivity()
    except (RuntimeError, AssertionError, torch.cuda.OutOfMemoryError) as e:
        logger.exception(f"unit sensitivity crashed: {e}")
    run_engine_check(minutes=20)
    run_grid(tasks=tasks, minutes=minutes)
    elapsed = wall_guard(T0F)
    left_min = (4.0 * 3600 + 25 * 60 - elapsed) / 60      # optional arms must end ~t0 + 4h25 (analysis by t0 + 4h45)
    if left_min > 5:
        run_optional(arms=arms, minutes=left_min)
    else:
        logger.warning(f"optional arms skipped: only {left_min:.0f} min before the analysis guard")
        write_json(RESULTS_DIR / "drop_decisions_optional.json", {"skipped": arms, "utc": utc_now(),
                                                                   "reason": "wall-clock guard"})
    logger.info("HF chain done")
