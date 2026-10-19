"""Independent re-derivation of the headline numbers (audit; deliberately does NOT import src/).

Reads the per-sample rows (runs/labelled_*.jsonl), the committed forecast and its hash log directly, and recomputes:
  1. correct-label counts, pass counts and Hill_cc per vLLM arm (Counter + math, not stats_utils)
  2. D_weights = Hill_cc(instruct_chat) - Hill_cc(base_chat), modal-share gap, pre-registered verdict logic
  3. a cluster-bootstrap CI for D_weights (pandas + python `random`, own loop) and a PLACEBO run on shuffled arm labels
  4. the instruct_chat vs base_chat label-distribution test (scipy chi2_contingency statistic, own permutation loop),
     and the same test on 200 shuffled-arm placebos (must reject at ~5 %, not systematically)
  5. regex-only re-labelling of the instruct chat programs (BFS / Dijkstra claims)
  6. PREDICT: sha256 vs hash log, top-1 hits and log scores from raw C1 rows
  7. steering and ban counts straight from the rows
Compares each value with results/analysis.json and writes results/audit_rederive.json.
  .venv/bin/python audit/rederive.py
"""
import hashlib
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

WS = Path(__file__).resolve().parent.parent
CAT = {"t1": ["bfs", "dfs", "bidir_bfs", "iddfs", "astar_greedy", "dijkstra_unit"],
       "t2": ["dijkstra", "bellman_ford_spfa", "bidir_dijkstra", "floyd_warshall", "dial"]}
FILES = {"base_tf": "labelled_base_tf__baseline.jsonl", "base_chat": "labelled_base_chat__baseline.jsonl",
         "instruct_chat": "labelled_instruct_chat__baseline.jsonl", "instruct_tf": "labelled_instruct_tf__baseline.jsonl",
         "instruct_chat_ban": "labelled_instruct_chat__ban.jsonl"}


def rows(fname):
    return [json.loads(l) for l in (WS / "runs" / fname).read_text().splitlines() if l.strip()]


def canon(lab, task):
    return lab if lab in CAT[task] else "other"


def hill_from_labels(labels):
    if not labels:
        return float("nan")
    n = len(labels)
    return math.exp(-sum((c / n) * math.log(c / n) for c in Counter(labels).values()))


def frame(arm, task):
    df = pd.DataFrame([r for r in rows(FILES[arm]) if r["task"] == task])
    df["ok"] = df["passed"].astype(bool) & df["parse_ok"].astype(bool) & df["label"].notna()
    df["lab"] = [canon(l, task) if isinstance(l, str) else None for l in df["label"]]
    return df[["paraphrase_id", "ok", "lab"]]


def boot_diff(dfa, dfb, B=2000, seed=99):
    """H(a) - H(b), paraphrase ids drawn once per replicate and shared by both arms; resample rows within ids."""
    rnd = random.Random(seed)
    ga = {p: g for p, g in dfa.groupby("paraphrase_id")}
    gb = {p: g for p, g in dfb.groupby("paraphrase_id")}
    pids = sorted(set(ga) | set(gb))
    out = []
    for _ in range(B):
        pick = [rnd.choice(pids) for _ in pids]
        la, lb = [], []
        for p in pick:
            for g, acc in ((ga.get(p), la), (gb.get(p), lb)):
                if g is None:
                    continue
                idx = [rnd.randrange(len(g)) for _ in range(len(g))]
                sub = g.iloc[idx]
                acc.extend(sub.loc[sub["ok"], "lab"].tolist())
        if len(la) < 5 or len(lb) < 5:
            continue
        out.append(hill_from_labels(la) - hill_from_labels(lb))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)


def perm_test(la, lb, n_perm=4000, seed=5):
    cats = sorted(set(la) | set(lb))

    def stat(x, y):
        tab = np.array([[x.count(c) for c in cats], [y.count(c) for c in cats]])
        tab = tab[:, tab.sum(0) > 0]
        if tab.shape[1] < 2:
            return 0.0
        return float(chi2_contingency(tab, correction=False)[0])
    obs = stat(la, lb)
    pool = la + lb
    rnd = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        rnd.shuffle(pool)
        if stat(pool[:len(la)], pool[len(la):]) >= obs - 1e-12:
            ge += 1
    return obs, (ge + 1) / (n_perm + 1)


