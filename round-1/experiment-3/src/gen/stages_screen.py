"""Phase gen2 (one vLLM process): S7 screen, S8 change points, S9 localise + confirm, S10 prompt swap, S11 knob."""

from __future__ import annotations

import collections
import json
import math
import time

import numpy as np
from loguru import logger

from analysis.cpd import binseg, perm_chi2
from common import GEN_DIR, LOG_DIR, ROOT, SUM_DIR, append_jsonl, log_hash, read_jsonl, stable_seed, tvd
from gen.engine import generate, sample_scheduled, sp
from gen.stages_pool import POOL_FILE, base_row, flush
from labeller.evidence import commitment
from tasks import t1_grid, t2_wsp

CATS = {"T1": t1_grid.CATALOGUE + ["other", "no_code"], "T2": t2_wsp.CATALOGUE + ["other", "no_code"]}
BANNED = {"T1": t1_grid.BANNED_MODE, "T2": t2_wsp.BANNED_MODE}
GRID_FULL = list(range(4, 93, 4))
GRID_BASELINE = [4, 8, 16, 32, 64]  # fallback 5: baseline collapsed at R in S6 (400/400 per task)
S_SCREEN, S_LOCAL, S_CONFIRM, S_CONTROL, S_SWAP_BAN, S_SWAP_BASE = 8, 8, 30, 30, 20, 10
SCREEN_FILE = GEN_DIR / "screen.jsonl"
LOCAL_FILE = GEN_DIR / "localise.jsonl"
CONFIRM_FILE = GEN_DIR / "confirm.jsonl"
SWAP_FILE = GEN_DIR / "swap.jsonl"
KNOB_FILE = GEN_DIR / "knob.jsonl"
DEVIATIONS = []


def counts_of(task: str, labels: list[str]) -> np.ndarray:
    c = np.zeros(len(CATS[task]))
    for lab in labels:
        c[CATS[task].index(lab if lab in CATS[task] else "other")] += 1
    return c


def _throughput(stage: str, n: int, ntok: int, dt: float) -> None:
    with open(LOG_DIR / "throughput.log", "a") as fh:
        fh.write(json.dumps({"stage": stage, "n": n, "tokens": ntok, "gen_s": dt, "tok_s": ntok / max(dt, 1e-6),
                             "s_per_sample": dt / max(1, n)}) + "\n")


def continuations(llm, tok, pool, reqs: list[dict], out_file, arm: str, stage: str, max_tokens: int = 768) -> list:
    """reqs: {task, condition, pid, bp_id, prompt_ids, base_ids, p, n, seed, extra} -> labelled rows appended."""
    if not reqs:
        return []
    t0 = time.time()
    outs = generate(llm, [r["prompt_ids"] + r["base_ids"][: r["p"]] for r in reqs],
                    [sp(1.0, max_tokens if r["p"] > 0 else 1024, r["seed"], n=r["n"]) for r in reqs])
    dt = time.time() - t0
    pending = []
    ntok = 0
    for r, o in zip(reqs, outs):
        pre = r["base_ids"][: r["p"]]
        for c in o.outputs:
            ids = list(c.token_ids)
            ntok += len(ids)
            text = tok.decode(pre + ids, skip_special_tokens=True)
            row = base_row(task=r["task"], condition=r["condition"], paraphrase_id=r["pid"], sample_id=c.index,
                           arm=arm, stage=stage, base_path_id=r["bp_id"], prefix_len=r["p"],
                           seed=r["seed"] + c.index, decoding="T=1.0,top_p=1.0,top_k=-1 (continuation)",
                           n_gen_tokens=len(ids), finish_reason=c.finish_reason, **r.get("extra", {}))
            pending.append((row, pool.submit(r["task"], text)))
    rows = flush(pending, out_file)
    _throughput(f"{arm}_{stage}", len(rows), ntok, dt)
    return rows


def next_token_dists(llm, tok, items: list[dict]) -> list[dict]:
    """Top-20 next-token distribution (T=1.0) at prefix length p: one 1-token request with logprobs=20."""
    if not items:
        return []
    outs = generate(llm, [it["prompt_ids"] + it["base_ids"][: it["p"]] for it in items],
                    [sp(1.0, 1, stable_seed("nt", it["bp_id"], it["p"]), logprobs=20) for it in items])
    res = []
    for it, o in zip(items, outs):
        lp = o.outputs[0].logprobs[0] if o.outputs[0].logprobs else {}
        toks = sorted(((tid, v.logprob) for tid, v in lp.items()), key=lambda x: -x[1])[:20]
        pr = np.exp(np.array([x[1] for x in toks])) if toks else np.array([1.0])
        mass = float(pr.sum())
        q = pr / pr.sum()
        ent = float(-(q * np.log2(q)).sum())
        res.append({"bp_id": it["bp_id"], "p": it["p"], "kind": it["kind"], "entropy_bits_top20": ent,
                    "top20_mass": mass,
                    "actual_token": tok.decode([it["base_ids"][it["p"]]]) if it["p"] < len(it["base_ids"]) else None,
                    "top": [(tok.decode([tid]), float(lpv)) for tid, lpv in toks[:10]]})
    return res


