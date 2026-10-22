#!/usr/bin/env python3
"""Row access: join raw rows with the current-version labels, per engine.

Engine a: this artifact's own engine-a rows (REPRO, PN_check, any gap filling) take precedence; exp22's rows (the same
engine on the same slots, relabelled under the current labeller: data/iter4_relabelled.jsonl) fill every other slot
when results/repro_bytes.json shows byte identity (source = 'exp22_reused'); exp19's PN_a1/PN_a2 rows are used for
engine-a PN when the exp19 PN byte check passes (labels: exp19's, T2 re-gated like every other row).
"""

from __future__ import annotations

import time
from typing import Any

import c6  # noqa: F401
from c6 import E19, E22, DATA, LABELS, RAW_DIR, RESULTS, read_json, read_jsonl, row_key

JOIN_FIELDS = ("engine", "task", "arm", "template", "sample_id", "family", "alpha", "direction_seed", "stage",
               "n_tokens", "finish_reason", "B", "overflow_at_step", "prompt_sha256", "realised_disp", "seed")


def _labels() -> dict[str, dict[str, Any]]:
    return {l["key"]: l for l in read_jsonl(LABELS)}


def engine_raw(engine: str) -> list[dict[str, Any]]:
    return read_jsonl(RAW_DIR / f"raw_{engine}.jsonl")


def joined(engine: str, task: str | None = None, labels: dict | None = None) -> list[dict[str, Any]]:
    labels = labels if labels is not None else _labels()
    out = []
    for r in engine_raw(engine):
        if task and r["task"] != task:
            continue
        l = labels.get(row_key(engine, r))
        if l is None:
            continue
        out.append({**{k: r.get(k) for k in JOIN_FIELDS}, "label": l["label"], "passed": bool(l.get("passed")),
                    "valid": bool(l.get("valid")), "code_sha256": l.get("code_sha256"),
                    "labeller_source": l.get("labeller_source"), "source": "this_run"})
    return out


def exp22_rows_relabelled(task: str) -> list[dict[str, Any]]:
    rel = {l["key"]: l for l in read_jsonl(DATA / "iter4_relabelled.jsonl") if l["task"] == task}
    out = []
    for r in read_jsonl(E22 / "samples_raw.jsonl"):
        if r["task"] != task or r["family"] not in ("TWIN", "POP"):
            continue
        k = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        l = rel.get(k)
        if l is None:
            continue
        out.append({"engine": "a", **{x: r.get(x) for x in ("task", "arm", "template", "sample_id", "family", "alpha",
                                                           "direction_seed", "stage", "n_tokens", "finish_reason",
                                                           "prompt_sha256", "seed")},
                    "B": 20, "overflow_at_step": None, "realised_disp": None, "label": l["label"],
                    "passed": bool(l.get("passed")), "valid": bool(l.get("valid")), "code_sha256": l.get("code_sha256"),
                    "labeller_source": "exp22 (T2 re-gated)", "source": "exp22_reused"})
    return out


def exp19_pn_rows(task: str) -> list[dict[str, Any]]:
    from regate_rules import apply_t2
    import sys
    from c6 import V22
    sys.path.insert(0, str(V22 / "inputs" / "exp8" / "suite"))
    from labeller.combine import combine, needs_judge

    out = []
    for r in read_jsonl(E19 / "samples.jsonl"):
        if r["task"] != task or r["arm"] not in ("PN_a1", "PN_a2"):
            continue
        lab = r["label"]
        if task == "T2" and lab != "invalid" and r.get("code") not in (None, "None"):
            rl, _ = apply_t2(r["runtime_label"], r["code"])
            al, _ = apply_t2(r["ast_label"], r["code"])
            j = {"label": r["judge_label"]} if r.get("judge_label") not in (None, "None") else None
            lab = "disputed" if (needs_judge(rl, al) and not j) else combine(rl, al, j)[0]
        out.append({"engine": "a", "task": task, "arm": r["arm"], "template": r["template"],
                    "sample_id": int(r["slot"]), "family": "PN", "alpha": float(r["alpha"]),
                    "direction_seed": int(r["direction_seed"]), "stage": "exp19", "n_tokens": int(r["n_new_tokens"]),
                    "finish_reason": r["finish_reason"], "B": 20, "overflow_at_step": None,
                    "prompt_sha256": r["prompt_sha256"], "realised_disp": None, "seed": None, "label": lab,
                    "passed": str(r["passed"]) == "True", "valid": str(r["valid"]) == "True",
                    "code_sha256": r.get("code_sha256"), "labeller_source": "exp19 (T2 re-gated)",
                    "source": "exp19_reused"})
    return out


def engine_rows(engine: str, task: str, labels: dict | None = None, allow_reuse: bool = True) -> list[dict[str, Any]]:
    """All usable rows of one engine and task; slot keys are unique (own rows win)."""
    own = joined(engine, task, labels)
    if engine != "a" or not allow_reuse:
        return own
    rep = read_json(RESULTS / "repro_bytes.json") if (RESULTS / "repro_bytes.json").exists() else {}
    seen = {(r["template"], r["arm"], int(r["sample_id"])) for r in own}
    out = list(own)
    if rep.get("reuse_exp22"):
        for r in exp22_rows_relabelled(task):
            k = (r["template"], r["arm"], int(r["sample_id"]))
            if k not in seen:
                out.append(r)
                seen.add(k)
    if rep.get("reuse_exp19_pn"):
        for r in exp19_pn_rows(task):
            k = (r["template"], r["arm"], int(r["sample_id"]))
            if k not in seen:
                out.append(r)
                seen.add(k)
    return out


def wait_labels(engine: str, task: str, timeout: float = 1200.0, poll: float = 15.0) -> int:
    """Block until every raw row of (engine, task) has a label; returns the number still missing at the end."""
    from loguru import logger

    t0 = time.time()
    while True:
        lab = {l["key"] for l in read_jsonl(LABELS)}
        missing = [r for r in engine_raw(engine) if r["task"] == task and row_key(engine, r) not in lab]
        if not missing or time.time() - t0 > timeout:
            if missing:
                logger.warning(f"label wait timed out: {len(missing)} rows of {engine}/{task} unlabelled")
            return len(missing)
        logger.info(f"waiting for {len(missing)} labels of {engine}/{task}")
        time.sleep(poll)
