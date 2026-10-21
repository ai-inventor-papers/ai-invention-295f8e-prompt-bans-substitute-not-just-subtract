"""Phase 4 per task (Stage-A order): gold set, blind two-judge adjudication with tie-break, labeller gate,
frozen FRLP sets, and the per-task bench files."""

from __future__ import annotations

import inspect
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

from . import astrules, rtrules
from .astrules import ast_label
from .catalogue import TASKS, display_name
from .judge import Judge
from .probes import make_probes, run_trace
from .refs import REFS
from .rtrules import runtime_label
from .stats import cohen_kappa, kappa_bootstrap, pabak, raw_agreement

FRLP_M = 30


def build_gold(task: str, pilot: list[dict], forced: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    gold = []
    # 10 pilot programs: distinct labels first, then random
    pil = [r for r in pilot if r["task"] == task and r["code"]]
    by = defaultdict(list)
    for r in pil:
        by[r["label"]].append(r)
    chosen = []
    for lab in sorted(by):
        chosen.append(rng.choice(by[lab]))
    rest = [r for r in pil if r not in chosen]
    rng.shuffle(rest)
    chosen = (chosen + rest)[:10]
    for r in chosen:
        gold.append({"gold_id": r["sample_id"], "source": "pilot", "code": r["code"], "runtime": r["runtime_label"],
                     "ast": r["ast_label"], "combined": r["label"], "known": None, "direction_subset": True})
    for m, code in REFS[task].items():
        gold.append({"gold_id": f"ref:{m}", "source": "reference", "code": code, "runtime": None, "ast": None,
                     "combined": m, "known": m, "direction_subset": True})
    for m in TASKS[task]["modes"]:
        fm = [r for r in forced if r["task"] == task and r["forced_mode"] == m and r["code"]]
        for r in rng.sample(fm, min(2, len(fm))):
            gold.append({"gold_id": r["sample_id"], "source": "forced", "code": r["code"], "runtime": r["runtime_label"],
                         "ast": r["ast_label"], "combined": r["label"], "known": None, "direction_subset": False})
    return gold


def adjudicate(judge: Judge, task: str, gold: list[dict]) -> None:
    recs1 = judge.label_many([("j1", task, g["code"]) for g in gold])
    recs2 = judge.label_many([("j2", task, g["code"]) for g in gold])
    dis = [i for i, (a, b) in enumerate(zip(recs1, recs2)) if a.get("label") != b.get("label")]
    recs3 = judge.label_many([("j3", task, gold[i]["code"]) for i in dis]) if dis else []
    r3 = dict(zip(dis, recs3))
    for i, g in enumerate(gold):
        g["j1"], g["j2"] = recs1[i].get("label"), recs2[i].get("label")
        if i in r3:
            g["j3"] = r3[i].get("label")
            votes = Counter(x for x in (g["j1"], g["j2"], g["j3"]) if x)
            top = votes.most_common(1)[0] if votes else (None, 0)
            g["adjudicated"] = top[0] if top[1] >= 2 else g["j3"]
            g["adjudication"] = "tie_break"
        else:
            g["j3"] = None
            g["adjudicated"] = g["j1"]
            g["adjudication"] = "agree"
        if g["adjudicated"] is None:
            g["adjudication"] = "unverifiable"


def gate_metrics(gold: list[dict], subset: bool = False) -> dict:
    gs = [g for g in gold if (g["direction_subset"] or not subset)]
    rt = [g["runtime"] for g in gs]
    ast = [g["ast"] for g in gs]
    k = cohen_kappa(rt, ast)
    lo, hi = kappa_bootstrap(rt, ast)
    refs = [g for g in gs if g["source"] == "reference"]
    ref_rt = sum(g["runtime"] == g["known"] for g in refs) / max(len(refs), 1)
    ref_ast = sum(g["ast"] == g["known"] for g in refs) / max(len(refs), 1)
    adj = [g for g in gs if g.get("adjudicated")]
    rt_adj = sum(g["runtime"] == g["adjudicated"] for g in adj) / max(len(adj), 1)
    comb_adj = sum(g["combined"] == g["adjudicated"] for g in adj) / max(len(adj), 1)
    ref_judge = sum(g.get("adjudicated") == g["known"] for g in refs) / max(len(refs), 1)
    return {"n": len(gs), "kappa_runtime_ast": k, "kappa_ci95": [lo, hi], "pabak": pabak(rt, ast),
            "raw_agreement": raw_agreement(rt, ast), "ref_acc_runtime": ref_rt, "ref_acc_ast": ref_ast,
            "runtime_vs_adjudicated": rt_adj, "combined_vs_adjudicated": comb_adj, "n_adjudicated": len(adj),
            "judges_on_references": ref_judge,
            "n_label_values": len(set(rt) | set(ast))}


def passes(m: dict) -> bool:
    return (m["kappa_runtime_ast"] >= 0.8 and m["ref_acc_runtime"] == 1.0 and m["ref_acc_ast"] == 1.0
            and m["runtime_vs_adjudicated"] >= 0.90)


def frlp_sets(task: str, forced: list[dict]) -> dict:
    out = {}
    for m in TASKS[task]["modes"]:
        att = [r for r in forced if r["task"] == task and r["forced_mode"] == m]
        att.sort(key=lambda r: (r.get("round") if (r.get("paraphrase_id") or 0) >= 0 else 1000 + (r.get("round") or 0),
                                r.get("paraphrase_id") if r.get("paraphrase_id") is not None else 99))
        lab = [r for r in att if r["label"] == m]
        ver = [r for r in lab if r.get("scrub_verified")]
        chosen = ver[:FRLP_M]
        half_ctr = Counter()
        rows = []
        for r in chosen:
            k = r["paraphrase_id"]
            half_ctr[k] += 1
            rows.append({"program_id": r["sample_id"], "paraphrase_id": k, "half": 1 + (half_ctr[k] - 1) % 2,
                         "passed": r["passed"]})
        pk = Counter(r["paraphrase_id"] for r in att)
        out[m] = {"n_attempts": len(att), "n_labelled": len(lab), "n_scrub_dropped": len(lab) - len(ver),
                  "adherence": len(lab) / max(len(att), 1), "M": len(chosen), "programs": rows,
                  "proposal_counts": {str(k): v for k, v in sorted(pk.items())},
                  "status": "ok" if len(chosen) >= FRLP_M else ("insufficient" if len(chosen) < 15 else "short")}
    return out


def write_task_files(root: Path, task: str, gold: list[dict], metrics: dict, sets: dict, pilot: list[dict],
                     forced: list[dict], assoc: list[dict], status: str, rounds: int) -> None:
    c = TASKS[task]
    d = root / "bench" / c["task_id"]
    hdr = f'"""Frozen {{}} for {c["task_id"]} (snapshot of bench/common/{{}}; shared helpers included)."""\n\n'
    (d / "ast_rules.py").write_text(hdr.format("AST rules", "astrules.py") + inspect.getsource(astrules))
    (d / "runtime_rules.py").write_text(hdr.format("runtime rules", "rtrules.py") + inspect.getsource(rtrules))
    (d / "probes.json").write_text(json.dumps(make_probes(task), indent=1))
    with (d / "gold_set.jsonl").open("w") as f:
        for g in gold:
            f.write(json.dumps(g) + "\n")
    (d / "gate.json").write_text(json.dumps({"task": task, "status": status, "revision_rounds": rounds, **metrics},
                                            indent=1))
    with (d / "forced_programs.jsonl").open("w") as f:
        for r in forced:
            if r["task"] == task:
                f.write(json.dumps(r) + "\n")
    with (d / "pilot_rows.jsonl").open("w") as f:
        for r in pilot:
            if r["task"] == task:
                f.write(json.dumps(r) + "\n")
    with (d / "association.jsonl").open("w") as f:
        for a in assoc:
            if a["task"] == task:
                f.write(json.dumps(a) + "\n")
    (d / "frlp_sets.json").write_text(json.dumps(sets, indent=1))


def run_gate(root: Path, order: list[str], deadline_ts: float | None = None) -> dict:
    import time
    pilot = [json.loads(l) for l in (root / "data" / "samples_pilot.jsonl").open()]
    forced = [json.loads(l) for l in (root / "data" / "samples_forced.jsonl").open()]
    assoc = [json.loads(l) for l in (root / "data" / "association.jsonl").open()]
    judge = Judge(root)
    summary = {}
    for i, t in enumerate(order):
        if deadline_ts is not None and time.time() > deadline_ts:
            summary[t] = {"status": "not_reached"}
            continue
        gold = build_gold(t, pilot, forced, seed=20261020 + i)
        for g in gold:
            if g["source"] == "reference":
                g["runtime"] = runtime_label(t, run_trace(g["code"], t))
                g["ast"] = ast_label(t, g["code"])
        adjudicate(judge, t, gold)
        full = gate_metrics(gold)
        sub = gate_metrics(gold, subset=True)
        pop_rt = [r["runtime_label"] for r in pilot + forced if r["task"] == t and r["label"] != "invalid"]
        pop_ast = [r["ast_label"] for r in pilot + forced if r["task"] == t and r["label"] != "invalid"]
        metrics = {"gold": full, "direction_subset": sub, "population_kappa_runtime_ast": cohen_kappa(pop_rt, pop_ast),
                   "population_n": len(pop_rt), "judge_spend_running": judge.spent,
                   "unverifiable": sum(1 for g in gold if g.get("adjudication") == "unverifiable")}
        ok = passes(full)
        status = "gated" if ok else "failed_round0"
        sets = frlp_sets(t, forced)
        write_task_files(root, t, gold, metrics, sets, pilot, forced, assoc, status, 0)
        summary[t] = {"status": status, **{k: full[k] for k in ("kappa_runtime_ast", "kappa_ci95", "pabak", "raw_agreement",
                                                                 "ref_acc_runtime", "ref_acc_ast", "runtime_vs_adjudicated",
                                                                 "combined_vs_adjudicated", "n")}}
        logger.info(f"GATE {t}: {status} kappa={full['kappa_runtime_ast']:.3f} CI={full['kappa_ci95']} "
                    f"pabak={full['pabak']:.3f} refs rt/ast={full['ref_acc_runtime']:.2f}/{full['ref_acc_ast']:.2f} "
                    f"rt-vs-adj={full['runtime_vs_adjudicated']:.3f} n={full['n']}")
    return summary


def revise(root: Path, tasks: list[str], round_no: int) -> dict:
    """Revision round: re-apply the revised runtime rules from stored traces, re-combine, re-score the same gold set
    (same seed, cached adjudications) and adjudicate a fresh 6-program holdout."""
    from .combine import combine, load_raw_samples, write_shared_rows
    from .retrace import apply_runtime_rules
    sources = ["samples_pilot_raw.jsonl", "samples_forced_raw.jsonl"]
    if (root / "data" / "samples_forced_topup_raw.jsonl").exists():
        sources.append("samples_forced_topup_raw.jsonl")
    apply_runtime_rules(root)
    combined = combine(root, sources)
    write_shared_rows(root, combined, load_raw_samples(root, sources))
    order = json.loads((root / "results" / "stageA_nominations.json").read_text())["order"]
    pilot = [json.loads(l) for l in (root / "data" / "samples_pilot.jsonl").open()]
    forced = [json.loads(l) for l in (root / "data" / "samples_forced.jsonl").open()]
    assoc = [json.loads(l) for l in (root / "data" / "association.jsonl").open()]
    judge = Judge(root)
    out = {}
    for t in tasks:
        i = order.index(t)
        gold = build_gold(t, pilot, forced, seed=20261020 + i)
        for g in gold:
            if g["source"] == "reference":
                g["runtime"] = runtime_label(t, run_trace(g["code"], t))
                g["ast"] = ast_label(t, g["code"])
        adjudicate(judge, t, gold)
        full = gate_metrics(gold)
        sub = gate_metrics(gold, subset=True)
        used = {g["gold_id"] for g in gold}
        rng = random.Random(20261020 + 1000 * round_no + i)
        pool = [r for r in pilot + forced if r["task"] == t and r["code"] and r["sample_id"] not in used]
        hold = [{"gold_id": r["sample_id"], "source": "holdout", "code": r["code"], "runtime": r["runtime_label"],
                 "ast": r["ast_label"], "combined": r["label"], "known": None, "direction_subset": False}
                for r in rng.sample(pool, min(6, len(pool)))]
        adjudicate(judge, t, hold)
        h_acc = sum(h["runtime"] == h["adjudicated"] for h in hold) / max(len(hold), 1)
        pop_rt = [r["runtime_label"] for r in pilot + forced if r["task"] == t and r["label"] != "invalid"]
        pop_ast = [r["ast_label"] for r in pilot + forced if r["task"] == t and r["label"] != "invalid"]
        metrics = {"gold": full, "direction_subset": sub, "population_kappa_runtime_ast": cohen_kappa(pop_rt, pop_ast),
                   "population_n": len(pop_rt), "holdout": {"n": len(hold), "runtime_vs_adjudicated": h_acc,
                                                            "items": [{k: h[k] for k in ("gold_id", "runtime", "ast",
                                                                                         "adjudicated")} for h in hold]},
                   "judge_spend_running": judge.spent}
        status = "gated" if passes(full) else f"failed_round{round_no}"
        write_task_files(root, t, gold, metrics, frlp_sets(t, forced), pilot, forced, assoc, status, round_no)
        out[t] = {"status": status, "revision_rounds": round_no, "holdout_runtime_vs_adjudicated": h_acc,
                  **{k: full[k] for k in ("kappa_runtime_ast", "kappa_ci95", "pabak", "raw_agreement", "ref_acc_runtime",
                                          "ref_acc_ast", "runtime_vs_adjudicated", "combined_vs_adjudicated", "n")}}
        logger.info(f"REVISION {round_no} {t}: {status} kappa={full['kappa_runtime_ast']:.3f} "
                    f"rt-vs-adj={full['runtime_vs_adjudicated']:.3f} holdout={h_acc:.2f}")
    return out
