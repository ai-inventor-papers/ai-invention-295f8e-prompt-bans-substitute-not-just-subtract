#!/usr/bin/env python3
"""Iteration-6 Step 0 (GEN_ART evaluation): repair the record, freeze the screen inputs, audit independently.

Stages: S0 setup + input hashing -> S1 re-timing (src/s1_retime.py, run before this script) -> S2 FREEZE
(frozen/*.json + commitments.log hash chain) -> S3 analyses 0a-0e -> S4 third-family blind adjudication
(src/s4_judge.py, run separately: `eval.py --stage judge`) -> S5 corrections, tables, figures, eval_out.json.
CPU only; no model is run. Usage:
  uv run --python .venv/bin/python eval.py --stage freeze     # S0 + S2 (needs retime/raw_times.json)
  uv run --python .venv/bin/python eval.py --stage analyse    # S3 (refuses to run without a verified chain)
  uv run --python .venv/bin/python eval.py --stage judge      # S4 (paid; at most USD 0.45)
  uv run --python .venv/bin/python eval.py --stage outputs    # S5
  uv run --python .venv/bin/python eval.py --stage all        # S0 + S2 + S3 + S5 (judge results reused if present)
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))

from common import REPORT, Inputs, canon, sha256_file, write_json  # noqa: E402
from load import load_units  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WS / "logs").mkdir(exist_ok=True)
logger.add(WS / "logs" / "eval.log", rotation="30 MB", level="DEBUG")

REPORT_TABLES = {"Table 174": 4058, "Table 196": 4419, "Table 197": 4439, "Table 203": 4525, "Table 206": 4579,
                 "Table 207": 4593, "Table 208": 4603, "Table 211": 4717, "Table 214": 4775, "Table 217": 4822,
                 "Table 126c": 3040, "Table 222": 4965}
REPORT_SECTIONS = ["## 4.10 ", "## 5.4 ", "## 5.5 ", "## 5.8 ", "## 5.10 ", "## 5.11 ", "## 5.12 ",
                   "# What we have learned so far"]


def report_index(inp: Inputs) -> dict:
    lines = inp.text("report", "current_report.md").splitlines()
    idx: dict = {"tables": {}, "sections": {}}
    for name in REPORT_TABLES:
        hits = [i + 1 for i, ln in enumerate(lines) if ln.startswith(f"**{name}.**")]
        if hits:
            s = hits[0]
            e = s
            while e < len(lines) and (e == s or lines[e].startswith("|") or not lines[e].strip()) and e - s < 60:
                e += 1
            idx["tables"][name] = {"caption_line": s, "end_line": e, "expected_line": REPORT_TABLES[name]}
    heads = [(i + 1, ln) for i, ln in enumerate(lines) if ln.startswith("#")]
    for key in REPORT_SECTIONS:
        hs = [h for h in heads if h[1].startswith(key)]
        if hs:
            s = hs[0][0]
            nxt = [h[0] for h in heads if h[0] > s and (h[1].startswith("## ") or h[1].startswith("# "))]
            idx["sections"][key.strip("# ").strip()] = {"start_line": s, "end_line": (nxt[0] - 1) if nxt else len(lines)}
    est = [i + 1 for i, ln in enumerate(lines) if ln.strip() == "**Established.**"]
    idx["established_lists"] = est
    return idx


def stage_freeze(inp: Inputs) -> None:
    import s2_freeze
    t0 = time.time()
    U = load_units(inp)
    write_json(WS / "results" / "report_index.json", report_index(inp))
    retime_p = WS / "retime" / "raw_times.json"
    if not retime_p.exists():
        raise FileNotFoundError("run src/s1_retime.py first (S1 must precede the freeze)")
    retime = json.loads(retime_p.read_text())
    res = s2_freeze.run(inp, U, retime)
    write_json(WS / "results" / "input_hashes.json", {"stage": "S0+S2", "files": inp.files})
    logger.info(f"S2 freeze done in {time.time() - t0:.0f}s; chain head {res['chain'][-1].split(' | ')[-1][:16]}")


def stage_analyse(inp: Inputs) -> None:
    import s3_analyses
    s3_analyses.run(inp)


def stage_judge(inp: Inputs) -> None:
    import s4_judge
    s4_judge.run(inp)


def stage_outputs(inp: Inputs) -> None:
    import s5_outputs
    s5_outputs.run(inp)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["freeze", "analyse", "judge", "outputs", "all"])
    a = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))
    inp = Inputs()
    t0 = time.time()
    if a.stage in ("freeze", "all"):
        stage_freeze(inp)
    if a.stage in ("analyse", "all"):
        stage_analyse(inp)
    if a.stage == "judge":
        stage_judge(inp)
    if a.stage in ("outputs", "all"):
        stage_outputs(inp)
    prev = json.loads((WS / "results" / "input_hashes.json").read_text()) if (WS / "results" / "input_hashes.json").exists() else {"files": {}}
    merged = {**prev.get("files", {}), **inp.files}
    write_json(WS / "results" / "input_hashes.json", {"stage": "cumulative", "files": merged,
                                                       "report_sha256": sha256_file(REPORT)})
    logger.info(f"stage {a.stage} finished in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
