"""0k: quote-verified positioning row for the one-token fork, and a dated, logged mini saturation search (M11).

collect() runs every fetch, grep and scholarly search through the aii-web-tools scripts (in parallel threads; each
call is an independent subprocess) and caches the raw text under audit/web/. assemble() builds positioning.json from
that cache and the executor's one-line verdicts. Nothing is trusted from earlier audits: their quotes are re-matched.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

from common import AUDIT, inp, read_jsonl, sha256_text, write_json

# the aii-web-tools skill lives beside the run store (<root>/.claude/skills); override with AII_SKILLS
from common import DEPS_ROOT  # noqa: E402

SKILL = Path(os.environ.get("AII_SKILLS", str(DEPS_ROOT.parents[3] / ".claude" / "skills"))) / "aii-web-tools"
PY = SKILL.parent / ".ability_client_venv" / "bin" / "python"
WEB = AUDIT / "web"

NEIGHBOURS = {
    "forking_paths": {"arxiv": "2412.07961", "row": 33, "claimed": "ICLR 2025", "name": "Forking Paths in Neural Text Generation (Bigelow et al.)"},
    "forking_fast": {"arxiv": "2608.19611", "row": None, "claimed": "arXiv v1 2026-08-20; NeurIPS 2026 virtual page", "name": "Forking Fast"},
    "hanna_ameisen": {"arxiv": "2604.12493", "row": 52, "claimed": "ICLR 2026", "name": "Latent Planning Emerges with Scale (Hanna and Ameisen)"},
    "nainani": {"arxiv": "2508.18098", "row": 11, "claimed": "arXiv preprint", "name": "Detecting and Characterizing Planning in Language Models (Nainani et al.)"},
    "ma_rui": {"arxiv": "2605.07984", "row": None, "claimed": "ICML 2026", "name": "Where's the Plan? (Ma and Rui)"},
    "jacopin": {"arxiv": "2609.18440", "row": 49, "claimed": "arXiv v1 2026-09-16", "name": "Planning or Improvisation? (Jacopin)"},
}
QUERIES = {
    "temperature_fork_margin": ["temperature sampling forking tokens margin language model diversity",
                                "fork tokens temperature decoding entropy branching LLM generation"],
    "das_algorithm_choice_code": ["distributed alignment search localization code generation algorithm choice",
                                  "causal intervention subspace which algorithm code language model generation"],
    "evaluator_search_novel_algorithms": ["evaluator-guided search novel algorithms LLM program search",
                                          "LLM evolutionary search new algorithms coding problems diversity"],
}
SEEDS = {
    "temperature_fork_margin": ["2604.09921", "2510.01218", "2309.02772"],
    "das_algorithm_choice_code": [],
    "evaluator_search_novel_algorithms": ["2610.19157", "2609.00077"],
}
NAMED_SEEDS = {"temperature_fork_margin": ["Lee 2025 temperature diversity forking"],
               "das_algorithm_choice_code": ["CDAS distribution-matching DAS ICLR 2026", "Before Reasoning Begins Qwen3-8B",
                                             "MIB mechanistic interpretability benchmark"],
               "evaluator_search_novel_algorithms": ["FunSearch mathematical discoveries program search",
                                                     "AlphaEvolve coding agent algorithmic discovery"]}


def _run(args: list[str], tag: str, timeout: int = 120) -> str:
    WEB.mkdir(parents=True, exist_ok=True)
    f = WEB / f"{tag}.txt"
    if f.exists() and f.stat().st_size > 50:
        return f.read_text()
    try:
        p = subprocess.run([str(PY), *args], capture_output=True, text=True, timeout=timeout)
        txt = p.stdout + ("\n[stderr]\n" + p.stderr[-500:] if p.returncode else "")
    except subprocess.TimeoutExpired:
        txt = "[timeout]"
    f.write_text(txt)
    return txt


def fetch(url: str, tag: str, chars: int = 8000) -> str:
    return _run([str(SKILL / "scripts" / "aii_fast_web_fetch.py"), "fetch", "--url", url, "--max-chars", str(chars)], tag)


def grep(url: str, pattern: str, tag: str) -> str:
    return _run([str(SKILL / "scripts" / "aii_fast_web_fetch.py"), "grep", "--url", url, "--pattern", pattern,
                 "--max-matches", "3", "--context-chars", "160", "-i"], tag)


def search(q: str, mode: str, tag: str) -> str:
    return _run([str(SKILL / "scripts" / "aii_fast_web_search.py"), "--query", q, "--mode", mode, "--max-results", "10"],
                tag)


def prior_quotes() -> dict[str, dict]:
    rows = read_jsonl(inp("art_OUuQUYQn5voE", "evidence/quotes_iter6.jsonl"))
    out = {}
    for k, n in NEIGHBOURS.items():
        hit = [r for r in rows if n["arxiv"] in json.dumps(r)]
        if hit:
            out[k] = hit[0]
    return out


def _pattern(quote: str) -> str:
    words = re.findall(r"[A-Za-z0-9\-']+", quote)[:9]
    return r"\W+".join(re.escape(w) for w in words)


def collect() -> dict[str, Any]:
    pq = prior_quotes()
    jobs = []
    for k, n in NEIGHBOURS.items():
        a = n["arxiv"]
        jobs.append(("fetch", f"https://arxiv.org/abs/{a}", f"abs_{a}"))
        if k in pq:
            pat = _pattern(pq[k]["quote"])
            jobs.append(("grep", f"https://arxiv.org/abs/{a}", f"grepabs_{a}", pat))
            jobs.append(("grep", pq[k]["url"], f"grephtml_{a}", pat))
    jobs.append(("search", "Forking Fast NeurIPS 2026", "general", "s_forkingfast_neurips"))
    jobs.append(("search", "Forking Paths in Neural Text Generation ICLR 2025 OpenReview", "general",
                 "s_forkingpaths_iclr"))
    for topic, qs in QUERIES.items():
        for i, q in enumerate(qs):
            jobs.append(("search", q, "scholarly", f"s_{topic}_{i}"))
    for topic, ids in SEEDS.items():
        for a in ids:
            jobs.append(("fetch", f"https://arxiv.org/abs/{a}", f"abs_{a}"))
    for topic, qs in NAMED_SEEDS.items():
        for i, q in enumerate(qs):
            jobs.append(("search", q, "general", f"n_{topic}_{i}"))
    t0 = time.time()

    def do(j):
        if j[0] == "fetch":
            return j[2], fetch(j[1], j[2])
        if j[0] == "grep":
            return j[2], grep(j[1], j[3], j[2])
        return j[3], search(j[1], j[2], j[3])

    with ThreadPoolExecutor(max_workers=12) as ex:
        res = dict(ex.map(do, jobs))
    logger.info(f"positioning: {len(jobs)} web calls in {time.time() - t0:.0f}s")
    log = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "jobs": [list(j) for j in jobs],
           "sha256": {k: sha256_text(v) for k, v in res.items()}}
    write_json(WEB / "collect_log.json", log)
    return res


def _hits(txt: str) -> list[dict]:
    out = []
    for m in re.finditer(r"^\s*\[?(\d+)\]?[.)]?\s+(.+?)\n\s*(?:URL:\s*)?(https?://\S+)", txt, re.M):
        out.append({"title": m.group(2).strip()[:200], "url": m.group(3).strip()})
    if not out:
        for m in re.finditer(r"(https?://\S+)", txt):
            out.append({"title": "", "url": m.group(1).rstrip(").,")})
    return out


def parse_abs(txt: str) -> dict:
    title = re.search(r"Title:\s*(.+)", txt)
    sub = re.findall(r"\[v(\d+)\]\s*([A-Z][a-z]{2},\s*\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})", txt)
    sub2 = re.search(r"Submitted on\s+(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})", txt)
    com = re.search(r"Comments:\s*\|?\s*(.+)", txt)
    t = title.group(1).strip() if title else None
    if not t:
        m = re.search(r"^#\s*(.+)$", txt, re.M)
        t = m.group(1).strip() if m else None
    return {"title": t, "versions": [f"v{v} {d}" for v, d in sub], "submitted": sub2.group(1) if sub2 else None,
            "comments": com.group(1).strip()[:200] if com else None, "fetched_chars": len(txt),
            "ok": len(txt) > 300 and "[timeout]" not in txt}


def first_abstract_sentence(txt: str) -> str | None:
    m = re.search(r"Abstract:?\s*(.+?\.)\s", txt, re.S)
    if not m:
        return None
    s = re.sub(r"\s+", " ", m.group(1)).strip()
    return s if 40 <= len(s) <= 400 else None
