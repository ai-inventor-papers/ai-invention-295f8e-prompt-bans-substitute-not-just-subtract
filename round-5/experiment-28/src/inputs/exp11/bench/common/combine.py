"""Combined labels: runtime if it agrees with AST or AST says 'unknown'; on disagreement (or runtime 'unknown')
the blind judge (j1) decides.  Writes data/labels_combined.jsonl and the shared-schema per-sample rows."""

from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from .harness import extract_code
from .judge import Judge


def load_raw_samples(root: Path, names: list[str]) -> dict[str, dict]:
    out = {}
    for n in names:
        p = root / "data" / n
        if p.exists():
            for l in p.open():
                r = json.loads(l)
                out[r["sample_id"]] = r
    return out


def combine(root: Path, raw_names: list[str], label_file: str = "labels_raw.jsonl",
            out_file: str = "labels_combined.jsonl") -> list[dict]:
    raw = load_raw_samples(root, raw_names)
    labs = [json.loads(l) for l in (root / "data" / label_file).open()]
    judge = Judge(root)
    need = []
    for r in labs:
        if not r.get("valid"):
            continue
        a, rt = r["ast_label"], r["runtime_label"]
        if rt == "unknown" or (a != "unknown" and a != rt):
            need.append(r)
    logger.info(f"{len(need)}/{len(labs)} attempts need the judge (runtime unknown or runtime != AST)")
    recs = judge.label_many([("j1", r["task"], extract_code(raw[r["sample_id"]]["text"])) for r in need])
    jl = {r["sample_id"]: rec for r, rec in zip(need, recs)}
    out = []
    for r in labs:
        if not r.get("valid"):
            lab, src = "invalid", "extraction"
        elif r["sample_id"] in jl:
            rec = jl[r["sample_id"]]
            if rec.get("label"):
                lab, src = rec["label"], "judge"
            else:  # judge unavailable: fall back to runtime (or AST)
                lab = r["runtime_label"] if r["runtime_label"] != "unknown" else r["ast_label"]
                src = "runtime_fallback" if r["runtime_label"] != "unknown" else "ast_fallback"
        else:
            lab = r["runtime_label"]
            src = "runtime+ast" if r["ast_label"] == r["runtime_label"] else "runtime(ast_unknown)"
        r2 = dict(r, label=lab, labeller_source=src, judge_label=jl.get(r["sample_id"], {}).get("label"))
        out.append(r2)
    with (root / "data" / out_file).open("w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    return out


def write_shared_rows(root: Path, combined: list[dict], raw: dict[str, dict], by_cond: dict | None = None) -> None:
    by_cond = by_cond or {"baseline": "samples_pilot.jsonl", "forced": "samples_forced.jsonl"}
    files = {k: (root / "data" / v).open("w") for k, v in by_cond.items()}
    order = sorted(combined, key=lambda r: (r["condition"], r["task"], r.get("mode") or "", r.get("attempt_idx") or 0,
                                           r["sample_id"]))
    for r in order:
        s = raw[r["sample_id"]]
        code = extract_code(s["text"])
        row = {"task": r["task"], "condition": r["condition"], "template": None, "paraphrase_id": r.get("paraphrase_id"),
               "sample_id": r["sample_id"], "seed": r["seed"], "model": s["model"], "decoding": s["decoding"],
               "label": r["label"], "labeller_source": r["labeller_source"], "passed": bool(r.get("passed")),
               "code_sha256": r["code_sha256"], "code": code,
               "forced_mode": r.get("mode"), "round": r.get("round"), "attempt_idx": r.get("attempt_idx"),
               "ast_label": r.get("ast_label"), "runtime_label": r.get("runtime_label"), "judge_label": r.get("judge_label"),
               "finish_reason": r.get("finish_reason"), "sum_logprob": s.get("sum_logprob"),
               "n_tokens": len(s.get("token_ids") or [])}
        if r["condition"] == "forced":
            row["scrub_verified"] = (r.get("scrub") or {}).get("verified")
        f = files.get(r["condition"])
        if f:
            f.write(json.dumps(row) + "\n")
    for f in files.values():
        f.close()
