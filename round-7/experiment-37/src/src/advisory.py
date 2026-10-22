#!/usr/bin/env python3
"""F5 path: no judge family passed the 10-control gate, so the final class of every candidate is the executor's
manual read. The pre-registered pair (mistralai/mistral-medium-3.1, moonshotai/kimi-k2-0905) is still run on every
shown candidate as UNGATED ADVISORY input (same frozen prompt, blind, shuffled), so the report can give inter-judge
agreement and judge-vs-manual agreement. Advisory votes never set a final class."""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

from adjudicate import CAND_P, JUDGE_P, _judge_batch, _kappa, judge_text, nearest_for  # noqa: E402
from common import (CAP_USD, DATA, PRED, RESULTS, append_jsonl, read_json, read_jsonl, setup_logging,  # noqa: E402
                    stable_seed, utc_now, write_json)


def main() -> None:
    setup_logging("advisory")
    from collections import Counter

    from critic import Critic
    from finalize import all_rows
    from inputs import load_task
    from orclient import ORClient
    c0 = read_json(PRED / "commit0.json")
    pair = c0["judges"]["pair"]
    cands = read_json(CAND_P)
    rows = {r["id"]: r for r in all_rows()}
    cx = read_json(DATA / "complexity.json")
    objs = {t: load_task(t) for t in ("T2", "T03", "A3")}
    critic = Critic()
    client = ORClient("adjudication", CAP_USD["adjudication"], concurrency=10)
    calls = {(r["key"], r["model"]): r for r in read_jsonl(JUDGE_P)}
    for t, ct in cands["tasks"].items():
        shown = list(ct["shown"])
        random.Random(stable_seed(t, "shuffle")).shuffle(shown)
        prompts = {i: judge_text(objs[t], rows[i]["code"], nearest_for(critic, rows[i]["code"], t, rows[i]),
                                 cx.get(i), c0["judge_prompt"]) for i in shown}
        for m in pair:
            todo = [(i, prompts[i]) for i in shown if (i, m) not in calls]
            if not todo or client.stop:
                continue
            res = asyncio.run(_judge_batch(client, m, todo))
            recs = [{"key": i, "model": m, "task": t, "result": v, "advisory": True, "utc": utc_now()}
                    for i, v in res.items()]
            append_jsonl(JUDGE_P, recs)
            for x in recs:
                calls[(x["key"], x["model"])] = x
            logger.info(f"{t}: advisory {m} on {len(todo)} candidates; spend ${client.spent:.3f}")
    adj = read_json(RESULTS / "adjudication.json")
    a_l, b_l = [], []
    for i, rec in adj["per_candidate"].items():
        votes = {m: (calls.get((i, m)) or {}).get("result") for m in pair}
        rec["advisory_votes"] = {m: (v or {}).get("class") for m, v in votes.items()}
        rec["advisory_named"] = {m: (v or {}).get("named_algorithm") for m, v in votes.items()}
        rec["advisory_ideas"] = {m: (v or {}).get("core_idea") for m, v in votes.items()}
        va, vb = rec["advisory_votes"].get(pair[0]), rec["advisory_votes"].get(pair[1])
        if va and vb:
            a_l.append(va)
            b_l.append(vb)
    adj["advisory_pair"] = pair
    adj["advisory_kappa"] = _kappa(a_l, b_l)
    adj["advisory_n_pairs"] = len(a_l)
    adj["advisory_agreement"] = sum(x == y for x, y in zip(a_l, b_l)) / len(a_l) if a_l else None
    adj["advisory_class_counts"] = {m: dict(Counter(r["advisory_votes"].get(m) for r in adj["per_candidate"].values()))
                                    for m in pair}
    adj["final_class_source"] = "manual read of every candidate (F5: no judge family passed the control gate)"
    adj["spent_usd"] = client.spent
    write_json(RESULTS / "adjudication.json", adj)
    logger.info(f"advisory kappa {adj['advisory_kappa']}, agreement {adj['advisory_agreement']}, spent ${client.spent:.3f}")


if __name__ == "__main__":
    main()
