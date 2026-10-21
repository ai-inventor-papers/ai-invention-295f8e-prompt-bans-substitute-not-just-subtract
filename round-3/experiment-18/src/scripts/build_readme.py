"""Assemble README.md from the skeleton and the result sections (tables filled from results/*.json)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import TASKS  # noqa: E402

lf = json.loads((ROOT / "results" / "longform.json").read_text())
rows = []
for k, v in lf.items():
    t, p, th, dt = k.split("|")
    D = TASKS[t]["default"]
    c, n = v["counts"], v["N"]
    alt = sum(x for l, x in c.items() if l in TASKS[t]["catalogue"] and l != D)
    rows.append(f"| {t} {p} {th.replace('think_', 'thinking ')} ({dt}) | {n} | {c.get(D, 0)} | {alt} | "
                f"{c.get('other', 0)} | {c.get('invalid', 0)} | {v['n_correct']} |")
think_bench = [k for k in lf if "think_on" in k and k.split("|")[0] in ("T03", "T04", "T06")]
if think_bench:
    parts = []
    for k in think_bench:
        v = lf[k]
        parts.append(f"{k.split('|')[0]} {k.split('|')[1]}: {v['counts']}")
    tb = ("- **Thinking on, bench tasks (N = 10 per prompt)**: " + "; ".join(parts) + ". Completion rate "
          + ", ".join(f"{lf[k]['thinking']['completion_rate']:.2f}" for k in think_bench) + ".")
else:
    tb = "- Thinking on for the bench tasks was not run (`results/not_run.json`)."
c = (ROOT / "scratch" / "readme_results_c.md").read_text().replace("__LF_TABLE__", "\n".join(rows)).replace(
    "__THINK_BENCH__", tb)
ab = (ROOT / "scratch" / "readme_results_ab.md").read_text()
det = (ROOT / "scratch" / "readme_details.md").read_text()
sk = (ROOT / "README.md").read_text() if "__RESULTS__" in (ROOT / "README.md").read_text() else \
    (ROOT / "scratch" / "readme_skeleton.md").read_text()
(ROOT / "scratch" / "readme_skeleton.md").write_text(sk)
out = sk.replace("__RESULTS__", ab + "\n" + c).replace("__DETAILS__", det)
(ROOT / "README.md").write_text(out)
print("README.md written", len(out))
