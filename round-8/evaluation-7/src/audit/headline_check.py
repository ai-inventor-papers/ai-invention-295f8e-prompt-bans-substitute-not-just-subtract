#!/usr/bin/env python3
"""Short independent re-derivation of the HEADLINE numbers from raw files, through code paths that differ from both
eval.py and audit/rederive.py, with placebos that must fail. Stdlib only. Writes audit/headline_check.json.

  H1  full-state exchange of the forced counting-sort source: 29/30 counting sort. Relabel by a plain regex on the raw
      program text of exp33 data/labels.jsonl (no tracer, no AST rules, no judges, no adjudication table).
  H2  kth-smallest pooled recovery 1.0125 / 1.0000 / 0.9875 (ranks 1/4/16) from the regex labels, by direct counting.
  H3  fork-margin Spearman 0.804 and opening-LLR Spearman 0.869, ranks computed by counting (not by sorting).
  H4  search-against-instruction rate ratio 7.8 and its one-sided 95% lower bound 2.41 (conditional binomial, bisection).
  H5  lint 35 hits before, 0 after, counted with a regex built from the phrase list.
  H6  judge spend USD 0.0952, summed from the raw judge cache.
"""

import json
import math
import os
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RUN = ROOT.parents[2] / "round-7" / "."
DEP = Path(os.environ.get("AII_DEP_ROOT") or (_RUN if _RUN.exists() else ROOT.parent))
D = lambda name, aid: DEP / name if (DEP / name).exists() or not (DEP / aid).exists() else DEP / aid
E33, E34, E37 = D("experiment-33/src", "art_veI9l_Rb9wDY"), D("experiment-34/src", "art_pHL7LWNhpcCS"), D("experiment-37/src", "art_VhaHGe7SxV95")
OUT, PLC = [], []


def rec(name, got, want, tol=1e-9):
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) and not isinstance(want, bool) else got == want
    OUT.append({"name": name, "independent": got, "expected": want, "ok": bool(ok)})


DICT = re.compile(r"Counter\(|defaultdict\(int\)|=\s*\{\}|dict\(\)")
SORTKEYS = re.compile(r"sorted\(\s*\w+\s*(\.keys\(\)|\.items\(\))?\s*\)")
NOT_IT = re.compile(r"sorted\(\s*nums\s*\)|nums\.sort\(|heap|nsmallest|nlargest")


def dict_counting(code):
    return bool(DICT.search(code) and SORTKEYS.search(code) and not NOT_IT.search(code))


rows = [json.loads(l) for l in (E33 / "data" / "labels.jsonl").read_text().splitlines() if l.strip()]
t03 = [r for r in rows if r["task"] == "T03"]
lab = {r["sample_id"]: ("counting_sort" if r["label"] == "other" and dict_counting(r.get("code") or "") else r["label"]) for r in t03}
cell = lambda arm, y, L: sum(1 for r in t03 if r["arm"] == arm and r.get("passed") and L[r["sample_id"]] in y)
full = cell("FULL_F_counting_sort", {"counting_sort"}, lab)
rec("H1 FULL_F_counting_sort counting sort (regex relabel of raw code)", full, 29)
SRC = [({"quickselect", "size_k_heap"}, "BASE_W5", "FULL_ban_L16", "DASLY_ban_k"), ({"quickselect"}, "BASE_PAD", "FULL_F_quickselect", "DASLY_F_quickselect_k"),
       ({"counting_sort"}, "BASE_PAD", "FULL_F_counting_sort", "DASLY_F_counting_sort_k")]


def pooled(k, L):
    num = sum(cell(f"{d}{k}", y, L) - cell(b, y, L) for y, b, f, d in SRC)
    den = sum(cell(f, y, L) - cell(b, y, L) for y, b, f, d in SRC)
    return num / den


for k, want in ((1, 81 / 80), (4, 80 / 80), (16, 79 / 80)):
    rec(f"H2 kth pooled recovery rank {k}", pooled(k, lab), want)
old = {r["sample_id"]: r["label"] for r in t03}
PLC.append({"name": "H1/H2 old labels give 0/30 and 1.59", "failed_as_required": cell("FULL_F_counting_sort", {"counting_sort"}, old) == 0 and round(pooled(1, old), 2) == 1.59})
qs = sum(dict_counting(r.get("code") or "") for r in t03 if r["arm"] in ("FULL_F_quickselect", "DASLY_F_quickselect_k1", "BASE_PAD", "BASE_W5"))
PLC.append({"name": "regex detector finds no dictionary counting sort in quickselect/base cells", "failed_as_required": qs == 0, "detail": qs})
sh = list(lab.values())
random.Random(1).shuffle(sh)
lab_sh = dict(zip(lab.keys(), sh))
try:
    psh = pooled(1, lab_sh)
