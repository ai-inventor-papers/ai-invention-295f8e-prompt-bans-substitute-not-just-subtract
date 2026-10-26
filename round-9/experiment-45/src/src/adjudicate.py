#!/usr/bin/env python3
"""Stage 5 adjudication. Candidate set A (per configuration, ban/confirm arm):
  - rows that pass with label_raw not in B_c (candidate survivors),
  - every row labelled 'other', 'dijkstra_unit', 'jps' or 'biastar' (classes that failed the iteration-2 gold gate),
  - a stratified random 10% of rows labelled inside B_c (audit; seed 0).
Baseline rows labelled other/dijkstra_unit/jps/biastar are adjudicated before B_c is computed (commit #2).
Each program goes to the two gated judges (blind to configuration and arm). Agreement -> adj_label. Disagreement ->
third judge + executor manual read (data/manual_reads.jsonl, logged reasons); a remaining 3-way split without a manual
read falls back to the label with mechanical (runtime/AST) support, else the third judge (flagged).
Rows outside A keep adj_label = label_raw. Audit disagreement > 10% -> every ban row of that configuration adjudicated.
"""

from __future__ import annotations

import collections
import math
import random
from typing import Any

from loguru import logger

from common import ADJ_PAIR, ADJ_THIRD, DATA, GATE_FAILED_CLASSES, read_jsonl, sha256_text

MANUAL = DATA / "manual_reads.jsonl"
REVIEW_CLASSES = ("other",) + GATE_FAILED_CLASSES


def manual_reads() -> dict[str, dict[str, Any]]:
    return {r["code_sha256"]: r for r in read_jsonl(MANUAL)}


def candidate_set(rows: list[dict[str, Any]], banned: list[str] | None, audit_frac: float = 0.10,
                  seed: int = 0) -> tuple[list[int], dict[int, str]]:
    """Indices of rows to adjudicate and the reason for each."""
    reason: dict[int, str] = {}
    for i, r in enumerate(rows):
        if r.get("code") is None:
            continue
        lab = r["label_raw"]
        if banned is not None and r.get("passed") and lab not in banned:
            reason[i] = "candidate_survivor"
        elif lab in REVIEW_CLASSES:
            reason[i] = f"review_class:{lab}"
    if banned is not None:
        pool = [i for i, r in enumerate(rows) if r.get("code") is not None and r["label_raw"] in banned
                and i not in reason]
        k = math.ceil(audit_frac * len(pool)) if pool else 0
        rng = random.Random(seed)
        for i in sorted(rng.sample(pool, k)) if k else []:
            reason[i] = "audit_in_banned"
    return sorted(reason), reason


def adjudicate_codes(codes: list[str], purpose: str) -> dict[str, dict[str, Any]]:
    """sha256(code) -> {adj_label, adj_other_name, adj_source, votes}."""
    import judge_tp

    uniq = list(dict.fromkeys(codes))
    if not uniq:
        return {}
    ja = judge_tp.judge_codes(uniq, ADJ_PAIR[0], purpose=f"adj:{purpose}")
    jb = judge_tp.judge_codes(uniq, ADJ_PAIR[1], purpose=f"adj:{purpose}")
    dis = [c for c, a, b in zip(uniq, ja, jb) if not (a and b and a["label"] == b["label"])]
    jc = dict(zip(dis, judge_tp.judge_codes(dis, ADJ_THIRD, purpose=f"adj3:{purpose}"))) if dis else {}
    man = manual_reads()
    out: dict[str, dict[str, Any]] = {}
    for c, a, b in zip(uniq, ja, jb):
        k = sha256_text(c)
        votes = {"a": a["label"] if a else None, "b": b["label"] if b else None}
        names = [x.get("other_name") for x in (a, b) if x and x.get("label") == "other"]
        if a and b and a["label"] == b["label"]:
            out[k] = {"adj_label": a["label"], "adj_source": "judges_agree", "votes": votes}
        else:
            cc = jc.get(c)
            votes["c"] = cc["label"] if cc else None
            if cc and cc.get("label") == "other":
                names.append(cc.get("other_name"))
            cnt = collections.Counter(v for v in votes.values() if v)
            top = cnt.most_common()
            if k in man:
                out[k] = {"adj_label": man[k]["label"], "adj_source": "manual_read", "votes": votes,
                          "manual_reason": man[k].get("reason")}
            elif top and top[0][1] >= 2:
                out[k] = {"adj_label": top[0][0], "adj_source": "third_judge_majority", "votes": votes,
                          "needs_manual": False}
            else:
                out[k] = {"adj_label": votes.get("c") or votes.get("a") or votes.get("b") or "other",
                          "adj_source": "split_third_judge", "votes": votes, "needs_manual": True}
        known = [n for n in names if n and str(n).strip().lower() not in ("unknown", "none", "null", "")]
        out[k]["adj_other_name"] = known[0] if (out[k]["adj_label"] == "other" and known) else None
        if k in man and out[k]["adj_label"] == "other":
            out[k]["adj_other_name"] = man[k].get("other_name")
    return out


