#!/usr/bin/env python3
"""STEP 2 - known-solution corpus + novelty critic.

CORPUS: every code-bearing example of the declared dependency art_j3Rm_lr2nzR6 by iteration 6's recipe (first of
output/input that is a string containing 'def ' or 'class ', shorter than 20,000 characters, with >= 5 iteration-6
5-token shingles), expected n_corpus = 18,237; plus the catalogue references of the tasks (critic only).
TOKENISER: Python tokenize; comments, docstrings (string-only statements), NL, NEWLINE, ENCODING dropped; keywords,
operators, builtins, attribute names (after '.') and imported names kept verbatim; other NAMEs -> ID, numbers -> NUM,
strings -> STR; INDENT/DEDENT kept.
SHINGLES: token 4-grams hashed (crc32) into 2^22 buckets -> one binary CSR row per program. Exact Jaccard to every
corpus row by sparse matmul in chunks of 512: J = inter / (|a| + |c| - inter); top-50 ids kept.
AST DISTANCE: pre-order node-type sequence (identifiers dropped), rapidfuzz normalised Levenshtein to the top-50 by
Jaccard; zss Zhang-Shasha only for adjudication candidates (top-10, trees above 800 nodes skipped with a flag).
"""

from __future__ import annotations

import ast
import builtins
import io
import json
import keyword
import tokenize
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy import sparse

from common import DATA, DEP_DIR, read_json, read_jsonl, sha256_text, utc_now, write_json, write_jsonl

DIM = 1 << 22
SH = 4
CHUNK = 512
TOPK = 50
CORPUS_DIR = DATA / "corpus"
BUILTINS = set(dir(builtins))
CORPUS_DATASETS = ("leetcodedataset", "mercury", "llm_creativity", "thealgorithms_python", "clrs_text",
                   "humanevalplus", "enamel", "concreteness_norms", "kodcode_algorithmic", "xlcost_python")

# ------------------------------------------------------------------------------------------------ iteration-6 rule
_K6 = {"heapq", "heappush", "heappop", "heapify", "deque", "popleft", "append", "pop", "parent", "find", "union",
       "rank", "visited", "seen", "dist", "inf", "float", "range", "len", "min", "max", "sorted", "set", "dict",
       "defaultdict", "list", "stack", "queue", "graph", "adj", "edges", "add", "get", "items", "extend", "insert"}


def _toks6(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append(t.string if (keyword.iskeyword(t.string) or t.string in _K6) else "ID")
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


def _n_shingles6(code: str) -> int:
    t = _toks6(code)
    return len({" ".join(t[i:i + 5]) for i in range(max(len(t) - 5 + 1, 0))})


# ------------------------------------------------------------------------------------------------ tokeniser
def _imported_names(code: str) -> set[str]:
    out: set[str] = set()
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return out
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                out.add(n.module.split(".")[0])
            for a in n.names:
                out.add(a.name)
    return out


def norm_tokens(code: str) -> list[str]:
    imported = _imported_names(code)
    raw = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            raw.append(t)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    out: list[str] = []
    prev_sig: str | None = None          # previous significant token (string form)
    line_start = True                    # are we at the start of a logical line?
    i = 0
    n = len(raw)
    while i < n:
        t = raw[i]
        tt = t.type
        if tt in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER):
            i += 1
            continue
        if tt == tokenize.NEWLINE:
            line_start = True
            prev_sig = None
            i += 1
            continue
        if tt in (tokenize.INDENT, tokenize.DEDENT):
            out.append(tokenize.tok_name[tt])
            line_start = True
            i += 1
            continue
        if tt == tokenize.STRING or tt == getattr(tokenize, "FSTRING_START", -1):
            # docstring / string-only statement: a string (or f-string) at line start followed by NEWLINE
            j = i
            if tt != tokenize.STRING:
                while j < n and raw[j].type != getattr(tokenize, "FSTRING_END", -2):
                    j += 1
            k = j + 1
            while k < n and raw[k].type in (tokenize.COMMENT, tokenize.NL):
                k += 1
            if line_start and (k >= n or raw[k].type in (tokenize.NEWLINE, tokenize.ENDMARKER)):
                i = k
                continue
            out.append("STR")
            prev_sig = "STR"
            line_start = False
            i = j + 1
            continue
        if tt == tokenize.NAME:
            s = t.string
            if keyword.iskeyword(s) or keyword.issoftkeyword(s) and s in ("match", "case"):
                out.append(s)
            elif prev_sig == "." or s in BUILTINS or s in imported:
                out.append(s)
            else:
                out.append("ID")
            prev_sig = s
        elif tt == tokenize.NUMBER:
            out.append("NUM")
            prev_sig = "NUM"
        elif tt == tokenize.OP:
            out.append(t.string)
            prev_sig = t.string
        else:
            out.append(tokenize.tok_name.get(tt, "TOK"))
            prev_sig = None
        line_start = False
        i += 1
    return out


