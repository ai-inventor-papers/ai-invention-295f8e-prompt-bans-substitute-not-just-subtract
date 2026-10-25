#!/usr/bin/env python3
"""Second, independent spot-check of the 0a/0b/0c/0f/0g/0h/0i headline numbers (standard library only).

Reads the raw dependency rows directly: data/samples_v9.jsonl (not the labelled_v9_<cell>.jsonl files that src/ and
audit/rederive.py read), data/manual_reads_v9.jsonl, results/retrace.jsonl, b3_heldout_rows.jsonl and b2_tf_T10.jsonl,
with class maps written out here from the record's definitions. It compares against the current run's stage metrics
(results/s0a.json ... s0i.json, named as eval_out.json's metrics_agg names them) or, given a path, against that
eval_out.json's metrics_agg. Imports nothing from src/, vendor/ or audit/rederive.py. Placebos: within-program swaps
of the lexical and mechanistic indicators must make the exact McNemar test stop rejecting and the pooled gap vanish.

    python3 -I audit/spotcheck.py [path/to/eval_out.json]     (also run as the stage `uv run eval.py spotcheck`)
"""

import itertools
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COARSE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID", "astar": "HEUR", "gbfs": "HEUR", "bibfs": "BIDIR",
          "biastar": "BIDIR", "idastar": "ID", "jps": "HEUR", "dijkstra_unit": "BFS"}
FINE = {"bfs": "BFS", "dfs": "DFS", "iddfs": "ID-depth", "astar": "HEUR-f", "gbfs": "HEUR-h", "bibfs": "BIDIR-BFS",
        "biastar": "BIDIR-heuristic", "idastar": "ID-f", "jps": "HEUR-jump", "dijkstra_unit": "BFS"}
FIVE = ["bfs", "dfs", "iddfs", "astar", "gbfs"]          # the five-name ban applied to every retraced configuration
UD_OK = {"dijkstra_unit", "idastar", "jps"}               # 0h sensitivity: these runtime labels count as compliant
STAGES = ("s0a", "s0b", "s0c", "s0f", "s0g", "s0h", "s0i")


def dep_root(art: str) -> Path:
    """AII_DEPS_ROOT/<id>, then the sibling folder <id>, then a DEP_<id>= line in the untracked .env."""
    cands = [Path(os.environ["AII_DEPS_ROOT"]) / art] if os.environ.get("AII_DEPS_ROOT") else []
    cands.append(ROOT.parent / art)
    env = ROOT / ".env"
    if env.exists():
        cands += [Path(l.split("=", 1)[1].strip()) for l in env.read_text().splitlines()
                  if l.startswith(f"DEP_{art}=")]
    for c in cands:
        if c.is_dir():
            return c
    raise SystemExit(f"dependency {art} not found (set AII_DEPS_ROOT)")


def jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def reading(rows: list, reads: dict, how: str, banned_all: list | None = None, completed_only: bool = True) -> dict:
    """lexical vs mechanistic compliance over the programs traceable under the given reading."""
    pairs = []
    for r in rows:
        # samples_v9 rows carry no has_code field: a program exists when its code text is non-empty
        if not r.get("has_code", bool(r.get("code"))) or (completed_only and r.get("truncated")):
            continue
        banned = banned_all or r["banned_set"]
        if how == "tracer_fine":
            if r.get("order_class") in (None, "UNTRACEABLE"):
                continue
            fb = {FINE[b] for b in banned} | ({"DFS-revisit"} if "dfs" in banned else set())
            ok = r.get("order_class_fine") not in fb
        else:
            lab = r.get("runtime_label")
            if lab in (None, "invalid"):
                continue
            if how == "runtime_fine":
                ok = FINE.get(lab, "OTHER") not in {FINE[b] for b in banned}
            elif how == "hand" and r["uid"] in reads:
                ok = reads[r["uid"]] != "UD"            # unit-weight Dijkstra = BFS order (banned); the rest: other
            elif how == "ud" and lab in UD_OK:
                ok = True
            else:
                ok = COARSE.get(lab, "OTHER") not in {COARSE[b] for b in banned}
        pairs.append((bool(r.get("lexical_L1")), ok, r.get("runtime_label")))
    n = len(pairs)
    k = sum(m for _, m, _ in pairs)
    b = sum(1 for x, m, _ in pairs if x and not m)
    c = sum(1 for x, m, _ in pairs if m and not x)
    return {"k": k, "n": n, "rate": k / n, "gap": sum(x for x, _, _ in pairs) / n - k / n, "b": b, "c": c,
            "mcnemar_p": mcnemar_exact(b, c), "pairs": pairs}


def swapped_gap(pairs: list, rng: random.Random) -> float:
    """gap after swapping each program's lexical and mechanistic indicator with probability 1/2"""
    sw = [(m, x) if rng.random() < 0.5 else (x, m) for x, m, _ in pairs]
    return sum(x for x, _ in sw) / len(sw) - sum(m for _, m in sw) / len(sw)


