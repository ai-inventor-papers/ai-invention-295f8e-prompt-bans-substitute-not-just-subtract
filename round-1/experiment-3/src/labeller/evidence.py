"""S3d: commitment evidence. commit_idx = generated-token index holding the first character of the first lexicon match."""

from __future__ import annotations

import re

LEX = {
    "T1": ["bfs", "breadth", "queue", "deque", "popleft", "dfs", "depth-first", "depth first", "stack", "recurs",
           "iddfs", "iterative deepening", "a*", "a-star", "astar", "heuristic", "manhattan", "greedy", "best-first",
           "heap", "heapq", "priority", "dijkstra", "bidirectional"],
    "T2": ["dijkstra", "heap", "heapq", "priority", "bellman", "ford", "spfa", "floyd", "warshall", "dial", "bucket",
           "bidirectional", "queue", "deque"],
}
STRICT = {
    "T1": ["bfs", "breadth-first", "breadth first", "dfs", "depth-first", "depth first", "iddfs",
           "iterative deepening", "a*", "a-star", "astar", "greedy", "best-first", "dijkstra", "bidirectional"],
    "T2": ["dijkstra", "bellman", "ford", "spfa", "floyd", "warshall", "dial", "bidirectional"],
}


def _pattern(terms: list[str]) -> re.Pattern:
    alts = []
    for t in sorted(terms, key=len, reverse=True):
        e = re.escape(t)
        if t in ("ford", "dial", "stack", "heap", "queue", "deque", "greedy", "priority", "bucket"):
            e = r"(?<![a-z])" + e  # word-start boundary for short common words ('afford', 'radial')
        alts.append(e)
    return re.compile("|".join(alts), re.I)


PAT = {t: _pattern(v) for t, v in LEX.items()}
PAT_STRICT = {t: _pattern(v) for t, v in STRICT.items()}


def char_to_token(tokenizer, ids: list[int], char_idx: int) -> int | None:
    """Smallest k such that len(decode(ids[:k+1])) > char_idx (cumulative decode lengths)."""
    lo_len = 0
    for k in range(len(ids)):
        L = len(tokenizer.decode(ids[: k + 1], skip_special_tokens=False))
        if L > char_idx:
            return k
        lo_len = L
    return None


def commitment(tokenizer, task: str, gen_ids: list[int], text: str | None = None) -> dict:
    if text is None:
        text = tokenizer.decode(gen_ids, skip_special_tokens=False)
    out = {"commit_idx": None, "evidence_term": None, "commit_char": None,
           "commit_idx_strict": None, "evidence_term_strict": None}
    m = PAT[task].search(text)
    if m:
        out["commit_char"] = m.start()
        out["evidence_term"] = m.group(0)
        out["commit_idx"] = char_to_token(tokenizer, gen_ids, m.start())
    ms = PAT_STRICT[task].search(text)
    if ms:
        out["evidence_term_strict"] = ms.group(0)
        out["commit_idx_strict"] = char_to_token(tokenizer, gen_ids, ms.start())
    return out
