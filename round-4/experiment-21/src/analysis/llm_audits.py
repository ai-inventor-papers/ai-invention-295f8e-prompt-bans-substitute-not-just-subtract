#!/usr/bin/env python3
"""LLM audits (OpenRouter, spend ledger in results/costs.json) and dependency usage.

A7 judge audit: 20 thinking traces (5 per temperature, fixed draw) -> openai/gpt-4.1-mini names the FIRST approach
the trace proposes (same label set as the lexicon); agreement and Cohen's kappa against the lexicon. Cap USD 0.10.
A9 novelty audit: every CORRECT 'other' program -> two blind judges from different families (openai/gpt-4.1-mini,
google/gemini-2.5-flash-lite): NOVEL / CATALOGUE VARIANT / LABELLER MISS / DEGENERATE (+ named algorithm);
deepseek/deepseek-chat-v3.1 resolves disagreements; each program is shown with its AST-nearest known solution (the
472-solution index of exp18, rebuilt and cross-checked from the dependency dataset art_j3Rm_lr2nzR6). Cap USD 0.10.
The first HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget' stops the batch.
"""

from __future__ import annotations

import json
import os
import random
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import core  # noqa: E402
from cfg import DATA_DIR, RESULTS_DIR, read_jsonl, sha256_text, utc_now, write_json  # noqa: E402
from cfg4 import DEP_DATASET, FIRST_APPROACH_LEXICON, LEXICON_CAP, NOVELTY_CAP  # noqa: E402

# dependency art_j3Rm_lr2nzR6 (published as a sibling folder): one env var, default = the run-volume layout
DEP_DIR = Path(os.environ.get("DEP_DATASET_DIR", str(DEP_DATASET)))

BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
LEDGER = RESULTS_DIR / "costs.json"
CACHE = DATA_DIR / "llm_audit_cache.jsonl"
_LOCK = threading.Lock()
TASK_DESC = {"T2": "weighted directed shortest path (n nodes, weighted edges, distance from s to t)",
             "T1": "grid path finding (any valid path between two free cells of a grid)",
             "T03": "k-th smallest value of an integer list"}
CATALOGUE = {"T2": "dijkstra, bf_spfa (Bellman-Ford/SPFA), bidirectional dijkstra, dial (bucket queue), floyd_warshall, "
                   "a_star", "T1": "bfs, dfs, iddfs, bidirectional bfs, a_star/greedy best-first, dijkstra",
             "T03": "full_sort, size_k_heap, heapify_pop, quickselect, median_of_medians, counting_sort"}


class Ledger:
    def __init__(self) -> None:
        self.d = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"calls": 0, "usd": {}, "stopped": False}

    def spent(self, purpose: str) -> float:
        return float(self.d["usd"].get(purpose, 0.0))

    def add(self, purpose: str, usd: float) -> None:
        with _LOCK:
            self.d["usd"][purpose] = self.spent(purpose) + usd
            self.d["calls"] += 1
            self.d["utc"] = utc_now()
            write_json(LEDGER, self.d)


def _cache() -> dict[str, Any]:
    return {r["key"]: r for r in read_jsonl(CACHE)}


def call(model: str, prompt: str, purpose: str, cap: float, ledger: Ledger, max_tokens: int = 300) -> str | None:
    key = sha256_text(model + "|" + prompt)
    c = _cache()
    if key in c:
        return c[key]["text"]
    if ledger.d.get("stopped") or ledger.spent(purpose) >= cap:
        return None
    from openai import OpenAI

    cli = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"], timeout=90)
    try:
        r = cli.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0,
                                        max_tokens=max_tokens, extra_body={"usage": {"include": True}})
    except Exception as e:  # noqa: BLE001 - API errors are logged; a budget 403 stops every later call
        msg = str(e)
        logger.error(f"OpenRouter call failed ({model}): {msg[:200]}")
        if BUDGET_MSG in msg:
            ledger.d["stopped"] = True
            write_json(LEDGER, ledger.d)
        return None
    txt = r.choices[0].message.content or ""
    cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
    ledger.add(purpose, cost)
    with _LOCK:
        with open(CACHE, "a") as fh:
            fh.write(json.dumps({"key": key, "model": model, "purpose": purpose, "text": txt, "cost": cost,
                                 "utc": utc_now()}) + "\n")
    logger.debug(f"LLM {model} {purpose}: {txt[:120]!r} (${cost:.5f})")
    return txt


