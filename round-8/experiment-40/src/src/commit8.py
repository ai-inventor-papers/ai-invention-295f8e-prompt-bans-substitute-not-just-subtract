#!/usr/bin/env python3
"""Hash-chained commitments: each line of commitments.log = {name, utc, payload_sha256, prev, hash}; the payload is
written to predictions/<name>.json first. verify() recomputes the chain and every payload hash."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cfg8 import COMMIT_LOG, PRED, read_json, utc_now, write_json

GENESIS = hashlib.sha256(b"iter8_gen_plan_experiment_2_idx3").hexdigest()


def _lines() -> list[dict[str, Any]]:
    if not COMMIT_LOG.exists():
        return []
    return [json.loads(l) for l in COMMIT_LOG.read_text().splitlines() if l.strip()]


def commit(name: str, payload: dict[str, Any]) -> str:
    existing = [l for l in _lines() if l["name"] == name]
    if existing:
        return existing[-1]["hash"]
    p = PRED / f"{name}.json"
    write_json(p, payload)
    ph = hashlib.sha256(p.read_bytes()).hexdigest()
    lines = _lines()
    prev = lines[-1]["hash"] if lines else GENESIS
    utc = utc_now()
    h = hashlib.sha256(f"{prev}|{name}|{ph}|{utc}".encode()).hexdigest()
    with open(COMMIT_LOG, "a") as fh:
        fh.write(json.dumps({"name": name, "utc": utc, "payload": f"predictions/{name}.json", "payload_sha256": ph,
                             "prev": prev, "hash": h}) + "\n")
    return h


def verify() -> dict[str, Any]:
    prev = GENESIS
    breaks, changed = [], []
    lines = _lines()
    for l in lines:
        h = hashlib.sha256(f"{prev}|{l['name']}|{l['payload_sha256']}|{l['utc']}".encode()).hexdigest()
        if h != l["hash"] or l["prev"] != prev:
            breaks.append(l["name"])
        p = PRED / f"{l['name']}.json"
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != l["payload_sha256"]:
            changed.append(l["name"])
        prev = l["hash"]
    return {"n_commits": len(lines), "breaks": breaks, "changed_payloads": changed,
            "ok": not breaks and not changed, "names": [l["name"] for l in lines]}


def committed(name: str) -> dict[str, Any] | None:
    p = PRED / f"{name}.json"
    return read_json(p) if p.exists() else None
