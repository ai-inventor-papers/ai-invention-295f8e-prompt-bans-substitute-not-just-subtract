#!/usr/bin/env python3
"""Standard library only. Re-derives every chain value of commitments.log from predictions/<name>.json and checks
that each commitment precedes the first sample it governs (commit0 < any generated row; commit1 < first G3 sweep row;
commit2b < first G1 validation/generation output; commit3 < first dose-sweep row)."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def first_utc(name: str) -> str | None:
    p = ROOT / "data" / name
    if not p.exists():
        return None
    ts = []
    for ln in p.read_text().splitlines():
        if ln.strip():
            try:
                ts.append(json.loads(ln)["utc"])
            except (json.JSONDecodeError, KeyError):
                pass
    return min(ts) if ts else None


def main() -> None:
    prev = "0" * 64
    rows, ok = [], True
    utc = {}
    for ln in (ROOT / "commitments.log").read_text().splitlines():
        if not ln.strip():
            continue
        parts = ln.split()
        name = parts[1]
        kv = dict(x.split("=", 1) for x in parts[2:])
        fsha = sha_file(ROOT / "predictions" / f"{name}.json")
        chain = hashlib.sha256((prev + fsha).encode()).hexdigest()
        good = fsha == kv["sha256"] and prev == kv["prev"] and chain == kv["chain"]
        ok &= good
        rows.append({"name": name, "utc": parts[0], "chain_ok": good})
        utc[name] = parts[0]
        prev = kv["chain"]
    order = {}
    firsts = {f: first_utc(f) for f in ("raw_engine.jsonl", "raw_u6.jsonl", "raw_g3cal.jsonl", "raw_g3.jsonl",
                                        "raw_g1gen.jsonl", "raw_g2dose.jsonl")}
    order["commit0_before_any_sample"] = all(v is None or utc.get("commit0", "~") < v for v in firsts.values())
    order["commit1_before_g3_sweep"] = firsts["raw_g3.jsonl"] is None or utc.get("commit1", "~") < firsts["raw_g3.jsonl"]
    order["commit2b_before_g1_generation"] = firsts["raw_g1gen.jsonl"] is None or \
        utc.get("commit2b", "~") < firsts["raw_g1gen.jsonl"]
    order["commit3_before_dose_sweep"] = firsts["raw_g2dose.jsonl"] is None or \
        utc.get("commit3", "~") < firsts["raw_g2dose.jsonl"]
    res = {"chain_ok": ok, "entries": rows, "ordering": order, "first_rows_utc": firsts,
           "all_ok": ok and all(order.values())}
    (ROOT / "results" / "verify_chain.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