def _parse_label(txt: str | None, allowed: list[str]) -> str | None:
    if not txt:
        return None
    t = txt.strip().lower()
    try:
        j = json.loads(t[t.find("{"):t.rfind("}") + 1])
        v = str(j.get("label") or j.get("answer") or "").strip().lower()
        if v in allowed:
            return v
    except (ValueError, AttributeError):
        pass
    for a in allowed:
        if a in t:
            return a
    return "unparsed"


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")   # undefined when both raters use one label


# ------------------------------------------------------------------------------------------------ A7
def judge_first_approach(n: int = 20) -> dict[str, Any]:
    raw = [r for r in read_jsonl(DATA_DIR / "raw_thinking.jsonl") if r["task"] == "T2" and not r.get("repeat")]
    if not raw:
        return {"available": False}
    rng = random.Random(20261021)
    by_t: dict[float, list] = {}
    for r in raw:
        by_t.setdefault(r["temperature"], []).append(r)
    pick = []
    for t in sorted(by_t):
        pool = sorted(by_t[t], key=lambda r: (r["template"], r["sample_id"]))
        pick += rng.sample(pool, min(n // len(by_t), len(pool)))
    allowed = [name for name, _ in FIRST_APPROACH_LEXICON] + ["none"]
    led = Ledger()

    def one(r):
        txt = r["think_text"][:6000]
        prompt = ("Below is the beginning of a model's private reasoning for this coding task: "
                  f"{TASK_DESC['T2']}.\nWhich algorithm does the reasoning FIRST name or propose as the approach? "
                  f"Answer JSON {{\"label\": one of {allowed}}}. 'none' if no algorithm is named.\n\n"
                  f"<reasoning>\n{txt}\n</reasoning>")
        return _parse_label(call("openai/gpt-4.1-mini", prompt, "lexicon_audit", LEXICON_CAP, led, 50), allowed)
    with ThreadPoolExecutor(8) as ex:
        jl = list(ex.map(one, pick))
    lex = [r["first_approach"] or "none" for r in pick]
    pairs = [(a, b) for a, b in zip(lex, jl) if b and b != "unparsed"]
    out = {"available": True, "n": len(pick), "n_judged": len(pairs),
           "agreement": sum(a == b for a, b in pairs) / max(len(pairs), 1),
           "kappa": kappa([a for a, _ in pairs], [b for _, b in pairs]),
           "kappa_note": "undefined (NaN) when both raters give a single label to every trace (chance agreement 1)",
           "rows": [{"template": r["template"], "sample_id": r["sample_id"], "T": r["temperature"], "lexicon": a,
                     "judge": b} for r, a, b in zip(pick, lex, jl)], "model": "openai/gpt-4.1-mini",
           "usd": led.spent("lexicon_audit")}
    write_json(RESULTS_DIR / "first_approach_judge_audit.json", out)
    logger.info(f"A7 judge audit: agreement {out['agreement']:.2f}, kappa {out['kappa']:.2f} (n={len(pairs)})")
    return out


# ------------------------------------------------------------------------------------------------ dependency
def known_solution_pool() -> dict[str, Any]:
    """exp18's 472-solution index (task-tagged), cross-checked against the dependency dataset: every dependency
    example whose metadata_bench_task maps to T2 (T02), T03 or T1 (T01) is counted per source dataset."""
    idx = read_jsonl(ROOT / "inputs/exp18/known_solutions.jsonl")
    pool = {t: [r["code"] for r in idx if r.get("task") == t and r.get("code")] for t in ("T2", "T03", "T1")}
    usage: dict[str, Any] = {"index": "inputs/exp18/known_solutions.jsonl", "pool_sizes": {t: len(v) for t, v in
                                                                                           pool.items()}}
    full = DEP_DIR / "full_data_out.json"
    if full.exists():
        d = json.loads(full.read_text())
        per: dict[str, Any] = {}
        t02_labels: Counter = Counter()
        noun = None
        for ds in d["datasets"]:
            name = ds["dataset"]
            c: Counter = Counter()
            for ex in ds["examples"]:
                bt = str(ex.get("metadata_bench_task") or "")
                tag = "T2" if bt.startswith("T02") else "T03" if bt.startswith("T03") else "T1" if bt.startswith("T01") else None
                if tag:
                    c[tag] += 1
                    if name == "llm_creativity" and tag == "T2":
                        t02_labels[ex.get("output")] += 1
                if name == "concreteness_norms" and str(ex.get("input", "")).strip().lower() == "man":
                    noun = {k: v for k, v in ex.items() if k.startswith("metadata_")}
            per[name] = {"n_examples": len(ds["examples"]), "mapped_to_this_artifact": dict(c)}
        usage["dependency_dataset"] = "art_j3Rm_lr2nzR6 full_data_out.json"
        usage["per_dataset"] = per
        usage["llm_creativity_T02_label_distribution"] = dict(t02_labels.most_common())
        usage["twin_noun_man_concreteness_entry"] = noun
        usage["how_used"] = {
            "leetcodedataset/mercury/thealgorithms_python/kodcode_algorithmic/xlcost_python": "known-solution pool for "
            "the A9 nearest-known-solution pass (LeetCode 743 = T2, 215 = T03, 1091 = T1-related)",
            "llm_creativity": "external reference composition of T02 (= T2) labels from another LLM study",
            "concreteness_norms": "provenance of the neutral twin noun 'man' used in every twin prompt",
            "clrs_text/humanevalplus/enamel": "not applicable here (tracer tests / harness validation / efficiency "
                                              "references for other tasks); loaded and counted only"}
        del d
    write_json(RESULTS_DIR / "dependency_usage.json", usage)
    return pool


# ------------------------------------------------------------------------------------------------ A9
def novelty_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pool = known_solution_pool()
    cand = [r for r in rows if r.get("label") == "other" and r.get("passed") and r.get("code")
            and not r["arm"].startswith(("SMOKE", "PAD", "GB_PAD", "TPN_PAD"))]
    seen, uniq = set(), []
    for r in cand:
        h = sha256_text(r["task"] + r["code"])
        if h not in seen:
            seen.add(h)
            uniq.append(r)
    led = Ledger()
    classes = ["novel", "catalogue variant", "labeller miss", "degenerate"]

    def nearest(r):
        sh = core.shingles(r["code"])
        best = (-1.0, None)
        for c in pool.get(r["task"], []):
            j = core.jaccard(sh, core.shingles(c))
            if j == j and j > best[0]:
                best = (j, c)
        return best

    def judge(r, model):
        prompt = (f"Task: {TASK_DESC[r['task']]}. Known catalogue of algorithms: {CATALOGUE[r['task']]}.\n"
                  "Classify the PROGRAM below (it passes the hidden tests). Classes: 'novel' (a correct algorithm not "
                  "in the catalogue and not a standard textbook variant), 'catalogue variant' (a known algorithm or a "
                  "standard variant of one), 'labeller miss' (it IS one of the catalogue algorithms), 'degenerate' "
                  "(brute force or a trick that only works on these tests). Respond with ONLY a JSON object "
                  "{\"label\": class, \"algorithm\": name} and no other text.\n\n```python\n" + r["code"][:6000] +
                  "\n```")
        return call(model, prompt, "novelty_audit", NOVELTY_CAP, led, 300)
    out_rows = []
    for r in uniq:
        a = judge(r, "openai/gpt-4.1-mini")
        b = judge(r, "google/gemini-2.5-flash-lite")
        la, lb = _parse_label(a, classes), _parse_label(b, classes)
        final = la if la == lb else _parse_label(judge(r, "deepseek/deepseek-chat-v3.1"), classes)
        j, near = nearest(r)
        out_rows.append({"task": r["task"], "arm": r["arm"], "template": r["template"], "sample_id": r["sample_id"],
                         "judge_a": la, "judge_b": lb, "final": final, "raw_a": (a or "")[:200],
                         "raw_b": (b or "")[:200], "nearest_known_jaccard": j,
                         "nearest_known_head": (near or "")[:300]})
    out = {"n_correct_other_programs": len(cand), "n_unique": len(uniq), "rows": out_rows,
           "final_counts": dict(Counter(r["final"] for r in out_rows)),
           "per_arm": dict(Counter((r["arm"], r["final"]) for r in out_rows).most_common()) and
           {f"{a}|{f}": n for (a, f), n in Counter((r["arm"], r["final"]) for r in out_rows).items()},
           "usd": led.spent("novelty_audit"),
           "manual_pass": "each row carries its AST-nearest known solution (Jaccard of identifier-normalised 4-gram "
                          "shingles) for the executor's manual read"}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    logger.info(f"A9 novelty audit: {len(uniq)} unique correct 'other' programs -> {out['final_counts']}")
    return out


def run_audits() -> dict[str, Any]:
    from report import load_rows

    rows = load_rows()
    fa = judge_first_approach()
    nv = novelty_audit(rows)
    return {"first_approach": fa, "novelty": nv}


if __name__ == "__main__":
    run_audits()
