#!/usr/bin/env python3
"""Items 0f and 0g (base artifact art_cDba8_DycUJd).

0f  held-out circuit effect per side and per contrast; the record's sign-flip p reproduced with the vendored
    stats9.sign_flip_p; the exact five-contrast test; the pair-prompt averaging rule of 8.14 / 7.41 recovered from
    the iteration-8 validation rows vendored inside the base artifact (vendor/art_18XvfcJJZi1O/); empty edits.
0g  random patching sets: distinct components, repeated MLPs, effective sizes, restricted nulls over the sets with
    ten distinct components, Rscaled beside Rpure and R, and per-prompt shares beside the ratio of means.
"""

from __future__ import annotations

import csv
import itertools
import json
import sys
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from io_util import A_BASE, TABLES, VENDOR, dep_path, dep_root, r2, read_json, read_jsonl, ref, save_stage

if str(VENDOR / A_BASE) not in sys.path:
    sys.path.insert(0, str(VENDOR / A_BASE))
import stats9 as S9  # noqa: E402  (vendored, unmodified)

KEY_ABL = "aligned|ablate|mlp|L0|H-1|COND"
KEY_STR = "aligned|steer|mlp|L0|H-1|COND"
V41_ROWS = "vendor/art_18XvfcJJZi1O/data/validation_rows_C1forced.jsonl"
V41_SUMMARY = "vendor/art_18XvfcJJZi1O/results/summary.json"


def d_values(rows: list[dict[str, Any]], key: str, n_rand: int = 50) -> list[float]:
    out = []
    for r in rows:
        v = r["res"].get(f"{key}|node")
        rv = [r["res"][f"{key}|r{j}"] for j in range(n_rand) if f"{key}|r{j}" in r["res"]]
        out.append(v - float(np.mean(rv)))
    return out


def sign_flip_one_sided(d: list[float]) -> float:
    d = np.asarray(d, float)
    obs = d.mean()
    cnt = tot = 0
    for s in itertools.product((1.0, -1.0), repeat=len(d)):
        tot += 1
        cnt += int((d * np.asarray(s)).mean() >= obs - 1e-12)
    return cnt / tot


