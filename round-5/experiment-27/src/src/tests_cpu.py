#!/usr/bin/env python3
"""CPU unit tests (testing plan): prompt rendering, parsers, sampler maths, KL, f_off / bisection, hull, hash chain.
-> results/tests_cpu.json"""

from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, RESULTS_DIR, ROOT, read_jsonl, sha256_file, sha256_text, write_json  # noqa: E402


def t_prompts() -> dict:
    from prompts5 import load_prompts, load_tokenizer, render_history

    pr = load_prompts()
    by = defaultdict(set)
    for (t, w, k), r in pr.items():
        by[t].add(json.dumps(r["ids"][r["p1"]:]))
    tok = load_tokenizer()
    r = pr[("T03", "W1", "psl")]
    hist = [{"role": "user", "content": r["user_text"]}, {"role": "assistant", "content": "1. first\n2. second"},
            {"role": "user", "content": "Step 2 of 3: go."}]
    ok_hist = True
    try:
        render_history(tok, hist)
    except AssertionError:
        ok_hist = False
    ifg = [v for (t, w, k), v in pr.items() if k == "ifg"]
    return {"spec_ids_identical_across_kinds": all(len(v) == 1 for v in by.values()), "n_tasks": len(by),
            "multi_turn_verbatim": ok_hist, "forced_intent_ids_present": all(v.get("forced_ids") for v in ifg)}


def t_sampler() -> dict:
    from engine5 import kl_rows, kl_scaled, step_probs5
    from engine_v4 import _inverse_cdf

    g = torch.Generator().manual_seed(0)
    same = 0
    n = 0
    for _ in range(10):
        L = torch.randn(1000, 500, generator=g, dtype=torch.float64) * 3
        u = torch.rand(1000, generator=g, dtype=torch.float64)
        ones = torch.ones(1000, 1, dtype=torch.float64)
        p_new = step_probs5(L, ones, torch.zeros(1000, dtype=torch.long), torch.ones(1000, dtype=torch.float64),
                            False, False)
        p_old = torch.softmax(L, dim=-1)
        same += int((_inverse_cdf(p_new, u) == _inverse_cdf(p_old, u)).sum())
        n += 1000
    # top-k and top-p masks vs brute-force sorted references
    L = torch.randn(200, 300, generator=g, dtype=torch.float64) * 2
    ones = torch.ones(200, 1, dtype=torch.float64)
    pk = step_probs5(L, ones, torch.full((200,), 10, dtype=torch.long), torch.ones(200, dtype=torch.float64), True, False)
    ok_k = all(int((pk[i] > 0).sum()) == 10 and set(torch.nonzero(pk[i]).flatten().tolist()) ==
               set(torch.topk(L[i], 10).indices.tolist()) for i in range(200))
    pp = step_probs5(L, ones, torch.zeros(200, dtype=torch.long), torch.full((200,), 0.9, dtype=torch.float64), False, True)
    ok_p = True
    for i in range(200):
        p = torch.softmax(L[i], -1)
        sp, si = p.sort(descending=True)
        c = sp.cumsum(0)
        m = int((c < 0.9).sum()) + 1
        if set(si[:m].tolist()) != set(torch.nonzero(pp[i]).flatten().tolist()):
            ok_p = False
    # KL vs scipy
    from scipy.stats import entropy
    a = torch.log_softmax(torch.randn(50, 400, generator=g, dtype=torch.float64), -1)
    b = torch.log_softmax(torch.randn(50, 400, generator=g, dtype=torch.float64), -1)
    k1 = kl_rows(a.float(), b.float()).numpy()
    k2 = np.array([entropy(np.exp(a[i].float().double().numpy()), np.exp(b[i].float().double().numpy())) for i in range(50)])
    kl_ok = float(np.max(np.abs(k1 - k2))) < 1e-6
    # f_off monotone for T > 1, bisection hits a known target
    z = torch.log_softmax(torch.randn(20, 600, generator=g) * 3, -1)
    Ts = [1.0, 1.2, 1.5, 2.0, 3.0, 4.0]
    fo = [float(kl_scaled(z, T).mean()) for T in Ts]
    mono = all(fo[i] < fo[i + 1] for i in range(len(fo) - 1))
    target = float(kl_scaled(z, 1.77).mean())
    lo, hi = 1.0, 4.0
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if float(kl_scaled(z, mid).mean()) < target:
            lo = mid
        else:
            hi = mid
    T_hat = math.sqrt(lo * hi)
    return {"inverse_cdf_identity": f"{same}/{n}", "topk_mask_ok": ok_k, "topp_mask_ok": ok_p,
            "kl_matches_scipy_1e-6": kl_ok, "f_off_monotone": mono, "bisection_T_hat": T_hat,
            "bisection_ok": abs(T_hat / 1.77 - 1) < 0.01}


def t_hull() -> dict:
    from hull_full import hull_prices_full, unit_tests

    res = unit_tests()
    res["hull_exp20_verbatim"] = sha256_file(ROOT / "src" / "hull_exp20.py") == sha256_file(INPUTS / "exp20" / "src" / "hull.py")
    rows = [r for r in read_jsonl(INPUTS / "exp19" / "data" / "samples.jsonl") if r.get("task") == "T03"]
    by = defaultdict(list)
    for r in rows:
        by[r["arm"]].append(r)
    out = {}
    for arms in (["TWIN", "PN_a0.5", "PN_a1", "PN_a2", "PN_a4"], ["TWIN", "PN_a0.5", "PN_a1", "PN_a2"]):
        st = [{"arm": a, "correct_labels": [r["label"] for r in by[a] if r.get("passed")],
               "pass": sum(bool(r.get("passed")) for r in by[a]) / len(by[a])} for a in arms if by.get(a)]
        h = hull_prices_full(st, n_draws=1000, seed=0, step=0.05, max_nonzero=3, refine=False)
        out["+".join(arms)] = h["H5"]
    res["exp19_T03_PN_H5_rederived"] = out
    res["exp19_T03_PN_H5_reported"] = 2.72
    res["exp19_T03_within_0.03"] = any(abs(v - 2.72) <= 0.03 for v in out.values())
    return res


def t_chain() -> dict:
    from commit import verify
    import commit as CM

    v = verify()
    tmp = Path(tempfile.mkdtemp())
    log2 = tmp / "commitments.log"
    shutil.copy(ROOT / "commitments.log", log2)
    lines = log2.read_text().splitlines()
    parts = lines[1].split()
    parts[2] = ("0" if parts[2][0] != "0" else "1") + parts[2][1:]
    lines[1] = " ".join(parts)
    log2.write_text("\n".join(lines) + "\n")
    old = CM.LOG
    CM.LOG = log2
    try:
        vt = verify()
    finally:
        CM.LOG = old
        shutil.rmtree(tmp)
    return {"chain_breaks": v["chain_breaks"], "n_lines": v["n_lines"], "tampered_detected": vt["chain_breaks"] > 0}


if __name__ == "__main__":
    from parsers import synthetic_tests

    res = {"prompts": t_prompts(), "parsers": synthetic_tests(), "sampler": t_sampler(), "hull": t_hull(),
           "chain": t_chain()}
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    print(json.dumps(res, indent=1, default=str))
