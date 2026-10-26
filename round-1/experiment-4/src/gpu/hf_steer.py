#!/usr/bin/env python3
"""HF steering arms with common random numbers (own process; never load vLLM here).

Hook on model.model.layers[L-1] (its output == hidden_states[L]) adds coef * ||x|| * v_hat at the last
position of every forward call: R at prefill (every row of a batch shares one prompt, so no padding) and
the single new position at each decode step. One batch = one baseline paraphrase (ids 0-9) x 10 samples,
seeded with torch.manual_seed(stable_hash(task, paraphrase_id)) for EVERY arm.

Schedule (one process, priorities, resumable from data/raw/hf_*.jsonl):
  hook tests -> stage 10 (paraphrase 0 of every dc arm + layer mini-sweep at L*+-4, c=1.0) -> layer rule ->
  full dc grid -> wait for test labels -> c*_t + pre-registered bisection point -> rand1/rand2 at c*_t ->
  extensions E1 placebo, E5 breadth, E4 cross-task transfer while the time budget allows.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (DIRECTIONS_DIR, EOS_IDS, GRID_C, LABEL_CACHE, LOGS_DIR, MODEL_ID, PAD_ID, RAW_DIR,  # noqa: E402
                    RESULTS_DIR, TASKS, append_jsonl, cond_name_steer, read_jsonl, resolve_model_path,
                    set_ram_limit, setup_logger, sha256_text, stable_hash)
from prompts.scaffold import build_prompt, check_suffix, segments  # noqa: E402
from labeller.harness import analyse_text  # noqa: E402
from labeller.ast_rules import ast_label  # noqa: E402

N_PARA, N_PER = 10, 10
MAX_NEW = 768
GEN_KW = dict(do_sample=True, temperature=1.0, top_p=1.0, top_k=0, max_new_tokens=MAX_NEW, eos_token_id=EOS_IDS,
              pad_token_id=PAD_ID, repetition_penalty=1.0)


class Steerer:
    """Forward hook that adds coef * ||x|| * v_hat at position -1."""

    def __init__(self, model):
        self.model = model
        self.coef = 0.0
        self.vec = None
        self.handle = None
        self.calls = []
        self.record = False
        self.captured = []

    def attach(self, layer: int, vec: np.ndarray | None, coef: float) -> None:
        self.detach()
        self.coef = float(coef)
        self.vec = None if vec is None else torch.tensor(vec / np.linalg.norm(vec), dtype=torch.float32).cuda()
        self.handle = self.model.model.layers[layer - 1].register_forward_hook(self.hook)

    def detach(self) -> None:
        if self.handle is not None:
            self.handle.remove()
            self.handle = None

    def hook(self, module, inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if self.record:
            self.calls.append(int(h.shape[1]))
        if self.coef == 0 or self.vec is None:
            return out
        h = h.clone()
        x = h[:, -1, :].float()
        x_new = x + self.coef * x.norm(dim=-1, keepdim=True) * self.vec
        if self.record:
            self.captured.append((x.detach().cpu(), x_new.detach().cpu()))
        h[:, -1, :] = x_new.to(h.dtype)
        return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h


def gen_batch(model, tok, ids: list[int], seed: int, n: int = N_PER, max_new: int = MAX_NEW) -> list[dict]:
    inp = torch.tensor([ids] * n, dtype=torch.long).cuda()
    att = torch.ones_like(inp)
    torch.manual_seed(seed)
    kw = dict(GEN_KW)
    kw["max_new_tokens"] = max_new
    with torch.no_grad():
        out = model.generate(input_ids=inp, attention_mask=att, **kw)
    res = []
    for i in range(n):
        new = out[i, len(ids):].tolist()
        stop = None
        for j, t in enumerate(new):
            if t in EOS_IDS:
                stop = j
                break
        toks = new if stop is None else new[:stop]
        res.append({"text": tok.decode(toks, skip_special_tokens=True), "n_tokens": len(toks),
                    "finish_reason": "stop" if stop is not None else "length", "token_ids": toks})
    del out, inp, att
    return res


def raw_path(task: str, cond: str) -> Path:
    return RAW_DIR / f"hf_{task}_{cond.replace(':', '-').replace('=', '')}.jsonl"


class Runner:
    def __init__(self, model, tok, steer: Steerer, deadline: float):
        self.model, self.tok, self.steer, self.deadline = model, tok, steer, deadline
        self.batch_times: list[float] = []

    def est_batch(self) -> float:
        return float(np.median(self.batch_times[-20:])) if self.batch_times else 40.0

    def time_left(self) -> float:
        return self.deadline - time.time()

    def run_arm(self, task: str, direction: str, vec: np.ndarray | None, coef: float, layer: int,
                pids: list[int], cond: str | None = None) -> str:
        cond = cond or cond_name_steer(direction, coef, layer)
        path = raw_path(task, cond)
        done = {r["paraphrase_id"] for r in read_jsonl(path)}
        segs = segments(task, "baseline")
        self.steer.attach(layer, vec, coef)
        try:
            for p in pids:
                if p in done:
                    continue
                ids = build_prompt(self.tok, segs[p], task)
                check_suffix(self.tok, ids, task)
                seed = stable_hash(task, p)
                t0 = time.time()
                try:
                    outs = gen_batch(self.model, self.tok, ids, seed)
                except torch.cuda.OutOfMemoryError:
                    logger.error("OOM in generate; emptying cache and retrying once")
                    torch.cuda.empty_cache()
                    outs = gen_batch(self.model, self.tok, ids, seed)
                dt = time.time() - t0
                self.batch_times.append(dt)
                rows = []
                for s, o in enumerate(outs):
                    rows.append({"task": task, "condition": cond, "paraphrase_id": p, "sample_id": s,
                                 "model": MODEL_ID, "engine": "hf", "segment": segs[p], "seed": seed,
                                 "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": 0,
                                              "repetition_penalty": 1.0, "max_new_tokens": MAX_NEW},
                                 "steering": {"direction": direction, "layer": layer, "coef": coef, "seed": seed},
                                 "prompt_n_tokens": len(ids), "text": o["text"], "n_tokens": o["n_tokens"],
                                 "finish_reason": o["finish_reason"]})
                append_jsonl(path, rows)
                append_jsonl(LOGS_DIR / "timing.jsonl", [{
                    "what": f"hf {task} {cond} p{p}", "n_samples": len(rows), "seconds": round(dt, 2),
                    "s_per_sample": round(dt / len(rows), 3), "max_tokens_in_batch": max(o["n_tokens"] for o in outs),
                    "utc": datetime.now(timezone.utc).isoformat()}])
                logger.info(f"{task} {cond} p{p}: {dt:.1f}s, max_tok={max(o['n_tokens'] for o in outs)}")
        finally:
            self.steer.detach()
        return cond


def load_dir(name: str) -> np.ndarray:
    return np.load(DIRECTIONS_DIR / name).astype(np.float32)


def hook_tests(model, tok, steer: Steerer, layer: int, vec: np.ndarray) -> dict:
    res = {}
    ids = build_prompt(tok, segments("T1", "baseline")[0], "T1")
    seed = stable_hash("hooktest", 0)
    # (b) no-op: c=0 with hook attached == no hook, token-identical under the same seed
    steer.detach()
    a = gen_batch(model, tok, ids, seed, n=10, max_new=96)
    steer.attach(layer, vec, 0.0)
    b = gen_batch(model, tok, ids, seed, n=10, max_new=96)
    steer.detach()
    res["noop_token_identical"] = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    # (c) the hook fires once at prefill on the full prompt and once per decode step on one position
    steer.attach(layer, vec, 0.5)
    steer.record, steer.calls, steer.captured = True, [], []
    _ = gen_batch(model, tok, ids, seed, n=2, max_new=8)
    steer.record = False
    steer.detach()
    calls = list(steer.calls)
    res["hook_calls"] = calls
    res["hook_call_pattern_ok"] = bool(calls and calls[0] == len(ids) and all(c == 1 for c in calls[1:])
                                       and len(calls) <= 8)
    # (d) at c=0.5 the residual at R has the expected norm change and a higher cosine with v_hat
    x, xn = steer.captured[0]
    v = torch.tensor(vec / np.linalg.norm(vec), dtype=torch.float32)
    nx, nxn = x.norm(dim=-1), xn.norm(dim=-1)
    cos0 = (x @ v) / nx
    expected = nx * torch.sqrt(1 + 0.25 + 2 * 0.5 * cos0)
    cos1 = (xn @ v) / nxn
    res["norm_before"] = nx.tolist()
    res["norm_after"] = nxn.tolist()
    res["norm_expected"] = expected.tolist()
    res["cos_before"] = cos0.tolist()
    res["cos_after"] = cos1.tolist()
    res["norm_change_ok"] = bool(torch.allclose(nxn, expected, rtol=1e-3))
    res["cos_rises"] = bool((cos1 > cos0).all())
    steer.captured = []
    return res


def provisional(task: str, text: str) -> tuple[str, bool]:
    """(label, format_ok) for the stage-10 layer rule, without running tests."""
    a = analyse_text(task, text)
    if a["code"] is None:
        return "no_code", False
    return ast_label(task, a["code"])["label"], a["format_ok"]


def layer_rule(task_list: list[str], lstar: int, alt_layers: list[int], c0_cond: dict, rows_by_cond) -> dict:
    """Keep L* unless, at c=1.0, L* changes neither label nor format in any of its 20 samples while another
    layer changes >= 5 of 20 (changes counted against the c=0 sample with the same seed)."""
    changes = {}
    for L in [lstar] + alt_layers:
        n_change, n_tot = 0, 0
        for t in task_list:
            base = {(r["paraphrase_id"], r["sample_id"]): provisional(t, r["text"]) for r in rows_by_cond(t, c0_cond[t])}
            for r in rows_by_cond(t, cond_name_steer("dc", 1.0, L)):
                k = (r["paraphrase_id"], r["sample_id"])
                if k not in base:
                    continue
                n_tot += 1
                if provisional(t, r["text"]) != base[k]:
                    n_change += 1
        changes[L] = {"changed": n_change, "n": n_tot}
    switch_to = None
    if changes[lstar]["changed"] == 0:
        best = max(alt_layers, key=lambda L: changes[L]["changed"])
        if changes[best]["changed"] >= 5:
            switch_to = best
    return {"changes": {str(k): v for k, v in changes.items()}, "switch_to": switch_to}


def wait_for_labels(task: str, conds: list[str], timeout_s: float) -> dict[str, list[dict]]:
    """Block until every raw row of these conditions has a label file; return labels per condition."""
    t0 = time.time()
    while True:
        out, missing = {}, 0
        for c in conds:
            labs = []
            for r in read_jsonl(raw_path(task, c)):
                f = LABEL_CACHE / task / f"{sha256_text(r['text'])}.json"
                if f.exists():
                    try:
                        labs.append(json.loads(f.read_text()))
                    except json.JSONDecodeError:
                        missing += 1
                else:
                    missing += 1
            out[c] = labs
        if missing == 0:
            return out
        if time.time() - t0 > timeout_s:
            logger.warning(f"label wait timed out for {task}: {missing} missing; using what exists")
            return out
        time.sleep(10)


def pass_rate(labs: list[dict]) -> float:
    return float(np.mean([bool(x.get("passed")) for x in labs])) if labs else float("nan")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-min", type=float, default=110.0, help="wall-clock budget for this process")
    ap.add_argument("--no-extensions", action="store_true")
    args = ap.parse_args()
    setup_logger("hf_steer")
    # RLIMIT_AS is incompatible with the CUDA driver (it reserves huge virtual ranges); GPU processes rely on
    # the container cgroup limit instead and keep host RAM use to the model load (~16 GB).
    t_start = time.time()
    deadline = t_start + args.budget_min * 60
    sel = json.loads((RESULTS_DIR / "layer_selection.json").read_text())
    lstar = int(sel["L_star"])
    mp = resolve_model_path()
    tok = AutoTokenizer.from_pretrained(mp)
    model = AutoModelForCausalLM.from_pretrained(mp, torch_dtype=torch.bfloat16, attn_implementation="sdpa").cuda().eval()
    logger.info(f"model loaded in {time.time() - t_start:.1f}s; L*={lstar}")
    gc_eff = {k: v for k, v in model.generation_config.to_dict().items() if k in ("temperature", "top_p", "top_k", "do_sample")}
    logger.info(f"model generation_config defaults (overridden per call): {gc_eff}; call kwargs: {GEN_KW}")
    steer = Steerer(model)
    run = Runner(model, tok, steer, deadline)
    state_path = RESULTS_DIR / "steer_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    def save_state():
        state_path.write_text(json.dumps(state, indent=1))

    dvec = {t: {L: load_dir(f"d_dc_{t}_L{L}.npy") for L in sel["layers"]} for t in TASKS}
    if "hook_tests" not in state:
        state["hook_tests"] = hook_tests(model, tok, steer, lstar, dvec["T1"][lstar])
        save_state()
        logger.info(f"hook tests: { {k: v for k, v in state['hook_tests'].items() if not isinstance(v, list)} }")

    def rows_by_cond(t, c):
        return read_jsonl(raw_path(t, c))

    # ---------------- STAGE 10 ----------------
    alt = [L for L in (lstar - 4, lstar + 4) if L in dvec["T1"]]
    for t in TASKS:
        run.run_arm(t, "dc", dvec[t][lstar], 0.0, lstar, [0])
        for c in GRID_C:
            run.run_arm(t, "dc", dvec[t][lstar], c, lstar, [0])
    for L in alt:
        for t in TASKS:
            run.run_arm(t, "dc", dvec[t][L], 1.0, L, [0])
    st10 = [r for r in read_jsonl(LOGS_DIR / "timing.jsonl") if r["what"].startswith("hf ")]
    per_batch = run.est_batch()
    n_batches_core = len(TASKS) * (1 + len(GRID_C)) * (N_PARA - 1) + len(TASKS) * (1 + 2) * N_PARA
    logger.info(f"stage 10 done: median batch {per_batch:.1f}s; core remaining ~{n_batches_core} batches = "
                f"{n_batches_core * per_batch / 60:.1f} min; time left {run.time_left() / 60:.1f} min")
    append_jsonl(LOGS_DIR / "timing.jsonl", [{"what": "hf stage10 extrapolation", "median_batch_s": per_batch,
                                              "core_batches_left": n_batches_core,
                                              "extrapolated_core_min": round(n_batches_core * per_batch / 60, 1),
                                              "n_stage_batches": len(st10)}])
    for t in TASKS:  # inspection: 3 outputs per c
        for c in [0.0] + GRID_C:
            rs = rows_by_cond(t, cond_name_steer("dc", c, lstar))[:3]
            for r in rs:
                logger.debug(f"[inspect {t} c={c}] {r['text'][:600]!r}")
    if "layer_rule" not in state:
        c0 = {t: cond_name_steer("dc", 0.0, lstar) for t in TASKS}
        state["layer_rule"] = layer_rule(TASKS, lstar, alt, c0, rows_by_cond)
        save_state()
    lr = state["layer_rule"]
    L = lstar
    if lr["switch_to"] is not None:
        L = int(lr["switch_to"])
        logger.warning(f"LAYER RULE: switching from L*={lstar} to L={L} (deviation logged)")
    state["L_used"] = L
    save_state()
    logger.info(f"layer rule: {lr}; using L={L}")

    # ---------------- FULL dc GRID ----------------
    allp = list(range(N_PARA))
    for t in TASKS:
        run.run_arm(t, "dc", dvec[t][L], 0.0, L, allp)
        for c in GRID_C:
            run.run_arm(t, "dc", dvec[t][L], c, L, allp)
        logger.info(f"{t} dc grid complete; time left {run.time_left() / 60:.1f} min")

    # ---------------- c* and bisection ----------------
    cstar: dict = state.get("cstar", {})
    for t in TASKS:
        if t in cstar and cstar[t].get("final"):
            continue
        conds = [cond_name_steer("dc", c, L) for c in [0.0] + GRID_C]
        labs = wait_for_labels(t, conds, timeout_s=40 * 60)
        pr = {c: pass_rate(labs[cond_name_steer("dc", c, L)]) for c in [0.0] + GRID_C}
        thr = 0.8 * pr[0.0]
        extra = None
        if pr[0.25] < thr:
            extra = 0.1
        else:
            ok = [c for c in GRID_C if pr[c] >= thr]
            cs = max(ok)
            nxt = [c for c in GRID_C if c > cs]
            if nxt:
                extra = round((cs + nxt[0]) / 2, 4)
        cstar[t] = {"pass_rates": {str(k): v for k, v in pr.items()}, "threshold": thr, "bisection": extra,
                    "final": False}
        state["cstar"] = cstar
        save_state()
        if extra is not None:
            run.run_arm(t, "dc", dvec[t][L], extra, L, allp)
    for t in TASKS:
        if cstar[t].get("final"):
            continue
        extra = cstar[t]["bisection"]
        pr = {float(k): v for k, v in cstar[t]["pass_rates"].items()}
        if extra is not None:
            lab = wait_for_labels(t, [cond_name_steer("dc", extra, L)], timeout_s=30 * 60)
            pr[extra] = pass_rate(lab[cond_name_steer("dc", extra, L)])
        thr = cstar[t]["threshold"]
        ok = [c for c in pr if c > 0 and pr[c] >= thr]
        flag = None
        if ok:
            cs = max(ok)
        else:
            ok50 = [c for c in pr if c > 0 and pr[c] >= 0.5]
            cs = max(ok50) if ok50 else min(c for c in pr if c > 0)
            flag = "no_correctness_preserving_c"
        cstar[t].update({"pass_rates": {str(k): v for k, v in sorted(pr.items())}, "c_star": cs, "flag": flag,
                         "final": True})
        state["cstar"] = cstar
        save_state()
        logger.info(f"{t}: c* = {cs} (flag={flag}); pass rates {pr}")
    (RESULTS_DIR / "cstar.json").write_text(json.dumps({"layer": L, **cstar}, indent=1))

    # ---------------- CONTROLS at c* ----------------
    rng_meta = json.loads((DIRECTIONS_DIR / "directions_meta.json").read_text())
    for k in (1, 2):
        for t in TASKS:
            run.run_arm(t, f"rand{k}", load_dir(f"rand{k}_{t}_L{L}.npy"), cstar[t]["c_star"], L, allp)
    logger.info(f"controls done; time left {run.time_left() / 60:.1f} min")

    # ---------------- EXTENSIONS ----------------
    if not args.no_extensions:
        ext = [("placebo", lambda t: load_dir(f"d_placebo_{t}_L{L}.npy"), allp),
               ("breadth", lambda t: load_dir(f"d_breadth_{t}_L{L}.npy"), allp),
               ("dcxfer", lambda t: dvec["T2" if t == "T1" else "T1"][L], list(range(5)))]
        for name, getv, pids in ext:
            need = len(TASKS) * len(pids) * run.est_batch()
            if run.time_left() < need * 1.1:
                logger.warning(f"skipping extension {name}: needs {need / 60:.1f} min, left {run.time_left() / 60:.1f}")
                state.setdefault("skipped_extensions", []).append(name)
                save_state()
                continue
            for t in TASKS:
                run.run_arm(t, name, getv(t), cstar[t]["c_star"], L, pids)
            state.setdefault("done_extensions", []).append(name)
            save_state()
    state["rand_meta"] = rng_meta.get("rand", {})
    state["finished_utc"] = datetime.now(timezone.utc).isoformat()
    save_state()
    logger.info(f"hf_steer finished in {(time.time() - t_start) / 60:.1f} min")
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
