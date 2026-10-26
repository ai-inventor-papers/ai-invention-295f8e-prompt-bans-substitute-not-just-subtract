"""Re-derive the numbers this review cites from the iteration-7 artifacts' own files.

Usage: python3 recompute_checks.py
The artifact folders are read from $AII_GEN_ART, default ../../gen_art (the run layout:
<run>/3_invention_loop/iter_7/review_report/review_report -> <run>/3_invention_loop/iter_7/gen_art).
Standard library only.
"""
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(os.environ.get("AII_GEN_ART", Path(__file__).resolve().parent / "..")).resolve()
DAS = ROOT / "experiment-33/src"   # art_veI9l_Rb9wDY
FORK = ROOT / "experiment-34/src"  # art_pHL7LWNhpcCS
UNIT = ROOT / "experiment-36/src"  # art_8O5eaNc5gxJs
SEARCH = ROOT / "experiment-37/src"  # art_VhaHGe7SxV95
GEMMA = ROOT / "experiment-38/src"  # art_HY7uYZz-OjRW


def load(p):
    return json.loads(Path(p).read_text())


def spearman(x, y):
    def rank(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den


def main():
    # 1. DAS: per-source recovery and the counting-sort labelling contradiction
    p1 = load(DAS / "results/p1.json")
    for task, v in p1["tasks"].items():
        for src, s in v["per_source"].items():
            per_k = {k: (d["count"], None if d["recovery"] is None else round(d["recovery"], 2))
                     for k, d in s["das"].items()}
            print(f"[DAS] {task} {src}: base {s['base_count']} full {s['full_count']} DAS(count,recovery) {per_k}")
        print(f"[DAS] {task} random-init control: {v.get('random_init_control', {}).get('present')}")
    rows = [json.loads(l) for l in (DAS / "data/labels.jsonl").read_text().splitlines()]
    c = Counter((r["arm"], r["label"]) for r in rows if r["task"] == "T03" and "counting" in r["arm"])
    print("[DAS] T03 counting-sort arms:", dict(c))
    nov = load(DAS / "results/novelty_audit.json")
    full = [r for r in nov["rows"] if r["arm"] == "FULL_F_counting_sort"]
    named = Counter(((r.get("judge_a") or {}).get("catalogue_name") or (r.get("judge_b") or {}).get("catalogue_name"), r["class"]) for r in full)
    print("[DAS] FULL_F_counting_sort 'other' programs, judge class/name:", dict(named))
    # pooled T03 rank-1 recovery with and without the 29 counted as counting sort
    print("[DAS] T03 pooled rank-1 recovery as reported: (21+30+30)/(22+29+0) =", round(81 / 51, 2),
          "; with the 29 counted:", round(81 / 80, 2))

    # 2. Fork margin and axis Spearman
    f = load(FORK / "results/f_analysis.json")
    for t in ("T10", "T2"):
        cells = f["cells"][t]
        y = [r["y"] for r in cells]
        print(f"[FORK] {t}: rho(m,y)={spearman([r['m'] for r in cells], y):.3f} "
              f"rho(llr48,y)={spearman([r['llr48'] for r in cells], y):.3f} rho(b,y)={spearman([r['b'] for r in cells], y):.3f}")

    # 3. Dose-unit 2x2 and E3 replication
    s1 = load(UNIT / "results/s1_2x2.json")
    for k in ("T10|a2|Y", "T2|a2|Y"):
        t = s1["tables"][k]
        print(f"[UNIT] {k}: shares {t['shares']} unit {t['RD_unit']} {t['RD_unit_ci95']} seed {t['RD_seed']} {t['RD_seed_ci95']}")
    e3 = load(UNIT / "results/e3_replicate.json")["T10_fresh_k10_19"]["2x2|Y"]
    print(f"[UNIT] E3 fresh slots: shares {e3['shares']} unit {e3['RD_unit']} seed {e3['RD_seed']} {e3['RD_seed_ci95']}")

    # 4. Search: level-b programs and clusters per arm
    pc = load(SEARCH / "results/program_classes.json")
    progs, clusters = Counter(), defaultdict(set)
    for k, v in pc.items():
        if v.get("is_first_of_distinct") and v["final_class"] in ("KNOWN OUTSIDE CATALOGUE", "NOVEL ALGORITHM"):
            key = tuple(k.split("|")[:2])
            progs[key] += 1
            clusters[key].add(v["merged_cluster_id"])
    for key in sorted(progs):
        print(f"[SEARCH] level b {key}: {progs[key]} distinct programs in {len(clusters[key])} clusters")

    # 5. Gemma dose sweep: prefilled DAS cells vs the unprefilled instruction cell; TF prediction gaps
    dose = load(GEMMA / "results/g2_dose.json")["cells"]
    for k in ("twin", "DAS|bfs|1.0", "forced_bfs_F5", "DAS-L|bfs|1.0"):
        d = dose[k]
        print(f"[GEMMA] {k}: attempted BFS {d['attempted_target']} correct {d['correct_target']} pass {d['pass_rate']}")
    gaps = [abs(v["labels"].get("bfs", 0) / v["n"] - v["tf_pred_attempted_bfs"])
            for v in dose.values() if v.get("tf_pred_attempted_bfs") is not None]
    print(f"[GEMMA] TF prediction gaps: n {len(gaps)} max {max(gaps):.3f} mean {sum(gaps) / len(gaps):.3f}")
    src = (GEMMA / "src/g2.py").read_text()
    print("[GEMMA] forced-BFS ceiling sampled from index 0 (no c* prefill):",
          'run.run_cell(pfz["ids"], [], rows' in src, "; DAS cells prefilled with c*:", 'ids = p["ids"] + cs' in src)
    dec = load(GEMMA / "results/g2_decisions.json")
    nv = dec["natural_variance"]["1"]
    print(f"[GEMMA] L17 rank-1 natural-variance share {nv['share']:.5f} vs random p95 {nv['random_p95']:.5f}; "
          f"recovery by rank {[round(dec['per_k'][k]['das_recovery_seed_median'], 2) for k in ('1', '2', '4', '8')]}")
    g3 = load(GEMMA / "results/g3_sweep.json")["cells"]
    errs = [g3[f"T{t}|topp1"]["abs_err_primary"] for t in ("0.3", "0.7", "1.0", "1.3")]
    print(f"[GEMMA] temperature MAE {sum(errs) / len(errs):.4f}")


if __name__ == "__main__":
    main()
