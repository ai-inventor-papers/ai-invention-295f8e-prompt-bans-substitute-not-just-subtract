#!/usr/bin/env python3
"""Stage 2.1: assemble data/placed_programs.jsonl -- every survivor family of the five-name ban and the covert
BFS/DFS programs, scrubbed with exp46 programs.scrub(), with a context variant assigned round-robin per family.

Family map (iteration-9 hand-read 'family' codes, data/manual_reads_v9.jsonl; iteration-8 adjudicated labels):
  F-UD  iter-8 C6 ban/confirm adj_label dijkstra_unit + iter-9 UD
  F-BF  iter-8 C6 'other' named Bellman-Ford / SPFA + iter-9 BF (grid Bellman-Ford, raster relaxation rounds)
  F-CK  iter-9 CK (coordinate-key heaps)
  F-RF  iter-9 RP (random priority) + RC (random choice) + iter-8 random-priority / random walk / randomized DFS
  F-RS  iter-9 FL (raster flood-fill sweeps) + iter-8 wavefront propagation
  F-SF  iter-9 SP (set frontier, set.pop order)
  F-OTH iter-9 MX (mixed FIFO/LIFO deque) + iter-8 BFS variants (adj_label bfs) + iter-8 other
  F-COV covert BFS/DFS of the five-name ban: exp45 retrace rows, config != C6, banned set = the five names, passes the
        48-case suite, lexically compliant (L1: no banned alias anywhere in the code), runtime label bfs or dfs
  F-COVX the same criteria on the iteration-2 single / multi-name bans (label inside the banned set), descriptive
Only programs that pass the 48-case suite (recorded flag) are placed."""

from __future__ import annotations

import collections
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v10  # noqa: E402

FAM9 = {"UD": "F-UD", "BF": "F-BF", "CK": "F-CK", "RP": "F-RF", "RC": "F-RF", "FL": "F-RS", "SP": "F-SF",
        "MX": "F-OTH"}
FIVE = {"bfs", "dfs", "iddfs", "astar", "gbfs"}


def iter8_family(r: dict) -> str | None:
    lab, name = r.get("adj_label"), (r.get("adj_other_name") or "")
    low = name.lower()
    if lab == "dijkstra_unit":
        return "F-UD"
    if lab == "bfs":
        return "F-OTH"
    if lab != "other":
        return None
    if "bellman" in low or "spfa" in low:
        return "F-BF"
    if "random" in low:
        return "F-RF"
    if "wavefront" in low:
        return "F-RS"
    return "F-OTH"


