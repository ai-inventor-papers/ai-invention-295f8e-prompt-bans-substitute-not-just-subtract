#!/usr/bin/env python3
"""Stage 1.6 FREEZE: per committed cell, the first 12 verified programs in verification-completion order (verified =
ACCEPT, or HAND with a hand-read ACCEPT); never chosen by state. Context variants W1-W5 round-robin by within-cell
index. Writes data/frame_freeze.json, data/factorial_set.jsonl, data/factorial_set_ctx2.jsonl (variant v+1 mod 5,
reliability re-extraction) and commits the freeze before any factorial state is extracted.
Top-ups (bibfs / iddfs / jps / biastar) are frozen the same way (12 per class) into data/topups_set.jsonl by
`freeze.py topups` once the paraphrase fallback has run and the hand reads are recorded."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cells  # noqa: E402
import v10  # noqa: E402

N_PER = 12


def verified_rows() -> list[dict]:
    rows = v10.read_jsonl(v10.DATA / "programs_v10.jsonl")
    hand = {r["uid"]: r["verdict"] for r in v10.read_jsonl(v10.DATA / "hand_reads_v10.jsonl")}
    out = []
    for r in rows:
        if r.get("pilot") or r.get("wave") == "smoke":
            continue
        ok = r["verdict"] == "ACCEPT" or (r["verdict"] == "HAND" and hand.get(r["uid"]) == "ACCEPT")
        if ok:
            out.append({**r, "hand_read": hand.get(r["uid"])})
    return out


def select(classes: list[str], rows: list[dict]) -> dict[str, list[dict]]:
    by = defaultdict(list)
    for r in rows:
        if r["cell"] in classes and len(by[r["cell"]]) < N_PER:
            by[r["cell"]].append(r)
    return by


def write_set(path: Path, sel: dict[str, list[dict]], shift: int = 0) -> int:
    n = 0
    with path.open("w") as fh:
        for c, rs in sel.items():
            for i, r in enumerate(rs):
                row = {"uid": r["uid"], "cell": c, "discipline": r.get("discipline"), "container": r.get("container"),
                       "heur_key": r.get("heur_key"), "wording": r.get("wording"), "prompt_id": r.get("prompt_id"),
                       "source": r.get("source"), "repair": r.get("repair"), "paraphrase_of": r.get("paraphrase_of"),
                       "author": r.get("author"), "provider": r.get("provider"), "hand_read": r.get("hand_read"),
                       "within_cell_index": i, "context_variant": (i + shift) % 5, "scrubbed": r["scrubbed_code"],
                       "scrubbed_sha256": r["scrubbed_sha256"], "raw_code": r["raw_code"],
                       "code_sha256": r["code_sha256"]}
                fh.write(json.dumps(row) + "\n")
                n += 1
    return n


def main(which: str) -> None:
    rows = verified_rows()
    if which == "factorial":
        committed = v10.read_json(v10.PRED / "commit1.json")["committed_cells"]
        sel = select(committed, rows)
        n = write_set(v10.DATA / "factorial_set.jsonl", sel)
        write_set(v10.DATA / "factorial_set_ctx2.jsonl", sel, shift=1)
        fr = {"utc": v10.utc_now(), "rule": "first 12 verified per cell in verification-completion order",
              "n": n, "counts": {c: len(v) for c, v in sel.items()},
              "below_floor": {c: len(sel.get(c, [])) for c in committed if len(sel.get(c, [])) < 10},
              "uids": {c: [r["uid"] for r in v] for c, v in sel.items()},
              "sources": {c: dict(Counter(r["source"] for r in v)) for c, v in sel.items()},
              "repairs": {c: sum(bool(r.get("repair")) for r in v) for c, v in sel.items()},
              "hand_read": {c: sum(r.get("hand_read") == "ACCEPT" for r in v) for c, v in sel.items()},
              "heur_keys": {c: dict(Counter(r.get("heur_key") for r in v)) for c, v in sel.items() if c.startswith("HEUR")},
              "context_variants": "round-robin by within-cell index (i mod 5); reliability set uses (i + 1) mod 5"}
        p = v10.DATA / "frame_freeze.json"
        v10.write_json(p, fr)
        print(v10.commit(p, "FREEZE_FACTORIAL", f"{n} programs; before any factorial state extraction"))
        print(fr["counts"], fr["below_floor"])
    else:
        sel = select(cells.TOPUP_CLASSES, rows)
        n = write_set(v10.DATA / "topups_set.jsonl", sel)
        fr = {"utc": v10.utc_now(), "n": n, "counts": {c: len(v) for c, v in sel.items()},
              "uids": {c: [r["uid"] for r in v] for c, v in sel.items()},
              "sources": {c: dict(Counter(r["source"] for r in v)) for c, v in sel.items()}}
        p = v10.DATA / "topup_freeze.json"
        v10.write_json(p, fr)
        print(v10.commit(p, "FREEZE_TOPUPS", f"{n} programs; before any top-up state extraction"))
        print(fr["counts"], fr["sources"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "factorial")
