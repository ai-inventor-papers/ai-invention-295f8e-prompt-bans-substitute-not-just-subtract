#!/usr/bin/env python3
"""F2 scoring passes (GPU, teacher forcing only): q_lik and the twin margin m on all 15 existing tasks, plus the
thinking-on T2 margin.

Programs: up to 10 test-passing forced programs per catalogue algorithm whose label equals the forced algorithm
(exp22 gpu_phase3.forced_programs fields): bench = forced_programs.jsonl (forced_mode / label / passed / code);
T1/T2 = exp7 forced_selected.jsonl (j / label / passed / code_scrubbed, the name-scrubbed copy). Fewer than 10 -> all
(minimum 3, flagged); fewer than 3 -> undefined. Continuation = tok('```python\\n' + code) after each twin prompt
(W1-W5; the fence is reconstructed because the stored programs hold only the extracted code -- flagged); the decode
round-trip is asserted. LP48 = sum of the fp32 log-probabilities of the first 48 code tokens (the first token whose
text contains code characters after the fence line). Every program is scored twice in two batch compositions
(order shuffled) to estimate the bf16 scoring SD. The mean residual over code tokens 1-32 at blocks 18 and 23 is
saved (descriptive code-opening manifold).
Thinking-on T2: one trace per template (enable_thinking=True, T 0.7, top-k 10, at most 4,096 tokens); for each
completed trace the default's and the runner-up's programs are teacher-forced after '</think>\\n\\n'.
"""

from __future__ import annotations

import json
import random
import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (BENCH, CACHE_DIR, E7, E22, E24, RESULTS_DIR, TEMPLATE_IDS, read_json, read_jsonl, setup_logging,
                 utc_now, write_json)
from engine_w16 import free_cuda, load_model, sample_think, score_openings, u_stream
from prompts import chat_ids

TASKS15 = ["T03", "T04", "T05", "T06", "T08", "T10", "T11", "T13", "T14", "R1", "R2", "R3", "R6", "T1", "T2"]
N_PROG = 10
N_SCORE = 48
FENCE = "```python\n"
THINK_END = 151668  # '</think>'


def bench_dir(task: str):
    return next(d for d in BENCH.iterdir() if d.is_dir() and d.name.split("_")[0] == task)


def forced_programs(task: str) -> dict[str, list[str]]:
    """{algorithm: [code, ...]} correct adherent forced programs, sorted by sample id, first N_PROG kept."""
    out: dict[str, list[tuple[str, str]]] = {}
    if task in ("T1", "T2"):
        et = {"T1": "t1", "T2": "t2"}[task]
        for r in read_jsonl(E7 / "data" / "forced_selected.jsonl"):
            if r["task"] == et and r["label"] == r["j"] and r["passed"]:
                code = r.get("code_scrubbed") or r.get("code_raw")
                if code:
                    out.setdefault(r["j"], []).append((str(r.get("prog_id") or r.get("sample_id")), code))
    else:
        for r in read_jsonl(bench_dir(task) / "forced_programs.jsonl"):
            if r.get("forced_mode") and r["label"] == r["forced_mode"] and r["passed"] and r.get("code"):
                out.setdefault(r["forced_mode"], []).append((str(r.get("sample_id")), r["code"]))
    # supplement (flagged): below 3 adherent programs, add test-passing programs whose label is the algorithm from
    # other forced conditions of the same file (label-verified, non-adherent) -- replaces the plan's generation fallback
    extra: dict[str, list[tuple[str, str]]] = {}
    if task not in ("T1", "T2"):
        for r in read_jsonl(bench_dir(task) / "forced_programs.jsonl"):
            if r.get("forced_mode") and r["label"] != r["forced_mode"] and r["passed"] and r.get("code"):
                extra.setdefault(r["label"], []).append((str(r.get("sample_id")), r["code"]))
    else:
        et = {"T1": "t1", "T2": "t2"}[task]
        for r in read_jsonl(E7 / "data" / "forced_selected.jsonl"):
            if r["task"] == et and r["label"] != r["j"] and r["passed"] and (r.get("code_scrubbed") or r.get("code_raw")):
                extra.setdefault(r["label"], []).append((str(r.get("prog_id")), r.get("code_scrubbed") or r["code_raw"]))
    res = {}
    bad = {"other", "invalid", "unknown", "unresolved", "no_code"}
    for a in sorted((set(out) | set(extra)) - bad):
        seen, keep = set(), []
        for sid, c in sorted(out.get(a, [])):
            c = c.strip("\n") + "\n"
            if c in seen:
                continue
            seen.add(c)
            keep.append(c)
        n_adh = len(keep)
        if n_adh < 3:
            for sid, c in sorted(extra.get(a, [])):
                c = c.strip("\n") + "\n"
                if c not in seen and len(keep) < 3:
                    seen.add(c)
                    keep.append(c)
        if keep:
            res[a] = keep[:N_PROG]
            SUPPLEMENTED.setdefault(task, {})[a] = {"n_adherent": min(n_adh, N_PROG), "n_used": len(res[a]),
                                                     "supplemented": len(keep) > n_adh}
    return res


