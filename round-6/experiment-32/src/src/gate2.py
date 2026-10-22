#!/usr/bin/env python3
"""Gate stage (ii) (plan section 5), per unit, after its first instruct and base sessions:
gold set = every reference + 10 base-pilot programs (valid BASE rows in slot order k = 0, 1, ... over W1-W5) + 10
instruct gate-draw programs (GATE, k 100-101, disjoint from the twin's CRN slots).
Each gold program is adjudicated by two blind judges (tie-break: a third); runtime and AST labels come from the
labellers. PASS: references 100% (runtime AND AST), Cohen's kappa(runtime, AST) >= 0.8 (raw agreement >= 0.9 when
kappa is degenerate because one label dominates), runtime vs adjudicated >= 0.9.
The catalogue is FROZEN here (units/<u>/catalogue_frozen.json); B6's candidate extra mode joins it only when it
appears >= 2 times among the gate-draw + base-pilot programs (final labels, before freezing).
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import LABELS, UNITS_DIR, read_jsonl, setup_logging, utc_now, write_json  # noqa: E402
from judge5 import adjudicate_many, spent  # noqa: E402
from units_spec import UNITS, catalogue  # noqa: E402
from unitlib import label_code, unit_mod  # noqa: E402


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


def gold_rows(u: str) -> list[dict]:
    """Panel II (plan 1.2 f): 10 base-pilot programs (valid BASE rows of chat slots 0-29 = k 0-5, slot order) + 10
    instruct twin programs (valid TWIN rows, slot order; vLLM slots k >= 10 are drawn before the HF CRN slots)."""
    labs = [l for l in read_jsonl(LABELS) if l["unit"] == u and l.get("valid")]
    base = sorted([l for l in labs if l["arm"] == "BASE" and l["slot"] < 6], key=lambda l: (l["slot"], l["template"]))
    gate = sorted([l for l in labs if l["arm"] == "TWIN"], key=lambda l: (l["slot"], l["template"]))
    for l in gate:
        l["arm"] = "GATE"
    return base[:10] + gate[:10]


def run_gate(u: str, holdout: bool = False, revision: bool = False) -> dict:
    mod = unit_mod(u)
    extra_modes = getattr(mod, "EXTRA_MODES", [])
    extra = {m: UNITS[u]["candidate_extra_mode"][m] for m in extra_modes} if extra_modes else None
    refs = dict(mod.REFERENCES)
    items, truth, rt, al = [], {}, {}, {}
    for m, code in refs.items():
        L = label_code(u, code, want_tests=False)
        iid = f"ref:{m}"
        items.append((iid, u, code))
        truth[iid] = m
        rt[iid], al[iid] = L["runtime_label"], L["ast_label"]
    gr = gold_rows(u)
    for l in gr:
        items.append((l["key"], u, l["code"]))
        L = label_code(u, l["code"], want_tests=False)        # live labels: the current (possibly revised) rules
        rt[l["key"]], al[l["key"]] = L["runtime_label"], L["ast_label"]
    adj = {r["id"]: r for r in adjudicate_many(items, f"gate_ii:{u}", extra_by_unit={u: extra} if extra else None)}
    ids = [i for i, _, _ in items]
    # runtime abstains (None) when a program cannot be traced (crash, timeout, stripped instrumentation); the AST
    # label is then used with a flag. kappa and runtime-vs-adjudicated are computed over traceable items; the
    # all-items versions and the combined-vs-adjudicated agreement (all items) are reported and gated too.
    tr_ids = [i for i in ids if rt[i] is not None and al[i] is not None]
    a = [str(rt[i]) for i in tr_ids]
    b = [str(al[i]) for i in tr_ids]
    kappa = cohen_kappa(a, b)
    raw = sum(x == y for x, y in zip(a, b)) / max(len(a), 1)
    kappa_all = cohen_kappa([str(rt[i]) for i in ids], [str(al[i]) for i in ids])
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
    ref_rt = sum(rt[i] == truth[i] for i in truth) / len(truth)
    ref_ast = sum(al[i] == truth[i] for i in truth) / len(truth)
    judges_on_refs = sum(adj[i]["label"] == truth[i] for i in truth) / len(truth)
    kappa_ok = (kappa is not None and kappa >= 0.8) or (kappa is None and raw >= 0.9)
    status = "gated" if (ref_rt == 1.0 and ref_ast == 1.0 and kappa_ok and rt_vs >= 0.9 and comb_vs >= 0.9) \
        else "failed"
    # B6 candidate extra mode: >= 2 occurrences among gate-draw + base-pilot programs (combined labels)
    cat = catalogue(u)
    extra_decision = None
    if extra_modes:
        cnt = Counter(comb[l["key"]] for l in gr)
        for em in extra_modes:
            joins = cnt.get(em, 0) >= 2
            extra_decision = {"mode": em, "count_gold_samples": cnt.get(em, 0), "joins_catalogue": joins}
            if joins:
                cat = cat + [em]
    rep = {"unit": u, "utc": utc_now(), "status": status, "holdout": holdout,
           "gold": {"n": len(ids), "n_references": len(truth), "n_base_pilot": sum(1 for l in gr if l["arm"] == "BASE"),
                    "n_gate_draw": sum(1 for l in gr if l["arm"] == "GATE"), "kappa_runtime_ast": kappa,
                    "kappa_runtime_ast_all_items": kappa_all, "n_traceable": len(tr_ids),
                    "runtime_vs_adjudicated_all_items": rt_vs_all,
                    "raw_agreement_runtime_ast": raw, "ref_acc_runtime": ref_rt, "ref_acc_ast": ref_ast,
                    "runtime_vs_adjudicated": rt_vs, "ast_vs_adjudicated": ast_vs,
                    "combined_vs_adjudicated": comb_vs, "n_adjudicated": len(adjd), "judges_on_references": judges_on_refs,
                    "label_values": dict(Counter(adj[i]["label"] for i in ids))},
           "items": [{"id": i, "runtime": rt[i], "ast": al[i], "adjudicated": adj[i]["label"], "how": adj[i]["how"],
                      "judge_a": adj[i]["judge_a"], "judge_b": adj[i]["judge_b"], "judge_c": adj[i]["judge_c"]}
                     for i in ids],
           "extra_mode_decision": extra_decision, "judge_spend_running": spent()}
    rep["revision_round"] = revision
    write_json(UNITS_DIR / u / ("gate_revision.json" if revision else "gate.json"), rep)
    if revision:
        rep["holdout"] = run_holdout(u, extra)
        write_json(UNITS_DIR / u / "gate_revision.json", rep)
    if True:
        write_json(UNITS_DIR / u / "catalogue_frozen.json",
                   {"unit": u, "utc": utc_now(), "catalogue": cat, "extra_mode_decision": extra_decision,
                    "frozen_at": "gate stage (ii), before any decisive sample is labelled"})
    logger.info(f"{u} gate (ii): {status}; kappa {kappa}; raw {raw:.2f}; rt_vs_adj {rt_vs:.2f}; refs {ref_rt}/{ref_ast};"
                f" judges_on_refs {judges_on_refs:.2f}; extra {extra_decision}")
    return rep


def run_holdout(u: str, extra: dict | None) -> dict:
    """Revision-round holdout: 6 NEW valid base programs (after the first 10 pilot programs), adjudicated."""
    labs = [l for l in read_jsonl(LABELS) if l["unit"] == u and l.get("valid") and l["arm"] == "BASE"]
    base = sorted(labs, key=lambda l: (l["slot"], l["template"]))[10:16]
    adj = adjudicate_many([(l["key"], u, l["code"]) for l in base], f"gate_holdout:{u}",
                          extra_by_unit={u: extra} if extra else None)
    items = []
    for l, a in zip(base, adj):
        comb = l.get("label") if l.get("label") is not None else a["label"]
        items.append({"id": l["key"], "runtime": l.get("runtime_label"), "ast": l.get("ast_label"),
                      "combined": comb, "adjudicated": a["label"], "how": a["how"]})
    ok = [i for i in items if i["adjudicated"] is not None]
    return {"n": len(items), "n_adjudicated": len(ok),
            "combined_vs_adjudicated": sum(i["combined"] == i["adjudicated"] for i in ok) / max(len(ok), 1),
            "runtime_vs_adjudicated": sum(str(i["runtime"]) == i["adjudicated"] for i in ok) / max(len(ok), 1),
            "items": items}


if __name__ == "__main__":
    setup_logging("gate2")
    rev = "--revision" in sys.argv
    for uu in sys.argv[1].split(","):
        run_gate(uu, revision=rev)
