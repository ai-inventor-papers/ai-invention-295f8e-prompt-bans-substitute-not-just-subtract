#!/usr/bin/env python3
"""Label worker (CPU, concurrent with sampling): for every raw row of a unit whose stage-(i) build exists, extract the
program (chat rows: first ```python block; plain-completion rows: header + generation up to the closing fence), run the
hidden tests, the runtime labeller (primary) and the AST labeller; association rows are mapped to a mode with the
unit's alias lexicon (the default's own name excluded once the default is known; otherwise all modes).
Rows go to data/labels.jsonl keyed unit|template|arm|slot|model_tag. Disagreements are adjudicated later by the
blind judges (src/judge5.py); unresolved ones are 'disputed' (excluded from shares, counted).
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import DATA_DIR, LABELS, RAW, UNITS_DIR, append_jsonl, read_json, read_jsonl, setup_logging  # noqa: E402
from prompts5 import load_prompts  # noqa: E402
import units_extra  # noqa: E402,F401  (registers the P_/V_ cards)
from units_spec import UNITS, map_answer  # noqa: E402
from unitlib import extract_code, extract_plain, label_code, load_tests  # noqa: E402

N_WORKERS = 12


def row_key(r: dict) -> str:
    return f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"


def ready_units() -> set[str]:
    out = set()
    for u in UNITS:
        g = UNITS_DIR / u / "gate_stage_i.json"
        if g.exists() and read_json(g)["status"] == "PROVISIONAL":
            out.add(u)
    return out


_TESTS: dict[str, list] = {}
_PROMPTS: dict = {}


def label_row(r: dict) -> dict:
    u = r["unit"]
    base = {"key": row_key(r), "unit": u, "template": r["template"], "arm": r["arm"], "slot": r["slot"],
            "model_tag": r["model_tag"], "family": r["family"]}
    if r["family"] == "ASSOC":
        return {**base, "assoc_answer": r["text"][:300], "assoc_mapped_all": map_answer(u, r["text"]),
                "label": None, "passed": None, "valid": None, "labeller_source": "assoc_alias_lexicon"}
    if u[:2] in ("P_", "V_"):
        L = units_extra.label_bench(u, r["text"])
        code = extract_code(r["text"])
        return {**base, **L, "code": code, "label": L.get("label_pre"), "finish_reason": r.get("finish_reason"),
                "n_tokens": r.get("n_tokens")}
    if r["family"] in ("PLAIN", "PLAIN_EXTRA"):
        if not _PROMPTS:
            _PROMPTS.update(load_prompts())
        code = extract_plain(_PROMPTS[r["prompt_pid"]]["user_text"], r["text"])
    else:
        code = extract_code(r["text"])
    if u not in _TESTS:
        _TESTS[u] = load_tests(u)
    L = label_code(u, code, cases=_TESTS[u])
    out = {**base, **{k: v for k, v in L.items() if k != "trace_summary"}, "code": code,
           "finish_reason": r.get("finish_reason"), "n_tokens": r.get("n_tokens")}
    out["label"] = L.get("label_pre")
    return out


def run_worker(follow: bool = True, stop_file: Path | None = None, units: set[str] | None = None) -> None:
    t0 = time.time()
    n_total = 0
    while True:
        done = {r["key"] for r in read_jsonl(LABELS)}
        ready = ready_units() if units is None else units & ready_units()
        raw = [r for r in read_jsonl(RAW) if not r.get("engine_check") and r["unit"] in ready
               and row_key(r) not in done]
        if raw:
            # push-arm and twin rows first (confirmation-critical), then everything else
            raw.sort(key=lambda r: (0 if r["family"] in ("ESC", "TWIN", "GATE") else
                                    (1 if r["family"] in ("BASE", "PN", "T13") else 2)))
            for i in range(0, len(raw), 48):
                part = raw[i:i + 48]
                tb = time.time()
                with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
                    out = list(ex.map(label_row, part))
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['unit']}/{part[0]['arm']}...) in {time.time() - tb:.1f}s;"
                            f" total {n_total}; backlog {len(raw) - i - len(part)}")
        else:
            if not follow or (stop_file is not None and stop_file.exists()):
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label5")
    follow = "--once" not in sys.argv
    run_worker(follow=follow, stop_file=DATA_DIR / "STOP_LABELLER")
