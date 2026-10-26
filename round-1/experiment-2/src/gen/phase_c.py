#!/usr/bin/env python3
"""Phase C: prompt bans (N=100 per event = 10 paraphrases x 10 samples), labelled while the model stays loaded.

Refuses to start unless predictions/predictions_v1.json matches the last hash in predictions/commit_log.jsonl,
and refuses to sample any event that has no committed entry. Succession: realised mode under ban:modal ->
step-2 set {modal, realised} -> step 3 if time allows and step 2 has a clear mode; a ban with < 50%
compliance is a ban failure and stops the succession.
Outputs: data/samples_phaseC.jsonl, results/phaseC_events.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
sys.path.insert(0, str(ROOT / "labeller"))
sys.path.insert(0, str(ROOT / "tasks"))
from common import (CATALOGUE, DECODING_GEN, MODEL_TAG, TASKS, add_deviation, append_jsonl, log_timing,  # noqa: E402
                    read_jsonl, setup_logger, sha256_file, stable_seed)

logger = setup_logger("phase_c")
N_PER_PARA = 10


def verify_commit() -> dict:
    pf = ROOT / "predictions" / "predictions_v1.json"
    log = read_jsonl(ROOT / "predictions" / "commit_log.jsonl")
    assert log, "no commit log: refusing to sample"
    h = sha256_file(pf)
    assert h == log[-1]["sha256"], f"predictions hash {h} != committed {log[-1]['sha256']}: refusing to sample"
    preds = json.loads(pf.read_text())
    preds["_commit_unix"] = log[-1]["unix"]
    logger.info(f"commit verified: sha256={h}")
    return preds


def realised_mode(rows: list[dict], banset: list[str], task: str) -> dict:
    n = len(rows)
    comp = [r for r in rows if r["passed"] and r["label"] not in banset and r["label"] not in ("no_code",)]
    cnt = Counter(r["label"] for r in comp)
    ranked = cnt.most_common()
    share = {m: c / max(len(comp), 1) for m, c in cnt.items()}
    top, run = (ranked[0] if ranked else (None, 0)), (ranked[1] if len(ranked) > 1 else (None, 0))
    lead = (top[1] - run[1]) / max(len(comp), 1)
    clear = top[0] is not None and lead >= 0.15
    return {"n": n, "n_compliant": len(comp), "compliance": len(comp) / max(n, 1),
            "label_counts_all": dict(Counter(r["label"] for r in rows)), "compliant_counts": dict(cnt),
            "compliant_shares": share, "top": top[0], "runner_up": run[0], "lead": lead,
            "realised": top[0] if clear else None, "clear": clear, "ban_failure": len(comp) / max(n, 1) < 0.5,
            "pass_rate": sum(r["passed"] for r in rows) / max(n, 1)}


def requests_for(prompts: list[dict], task: str, cond: str, n_per_para: int, tag: str) -> list[dict]:
    ps = sorted([p for p in prompts if p["task"] == task and p["condition"] == cond], key=lambda p: p["paraphrase_id"])
    assert len(ps) == 10, f"{task} {cond}: {len(ps)} prompts"
    reqs = []
    for s in range(n_per_para):
        for p in ps:
            reqs.append({"task": task, "condition": cond, "paraphrase_id": p["paraphrase_id"], "sample_id": s,
                         "prompt_id": p["prompt_id"], "prompt_ids": p["prompt_ids"], "max_tokens": 1024,
                         "model": MODEL_TAG, "decoding": DECODING_GEN, "phase": "C", "event_tag": tag})
    return reqs


def run_events(model, tok, prompts, events: list[tuple[str, list[str]]], preds: dict, n_per_para: int, logger_,
               label_rows, seed_tag: str) -> list[dict]:
    from hf_engine import hf_sample

    reqs = []
    for task, bset in events:
        eid = f"{task}|ban:{'+'.join(bset)}"
        assert eid in preds["events"], f"event {eid} has no committed prediction: refusing to sample"
        reqs += requests_for(prompts, task, "ban:" + "+".join(bset), n_per_para, eid)
    t0 = time.time()
    rows = hf_sample(model, tok, reqs, logger_, batch_size=32, seed_base=stable_seed("phaseC", seed_tag) % 100000)
    dt = time.time() - t0
    now = time.time()
    for r in rows:
        r["utc"] = now
        r["first_sample_after_commit"] = now > preds["_commit_unix"]
    log_timing("C", seed_tag, len(rows), dt)
    logger_.info(f"{seed_tag}: {len(rows)} samples in {dt / 60:.1f} min ({dt / max(len(rows), 1):.2f}s/sample)")
    label_rows(rows, logger_, workers=5)
    append_jsonl(ROOT / "data" / "samples_phaseC.jsonl", rows)
    return rows


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline-min", type=float, default=60.0, help="minutes from start after which optional arms are skipped")
    ap.add_argument("--mention", action="store_true")
    args = ap.parse_args()
    t_start = time.time()
    preds = verify_commit()
    from hf_engine import load_model
    from label import label_rows

    prompts = [p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl") if p["kind"] == "geom"]
    summA = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    model, tok = load_model(logger)
    (ROOT / "data" / "samples_phaseC.jsonl").unlink(missing_ok=True)
    out = {"events": {}, "succession": {}}
    # single bans: modal + present-minor
    singles = []
    for t in TASKS:
        modal = summA[t]["modal"]
        singles.append((t, [modal]))
        singles += [(t, [m]) for m in CATALOGUE[t] if summA[t]["strata"][m] == "present_minor"]
    rows = run_events(model, tok, prompts, singles, preds, N_PER_PARA, logger, label_rows, "single_bans")
    for t, bset in singles:
        eid = f"{t}|ban:{'+'.join(bset)}"
        rr = [r for r in rows if r["event_tag"] == eid]
        out["events"][eid] = realised_mode(rr, bset, t) | {"task": t, "banset": bset}
        logger.info(f"{eid}: {out['events'][eid]}")
    (ROOT / "results" / "phaseC_events.json").write_text(json.dumps(out, indent=1))
    # succession
    for step in (2, 3):
        evs = []
        for t in TASKS:
            chain = out["succession"].setdefault(t, {"chain": [summA[t]["modal"]], "stopped": None})
            if chain["stopped"]:
                continue
            last = f"{t}|ban:{'+'.join(chain['chain'])}"
            res = out["events"].get(last)
            if res is None:
                continue
            if res["ban_failure"]:
                chain["stopped"] = f"ban failure at {last} (compliance {res['compliance']:.2f})"
                continue
            if not res["clear"]:
                chain["stopped"] = f"no clear realised mode at {last}"
                continue
            if len(chain["chain"]) >= len(CATALOGUE[t]) - 1:
                chain["stopped"] = "catalogue exhausted"
                continue
            nxt = chain["chain"] + [res["realised"]]
            chain["chain"] = nxt
            evs.append((t, nxt))
        if not evs:
            break
        elapsed = (time.time() - t_start) / 60
        if step == 3 and elapsed > args.deadline_min:
            add_deviation(f"Succession step 3 dropped (time drop order 3): Phase C at {elapsed:.0f} min.")
            for t, b in evs:
                out["succession"][t]["stopped"] = "time (drop order 3)"
                out["succession"][t]["chain"] = b[:-1]
            break
        rows = run_events(model, tok, prompts, evs, preds, N_PER_PARA, logger, label_rows, f"step{step}")
        for t, bset in evs:
            eid = f"{t}|ban:{'+'.join(bset)}"
            rr = [r for r in rows if r["event_tag"] == eid]
            out["events"][eid] = realised_mode(rr, bset, t) | {"task": t, "banset": bset, "step": step}
            logger.info(f"{eid}: {out['events'][eid]}")
        (ROOT / "results" / "phaseC_events.json").write_text(json.dumps(out, indent=1))
    # optional mention:modal N=50 per task
    elapsed = (time.time() - t_start) / 60
    if args.mention and elapsed < args.deadline_min:
        from hf_engine import hf_sample
        from label import label_rows as lr

        reqs = []
        for t in TASKS:
            reqs += requests_for(prompts, t, f"mention:{summA[t]['modal']}", 5, f"{t}|mention:{summA[t]['modal']}")
        rows = hf_sample(model, tok, reqs, logger, batch_size=32, seed_base=stable_seed("phaseC", "mention") % 100000)
        for r in rows:
            r["utc"] = time.time()
        lr(rows, logger, workers=5)
        append_jsonl(ROOT / "data" / "samples_phaseC.jsonl", rows)
        for t in TASKS:
            m = summA[t]["modal"]
            rr = [r for r in rows if r["task"] == t]
            out["events"][f"{t}|mention:{m}"] = realised_mode(rr, [], t) | {"task": t, "banset": [], "kind": "mention"}
    else:
        add_deviation("mention:modal was not sampled inside Phase C (optional arm); see the Phase C extension.")
    out["elapsed_min"] = (time.time() - t_start) / 60
    (ROOT / "results" / "phaseC_events.json").write_text(json.dumps(out, indent=1))
    logger.info(f"Phase C done in {out['elapsed_min']:.1f} min")


if __name__ == "__main__":
    main()
