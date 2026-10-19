#!/usr/bin/env python3
"""8i Mechanical verdicts (S-T5, S-T6, S-T7, S-B with Holm correction) and the forecast check (P1-P8)."""

from __future__ import annotations

from prompts.build import SEMANTIC_IMPLIED

ALPHA = 0.05


def holm(pvals: dict) -> dict:
    items = sorted(((p if p is not None else 1.0), k) for k, p in pvals.items())
    m = len(items)
    adj, running = {}, 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def _slope_rows(ph, task, thinking=False, theta=0.8, linkage="single"):
    return [s for s in ph["slopes"] if s["task"] == task and s["thinking"] == thinking and s["theta"] == theta
            and s["linkage"] == linkage]


def screen_tests(task: str, A: dict) -> dict:
    si = {r["condition"]: r for r in A["seeds_instructions"] if r["task"] == task}
    sub = A["subspace_test"][task]["l_star"]["conditions"]
    vs = A["variance_split"][task]
    ph = A["ideas_by_phrasings"]
    # S-T5: random seeds within 1.5x paraphrase noise at R; semantic seed exceeds the null
    rand_within_R = all(sub[c]["within_null_1p5"] for c in ("seed_entropy", "seed_word"))
    p5 = sub["seed_semantic"]["mannwhitney_p_greater"]
    # S-T6: excess mode-share slope (S_gen, data-matched null) <= 0 while complement variance rises
    key = "S_gen" if "S_gen" in vs["slopes"] else "S_R"
    sl = vs["slopes"][key]
    ex_ok = sl["excess_share_dm"]["ci95"][0] <= 0
    comp = sl["comp_var"]
    # one-sided bootstrap p for 'complement variance does not rise with T'
    p6 = comp.get("p_le0")
    if p6 is not None:
        p6 = max(p6, 1.0 / 1001)
    comp_rises = comp.get("ci95", [0, 0])[0] > 0
    # S-T7: phrasing slope > idea slope (paired), log PPI slope > 0 at every theta and both samplers
    prim = _slope_rows(ph, task)
    p7 = max((r["p_one_sided_diff_le_0"] for r in prim if r["p_one_sided_diff_le_0"] is not None), default=1.0)
    ppi_all = [s for s in ph["slopes"] if s["task"] == task and not s["thinking"]]
    ppi_pos_all = all((s["slope_log_PPI"] or 0) > 0 for s in ppi_all)
    diff_ci_pos = all(r["ci95_diff"] and r["ci95_diff"][0] > 0 for r in prim)
    idea_ge_phr = any(r["ci95_diff"] and r["ci95_diff"][1] <= 0 for r in prim)
    # S-B: random-seed behaviour shift within +-15 pp (90% CI); semantic seed moves toward implied mode
    rand_within_B = all(si[c]["equivalence_within_15pp"] for c in ("seed_entropy", "seed_word"))
    rand_exceeds_B = any(abs(si[c]["modal_share_shift_pp"]) > 15 for c in ("seed_entropy", "seed_word"))
    rand_exceeds_R = any(sub[c]["ratio_ci90"][0] > 1.5 for c in ("seed_entropy", "seed_word"))
    pB = si["seed_semantic"].get("implied_cluster_perm_one_sided_p", 1.0)
    pvals = {"S-T5": p5, "S-T6": p6 if p6 is not None else 1.0, "S-T7": p7, "S-B": pB}
    adj = holm(pvals)
    sem_R_toward = sub["seed_semantic"]["cos_with_centroids"].get(SEMANTIC_IMPLIED[task], 0) > 0
    res = {
        "S-T5": dict(p=p5, p_holm=adj["S-T5"], random_seeds_within_1p5=rand_within_R,
                     holds=bool(rand_within_R and adj["S-T5"] < ALPHA)),
        "S-T6": dict(subspace=key, excess_share_slope=sl["excess_share_dm"]["slope"],
                     excess_share_ci95=sl["excess_share_dm"]["ci95"], excess_slope_le0=ex_ok,
                     comp_var_slope=comp["slope"], comp_var_ci95=comp.get("ci95"), comp_rises=comp_rises,
                     p=p6, p_holm=adj["S-T6"], holds=bool(ex_ok and comp_rises and adj["S-T6"] < ALPHA)),
        "S-T7": dict(p=p7, p_holm=adj["S-T7"], log_ppi_slope_positive_every_theta_sampler=ppi_pos_all,
                     paired_diff_ci_positive_primary=diff_ci_pos, idea_slope_ge_phrasing_slope=idea_ge_phr,
                     holds=bool(ppi_pos_all and diff_ci_pos and adj["S-T7"] < ALPHA)),
        "S-B": dict(p=pB, p_holm=adj["S-B"], random_seeds_within_15pp=rand_within_B,
                    semantic_implied_shift_pp=si["seed_semantic"].get("implied_share_change_pp"),
                    holds=bool(rand_within_B and adj["S-B"] < ALPHA)),
        "random_seed_exceeds_15pp": rand_exceeds_B, "random_seed_exceeds_R_null": rand_exceeds_R,
        "semantic_moves_toward_implied_R": bool(sem_R_toward),
        "semantic_moves_toward_implied_behaviour": bool((si["seed_semantic"].get("implied_share_change_pp") or 0) > 0
                                                        and pB < ALPHA)}
    return res