def run() -> dict:
    import programs

    rows: list[dict] = []
    # ---- iteration 8 (C6 = Qwen3-32B thinking, five-name ban + confirmation)
    for f in ("labelled_C6_ban.jsonl", "labelled_C6_confirm.jsonl"):
        for r in v10.read_jsonl(v10.IN44 / "data" / f):
            fam = iter8_family(r)
            if fam is None or not r.get("passed") or not r.get("code"):
                continue
            rows.append({"uid": f"i8|{r['uid']}", "family": fam, "source": "iter8_C6", "config": "C6",
                         "author": r.get("model"), "label": r.get("adj_label"), "other_name": r.get("adj_other_name"),
                         "code": r["code"], "passed48": bool(r.get("passed")), "passed41": bool(r.get("passed_exp2")),
                         "runtime_label": r.get("runtime_label")})
    # ---- iteration 9 hand-read k = 5 survivors
    surv = {r["uid"]: r for r in v10.read_jsonl(v10.IN45 / "data" / "survivors_for_tpg.jsonl")}
    samp = {r["uid"]: r for r in v10.read_jsonl(v10.IN45 / "data" / "samples_v9.jsonl")}
    mr = v10.read_jsonl(v10.IN45 / "data" / "manual_reads_v9.jsonl")
    for m in mr:
        src = surv.get(m["uid"]) or samp.get(m["uid"])
        if src is None or not src.get("code"):
            logger.warning(f"no code for iter-9 manual read {m['uid']}")
            continue
        rows.append({"uid": f"i9|{m['uid']}", "family": FAM9[m["family"]], "family_code_iter9": m["family"],
                     "source": "iter9_k5", "config": src.get("cell"), "author": src.get("model"),
                     "label": src.get("label"), "other_name": m.get("algorithm"), "code": src["code"],
                     "passed48": bool(src.get("passed")), "passed41": bool(src.get("passed_exp2")),
                     "runtime_label": src.get("runtime_label"), "tracer_class": src.get("order_class")})
    # ---- covert BFS / DFS
    for r in v10.read_jsonl(v10.IN45 / "results" / "retrace_extras.jsonl"):
        if r.get("config") == "C6" or not r.get("passed") or not r.get("lexical_L1") or not r.get("code"):
            continue
        rl = r.get("runtime_label")
        bs = set(r.get("banned_set") or [])
        if rl not in ("bfs", "dfs") or rl not in bs:
            continue
        fam = "F-COV" if bs == FIVE else "F-COVX"
        rows.append({"uid": f"cov|{r['uid']}", "family": fam, "source": r.get("source"), "config": r.get("config"),
                     "author": r.get("model"), "label": r.get("label"), "code": r["code"], "passed48": True,
                     "passed41": bool(r.get("passed_exp2")), "runtime_label": rl, "tracer_class": r.get("order_class"),
                     "covert_kind": rl, "tracer_agrees": r.get("order_class") == rl.upper(),
                     "banned_set": sorted(bs)})
    # ---- dedupe by code, scrub, assign context variants
    seen: dict[str, str] = {}
    out, dups = [], 0
    per_fam = collections.Counter()
    for r in rows:
        k = v10.sha256_text(r["code"])
        if k in seen:
            dups += 1
            continue
        seen[k] = r["uid"]
        try:
            s, smap = programs.scrub(r["code"])
        except (SyntaxError, ValueError, RecursionError) as e:
            logger.warning(f"scrub failed {r['uid']}: {e}")
            continue
        hits = [m.group(0) for m in programs.ALIAS_RE.finditer(s)]
        r.update({"code_sha256": k, "scrubbed": s, "scrubbed_sha256": v10.sha256_text(s), "scrub_map": smap,
                  "alias_hits_after_scrub": hits[:5], "context_variant": per_fam[r["family"]] % 5})
        per_fam[r["family"]] += 1
        out.append(r)
    v10.DATA.mkdir(exist_ok=True)
    with (v10.DATA / "placed_programs.jsonl").open("w") as fh:
        import json

        for r in out:
            fh.write(json.dumps(r, default=str) + "\n")
    summ = {"utc": v10.utc_now(), "n": len(out), "n_duplicates_dropped": dups, "per_family": dict(per_fam),
            "per_family_source": {f: dict(collections.Counter(r["source"] for r in out if r["family"] == f))
                                  for f in per_fam},
            "iter9_family_codes": dict(collections.Counter(m["family"] for m in mr)),
            "hypothesis_counts_iter9": {"UD": 23, "CK": 18, "BF": 17, "RP": 8, "SP": 3, "FL": 3, "RC": 2, "MX": 2},
            "covert_by_config": dict(collections.Counter(r["config"] for r in out if r["family"] == "F-COV")),
            "covert_by_kind": dict(collections.Counter(r["covert_kind"] for r in out if r["family"] == "F-COV")),
            "covert_strict_tracer_agrees": sum(1 for r in out if r["family"] == "F-COV" and r.get("tracer_agrees")),
            "scrub_alias_hits": sum(1 for r in out if r["alias_hits_after_scrub"]),
            "family_uids": {f: [r["uid"] for r in out if r["family"] == f] for f in per_fam},
            "family_code_sha256": {f: [r["code_sha256"] for r in out if r["family"] == f] for f in per_fam}}
    v10.write_json(v10.RESULTS / "placed_programs_summary.json", summ)
    logger.info(f"placed programs: {summ['per_family']} (dups {dups}); covert by config {summ['covert_by_config']}")
    return summ


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    run()
