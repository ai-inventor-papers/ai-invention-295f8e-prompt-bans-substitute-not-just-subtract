#!/usr/bin/env python3
"""S11 positioning: dated web/scholarly queries (aii-web-tools scripts) and regex greps of named papers, run in
parallel; raw outputs go to results/positioning_raw.json. The verdicts (occupies / adjacent / irrelevant) are written
by hand into results/positioning.json from these raw quotes."""
from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = Path(os.environ.get("AII_WEB_TOOLS_DIR", str(ROOT / "tools" / "aii-web-tools")))  # skill folder
PY = SKILL.parent / ".ability_client_venv" / "bin" / "python"

QUERIES = [
    ("scholarly", "denial prompting NeoCoder banned techniques code generation"),
    ("general", "NeoCoder denial prompting LLM creativity code generation NAACL 2025"),
    ("scholarly", "IFEvalCode instruction following code generation constraints"),
    ("general", "LLM code generation prohibited algorithm constraint compliance behavioral check 2025"),
    ("general", "counter-intuitive constraints code generation LLM fail 2026"),
    ("scholarly", "FunSearch online bin packing priority function heuristics"),
    ("general", "Herrmann Pallez 2510.27353 bin packing LLM heuristics simple baseline"),
    ("general", "BehaveSim behavioral similarity heuristics LLM automated heuristic design ICLR 2026"),
    ("general", "Zhang 2407.10873 understanding LLM automated heuristic design bin packing"),
    ("general", "LLM renamed algorithm forbidden instruction code obeys text not behavior"),
]
GREPS = [
    ("https://arxiv.org/abs/2407.09007", "denial|constraint|creativ"),
    ("https://arxiv.org/abs/2510.27353", "bin packing|baseline|simple"),
    ("https://arxiv.org/abs/2407.10873", "heuristic|bin packing|evolution"),
    ("https://arxiv.org/abs/2507.22462", "IFEvalCode|constraint|instruction"),
]


def run(cmd: list[str], timeout: int = 120) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + ("\nSTDERR: " + r.stderr[-500:] if r.returncode else "")
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def search(mode: str, q: str) -> dict:
    out = run([str(PY), str(SKILL / "scripts" / "aii_fast_web_search.py"), "--query", q, "--mode", mode,
               "--max-results", "8"])
    return {"kind": "search", "mode": mode, "query": q, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "output": out[:12000]}


def grep(url: str, pat: str) -> dict:
    out = run([str(PY), str(SKILL / "scripts" / "aii_fast_web_fetch.py"), "grep", "--url", url, "--pattern", pat,
               "--max-matches", "8", "--context-chars", "220"])
    return {"kind": "grep", "url": url, "pattern": pat, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "output": out[:12000]}


def main() -> None:
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(search, m, q) for m, q in QUERIES] + [ex.submit(grep, u, p) for u, p in GREPS]
        res = [f.result() for f in futs]
    (ROOT / "results" / "positioning_raw.json").write_text(json.dumps(res, indent=1))
    print("done", len(res))


if __name__ == "__main__":
    main()
