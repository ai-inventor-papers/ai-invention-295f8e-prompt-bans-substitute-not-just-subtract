#!/usr/bin/env python3
"""Recompute the iteration-5 headline numbers the review relies on, from the artifacts' own files.

Stdlib only. Reads the run's artifact folders in place (read-only) and writes checks/recompute_iter5.json.
Usage: python3 -I checks/recompute_iter5.py [RUN_LOOP_DIR]
RUN_LOOP_DIR defaults to the 3_invention_loop folder three levels above this workspace.
"""
import json
import math
import random
import sys
from itertools import product
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
LOOP = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[3]
I5 = LOOP / "round-5" / "."
I4 = LOOP / "round-4" / "."


def load(p):
    return json.loads(Path(p).read_text())


def rank(x):
    s = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[s[j + 1]] == x[s[i]]:
            j += 1
        for k in range(i, j + 1):
            r[s[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    ma, mb = mean(ra), mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den


def poisson_binomial_tail(ps, k):
    tot = 0.0
    for bits in product([0, 1], repeat=len(ps)):
        if sum(bits) >= k:
            pr = 1.0
            for b, p in zip(bits, ps):
                pr *= p if b else (1 - p)
            tot += pr
    return tot


def fisher_greater(a, b, c, d):
    n1, n2, k = a + b, c + d, a + c
    N = n1 + n2
    return sum(math.comb(n1, x) * math.comb(n2, k - x) / math.comb(N, k) for x in range(a, min(n1, k) + 1))


out = {}

# 1. Movability half (A1), panels A and B and pooled.
a = load(I5 / "experiment-25/src/results/a1.json")
ae = load(I5 / "experiment-25/src/results/a1_with_extension.json")
b = load(I5 / "experiment-26/src/results/a1_panel.json")
beta, E = a["beta"] + b["beta"], a["E"] + b["E"]
rho = spearman(beta, E)
random.seed(0)
hits = sum(spearman(beta, random.sample(E, len(E))) >= rho - 1e-12 for _ in range(50000))
out["A1"] = {
    "panelA_rho": spearman(a["beta"], a["E"]),
    "panelB_rho": spearman(b["beta"], b["E"]),
    "pooled13_rho": rho,
    "pooled13_perm_p_one_sided": hits / 50000,
    "pooled15_rho": spearman(ae["beta"] + b["beta"], ae["E"] + b["E"]),
}

# 2. Landing half (A2), pooled Qwen new units, and the instruct-twin confound.
chance = {"A1": 1 / 6, "A3": 1 / 3, "A7": 1 / 3, "B2": 1 / 3, "B3": 1 / 3, "B4": 1 / 5, "B7": 1 / 3}
hit = {"A1": 1, "A3": 1, "A7": 1, "B2": 1, "B3": 1, "B4": 0, "B7": 1}
out["A2_qwen_pooled"] = {"hits": sum(hit.values()), "n": 7,
                          "p": poisson_binomial_tail(list(chance.values()), sum(hit.values()))}
units_b = {u["unit"]: u for u in load(I5 / "experiment-26/src/results/unit_outcomes.json")["units"]}
twin_alt = {u: units_b[u]["twin_cell"]["labels_correct"] for u in ("B2", "B3", "B4", "B7")}
a3 = load(I5 / "experiment-25/src/results/unit_A3_summary.json")
out["A2_twin_minority"] = {
    "A3_twin_p0_offdefault": a3["escape_cells"][0]["p0"],
    "panelB_twin_correct": twin_alt,
}
g = load(I5 / "experiment-28/src/results/predictors.json")["units"]
out["gemma_twin_and_base_support"] = {
    t: {"twin_attempts": g[t]["default"]["attempt_counts"], "base_chat_attempts": g[t]["pt_chat"]["attempt_counts"],
        "base_plain_attempts": g[t]["pt_plain"]["attempt_counts"], "r_u": g[t]["r_u"]}
    for t in ("T1", "T04", "R6", "T05", "T11", "T03", "T10")
}
q_unconf = [1 / 6, 1 / 3, 1 / 5, 1 / 3]          # A1, A7, B4, B7 (twin wrote no alternative)
g_unconf = [1 / 3, 1 / 2, 1 / 5, 1 / 3]          # T05, T11, T03, T10 (twin wrote no alternative)
out["A2_unconfounded"] = {
    "qwen_3_of_4_p": poisson_binomial_tail(q_unconf, 3),
    "gemma_2_of_4_p": poisson_binomial_tail(g_unconf, 2),
    "both_5_of_8_p": poisson_binomial_tail(q_unconf + g_unconf, 5),
}
ga2 = load(I5 / "experiment-28/src/results/e_a2.json")
out["gemma_A2"] = {"hits": ga2["hits"], "n": ga2["n_events"], "p": ga2["poisson_binomial_p"],
                   "p_recomputed": poisson_binomial_tail(ga2["chance"], ga2["hits"]),
                   "base_minus_assoc": ga2["mean_base_minus_assoc"],
                   "base_minus_assoc_defined_only": ga2["mean_base_minus_assoc_defined_only"],
                   "wilcoxon_p": ga2["wilcoxon_p_base_vs_assoc"]}
ga1 = load(I5 / "experiment-28/src/results/e_a1.json")
out["gemma_A1"] = {"rho": ga1["rho"], "p": ga1["p_one_sided_perm"],
                   "rho_recomputed": spearman([ga1["beta"][u] for u in ga1["units"]], [ga1["E"][u] for u in ga1["units"]])}

# 3. Existing tasks in the iteration's own bf16 engine: landing check (panel A extra arm).
ex = load(I5 / "experiment-25/src/results/extra_arm_a.json")
out["existing_bf16_landing"] = {t: ex[t]["landing"] for t in ("T03", "T10")}

# 4. Plan noise: 8-bit (iteration 4) against bf16 (iteration 5) at near-matched dose.
c = load(I5 / "experiment-27/src/results/cells.json")
ur = load(I5 / "experiment-27/src/results/unit_ratio.json")
sw = load(I4 / "experiment-19/src/results/alpha_sweep.json")


def fp8(task, alpha):
    row = [s for s in sw[task]["sweep"] if s["alpha"] == alpha][0]
    return row["off_default_share"], row["correct_comp"]


out["plan_noise_engine"] = {}
for t in ("T10", "T2", "T03", "T05", "T1"):
    out["plan_noise_engine"][t] = {
        "bf16_banfree_over_ban_unit_ratio": ur[t]["banfree_over_ban_mean"],
        "bf16_PN_a1": (c[f"{t}|PN_a1"]["off_default_share"], c[f"{t}|PN_a1"]["correct_composition"]),
        "bf16_PN_a2": (c[f"{t}|PN_a2"]["off_default_share"], c[f"{t}|PN_a2"]["correct_composition"]),
        "fp8_PN_a1": fp8(t, 1.0), "fp8_PN_a2": fp8(t, 2.0),
    }
out["plan_noise_engine"]["fisher_T10_a2_fp8_30of50_vs_bf16_1of50"] = fisher_greater(30, 20, 1, 49)
out["plan_noise_engine"]["fisher_T2_a2_fp8_27of50_vs_bf16_2of50"] = fisher_greater(27, 23, 2, 48)

# 5. Plan sampler comparison and the literal cell.
cc = load(I5 / "experiment-27/src/results/claim_c.json")
out["claim_C"] = {"verdict": cc["verdict"], "wins": cc["primary"]["wins"], "D_bar": cc["D_bar"], "D_bar_ci95": cc["D_bar_ci95"]}
lit = load(I5 / "experiment-27/src/results/literal_cell.json")
out["literal_cell"] = {
    "C_T": lit["C_T"]["n_change_final_label"],
    "phrasing_clusters_theta08": {k: v["phrasing"]["theta_0.8"]["n_clusters"] for k, v in lit["per_T"].items()},
}

# 6. Transplant confirmation (top-k frequent and kth smallest).
conf = load(I5 / "experiment-24/src/results/confirmation.json")["per_task"]
out["transplant"] = {
    "T14_T_off": (conf["T14"]["arms"]["T1.0"]["k_off"], conf["T14"]["arms"]["T1.0"]["n_correct"]),
    "T14_vs_MR": conf["T14"]["arms"]["MR1.0"]["mcnemar_T_vs_this"],
    "T03_vs_MR": conf["T03"]["arms"]["MR1.0"]["mcnemar_T_vs_this"],
}

# 7. Llama qualifying cells left out of Table 126c (iteration-4 record audit knob table).
import csv  # noqa: E402
rows = list(csv.DictReader(open(I4 / "evaluation-3/src/tables/knob_table.csv")))
out["llama_qualifying"] = [
    {k: r[k] for k in ("row_id", "task", "arm", "H1r25", "pass_cost_pts", "correct_composition")}
    for r in rows if "llama" in r["model"].lower() and r["qualify"] == "True"
]

(HERE / "recompute_iter5.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str)[:6000])
