"""Applied once the bench thinking-on job has written its rows: not_run.json, deviation D14, README bullet."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = [json.loads(l) for l in (ROOT / "data" / "samples_longform.jsonl").open() if '"thinking": true' in l]
bench = [r for r in rows if r["task"] in ("T03", "T04", "T06")]
nr = json.loads((ROOT / "results" / "not_run.json").read_text())
nr = [x for x in nr if not x["item"].startswith("thinking-on long-form on bench tasks")]
for x in nr:
    if x["item"].startswith("thinking-on extension of T1/T2"):
        x["reason"] = ("the extension process (T1/T2 indices 10-24 together with the bench cells) was stopped at 22:36 "
                       "when the KV cache saturated; the bench cells were re-launched alone at 23:07 and completed "
                       f"({len(bench)} runs); the T1/T2 extension was not re-launched (time)")
(ROOT / "results" / "not_run.json").write_text(json.dumps(nr, indent=1))
p = ROOT / "method.py"
s = p.read_text()
old = s[s.index('    {"id": "D14"'):s.index('    {"id": "D15"')]
new = ('    {"id": "D14", "what": "Thinking-on: the floor (T1/T2, N=10 per prompt) ran; the first extension process (T1/T2 '
       'to N=25 plus bench T03/T04/T06 at N=10) was stopped after ~6 min when the KV cache saturated and nothing of it '
       'was written; the bench cells (N=10 per prompt) were re-launched alone after the thinking-off jobs ended and '
       'completed; the T1/T2 extension to N=25 was not re-run.",\n'
       '     "consequence": "thinking-on cells have N=10 per prompt (upper bound on the novel rate ~26% per cell)."},\n')
s = s.replace(old, new)
p.write_text(s)
d = ROOT / "scratch" / "readme_details.md"
t = d.read_text()
old2 = """  - Thinking-on for the bench tasks and the T1/T2 extension to N = 25. The never-drop floor ran: T1/T2 thinking-on,
    N = 10 per prompt."""
new2 = """  - The T1/T2 thinking-on extension to N = 25. The never-drop floor ran (T1/T2 thinking-on, N = 10 per prompt), and
    the bench thinking-on cells (T03/T04/T06, N = 10 per prompt) ran after a KV-cache-driven restart."""
assert old2 in t
d.write_text(t.replace(old2, new2))
print("post-bench updates applied;", len(bench), "bench thinking rows")
