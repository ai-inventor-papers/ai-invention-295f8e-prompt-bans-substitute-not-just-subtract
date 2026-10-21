#!/usr/bin/env python3
"""Labelling with the frozen exp11 bench labellers (one labeller for every arm).

label_one (extraction, hidden tests, AST labeller, runtime-trace labeller) runs in a thread pool (each call spawns
sandbox subprocesses); the combine rule is exp11's: runtime label when it agrees with AST or AST says 'unknown';
otherwise (or when runtime is 'unknown') the blind judge j1 (gemini-2.5-flash-lite, name-scrubbed code) decides;
judge unavailable -> runtime (or AST) fallback, flagged.  Identical code (same task, same sha256) reuses its labels.

Also S0.3: the labeller re-check on every gold-set program and every reference against gate.json.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

from common import (BENCH, DATA, LABELS, RESULTS, ROOT, TASK_ORDER, bench_import, read_jsonl, sha256_text,
                    task_dir, write_json, write_jsonl)

JUDGE_CAP_USD = 0.60
_LABEL_FIELDS = ["valid", "passed", "n_pass", "n_cases", "ast_label", "runtime_label", "load_error", "extracted",
                 "code_sha256", "statuses_sig"]


class Labeller:
    """Thread-pool labeller with a (task, code sha256) cache and a serialised judge pass."""

    def __init__(self, workers: int = 10):
        bench_import()
        from bench.common import judge as judge_mod
        from bench.common.testgen import read_tests

        judge_mod.PERSONAL_CAP = JUDGE_CAP_USD  # this artifact's judge cap (plan: USD 0.6)
        self.cases = {t: read_tests(task_dir(t) / "tests.jsonl") for t in TASK_ORDER}
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.lock = threading.Lock()
        self.judge_lock = threading.Lock()
        self.code_cache: dict[str, dict] = {}
        self.cache_path = LABELS / "code_cache.jsonl"
        LABELS.mkdir(parents=True, exist_ok=True)
        for r in read_jsonl(self.cache_path):
            self.code_cache[r["key"]] = r["lab"]
        self._judge = None
        logger.info(f"Labeller up: {workers} workers, {len(self.code_cache)} cached code labels")

    # ---------------------------------------------------------------- raw labelling (tests + AST + runtime)
    def _label_raw(self, row: dict) -> dict:
        from bench.common.harness import code_sha, extract_code
        from bench.common.labeling import label_one

        code = extract_code(row["text"])
        key = f"{row['task']}|{code_sha(code)}"
        with self.lock:
            hit = self.code_cache.get(key)
        if hit is not None:
            return dict(hit, cache_hit=True)
        r = {"text": row["text"], "task": row["task"], "condition": "iter3", "sample_id": row["sample_id"],
             "seed": row.get("seed"), "finish_reason": row.get("finish_reason")}
        out = label_one(r, self.cases[row["task"]])
        lab = {k: out.get(k) for k in _LABEL_FIELDS}
        lab["trace_error"] = (out.get("trace") or {}).get("error")
        with self.lock:
            self.code_cache[key] = lab
            with self.cache_path.open("a") as f:
                f.write(json.dumps({"key": key, "lab": lab}) + "\n")
        return dict(lab, cache_hit=False)

    def judge(self):
        if self._judge is None:
            from bench.common.judge import Judge

            self._judge = Judge(ROOT)
        return self._judge

    # ---------------------------------------------------------------- full labelling of a list of raw rows
    def label_rows(self, rows: list[dict], tag: str = "") -> list[dict]:
        """rows: raw sample rows with sample_id, task, text (+ any metadata).  Returns label rows (same order)."""
        from bench.common.harness import extract_code

        t0 = time.time()
        futs = [self.pool.submit(self._label_raw, r) for r in rows]
        labs = []
        for r, fu in zip(rows, futs):
            try:
                labs.append(fu.result())
            except Exception as e:  # noqa: BLE001 - recorded as an unlabelled row, never dropped silently
                logger.error(f"label failed {r['sample_id']}: {e!r}")
                labs.append({"valid": False, "passed": False, "ast_label": "invalid", "runtime_label": "invalid",
                             "label_error": repr(e)[:200]})
        need = [i for i, l in enumerate(labs) if l.get("valid") and (
            l["runtime_label"] == "unknown" or (l["ast_label"] != "unknown" and l["ast_label"] != l["runtime_label"]))]
        jl: dict[int, dict] = {}
        if need:
            with self.judge_lock:
                items = [("j1", rows[i]["task"], extract_code(rows[i]["text"])) for i in need]
                try:
                    recs = self.judge().label_many(items, concurrency=8)
                    # transient upstream rate limits (HTTP 429) are retried with backoff; budget refusals never are
                    for attempt in range(4):
                        retry = [k for k, rec in enumerate(recs) if not rec.get("label")
                                 and rec.get("error") not in ("budget", "aborted", "personal cap reached")]
                        if not retry or self.judge().aborted:
                            break
                        time.sleep(5 * (attempt + 1))
                        again = self.judge().label_many([items[k] for k in retry], concurrency=4)
                        for k, rec in zip(retry, again):
                            recs[k] = rec
                except Exception as e:  # noqa: BLE001 - judge outage -> runtime fallback (flagged)
                    logger.error(f"judge batch failed: {e!r}")
                    recs = [{"label": None, "error": repr(e)[:200]} for _ in items]
                jl = dict(zip(need, recs))
        out = []
        for i, (r, l) in enumerate(zip(rows, labs)):
            if not l.get("valid"):
                lab, src = "invalid", "extraction"
            elif i in jl:
                rec = jl[i]
                if rec.get("label"):
                    lab, src = rec["label"], "judge"
                else:
                    lab = l["runtime_label"] if l["runtime_label"] != "unknown" else l["ast_label"]
                    src = "runtime_fallback_judge_unavailable" if l["runtime_label"] != "unknown" else \
                        "ast_fallback_judge_unavailable"
            else:
                lab = l["runtime_label"]
                src = "runtime+ast" if l["ast_label"] == l["runtime_label"] else "runtime(ast_unknown)"
            meta = {k: v for k, v in r.items() if k not in ("text", "token_ids", "prompt_token_ids")}
            out.append({**meta, **{k: l.get(k) for k in _LABEL_FIELDS}, "label": lab, "labeller_source": src,
                        "judge_label": jl.get(i, {}).get("label"), "passed": bool(l.get("passed")),
                        "cache_hit": l.get("cache_hit")})
        n_j = len(need)
        logger.info(f"labelled {len(rows)} rows {tag} in {time.time() - t0:.0f}s ({n_j} judged; spend "
                    f"${self.judge().spent if self._judge else 0:.4f})")
        return out

    def submit(self, rows: list[dict], tag: str = "") -> Future:
        """Non-blocking: label in a helper thread (the GPU process keeps sampling)."""
        ex = ThreadPoolExecutor(max_workers=1)
        fu = ex.submit(self.label_rows, rows, tag)
        ex.shutdown(wait=False)
        return fu

    def spent(self) -> float:
        return self.judge().spent if self._judge else 0.0


def label_arm_file(lab: Labeller, raw_path: Path, out_path: Path, tag: str = "") -> list[dict]:
    """Label every row of a raw jsonl that is not yet in out_path; returns all label rows of out_path."""
    raw = read_jsonl(raw_path)
    done = {r["sample_id"] for r in read_jsonl(out_path)}
    todo = [r for r in raw if r["sample_id"] not in done]
    if todo:
        res = lab.label_rows(todo, tag or raw_path.name)
        write_jsonl(out_path, res, mode="a")
    return read_jsonl(out_path)


# ---------------------------------------------------------------------------------------- S0.3 re-check
def cohen_kappa(a: list[str], b: list[str]) -> float:
    from collections import Counter

    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / n ** 2
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def recheck(workers: int = 12) -> dict:
    lab = Labeller(workers=workers)
    report: dict[str, Any] = {"tasks": {}, "pass": True}
    for t in TASK_ORDER:
        tdir = task_dir(t)
        gate = json.loads((tdir / "gate.json").read_text())
        gold = read_jsonl(tdir / "gold_set.jsonl")
        refs = sorted((tdir / "references").glob("*.py"))
        rows = [{"sample_id": g["gold_id"], "task": t, "text": "```python\n" + g["code"] + "\n```"} for g in gold]
        rows += [{"sample_id": f"ref:{p.stem}", "task": t, "text": "```python\n" + p.read_text() + "\n```"}
                 for p in refs]
        res = lab.label_rows(rows, f"recheck {t}")
        g_res, r_res = res[:len(gold)], res[len(gold):]
        adj = [g["adjudicated"] for g in gold]
        rt = [r["runtime_label"] for r in g_res]
        ast = [r["ast_label"] for r in g_res]
        comb = [r["label"] for r in g_res]
        rt_vs_adj = sum(x == y for x, y in zip(rt, adj)) / len(gold)
        comb_vs_adj = sum(x == y for x, y in zip(comb, adj)) / len(gold)
        same_as_stored_rt = sum(x == g["runtime"] for x, g in zip(rt, gold)) / len(gold)
        same_as_stored_ast = sum(x == g["ast"] for x, g in zip(ast, gold)) / len(gold)
        ref_rt = sum(r["runtime_label"] == p.stem for r, p in zip(r_res, refs)) / len(refs)
        ref_ast = sum(r["ast_label"] == p.stem for r, p in zip(r_res, refs)) / len(refs)
        ref_pass = sum(bool(r["passed"]) for r in r_res) / len(refs)
        g_gate = gate["gold"]
        ok = (ref_rt == 1.0 and ref_ast == 1.0 and abs(rt_vs_adj - g_gate["runtime_vs_adjudicated"]) <= 0.02)
        report["tasks"][t] = {
            "n_gold": len(gold), "n_refs": len(refs), "runtime_vs_adjudicated": rt_vs_adj,
            "gate_runtime_vs_adjudicated": g_gate["runtime_vs_adjudicated"],
            "combined_vs_adjudicated": comb_vs_adj, "gate_combined_vs_adjudicated": g_gate["combined_vs_adjudicated"],
            "kappa_runtime_ast": cohen_kappa(rt, ast), "gate_kappa_runtime_ast": g_gate["kappa_runtime_ast"],
            "runtime_same_as_stored": same_as_stored_rt, "ast_same_as_stored": same_as_stored_ast,
            "ref_acc_runtime": ref_rt, "ref_acc_ast": ref_ast, "ref_pass_rate": ref_pass, "pass": ok,
            "mismatch_items": [{"id": g["gold_id"], "runtime_now": x, "runtime_stored": g["runtime"],
                                "adjudicated": g["adjudicated"]} for x, g in zip(rt, gold) if x != g["runtime"]],
            "ref_failures": [{"ref": p.stem, "runtime": r["runtime_label"], "ast": r["ast_label"],
                              "passed": r["passed"]} for r, p in zip(r_res, refs)
                             if r["runtime_label"] != p.stem or r["ast_label"] != p.stem or not r["passed"]]}
        report["pass"] = report["pass"] and ok
        logger.info(f"recheck {t}: rt_vs_adj {rt_vs_adj:.3f} (gate {g_gate['runtime_vs_adjudicated']:.3f}) "
                    f"refs rt {ref_rt:.2f} ast {ref_ast:.2f} pass {ref_pass:.2f} -> {'OK' if ok else 'FAIL'}")
    report["judge_spend_usd"] = lab.spent()
    write_json(RESULTS / "labeller_recheck.json", report)
    return report


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s0_recheck")
    rep = recheck()
    logger.info(f"labeller re-check overall: {'PASS' if rep['pass'] else 'FAIL'}")
