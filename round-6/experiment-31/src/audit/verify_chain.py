#!/usr/bin/env python3
"""Verify the commitment hash chain (commitments.log vs predictions/*.json) and that no clamp-cell row predates
commit #1 and no S3 row predates commit #0. Usage: python3 audit/verify_chain.py (from the artifact root)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    prev = "0" * 64
    rows, ok = [], True
    times = {}
    for ln in (ROOT / "commitments.log").read_text().splitlines():
        if not ln.strip():
            continue
        utc, name, *kv = ln.split()
        d = dict(x.split("=", 1) for x in kv)
        f = sha(ROOT / "predictions" / f"{name}.json")
        chain = hashlib.sha256((prev + f).encode()).hexdigest()
        good = f == d["sha256"] and prev == d["prev"] and chain == d["chain"]
        ok &= good
        rows.append({"name": name, "utc": utc, "ok": good})
        times[name] = utc
        prev = d["chain"]

    def first_utc(path):
        p = ROOT / path
        if not p.exists():
            return None
        ts = [json.loads(x).get("utc") for x in p.read_text().splitlines() if x.strip()]
        ts = [t for t in ts if t]
        return min(ts) if ts else None
    order = {"s3_first_row_after_commit0": (first_utc("data/raw_s3.jsonl") or "9") > times.get("commit0", "0"),
             "cells_first_row_after_commit1": (first_utc("data/raw_cells.jsonl") or "9") > times.get("commit1", "~")}
    out = {"chain_ok": ok, "entries": rows, "ordering": order, "all_ok": ok and all(order.values())}
    (ROOT / "results" / "verify_chain.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