def shingle_ids(code: str) -> np.ndarray:
    t = norm_tokens(code)
    if not t:
        return np.zeros(0, dtype=np.int64)
    if len(t) < SH:
        grams = [" ".join(t)]
    else:
        grams = [" ".join(t[i:i + SH]) for i in range(len(t) - SH + 1)]
    return np.unique(np.fromiter((zlib.crc32(g.encode()) % DIM for g in grams), dtype=np.int64, count=len(grams)))


def to_matrix(id_lists: list[np.ndarray]) -> sparse.csr_matrix:
    indptr = np.zeros(len(id_lists) + 1, dtype=np.int64)
    for i, a in enumerate(id_lists):
        indptr[i + 1] = indptr[i] + len(a)
    indices = np.concatenate(id_lists) if id_lists else np.zeros(0, dtype=np.int64)
    data = np.ones(len(indices), dtype=np.float32)
    return sparse.csr_matrix((data, indices.astype(np.int32), indptr), shape=(len(id_lists), DIM))


def jaccard_pair(a: str, b: str) -> float:
    x, y = set(shingle_ids(a).tolist()), set(shingle_ids(b).tolist())
    if not x and not y:
        return 1.0
    return len(x & y) / len(x | y)


# ------------------------------------------------------------------------------------------------ AST sequences
_TYPE_CODE: dict[str, str] = {}


def _code_of_type(name: str) -> str:
    if name not in _TYPE_CODE:
        _TYPE_CODE[name] = chr(0x4E00 + len(_TYPE_CODE))
    return _TYPE_CODE[name]


