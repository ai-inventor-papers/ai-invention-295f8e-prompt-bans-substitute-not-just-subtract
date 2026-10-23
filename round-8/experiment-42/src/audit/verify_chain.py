#!/usr/bin/env python3
"""Standard-library audit of the commitment hash chain and of commit-before-sample ordering.

Every line of commitments.log is '<utc> <name> sha256=<file sha> prev=<previous chain> chain=<sha256(prev + file sha)>'.
Ordering rules (iteration-8 plan): commit #0 precedes every sample; #1 precedes every G1 and reverse-generation row;
#2 precedes every edited free-generation row; #3 precedes every wording-extension row."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(p: Path) -> list:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                pass
    return out


def main() -> None:
    prev = "0" * 64
    entries, ok = [], True
    utc = {}
    for ln in (ROOT / "commitments.log").read_text().splitlines():
        if not ln.strip():
            continue
        parts = ln.split()
        name = parts[1]
        kv = dict(x.split("=", 1) for x in parts[2:])
        fsha = sha(ROOT / "predictions" / f"{name}.json")
        chain = hashlib.sha256((prev + fsha).encode()).hexdigest()
        good = fsha == kv["sha256"] and prev == kv["prev"] and chain == kv["chain"]
        ok &= good
        entries.append({"name": name, "utc": parts[0], "file_sha_ok": fsha == kv["sha256"], "chain_ok": good})
        utc[name] = parts[0]
        prev = kv["chain"]
    data = ROOT / "data"
    first = {}
    for f in sorted(data.glob("raw_*.jsonl")):
        ts = [r["utc"] for r in rows(f) if "utc" in r]
        if ts:
            first[f.name] = min(ts)
    order = {"commit0_before_every_sample": all(t > utc["commit0"] for t in first.values()),
             "commit1_before_G1_rows": first.get("raw_g1.jsonl", "9") > utc.get("commit1", "9"),
             "commit1_before_reverse_rows": first.get("raw_rev.jsonl", "9") > utc.get("commit1", "9"),
             "commit2_before_edited_free_rows": first.get("raw_fcells.jsonl", "9") > utc.get("commit2", "9")}
    if "raw_g1e.jsonl" in first:
        order["commit3_before_wording_extension_rows"] = first["raw_g1e.jsonl"] > utc.get("commit3", "9")
    res = {"chain_ok": ok, "entries": entries, "first_row_utc": first, "commit_utc": utc, "ordering": order,
           "all_ok": bool(ok and all(order.values()))}
    (ROOT / "results" / "verify_chain.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"chain_ok": ok, "ordering": order, "all_ok": res["all_ok"]}, indent=1))


if __name__ == "__main__":
    main()
