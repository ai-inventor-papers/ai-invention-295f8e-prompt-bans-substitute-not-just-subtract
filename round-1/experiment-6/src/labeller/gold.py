#!/usr/bin/env python3
"""Gold set and labeller gate (per task).

Gold set = all references and variants + 30 model programs per task drawn from A0, A1 at T=1.3, A3 and A5,
stratified by provisional label (<= 8 per label; every 'other' and every runtime/AST disagreement first).
Two judge models from different families label every gold program; a third model adjudicates disagreements.
Gate: kappa(runtime, AST) >= 0.8 on gold model programs; 100% runtime and AST agreement on references;
>= 90% agreement between the final label and the adjudicated gold label. Also: forced-label agreement on A5.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import LABELS, REFS_DIR, RESULTS, TASKS, read_jsonl, setup_logging, write_json  # noqa: E402
from labeller.ast_rules import ast_label  # noqa: E402
from labeller.judge import ADJUDICATOR, GOLD_JUDGES, Budget, judge_many  # noqa: E402
from labeller.tracer import runtime_label  # noqa: E402

GOLD_FILE = LABELS / "gold_judgements.jsonl"
REF_MODE = {
    "t1_bfs.py": "bfs", "t1_dfs.py": "dfs", "t1_dfs_recursive.py": "dfs",
    "t1_bidirectional_bfs.py": "bidirectional_bfs", "t1_iddfs.py": "iddfs", "t1_iddfs_iterative.py": "iddfs",
    "t1_astar_greedy.py": "astar_greedy", "t1_greedy_best_first.py": "astar_greedy",
    "t1_dijkstra_unit.py": "dijkstra_unit", "t2_dijkstra.py": "dijkstra", "t2_dijkstra_eager.py": "dijkstra",
    "t2_bellman_ford_spfa.py": "bellman_ford_spfa", "t2_spfa.py": "bellman_ford_spfa",
    "t2_bidirectional_dijkstra.py": "bidirectional_dijkstra", "t2_floyd_warshall.py": "floyd_warshall",
    "t2_dial.py": "dial",
}


def cohen_kappa(a: list, b: list) -> float | None:
    a = ["none" if x is None else x for x in a]
    b = ["none" if x is None else x for x in b]
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def select_gold(samples: list[dict], task: str, n_target: int = 30, per_label: int = 8, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed + (0 if task == "T1" else 1))
    pool: dict[str, dict] = {}
    for s in samples:
        if s["task"] != task or s.get("code") is None or s["label"] == "unparseable":
            continue
        ok = s["arm"] in ("A0", "A3", "A5") or (s["arm"] == "A1" and s["decoding"]["T"] == 1.3)
        if ok and s["code_sha256"] not in pool:
            pool[s["code_sha256"]] = s
    progs = list(pool.values())
    rng.shuffle(progs)
    chosen, counts = [], Counter()
    hard = [p for p in progs if p["label"] == "other" or p["runtime_label"] != p["ast_label"]
            or p["runtime_label"] is None]
    for p in hard:
        if len(chosen) >= n_target * 0.6 or counts[p["label"]] >= per_label:
            continue
        chosen.append(p)
        counts[p["label"]] += 1
    by_label = defaultdict(list)
    for p in progs:
        if p not in chosen:
            by_label[p["label"]].append(p)
    labels = sorted(by_label, key=lambda k: len(by_label[k]))
    while len(chosen) < n_target and any(by_label[k] for k in labels):
        for k in labels:
            if by_label[k] and counts[k] < per_label and len(chosen) < n_target:
                chosen.append(by_label[k].pop())
                counts[k] += 1
        if all(counts[k] >= per_label or not by_label[k] for k in labels):
            rest = [p for k in labels for p in by_label[k]]
            for p in rest[: n_target - len(chosen)]:
                chosen.append(p)
            break
    return chosen


def main() -> None:
    logger = setup_logging("gold")
    samples = list(read_jsonl(RESULTS / "samples.jsonl"))
    gate: dict = {}
    budget = Budget(0.4)
    cached = {(r["task"], r["key"], r["model"]): r for r in read_jsonl(GOLD_FILE) if r.get("label")}
    for task in TASKS:
        gold = select_gold(samples, task)
        refs = sorted(REFS_DIR.glob(f"{task.lower()}_*.py"))
        items = [dict(task=task, key=f"ref:{f.name}", code=f.read_text(), kind="gold") for f in refs]
        items += [dict(task=task, key=f"prog:{g['code_sha256']}", code=g["code"], kind="gold") for g in gold]
        judg = defaultdict(dict)
        for model in GOLD_JUDGES:
            need = [it for it in items if (task, it["key"], model) not in cached]
            out = asyncio.run(judge_many(need, model, budget, concurrency=16)) if need else []
            good = [o for o in out if o.get("label")]
            from common import append_jsonl
            append_jsonl(GOLD_FILE, good)
            for o in good:
                cached[(task, o["key"], model)] = o
            for it in items:
                r = cached.get((task, it["key"], model))
                if r:
                    judg[it["key"]][model] = r["label"]
        need_adj = [it for it in items if len(set(judg[it["key"]].values())) > 1 or len(judg[it["key"]]) < 2]
        need_adj2 = [it for it in need_adj if (task, it["key"], ADJUDICATOR) not in cached]
        out = asyncio.run(judge_many(need_adj2, ADJUDICATOR, budget, concurrency=8)) if need_adj2 else []
        good = [o for o in out if o.get("label")]
        from common import append_jsonl
        append_jsonl(GOLD_FILE, good)
        for o in good:
            cached[(task, o["key"], ADJUDICATOR)] = o
        adjudicated = {}
        for it in items:
            v = list(judg[it["key"]].values())
            if len(v) == 2 and v[0] == v[1]:
                adjudicated[it["key"]] = v[0]
            else:
                r = cached.get((task, it["key"], ADJUDICATOR))
                adjudicated[it["key"]] = r["label"] if r else (v[0] if v else None)
        # references: runtime and AST must both equal the reference's mode
        ref_rows = []
        for f in refs:
            rt = runtime_label(f.read_text(), task)["label"]
            al = ast_label(f.read_text(), task)[0]
            ref_rows.append(dict(ref=f.name, mode=REF_MODE[f.name], runtime=rt, ast=al,
                                 gold=adjudicated.get(f"ref:{f.name}")))
        ref_agree = float(np.mean([r["runtime"] == r["mode"] and r["ast"] == r["mode"] for r in ref_rows]))
        ref_gold_agree = float(np.mean([r["gold"] == r["mode"] for r in ref_rows]))
        # gold model programs
        rl = [g["runtime_label"] for g in gold]
        al = [g["ast_label"] for g in gold]
        final = [g["label"] for g in gold]
        gl = [adjudicated.get(f"prog:{g['code_sha256']}") for g in gold]
        kappa_gold = cohen_kappa(rl, al)
        gold_agree = float(np.mean([f == g for f, g in zip(final, gl)])) if gold else None
        corr_pairs = [(f, g2) for f, g2, gg in zip(final, gl, gold) if gg["passed"]]
        gold_agree_correct = float(np.mean([f == g2 for f, g2 in corr_pairs])) if corr_pairs else None
        kappa_gold_correct = cohen_kappa([gg["runtime_label"] for gg in gold if gg["passed"]],
                                         [gg["ast_label"] for gg in gold if gg["passed"]])
        conf = Counter((f, g) for f, g in zip(final, gl))
        consensus = [(g, adjudicated.get(f"prog:{g['code_sha256']}")) for g in gold
                     if g["labeller_source"] == "runtime+ast"]
        judge_vs_consensus = float(np.mean([a["label"] != b for a, b in consensus])) if consensus else None
        # population-level runtime/AST agreement (all unique programs of the task)
        uniq = {}
        for s in samples:
            if s["task"] == task and s.get("code_sha256") and s["label"] != "unparseable":
                uniq[s["code_sha256"]] = s
        kappa_pop = cohen_kappa([u["runtime_label"] for u in uniq.values()], [u["ast_label"] for u in uniq.values()])
        agree_pop = float(np.mean([u["runtime_label"] == u["ast_label"] and u["runtime_label"] is not None
                                   for u in uniq.values()]))
        # forced-label agreement (A5)
        forced = [s for s in samples if s["task"] == task and s["arm"] == "A5"]
        fl = [s["label"] == s["condition"].split(":")[1] for s in forced]
        fl_c = [s["label"] == s["condition"].split(":")[1] for s in forced if s["passed"]]
        per_mode = {}
        for m in sorted({s["condition"].split(":")[1] for s in forced}):
            xs = [s for s in forced if s["condition"] == f"forced:{m}"]
            per_mode[m] = dict(n=len(xs), labelled_as_forced=sum(s["label"] == m for s in xs),
                               correct=sum(s["passed"] for s in xs),
                               verified=sum(s["label"] == m and s["passed"] for s in xs),
                               label_counts=dict(Counter(s["label"] for s in xs)))
        passed = bool(kappa_gold is not None and kappa_gold >= 0.8 and ref_agree == 1.0 and
                      gold_agree is not None and gold_agree >= 0.9)
        revisions = [
            "rev1 tracer T1: BFS monotonicity and heap-key matching use first pops only; >=97% non-decreasing steps",
            "rev1 tracer T1: A*/greedy fallback also accepts Spearman(key, h) >= 0.9 with few expansions",
            "rev1 tracer T2: no heap, no FIFO, growth exponent >= 1.6 -> bellman_ford_spfa (rounds over adjacency)",
            "rev1 AST T2: rounds over adjacency with a relaxation test, and FIFO label-correcting loops -> BF/SPFA",
            "rev2 tracer T2: bidirectional requires interleaved pops from the two heaps (>=2 switches)",
            "rev2 AST T2: bidirectional requires one loop popping two heaps",
            "pre-gate (references only): FW growth rule also accepts exponent>=2.2 with >=n^3/2 line events; "
            "list.pop() classified with the pre-pop length; W1/W2 made strongly connected with a FIFO gadget"]
        gate[task] = dict(
            n_gold_programs=len(gold), n_references=len(refs), kappa_runtime_ast_gold=kappa_gold,
            ref_agreement_runtime_and_ast=ref_agree, ref_agreement_gold_judges=ref_gold_agree,
            gold_agreement_final_vs_adjudicated=gold_agree,
            gold_agreement_correct_programs_only=gold_agree_correct, n_gold_correct=len(corr_pairs),
            kappa_runtime_ast_gold_correct_only=kappa_gold_correct,
            judge_disagrees_with_runtime_ast_consensus=judge_vs_consensus,
            kappa_runtime_ast_population=kappa_pop, runtime_ast_agreement_population=agree_pop,
            n_unique_programs=len(uniq), gate_passed=passed, revisions=revisions,
            flag=None if passed else "labeller_gate_failed",
            confusion_final_vs_gold={f"{a}->{b}": v for (a, b), v in conf.items()},
            gold_label_counts=dict(Counter(gl)), references=ref_rows,
            n_adjudicated=len(need_adj),
            forced_label_agreement=dict(all=float(np.mean(fl)) if fl else None,
                                        among_correct=float(np.mean(fl_c)) if fl_c else None,
                                        n=len(fl), per_mode=per_mode))
        logger.info(f"{task}: gate={passed} kappa_gold={kappa_gold} ref={ref_agree} gold_agree={gold_agree} "
                    f"pop_kappa={kappa_pop} forced={gate[task]['forced_label_agreement']['all']}")
    gate["gold_judges"] = GOLD_JUDGES
    gate["adjudicator"] = ADJUDICATOR
    gate["gold_cost_usd"] = round(budget.spent, 4)
    gate["budget_stopped"] = budget.stopped
    write_json(RESULTS / "labeller_gate.json", gate)


if __name__ == "__main__":
    main()
