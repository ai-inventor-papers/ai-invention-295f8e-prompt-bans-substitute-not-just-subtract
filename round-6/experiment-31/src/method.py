#!/usr/bin/env python3
"""Claim S: where does gemma-3-4b-it fork between BFS and DFS on one grid-path prompt (T1), and do Gemma Scope 2
resid_post SAEs read and steer that choice better than difference-in-means, raw-residual, raw-dimension, random
and prompting baselines?

Entry point. Every stage is one function; run `uv run method.py --stage <name>` (or `.venv/bin/python method.py`).
Stages (in the order they were run): s0, gen1, label, tf, gate, fork, variants, select, clamps, top5geo, novelty,
analysis, outputs. See README.md for what each produces. Source modules live in src/.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loguru import logger  # noqa: E402

from cfg import (B_CRN, BENCH, stable_seed, DATA_DIR, IT_ID, IT_REV, LOG_DIR, N_OLD_SLOTS, N_SPLIT_PER_T, PRED_DIR,  # noqa: E402
                 RESULTS_DIR, SAE_IDS, SAE_LAYERS, SCOPE_REPO, SCOPE_REV, SLOT_PREFIX, SLOT_PREFIX_OLD,
                 TC_REPO, TC_REV, TEMPLATE_IDS, append_jsonl, cap_of, container_ram_gb, read_json, read_jsonl,
                 set_ram_limit, setup_logging, sha256_file, utc_now, write_json)

TASKS_S3 = ("T1", "T04", "R6")
CPU_STAGES = ("s0", "label", "analysis", "novelty", "outputs", "geo")


def slot_key(task: str, w: str, k: int) -> tuple[str, str, str, int]:
    return (SLOT_PREFIX_OLD if k < N_OLD_SLOTS else SLOT_PREFIX, task, w, k)


# ================================================================================================ S0
def stage_s0() -> None:
    """Verify staged inputs, record hardware and instrument ids, write commit #0."""
    import platform
    import subprocess

    import torch
    import transformers
    from huggingface_hub import HfApi

    from commit import commit

    res: dict[str, Any] = {"utc": utc_now()}
    # ---- staged copies vs exp28's verified SHA256SUMS (paths 'inputs/...')
    sums = {}
    for ln in (ROOT / "inputs" / "exp28_staged_SHA256SUMS").read_text().splitlines():
        if ln.strip():
            h, p = ln.split(None, 1)
            sums[p.strip()] = h
    bad, n_ok = [], 0
    for p, h in sums.items():
        if p == "inputs/SHA256SUMS":
            continue
        fp = ROOT / p
        if not fp.exists():
            bad.append({"path": p, "why": "missing"})
            continue
        if sha256_file(fp) != h:
            bad.append({"path": p, "why": "sha mismatch"})
        else:
            n_ok += 1
    res["staged_vs_exp28_sums"] = {"n_ok": n_ok, "n_bad": len(bad), "bad": bad[:20]}
    # ---- bench commitment
    com = read_json(BENCH / "commitment.json")
    nb, bb, nl = 0, [], 0
    dirs = {d.name.split("_")[0]: d for d in BENCH.iterdir() if d.is_dir()}
    for task, rec in com["tasks"].items():
        if task not in ("T04", "R6"):
            continue
        for rel_p, h in rec["files"].items():
            fp = dirs[task] / rel_p
            if not fp.exists():
                continue
            nl += 1
            if sha256_file(fp) == h:
                nb += 1
            else:
                bb.append(f"{task}/{rel_p}")
    res["bench_commitment"] = {"tasks": ["T04", "R6"], "n_ok": nb, "n_bad": len(bb), "bad": bb[:20], "n_checked": nl}
    files = list(range(nl))
    # ---- manifest of everything staged
    man = []
    for fp in sorted((ROOT / "inputs").rglob("*")):
        if fp.is_file():
            man.append(f"{sha256_file(fp)}  {fp.relative_to(ROOT)}")
    (ROOT / "inputs" / "MANIFEST.sha256").write_text("\n".join(man) + "\n")
    res["manifest_n_files"] = len(man)
    # ---- hardware
    hw = {"gpu": torch.cuda.get_device_name(0), "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
          "bf16": torch.cuda.is_bf16_supported(), "torch": torch.__version__, "cuda": torch.version.cuda,
          "transformers": transformers.__version__, "python": platform.python_version(),
          "cpus_quota": __import__("cfg").detect_cpus(), "ram_gb_limit": container_ram_gb(),
          "driver": subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                   capture_output=True, text=True).stdout.strip(),
          "sae_lens": "not used (direct JumpReLU load from params.safetensors)",
          "circuit_tracer": "not installed (S10 dropped first by the drop order; first-order fallback)"}
    write_json(PRED_DIR / "hardware.json", hw)
    # ---- instrument ids (asserted against the Hub listing)
    api = HfApi()
    files_scope = set(api.list_repo_files(SCOPE_REPO, revision=SCOPE_REV))
    files_tc = set(api.list_repo_files(TC_REPO, revision=TC_REV))
    ids = {"sae": {}, "transcoders_listed": [], "circuit_tracer_configs": []}
    for l in SAE_LAYERS:
        sid = SAE_IDS[l]
        assert f"{sid}/params.safetensors" in files_scope and f"{sid}/config.json" in files_scope, sid
        ids["sae"][str(l)] = {"id": sid, "repo": SCOPE_REPO, "revision": SCOPE_REV}
    ids["transcoders_listed"] = sorted({f.rsplit("/", 1)[0] for f in files_scope
                                        if f.startswith("transcoder_all/") and "width_16k" in f})[:200]
    ids["circuit_tracer_configs"] = sorted(f for f in files_tc if f.endswith("config.yaml"))
    ids["model"] = {"id": IT_ID, "revision": IT_REV}
    write_json(PRED_DIR / "instrument_ids.json", ids)
    # ---- commit #0
    code_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}
    code_hashes["method.py"] = sha256_file(ROOT / "method.py")
    rules = read_json(ROOT / "predictions" / "rules_commit0.json")
    c0 = commit("commit0", {"rules": rules, "instrument_ids": ids, "hardware": hw, "code_sha256": code_hashes,
                            "inputs_manifest_sha256": sha256_file(ROOT / "inputs" / "MANIFEST.sha256"),
                            "staging": res})
    res["commit0"] = c0
    write_json(RESULTS_DIR / "s0_inputs.json", res)
    logger.info(f"S0 done: staged ok {n_ok}, bad {len(bad)}; bench ok {nb}/{len(files)}; commit0 {c0['sha256'][:12]}")


# ================================================================================================ GPU stage 1
def _crn_rows(task: str, w: str, arm: str, slots: list[int], stage: str, meta: dict | None = None) -> list[dict]:
    return [{"row_id": f"{stage}|{task}|{w}|{arm}|{k}", "task": task, "arm": arm, "template": w, "slot": k,
             "ukey": slot_key(task, w, k), "meta": dict(meta or {})} for k in slots]


def stage_gen1(args: argparse.Namespace) -> None:
    """S1 unit tests (U1, U2) + S3 natural splits (T1, T04, R6) + S5 contrast-arm generation (forced BFS/DFS,
    ban BFS/DFS) + S11 TOP5 and its twin. Slots 0-9 of every template use exp28's keys (engine check)."""
    import numpy as np
    import torch

    import engine as EG
    import prompts as PG
    from gen import Runner, add_edits
    from sae import JumpReLUSAE

    run = Runner()
    tests: dict[str, Any] = {}
    # ---------------- U1: CRN determinism (same slot twice -> byte-identical programs)
    p = PG.p_twin("T1", "W1")
    rows = _crn_rows("T1", "W1", "u1", [0, 1], "u1")
    a = run.run_crn(p, rows, 96, "u1", DATA_DIR / "tests_u1.jsonl", "U1a")
    b = run.run_crn(p, rows, 96, "u1", DATA_DIR / "tests_u1.jsonl", "U1b")
    tests["U1_crn_determinism"] = {"pass": all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b)),
                                   "n": len(a)}
    # ---------------- U2: identity hooks (zero additive edit; error-preserving SAE splice) are bit-identical
    ids = p["ids"]
    with torch.no_grad():
        base = EG.prefill_single(run.model, ids, 1)["logits"]
        z = add_edits([{22: (torch.arange(0, len(ids), device="cuda"),
                             torch.zeros(len(ids), 2560, device="cuda"))}], 1)
        zl = EG.prefill_single(run.model, ids, 1, edits=z)["logits"]
        sae = JumpReLUSAE(22, "cuda")

        def splice(h: torch.Tensor) -> torch.Tensor:
            x = h.float()
            f, xh = sae.recon(x)
            return (xh + (x - xh)).to(h.dtype)
        sl = EG.prefill_single(run.model, ids, 1, edits={22: splice})["logits"]
        # clamp-to-own-value: f_i <- f_i for the 20 most active latents (dh = 0 by construction)
        def own(h: torch.Tensor) -> torch.Tensor:
            x = h.float()
            f = sae.encode(x)
            top = f[0, -1].topk(20).indices
            dh = ((f[..., top] - f[..., top])[..., None] * sae.W_dec[top]).sum(-2)
            return (x + dh).to(h.dtype)
        ol = EG.prefill_single(run.model, ids, 1, edits={22: own})["logits"]
    tests["U2_identity_hooks"] = {
        "zero_edit_bit_identical": bool(torch.equal(base, zl)),
        "error_preserving_splice_bit_identical": bool(torch.equal(base, sl)),
        "splice_max_abs_logit_diff": float((base - sl).abs().max()),
        "clamp_to_own_value_bit_identical": bool(torch.equal(base, ol))}
    del sae
    torch.cuda.empty_cache()
    logger.info(f"unit tests: {json.dumps(tests)}")
    write_json(RESULTS_DIR / "tests_gpu_s1.json", tests)
    # ---------------- S3 natural splits (slots 0-9 first for every task = engine check rows)
    n_slots = args.n_slots or N_SPLIT_PER_T
    for task in (args.tasks.split(",") if args.tasks else TASKS_S3):
        for w in TEMPLATE_IDS:
            p = PG.p_twin(task, w)
            done = {r["row_id"] for r in read_jsonl(DATA_DIR / "raw_s3.jsonl")}
            rows = [r for r in _crn_rows(task, w, "twin", list(range(n_slots)), "s3") if r["row_id"] not in done]
            if rows:
                run.run_crn(p, rows, cap_of(task), "s3", DATA_DIR / "raw_s3.jsonl", f"S3:{task}:{w}")
    if args.skip_contrast:
        run.free()
        return
    # ---------------- contrast arms (multi-prompt batches; slots keyed like the twin's W_i slot k)
    items = []
    for f_i, w in zip(["F1", "F2", "F3", "F4", "F5"], TEMPLATE_IDS):
        for mode in ("bfs", "dfs"):
            pf = PG.p_forced("T1", mode, f_i)
            PG.register(pf)
            for k in range(10):
                items.append({"row_id": f"s5|T1|{f_i}|forced_{mode}|{k}", "ids": pf["ids"], "n_prefix": 0,
                              "prefix_ids": [], "ukey": slot_key("T1", w, k),
                              "meta": {"task": "T1", "arm": f"forced_{mode}", "template": f_i, "slot": k,
                                       "prompt_sha256": pf["prompt_sha256"], "prompt_kind": "forced",
                                       "temperature": 1.0, "top_k": None, "thinking": False, "precision": "bf16",
                                       "model": IT_ID}})
    for w in TEMPLATE_IDS:
        for mode in ("bfs", "dfs"):
            pb = PG.p_ban("T1", mode, w)
            PG.register(pb)
            for k in range(10):
                items.append({"row_id": f"s5|T1|{w}|ban_{mode}|{k}", "ids": pb["ids"], "n_prefix": 0,
                              "prefix_ids": [], "ukey": slot_key("T1", w, k),
                              "meta": {"task": "T1", "arm": f"ban_{mode}", "template": w, "slot": k,
                                       "prompt_sha256": pb["prompt_sha256"], "prompt_kind": "ban",
                                       "temperature": 1.0, "top_k": None, "thinking": False, "precision": "bf16",
                                       "model": IT_ID}})
    for w in TEMPLATE_IDS:
        pb, pn = PG.p_top5("T1", w)
        PG.register(pb)
        PG.register(pn)
        for arm, pp in (("top5", pb), ("top5_twin", pn)):
            for k in range(10):
                items.append({"row_id": f"s11|T1|{w}|{arm}|{k}", "ids": pp["ids"], "n_prefix": 0,
                              "prefix_ids": [], "ukey": slot_key("T1", w, k),
                              "meta": {"task": "T1", "arm": arm, "template": w, "slot": k,
                                       "prompt_sha256": pp["prompt_sha256"], "prompt_kind": arm,
                                       "temperature": 1.0, "top_k": None, "thinking": False, "precision": "bf16",
                                       "model": IT_ID}})
    done = {r["row_id"] for r in read_jsonl(DATA_DIR / "raw_contrast.jsonl")}
    items = [it for it in items if it["row_id"] not in done]
    # group rows of the same prompt together (2 prompts x 10 slots per batch of 20)
    run.run_multi(items, 1536, "contrast", DATA_DIR / "raw_contrast.jsonl", "CON", B=B_CRN)
    run.free()
    _ = np


