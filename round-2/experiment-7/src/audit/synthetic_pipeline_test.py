#!/usr/bin/env python3
"""End-to-end test of the C1 pipeline (CellArrays -> rows -> bootstrap -> nulls -> branch) on synthetic TaskData
with a planted LADDER structure (every ban moves mass along the same external profile u) and with a planted
X-SPECIFIC structure (each ban adds a row-specific profile orthogonal to u, equal to its prime-and-veto profile)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from c1 import RAND_NAMES, needed_conds, run_c1  # noqa: E402
from config import MODES, RESULTS, SHAMS, TASKS, WS, write_json  # noqa: E402
from frlp import TaskData  # noqa: E402


def fake_task(t: str, kind: str, rng: np.random.Generator) -> TaskData:
    js = MODES[t]
    rows = []
    for j in js:
        for r in range(20):
            rows.append({"prog_id": f"{t}|{j}|{r}", "j": j, "half": "h1" if r % 2 == 0 else "h2", "passed": True,
                         "paraphrase_id": r % 10, "family": "plain", "rank": r, "m_j": 20})
    progs = pd.DataFrame(rows).set_index("prog_id")
    u = rng.normal(size=len(js))
    spec = {B: rng.normal(size=len(js)) for B in js}
    conds, _virt = needed_conds(t)
    base_level = rng.normal(size=len(js))
    L = {}
    for c in conds + [f"forced|{j}|plain|k{k}" for j in js for k in range(10)]:
        parts = c.split("|")
        shift = np.zeros(len(js))
        if parts[0] in ("ban", "mention") and parts[1] in js:
            B = parts[1]
            sgn = 1.0 if parts[0] == "ban" else 0.5
            shift = (1.5 * u if kind == "ladder" else 1.5 * spec[B]) * sgn
            shift[js.index(B)] -= 3.0
        elif parts[0] == "ban" and parts[1] == "nonce":
            shift = 1.0 * u
        elif parts[0] == "edit" or c == "novelty":
            shift = 1.0 * u
        vals = {}
        for pid, r in progs.iterrows():
            k = js.index(r["j"])
            vals[pid] = -100 + base_level[k] + shift[k] + 0.3 * rng.normal()
        L[("edit|" if c.startswith("edit|") else "primary|") + c] = vals
    df = pd.DataFrame(L).T
    td = TaskData(task=t, progs=progs, yields={j: 1.0 for j in js}, yields_pass={j: 1.0 for j in js},
                  measurable=list(js))
    td.L = {"total": df, "body": df, "cum256": df}
    lq = pd.Series({pid: -100.0 for pid in progs.index})
    td.lq = {f"{d}|{c}": lq for d in ("mixture", "single", "single_raw", "mixture_raw") for c in ("total", "body", "cum256")}
    return td


def main() -> None:
    out = {}
    for kind in ("ladder", "xspecific"):
        rng = np.random.default_rng(1)
        tds = {t: fake_task(t, kind, rng) for t in TASKS}
        res = run_c1(tds, "primary", "primary", "neutral", n_boot=60, n_perm=3000)
        out[kind] = {"pooled_share": res["pooled"]["share_point"]["SHARE"], "pooled_ci": res["pooled"]["bootstrap"]["SHARE_ci"],
                     "branch": res["pooled"]["branch"], "aim": res.get("aim_prime_veto"),
                     "ladder_exists": {t: res["tasks"][t]["ladder_exists"]["exists"] for t in TASKS},
                     "task_branches": {t: res["tasks"][t]["branch"] for t in TASKS}}
        print(kind, out[kind])
    out["pass"] = bool(out["ladder"]["branch"] == "LADDER" and out["xspecific"]["branch"] in
                       ("SUBSTITUTION", "X-SPECIFIC-UNAIMED"))
    write_json(RESULTS / "synthetic_pipeline_test.json", out)
    print("PASS" if out["pass"] else "FAIL")


if __name__ == "__main__":
    main()
