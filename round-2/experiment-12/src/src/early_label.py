#!/usr/bin/env python3
"""C5 early-label detector for thinking text (thought anchors) and the D1 sentence taxonomy.

The FIRST sentence that (a) names a catalogue mechanism (exp6 ALIAS_LEXICON / mode_patterns; strong terms first,
weak data-structure terms only when no strong term follows within 2 sentences), (b) carries a commitment cue and
(c) has no negation cue in the same clause BEFORE the mention gives the early label. Code reached first -> the
canonical labeller labels the code (done in the analysis stage). Neither -> 'undecided'.
"""

from __future__ import annotations

import re
from typing import Any

from core import EXP6, load_module

UNDECIDED = "undecided"
# exp6 mode names -> exp1 catalogue ids
EXP6_TO_EXP1 = {"t1": {"bfs": "bfs", "dfs": "dfs", "bidirectional_bfs": "bibfs", "iddfs": "iddfs",
                       "astar_greedy": "astar_gbfs", "dijkstra_unit": "dijkstra"},
                "t2": {"dijkstra": "dijkstra", "bellman_ford_spfa": "bf_spfa", "bidirectional_dijkstra": "bidijkstra",
                       "floyd_warshall": "floyd", "dial": "dial"}}
WEAK = {"t1": [(r"priority queue|\bheapq?\b", "dijkstra"), (r"\bdeque\b|\bqueue\b", "bfs"),
               (r"\bstack\b|\brecursi|\bbacktrack", "dfs")],
        "t2": [(r"priority queue|\bheapq?\b", "dijkstra"), (r"\bdeque\b|\bqueue\b", "bf_spfa")]}
COMMIT = [r"\bi will use\b", r"\bi'll use\b", r"\blet's use\b", r"\blet me use\b", r"\bwe can use\b",
          r"\bi'll go with\b", r"\bimplement", r"\bthe plan is\b", r"\buse a\b", r"\busing a\b",
          # obvious variants of the plan's cues (logged as an extension)
          r"\bwe will use\b", r"\bwe'll use\b", r"\blet's go with\b", r"\bgo with\b", r"\bi can use\b",
          r"\bshould use\b", r"\blet's try\b", r"\bi'll try\b", r"\bapproach is\b", r"\bwill be to use\b"]
NEG = [r"\bnot\b", r"n't\b", r"\bavoid", r"\binstead of\b", r"\bwithout\b", r"\bcannot\b", r"\bbanned\b",
       r"\bforbidden\b", r"\bprohibited\b", r"\bexcept\b", r"\bcan't\b", r"\bno\b", r"\bnor\b", r"\brather than\b"]
CLAUSE_SPLIT = re.compile(r"[,;:()]|\bbut\b|\bhowever\b|\bwhereas\b|\bso\b|\bthen\b")

_TH = None


def thinking_mod():
    """exp6 analysis/thinking.py imports its own `analysis.metrics` and `common`; those names collide with this
    repo's src/analysis.py (and exp1's common.py), so they are stashed from sys.modules while exp6's are loaded."""
    global _TH
    if _TH is None:
        import sys

        names = ("analysis", "analysis.metrics", "common")
        saved = {k: sys.modules.pop(k) for k in names if k in sys.modules}
        p = str(EXP6)
        sys.path.insert(0, p)
        try:
            _TH = load_module("exp6_thinking", EXP6 / "analysis" / "thinking.py")
        finally:
            sys.path[:] = [x for x in sys.path if x != p]
            for k in names:
                sys.modules.pop(k, None)
            sys.modules.update(saved)
    return _TH


def sentences(text: str) -> list[str]:
    return thinking_mod().sentences(text)


def strong_patterns(task: str) -> dict[str, list[str]]:
    pats = thinking_mod().mode_patterns(task.upper())
    out: dict[str, list[str]] = {}
    for m, ps in pats.items():
        lab = EXP6_TO_EXP1[task].get(m)
        if lab is None:
            continue
        out.setdefault(lab, [])
        out[lab].extend(ps)
    if task == "t1":
        # 'dijkstra' inside t1 means unit-weight Dijkstra; 'A*' also via 'heuristic'
        out.setdefault("astar_gbfs", []).append(r"\bheuristic")
    return out


