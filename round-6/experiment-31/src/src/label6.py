#!/usr/bin/env python3
"""Label worker (CPU): for every raw row (vLLM and HF) of a unit whose stage-(i) build is PROVISIONAL, extract the
program (chat rows: first ```python block; plain-completion rows: docstring header + body up to the closing fence),
run the hidden tests, the runtime labeller (primary) and the AST labeller. Association rows are mapped to a mode with
the unit's alias lexicon; base-intent rows keep their sentence. Rows go to data/labels.jsonl keyed
unit|template|arm|slot|model_tag|src. Runtime/AST disagreements are adjudicated later by the blind judges
(src/gate6.py adjudicate_all); unresolved ones are 'disputed' (excluded from compositions, counted).
Usage: python src/label6.py [--units I1,I2] [--follow]
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import DATA_DIR, LABELS, RAW, RAW_HF, UNITS_DIR, append_jsonl, read_json, read_jsonl, setup_logging  # noqa
from prompts6 import load_prompts  # noqa: E402
from units_spec6 import UNITS, map_answer  # noqa: E402
from unitlib6 import extract_code, extract_plain, label_code, load_tests  # noqa: E402

N_WORKERS = 24
_TESTS: dict[str, list] = {}
_PROMPTS: dict = {}


def row_key(r: dict) -> str:
    src = "hf" if r.get("engine", "").startswith("hf") else "vllm"
    return f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}|{src}"


def ready_units() -> set[str]:
    out = set()
    for u in UNITS:
        g = UNITS_DIR / u / "gate_stage_i.json"
        if g.exists() and read_json(g)["status"] == "PROVISIONAL":
            out.add(u)
    return out


def family(arm: str) -> str:
    return arm.split("_")[0]


def label_row(r: dict) -> dict:
    u = r["unit"]
    base = {"key": row_key(r), "unit": u, "template": r["template"], "arm": r["arm"], "slot": r["slot"],
            "model_tag": r["model_tag"], "family": family(r["arm"]), "src": row_key(r).rsplit("|", 1)[1],
            "temperature": r.get("temperature"), "finish_reason": r.get("finish_reason"),
            "n_tokens": r.get("n_tokens"), "utc_row": r.get("utc")}
    if r["arm"].startswith("ASSOC_"):
        return {**base, "assoc_answer": r["text"][:300], "assoc_mapped_all": map_answer(u, r["text"]),
                "label": None, "passed": None, "valid": None, "labeller_source": "assoc_alias_lexicon"}
    if r["arm"] == "BINTENT":
        return {**base, "intent": r["text"].strip()[:400], "label": None, "passed": None, "valid": None,
                "labeller_source": "intent_text"}
    if r["arm"] == "PLAIN":
        if not _PROMPTS:
            _PROMPTS.update(load_prompts())
        code = extract_plain(_PROMPTS[r["prompt_pid"]]["user_text"], r["text"])
    else:
        code = extract_code(r["text"])
    if u not in _TESTS:
        _TESTS[u] = load_tests(u)
    L = label_code(u, code, cases=_TESTS[u])
    out = {**base, **{k: v for k, v in L.items() if k != "trace_summary"}, "code": code}
    out["label"] = L.get("label_pre")
    return out


def run(units: set[str] | None, follow: bool) -> None:
    t0 = time.time()
    n_total = 0
    while True:
        done = {r["key"] for r in read_jsonl(LABELS)}
        ready = ready_units() if units is None else (units & ready_units())
        raw = [r for r in read_jsonl(RAW) + read_jsonl(RAW_HF) if r["unit"] in ready and row_key(r) not in done
               and r["arm"] != "PAD" and not r.get("shadow")]
        if raw:
            raw.sort(key=lambda r: (0 if family(r["arm"]) in ("ESC", "PN", "GTN", "TWIN") else 1))
            for i in range(0, len(raw), 96):
                part = raw[i:i + 96]
                tb = time.time()
                with ThreadPoolExecutor(max_workers=N_WORKERS) as ex:
                    out = list(ex.map(label_row, part))
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['unit']}/{part[0]['arm']}...) in {time.time() - tb:.1f}s;"
                            f" total {n_total}; backlog {len(raw) - i - len(part)}")
        else:
            if not follow or (DATA_DIR / "STOP_LABELLER").exists():
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", default=None)
    ap.add_argument("--follow", action="store_true")
    a = ap.parse_args()
    setup_logging("label6")
    run(set(a.units.split(",")) if a.units else None, a.follow)


if __name__ == "__main__":
    main()
