#!/usr/bin/env python3
"""S1 known-heuristic corpus (data/corpus/corpus.json) and the tuned ab baseline.

Priority-form entries are evaluated through the SAME sandbox code path as search offspring (EvalPool): P1 decision
vector (60 s), selection F (60 s per set), held-out H-FSW5k and H-OR3 (120 s per set); key baselines on all eight
held-out sets. Stateful baselines (Next Fit, Harmonic-k with k tuned on F) are compared by held-out score only.
The ab grid (a 0..20, b 0..60, base FF/BF/WF = 3,843 points) gets P1 decision vectors for every point and F for the
first 2,000 points of default_rng(20261025).permutation(3843); the tuned member is argmin F over the first C* points.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import textwrap
import time
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bp  # noqa: E402
import probes  # noqa: E402
import sandbox  # noqa: E402

ROOT = bp.ROOT
CORPUS_DIR = ROOT / "data" / "corpus"
BF_OR_EXC, BF_W_EXC = 0.05997931747673214, 0.042309606769537086
HELDOUT_ALL = ["H-FSW5k", "H-OR3", "H-OR1", "H-OR2", "H-OR4", "H-W5k", "H-W10k", "H-SHIFT"]
HELDOUT_PRIMARY = ["H-FSW5k", "H-OR3"]
AB_POINTS = [(a, b, base) for a in range(21) for b in range(61) for base in ("FF", "BF", "WF")]
AB_ORDER_SEED = 20261025
C_STAR_LADDER = [2000, 1500, 1000]

SRC_SS = ("def priority(item, bins):\n"
          "    # Sum-of-Squares (Csirik et al. 2006), adapted: N(g) counts the passed OPEN bins with gap g, 0 < g < cap\n"
          "    cap = int(bins.max())\n"
          "    r = bins.astype(int)\n"
          "    counts = np.bincount(r[r < cap], minlength=cap + 1)\n"
          "    delta = np.zeros(len(bins), dtype=float)\n"
          "    is_open = r < cap\n"
          "    delta[is_open] += 1 - 2 * counts[r[is_open]]\n"
          "    new_gap = r - int(item)\n"
          "    pos = new_gap > 0\n"
          "    delta[pos] += 2 * counts[new_gap[pos]] + 1\n"
          "    return -delta\n")
SRC_C12_VEC = ("def priority(item, bins):\n    g = bins - item\n"
               "    return np.select([g <= 2, g <= 3, g <= 5, g <= 7, g <= 9, g <= 12, g <= 15, g <= 18, g <= 20, g <= 21],\n"
               "                     [4, 3, 2, 1, 0.9, 0.95, 0.97, 0.98, 0.98, 0.98], 0.99)\n")


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(b: bytes | str) -> str:
    return hashlib.sha256(b.encode() if isinstance(b, str) else b).hexdigest()


def strip_imports(code: str) -> str:
    keep = []
    for ln in code.splitlines():
        m = re.match(r"\s*(import|from)\s+(\w+)", ln)
        if m and m.group(2) not in ("numpy", "math"):
            continue
        keep.append(ln)
    return "\n".join(keep) + "\n"


def rename_fn(code: str, old: str) -> str:
    return re.sub(rf"def\s+{old}\s*\(", "def priority(", code)


def ext_entry(rel: str) -> dict:
    srcs = {e["local"]: e for e in json.loads((ROOT / "results" / "ext_sources.json").read_text())}
    e = srcs[rel]
    return {"url": e["url"], "commit": e.get("commit", ""), "access_utc": e["utc"], "file_sha256": e["sha256"]}


def priority_entries() -> tuple[list[dict], dict]:
    E: list[dict] = []
    stats: dict = {}

    def add(name: str, family: str, code: str, note: str, prov: dict | None = None, key: bool = False) -> None:
        E.append({"name": name, "family": family, "code": code, "code_sha256": sha(code), "adapter_note": note,
                  "priority_form": True, "key_baseline": key, "norm_key": sandbox.normalise_key(code),
                  **(prov or {"url": "", "commit": "", "access_utc": utc(), "file_sha256": ""})})

    add("FF", "textbook", bp.SRC_FF, "First Fit (Johnson 1973); bp.SRC_FF", key=True)
    add("BF", "textbook", bp.SRC_BF, "Best Fit; FunSearch's seed priority -(bins - item)", key=True)
    add("WF", "textbook", bp.SRC_WF, "Worst Fit among open bins, new bin if none fits; bp.SRC_WF", key=True)
    add("AWF", "textbook", probes.SRC_AWF, "Almost Worst Fit (Johnson 1974); second-largest gap among open bins", key=True)
    add("SS", "sum_of_squares", SRC_SS, "Sum-of-Squares (Csirik, Johnson, Kenyon, Orlin, Shor, Weber; STOC 2000/JACM "
        "2006) in priority form; adapted: sees only fitting bins", key=True)
    _, _, or_src, w_src = bp.funsearch_notebook()
    nb = ext_entry("ext/funsearch/bin_packing__bin_packing.ipynb")
    add("c12", "funsearch", or_src, "FunSearch OR heuristic, notebook cell 8 verbatim (bp.prio_c12_vec is its exact "
        "vectorised equivalent, gate-verified per instance)", nb, key=True)
    add("c12_vec", "funsearch", SRC_C12_VEC, "bp.prio_c12_vec (vectorised c12)", nb)
    add("c14", "funsearch", w_src, "FunSearch Weibull heuristic, notebook cell 9 verbatim", nb, key=True)
    # ---- EoH runs 1-3 (population_generation_20.json 'code' fields; score -> priority; dedup by normalise_key)
    seen: dict[str, str] = {}
    stats["eoh"] = {}
    for r in (1, 2, 3):
        rel = f"ext/eoh/docs__Results__Prob1_OnlineBinPacking__run{r}__population_generation_20.json"
        pop = json.loads((ROOT / rel).read_text())
        n_dup = 0
        for i, ind in enumerate(pop):
            code = rename_fn(textwrap.dedent(ind["code"]).strip("\n") + "\n", "score")
            repaired = False
            if sandbox.normalise_key(code) is None:  # run 3 member 3 is published with 1-space def AND body
                lines = [ln.strip() for ln in code.splitlines() if ln.strip()]
                d = next(j for j, ln in enumerate(lines) if ln.startswith("def priority"))
                code = "\n".join(lines[:d + 1] + ["    " + ln for ln in lines[d + 1:]]) + "\n"
                repaired = True
            k = sandbox.normalise_key(code)
            if k in seen:
                n_dup += 1
                continue
            seen[k] = f"EoH_r{r}_{i:02d}"
            add(f"EoH_r{r}_{i:02d}", f"eoh_run{r}", code, f"EoH run {r} member {i} (published objective "
                f"{ind['objective']}); dedented; def score -> def priority"
                + ("; whitespace repaired (published with 1-space def and body)" if repaired else ""), ext_entry(rel))
            E[-1]["eoh_objective"] = ind["objective"]
            E[-1]["eoh_algorithm"] = (ind.get("algorithm") or "")[:400]
        stats["eoh"][f"run{r}"] = {"n_programs": len(pop), "n_duplicates_dropped": n_dup}
    rel = "ext/reevo/prompts__bpp_online__seed_func.txt"
    add("ReEvo_seed", "reevo", rename_fn((ROOT / rel).read_text(), "priority_v1"),
        "ReEvo bpp_online seed function (c14 with renamed variable); priority_v1 -> priority", ext_entry(rel), key=True)
    rel = "ext/hsevo/problems__bpp_online__gpt.py"
    add("HSEvo_gpt", "hsevo", rename_fn(strip_imports((ROOT / rel).read_text()), "priority_v2"),
        "HSEvo problems/bpp_online/gpt.py; unused imports random/scipy/torch removed; priority_v2 -> priority",
        ext_entry(rel), key=True)
    rel = "ext/hsevo/baselines__reevo__prompts__bpp_online__seed_func.txt"
    add("HSEvo_seed", "hsevo", rename_fn((ROOT / rel).read_text(), "priority_v1"),
        "HSEvo baselines/reevo seed function; priority_v1 -> priority", ext_entry(rel))
    rel = "ext/mctsahd/problems__bpp_online__gpt.py"
    add("MCTSAHD_gpt", "mcts_ahd", (ROOT / rel).read_text(), "MCTS-AHD problems/bpp_online/gpt.py verbatim",
        ext_entry(rel), key=True)
    rel = "ext/llm4ad/llm4ad__task__optimization__online_bin_packing__template.py"
    tpl = re.search(r"template_program = '''(.*?)'''", (ROOT / rel).read_text(), re.S).group(1)
    add("LLM4AD_template", "llm4ad", tpl, "LLM4AD online_bin_packing template_program (item - bins)", ext_entry(rel))
    rel = "ext/llm4ad/example__tasks__online_bin_packing__online_bin_packing_tutorial.ipynb"
    add("LLM4AD_tutorial", "llm4ad", "import numpy as np\n\ndef priority(item, bins):\n    return bins - item\n",
        "LLM4AD tutorial template (cell 13) body `return bins - item`", ext_entry(rel))
    rel = "ext/llm4ad/llm4ad__task__optimization__online_bin_packing__evaluation.py"
    add("LLM4AD_eval_default", "llm4ad", "def priority(item, valid_bins):\n    priorities = -valid_bins\n"
        "    return priorities\n", "LLM4AD evaluation.py __main__ default priority (-valid_bins)", ext_entry(rel))
    ab_prov = ext_entry("ext/arxiv_2510.27353/2510.27353.html")
    add("abFF_5_24", "ab", bp.ab_source(5, 24, "FF"), "ab-FirstFit a=5 b=24 (2510.27353 Fig. 9a)", ab_prov, key=True)
    add("abWF_1_21", "ab", bp.ab_source(1, 21, "WF"), "ab-WorstFit a=1 b=21 (2510.27353 Fig. 9b)", ab_prov, key=True)
    add("abBF_1_21", "ab", bp.ab_source(1, 21, "BF"), "ab-BestFit a=1 b=21: unpublished parameters (the paper selects "
        "abBF parameters per instance and prints none)", ab_prov)
    # ---- textbook implementations found in the declared dependency art_j3Rm_lr2nzR6
    dep = json.loads((CORPUS_DIR / "dep_scan" / "dep_scan_hits.json").read_text())
    dep_rules = {"xlcost_python:5342": ("FF", bp.SRC_FF, "bin packing first fit (GeeksforGeeks)"),
                 "xlcost_python:9220": ("BF", bp.SRC_BF, "bin packing; labelled first fit, implements best fit "
                                        "(source is buggy: an existing bin is never decremented); intended rule = BF"),
                 "xlcost_python:9219": ("BF", bp.SRC_BF, "memory-management best fit; blocks = open bins"),
                 "xlcost_python:5338": ("WF", bp.SRC_WF, "memory-management worst fit; blocks = open bins"),
                 "xlcost_python:2196": ("FF", bp.SRC_FF, "memory-management first fit; blocks = open bins"),
                 "xlcost_python:3242": ("FF", bp.SRC_FF, "memory-management first fit; blocks = open bins")}
    n_dep = 0
    for h in dep["hits"]:
        if h["record_id"] in dep_rules:
            rule, code, note = dep_rules[h["record_id"]]
            add(f"dep_{h['record_id'].replace(':', '_')}", f"dependency_textbook_{rule}", code,
                f"art_j3Rm_lr2nzR6 {h['record_id']}: {note}; priority form = {rule}",
                {"url": "art_j3Rm_lr2nzR6/full_data_out.json", "commit": dep["file_sha256"], "access_utc": dep["utc"],
                 "file_sha256": h["sha256"]})
            n_dep += 1
    stats["dependency"] = {"n_regex_hits": len(dep["hits"]), "n_priority_expressible_added": n_dep,
                           "next_fit_record": "xlcost_python:1427 (memory-management next fit) -> stateful NF baseline"}
    late = CORPUS_DIR / "search_entries.json"
    if late.exists():
        for e in json.loads(late.read_text()):
            add(e["name"], e["family"], e["code"], e["adapter_note"], {k: e[k] for k in
                ("url", "commit", "access_utc", "file_sha256")})
            E[-1]["from_dated_search"] = True
    return E, stats


def next_fit(items: list[int], cap: int) -> int:
    used, rem = 0, -1
    for s in items:
        if rem < s:
            used += 1
            rem = cap
        rem -= s
    return used


def fitness() -> bp.Fitness:
    return bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), BF_OR_EXC, BF_W_EXC)


def heldout_excess(set_name: str, bins: list[int]) -> float:
    insts = bp.load_set(set_name)
    return 100.0 * bp.family_excess(bins, [x["l1"] for x in insts])


def run_tasks(pool: sandbox.EvalPool, tasks: list[dict]) -> list[dict]:
    futs = [pool.submit(t) for t in tasks]
    out = []
    for i, f in enumerate(futs):
        out.append(f.result())
        if (i + 1) % 250 == 0:
            logger.info(f"  {i + 1}/{len(futs)} done")
    return out


def decision_list(res: dict) -> list[int] | None:
    b = res.get("probes", {}).get("P1")
    return None if b is None else np.frombuffer(b, dtype=np.uint16).astype(int).tolist()


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "corpus.log", rotation="30 MB", level="DEBUG")
    t0 = time.time()
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    fit = fitness()
    entries, stats = priority_entries()
    logger.info(f"{len(entries)} priority-form corpus entries; stats {stats}")
    pool = sandbox.EvalPool(n_workers, ROOT, as_gib=2.0)
    # ---- 1. selection F + P1 decisions for every priority-form entry
    res = run_tasks(pool, [{"code": e["code"], "sets": ["SEL-OR", "SEL-W"], "limit": 60.0, "fail_fast": True,
                            "probes": ["P1"], "probe_limit": 60.0} for e in entries])
    for e, r in zip(entries, res):
        e["sel_error_type"], e["sel_msg"] = r["error_type"], r.get("msg", "")
        if r["error_type"] == "ok":
            b25 = r["bins"]["SEL-OR"] + r["bins"]["SEL-W"]
            e["sel_bins"] = b25
            e["F"] = fit.F(b25)
            e["decisions"] = decision_list(r)
        else:
            e["F"], e["decisions"] = None, None
            # decisions are still wanted for entries that fail selection (e.g. a timeout): probes only
    missing = [i for i, e in enumerate(entries) if e["decisions"] is None]
    if missing:
        res = run_tasks(pool, [{"code": entries[i]["code"], "sets": [], "limit": 60.0, "probes": ["P1"],
                                "probe_limit": 60.0} for i in missing])
        for i, r in zip(missing, res):
            entries[i]["decisions"] = decision_list(r) if r["error_type"] == "ok" else None
            entries[i]["probe_error_type"] = r["error_type"]
    logger.info(f"selection done ({time.time() - t0:.0f}s): " +
                ", ".join(f"{e['name']}={e['F'] if e['F'] is None else round(e['F'], 4)}" for e in entries[:12]))
    # ---- 2. ab grid: decisions for all 3,843 points, F for the first 2,000 of the committed permutation
    order = np.random.default_rng(AB_ORDER_SEED).permutation(len(AB_POINTS))
    first = set(order[:2000].tolist())
    ab_tasks = []
    for i, (a, b, base) in enumerate(AB_POINTS):
        ab_tasks.append({"code": bp.ab_source(a, b, base), "sets": ["SEL-OR", "SEL-W"] if i in first else [],
                         "limit": 60.0, "fail_fast": True, "probes": ["P1"], "probe_limit": 60.0})
    ab_res = run_tasks(pool, ab_tasks)
    grid = []
    for i, ((a, b, base), r) in enumerate(zip(AB_POINTS, ab_res)):
        row = {"i": i, "a": a, "b": b, "base": base, "error_type": r["error_type"], "F": None,
               "decisions": decision_list(r) if r["error_type"] == "ok" else None}
        if i in first and r["error_type"] == "ok":
            row["F"] = fit.F(r["bins"]["SEL-OR"] + r["bins"]["SEL-W"])
        grid.append(row)
    rank = {int(p): k for k, p in enumerate(order.tolist())}
    tuned = {}
    for cs in C_STAR_LADDER:
        pref = [grid[int(p)] for p in order[:cs] if grid[int(p)]["F"] is not None]
        best = min(pref, key=lambda g: (g["F"], rank[g["i"]]))
        tuned[str(cs)] = {"i": best["i"], "a": best["a"], "b": best["b"], "base": best["base"], "F": best["F"]}
    logger.info(f"ab grid done ({time.time() - t0:.0f}s); tuned prefix argmins {tuned}")
    have = {e["norm_key"] for e in entries}
    for cs, t in tuned.items():
        code = bp.ab_source(t["a"], t["b"], t["base"])
        nk = sandbox.normalise_key(code)
        names = [e for e in entries if e["norm_key"] == nk]
        if names:
            names[0].setdefault("tuned_for_c_star", []).append(int(cs))
            continue
        g = grid[t["i"]]
        entries.append({"name": f"abTUNED_{t['base']}_{t['a']}_{t['b']}", "family": "ab_tuned", "code": code,
                        "code_sha256": sha(code), "priority_form": True, "key_baseline": True, "norm_key": nk,
                        "adapter_note": f"tuned ab member: argmin F over the first C* points of the committed "
                                        f"permutation (rng {AB_ORDER_SEED})", "url": "", "commit": "",
                        "access_utc": utc(), "file_sha256": "", "F": g["F"], "decisions": g["decisions"],
                        "sel_error_type": "ok", "tuned_for_c_star": [int(cs)]})
        have.add(nk)
    # ---- 3. held-out: primary for all entries, all eight for key baselines (120 s per set)
    ho_tasks = []
    for e in entries:
        sets = HELDOUT_ALL if e.get("key_baseline") else HELDOUT_PRIMARY
        ho_tasks.append({"code": e["code"], "sets": sets, "limit": 120.0, "fail_fast": False, "probes": []})
    ho_res = run_tasks(pool, ho_tasks)
    for e, r in zip(entries, ho_res):
        e["heldout_excess_pct"] = {s: heldout_excess(s, b) for s, b in r["bins"].items()}
        e["heldout_bins"] = r["bins"]
        e["heldout_error"] = None if r["error_type"] == "ok" else f"{r['error_type']}: {r.get('msg', '')}"
    pool.close()
    # ---- 4. stateful baselines: Next Fit; Harmonic-k with k in 3..10 tuned on F
    sel = bp.load_set("SEL-OR") + bp.load_set("SEL-W")
    stateful = []
    nf_b25 = [next_fit(x["items"], x["capacity"]) for x in sel]
    nf = {"name": "NF", "family": "textbook_stateful", "F": fit.F(nf_b25),
          "adapter_note": "Next Fit (stateful; not priority-expressible); also xlcost_python:1427"}
    hk = []
    for k in range(3, 11):
        b25 = [bp.harmonic_k(x["items"], x["capacity"], k) for x in sel]
        hk.append((fit.F(b25), k))
    kstar = min(hk)[1]
    hstar = {"name": f"Harmonic_{kstar}", "family": "textbook_stateful", "F": min(hk)[0], "k": kstar,
             "F_by_k": {str(k): f for f, k in hk}, "adapter_note": "Lee & Lee Harmonic-k, k in 3..10 tuned on F"}
    for row, fn in ((nf, lambda it, c: next_fit(it, c)), (hstar, lambda it, c: bp.harmonic_k(it, c, kstar))):
        row["heldout_excess_pct"] = {}
        for s in HELDOUT_ALL:
            insts = bp.load_set(s)
            row["heldout_excess_pct"][s] = heldout_excess(s, [fn(x["items"], x["capacity"]) for x in insts])
        stateful.append(row)
    # ---- 5. corpus agreement matrix + known-equivalence calibration
    pf = [e for e in entries if e.get("decisions") is not None]
    D = np.array([e["decisions"] for e in pf], dtype=np.int64)
    ok = D != probes.ERR
    agree = np.zeros((len(pf), len(pf)))
    for i in range(len(pf)):
        agree[i] = np.mean((D == D[i]) & ok & ok[i], axis=1)
    idx = {e["name"]: i for i, e in enumerate(pf)}

    def ag(a: str, b: str) -> float | None:
        return float(agree[idx[a], idx[b]]) if a in idx and b in idx else None

    calib = {"c14~abWF_1_21": ag("c14", "abWF_1_21"), "c12~abFF_5_24": ag("c12", "abFF_5_24"),
             "c12~c12_vec": ag("c12", "c12_vec"), "c14~ReEvo_seed": ag("c14", "ReEvo_seed"),
             "BF~LLM4AD_template": ag("BF", "LLM4AD_template")}
    pairs_one_principle = {k: v for k, v in calib.items() if k in ("c14~abWF_1_21", "c12~abFF_5_24")}
    selective = all(v is not None and v >= 0.9 for v in pairs_one_principle.values())
    calib_out = {"utc": utc(), "pairs": calib, "rule": "max corpus agreement < 0.9 is required for NB",
                 "rule_selective_on_one_principle_pairs": selective,
                 "statement": ("The 0.9 probe rule is selective on the pairs 2510.27353 calls one principle."
                               if selective else
                               "A pair that 2510.27353 calls one principle agrees below 0.9: the 0.9 probe rule is "
                               "NOT selective there, so the judges, the manual read and V3-strict carry V3."),
                 "names": [e["name"] for e in pf], "agreement_matrix": np.round(agree, 4).tolist()}
    (ROOT / "results" / "calibration.json").write_text(json.dumps(calib_out))
    # ---- 6. write corpus, ab grid, results
    for e in entries:
        e.pop("sel_bins", None)
    corpus = {"utc": utc(), "n_priority_form": len(entries), "entries": entries, "stateful": stateful,
              "stats": stats, "tuned_ab_prefix_argmin": tuned, "ab_order_seed": AB_ORDER_SEED}
    blob = json.dumps(corpus, separators=(",", ":"))
    (CORPUS_DIR / "corpus.json").write_text(blob)
    ab_blob = json.dumps({"points": grid, "order": order.tolist()}, separators=(",", ":"))
    (CORPUS_DIR / "ab_grid.json").write_text(ab_blob)
    summary = {"utc": utc(), "corpus_sha256": sha(blob), "ab_grid_sha256": sha(ab_blob), "n_entries": len(entries),
               "n_with_decisions": len(pf), "stats": stats, "tuned_ab_prefix_argmin": tuned,
               "calibration": {k: v for k, v in calib_out.items() if k not in ("agreement_matrix", "names")},
               "secs": time.time() - t0,
               "table": [{"name": e["name"], "family": e["family"], "F": e.get("F"),
                          "sel_error": e.get("sel_error_type"),
                          "heldout_excess_pct": {k: round(v, 4) for k, v in e.get("heldout_excess_pct", {}).items()},
                          "heldout_error": e.get("heldout_error")} for e in entries],
               "stateful": stateful}
    (ROOT / "results" / "corpus.json").write_text(json.dumps(summary, indent=1))
    logger.info(f"corpus written: {len(entries)} entries, sha {summary['corpus_sha256'][:12]}, "
                f"{time.time() - t0:.0f}s; calibration {calib}")


if __name__ == "__main__":
    main()