def apply_adjudication(rows: list[dict[str, Any]], banned: list[str] | None, purpose: str) -> dict[str, Any]:
    """In place: sets adj_label / adj_source / adj_reason / judge_labels on every row. Returns audit stats."""
    idx, reason = candidate_set(rows, banned)
    codes = [rows[i]["code"] for i in idx]
    res = adjudicate_codes(codes, purpose)
    for i, r in enumerate(rows):
        if r.get("code") is None:
            r.update({"adj_label": "invalid", "adj_source": "invalid", "adj_reason": None, "judge_labels": None,
                      "adj_other_name": None})
            continue
        if i in reason:
            a = res.get(r["code_sha256"])
            if a is None:
                r.update({"adj_label": r["label_raw"], "adj_source": "judge_unavailable", "adj_reason": reason[i],
                          "judge_labels": None, "adj_other_name": None})
            else:
                r.update({"adj_label": a["adj_label"], "adj_source": a["adj_source"], "adj_reason": reason[i],
                          "judge_labels": a["votes"], "adj_other_name": a.get("adj_other_name"),
                          "needs_manual": a.get("needs_manual", False)})
        else:
            r.update({"adj_label": r["label_raw"], "adj_source": "labeller", "adj_reason": None, "judge_labels": None,
                      "adj_other_name": None})
    audit = [rows[i] for i in idx if reason[i] == "audit_in_banned"]
    dis = sum(1 for r in audit if r["adj_label"] != r["label_raw"])
    stats = {"n_adjudicated": len(idx), "reasons": dict(collections.Counter(reason.values())),
             "audit_n": len(audit), "audit_disagree": dis,
             "audit_disagreement_rate": dis / len(audit) if audit else None,
             "label_changes": sum(1 for i in idx if rows[i]["adj_label"] != rows[i]["label_raw"]),
             "sources": dict(collections.Counter(rows[i]["adj_source"] for i in idx))}
    if banned is not None and audit and dis / len(audit) > 0.10:
        logger.warning(f"[{purpose}] audit disagreement {dis}/{len(audit)} > 10% -> adjudicating all ban rows")
        rest = [i for i, r in enumerate(rows) if r.get("code") is not None and i not in reason]
        res2 = adjudicate_codes([rows[i]["code"] for i in rest], purpose + ":extended")
        for i in rest:
            a = res2.get(rows[i]["code_sha256"])
            if a:
                rows[i].update({"adj_label": a["adj_label"], "adj_source": a["adj_source"],
                                "adj_reason": "extended_after_audit", "judge_labels": a["votes"],
                                "adj_other_name": a.get("adj_other_name"), "needs_manual": a.get("needs_manual")})
        stats["extended"] = len(rest)
    return stats