# ================================================================================================ labelling
def stage_label(args: argparse.Namespace) -> None:
    """CPU: label every raw_*.jsonl row with the frozen labellers (exp8 suite for T1, exp11 bench for T04/R6)."""
    import label_worker as LW

    LW.run_worker(follow=args.follow, stop_file=DATA_DIR / "STOP_LABELLER", judge=not args.no_judge)


# ================================================================================================ S4 fork
def load_labelled(raw_name: str, task: str | None = None, arm: str | None = None) -> list[dict[str, Any]]:
    """raw rows joined with their label rows (rows without a label are skipped)."""
    lab = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / raw_name):
        if task and r.get("task") != task:
            continue
        if arm and r.get("arm") != arm:
            continue
        L = lab.get(r["row_id"])
        if L is None:
            continue
        rr = dict(r)
        for k in ("label", "labeller_source", "passed", "valid", "runtime_label", "ast_label", "judge_label",
                  "fallback_label", "code_sha256", "code", "extract_how"):
            rr[k] = L.get(k)
        out.append(rr)
    return out


def response_ids(r: dict[str, Any]) -> list[int]:
    """generated ids without the trailing stop token."""
    ids = list(r["token_ids"])
    while ids and ids[-1] in (1, 106):
        ids = ids[:-1]
    return ids


def identifying_index(tok: Any, ids: list[int]) -> int | None:
    """First response-token index i such that the partial labeller is decided on ids[:i+1] (binary search)."""
    import fork as F

    if F.partial_label(tok.decode(ids, skip_special_tokens=True)) is None:
        return None
    lo, hi = 0, len(ids) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if F.partial_label(tok.decode(ids[:mid + 1], skip_special_tokens=True)) is not None:
            hi = mid
        else:
            lo = mid + 1
    return lo


def stage_fork(args: argparse.Namespace) -> None:
    """S4: partial-code labeller validation (U8), base paths, coarse prefix resampling, change points,
    single-token refinement, identifying tokens, identical-prefix share, c* and the fork token sets."""
    import numpy as np

    import fork as F
    import prompts as PG
    from cfg import (FORK_CONT, FORK_MAX_NEW, FORK_PERM, FORK_POSITIONS, FORK_REFINE_CONT, FORK_RISE,
                     TOKEN_SET_HI, TOKEN_SET_LO, wilson_ci)
    from gen import Runner

    rows = [r for r in load_labelled("raw_s3.jsonl", "T1") if r["arm"] == "twin"]
    run = Runner()
    tok = run.tok
    # ---------------- U8: partial labeller vs full labels on valid attempts (first 320 tokens)
    conf: dict[str, int] = {}
    agree = n = 0
    for r in rows:
        if not r["valid"] or r["label"] in ("invalid", "disputed"):
            continue
        pl = F.partial_label(tok.decode(response_ids(r)[:FORK_MAX_NEW], skip_special_tokens=True)) or "other"
        fl = F.map_full(r["label"])
        conf[f"{fl}->{pl}"] = conf.get(f"{fl}->{pl}", 0) + 1
        n += 1
        agree += pl == fl
    u8 = {"n": n, "agreement": agree / max(n, 1), "confusion": conf, "pass": agree / max(n, 1) >= 0.95}
    use_partial = u8["pass"]
    logger.info(f"U8 partial labeller: {u8}")
    # ---------------- identifying token per S3 sample
    ident = {}
    for r in rows:
        ids = response_ids(r)
        i = identifying_index(tok, ids)
        ident[r["row_id"]] = {"idx": i, "token": tok.decode([ids[i]]) if i is not None else None,
                              "cls": F.map_full(r["label"]) if r["valid"] else "invalid", "template": r["template"],
                              "label": r["label"], "passed": r["passed"]}
    # ---------------- base paths: 12 BFS + 12 DFS valid attempts (round-robin over templates, prefer correct)
    def pick(cls: str, n_want: int = 12) -> list[dict[str, Any]]:
        cand = [r for r in rows if r["valid"] and r["label"] == cls]
        by_w: dict[str, list] = {}
        for r in sorted(cand, key=lambda r: (not r["passed"], r["template"], r["slot"])):
            by_w.setdefault(r["template"], []).append(r)
        out: list[dict[str, Any]] = []
        while len(out) < n_want and any(by_w.values()):
            for w in TEMPLATE_IDS:
                if by_w.get(w) and len(out) < n_want:
                    out.append(by_w[w].pop(0))
        return out
    base = pick("bfs") + pick("dfs")
    tw = {w: PG.p_twin("T1", w) for w in TEMPLATE_IDS}
    stop = F.decided if use_partial else None
    max_new = FORK_MAX_NEW if use_partial else 1536

    def items_for(paths: list[dict], positions: list[int], n_cont: int, tag: str) -> list[dict[str, Any]]:
        its = []
        for r in paths:
            ids = response_ids(r)
            for t in positions:
                if t > len(ids):
                    continue
                for j in range(n_cont):
                    its.append({"row_id": f"{tag}|{r['row_id']}|{t}|{j}", "ids": tw[r["template"]]["ids"] + ids[:t],
                                "n_prefix": 0, "prefix_ids": ids[:t], "ukey": ("iter6S-fork", tag, r["row_id"], t, j),
                                "meta": {"task": "T1", "base_row": r["row_id"], "base_label": r["label"], "t": t,
                                         "j": j, "template": r["template"], "tag": tag}})
        return its

    raw_fork = DATA_DIR / "fork_cont.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw_fork)}
    coarse = [it for it in items_for(base, list(FORK_POSITIONS), FORK_CONT, "coarse") if it["row_id"] not in done]
    logger.info(f"fork coarse: {len(coarse)} continuations to run (B={args.fork_b})")
    t0 = time.time()
    if coarse:
        pilot = coarse[:args.fork_b]
        run.run_multi(pilot, max_new, "fork", raw_fork, "FORKpilot", B=args.fork_b, stop_fn=stop)
        dt = time.time() - t0
        est = dt * len(coarse) / len(pilot)
        write_json(LOG_DIR / "timing_fork.json", {"pilot_rows": len(pilot), "pilot_s": dt,
                                                   "extrapolated_coarse_s": est})
        logger.info(f"fork pilot {dt:.1f}s for {len(pilot)} -> coarse estimate {est / 60:.1f} min")
        run.run_multi(coarse[len(pilot):], max_new, "fork", raw_fork, "FORK", B=args.fork_b, stop_fn=stop)

    def cls_of(row: dict[str, Any]) -> str:
        pl = F.partial_label(row["text"])
        return pl or "other"

    cont = read_jsonl(raw_fork)
    for c in cont:
        c["cls"] = cls_of(c)
    # ---------------- U6: full-length prefix reproduces the base label; t=0 share vs S3 marginal
    u6_full = all(F.map_full(r["label"]) == (F.partial_label(r["text"]) or "other") for r in base)
    t0rows = [c for c in cont if c["t"] == 0 and c.get("tag") == "coarse"]
    k0 = sum(c["cls"] == "bfs" for c in t0rows)
    valid = [r for r in rows if r["valid"] and r["label"] not in ("invalid", "disputed")]
    kb = sum(r["label"] == "bfs" for r in valid)
    lo, hi = wilson_ci(kb, len(valid))
    u6 = {"full_prefix_reproduces_label": u6_full, "t0_bfs_share": k0 / max(len(t0rows), 1), "t0_n": len(t0rows),
          "s3_bfs_share": kb / max(len(valid), 1), "s3_ci95": [lo, hi],
          "t0_within_ci": lo <= k0 / max(len(t0rows), 1) <= hi}
    # ---------------- change points per path and pooled per class
    per_path = []
    for r in base:
        own = F.map_full(r["label"])
        ks, ns, ts, pb = [], [], [], []
        for t in FORK_POSITIONS:
            cs = [c for c in cont if c["base_row"] == r["row_id"] and c["t"] == t and c.get("tag") == "coarse"]
            if not cs:
                continue
            ks.append(sum(c["cls"] == own for c in cs))
            ns.append(len(cs))
            ts.append(t)
            pb.append(sum(c["cls"] == "bfs" for c in cs) / len(cs))
        cp = F.change_points(ks, ns, FORK_PERM, seed=stable_seed("cp", r["row_id"]) % 2 ** 31)
        fork_t = None
        rise = None
        for i, ci in enumerate(cp["cps"]):
            before = cp["segments"][i]["p"]
            after = cp["segments"][i + 1]["p"]
            if cp["p_value"] < 0.05 and after is not None and before is not None and after - before >= FORK_RISE:
                fork_t = ts[ci]          # first coarse position after the change (fork token in (ts[ci-1], ts[ci]])
                rise = after - before
                break
        dp = np.abs(np.diff(np.array(ks) / np.array(ns))) if len(ks) > 1 else np.array([0.0])
        per_path.append({"row_id": r["row_id"], "label": r["label"], "template": r["template"], "t": ts,
                         "k_own": ks, "n": ns, "p_bfs": pb, "cp": cp, "fork_t": fork_t, "rise": rise,
                         "argmax_dp_t": ts[int(np.argmax(dp)) + 1] if len(ts) > 1 else None,
                         "lcp_with_other_class_max": max(F.lcp(response_ids(r), response_ids(o)) for o in valid
                                                         if F.map_full(o["label"]) != F.map_full(r["label"]))})
    forks = [p["fork_t"] for p in per_path if p["fork_t"] is not None]
    branch = "change_point" if forks else "distributed over generation"
    fork_coarse = int(np.median(forks)) if forks else int(np.median([p["argmax_dp_t"] for p in per_path
                                                                     if p["argmax_dp_t"] is not None]))
    # ---------------- refinement at single-token resolution: every token in [fork-4, fork], 16 continuations
    ref_paths = [p for p in per_path if p["fork_t"] is not None][:args.refine_paths]
    by_id = {r["row_id"]: r for r in base}
    ref_items = []
    for p in ref_paths:
        ft = p["fork_t"]
        ref_items += items_for([by_id[p["row_id"]]], list(range(max(0, ft - 4), ft + 1)), FORK_REFINE_CONT, "refine")
    done = {r["row_id"] for r in read_jsonl(raw_fork)}
    ref_items = [it for it in ref_items if it["row_id"] not in done]
    if ref_items:
        run.run_multi(ref_items, max_new, "fork", raw_fork, "REFINE", B=args.fork_b, stop_fn=stop)
    cont = read_jsonl(raw_fork)
    for c in cont:
        c["cls"] = cls_of(c)
    refined = []
    for p in ref_paths:
        r = by_id[p["row_id"]]
        ids = response_ids(r)
        own = F.map_full(r["label"])
        ser = []
        for t in range(max(0, p["fork_t"] - 4), p["fork_t"] + 1):
            cs = [c for c in cont if c["base_row"] == r["row_id"] and c["t"] == t and c.get("tag") == "refine"]
            if cs:
                ser.append({"t": t, "n": len(cs), "p_own": sum(c["cls"] == own for c in cs) / len(cs),
                            "p_bfs": sum(c["cls"] == "bfs" for c in cs) / len(cs)})
        jumps = [(ser[i + 1]["p_own"] - ser[i]["p_own"], ser[i + 1]["t"]) for i in range(len(ser) - 1)]
        best = max(jumps) if jumps else (0.0, p["fork_t"])
        ft = best[1]                                  # prefix length after which own share jumped
        tok_id = ids[ft - 1] if ft >= 1 else None     # the token whose inclusion produced the jump
        refined.append({"row_id": r["row_id"], "label": r["label"], "series": ser, "fork_len": ft,
                        "fork_token_index": ft - 1, "fork_token": tok.decode([tok_id]) if tok_id is not None else None,
                        "jump": best[0],
                        "p_bfs_before": next((s["p_bfs"] for s in ser if s["t"] == ft - 1), None),
                        "p_bfs_after": next((s["p_bfs"] for s in ser if s["t"] == ft), None)})
    # ---------------- global fork token index (deviation D-fork, fixed before commit #1): among the refined
    # per-path fork token indices, the one at which the canonical (modal) prefix actually branches, i.e. with the
    # largest mutual information between the next token and the program class over S3 samples on c*(t) (ties ->
    # the modal refined index). The median rule first coded here landed on a position where every sample writes
    # the same indentation token (MI = 0), which would make the fork readout constant by construction.
    ids_all = [response_ids(r) for r in valid]
    s3_rows = [{"ids": response_ids(r), "cls": F.map_full(r["label"])} for r in valid]

    def mi_at(t: int) -> tuple[float, int]:
        cs, _ = F.canonical_prefix(ids_all, t)
        rr = [x for x in s3_rows if len(x["ids"]) > t and x["ids"][:t] == cs and x["cls"] in ("bfs", "dfs")]
        if not rr:
            return 0.0, 0
        def h(ps):
            return -sum(q * np.log2(q) for q in ps if q > 0)
        pb = sum(x["cls"] == "bfs" for x in rr) / len(rr)
        by_tok: dict[int, list[str]] = {}
        for x in rr:
            by_tok.setdefault(x["ids"][t], []).append(x["cls"])
        cond = sum(len(v) / len(rr) * h([sum(c == "bfs" for c in v) / len(v), sum(c == "dfs" for c in v) / len(v)])
                   for v in by_tok.values())
        return float(h([pb, 1 - pb]) - cond), len(rr)
    if refined:
        idxs = [x["fork_token_index"] for x in refined]
        cands = sorted(set(idxs))
        mi_tab = {t: mi_at(t) for t in cands}
        mode = max(cands, key=lambda t: (idxs.count(t), t))
        tf = max(cands, key=lambda t: (round(mi_tab[t][0], 6), t == mode))
        fork_rule = {"candidates": {str(t): {"mi_bits": mi_tab[t][0], "n_on_cstar": mi_tab[t][1],
                                             "n_paths": idxs.count(t)} for t in cands},
                     "median_index": int(np.median(idxs)), "modal_index": mode, "chosen": tf}
    else:
        tf = max(0, fork_coarse - 1)
        fork_rule = {"chosen": tf, "fallback": "coarse median - 1"}
    # ---------------- c*, token sets, identical-prefix share
    cstar, cnt = F.canonical_prefix(ids_all, tf)
    # continuations whose (prefix + continuation) starts with c* add evidence about the fork token
    extra = []
    for c in cont:
        ids = response_ids({"token_ids": c["token_ids"]})
        if c["t"] <= tf and len(ids) > tf and ids[:tf] == cstar:
            extra.append({"ids": ids, "cls": c["cls"]})
    table = F.token_table(s3_rows + extra, cstar)
    table_s3 = F.token_table(s3_rows, cstar)
    Bset = [t for t, v in table.items() if not v["pooled"] and v["p_bfs"] is not None and v["p_bfs"] >= TOKEN_SET_HI]
    Dset = [t for t, v in table.items() if not v["pooled"] and v["p_bfs"] is not None and v["p_bfs"] <= TOKEN_SET_LO]
    ids_by_w = {w: [response_ids(r) for r in valid if r["template"] == w] for w in TEMPLATE_IDS}
    ips = F.identical_prefix_share(ids_by_w, tf)
    gaps = [ident[r["row_id"]]["idx"] - tf for r in valid if ident[r["row_id"]]["idx"] is not None]
    out = {"U8_partial_labeller": u8, "U6": u6, "use_partial_labeller": use_partial, "base_paths": [
        {"row_id": r["row_id"], "label": r["label"], "passed": r["passed"], "template": r["template"]} for r in base],
        "per_path": per_path, "branch": branch, "fork_coarse_median": fork_coarse, "refined": refined,
        "fork_index_rule": fork_rule,
        "fork_token_index": tf, "cstar_ids": cstar, "cstar_text": tok.decode(cstar), "cstar_count": cnt,
        "cstar_share": cnt / len(ids_all),
        "token_table": {str(k): {**v, "token": tok.decode([k])} for k, v in sorted(table.items(), key=lambda kv: -kv[1]["n"])},
        "token_table_s3_only": {str(k): {**v, "token": tok.decode([k])} for k, v in table_s3.items()},
        "B_set": Bset, "D_set": Dset, "B_tokens": [tok.decode([t]) for t in Bset],
        "D_tokens": [tok.decode([t]) for t in Dset],
        "identical_prefix_share": ips, "identifying": ident,
        "gap_fork_to_identifying": {"median": float(np.median(gaps)) if gaps else None,
                                    "q10": float(np.quantile(gaps, 0.1)) if gaps else None,
                                    "q90": float(np.quantile(gaps, 0.9)) if gaps else None},
        "n_continuations": len(cont)}
    write_json(RESULTS_DIR / "fork.json", out)
    logger.info(f"fork: branch {branch}, coarse {fork_coarse}, token index {tf}, c* '{out['cstar_text'][-40:]}', "
                f"B {out['B_tokens']} D {out['D_tokens']}, IPS {ips}")
    run.free()


