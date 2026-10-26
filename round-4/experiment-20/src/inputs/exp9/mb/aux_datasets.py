#!/usr/bin/env python3
"""Uses of the declared dependency beyond the neutral-noun bank (all ten datasets of art_j3Rm_lr2nzR6):

* CORPUS ladder (leetcodedataset, mercury, thealgorithms_python, kodcode_algorithmic, xlcost_python): how often public
  Python code / problem text names each catalogue algorithm (alias lexicon, one count per document). It gives an extra
  external-popularity forecast over survivors, committed with the five planned forecasts (an addition to the plan).
* External T2 landing (llm_creativity): another model family's blind-judged T02 labels, beside our T2 baseline.
* Textbook canon (clrs_text): which catalogue algorithms appear among the CLRS-30 execution traces.
* Harness screen check (humanevalplus, enamel): the stdlib-only candidate interpreter (-I -S) and the forbidden-import
  screen on 2 x 164 canonical solutions (compile + definition exec): screen false positives and crash rate.
"""

from __future__ import annotations

import ast
import collections
import json
import re
import subprocess
from typing import Any

from loguru import logger

from common import DS_FILE, MODES, RESULTS_DIR, write_json

FAMILY_RE = {
    "bfs": r"\b(bfs|breadth[\s_-]?first)\b", "dfs": r"\b(dfs|depth[\s_-]?first)\b",
    "bibfs": r"bidirectional[\s_-]?(bfs|breadth)", "iddfs": r"\b(iddfs|iterative[\s_-]?deepening)\b",
    "astar": r"(\ba\*|\ba[\s_-]?star\b|\bastar\b)", "gbfs": r"(greedy[\s_-]?best[\s_-]?first|best[\s_-]?first[\s_-]?search)",
    "dijkstra_unit": r"\bdijkstra", "idastar": r"(\bida\*|\bida[\s_-]?star\b)", "jps": r"(\bjps\b|jump[\s_-]?point)",
    "biastar": r"bidirectional[\s_-]?(a\*|a[\s_-]?star)", "dijkstra": r"\bdijkstra",
    "bf_spfa": r"(bellman[\s_-]?ford|\bspfa\b)", "bidijkstra": r"bidirectional[\s_-]?dijkstra",
    "floyd": r"floyd[\s_-]?warshall|\bfloyd\b", "dial": r"(\bdial'?s?\b[\s_-]?(algorithm)?|bucket[\s_-]?queue)",
}
CORPORA = {"leetcodedataset": ("input", "output"), "mercury": ("output",), "thealgorithms_python": ("input",),
           "kodcode_algorithmic": ("input", "output"), "xlcost_python": ("input", "output")}


def stage_aux() -> None:
    data = json.loads(DS_FILE.read_text())
    ds = {d["dataset"]: d["examples"] for d in data["datasets"]}
    del data
    out: dict[str, Any] = {"source": "art_j3Rm_lr2nzR6 full_data_out.json (10 datasets)"}
    # CORPUS ladder
    counts = {t: collections.Counter() for t in MODES}
    per_corpus = {}
    for name, fields in CORPORA.items():
        c = collections.Counter()
        for e in ds[name]:
            if str(e.get("metadata_duplicate_of")) not in ("None", "", "null"):
                continue
            text = " ".join(str(e.get(f) or "") for f in fields).lower()
            for alg, pat in FAMILY_RE.items():
                if re.search(pat, text, re.I):
                    c[alg] += 1
        per_corpus[name] = {"n_docs": len(ds[name]), "counts": dict(c)}
        for t in MODES:
            for alg in MODES[t]:
                counts[t][alg] += c.get(alg, 0)
    out["corpus_counts"] = {t: dict(counts[t]) for t in MODES}
    out["corpus_per_source"] = per_corpus
    # external T2 landing
    lc = collections.Counter(e["output"] for e in ds["llm_creativity"]
                             if str(e.get("metadata_excluded_from_headline")) != "True")
    out["llm_creativity_t02_labels"] = dict(lc)
    out["llm_creativity_by_strategy"] = {s: dict(collections.Counter(e["output"] for e in ds["llm_creativity"]
                                                                     if e.get("metadata_strategy") == s))
                                         for s in sorted({e.get("metadata_strategy") for e in ds["llm_creativity"]})}
    # CLRS canon
    clrs = collections.Counter(e["metadata_algorithm"] for e in ds["clrs_text"])
    canon_map = {"bfs": ["bfs"], "dfs": ["dfs"], "dijkstra": ["dijkstra"], "dijkstra_unit": ["dijkstra"],
                 "bf_spfa": ["bellman_ford"], "floyd": ["floyd_warshall"]}
    out["clrs_algorithms"] = dict(clrs)
    out["clrs_canon"] = {t: {a: any(x in clrs for x in canon_map.get(a, [])) for a in MODES[t]} for t in MODES}
    # harness screen check on canonical solutions
    from tasks.sandbox_tests import screen  # noqa: PLC0415  (stdlib-only module)
    from tasks.harness import SYS_PY

    res = {}
    for name in ("humanevalplus", "enamel"):
        n = ok_compile = screened = exec_ok = 0
        for e in ds[name]:
            code = e["output"]
            n += 1
            try:
                ast.parse(code)
                ok_compile += 1
            except SyntaxError:
                continue
            kind, _ = screen(code)
            screened += int(kind is not None)
            if kind is None:
                p = subprocess.run([SYS_PY, "-I", "-S", "-c", code], capture_output=True, text=True, timeout=20)
                exec_ok += int(p.returncode == 0)
        res[name] = {"n": n, "parse_ok": ok_compile, "screen_rejected": screened, "definition_exec_ok": exec_ok}
    out["harness_screen_check"] = res
    write_json(RESULTS_DIR / "aux_datasets.json", out)
    logger.info(f"aux: corpus counts {out['corpus_counts']}; llm_creativity {dict(lc)}; harness {res}")
