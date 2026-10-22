#!/usr/bin/env python3
"""S0-CPU GATES (no GPU work until all pass) and the iteration-4 relabel.

C1  the 40 population directions (+ the 9004 positive control) are bitwise equal to unit(PCG64(s).standard_normal)
C2  slot map from exp22 samples_raw.jsonl: 10 screen + 20 confirmation slots per cell, prompt sha256 == prompts4,
    seed == stable_seed(task, template, k)  -> predictions/slot_map.json
C3  src/escape.py reproduces exp22 results/escape.json exactly from exp22's own labels (T10, T2, T03; alpha 1, 2)
C4  ONE labeller version for every row = exp22's labeller + the exp28 re-gated array-Dijkstra T2 rule: every exp22
    T2 row is relabelled (runtime and AST labels re-gated, then the suite's combine(); exp22's judge label is kept
    where the pair still needs a judge); T10/T03 bench labels are unchanged by construction (same labeller).
    -> inputs-derived data/iter4_relabelled.jsonl, results/relabel_iter4.json (every changed label listed) and
       E_iter4_relabelled (the reproduction target)
C5  n[l,p] (ctx4.ban_unit) has shape [12, |S|]; exp22's logged POP realised displacement along u equals alpha*n
    within 1% (rel_err_max) on every logged POP prefill of T10/T2/T03
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c6 import (DATA, DEFAULTS, E22, PRED, RESULTS, SEEDS_POP, V22, read_json, read_jsonl, setup_logging,  # noqa: E402
                    sha256_file, stable_seed, utc_now, write_json, append_jsonl)
from escape import escape_table  # noqa: E402

TASKS3 = ("T10", "T2", "T03")


def catalogue(task: str) -> set[str]:
    import cfg4  # noqa: F401  (vendored; sets paths)
    from screen import catalogue as cat
    return set(cat(task))


def c1() -> dict[str, Any]:
    bad = []
    for s in SEEDS_POP + [9004]:
        p = V22 / "directions" / f"rand_{s}.npy"
        v = np.load(p)
        x = np.random.Generator(np.random.PCG64(s)).standard_normal(4096)
        u = (x / np.linalg.norm(x)).astype(np.float32)
        if not (v.dtype == np.float32 and v.shape == (4096,) and np.array_equal(v, u)):
            bad.append(s)
    return {"pass": not bad, "n": len(SEEDS_POP) + 1, "bad": bad,
            "sha256": {s: sha256_file(V22 / "directions" / f"rand_{s}.npy") for s in SEEDS_POP + [9004]}}


def load_exp22_rows() -> list[dict[str, Any]]:
    keep = ("task", "arm", "template", "sample_id", "family", "alpha", "direction_seed", "stage", "prompt_sha256",
            "seed", "n_tokens", "finish_reason", "fence_step", "logprob_sum", "block_id")
    out = []
    for r in read_jsonl(E22 / "samples_raw.jsonl"):
        if r["task"] in TASKS3:
            d = {k: r.get(k) for k in keep}
            d["token_ids"] = r["token_ids"]
            out.append(d)
    return out


def c2(raw: list[dict[str, Any]]) -> dict[str, Any]:
    prompts = {}
    for p in read_jsonl(V22 / "prompts" / "prompts4.jsonl"):
        if p["task"] in TASKS3 and p["kind"] == "twin":
            prompts[(p["task"], p["template_id"])] = p["prompt_sha256"]
    slot_map: dict[str, dict[str, list]] = {}
    problems = []
    for r in raw:
        if r["family"] not in ("TWIN", "POP"):
            continue
        k = int(r["sample_id"])
        phase = ("twin" if r["family"] == "TWIN" else ("screen" if k in (0, 1) else "confirm"))
        if r["family"] == "TWIN" and k >= 10:
            phase = "twin_pad"
        ent = [r["template"], k, int(r["seed"]), r["prompt_sha256"], phase]
        slot_map.setdefault(r["task"], {}).setdefault(r["arm"], []).append(ent)
        if r["prompt_sha256"] != prompts[(r["task"], r["template"])]:
            problems.append(("prompt_sha", r["task"], r["arm"], r["template"], k))
        if int(r["seed"]) != stable_seed(r["task"], r["template"], k):
            problems.append(("seed", r["task"], r["arm"], r["template"], k))
    counts = {}
    for t in TASKS3:
        arms = slot_map.get(t, {})
        n_scr_ok = n_conf = 0
        for s in SEEDS_POP:
            for a in (1.0, 2.0):
                ents = arms.get(f"POP_d{s}_a{a}", [])
                scr = sorted((e[0], e[1]) for e in ents if e[4] == "screen")
                cf = [e for e in ents if e[4] == "confirm"]
                if scr == sorted((w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in (0, 1)):
                    n_scr_ok += 1
                else:
                    problems.append(("screen_slots", t, s, a, len(scr)))
                if cf:
                    n_conf += 1
                    if len(cf) != 20:
                        problems.append(("confirm_slots", t, s, a, len(cf)))
        tw = sorted((e[0], e[1]) for e in arms.get("TWIN", []) if e[4] == "twin")
        counts[t] = {"cells_with_10_screen_slots": n_scr_ok, "cells_confirmed_tested": n_conf,
                     "twin_slots": len(tw), "twin_complete": len(set(tw)) == 50}
        if len(set(tw)) != 50:
            problems.append(("twin_slots", t, len(set(tw))))
    for t in slot_map:
        for arm in slot_map[t]:
            slot_map[t][arm].sort()
    write_json(PRED / "slot_map.json", {"utc": utc_now(), "fields": ["template", "k", "seed", "prompt_sha256", "phase"],
                                        "map": slot_map})
    return {"pass": not problems, "counts": counts, "problems": problems[:50], "n_problems": len(problems),
            "slot_map_sha256": sha256_file(PRED / "slot_map.json")}


def join(raw: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in raw:
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        if k in labels:
            l = labels[k]
            out.append({**{x: r.get(x) for x in ("task", "arm", "template", "sample_id", "family", "alpha",
                                                 "direction_seed", "stage", "n_tokens", "finish_reason")},
                        "label": l["label"], "passed": bool(l.get("passed")), "valid": bool(l.get("valid")),
                        "code_sha256": l.get("code_sha256")})
    return out


def c3(raw: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    esc = read_json(E22 / "escape.json")
    rows = join(raw, labels)
    res, ok = {}, True
    for t in TASKS3:
        rt = [r for r in rows if r["task"] == t and r["family"] in ("TWIN", "POP")]
        tab = escape_table(rt, SEEDS_POP, catalogue(t), DEFAULTS[t])
        ref = esc[t]
        cmp = {"twin_mine": tab["twin"], "twin_ref": ref["twin"], "twin_equal": tab["twin"] == ref["twin"]}
        ok &= cmp["twin_equal"]
        for a in ("1.0", "2.0"):
            m, r_ = tab["E_t"][a], ref["E_t"][a]
            eq = (m["n_run"] == r_["n_run"] and m["n_screen_pass"] == r_["n_screen_pass"]
                  and m["n_confirmed"] == r_["n_confirmed"] and abs(m["E_t"] - r_["E_t"]) < 1e-12)
            cmp[a] = {"mine": m, "ref": {k: r_[k] for k in ("n_run", "n_screen_pass", "n_confirmed", "E_t")},
                      "equal": eq}
            ok &= eq
        mine_conf = sorted((int(k.split("|")[0]), k.split("|")[1]) for k, c in tab["cells"].items() if c["confirmed"])
        ref_conf = sorted((c["seed"], c["alpha"]) for c in ref["confirmed"])
        cmp["confirmed_set_equal"] = mine_conf == ref_conf
        ok &= cmp["confirmed_set_equal"]
        res[t] = cmp
    return {"pass": bool(ok), "per_task": res}


def regate_row(l: dict[str, Any]) -> dict[str, Any]:
    """Current labeller version applied to an exp22 path-task label row (no new judge call)."""
    from labeller.combine import combine, needs_judge  # vendored exp8 suite
    from regate_rules import apply_t2  # vendored exp28

    if l["label"] == "invalid" or l.get("code") is None:
        return {**l, "label_v6": l["label"], "regate_applied": False}
    rl, r1 = apply_t2(l.get("runtime_label"), l.get("code"))
    al, r2 = apply_t2(l.get("ast_label"), l.get("code"))
    j = {"label": l["judge_label"]} if l.get("judge_label") else None
    if needs_judge(rl, al) and not j:
        lab = "disputed"
    else:
        lab, _ = combine(rl, al, j)
    return {**l, "label_v6": lab, "runtime_label_v6": rl, "ast_label_v6": al, "regate_applied": bool(r1 or r2)}


def c4(raw: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, dict]]:
    import cfg4  # noqa: F401
    sys.path.insert(0, str(V22 / "inputs" / "exp8" / "suite"))
    new = {}
    changed = []
    for k, l in labels.items():
        if l["task"] not in TASKS3:
            continue
        if l["task"] == "T2":
            r = regate_row(l)
            nl = r["label_v6"]
        else:
            nl = l["label"]
        nn = {**l, "label": nl, "label_iter4": l["label"]}
        new[k] = nn
        if nl != l["label"]:
            changed.append({"key": k, "from": l["label"], "to": nl})
    out_rows = [{x: v.get(x) for x in ("key", "task", "template", "arm", "sample_id", "label", "label_iter4", "passed",
                                       "valid", "runtime_label", "ast_label", "judge_label", "code_sha256")}
                for v in new.values()]
    p = DATA / "iter4_relabelled.jsonl"
    if p.exists():
        p.unlink()
    append_jsonl(p, out_rows)
    rows = join(raw, new)
    E = {}
    for t in TASKS3:
        rt = [r for r in rows if r["task"] == t and r["family"] in ("TWIN", "POP")]
        tab = escape_table(rt, SEEDS_POP, catalogue(t), DEFAULTS[t])
        E[t] = {"twin": tab["twin"], "E_t": tab["E_t"],
                "confirmed": sorted(k for k, c in tab["cells"].items() if c["confirmed"]),
                "screen_pass_not_topped": sorted(k for k, c in tab["cells"].items()
                                                 if c["screen_pass"] and not c["topped_up"])}
    by = collections.Counter((c["key"].split("|")[0], c["from"], c["to"]) for c in changed)
    rep = {"labeller_version": "exp22 label_worker (vendored) + exp28 regate_rules.apply_t2 on T2 runtime and AST labels",
           "n_rows": len(new), "n_changed": len(changed),
           "changes_by_task": {f"{a}:{b}->{c}": n for (a, b, c), n in sorted(by.items())},
           "changed_rows": changed, "E_iter4_relabelled": E}
    write_json(RESULTS / "relabel_iter4.json", rep)
    return {"pass": True, "n_changed": len(changed), "changes_by_task": rep["changes_by_task"],
            "E_iter4_relabelled": {t: {a: E[t]["E_t"][a]["E_t"] for a in ("1.0", "2.0")} for t in TASKS3},
            "screen_pass_not_topped_after_relabel": {t: E[t]["screen_pass_not_topped"] for t in TASKS3}}, new


def c5() -> dict[str, Any]:
    import cfg4  # noqa: F401
    from ctx4 import ban_unit

    prompts = {}
    for p in read_jsonl(V22 / "prompts" / "prompts4.jsonl"):
        if p["kind"] == "twin" and p["task"] in TASKS3:
            prompts.setdefault(p["task"], set()).add(p["spec_end"] - p["p1"])
    shapes, ok = {}, True
    for t in TASKS3:
        n = ban_unit(t)
        S = prompts[t]
        shapes[t] = {"shape": list(n.shape), "S_lengths": sorted(S), "mean_n": float(n.mean()),
                     "mean_n_per_block": [float(x) for x in n.mean(1)]}
        ok &= (n.shape[0] == 12 and len(S) == 1 and n.shape[1] == next(iter(S)))
    recs = [r for r in read_jsonl(E22 / "realised_disp.jsonl") if r["task"] in TASKS3 and r["arm"].startswith("POP")]
    errs = np.array([r["rel_err_max"] for r in recs])
    frac_ok = float((errs <= 0.01).mean()) if len(errs) else float("nan")
    ok &= frac_ok == 1.0
    return {"pass": bool(ok), "units": shapes, "n_pop_prefills": len(recs), "rel_err_max_max": float(errs.max()),
            "rel_err_max_median": float(np.median(errs)), "frac_within_1pct": frac_ok}


def main() -> None:
    setup_logging("cpu_gates")
    from loguru import logger

    raw = load_exp22_rows()
    labels = {l["key"]: l for l in read_jsonl(E22 / "labels.jsonl") if l["task"] in TASKS3}
    out = {"utc": utc_now()}
    out["C1"] = c1()
    logger.info(f"C1 {out['C1']['pass']}")
    out["C2"] = c2(raw)
    logger.info(f"C2 {out['C2']['pass']} {out['C2']['counts']} problems {out['C2']['problems'][:5]}")
    out["C3"] = c3(raw, labels)
    logger.info(f"C3 {out['C3']['pass']}")
    for t, v in out["C3"]["per_task"].items():
        logger.info(f"  {t}: twin_equal {v['twin_equal']} a1 {v['1.0']['equal']} a2 {v['2.0']['equal']} "
                    f"conf_set {v['confirmed_set_equal']} mine a1 {v['1.0']['mine']} a2 {v['2.0']['mine']}")
    out["C4"], _ = c4(raw, labels)
    logger.info(f"C4 changed {out['C4']['n_changed']} {out['C4']['changes_by_task']} E {out['C4']['E_iter4_relabelled']}")
    out["C5"] = c5()
    logger.info(f"C5 {out['C5']['pass']} n {out['C5']['n_pop_prefills']} max {out['C5']['rel_err_max_max']:.2e}")
    out["all_pass"] = all(out[c]["pass"] for c in ("C1", "C2", "C3", "C4", "C5"))
    write_json(RESULTS / "cpu_gates.json", out)
    logger.info(f"ALL PASS: {out['all_pass']}")
    if not out["all_pass"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
