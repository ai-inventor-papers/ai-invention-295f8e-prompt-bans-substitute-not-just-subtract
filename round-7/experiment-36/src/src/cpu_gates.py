#!/usr/bin/env python3
"""CPU gates G1-G5 of step K -> results/cpu_gates.json.

G1  every bench file's sha256 equals exp11 bench/commitment.json (T03, T05, T10 and the rest of the frozen bench).
G2  labeller re-check: bench references and gold sets of T03, T05, T10 (runtime label vs adjudicated, against each
    task's gate.json, tolerance 0.02) and the exp8 suite references and eval gold set for T1/T2 (vs gate_report.json),
    with the exp28 T2 re-gate applied as an extra column (exp27 s0_checks logic, mechanical labels only, no judge).
G3  seeds: S4 = stable_seed(task, 'PN_a<alpha>', w, k) equals every logged direction_seed of exp29 engine-d PN rows
    (T10, T2) and of exp19's PN rows (T03, T05, T1); S5 = stable_seed(task, 'PN5', w, k) equals exp27's logged
    PN_a1/PN_a2 direction_seed on all five tasks; regenerated unit vectors are unit-norm float32; the code-stage stream
    of exp27 (n 1,536) has exp29's stream (n 1,024) as its prefix.
G4  unit files: shape [12, |S|] with |S| = spec_end - p1 of every template's twin prompt; sha256 equal to the
    originals of exp13/exp17 (inputs/) and to exp22 input_hashes.json where listed; exp22 units.json outlier rule.
G5  the vendored exp27 hull reproduces exp27's H5 for T10 BINT (2.527) and T03 PN (1.984) (results/g5_hull_gate.json,
    written by src/s3_prices.py g5).

usage: .venv/bin/python src/cpu_gates.py
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import RESULTS, read_json, read_jsonl, sha256_file, stable_seed, write_json  # noqa: E402
import k_units as KU  # noqa: E402

BENCH = K.V22 / "inputs" / "exp11" / "bench"
SUITE = K.V22 / "inputs" / "exp8" / "suite"
for _p in (str(SUITE), str(K.V22 / "inputs" / "exp11")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def g1() -> dict[str, Any]:
    from bench.common.catalogue import TASKS

    com = read_json(BENCH / "commitment.json")
    out: dict[str, Any] = {"bench": {}, "mismatches": []}
    for t, v in com["tasks"].items():
        d = BENCH / TASKS[t]["task_id"]
        ok = 0
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            p = d / f
            got = sha256_file(p) if p.exists() else None
            if got != h:
                out["mismatches"].append({"task": t, "file": f, "expected": h, "got": got})
            else:
                ok += 1
        out["bench"][t] = {"files_checked": ok}
    out["copy_vs_original_commitment"] = sha256_file(BENCH / "commitment.json") == sha256_file(
        K.INPUTS / "exp11" / "bench" / "commitment.json")
    out["pass"] = not out["mismatches"] and out["copy_vs_original_commitment"]
    return out


def g2() -> dict[str, Any]:
    from bench.common.catalogue import TASKS
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests

    res: dict[str, Any] = {}
    for t in ("T03", "T05", "T10"):
        d = BENCH / TASKS[t]["task_id"]
        cases = read_tests(d / "tests.jsonl")
        refs = sorted((d / "references").glob("*.py"))

        def lab(code: str, sid: str, t: str = t, cases: list = cases) -> dict[str, Any]:
            return label_one({"sample_id": sid, "task": t, "condition": "recheck", "mode": None, "paraphrase_id": None,
                              "round": None, "attempt_idx": None, "seed": 0, "finish_reason": "stop",
                              "text": "```python\n" + code + "\n```"}, cases)
        with ThreadPoolExecutor(8) as ex:
            rl = list(ex.map(lambda p: (p.stem, lab(p.read_text(), p.stem)), refs))
        ref_ok = sum(1 for m, l in rl if l.get("runtime_label") == m and l.get("passed"))
        gold = read_jsonl(d / "gold_set.jsonl")
        with ThreadPoolExecutor(8) as ex:
            gl = list(ex.map(lambda g: lab(g["code"], g["gold_id"]), gold))
        agree = [l.get("runtime_label") == g["adjudicated"] for g, l in zip(gold, gl)]
        gate = read_json(d / "gate.json")
        exp = gate["gold"]["runtime_vs_adjudicated"]
        acc = sum(agree) / max(len(agree), 1)
        res[t] = {"references_ok": ref_ok, "n_references": len(refs), "gold_n": len(gold),
                  "gold_runtime_vs_adjudicated": acc, "gate_runtime_vs_adjudicated": exp,
                  "within_0.02": abs(acc - exp) <= 0.02 + 1e-9, "references_pass": ref_ok == len(refs)}
        logger.info(f"G2 {t}: refs {ref_ok}/{len(refs)}, gold runtime acc {acc:.3f} (gate {exp:.3f})")
    from labeller import ast_rules, runtime_rules
    from regate_rules import apply_t2
    from tasks.harness import evaluate_program

    gr = read_json(SUITE / "labeller" / "gate_report.json")
    refs = []
    for tdir, t in (("t1_grid", "t1"), ("t2_wsp", "t2")):
        for p in sorted((SUITE / "tasks" / tdir / "references").glob("*.py")):
            refs.append((t, p))
    ref_modes = {k: v["mode"] for k, v in (gr["references"].items() if isinstance(gr["references"], dict) else [])}

    def one(tp):
        t, p = tp
        code = p.read_text()
        ev = evaluate_program(t, code)
        rl = runtime_rules.label(t, ev["probes"])[0]
        al = ast_rules.label(code, t)[0]
        return {"file": f"{t}/{p.name}", "runtime": rl, "ast": al, "passed": bool(ev["tests"].get("passed")),
                "mode": ref_modes.get(f"{t}/{p.name}")}
    with ThreadPoolExecutor(8) as ex:
        rr = list(ex.map(one, refs))
    ok = sum(1 for r in rr if r["mode"] is not None and r["runtime"] == r["mode"] and r["ast"] == r["mode"])
    gold = [g for g in read_jsonl(SUITE / "labeller" / "gold_set.jsonl") if g.get("split") == "eval"]
    adj_key = next((k for k in ("adjudicated", "gold_label", "label") if gold and k in gold[0]), None)

    def gone(g):
        ev = evaluate_program(g["task"], g["code"])
        r = runtime_rules.label(g["task"], ev["probes"])[0]
        a = ast_rules.label(g["code"], g["task"])[0]
        rg = apply_t2(r, g["code"])[0] if g["task"] == "t2" else r
        return r, a, rg
    with ThreadPoolExecutor(8) as ex:
        gl = list(ex.map(gone, gold))
    suite: dict[str, Any] = {"references_ok": ok, "n_references": len(rr)}
    if adj_key:
        n = max(len(gold), 1)
        acc_rt = sum(1 for g, (r, a, rg) in zip(gold, gl) if r == g[adj_key]) / n
        acc_ast = sum(1 for g, (r, a, rg) in zip(gold, gl) if a == g[adj_key]) / n
        acc_rg = sum(1 for g, (r, a, rg) in zip(gold, gl) if rg == g[adj_key]) / n
        em = gr["eval_metrics"]
        suite.update({"gold_eval_n": len(gold), "acc_runtime_vs_adjudicated": acc_rt,
                      "acc_ast_vs_adjudicated": acc_ast, "acc_runtime_regated_t2": acc_rg,
                      "gate_acc_runtime": em["acc_runtime_vs_adjudicated"], "gate_acc_ast": em["acc_ast_vs_adjudicated"],
                      "runtime_within_0.02": abs(acc_rt - em["acc_runtime_vs_adjudicated"]) <= 0.02 + 1e-9})
    e27 = read_json(K.E27 / "results" / "labeller_recheck.json")["exp8_suite"]
    suite["exp27_recheck"] = {k: e27.get(k) for k in ("gold_eval_n", "acc_runtime_vs_adjudicated",
                                                       "acc_ast_vs_adjudicated")}
    suite["equals_exp27_recheck"] = all(abs(suite.get(k, -1) - e27[k]) < 1e-12 for k in
                                        ("acc_runtime_vs_adjudicated", "acc_ast_vs_adjudicated"))
    suite["note"] = ("gate_report.json's 0.843 / 0.888 are over the 89 resolved eval items; this re-check scores all 92 "
                     "(3 unresolved count as misses), exactly as iteration 5's recheck did (0.8043 / 0.8587)")
    res["suite_T1_T2"] = suite
    logger.info(f"G2 suite: refs {ok}/{len(rr)}; {({k: v for k, v in suite.items() if k.startswith('acc')})}")
    res["pass"] = all(v["within_0.02"] and v["references_pass"] for k, v in res.items() if k in ("T03", "T05", "T10")) \
        and (suite.get("runtime_within_0.02", False) or suite.get("equals_exp27_recheck", False)) and ok == len(rr)
    return res


def g3() -> dict[str, Any]:
    out: dict[str, Any] = {}
    n_ok, n = 0, 0
    bad = []
    for r in read_jsonl(K.E29 / "data" / "raw" / "raw_d.jsonl"):
        if r["arm"] in ("PN_a1", "PN_a2"):
            a = 1.0 if r["arm"] == "PN_a1" else 2.0
            s, u = KU.s4_direction(r["task"], a, r["template"], int(r["sample_id"]))
            n += 1
            if s == int(r["direction_seed"]):
                n_ok += 1
            else:
                bad.append(r["sample_id"])
    out["S4_vs_exp29_engine_d"] = {"n": n, "match": n_ok}
    n_ok19, n19 = 0, 0
    for r in read_jsonl(K.E19 / "data" / "samples.jsonl"):
        if r.get("arm") in ("PN_a1", "PN_a2") and r["task"] in ("T03", "T05", "T1", "T10", "T2"):
            a = 1.0 if r["arm"] == "PN_a1" else 2.0
            s, _ = KU.s4_direction(r["task"], a, r["template"], int(r["slot"]))
            n19 += 1
            n_ok19 += s == int(r["direction_seed"])
    out["S4_vs_exp19"] = {"n": n19, "match": n_ok19}
    n27, ok27 = 0, 0
    for r in read_jsonl(K.E27 / "data" / "samples_raw.jsonl"):
        if r["arm"] in ("PN_a1", "PN_a2") and r["task"] in K.D5_TASKS:
            s, u = KU.s5_direction(r["task"], r["template"], int(r["slot"]))
            n27 += 1
            ok27 += s == int(r["direction_seed"])
    out["S5_vs_exp27"] = {"n": n27, "match": ok27}
    _, u = KU.s4_direction("T10", 2.0, "W1", 0)
    out["unit_norm"] = float(np.linalg.norm(u.astype(np.float64)))
    import cfg4  # noqa: F401
    from engine import u_stream
    a = u_stream("T10", "W1", 0, n=1536)
    b = u_stream("T10", "W1", 0, n=1024)
    out["stream_prefix_equal"] = bool(np.array_equal(a[:1024], b))
    out["pass"] = (n_ok == n > 0 and n_ok19 == n19 > 0 and ok27 == n27 > 0 and out["stream_prefix_equal"]
                   and abs(out["unit_norm"] - 1) < 1e-6)
    return out


def g4() -> dict[str, Any]:
    prompts = {}
    for line in open(K.V22 / "prompts" / "prompts4.jsonl"):
        r = json.loads(line)
        if r["kind"] == "twin":
            prompts[(r["task"], r["template_id"])] = r
    ih = read_json(K.E22 / "input_hashes.json")
    flat = json.dumps(ih)
    units = read_json(K.E22 / "units.json")
    out: dict[str, Any] = {}
    orig = {"T10": K.INPUTS / "exp13/results/tensors/norms_T10.npz", "T03": K.INPUTS / "exp13/results/tensors/norms_T03.npz",
            "T05": K.INPUTS / "exp13/results/tensors/norms_T05.npz", "T1": K.INPUTS / "exp17/directions/norms_T1.npy",
            "T2": K.INPUTS / "exp17/directions/norms_T2.npy"}
    vend = {"T10": KU.E13V / "results/tensors/norms_T10.npz", "T03": KU.E13V / "results/tensors/norms_T03.npz",
            "T05": KU.E13V / "results/tensors/norms_T05.npz", "T1": KU.E17V / "directions/norms_T1.npy",
            "T2": KU.E17V / "directions/norms_T2.npy"}
    ok_all = True
    for t in K.D5_TASKS:
        n = KU.u_abs(t)
        sizes = {w: prompts[(t, w)]["spec_end"] - prompts[(t, w)]["p1"] for w in K.TEMPLATES}
        h_v, h_o = sha256_file(vend[t]), sha256_file(orig[t])
        named = t in json.dumps(units.get("outliers", units)) if isinstance(units, dict) else False
        rec = {"shape": list(n.shape), "spec_sizes": sizes, "aligned": n.shape == (12, sizes["W1"]) and
               len(set(sizes.values())) == 1, "sha256_vendored": h_v, "sha256_original": h_o,
               "vendored_eq_original": h_v == h_o, "listed_in_exp22_input_hashes": h_v in flat,
               "units_json_mentions_task": named, "mean": float(n.mean()), "min": float(n.min()),
               "max": float(n.max()), "fro": float(np.linalg.norm(n.astype(np.float64)))}
        ok_all &= rec["aligned"] and rec["vendored_eq_original"]
        out[t] = rec
    out["units_json_keys"] = list(units.keys())[:20] if isinstance(units, dict) else None
    out["exp22_outliers"] = {t: units.get("outliers", {}).get(t, []) for t in K.D5_TASKS}
    out["outlier_rule_note"] = (
        "exp22 units.json LISTS outlier cells (T03, T05, T10: spec position 3 at blocks 12-16, n 36-106 against block "
        "medians 3-6; T2: position 3 at block 14 and position 87 -- a '0' digit token whose residual norm jumps to "
        "~10,290 at block 16, a massive activation -- at blocks 16-23 with n ~748, 82% of T2's U_abs energy; T1: none) "
        "but defines no exclusion rule, and exp22/exp29's ctx4.ban_unit loads the raw unit. This artifact therefore "
        "uses the raw unit, so D1 reproduces exp29's design; the T2 consequences for P_top / P_rest / P_shuf and U_bf* "
        "are reported (results/unit_profiles.json, README).")
    out["pass"] = ok_all
    return out


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("cpu_gates")
    res = {"G1": g1(), "G3": g3(), "G4": g4()}
    res["G2"] = g2()
    gp = RESULTS / "g5_hull_gate.json"
    res["G5"] = read_json(gp) if gp.exists() else {"pass": None, "note": "run src/s3_prices.py g5"}
    res["all_pass"] = all(v.get("pass") for v in res.values() if isinstance(v, dict))
    res["utc"] = K.utc_now()
    write_json(RESULTS / "cpu_gates.json", res)
    logger.info({k: (v.get("pass") if isinstance(v, dict) else v) for k, v in res.items()})


if __name__ == "__main__":
    main()