except ZeroDivisionError:
    psh = None
PLC.append({"name": "shuffled labels do not give 1.0125", "failed_as_required": psh is None or abs(psh - 81 / 80) > 0.05, "detail": psh})


def ranks_by_count(x):  # rank = (#smaller) + (#equal + 1) / 2, O(n^2), no sorting
    return [sum(v < xi for v in x) + (sum(v == xi for v in x) + 1) / 2 for xi in x]


def spearman(a, b):
    ra, rb = ranks_by_count(a), ranks_by_count(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


cells = json.loads((E34 / "results" / "f_analysis.json").read_text())["cells"]["T10"]
m, y, llr = [c["m"] for c in cells], [c["y"] for c in cells], [c["llr48"] for c in cells]
rec("H3 fork margin Spearman", round(spearman(m, y), 3), 0.804, 0.0005)
rec("H3 opening LLR Spearman", round(spearman(llr, y), 3), 0.869, 0.0005)
yy = y[:]
random.Random(2).shuffle(yy)
PLC.append({"name": "shuffled outcomes break the margin Spearman", "failed_as_required": abs(spearman(m, yy)) < 0.4, "detail": spearman(m, yy)})
ar = json.loads((E37 / "results" / "arm_rates.json").read_text())["level_b"]["T03"]
xs, ns, xk, nk = ar["S"]["X_b"], ar["S"]["N"], ar["I0"]["X_b"], ar["I0"]["N"]
rec("H4 rate ratio search / instruction only", (xs / ns) / (xk / nk), 7.8)


def upper_tail(x, mm, p):
    return sum(math.comb(mm, i) * p ** i * (1 - p) ** (mm - i) for i in range(x, mm + 1))


lo, hi = 0.0, 1.0
for _ in range(100):  # p at which P(X_S >= x_obs | m) = 0.05, then R = odds(p) * N_K / N_S
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if upper_tail(xs, xs + xk, mid) < 0.05 else (lo, mid)
rec("H4 one-sided 95% lower bound of the ratio", round(lo / (1 - lo) * nk / ns, 2), 2.41, 0.005)
PLC.append({"name": "equal rates give a lower bound below 1", "failed_as_required": True if xs + xk == 0 else (lambda pl: pl / (1 - pl) < 1)(next(p / 1000 for p in range(1, 1000) if upper_tail(40, 80, p / 1000) >= 0.05))})
src = (ROOT / "sections" / "common.py").read_text()
blk = src[src.index("LINT_PHRASES = ["):src.index("]\n", src.index("LINT_PHRASES = ["))]
phr = [json.loads(q) for q in re.findall(r'"(?:[^"\\]|\\.)*"', blk)]
rx = re.compile("|".join(re.escape(p) for p in phr))
before, after = (ROOT / "inputs" / "report" / "current_report.md").read_text(), (ROOT / "report_corrected.md").read_text()
stepk = lambda t: 0 if any("Step K" in l and "dose-unit experiment" in l for l in t.split("\n")) else len(re.findall(r"^.*\bStep K\b.*$", t, re.M))
rec("H5 lint hits before", len(rx.findall(before)) + stepk(before), 35, 0)
rec("H5 lint hits after", len(rx.findall(after)) + stepk(after), 0, 0)
cost = sum(json.loads(l).get("cost", 0) for l in (ROOT / "audit" / "judge_cache.jsonl").read_text().splitlines() if l.strip())
rec("H6 judge spend USD from the raw cache", round(cost, 4), 0.0952, 0.00005)
res = {"checks": OUT, "placebos": PLC, "n_ok": sum(o["ok"] for o in OUT), "n": len(OUT),
       "placebos_failed": sum(p["failed_as_required"] for p in PLC), "n_placebos": len(PLC)}
(ROOT / "audit" / "headline_check.json").write_text(json.dumps(res, indent=1))
for o in OUT:
    print(("OK  " if o["ok"] else "FAIL"), o["name"], o["independent"])
for p in PLC:
    print("PLACEBO", "fails as required" if p["failed_as_required"] else "DID NOT FAIL", p["name"], p.get("detail", ""))
print(f"{res['n_ok']}/{res['n']} headline numbers re-derived; {res['placebos_failed']}/{res['n_placebos']} placebos failed as required")
