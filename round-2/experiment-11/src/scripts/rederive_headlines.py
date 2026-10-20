#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from raw per-sample files, through code paths that do not reuse
the bench's aggregation functions (no bench.common imports), plus placebo versions of each test-like claim.

A  pilot collapse: (i) modal share from data/labels_combined.jsonl; (ii) regex signatures of each task's modal
   mechanism applied to the raw generations in data/samples_pilot_raw.jsonl (a labeller-free path).
B  gate kappa(runtime, AST) per task from bench/<task>/gold_set.jsonl via a numpy confusion matrix; placebo: the AST
   column permuted 1,000 times (the 0.8 gate must fail).
C  FRLP L_corr per cell from data/program_scores.jsonl + attempt counts from data/samples_forced_raw.jsonl; S per task;
   pilot log score under pi vs uniform; placebos: uniformly random pilot labels, and L_corr permuted across modes.
D  judge share, runtime-AST agreement, OpenRouter spend, Llama modal shares, association nomination, Wilson CI
   (scipy), Kendall tau (scipy).
Writes results/rederive_headlines.json.
"""

import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, kendalltau

ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = {"T03": "T03_kth_smallest", "T04": "T04_substring_search", "T05": "T05_two_sum", "T06": "T06_find_duplicate",
            "T08": "T08_fibonacci", "T10": "T10_connected_components", "T11": "T11_longest_increasing_subsequence",
            "T13": "T13_merge_intervals", "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals",
            "R2": "R2_cycle_detection", "R3": "R3_topological_order", "R6": "R6_first_last_position"}
# labeller-free signatures of each task's modal mechanism (regexes over the raw generation)
SIG = {
    "T03": lambda c: bool(re.search(r"sorted\(|\.sort\(", c)) and not re.search(r"heapq|pivot|partition", c),
    "T04": lambda c: bool(re.search(r"haystack\[[^\]]*:[^\]]*\]\s*==|haystack\[\s*\w+\s*\+\s*\w+\s*\]\s*[!=]=", c))
    and not re.search(r"lps|\.find\(|\.index\(", c),
    "T05": lambda c: bool(re.search(r"=\s*\{\s*\}|dict\(\)", c)) and bool(re.search(r"\bin\s+\w+", c)),
    "T06": lambda c: bool(re.search(r"set\(\)", c)) and bool(re.search(r"\bin\s+\w+", c)),
    "T08": lambda c: bool(re.search(r"for\s+\w+\s+in\s+range", c)) and not re.search(r"def\s+(?!solve)\w+", c),
    "T10": lambda c: bool(re.search(r"parent", c)) and bool(re.search(r"def\s+find", c)),
    "T11": lambda c: bool(re.search(r"for\s+\w+\s+in\s+range\(\s*\w+\s*\)", c)) and "bisect" not in c,
    "T13": lambda c: bool(re.search(r"sorted\(|\.sort\(", c)) and "parent" not in c,
    "T14": lambda c: bool(re.search(r"Counter|\.get\(\s*\w+\s*,\s*0\s*\)|defaultdict\(int\)", c))
    and bool(re.search(r"sorted\(.*key\s*=|\.sort\(.*key\s*=|most_common\(\s*\)", c)),
    "R1": lambda c: bool(re.search(r"key\s*=\s*lambda\s+\w+\s*:\s*\w+\[1\]", c)),
    "R2": lambda c: bool(re.search(r"def\s+(?!solve\b)(\w+)\s*\([^)]*\)\s*:[\s\S]*\b\1\s*\(", c))
    or bool(re.search(r"\.pop\(\)", c)),  # a recursive helper or an explicit stack (depth-first)
    "R3": lambda c: bool(re.search(r"in_?degree", c)) and bool(re.search(r"deque|popleft|pop\(0\)|\.pop\(\)", c)),
    "R6": lambda c: bool(re.search(r"mid\s*=", c)) and "bisect" not in c,
}
FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)?[ \t]*\n(.*?)(?:```|$)", re.S)


def jl(p):
    return [json.loads(l) for l in (ROOT / p).open()]


def kappa_np(a, b):
    labs = sorted(set(a) | set(b))
    idx = {l: i for i, l in enumerate(labs)}
    m = np.zeros((len(labs), len(labs)))
    for x, y in zip(a, b):
        m[idx[x], idx[y]] += 1
    n = m.sum()
    po = np.trace(m) / n
    pe = float((m.sum(0) * m.sum(1)).sum()) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def main():
    out = {}
    mo = json.loads((ROOT / "method_out.json").read_text())
    cand = {e["metadata_task"]: e for e in mo["datasets"][0]["examples"]}
    # A
    labs = jl("data/labels_combined.jsonl")
    raw = jl("data/samples_pilot_raw.jsonl")
    a = {}
    for t in TASK_DIR:
        pl = [r["label"] for r in labs if r["task"] == t and r["condition"] == "baseline" and r["label"] != "invalid"]
        top, k = Counter(pl).most_common(1)[0]
        codes = [(FENCE.search(r["text"]) or [None, ""])[1] for r in raw if r["task"] == t]
        sig = sum(SIG[t](c) for c in codes) / len(codes)
        a[t] = {"modal": top, "share": k / len(pl), "reported_share": cand[t]["metadata_modal_share"],
                "match": abs(k / len(pl) - cand[t]["metadata_modal_share"]) < 1e-12, "regex_signature_share": sig}
    out["A_pilot_collapse"] = a
    # B
    b = {}
    rng = np.random.default_rng(0)
    for t, d in TASK_DIR.items():
        g = jl(f"bench/{d}/gold_set.jsonl")
        rt, ast = [x["runtime"] for x in g], [x["ast"] for x in g]
        k = kappa_np(rt, ast)
        perm = [kappa_np(rt, list(rng.permutation(ast))) for _ in range(1000)]
        rep = json.loads((ROOT / "bench" / d / "gate.json").read_text())["gold"]["kappa_runtime_ast"]
        adj = [x for x in g if x.get("adjudicated")]
        b[t] = {"kappa": k, "reported": rep, "match": abs(k - rep) < 1e-9,
                "runtime_vs_adjudicated": sum(x["runtime"] == x["adjudicated"] for x in adj) / len(adj),
                "placebo_mean_kappa": float(np.mean(perm)), "placebo_frac_ge_0.8": float(np.mean(np.array(perm) >= 0.8))}
    out["B_gate_kappa"] = b
    # C
    sc = defaultdict(dict)
    for r in jl("data/program_scores.jsonl"):
        sc[r["program_id"]][r["prompt_id"]] = r["logp_sum"]
    forced_raw = jl("data/samples_forced_raw.jsonl")
    lab_by = {r["sample_id"]: r["label"] for r in labs}
    cells_rep = {(c["task"], c["algorithm"]): c for c in jl("data/frlp_cells.jsonl")
                 if c["half"] == "all" and c["variant"] == "main"}
    c_out, pilot_scores = {}, {}
    for t, d in TASK_DIR.items():
        sets = json.loads((ROOT / "bench" / d / "frlp_sets.json").read_text())
        lc = {}
        for j, st in sets.items():
            att = [r for r in forced_raw if r["task"] == t and r["mode"] == j]
            nk = Counter(r["paraphrase_id"] for r in att)
            N = sum(nk.values())
            ids = [p["program_id"] for p in st["programs"]]
            w = []
            for pid in ids:
                s = sc[pid]
                comps = np.array([math.log(nk[k] / N) + s[f"F{k}"] for k in nk])
                w.append(s["baseline"] - np.logaddexp.reduce(comps))
            w = np.array(w)
            L = np.logaddexp.reduce(w) - math.log(len(w)) if len(w) else float("nan")
            adh = sum(lab_by[r["sample_id"]] == j for r in att) / len(att)
            Lc = L + math.log(adh)
            ess = math.exp(2 * np.logaddexp.reduce(w) - np.logaddexp.reduce(2 * w)) if len(w) else 0.0
            rep = cells_rep[(t, j)]["L_corr"]
            lc[j] = {"L_corr": Lc, "reported": rep, "match": rep is not None and abs(Lc - rep) < 1e-6, "ess": ess,
                     "M": len(w), "usable": len(w) >= 15}
        use = {j: v["L_corr"] for j, v in lc.items() if v["usable"]}
        S = sum(math.exp(v) for v in use.values())
        K = len(sets)
        tot = sum(math.exp(v) for v in use.values())
        pi = {j: 0.93 * (math.exp(use[j]) / tot if j in use else 0.0) + 0.05 / K for j in sets}
        pi["other"] = 0.02
        z = sum(pi.values())
        pi = {k: v / z for k, v in pi.items()}
        pil = [r["label"] for r in labs if r["task"] == t and r["condition"] == "baseline" and r["label"] != "invalid"]
        ls = float(np.mean([math.log(pi.get(l, pi["other"])) for l in pil]))
        lu = math.log(1 / (K + 1))
        rnd = random.Random(1)
        fake = [rnd.choice(list(sets)) for _ in pil]
        ls_placebo = float(np.mean([math.log(pi[l]) for l in fake]))
        # placebo 2: L_corr permuted across modes
        modes = list(use)
        perm_vals = list(use.values())
        rnd.shuffle(perm_vals)
        tot2 = sum(math.exp(v) for v in perm_vals)
        pi2 = {j: 0.93 * math.exp(v) / tot2 + 0.05 / K for j, v in zip(modes, perm_vals)}
        for j in sets:
            pi2.setdefault(j, 0.05 / K)
        pi2["other"] = 0.02
        z2 = sum(pi2.values())
        ls_perm = float(np.mean([math.log(pi2.get(l, pi2["other"]) / z2) for l in pil]))
        c_out[t] = {"cells": lc, "S": S, "S_reported": cand[t]["metadata_frlp_validity"]["S"],
                    "log_score_pi": ls, "log_score_uniform": lu, "beats_uniform": ls > lu,
                    "placebo_random_labels_beats_uniform": ls_placebo > lu,
                    "placebo_permuted_Lcorr_beats_uniform": ls_perm > lu,
                    "argmax_pi_is_pilot_mode": max(sets, key=lambda j: pi[j]) == a[t]["modal"]}
    out["C_frlp"] = c_out
    # D
    valid = [r for r in labs if r.get("valid")]
    spend = jl("logs/openrouter_spend.jsonl")
    llama = jl("data/labels_llama_combined.jsonl")
    assoc = jl("data/association.jsonl")
    d = {"judge_share": sum(r["labeller_source"] == "judge" for r in labs) / len(labs),
         "runtime_ast_agreement": sum(r["ast_label"] == r["runtime_label"] for r in valid) / len(valid),
         "n_attempts": len(labs), "openrouter_usd": sum(x.get("cost") or 0 for x in spend), "n_calls": len(spend),
         "llama_modal_share": {t: (lambda c: c.most_common(1)[0][1] / sum(c.values()))(
             Counter(r["label"] for r in llama if r["task"] == t and r["label"] != "invalid")) for t in TASK_DIR},
         "wilson_50_50": list(binomtest(50, 50).proportion_ci(confidence_level=0.95, method="wilson")),
         "wilson_49_50": list(binomtest(49, 50).proportion_ci(confidence_level=0.95, method="wilson"))}
    assoc_nom = {}
    for t in TASK_DIR:
        x = a[t]["modal"]
        cnt = Counter(r["mapped"] for r in assoc if r["task"] == t and r["X"] == x and r["category"] == "survivor")
        top = max(cnt.values())
        assoc_nom[t] = {"rederived": sorted(k for k, v in cnt.items() if v == top),
                        "reported": cand[t]["predict_association"].split("|")}
        assoc_nom[t]["match"] = assoc_nom[t]["rederived"] == sorted(assoc_nom[t]["reported"])
    d["association_nomination"] = assoc_nom
    d["prox_differs_from_assoc_reported"] = sum(cand[t]["predict_proximity"] != cand[t]["predict_association"]
                                                for t in TASK_DIR)
    oa, ob = mo["metadata"]["orders"]["stageA"], mo["metadata"]["orders"]["stageB"]
    d["kendall_tau_A_B"] = float(kendalltau([oa.index(t) for t in TASK_DIR], [ob.index(t) for t in TASK_DIR]).statistic)
    out["D_misc"] = d
    summ = {"A_modal_share_matches": sum(v["match"] for v in a.values()),
            "A_min_regex_signature_share": min(v["regex_signature_share"] for v in a.values()),
            "B_kappa_matches": sum(v["match"] for v in b.values()),
            "B_placebo_max_frac_ge_0.8": max(v["placebo_frac_ge_0.8"] for v in b.values()),
            "C_cells_match": sum(v["match"] for t in c_out.values() for v in t["cells"].values()),
            "C_n_cells": sum(len(t["cells"]) for t in c_out.values()),
            "C_beats_uniform": sum(v["beats_uniform"] for v in c_out.values()),
            "C_placebo_random_labels_beats_uniform": sum(v["placebo_random_labels_beats_uniform"] for v in c_out.values()),
            "C_placebo_permuted_beats_uniform": sum(v["placebo_permuted_Lcorr_beats_uniform"] for v in c_out.values()),
            "C_S_in_range": sum(0.3 <= v["S"] <= 3 for v in c_out.values()),
            "D_association_matches": sum(v["match"] for v in assoc_nom.values())}
    out["summary"] = summ
    (ROOT / "results" / "rederive_headlines.json").write_text(
        json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps(summ, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps({k: v for k, v in d.items() if k != "association_nomination"}, indent=1,
                     default=lambda o: o.item() if hasattr(o, "item") else str(o))[:1500])


if __name__ == "__main__":
    main()
