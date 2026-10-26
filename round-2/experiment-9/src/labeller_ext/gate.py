#!/usr/bin/env python3
"""5f labeller gate (before any ban prompt).

(i) every reference variant gets the correct mode from BOTH runtime and AST (100%);
(ii) gold set = forced:X programs (sample_index 0 = development, used for rule revision; sample_index 1 =
     evaluation) + 20 baseline programs per task stratified by runtime label (all non-modal labels included),
     each labelled blind by two judge families, a third model on disagreement -> adjudicated label;
(iii) Cohen's kappa runtime vs AST on the evaluation gold (target >= 0.8), runtime vs adjudicated (>= 0.9),
     AST vs adjudicated, combined label vs adjudicated, confusion matrix; spot check of 'agree' programs.
"""

from __future__ import annotations

import collections
import random
from typing import Any

from loguru import logger

from common import (DATA_DIR, GOLD_JUDGES, GOLD_TIEBREAK, JUDGE_MODEL, LABEL_DIR, MODES, RESULTS_DIR, TASKS,
                    read_jsonl, sha256_text, write_json, write_jsonl)

GOLD_FILE = LABEL_DIR / "gold_set.jsonl"
GATE_FILE = LABEL_DIR / "gate_report.json"


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return 1.0 if pe >= 1.0 else (po - pe) / (1 - pe)


def build_gold() -> list[dict[str, Any]]:
    from labeller.extract import extract_code
    from pipeline import load_eval_cache, mechanical_labels

    cache = load_eval_cache()
    rows = [r for r in read_jsonl(DATA_DIR / "raw_preban.jsonl") if r["kind"] == "program"]
    gold: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not r["condition"].startswith("forced:"):
            continue
        code, _ = extract_code(r["text"])
        if code is None:
            continue
        key = f"{r['task']}|{sha256_text(code)}"
        split = "dev" if r["sample_index"] == 0 else "eval"
        if key in gold:
            if split == "dev":
                gold[key]["split"] = "dev"  # a program seen in development never counts as evaluation
            continue
        mk = mechanical_labels(r["task"], code, cache[key])
        gold[key] = {"key": key, "task": r["task"], "source": r["condition"], "intended": r["condition"].split(":")[1],
                     "split": split, "code": code, "passed": cache[key]["passed"], **mk}
    rng = random.Random(20261019)
    for task in TASKS:
        base = {}
        for r in rows:
            if r["task"] != task or r["condition"] != "baseline":
                continue
            code, _ = extract_code(r["text"])
            if code is None:
                continue
            key = f"{task}|{sha256_text(code)}"
            if key in base or key in gold:
                continue
            base[key] = {"key": key, "task": task, "source": "baseline", "intended": None, "split": "eval",
                         "code": code, "passed": cache[key]["passed"], **mechanical_labels(task, code, cache[key])}
        by = collections.defaultdict(list)
        for k in sorted(base):
            by[base[k]["runtime_label"]].append(base[k])
        modal = max(by, key=lambda x: len(by[x])) if by else None
        chosen = []
        for lbl in sorted(by):
            if lbl != modal:
                chosen += by[lbl]
        chosen = chosen[:20]
        pool = by.get(modal, [])
        rng.shuffle(pool)
        chosen += pool[:max(0, 20 - len(chosen))]
        for g in chosen:
            g["source"] = f"baseline(runtime={g['runtime_label']})"
            gold[g["key"]] = g
    return list(gold.values())


