#!/usr/bin/env python3
"""Nearest-known-solution pass (replaces the plan's two-judge novelty audit; zero API cost).

Reference corpus: every code-bearing 'output' (or code-bearing 'input') of ALL 10 datasets of the declared dependency
art_j3Rm_lr2nzR6 full_data_out.json (leetcodedataset, mercury, llm_creativity [labels only -> no code],
thealgorithms_python, clrs_text, humanevalplus, enamel, concreteness_norms [no code], kodcode_algorithmic,
xlcost_python); the per-dataset count of code solutions is reported.
Programs: every distinct correct off-default program and every 'other' program of each engine on T10 and T2 (alpha 2
POP rows + PN rows), deduplicated by code sha256.
Similarity: Python token stream with identifiers/strings/numbers abstracted (keywords, operators and a fixed list of
algorithm-revealing names kept: heapq, heappush, heappop, deque, popleft, append, pop, parent, find, union, rank,
visited, dist, inf ...), 5-token shingles, Jaccard via sparse binary matrices; for each program the maximum over the
corpus and the source dataset of the nearest solution. Classes: KNOWN-CLOSE (max J >= 0.5), VARIANT (0.25-0.5),
DISTANT (< 0.25) -- descriptive only, compared across engines.
"""

from __future__ import annotations

import io
import json
import keyword
import sys
import tokenize
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c6  # noqa: E402,F401
from c6 import DATA, RESULTS, read_jsonl, utc_now, write_json  # noqa: E402

# declared dependency art_j3Rm_lr2nzR6 (override with AII_DEP_ART_J3RM when the folder lives elsewhere)
DEP = Path(__import__("os").environ.get("AII_DEP_ART_J3RM", str(Path(__file__).resolve().parents[2] / "art_j3Rm_lr2nzR6")))
KEEP = {"heapq", "heappush", "heappop", "heapify", "deque", "popleft", "append", "pop", "parent", "find", "union",
        "rank", "visited", "seen", "dist", "inf", "float", "range", "len", "min", "max", "sorted", "set", "dict",
        "defaultdict", "list", "stack", "queue", "graph", "adj", "edges", "add", "get", "items", "extend", "insert"}
DIM = 1 << 20
SH = 5


def toks(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append(t.string if (keyword.iskeyword(t.string) or t.string in KEEP) else "ID")
            elif t.type == tokenize.OP:
                out.append(t.string)
            elif t.type == tokenize.NUMBER:
                out.append("NUM")
            elif t.type == tokenize.STRING:
                out.append("STR")
            elif t.type in (tokenize.INDENT, tokenize.DEDENT):
                out.append(tokenize.tok_name[t.type])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def shingles(code: str) -> set[int]:
    t = toks(code)
    return {hash(" ".join(t[i:i + SH])) % DIM for i in range(max(len(t) - SH + 1, 0))}


def matrix(sets: list[set[int]]) -> sparse.csr_matrix:
    rows, cols = [], []
    for i, s in enumerate(sets):
        rows += [i] * len(s)
        cols += list(s)
    return sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(sets), DIM))


def corpus() -> tuple[list[set[int]], list[str], dict[str, int]]:
    full = json.loads((DEP / "full_data_out.json").read_text())
    sets, src, per = [], [], Counter()
    for d in full["datasets"]:
        per[d["dataset"]] += 0
        for ex in d["examples"]:
            for fld in ("output", "input"):
                v = ex.get(fld)
                if isinstance(v, str) and ("def " in v or "class " in v) and len(v) < 20000:
                    s = shingles(v)
                    if len(s) >= 5:
                        sets.append(s)
                        src.append(d["dataset"])
                        per[d["dataset"]] += 1
                    break
    return sets, src, dict(per)


def main() -> None:
    from analysis import catalogue  # noqa: F401  (vendored catalogue via the analysis helpers)
    from c6 import DEFAULTS

    rows = read_jsonl(DATA / "samples.jsonl")
    labels = {l["key"]: l for l in read_jsonl(DATA / "labels.jsonl")}
    rel = {l["key"]: l for l in read_jsonl(DATA / "iter4_relabelled.jsonl")}
    # code text per row: this run's label rows carry the code; reused engine-a rows: exp22 label rows
    e22 = {l["key"]: l for l in read_jsonl(c6.E22 / "labels.jsonl")}
    progs: dict[str, str] = {}
    use = defaultdict(list)
    for r in rows:
        if r["task"] not in ("T10", "T2") or r["family"] not in ("POP", "PN"):
            continue
        if r["label"] in ("invalid", "disputed"):
            continue
        off = r["label"] != DEFAULTS[r["task"]]
        if not ((off and r["passed"]) or r["label"] == "other"):
            continue
        key6 = f"{r['engine']}|{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        key4 = f"{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
        code = (labels.get(key6) or {}).get("code") or (e22.get(key4) or {}).get("code")
        if not code:
            continue
        sha = r.get("code_sha256") or str(hash(code))
        progs[sha] = code
        use[(r["engine"], r["task"])].append((sha, r["label"]))
    shas = sorted(progs)
    P = matrix([shingles(progs[s]) for s in shas])
    sets, src, per = corpus()
    C = matrix(sets)
    inter = (P @ C.T).tocsr()
    pn = np.asarray(P.sum(1)).ravel()
    cn = np.asarray(C.sum(1)).ravel()
    best = {}
    for i, s in enumerate(shas):
        row = inter.getrow(i)
        if row.nnz == 0:
            best[s] = (0.0, None)
            continue
        j = row.indices
        jac = row.data / (pn[i] + cn[j] - row.data)
        k = int(np.argmax(jac))
        best[s] = (float(jac[k]), src[j[k]])
    out = {"utc": utc_now(), "corpus_code_solutions_per_dataset": per, "n_corpus": len(sets),
           "n_distinct_programs": len(shas), "per_engine_task": {}}
    for (e, t), lst in sorted(use.items()):
        uniq = {s: l for s, l in lst}
        js = np.array([best[s][0] for s in uniq])
        cls = Counter("KNOWN-CLOSE" if best[s][0] >= 0.5 else ("VARIANT" if best[s][0] >= 0.25 else "DISTANT")
                      for s in uniq)
        out["per_engine_task"][f"{e}|{t}"] = {
            "n_rows": len(lst), "n_distinct": len(uniq), "median_max_jaccard": float(np.median(js)) if len(js) else None,
            "classes": dict(cls), "nearest_dataset": dict(Counter(best[s][1] for s in uniq)),
            "other_programs": [{"sha": s[:12], "max_jaccard": best[s][0], "nearest": best[s][1]}
                               for s, l in uniq.items() if l == "other"][:20]}
    write_json(RESULTS / "known_solutions.json", out)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "other_programs"}
                      for k, v in out["per_engine_task"].items()}, indent=0)[:3000])
    print(per)


if __name__ == "__main__":
    main()
