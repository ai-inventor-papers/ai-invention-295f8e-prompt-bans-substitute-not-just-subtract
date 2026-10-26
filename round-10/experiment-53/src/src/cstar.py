"""COMMIT #2: choose C* from the measured round times of the 100-call stage and write data/targets.json.

Projected time for C calls = sum over arm-seeds of (C - done)/32 x W_share(arm-seed) x 1.2, where W is the
steady-state round wall time (rounds 2..last measured) and W_share apportions W by each arm-seed's generated plus
prefilled tokens. T_rem = (STOP - now) - 10 min. The first C* table row that fits is committed.
Usage: python src/cstar.py [STOP_UTC_HH:MM]
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, PRED, ledger, read_jsonl, utc_now, write_json  # noqa: E402
from commit import amend  # noqa: E402

SAFETY = 1.2
ARMS5 = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]
CORE = ["T1.0", "T1.6", "DTB", "RPB"]


def stop_epoch(hhmm: str) -> float:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    return time.mktime(time.strptime(f"{today} {hhmm}", "%Y-%m-%d %H:%M")) - time.timezone


def main() -> None:
    stop = sys.argv[1] if len(sys.argv) > 1 else "22:25"
    rounds = read_jsonl(DATA / "rounds.jsonl")
    steady = [r for r in rounds if r["round"] >= 2 and r["n_calls"] > 0]
    W = sum(r["gen_wall"] for r in steady) / len(steady)
    tok = {}
    for r in steady:
        for k, v in r["tokens"].items():
            d = tok.setdefault(k, {"gen": 0, "prompt": 0, "calls": 0})
            d["gen"] += v["gen"]
            d["prompt"] += v["prompt"]
            d["calls"] += v["calls"]
    # share of the round time per arm-seed by generated + prefilled (uncached share unknown -> both counted)
    weight = {k: (v["gen"] + 0.1 * v["prompt"]) / max(1, v["calls"]) for k, v in tok.items()}
    tot = sum(weight.values())
    share = {k: W * w / tot for k, w in weight.items()}  # seconds per round attributable to that arm-seed
    rows = read_jsonl(DATA / "calls.jsonl")
    done = {}
    for r in rows:
        k = f"{r['arm']}|{r['seed']}"
        done[k] = max(done.get(k, 0), r["call_idx"] + 1)
    now = time.time()
    T_rem = stop_epoch(stop) - now - 600

    def proj(cfg: dict) -> float:
        return SAFETY * sum(max(0, C - done.get(k, 0)) / 32 * share[k] for k, C in cfg.items())

    table = []
    chosen = None
    for C in (2000, 1500, 1000):  # row A
        cfg = {f"{a}|{s}": C for a in ARMS5 for s in (0, 1)}
        t = proj(cfg)
        table.append({"row": "A", "C": C, "projected_s": t, "fits": t <= T_rem})
        if chosen is None and t <= T_rem:
            chosen = ("A", C, cfg)
    if chosen is None:
        for C in (2000, 1500, 1000):  # row B
            cfg = {f"{a}|{s}": C for a in CORE for s in (0, 1)}
            t = proj(cfg)
            table.append({"row": "B", "C": C, "projected_s": t, "fits": t <= T_rem})
            if chosen is None and t <= T_rem:
                chosen = ("B", C, cfg)
    if chosen is None:
        for C0 in (2000, 1500):  # row C
            cfg = {f"{a}|0": C0 for a in CORE} | {f"{a}|1": 1000 for a in CORE}
            t = proj(cfg)
            table.append({"row": "C", "C": C0, "projected_s": t, "fits": t <= T_rem})
            if chosen is None and t <= T_rem:
                chosen = ("C", C0, cfg)
    if chosen is None:
        cfg = {f"{a}|{s}": 1000 for a in CORE for s in (0, 1)}
        t = proj(cfg)
        table.append({"row": "D", "C": 1000, "projected_s": t, "fits": t <= T_rem})
        chosen = ("D", 1000, cfg) if t <= T_rem else ("E", None, {f"{a}|{s}": 100000 for a in CORE for s in (0, 1)})
    row, C, cfg = chosen
    arm_seeds = [{"arm": k.split("|")[0], "seed": int(k.split("|")[1]), "target": v} for k, v in cfg.items()]
    nosel = None
    if row == "A" and C >= 1500:
        last_round = math.ceil(C / 32) - 1
        cur_round = max(r["round"] for r in rounds) + 1
        remaining = max(1, last_round - cur_round + 1)
        per_round = math.ceil(500 / remaining)
        nosel = {"arm": "NOSEL", "seed": 0, "target": 500, "per_round": per_round, "start_round": cur_round}
        arm_seeds.append(nosel)
    out = {"utc": utc_now(), "commit": 2, "stop_utc": stop, "W_steady_s": W, "rounds_used": [r["round"] for r in steady],
           "W_share_s": share, "tokens_per_call": {k: {"gen": v["gen"] / v["calls"], "prompt": v["prompt"] / v["calls"]}
                                                    for k, v in tok.items()},
           "done": done, "T_rem_s": T_rem, "safety": SAFETY, "table": table, "chosen_row": row, "C_star": C,
           "nosel": nosel, "below_plan": row == "E"}
    write_json(PRED / "cstar.json", out)
    write_json(DATA / "targets.json", {"arm_seeds": arm_seeds, "stage": f"COMMIT #2 row {row} C*={C}"})
    amend("COMMIT#2", ["predictions/cstar.json", "data/targets.json"])
    ledger("COMMIT#2", row=row, C=C)
    print(json.dumps({k: out[k] for k in ("W_steady_s", "T_rem_s", "table", "chosen_row", "C_star", "nosel")},
                     indent=1))


if __name__ == "__main__":
    main()
