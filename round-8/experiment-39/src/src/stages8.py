#!/usr/bin/env python3
"""GPU stages 1-4 (registered into gpu8.STAGES).

smoke  every decode_k1 option on 2 short rows each (results/smoke_<model>.json)
s1     blind locator on T10 and B3: 6 twin base paths (slots 0-5), prefixes j = 2, 4, ..., 64, 8 continuations each
       with fresh locator streams, stopped once the opening classifier decides ('decided'); change points from exp35
       forks.change_points with a 1,000-shuffle permutation null (analysis in locator8.py). The code never reads the
       known decision indices.
s2     token maps: for every decision node, teacher-forced fp32 logits per template (top-64 saved), the T = 1 opening
       path log-probability (w_c), and K = 10 full T = 1 continuations for every token of the union of the templates'
       top-20 (2 per template); T10 n11 = n10 + ' def' adds ' bfs' and ' dfs'; T10's non-committal index-10 tokens
       get a teacher-forced top-64 at index 11 (pooled class map, no new continuations).
s3     arms (after COMMIT #1), see arms8.py
s4     HR (after COMMIT #2), see arms8.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, CONTS, K_MAP, RESULTS_DIR, SAMPLES, SEED_LOCATOR, TEMPLATES, TOPK_DOSE, UNITS,  # noqa
                  log_deviation, read_json, read_jsonl, slot_template, slot_ukey, u_stream, utc_now, write_json)
import gpu8 as G8  # noqa: E402
import units8 as U8  # noqa: E402

NODE_DIR = CACHE_DIR / "nodes"
NODE_DIR.mkdir(parents=True, exist_ok=True)


def smoke(R: Any, units: list[str]) -> None:
    import engine8 as EN
    tok = R.tok
    unit = "T10" if R.flavor == "qwen" else "G"
    pre = R.prefill(unit, "W1")
    op = [n["opening"] for n in U8.nodes(unit)]
    base = {"pre": pre, "max_new": 48, "openings": op}
    opts = [{}, {"T": 1.3, "top_p": 0.95}, {"T": 3.0, "min_p": 0.1}, {"edt": {"q": 0.5, "T": 2.0}},
            {"adapt": {"T": 2.0}}, {"dose": {"T": 15.0, "k": 20}}, {"fixed_pos": {"pos": [3, 4], "T": 15.0, "k": 20}},
            {"window": {"n": 16, "T": 15.0, "k": 20}}]
    rows = [{**base, **o, "u": u_stream(*slot_ukey(unit, s))} for o in opts for s in range(2)]
    res = EN.decode_k1(R.model, tok, rows, fence_kind=UNITS[unit]["fence"])
    out = [{"opt": {k: str(v)[:60] for k, v in opts[i // 2].items()}, "dec_pos": r["decision_pos"],
            "dec_tok": r["decision_token"], "n_mod": r["n_modified_steps"], "mod": r["modified_steps"][:10],
            "body_start": r["body_start"], "text": tok.decode(r["token_ids"])[:120]} for i, r in enumerate(res)]
    write_json(RESULTS_DIR / f"smoke_{R.flavor}.json", out)


# ------------------------------------------------------------------------------------------------ stage 1
def stage1_locator(R: Any, units: list[str]) -> None:
    tok = R.tok
    for ui, unit in enumerate(("T10", "B3")):
        if unit not in units:
            continue
        twin = {r["slot"]: r for r in read_jsonl(SAMPLES) if r["unit"] == unit and r["arm"] == "A0"}
        specs = []
        for p in range(6):
            path = twin[p]["token_ids"]
            for j in range(2, 65, 2):
                if j >= len(path) - 1:
                    break
                for k in range(8):
                    specs.append({"sid": f"LOC|{unit}|p{p}|j{j}|{k}", "unit": unit, "arm": "LOC", "stage": "S1",
                                  "slot": p, "w": slot_template(p), "base_slot": p, "j": j, "k": k,
                                  "ukey": ("iter8loc", SEED_LOCATOR + ui * 1000 + p * 100 + j, k),
                                  "max_new": UNITS[unit]["max_new"], "T": 1.0, "prefix": path[:j]})

        def factory(part: list[dict[str, Any]], unit=unit) -> Callable:
            def stop(r_: int, ids: list[int]) -> bool:
                if len(ids) <= len(part[r_]["prefix"]) + 2:
                    return False
                return U8.classify_partial(unit, tok.decode(ids, skip_special_tokens=True)) != "undecided"
            return stop
        t0 = time.time()
        R.run(specs, f"S1_loc_{unit}", out=CONTS, light=True, stop_fn_factory=factory, batch=50)
        G8.logger.info(f"locator {unit}: {len(specs)} continuations in {time.time() - t0:.0f}s")
        R.clear()


# ------------------------------------------------------------------------------------------------ stage 2
def node_list(unit: str) -> list[dict[str, Any]]:
    out = list(U8.nodes(unit))
    sec = U8.second_node(unit)
    if sec:
        out.append(sec)
    return out


def tf_node(R: Any, unit: str, opening: list[int]) -> dict[str, Any]:
    """Per template: top-64 (ids, logits) at the node, and the T = 1 log-probability of the opening path."""
    import engine8 as EN
    res = {}
    for w in TEMPLATES:
        ids = U8.prompt_ids(unit, w)
        rows = EN.teacher_force_rows(R.model, ids + opening, len(ids))        # row j predicts opening[j]; last = node
        z = rows[-1]
        top = np.argsort(-z)[:64]
        lp = 0.0
        for j, t in enumerate(opening):
            x = rows[j] - rows[j].max()
            lp += float(x[t] - math.log(np.exp(x).sum()))
        res[w] = {"top_ids": top.tolist(), "top_z": z[top].tolist(), "path_logprob": lp,
                  "top_str": [R.tok.decode([int(t)]) for t in top[:24]]}
    return res


def stage2_maps(R: Any, units: list[str]) -> None:
    tok = R.tok
    order = [u for u in ("T10", "B3", "G", "T1", "A3", "B6") if u in units and UNITS[u]["model"] == R.flavor]
    for unit in order:
        for nd in node_list(unit):
            t0 = time.time()
            path = NODE_DIR / f"{unit}_{nd['id']}.json"
            if path.exists():
                info = read_json(path)
            else:
                tf = tf_node(R, unit, nd["opening"])
                pooled: dict[int, float] = {}
                for w in TEMPLATES:
                    ids, z = tf[w]["top_ids"], np.array(tf[w]["top_z"])
                    p = np.exp(z[:TOPK_DOSE] - z[:TOPK_DOSE].max())
                    p /= p.sum()
                    for t, pp in zip(ids[:TOPK_DOSE], p):
                        pooled[t] = pooled.get(t, 0.0) + pp / len(TEMPLATES)
                toks = sorted(pooled, key=lambda t: -pooled[t])[:24]
                if unit == "T10" and nd["id"] == "n11":
                    for s in (" bfs", " dfs"):
                        t = G8.tok_id(tok, s)
                        if t not in toks:
                            toks.append(t)
                info = {"unit": unit, "node": nd["id"], "opening": nd["opening"], "pos": nd["pos"], "tf": tf,
                        "map_tokens": toks, "map_token_str": {str(t): tok.decode([t]) for t in toks},
                        "pooled_p20": {str(t): pooled.get(t, 0.0) for t in toks}, "utc": utc_now()}
                # T10 n10: teacher-forced top-64 at index 11 under every index-10 token with T = 1 mass >= 1e-4
                if unit == "T10" and nd["id"] == "n10":
                    sec = {}
                    for t in toks:
                        if pooled.get(t, 0.0) < 1e-4 and t != U8.T10_DEF:
                            continue
                        sec[str(t)] = tf_node(R, unit, nd["opening"] + [t])
                    info["second_tf"] = sec
                write_json(path, info)
            specs = []
            for t in info["map_tokens"]:
                for k in range(K_MAP):
                    w = TEMPLATES[k % 5]
                    specs.append({"sid": f"MAP|{unit}|{nd['id']}|{t}|{k}", "unit": unit, "arm": "MAP", "stage": "S2",
                                  "slot": None, "w": w, "node": nd["id"], "token": int(t), "k": k,
                                  "ukey": ("iter8map", unit, nd["id"], int(t), k),
                                  "max_new": UNITS[unit]["max_new"], "T": 1.0, "prefix": nd["opening"] + [int(t)]})
            R.run(specs, f"S2_map_{unit}_{nd['id']}", out=CONTS, light=True)
            G8.logger.info(f"token map {unit}/{nd['id']}: {len(specs)} continuations in {time.time() - t0:.0f}s")
            R.clear()


STAGES: dict[str, Callable] = {"smoke": smoke, "s1": stage1_locator, "s2": stage2_maps}

try:                                     # stages 3-4 live in arms8.py (written after COMMIT #1 code)
    import arms8  # noqa: E402
    STAGES.update(arms8.STAGES)
except ImportError:
    pass