def _mentions(sent_low: str, pats: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    out = []
    for p, lab in pats:
        for mm in re.finditer(p, sent_low):
            out.append((mm.start(), mm.end(), lab))
    return sorted(out)


POST_NEG = [r"\bbanned\b", r"\bforbidden\b", r"\bprohibited\b", r"\bnot allowed\b", r"\bisn't allowed\b",
            r"\bdisallowed\b", r"off[- ]limits", r"\bcan(?:not|'t) be used\b", r"\bnot permitted\b", r"\bis not\b",
            r"\bisn't\b", r"\bnot an option\b", r"\bout of the question\b"]


def _negated(sent_low: str, start: int, end: int | None = None) -> bool:
    """A negation cue in the same clause: any cue before the mention ('not use BFS', 'instead of BFS'), or a passive
    prohibition after it ('BFS is banned', 'BFS is not allowed')."""
    pre = sent_low[:start]
    parts = CLAUSE_SPLIT.split(pre)
    clause = parts[-1] if parts else pre
    if any(re.search(n, clause) for n in NEG):
        return True
    if end is None:
        return False
    post = CLAUSE_SPLIT.split(sent_low[end:])[0]
    return any(re.search(n, post) for n in POST_NEG)


def _committed(sent_low: str) -> bool:
    return any(re.search(c, sent_low) for c in COMMIT)


def strong_list(task: str) -> list[tuple[str, str]]:
    sp = strong_patterns(task)
    lst = [(p, lab) for lab, ps in sp.items() for p in ps]
    # bidirectional before plain BFS/Dijkstra so 'bidirectional BFS' is not read as BFS
    return sorted(lst, key=lambda x: 0 if x[1] in ("bibfs", "bidijkstra") else 1)


def sentence_mechanisms(task: str, sent: str, weak: bool = False) -> list[dict[str, Any]]:
    low = sent.lower()
    pats = WEAK[task] if weak else strong_list(task)
    ms = _mentions(low, pats)
    seen: list[tuple[int, int]] = []
    out = []
    for a, b, lab in ms:
        if any(a < y and x < b for x, y in seen):  # overlapping match already taken
            continue
        seen.append((a, b))
        out.append({"label": lab, "start": a, "negated": _negated(low, a, b)})
    return out


def early_label(task: str, text: str) -> dict[str, Any]:
    """Early label of the thinking text generated after a resample point (sentences in order)."""
    think = text.split("</think>", 1)[0]
    sents = sentences(think)
    strong_idx = [i for i, s in enumerate(sents) if sentence_mechanisms(task, s)]
    for i, s in enumerate(sents):
        low = s.lower()
        if not _committed(low):
            continue
        ms = [m for m in sentence_mechanisms(task, s) if not m["negated"]]
        if ms:
            return {"label": ms[0]["label"], "source": "sentence_strong", "sentence_idx": i, "sentence": s[:300]}
        wm = [m for m in sentence_mechanisms(task, s, weak=True) if not m["negated"]]
        if wm and not any(i < j <= i + 2 for j in strong_idx):
            return {"label": wm[0]["label"], "source": "sentence_weak", "sentence_idx": i, "sentence": s[:300]}
    reached_code = "</think>" in text and "```python" in text.split("</think>", 1)[1]
    return {"label": None if reached_code else UNDECIDED, "source": "code" if reached_code else "none",
            "sentence_idx": None, "sentence": None, "reached_code": reached_code}


def sentence_category(task: str, sent: str, banned: str) -> str:
    """BAN_RESTATEMENT | SUBSTITUTE_NAMING | ALTERNATIVE_LISTING | PROBLEM_RESTATEMENT | OTHER (rule-based)."""
    low = sent.lower()
    ms = sentence_mechanisms(task, sent)
    labs = {m["label"] for m in ms}
    if any(m["label"] == banned and m["negated"] for m in ms) or (
            banned in labs and any(re.search(n, low) for n in NEG + [r"\bcan'?t\b", r"\bnot allowed\b"])):
        return "BAN_RESTATEMENT"
    if len(labs) >= 2:
        return "ALTERNATIVE_LISTING"
    if any(m["label"] != banned and not m["negated"] for m in ms) and _committed(low):
        return "SUBSTITUTE_NAMING"
    if any(m["label"] != banned for m in ms):
        return "ALTERNATIVE_LISTING" if len(labs) > 1 else "SUBSTITUTE_NAMING" if _committed(low) else "OTHER_MECHANISM"
    if re.search(r"\bgrid\b|\bgraph\b|\bstart\b|\bgoal\b|\bpath\b|\bnodes?\b|\bedges?\b|\bweights?\b|"
                 r"\bproblem\b|\btask\b|\breturn\b|\bfunction\b|\binput\b", low):
        return "PROBLEM_RESTATEMENT"
    return "OTHER"