def adjudicate(gold: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from labeller.judge import judge_many

    items = [{"task": g["task"], "code": g["code"]} for g in gold]
    a, _ = judge_many(items, GOLD_JUDGES[0], "gold_adjudication", 0.3)
    b, _ = judge_many(items, GOLD_JUDGES[1], "gold_adjudication", 0.3)
    dis = [i for i, (x, y) in enumerate(zip(a, b)) if x and y and x["label"] != y["label"]]
    c_items = [items[i] for i in dis]
    c, _ = judge_many(c_items, GOLD_TIEBREAK, "gold_adjudication", 0.3) if c_items else ([], None)
    cmap = {i: r for i, r in zip(dis, c)}
    for i, g in enumerate(gold):
        la = a[i]["label"] if a[i] else None
        lb = b[i]["label"] if b[i] else None
        g["judge_a"], g["judge_b"] = la, lb
        g["judge_c"] = cmap[i]["label"] if (i in cmap and cmap[i]) else None
        if la is not None and la == lb:
            g["adjudicated"] = la
        elif g["judge_c"] is not None and g["judge_c"] in (la, lb):
            g["adjudicated"] = g["judge_c"]
        else:
            g["adjudicated"] = "unresolved"
        g["judge_a_rationale"] = a[i]["rationale"] if a[i] else None
    return gold


def _metrics(gs: list[dict[str, Any]]) -> dict[str, Any]:
    res = [g for g in gs if g["adjudicated"] != "unresolved"]
    rt = [g["runtime_label"] for g in res]
    at = [g["ast_label"] for g in res]
    adj = [g["adjudicated"] for g in res]
    comb = []
    for g in res:
        if g["runtime_label"] == g["ast_label"] and g["runtime_label"] not in ("unknown", "inconsistent"):
            comb.append(g["runtime_label"])
        else:
            comb.append(g["judge_a"] or "other")  # judge_a is the production judge model
    conf = collections.Counter((x, y) for x, y in zip(rt, adj))
    return {
        "n": len(gs), "n_unresolved": len(gs) - len(res),
        "kappa_runtime_ast": cohen_kappa(rt, at),
        "agree_runtime_ast": sum(x == y for x, y in zip(rt, at)) / max(1, len(res)),
        "acc_runtime_vs_adjudicated": sum(x == y for x, y in zip(rt, adj)) / max(1, len(res)),
        "acc_ast_vs_adjudicated": sum(x == y for x, y in zip(at, adj)) / max(1, len(res)),
        "acc_combined_vs_adjudicated": sum(x == y for x, y in zip(comb, adj)) / max(1, len(res)),
        "kappa_judges_a_b": cohen_kappa([g["judge_a"] or "none" for g in res], [g["judge_b"] or "none" for g in res]),
        "runtime_unknown_or_inconsistent": sum(x in ("unknown", "inconsistent") for x in rt),
        "confusion_runtime_x_adjudicated": {f"{x}->{y}": n for (x, y), n in sorted(conf.items())},
        "forced_compliance_adjudicated": (sum(1 for g in res if g["intended"] and g["adjudicated"] == g["intended"])
                                          / max(1, sum(1 for g in res if g["intended"]))),
    }


def spot_check_agree() -> dict[str, Any]:
    """10 'agree' programs per task (non-forced pre-ban conditions) re-labelled by the production judge."""
    from labeller.extract import extract_code
    from labeller.judge import judge_many
    from pipeline import load_eval_cache, mechanical_labels

    cache = load_eval_cache()
    rng = random.Random(7)
    out = {}
    for task in TASKS:
        rows = [r for r in read_jsonl(DATA_DIR / "raw_preban.jsonl") if r["kind"] == "program" and r["task"] == task
                and not r["condition"].startswith("forced")]
        seen, picks = set(), []
        rng.shuffle(rows)
        for r in rows:
            code, _ = extract_code(r["text"])
            if code is None:
                continue
            key = f"{task}|{sha256_text(code)}"
            if key in seen:
                continue
            seen.add(key)
            mk = mechanical_labels(task, code, cache[key])
            if mk["runtime_label"] == mk["ast_label"] and mk["runtime_label"] not in ("unknown", "inconsistent"):
                picks.append({"task": task, "code": code, "label": mk["runtime_label"]})
            if len(picks) >= 10:
                break
        js, _ = judge_many([{"task": p["task"], "code": p["code"]} for p in picks], JUDGE_MODEL, "spot_check", 0.05)
        agree = sum(1 for p, j in zip(picks, js) if j and j["label"] == p["label"])
        out[task] = {"n": len(picks), "judge_agrees": agree,
                     "pairs": [(p["label"], j["label"] if j else None) for p, j in zip(picks, js)]}
    return out


def stage_gate() -> None:
    from pipeline import mechanical_labels, references
    from tasks.harness import parallel_map, run_probes

    # (i) references
    ref_ok = {}
    for task in TASKS:
        refs = references(task)
        trs = parallel_map(lambda r: {"probes": run_probes(task, r["code"])}, refs, workers=8, desc=f"gate refs {task}")
        for r, tr in zip(refs, trs):
            mk = mechanical_labels(task, r["code"], tr)
            ref_ok[f"{task}/{r['file']}"] = {"mode": r["mode"], "runtime": mk["runtime_label"], "ast": mk["ast_label"],
                                             "ok": mk["runtime_label"] == r["mode"] == mk["ast_label"]}
    refs_pass = all(v["ok"] for v in ref_ok.values())
    # (ii) gold set
    gold = adjudicate(build_gold())
    write_jsonl(GOLD_FILE, gold)
    dev = [g for g in gold if g["split"] == "dev"]
    ev = [g for g in gold if g["split"] == "eval"]
    m_eval = _metrics(ev)
    m_dev = _metrics(dev)
    per_task = {t: _metrics([g for g in ev if g["task"] == t]) for t in TASKS}
    gate_passed = bool(refs_pass and (m_eval["kappa_runtime_ast"] or 0) >= 0.8
                       and m_eval["acc_runtime_vs_adjudicated"] >= 0.9)
    report = {
        "references_100pct": refs_pass, "references": ref_ok,
        "gold_counts": {"dev": len(dev), "eval": len(ev),
                        "by_source": dict(collections.Counter(g["source"].split("(")[0] for g in gold))},
        "eval_metrics": m_eval, "dev_metrics": m_dev, "eval_metrics_per_task": per_task,
        "targets": {"kappa_runtime_ast": 0.8, "acc_runtime_vs_adjudicated": 0.9},
        "gate_passed": gate_passed,
        "spot_check_agree": spot_check_agree(),
        "note": ("Disagreements and unknown/inconsistent runtime labels are always routed to the blind judge in "
                 "production, so the combined-label accuracy is the operative one; combined accuracy uses the "
                 "production judge (one of the two gold judges) and is therefore optimistic."),
    }
    write_json(GATE_FILE, report)
    write_json(RESULTS_DIR / "labeller_gate.json", report)
    logger.info(f"gate: refs={refs_pass} eval={ {k: v for k, v in m_eval.items() if not isinstance(v, dict)} } "
                f"passed={gate_passed}")
    _ = MODES
