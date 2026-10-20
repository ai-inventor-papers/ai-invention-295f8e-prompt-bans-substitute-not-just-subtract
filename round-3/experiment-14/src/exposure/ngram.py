"""Token n-gram utilities: per-program n-gram sets, the frozen distinctive-n-gram rule, occurrence search.

Frozen rule (plan step 0.7 / 2.4):
  candidates   = n-grams (n = 1..6) whose presence (share of reference programs containing them) >= 0.8,
                 minus n-grams already in the veto mask;
  collateral   = max over collateral groups of the share of the group's programs containing the n-gram;
  order        = (collateral asc, n asc, presence desc, token ids asc);
  shown rule   = the first candidate contained in >= min(5, |P_Y|) shown-pool programs, else the candidate with the
                 largest shown count (round 1 only; later rounds have no shown constraint);
  relaxed rule = (later rounds only) if no candidate reaches 0.8, the highest-presence n-gram with collateral < 0.5.
"""

from __future__ import annotations

from collections import Counter


def ngram_set(ids: list[int], nmax: int = 6) -> set[tuple[int, ...]]:
    out: set[tuple[int, ...]] = set()
    n_ids = len(ids)
    for n in range(1, nmax + 1):
        for i in range(n_ids - n + 1):
            out.add(tuple(ids[i:i + n]))
    return out


def contains(ids: list[int], g: tuple[int, ...] | list[int]) -> bool:
    g = tuple(g)
    n = len(g)
    if n == 0 or n > len(ids):
        return False
    first = g[0]
    for i in range(len(ids) - n + 1):
        if ids[i] == first and tuple(ids[i:i + n]) == g:
            return True
    return False


def occurrences(ids: list[int], g: tuple[int, ...] | list[int]) -> list[int]:
    g = tuple(g)
    n = len(g)
    return [i for i in range(len(ids) - n + 1) if tuple(ids[i:i + n]) == g] if n else []


def group_shares(groups: dict[str, list[set]]) -> dict[str, tuple[Counter, int]]:
    """Per group: Counter over n-grams of the member sets and the group size."""
    out = {}
    for name, sets in groups.items():
        c: Counter = Counter()
        for s in sets:
            c.update(s)
        out[name] = (c, len(sets))
    return out


def collateral_of(g: tuple[int, ...], shares: dict[str, tuple[Counter, int]]) -> tuple[float, dict[str, float]]:
    by = {name: (c[g] / n if n else 0.0) for name, (c, n) in shares.items()}
    return (max(by.values()) if by else 0.0), by


def select_distinctive(ref_sets: list[set], groups: dict[str, list[set]], shown_sets: list[set] | None = None,
                       presence_min: float = 0.8, exclude: set | None = None, allow_relaxed: bool = False,
                       relaxed_collateral_max: float = 0.5, coveto_share: float = 0.5,
                       groups_correct: dict[str, list[set]] | None = None) -> dict | None:
    """Apply the frozen distinctive-n-gram rule.  Returns None when there is no reference program."""
    exclude = exclude or set()
    n_ref = len(ref_sets)
    if n_ref == 0:
        return None
    pres: Counter = Counter()
    for s in ref_sets:
        pres.update(s)
    shares = group_shares(groups)
    cand = [g for g, c in pres.items() if c / n_ref >= presence_min and g not in exclude]
    relaxed = False
    if not cand:
        if not allow_relaxed:
            return {"ids": None, "n_candidates": 0, "relaxed": False, "reason": "no candidate reaches presence"}
        pool = [g for g in pres if g not in exclude]
        scored = [(g, pres[g] / n_ref, collateral_of(g, shares)[0]) for g in pool]
        scored = [x for x in scored if x[2] < relaxed_collateral_max]
        if not scored:
            return {"ids": None, "n_candidates": 0, "relaxed": True, "reason": "no n-gram with collateral < 0.5"}
        scored.sort(key=lambda x: (-x[1], x[2], len(x[0]), x[0]))
        cand = [scored[0][0]]
        relaxed = True
    keyed = []
    for g in cand:
        col, _ = collateral_of(g, shares)
        keyed.append(((col, len(g), -pres[g] / n_ref, g), g))
    keyed.sort(key=lambda x: x[0])
    ordered = [g for _, g in keyed]
    chosen, shown_count = None, None
    if shown_sets is not None:
        need = min(5, len(shown_sets))
        counts = {g: sum(1 for s in shown_sets if g in s) for g in ordered}
        for g in ordered:
            if counts[g] >= need:
                chosen = g
                break
        if chosen is None:  # the candidate with the largest shown count (first in rule order among ties)
            best = max(counts.values()) if counts else 0
            chosen = next(g for g in ordered if counts[g] == best)
        shown_count = counts[chosen]
    else:
        chosen = ordered[0]
    col, by = collateral_of(chosen, shares)
    out = {"ids": list(chosen), "n": len(chosen), "presence": pres[chosen] / n_ref, "collateral": col,
           "collateral_by_group": by, "coveto_groups": sorted(k for k, v in by.items() if v >= coveto_share),
           "n_candidates": len(cand), "relaxed": relaxed, "shown_count": shown_count, "n_ref": n_ref,
           "rank_in_rule_order": ordered.index(chosen)}
    if groups_correct is not None:
        _, byc = collateral_of(chosen, group_shares(groups_correct))
        out["collateral_by_group_correct_only"] = byc
    return out
