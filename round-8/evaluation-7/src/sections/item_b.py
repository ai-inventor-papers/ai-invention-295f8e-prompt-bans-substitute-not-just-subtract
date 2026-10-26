#!/usr/bin/env python3
"""Item 0b: recovery by source and rank (the summary statistic; pooled recovery secondary) and the three untrained-
network ratios with their definitions (shortest path only)."""

from __future__ import annotations

from typing import Any

from sections.common import SUFFIX, TABLES, clopper_pearson, dep, edit, read_json, src_ref, value, write_csv

TASK_NAME = {"T2": "shortest path", "T10": "connected components", "T03": "kth smallest"}
Y_NAME = {"bf_spfa": "Bellman-Ford/SPFA", "floyd": "Floyd-Warshall", "bfs": "BFS", "dfs": "DFS",
          "quickselect": "quickselect", "size_k_heap": "size k heap", "counting_sort": "counting sort"}
SRC_NAME = {"ban": "fifth template ban", "F_bf_spfa": "forced Bellman-Ford/SPFA", "F_floyd": "forced Floyd-Warshall",
            "F_bfs": "forced BFS", "F_dfs": "forced DFS", "F_quickselect": "forced quickselect",
            "F_counting_sort": "forced counting sort"}
RANKS = (1, 2, 4, 8, 16)


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    rc = ctx["a5"]
    per = {"T2": rc["old"]["T2"], "T10": rc["old"]["T10"], "T03": rc["new"]["T03"]}
    rows, md = [], []
    p1 = read_json(dep("exp33", "results/p1.json"))["tasks"]
    for t in ("T2", "T10", "T03"):
        for s, ps in per[t]["per_source"].items():
            b, f = ps["base_count"], ps["full_count"]
            # recorded per_source values in p1.json must match the port (old labels), except the relabelled cell
            rec_full = p1[t]["per_source"][s]["full_count"]
            value(f"{t} {s} full-state count", rec_full, f, "MATCH" if rec_full == f else "CORRECTED",
                  src_ref("exp33", "results/p1.json", f"tasks.{t}.per_source.{s}.full_count"), 0, "0b")
            cells = []
            for k in RANKS:
                d = ps["das"].get(k)
                if d is None:
                    rows.append({"task": t, "source": s, "Y": "+".join(ps["Y"]), "rank": k, "generated": "n",
                                 "base": b, "full": f})
                    cells.append("not generated")
                    continue
                den = f - b
                r = (d["count"] - b) / den if den != 0 else None
                ci = clopper_pearson(d["count"], 30)
                rows.append({"task": t, "source": s, "Y": "+".join(ps["Y"]), "rank": k, "generated": "y", "base": b,
                             "full": f, "das_count": d["count"], "recovery": "undefined" if r is None else round(r, 4),
                             "pass": round(d["pass"], 4), "share": round(d["count"] / 30, 4),
                             "share_cp95_lo": round(ci[0], 4), "share_cp95_hi": round(ci[1], 4)})
                cells.append(f"{d['count']} ({'undefined' if r is None else f'{r:.2f}'})")
                value(f"{t} {s} rank {k} correct Y (of 30)", p1[t]["per_source"][s]["das"][str(k)]["count"],
                      d["count"], "MATCH", src_ref("exp33", "results/p1.json", f"tasks.{t}.per_source.{s}.das.{k}.count"), 0, "0b")
            md.append(f"| {TASK_NAME[t]} | {SRC_NAME[s]} | {', '.join(Y_NAME[y] for y in ps['Y'])} | {b} | {f} | " + " | ".join(cells) + " |")
    write_csv(TABLES / "recovery_by_source.csv", rows,
              ["task", "source", "Y", "rank", "generated", "base", "full", "das_count", "recovery", "pass", "share",
               "share_cp95_lo", "share_cp95_hi"])
    table = ("**Table 297b.** Recovery by source and rank (summary statistic; pooled recovery is secondary). Each cell is "
             "the count of correct programs of the target algorithm of 30 and, in parentheses, the recovery (DAS count - "
             "base) / (full state count - base), undefined when the denominator is 0. Forced sources were generated at "
             "ranks 1, 4 and 16 only (deviation D-C-k), and the kth smallest ban source at ranks 1, 4 and 16. The kth "
             "smallest forced counting sort row uses the relabelled full state (29). Source: `results/p1.json` per_source "
             "of the DAS experiment, recomputed from `data/labels.jsonl` (iteration-8 correction: new table)\n\n"
             "| Task | Source | Target Y | Base | Full state | Rank 1 | Rank 2 | Rank 4 | Rank 8 | Rank 16 |\n"
             "|-|-|-|-|-|-|-|-|-|-|\n" + "\n".join(md))
    # untrained network ratios (shortest path only)
    ri = read_json(dep("exp33", "results/randinit_T2.json"))
    ly = read_json(dep("exp33", "results/randinit_ly_T2.json"))
    r_comm = ri["ratio"]
    r_fit = ly["random_net_heldout_das16_gain"] / ly["trained_heldout_das16_gain"]
    r_lme = ly["random_net_heldout_das16_lmeY_gain"] / ly["trained_heldout_das16_lmeY_gain"]
    value("untrained network: committed ratio (contrastive objective, against the diverged fit)", None, r_comm, "NEW",
          src_ref("exp33", "results/randinit_T2.json", "ratio"), 0.0005, "0b",
          f"{ri['random_net_heldout_das16_gain']:.2f} against {ri['trained_heldout_das16_gain']:.2f}; D-randinit: not meaningful")
    value("untrained network: fit-value ratio quoted in 7.3.5", 0.92, r_fit, "MATCH",
          src_ref("exp33", "results/randinit_ly_T2.json", "random_net_heldout_das16_gain / trained_heldout_das16_gain"), 0.005, "0b",
          f"{ly['random_net_heldout_das16_gain']:.2f} against {ly['trained_heldout_das16_gain']:.2f} nats")
    value("untrained network: matched likelihood-gain ratio (ratio_lmeY)", None, r_lme, "NEW",
          src_ref("exp33", "results/randinit_ly_T2.json", "ratio_lmeY"), 0.005, "0b",
          f"{ly['random_net_heldout_das16_lmeY_gain']:.2f} against {ly['trained_heldout_das16_lmeY_gain']:.2f} nats")
    assert abs(r_lme - ly["ratio_lmeY"]) < 1e-9 and abs(r_fit - ly["ratio"]) < 1e-9
    g_rand, g_tr = ly["random_net_heldout_das16_lmeY_gain"], ly["trained_heldout_das16_lmeY_gain"]
    # permuted-label transfers: absolute and relative to the full-state effect
    pr = {}
    for t, arm in (("T2", "PERMLY_ban_k2"), ("T10", "PERMLY_ban_k16"), ("T03", "PERMLY_ban_k1")):
        q = per[t]["per_source"]["ban"]["perm"][arm]
        pr[t] = q
        value(f"{t} permuted-label transfer ({arm}), absolute", {"T2": 0.47, "T10": 0.70, "T03": 0.60}[t], q["transfer"],
              "MATCH", src_ref("exp33", "results/p1.json", f"tasks.{t}.per_k.permuted_transfer_max"), 0.005, "0b")
        value(f"{t} permuted-label transfer ({arm}), relative to the full-state effect", None, q["relative_to_full"],
              "NEW", src_ref("exp33", "data/labels.jsonl", f"arm=={arm}"), 0.005, "0b")
    rel = sorted(q["relative_to_full"] for q in pr.values())
    ban_sp = per["T2"]["per_source"]["ban"]
    rec_bf = [per["T2"]["per_source"]["F_bf_spfa"]["das"][k]["recovery"] for k in (1, 4, 16)]
    rec_bfs = [per["T10"]["per_source"]["F_bfs"]["das"][k]["recovery"] for k in (1, 4, 16)]
    rng_bf = f"{min(rec_bf):.2f} to {max(rec_bf):.2f}"
    rng_bfs = f"{min(rec_bfs):.2f} to {max(rec_bfs):.2f}"
    persrc = (f"by source it matches or exceeds the full state exchange for the ban sources (except shortest path at rank "
              f"16, {ban_sp['das'][16]['count']} against {ban_sp['full_count']}) and for the forced Floyd-Warshall, "
              f"quickselect, counting sort and DFS sources, recovers {rng_bf} of forced Bellman-Ford/SPFA and {rng_bfs} of "
              f"forced BFS, and rank 2 is untested for forced sources (Table 297b)")
    unt = (f"the untrained-network control ran on shortest path only; the committed comparison with the diverged "
           f"contrastive fit (ratio {r_comm:.3f}) proved meaningless and was replaced post hoc; under the matched "
           f"likelihood fit the untrained network gains {g_rand:.1f} nats against {g_tr:.1f} for the trained one "
           f"(ratio {r_lme:.1f}), while the fit-value ratio is {r_fit:.2f} ({ly['random_net_heldout_das16_gain']:.2f} "
           f"against {ly['trained_heldout_das16_gain']:.2f} nats)")
    E = []
    E.append(edit("C8-b01", "0b", "7.3.4", "Recovery is the ratio of the edit's transfer to the full state transfer; pooled over sources it lies between 0.73 and 1.71 at every rank on every task, and above 1 where a trained direction moves the model further than the full exchange.",
                  f"Recovery is the ratio of the edit's transfer to the full state transfer, and its summary is per source and rank: {persrc}. Pooled over sources as a ratio of sums (secondary), it lies between 0.73 and 1.71 on shortest path and connected components and between 0.99 and 1.01 on kth smallest after the counting-sort relabel, above 1 where a trained direction moves the model further than the full exchange{SUFFIX}."))
    E.append(edit("C8-b02", "0b", "Table 297b", "\n\n### 7.3.5 The controls that make it a handle, not a variable",
                  "\n\n" + table + "\n\n### 7.3.5 The controls that make it a handle, not a variable", kind="table_insert"))
    E.append(edit("C8-b03", "0b", "7.3.5", "The fits on permuted labels transfer 0.47 on shortest path, 0.70 on connected components and 0.60 on kth smallest of the full state effect, against a committed limit of 0.1:",
                  f"The fits on permuted labels transfer 0.47 on shortest path, 0.70 on connected components and 0.60 on kth smallest as absolute transfers ((count - base)/30; relative to the full state effect {pr['T2']['relative_to_full']:.2f}, {pr['T10']['relative_to_full']:.2f} and {pr['T03']['relative_to_full']:.2f}), against a committed limit of 0.1 (iteration-8 correction):"))
    E.append(edit("C8-b04", "0b", "7.3.5", "The untrained network admits a teacher-forced fit almost as good as the trained one (13.31 nats against 14.45 on shortest path, a ratio of 0.92 against a limit of 0.5).",
                  f"The untrained network admits a teacher-forced fit as good as the trained one or better: {unt}; three different ratios exist (committed {r_comm:.3f}, fit value {r_fit:.2f}, likelihood gain {r_lme:.2f}), each against a limit of 0.5, and only the last is measured in the objective both maps were fitted with (LME_Y){SUFFIX}."))
    E.append(edit("C8-b05", "0b", "Table 372", "| DAS claim (Qwen3-8B) | Not supported on any task | Recovery 0.73 to 1.71 and random subspaces null, but permuted labels transfer 0.47 to 0.70 and an untrained network fits at 0.92 of the trained fit |",
                  f"| DAS claim (Qwen3-8B) | Not supported on any task | By source (Table 297b): matches or exceeds the full-state exchange for ban sources and for the forced Floyd-Warshall, quickselect, counting sort and DFS sources; recovers {rng_bf} of forced Bellman-Ford/SPFA and {rng_bfs} of forced BFS; rank 2 untested for forced sources; random subspaces null; permuted labels transfer 0.47 to 0.70 of the 30 slots; the untrained network (shortest path only) gains {g_rand:.1f} nats against {g_tr:.1f} under the matched likelihood fit (ratio {r_lme:.1f}; the committed ratio {r_comm:.3f} was against the diverged fit) (iteration-8 correction) |", kind="table_row"))
    E.append(edit("C8-b06", "0a+0b", "7.10", "In Qwen3-8B a rank-1 or rank-2 subspace of the task specification states at blocks 12 to 23 is a steering handle on the algorithm that matches the full state exchange, and on two tasks it routes more cleanly than the full state. The handle is not a certified variable, because permuted labels and an untrained network admit it.",
                  f"In Qwen3-8B a rank-1 or rank-2 subspace of the task specification states at blocks 12 to 23 is a steering handle on the algorithm that matches or exceeds the full-state exchange for ban sources and for the forced Floyd-Warshall, quickselect, counting sort and DFS sources; recovers {rng_bf} of forced Bellman-Ford/SPFA and {rng_bfs} of forced BFS; rank 2 untested for forced sources. It routes more cleanly than the full state on one task (shortest path: Floyd-Warshall 28/28 against 8/20); on kth smallest the DAS edit changes the implementation form (mostly an array of counts against the full state's dictionary with sorted keys), not the algorithm. The handle is not a certified variable, because permuted labels and an untrained network admit it ({unt}){SUFFIX}."))
    E.append(edit("C8-b07", "0b", "closing", "and a DAS subspace of rank 1 or 2 at blocks 12 to 23 matches that exchange in generation while random subspaces of the same rank do nothing.",
                  f"and a DAS subspace of rank 1 or 2 at blocks 12 to 23 matches or exceeds that exchange in generation for the ban sources and the forced Floyd-Warshall, quickselect, counting sort and DFS sources, and recovers {rng_bf} of forced Bellman-Ford/SPFA and {rng_bfs} of forced BFS, while random subspaces of the same rank do nothing{SUFFIX}."))
    E.append(edit("C8-b08", "0b", "closing", "That subspace is a steering handle and not a certified variable: permuted labels transfer 0.47 to 0.70 of its effect, an untrained network admits a fit 0.92 as good [132], and the reverse interchange does not restore the default [122].",
                  f"That subspace is a steering handle and not a certified variable: permuted labels transfer 0.47 to 0.70 of the 30 slots ({rel[0]:.2f} to {rel[-1]:.2f} of the full-state effect); {unt} [132]; and the reverse interchange does not restore the default [122]{SUFFIX}."))
    E.append(edit("C8-b10", "0b", "7.3.4", "A rank-1 or rank-2 edit moves the algorithm about as far as the full state exchange on all three tasks,",
                  "A rank-1 or rank-2 edit of the ban source moves the algorithm about as far as the full state exchange on all three tasks (forced sources by source in Table 297b; iteration-8 correction),"))
    E.append(edit("C8-b09", "0b", "7.9", "In Qwen3-8B a rank-1 or rank-2 DAS edit matches the full state exchange at the same site,",
                  f"In Qwen3-8B a rank-1 or rank-2 DAS edit matches the full state exchange at the same site for most sources (it recovers {rng_bfs} of forced BFS and {rng_bf} of forced Bellman-Ford/SPFA; Table 297b; iteration-8 correction),"))
    return {"edits": E, "verdict": "CORRECTED",
            "summary": {"untrained_ratios": {"committed_contrastive": r_comm, "fit_value": r_fit, "matched_lmeY": r_lme},
                        "permuted_relative_to_full": {t: q["relative_to_full"] for t, q in pr.items()},
                        "forced_bf_recovery": rec_bf, "forced_bfs_recovery": rec_bfs}}
