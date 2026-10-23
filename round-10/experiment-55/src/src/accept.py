#!/usr/bin/env python3
"""Stage 1.5 ACCEPTANCE pipeline (shared by the factorial set, the top-ups, the survivors and the covert set).

Per program: last ```python fence (iteration 8's extract_last_fence) -> 48-case suite (tests.json within limits.json)
AND 41-case suite (hidden_tests_t1.json), both 100% (iteration 8's harness, evaluations cached by code sha256 in
data/program_eval_cache.jsonl, seeded with iteration 9's cache: same harness files, byte-identical) -> SCRUB (E46
programs.scrub: docstrings and comments dropped, algorithm-naming identifiers renamed, alias literals replaced) ->
both suites again on the scrubbed code -> alias audit (0 hits of the catalogue alias regex) -> INSTRUMENT
(src/instrument.py, on the scrubbed code; cached in data/instrument_cache.jsonl) -> dedupe (scrubbed sha256, then AST
4-gram Jaccard >= 0.95 against every earlier kept program, keep the first in (round, slot) order).
Factorial acceptance: measured (disc, cont) == requested cell -> accept; == another planned cell -> reassign (logged,
requested_cell kept); else reject. PROBE programs are accepted into PROBE when measured LEV x DEQ.

Usage: python src/accept.py factorial
"""

from __future__ import annotations

import ast
import multiprocessing as mp
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loguru import logger  # noqa: E402

import label_tp  # noqa: E402
import programs  # noqa: E402
from common import append_jsonl, read_jsonl, sha256_text, utc_now, write_jsonl  # noqa: E402
from tpg2 import (DATA, LOGS, REQUESTED_CELLS, RESULTS, cell_dc, forbidden_regex, write_json)  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "accept.log"), rotation="30 MB", level="DEBUG")

INST_CACHE = DATA / "instrument_cache.jsonl"
N_WORKERS = 6
label_tp.WORKERS = N_WORKERS
PLANNED = {cell_dc(c): c for c in REQUESTED_CELLS}
FORBID = forbidden_regex()


