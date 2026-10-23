#!/usr/bin/env python3
"""Screen labelling, banned sets B_c (commit #2), screen metrics and the committed selection rule (commit #3)."""

from __future__ import annotations

import collections
import hashlib
from typing import Any

from loguru import logger

from common import (CANON_ORDER, CARRIED, CONFIGS, DATA, FILL_ORDER, PRED, RESULTS, SELECTION, alias_regex, commit,
                    newcombe_diff, read_json, read_jsonl, wilson_ci, wilson_upper_one_sided, write_json, write_jsonl)

CATALOGUE = set(CANON_ORDER)


def raw_path(cid: str, arm: str):
    return DATA / f"raw_{cid}_{arm}.jsonl"


def labelled_path(cid: str, arm: str):
    return DATA / f"labelled_{cid}_{arm}.jsonl"


def label_arm(arm: str, cids: list[str] | None = None) -> dict[str, int]:
    """Label every configuration's raw rows of one arm (dedup by slot; keeps the first record per slot)."""
    import label_tp

    out = {}
    all_rows, owner = [], []
    for cid in cids or list(CONFIGS):
        rows = read_jsonl(raw_path(cid, arm))
        seen, uniq = set(), []
        for r in rows:
            key = (r.get("arm"), r.get("slot"))
            if key in seen:
                continue
            seen.add(key)
            r["config"] = cid
            r["uid"] = f"{cid}|{r.get('arm')}|{r.get('slot')}"
            uniq.append(r)
        all_rows += uniq
        owner += [cid] * len(uniq)
    lab = label_tp.label_rows(all_rows)
    by: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for cid, r in zip(owner, lab):
        by[cid].append(r)
    for cid, rows in by.items():
        rows.sort(key=lambda r: int(r["slot"]))
        write_jsonl(labelled_path(cid, arm), rows)
        out[cid] = len(rows)
        logger.info(f"labelled {cid} {arm}: {len(rows)} rows; label_raw {dict(collections.Counter(r['label_raw'] for r in rows))}")
    return out