def run_0f() -> dict[str, Any]:
    rows = read_jsonl(dep_path(A_BASE, "results/b3_heldout_rows.jsonl"))
    st = read_json(dep_path(A_BASE, "results/b3_summary.json"))
    sides_ok = all((r["side"] == "clean") == r["vid"].endswith("|pad") for r in rows)
    res: dict[str, Any] = {"sides_confirmed": sides_ok, "modes": {}}
    tab = []
    for mode, key in (("ablate", KEY_ABL), ("steer", KEY_STR)):
        d = d_values(rows, key)
        raw = [r["res"][f"{key}|node"] for r in rows]
        forced = [x for x, r in zip(d, rows) if r["side"] == "corrupt"]
        padded = [x for x, r in zip(d, rows) if r["side"] == "clean"]
        contrasts = {}
        for r, x in zip(rows, d):
            c = r["vid"].split("|")[0]
            contrasts.setdefault(c, {})[r["side"]] = x
        cmean = [float(np.mean([v["clean"], v["corrupt"]])) for v in contrasts.values()]
        cforced = [v["corrupt"] for v in contrasts.values()]
        p_rec = S9.sign_flip_p(d)
        rec = {"per_row": [{"prompt_idx": r["prompt_idx"], "vid": r["vid"], "side": r["side"], "d": x, "node_raw": y}
                           for r, x, y in zip(rows, d, raw)],
               "mean_forced": float(np.mean(forced)), "mean_padded": float(np.mean(padded)),
               "mean_all": float(np.mean(d)), "recorded_mean": st["per_node"][key]["mean_d_heldout"],
               "p_sign_flip_10_reproduced": p_rec, "p_sign_flip_10_recorded": st["per_node"][key]["p_sign_flip_heldout"],
               "contrast_means": dict(zip(contrasts.keys(), cmean)), "contrast_forced": dict(zip(contrasts.keys(), cforced)),
               "p5_contrast_mean_two_sided": S9.sign_flip_p(cmean), "p5_contrast_mean_one_sided": sign_flip_one_sided(cmean),
               "p5_forced_two_sided": S9.sign_flip_p(cforced), "p5_forced_one_sided": sign_flip_one_sided(cforced),
               "n_distinct_patterns_contrast_mean": len({tuple(np.sign(np.asarray(cmean) * np.asarray(s)))
                                                         for s in itertools.product((1, -1), repeat=5)})}
        res["modes"][mode] = rec
        for r, x, y in zip(rows, d, raw):
            tab.append([mode, r["prompt_idx"], r["vid"], "forced (corrupt)" if r["side"] == "corrupt" else "padded (clean)",
                        f"{x:.6f}", f"{y:.6f}"])
    # pair-prompt averaging rule (iteration-8 rows vendored inside the base artifact)
    pr: dict[str, Any] = {"status": "CARRIED", "source": ref(A_BASE, V41_ROWS)}
    try:
        v41 = read_jsonl(dep_root(A_BASE) / V41_ROWS)
        s41 = read_json(dep_root(A_BASE) / V41_SUMMARY)["validation"]["C1forced"]["per_node"]
        for mode in ("ablate", "steer"):
            k = f"{mode}|mlp|L0|H-1|COND"
            dd = []
            for r in v41:
                v = r["res"].get(f"{k}|node")
                rv = [r["res"][f"{k}|r{j}"] for j in range(50) if f"{k}|r{j}" in r["res"]]
                dd.append((r["prompt_idx"], r["side"], r.get("heldout"), v - float(np.mean(rv))))
            pair = [x for x in dd if not x[2]]
            rec_val = [x for x in s41[mode] if x["node"] == "mlp|L0|H-1|COND"][0]["mean_d_pair_prompts"]
            both = float(np.mean([x[3] for x in pair]))
            forced_only = float(np.mean([x[3] for x in pair if x[1] == "corrupt"]))
            pad_only = float(np.mean([x[3] for x in pair if x[1] == "clean"]))
            pr[mode] = {"recorded": rec_val, "mean_both_sides_20": both, "mean_forced_side_10": forced_only,
                        "mean_padded_side_10": pad_only, "n_pair_rows": len(pair),
                        "rule": "both sides" if abs(both - rec_val) < 1e-9 else
                        ("forced side only" if abs(forced_only - rec_val) < 1e-9 else "undetermined"),
                        "prompt0_d": [x[3] for x in dd if x[0] == 0][0]}
        if all(pr[m]["rule"] != "undetermined" for m in ("ablate", "steer")):
            pr["status"] = "MATCH"
        pr["repro_6_1"] = st["repro_6_1"]
    except (FileNotFoundError, KeyError, IndexError) as e:
        logger.warning(f"pair-prompt rule not recoverable: {e!r}; status CARRIED")
        pr["error"] = repr(e)
    res["pair_rule"] = pr
    # empty edits
    empty = {r["vid"]: [r["n_empty_edits"], r["n_jobs"]] for r in rows}
    groups_empty: Counter = Counter()
    for r in rows:
        keys = {}
        for k, v in r["res"].items():
            base, leaf = k.rsplit("|", 1)
            keys.setdefault(base, []).append(v)
        for base, vals in keys.items():
            if len(set(vals)) == 1:
                groups_empty[(r["vid"], base.split("|")[0])] += len(vals)
    ex_len = st["per_node"].get("exact_length|ablate|mlp|L0|H-1|COND", {})
    exd = ex_len.get("d_per_prompt", [])
    keep = [x for x, r in zip(exd, rows) if r["vid"].split("|")[0] not in ("F11", "F15")]
    res["empty_edits"] = {"per_row": empty, "sum_F11_F15": [sum(v[0] for k, v in empty.items() if k.startswith(("F11|", "F15|"))),
                                                             sum(v[1] for k, v in empty.items() if k.startswith(("F11|", "F15|")))],
                          "sum_all": [sum(v[0] for v in empty.values()), sum(v[1] for v in empty.values())],
                          "identical_value_groups": {f"{a}|{b}": n for (a, b), n in groups_empty.items()},
                          "exact_length_ablate_mean_with": float(np.mean(exd)) if exd else None,
                          "exact_length_ablate_mean_without_F11_F15": float(np.mean(keep)) if keep else None,
                          "random_meta": st["random_meta"]}
    with open(TABLES / "heldout_per_side.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["mode", "prompt_idx", "vid", "side", "d_node_minus_random_mean", "node_raw"])
        w.writerows(tab)
    a, s_ = res["modes"]["ablate"], res["modes"]["steer"]
    metrics = {"ablate_forced": a["mean_forced"], "ablate_padded": a["mean_padded"], "ablate_all": a["mean_all"],
               "steer_forced": s_["mean_forced"], "steer_padded": s_["mean_padded"], "steer_all": s_["mean_all"],
               "ablate_p10_reproduced": a["p_sign_flip_10_reproduced"], "steer_p10_reproduced": s_["p_sign_flip_10_reproduced"],
               "p5_two_sided": a["p5_contrast_mean_two_sided"], "p5_one_sided": a["p5_contrast_mean_one_sided"],
               "empty_F11_F15": res["empty_edits"]["sum_F11_F15"][0], "jobs_F11_F15": res["empty_edits"]["sum_F11_F15"][1],
               "pair_rule_recovered": float(pr["status"] == "MATCH")}
    ex = []
    for mode in ("ablate", "steer"):
        m = res["modes"][mode]
        for c in m["contrast_means"]:
            ex.append({"input": f"held-out contrast {c}, layer-0 condition MLP, {mode}",
                       "output": f"forced side {m['contrast_forced'][c]:.2f} nats; mean of the two sides {m['contrast_means'][c]:.2f}",
                       "metadata_mode": mode, "metadata_contrast": c, "eval_forced": m["contrast_forced"][c],
                       "eval_contrast_mean": m["contrast_means"][c]})
    section = {"inputs": [ref(A_BASE, "results/b3_heldout_rows.jsonl"), ref(A_BASE, "results/b3_summary.json"),
                          ref(A_BASE, V41_ROWS), ref(A_BASE, V41_SUMMARY)],
               "computation": "d = node value minus the mean of its 50 random-set values per row (src/b3_9.py analyze); "
                              "per-side and per-contrast means; vendored stats9.sign_flip_p for the record's 10-row p; "
                              "exact 32-pattern tests on the five contrasts; the pair-prompt rule recovered from the "
                              "vendored iteration-8 validation rows",
               "results": {k: v for k, v in res.items() if k != "modes"} | {"modes": {m: {kk: vv for kk, vv in res["modes"][m].items() if kk != "per_row"} for m in res["modes"]}},
               "edits": ["E-9.5-heldout", "E-T444", "E-9.7-circuit", "E-closing-handles"],
               "status": "DONE" if sides_ok else "MISMATCH"}
    save_stage("s0f", {"status": section["status"], "result": res, "metrics": metrics, "section": section,
                       "examples": {"heldout_per_side": ex}})
    return res


# ------------------------------------------------------------------------------------------------ 0g
def _shares_from_rows(unit: str) -> tuple[dict[str, list[float]], dict[str, float], list[float]]:
    """Per arm: per-prompt (m - m_I)/(m_B - m_I); ratio of means; per-prompt gaps m_I - m_B."""
    by_arm: dict[str, dict[str, float]] = {}
    mI: dict[str, float] = {}
    mB: dict[str, float] = {}
    with open(dep_path(A_BASE, f"results/b2_tf_{unit}.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            by_arm.setdefault(r["arm"], {})[r["pid"]] = r["m"]
            mI[r["pid"]] = r["m_I"]
            mB[r["pid"]] = r["m_B"]
    pids = sorted(mI)
    per, rom = {}, {}
    for arm, d in by_arm.items():
        if not all(p in d for p in pids):
            continue
        per[arm] = [(d[p] - mI[p]) / (mB[p] - mI[p]) for p in pids]
        rom[arm] = (np.mean([d[p] for p in pids]) - np.mean([mI[p] for p in pids])) / (
            np.mean([mB[p] for p in pids]) - np.mean([mI[p] for p in pids]))
    gaps = [mI[p] - mB[p] for p in pids]
    return per, rom, gaps


def run_0g() -> dict[str, Any]:
    rs = read_json(dep_path(A_BASE, "results/random_sets.json"))
    b2 = read_json(dep_path(A_BASE, "results/b2_summary.json"))
    unit_name = {"B3": "minimum spanning tree", "T10": "connected components"}
    out: dict[str, Any] = {}
    tab = []
    for unit in ("B3", "T10"):
        per, rom, gaps = _shares_from_rows(unit)
        u = b2["units"][unit]
        obs = u["arms"]["FSTACK"]["share"]
        out[unit] = {"fstack_share_recorded": obs, "fstack_share_recomputed": float(rom["FSTACK"]), "families": {}}
        for fam, setkey in (("R", "R"), ("Rpure", "Rpure"), ("Rscaled", "R")):
            sets = rs[unit][setkey]["sets"]
            shares = u[f"null_{fam}"]["shares"]
            # alignment by ids: recompute each set's share from the per-prompt rows of arm <fam><s>
            rec = [float(rom.get(f"{fam}{s}", np.nan)) for s in range(len(sets))]
            align_max = float(np.nanmax(np.abs(np.asarray(rec) - np.asarray(shares))))
            distinct = [len(set(s_)) for s_ in sets]
            mlp_rep = [len([x for x in s_ if x.startswith("mlp")]) != len({x for x in s_ if x.startswith("mlp")})
                       for s_ in sets]
            full = [i for i, n in enumerate(distinct) if n == len(sets[i])]
            sh_full = [shares[i] for i in full]
            N = len(sh_full)
            ge_all = sum(1 for x in shares if x >= obs)
            ge_full = sum(1 for x in sh_full if x >= obs)
            rec_f = {"n_sets": len(sets), "sets_with_repeated_mlp": int(sum(mlp_rep)),
                     "effective_size_counts": dict(Counter(distinct)), "n_ten_distinct": N,
                     "median_all": float(np.median(shares)), "p_all": (1 + ge_all) / (len(shares) + 1),
                     "recorded_median": u[f"null_{fam}"]["median"], "recorded_p": u[f"null_{fam}"]["empirical_p_upper"],
                     "restricted_median": float(np.median(sh_full)) if N else None,
                     "restricted_p": (1 + ge_full) / (N + 1), "restricted_floor": 1 / (N + 1),
                     "alignment_max_abs_diff": align_max, "aligned": align_max < 1e-9}
            out[unit]["families"][fam] = rec_f
            tab.append([unit_name[unit], fam, len(sets), int(sum(mlp_rep)),
                        "; ".join(f"{k} distinct: {v}" for k, v in sorted(Counter(distinct).items())), N,
                        r2(rec_f["median_all"]), f"{rec_f['p_all']:.3f}",
                        r2(rec_f["restricted_median"]) if N else "n/a (N = 0)", f"{rec_f['restricted_p']:.3f}",
                        f"{rec_f['restricted_floor']:.3f}", f"{align_max:.2e}"])
        # per-prompt shares: fork stack and five fork MLPs
        pp = {}
        for arm in ("FSTACK", "F_MLP"):
            s_ = np.asarray(per[arm])
            q1, q3 = np.quantile(s_, [0.25, 0.75])
            pp[arm] = {"mean_of_ratios": float(s_.mean()), "median": float(np.median(s_)), "iqr": [float(q1), float(q3)],
                       "min": float(s_.min()), "max": float(s_.max()), "share_negative": float(np.mean(s_ < 0)),
                       "ratio_of_means": float(rom[arm]), "recorded_share": u["arms"][arm]["share"],
                       "recorded_mean_of_ratios": u["arms"][arm]["share_mean_of_ratios"]}
        pp["n_prompts"] = len(gaps)
        pp["n_small_gap_lt_0.5"] = int(sum(1 for g in gaps if abs(g) < 0.5))
        pp["gaps"] = gaps
        out[unit]["per_prompt"] = pp
    with open(TABLES / "table441b_random_sets.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit", "family", "sets", "sets_with_repeated_mlp", "effective_sizes", "ten_distinct_sets",
                    "median_all", "p_all", "restricted_median", "restricted_p", "restricted_floor", "alignment_max_diff"])
        w.writerows(tab)
    with open(TABLES / "table441c_per_prompt_shares.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["unit", "arm", "ratio_of_means", "mean_of_ratios", "median", "iqr_lo", "iqr_hi", "min", "max",
                    "share_negative", "n_prompts", "n_abs_gap_lt_0.5"])
        for unit in ("B3", "T10"):
            for arm in ("FSTACK", "F_MLP"):
                p = out[unit]["per_prompt"][arm]
                w.writerow([unit_name[unit], arm, f"{p['ratio_of_means']:.4f}", f"{p['mean_of_ratios']:.4f}",
                            f"{p['median']:.4f}", f"{p['iqr'][0]:.4f}", f"{p['iqr'][1]:.4f}", f"{p['min']:.4f}",
                            f"{p['max']:.4f}", f"{p['share_negative']:.4f}", out[unit]["per_prompt"]["n_prompts"],
                            out[unit]["per_prompt"]["n_small_gap_lt_0.5"]])
    b3, t10 = out["B3"], out["T10"]
    metrics = {"mst_R_repeated_mlp": b3["families"]["R"]["sets_with_repeated_mlp"],
               "mst_Rpure_repeated_mlp": b3["families"]["Rpure"]["sets_with_repeated_mlp"],
               "cc_R_repeated_mlp": t10["families"]["R"]["sets_with_repeated_mlp"],
               "cc_Rpure_repeated_mlp": t10["families"]["Rpure"]["sets_with_repeated_mlp"],
               "mst_R_restricted_N": b3["families"]["R"]["n_ten_distinct"],
               "cc_R_restricted_N": t10["families"]["R"]["n_ten_distinct"],
               "mst_Rscaled_median": b3["families"]["Rscaled"]["median_all"], "mst_Rscaled_p": b3["families"]["Rscaled"]["p_all"],
               "cc_fstack_mean_of_ratios": t10["per_prompt"]["FSTACK"]["mean_of_ratios"],
               "cc_fmlp_mean_of_ratios": t10["per_prompt"]["F_MLP"]["mean_of_ratios"],
               "cc_fstack_ratio_of_means": t10["per_prompt"]["FSTACK"]["ratio_of_means"],
               "cc_share_negative_fstack": t10["per_prompt"]["FSTACK"]["share_negative"],
               "cc_n_small_gap": t10["per_prompt"]["n_small_gap_lt_0.5"],
               "all_aligned": float(all(f["aligned"] for u in out.values() for f in u["families"].values()))}
    ex = [{"input": f"random patching sets, {r[0]}, family {r[1]}",
           "output": f"{r[2]} sets; {r[3]} repeat an MLP; effective sizes {r[4]}; ten-distinct sets {r[5]}; "
                     f"median {r[6]} (p {r[7]}); restricted median {r[8]} (p {r[9]}, floor {r[10]})",
           "metadata_unit": r[0], "metadata_family": r[1], "eval_sets_with_repeated_mlp": float(r[3]),
           "eval_ten_distinct": float(r[5])} for r in tab]
    section = {"inputs": [ref(A_BASE, "results/random_sets.json"), ref(A_BASE, "results/b2_summary.json"),
                          ref(A_BASE, "results/b2_tf_B3.jsonl"), ref(A_BASE, "results/b2_tf_T10.jsonl"),
                          ref(A_BASE, "src/cmap9.py", "draw_random_sets")],
               "computation": "distinct components per set; sets repeating an MLP; null shares aligned to sets by "
                              "recomputing each set's ratio-of-means share from its own arm rows (R<s>, Rpure<s>, "
                              "Rscaled<s>; Rscaled reuses the R sets scaled to the fork stack's write norm); restricted "
                              "null over ten-distinct sets with (1 + #null >= obs)/(N + 1); per-prompt shares "
                              "(m - m_I)/(m_B - m_I)",
               "results": out, "edits": ["E-T441", "E-9.5-patching", "E-closing-handles"], "status": "DONE"}
    save_stage("s0g", {"status": "DONE", "result": out, "metrics": metrics, "section": section,
                       "examples": {"random_sets_effective": ex}})
    return out