# ================================================================================================ S3 states + S2 gate
N_READ = 97          # read positions P-1 .. P+95 (predicting response tokens 0..96)


def stage_tfgate(args: argparse.Namespace) -> None:
    """Teacher-force every S3 sample once (states at layers 9/17/22/29: read positions P-1..P+95 and the T1
    identifying-token read position; per-template SPEC states), then the S2 instrument gate (FVE, L0, dead share,
    spliced-in delta CE with BOS excluded and error NOT added back, loss recovered vs zero ablation) on corpus A
    (task prompts + own programs) against corpus B (wikitext-103 + LeetCode statements with greedy answers), plus a
    descriptive corpus C (human-written Python from the dependency: TheAlgorithms BFS/DFS files, HumanEval+)."""
    import numpy as np
    import torch

    import engine as EG
    import prompts as PG
    from cfg import STATES_DIR, stable_seed
    from gen import Runner
    from sae import load_saes
    from units import ox_norm

    run = Runner()
    tok = run.tok
    layers = list(SAE_LAYERS)
    fk = read_json(RESULTS_DIR / "fork.json") if (RESULTS_DIR / "fork.json").exists() else {"identifying": {}}
    # ---------------- teacher-forced states
    for task in TASKS_S3:
        outp = STATES_DIR / f"s3_{task}.pt"
        if outp.exists() and not args.redo:
            continue
        rows = load_labelled("raw_s3.jsonl", task)
        rows = [r for r in rows if r["arm"] == "twin"]
        rows.sort(key=lambda r: (r["template"], r["slot"]))
        H = torch.zeros(len(rows), N_READ + 1, len(layers), 2560, dtype=torch.float16)
        spec = {}
        meta = []
        for i, r in enumerate(rows):
            p = PG.p_twin(task, r["template"])
            P = p["P"]
            resp = response_ids(r)
            ident = (fk["identifying"].get(r["row_id"]) or {}).get("idx")
            rid = None if ident is None else P + ident - 1
            ids = p["ids"] + resp[:max(N_READ, (ident or 0) + 1)]
            pos = [P - 1 + j for j in range(N_READ)]
            pos_ok = [q for q in pos if q < len(ids)]
            want = pos_ok + ([rid] if rid is not None and rid < len(ids) else [])
            st = run.states(ids, layers, positions=None)["h"]
            for li, l in enumerate(layers):
                H[i, :len(pos_ok), li] = st[l][pos_ok].half()
                if rid is not None and rid < len(ids):
                    H[i, N_READ, li] = st[l][rid].half()
            if r["template"] not in spec:
                spec[r["template"]] = {"S": {l: st[l][p["spec_start"]:p["spec_end"]].half() for l in layers},
                                       "R": {l: st[l][P - 1].half() for l in layers},
                                       "spec_start": p["spec_start"], "spec_end": p["spec_end"], "P": P}
            meta.append({"row_id": r["row_id"], "template": r["template"], "slot": r["slot"], "label": r["label"],
                         "passed": r["passed"], "valid": r["valid"], "P": P, "n_resp": len(resp),
                         "n_pos": len(pos_ok), "ident_idx": ident, "rid_abs": rid, "resp_ids": resp[:400]})
            del st
        torch.save({"H": H, "meta": meta, "spec": spec, "layers": layers, "read_positions": "P-1..P+95, then r_id"},
                   outp)
        logger.info(f"states {task}: {len(rows)} samples -> {outp.name}")
        del H
        gc.collect()
    # ---------------- S2 gate
    saes = load_saes("cuda", tuple(layers))
    gate_path = RESULTS_DIR / "gate.json"
    texts: dict[str, list[dict[str, Any]]] = {"A": [], "B": [], "C": []}
    # corpus A: twin prompt + own program, response tokens scored (60 programs per task)
    for task in TASKS_S3:
        rows = [r for r in load_labelled("raw_s3.jsonl", task) if r["arm"] == "twin" and r["valid"]]
        rng = np.random.default_rng(stable_seed("gateA", task) % 2 ** 32)
        pick = sorted(rng.choice(len(rows), size=min(60, len(rows)), replace=False).tolist())
        for j in pick:
            r = rows[j]
            p = PG.p_twin(task, r["template"])
            texts["A"].append({"ids": p["ids"] + response_ids(r), "score_from": p["P"], "src": f"{task}:own"})
    # corpus B: wikitext-103 passages + LeetCode statements (chat) with the model's greedy answers
    wk = gate_wikitext(tok, 100)
    texts["B"] += [{"ids": ids, "score_from": 1, "src": "wikitext"} for ids in wk]
    lc = read_json(ROOT / "inputs" / "dep_extract" / "leetcode_nonbench.json")[:100]
    gen_items = []
    for i, q in enumerate(lc):
        rendered, ids, _ = PG.render(q["input"][:2500] + "\n\nWrite a Python solution.")
        gen_items.append({"row_id": f"gate|lc|{q['qid']}", "ids": ids, "n_prefix": 0, "prefix_ids": [],
                          "ukey": ("iter6S-gate", q["qid"]), "meta": {"qid": q["qid"], "P": len(ids)}})
    greedy_path = DATA_DIR / "gate_greedy.jsonl"
    done = {r["row_id"] for r in read_jsonl(greedy_path)}
    todo = [g for g in gen_items if g["row_id"] not in done]
    if todo:
        greedy(run, todo, 512, greedy_path)
    for g in read_jsonl(greedy_path):
        it = next(x for x in gen_items if x["row_id"] == g["row_id"])
        texts["B"].append({"ids": it["ids"] + response_ids(g), "score_from": len(it["ids"]), "src": "leetcode"})
    # corpus C (descriptive): human-written Python from the dependency
    for c in read_json(ROOT / "inputs" / "dep_extract" / "human_code.json")[:60]:
        ids = tok("<bos>" + c["code"][:4000], add_special_tokens=False)["input_ids"][:768]
        texts["C"].append({"ids": ids, "score_from": 1, "src": c["src"]})
    res = gate_measure(run, saes, texts, layers)
    res["rule"] = "PASS if dCE_A <= 1.5 dCE_B and FVU_A <= 1.5 FVU_B"
    for l in layers:
        a, b = res["sites"][str(l)]["A"], res["sites"][str(l)]["B"]
        res["sites"][str(l)]["pass"] = bool(a["dCE"] <= 1.5 * b["dCE"] and a["FVU"] <= 1.5 * b["FVU"])
        res["sites"][str(l)]["U3_generic_ok"] = bool(30 <= b["L0"] <= 60 and b["FVE"] > 0.5)
    res["n_texts"] = {k: len(v) for k, v in texts.items()}
    write_json(gate_path, res)
    logger.info("gate: " + json.dumps({l: (res['sites'][str(l)]['pass'], round(res['sites'][str(l)]['A']['dCE'], 3),
                                            round(res['sites'][str(l)]['B']['dCE'], 3)) for l in layers}))
    run.free()
    _ = (EG, ox_norm)