def run_gen2(llm, tok, prompts: dict, pool) -> None:
    t_start = time.time()
    pools = read_jsonl(POOL_FILE)
    base_paths = []
    for r in pools:
        if r["sample_id"] == 0 and ((r["arm"] == "G1" and r["condition"] == "baseline") or r["arm"] == "G2"):
            bp_id = f"{r['task']}|{r['condition']}|{r['paraphrase_id']}"
            others = [x["label"] for x in pools if x["arm"] == r["arm"] and x["task"] == r["task"]
                      and x["paraphrase_id"] == r["paraphrase_id"] and x["sample_id"] != 0]
            base_paths.append({"bp_id": bp_id, "task": r["task"], "condition": r["condition"],
                               "pid": r["paraphrase_id"], "base_ids": r["gen_token_ids"], "final_label": r["label"],
                               "commit_idx": r["commit_idx"], "evidence_term": r["evidence_term"],
                               "o0_labels": others, "L": len(r["gen_token_ids"])})
    base_paths.sort(key=lambda b: (b["condition"] != "ban", b["task"], b["pid"]))
    logger.info(f"{len(base_paths)} base paths")
    DEVIATIONS.append("baseline base paths screened on grid {4,8,16,32,64} only (fallback 5: baseline collapsed at R)")
    bp_by = {b["bp_id"]: b for b in base_paths}
    # ------------------------------------------------------------------ S7 screen (staged)
    done = {(r["base_path_id"], r["prefix_len"]) for r in read_jsonl(SCREEN_FILE)}

    def screen_reqs(bps):
        reqs = []
        for b in bps:
            grid = GRID_FULL if b["condition"] == "ban" else GRID_BASELINE
            for p in grid:
                if p >= b["L"] - 1 or (b["bp_id"], p) in done:
                    continue
                reqs.append({"task": b["task"], "condition": b["condition"], "pid": b["pid"], "bp_id": b["bp_id"],
                             "prompt_ids": prompts[f"{b['task']}|{b['condition']}|{b['pid']}"]["prompt_token_ids"],
                             "base_ids": b["base_ids"], "p": p, "n": S_SCREEN,
                             "seed": stable_seed(b["task"], b["condition"], b["pid"], "screen", p)})
        return reqs

    stage1 = [b for b in base_paths if b["pid"] == 0]
    t0 = time.time()
    continuations(llm, tok, pool, screen_reqs(stage1), SCREEN_FILE, "A1_screen", "stage1")
    logger.info(f"S7 stage1 ({len(stage1)} paths) took {time.time() - t0:.0f}s")
    continuations(llm, tok, pool, screen_reqs([b for b in base_paths if b["pid"] != 0]), SCREEN_FILE,
                  "A1_screen", "full")
    logger.info(f"S7 done at {time.time() - t_start:.0f}s")
    screen = read_jsonl(SCREEN_FILE)
    # ------------------------------------------------------------------ S8 change points (provisional labels)
    by_pos = collections.defaultdict(list)
    for r in screen:
        by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label"])
    cands = []
    for b in base_paths:
        grid = [p for p in (GRID_FULL if b["condition"] == "ban" else GRID_BASELINE) if (b["bp_id"], p) in by_pos]
        positions = [0] + grid
        C = np.stack([counts_of(b["task"], b["o0_labels"])] + [counts_of(b["task"], by_pos[(b["bp_id"], p)])
                                                               for p in grid])
        cps = binseg(C, n_perm=1000, seed=stable_seed(b["bp_id"], "cpd") % 2 ** 32)
        b["positions"] = positions
        b["cps"] = [{"bracket": [positions[c["index"] - 1], positions[c["index"]]], **c} for c in cps]
        for c in b["cps"]:
            cands.append({"bp_id": b["bp_id"], "bracket": c["bracket"]})
    logger.info(f"S8: {len(cands)} candidate change points on {len({c['bp_id'] for c in cands})} paths")
    # ------------------------------------------------------------------ S9 localise
    local_done = {(r["base_path_id"], r["prefix_len"]) for r in read_jsonl(LOCAL_FILE)}
    reqs = []
    for c in cands:
        b = bp_by[c["bp_id"]]
        lo, hi = c["bracket"]
        for p in range(lo + 1, hi):
            if (b["bp_id"], p) in local_done or p >= b["L"] - 1:
                continue
            local_done.add((b["bp_id"], p))
            reqs.append({"task": b["task"], "condition": b["condition"], "pid": b["pid"], "bp_id": b["bp_id"],
                         "prompt_ids": prompts[f"{b['task']}|{b['condition']}|{b['pid']}"]["prompt_token_ids"],
                         "base_ids": b["base_ids"], "p": p, "n": S_LOCAL,
                         "seed": stable_seed(b["task"], b["condition"], b["pid"], "local", p)})
    continuations(llm, tok, pool, reqs, LOCAL_FILE, "A2_localise", "full")
    for r in read_jsonl(LOCAL_FILE):
        by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label"])

    def o_at(bp_id: str, p: int) -> np.ndarray:
        b = bp_by[bp_id]
        labs = list(b["o0_labels"]) if p == 0 else []
        labs += by_pos.get((bp_id, p), [])
        return counts_of(b["task"], labs)

    for c in cands:
        lo, hi = c["bracket"]
        best, bt = -1.0, lo
        for s in range(lo, hi):
            v = tvd(o_at(c["bp_id"], s), o_at(c["bp_id"], s + 1))
            if v == v and v > best:
                best, bt = v, s
        c["t"] = bt
        c["tvd_local"] = best
    # ------------------------------------------------------------------ S9 confirm + controls
    conf_rows = read_jsonl(CONFIRM_FILE)
    for r in conf_rows:
        by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label"])
    reqs, nt_items = [], []
    rng = np.random.default_rng(12345)
    controls = []
    for b in base_paths:
        my = [c for c in cands if c["bp_id"] == b["bp_id"]]
        if not my:
            continue
        P = prompts[f"{b['task']}|{b['condition']}|{b['pid']}"]["prompt_token_ids"]
        for c in my:
            for p in (c["t"], c["t"] + 1):
                have = int(o_at(b["bp_id"], p).sum())
                need = S_CONFIRM - have
                if need > 0 and p < b["L"] - 1:
                    reqs.append({"task": b["task"], "condition": b["condition"], "pid": b["pid"], "bp_id": b["bp_id"],
                                 "prompt_ids": P, "base_ids": b["base_ids"], "p": p, "n": need,
                                 "seed": stable_seed(b["task"], b["condition"], b["pid"], "confirm", p)})
            nt_items.append({"bp_id": b["bp_id"], "p": c["t"], "kind": "fork_candidate", "prompt_ids": P,
                             "base_ids": b["base_ids"]})
        ts = [c["t"] for c in my]
        ok_q = [q for q in range(4, 89) if all(abs(q - t) >= 8 for t in ts) and q + 1 < b["L"] - 1]
        if ok_q:
            q = int(rng.choice(ok_q))
            controls.append({"bp_id": b["bp_id"], "q": q})
            for p in (q, q + 1):
                have = int(o_at(b["bp_id"], p).sum())
                need = S_CONTROL - have
                if need > 0:
                    reqs.append({"task": b["task"], "condition": b["condition"], "pid": b["pid"], "bp_id": b["bp_id"],
                                 "prompt_ids": P, "base_ids": b["base_ids"], "p": p, "n": need,
                                 "seed": stable_seed(b["task"], b["condition"], b["pid"], "control", p),
                                 "extra": {"is_control": True}})
            nt_items.append({"bp_id": b["bp_id"], "p": q, "kind": "control", "prompt_ids": P,
                             "base_ids": b["base_ids"]})
    if not conf_rows:
        continuations(llm, tok, pool, reqs, CONFIRM_FILE, "A2_confirm", "full")
        for r in read_jsonl(CONFIRM_FILE):
            by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label"])
    # vLLM logprobs trigger a torch-inductor compile (no C compiler on this host): the next-token distributions at
    # fork candidates and controls are computed in the HF phase (analysis/states.py) from the same token prefixes.
    (SUM_DIR / "next_token_items.json").write_text(json.dumps(
        [{"bp_id": it["bp_id"], "p": it["p"], "kind": it["kind"]} for it in nt_items], indent=1))
    # provisional confirmation (runtime labels) -- final confirmation is recomputed in analysis after adjudication
    forks = []
    for c in cands:
        b = bp_by[c["bp_id"]]
        a, bb = o_at(c["bp_id"], c["t"]), o_at(c["bp_id"], c["t"] + 1)
        v = tvd(a, bb)
        pv = perm_chi2(a, bb, n_perm=2000, seed=stable_seed(c["bp_id"], c["t"]) % 2 ** 32)
        lo, hi = c["bracket"]
        coarse = tvd(o_at(c["bp_id"], lo), o_at(c["bp_id"], hi))
        sharp = v / coarse if coarse and coarse > 0 else float("nan")
        c.update({"tvd": v, "p_perm": pv, "coarse_tvd": coarse, "sharpness": sharp,
                  "confirmed": bool(pv < 0.05 and v >= 0.20 and sharp == sharp and sharp >= 0.5)})
        if c["confirmed"]:
            forks.append(c)
    for ctl in controls:
        a, bb = o_at(ctl["bp_id"], ctl["q"]), o_at(ctl["bp_id"], ctl["q"] + 1)
        ctl["tvd"] = tvd(a, bb)
        ctl["p_perm"] = perm_chi2(a, bb, n_perm=2000, seed=stable_seed(ctl["bp_id"], ctl["q"]) % 2 ** 32)
    prov = {"candidates": cands, "controls": controls,
            "paths": [{k: v for k, v in b.items() if k not in ("base_ids",)} for b in base_paths]}
    (SUM_DIR / "gen2_provisional.json").write_text(json.dumps(prov, indent=1, default=str))
    logger.info(f"S9: {len(forks)} provisional confirmed forks; done at {time.time() - t_start:.0f}s")
    # ------------------------------------------------------------------ S10 prompt swap
    first_fork = {}
    for c in sorted(forks, key=lambda c: c["t"]):
        first_fork.setdefault(c["bp_id"], c["t"])
    pred_path = ROOT / "predictions.json"
    preds = json.loads(pred_path.read_text()) if pred_path.exists() else {}
    swap_plan = []
    for b in base_paths:
        if b["condition"] != "baseline":
            continue
        cstar = first_fork.get(b["bp_id"], b["commit_idx"])
        src = "first_confirmed_fork" if b["bp_id"] in first_fork else "commit_idx"
        if cstar is None or cstar + 1 >= b["L"]:
            continue
        swap_plan.append({"bp_id": b["bp_id"], "cut": int(cstar), "cut_source": src})
    if "S10" not in preds:
        preds["S10"] = {"predicted_pattern": "ban effect at pre > ban effect at post (banned-mode share drops more "
                                             "when the ban prompt sees the prefix cut BEFORE the committing token)",
                        "swap_plan": swap_plan, "S_ban": S_SWAP_BAN, "S_baseline": S_SWAP_BASE,
                        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        pred_path.write_text(json.dumps(preds, indent=1))
        log_hash("predictions_S10", pred_path)
    if not read_jsonl(SWAP_FILE):
        reqs = []
        for s in swap_plan:
            b = bp_by[s["bp_id"]]
            for side, p in (("pre", s["cut"]), ("post", s["cut"] + 1)):
                for cond, n in (("ban", S_SWAP_BAN), ("baseline", S_SWAP_BASE)):
                    reqs.append({"task": b["task"], "condition": cond, "pid": b["pid"], "bp_id": b["bp_id"],
                                 "prompt_ids": prompts[f"{b['task']}|{cond}|{b['pid']}"]["prompt_token_ids"],
                                 "base_ids": b["base_ids"], "p": p, "n": n,
                                 "seed": stable_seed(b["task"], cond, b["pid"], "swap", p),
                                 "extra": {"swap_side": side, "swap_prompt": cond, "cut": s["cut"],
                                           "cut_source": s["cut_source"]}})
        continuations(llm, tok, pool, reqs, SWAP_FILE, "A3_swap", "full")
    logger.info(f"S10 done at {time.time() - t_start:.0f}s")
    # ------------------------------------------------------------------ S11 knob
    hot = {}
    for task in ("T1", "T2"):
        chain = []
        base_f = [first_fork[b["bp_id"]] for b in base_paths if b["task"] == task and b["condition"] == "baseline"
                  and b["bp_id"] in first_fork]
        ban_f = [first_fork[b["bp_id"]] for b in base_paths if b["task"] == task and b["condition"] == "ban"
                 and b["bp_id"] in first_fork]
        commits = [r["commit_idx"] for r in pools if r["task"] == task and r["arm"] == "G1"
                   and r["commit_idx"] is not None]
        if base_f:
            src, idx = "baseline_forks", [k for k, _ in collections.Counter(base_f).most_common(3)]
        elif ban_f:
            src, idx = "ban_forks", [k for k, _ in collections.Counter(ban_f).most_common(3)]
        else:
            src, idx = "commit_idx_mode", [collections.Counter(commits).most_common(1)[0][0]]
        chain.append(src)
        H = sorted({h for f in idx for h in range(max(0, f - 2), f + 3)})
        hot[task] = {"fork_indices": idx, "H": H, "source": src,
                     "baseline_forks": base_f, "ban_forks": ban_f}
    if "S11" not in preds:
        preds["S11"] = {"hot_sets": hot, "T_hot": 1.3, "T_cold": 0.3, "N_per_arm": 100,
                        "random_window_rule": "same number of 5-token windows as fork indices, centres ~U[2,94], "
                                              ">= 5 tokens from any fork index, non-overlapping",
                        "anchored_rule": "T=0.3 until ```python (inclusive), then 1.3 for 5 tokens, then 0.3",
                        "predicted_signs": ["Hill_cc(FORK) > Hill_cc(RANDOM_WINDOW)",
                                            "FORK within-mode phrasing Hill < global T=1.3",
                                            "FORK pass rate >= global T=1.0"],
                        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        pred_path.write_text(json.dumps(preds, indent=1))
        log_hash("predictions_S11", pred_path)
    if not read_jsonl(KNOB_FILE):
        jobs, metas = [], []
        for task in ("T1", "T2"):
            H = hot[task]["H"]
            fidx = hot[task]["fork_indices"]
            for pid in range(10):
                P = prompts[f"{task}|baseline|{pid}"]["prompt_token_ids"]
                for k in range(10):
                    # FORK
                    segs = _segments_from_hot(H)
                    jobs.append({"prompt_ids": P, "segments": segs, "seed": stable_seed(task, pid, k, "FORK")})
                    metas.append((task, pid, k, "A4_FORK", {"hot_idx": H}))
                    # RANDOM-WINDOW
                    rr = np.random.default_rng(stable_seed(task, pid, k, "RW") % 2 ** 32)
                    centres = []
                    tries = 0
                    while len(centres) < len(fidx) and tries < 1000:
                        tries += 1
                        cc = int(rr.integers(2, 95))
                        if all(abs(cc - f) >= 5 for f in fidx) and all(abs(cc - x) >= 5 for x in centres):
                            centres.append(cc)
                    Hr = sorted({h for cc in centres for h in range(cc - 2, cc + 3)})
                    jobs.append({"prompt_ids": P, "segments": _segments_from_hot(Hr),
                                 "seed": stable_seed(task, pid, k, "RW")})
                    metas.append((task, pid, k, "A4_RANDOM_WINDOW", {"hot_idx": Hr}))
                    # ANCHORED
                    jobs.append({"prompt_ids": P, "segments": [(0.3, None, "```python"), (1.3, 5, None),
                                                               (0.3, None, None)],
                                 "seed": stable_seed(task, pid, k, "ANCH")})
                    metas.append((task, pid, k, "A4_ANCHORED", {}))
        t0 = time.time()
        states = sample_scheduled(llm, jobs, max_total=1024)
        dt = time.time() - t0
        pending = []
        ntok = 0
        for (task, pid, k, arm, extra), st in zip(metas, states):
            ids = st["ids"]
            ntok += len(ids)
            text = tok.decode(ids, skip_special_tokens=True)
            ev = commitment(tok, task, ids, text)
            row = base_row(task=task, condition="baseline", paraphrase_id=pid, sample_id=k, arm=arm, stage="full",
                           seed=stable_seed(task, pid, k, arm), decoding=f"{arm} schedule (T_hot=1.3, T_cold=0.3)",
                           n_gen_tokens=len(ids), finish_reason=st["finish_reason"], gen_token_ids=ids, text=text,
                           temps_hot_idx=[i for i, T in enumerate(st["temps"]) if T > 1.0][:40], **extra, **ev)
            pending.append((row, pool.submit(task, text)))
        flush(pending, KNOB_FILE)
        _throughput("A4_knob", len(states), ntok, dt)
    (SUM_DIR / "gen2_deviations.json").write_text(json.dumps(DEVIATIONS, indent=1))
    logger.info(f"gen2 complete at {time.time() - t_start:.0f}s")


def _segments_from_hot(H: list[int]) -> list[tuple]:
    if not H:
        return [(0.3, None, None)]
    segs = []
    cur = 0
    Hs = sorted(set(H))
    i = 0
    while i < len(Hs):
        j = i
        while j + 1 < len(Hs) and Hs[j + 1] == Hs[j] + 1:
            j += 1
        start, end = Hs[i], Hs[j]
        if start > cur:
            segs.append((0.3, start - cur, None))
        segs.append((1.3, end - start + 1, None))
        cur = end + 1
        i = j + 1
    segs.append((0.3, None, None))
    return segs
