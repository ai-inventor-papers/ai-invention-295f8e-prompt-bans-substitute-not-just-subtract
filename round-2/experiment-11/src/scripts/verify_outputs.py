#!/usr/bin/env python3
"""Independent output check (stdlib only, no bench imports):
1. recount every pilot count, modal share, presence and collapse flag from data/samples_pilot.jsonl and compare with
   method_out.json;
2. recompute every per-file sha256 in bench/commitment.json from the files on disk and walk the commitments.log
   hash chain;
3. re-run the no-ban audit over logs/prompts_rendered.jsonl.
Exit code 0 only if everything matches.
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAN = re.compile(r"(?i)\b(do not|don't|must not|never|without using|avoid|instead of|not allowed|forbidden|banned?|"
                 r"prohibit\w*|zorblax|novel|unusual|creative|unconventional)\b")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    problems = []
    mo = json.loads((ROOT / "method_out.json").read_text())
    cand = {e["metadata_task"]: e for e in mo["datasets"][0]["examples"]}
    rows = [json.loads(l) for l in (ROOT / "data" / "samples_pilot.jsonl").open()]
    for t, e in cand.items():
        labs = [r["label"] for r in rows if r["task"] == t]
        att = [x for x in labs if x != "invalid"]
        c = Counter(att)
        mk = c.most_common(1)[0][1] if c else 0
        sec = c.most_common(2)[1][1] if len(c) > 1 else 0
        checks = {"metadata_pilot_counts": dict(Counter(labs)), "metadata_n_attempted": len(att),
                  "metadata_modal_share": mk / max(len(att), 1), "metadata_presence_flag": sec / max(len(att), 1) >= 0.10,
                  "metadata_collapse_flag": mk / max(len(att), 1) >= 0.90}
        for k, v in checks.items():
            if e[k] != v:
                problems.append(f"recount {t} {k}: {e[k]} != {v}")
    com = json.loads((ROOT / "bench" / "commitment.json").read_text())
    tid = {e["metadata_task"]: e["metadata_task_id"] for e in cand.values()}
    for t, v in com["tasks"].items():
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            if sha(ROOT / "bench" / tid[t] / f) != h:
                problems.append(f"hash mismatch {t}:{f}")
    prev = "0" * 64
    for line in (ROOT / "commitments.log").read_text().splitlines():
        if json.loads(line)["prev_line_sha256"] != prev:
            problems.append("commitments.log hash chain broken")
        prev = hashlib.sha256(line.encode()).hexdigest()
    n, hits = 0, 0
    for l in (ROOT / "logs" / "prompts_rendered.jsonl").open():
        n += 1
        hits += bool(BAN.search(json.loads(l)["user_text"]))
    if hits:
        problems.append(f"no-ban audit: {hits} hits")
    print(json.dumps({"tasks_recounted": len(cand), "prompts_audited": n, "ban_hits": hits,
                      "commitment_files_checked": sum(len(v["files"]) - 1 for v in com["tasks"].values()),
                      "problems": problems}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
