#!/usr/bin/env python3
"""Step 2: family/yield per algorithm, name-scrub + verify (parse, pass status, label unchanged), uniform selection
of M <= 30 programs per measurable algorithm with halves, free-form labels and association profiles.
Also the scrubber acceptance test on the 22 references and 50 exp1 programs (testing plan T0-2)."""

from __future__ import annotations

import collections
import difflib
import random
import re
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import spearmanr

from config import (DATA, DATA_IN, LOGS, MIN_MEASURABLE, MODES, N_FORCED_TARGET, OTHER, RESULTS, SEED_HALVES,
                    SEED_SELECT, SUITE, TASKS, read_jsonl, setup_logging, sha256_text, write_json, write_jsonl)
from scrub import residual_names, scrub

FREE_LEX = {
    "t1": [("bibfs", r"bi-?directional\s+(bfs|breadth)"), ("iddfs", r"iterative[\s-]+deepening|\biddfs\b"),
           ("astar_gbfs", r"\ba\*|\ba-star\b|\ba star\b|best[\s-]+first|\bgbfs\b"),
           ("bfs", r"breadth[\s-]+first|\bbfs\b"), ("dfs", r"depth[\s-]+first|\bdfs\b"), ("dijkstra", r"dijkstra")],
    "t2": [("bidijkstra", r"bi-?directional\s+dijkstra"), ("bf_spfa", r"bellman|\bspfa\b|shortest path faster"),
           ("floyd", r"floyd|warshall"), ("dial", r"\bdial"), ("dijkstra", r"dijkstra")],
}


def free_label(task: str, text: str, x: str) -> str:
    """First catalogue name matched by the lexicon (earliest position, longest match) that is not X."""
    hits = []
    for mode, pat in FREE_LEX[task]:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            hits.append((m.start(), -(m.end() - m.start()), m.end(), mode))
    hits.sort()
    taken: list[tuple[int, int]] = []
    for s, _neg, e, mode in hits:
        if any(not (e <= a or s >= b) for a, b in taken):
            continue
        taken.append((s, e))
        if mode != x:
            return mode
    return OTHER


def verify_scrub(rows: list[dict[str, Any]], comment_only: bool = False) -> list[dict[str, Any]]:
    from labelling import label_texts

    todo = []
    for r in rows:
        try:
            if comment_only:
                code_s, info = scrub_comments_only(r["code"])
            else:
                code_s, info = scrub(r["code"])
        except (SyntaxError, ValueError, Exception) as e:  # noqa: BLE001 - tokenize errors are heterogeneous
            r["scrub_ok"], r["scrub_error"] = False, f"scrub: {type(e).__name__}"
            continue
        r["code_scrubbed"], r["scrub_info"] = code_s, info
        todo.append({"task": r["task"], "text": "```python\n" + code_s + "```", "_ref": r})
    lab = label_texts(todo)
    for q in lab:
        r = q["_ref"]
        r["scrub_label"], r["scrub_passed"] = q["label"], bool(q["passed"])
        r["scrub_ok"] = bool(q["label"] == r["label"] and bool(q["passed"]) == bool(r["passed"]))
        if not r["scrub_ok"]:
            r["scrub_error"] = f"label {r['label']}->{q['label']} passed {r['passed']}->{q['passed']}"
    return rows


def scrub_comments_only(code: str) -> tuple[str, dict]:
    """F5 fallback: comments/docstrings only (identifiers kept)."""
    import scrub as S

    old = S.has_stem
    S.has_stem = lambda name: False
    try:
        return S.scrub(code)
    finally:
        S.has_stem = old