def gate_wikitext(tok: Any, n: int) -> list[list[int]]:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    fp = hf_hub_download("Salesforce/wikitext", "wikitext-103-raw-v1/test-00000-of-00001.parquet",
                         repo_type="dataset")
    lines = [x for x in pq.read_table(fp).column("text").to_pylist()]
    # passages: consecutive non-heading lines joined until ~512 tokens
    out, cur = [], ""
    for ln in lines:
        if ln.strip().startswith("="):
            if len(cur) > 1500:
                out.append(cur)
            cur = ""
            continue
        cur += ln
        if len(cur) > 2600:
            out.append(cur)
            cur = ""
        if len(out) >= n:
            break
    return [tok("<bos>" + t, add_special_tokens=False)["input_ids"][:512] for t in out[:n]]


def greedy(run: Any, items: list[dict[str, Any]], max_new: int, path: Path) -> None:
    """Greedy answers (temperature 1e-6 in the inverse-CDF sampler = argmax), multi-prompt batches of 20."""
    import numpy as np

    import engine as EG
    for b0 in range(0, len(items), 20):
        chunk = items[b0:b0 + 20]
        pre = EG.prefill_multi(run.model, [c["ids"] for c in chunk])
        U = np.full((len(chunk), max_new), 0.5)
        res = EG.decode(run.model, run.tok, pre, U, np.full(len(chunk), 1e-6), max_new)
        append_jsonl(path, [{"row_id": c["row_id"], "token_ids": g["token_ids"], "finish_reason": g["finish_reason"],
                             "text": g["text"], **c["meta"]} for c, g in zip(chunk, res)])
        logger.info(f"greedy {b0}: {len(chunk)} rows, {res[0]['steps']} steps")


def gate_measure(run: Any, saes: dict, texts: dict[str, list[dict[str, Any]]], layers: list[int]) -> dict[str, Any]:
    """Per corpus and SAE site: L0, FVE (full and with the 5 massive channels excluded), dead-latent share,
    CE clean / spliced (xhat at block-l output, BOS excluded, error not added back) / zero-ablated."""
    import torch

    import engine as EG
    from push import block_hooks

    acc = {str(l): {k: {"sse": 0.0, "sst": 0.0, "sse_ox": 0.0, "sst_ox": 0.0, "l0": 0.0, "n": 0, "ce_clean": 0.0,
                        "ce_splice": 0.0, "ce_zero": 0.0, "n_ce": 0, "alive": torch.zeros(saes[l].d_sae, dtype=torch.bool)}
                    for k in texts} for l in layers}
    means: dict[str, dict[int, torch.Tensor]] = {}

    def ce_of(hidden: torch.Tensor, ids: list[int], s0: int) -> torch.Tensor:
        """per-token CE of ids[s0:] from final hidden states [L, D] (lm_head in chunks of 256 positions)."""
        out = []
        for c0 in range(s0 - 1, len(ids) - 1, 256):
            c1 = min(c0 + 256, len(ids) - 1)
            lp = torch.log_softmax(EG.lm_logits(run.model, hidden[c0:c1]).float(), -1)
            tg = torch.tensor(ids[c0 + 1:c1 + 1], device=lp.device)
            out.append(-lp.gather(-1, tg[:, None])[:, 0])
            del lp
        return torch.cat(out)

    with torch.no_grad():
        for corpus, items in texts.items():
            # corpus mean per layer for the FVE denominator (first pass)
            sums = {l: torch.zeros(2560, device="cuda", dtype=torch.float64) for l in layers}
            cnt = 0
            cache = []
            for it in items:
                ids = it["ids"]
                cap = {}

                def mk(l):
                    def g(h):
                        cap[l] = h[0].float()
                    return g
                with block_hooks(EG.layers(run.model), None, {l: mk(l) for l in layers}):
                    out = run.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
                ce0 = ce_of(out.last_hidden_state[0], ids, it["score_from"])
                s0 = it["score_from"]
                for l in layers:
                    x = cap[l][s0:]
                    sums[l] += x.double().sum(0)
                cnt += len(ids) - s0
                cache.append((ids, s0, ce0))
                for l in layers:
                    x = cap[l][s0:]
                    f, xh = saes[l].recon(x)
                    a = acc[str(l)][corpus]
                    a["l0"] += float((f > 0).sum())
                    a["n"] += x.shape[0]
                    a["alive"] |= (f > 0).any(0).cpu()
                    a["sse"] += float(((x - xh) ** 2).sum())
                    M = x.abs().topk(5, dim=-1).indices
                    mask = torch.ones_like(x)
                    mask.scatter_(1, M, 0.0)
                    a["sse_ox"] += float((((x - xh) * mask) ** 2).sum())
                    a["_x2"] = a.get("_x2", 0.0) + float((x.double() ** 2).sum())
                    a["_x2_ox"] = a.get("_x2_ox", 0.0) + float(((x * mask).double() ** 2).sum())
                    a["_sumx_ox"] = a.get("_sumx_ox", 0) + (x * mask).double().sum(0)
                del out, cap
            means[corpus] = {l: (sums[l] / max(cnt, 1)) for l in layers}
            for l in layers:
                a = acc[str(l)][corpus]
                mu = means[corpus][l]
                a["sst"] = a["_x2"] - float(cnt * (mu ** 2).sum())
                mu_ox = a["_sumx_ox"] / max(cnt, 1)
                a["sst_ox"] = a["_x2_ox"] - float(cnt * (mu_ox ** 2).sum())
            # CE under splice / zero ablation
            for ids, s0, ce0 in cache:
                for l in layers:
                    a = acc[str(l)][corpus]

                    def spl(h, l=l):
                        x = h.float()
                        _, xh = saes[l].recon(x[:, 1:])
                        h2 = h.clone()
                        h2[:, 1:] = xh.to(h.dtype)
                        return h2

                    def zer(h):
                        h2 = h.clone()
                        h2[:, 1:] = 0
                        return h2
                    for kind, fn in (("splice", spl), ("zero", zer)):
                        with block_hooks(EG.layers(run.model), {l: fn}, None):
                            out = run.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
                        a[f"ce_{kind}"] += float(ce_of(out.last_hidden_state[0], ids, s0).sum())
                        del out
                    a["ce_clean"] += float(ce0.sum())
                    a["n_ce"] += len(ids) - s0
            logger.info(f"gate corpus {corpus}: {len(items)} texts, {cnt} tokens")
    res: dict[str, Any] = {"sites": {}}
    for l in layers:
        site = {}
        for corpus in texts:
            a = acc[str(l)][corpus]
            n_ce = max(a["n_ce"], 1)
            ce_c, ce_s, ce_z = a["ce_clean"] / n_ce, a["ce_splice"] / n_ce, a["ce_zero"] / n_ce
            site[corpus] = {"n_tokens": a["n"], "L0": a["l0"] / max(a["n"], 1),
                            "FVU": a["sse"] / max(a["sst"], 1e-9), "FVE": 1 - a["sse"] / max(a["sst"], 1e-9),
                            "FVU_ox": a["sse_ox"] / max(a["sst_ox"], 1e-9),
                            "FVE_ox": 1 - a["sse_ox"] / max(a["sst_ox"], 1e-9),
                            "dead_share": 1 - float(a["alive"].float().mean()),
                            "CE_clean": ce_c, "CE_splice": ce_s, "CE_zero": ce_z, "dCE": ce_s - ce_c,
                            "loss_recovered": (ce_z - ce_s) / max(ce_z - ce_c, 1e-9)}
        res["sites"][str(l)] = site
    return res


# ================================================================================================ S5 variants
def choose_nouns(tok: Any) -> dict[str, Any]:
    """12 frozen exp7 T1 nouns + 12 new nouns from the dependency's flagged concreteness-norm candidates (same
    Gemma token count as the frozen nouns, stoplist and exp7 exclusions removed, by SUBTLEX frequency, alignable in
    all five templates)."""
    import prompts as PG
    from cfg import E7, NOUN_STOPLIST

    fz = read_json(E7 / "frozen" / "templates_nouns_padding.json")
    frozen = []
    from cfg import T1_MODES
    for m in T1_MODES:
        ab = fz["nouns"]["t1"][m]
        frozen += [ab["A"], ab["B"]]
    excl = set(fz["templates"]["noun_exclusions"]) | set(NOUN_STOPLIST) | set(frozen)
    ntok = {n: len(tok(" " + n, add_special_tokens=False)["input_ids"]) for n in frozen}
    want = sorted(set(ntok.values()))
    cand = read_json(ROOT / "inputs" / "dep_extract" / "noun_candidates.json")
    cand = sorted(cand, key=lambda c: (-float(c["subtlex"] or 0), c["word"]))
    new = []
    for c in cand:
        w = c["word"]
        if w in excl or not w.isalpha() or not w.islower():
            continue
        if len(tok(" " + w, add_special_tokens=False)["input_ids"]) not in want:
            continue
        if all(PG.p_noun_variant("T1", t, w) is not None for t in TEMPLATE_IDS):
            new.append(w)
        if len(new) == 12:
            break
    return {"frozen": frozen, "new": new, "frozen_token_counts": ntok,
            "new_meta": {c["word"]: c for c in cand if c["word"] in new}}


def y_from_logits(logits: Any, fk: dict[str, Any]) -> float:
    """Fork logit readout y (committed in fork.json/commit #1): log sum_B p - log sum_D p, else
    logit(sum_tok p(tok) q(tok)) with q = P(BFS | fork token) (tokens with < 3 observations -> marginal)."""
    import torch

    lp = torch.log_softmax(logits.float(), -1)
    if fk["B_set"] and fk["D_set"]:
        b = torch.logsumexp(lp[fk["B_set"]], 0)
        d = torch.logsumexp(lp[fk["D_set"]], 0)
        return float(b - d)
    q = torch.full_like(lp, fk["q_marginal"])
    for t, v in fk["token_table"].items():
        if not v["pooled"] and v["p_bfs"] is not None:
            q[int(t)] = v["p_bfs"]
    s = float((lp.exp() * q).sum().clamp(1e-6, 1 - 1e-6))
    import math
    return math.log(s / (1 - s))


def all_contrast_prompts() -> list[dict[str, Any]]:
    import prompts as PG
    from cfg import T1_MODES

    out = []
    for m in T1_MODES:
        for f in ("F1", "F2", "F3", "F4", "F5"):
            p = PG.p_forced("T1", m, f)
            out.append({**p, "group": f"forced_{m}", "tag": f"forced|{m}|{f}"})
        for i in range(10):
            p = PG.p_forced_para("T1", m, i)
            out.append({**p, "group": f"forced_{m}", "tag": f"para|{m}|{i}"})
    for w in TEMPLATE_IDS:
        for m in ("bfs", "dfs"):
            out.append({**PG.p_ban("T1", m, w), "group": f"ban_{m}", "tag": f"ban|{m}|{w}"})
        b, n = PG.p_top5("T1", w)
        out.append({**b, "group": "top5", "tag": f"top5|{w}"})
        out.append({**n, "group": "top5_twin", "tag": f"top5_twin|{w}"})
        out.append({**PG.p_twin("T1", w), "group": "twin", "tag": f"twin|{w}"})
    return out


