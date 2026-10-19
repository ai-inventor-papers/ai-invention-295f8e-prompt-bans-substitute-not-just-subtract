#!/usr/bin/env python3
"""Labeller gate (before any summary and before the forecast commit).

Gold set per task: 10 random vLLM-baseline programs, 6 steered programs (2 each from c = 0.5, 1.0 and c*),
all references, and 2 hand-written off-catalogue programs. Two judge models label every gold item with
rationales; a third resolves their disagreements (references / off-catalogue items have known truth).
Criteria: Cohen kappa(runtime, AST) >= 0.8; 100% agreement on the references; >= 90% runtime-versus-
adjudicated agreement. A task failing after the revision rounds is flagged 'labeller_limited' (its
disagreements then always use adjudicated labels). Writes gold/gold_set.jsonl, results/labeller_gate.json.
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, GOLD_DIR, LABEL_CACHE, RAW_DIR, RESULTS_DIR, TASKS, TASKS_DIR, read_jsonl, setup_logger, sha256_text  # noqa: E402
from analysis.stats import cohen_kappa, kappa_ci, wilson  # noqa: E402
from labeller.ast_rules import ast_label  # noqa: E402
from labeller.judge import Judge  # noqa: E402
from labeller.label import run_code  # noqa: E402
from labeller.tracer import runtime_label  # noqa: E402
from loguru import logger  # noqa: E402

JUDGES = ["google/gemini-2.5-flash-lite", "openai/gpt-4.1-mini"]
RESOLVER = "anthropic/claude-haiku-4.5"
REF_LABEL = {"T1_bfs": "bfs", "T1_dfs": "dfs", "T1_bidirectional_bfs": "bidirectional_bfs", "T1_iddfs": "iddfs",
             "T1_astar": "astar", "T1_dijkstra_unit": "dijkstra_unit", "T2_dijkstra": "dijkstra",
             "T2_bellman_ford": "bellman_ford_spfa", "T2_spfa": "bellman_ford_spfa",
             "T2_bidirectional_dijkstra": "bidirectional_dijkstra", "T2_floyd_warshall": "floyd_warshall",
             "T2_dial": "dial"}


def norm(lab: str | None) -> str:
    return "other" if lab in (None, "unknown") else lab


def pick_programs(task: str, raw: str, k: int, rng: random.Random) -> list[dict]:
    rows = read_jsonl(RAW_DIR / raw)
    cands = []
    for r in rows:
        f = LABEL_CACHE / task / f"{sha256_text(r['text'])}.json"
        if f.exists():
            lab = json.loads(f.read_text())
            if lab.get("code"):
                cands.append({"source": raw, "paraphrase_id": r["paraphrase_id"], "sample_id": r["sample_id"],
                              "code": lab["code"], "passed": lab["passed"]})
    rng.shuffle(cands)
    return cands[:k]


def gold_items(task: str, cstar: float, layer: int) -> list[dict]:
    rng = random.Random(f"gold-{task}")
    items = [dict(x, kind="baseline") for x in pick_programs(task, f"vllm_{task}_baseline.jsonl", 10, rng)]
    for c in (0.5, 1.0, cstar):
        items += [dict(x, kind=f"steered_c{c:g}") for x in pick_programs(task, f"hf_{task}_steer-dc-c{c:g}-L{layer}.jsonl", 2, rng)]
    for p in sorted((TASKS_DIR / "references").glob(f"{task}_*.py")):
        items.append({"source": f"references/{p.name}", "kind": "reference", "code": p.read_text(),
                      "truth": REF_LABEL[p.stem]})
    from tasks.build_tests import OFFCAT
    for name, code in OFFCAT[task].items():
        items.append({"source": f"offcat/{name}", "kind": "off_catalogue", "code": code, "truth": "other"})
    return items


async def judge_all(items: list[tuple[str, dict]]) -> None:
    j = Judge(cap_usd=0.60)
    sem = asyncio.Semaphore(12)
    for model in JUDGES:
        outs = await asyncio.gather(*[j.call(model, t, it["code"], sem) for t, it in items])
        for (t, it), o in zip(items, outs):
            it.setdefault("judges", {})[model] = None if o is None else {"label": o["label"], "rationale": o.get("rationale")}
    need = [(t, it) for t, it in items if len({(v or {}).get("label") for v in it["judges"].values()}) > 1]
    outs = await asyncio.gather(*[j.call(RESOLVER, t, it["code"], sem) for t, it in need])
    for (t, it), o in zip(need, outs):
        it["resolver"] = None if o is None else {"label": o["label"], "rationale": o.get("rationale")}
    logger.info(f"gate judge spend ${j.spent:.4f} over {j.n_calls} calls (stopped={j.stopped})")


def main() -> None:
    setup_logger("gate")
    cst = json.loads((RESULTS_DIR / "cstar.json").read_text())
    layer = int(cst["layer"])
    allitems = []
    for t in TASKS:
        for it in gold_items(t, cst[t]["c_star"], layer):
            res = run_code(t, it["code"])
            al = ast_label(t, it["code"])
            it["label_runtime"] = runtime_label(t, res.get("trace") or {}, al.get("facts"))
            it["label_ast"] = al["label"]
            it["passed_tests"] = res.get("passed")
            allitems.append((t, it))
    asyncio.run(judge_all(allitems))
    report = {"criteria": {"kappa_runtime_ast_min": 0.8, "reference_agreement": 1.0, "runtime_vs_adjudicated_min": 0.9}}
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    with (GOLD_DIR / "gold_set.jsonl").open("w") as f:
        for t, it in allitems:
            js = [v["label"] for v in it["judges"].values() if v]
            if "truth" in it:
                adj, src = it["truth"], "known_truth"
            elif len(set(js)) == 1 and js:
                adj, src = js[0], "two_judges_agree"
            elif it.get("resolver"):
                adj, src = it["resolver"]["label"], "resolver"
            else:
                adj, src = norm(it["label_ast"]), "ast_judge_unavailable"
            it["adjudicated"], it["adjudication_source"] = adj, src
            f.write(json.dumps({"task": t, **{k: v for k, v in it.items()}}) + "\n")
    for t in TASKS:
        its = [it for tt, it in allitems if tt == t]
        rt = [norm(it["label_runtime"]) for it in its]
        ast_ = [norm(it["label_ast"]) for it in its]
        adj = [it["adjudicated"] for it in its]
        refs = [it for it in its if it["kind"] == "reference"]
        k = cohen_kappa(rt, ast_)
        ref_ok = all(it["label_runtime"] == it["truth"] and it["label_ast"] == it["truth"] for it in refs)
        agree = sum(a == b for a, b in zip(rt, adj))
        comb = [a if a == b else c for a, b, c in zip(rt, ast_, adj)]  # pipeline label: agreement else judge
        judge_acc = {}
        for m in JUDGES:
            known = [it for it in its if "truth" in it and it["judges"].get(m)]
            judge_acc[m] = (sum(it["judges"][m]["label"] == it["truth"] for it in known) / len(known)) if known else None
        rep = {"n_gold": len(its), "kappa_runtime_ast": k, "kappa_ci95": kappa_ci(rt, ast_),
               "reference_agreement_100pct": ref_ok, "runtime_vs_adjudicated": agree / len(its),
               "runtime_vs_adjudicated_ci95": wilson(agree, len(its)),
               "ast_vs_adjudicated": sum(a == b for a, b in zip(ast_, adj)) / len(its),
               "pipeline_vs_adjudicated": sum(a == b for a, b in zip(comb, adj)) / len(its),
               "judge_accuracy_on_known_truth": judge_acc,
               "disagreements": [{"source": it["source"], "runtime": it["label_runtime"], "ast": it["label_ast"],
                                  "adjudicated": it["adjudicated"], "via": it["adjudication_source"]}
                                 for it in its if norm(it["label_runtime"]) != it["adjudicated"]
                                 or norm(it["label_ast"]) != it["adjudicated"]]}
        rep["pass"] = bool(k >= 0.8 and ref_ok and rep["runtime_vs_adjudicated"] >= 0.9)
        rep["flag"] = None if rep["pass"] else "labeller_limited"
        report[t] = rep
        logger.info(f"gate {t}: kappa={k:.3f} ref_ok={ref_ok} rt_vs_adj={rep['runtime_vs_adjudicated']:.3f} "
                    f"pipeline_vs_adj={rep['pipeline_vs_adjudicated']:.3f} pass={rep['pass']}")
    (RESULTS_DIR / "labeller_gate.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