def scrub_acceptance() -> dict[str, Any]:
    """Scrubber on the 22 references and 50 exp1 baseline/ban programs: parse, pass, label kept, no names left."""
    from labelling import label_texts
    import pipeline

    rows = []
    for t in TASKS:
        for r in pipeline.references(t):
            rows.append({"task": t, "code": r["code"], "src": f"ref:{r['file']}"})
    ex = [r for r in read_jsonl(DATA_IN / "exp1" / "labelled.jsonl") if r.get("code") and
          (r["condition"] in ("baseline",) or r["condition"].startswith("ban:")) and r["label"] != "no_code"]
    random.Random(5).shuffle(ex)
    for r in ex[:50]:
        rows.append({"task": r["task"], "code": r["code"], "src": f"exp1:{r['condition']}"})
    lab0 = label_texts([{"task": r["task"], "text": "```python\n" + r["code"] + "```"} for r in rows])
    for r, q in zip(rows, lab0):
        r["label"], r["passed"] = q["label"], bool(q["passed"])
    rows = verify_scrub(rows)
    resid = [r["src"] for r in rows if r.get("code_scrubbed") and residual_names(r["code_scrubbed"])]
    ok = [r for r in rows if r.get("scrub_ok")]
    return {"n": len(rows), "n_ok": len(ok), "failures": [{"src": r["src"], "error": r.get("scrub_error")}
                                                          for r in rows if not r.get("scrub_ok")],
            "residual_name_programs": resid, "pass": len(ok) == len(rows) and not resid,
            "examples": [r for r in rows if r.get("scrub_info", {}).get("renamed")][:5]}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("select_programs")
    lab = read_jsonl(DATA / "forced_labelled.jsonl")
    out_rows, yields, deviations = [], {}, []
    for t in TASKS:
        for j in MODES[t]:
            fam_stats = {}
            for fam in ("plain", "desc"):
                rr = [r for r in lab if r["task"] == t and r["j"] == j and r["family"] == fam]
                fam_stats[fam] = {"attempts": len(rr), "labelled": sum(r["label"] == j for r in rr),
                                  "passed_labelled": sum(r["label"] == j and bool(r["passed"]) for r in rr),
                                  "no_code": sum(r["label"] == "no_code" for r in rr),
                                  "labels": dict(collections.Counter(r["label"] for r in rr))}
            p, d = fam_stats["plain"], fam_stats["desc"]
            family = "plain" if (p["labelled"] >= N_FORCED_TARGET or d["labelled"] <= p["labelled"]) else "desc"
            fs = fam_stats[family]
            y = fs["labelled"] / max(1, fs["attempts"])
            measurable = fs["labelled"] >= MIN_MEASURABLE
            pool = [dict(r) for r in lab if r["task"] == t and r["j"] == j and r["family"] == family
                    and r["label"] == j and r.get("code")]
            yields[f"{t}|{j}"] = {"family": family, "yield": y, "measurable": measurable, **{f"{k}_{f}": v for f in fam_stats for k, v in fam_stats[f].items()}}
            if not measurable:
                logger.warning(f"{t}|{j}: FRLP-unmeasurable ({fs['labelled']} labelled in {family})")
                continue
            pool = verify_scrub(pool)
            ok = [r for r in pool if r.get("scrub_ok")]
            frac_fail = 1 - len(ok) / max(1, len(pool))
            scrub_mode = "full"
            if frac_fail > 0.30:
                deviations.append(f"{t}|{j}: {frac_fail:.0%} scrub failures -> comment-only scrubbing (F5)")
                pool2 = verify_scrub([dict(r, scrub_ok=None) for r in pool], comment_only=True)
                ok = [r for r in pool2 if r.get("scrub_ok")]
                scrub_mode = "comment_only"
            yields[f"{t}|{j}"].update({"n_scrub_verified": len(ok), "scrub_fail_frac": frac_fail,
                                       "scrub_mode": scrub_mode})
            if len(ok) < MIN_MEASURABLE:
                yields[f"{t}|{j}"]["measurable"] = False
                logger.warning(f"{t}|{j}: only {len(ok)} verified after scrubbing -> unmeasurable")
                continue
            rng = random.Random(f"{SEED_SELECT}|{t}|{j}")
            ok.sort(key=lambda r: (r["paraphrase_id"], r["sample_id"]))
            rng.shuffle(ok)
            m_j = min(N_FORCED_TARGET, len(ok))
            sel = ok[:m_j]
            # halves: ranks 0..19 split 10/10 (so the M=20 cut keeps balanced halves), ranks 20..29 split evenly
            halves = [None] * m_j
            for lo, hi in ((0, min(20, m_j)), (20, m_j)):
                idx = list(range(lo, hi))
                random.Random(f"{SEED_HALVES}|{t}|{j}|{lo}").shuffle(idx)
                for q, i in enumerate(idx):
                    halves[i] = "h1" if q < (len(idx) + 1) // 2 else "h2"
            for rank, (r, h) in enumerate(zip(sel, halves)):
                out_rows.append({"prog_id": f"{t}|{j}|{rank}", "task": t, "j": j, "family": family, "rank": rank,
                                 "m_j": m_j, "half": h, "paraphrase_id": r["paraphrase_id"],
                                 "sample_id": r["sample_id"], "seed": r["seed"], "passed": bool(r["passed"]),
                                 "label": r["label"], "labeller_source": r["labeller_source"],
                                 "code_raw": r["code"], "code_scrubbed": r["code_scrubbed"],
                                 "sha256": sha256_text(r["code_scrubbed"]), "sha256_raw": r["code_sha256"],
                                 "scrub_mode": scrub_mode, "renamed": r["scrub_info"]["renamed"],
                                 "text_is_fenced_code": r.get("text", "").strip() == ("```python\n" + r["code"]
                                                                                       + "```").strip(),
                                 "n_output_tokens": r.get("n_output_tokens")})
            logger.info(f"{t}|{j}: family={family} yield={y:.2f} verified={len(ok)}/{len(pool)} M={m_j}")
    resid = [r["prog_id"] for r in out_rows if r["scrub_mode"] == "full" and residual_names(r["code_scrubbed"])]
    write_jsonl(DATA / "forced_selected.jsonl", out_rows)
    # scrub examples
    ex = [r for r in out_rows if r["renamed"]][:5]
    md = ["# Scrub examples (5 diffs, raw -> scrubbed)\n"]
    for r in ex:
        diff = "\n".join(difflib.unified_diff(r["code_raw"].splitlines(), r["code_scrubbed"].splitlines(),
                                              "raw", "scrubbed", lineterm="", n=1))
        md.append(f"## {r['prog_id']}\n\n```diff\n{diff}\n```\n")
    (LOGS / "scrub_examples.md").write_text("\n".join(md))
    acc = scrub_acceptance()
    acc.pop("examples", None)
    # free-form association
    free = read_jsonl(DATA / "freeform_raw.jsonl")
    flab = []
    for r in free:
        flab.append({**{k: r[k] for k in ("task", "condition", "X", "sample_id", "seed", "model", "decoding",
                                          "template", "paraphrase_id")},
                     "text": r["text"], "label": free_label(r["task"], r["text"], r["X"]),
                     "labeller_source": "lexicon", "passed": None, "code_sha256": None, "code": None})
    write_jsonl(DATA / "freeform_labelled.jsonl", flab)
    meas = {t: [j for j in MODES[t] if yields.get(f"{t}|{j}", {}).get("measurable")] for t in TASKS}
    assoc, counts = {}, {}
    for t in TASKS:
        for x in MODES[t]:
            surv = [j for j in meas[t] if j != x]
            c = collections.Counter(r["label"] for r in flab if r["task"] == t and r["X"] == x)
            counts[f"{t}|{x}"] = dict(c)
            assoc[f"{t}|{x}"] = {j: (c.get(j, 0) + 1) / (20 + len(surv)) for j in surv}
    # replication against exp1's free-text map (old display names)
    old = read_jsonl(DATA_IN / "exp1" / "qwen_freetext.jsonl")
    rep = {}
    if old:
        import sys

        sys.path.insert(0, str(SUITE))
        for t in TASKS:
            xs, a_new, a_old = [], [], []
            for x in MODES[t]:
                rows_o = [r for r in old if r.get("task") == t and r.get("mode_X") == x]
                co = collections.Counter(free_label(t, r.get("raw", ""), x) for r in rows_o)
                for j in MODES[t]:
                    if j == x:
                        continue
                    xs.append(f"{x}->{j}")
                    a_new.append(counts[f"{t}|{x}"].get(j, 0))
                    a_old.append(co.get(j, 0))
            rho = spearmanr(a_new, a_old).correlation if len(set(a_new)) > 1 and len(set(a_old)) > 1 else None
            rep[t] = {"spearman_new_vs_exp1": rho, "n_pairs": len(xs), "n_exp1_rows": sum(
                1 for r in old if r.get("task") == t)}
    write_json(RESULTS / "association.json", {"profiles": assoc, "counts": counts, "replication_exp1": rep,
                                              "rule": "first catalogue name matched by the lexicon that is not X; "
                                                      "A_X(j) = (count_j + 1) / (20 + |S_X|)"})
    write_json(RESULTS / "yields.json", {"yields": yields, "deviations": deviations,
                                         "residual_name_programs": resid, "scrub_acceptance": acc,
                                         "n_selected": len(out_rows)})
    logger.info(f"selected {len(out_rows)} programs; residual-name programs={len(resid)}; scrub acceptance "
                f"{acc['n_ok']}/{acc['n']} pass={acc['pass']}; replication={rep}")


if __name__ == "__main__":
    main()