SUPPLEMENTED: dict[str, dict[str, Any]] = {}


def twin_prompts(tok: Any) -> dict[tuple[str, str], list[int]]:
    out = {}
    for r in read_jsonl(E22 / "prompts" / "prompts4.jsonl"):
        if r["kind"] == "twin" and r["task"] in TASKS15:
            ids = chat_ids(tok, r["user_text"])
            assert ids == r["ids"], f"twin re-render mismatch {r['task']}/{r['template_id']}"
            out[(r["task"], r["template_id"])] = ids
    return out


def continuation(tok: Any, code: str) -> tuple[list[int], int]:
    text = FENCE + code
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    assert tok.decode(ids) == text, "decode round-trip failed"
    cs = next(j for j, (a, b) in enumerate(offs) if b > len(FENCE))
    return ids, cs


def lme(x: np.ndarray) -> float:
    m = float(np.max(x))
    return m + float(np.log(np.mean(np.exp(x - m))))


@torch.no_grad()
def run_qlik(model: Any, tok: Any) -> None:
    outp = RESULTS_DIR / "q_lik_raw.json"
    if outp.exists():
        return
    t0 = time.time()
    tw = twin_prompts(tok)
    items, meta = [], []
    progs_all: dict[str, dict[str, list[str]]] = {}
    for t in TASKS15:
        progs = forced_programs(t)
        progs_all[t] = progs
        for a, codes in progs.items():
            if len(codes) < 3:
                continue
            for pi, code in enumerate(codes):
                cont, cs = continuation(tok, code)
                for w in TEMPLATE_IDS:
                    p = tw[(t, w)]
                    items.append({"ids": p + cont, "P": len(p), "cs": cs, "n": len(cont)})
                    meta.append({"task": t, "alg": a, "prog": pi, "w": w})
    logger.info(f"q_lik: {len(items)} teacher-forced sequences")
    rng = random.Random(0)
    res = {}
    for rep in (0, 1):
        order = list(range(len(items)))
        if rep == 1:
            rng.shuffle(order)
        else:
            order.sort(key=lambda i: len(items[i]["ids"]))  # composition A: length-sorted batches
        sc = score_openings(model, [items[i] for i in order], n_score=N_SCORE, batch=8,
                            capture_blocks=(18, 23) if rep == 0 else ())
        for j, i in enumerate(order):
            res.setdefault(i, {})[rep] = sc[j]
        free_cuda()
    rows = []
    states = {18: [], 23: []}
    for i, m in enumerate(meta):
        a, b = res[i][0], res[i][1]
        rows.append({**m, "m_tokens": a["m"], "lp48": float(a["lp"].sum()), "lp48_rep2": float(b["lp"].sum()),
                     "lp_tok_mean": float(a["lp"].mean()) if a["m"] else None,
                     "lp_tokens": [round(float(x), 5) for x in a["lp"]]})
        for l in (18, 23):
            states[l].append(a["states"][l])
    np.savez(CACHE_DIR / "code_opening_states.npz", s18=np.stack(states[18]).astype(np.float32),
             s23=np.stack(states[23]).astype(np.float32), meta=np.array([json.dumps(m) for m in meta]))
    write_json(outp, {"rows": rows, "n_programs": {t: {a: len(c) for a, c in p.items()} for t, p in progs_all.items()},
                      "program_sources": SUPPLEMENTED,
                      "n_score": N_SCORE, "fence": "reconstructed '```python\\n' + code (flagged)",
                      "seconds": time.time() - t0, "utc": utc_now()}, indent=None)
    logger.info(f"q_lik done in {time.time() - t0:.0f}s")


