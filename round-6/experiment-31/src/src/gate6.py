#!/usr/bin/env python3
"""Gate stage (ii) (plan S4 step 4), per unit, after its vLLM instruct and base rows are labelled:
gold set = every reference + the first 10 VALID base chat rows in slot order (k, then template) + 10 instruct programs
(twin T1.0 slots k = 10, 11, two per template). Each gold program is adjudicated by two blind judges from different
families (openai/gpt-4.1-mini, google/gemini-2.5-flash; deepseek/deepseek-chat-v3.1 breaks ties); runtime and AST
labels come from the labellers. PASS: references 100% (runtime AND AST), Cohen's kappa(runtime, AST) >= 0.8 on the
gold set (raw agreement >= 0.9 when kappa is degenerate because one label dominates; iteration-5 convention), runtime
vs adjudicated >= 0.9 (traceable items; the all-items and combined-vs-adjudicated values are reported).
One revision round (--revision): rules revised, re-scored on a fresh holdout (valid base rows 10..19 in slot order +
twin T1.0 slots k = 12, 13). After the gate: every runtime/AST disagreement of the unit is adjudicated and the base
audit (15 random valid base programs, two judge families) is run.
Usage: python src/gate6.py I1,I2 [--revision]
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import UNITS_DIR, setup_logging, utc_now, write_json  # noqa: E402
from judge6 import JUDGE_A, JUDGE_B, adjudicate_many, judge_one, spent  # noqa: E402
from labels_view6 import adjudicate_pending, load_final  # noqa: E402
from units_spec6 import catalogue  # noqa: E402
from unitlib6 import label_code, unit_mod  # noqa: E402


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1 - 1e-12:
        return None
    return (po - pe) / (1 - pe)


def gold_rows(u: str, holdout: bool = False) -> list[dict]:
    labs = [l for l in load_final([u]) if l.get("src") == "vllm"]
    base = sorted([l for l in labs if l["arm"] == "BASE" and l.get("valid")], key=lambda l: (l["slot"], l["template"]))
    ks = (12, 13) if holdout else (10, 11)
    inst = sorted([l for l in labs if l["arm"] == "TWIN" and l["slot"] in ks],
                  key=lambda l: (l["slot"], l["template"]))
    return (base[10:20] if holdout else base[:10]) + inst[:10]


def score(u: str, items: list[tuple[str, str]], truth: dict[str, str], rt: dict, al: dict, tag: str) -> dict:
    adj = {r["id"]: r for r in adjudicate_many([(i, u, c) for i, c in items], tag)}
    ids = [i for i, _ in items]
    tr_ids = [i for i in ids if rt[i] is not None and al[i] is not None]
    a = [str(rt[i]) for i in tr_ids]
    b = [str(al[i]) for i in tr_ids]
    kappa = cohen_kappa(a, b)
    raw = sum(x == y for x, y in zip(a, b)) / max(len(a), 1)
    adjd = [i for i in ids if adj[i]["label"] is not None]
    adjd_tr = [i for i in adjd if rt[i] is not None]
    rt_vs = sum(str(rt[i]) == adj[i]["label"] for i in adjd_tr) / max(len(adjd_tr), 1)
    rt_vs_all = sum(str(rt[i]) == adj[i]["label"] for i in adjd) / max(len(adjd), 1)
    ast_vs = sum(str(al[i]) == adj[i]["label"] for i in adjd) / max(len(adjd), 1)
    comb = {}
    for i in ids:
        if rt[i] is not None and rt[i] == al[i]:
            comb[i] = rt[i]
        elif rt[i] is None and al[i] is not None:
            comb[i] = al[i]
        elif al[i] is None and rt[i] is not None:
            comb[i] = rt[i]
        else:
            comb[i] = adj[i]["label"]
    comb_vs = sum(comb[i] == adj[i]["label"] for i in adjd) / max(len(adjd), 1)
    ref_rt = sum(rt[i] == truth[i] for i in truth) / max(len(truth), 1) if truth else None
    ref_ast = sum(al[i] == truth[i] for i in truth) / max(len(truth), 1) if truth else None
    judges_on_refs = sum(adj[i]["label"] == truth[i] for i in truth) / max(len(truth), 1) if truth else None
    kappa_ok = (kappa is not None and kappa >= 0.8) or (kappa is None and raw >= 0.9)
    return {"n": len(ids), "n_traceable": len(tr_ids), "kappa_runtime_ast": kappa, "kappa_ok": kappa_ok,
            "raw_agreement_runtime_ast": raw, "runtime_vs_adjudicated": rt_vs,
            "runtime_vs_adjudicated_all_items": rt_vs_all, "ast_vs_adjudicated": ast_vs,
            "combined_vs_adjudicated": comb_vs, "n_adjudicated": len(adjd), "ref_acc_runtime": ref_rt,
            "ref_acc_ast": ref_ast, "judges_on_references": judges_on_refs,
            "label_values": dict(Counter(adj[i]["label"] for i in ids)),
            "items": [{"id": i, "runtime": rt[i], "ast": al[i], "adjudicated": adj[i]["label"], "how": adj[i]["how"],
                       "judge_a": adj[i]["judge_a"], "judge_b": adj[i]["judge_b"], "judge_c": adj[i]["judge_c"]}
                      for i in ids]}


def run_gate(u: str, revision: bool = False) -> dict:
    mod = unit_mod(u)
    items, truth, rt, al = [], {}, {}, {}
    if not revision:
        for m, code in mod.REFERENCES.items():
            L = label_code(u, code, want_tests=False)
            iid = f"ref:{m}"
            items.append((iid, code))
            truth[iid] = m
            rt[iid], al[iid] = L["runtime_label"], L["ast_label"]
    gr = gold_rows(u, holdout=revision)
    for l in gr:
        if revision:
            L = label_code(u, l["code"], want_tests=False)   # revised rules re-scored on the fresh holdout
            rt[l["key"]], al[l["key"]] = L["runtime_label"], L["ast_label"]
        else:
            rt[l["key"]], al[l["key"]] = l.get("runtime_label"), l.get("ast_label")
        items.append((l["key"], l["code"]))
    if revision:
        for m, code in mod.REFERENCES.items():
            L = label_code(u, code, want_tests=False)
            iid = f"ref:{m}"
            items.append((iid, code))
            truth[iid] = m
            rt[iid], al[iid] = L["runtime_label"], L["ast_label"]
    sc = score(u, items, truth, rt, al, f"gate_ii{'_rev' if revision else ''}:{u}")
    status = "gated" if (sc["ref_acc_runtime"] == 1.0 and sc["ref_acc_ast"] == 1.0 and sc["kappa_ok"] and
                         sc["runtime_vs_adjudicated"] >= 0.9) else "failed"
    rep = {"unit": u, "utc": utc_now(), "status": status, "revision_round": revision,
           "gold": {"n_references": len(truth), "n_base": sum(1 for l in gr if l["arm"] == "BASE"),
                    "n_instruct": sum(1 for l in gr if l["arm"] == "TWIN"), **{k: v for k, v in sc.items()}},
           "catalogue": catalogue(u), "judge_spend_running": spent()}
    write_json(UNITS_DIR / u / ("gate_revision.json" if revision else "gate.json"), rep)
    logger.info(f"{u} gate (ii){' REVISION' if revision else ''}: {status}; kappa {sc['kappa_runtime_ast']}; raw "
                f"{sc['raw_agreement_runtime_ast']:.2f}; rt_vs_adj {sc['runtime_vs_adjudicated']:.2f}; refs "
                f"{sc['ref_acc_runtime']}/{sc['ref_acc_ast']}; comb {sc['combined_vs_adjudicated']:.2f}; spend "
                f"{spent():.3f}")
    return rep


def base_audit(u: str, n: int = 15) -> dict:
    labs = [l for l in load_final([u]) if l["arm"] in ("BASE", "PLAIN") and l.get("valid") and l.get("final")
            not in (None, "disputed")]
    rng = random.Random(f"base_audit|{u}")
    pick = rng.sample(labs, min(n, len(labs)))
    a = [judge_one(JUDGE_A, u, l["code"], f"base_audit:{u}") for l in pick]
    b = [judge_one(JUDGE_B, u, l["code"], f"base_audit:{u}") for l in pick]
    fin = [l["final"] for l in pick]
    agree_a = sum(x == y for x, y in zip(a, fin)) / max(len(pick), 1)
    agree_b = sum(x == y for x, y in zip(b, fin)) / max(len(pick), 1)
    agree_ab = sum(x == y for x, y in zip(a, b)) / max(len(pick), 1)
    rep = {"unit": u, "n": len(pick), "agreement_final_vs_judge_a": agree_a, "agreement_final_vs_judge_b": agree_b,
           "agreement_judges": agree_ab, "flag_below_0.8": min(agree_a, agree_b) < 0.8,
           "items": [{"key": l["key"], "final": f, "judge_a": x, "judge_b": y} for l, f, x, y in zip(pick, fin, a, b)]}
    write_json(UNITS_DIR / u / "base_audit.json", rep)
    logger.info(f"{u} base audit: final~A {agree_a:.2f}, final~B {agree_b:.2f}, A~B {agree_ab:.2f}")
    return rep


if __name__ == "__main__":
    setup_logging("gate6")
    rev = "--revision" in sys.argv
    post = "--post" in sys.argv
    for uu in sys.argv[1].split(","):
        if post:
            n = adjudicate_pending([uu])
            logger.info(f"{uu}: adjudicated {n} disagreement rows")
            base_audit(uu)
        else:
            run_gate(uu, revision=rev)