def stage_variants(args: argparse.Namespace) -> None:
    """S5: 120 neutral variants (y_v at the fork + cached states), contrast-prompt states, sampling validation."""
    import numpy as np
    import torch

    import fork as F
    import prompts as PG
    from cfg import STATES_DIR, T1_MODES
    from gen import Runner
    from sae import load_saes

    run = Runner()
    tok = run.tok
    fk = read_json(RESULTS_DIR / "fork.json")
    cstar = fk["cstar_ids"]
    valid = [r for r in load_labelled("raw_s3.jsonl", "T1") if r["valid"] and r["label"] not in ("invalid", "disputed")]
    fk["q_marginal"] = sum(r["label"] == "bfs" for r in valid) / len(valid)
    nouns = choose_nouns(tok)
    write_json(RESULTS_DIR / "nouns.json", nouns)
    saes = load_saes("cuda", tuple(SAE_LAYERS))
    all_layers = list(range(34))

    def states_for(p: dict[str, Any], per_pos_sae: bool = False) -> dict[str, Any]:
        ids = p["ids"] + cstar
        st = run.states(ids, all_layers, positions=None, want_logits_at=[len(ids) - 1])
        a, b = p["spec_start"], p["spec_end"]
        h = st["h"]
        rec = {"fork": torch.stack([h[l][-1] for l in all_layers]).half(),
               "spec_mean": torch.stack([h[l][a:b].mean(0) for l in all_layers]).half(),
               "y": y_from_logits(st["logits"][0], fk), "P": p["P"], "spec_start": a, "spec_end": b,
               "logits_top": torch.topk(st["logits"][0].float(), 20)}
        codes_f, codes_s = {}, {}
        for l in SAE_LAYERS:
            hf = h[l][-1:].cuda()
            hs = h[l][a:b].cuda()
            codes_f[l] = saes[l].encode(hf)[0].half().cpu()
            codes_s[l] = saes[l].encode(hs).mean(0).half().cpu()
        rec["codes_fork"] = codes_f
        rec["codes_spec_mean"] = codes_s
        if per_pos_sae:
            rec["spec_states"] = {l: h[l][a:b].half() for l in SAE_LAYERS}
        rec["logits_top"] = {"ids": rec["logits_top"].indices.tolist(), "vals": rec["logits_top"].values.tolist()}
        del st, h
        return rec

    # ---------------- 120 neutral variants
    var_path = STATES_DIR / "variants.pt"
    if not var_path.exists() or args.redo:
        V = []
        for w in TEMPLATE_IDS:
            for src, lst in (("frozen", nouns["frozen"]), ("new", nouns["new"])):
                for n in lst:
                    p = PG.p_noun_variant("T1", w, n)
                    if p is None:
                        logger.warning(f"variant {w}/{n} not alignable")
                        continue
                    PG.register(p)
                    rec = states_for(p)
                    rec.update({"template": w, "noun": n, "noun_source": src, "ids": p["ids"],
                                "prompt_sha256": p["prompt_sha256"]})
                    V.append(rec)
        torch.save(V, var_path)
        ys = np.array([v["y"] for v in V])
        logger.info(f"variants: {len(V)}; y mean {ys.mean():.3f} sd {ys.std():.3f}")
    V = torch.load(var_path)
    # ---------------- contrast prompts
    con_path = STATES_DIR / "contrast.pt"
    if not con_path.exists() or args.redo:
        C = []
        for p in all_contrast_prompts():
            PG.register(p)
            rec = states_for(p, per_pos_sae=p["group"] in ("forced_bfs", "forced_dfs", "twin"))
            rec.update({"group": p["group"], "tag": p["tag"], "template": p.get("template"), "ids": p["ids"],
                        "aligned": p.get("aligned", True), "prompt_sha256": p["prompt_sha256"]})
            C.append(rec)
        torch.save(C, con_path)
        logger.info(f"contrast states: {len(C)}")
    # ---------------- sampling validation: 60 variants (frozen nouns) x N=10 from prompt + c*, partial labeller
    sv_path = DATA_DIR / "sampling_validation.jsonl"
    done = {r["row_id"] for r in read_jsonl(sv_path)}
    items = []
    for v in V:
        if v["noun_source"] != "frozen":
            continue
        for k in range(args.sv_n):
            rid = f"sv|{v['template']}|{v['noun']}|{k}"
            if rid in done:
                continue
            items.append({"row_id": rid, "ids": v["ids"] + cstar, "n_prefix": len(cstar), "prefix_ids": cstar,
                          "ukey": slot_key("T1", v["template"], k),
                          "meta": {"template": v["template"], "noun": v["noun"], "slot": k, "y": v["y"]}})
    if items:
        run.run_multi(items, 320, "sv", sv_path, "SV", B=48, stop_fn=F.decided)
    rows = read_jsonl(sv_path)
    for r in rows:
        r["cls"] = F.partial_label(r["text"]) or "other"
    write_jsonl_cls = [{"row_id": r["row_id"], "template": r["template"], "noun": r["noun"], "slot": r["slot"],
                        "y": r["y"], "cls": r["cls"], "n_new_tokens": r["n_new_tokens"],
                        "finish_reason": r["finish_reason"]} for r in rows]
    from cfg import write_jsonl
    write_jsonl(DATA_DIR / "sampling_validation_labels.jsonl", write_jsonl_cls)
    run.free()
    _ = (T1_MODES, F)


# ================================================================================================ S7 selection
def y_torch(logits: Any, fk: dict[str, Any]) -> Any:
    """Differentiable fork readout (same rule as y_from_logits)."""
    import torch

    lp = torch.log_softmax(logits.float(), -1)
    if fk["B_set"] and fk["D_set"]:
        return torch.logsumexp(lp[fk["B_set"]], 0) - torch.logsumexp(lp[fk["D_set"]], 0)
    q = torch.full_like(lp, fk["q_marginal"])
    for t, v in fk["token_table"].items():
        if not v["pooled"] and v["p_bfs"] is not None:
            q[int(t)] = v["p_bfs"]
    s = (lp.exp() * q).sum().clamp(1e-6, 1 - 1e-6)
    return torch.log(s / (1 - s))


def fork_ctx() -> dict[str, Any]:
    fk = read_json(RESULTS_DIR / "fork.json")
    valid = [r for r in load_labelled("raw_s3.jsonl", "T1") if r["valid"] and r["label"] not in ("invalid", "disputed")]
    fk["q_marginal"] = sum(r["label"] == "bfs" for r in valid) / len(valid)
    return fk


def site_positions(site: str, ids_full: list[int], spec_start: int, spec_end: int) -> list[int]:
    return [len(ids_full) - 1] if site == "FORK" else list(range(spec_start, spec_end))


def y_rows(run: Any, ids: list[int], row_specs: list[Any], fk: dict[str, Any]) -> list[float]:
    """One batched prefill of `ids` with per-row live edits; y at the last position per row."""
    import engine as EG
    from clamp import live_edits

    out = EG.prefill_single(run.model, ids, len(row_specs), edits=live_edits(row_specs))
    ys = [float(y_torch(out["logits"][i], fk)) for i in range(len(row_specs))]
    del out
    return ys


def stage_select(args: argparse.Namespace) -> None:
    """S7: input-score (forced contrast) and output-score (attribution patching) feature sets, ban-contrast sets,
    DiM/RANDF/ISO directions, the layer rule on held-out templates, then COMMIT #1 (before any clamp generation)."""
    import numpy as np
    import torch

    import engine as EG
    from cfg import ACTIVE_FRAC, K_SET, LAM_SET, STATES_DIR
    from clamp import (EditSpec, iso_dir, massive_channels, ox_mask, randf_dir, top_by_attr, top_by_d,
                       unit_masked)
    from commit import commit
    from gen import Runner
    from push import block_hooks
    from sae import load_saes

    fk = fork_ctx()
    cstar = fk["cstar_ids"]
    gate = read_json(RESULTS_DIR / "gate.json")
    gated = [l for l in SAE_LAYERS if gate["sites"][str(l)]["pass"]]
    gate_note = "gated" if gated else "ALL SITES FAILED THE GATE: SAE results descriptive only"
    use_layers = gated or list(SAE_LAYERS)
    run = Runner()
    saes = load_saes("cuda", tuple(SAE_LAYERS))
    V = torch.load(STATES_DIR / "variants.pt")
    C = torch.load(STATES_DIR / "contrast.pt")
    grp = lambda g: [c for c in C if c["group"] == g]  # noqa: E731
    fb, fd, bb, bd, tw = grp("forced_bfs"), grp("forced_dfs"), grp("ban_bfs"), grp("ban_dfs"), grp("twin")
    SPEC_LEN = tw[0]["spec_end"] - tw[0]["spec_start"]
    sel: dict[str, Any] = {"gated_layers": gated, "use_layers": use_layers, "gate_note": gate_note}
    M = {l: massive_channels(torch.cat([t["spec_states"][l].float() for t in tw])) for l in SAE_LAYERS}
    mask = {l: ox_mask(M[l]) for l in SAE_LAYERS}
    sel["massive_channels"] = {str(l): M[l].tolist() for l in SAE_LAYERS}

    def codes(group: list, site: str, l: int) -> torch.Tensor:
        key = "codes_fork" if site == "FORK" else "codes_spec_mean"
        return torch.stack([c[key][l].float() for c in group])

    def spec_codes(group: list, l: int) -> torch.Tensor:
        """[n, SPEC_LEN, F] per-position codes (relative spec index)."""
        return torch.stack([saes[l].encode(c["spec_states"][l].float().cuda()).cpu() for c in group])

    targets: dict[str, Any] = {}
    sets: dict[str, Any] = {"input": {}, "ban": {}, "output": {}}
    for l in SAE_LAYERS:
        sc_b, sc_d = spec_codes(fb, l), spec_codes(fd, l)
        targets[f"SPEC|{l}|bfs"] = sc_b.mean(0)             # [SPEC_LEN, F]
        targets[f"SPEC|{l}|dfs"] = sc_d.mean(0)
        targets[f"FORK|{l}|bfs"] = codes(fb, "FORK", l).mean(0)
        targets[f"FORK|{l}|dfs"] = codes(fd, "FORK", l).mean(0)
        for site in ("FORK", "SPEC"):
            for k in K_SET:
                sets["input"][f"{site}|{l}|{k}"] = top_by_d(codes(fb, site, l), codes(fd, site, l), k, ACTIVE_FRAC)
            sets["ban"][f"{site}|{l}|20"] = top_by_d(codes(bd, site, l), codes(bb, site, l), 20, ACTIVE_FRAC)
        del sc_b, sc_d
    # ---------------- output score: attribution patching on W1-W3 variants
    attr = {f"{s}|{l}": [] for s in ("FORK", "SPEC") for l in SAE_LAYERS}
    lay = EG.layers(run.model)
    for v in V:
        if v["template"] not in ("W1", "W2", "W3"):
            continue
        ids = v["ids"] + cstar
        cap: dict[int, Any] = {}

        def mk(l):
            def g(h):
                h.retain_grad()
                cap[l] = h
            return g
        hemb = run.model.model.embed_tokens.register_forward_hook(
            lambda m, i, o: o.detach().requires_grad_(True))
        try:
            with torch.enable_grad(), block_hooks(lay, None, {l: mk(l) for l in SAE_LAYERS}):
                out = run.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
                y = y_torch(EG.lm_logits(run.model, out.last_hidden_state[0, -1]), fk)
                y.backward()
        finally:
            hemb.remove()
        a, b = v["spec_start"], v["spec_end"]
        with torch.no_grad():
            for l in SAE_LAYERS:
                h = cap[l][0].detach().float()
                g = cap[l].grad[0].float()
                f = saes[l].encode(h[[-1] + list(range(a, b))])
                gd = g[[-1] + list(range(a, b))] @ saes[l].W_dec.T      # [1+S, F]
                s = f * gd
                attr[f"FORK|{l}"].append(s[0].cpu())
                attr[f"SPEC|{l}"].append(s[1:].sum(0).cpu())
        del out, cap, y
        torch.cuda.empty_cache()
    for key, lst in attr.items():
        S = torch.stack(lst)
        site, l = key.split("|")
        for k in K_SET:
            sets["output"][f"{site}|{l}|{k}"] = top_by_attr(S, k)
    # ---------------- DiM directions, RANDF and ISO
    dirs: dict[str, Any] = {}
    s3 = torch.load(STATES_DIR / "s3_T1.pt")
    for li, l in enumerate(SAE_LAYERS):
        Xs = s3["H"][:, :N_READ, li].reshape(-1, 2560)
        Xs = Xs[Xs.abs().sum(-1) > 0].float()
        freq = torch.zeros(saes[l].d_sae)
        for i in range(0, Xs.shape[0], 4096):
            freq += (saes[l].encode(Xs[i:i + 4096].cuda()) > 0).float().sum(0).cpu()
        freq /= Xs.shape[0]
        dirs[f"freq|{l}"] = freq
        for site in ("FORK", "SPEC"):
            if site == "FORK":
                mb = torch.stack([c["fork"][l].float() for c in fb]).mean(0)
                md = torch.stack([c["fork"][l].float() for c in fd]).mean(0)
            else:
                mb = torch.stack([c["spec_states"][l].float().mean(0) for c in fb]).mean(0)
                md = torch.stack([c["spec_states"][l].float().mean(0) for c in fd]).mean(0)
            dirs[f"DiM|{site}|{l}"] = unit_masked(mb - md, mask[l]).cpu()
            dirs[f"ISO|{site}|{l}"] = iso_dir(("iso", site, l), mask[l]).cpu()
            for k in K_SET:
                d, lat, sg = randf_dir(saes[l], freq, k, ("randf", site, l, k), mask[l])
                dirs[f"RANDF|{site}|{l}|{k}"] = d.cpu()
                dirs[f"RANDF_lat|{site}|{l}|{k}"] = (lat, sg)
    del s3
    # ---------------- layer rule: held-out W4-W5 variants, FEAT-input k=20 lam=1 toward BFS
    def feat_spec(site: str, l: int, k: int, lam: float, src: str, toward: str, v: dict) -> Any:
        lat = sets[src][f"{site}|{l}|{k}"]["idx"]
        T = targets[f"{site}|{l}|{toward}"]
        T = T[:, lat] if site == "SPEC" else T[lat]
        pos = site_positions(site, v["ids"] + cstar, v["spec_start"], v["spec_end"])
        return EditSpec("FEAT", l, pos, saes[l], lat=lat, target=T, lam=lam, mask=mask[l])

    rule = {}
    held = [v for v in V if v["template"] in ("W4", "W5")]
    for site in ("FORK", "SPEC"):
        per_l = {}
        for l in use_layers:
            dys, norms = [], []
            for v in held:
                sp = feat_spec(site, l, 20, 1.0, "input", "bfs", v)
                y1 = y_rows(run, v["ids"] + cstar, [[sp]], fk)[0]
                dys.append(y1 - v["y"])
                norms.append(sp.log["ox_norm_mean"])
            per_l[str(l)] = {"mean_dy": float(np.mean(dys)), "mean_ox_norm": float(np.mean(norms)),
                             "dy_per_norm": float(np.mean(dys) / max(np.mean(norms), 1e-9))}
        best = max(per_l, key=lambda kk: per_l[kk]["dy_per_norm"])
        rule[site] = {"per_layer": per_l, "layer": int(best)}
    sel["layer_rule"] = rule
    sel["sets"] = sets
    sel["dirs_meta"] = {k: (v if isinstance(v, tuple) else None) for k, v in dirs.items() if k.startswith("RANDF_lat")}
    torch.save({"targets": targets, "dirs": dirs, "masks": {l: mask[l].cpu() for l in SAE_LAYERS}, "sets": sets,
                "rule": rule, "M": M}, STATES_DIR / "selection.pt")
    write_json(RESULTS_DIR / "selection.json", sel)
    # ---------------- generation cell list (toward BFS unless stated); lam = 1
    better = max(("FORK", "SPEC"), key=lambda s: rule[s]["per_layer"][str(rule[s]["layer"])]["mean_dy"])
    cells = []
    for site in ("FORK", "SPEC"):
        for k in (5, 20, 50):
            cells.append({"cell": f"{site}|FEATin|k{k}", "site": site, "kind": "FEAT", "src": "input", "k": k,
                          "toward": "bfs"})
        cells.append({"cell": f"{site}|DiM@k20", "site": site, "kind": "DiM", "src": "input", "k": 20, "toward": "bfs"})
        cells.append({"cell": f"{site}|DiM@k50", "site": site, "kind": "DiM", "src": "input", "k": 50, "toward": "bfs"})
        cells.append({"cell": f"{site}|RANDF@k50", "site": site, "kind": "RANDF", "src": "input", "k": 50,
                      "toward": "bfs"})
    cells.append({"cell": f"{better}|FEATout|k20", "site": better, "kind": "FEAT", "src": "output", "k": 20,
                  "toward": "bfs"})
    cells.append({"cell": f"{better}|FEATin|k20|toDFS", "site": better, "kind": "FEAT", "src": "input", "k": 20,
                  "toward": "dfs"})
    cells.append({"cell": f"{better}|DiM@k20|toDFS", "site": better, "kind": "DiM", "src": "input", "k": 20,
                  "toward": "dfs"})
    code_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted((ROOT / "src").glob("*.py"))}
    code_hashes["method.py"] = sha256_file(ROOT / "method.py")
    c1 = commit("commit1", {
        "cstar_ids": cstar, "cstar_text": fk["cstar_text"], "fork_token_index": fk["fork_token_index"],
        "B_set": fk["B_set"], "D_set": fk["D_set"], "B_tokens": fk["B_tokens"], "D_tokens": fk["D_tokens"],
        "y_rule": "log sum_B p - log sum_D p" if (fk["B_set"] and fk["D_set"]) else "logit(sum p q)",
        "q_marginal": fk["q_marginal"], "gate": {l: gate["sites"][str(l)]["pass"] for l in SAE_LAYERS},
        "gate_note": gate_note, "layer_rule": rule, "better_site": better, "sets": sets,
        "dim_sha256": {k: __import__("hashlib").sha256(v.numpy().tobytes()).hexdigest() for k, v in dirs.items()
                       if k.startswith(("DiM|", "ISO|", "RANDF|"))},
        "randf_latents": sel["dirs_meta"], "doses": {"lam_cells": 1.0, "lam_sweep": list(LAM_SET)},
        "cells": cells, "N_per_cell": 50, "selection_pt_sha256": sha256_file(STATES_DIR / "selection.pt"),
        "nouns": read_json(RESULTS_DIR / "nouns.json"), "code_sha256": code_hashes,
        "thresholds": {"feature_claim": "FEAT target-correct >= DiM target-correct at matched norm, pass >= 0.8 x twin pass",
                       "randf": "FEAT - RANDF >= 0.20 with exact McNemar p < 0.05", "holm": "within family S"}})
    logger.info(f"commit1 {c1['sha256'][:12]}: layers {rule}, better site {better}")
    run.free()


