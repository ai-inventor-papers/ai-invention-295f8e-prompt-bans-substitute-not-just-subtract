#!/usr/bin/env python3
"""F1: where is the algorithm decided? Opening classifiers, base paths, prefix resampling, change points, forks.

Opening classifier partial_label(task, text) (exp31 fork.py style): lexical signatures on the program prefix; the
class of the EARLIEST decisive evidence is returned once it appears, None while undecided. On a complete program
with no lexical evidence the frozen AST rule decides (exp11 bench astrules for T10/T03, exp8 suite ast_rules + exp28
regate for T2). Because the earliest evidence decides, a prefix that already holds decisive evidence fixes the label
of every continuation: such screen positions are recorded as 'determined by prefix' (k = 0 of S) without sampling.

Outcome series of a base path: k_t = continuations (from position t, fresh CRN keys (task, 'fork', path, t, i)) whose
label differs from the base path's class, n_t = decided continuations.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from typing import Any

import numpy as np

import c7 as common
from c7 import DEFAULTS, IN29, IN30, guarded_e29_rows, read_jsonl

# ------------------------------------------------------------------------------------------------ classifiers
EVIDENCE: dict[str, list[tuple[str, str]]] = {
    "T2": [
        ("dijkstra", r"\bheappush\s*\(|\bheappop\s*\(|PriorityQueue\s*\("),
        ("bf_spfa", r"\bdeque\s*\(|\.popleft\s*\(|for\s+\w+\s+in\s+range\s*\(\s*n\s*-"
                    r"\s*1\s*\)|\bin_queue\b|\binq\b|[Bb]ellman|\bspfa\b|\bSPFA\b"),
        ("floyd", r"dist\s*\[\s*i\s*\]\s*\[\s*k\s*\]\s*\+\s*dist\s*\[\s*k\s*\]\s*\[\s*j\s*\]"),
    ],
    "T10": [
        ("union_find", r"\bparent\s*=\s*(list\s*\(\s*range|\[\s*\w+\s+for\b|\{)|def\s+find\s*\(|def\s+union\s*\(|"
                       r"class\s+(UnionFind|DSU|DisjointSet)|\bparent\s*\[\s*\w+\s*\]\s*=\s*find\b"),
        ("bfs", r"\bdeque\s*\(|\.popleft\s*\(|\.pop\s*\(\s*0\s*\)|\bQueue\s*\("),
        ("dfs", r"\bstack\s*=|\.pop\s*\(\s*\)|def\s+dfs\s*\(|sys\.setrecursionlimit|\bdfs\s*\("),
    ],
    "T03": [
        ("size_k_heap", r"\bnsmallest\s*\(|\bnlargest\s*\(|heappushpop|heapreplace|len\s*\(\s*\w+\s*\)\s*>\s*k\b"),
        ("heapify_pop", r"\bheapify\s*\(\s*(nums|arr|a|heap|h)\s*\)\s*\n[\s\S]{0,200}?for\s+\w+\s+in\s+range\s*\("
                        r"\s*k\s*(-\s*1\s*)?\)"),
        ("quickselect", r"\bpivot\b|def\s+partition\s*\(|def\s+quick_?select\s*\(|def\s+select\s*\("),
        ("median_of_medians", r"median_of_medians|def\s+mom\s*\("),
        ("counting_sort", r"\[0\]\s*\*\s*\(?\s*(20001|20000|10001|max_val|maxv|mx)|\+\s*10000\s*\]"),
        ("full_sort", r"\bsorted\s*\(|\.sort\s*\("),
    ],
}
_RX = {t: [(c, re.compile(rx)) for c, rx in L] for t, L in EVIDENCE.items()}


def code_of(text: str) -> str:
    i = text.find("```")
    if i >= 0:
        j = text.find("\n", i)
        text = text[j + 1:] if j >= 0 else ""
    k = text.find("```")
    return text[:k] if k >= 0 else text


def evidence(task: str, text: str) -> list[tuple[int, str]]:
    code = code_of(text)
    out = []
    for c, rx in _RX[task]:
        m = rx.search(code)
        if m:
            out.append((m.start(), c))
    return sorted(out)


def partial_label(task: str, text: str) -> str | None:
    ev = evidence(task, text)
    return ev[0][1] if ev else None


def fence_closed(task: str, text: str) -> bool:
    from engine4 import fence_closed as fc
    return fc(text, common.FENCE[task])


def complete_label(task: str, text: str) -> str:
    """AST fallback for a complete program without lexical evidence (frozen rules, no execution)."""
    code = _extract(task, text)
    if not code:
        return "invalid"
    if task == "T2":
        from regate_rules import apply_t2
        sys.path.insert(0, str(common.V22 / "inputs" / "exp8" / "suite"))
        from labeller import ast_rules
        try:
            lab, _, _ = ast_rules.label(code, "t2")
        except Exception:  # noqa: BLE001
            return "unknown"
        lab, _ = apply_t2(lab, code)
        return lab
    sys.path.insert(0, str(common.V22 / "inputs" / "exp11"))
    from bench.common.astrules import ast_label
    return ast_label(task, code)


def _extract(task: str, text: str) -> str | None:
    if task == "T2":
        sys.path.insert(0, str(common.V22 / "inputs" / "exp8" / "suite"))
        from labeller.extract import extract_code
        code, _ = extract_code(text)
        return code
    sys.path.insert(0, str(common.V22 / "inputs" / "exp11"))
    from bench.common.harness import extract_code
    return extract_code(text)


def opening_label(task: str, text: str) -> tuple[str | None, str]:
    """Label of a (possibly unfinished) continuation: lexical evidence, else AST on a closed fence, else None."""
    pl = partial_label(task, text)
    if pl is not None:
        return pl, "partial"
    if fence_closed(task, text):
        return complete_label(task, text), "fence_ast"
    return None, "undecided"


# ------------------------------------------------------------------------------------------------ validation
def labelled_programs(task: str) -> list[dict[str, Any]]:
    """Non-POP labelled programs of exp29 (engine d) and exp30 with their text: TWIN, PN, BAN, ST, X, FORCED rows."""
    out = []
    if task in ("T10", "T2"):
        labs = {r["key"]: r for r in guarded_e29_rows(IN29 / "labels.jsonl") if r["key"].startswith("d|")}
        for r in guarded_e29_rows(IN29 / "raw_d.jsonl"):
            key = f"d|{r['task']}|{r['template']}|{r['arm']}|{r['sample_id']}"
            if r["task"] == task and key in labs:
                l = labs[key]
                out.append({"src": "e29", "task": task, "arm": r["arm"], "template": r["template"],
                            "sample_id": r["sample_id"], "text": r["text"], "ids": r["token_ids"], "label": l["label"],
                            "passed": l["passed"]})
    labs30 = {(r["task"], r["arm"], str(r["sample_id"])): r for r in read_jsonl(IN30 / "labels.jsonl")}
    for r in read_jsonl(IN30 / "samples_raw.jsonl"):
        if r["task"] != task:
            continue
        l = labs30.get((r["task"], r["arm"], str(r["sample_id"])))
        if l is None:
            continue
        k30 = int(str(r.get("crn_key") or "").split("|")[-1]) if r.get("crn_key") else int(r.get("slot") or 0)
        out.append({"src": "e30", "task": task, "arm": r["arm"], "template": r["template"], "slot": r.get("slot"),
                    "sample_id": k30, "sid30": r["sample_id"], "text": r["text"], "ids": r["token_ids"], "label": l["label"],
                    "passed": l["passed"], "dir_seed": r.get("dir_seed"), "alpha": r.get("alpha"),
                    "site": r.get("site")})
    return out


def validate(task: str, n: int = 200, seed: int = 0) -> dict[str, Any]:
    """Agreement of the opening classifier (applied to complete programs) with the frozen label, stratified by class."""
    rows = [r for r in labelled_programs(task) if r["label"] in common.CATALOGUE[task]]
    rng = np.random.default_rng(seed)
    by = defaultdict(list)
    for r in rows:
        by[r["label"]].append(r)
    classes = sorted(by)
    per = max(1, n // max(1, len(classes)))
    pick = []
    for c in classes:
        idx = rng.permutation(len(by[c]))[:per]
        pick += [by[c][i] for i in idx]
    rest = [r for r in rows if r not in pick]
    if len(pick) < n and rest:
        idx = rng.permutation(len(rest))[:n - len(pick)]
        pick += [rest[i] for i in idx]
    agree = committed = 0
    conf = Counter()
    lex = 0
    for r in pick:
        lab, how = opening_label(task, r["text"])
        if lab is None or lab in ("unknown", "invalid"):
            conf[(r["label"], "abstain")] += 1
            continue
        committed += 1
        lex += how == "partial"
        agree += lab == r["label"]
        conf[(r["label"], lab)] += 1
    return {"task": task, "n": len(pick), "committed": committed, "agree": agree,
            "agreement": agree / committed if committed else None, "abstain_rate": 1 - committed / len(pick),
            "lexical_share": lex / committed if committed else None,
            "confusion": {f"{a}->{b}": v for (a, b), v in sorted(conf.items())},
            "pass": bool(committed and agree / committed >= 0.95)}


# ------------------------------------------------------------------------------------------------ base paths
def first_decision_token(task: str, tok: Any, ids: list[int], cls: str) -> int | None:
    """Smallest t such that the prefix ids[:t] already carries decisive evidence for `cls` (partial label)."""
    lo, hi = 0, len(ids)
    if partial_label(task, tok.decode(ids, skip_special_tokens=True)) != cls:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if partial_label(task, tok.decode(ids[:mid], skip_special_tokens=True)) == cls:
            hi = mid
        else:
            lo = mid + 1
    return lo


def select_base_paths(task: str, tok: Any, n_per_class: int = 6) -> list[dict[str, Any]]:
    """F1.1: correct programs; default from TWIN rows (2 templates x 3), non-default classes from BAN rows (ban
    prompt, no hook) and per-sample-noise rows (exp29 PN_a2, hook active during resampling); only programs whose
    opening-classifier label equals their frozen label are eligible (so k_t compares like with like)."""
    rows = labelled_programs(task)
    default = DEFAULTS[task]
    ok = []
    for r in rows:
        if not r["passed"] or r["label"] not in common.CATALOGUE[task]:
            continue
        lab, how = opening_label(task, r["text"])
        if lab != r["label"] or how != "partial":
            continue
        r["t_dec"] = first_decision_token(task, tok, r["ids"], r["label"])
        ok.append(r)
    paths = []

    def take(cands: list[dict[str, Any]], k: int, kind: str) -> list[dict[str, Any]]:
        cands = sorted(cands, key=lambda r: (r["template"], int(r["sample_id"])))
        by_w = defaultdict(list)
        for r in cands:
            by_w[r["template"]].append(r)
        order = sorted(by_w, key=lambda w: -len(by_w[w]))
        out = []
        # few templates keep batches large (rows of one template share the prompt length)
        for w in order:
            for r in by_w[w]:
                if len(out) < k:
                    out.append({**r, "cell": kind})
        return out

    tw = [r for r in ok if r["arm"] == "TWIN" and r["label"] == default and r["src"] == ("e30" if task == "T03"
                                                                                           else "e29")]
    paths += take(tw, n_per_class, "TWIN")
    for c in common.CATALOGUE[task]:
        if c == default:
            continue
        ban = [r for r in ok if r["arm"] == "BAN" and r["label"] == c]
        pn = [r for r in ok if r["arm"] in ("PN_a2", "PN_a2.0") and r["label"] == c]
        if len(ban) + len(pn) < 4:
            continue
        k_pn = min(len(pn), n_per_class // 2)
        sel = take(pn, k_pn, "PN") + take(ban, n_per_class - k_pn, "BAN")
        if len(sel) < n_per_class:
            sel += take([r for r in pn if r not in sel], n_per_class - len(sel), "PN")
        paths += sel
    for i, p in enumerate(paths):
        p["path_id"] = f"{task}:{p['cell']}:{p['label']}:{p['template']}:{p['sample_id']}"
        p["class"] = p["label"]
    return paths


# ------------------------------------------------------------------------------------------------ change points
def series_cp(k: list[int], n: list[int], n_perm: int = 1000, seed: int = 0) -> dict[str, Any]:
    from fork import change_points   # vendored exp31
    if sum(n) == 0 or len(k) < 3:
        return {"gain": 0.0, "cps": [], "p_value": 1.0, "segments": []}
    return change_points(k, n, n_perm=n_perm, seed=seed)


def canonical_opening(ids_list: list[list[int]], t: int) -> tuple[list[int], float]:
    from fork import canonical_prefix
    if not any(len(x) >= t for x in ids_list):
        return [], 0.0
    pref, cnt = canonical_prefix(ids_list, t)
    return pref, cnt / max(1, sum(1 for x in ids_list if len(x) >= t))


def entropy_bits(counts: dict[str, int]) -> float:
    n = sum(counts.values())
    if n == 0:
        return float("nan")
    return float(-sum(c / n * np.log2(c / n) for c in counts.values() if c > 0))