def shingles(code: str) -> set[tuple[str, ...]]:
    try:
        seq = [type(n).__name__ for n in ast.walk(ast.parse(code))]
    except SyntaxError:
        return set()
    return {tuple(seq[i:i + 4]) for i in range(len(seq) - 3)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def measure_all(codes: list[str]) -> dict[str, dict[str, Any]]:
    import instrument

    cache = {r["key"]: r["m"] for r in read_jsonl(INST_CACHE)}
    todo = {}
    for c in codes:
        k = sha256_text(c)
        if k not in cache:
            todo[k] = c
    logger.info(f"instrument: {len(set(map(sha256_text, codes)))} unique, {len(todo)} to run")
    if todo:
        with ProcessPoolExecutor(max_workers=N_WORKERS, mp_context=mp.get_context("spawn")) as ex:
            futs = [ex.submit(instrument.measure_worker, (k, c)) for k, c in todo.items()]
            for n, f in enumerate(as_completed(futs), 1):
                k, m = f.result()
                cache[k] = m
                append_jsonl(INST_CACHE, {"key": k, "m": m, "utc": utc_now()})
                if n % 25 == 0 or n == len(futs):
                    logger.info(f"instrument {n}/{len(futs)}")
    return cache


def pipeline(rows: list[dict[str, Any]], code_field: str | None = "content") -> list[dict[str, Any]]:
    """Adds code, suites, scrubbed code, scrubbed suites, alias audit and instrument fields to every row."""
    for r in rows:
        if code_field == "content":
            code, how = label_tp.extract_last_fence(r.get("content"))
        else:
            code, how = r.get(code_field), "given"
        r["code"], r["extract"] = code, how
        r["code_sha256"] = sha256_text(code) if code else None
    codes = [r["code"] for r in rows if r["code"]]
    ev = label_tp.evaluate_unique(codes) if codes else {}
    for r in rows:
        if not r["code"]:
            r["valid"], r["reject"] = False, "no_code"
            continue
        e = ev[r["code_sha256"]]
        r["passed_48"], r["passed_41"] = bool(e.get("passed")), bool(e.get("passed_exp2"))
        r["n_passed_48"] = e.get("n_passed")
        if not (r["passed_48"] and r["passed_41"]):
            r["valid"], r["reject"] = False, "fails_suite_raw"
            continue
        try:
            sc, rmap = programs.scrub(r["code"])
        except (SyntaxError, ValueError, RecursionError) as ex:
            r["valid"], r["reject"] = False, f"scrub_error:{type(ex).__name__}"
            continue
        r["scrubbed"], r["rename_map"] = sc, rmap
        r["scrubbed_sha256"] = sha256_text(sc)
        r["alias_hits_after_scrub"] = [m.group(0) for m in programs.ALIAS_RE.finditer(sc)][:5]
        r["extended_forbidden_hits_after_scrub"] = sorted({m.group(0).lower() for m in FORBID.finditer(sc)})[:8]
    scs = [r["scrubbed"] for r in rows if r.get("scrubbed")]
    ev2 = label_tp.evaluate_unique(scs) if scs else {}
    for r in rows:
        if not r.get("scrubbed"):
            continue
        e = ev2[r["scrubbed_sha256"]]
        r["scrubbed_passed_48"], r["scrubbed_passed_41"] = bool(e.get("passed")), bool(e.get("passed_exp2"))
        if not (r["scrubbed_passed_48"] and r["scrubbed_passed_41"]):
            r["valid"], r["reject"] = False, "fails_suite_scrubbed"
        elif r["alias_hits_after_scrub"]:
            r["valid"], r["reject"] = False, "alias_after_scrub"
        else:
            r["valid"] = True
    ok = [r["scrubbed"] for r in rows if r.get("valid")]
    meas = measure_all(ok) if ok else {}
    for r in rows:
        if r.get("valid"):
            m = meas[r["scrubbed_sha256"]]
            r["disc"], r["cont"], r["fine"] = m["disc"], m["cont"], m.get("fine")
            r["instrument"] = {k: m.get(k) for k in ("tracer_order_class", "tracer_fine", "p_mono", "level_cover",
                                                     "p_lifo", "revisit_share", "sweep_probes", "repush_probes",
                                                     "relaxation_ast", "rng_diff_probes", "rng_nondet_probes",
                                                     "goal_diff_pairs", "goal_early_share", "coord_key",
                                                     "coord_share", "lev_assign_p_mono", "container_votes",
                                                     "container_share", "ast_hint", "n_informative", "id_share",
                                                     "bidir_share", "fifo_flag", "n_valid_paths")}
    return rows


def dedupe(rows: list[dict[str, Any]], key=lambda r: (r.get("round", 0), r.get("slot", 0))) -> None:
    kept_sha: set[str] = set()
    kept_sh: list[tuple[str, set]] = []
    for r in sorted([r for r in rows if r.get("valid")], key=key):
        sh = shingles(r["scrubbed"])
        if r["scrubbed_sha256"] in kept_sha:
            r["valid"], r["reject"], r["duplicate_of"] = False, "duplicate_exact", r["scrubbed_sha256"][:16]
            continue
        dup = next((u for u, s in kept_sh if jaccard(sh, s) >= 0.95), None)
        if dup:
            r["valid"], r["reject"], r["duplicate_of"] = False, "duplicate_ast_jaccard_0.95", dup
            continue
        kept_sha.add(r["scrubbed_sha256"])
        kept_sh.append((r["uid"], sh))


def stage_factorial() -> None:
    raw = read_jsonl(DATA / "raw_factorial.jsonl")
    for r in raw:
        r["uid"] = f"F|{r['cell']}|r{r['round']}|{r['slot']}"
        r["requested_cell"] = r["cell"]
    rows = pipeline(raw)
    dedupe(rows)
    for r in rows:
        if not r.get("valid"):
            r["accepted"] = False
            continue
        req = r["requested_cell"]
        meas = (r["disc"], r["cont"])
        if req == "PROBE":
            r["accepted"] = meas == ("LEV", "DEQ")
            r["cell"] = "PROBE"
            if not r["accepted"]:
                r["reject"] = f"measured_{meas[0]}_{meas[1]}"
        elif meas == cell_dc(req):
            r["accepted"], r["cell"] = True, req
        elif meas in PLANNED:
            r["accepted"], r["cell"], r["reassigned"] = True, PLANNED[meas], True
        else:
            r["accepted"], r["reject"] = False, f"measured_{meas[0]}_{meas[1]}"
    write_jsonl(DATA / "factorial.jsonl", rows)
    by = defaultdict(Counter)
    for r in rows:
        by[r["requested_cell"]]["calls"] += 1
        by[r["requested_cell"]]["valid"] += int(bool(r.get("valid")))
        if r.get("accepted"):
            by[r["cell"]]["accepted"] += 1
            by[r["cell"]]["accepted_reassigned_in"] += int(bool(r.get("reassigned")))
        else:
            by[r["requested_cell"]]["reject:" + str(r.get("reject"))] += 1
        if r.get("valid"):
            by[r["requested_cell"]][f"measured:{r['disc']}_{r['cont']}"] += 1
    summ = {c: dict(v) for c, v in sorted(by.items())}
    write_json(RESULTS / "acceptance_factorial.json", {"by_cell": summ, "n_rows": len(rows), "utc": utc_now()})
    for c, v in summ.items():
        logger.info(f"{c:10s} calls {v.get('calls', 0):3d} valid {v.get('valid', 0):3d} accepted "
                    f"{v.get('accepted', 0):3d} | " + ", ".join(f"{k}={n}" for k, n in v.items()
                                                                  if k.startswith('measured:'))[:200])


if __name__ == "__main__":
    if sys.argv[1] == "factorial":
        stage_factorial()