def overall(per_task: dict) -> dict:
    t7 = {t: v["S-T7"]["holds"] for t, v in per_task.items()}
    t6 = {t: v["S-T6"]["holds"] for t, v in per_task.items()}
    rand_ok = all(v["S-T5"]["random_seeds_within_1p5"] and v["S-B"]["random_seeds_within_15pp"]
                  for v in per_task.values())
    sem_ok = any(v["semantic_moves_toward_implied_R"] or v["semantic_moves_toward_implied_behaviour"]
                 for v in per_task.values())
    same_sign_67 = any(t7[t] and t6[t] for t in per_task)
    contradicted = any(v["S-T7"]["idea_slope_ge_phrasing_slope"] or v["random_seed_exceeds_15pp"] or
                       v["random_seed_exceeds_R_null"] for v in per_task.values())
    if same_sign_67 and rand_ok and sem_ok and not contradicted:
        verdict = "SUPPORTED: temperature and seeds are phrasing knobs, not idea knobs"
    elif contradicted:
        verdict = "CONTRADICTED: temperature and/or seeds act as idea knobs"
    else:
        failing = []
        if not any(t7.values()):
            failing.append("S-T7 phrasing slope")
        if not any(t6.values()):
            failing.append("S-T6 variance-share slope")
        if not all(v["S-T5"]["random_seeds_within_1p5"] for v in per_task.values()):
            failing.append("random-seed equivalence at R (1.5x bound)")
        if not all(v["S-B"]["random_seeds_within_15pp"] for v in per_task.values()):
            failing.append("random-seed behavioural equivalence (+-15 pp)")
        if not sem_ok:
            failing.append("semantic seed positive control")
        verdict = "MIXED: failing sub-claims -> " + "; ".join(failing)
    return dict(verdict=verdict, S_T7_by_task=t7, S_T6_by_task=t6, random_seeds_pass_both_bounds=rand_ok,
                semantic_positive_control=sem_ok, contradiction_triggered=contradicted)