# ================================================================================================ S8 clamps
def stage_clamps(args: argparse.Namespace) -> None:
    """S8: logit-level dose-response sweep on the 120 variants, then the 15 generation cells (N=50 each) plus the
    canonical-prefix twin, all CRN-paired (W1-W5 x slots 0-9, keys of the S3 slots 0-9)."""
    import numpy as np
    import torch

    import engine as EG
    import prompts as PG
    from cfg import CAPTURE_BLOCKS, K_SET, LAM_SET, STATES_DIR
    from clamp import EditSpec
    from gen import Runner
    from sae import load_saes

    c1 = read_json(PRED_DIR / "commit1.json")
    fk = fork_ctx()
    cstar = c1["cstar_ids"]
    S = torch.load(STATES_DIR / "selection.pt")
    targets, dirs, masks, sets, rule = S["targets"], S["dirs"], S["masks"], S["sets"], S["rule"]
    run = Runner()
    saes = load_saes("cuda", tuple(SAE_LAYERS))

    def feat(site, l, k, lam, src, toward, pos):
        lat = sets[src][f"{site}|{l}|{k}"]["idx"]
        T = targets[f"{site}|{l}|{toward}"]
        T = T[:, lat] if site == "SPEC" else T[lat]
        return EditSpec("FEAT", l, pos, saes[l], lat=lat, target=T, lam=lam, mask=masks[l])

    def control(kind, site, l, k, lam, toward, pos, src="input"):
        lat = sets[src][f"{site}|{l}|{k}"]["idx"]
        T = targets[f"{site}|{l}|{toward}"]
        T = T[:, lat] if site == "SPEC" else T[lat]
        if kind == "DiM":
            d = dirs[f"DiM|{site}|{l}"] * (1 if toward == "bfs" else -1)
        elif kind == "RANDF":
            d = dirs[f"RANDF|{site}|{l}|{k}"]
        else:
            d = dirs[f"ISO|{site}|{l}"]
        return EditSpec(kind, l, pos, saes[l], direction=d, mask=masks[l],
                        match={"lat": lat, "target": T, "lam": lam})

    # ---------------- logit-level sweep (forward passes only)
    sweep_path = RESULTS_DIR / "logit_sweep.jsonl"
    done = {(r["template"], r["noun"]) for r in read_jsonl(sweep_path)}
    V = torch.load(STATES_DIR / "variants.pt")
    if args.sweep_n:
        V = [v for v in V if v["noun_source"] == "frozen"][:args.sweep_n] if args.sweep_n <= 60 else V
    for v in V:
        if (v["template"], v["noun"]) in done:
            continue
        ids = v["ids"] + cstar
        cfgs = []
        for site in ("FORK", "SPEC"):
            l = rule[site]["layer"]
            pos = site_positions(site, ids, v["spec_start"], v["spec_end"])
            for src in ("input", "output"):
                for k in K_SET:
                    for lam in LAM_SET:
                        cfgs.append(({"site": site, "layer": l, "kind": "FEAT", "src": src, "k": k, "lam": lam},
                                     feat(site, l, k, lam, src, "bfs", pos)))
            for k in K_SET:
                for lam in LAM_SET:
                    for kind in ("DiM", "RANDF", "ISO"):
                        cfgs.append(({"site": site, "layer": l, "kind": kind, "src": "input", "k": k, "lam": lam},
                                     control(kind, site, l, k, lam, "bfs", pos)))
            cfgs.append(({"site": site, "layer": l, "kind": "FEAT", "src": "ban", "k": 20, "lam": 1.0},
                         feat(site, l, 20, 1.0, "ban", "bfs", pos)))
            for l2 in rule[site]["per_layer"]:
                l2 = int(l2)
                if l2 != l:
                    cfgs.append(({"site": site, "layer": l2, "kind": "FEAT", "src": "input", "k": 20, "lam": 1.0},
                                 feat(site, l2, 20, 1.0, "input", "bfs", pos)))
        out = []
        for b0 in range(0, len(cfgs), args.sweep_b):
            chunk = cfgs[b0:b0 + args.sweep_b]
            ys = y_rows(run, ids, [[sp] for _, sp in chunk], fk)
            for (meta, sp), y in zip(chunk, ys):
                out.append({"template": v["template"], "noun": v["noun"], "noun_source": v["noun_source"],
                            "y0": v["y"], "y": y, "dy": y - v["y"], **meta, **sp.log,
                            "held_out": v["template"] in ("W4", "W5")})
        append_jsonl(sweep_path, out)
    logger.info("logit sweep done")
    # ---------------- generation cells
    cells_path = DATA_DIR / "raw_cells.jsonl"
    done = {r["row_id"] for r in read_jsonl(cells_path)}
    n_slots = args.cell_slots
    extra = read_json(RESULTS_DIR / "extra_cells.json") if (RESULTS_DIR / "extra_cells.json").exists() else []
    for w in TEMPLATE_IDS:
        p = PG.p_twin("T1", w)
        ids = p["ids"] + cstar
        clean = EG.clean_states(run.model, ids, p["spec_start"], p["spec_end"], list(CAPTURE_BLOCKS))
        rows = []
        for k in range(n_slots):
            rows.append({"row_id": f"cell|T1|{w}|twin_cstar|{k}", "task": "T1", "arm": "twin_cstar",
                         "template": w, "slot": k, "ukey": slot_key("T1", w, k), "specs": None,
                         "meta": {"cell": "twin_cstar", "site": None}})
        for c in c1["cells"] + extra:
            site = c["site"]
            l = int(c.get("layer") or rule[site]["layer"])
            pos = site_positions(site, ids, p["spec_start"], p["spec_end"])
            lam = float(c.get("lam", 1.0))
            if c["kind"] == "FEAT":
                sp = feat(site, l, c["k"], lam, c["src"], c["toward"], pos)
            else:
                sp = control(c["kind"], site, l, c["k"], lam, c["toward"], pos, c["src"])
            for k in range(n_slots):
                rows.append({"row_id": f"cell|T1|{w}|{c['cell']}|{k}", "task": "T1", "arm": c["cell"],
                             "template": w, "slot": k, "ukey": slot_key("T1", w, k), "specs": [sp],
                             "meta": {"cell": c["cell"], "site": site, "layer": l, "kind": c["kind"],
                                      "src": c["src"], "k_features": c["k"], "toward": c["toward"], "lambda": lam}})
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_crn(p, rows, 1536, "cells", cells_path, f"CELL:{w}", prefix_ids=cstar, capture_ref=clean)
        del clean
        torch.cuda.empty_cache()
    run.free()
    _ = np


