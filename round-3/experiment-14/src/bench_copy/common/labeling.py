"""Label every pilot / forced attempt: extraction, hidden tests, AST label, runtime label, scrub check.

Output: data/labels_raw.jsonl (one row per attempt).  The judge pass (judge.py) fills combined labels later.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

from .astrules import ast_label
from .catalogue import TASKS
from .harness import code_sha, extract_code, run_tests, syntax_ok
from .probes import run_trace
from .rtrules import runtime_label
from .scrub import scrub_response
from .testgen import read_tests


def _trace_summary(tr: dict) -> dict:
    return {"error": tr.get("error"), "probe_errors": {k: v.get("error") for k, v in tr["probes"].items() if v.get("error")}}


def label_one(row: dict, cases: list[dict]) -> dict:
    t = row["task"]
    code = extract_code(row["text"])
    out = {"sample_id": row["sample_id"], "task": t, "condition": row["condition"], "mode": row.get("mode"),
           "paraphrase_id": row.get("paraphrase_id"), "round": row.get("round"), "attempt_idx": row.get("attempt_idx"),
           "seed": row["seed"], "finish_reason": row.get("finish_reason"), "code_sha256": code_sha(code),
           "extracted": code is not None}
    if code is None or not syntax_ok(code) or "def solve" not in code:
        out.update(valid=False, passed=False, ast_label="invalid", runtime_label="invalid")
        return out
    out["valid"] = True
    tr = run_tests(code, t, cases)
    out.update(passed=tr["passed"], n_pass=tr["n_pass"], n_cases=tr["n_cases"], first_fail=tr["first_fail"],
               load_error=tr["load_error"], statuses_sig="".join(s[0] for s in tr["statuses"]))
    out["ast_label"] = ast_label(t, code)
    trace = run_trace(code, t)
    out["runtime_label"] = runtime_label(t, trace)
    out["trace"] = _trace_summary(trace)
    if row["condition"] == "forced":
        s_text, s_code, info = scrub_response(row["text"], code)
        sc = {"changed": s_code != code, "ok": info["ok"], "renamed": info["renamed"],
              "comments_removed": info["comments_removed"], "docstrings_removed": info["docstrings_removed"]}
        if s_code != code and info["ok"]:
            tr2 = run_tests(s_code, t, cases)
            sc["same_tests"] = "".join(s[0] for s in tr2["statuses"]) == out["statuses_sig"]
            sc["runtime_label"] = runtime_label(t, run_trace(s_code, t))
            sc["same_runtime_label"] = sc["runtime_label"] == out["runtime_label"]
        elif s_code == code:
            sc["same_tests"] = True
            sc["same_runtime_label"] = True
        else:
            sc["same_tests"] = False
            sc["same_runtime_label"] = False
        sc["verified"] = bool(sc["ok"] and sc["same_tests"] and sc["same_runtime_label"])
        out["scrub"] = sc
    return out


def label_all(root: Path, sources: list[str], out_name: str = "labels_raw.jsonl", workers: int = 5) -> None:
    out_path = root / "data" / out_name
    done = set()
    if out_path.exists():
        done = {json.loads(l)["sample_id"] for l in out_path.open()}
    rows = []
    for s in sources:
        rows += [json.loads(l) for l in (root / "data" / s).open()]
    rows = [r for r in rows if r["sample_id"] not in done]
    cases = {t: read_tests(root / "bench" / c["task_id"] / "tests.jsonl") for t, c in TASKS.items()}
    logger.info(f"labelling {len(rows)} attempts with {workers} workers")
    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex, out_path.open("a") as f:
        futs = {ex.submit(label_one, r, cases[r["task"]]): r["sample_id"] for r in rows}
        for fu in as_completed(futs):
            try:
                res = fu.result()
            except Exception as e:  # noqa: BLE001 - record and continue; never silently drop
                logger.error(f"labelling failed for {futs[fu]}: {e}")
                continue
            f.write(json.dumps(res) + "\n")
            f.flush()
            n += 1
            if n % 200 == 0:
                logger.info(f"  labelled {n}/{len(rows)} in {time.time() - t0:.0f}s")
    logger.info(f"labelling done: {n} rows in {time.time() - t0:.0f}s")


def retest(root: Path, tasks: list[str], raw_names: list[str], label_file: str = "labels_raw.jsonl",
           workers: int = 5) -> dict:
    """Re-run the (extended) hidden tests for already-labelled attempts of the given tasks; updates pass status and
    the scrub same-tests check in place.  Labels are unaffected (they do not depend on the tests)."""
    raw = {}
    for n in raw_names:
        for l in (root / "data" / n).open():
            r = json.loads(l)
            raw[r["sample_id"]] = r
    labs = [json.loads(l) for l in (root / "data" / label_file).open()]
    cases = {t: read_tests(root / "bench" / TASKS[t]["task_id"] / "tests.jsonl") for t in tasks}
    todo = [r for r in labs if r["task"] in tasks and r.get("valid")]

    def one(r):
        s = raw[r["sample_id"]]
        code = extract_code(s["text"])
        tr = run_tests(code, r["task"], cases[r["task"]])
        upd = {"passed": tr["passed"], "n_pass": tr["n_pass"], "n_cases": tr["n_cases"], "first_fail": tr["first_fail"],
               "load_error": tr["load_error"], "statuses_sig": "".join(x[0] for x in tr["statuses"])}
        if r["condition"] == "forced" and r.get("scrub") and r["scrub"].get("changed") and r["scrub"].get("ok"):
            _, s_code, _ = scrub_response(s["text"], code)
            tr2 = run_tests(s_code, r["task"], cases[r["task"]])
            upd["scrub_same_tests"] = "".join(x[0] for x in tr2["statuses"]) == upd["statuses_sig"]
        return r["sample_id"], upd

    with ThreadPoolExecutor(workers) as ex:
        res = dict(ex.map(one, todo))
    changed = 0
    for r in labs:
        if r["sample_id"] in res:
            u = res[r["sample_id"]]
            changed += u["passed"] != r.get("passed")
            sst = u.pop("scrub_same_tests", None)
            r.update(u)
            if sst is not None:
                r["scrub"]["same_tests"] = sst
                r["scrub"]["verified"] = bool(r["scrub"]["ok"] and sst and r["scrub"].get("same_runtime_label"))
    with (root / "data" / label_file).open("w") as f:
        for r in labs:
            f.write(json.dumps(r) + "\n")
    return {"n_retested": len(res), "pass_status_changed": changed}
