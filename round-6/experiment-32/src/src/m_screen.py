#!/usr/bin/env python3
"""Plan 0.7: the M-screen from iteration-5 data on disk only (no new sample is read). For the 15 iteration-5 units
(A1-A5, A7-A9 from exp25 pooled_inputs.json; B1-B7 from exp26 pooled_inputs.json and its labelled rows) compute the
candidates beta, replacement class, runtime merit, twin modal share (N 50) and K, and their Spearman rho with the
iteration-5 E_u. B units: E_u recomputed under the iteration-6 escape definition (share = correct S-labelled / all
programs, p0 = (k_twin + 0.5)/(n_twin + 1), confirmation at N 30) from the vendored labelled rows; A units: the
iteration-5 E_u as published (their per-row correctness is not in the pooled file; flagged). Sign rule: the sign of
the screen rho unless |rho| < 0.1 or no screen value (fork margin), then the mechanism sign. Writes and commits
predictions/m_signs.json."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scipy.stats import binomtest, spearmanr  # noqa: E402

from cfg5 import PRED_DIR, UNITS_DIR, VENDOR, read_json, read_jsonl, setup_logging, utc_now, write_json  # noqa: E402

MECH = {"beta": "+", "replacement_class": "-", "runtime_merit": "+", "twin_modal_share": "-", "K": "+",
        "fork_margin": "-"}
LIB = {"B1": ["arithmetic_sum"], "B2": ["set_sum_identity"], "B3": [], "B4": ["library_isqrt", "float_sqrt"],
       "B5": ["itertools_combinations"], "B6": ["sort_compare"], "B7": []}


def e_u_iter6_B(u: str, rows: list[dict], default: str, cat: list[str]) -> float | None:
    S = set(cat) - {default}
    tw = [r for r in rows if r["unit"] == u and r["arm"] == "TWIN" and r["model_tag"] == "instruct" and r["slot"] < 10]
    if not tw:
        return None
    n_tw = len(tw)
    k_tw = sum(1 for r in tw if r.get("passed") and r.get("label") in S)
    pass_tw = sum(1 for r in tw if r.get("passed")) / n_tw
    off_tw = k_tw / n_tw
    p0 = (k_tw + 0.5) / (n_tw + 1)
    by = defaultdict(list)
    for r in rows:
        if r["unit"] == u and r["arm"].startswith("ESC_"):
            by[r["arm"]].append(r)
    alphas = defaultdict(lambda: [0, 0])
    for arm, rr in by.items():
        a = arm.rsplit("_a", 1)[1]
        s1 = [r for r in rr if r["slot"] in (0, 1)]
        s30 = [r for r in rr if r["slot"] in range(6)]
        alphas[a][1] += 1
        if len(s1) < 10:
            continue
        sh1 = sum(1 for r in s1 if r.get("passed") and r.get("label") in S) / len(s1)
        ps1 = sum(1 for r in s1 if r.get("passed")) / len(s1)
        if not (sh1 >= off_tw + 0.2 - 1e-12 and ps1 >= 0.8 * pass_tw - 1e-12) or len(s30) < 30:
            continue
        k = sum(1 for r in s30 if r.get("passed") and r.get("label") in S)
        ps30 = sum(1 for r in s30 if r.get("passed")) / len(s30)
        p = binomtest(k, len(s30), p0, alternative="greater").pvalue
        if p < 0.05 and ps30 >= 0.8 * pass_tw - 1e-12:
            alphas[a][0] += 1
    if not alphas:
        return None
    return sum(c / 8 for c, _ in alphas.values()) / len(alphas)


def runtime_merit(u: str, d: str, cat: list[str]) -> float | None:
    p = UNITS_DIR / u / "tests.jsonl"
    if not p.exists():
        return None
    tot = Counter()
    for l in p.read_text().splitlines():
        c = json.loads(l)
        if c.get("kind") == "stress" and c.get("ref_times"):
            for m, t in c["ref_times"].items():
                tot[m] += float(t)
    alts = [tot[a] for a in cat if a != d and tot.get(a)]
    if d not in tot or not alts:
        return None
    return math.log2(tot[d] / min(alts))


def main() -> None:
    setup_logging("m_screen")
    rows_B = read_jsonl(VENDOR / "exp26" / "samples_B_nocode.jsonl")
    p26 = read_json(VENDOR / "exp26" / "pooled_inputs.json")["records"]
    p25 = read_json(VENDOR / "exp25" / "pooled_inputs.json")["units"]
    units = []
    for r in p26:
        u = r["unit_id"]
        if u not in LIB:
            continue
        cat = r["unit_facts"]["catalogue"]
        d = r["unit_facts"]["default"]
        twc = r["twin"]["correct_composition"]
        ru = r["base"]["r_u"]
        units.append({"unit": u, "default": d, "K": len(cat), "beta": r["base"]["beta_u"],
                      "replacement_class": int(ru in LIB[u] or twc.get(ru, 0) > 0),
                      "runtime_merit": runtime_merit(u, d, cat),
                      "twin_modal_share": twc.get(d, 0) / max(sum(twc.values()), 1),
                      "E_u_iter5": r["outcomes"]["E_u"], "E_u": e_u_iter6_B(u, rows_B, d, cat),
                      "E_u_source": "iteration-6 definition recomputed from vendored labelled rows"})
    for r in p25:
        u = r["unit_id"]
        if u not in ("A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9"):
            continue
        cat = r["catalogue"]
        d = r["default"]
        twc = r["twin"]["comp_correct"]
        ru = r["base"].get("r")
        lib = [m for m in cat if "library" in m or "builtin" in m]
        cells = r["escape"]["cells"]
        E = {}
        for c in cells:
            E.setdefault(c["alpha"], []).append(bool(c.get("confirmed")))
        e_u = sum(sum(v) / 8 for v in E.values()) / len(E) if E else None
        units.append({"unit": u, "default": d, "K": len(cat), "beta": r["base"].get("beta"),
                      "replacement_class": int((ru in lib) or twc.get(ru, 0) > 0), "runtime_merit": None,
                      "twin_modal_share": twc.get(d, 0) / max(sum(twc.values()), 1), "E_u_iter5": e_u, "E_u": e_u,
                      "E_u_source": "iteration-5 published cells (per-row correctness not in the pooled file)"})
    res = {"utc": utc_now(), "units": units, "screen_rho": {}, "signs": {}, "rule": __doc__}
    for c in ("beta", "replacement_class", "runtime_merit", "twin_modal_share", "K"):
        pairs = [(x[c], x["E_u"]) for x in units if x.get(c) is not None and x.get("E_u") is not None]
        rho = None
        if len(pairs) >= 3 and len({a for a, _ in pairs}) > 1 and len({b for _, b in pairs}) > 1:
            rho = float(spearmanr([a for a, _ in pairs], [b for _, b in pairs]).statistic)
        res["screen_rho"][c] = {"rho": rho, "n": len(pairs)}
        res["signs"][c] = MECH[c] if (rho is None or abs(rho) < 0.1) else ("+" if rho > 0 else "-")
    res["signs"]["fork_margin"] = MECH["fork_margin"]
    res["mechanism_signs"] = MECH
    p = PRED_DIR / "m_signs.json"
    write_json(p, res)
    print(json.dumps({"screen_rho": res["screen_rho"], "signs": res["signs"]}, indent=1))


if __name__ == "__main__":
    main()
