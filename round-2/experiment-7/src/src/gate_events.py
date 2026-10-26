#!/usr/bin/env python3
"""Step 0.3: build the FRLP gate events from exp1's sampled, labelled programs (T=1.0, thinking off).

Per task: baseline, the modal ban, every mention:X, listall, every ban of an absent algorithm whose default share
fell >= 10 points versus baseline, and every exp1 two-step ban with >= 15 attempted non-banned samples. Per event
the 5 paraphrases with the most code samples are kept, with their exact exp1 prompt text and attempted labels.
The two exp1 succession step-2 events are stored separately (descriptive only).
"""

from __future__ import annotations

import collections
from typing import Any

from loguru import logger

from config import (DATA_IN, DEFAULT_MODE, MODES, OTHER, RESULTS, SUITE, TASKS, commit, read_json, read_jsonl,
                    setup_logging, write_json)

MAIN_DECODING = "T1.0_topp1.0_topk-off_max1024_thinkoff"
MODAL_BAN = {"t1": "ban:bfs", "t2": "ban:dijkstra"}
N_PARA = 5


def exp1_succession_prompts(task: str, banned: list[str]) -> list[dict[str, Any]]:
    """Rebuild exp1's step-2 prompts: exp1 BAN_TEMPLATES with X = exp1 display names joined 'A or B' (ban order)."""
    import sys

    sys.path.insert(0, str(SUITE))
    from common import CATALOGUE, join_names_or  # exp1's frozen names
    from gen.prompts import BAN_TEMPLATES, fill, make_prompt

    names = join_names_or([CATALOGUE[task][m] for m in banned])
    return [{"paraphrase_id": i, "prompt": make_prompt(task, fill(t, X=names))} for i, t in enumerate(BAN_TEMPLATES)]


def distribution(labels: list[str], task: str) -> dict[str, int]:
    c = collections.Counter(lbl if lbl in MODES[task] else OTHER for lbl in labels)
    return {k: int(c.get(k, 0)) for k in MODES[task] + [OTHER]}


def build_event(task: str, cond: str, rows: list[dict[str, Any]], prompts: dict[int, str],
                banned: list[str]) -> dict[str, Any]:
    by_pid: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_pid[int(r["paraphrase_id"])].append(r)
    pids = sorted(by_pid, key=lambda p: (-len(by_pid[p]), p))[:N_PARA]
    kept = [r for p in pids for r in by_pid[p]]
    dist_all = distribution([r["label"] for r in kept], task)
    allowed = [m for m in MODES[task] if m not in banned]
    allowed_dist = {k: v for k, v in dist_all.items() if k not in banned}
    n_allowed = sum(allowed_dist.values())
    shares = sorted(((v / n_allowed if n_allowed else 0.0), k) for k, v in allowed_dist.items())[::-1]
    top, runner = shares[0], (shares[1] if len(shares) > 1 else (0.0, None))
    return {
        "event_id": f"{task}|{cond}", "task": task, "condition": cond, "banned": banned, "allowed": allowed,
        "paraphrase_ids": pids,
        "paraphrases": [{"paraphrase_id": p, "prompt": prompts[p],
                         "labels": [r["label"] for r in by_pid[p]],
                         "passed": [bool(r["passed"]) for r in by_pid[p]],
                         "distribution": distribution([r["label"] for r in by_pid[p]], task)} for p in pids],
        "n_samples": len(kept), "distribution_attempted": dist_all, "distribution_allowed": allowed_dist,
        "n_banned_label_samples": int(sum(v for k, v in dist_all.items() if k in banned)),
        "realised_mode": top[1], "realised_top_share": top[0], "runner_up": runner[1],
        "runner_up_share": runner[0], "clear_mode": bool(top[0] - runner[0] >= 0.15),
    }


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("gate_events")
    rows = [r for r in read_jsonl(DATA_IN / "exp1" / "labelled.jsonl")
            if r["decoding"] == MAIN_DECODING and r["label"] != "no_code" and r.get("code")]
    conds = read_json(SUITE / "prompts" / "conditions.json")
    summaries = read_json(DATA_IN / "exp1" / "condition_summaries.json")
    by_cond: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_cond[(r["task"], r["condition"])].append(r)
    events, succession, selection_log = [], [], {}
    for task in TASKS:
        default = DEFAULT_MODE[task]

        def share_default(cond: str) -> float:
            labs = [r["label"] for r in by_cond[(task, cond)]]
            return sum(lbl == default for lbl in labs) / max(1, len(labs))

        base_share = share_default("baseline")
        chosen = ["baseline", MODAL_BAN[task]] + [f"mention:{m}" for m in MODES[task]] + ["listall"]
        drops = {}
        for m in MODES[task]:
            cond = f"ban:{m}"
            if cond == MODAL_BAN[task] or m == default:
                continue
            drops[cond] = base_share - share_default(cond)
            if drops[cond] >= 0.10 - 1e-12:
                chosen.append(cond)
        # two-step (succession step 2): included only with >= 15 attempted non-banned samples
        srows = by_cond[(task, "succession:2")]
        raw = read_jsonl(DATA_IN / "exp1" / "raw_succession.jsonl")
        banned2 = next(r["banned_set"] for r in raw if r["task"] == task and str(r.get("step")) == "2")
        n_nonbanned = sum(r["label"] not in banned2 for r in srows)
        selection_log[task] = {"baseline_default_share": base_share, "absent_ban_default_drop": drops,
                               "two_step_banned": banned2, "two_step_nonbanned_attempted": n_nonbanned,
                               "two_step_included": n_nonbanned >= 15}
        for cond in chosen:
            banned = [cond.split(":")[1]] if cond.startswith("ban:") else []
            prompts = {int(p["paraphrase_id"]): p["prompt"] for p in conds["tasks"][task]["conditions"][cond]}
            ev = build_event(task, cond, by_cond[(task, cond)], prompts, banned)
            ev["exp1_summary_label_counts"] = summaries.get(f"{task}|{cond}", {}).get("label_counts")
            events.append(ev)
        sp = {p["paraphrase_id"]: p["prompt"] for p in exp1_succession_prompts(task, banned2)}
        sev = build_event(task, "succession:2", srows, sp, list(banned2))
        sev["descriptive_only"] = True
        if n_nonbanned >= 15:
            events.append(sev)
        succession.append(sev)
        logger.info(f"{task}: events={chosen}; drops={ {k: round(v, 3) for k, v in drops.items()} }; "
                    f"two-step non-banned={n_nonbanned}")
    out = {"rule": "per task: baseline, modal ban, every mention:X, listall, absent bans with default-share drop "
                   ">= 10 points, two-step bans with >= 15 attempted non-banned samples; 5 paraphrases with most "
                   "code samples (ties: lowest id); attempted labels (pass or fail), no_code dropped",
           "decoding": MAIN_DECODING, "selection": selection_log, "events": events,
           "succession_step2_descriptive": succession}
    write_json(RESULTS / "gate_events.json", out)
    commit(RESULTS / "gate_events.json", "gate events frozen before any scoring")
    for ev in events:
        logger.info(f"{ev['event_id']}: n={ev['n_samples']} allowed={ev['distribution_allowed']} "
                    f"mode={ev['realised_mode']} clear={ev['clear_mode']}")


if __name__ == "__main__":
    main()