def banned_set(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Top five by implemented count (adjudicated label, pass or fail, 'invalid'/'other' excluded); ties -> higher
    correct count, then canonical order; fewer than 5 classes with count >= 1 -> fill from FILL_ORDER."""
    impl = collections.Counter(r["adj_label"] for r in rows if r["adj_label"] in CATALOGUE)
    corr = collections.Counter(r["adj_label"] for r in rows if r["adj_label"] in CATALOGUE and r.get("passed"))
    ranked = sorted([a for a in CANON_ORDER if impl[a] >= 1],
                    key=lambda a: (-impl[a], -corr[a], CANON_ORDER.index(a)))
    b = ranked[:5]
    filled = []
    for a in FILL_ORDER:
        if len(b) >= 5:
            break
        if a not in b:
            b.append(a)
            filled.append(a)
    return sorted(b, key=CANON_ORDER.index), {"implemented": dict(impl), "correct": dict(corr), "filled": filled,
                                             "ranked_with_count": ranked}


def stage_commit2() -> dict[str, Any]:
    """Adjudicate baseline review-class rows, compute every B_c, render the ban prompts, commit."""
    import adjudicate
    import prompts_tp

    payload: dict[str, Any] = {"banned_sets": {}, "baseline_counts": {}, "ban_prompts": {}, "adjudication": {}}
    for cid, cfg in CONFIGS.items():
        rows = read_jsonl(labelled_path(cid, "baseline"))
        if not rows:
            logger.warning(f"{cid}: no labelled baseline rows")
            continue
        st = adjudicate.apply_adjudication(rows, banned=None, purpose=f"{cid}:baseline")
        write_jsonl(labelled_path(cid, "baseline"), rows)
        b, info = banned_set(rows)
        payload["banned_sets"][cid] = b
        payload["baseline_counts"][cid] = {**info, "n": len(rows),
                                           "adj_composition": dict(collections.Counter(r["adj_label"] for r in rows)),
                                           "pass_rate": sum(bool(r.get("passed")) for r in rows) / len(rows)}
        payload["adjudication"][cid] = st
        prompts = prompts_tp.screen_ban_prompts(b, cfg["n_ban"])
        payload["ban_prompts"][cid] = [{"slot": p["slot"], "template": p["template"],
                                        "sha256": hashlib.sha256(p["prompt"].encode()).hexdigest(),
                                        "segment": p["segment"]} for p in prompts]
        logger.info(f"{cid} B_c = {b} (impl {info['implemented']}, filled {info['filled']})")
    p = PRED / "commit2.json"
    write_json(p, payload)
    commit(p, "commit2", "banned sets B_c and rendered ban prompts, before any ban sample")
    return payload


def name_free(r: dict[str, Any], banned: list[str]) -> tuple[bool, bool]:
    rx = alias_regex(banned)
    code_free = not rx.search(r.get("code") or "")
    all_free = code_free and not rx.search((r.get("content") or "") + "\n" + (r.get("reasoning") or ""))
    return code_free, all_free


def is_correct_survivor(r: dict[str, Any], banned: list[str], include_unresolved: bool = False) -> bool:
    if not r.get("passed"):
        return False
    lab = r.get("adj_label")
    if lab in banned or lab in ("invalid", "no_code", None):
        return False
    if lab in CATALOGUE:
        return True
    if lab == "other":
        return bool(r.get("adj_other_name")) or include_unresolved
    return False


def config_metrics(cid: str, arm: str = "ban") -> dict[str, Any]:
    c2 = read_json(PRED / "commit2.json")
    banned = c2["banned_sets"][cid]
    rows = read_jsonl(labelled_path(cid, arm))
    base = read_jsonl(labelled_path(cid, "baseline"))
    n = len(rows)
    cs = [r for r in rows if is_correct_survivor(r, banned)]
    cs_unres = [r for r in rows if is_correct_survivor(r, banned, include_unresolved=True)]
    att = [r for r in rows if r.get("adj_label") not in banned and r.get("adj_label") not in ("invalid", None)]
    bm = [r for r in rows if r.get("adj_label") in banned]
    nf = [name_free(r, banned) for r in bm]
    comp = collections.Counter(r.get("adj_label") for r in rows)
    bcomp = collections.Counter(r.get("adj_label") for r in base)
    shifts = {}
    for a in sorted(set(comp) | set(bcomp), key=lambda x: (CANON_ORDER.index(x) if x in CANON_ORDER else 99, str(x))):
        d, lo, hi = newcombe_diff(comp[a], n, bcomp[a], len(base))
        shifts[a] = {"ban": comp[a], "baseline": bcomp[a], "diff": d, "newcombe95": [lo, hi]}
    per_t: dict[str, dict[str, Any]] = {}
    for t in sorted({r.get("template") for r in rows}):
        rt = [r for r in rows if r.get("template") == t]
        per_t[t] = {"n": len(rt), "correct_survivors": sum(is_correct_survivor(r, banned) for r in rt),
                    "banned_mechanism": sum(r.get("adj_label") in banned for r in rt),
                    "pass": sum(bool(r.get("passed")) for r in rt)}
    k = len(cs)
    rx_bd = __import__("re").compile(r"\bbfs\b|breadth|\bdfs\b|depth[- _]first", __import__("re").IGNORECASE)
    rx_spfa = __import__("re").compile(r"spfa", __import__("re").IGNORECASE)
    cs_strict = [r for r in cs if not (r["adj_label"] == "other" and rx_bd.search(str(r.get("adj_other_name") or "")))]
    cs_strict2 = [r for r in cs_strict if not (r["adj_label"] == "other" and
                                               rx_spfa.search(str(r.get("adj_other_name") or "")))]
    cs_cat = [r for r in cs if r["adj_label"] in CATALOGUE]
    m = {"config": cid, "name": CONFIGS[cid]["name"], "arm": arm, "banned_set": banned, "n": n,
         "n_correct_survivors": k, "share_cs": k / n if n else None, "share_cs_wilson95": wilson_ci(k, n),
         "share_cs_upper95_one_sided": wilson_upper_one_sided(k, n),
         "n_correct_survivors_incl_unresolved_other": len(cs_unres),
         "sensitivity_cs": {"catalogue_only": len(cs_cat),
                            "excluding_other_named_bfs_dfs_variant": len(cs_strict),
                            "excluding_bfs_dfs_variant_and_spfa": len(cs_strict2),
                            "share_excluding_bfs_dfs_variant": len(cs_strict) / n if n else None,
                            "share_excluding_bfs_dfs_variant_and_spfa": len(cs_strict2) / n if n else None,
                            "note": "primary = committed adjudication; these drop 'other' survivors whose adjudicated "
                                    "name is a BFS/DFS variant (and SPFA, which degenerates toward BFS on a unit grid)"},
         "attempted_survivor_share": len(att) / n if n else None,
         "attempted_survivor_wilson95": wilson_ci(len(att), n),
         "banned_mechanism_share": len(bm) / n if n else None, "banned_mechanism_wilson95": wilson_ci(len(bm), n),
         "name_free_reimpl_code": (sum(a for a, _ in nf) / len(nf)) if nf else None,
         "name_free_reimpl_all_text": (sum(b for _, b in nf) / len(nf)) if nf else None,
         "n_banned_mechanism": len(bm),
         "pass_rate": sum(bool(r.get("passed")) for r in rows) / n if n else None,
         "pass_rate_exp2": sum(bool(r.get("passed_exp2")) for r in rows) / n if n else None,
         "pass_agreement_suites": sum(bool(r.get("passed")) == bool(r.get("passed_exp2")) for r in rows) / n if n else None,
         "invalid_share": comp["invalid"] / n if n else None,
         "truncation_share": sum(bool(r.get("thinking_truncated") or r.get("finish_reason") == "length")
                                 for r in rows) / n if n else None,
         "composition": dict(comp), "baseline_composition": dict(bcomp), "baseline_n": len(base),
         "baseline_pass_rate": sum(bool(r.get("passed")) for r in base) / len(base) if base else None,
         "shift_vs_baseline": shifts, "per_template": per_t,
         "survivor_algorithms": dict(collections.Counter(r["adj_label"] if r["adj_label"] != "other" else
                                                         f"other:{r.get('adj_other_name')}" for r in cs)),
         "engine": CONFIGS[cid]["provider"] if CONFIGS[cid]["engine"] == "openrouter" else "local vLLM",
         "providers": dict(collections.Counter(str(r.get("provider")) for r in rows)),
         "quantization": CONFIGS[cid]["quantization"], "thinking": CONFIGS[cid]["thinking"],
         "params_b": CONFIGS[cid]["params_b"], "local": CONFIGS[cid].get("local", False),
         "mean_reasoning_tokens": (sum(int(r.get("reasoning_tokens") or 0) for r in rows) / n) if n else None,
         "cost_usd": sum(float(r.get("cost_usd") or 0) for r in rows) + sum(float(r.get("cost_usd") or 0) for r in base)}
    return m


def screen_table() -> dict[str, Any]:
    tab = {cid: config_metrics(cid) for cid in CONFIGS if labelled_path(cid, "ban").exists()}
    carried = read_json(RESULTS / "carried_rows.json")
    for cid, info in carried.items():
        n = info["n"]
        k = info.get("n_correct_survivors") or 0
        tab[cid] = {"config": cid, "name": CARRIED[cid]["name"], "arm": "ban (carried)", "banned_set": info["banned_set"],
                    "n": n, "n_correct_survivors": k, "share_cs": k / n, "share_cs_wilson95": wilson_ci(k, n),
                    "share_cs_upper95_one_sided": wilson_upper_one_sided(k, n), "composition": info["composition"],
                    "pass_rate": info.get("pass_rate"), "banned_mechanism_share": info.get("banned_share"),
                    "engine": CARRIED[cid]["engine"], "source": info["source"], "carried": True,
                    "params_b": CARRIED[cid]["params_b"], "thinking": CARRIED[cid]["thinking"]}
    write_json(RESULTS / "screen.json", tab)
    return tab


def select(tab: dict[str, Any]) -> dict[str, Any]:
    """Committed rule (new configurations only; carried rows are context)."""
    new = {c: m for c, m in tab.items() if not m.get("carried")}
    q = {c: m for c, m in new.items() if (m["share_cs"] or 0) >= SELECTION["threshold_share_cs"]}
    out: dict[str, Any] = {"Q": sorted(q), "threshold": SELECTION["threshold_share_cs"],
                           "shares": {c: m["share_cs"] for c, m in tab.items()},
                           "upper95_one_sided": {c: m["share_cs_upper95_one_sided"] for c, m in tab.items()}}
    if q:
        best = max(m["share_cs"] for m in q.values())
        tied = [c for c, m in q.items() if best - m["share_cs"] <= SELECTION["tie_window"]]
        tied.sort(key=lambda c: (-q[c]["share_cs_wilson95"][0], q[c]["params_b"], 0 if q[c].get("local") else 1))
        out.update({"m_star": tied[0], "tied": tied, "mode": "SELECTED",
                    "TP_RESULT": f"{tied[0]} ({CONFIGS[tied[0]]['name']}) obeys: share_cs = {q[tied[0]]['share_cs']:.2f}"})
    else:
        most = max(new, key=lambda c: (new[c]["n_correct_survivors"], -new[c]["params_b"]))
        if all(new[c]["n_correct_survivors"] == 0 for c in new):
            most = "C1"
        out.update({"m_star": most, "mode": "DESCRIPTIVE",
                    "TP_RESULT": "no tested open model obeys a five-name ban on this task"})
    return out
