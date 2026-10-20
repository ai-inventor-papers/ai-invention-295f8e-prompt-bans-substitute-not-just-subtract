#!/usr/bin/env python3
"""H9 independent re-derivation (written separately from src/analysis.py and src/scoring.py).

From the raw files only (data/raw_gen.jsonl, data/labels.jsonl, predictions/forecasts.json) it recomputes, per event,
the gate, the non-banned landing, Hill_cc, the smoothed log score of every family, the winner, the advance count and
the branch, and compares them with results/c1_events.jsonl and results/analysis.json.  Placebo: the family labels are
permuted within each event 1,000 times (families exchangeable under the null); the share of permutations in which a
given family advances estimates the rule's false-advance rate.  Finally the commitments.log hash chain is verified."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
FAM = ["SUBTRACT", "LADDER", "ASSOCIATE", "PROXIMITY"]


def jl(p: Path) -> list[dict]:
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def q_of(f: dict | None, S: list[str]) -> dict[str, float]:
    bins = S + ["other"]
    if not f:
        f = {b: 1 / len(bins) for b in bins}
    tot = sum(max(f.get(b, 0.0), 0.0) for b in bins)
    return {b: 0.93 * (max(f.get(b, 0.0), 0.0) / tot) + (0.05 / len(S) if b in S else 0.0) + (0.02 if b == "other" else 0.0)
            for b in bins}


def main() -> None:
    raw = {r["row_id"]: r for r in jl(WS / "data" / "raw_gen.jsonl")}
    lab = {r["row_id"]: r for r in jl(WS / "data" / "labels.jsonl")}
    fcs = json.loads((WS / "predictions" / "forecasts.json").read_text())["events"]
    mine = {}
    by_ev = defaultdict(list)
    for rid, r in raw.items():
        if r.get("phase") in ("G1", "G2") and rid in lab:
            by_ev[r["event_id"]].append(lab[rid])
    for eid, fc in fcs.items():
        X, S = fc["X"], fc["S"]
        rows = by_ev.get(eid, [])
        att = [r["label"] for r in rows if r["label"] not in ("invalid", "unresolved")]
        nb = [l for l in att if l != X and l in S + ["other"]]
        avoid = 1 - att.count(X) / len(att) if att else float("nan")
        gate = bool(att) and avoid >= 0.5 and len(nb) >= 20
        cc = Counter(r["label"] for r in rows if r.get("passed") and r["label"] not in ("invalid", X))
        n = sum(cc.values())
        hill = math.exp(-sum((v / n) * math.log(v / n) for v in cc.values() if v)) if n else float("nan")
        ls = {}
        for f in FAM:
            fam = fc["families"][f]
            q = q_of(fam["f"] if fam["defined"] else None, S)
            ls[f] = sum(math.log(q[l]) for l in nb) / len(nb) if nb else float("nan")
        tops = {fam["top1"] for fam in fc["families"].values() if fam["defined"]}
        dis = len(tops) > 1
        srt = sorted(((v, k) for k, v in ls.items() if not math.isnan(v)), reverse=True)
        win = srt[0][1] if (gate and dis and len(srt) > 1 and srt[0][0] - srt[1][0] >= 0.10) else None
        mine[eid] = {"gate": gate, "avoid": avoid, "n_nonbanned": len(nb), "hill_cc": hill, "logscore": ls,
                     "disagreeing": dis, "winner": win, "task": fc["task"]}
    wins = Counter(v["winner"] for v in mine.values() if v["winner"])
    adv = {f: wins.get(f, 0) >= 3 for f in FAM}
    ndg = sum(1 for v in mine.values() if v["gate"] and v["disagreeing"])
    if ndg < 3:
        branch = "UNDETERMINED"
    elif (adv["SUBTRACT"] or adv["LADDER"]) and (adv["ASSOCIATE"] or adv["PROXIMITY"]):
        branch = "CONFLICT"
    elif adv["SUBTRACT"] or adv["LADDER"]:
        branch = "SUBTRACTION/LADDER"
    elif adv["ASSOCIATE"] or adv["PROXIMITY"]:
        branch = "SUBSTITUTION"
    else:
        branch = "NO ADVANCE (X-SPECIFIC BUT UNAIMED or aimed-unresolved; see analysis)"
    # compare
    theirs = {r["event_id"]: r for r in jl(WS / "results" / "c1_events.jsonl")}
    an = json.loads((WS / "results" / "analysis.json").read_text())
    mism = []
    for eid, v in mine.items():
        t = theirs.get(eid)
        if t is None:
            mism.append((eid, "missing row"))
            continue
        if bool(t["gate_pass"]) != v["gate"]:
            mism.append((eid, "gate"))
        if bool(t["disagreeing"]) != v["disagreeing"]:
            mism.append((eid, "disagreeing"))
        if (t.get("winner") or None) != v["winner"]:
            mism.append((eid, "winner"))
        for f in FAM:
            a, b = t["logscore"].get(f), v["logscore"][f]
            if not ((a is None and math.isnan(b)) or (a is not None and not math.isnan(b) and abs(a - b) < 1e-9)):
                mism.append((eid, f"logscore {f}"))
        hc = t.get("hill_cc")
        hc = None if (hc is None or (isinstance(hc, float) and math.isnan(hc))) else hc
        if not ((hc is None and math.isnan(v["hill_cc"])) or (hc is not None and abs(hc - v["hill_cc"]) < 1e-9)):
            mism.append((eid, "hill_cc"))
    their_branch = an["c1"]["branch"]
    branch_match = their_branch.split(" (")[0].split("/")[0] in branch or branch.split(" (")[0] in their_branch \
        or (branch.startswith("NO ADVANCE") and (their_branch.startswith("X-SPECIFIC") or their_branch.startswith("NO FAMILY")))
    # placebo: permute family labels within each event
    rng = random.Random(0)
    adv_counts = Counter()
    any_adv = 0
    gd = [v for v in mine.values() if v["gate"] and v["disagreeing"]]
    for _ in range(1000):
        w = Counter()
        for v in gd:
            vals = [v["logscore"][f] for f in FAM]
            rng.shuffle(vals)
            ls = dict(zip(FAM, vals))
            srt = sorted(((x, k) for k, x in ls.items() if not math.isnan(x)), reverse=True)
            if len(srt) > 1 and srt[0][0] - srt[1][0] >= 0.10:
                w[srt[0][1]] += 1
        a = [f for f in FAM if w.get(f, 0) >= 3]
        for f in a:
            adv_counts[f] += 1
        any_adv += bool(a)
    # hash chain
    prev = "0" * 64
    chain_ok = True
    for line in (WS / "commitments.log").read_text().splitlines():
        e = json.loads(line)
        h = hashlib.sha256((prev + e["file"] + e["sha256"] + e["utc"] + e.get("note", "")).encode()).hexdigest()
        chain_ok &= (e["prev_hash"] == prev and h == e["hash"])
        prev = e["hash"]
    # T8: every committed prediction precedes the first ban sample (commit utc and file mtime vs first G row time)
    import datetime as dt
    g_times = [r["t_unix"] for r in raw.values() if r.get("phase") in ("G1", "G2") and r.get("t_unix")]
    first_ban = min(g_times) if g_times else None
    t8 = {"first_ban_row_unix": first_ban, "entries": []}
    for line in (WS / "commitments.log").read_text().splitlines():
        e = json.loads(line)
        ts = dt.datetime.fromisoformat(e["utc"]).timestamp()
        f = WS / e["file"]
        mt = f.stat().st_mtime if f.exists() else None
        if e["file"].startswith("predictions/screen"):
            continue
        t8["entries"].append({"file": e["file"], "commit_before_first_ban": bool(first_ban and ts < first_ban),
                              "mtime_before_first_ban": bool(first_ban and mt and mt < first_ban)})
    t8["passed"] = all(x["commit_before_first_ban"] and x["mtime_before_first_ban"] for x in t8["entries"])
    # T9 confirmation signals
    pil = defaultdict(Counter)
    bf = defaultdict(Counter)
    for rid, l in lab.items():
        if l["label"] in ("invalid", "unresolved"):
            continue
        if l.get("phase") == "pilot":
            pil[l["task"]][l["label"]] += 1
        elif l.get("phase") in ("B1", "B4"):
            bf[l["task"]][l["label"]] += 1
    same = {t: (pil[t].most_common(1)[0][0] == bf[t].most_common(1)[0][0]) for t in bf if pil[t]}
    t9 = {"bf16_modal_equals_fp8_pilot_modal": same, "n_same": sum(same.values()), "n": len(same)}
    res = {"t8_commit_before_bans": t8, "t9_confirmation": t9, "n_events": len(mine), "n_gated": sum(1 for v in mine.values() if v["gate"]), "n_disagreeing_gated": ndg,
           "wins": dict(wins), "advances": adv, "branch_rederived": branch, "branch_reported": their_branch,
           "branch_match": bool(branch_match), "mismatches": mism, "n_mismatches": len(mism),
           "placebo_family_permutation": {"n_perm": 1000, "advance_rate_by_family": {f: adv_counts[f] / 1000 for f in FAM},
                                          "any_family_advances_rate": any_adv / 1000, "n_disagreeing_gated": len(gd)},
           "hash_chain_ok": chain_ok}
    (WS / "results" / "independent_rederivation.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "mismatches"}, indent=1))


if __name__ == "__main__":
    main()