def main() -> None:
    if len(sys.argv) > 1:
        target = sys.argv[1]
        agg = json.loads(Path(target).read_text())["metrics_agg"]
    else:
        target = "results/" + ", ".join(f"{s}.json" for s in STAGES) + " (metrics)"
        agg = {f"{st}_{k}": v for st in STAGES
               for k, v in json.loads((ROOT / "results" / f"{st}.json").read_text())["metrics"].items()}
    d1, d3 = dep_root("art_8nXdw3_lDAll"), dep_root("art_cDba8_DycUJd")
    rows = jsonl(d1 / "data/samples_v9.jsonl")
    reads = {r["uid"]: r["family"] for r in jsonl(d1 / "data/manual_reads_v9.jsonl")}
    cell = lambda c: [r for r in rows if r["cell"] == c]  # noqa: E731
    got = {}
    # 0a: hand reads substituted; the fine tracer on the k = 5 cells
    for tag, c in (("q32_k5", "A_k5"), ("q32_ho", "A_k5_ho"), ("q14_k5", "E_k5"), ("q14_ho", "E_k5_ho")):
        h = reading(cell(c), reads, "hand")
        got[f"s0a_{tag}_hand_rate"], got[f"s0a_{tag}_hand_gap"] = h["rate"], h["gap"]
    h5 = reading(cell("A_k5"), reads, "hand")
    got["s0a_q32_k5_hand_k"], got["s0a_q32_k5_hand_n"] = h5["k"], h5["n"]
    got["s0a_q14_ho_tracer_fine_gap"] = reading(cell("E_k5_ho"), reads, "tracer_fine")["gap"]
    got["s0a_q32_k5_tracer_fine_gap"] = reading(cell("A_k5"), reads, "tracer_fine")["gap"]
    # 0b: runtime fine classes; greedy best-first among the k = 4 coarse violations
    f4 = reading(cell("A_k4"), reads, "runtime_fine")
    got["s0b_q32_k4_runtime_fine_k"], got["s0b_q32_k4_runtime_fine_n"] = f4["k"], f4["n"]
    got["s0b_q32_k5_runtime_fine"] = reading(cell("A_k5"), reads, "runtime_fine")["rate"]
    c4 = reading(cell("A_k4"), reads, "runtime")["pairs"]
    got["s0b_q32_k4_coarse_violations"] = sum(1 for _, m, _ in c4 if not m)
    got["s0b_q32_k4_coarse_violations_greedy"] = sum(1 for _, m, lab in c4 if not m and lab == "gbfs")
    # 0c: described against named
    desc, named = reading(cell("C_desc"), reads, "runtime"), reading(cell("A_k5"), reads, "runtime")
    got["s0c_runtime_diff"] = desc["rate"] - named["rate"]
    got["s0c_per_cell_argued_diff"] = desc["rate"] - h5["rate"]
    # 0f: held-out circuit per side
    held = jsonl(d3 / "results/b3_heldout_rows.jsonl")
    raw = {}                                               # extra, not compared
    for mode in ("ablate", "steer"):
        key = f"aligned|{mode}|mlp|L0|H-1|COND"
        # the record's per-row effect (b3_9.py lines 236-241): node value minus the mean of the row's 50 random sets
        d = {h["vid"]: h["res"][f"{key}|node"] - sum(h["res"][f"{key}|r{j}"] for j in range(50)) / 50 for h in held}
        forced = [v for vid, v in d.items() if vid.endswith("|forced")]
        padded = [v for vid, v in d.items() if vid.endswith("|pad")]
        got[f"s0f_{mode}_forced"], got[f"s0f_{mode}_padded"] = sum(forced) / 5, sum(padded) / 5
        got[f"s0f_{mode}_all"] = (sum(forced) + sum(padded)) / 10
        raw[f"{mode}_node_raw_forced"] = sum(h["res"][f"{key}|node"] for h in held if h["vid"].endswith("|forced")) / 5
        if mode == "ablate":                               # five contrasts: the mean of each pair's two rows
            con = [(d[f"F{i}|forced"] + d[f"F{i}|forced|pad"]) / 2 for i in range(11, 16)]
            pats = [sum(s * x for s, x in zip(signs, con)) for signs in itertools.product((1, -1), repeat=5)]
            got["s0f_p5_one_sided"] = sum(p >= sum(con) - 1e-12 for p in pats) / 32
            got["s0f_p5_two_sided"] = sum(abs(p) >= abs(sum(con)) - 1e-12 for p in pats) / 32
    got["s0f_empty_F11_F15"] = sum(h["n_empty_edits"] for h in held if h["vid"][:3] in ("F11", "F15"))
    got["s0f_jobs_F11_F15"] = sum(h["n_jobs"] for h in held if h["vid"][:3] in ("F11", "F15"))
    # 0g: per-prompt shares (m - m_I)/(m_B - m_I) on connected components against the ratio of means
    m_arm, m_i, m_b = {}, {}, {}
    for r in jsonl(d3 / "results/b2_tf_T10.jsonl"):
        m_arm.setdefault(r["arm"], {})[r["pid"]] = r["m"]
        m_i[r["pid"]], m_b[r["pid"]] = r["m_I"], r["m_B"]
    pids = sorted(m_i)
    share = {a: [(m_arm[a][p] - m_i[p]) / (m_b[p] - m_i[p]) for p in pids] for a in ("FSTACK", "F_MLP")}
    got["s0g_cc_fstack_mean_of_ratios"] = statistics.fmean(share["FSTACK"])
    got["s0g_cc_fmlp_mean_of_ratios"] = statistics.fmean(share["F_MLP"])
    got["s0g_cc_fstack_ratio_of_means"] = (sum(m_arm["FSTACK"][p] - m_i[p] for p in pids)
                                           / sum(m_b[p] - m_i[p] for p in pids))
    got["s0g_cc_share_negative_fstack"] = sum(s < 0 for s in share["FSTACK"]) / len(pids)
    got["s0g_cc_n_small_gap"] = sum(abs(m_i[p] - m_b[p]) < 0.5 for p in pids)
    # 0h: unit-weight Dijkstra, IDA* and JPS compliant over the retraced programs (equal-weight mean of the
    # per-configuration paired gaps), the covert programs, and the exhaustion cells
    ret = jsonl(d1 / "results/retrace.jsonl")
    cfgs = sorted({r["config"] for r in ret}, key=lambda c: int(c[1:]))
    by_cfg = {c: [r for r in ret if r["config"] == c] for c in cfgs}
    ud = {c: reading(rs, reads, "ud", FIVE, completed_only=False) for c, rs in by_cfg.items()}
    rt = {c: reading(rs, reads, "runtime", FIVE, completed_only=False) for c, rs in by_cfg.items()}
    got["s0h_pooled_gap_ud_compliant"] = statistics.fmean(v["gap"] for v in ud.values())
    got["s0h_pooled_gap_runtime_recomputed"] = statistics.fmean(v["gap"] for v in rt.values())
    got["s0h_programs"] = sum(v["n"] for v in rt.values())
    covert = [lab for v in rt.values() for x, m, lab in v["pairs"] if x and not m]
    got["s0h_covert"], got["s0h_covert_bfs_or_dfs"] = len(covert), sum(lab in ("bfs", "dfs") for lab in covert)
    for tag, c in (("q32_k4", "A_k4"), ("q32_k5", "A_k5"), ("q14_k5", "E_k5")):
        got[f"s0h_{tag}_ud"] = reading(cell(c), reads, "ud")["rate"]
    # 0i: rotated and described samples planned (six rotated five-name sets and the described ban, 50 each) and present
    rot = sorted({r["cell"] for r in rows if r["cell"][:3] in ("B_R", "D_R")})
    got["s0i_planned_samples"] = 50 * (len(rot) + 1)
    got["s0i_present_samples"] = sum(1 for r in rows if r["cell"] in rot or r["cell"] == "C_desc")
    got["s0i_lost_samples"] = got["s0i_planned_samples"] - got["s0i_present_samples"]
    checks = [{"metric": k, "spotcheck": v, "pipeline": agg.get(k),
               "match": agg.get(k) is not None and abs(v - agg[k]) <= 1e-9} for k, v in got.items()]
    # placebos: swapping each program's lexical and mechanistic indicator at random makes b and c exchangeable,
    # so the McNemar test must stop rejecting and the pooled gap must fall to about 0
    rng = random.Random(20261025)
    placebo_p = []
    for _ in range(200):
        sw = [(m, x) if rng.random() < 0.5 else (x, m) for x, m, _ in h5["pairs"]]
        placebo_p.append(mcnemar_exact(sum(1 for x, m in sw if x and not m), sum(1 for x, m in sw if m and not x)))
    pooled_null = [statistics.fmean(swapped_gap(v["pairs"], rng) for v in ud.values()) for _ in range(200)]
    out = {"compared_against": target, "n_checks": len(checks), "n_mismatches": sum(not c["match"] for c in checks),
           "checks": checks, "heldout_raw_node_means_not_compared": raw,
           "placebo": {"test": "exact McNemar, Qwen3-32B k = 5 hand-read substituted",
                       "observed_p": h5["mcnemar_p"], "draws": 200,
                       "share_placebo_p_below_0.05": sum(p < 0.05 for p in placebo_p) / 200,
                       "median_placebo_p": sorted(placebo_p)[100]},
           "placebo_pooled_gap": {"test": "pooled UD-compliant rename gap over the ten retraced configurations",
                                  "observed": got["s0h_pooled_gap_ud_compliant"], "draws": 200,
                                  "mean_placebo": statistics.fmean(pooled_null),
                                  "max_abs_placebo": max(abs(g) for g in pooled_null),
                                  "share_placebo_ge_observed": sum(g >= got["s0h_pooled_gap_ud_compliant"]
                                                                   for g in pooled_null) / 200}}
    (ROOT / "audit/spotcheck.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "checks"}, indent=1))
    for c in checks:
        print(f"{'OK ' if c['match'] else 'BAD'} {c['metric']}: spotcheck {c['spotcheck']} | pipeline {c['pipeline']}")


if __name__ == "__main__":
    main()