def ast_seq(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    out: list[str] = []
    stack = [tree]
    while stack:
        n = stack.pop()
        name = type(n).__name__
        if name in ("Load", "Store", "Del"):
            continue
        out.append(_code_of_type(name))
        kids = list(ast.iter_child_nodes(n))
        stack.extend(reversed(kids))
    return "".join(out)


def ast_tree(code: str):
    """zss tree of node types (identifiers dropped)."""
    from zss import Node
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None, 0
    count = 0

    def build(n):
        nonlocal count
        count += 1
        z = Node(type(n).__name__)
        for c in ast.iter_child_nodes(n):
            if type(c).__name__ in ("Load", "Store", "Del"):
                continue
            z.addkid(build(c))
        return z
    try:
        return build(tree), count
    except RecursionError:
        return None, count


# ------------------------------------------------------------------------------------------------ corpus
def same_task_tags(ds: str, ex: dict[str, Any]) -> list[str]:
    tags = []
    bt = str(ex.get("metadata_bench_task") or "")
    named = ex.get("metadata_bench_tasks_named") or []
    if isinstance(named, str):
        try:
            named = json.loads(named)
        except json.JSONDecodeError:
            named = [named]
    qid = str(ex.get("metadata_question_id") or "")
    if bt.startswith("T03") or "T03_kth_smallest" in named or (ds in ("leetcodedataset", "mercury") and qid == "215"):
        tags.append("T03")
    if bt.startswith("T02") or "T02_weighted_shortest_path" in named or \
            (ds in ("leetcodedataset", "mercury") and qid in ("743", "1631", "1514")):
        tags.append("T2")
    txt = (str(ex.get("input") or "")[:4000] + " " + str(ex.get("metadata_slug") or "") + " " +
           str(ex.get("metadata_task_slug") or "") + " " + str(ex.get("metadata_title") or "")).lower()
    if (ds in ("leetcodedataset", "mercury") and qid == "42") or ("trap" in txt and "rain" in txt) or \
            "trapping-rain-water" in txt:
        tags.append("A3")
    return tags


def build_corpus(task_objs: dict[str, dict[str, Any]], force: bool = False) -> dict[str, Any]:
    meta_p = CORPUS_DIR / "meta.jsonl"
    mat_p = CORPUS_DIR / "shingles.npz"
    if meta_p.exists() and mat_p.exists() and not force:
        return read_json(CORPUS_DIR / "summary.json")
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"loading dependency full_data_out.json from {DEP_DIR.name}")
    full = json.loads((DEP_DIR / "full_data_out.json").read_text())
    metas, codes, per = [], [], Counter()
    for d in full["datasets"]:
        ds = d["dataset"]
        per[ds] += 0
        for ei, ex in enumerate(d["examples"]):
            for fld in ("output", "input"):
                v = ex.get(fld)
                if isinstance(v, str) and ("def " in v or "class " in v) and len(v) < 20000:
                    if _n_shingles6(v) >= 5:
                        metas.append({"id": f"{ds}:{ei}", "dataset": ds, "row": ei, "field": fld,
                                      "qid": ex.get("metadata_question_id"), "tags": same_task_tags(ds, ex),
                                      "kind": "corpus", "sha": sha256_text(v)[:16]})
                        codes.append(v)
                        per[ds] += 1
                    break
    n_corpus = len(codes)
    del full
    for t, obj in task_objs.items():
        for name, code in obj["references"].items():
            metas.append({"id": f"catalogue:{t}:{name}", "dataset": "catalogue", "row": -1, "field": "reference",
                          "qid": None, "tags": [t], "kind": "catalogue", "mode": obj["ref_mode"][name],
                          "sha": sha256_text(code)[:16], "code_sha256": sha256_text(code)})
            codes.append(code)
    logger.info(f"corpus: {n_corpus} code solutions + {len(codes) - n_corpus} catalogue references; per dataset {dict(per)}")
    ids = [shingle_ids(c) for c in codes]
    M = to_matrix(ids)
    sparse.save_npz(mat_p, M)
    seqs = [ast_seq(c) for c in codes]
    write_jsonl(meta_p, metas)
    write_jsonl(CORPUS_DIR / "codes.jsonl", [{"id": m["id"], "code": c} for m, c in zip(metas, codes)])
    write_json(CORPUS_DIR / "ast_seqs.json", seqs, indent=None)
    write_json(CORPUS_DIR / "type_codes.json", _TYPE_CODE, indent=None)
    pools = {t: sum(1 for m in metas if t in m["tags"] and m["kind"] == "corpus") for t in task_objs}
    summ = {"utc": utc_now(), "n_corpus": n_corpus, "n_catalogue": len(codes) - n_corpus,
            "per_dataset": dict(per), "expected_n_corpus": 18237, "deviation": n_corpus - 18237,
            "same_task_pool_sizes": pools, "dim": DIM, "shingle": SH,
            "nnz_per_row_median": float(np.median(np.diff(M.indptr)))}
    write_json(CORPUS_DIR / "summary.json", summ)
    return summ


