#!/usr/bin/env python3
"""CPU tests C1-C6 (results/tests_cpu.json) and the evaluation of the Stage 0 GPU tests U1-U8
(results/tests_gpu.json, predictions/stage3_flags.json: the identity shortcut is enabled only if U2 passes).
Usage: tests8.py cpu | gpu
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (E34, E35, E38, INPUTS, LABELS, PRED_DIR, RESULTS_DIR, SAMPLES, TEMPLATES, read_json,  # noqa: E402
                  read_jsonl, slot_ukey, u_stream, utc_now, write_json)
import predict8 as PR  # noqa: E402


# ------------------------------------------------------------------------------------------------ CPU
def c1_labeller() -> dict:
    """Labeller re-check: reference implementations of A3 (and B3/B6 when present) and agreement of the frozen
    labellers (through label7) with the stored labels of 20 prior programs per unit (exp35 B3/A3/B6 sweep rows,
    exp34 T10/T2/T03 twins, exp38 G3 T1 rows)."""
    import label7 as L7
    out: dict = {"references": {}, "agreement": {}}
    refdir = INPUTS / "iter5_exp25" / "newbench" / "A3_trapping_rain_water" / "references"
    rows = []
    for f in sorted(refdir.glob("*.py")):
        rows.append({"sid": f"ref|A3|{f.stem}", "unit": "A3", "text": "```python\n" + f.read_text() + "\n```",
                     "want": f.stem})
    for ud in ("B3", "B6"):
        for d in (INPUTS / "iter5_exp26").rglob(f"*{ud}*"):
            if d.is_dir() and (d / "references").exists():
                for f in sorted((d / "references").glob("*.py")):
                    rows.append({"sid": f"ref|{ud}|{f.stem}", "unit": ud,
                                 "text": "```python\n" + f.read_text() + "\n```", "want": f.stem})
    if rows:
        res = L7.label_rows([{k: r[k] for k in ("sid", "unit", "text")} for r in rows])
        for r, o in zip(rows, res):
            out["references"][r["sid"]] = {"want": r["want"], "got": o["label"], "passed": o["passed"],
                                           "ok": o["label"] == r["want"]}
    # agreement with stored labels of prior programs
    prior = []
    lab35 = {r["sid"]: r for r in read_jsonl(E35 / "data" / "labels.jsonl")}
    for r in read_jsonl(E35 / "data" / "samples_raw.jsonl"):
        if r.get("cell") == "T1.0_p1" and r["sid"] in lab35 and int(r["slot"]) < 24:
            prior.append({"sid": "p35|" + r["sid"], "unit": r["unit"], "text": r["text"],
                          "want": lab35[r["sid"]]["label"]})
    raw38 = {r["row_id"]: r for r in read_jsonl(E38 / "data" / "raw_g3.jsonl")}
    for r in read_jsonl(E38 / "data" / "labels.jsonl"):
        if r.get("row_id", "").startswith("g3|T1.0|topp1") and r["row_id"] in raw38 and len(prior) < 400:
            if int(raw38[r["row_id"]]["slot"]) < 4:
                prior.append({"sid": "p38|" + r["row_id"], "unit": "T1", "text": raw38[r["row_id"]]["text"],
                              "want": r["label"]})
    res = L7.label_rows([{k: r[k] for k in ("sid", "unit", "text")} for r in prior])
    by_unit: dict = {}
    for r, o in zip(prior, res):
        u = r["unit"] + ("(G)" if r["sid"].startswith("p38") else "")
        d = by_unit.setdefault(u, {"n": 0, "agree": 0, "disagreements": []})
        d["n"] += 1
        if o["label"] == r["want"]:
            d["agree"] += 1
        elif len(d["disagreements"]) < 5:
            d["disagreements"].append({"want": r["want"], "got": o["label"]})
    for u, d in by_unit.items():
        d["rate"] = d["agree"] / max(d["n"], 1)
    out["agreement"] = by_unit
    out["pass"] = all(v["ok"] for v in out["references"].values()) and all(d["rate"] >= 0.9 for d in by_unit.values())
    return out


def c2_predict() -> dict:
    sys.path.append(str(E35 / "src"))
    import predict as P35  # exp35 committed prediction functions
    u5, u8 = P35.u5_test(), P35.u8_test()
    z = np.random.default_rng(0).normal(size=500) * 3
    ids, p = PR.dist_topk(z, 1e6, 20)
    uni = bool(np.allclose(p, 1 / 20, atol=1e-4))
    # binary fork with margin m: composed minority prediction vs closed form
    m = 2.3
    V = 40
    zz = np.full(V, -1e4)
    zz[3], zz[7] = m, 0.0
    tm = {3: {"phat": np.array([1.0, 0.0]), "pfail": 0.0, "off_default": False, "prev": 0.0},
          7: {"phat": np.array([0.0, 1.0]), "pfail": 0.0, "off_default": True, "prev": 0.0}}
    resid = {"phat": np.array([0.5, 0.5]), "pfail": 0.0}
    errs = []
    for T in (0.5, 1.0, 2.0, 7.0):
        got = PR.compose_node(zz, T, tm, resid, None, k=2)["F"][1]
        errs.append(abs(got - PR.binary_closed_form(m, T) if hasattr(PR, "binary_closed_form") else
                        got - 1 / (1 + math.exp(m / T))))
    # two-token composition vs brute-force enumeration on a synthetic tree
    z1 = np.log(np.array([0.5, 0.3, 0.2] + [1e-12] * 7))
    z2 = np.log(np.array([0.1, 0.6, 0.3] + [1e-12] * 7))
    tm1 = {0: {"phat": np.array([1.0, 0.0]), "pfail": 0.0}, 2: {"phat": np.array([0.0, 1.0]), "pfail": 0.0}}
    tm2 = {0: {"phat": np.array([0.0, 1.0]), "pfail": 0.0}, 1: {"phat": np.array([1.0, 0.0]), "pfail": 0.0},
           2: {"phat": np.array([0.0, 1.0]), "pfail": 0.0}}
    sec = {1: {"z": z2, "tmap": tm2, "resid": resid}}
    T = 1.7
    got = PR.compose_node(z1, T, tm1, resid, sec, k=3)["F"]
    p1 = np.exp(z1[:3] / T) / np.exp(z1[:3] / T).sum()
    p2 = np.exp(z2[:3] / T) / np.exp(z2[:3] / T).sum()
    brute = p1[0] * np.array([1, 0]) + p1[2] * np.array([0, 1]) + p1[1] * (p2[0] * np.array([0, 1]) +
                                                                           p2[1] * np.array([1, 0]) +
                                                                           p2[2] * np.array([0, 1]))
    two = float(np.abs(got - brute).max())
    return {"u5": u5["pass"], "u8": u8["pass"], "topk_uniform_T_inf": uni, "binary_max_err": max(errs),
            "two_token_max_err": two, "pass": u5["pass"] and u8["pass"] and uni and max(errs) < 1e-9 and two < 1e-12}


def c3_stats() -> dict:
    toy = ["a"] * 4 + ["b"] * 3 + ["c"] * 2
    h_exact = PR.hill1_rarefied(toy, 5)
    h_brute = PR.hill1_bruteforce(toy, 5)
    # Newcombe (1998) paired example: a=1, b=3? use Table II style check against an independent implementation
    ex = [(12, 9, 2, 21), (10, 3, 1, 26), (5, 2, 0, 3)]
    nc = [PR.newcombe_paired(*e) for e in ex]
    sane = all(r["lo"] <= r["diff"] <= r["hi"] for r in nc)
    # hand computation of Newcombe's method 10 (Wilson limits, phi with the n/2 correction) for (12, 9, 2, 21):
    # p1 = 21/44, p2 = 14/44, Wilson (0.3375, 0.6207) / (0.2000, 0.4656), phi = 212 / sqrt(202860) = 0.4707
    # -> 0.1591 (0.0112, 0.2954)
    ref = nc[0]
    ref_ok = abs(ref["diff"] - 0.1591) < 1e-3 and abs(ref["lo"] - 0.0112) < 1e-3 and abs(ref["hi"] - 0.2954) < 1e-3
    p1 = PR.mae_noise_ceiling([np.array([0.6, 0.4])], draws=2000, seed=1)
    p2 = PR.mae_noise_ceiling([np.array([0.6, 0.4])], draws=2000, seed=1)
    return {"hill_exact": h_exact, "hill_brute": h_brute, "hill_match": abs(h_exact - h_brute) < 1e-9,
            "newcombe": nc, "newcombe_ref_example_a": ref_ok, "noise_ceiling_reproducible": p1 == p2,
            "pass": abs(h_exact - h_brute) < 1e-9 and sane and ref_ok and p1 == p2}


def c5_schedule() -> dict:
    """AdapT block-start detection (the device state machine re-implemented on token strings) on 5 programs."""
    from transformers import AutoTokenizer
    from cfg8 import QWEN_ID, QWEN_REV, model_path
    tok = AutoTokenizer.from_pretrained(model_path(QWEN_ID, QWEN_REV))
    progs = ["```python\ndef solve(n):\n    return n\n```",
             "```python\ndef solve(a, b):\n    if a:\n        return b\n    return a\n```",
             "```python\nimport heapq\n\ndef solve(x):\n    for i in range(x):\n        pass\n```",
             "```python\ndef solve(s):\n    while s:  \n        s -= 1\n    return s\n```",
             "```python\ndef solve(g):\n    # comment\n    def inner(v):\n        return v\n    return inner(g)\n```"]
    want = [["return"], ["if", "return"], ["for", "pass"], ["while", "s"], ["#", "return"]]
    ok = []
    got_all = []
    for prog, wnt in zip(progs, want):
        ids = tok.encode(prog, add_special_tokens=False)
        line_colon, pending, got = False, False, []
        for t in ids:
            s = tok.decode([t])
            if pending and s.strip():
                got.append(s.strip().split()[0] if s.strip() else s)
            b, a = s.split("\n")[0], s.split("\n")[-1]
            nl, nsb, nsa, ns = "\n" in s, b.strip() != "", a.strip() != "", s.strip() != ""
            cb, ca = b.rstrip(" \t").endswith(":"), a.rstrip(" \t").endswith(":")
            end_colon = cb if nsb else line_colon
            if nl:
                pend_new = (pending and not nsb) or end_colon
                if nsa:
                    pend_new = False
                line_colon = ca and nsa
            else:
                pend_new = pending and not ns
                if ns:
                    line_colon = cb
            pending = pend_new
        got_all.append(got)
        ok.append([g.lstrip("#") or "#" for g in got][:len(wnt)] == [w.lstrip("#") or "#" for w in wnt])
    rng_ok = int(np.random.default_rng(8_800_000 + 3).integers(64)) == int(np.random.default_rng(8_800_000 + 3)
                                                                           .integers(64))
    return {"adapt_block_starts": got_all, "want": want, "per_program_ok": ok, "rng_deterministic": rng_ok,
            "pass": all(ok) and rng_ok}


def c6_commit() -> dict:
    import commit8 as CM
    v = CM.verify()
    return {"verify": v["ok"], "tamper_detected": CM.tamper_test(), "pass": v["ok"] and CM.tamper_test()}


def u6_entropy() -> dict:
    z = torch.randn(4, 1000, dtype=torch.float64) * 4
    lsm = torch.log_softmax(z, -1)
    mine = -(lsm.exp() * lsm).nan_to_num().sum(-1)
    ref = torch.distributions.Categorical(logits=z).entropy()
    d = float((mine - ref).abs().max())
    return {"max_abs_diff": d, "pass": d < 1e-6}


def run_cpu() -> None:
    out = {"utc": utc_now()}
    for name, fn in (("C2_predict", c2_predict), ("C3_stats", c3_stats), ("C5_schedule", c5_schedule),
                     ("C6_commit", c6_commit), ("U6_entropy_formula", u6_entropy), ("C1_labeller", c1_labeller)):
        try:
            out[name] = fn()
        except Exception as e:  # noqa: BLE001 - a failing test is recorded, not hidden
            out[name] = {"pass": False, "error": f"{type(e).__name__}: {e}"}
        print(name, out[name].get("pass"), flush=True)
    write_json(RESULTS_DIR / "tests_cpu.json", out)


# ------------------------------------------------------------------------------------------------ GPU rows
def run_gpu() -> None:
    rows = read_jsonl(SAMPLES)
    labels = {r["sid"]: r for r in read_jsonl(LABELS)}
    twin = {(r["unit"], r["slot"]): r for r in rows if r["arm"] == "A0"}
    by_arm: dict = {}
    for r in rows:
        if r.get("stage") == "S0_test":
            by_arm.setdefault(r["arm"], []).append(r)
    out: dict = {"utc": utc_now()}

    def same(r):
        t = twin.get((r["unit"], r["slot"]))
        return t is not None and t["token_ids"] == r["token_ids"]
    for a in ("U1b1", "U1b8", "U2a"):
        rs = by_arm.get(a, [])
        out[a] = {"n": len(rs), "identical": sum(same(r) for r in rs)}
    u1 = by_arm.get("U1b1", []) + by_arm.get("U1b8", [])
    out["U1_pass"] = sum(same(r) for r in u1) >= 0.9 * max(len(u1), 1)
    # U2b / U3: dose 15 top-20 at n10 on 20 T10 slots
    rs = by_arm.get("U2b", [])
    unchanged, ident, rep_ok = 0, 0, 0
    detail = []
    for r in rs:
        t = twin.get(("T10", r["slot"]))
        u = u_stream(*slot_ukey("T10", r["slot"]))
        pred = PR.replay_token(t["dec_top_ids"], t["dec_top_z"], float(u[t["decision_pos"]]), 15.0, 20) \
            if t and t.get("dec_top_ids") else None
        own = PR.replay_token(r["dec_top_ids"], r["dec_top_z"], float(u[r["decision_pos"]]), 15.0, 20) \
            if r.get("dec_top_ids") else None
        rep_ok += int(pred == r["decision_token"])
        if t and r["decision_token"] == t["decision_token"]:
            unchanged += 1
            ident += int(r["token_ids"] == t["token_ids"])
        detail.append({"slot": r["slot"], "twin_tok": t["decision_token"] if t else None, "dosed_tok": r["decision_token"],
                       "replay_from_twin": pred, "replay_from_own_logits": own})
    out["U2b"] = {"n": len(rs), "unchanged_token": unchanged, "unchanged_identical": ident, "detail": detail}
    out["U2_pass"] = (out["U2a"]["identical"] >= 0.95 * max(out["U2a"]["n"], 1)) and \
        (unchanged == 0 or ident >= 0.95 * unchanged)
    out["U3"] = {"n": len(rs), "replay_match": rep_ok, "own_logits_match": sum(d["replay_from_own_logits"] ==
                                                                               d["dosed_tok"] for d in detail)}
    out["U3_pass"] = rep_ok >= 0.95 * max(len(rs), 1)
    # U4: top-20 truncation at T = 100 from captured logits (simulated draws with the replay transform)
    t0 = next((r for r in rows if r["arm"] == "A0" and r["unit"] == "T10" and r.get("dec_top_ids")), None)
    if t0:
        rng = np.random.default_rng(4)
        draws = [PR.replay_token(t0["dec_top_ids"], t0["dec_top_z"], float(x), 100.0, 20) for x in rng.random(2000)]
        top20 = set(t0["dec_top_ids"][:20])
        cnt = Counter(draws)
        obs = np.array([cnt.get(t, 0) for t in t0["dec_top_ids"][:20]])
        z20 = np.array(t0["dec_top_z"][:20]) / 100.0
        exp = np.exp(z20 - z20.max())
        exp = exp / exp.sum() * 2000
        chi = stats.chisquare(obs, exp)
        out["U4"] = {"outside_top20": sum(1 for d in draws if d not in top20), "chi2_p": float(chi.pvalue)}
        out["U4_pass"] = out["U4"]["outside_top20"] == 0 and chi.pvalue > 0.01
    # U5: decision index on canonical-opening twin slots
    u5 = {}
    for u in ("T10", "T1", "B3", "A3", "B6", "G"):
        tw = [r for r in rows if r["arm"] == "A0" and r["unit"] == u]
        import units8 as U8
        nds = U8.nodes(u)
        ok = [r["decision_pos"] == nds[r["decision_node"]]["pos"] for r in tw if r.get("reached_decision")]
        u5[u] = {"reached": len(ok), "n": len(tw), "pos_ok": sum(ok)}
    out["U5"] = u5
    out["U5_pass"] = all(v["pos_ok"] == v["reached"] for v in u5.values())
    # U7 / U8 (labels)
    for a, want in (("U7dfs", "dfs"), ("U7find", "union_find"), ("U8visited", "dfs"), ("U8queue", "bfs")):
        rs = by_arm.get(a, [])
        labs = [labels.get(r["sid"], {}).get("label") for r in rs]
        passed = [labels.get(r["sid"], {}).get("passed") for r in rs]
        out[a] = {"n": len(rs), "labels": dict(Counter(labs)), "n_want": sum(l == want for l in labs),
                  "n_pass": sum(bool(p) for p in passed)}
    out["U7_pass"] = out["U7dfs"]["n_want"] >= 9 and out["U7find"]["n_want"] >= 9
    out["U8_pass"] = (out["U8visited"]["n_want"] >= 4 and out["U8queue"]["n_want"] >= 4 and
                      out["U8queue"]["n_pass"] <= 1) if out["U8visited"]["n"] else None
    write_json(RESULTS_DIR / "tests_gpu.json", out)
    flags_p = PRED_DIR / "stage3_flags.json"
    flags = read_json(flags_p) if flags_p.exists() else {}
    flags["identity_shortcut"] = bool(out["U2_pass"])
    flags["utc_tests"] = utc_now()
    write_json(flags_p, flags)
    print(json.dumps({k: v for k, v in out.items() if k.endswith("pass")}, indent=1, default=str))


if __name__ == "__main__":
    run_cpu() if sys.argv[1] == "cpu" else run_gpu()
