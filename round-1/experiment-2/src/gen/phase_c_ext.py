#!/usr/bin/env python3
"""Phase C extension (run after Phase D): the optional mention:modal arm (N=50/task) and EXPLORATORY step-2
ban events sampled although the pre-declared succession rule stopped (modal-ban compliance < 50%).

Every step-2 set sampled here already has a committed forecast in predictions_v1.json (all possible step-2
sets were committed in Phase B), so the commit protocol still holds; the events are flagged exploratory=True
and the analysis reports them separately from the primary events. N=50 per event (the plan's fallback size).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
sys.path.insert(0, str(ROOT / "labeller"))
sys.path.insert(0, str(ROOT / "tasks"))
from common import TASKS, add_deviation, append_jsonl, log_timing, read_jsonl, setup_logger, stable_seed  # noqa: E402
from phase_c import realised_mode, requests_for, verify_commit  # noqa: E402

logger = setup_logger("phase_c_ext")


@logger.catch(reraise=True)
def main() -> None:
    preds = verify_commit()
    from hf_engine import hf_sample, load_model
    from label import label_rows

    prompts = [p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl") if p["kind"] == "geom"]
    summA = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    outp = ROOT / "results" / "phaseC_events.json"
    out = json.loads(outp.read_text())
    # exploratory step-2 sets: modal + each compliant label seen under ban:modal (most frequent first, max 2)
    evs = []
    for t in TASKS:
        m0 = summA[t]["modal"]
        res = out["events"].get(f"{t}|ban:{m0}", {})
        cands = sorted(res.get("compliant_counts", {}).items(), key=lambda kv: -kv[1])[:2]
        for lab, _ in cands:
            eid = f"{t}|ban:{m0}+{lab}"
            assert eid in preds["events"], f"{eid} not committed"
            evs.append((t, [m0, lab], eid))
    reqs = []
    for t, bset, eid in evs:
        reqs += requests_for(prompts, t, "ban:" + "+".join(bset), 5, eid)
    for t in TASKS:
        m0 = summA[t]["modal"]
        reqs += requests_for(prompts, t, f"mention:{m0}", 5, f"{t}|mention:{m0}")
    model, tok = load_model(logger)
    t0 = time.time()
    rows = hf_sample(model, tok, reqs, logger, batch_size=32, seed_base=stable_seed("phaseC", "ext") % 100000)
    log_timing("C", "ext", len(rows), time.time() - t0)
    now = time.time()
    for r in rows:
        r["utc"] = now
        r["exploratory"] = r["condition"].startswith("ban:")
        r["first_sample_after_commit"] = now > preds["_commit_unix"]
    label_rows(rows, logger, workers=6)
    append_jsonl(ROOT / "data" / "samples_phaseC.jsonl", rows)
    for t, bset, eid in evs:
        rr = [r for r in rows if r["event_tag"] == eid]
        out["events"][eid] = realised_mode(rr, bset, t) | {"task": t, "banset": bset, "step": 2, "exploratory": True}
        logger.info(f"{eid}: {out['events'][eid]}")
    for t in TASKS:
        m0 = summA[t]["modal"]
        rr = [r for r in rows if r["event_tag"] == f"{t}|mention:{m0}"]
        out["events"][f"{t}|mention:{m0}"] = realised_mode(rr, [], t) | {"task": t, "banset": [], "kind": "mention"}
        logger.info(f"{t}|mention:{m0}: {out['events'][f'{t}|mention:{m0}']}")
    outp.write_text(json.dumps(out, indent=1))
    add_deviation("Exploratory extension (after Phase D): step-2 ban sets {modal + each of the two most frequent "
                  "compliant labels under ban:modal} were sampled at N=50 although the pre-declared succession rule "
                  "stopped at the modal-ban failure (< 50% compliance). Their forecasts were committed in Phase B; they "
                  "are reported separately from the primary events. The optional mention:modal arm (N=50/task) was "
                  "also sampled here.")
    logger.info(f"Phase C extension done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