class Critic:
    """Nearest-known similarity of programs against corpus + catalogue references."""

    def __init__(self) -> None:
        self.M = sparse.load_npz(CORPUS_DIR / "shingles.npz").tocsr().astype(np.float32)
        self.meta = read_jsonl(CORPUS_DIR / "meta.jsonl")
        self.sizes = np.asarray(self.M.sum(1)).ravel().astype(np.float32)
        tc = read_json(CORPUS_DIR / "type_codes.json")
        _TYPE_CODE.update(tc)
        self.seqs = read_json(CORPUS_DIR / "ast_seqs.json")
        self.MT = self.M.T.tocsr()
        self.cat_sha = {m["code_sha256"]: i for i, m in enumerate(self.meta) if m["kind"] == "catalogue"}
        self._codes: list[str] | None = None

    def code(self, idx: int) -> str:
        if self._codes is None:
            self._codes = [r["code"] for r in read_jsonl(CORPUS_DIR / "codes.jsonl")]
        return self._codes[idx]

    def score(self, codes: list[str], topk: int = TOPK, exclude_self: bool = False) -> list[dict[str, Any]]:
        """exclude_self=True only when scoring the seed references themselves (their identical corpus row)."""
        from rapidfuzz.distance import Levenshtein
        out: list[dict[str, Any]] = []
        for c0 in range(0, len(codes), CHUNK):
            chunk = codes[c0:c0 + CHUNK]
            ids = [shingle_ids(c) for c in chunk]
            P = to_matrix(ids)
            inter = (P @ self.MT).toarray()
            ps = np.array([len(a) for a in ids], dtype=np.float32)
            denom = ps[:, None] + self.sizes[None, :] - inter
            J = np.where(denom > 0, inter / np.maximum(denom, 1e-9), 0.0)
            for r, code in enumerate(chunk):
                row = J[r]
                selfi = self.cat_sha.get(sha256_text(code)) if exclude_self else None
                if selfi is not None:
                    row = row.copy()
                    row[selfi] = -1.0           # exclude the identical self-match of a reference seed
                k = min(topk, len(row))
                top = np.argpartition(-row, k - 1)[:k]
                top = top[np.argsort(-row[top])]
                s = float(max(row[top[0]], 0.0))
                seq = ast_seq(code)
                ad = None
                ad_min = None
                if seq is not None:
                    dists = []
                    for j in top:
                        sj = self.seqs[j]
                        dists.append(Levenshtein.normalized_distance(seq, sj) if sj is not None else 1.0)
                    ad = float(dists[0])
                    ad_min = float(min(dists))
                nm = self.meta[int(top[0])]
                out.append({"s": round(s, 6), "novelty": round(1.0 - s, 6), "nearest_id": nm["id"],
                            "nearest_dataset": nm["dataset"], "nearest_idx": int(top[0]),
                            "top_ids": [int(x) for x in top[:10]], "top_sims": [round(float(row[x]), 4) for x in top[:10]],
                            "ast_dist": ad, "ast_dist_min": ad_min, "n_shingles": int(len(ids[r]))})
        return out

    def nearest_same_task(self, code: str, task: str, k: int = 2) -> list[tuple[int, float]]:
        ids = shingle_ids(code)
        P = to_matrix([ids])
        inter = (P @ self.MT).toarray()[0]
        denom = len(ids) + self.sizes - inter
        J = np.where(denom > 0, inter / np.maximum(denom, 1e-9), 0.0)
        idx = [i for i, m in enumerate(self.meta) if task in m["tags"] and m["kind"] == "corpus"]
        if not idx:
            return []
        idx = np.array(idx)
        order = idx[np.argsort(-J[idx])][:k]
        return [(int(i), float(J[i])) for i in order]


def zss_distance(a: str, b: str, max_nodes: int = 800) -> dict[str, Any]:
    from zss import simple_distance
    ta, na = ast_tree(a)
    tb, nb = ast_tree(b)
    if ta is None or tb is None:
        return {"zss": None, "flag": "parse"}
    if na > max_nodes or nb > max_nodes:
        return {"zss": None, "flag": f"too_big({na},{nb})"}
    d = simple_distance(ta, tb)
    return {"zss": int(d), "zss_norm": round(d / max(na, nb), 4), "flag": None}
