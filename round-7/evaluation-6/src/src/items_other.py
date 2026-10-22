"""Items 0c (Gemma within its controls), 0d (per-model synthesis), 0h (NLA test at one unit per sample),
0i (U6 and D12), 0j (Section 4.9 limited to the audited pools) and 0l (conditional tags)."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

import numpy as np

from common import MARK, inp, read_json, read_jsonl, src_ref
from corrections import V
from stats import (binom_two_sided, cluster_bootstrap_mean_diff, durkalski_mcnemar, mcnemar_exact, sign_test,
                   sign_test_floor)

GE = "art_zNyBP6zieI5u"
NL = "art_dbUtqBjT0tPf"
TAG = "(ban-free unit and iteration-5 seeds; pending the 2x2 of Step K)"


# ======================================================================== 0c
def gemma_values() -> dict[str, Any]:
    das = read_json(inp(GE, "results/das.json"))
    ro = read_json(inp(GE, "results/readout.json"))
    rh = read_json(inp(GE, "results/rederive_headlines.json"))["H1_readout"]
    cl = read_json(inp(GE, "results/clamps.json"))["cells"]
    v = []
    per = {}
    for k, d in das["per_k"].items():
        per[k] = {"das": d["das"]["heldout_mean_dy"], "random": d["random_subspace"]["heldout_mean_dy"],
                  "shuffled": d["shuffled_source"]["heldout_mean_dy"], "frac_pos": d["das"]["heldout_frac_pos"]}
        ref = src_ref(GE, "results/das.json", f"per_k.{k}")
        v += [V(f"DAS|k{k}|heldout_dy", per[k]["das"], {"1": 8.81, "2": 9.51, "4": 9.76}[k], tol="effect", source=ref),
              V(f"DAS|k{k}|random_dy", per[k]["random"], {"1": -0.08, "2": 0.03, "4": 0.05}[k], tol="effect", source=ref),
              V(f"DAS|k{k}|shuffled_dy", per[k]["shuffled"], {"1": 10.11, "2": 9.69, "4": 11.42}[k], tol="effect",
                source=ref)]
    d4 = cl["FORK|DAS|k4"]
    das_bfs, das_pass_k = d4["attempted"].get("bfs", 0), int(round(d4["pass_rate"] * d4["n"]))
    v += [V("DAS|k4|generation_bfs", das_bfs, 50, source=src_ref(GE, "results/clamps.json", "cells.FORK|DAS|k4")),
          V("DAS|k4|generation_passing", das_pass_k, 0, source=src_ref(GE, "results/clamps.json", "cells.FORK|DAS|k4"))]
    lasso = ro["models"]["SAE|FORK|29"]["R2_lono"]
    v += [V("readout|lasso_SAE_fork29", lasso, 0.66, tol="prop", source=src_ref(GE, "results/readout.json")),
          V("readout|ridge_SAE_std_fork29", rh["R2_lono_ridge_SAE_FORK29"], 0.1499, tol="prop",
            source=src_ref(GE, "results/rederive_headlines.json", "H1_readout")),
          V("readout|ridge_template_nounnorms", rh["R2_lono_ridge_template_nounnorms"], 0.0861, tol="prop",
            source=src_ref(GE, "results/rederive_headlines.json", "H1_readout")),
          V("readout|delta", rh["delta"], 0.0638, tol="prop", source=src_ref(GE, "results/rederive_headlines.json")),
          V("readout|placebo_fails", rh["placebo_fails"], True, tol="text",
            source=src_ref(GE, "results/rederive_headlines.json"))]
    es = rh["estimator_sensitivity_unstandardized_ridge"]
    sae29 = [x for k, x in es.items() if k.startswith("SAE|codes_fork|L29")]
    raw29 = [es["RAW|codes_fork|L29|ridge_raw_a1000"], es["RAW|codes_fork|L29|ridge_raw_a100000"]]
    v += [V("readout|unstd_SAE_ridge_min", min(sae29), -0.76, tol="prop", source=src_ref(GE, "results/rederive_headlines.json")),
          V("readout|unstd_SAE_ridge_max", max(sae29), 0.06, tol="prop", source=src_ref(GE, "results/rederive_headlines.json")),
          V("readout|raw_ridge_min", min(raw29), 0.70, tol="prop", source=src_ref(GE, "results/rederive_headlines.json")),
          V("readout|raw_ridge_max", max(raw29), 0.72, tol="prop", source=src_ref(GE, "results/rederive_headlines.json"))]
    toward_bfs = {k: c for k, c in cl.items() if k.startswith("FORK|") and "toDFS" not in k}
    clamp = {k: {"bfs": c["attempted"].get("bfs", 0), "n": c["n"], "pass": c["pass_rate"]} for k, c in toward_bfs.items()}
    twin = cl["twin_cstar"]["pass_rate"]
    k5 = clamp["FORK|FEATin|k5"]
    v += [V("clamp|twin_pass", twin, 0.84, tol="prop", source=src_ref(GE, "results/clamps.json", "cells.twin_cstar")),
          V("clamp|SAE_top5_bfs", k5["bfs"], 18, source=src_ref(GE, "results/clamps.json", "cells.FORK|FEATin|k5")),
          V("clamp|SAE_top5_pass", k5["pass"], 0.84, tol="prop", source=src_ref(GE, "results/clamps.json"))]
    for k, c in clamp.items():
        v.append(V(f"clamp|{k}|pass", c["pass"], None, tol="prop", source=src_ref(GE, "results/clamps.json", f"cells.{k}")))
    main4 = [clamp[k]["pass"] for k in ("FORK|FEATin|k20", "FORK|FEATin|k50", "FORK|DiM@k20", "FORK|DiM@k50")]
    others = [c["pass"] for k, c in clamp.items() if k not in ("FORK|FEATin|k5", "FORK|FEATin|k20", "FORK|FEATin|k50",
                                                               "FORK|DiM@k20", "FORK|DiM@k50", "FORK|DAS|k4",
                                                               "FORK|NODES5|ablate")]
    return {"das": per, "das_gen": {"bfs": das_bfs, "n": d4["n"], "passing": das_pass_k}, "lasso": lasso,
            "ridge_std": rh["R2_lono_ridge_SAE_FORK29"], "ridge_ctrl": rh["R2_lono_ridge_template_nounnorms"],
            "ridge_delta": rh["delta"], "unstd_sae": (min(sae29), max(sae29)), "raw_ridge": (min(raw29), max(raw29)),
            "clamps": clamp, "twin_pass": twin, "top5": k5, "main4_pass": (min(main4), max(main4)),
            "other_pass": (min(others), max(others)), "values": v}


def item_0c(ed, g: dict) -> None:
    d1, d4 = g["das"]["1"], g["das"]["4"]
    rnd = max(abs(g["das"][k]["random"]) for k in g["das"])
    das_txt = (f"a rank-1 DAS subspace fitted on forced-BFS sources moves the held-out fork log-odds by "
               f"{d1['das']:.1f} nats (random subspaces of the same rank {min(x['random'] for x in g['das'].values()):+.2f} "
               f"to {max(x['random'] for x in g['das'].values()):+.2f}); because every source was forced-BFS, the "
               f"shuffled-source control is uninformative by construction ({d1['shuffled']:.1f} nats); no "
               "random-initialisation or target-shuffled control was run; and the rank-4 interchange gives BFS in "
               f"{g['das_gen']['bfs']} of {g['das_gen']['n']} attempts with {g['das_gen']['passing']} of "
               f"{g['das_gen']['n']} programs passing, so this does not show that the choice is one-dimensional")
    ed.sub("**DAS finds the choice in one direction at the fork, and forcing it breaks the program.**", "0c",
           "**DAS finds the choice in one direction at the fork, and forcing it breaks the program.**",
           "**DAS moves the fork log-odds within the controls it had, and forcing it breaks the program.**")
    ed.sub("**DAS finds the choice in one direction at the fork, and forcing it breaks the program.**", "0c",
           "Together with the difference-in-means result, this says that the plan is close to one direction at one "
           "position, and that pushing it hard costs correctness, as subspace interventions can when they leave the "
           "model's natural range [122].",
           f"Stated within its controls, {das_txt}. With unrestricted alignment maps interchange accuracy reaches 100% "
           "even on randomly initialised language models (Sutter et al., Table 277 row 14), so the fit stays "
           "uninterpretable until those controls run; pushing hard costs correctness, as subspace interventions can when "
           "they leave the model's natural range [122].")
    ed.sub("**Table 263.** DAS at the fork (layer 22)", "0c", "Source: Gemma feature experiment `results/das.json`.",
           "Every source was a forced-BFS prompt, so the shuffled-source column is uninformative by construction; no "
           "random-initialisation or target-shuffled control was run, and the rank-4 interchange gave "
           f"{g['das_gen']['passing']} of {g['das_gen']['n']} passing programs (Table 262), so the table does not show "
           "that the choice is one-dimensional. Source: Gemma feature experiment `results/das.json`.")
    ridge = (f"the standardised ridge on the same layer-29 SAE codes reaches R-squared {g['ridge_std']:.2f} against "
             f"{g['ridge_ctrl']:.3f} for a template-plus-noun-norm control (delta {g['ridge_delta']:.3f}, below the "
             "preregistered 0.10 bar)")
    note = ("a linear readout of the fork log-odds from the residual at the fork position is close to a next-token "
            "readout, so the raw-residual 0.72 shows that the next-token distribution is linearly encoded there, not "
            "that a plan is")
    ed.sub("**Readable beyond the text, at the fork, but not specifically through the SAE.**", "0c",
           "The information is in the residual stream at the fork, and the SAE advantage depends on the estimator.",
           f"Beside the Lasso, {ridge}; the unstandardised SAE ridge ranges from {g['unstd_sae'][0]:.2f} to "
           f"{g['unstd_sae'][1]:.2f} across penalties while the raw ridge stays at {g['raw_ridge'][0]:.2f} to "
           f"{g['raw_ridge'][1]:.2f}, which is why the SAE advantage depends on the estimator. Moreover, {note}; no "
           "logit-lens control of matched capacity was run.")
    ed.sub("**Table 261.** Cross-prompt readout of the fork log-odds", "0c",
           "Source: Gemma feature experiment `results/readout.json`.",
           f"Post hoc, {ridge}. At the fork position this readout is close to a next-token readout (no logit-lens "
           "control was run). Source: Gemma feature experiment `results/readout.json`, `results/rederive_headlines.json`.")
    top5 = g["top5"]
    ed.sub("**Steering: the features move the fork, difference in means moves it more, and every fork edit breaks "
           "programs.**", "0c",
           "and every fork edit breaks programs.**", "and edits toward BFS cost correctness.**")
    ed.sub("**Steering: the features move the fork, difference in means moves it more, and every fork edit breaks "
           "programs.**", "0c",
           "Every edit at the fork lowered the pass rate, from 0.84 for the twin to 0.58 and 0.48 for the SAE clamps and "
           "0.32 and 0.16 for difference in means,",
           f"Edits toward BFS at the fork lowered the pass rate from {g['twin_pass']:.2f} for the twin to "
           f"{g['clamps']['FORK|FEATin|k20']['pass']:.2f} and {g['clamps']['FORK|FEATin|k50']['pass']:.2f} for the "
           f"top-20 and top-50 SAE clamps and {g['clamps']['FORK|DiM@k20']['pass']:.2f} and "
           f"{g['clamps']['FORK|DiM@k50']['pass']:.2f} for difference in means ({g['other_pass'][0]:.2f} to "
           f"{g['other_pass'][1]:.2f} for the other BFS-ward fork edits, {g['das_gen']['passing'] / g['das_gen']['n']:.2f} "
           f"for the DAS interchange), except the SAE top-5 clamp ({top5['bfs']} BFS of {top5['n']}, pass "
           f"{top5['pass']:.2f}),")
    ed.sub("3. *Gemma's BFS-or-DFS choice is made at one generated token,*", "0c",
           "and is readable from the residual stream at that position across prompts (Lasso on SAE codes R-squared 0.66 "
           "against 0.18 for text, preregistered; ridge on the raw state 0.72, post hoc).",
           "and its fork log-odds is linearly decodable from the residual stream at that position across prompts (Lasso "
           "on SAE codes R-squared 0.66 against 0.18 for text, preregistered; ridge on the raw state 0.72, post hoc); at "
           f"the fork position that is close to a next-token readout, so it shows that the next-token distribution is "
           f"linearly encoded there, not that a plan is, and {ridge}.")
    ed.sub("4. *Steering the fork works and costs correctness.*", "0c",
           "and every edit toward the minority algorithm breaks programs; edits toward the default are clean.",
           f"and edits toward the minority algorithm lowered the pass rate from {g['twin_pass']:.2f} to "
           f"{g['main4_pass'][0]:.2f}-{g['main4_pass'][1]:.2f}, except the SAE top-5 clamp ({top5['bfs']} BFS, pass "
           f"{top5['pass']:.2f}); edits toward the default are clean.")
    ed.sub("Three leads come with it.", "0c",
           "Gemma's one-token fork offers a clean site where DAS already captures the choice in one direction;",
           f"Gemma's one-token fork offers a clean site where a rank-1 DAS subspace moves the fork log-odds by "
           f"{d1['das']:.1f} nats, a fit that needs the Sutter controls (random initialisation, shuffled targets, "
           "forced-DFS sources) before it says anything about dimensionality;")
    g["das_txt"] = das_txt
    g["ridge_txt"] = ridge
    g["note_txt"] = note
    _ = d4


# ======================================================================== 0h
def nla_units() -> dict[str, Any]:
    c2 = read_json(inp(NL, "predictions/commit2_readout.json"))
    tasks = c2["tasks"]
    idx = {r["state_id"]: r for r in read_jsonl(inp(NL, "cache/states_index.jsonl"))}
    labels = {r["sample_id"]: r for r in read_jsonl(inp(NL, "data/labels.jsonl"))}
    expl, text = defaultdict(list), {}
    for r in read_jsonl(inp(NL, "data/judgements.jsonl")):
        if r["mode"] == "EXPL":
            expl[r["state_id"]].append(r)
        else:
            text[(r["mode"], r["text_id"])] = r["resolved"]

    def x_of(sid: str, tgt: str) -> int | None:
        rs = [r for r in expl.get(sid, []) if int(r["expl_id"].split("#")[-1]) <= 3]
        if not rs:
            return None
        h = sum(1 for r in rs if r["resolved"] == tgt)
        return int(h >= 2) if len(rs) >= 2 else int(h >= 1)

    units = []
    for sid, r in idx.items():
        if r["kind"] != "GEN" or not tasks.get(r["task"], {}).get("regate_pass", True):
            continue
        lab = labels.get(r["sample_id"])
        if lab is None:
            continue
        tid = f"{r['task']}|{r['condition']}|{r.get('mode') or '-'}|{r['template']}|{r['position']}|{r['slot']}"
        yv = text.get(("PREDICT", tid))
        units.append({"sid": sid, "task": r["task"], "sample": r["sample_id"], "g": int(r["position"][1:]),
                      "mixed": bool(r.get("mixed")), "x": x_of(sid, lab["label"]),
                      "y": None if yv is None else int(yv == lab["label"]), "name": text.get(("NAME", tid))})
    first = {}
    for u in sorted(units, key=lambda u: u["g"]):
        if u["name"] not in {"none_named", "other", "unresolved", None} and u["sample"] not in first:
            first[u["sample"]] = u["g"]
    sel = [u for u in units if u["mixed"] and u["g"] < first.get(u["sample"], 10 ** 6)
           and u["x"] is not None and u["y"] is not None]
    n_mixed_samples = len({u["sample"] for u in units if u["mixed"]})
    return {"units": sel, "n_mixed_samples": n_mixed_samples}


def item_0h(ed, seed: int = 20261022) -> dict[str, Any]:
    rec = read_json(inp(NL, "results/readout.json"))["N6_per_sample"]
    U = nla_units()
    units = U["units"]
    b = sum(1 for u in units if u["x"] == 1 and u["y"] == 0)
    c = sum(1 for u in units if u["x"] == 0 and u["y"] == 1)
    p = mcnemar_exact(b, c)
    boot = cluster_bootstrap_mean_diff(units, "task", 2000, seed)
    clusters = sorted({u["task"] for u in units})
    by_s = defaultdict(list)
    for u in units:
        by_s[u["sample"]].append(u)
    samples = sorted(by_s)
    first = [min(by_s[s], key=lambda u: u["g"]) for s in samples]
    b1 = sum(1 for u in first if u["x"] == 1 and u["y"] == 0)
    c1 = sum(1 for u in first if u["x"] == 0 and u["y"] == 1)
    p1 = mcnemar_exact(b1, c1)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(2000):
        pick = [by_s[s][int(rng.integers(len(by_s[s])))] for s in samples]
        bb = sum(1 for u in pick if u["x"] == 1 and u["y"] == 0)
        cc = sum(1 for u in pick if u["x"] == 0 and u["y"] == 1)
        draws.append((bb, cc, mcnemar_exact(bb, cc)))
    med = (statistics.median(d[0] for d in draws), statistics.median(d[1] for d in draws),
           statistics.median(d[2] for d in draws))
    share_sig = sum(d[2] < 0.05 for d in draws) / len(draws)
    diffs = [float(np.mean([u["x"] for u in by_s[s]]) - np.mean([u["y"] for u in by_s[s]])) for s in samples]
    sg = sign_test(diffs)
    dk = durkalski_mcnemar({s: (sum(1 for u in by_s[s] if u["x"] == 1 and u["y"] == 0),
                                sum(1 for u in by_s[s] if u["x"] == 0 and u["y"] == 1)) for s in samples})
    per_task = {}
    for t in clusters:
        tu = [u for u in units if u["task"] == t]
        per_task[t] = {"n_units": len(tu), "n_samples": len({u["sample"] for u in tu}),
                       "mean_x": float(np.mean([u["x"] for u in tu])), "mean_y": float(np.mean([u["y"] for u in tu]))}
    task_signs = sign_test([per_task[t]["mean_x"] - per_task[t]["mean_y"] for t in clusters])
    floor = sign_test_floor(len(clusters))
    ref = src_ref(NL, "results/readout.json", "N6_per_sample")
    vals = [V("N6|n_units", len(units), rec["n"], source=ref), V("N6|b", b, rec["b"], source=ref),
            V("N6|c", c, rec["c"], source=ref), V("N6|p", p, rec["p"], tol="p", source=ref),
            V("N6|cluster_boot_ci", boot, rec["cluster_bootstrap"]["ci95"], tol="ci", source=ref),
            V("N6|n_clusters", len(clusters), rec["cluster_bootstrap"]["n_clusters"], source=ref),
            V("N6|n_samples_contributing", len(samples), None, source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|n_mixed_samples", U["n_mixed_samples"], rec["n_samples"], source=ref),
            V("N6|one_unit_first|b", b1, None, source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|one_unit_first|c", c1, None, source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|one_unit_first|p", p1, None, tol="p", source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|random_unit|median_p", med[2], None, tol="p", source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|random_unit|share_p_lt_0.05", share_sig, None, tol="prop", source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|sign_test_per_sample|p", sg["p"], None, tol="p", source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|durkalski|p", dk["p"], None, tol="p", source=src_ref(NL, "data/judgements.jsonl")),
            V("N6|task_cluster_sign_floor", floor, 0.0625, tol="p", source="arithmetic: 2/2^5")]
    ex = lambda q: f"{q:.1e}" if q < 1e-3 else f"{q:.3f}"
    one = (f"with one unit per sample (the first in position order, {len(samples)} samples) the contrast is "
           f"{b1}:{c1} (exact p {ex(p1)})")
    ed.sub("**The NLA never names the planned algorithm before the code.**", "0h",
           "(0.25 against 0.07; exact McNemar 20:88, p 2e-11).",
           f"(0.25 against 0.07; exact McNemar 20:88, p 2e-11 when the {len(units)} units are treated as independent). "
           f"The units are nested in {len(samples)} samples and {len(clusters)} task clusters: the task-cluster "
           f"bootstrap interval of the difference is [{boot[0]:.2f}, {boot[1]:.2f}], {one}, a median over 2,000 draws "
           f"of one random unit per sample of {med[0]:.0f}:{med[1]:.0f} (p {ex(med[2])}; {share_sig:.2f} of draws below "
           f"0.05), a sign test on the per-sample differences {sg['n_pos']}:{sg['n_neg']} (p {ex(sg['p'])}) and a "
           f"Durkalski-adjusted McNemar with samples as clusters p {ex(dk['p'])}. The samples share {len(clusters)} task "
           f"clusters, and with {len(clusters)} clusters no cluster-level test can reach a two-sided p below "
           f"{floor:.4f}, so the evidence at the task level is inconclusive whatever the sample-level p.")
    row = [l for l in ed.lines if l.startswith("| per sample, mixed conditions (364 units, 120 samples)")]
    if len(row) == 1:
        ed.whole(row[0], "0h", "replace",
                 f"| per sample, mixed conditions ({len(units)} units nested in {len(samples)} samples and "
                 f"{len(clusters)} task clusters) | 0.066 correct | outside reader 0.253 | 20 : 88 per unit; {b1} : {c1} "
                 f"at one unit per sample | 2e-11 per unit (units treated as independent); {ex(p1)} at one unit per "
                 f"sample; task-cluster bootstrap of the difference [{boot[0]:.2f}, {boot[1]:.2f}] | outside reader "
                 f"better per sample; inconclusive at the task level ({len(clusters)} clusters: no cluster-level test "
                 f"below p {floor:.4f}) {MARK} |",
                 values=[], section="6.6", table="Table 270", rationale="N6 restated with its clustered interval")
    ed.sub("5. *The NLA does not verbalise the planned algorithm at pre-code positions", "0h",
           "an outside reader of the text predicts the realised algorithm better than the NLA.",
           f"an outside reader of the text predicts the realised algorithm better than the NLA per sample ({b1}:{c1} at "
           f"one unit per sample, p {ex(p1)}), and at the task level the evidence is inconclusive ({len(clusters)} task "
           f"clusters; bootstrap interval [{boot[0]:.2f}, {boot[1]:.2f}]).")
    return {"units": units, "n_units": len(units), "b": b, "c": c, "p": p, "cluster_boot_ci": boot, "clusters": clusters,
            "n_samples": len(samples), "n_mixed_samples": U["n_mixed_samples"],
            "one_unit_first": {"b": b1, "c": c1, "p": p1},
            "random_unit": {"median_b": med[0], "median_c": med[1], "median_p": med[2], "share_p_lt_05": share_sig,
                            "n_draws": 2000, "seed": seed},
            "sign_test_per_sample": sg, "durkalski": dk, "per_task": per_task, "task_level_sign": task_signs,
            "cluster_floor_p": floor, "one_txt": one, "values": vals,
            "rows": [{"sample": s, "task": by_s[s][0]["task"], "n_units": len(by_s[s]), "first_g": first[i]["g"],
                      "x_first": first[i]["x"], "y_first": first[i]["y"], "mean_x": float(np.mean([u["x"] for u in by_s[s]])),
                      "mean_y": float(np.mean([u["y"] for u in by_s[s]]))} for i, s in enumerate(samples)]}


# ======================================================================== 0i (U6, D12)
def item_0i_u6_d12(ed) -> dict[str, Any]:
    f = read_json(inp(GE, "results/fork.json"))["U6"]
    dev = read_json(inp(GE, "results/deviations.json"))["D12_not_run"]
    k = int(round(f["t0_bfs_share"] * f["t0_n"]))
    p = binom_two_sided(k, f["t0_n"], f["s3_bfs_share"])
    vals = [V("U6|t0_bfs_share", f["t0_bfs_share"], 0.38, tol="prop", source=src_ref(GE, "results/fork.json", "U6")),
            V("U6|t0_n", f["t0_n"], 192, source=src_ref(GE, "results/fork.json", "U6")),
            V("U6|s3_bfs_share", f["s3_bfs_share"], 0.305, tol="prop", source=src_ref(GE, "results/fork.json", "U6")),
            V("U6|s3_ci95", f["s3_ci95"], [0.245, 0.372], tol="ci", source=src_ref(GE, "results/fork.json", "U6")),
            V("U6|t0_within_ci", f["t0_within_ci"], False, tol="text", source=src_ref(GE, "results/fork.json", "U6")),
            V("U6|exact_binomial_p", p, None, tol="p", source="exact binomial of the U6 counts"),
            V("D12|text", dev, None, tol="text", source=src_ref(GE, "results/deviations.json", "D12_not_run"))]
    block = ("\n\n*Executed but not reported until iteration 7.* The fork's unit test U6 failed mildly: continuations "
             f"from the empty prefix give BFS {f['t0_bfs_share']:.2f} ({k} of {f['t0_n']}) against the natural "
             f"{f['s3_bfs_share']:.3f} [{f['s3_ci95'][0]:.3f}, {f['s3_ci95'][1]:.3f}] (outside the interval; exact "
             f"binomial p {p:.3f} against 0.305), so the resampled continuations are slightly richer in BFS than the "
             f"natural samples. The deviation log records what did not run (D12, verbatim): \"{dev}\" {MARK}")
    ed.insert("the change was made before the second commitment.", "0i", block, values=vals, section="6.5",
              table=None, rationale="U6 and D12 executed or logged but never reported")
    ed.insert("The only DAS result of the iteration is Gemma's, at the fork position (Section 6.5).", "0i",
              f" The Gemma experiment's deviation D12 adds what it did not run: \"{dev}\" {MARK}", values=[],
              section="6.8", table=None, rationale="D12 into 6.8")
    return {"U6": {**f, "k": k, "exact_binomial_p": p, "verdict": "mild failure"}, "D12": dev, "values": vals}


# ======================================================================== 0d
def item_0d(ed, a: dict, g: dict, h: dict) -> dict[str, Any]:
    C = lambda t, c: a["cells"][f"{t}|{c}"]
    sp, fb, fc = C("T2", "X_0-35"), C("T2", "FORCEDX_0-35"), C("T10", "FORCEDX_0-35")
    k0 = C("T03", "X_0-35")
    q3 = (f"exchanging the task-specification states alone reproduces the substitute of the ban on shortest path "
          f"(Bellman-Ford/SPFA in {sp['attempted_Y']} of 30 attempts, {sp['correct_Y']} of 30 correct programs) and a "
          f"forced instruction on shortest path ({fb['attempted_Y']} of 30 attempts, {fb['correct_Y']} of 30 correct) and "
          f"connected components (BFS in {fc['attempted_Y']} of 30 attempts, {fc['correct_Y']} of 30 correct)")
    ed.sub("**Where the choice is held, in three models.**", "0d",
           ed._line("**Where the choice is held, in three models.**").split(" The finding of iteration 3")[0],
           "**Where the choice is held, model by model.** The three internal experiments measured different quantities "
           "at different sites, so their results are stated per model and per quantity (Table 279) rather than as one "
           f"map. In Qwen3-8B what was measured is where an external ban or instruction is carried: {q3}, while on the "
           "direct-route tasks the condition span carries it; Qwen3-8B's natural choice was not measured, because it "
           "writes one algorithm per prompt. In gemma-3-4b-it, which writes two algorithms for one prompt, the natural "
           "choice is made at one generated token after a shared opening; task-specification edits and readouts barely "
           "reach it, and the read position was never read or edited (Gemma's SPEC site is a mean over the "
           "task-specification positions, which exclude the read position). In Qwen2.5-7B-Instruct no verbalisable "
           "plan was found at pre-code positions: the NLA names the algorithm at the token where the prompt names it and "
           "not 170 tokens later, and edits work only at the generated-token site. The read position is inert as a "
           "carrier in Qwen3-8B (its exchange transfers nothing on six tasks) and reads only the format line in the NLA; "
           "Gemma's read position was not measured.")
    t279 = ("\n\n**Table 279.** What was measured where, per model and quantity (NEW in iteration 7). Sources: exchange "
            "and site experiment `results/stage_a.json`; Gemma feature experiment `results/fork.json`, "
            "`results/readout.json`, `src/cfg.py`; NLA experiment `results/readout.json`, `results/local_control.json`. "
            + MARK + "\n\n| Model | Quantity | Site measured | Instrument | Result | Sites never measured |\n|-|-|-|-|-|-|\n"
            f"| Qwen3-8B | where an external ban or instruction is carried | task-specification states (blocks 0-11, "
            "12-23, 24-35, 0-35), condition span, read position | full-state exchange and KV splice into a "
            f"token-matched twin | carried by the task-specification states on prompt-route tasks (shortest path "
            f"{sp['attempted_Y']} of 30 attempts, {sp['correct_Y']} of 30 correct; kth smallest {k0['attempted_Y']} of "
            f"30, {k0['correct_Y']} of 30) and by the condition span on direct-route tasks; read position 0 on six tasks "
            "| generated tokens; any low-rank subspace (Stage B not run) |\n"
            "| Qwen3-8B | its natural choice | not measured (one algorithm per prompt) | n/a | n/a | every site |\n"
            "| gemma-3-4b-it | its natural choice (BFS or DFS) | generated token at response index 32; mean over the "
            "task-specification positions | prefix resampling; cross-prompt readout; SAE, difference-in-means and DAS "
            "edits | one generated token decides; task-spec edits and readouts barely reach it (SAE codes = text, 0.18) "
            "| the read position |\n"
            "| gemma-3-4b-it | the read position | never read or edited | n/a | n/a | the read position |\n"
            "| Qwen2.5-7B-Instruct | a verbalisable plan | end-of-prompt positions (SPEC-3 to READ), the name token, "
            "generated tokens 1 to 16 | NLA explanations judged blind | none at pre-code positions; the algorithm is named "
            f"at its name token (80% forced, 89% ban); per sample the outside reader is ahead ({h['one_unit_first']['b']}:"
            f"{h['one_unit_first']['c']} at one unit per sample) | non-verbal carriers at any position |")
    # Table 279 rides on the same paragraph correction (an insert inside a replaced paragraph would overlap it)
    ed.sub("**Where the choice is held, in three models.**", "0d", "after an opening shared by every algorithm.",
           "after an opening shared by every algorithm." + t279)
    ed.sub("The plan-variable account was tested in part", "0d",
           "Where the choice is held is now measured in three models: the task-specification states in Qwen3-8B for bans "
           "and instructions on the prompt-route tasks, one generated token in Gemma, and nothing verbalisable before the "
           "code in Qwen2.5-7B-Instruct.",
           "Three different quantities were measured, one per model (Table 279): where a ban or instruction is carried "
           "in Qwen3-8B (the task-specification states on the prompt-route tasks), where Gemma's natural choice is made "
           "(one generated token), and whether Qwen2.5-7B-Instruct's plan is verbalisable before the code (not to this "
           "NLA); Qwen3-8B's natural choice and Gemma's read position were never measured.")
    ed.sub("- *The read position as a carrier of the choice:*", "0d",
           "zero transfer in six Qwen3-8B tasks (Tables 244 to 249), no readout beyond text in Gemma (Table 261), only "
           "the format line in the NLA explanations.",
           "zero transfer in six Qwen3-8B tasks (Tables 244 to 249) and only the format line in the NLA explanations. "
           "Gemma's read position was never read or edited (its SPEC site is a mean over the task-specification "
           "positions, from the first token of 'Task:' to the last token of the user message, `src/cfg.py` line 7), so "
           "Gemma does not bear on this dead end.")
    ed.sub("2. *In Qwen3-8B the substitute of a ban and the algorithm of an instruction", "0a",
           "Exchanging those states alone transfers the ban on shortest path (0.80) and kth smallest (0.57), and a forced "
           "instruction on shortest path (30 of 30) and connected components (28 of 30);",
           f"Exchanging those states alone transfers the ban on shortest path ({sp['attempted_Y']} of 30 attempts, "
           f"{sp['correct_Y']} of 30 correct programs) and kth smallest ({k0['attempted_Y']} of 30 attempts, "
           f"{k0['correct_Y']} of 30 correct), and a forced instruction on shortest path ({fb['attempted_Y']} of 30 "
           f"attempts, {fb['correct_Y']} of 30 correct) and connected components ({fc['attempted_Y']} of 30 attempts, "
           f"{fc['correct_Y']} of 30 correct);")
    # closing paragraph: one rewrite carrying 0a, 0c, 0d and 0h
    closing = ed._line("Where the choice is held has now been measured in three models")
    tail = closing[closing.find(" Whether the choice in Qwen3-8B is a low-rank variable"):]
    new_closing = (
        "Three quantities have now been measured, one per model and each at its own site (Table 279). In Qwen3-8B the "
        "residual states at the task-specification positions carry the substitute of a ban and the algorithm of an "
        f"instruction on the prompt-route tasks: exchanging those states alone into a neutral twin transfers the ban on "
        f"shortest path ({sp['attempted_Y']} of 30 attempts, {sp['correct_Y']} of 30 correct programs) and kth smallest "
        f"({k0['attempted_Y']} of 30 attempts, {k0['correct_Y']} of 30 correct) and a forced instruction on shortest "
        f"path ({fb['attempted_Y']} of 30 attempts, {fb['correct_Y']} of 30 correct) and connected components "
        f"({fc['attempted_Y']} of 30 attempts, {fc['correct_Y']} of 30 correct), while matched-norm random exchanges and "
        "a placebo transfer at most 4 of 30; on the direct-route tasks the condition span carries the ban. Qwen3-8B's "
        "natural choice was not measured. In gemma-3-4b-it the natural choice between BFS and DFS is made at one "
        "generated token after a shared 32-token opening (` visited` leads to DFS with BFS probability 0.011; a blank "
        "line, `if` or `queue` lead to BFS at 0.95 to 1.00), about 138 tokens before the code identifies the algorithm. "
        "Its fork log-odds is linearly decodable across prompts from the residual stream at that position (a "
        "preregistered Lasso on Gemma Scope 2 SAE codes R-squared 0.66 against 0.18 for the text; a post-hoc ridge on "
        f"the raw state 0.72), but {g['note_txt']}, and {g['ridge_txt']}. Within the controls it had, {g['das_txt']}; a "
        "difference-in-means edit moves the fork log-odds 2.3 times as far as the SAE clamp at matched norm, and edits "
        f"toward the minority algorithm lowered the pass rate from {g['twin_pass']:.2f} to {g['main4_pass'][0]:.2f}-"
        f"{g['main4_pass'][1]:.2f}, except the SAE top-5 clamp ({g['top5']['bfs']} BFS, pass {g['top5']['pass']:.2f}), "
        "so no feature claim is made. Gemma's read position was never read or edited. In Qwen2.5-7B-Instruct a natural "
        "language autoencoder names the algorithm at the token where the prompt names it and not 170 tokens later, and "
        "its pre-code explanations name no algorithm; an outside reader of the text predicts the realised algorithm "
        f"better per unit (20:88), and {h['one_txt']}, with a task-cluster interval of [{h['cluster_boot_ci'][0]:.2f}, "
        f"{h['cluster_boot_ci'][1]:.2f}] that is inconclusive at the task level; a verbal edit steered two of four tasks "
        "only at the generated-token site and large doses, in an exploratory follow-up. The read position is inert as a "
        "carrier in Qwen3-8B and in the NLA's reading." + tail)
    ed.sub("Where the choice is held has now been measured in three models", "0d", closing, new_closing)
    remain = ed._line("What remains open follows from this.")
    head = remain[:remain.find(" Of the items of the request,")]
    ed.sub("What remains open follows from this.", "0d", head,
           "What remains open follows from this. First, the plan-and-fork account: whether Qwen3-8B's choice is a "
           "low-rank plan variable at the task-specification positions that is realised at a fork token in generation, "
           "tested by DAS fitted against the Stage A exchanges (whose correct-Y counts are the full-state denominator) "
           "and by the projection of iteration 4's 40 directions onto the fitted subspace. Second, DAS with the Sutter "
           "controls (a fit on a randomly initialised model, shuffled targets and forced-DFS sources), without which "
           "neither Gemma's fork subspace nor a Qwen3-8B one says anything about dimensionality. Third, the fork-margin "
           "test of temperature: whether temperature changes the algorithm only where the margin at a fork token is "
           "small, which would reconcile the temperature nulls with forking-path accounts. Fourth, the circuit at "
           "Gemma's fork, the transcoder attribution graph that the first-order fallback replaced. Fifth, "
           "evaluator-guided search, the documented route to new programs [81, 82], which this run has not tried. The "
           "question of what makes the ban-free unit weaker than the ban unit (its per-position and per-block profile or "
           "its direction seeds) and whether base intent holds on more tasks remain as before.")
    return {"table_279": True}


# ======================================================================== 0j
def item_0j(ed, report_iter6: str, report: str) -> dict[str, Any]:
    pre = "**Novelty, audited everywhere.**"
    old_line = next(l for l in report_iter6.split("\n") if l.startswith(pre))
    cur_line = ed._line(pre)
    i = 0
    while i < min(len(old_line), len(cur_line)) and old_line[i] == cur_line[i]:
        i += 1
    insertion = cur_line[i:]
    found_by = "diff against art_aRTQM6CQ0Dre:inputs/report/current_report.md"
    if not insertion.startswith("; the 14 that judges over-called"):
        k = cur_line.find("; the 14 that judges over-called in iteration 5 were re-adjudicated blind in iteration 6")
        insertion, found_by = cur_line[k:], "fallback string"
    base = cur_line[: len(cur_line) - len(insertion)]
    claim = ("every correct program outside the catalogue that the run produced has been read by two blind judges and "
             "the executor, and none was new")
    assert claim in base
    new_base = base.replace(claim, (
        "every correct program outside the catalogue in the pools audited so far has been read by two blind judges and "
        "the executor, and none was new: iterations 1 to 3, the 78 correct programs outside the catalogue among 11,763 "
        "unique correct programs (Section 3.2.3, Table 87); iteration 4, the audits of Table 165; iteration 5, its 130 "
        "correct programs outside the catalogue, with the 14 over-calls re-adjudicated in iteration 6 (Section 6.2.6); "
        "and iteration 6, the pools of Table 278, including the engine control's 3 correct programs labelled other, "
        "judged in iteration 7. Two pools were never audited by judges: about 9,000 programs of the forking token "
        "experiment, as recorded in Section 3.2.3, and the engine control's nearest-known pass of iteration 6 (up to 237 "
        "correct programs per engine and task, compared with known solutions by token overlap only; Table 278)"))
    body = insertion.lstrip("; ").rstrip(".")
    new_line = new_base.rstrip(";").rstrip() + f". *(Correction, iteration 6: {body}.)* " + MARK
    vals = [V("pool|forking_token_unaudited", None, "about 9,000", carried=True,
              source="report Section 3.2.3 ('About 9,000 other programs of the forking token experiment were not audited')"),
            V("insertion_found_by", found_by, None, tol="text", source="art_aRTQM6CQ0Dre:inputs/report/current_report.md")]
    ed.whole(cur_line, "0j", "replace", new_line, values=vals, section="4.9", table=None,
             rationale="iteration-6 insertion wrapped; claim limited to the audited pools")
    leftovers = [ln for ln, l in enumerate(report.split("\n"), 1)
                 if "every correct program outside the catalogue that the run produced" in l and not l.startswith(pre)]
    return {"insertion": insertion, "found_by": found_by, "lint_other_lines": leftovers, "values": vals}


# ======================================================================== 0l
def item_0l(ed) -> dict[str, Any]:
    t = f" {TAG}"
    ed.sub("**The plan sampler comparison is DISCONFIRMED** (Table 207).", "0l",
           "**The plan sampler comparison is DISCONFIRMED** (Table 207).",
           f"**The plan sampler comparison is DISCONFIRMED** (Table 207){t}.")
    ed.sub("- *The plan sampler comparison: plan noise prices at least as well as text-level plan samplers.*", "0l",
           "Disconfirmed (1 of 5 decisive tasks);", f"Disconfirmed (1 of 5 decisive tasks){t};")
    ed.sub("- *The movability half: the base repertoire predicts which tasks a nudge moves.*", "0l",
           "Not supported as a strong predictor, and not disconfirmed:",
           f"Not supported as a strong predictor, and not disconfirmed{t}:")
    ed.sub("The movability verdict is restated with its interval and power", "0l",
           "The movability verdict is restated with its interval and power (correction in Section 5.11).",
           f"The movability verdict is restated with its interval and power (correction in Section 5.11){t}.")
    ed.sub("Priced as a knob, plan noise is not the practical answer on the evidence so far.", "0l",
           "plan noise matched the best sampler on 1 of 5 decisive tasks:",
           f"plan noise matched the best sampler on 1 of 5 decisive tasks{t}:")
    ed.sub("What decides the replacement under a modal ban has measured leads and no confirmed rule.", "0l",
           "Both verdicts are conditional on the ban-free unit and seeds of iteration 5.",
           f"Both verdicts are conditional on the ban-free unit and seeds of iteration 5{t}.")
    return {"tag": TAG, "n_tagged": 6}