# ================================================================================================ S9 DAS
class DASSpec:
    """Interchange edit h <- h + R R^T (h_src - h) at one block output, one position (prefill only)."""

    def __init__(self, layer: int, pos: list[int], R: Any, h_src: Any):
        import torch

        self.kind, self.layer = "DAS", layer
        self.pos = torch.tensor(pos, device="cuda", dtype=torch.long)
        self.R = R.to("cuda").float()
        self.h_src = h_src.to("cuda").float()
        self.log: dict[str, float] = {}

    def dh(self, hs: Any) -> Any:
        d = (self.h_src[None] - hs) @ self.R @ self.R.T
        self.log = {"ox_norm_mean": float(d.norm(dim=-1).mean()), "norm_mean": float(d.norm(dim=-1).mean())}
        return d


def stage_das(args: argparse.Namespace) -> None:
    """S9: distributed alignment search at the FORK site (one layer, one position, linear rank-k subspace).
    Source = the forced-BFS prompt (F_i) of the same template, aligned at the last position of prompt + c*.
    Loss = KL(p_src || p_intervened) at the fork; train W1-W3 variants, evaluate W4-W5; controls = random rank-k
    subspace and shuffled-source DAS; generation N=50 for the best k (toward BFS)."""
    import numpy as np
    import torch

    import engine as EG
    import prompts as PG
    from cfg import STATES_DIR
    from gen import Runner
    from push import block_hooks

    fk = fork_ctx()
    cstar = fk["cstar_ids"]
    S = torch.load(STATES_DIR / "selection.pt")
    l = int(S["rule"]["FORK"]["layer"])
    run = Runner()
    lay = EG.layers(run.model)
    V = torch.load(STATES_DIR / "variants.pt")
    C = torch.load(STATES_DIR / "contrast.pt")
    src = {}
    for f_i, w in zip(["F1", "F2", "F3", "F4", "F5"], TEMPLATE_IDS):
        c = next(c for c in C if c["tag"] == f"forced|bfs|{f_i}")
        ids = c["ids"] + cstar
        st = run.states(ids, [l], positions=[len(ids) - 1], want_logits_at=[len(ids) - 1])
        src[w] = {"h": st["h"][l][0].cuda(), "logp": torch.log_softmax(st["logits"][0].float().cuda(), -1)}

    def cache_for(ids: list[int]) -> Any:
        pre = EG.prefill_single(run.model, ids[:-1], 1)
        return EG.build_prealloc(pre["kv"], len(ids))

    def step_logits(cache: Any, ids: list[int], hook) -> Any:
        P = len(ids)
        for L in cache.layers:
            L.kbuf, L.vbuf = L.kbuf.detach(), L.vbuf.detach()     # drop the previous step's autograd graph
            L.n = P - 1
            L.keys, L.values = L.kbuf[:, :, :L.n], L.vbuf[:, :, :L.n]
        with block_hooks(lay, {l: hook}, None):
            out = run.model.model(input_ids=torch.tensor([[ids[-1]]], device="cuda"), past_key_values=cache,
                                  position_ids=torch.tensor([[P - 1]], device="cuda"), use_cache=True)
        return EG.lm_logits(run.model, out.last_hidden_state[:, -1])[0]

    data = []
    for v in V:
        ids = v["ids"] + cstar
        data.append({"v": v, "ids": ids, "cache": cache_for(ids), "w": v["template"],
                     "train": v["template"] in ("W1", "W2", "W3")})
    logger.info(f"DAS: {len(data)} variant caches at layer {l}")

    def make_hook(R: Any, hsrc: Any):
        def f(h):
            x = h.float()
            x = x + (hsrc[None, None] - x) @ R @ R.T
            return x.to(h.dtype)
        return f

    def evaluate(R: Any, shuffle: bool = False, seed: int = 0) -> dict[str, Any]:
        rng = np.random.default_rng(seed)
        dys, dys_tr = [], []
        with torch.no_grad():
            for d in data:
                w = d["w"] if not shuffle else TEMPLATE_IDS[int(rng.integers(5))]
                lg = step_logits(d["cache"], d["ids"], make_hook(R, src[w]["h"]))
                dy = float(y_torch(lg, fk)) - d["v"]["y"]
                (dys_tr if d["train"] else dys).append(dy)
        return {"heldout_mean_dy": float(np.mean(dys)), "train_mean_dy": float(np.mean(dys_tr)),
                "heldout_frac_pos": float(np.mean(np.array(dys) > 0))}

    def train(k: int, shuffle: bool = False, epochs: int = 12, seed: int = 0) -> Any:
        g = torch.Generator(device="cpu").manual_seed(seed)
        W = torch.randn(2560, k, generator=g).cuda().requires_grad_(True)
        opt = torch.optim.Adam([W], lr=2e-2)
        rng = np.random.default_rng(seed)
        tr = [d for d in data if d["train"]]
        for ep in range(epochs):
            order = rng.permutation(len(tr))
            for i in order:
                d = tr[i]
                w = d["w"] if not shuffle else TEMPLATE_IDS[int(rng.integers(5))]
                R, _ = torch.linalg.qr(W)
                with torch.enable_grad():
                    lg = step_logits(d["cache"], d["ids"], make_hook(R, src[w]["h"]))
                    lp = torch.log_softmax(lg.float(), -1)
                    ps = src[d["w"]]["logp"].exp()
                    loss = (ps * (src[d["w"]]["logp"] - lp)).sum()
                opt.zero_grad()
                loss.backward()
                opt.step()
        R, _ = torch.linalg.qr(W.detach())
        return R

    res: dict[str, Any] = {"layer": l, "site": "FORK", "map_class": "one layer, one position, linear rank-k subspace",
                           "source": "forced-BFS prompt F_i of the same template (+ c*), last position", "per_k": {}}
    best = None
    for k in (1, 2, 4):
        R = train(k, seed=k)
        ev = evaluate(R)
        rnd = [evaluate(torch.linalg.qr(torch.randn(2560, k, generator=torch.Generator().manual_seed(100 + s)).cuda())[0])
               for s in range(3)]
        Rs = train(k, shuffle=True, seed=50 + k)
        ev_s = evaluate(Rs, shuffle=True, seed=7)
        res["per_k"][str(k)] = {"das": ev, "random_subspace": {
            "heldout_mean_dy": float(np.mean([r["heldout_mean_dy"] for r in rnd]))}, "shuffled_source": ev_s}
        torch.save(R.cpu(), STATES_DIR / f"das_R_k{k}.pt")
        if best is None or ev["heldout_mean_dy"] > res["per_k"][str(best)]["das"]["heldout_mean_dy"]:
            best = k
        logger.info(f"DAS k={k}: {res['per_k'][str(k)]}")
    res["best_k"] = best
    write_json(RESULTS_DIR / "das.json", res)
    for d in data:
        d["cache"] = None
    torch.cuda.empty_cache()
    # ---------------- generation for the best k (toward BFS), N=50 on the canonical twin, CRN slots 0-9
    Rb = torch.load(STATES_DIR / f"das_R_k{best}.pt")
    cells_path = DATA_DIR / "raw_cells.jsonl"
    done = {r["row_id"] for r in read_jsonl(cells_path)}
    for w in TEMPLATE_IDS:
        p = PG.p_twin("T1", w)
        ids = p["ids"] + cstar
        sp = DASSpec(l, [len(ids) - 1], Rb, src[w]["h"])
        rows = [{"row_id": f"cell|T1|{w}|FORK|DAS|k{best}|{k}", "task": "T1", "arm": f"FORK|DAS|k{best}",
                 "template": w, "slot": k, "ukey": slot_key("T1", w, k), "specs": [sp],
                 "meta": {"cell": f"FORK|DAS|k{best}", "site": "FORK", "layer": l, "kind": "DAS", "src": "das",
                          "k_features": best, "toward": "bfs", "lambda": 1.0}} for k in range(10)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_crn(p, rows, 1536, "das", cells_path, f"DAS:{w}", prefix_ids=cstar)
    run.free()


# ================================================================================================ S10 fallback
class NodeSpec:
    """Set chosen SAE latents at one position to given values (ablate: 0; steer: a target), error preserved;
    optionally rescale the edit to a fixed norm (random-node control at matched contribution norm)."""

    def __init__(self, layer: int, pos: list[int], sae: Any, lat: list[int], target: Any, norm: float | None = None):
        import torch

        self.kind, self.layer = "NODE", layer
        self.pos = torch.tensor(pos, device="cuda", dtype=torch.long)
        self.sae, self.lat = sae, torch.tensor(lat, device="cuda", dtype=torch.long)
        self.target = torch.as_tensor(target, dtype=torch.float32, device="cuda")
        self.norm = norm
        self.log: dict[str, float] = {}

    def dh(self, hs: Any) -> Any:
        pre = hs @ self.sae.W_enc[:, self.lat] + self.sae.b_enc[self.lat]
        f = pre * (pre > self.sae.threshold[self.lat])
        d = (self.target[None] - f) @ self.sae.W_dec[self.lat]
        if self.norm is not None:
            d = d / d.norm(dim=-1, keepdim=True).clamp(min=1e-9) * self.norm
        self.log = {"ox_norm_mean": float(d.norm(dim=-1).mean()), "norm_mean": float(d.norm(dim=-1).mean())}
        return d


def stage_attrib(args: argparse.Namespace) -> None:
    """S10 FALLBACK (first-order attribution, not an attribution graph): the top-5 FORK-site nodes (layer, latent)
    by |first-order attribution| to y over W1-W3 variants, validated in the REAL model on the 10 highest-y and 10
    lowest-y variants: per node ablation (f_i <- 0) and steering (f_i <- the other side's forced-prompt mean), each
    against 5 random active latents at matched contribution norm; then joint top-5 ablation and joint steering
    toward BFS, generation N=30 each on the canonical twin (CRN slots 0-5)."""
    import numpy as np
    import torch

    import prompts as PG
    from cfg import STATES_DIR
    from gen import Runner
    from sae import load_saes

    fk = fork_ctx()
    cstar = fk["cstar_ids"]
    S = torch.load(STATES_DIR / "selection.pt")
    sets, targets = S["sets"], S["targets"]
    run = Runner()
    saes = load_saes("cuda", tuple(SAE_LAYERS))
    nodes = []
    for l in SAE_LAYERS:
        o = sets["output"][f"FORK|{l}|20"]
        nodes += [{"layer": l, "latent": int(i), "score": float(s)} for i, s in zip(o["idx"], o["s"])]
    nodes = sorted(nodes, key=lambda n: -abs(n["score"]))[:5]
    V = torch.load(STATES_DIR / "variants.pt")
    Vs = sorted(V, key=lambda v: v["y"])
    probe = Vs[-10:] + Vs[:10]
    rng = np.random.default_rng(stable_seed("attrib-random") % 2 ** 32)
    out_nodes = []
    for n in nodes:
        l, i = n["layer"], n["latent"]
        rec = {**n, "ablate_dy": [], "steer_dy": [], "rand_ablate_dy": [], "rand_steer_dy": [], "active_frac": 0.0}
        for v in probe:
            ids = v["ids"] + cstar
            pos = [len(ids) - 1]
            a_v = float(v["codes_fork"][l][i])
            rec["active_frac"] += (a_v > 0) / len(probe)
            hi_side = v["y"] >= np.median([u["y"] for u in V])
            tgt = float(targets[f"FORK|{l}|{'dfs' if hi_side else 'bfs'}"][i])
            specs = [NodeSpec(l, pos, saes[l], [i], [0.0]), NodeSpec(l, pos, saes[l], [i], [tgt])]
            act = torch.nonzero(v["codes_fork"][l].float() > 0).flatten().tolist()
            act = [j for j in act if j != i]
            rnd = rng.choice(act, size=min(5, len(act)), replace=False).tolist() if act else []
            contrib = abs(a_v) * float(saes[l].W_dec[i].norm())
            steer_contrib = abs(tgt - a_v) * float(saes[l].W_dec[i].norm())
            for j in rnd:
                tj = float(targets[f"FORK|{l}|{'dfs' if hi_side else 'bfs'}"][j])
                specs.append(NodeSpec(l, pos, saes[l], [j], [0.0], norm=max(contrib, 1e-6)))
                specs.append(NodeSpec(l, pos, saes[l], [j], [tj], norm=max(steer_contrib, 1e-6)))
            ys = y_rows(run, ids, [[sp] for sp in specs], fk)
            dys = [y - v["y"] for y in ys]
            sgn = -1.0 if hi_side else 1.0           # steering moves high-y prompts down, low-y prompts up
            rec["ablate_dy"].append(dys[0])
            rec["steer_dy"].append(sgn * dys[1])
            rec["rand_ablate_dy"] += [abs(x) for x in dys[2::2]]
            rec["rand_steer_dy"] += [sgn * x for x in dys[3::2]]
        for k in ("ablate_dy", "steer_dy", "rand_ablate_dy", "rand_steer_dy"):
            rec[k + "_mean"] = float(np.mean(rec[k])) if rec[k] else None
        rec["abs_ablate_dy_mean"] = float(np.mean(np.abs(rec["ablate_dy"])))
        out_nodes.append(rec)
        logger.info(f"node L{l}:{i} score {n['score']:.3g}: |ablate| {rec['abs_ablate_dy_mean']:.3f} vs random "
                    f"{rec['rand_ablate_dy_mean']}, steer {rec['steer_dy_mean']:.3f} vs random {rec['rand_steer_dy_mean']}")
    res = {"status": "S10 attribution graph not run (dropped first by the drop order on the slower GPU); FALLBACK: "
                     "first-order attribution, not an attribution graph",
           "nodes": [{k: v for k, v in r.items() if not isinstance(v, list)} for r in out_nodes],
           "per_prompt": out_nodes, "probe": "10 highest-y + 10 lowest-y neutral variants, FORK site"}
    # ---------------- joint top-5 ablation and joint steering toward BFS: generation N=30
    cells_path = DATA_DIR / "raw_cells.jsonl"
    done = {r["row_id"] for r in read_jsonl(cells_path)}
    for w in TEMPLATE_IDS:
        p = PG.p_twin("T1", w)
        ids = p["ids"] + cstar
        pos = [len(ids) - 1]
        rows = []
        for cell, mode in (("FORK|NODES5|ablate", "ablate"), ("FORK|NODES5|steerBFS", "steer")):
            specs = []
            for n in nodes:
                l, i = n["layer"], n["latent"]
                t = 0.0 if mode == "ablate" else float(targets[f"FORK|{l}|bfs"][i])
                specs.append(NodeSpec(l, pos, saes[l], [i], [t]))
            for k in range(6):
                rows.append({"row_id": f"cell|T1|{w}|{cell}|{k}", "task": "T1", "arm": cell, "template": w, "slot": k,
                             "ukey": slot_key("T1", w, k), "specs": specs,
                             "meta": {"cell": cell, "site": "FORK", "layer": None, "kind": "NODES5", "src": "output",
                                      "k_features": 5, "toward": "bfs", "lambda": 1.0}})
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            run.run_crn(p, rows, 1536, "attrib", cells_path, f"ATTR:{w}", prefix_ids=cstar)
    write_json(RESULTS_DIR / "attribution.json", res)
    run.free()


# ================================================================================================ analysis (CPU)
def sampling_validation_summary() -> dict[str, Any]:
    import numpy as np
    from scipy import stats

    rows = read_jsonl(DATA_DIR / "sampling_validation_labels.jsonl")
    by: dict[tuple, list] = {}
    for r in rows:
        by.setdefault((r["template"], r["noun"]), []).append(r)
    ys, ls, ps, ns = [], [], [], []
    for (w, n), rr in by.items():
        k = sum(r["cls"] == "bfs" for r in rr)
        m = len(rr)
        ys.append(rr[0]["y"])
        ls.append(np.log((k + 0.5) / (m - k + 0.5)))
        ps.append(k / m)
        ns.append(m)
    ys, ls, ps = np.array(ys), np.array(ls), np.array(ps)
    rho = float(stats.spearmanr(ys, ls).correlation) if len(ys) > 2 else None
    rng = np.random.default_rng(3)
    pt = np.clip((ps * 10 + 0.5) / 11, 0.02, 0.98)
    ceil = []
    for _ in range(1000):
        a = rng.binomial(10, pt) / 10
        b = rng.binomial(10, pt) / 10
        ceil.append(stats.spearmanr(a, b).correlation)
    res = {"n_variants": len(ys), "n_per_variant": int(np.median(ns)) if ns else 0, "spearman_y_vs_logit_share": rho,
           "binomial_noise_ceiling_split_replicate_spearman": float(np.nanmedian(ceil)),
           "mean_bfs_share": float(ps.mean()) if len(ps) else None,
           "pearson_y_vs_logit_share": float(np.corrcoef(ys, ls)[0, 1]) if len(ys) > 2 else None,
           "positive": bool(rho is not None and rho > 0)}
    write_json(RESULTS_DIR / "sampling_validation.json", res)
    return res


def stage_analysis(args: argparse.Namespace) -> None:
    """All CPU analyses, figures and the S13 audits; each part is isolated (an error is logged and recorded)."""
    import traceback

    import analysis_S as A
    import figures_S as FG
    import novelty as NV
    from sae import load_saes

    errs: dict[str, str] = {}

    def part(name: str, fn, *a, **k):
        t0 = time.time()
        try:
            out = fn(*a, **k)
            logger.info(f"analysis part {name} ok in {time.time() - t0:.0f}s")
            return out
        except Exception as e:  # noqa: BLE001 - one failing analysis must not block the others; recorded below
            logger.exception(f"analysis part {name} failed: {e}")
            errs[name] = traceback.format_exc()[-3000:]
            return None

    only = set(args.parts.split(",")) if args.parts else None
    want = lambda n: only is None or n in only  # noqa: E731
    fk = read_json(RESULTS_DIR / "fork.json") if (RESULTS_DIR / "fork.json").exists() else None
    gate = read_json(RESULTS_DIR / "gate.json") if (RESULTS_DIR / "gate.json").exists() else None
    gated = [l for l in SAE_LAYERS if gate and gate["sites"][str(l)]["pass"]] or list(SAE_LAYERS)
    saes = load_saes("cpu", tuple(SAE_LAYERS)) if (want("s6a") or want("s6b") or want("s6c") or want("geo")) else None
    if want("s3"):
        part("natural_split", A.natural_split, load_labelled)
        part("engine_check", A.engine_check, load_labelled, str(ROOT / "inputs" / "exp28" / "data" / "samples.jsonl"))
        part("top5", A.top5_landing, load_labelled)
    if want("s6a") and fk:
        out = {}
        for read in ("r_id", "r_fork"):
            out[f"T1|{read}"] = part(f"s6a_T1_{read}", A.within_prompt, "T1", fk, saes, list(SAE_LAYERS), read,
                                     args.n_perm_s6a)
        for task in ("T04", "R6"):
            out[f"{task}|g32"] = part(f"s6a_{task}", A.within_prompt, task, None, saes, list(SAE_LAYERS), "g32", 100)
        write_json(RESULTS_DIR / "decodability_within.json", out)
    if want("s6b"):
        part("sampling_validation", sampling_validation_summary)
        part("s6b_readout", A.cross_prompt_readout, saes, gated, read_json(RESULTS_DIR / "nouns.json"))
    if want("s6c"):
        part("s6c_contrast", A.contrast_separability, saes, list(SAE_LAYERS))
    if want("s8") and (PRED_DIR / "commit1.json").exists():
        part("sweep_summary", A.sweep_summary)
        cl = part("clamp_tests", A.clamp_tests, load_labelled, read_json(PRED_DIR / "commit1.json"))
        tp = read_json(RESULTS_DIR / "top5.json") if (RESULTS_DIR / "top5.json").exists() else None
        if cl and tp:
            part("fig_clamps", FG.clamp_figure, cl, tp)
        part("fig_dose", FG.dose_figure)
    if want("geo") and fk:
        ns = read_json(RESULTS_DIR / "natural_split.json")
        impl = {k: v for k, v in ns["T1"]["all"]["attempted"].items() if k not in ("invalid", "disputed")}
        sel = read_json(RESULTS_DIR / "selection.json") if (RESULTS_DIR / "selection.json").exists() else None
        ls = sorted({int(sel["layer_rule"]["SPEC"]["layer"])} | {17, 22}) if sel else [17, 22]
        part("geometry", FG.geometry, saes, ls, impl)
        part("generated_panel", FG.generated_panel, fk)
        part("fork_figure", FG.fork_figure, fk)
    if want("s13"):
        rows = []
        for f in ("raw_s3.jsonl", "raw_contrast.jsonl", "raw_cells.jsonl"):
            if (DATA_DIR / f).exists():
                rows += load_labelled(f)
        part("novelty", NV.audit, rows)
        part("regate", NV.regate, [r for r in rows if r["task"] == "T1" and r.get("arm") == "twin"])
    prev = read_json(RESULTS_DIR / "analysis_errors.json") if (RESULTS_DIR / "analysis_errors.json").exists() else {}
    prev.update(errs)
    for k in list(prev):
        if k not in errs and only is not None:
            continue
    write_json(RESULTS_DIR / "analysis_errors.json", errs if only is None else prev)


# ================================================================================================ outputs
def stage_outputs(args: argparse.Namespace) -> None:
    """method_out.json (exp_gen_sol_out) + full/mini/preview variants; costs and timing summaries."""
    import subprocess

    import novelty as NV
    import outputs as OUT
    import prompts as PG

    tb = read_jsonl(LOG_DIR / "timing_batches.jsonl")
    by_stage: dict[str, float] = {}
    for r in tb:
        by_stage[r["stage"]] = by_stage.get(r["stage"], 0.0) + r["seconds"]
    write_json(RESULTS_DIR / "timing.json", {"generation_seconds_by_stage": by_stage, "n_batches": len(tb)})
    spend = {"openrouter_total_usd_this_artifact": NV.spent_total(), "cap_usd": 1.00}
    write_json(RESULTS_DIR / "costs.json", spend)
    OUT.build(load_labelled, PG)
    skill = Path(os.environ.get("AII_JSON_SKILL_DIR", "aii-json-skill-not-set"))   # optional schema validator
    py = skill.parent / ".ability_client_venv" / "bin" / "python"
    for cmd in ([str(py), str(skill / "scripts" / "aii_json_validate_schema.py"), "--format", "exp_gen_sol_out",
                 "--file", str(ROOT / "method_out.json")],
                [str(py), str(skill / "scripts" / "aii_json_format_mini_preview.py"), "--input",
                 str(ROOT / "method_out.json")]):
        if py.exists():
            r = subprocess.run(cmd, capture_output=True, text=True)
            logger.info((r.stdout + r.stderr)[-1500:])


# ================================================================================================ main
STAGES = {"s0": lambda a: stage_s0(), "gen1": stage_gen1, "label": stage_label, "fork": stage_fork,
          "tfgate": stage_tfgate, "variants": stage_variants, "select": stage_select, "clamps": stage_clamps,
          "analysis": stage_analysis, "das": stage_das, "outputs": stage_outputs, "attrib": stage_attrib}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--tasks", default=None)
    ap.add_argument("--n-slots", type=int, default=None)
    ap.add_argument("--skip-contrast", action="store_true")
    ap.add_argument("--follow", action="store_true")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--ram-gb", type=float, default=22.0)
    ap.add_argument("--fork-b", type=int, default=48)
    ap.add_argument("--refine-paths", type=int, default=8)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--sv-n", type=int, default=10)
    ap.add_argument("--sweep-n", type=int, default=0)
    ap.add_argument("--sweep-b", type=int, default=32)
    ap.add_argument("--cell-slots", type=int, default=10)
    ap.add_argument("--parts", default=None)
    ap.add_argument("--n-perm-s6a", type=int, default=200)
    args = ap.parse_args()
    setup_logging(f"method_{args.stage}")
    if args.stage in CPU_STAGES:
        set_ram_limit(args.ram_gb)   # RLIMIT_AS (CPU stages only: CUDA reserves huge virtual ranges)
    else:
        logger.info("GPU stage: RAM bounded by the cgroup (28 GB); VRAM by set_per_process_memory_fraction")
    t0 = time.time()
    logger.info(f"stage {args.stage} start; pid {os.getpid()}")
    STAGES[args.stage](args)
    logger.info(f"stage {args.stage} done in {time.time() - t0:.0f}s")
    gc.collect()


if __name__ == "__main__":
    logger.catch(reraise=True)(main)()
