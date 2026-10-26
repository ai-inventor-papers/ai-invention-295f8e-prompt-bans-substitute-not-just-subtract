"""(0c) Novelty audit, final stage: final classes (majority of A and B, C on disagreement; the manual pass overrides
only with a recorded reason), Cohen's kappa with a bootstrap CI and the confusion matrix, controls, class counts by
condition / model / task with instruction-driven conditions flagged, the novelty answer with its rule-of-three bound,
and multi-ban avoidance recomputed with 'other' kept separate (exp9 TOP, ARC, SCATTER, TOP5)."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from common.paths import AUDIT, RESULTS, SEED, TABLES, read_json, read_jsonl, sha256_text, src, write_json
from common.stats import cohen_kappa, wilson
from sections import s0c_novelty as N

INSTR = N.INSTRUCTION_CONDS


def _parsed(res: dict[str, Any], iid: str, j: str) -> dict[str, Any]:
    return ((res.get(iid, {}).get(j) or {}).get("parsed") or {})


def run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sel = N.build_selection(rows)
    controls = N.build_controls()
    items = sel["A"] + sel["B_TOP"] + sel["B"]
    cache = N.load_cache()
    res: dict[str, dict[str, Any]] = defaultdict(dict)
    for it in controls + items:
        p = sha256_text(N.build_prompt(it["task"], it["code"]))
        for j in "ABC":
            if (j, it["item_id"], p) in cache:
                res[it["item_id"]][j] = cache[(j, it["item_id"], p)]
    commit = (AUDIT / "selection_commit.txt").read_text() if (AUDIT / "selection_commit.txt").exists() else ""
    manual = {r["item_id"]: r for r in read_jsonl(AUDIT / "manual_pass.jsonl")} if (AUDIT / "manual_pass.jsonl").exists() else {}
    refs = N.reference_shingles()
    table = []
    for it in items:
        a, b, c = (_parsed(res, it["item_id"], j) for j in "ABC")
        fc, how = N.final_class(res.get(it["item_id"], {}))
        m = manual.get(it["item_id"])
        final = fc
        override = None
        if m and m.get("override") and m.get("manual_class") != fc:
            final, override = m["manual_class"], m.get("manual_reason")
        closest = None
        for p in (c, a, b):
            if p.get("class") == fc and (p.get("catalogue_match") or p.get("closest_known_algorithm")):
                closest = p.get("catalogue_match") or p.get("closest_known_algorithm")
                break
        jac, jarg = N.max_jaccard(it["code"], it["task"], refs)
        instr = any(INSTR.search(cnd) for cnd in it["conditions"])
        table.append({"item_id": it["item_id"], "set": it["set"], "task": it["task"], "label": it["label_fine"],
                      "passed": it["passed"], "models": it["models"], "exps": it["exps"], "conditions": it["conditions"],
                      "n_copies": it["n_copies"], "instruction_driven": instr,
                      "judge_A": a.get("class"), "judge_B": b.get("class"), "judge_C": c.get("class"),
                      "match_A": a.get("catalogue_match"), "match_B": b.get("catalogue_match"),
                      "closest_A": a.get("closest_known_algorithm"), "closest_B": b.get("closest_known_algorithm"),
                      "summary_A": a.get("mechanism_summary"), "final_judge_class": fc, "final_how": how,
                      "final_class": final, "manual_class": m.get("manual_class") if m else None,
                      "manual_reason": m.get("manual_reason") if m else None, "manual_override": override,
                      "closest_known": closest, "max_ast4_jaccard": jac, "max_ast4_jaccard_ref": jarg,
                      "code": it["code"], "provenance": it["provenance"]})
    df = pd.DataFrame(table)
    # agreement
    both = df[df["judge_A"].notna() & df["judge_B"].notna()]
    kappa = cohen_kappa(both["judge_A"].tolist(), both["judge_B"].tolist())
    rng = np.random.default_rng(SEED)
    kb = []
    aa, bb = both["judge_A"].tolist(), both["judge_B"].tolist()
    for _ in range(2000):
        idx = rng.integers(0, len(aa), len(aa))
        kb.append(cohen_kappa([aa[i] for i in idx], [bb[i] for i in idx]))
    kb = np.array([x for x in kb if np.isfinite(x)])
    conf = pd.crosstab(both["judge_A"], both["judge_B"]).to_dict()
    kappa_A = {}
    for s in ("A", "B_TOP", "B"):
        sub = both[both["set"] == s]
        kappa_A[s] = cohen_kappa(sub["judge_A"].tolist(), sub["judge_B"].tolist()) if len(sub) else math.nan
    # collapsed agreement: NOVEL vs not-NOVEL, and DEGENERATE vs known (LABELLER_MISS + CATALOGUE_VARIANT)
    col = {"LABELLER_MISS": "KNOWN", "CATALOGUE_VARIANT": "KNOWN", "NOVEL_ALGORITHM": "NOVEL",
           "DEGENERATE_OR_HARDCODED": "DEGENERATE"}
    kappa_collapsed = cohen_kappa([col[x] for x in aa], [col[x] for x in bb])
    agree_collapsed = float(np.mean([col[x] == col[y] for x, y in zip(aa, bb)]))
    # manual agreement on Set A
    mA = df[(df["set"] == "A") & df["manual_class"].notna()]
    man_agree = float(np.mean(mA["manual_class"] == mA["final_judge_class"])) if len(mA) else math.nan
    man_agree_col = float(np.mean([col.get(x) == col.get(y) for x, y in zip(mA["manual_class"], mA["final_judge_class"])])) if len(mA) else math.nan
    ctrl = N.score_controls(controls, res)
    ctrl_shuf = N.score_controls(controls, res, shuffle_expected=True, seed=SEED)
    ctrl_identity = sum(1 for r in ctrl["pos_rows"] if r["match_A"] == r["expected"] and r["match_B"] == r["expected"])
    ctrl_novel = sum(1 for r in ctrl["pos_rows"] if r["final_class"] == "NOVEL_ALGORITHM") + \
        sum(1 for r in ctrl["neg_rows"] if r["final_class"] == "NOVEL_ALGORITHM")
    # novelty answer (correct programs = Set A)
    A = df[df["set"] == "A"]
    n_novel_final = int((A["final_class"] == "NOVEL_ALGORITHM").sum())
    n_novel_any_judge = int(((A["judge_A"] == "NOVEL_ALGORITHM") | (A["judge_B"] == "NOVEL_ALGORITHM") |
                             (A["judge_C"] == "NOVEL_ALGORITHM")).sum())
    n_novel_manual = int((A["manual_class"] == "NOVEL_ALGORITHM").sum())
    N_A = len(A)
    N_A_dup = int(A["n_copies"].sum())
    n_correct_all = sum(1 for r in rows if r["passed"] is True and r["dedup_key"])
    n_correct_unique = len({r["dedup_key"] for r in rows if r["passed"] is True and r["dedup_key"]})
    answer = {"correct_other_unique": N_A, "correct_other_with_duplicates": N_A_dup,
              "confirmed_novel_correct": n_novel_final, "novel_calls_any_single_judge": n_novel_any_judge,
              "novel_manual": n_novel_manual,
              "rule_of_three_upper_95_over_correct_other": 3 / N_A if n_novel_final == 0 and N_A else None,
              "rule_of_three_upper_95_over_all_correct_unique": 3 / n_correct_unique if n_novel_final == 0 else None,
              "n_correct_programs_unique_all_files": n_correct_unique, "n_correct_programs_with_duplicates": n_correct_all,
              "scope": "the 11 declared artifacts (origin files only) plus the 1,200-program exp3 pools copy inside exp8; "
                       "about 9,000 other exp3 programs were not audited",
              "statement": ("no instruction or knob produced a correct novel algorithm (judge-confirmed: 0 of "
                            f"{N_A} unique correct out-of-catalogue programs; 95% upper bound {3 / max(1, N_A):.3f} on "
                            f"that population, {3 / max(1, n_correct_unique):.5f} over all {n_correct_unique} unique "
                            "correct programs audited)") if n_novel_final == 0 else
                           f"{n_novel_final} correct program(s) were judged NOVEL; see the follow-up block"}
    followups = [N.novel_followup({"item_id": r["item_id"], "task": r["task"], "code": r["code"]})
                 for _, r in df[df["final_class"] == "NOVEL_ALGORITHM"].iterrows()]
    # class counts by condition / model / task
    by = []
    for _, r in df.iterrows():
        for cnd in r["conditions"]:
            by.append({"set": r["set"], "task": r["task"], "model": "|".join(r["models"]), "condition": cnd,
                       "instruction_driven": bool(INSTR.search(cnd)), "final_class": r["final_class"]})
    bydf = pd.DataFrame(by)
    counts = (bydf.groupby(["set", "task", "model", "condition", "instruction_driven", "final_class"]).size()
              .reset_index(name="n"))
    counts.to_csv(TABLES / "novelty_class_counts.csv", index=False)
    cmap = sorted({(c, bool(INSTR.search(c))) for c in bydf["condition"]})
    pd.DataFrame([{"condition": c, "instruction_driven": f} for c, f in cmap]).to_csv(TABLES / "condition_class_map.csv",
                                                                                     index=False)
    instr_rows = df[df["instruction_driven"] & (df["set"] == "A")]
    # multi-ban avoidance (exp9)
    item_by_key = {}
    for it in items:
        item_by_key[it["dedup_key"]] = it["item_id"]
    fc_by_item = {r["item_id"]: r for r in table}
    av = []
    for cond in ("multi:TOP", "multi:ARC", "multi:SCATTER", "multi:TOP5"):
        rs = [r for r in rows if r["exp"] == "exp9" and r["condition"] == cond]
        banned = set(rs[0]["banned_set"])

        def lab9(r):
            return r["label_fine"] if r["label_fine"] in ("astar", "gbfs") else r["label"]

        n = len(rs)
        cat = Counter()
        corrected = Counter()
        reassigned = []
        for r in rs:
            lb = lab9(r)
            k = ("banned" if lb in banned else "unparseable" if lb == "unparseable" else
                 "other" if lb in ("other", "other_ext") else "nonbanned_catalogue")
            cat[k] += 1
            kc = k
            if k in ("other", "nonbanned_catalogue") and r["dedup_key"] in item_by_key:
                fr = fc_by_item.get(item_by_key[r["dedup_key"]])
                if fr and fr["final_class"] in ("LABELLER_MISS", "CATALOGUE_VARIANT"):
                    mt = N.match_name("t1", fr["closest_known"]) or N.match_name("t1", fr["closest_A"])
                    mt9 = {"astar": "astar", "gbfs": "gbfs", "dijkstra": "dijkstra_unit"}.get(mt, mt)
                    if mt9 in banned:
                        kc = "banned"
                        reassigned.append({"item_id": fr["item_id"], "label": lb, "judged_as": mt9})
            corrected[kc] += 1
        rec = {"condition": cond, "banned_set": sorted(banned), "n": n}
        for k in ("banned", "nonbanned_catalogue", "other", "unparseable"):
            rec[f"{k}_share"] = cat[k] / n
            rec[f"{k}_wilson"] = wilson(cat[k], n)
            rec[f"{k}_n"] = cat[k]
        rec["avoidance_raw"] = 1 - cat["banned"] / n
        rec["avoidance_raw_wilson"] = wilson(n - cat["banned"], n)
        rec["avoidance_corrected"] = 1 - corrected["banned"] / n
        rec["avoidance_corrected_wilson"] = wilson(n - corrected["banned"], n)
        rec["n_reassigned_to_banned"] = len(reassigned)
        rec["reassigned"] = reassigned
        rec["avoidance_catalogue_only"] = cat["nonbanned_catalogue"] / n
        av.append(rec)
    pd.DataFrame([{k: v for k, v in r.items() if k != "reassigned"} for r in av]).to_csv(
        TABLES / "multiban_avoidance_corrected.csv", index=False)
    out = {"n_items": len(items), "counts_unique": sel["counts_unique"], "counts_with_duplicates": sel["counts_with_duplicates"],
           "strata": sel["strata"], "selection_commit": commit,
           "kappa_A_B": kappa, "kappa_ci95": (float(np.quantile(kb, 0.025)), float(np.quantile(kb, 0.975))),
           "kappa_by_set": kappa_A, "kappa_collapsed_known_novel_degenerate": kappa_collapsed,
           "agreement_collapsed": agree_collapsed, "confusion_A_rows_B_cols": conf,
           "n_tiebreaks": int(df["judge_C"].notna().sum()),
           "final_class_counts": {s: dict(Counter(df[df["set"] == s]["final_class"])) for s in ("A", "B_TOP", "B")},
           "judge_only_class_counts": {s: dict(Counter(df[df["set"] == s]["final_judge_class"])) for s in ("A", "B_TOP", "B")},
           "manual_agreement_setA_exact": man_agree, "manual_agreement_setA_collapsed": man_agree_col,
           "manual_n": int(len(mA)), "manual_class_counts_setA": dict(Counter(mA["manual_class"])),
           "controls": ctrl, "controls_placebo_wrong_names": {"pos_hits": ctrl_shuf["pos_hits"], "pos_n": ctrl_shuf["pos_n"]},
           "controls_identity_both_judges": ctrl_identity, "controls_called_novel": ctrl_novel,
           "controls_gate": ("FAILED on the strict class criterion (>= 9/10 LABELLER_MISS with the right name): "
                             f"{ctrl['pos_hits']}/10; both judges named the right algorithm in {ctrl_identity}/10; "
                             f"negatives {ctrl['neg_hits']}/5; no control was called NOVEL")
           if not ctrl["pass"] else "PASSED",
           "novelty_answer": answer, "novel_followups": followups,
           "instruction_driven_setA": {"n": int(len(instr_rows)), "final_classes": dict(Counter(instr_rows["final_class"]))},
           "multiban_avoidance": av,
           "spend_usd_judges": float(sum(r.get("cost", 0.0) for r in cache.values())),
           "judges": N.JUDGES, "sources": [src("exp9", "data/samples.jsonl")] + sorted({p["source"] for it in items for p in it["provenance"]})}
    write_json(RESULTS / "novelty_audit.json", {**out, "table": [{k: v for k, v in r.items() if k != "code"} for r in table]})
    pd.DataFrame([{k: (v if not isinstance(v, (list, dict)) else str(v)) for k, v in r.items() if k not in ("code", "provenance")}
                  for r in table]).to_csv(TABLES / "novelty_audit.csv", index=False)
    logger.info(f"novelty: kappa {kappa:.3f}; final A {out['final_class_counts']['A']}; controls {out['controls_gate']}")
    return {**out, "table": table}
