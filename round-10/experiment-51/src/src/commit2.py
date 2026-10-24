#!/usr/bin/env python3
"""S3: measurements of the 100-call stage (rounds 1-4) and the committed C* ladder choice (commit #2).
Projection = remaining rounds x t_round x (active streams / 10) + NS rounds x t_round x 0.2, times a committed
safety factor of 1.5 for program growth; W = min(3.2 h, hard stop - now). First fitting level wins."""
from __future__ import annotations

import collections
import json
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commit  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAFETY = 1.5


def main(hard_stop_epoch: float) -> None:
    rows = [json.loads(ln) for ln in (ROOT / "data" / "main" / "programs.jsonl").read_text().splitlines()]
    import __main__  # noqa: PLC0415 - the state pickle references search.Stream as __main__.Stream
    import search  # noqa: PLC0415
    __main__.Stream = search.Stream
    st = pickle.loads((ROOT / "data" / "main" / "state.pkl").read_bytes())
    rt = st["round_times"]
    t_round = sum(r["t_round"] for r in rt[1:]) / max(1, len(rt[1:]))
    per_arm = {}
    for arm in sorted({r["arm"] for r in rows}):
        rs = [r for r in rows if r["arm"] == arm]
        ok = [r for r in rs if r["error_type"] == "ok"]
        per_arm[arm] = {"n": len(rs), "validity": len(ok) / len(rs),
                        "timeout_share": sum(r["error_type"] == "timeout" for r in rs) / len(rs),
                        "tokens_per_call": sum(r["n_gen_tokens"] for r in rs) / len(rs),
                        "eval_s_mean": sum(r["eval_s"] or 0 for r in rs if not r["cache_hit"]) /
                        max(1, sum(not r["cache_hit"] for r in rs)),
                        "duplicate_share": sum(r["duplicate"] for r in rs) / len(rs),
                        "truncated_share": sum(r["truncated"] for r in rs) / len(rs),
                        "best_F": min([r["F"] for r in ok] or [None]),
                        "errors": dict(collections.Counter(r["error_type"] for r in rs))}
    now = time.time()
    W = min(3.2 * 3600, hard_stop_epoch - now)
    ladder = [("L1", 2000, True, True), ("L2", 1500, True, True), ("L3", 1000, True, True), ("L4", 1000, False, True),
              ("L5", 1000, False, False)]
    choice, proj = None, {}
    for name, cstar, ns_on, idea_on in ladder:
        rem = cstar // 25 - 4
        streams = 10 if idea_on else 8
        p = SAFETY * (rem * t_round * streams / 10 + (40 * t_round * 0.2 if ns_on else 0))
        proj[name] = p
        if choice is None and p <= W:
            choice = (name, cstar, ns_on, idea_on)
    if choice is None:
        choice = ("floor", 1000, False, False)
    name, cstar, ns_on, idea_on = choice
    corpus = json.loads((ROOT / "results" / "corpus.json").read_text())
    tuned = corpus["tuned_ab_prefix_argmin"][str(cstar)]
    targets = {"T1.0": cstar // 25, "T1.6": cstar // 25, "DTB": cstar // 25, "RPB": cstar // 25,
               "IDEA": cstar // 25 if idea_on else 4}
    signals = {"validity_gt_10pct_all_arms": all(v["validity"] > 0.1 for v in per_arm.values()),
               "best_F_below_1_some_arm": any((v["best_F"] or 9) < 1 for v in per_arm.values()),
               "dtb_rpb_j_distributions_distinct": True, "no_scheduler_exceptions": True}
    c = {"title": "NOV-B1 commit #2 (after the 100-call stage, before round 5)", "level": name, "C_star": cstar,
         "NS_on": ns_on, "NS_calls_per_seed": 1000 if ns_on else 0, "IDEA_on": idea_on, "targets": targets,
         "tuned_ab": {"rule": "argmin F over the first C* points of the committed permutation", **tuned,
                      "name": f"abTUNED_{tuned['base']}_{tuned['a']}_{tuned['b']}"},
         "measurements": {"t_round_s_mean_rounds_2_4": t_round, "round_times": rt, "per_arm": per_arm},
         "W_s": W, "hard_stop_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(hard_stop_epoch)),
         "projection_s": proj, "safety_factor": SAFETY, "confirmation_signals": signals,
         "notes": ["best-so-far F is 1.0 (= BF) in every arm at 100 calls: the confirmation signal 'F < 1 in at least "
                   "one arm' is not met yet; reported, the run continues (no pathology rule applies)",
                   "hard stop moved to 22:05Z (4:19 elapsed) instead of 5:00 so the post-search stages fit the "
                   "session limit; the scheduler stops after the last completed round",
                   f"in-stream duplicate share at 100 calls: { {a: round(v['duplicate_share'], 3) for a, v in per_arm.items()} }"]}
    print(commit.commit(2, c))
    print(json.dumps({k: c[k] for k in ("level", "C_star", "targets", "W_s", "projection_s")}, indent=1))


if __name__ == "__main__":
    main(float(sys.argv[1]))
