#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers (audit; imports nothing from analysis/ or labeller/).

Reads the raw files directly -- raw model text (data/raw_preban.jsonl), per-sample label rows (data/samples.jsonl),
the gold set, commitments.log and the prediction files -- and recomputes every headline number through separate
code (pandas + a fresh ranking parser and Borda count). The log-score contest and the T9 family comparison are also
re-run on placebo input (uniform-random labels; a deliberately wrong association winner) to confirm they fail there.
Writes results/independent_rederivation.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODES = {"t1": ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"],
         "t2": ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]}


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def close(a, b, tol=0.005) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def main() -> None:
    S = pd.DataFrame(jl(ROOT / "data" / "samples.jsonl"))
    mo = json.loads((ROOT / "method_out.json").read_text())["metadata"]
    checks: list[dict] = []

    def chk(name, reported, recomputed, tol=0.005):
        ok = (reported == recomputed) if not isinstance(recomputed, float) else close(reported, recomputed, tol)
        checks.append({"number": name, "reported": reported, "recomputed": recomputed, "match": bool(ok)})

    code = S[S["label"] != "no_code"]
    # H1 baselines
    for t, m in (("t1", "bfs"), ("t2", "dijkstra")):
        b = code[(code.task == t) & (code.condition == "baseline")]
        chk(f"{t} baseline share of {m} (N={len(b)})", 1.0, float((b.label == m).mean()))
    # H2 modal bans: compliance and compliant landing
    for t, x, sub in (("t1", "bfs", "dfs"), ("t2", "dijkstra", "bf_spfa")):
        b = code[(code.task == t) & (code.condition == f"ban:{x}")]
        comp = 1 - (b.label == x).mean()
        compliant = b[(b.passed) & (b.label != x)]
        ev = next(e for e in mo["event_table"] if e["event_id"] == f"{t}|ban:{x}")
        chk(f"{t} ban:{x} compliance", ev["compliance"], float(comp))
        chk(f"{t} ban:{x} n_compliant", ev["n_compliant"], int(len(compliant)))
        chk(f"{t} ban:{x} share of {sub} among compliant", 1.0, float((compliant.label == sub).mean()))
    # H6 succession step 2 compliance
    for t in ("t1", "t2"):
        b = code[(code.task == t) & (code.condition == "succession:2")]
        banned = b.banned_set.iloc[0]
        ev = next(e for e in mo["event_table"] if e["event_id"] == f"{t}|succession:2")
        chk(f"{t} succession:2 compliance (banned {banned})", ev["compliance"], float(1 - b.label.isin(banned).mean()))

    # H3 Borda maps re-parsed from RAW model text with a fresh parser
    conds = json.loads((ROOT / "prompts" / "conditions.json").read_text())
    raw = jl(ROOT / "data" / "raw_preban.jsonl")
    borda: dict = {}
    for t in ("t1", "t2"):
        K = len(MODES[t])
        for x in MODES[t]:
            pts = Counter()
            firsts = Counter()
            n = 0
            for r in raw:
                if r["kind"] != "rank" or r["task"] != t or r["mode_X"] != x:
                    continue
                order = conds["tasks"][t]["elicit_rank"][x][r["paraphrase_id"]]["option_order"]
                letters = re.findall(r'"([A-Z])"', r["text"].split("]")[0])
                if sorted(letters) != [chr(65 + i) for i in range(K - 1)]:
                    continue
                n += 1
                for pos, L in enumerate(letters):
                    pts[order[ord(L) - 65]] += K - 2 - pos
                firsts[order[ord(letters[0]) - 65]] += 1
            others = [m for m in MODES[t] if m != x]
            A = {y: (pts[y] + 1) / sum(pts[z] + 1 for z in others) for y in others}
            win = sorted(others, key=lambda y: (-pts[y], -firsts[y], y))[0]
            borda[(t, x)] = {"A": A, "winner": win, "clarity": firsts[win] / n, "n": n}
    chk("t1 X=bfs Borda winner", mo["association_maps"]["t1"]["bfs"]["borda_winner"], borda[("t1", "bfs")]["winner"])
    chk("t1 X=bfs clarity", mo["association_maps"]["t1"]["bfs"]["clarity"], borda[("t1", "bfs")]["clarity"])
    chk("t1 X=bfs: DFS ranked last by Borda", True,
        min(borda[("t1", "bfs")]["A"], key=borda[("t1", "bfs")]["A"].get) == "dfs")
    chk("t2 X=dijkstra Borda winner", mo["association_maps"]["t2"]["dijkstra"]["borda_winner"],
        borda[("t2", "dijkstra")]["winner"])
    # free text, independent substring matcher on raw text
    ft = [r["text"].lower() for r in raw if r["kind"] == "free" and r["task"] == "t1" and r["mode_X"] == "bfs"]
    chk("t1 free text X=bfs answers naming DFS", 19, sum(1 for s in ft if "depth-first" in s or "dfs" in s))

    # H4 log scores from the independently rebuilt maps, composed by hand
    def composed(p: dict, surv: list) -> dict:
        tot = sum(p[y] for y in surv)
        q = {y: 0.98 * (0.95 * p[y] / tot + 0.05 / len(surv)) for y in surv}
        q["other"] = 0.02
        return q

    diffs, events = [], {}
    for t, x in (("t1", "bfs"), ("t2", "dijkstra")):
        surv = [m for m in MODES[t] if m != x]
        b = code[(code.task == t) & (code.condition == f"ban:{x}") & code.passed & (code.label != x)]
        labs = [l if l in surv else "other" for l in b.label]
        qa = composed(borda[(t, x)]["A"], surv)
        qf = composed({y: 1.0 for y in surv}, surv)  # baseline gives zero mass to every survivor -> uniform
        froz = json.loads((ROOT / "predictions" / f"{t}_single_bans.json").read_text())["events"][f"ban:{x}"]
        chk(f"{t} frozen composed assoc q equals rebuilt q (max abs diff)", 0.0,
            float(max(abs(froz["composed"]["assoc"][y] - qa[y]) for y in qa)), tol=1e-9)
        la = float(np.mean([math.log(qa[y]) for y in labs]))
        lf = float(np.mean([math.log(qf[y]) for y in labs]))
        rep = next(e for e in mo["contest"]["events"] if e["event_id"] == f"{t}|ban:{x}")["per_predictor"]
        chk(f"{t} ban:{x} assoc log score", rep["assoc"]["log_score"], la)
        chk(f"{t} ban:{x} freq log score", rep["freq"]["log_score"], lf)
        diffs.append(la - lf)
        events[(t, x)] = (surv, labs, qa, qf)
    pooled = mo["contest"]["strata"]["all_informative"]["pooled_assoc_minus_freq"]
    chk("mean paired log-score difference (assoc - freq)", pooled["mean_paired_diff"], float(np.mean(diffs)))
    chk("association wins k of n", f"{pooled['assoc_wins']}/{pooled['assoc_wins_of']}",
        f"{sum(d > 0 for d in diffs)}/{len(diffs)}")

    # H7 mention effects (pp) from per-sample rows
    for t, x, rep in (("t1", "dfs", 100.0), ("t1", "iddfs", 72.0), ("t1", "astar_gbfs", 56.0), ("t2", "bf_spfa", 100.0),
                      ("t2", "floyd", 86.0), ("t1", "dijkstra", 0.0), ("t2", "dial", 0.0), ("t2", "bidijkstra", 0.0)):
        m = code[(code.task == t) & (code.condition == f"mention:{x}")]
        b = code[(code.task == t) & (code.condition == "baseline")]
        chk(f"{t} mention:{x} effect (pp)", rep, float(100 * ((m.label == x).mean() - (b.label == x).mean())), tol=0.5)

    # H8 gate metrics with a crosstab-based kappa
    g = pd.DataFrame(jl(ROOT / "labeller" / "gold_set.jsonl"))
    ev_ = g[(g.split == "eval") & (g.adjudicated != "unresolved")]

    def kappa(a, b):
        ct = pd.crosstab(a, b)
        cats = sorted(set(ct.index) | set(ct.columns))
        ct = ct.reindex(index=cats, columns=cats, fill_value=0).to_numpy(float)
        n = ct.sum()
        po = np.trace(ct) / n
        pe = (ct.sum(1) @ ct.sum(0)) / n ** 2
        return float((po - pe) / (1 - pe))

    gm = mo["labeller_gate"]["eval_metrics"]
    chk("gate eval kappa runtime vs AST", gm["kappa_runtime_ast"], kappa(ev_.runtime_label, ev_.ast_label))
    chk("gate eval runtime vs adjudicated", gm["acc_runtime_vs_adjudicated"],
        float((ev_.runtime_label == ev_.adjudicated).mean()))
    comb = np.where((ev_.runtime_label == ev_.ast_label) & ~ev_.runtime_label.isin(["unknown", "inconsistent"]),
                    ev_.runtime_label, ev_.judge_a.fillna("other"))
    chk("gate eval combined vs adjudicated", gm["acc_combined_vs_adjudicated"], float((comb == ev_.adjudicated).mean()))

    # H9 commitment audit, recomputed: chain hashes + commit time < first generation time of each event
    ents = jl(ROOT / "commitments.log")
    prev = "0" * 64
    chain_ok = True
    for e in ents:
        chain_ok &= e["prev_entry_hash"] == prev and hashlib.sha256(
            (prev + e["sha"] + e["utc_time"]).encode()).hexdigest() == e["entry_hash"]
        prev = e["entry_hash"]
    chk("hash chain verifies", True, bool(chain_ok))
    ts = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")  # noqa: E731
    pre_ok = True
    for f, conds_ in (("predictions/t1_single_bans.json", ("ban:", "mention:")),
                      ("predictions/t2_single_bans.json", ("ban:", "mention:")),
                      ("predictions/t1_succ_step2.json", ("succession:2",)),
                      ("predictions/t2_succ_step2.json", ("succession:2",))):
        t = f.split("/")[1][:2]
        sha = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
        ent = [e for e in ents if e["file"] == f and e["sha"] == sha]
        first = S[(S.task == t) & S.condition.str.startswith(conds_)].gen_start_utc.map(ts).min()
        pre_ok &= bool(ent) and ts(ent[0]["utc_time"]) < first
    chk("every event's predictions committed before its first generation", True, bool(pre_ok))

    # PLACEBOS: the contest and the T9 comparison must FAIL on placebo input
    rng = np.random.default_rng(2026)
    placebo = []
    for (t, x), (surv, labs, qa, qf) in events.items():
        u = list(rng.choice(surv, size=len(labs)))
        d_placebo = float(np.mean([math.log(qa[y]) - math.log(qf[y]) for y in u]))
        # T9-style: substitution family on the association winner vs uniform subtraction, split-half held-out LL
        win = borda[(t, x)]["winner"]
        wrong = sorted([y for y in surv if y not in labs], key=lambda y: borda[(t, x)]["A"][y])[0] if \
            [y for y in surv if y not in labs] else win

        def t9_margin(lbls, winner):
            eps_grid = np.linspace(0, (len(surv) - 1) / len(surv), 41)
            margins = []
            for _ in range(10):
                idx = rng.permutation(len(lbls))
                tr = [lbls[i] for i in idx[: len(lbls) // 2]]
                te = [lbls[i] for i in idx[len(lbls) // 2:]]

                def q_of(eps):
                    return composed({y: (1 - eps) if y == winner else eps / (len(surv) - 1) for y in surv}, surv)

                best = max(eps_grid, key=lambda e: sum(math.log(q_of(e)[y]) for y in tr))
                qs = q_of(best)
                margins.append(np.mean([math.log(qs[y]) for y in te]) - np.mean([math.log(qf[y]) for y in te]))
            return float(np.mean(margins))

        placebo.append({"event": f"{t}|ban:{x}", "real_paired_diff": float(np.mean([math.log(qa[y]) - math.log(qf[y])
                                                                                    for y in labs])),
                        "placebo_uniform_labels_paired_diff": d_placebo,
                        "placebo_fails(assoc does not win)": d_placebo <= 0,
                        "t9_margin_real": t9_margin(labs, win),
                        "t9_margin_placebo_uniform_labels": t9_margin(u, win),
                        "t9_margin_placebo_wrong_winner": t9_margin(labs, wrong), "wrong_winner_used": wrong})
    out = {"n_checks": len(checks), "n_match": sum(c["match"] for c in checks), "checks": checks,
           "placebo_tests": placebo,
           "not_rederived": ["S1 paraphrase-null percentiles (null is degenerate: JS=0 because each baseline has "
                             "one mode)", "sharpness-matched sensitivity", "C4 Spearman", "OpenRouter cost ledger",
                             "the labels themselves (the labeller is the measurement instrument; validated by the "
                             "gate, not re-derived here)"]}
    (ROOT / "results" / "independent_rederivation.json").write_text(json.dumps(out, indent=1, default=str))
    for c in checks:
        print(("OK  " if c["match"] else "DIFF"), c["number"], "| reported", c["reported"], "| recomputed",
              c["recomputed"])
    for p in placebo:
        print("PLACEBO", json.dumps(p, default=str))
    print(f"{out['n_match']}/{out['n_checks']} headline numbers re-derived and matching")


if __name__ == "__main__":
    main()