def main():
    an = json.loads((WS / "results" / "analysis.json").read_text())
    rep = {"per_arm": {}, "collapse": {}, "placebo": {}, "regex_relabel": {}, "predict": {}, "steering": {}, "ban": {}}
    mismatches = []

    def check(name, mine, theirs, tol=1e-6):
        ok = (mine is None and theirs is None) or (mine is not None and theirs is not None and abs(mine - theirs) <= tol)
        if not ok:
            mismatches.append({"what": name, "rederived": mine, "pipeline": theirs})
        return ok

    # 1-2. per-arm Hill_cc, counts, verdict ingredients
    for task in ("t1", "t2"):
        F = {a: frame(a, task) for a in ("base_tf", "base_chat", "instruct_chat", "instruct_tf")}
        for a, df in F.items():
            labs = df.loc[df["ok"], "lab"].tolist()
            h = hill_from_labels(labs)
            rep["per_arm"][f"{a}|{task}"] = {"N": len(df), "n_correct": len(labs), "counts": dict(Counter(labs)), "hill_cc": h}
            check(f"hill_cc {a}|{task}", h, an["arms"][f"{a}|{task}"]["hill_cc"])
            check(f"n_correct {a}|{task}", len(labs), an["arms"][f"{a}|{task}"]["n_correct_labelled"])
        li = F["instruct_chat"].loc[F["instruct_chat"]["ok"], "lab"].tolist()
        lb = F["base_chat"].loc[F["base_chat"]["ok"], "lab"].tolist()
        lt = F["base_tf"].loc[F["base_tf"]["ok"], "lab"].tolist()
        d_w = hill_from_labels(li) - hill_from_labels(lb)
        mode_i = Counter(li).most_common(1)[0][0]
        gap = 100 * (Counter(li)[mode_i] / len(li) - Counter(lb)[mode_i] / len(lb))
        lo, hi, nb = boot_diff(F["base_chat"], F["instruct_chat"])
        weights_bar = (-d_w >= 0.5) and lo > 0 and gap >= 15
        mode_tf = Counter(lt).most_common(1)[0][0]
        lo_t, hi_t, _ = boot_diff(F["base_tf"], F["instruct_chat"], seed=7)
        already = (mode_tf == mode_i) and hi_t < 0.5
        verdict = "INSTALLED_BY_POST_TRAINING" if weights_bar else ("ALREADY_IN_BASE" if already else "MIXED_or_FORMAT")
        chi, p = perm_test(li, lb)
        rep["collapse"][task] = {"D_weights": d_w, "H_base_chat_minus_instruct_CI": [lo, hi], "n_boot": nb,
                                 "modal_share_gap_pp": gap, "verdict_rederived": verdict,
                                 "verdict_pipeline": an["collapse_screen"][task]["verdict_cc"]["verdict"],
                                 "perm_chi2": chi, "perm_p": p}
        check(f"D_weights {task}", d_w, an["collapse_screen"][task]["D_weights_cc"]["est"])
        check(f"modal gap {task}", gap, an["collapse_screen"][task]["verdict_cc"]["modal_share_gap_pp_weights"], 1e-6)
        # 3-4. PLACEBO: shuffle arm membership of the pooled base_chat + instruct_chat rows (paraphrase ids kept)
        pooled = pd.concat([F["base_chat"].assign(arm="b"), F["instruct_chat"].assign(arm="i")], ignore_index=True)
        rnd = random.Random(2024)
        ps, cis_excl0 = [], 0
        for k in range(200):
            arms = pooled["arm"].tolist()
            rnd.shuffle(arms)
            sh = pooled.assign(arm=arms)
            xa = sh[(sh["arm"] == "i") & sh["ok"]]["lab"].tolist()
            xb = sh[(sh["arm"] == "b") & sh["ok"]]["lab"].tolist()
            ps.append(perm_test(xa, xb, n_perm=300, seed=k)[1])
            if k < 20:
                l2, h2, _ = boot_diff(sh[sh["arm"] == "b"], sh[sh["arm"] == "i"], B=300, seed=k)
                cis_excl0 += (l2 > 0 or h2 < 0)
        rep["placebo"][task] = {"perm_test_reject_rate_at_0.05_over_200_shuffles": float(np.mean(np.array(ps) < 0.05)),
                                "bootstrap_CI_excludes_0_in_20_shuffles": cis_excl0}
    # 5. regex-only relabel of instruct chat programs
    ic = rows(FILES["instruct_chat"])
    for task, pat, name in (("t1", r"popleft\(|\.pop\(0\)|Queue\(", "BFS-like (FIFO queue)"),
                            ("t2", r"heapq|heappush|PriorityQueue", "Dijkstra-like (heap)")):
        rr = [r for r in ic if r["task"] == task and r.get("code")]
        rep["regex_relabel"][task] = {"pattern": name, "matches": sum(bool(re.search(pat, r["code"])) for r in rr),
                                      "n": len(rr), "pipeline_modal_count": Counter(r["label"] for r in rr).most_common(1)[0]}
    # 6. PREDICT
    pf = WS / "predictions" / "predict_modal_ban.json"
    sha = hashlib.sha256(pf.read_bytes()).hexdigest()
    logged = [json.loads(l)["sha256"] for l in (WS / "predictions" / "hash_log.txt").read_text().splitlines() if l.strip()]
    pred = json.loads(pf.read_text())
    c1 = rows(FILES["instruct_chat_ban"])
    rep["predict"]["sha256_matches_hash_log"] = sha in logged
    for task, banned in (("t1", "bfs"), ("t2", "dijkstra")):
        ev = pred["events"][task]
        S = ev["survivors"]
        comp = [canon(r["label"], task) for r in c1 if r["task"] == task and r.get("passed") and r.get("label")
                and canon(r["label"], task) != banned]
        comp = [c if c in S else "other" for c in comp]
        realised = Counter(comp).most_common(2)
        lead = (realised[0][1] - (realised[1][1] if len(realised) > 1 else 0)) / len(comp)
        mode = realised[0][0] if lead >= 0.15 else "no clear mode"
        out = {}
        for name, pr in ev["predictors"].items():
            ls = sum(math.log(pr["p"][c]) for c in comp) / len(comp)
            out[name] = {"top1": pr["top1"], "hit": pr["top1"] == mode, "log_score": ls}
            prow = [x for x in an["rows"]["PREDICT"] if x["task"] == task and x["predictor"] == name][0]
            check(f"log score {task} {name}", ls, prow["log_score"], 1e-9)
        rep["predict"][task] = {"n_compliant": len(comp), "realised_mode": mode, "predictors": out, "primary": ev["primary"]}
    # 7. steering + ban counts
    for f in sorted((WS / "runs").glob("labelled_steer__*.jsonl")):
        rr = rows(f.name)
        for task in ("t1", "t2"):
            x = [r for r in rr if r["task"] == task]
            if x:
                rep["steering"][f"{x[0]['arm']}|{task}"] = {
                    "N": len(x), "parse": sum(bool(r["parse_ok"]) for r in x), "pass": sum(bool(r["passed"]) for r in x),
                    "correct_labels": dict(Counter(canon(r["label"], task) for r in x if r["passed"] and r.get("label")))}
    for task in ("t1", "t2"):
        x = [r for r in c1 if r["task"] == task]
        rep["ban"][task] = {"N": len(x), "pass": sum(bool(r["passed"]) for r in x),
                            "correct_labels": dict(Counter(canon(r["label"], task) for r in x if r["passed"]))}
    rep["mismatches_vs_pipeline"] = mismatches
    (WS / "results" / "audit_rederive.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"collapse": rep["collapse"], "placebo": rep["placebo"], "regex_relabel": rep["regex_relabel"],
                      "predict": {k: v for k, v in rep["predict"].items()}, "mismatches": mismatches}, indent=1, default=str))


if __name__ == "__main__":
    main()