def forecast_check(A: dict) -> dict:
    tab = A["bfs_dijkstra_table"]
    out = {}
    t1 = [r for r in tab if r["task"] == "T1" and r["arm"] == "A1"]
    out["P1"] = dict(prediction="T1 thinking-off BFS share >= 0.7 at every T",
                     observed={r["cell"]: r["share_classified"]["share"] for r in t1},
                     hit=all(r["share_classified"]["share"] >= 0.7 for r in t1))
    t2 = [r for r in tab if r["task"] == "T2" and r["arm"] in ("A1",) ]
    out["P2"] = dict(prediction="T2 Dijkstra share >= 0.8 at every T", observed={r["cell"]: r["share_classified"]["share"]
                                                                                 for r in t2},
                     hit=all(r["share_classified"]["share"] >= 0.8 for r in t2))
    si = A["seeds_instructions"]
    p3 = [r for r in si if r["condition"] in ("seed_entropy", "seed_word")]
    out["P3"] = dict(prediction="entropy/word seeds: 90% CI of modal shift within +-15 pp and perm p > 0.05",
                     observed={f"{r['task']}|{r['condition']}": dict(ci90=r["shift_ci90"], p=r["cluster_perm_p"])
                               for r in p3},
                     hit=all(r["equivalence_within_15pp"] and r["cluster_perm_p"] > 0.05 for r in p3))
    p4 = [r for r in si if r["condition"] == "seed_semantic"]
    out["P4"] = dict(prediction="semantic seed shifts toward implied mode with p < 0.05 on >= 1 task",
                     observed={r["task"]: dict(change_pp=r["implied_share_change_pp"],
                                               perm_p=r["implied_cluster_perm_one_sided_p"],
                                               fisher_p=r["implied_fisher_one_sided_p"]) for r in p4},
                     hit=any(r["implied_share_change_pp"] > 0 and r["implied_cluster_perm_one_sided_p"] < 0.05
                             for r in p4))
    st = A["subspace_test"]
    obs5, hit5 = {}, True
    for task in ("T1", "T2"):
        c = st[task]["l_star"]["conditions"]
        imp = SEMANTIC_IMPLIED[task]
        rnd = all(c[x]["ratio_ci90"][1] < 1.5 for x in ("seed_entropy", "seed_word"))
        sem = c["seed_semantic"]["mannwhitney_p_greater"] < 0.05 and c["seed_semantic"]["cos_with_centroids"][imp] > 0
        obs5[task] = dict(entropy_ratio_ci90=c["seed_entropy"]["ratio_ci90"], word_ratio_ci90=c["seed_word"]["ratio_ci90"],
                          semantic_mw_p=c["seed_semantic"]["mannwhitney_p_greater"],
                          semantic_cos_implied=c["seed_semantic"]["cos_with_centroids"][imp])
        hit5 = hit5 and rnd and sem
    out["P5"] = dict(prediction="random seeds within 1.5x null at R; semantic exceeds and moves toward implied centroid",
                     observed=obs5, hit=hit5)
    ph = A["ideas_by_phrasings"]["slopes"]
    off = [s for s in ph if not s["thinking"]]
    out["P6"] = dict(prediction="log PPI slope > 0 at every theta and both samplers; DA_phr slope > DA_idea slope",
                     observed={f"{s['task']}|{s['sampler']}|{s['theta']}|{s['linkage']}": dict(
                         slope_log_PPI=s["slope_log_PPI"], diff=s["slope_diff_phr_minus_idea"]) for s in off},
                     hit=all((s["slope_log_PPI"] or 0) > 0 and (s["slope_diff_phr_minus_idea"] or 0) > 0 for s in off))
    vs = A["variance_split"]
    obs7, hit7 = {}, True
    for task in ("T1", "T2"):
        key = "S_gen" if "S_gen" in vs[task]["slopes"] else "S_R"
        sl = vs[task]["slopes"][key]
        ok = sl["excess_share_dm"]["ci95"][0] <= 0 and sl["comp_var"]["ci95"][0] > 0
        obs7[task] = dict(subspace=key, excess_ci95=sl["excess_share_dm"]["ci95"], comp_ci95=sl["comp_var"]["ci95"])
        hit7 = hit7 and ok
    out["P7"] = dict(prediction="excess mode-share slope <= 0 while complement variance rises", observed=obs7, hit=hit7)
    buy = A["buy_rows"]
    obs8, hit8 = {}, True
    for task in ("T1", "T2"):
        g = [r for r in buy if r["task"] == task and r["knob"] == "gen_then_select"]
        others = [r for r in buy if r["task"] == task and r["knob"] != "gen_then_select" and r["DA_idea_25"]]
        gv = g[0]["DA_idea_25"] if g else None
        mx = max((r["DA_idea_25"] for r in others), default=None)
        obs8[task] = dict(gen_then_select=gv, best_other=mx)
        hit8 = hit8 and gv is not None and mx is not None and gv > mx
    out["P8"] = dict(prediction="gen-then-select has the highest DA_idea@25", observed=obs8, hit=hit8)
    out["n_hits"] = sum(1 for k, v in out.items() if isinstance(v, dict) and v.get("hit"))
    return out