@torch.no_grad()
def run_thinking(model: Any, tok: Any) -> None:
    outp = RESULTS_DIR / "f2_thinking_raw.json"
    if outp.exists():
        return
    t0 = time.time()
    tw = {r["template_id"]: r for r in read_jsonl(E22 / "prompts" / "prompts4.jsonl")
          if r["kind"] == "twin" and r["task"] == "T2"}
    progs = forced_programs("T2")
    rep = read_json(E24 / "results" / "base_repertoire.json")["per_task"]["T2"]
    D, ru = rep["default"], rep["r_t"]
    traces = []
    for w in TEMPLATE_IDS:
        ids = chat_ids(tok, tw[w]["user_text"], thinking=True)
        tr = sample_think(model, ids, [u_stream("T2", w, "THINK", n=4096)], 4096, 0.7, 10)[0]
        traces.append({"w": w, "prompt_ids": ids, **tr})
        logger.info(f"thinking trace T2/{w}: {tr['n_tokens']} tokens, finished {tr['finished']}")
        free_cuda()
    out = []
    for tr in traces:
        tk = tr["token_ids"]
        if THINK_END not in tk:
            out.append({"w": tr["w"], "completed": False, "n_tokens": tr["n_tokens"]})
            continue
        j = tk.index(THINK_END)
        head = tr["prompt_ids"] + tk[:j + 1]
        nl = tok("\n\n", add_special_tokens=False)["input_ids"]
        items, mt = [], []
        for a in (D, ru):
            for code in progs.get(a, []):
                cont, cs = continuation(tok, code)
                items.append({"ids": head + nl + cont, "P": len(head) + len(nl), "cs": cs, "n": len(cont)})
                mt.append(a)
        sc = score_openings(model, items, n_score=N_SCORE, batch=4)
        lpD = [float(s["lp"].sum()) for s, a in zip(sc, mt) if a == D]
        lpR = [float(s["lp"].sum()) for s, a in zip(sc, mt) if a == ru]
        final_text = tok.decode(tk[j + 1:], skip_special_tokens=True)
        out.append({"w": tr["w"], "completed": True, "n_think_tokens": j, "n_tokens": tr["n_tokens"],
                    "m": float(np.mean(lpD) - np.mean(lpR)) if lpD and lpR else None,
                    "final_text_head": final_text[:300], "think_text_head": tok.decode(tk[:min(j, 200)])})
        free_cuda()
    write_json(outp, {"D": D, "r_u": ru, "traces": out, "sampler": "T 0.7, top-k 10, max 4096, enable_thinking",
                      "seconds": time.time() - t0, "utc": utc_now()})


def main() -> None:
    setup_logging("scoring")
    torch.backends.cuda.matmul.allow_tf32 = False
    tok, model = load_model()
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "qlik"):
        run_qlik(model, tok)
    if what in ("all", "think"):
        run_thinking(model, tok)


if __name__ == "__main__":
    main()
