"""Re-trace every labelled attempt (original and scrubbed code) and store compact traces, so runtime rules can be
revised (gate revision rounds) without re-running the tracer; apply_runtime_rules() recomputes runtime labels."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger

from .harness import extract_code
from .probes import run_trace
from .rtrules import runtime_label
from .scrub import scrub_response


def _compact(tr: dict) -> dict:
    for p in tr["probes"].values():
        f = p.get("features") or {}
        for k in ("clist_idx", "cstr_idx"):
            if k in f:
                f[k] = f[k][:300]
    return tr


def retrace_all(root: Path, raw_names: list[str], label_file: str = "labels_raw.jsonl", out: str = "traces.jsonl",
                workers: int = 5) -> None:
    raw = {}
    for n in raw_names:
        for l in (root / "data" / n).open():
            r = json.loads(l)
            raw[r["sample_id"]] = r
    labs = [json.loads(l) for l in (root / "data" / label_file).open()]
    out_p = root / "data" / out
    done = {json.loads(l)["sample_id"] for l in out_p.open()} if out_p.exists() else set()
    todo = [r for r in labs if r.get("valid") and r["sample_id"] not in done]

    def one(r):
        s = raw[r["sample_id"]]
        code = extract_code(s["text"])
        rec = {"sample_id": r["sample_id"], "task": r["task"], "trace": _compact(run_trace(code, r["task"]))}
        if r["condition"] == "forced":
            _, s_code, info = scrub_response(s["text"], code)
            if info["ok"] and s_code != code:
                rec["trace_scrubbed"] = _compact(run_trace(s_code, r["task"]))
        return rec

    logger.info(f"re-tracing {len(todo)} attempts")
    with ThreadPoolExecutor(workers) as ex, out_p.open("a") as f:
        for i, rec in enumerate(ex.map(one, todo)):
            f.write(json.dumps(rec) + "\n")
            if (i + 1) % 500 == 0:
                logger.info(f"  traced {i + 1}/{len(todo)}")
    logger.info("re-trace done")


def apply_runtime_rules(root: Path, label_file: str = "labels_raw.jsonl", traces: str = "traces.jsonl") -> dict:
    tr = {}
    for l in (root / "data" / traces).open():
        r = json.loads(l)
        tr[r["sample_id"]] = r
    labs = [json.loads(l) for l in (root / "data" / label_file).open()]
    changed = 0
    for r in labs:
        t = tr.get(r["sample_id"])
        if not r.get("valid") or t is None:
            continue
        new = runtime_label(r["task"], t["trace"])
        changed += new != r["runtime_label"]
        r["runtime_label"] = new
        if r["condition"] == "forced" and r.get("scrub"):
            sc = r["scrub"]
            if "trace_scrubbed" in t:
                sc["runtime_label"] = runtime_label(r["task"], t["trace_scrubbed"])
                sc["same_runtime_label"] = sc["runtime_label"] == new
                sc["verified"] = bool(sc["ok"] and sc["same_tests"] and sc["same_runtime_label"])
    with (root / "data" / label_file).open("w") as f:
        for r in labs:
            f.write(json.dumps(r) + "\n")
    return {"n": len(labs), "runtime_labels_changed": changed}
