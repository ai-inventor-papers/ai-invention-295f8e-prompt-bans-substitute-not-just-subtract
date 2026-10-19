#!/usr/bin/env python3
"""Step 11 scoring (all descriptive): event table, contest metrics, T9 family test, S1 sham control,
mention effects, C4 recurrence-vs-clarity, landing table, pre-commitment audit."""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime
from typing import Any

import numpy as np
from loguru import logger

from analysis.assoc import compose, restricted
from analysis.metrics import (binom_exact_ci, bootstrap_ci, condition_summary, event_outcome, is_informative,
                              js_bits, log_score, newcombe_diff_ci, smoothed, spearman, top2_agree)
from common import (DATA_DIR, MODES, NO_CODE, OTHER, PRED_DIR, RESULTS_DIR, ROOT, TASKS, read_commitments,
                    read_jsonl, sha256_file, wilson_ci, write_json)

PRIMARY = ("assoc", "freq")
ALT_ASSOC = ("assoc_first", "assoc_ext", "freetext")
ALT_FREQ = ("freq_listall", "freq_T13")
SUCC_EXTRA = ("assoc_firstban", "assoc_pooled")


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")


def load_events() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows = read_jsonl(DATA_DIR / "labelled.jsonl")
    by_cond: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_cond.setdefault(f"{r['task']}|{r['condition']}", []).append(r)
    events = []
    for task in TASKS:
        single = json.loads((PRED_DIR / f"{task}_single_bans.json").read_text())
        for x in MODES[task]:
            pred = single["events"][f"ban:{x}"]
            rws = by_cond.get(f"{task}|ban:{x}", [])
            out = event_outcome(task, rws, [x])
            events.append({"event_id": f"{task}|ban:{x}", "task": task, "kind": "single", "step": 1 if
                           pred["stratum"] == "modal" else None, "condition": f"ban:{x}", "banned": [x], "pred": pred,
                           "pred_file": f"predictions/{task}_single_bans.json", "out": out,
                           "stratum": pred["stratum"], "informative": is_informative(pred["stratum"], out),
                           "sham": pred["stratum"] == "absent", "rows": rws,
                           "twin_rows": by_cond.get(f"{task}|mention:{x}", [])})
        for k in range(2, 6):
            p = PRED_DIR / f"{task}_succ_step{k}.json"
            if not p.exists():
                continue
            pred = json.loads(p.read_text())
            rws = by_cond.get(f"{task}|succession:{k}", [])
            if not rws:
                continue
            out = event_outcome(task, rws, pred["banned_in_order"])
            events.append({"event_id": f"{task}|succession:{k}", "task": task, "kind": "succession", "step": k,
                           "condition": f"succession:{k}", "banned": pred["banned_in_order"], "pred": pred,
                           "pred_file": f"predictions/{task}_succ_step{k}.json", "out": out,
                           "stratum": "succession",
                           "informative": bool(pred.get("contest_event", True)) and is_informative("succession", out),
                           "sham": False, "rows": rws, "twin_rows": []})
    return events, by_cond


def compliant_labels(ev: dict[str, Any]) -> list[str]:
    S = ev["out"]["survivors"]
    return [r["label"] if r["label"] in S else OTHER for r in ev["rows"]
            if r["label"] != NO_CODE and r["passed"] and r["label"] not in ev["banned"]]


def predictor_names(ev: dict[str, Any]) -> list[str]:
    names = [k for k in PRIMARY + ALT_ASSOC + ALT_FREQ if k in ev["pred"]["composed"]]
    names += [k for k in SUCC_EXTRA if k in ev["pred"]["composed"]]
    return names


def top1_hit(nom: dict[str, Any], realised: str) -> float:
    if realised == "no clear mode":
        return 0.0
    if nom["is_tied"]:
        return 1.0 / len(nom["tied"]) if realised in nom["tied"] else 0.0
    return 1.0 if nom["top"] == realised else 0.0


def score_event(ev: dict[str, Any], seed: int = 0) -> dict[str, Any]:
    S = ev["out"]["survivors"]
    labs = compliant_labels(ev)
    shares = ev["out"]["realised_shares"]
    real_sm = smoothed(ev["out"]["realised_counts"], S + [OTHER])
    res: dict[str, Any] = {"n_compliant": len(labs), "chance_top1": 1 / len(S), "per_predictor": {}}
    for name in predictor_names(ev):
        q = ev["pred"]["composed"][name]
        nom = ev["pred"]["nominations"][name]
        res["per_predictor"][name] = {
            "nomination": nom["top"] if not nom["is_tied"] else nom["tied"],
            "top1_hit": top1_hit(nom, ev["out"]["realised_mode"]),
            "log_score": log_score(q, labs), "js_bits": js_bits(q, real_sm),
            "spearman": spearman([q[y] for y in S], [shares[y] for y in S]) if len(S) >= 3 else None,
            "top2_agree": top2_agree(q, shares, S),
            "log_score_no_other": _log_score_no_other(q, labs, S),
        }
    # paired assoc - freq per-sample log-score differences with within-event bootstrap
    qa, qf = ev["pred"]["composed"]["assoc"], ev["pred"]["composed"]["freq"]
    d = [math.log(qa[y]) - math.log(qf[y]) for y in labs]
    res["paired_assoc_minus_freq"] = {"mean": float(np.mean(d)) if d else None,
                                      "ci95": bootstrap_ci(d, 2000, seed) if d else None}
    for alt in ALT_FREQ:
        qx = ev["pred"]["composed"][alt]
        dd = [math.log(qa[y]) - math.log(qx[y]) for y in labs]
        res[f"paired_assoc_minus_{alt}"] = {"mean": float(np.mean(dd)) if dd else None,
                                            "ci95": bootstrap_ci(dd, 2000, seed) if dd else None}
    return res


def _log_score_no_other(q: dict[str, float], labs: list[str], S: list[str]) -> float | None:
    ls = [y for y in labs if y in S]
    if not ls:
        return None
    tot = sum(q[y] for y in S)
    return float(np.mean([math.log(q[y] / tot) for y in ls]))


def pooled(scored: list[dict[str, Any]], key: str = "paired_assoc_minus_freq") -> dict[str, Any]:
    vals = [s["score"][key]["mean"] for s in scored if s["score"][key]["mean"] is not None]
    wins = sum(1 for v in vals if v > 0)
    return {"n_events": len(vals), "mean_paired_diff": float(np.mean(vals)) if vals else None,
            "event_bootstrap_ci95": bootstrap_ci(vals, 2000, 1) if len(vals) >= 2 else None,
            "assoc_wins": wins, "assoc_wins_of": len(vals),
            "per_task": {t: [round(s["score"][key]["mean"], 4) for s in scored if s["task"] == t
                             and s["score"][key]["mean"] is not None] for t in TASKS},
            "note": "descriptive; a task-cluster bootstrap is impossible with 2 tasks"}


def contest_summary(scored: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    names = sorted({n for s in scored for n in s["score"]["per_predictor"]})
    for n in names:
        rows = [s["score"]["per_predictor"][n] for s in scored if n in s["score"]["per_predictor"]]
        out[n] = {"n_events": len(rows), "top1_hits": float(sum(r["top1_hit"] for r in rows)),
                  "mean_log_score": float(np.mean([r["log_score"] for r in rows])) if rows else None,
                  "mean_js_bits": float(np.mean([r["js_bits"] for r in rows])) if rows else None,
                  "mean_spearman": (float(np.mean([r["spearman"] for r in rows if r["spearman"] is not None]))
                                    if any(r["spearman"] is not None for r in rows) else None),
                  "top2_agree": sum(1 for r in rows if r["top2_agree"]),
                  "top2_eligible": sum(1 for r in rows if r["top2_agree"] is not None)}
    out["expected_chance_top1_hits"] = float(sum(s["score"]["chance_top1"] for s in scored))
    out["c1a_eligible_events(|S|>=3)"] = [s["event_id"] for s in scored if len(s["out"]["survivors"]) >= 3]
    return out


def sharpness_matched(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """One power parameter beta per predictor family (p^beta renormalised over S), fitted IN-SAMPLE on pooled
    informative events, then composed and scored."""
    grid = np.exp(np.linspace(np.log(0.25), np.log(8.0), 41))
    out = {}
    for name in ("assoc", "freq", "assoc_first", "assoc_ext", "freetext", "freq_listall", "freq_T13"):
        best = None
        for b in grid:
            tot, n = 0.0, 0
            for s in scored:
                S = s["out"]["survivors"]
                p = s["pred"]["raw"][name]
                pb = restricted({y: p[y] ** b if p[y] > 0 else 0.0 for y in S}, S)
                q = compose(pb, S)
                labs = compliant_labels(s)
                tot += sum(math.log(q[y]) for y in labs)
                n += len(labs)
            ll = tot / max(1, n)
            if best is None or ll > best[1]:
                best = (float(b), ll)
        out[name] = {"beta": best[0], "mean_log_score_in_sample": best[1]} if best else None
    out["label"] = "in-sample sharpness-matched sensitivity (not a calibrated out-of-sample score)"
    return out


def t9_family_test(scored: list[dict[str, Any]], base: dict[str, Any]) -> dict[str, Any]:
    rng = np.random.default_rng(9)
    per_event = []
    for s in scored:
        labs = compliant_labels(s)
        if len(labs) < 10:
            continue
        S = s["out"]["survivors"]
        task = s["task"]
        winner = s["pred"].get("assoc_restricted_winner")
        f = restricted(base[task]["baseline"]["freq"]["f"], S) if any(
            base[task]["baseline"]["freq"]["f"].get(y, 0) > 0 for y in S) else {y: 0.0 for y in S}
        eps_grid = np.linspace(0.0, (len(S) - 1) / len(S), 41)
        tau_grid = np.exp(np.linspace(np.log(0.05), np.log(20.0), 41))

        def sub_q(eps):
            p = {y: (1 - eps) if y == winner else eps / (len(S) - 1) for y in S} if len(S) > 1 else {winner: 1.0}
            return compose(p, S)

        def subtr_q(tau):
            if all(f[y] <= 0 for y in S):
                return compose({y: 1 / len(S) for y in S}, S)
            p = {y: (f[y] ** (1 / tau) if f[y] > 0 else 0.0) for y in S}
            return compose(restricted(p, S), S)

        sub_qs = [sub_q(e) for e in eps_grid]
        subtr_qs = [subtr_q(t) for t in tau_grid]
        arr = np.array(labs)
        sub_test, subtr_test = [], []
        for _ in range(10):
            idx = rng.permutation(len(arr))
            tr, te = arr[idx[: len(arr) // 2]], arr[idx[len(arr) // 2:]]
            bs = max(sub_qs, key=lambda q: sum(math.log(q[y]) for y in tr))
            bt = max(subtr_qs, key=lambda q: sum(math.log(q[y]) for y in tr))
            sub_test.append(float(np.mean([math.log(bs[y]) for y in te])))
            subtr_test.append(float(np.mean([math.log(bt[y]) for y in te])))
        ms, mt = float(np.mean(sub_test)), float(np.mean(subtr_test))
        margin = ms - mt
        win = "substitution" if margin > 1e-9 else ("subtraction" if margin < -1e-9 else "tie")
        per_event.append({"event_id": s["event_id"], "winner": win, "margin": margin, "sub_test_ll": ms,
                          "subtr_test_ll": mt, "concordant_AF": s["pred"]["concordant_AF"],
                          "label": "leak-shape test only" if s["pred"]["concordant_AF"] else "D-AF contest",
                          "subtraction_degenerate_uniform": all(f[y] <= 0 for y in S)})

    def frac(evs):
        n = len(evs)
        k = sum(1 for e in evs if e["winner"] == "substitution")
        return {"n": n, "substitution_wins": k, "fraction": k / n if n else None, "exact_binom_ci95": binom_exact_ci(k, n)}

    return {"per_event": per_event, "all_informative": frac(per_event),
            "d_af": frac([e for e in per_event if not e["concordant_AF"]]),
            "note": "descriptive; the subtraction family is uniform whenever the baseline gives zero mass to every survivor"}


def paraphrase_null(base_rows: list[dict[str, Any]], task: str, n_a: int, n_b: int, draws: int = 2000,
                    seed: int = 0) -> np.ndarray:
    keys = MODES[task] + [OTHER]
    rng = np.random.default_rng(seed)
    by_p: dict[int, list[str]] = {}
    for r in base_rows:
        if r["label"] != NO_CODE:
            by_p.setdefault(r["paraphrase_id"], []).append(r["label"] if r["label"] in MODES[task] else OTHER)
    pids = sorted(by_p)
    vals = np.empty(draws)
    for i in range(draws):
        perm = rng.permutation(pids)
        ga = [y for p in perm[:len(pids) // 2] for y in by_p[p]]
        gb = [y for p in perm[len(pids) // 2:] for y in by_p[p]]
        sa = rng.choice(ga, size=min(n_a, len(ga)), replace=False)
        sb = rng.choice(gb, size=min(n_b, len(gb)), replace=False)
        vals[i] = js_bits(smoothed(Counter(sa.tolist()), keys), smoothed(Counter(sb.tolist()), keys))
    return vals


def s1_sham(events: list[dict[str, Any]], by_cond: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out: dict[str, Any] = {"per_event": [], "null": {}}
    rng = np.random.default_rng(11)
    for task in TASKS:
        base_rows = by_cond.get(f"{task}|baseline", [])
        null = paraphrase_null(base_rows, task, 100, 50, 2000, seed=3)
        delta = float(np.quantile(null, 0.95))
        out["null"][task] = {"n_a": 100, "n_b": 50, "draws": 2000, "p95_delta": delta, "median": float(np.median(null)),
                             "construction": "random 5/5 split of the 10 baseline paraphrases; 100 vs 50 samples "
                                             "without replacement; JS in bits with +0.5 smoothing"}
        keys = MODES[task] + [OTHER]
        for ev in events:
            if ev["task"] != task or not ev["sham"]:
                continue
            a = [r["label"] if r["label"] in MODES[task] else OTHER for r in ev["rows"] if r["label"] != NO_CODE]
            b = [r["label"] if r["label"] in MODES[task] else OTHER for r in ev["twin_rows"] if r["label"] != NO_CODE]
            if not a or not b:
                continue
            js = js_bits(smoothed(Counter(a), keys), smoothed(Counter(b), keys))
            bs = []
            for _ in range(1000):
                sa = rng.choice(a, size=len(a), replace=True)
                sb = rng.choice(b, size=len(b), replace=True)
                bs.append(js_bits(smoothed(Counter(sa.tolist()), keys), smoothed(Counter(sb.tolist()), keys)))
            ub90 = float(np.quantile(bs, 0.90))
            modal = ev["pred"]["nominations"]["freq"]["top"] or max(MODES[task], key=lambda m: Counter(a)[m])
            ka, kb = Counter(a)[modal], Counter(b)[modal]
            out["per_event"].append({
                "event_id": ev["event_id"], "js_ban_vs_mention": js, "null_percentile": float((null <= js).mean()),
                "bootstrap_ub90": ub90, "equivalent_descriptive": ub90 < delta, "modal_mode": modal,
                "modal_share_ban": ka / len(a), "modal_share_ban_wilson": list(wilson_ci(ka, len(a))),
                "modal_share_mention": kb / len(b), "modal_share_mention_wilson": list(wilson_ci(kb, len(b))),
                "modal_shift_pp": 100 * (ka / len(a) - kb / len(b)),
                "modal_shift_newcombe_pp": [100 * v for v in newcombe_diff_ci(ka, len(a), kb, len(b))],
                "n_ban": len(a), "n_mention": len(b)})
        # sham ban vs baseline at matched N: null = 100 vs 100 from random 5/5 paraphrase splits
        null100 = paraphrase_null(base_rows, task, 100, 100, 2000, seed=5)
        d100 = float(np.quantile(null100, 0.95))
        out["null"][task]["vs_baseline_100v100"] = {"p95_delta": d100, "median": float(np.median(null100))}
        blab = [r["label"] if r["label"] in MODES[task] else OTHER for r in base_rows if r["label"] != NO_CODE]
        for ev in events:
            if ev["task"] != task or not ev["sham"]:
                continue
            a = [r["label"] if r["label"] in MODES[task] else OTHER for r in ev["rows"] if r["label"] != NO_CODE]
            if not a or not blab:
                continue
            obs = [js_bits(smoothed(Counter(a), keys),
                           smoothed(Counter(rng.choice(blab, size=min(100, len(blab)), replace=False).tolist()), keys))
                   for _ in range(200)]
            ka = sum(1 for y in a if y == ev["banned"][0])
            out.setdefault("sham_vs_baseline", []).append({
                "event_id": ev["event_id"], "js_median": float(np.median(obs)),
                "null_percentile": float((null100 <= np.median(obs)).mean()), "p95_delta": d100,
                "within_null_p95": float(np.median(obs)) <= d100, "label_counts": dict(Counter(a)),
                "banned_mode_share": ka / len(a), "banned_mode_share_wilson": list(wilson_ci(ka, len(a)))})
        # neutral-segment check: baseline_empty (50) vs 100-sample subsamples of baseline
        emp = [r["label"] if r["label"] in MODES[task] else OTHER for r in by_cond.get(f"{task}|baseline_empty", [])
               if r["label"] != NO_CODE]
        bl = [r["label"] if r["label"] in MODES[task] else OTHER for r in base_rows if r["label"] != NO_CODE]
        if emp and bl:
            obs = [js_bits(smoothed(Counter(rng.choice(bl, size=100, replace=False).tolist()), keys),
                           smoothed(Counter(emp), keys)) for _ in range(200)]
            out["null"][task]["baseline_empty_vs_baseline"] = {
                "js_median_over_subsamples": float(np.median(obs)),
                "null_percentile": float((null <= np.median(obs)).mean()), "n_empty": len(emp)}
    return out


def mention_effects(by_cond: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out = {}
    for task in TASKS:
        bl = [r for r in by_cond.get(f"{task}|baseline", []) if r["label"] != NO_CODE]
        keys = MODES[task] + [OTHER]
        for x in MODES[task]:
            mr = [r for r in by_cond.get(f"{task}|mention:{x}", []) if r["label"] != NO_CODE]
            br = [r for r in by_cond.get(f"{task}|ban:{x}", []) if r["label"] != NO_CODE]
            if not mr:
                continue
            km, kb = sum(r["label"] == x for r in mr), sum(r["label"] == x for r in bl)
            kban = sum(r["label"] == x for r in br)
            out[f"{task}|{x}"] = {
                "share_mention": km / len(mr), "share_baseline": kb / len(bl), "share_ban": kban / len(br) if br else None,
                "mention_minus_baseline_pp": 100 * (km / len(mr) - kb / len(bl)),
                "newcombe_ci_pp": [100 * v for v in newcombe_diff_ci(km, len(mr), kb, len(bl))],
                "ban_minus_baseline_pp": 100 * (kban / len(br) - kb / len(bl)) if br else None,
                "n_mention": len(mr), "n_baseline": len(bl)}
        la = [r for r in by_cond.get(f"{task}|listall", []) if r["label"] != NO_CODE]
        if la:
            out[f"{task}|listall_vs_baseline_js_bits"] = js_bits(
                smoothed(Counter(r["label"] if r["label"] in MODES[task] else OTHER for r in la), keys),
                smoothed(Counter(r["label"] if r["label"] in MODES[task] else OTHER for r in bl), keys))
    return out


def c4_table(events: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for ev in events:
        if ev["stratum"] in ("modal", "present", "succession") and ev["out"]["recurrence"] is not None:
            rows.append({"event_id": ev["event_id"], "task": ev["task"], "recurrence": ev["out"]["recurrence"],
                         "clarity_S": ev["pred"]["clarity_S"], "clarity_cc": ev["pred"]["clarity_cc"],
                         "kendall_w": ev["pred"]["kendall_w"], "first_entropy_norm": ev["pred"]["first_entropy_norm"]})
    res: dict[str, Any] = {"table": rows}
    for scope in TASKS + ("pooled",):
        rs = [r for r in rows if scope == "pooled" or r["task"] == scope]
        res[f"spearman_{scope}"] = {k: spearman([r["recurrence"] for r in rs], [r[k] for r in rs])
                                    for k in ("clarity_S", "clarity_cc", "kendall_w", "first_entropy_norm")}
        res[f"n_{scope}"] = len(rs)
    res["note"] = "descriptive; few events per task"
    return res


def landing_table(events: list[dict[str, Any]], by_cond: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    state_p = RESULTS_DIR / "succession_state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    evmap = {e["event_id"]: e for e in events}
    out = []
    for task in TASKS:
        bl = [r for r in by_cond.get(f"{task}|baseline", []) if r["label"] != NO_CODE and r["passed"]]
        prev = {m: sum(r["label"] == m for r in bl) / max(1, len(bl)) for m in MODES[task]}
        for st in state.get(task, {}).get("steps", []):
            eid = f"{task}|{st['condition']}"
            ev = evmap.get(eid)
            if ev is None:
                continue
            S = ev["out"]["survivors"]
            sh = ev["out"]["realised_shares"]
            gains = {y: 100 * (sh[y] - prev.get(y, 0.0)) for y in S}
            noms = ev["pred"]["nominations"]
            out.append({"task": task, "step": st["step"], "condition": st["condition"], "banned": st["banned"],
                        "survivors": S, "compliant_share": {y: sh[y] for y in S + [OTHER]},
                        "previous_share": {y: prev.get(y, 0.0) for y in S}, "gain_pp": gains,
                        "largest_gainer": max(S, key=lambda y: gains[y]) if S else None,
                        "realised_mode": ev["out"]["realised_mode"],
                        "assoc_nomination": noms["assoc"]["top"] or noms["assoc"]["tied"],
                        "freq_nomination": noms["freq"]["top"] or ("tied:" + ",".join(noms["freq"]["tied"])),
                        "assoc_hit": top1_hit(noms["assoc"], ev["out"]["realised_mode"]),
                        "freq_hit": top1_hit(noms["freq"], ev["out"]["realised_mode"]),
                        "compliance": ev["out"]["compliance"], "pass_rate": ev["out"]["pass_rate"],
                        "hill_cc": ev["out"]["hill_cc"], "n_compliant": ev["out"]["n_compliant"],
                        "next": st.get("next"), "next_rule": st.get("next_rule")})
            prev = {y: sh.get(y, 0.0) for y in MODES[task]}
    return out


def commitment_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    entries = read_commitments()
    from common import verify_chain

    ok_chain, problems = verify_chain()
    res = {"chain_ok": ok_chain, "chain_problems": problems, "events": []}
    for ev in events:
        p = ROOT / ev["pred_file"]
        sha = sha256_file(p)
        ent = [e for e in entries if e["file"] == ev["pred_file"] and e["sha"] == sha]
        samples = ev["rows"] + ev["twin_rows"]
        first = min((_ts(r["gen_start_utc"]) for r in samples if r.get("gen_start_utc")), default=None)
        commit_t = _ts(ent[0]["utc_time"]) if ent else None
        ok = bool(ent) and first is not None and commit_t < first
        res["events"].append({"event_id": ev["event_id"], "pred_file": ev["pred_file"], "sha_matches": bool(ent),
                              "commit_utc": ent[0]["utc_time"] if ent else None,
                              "first_generation_utc": first.isoformat() + "Z" if first else None,
                              "pre_committed": ok})
    res["all_pre_committed"] = all(e["pre_committed"] for e in res["events"])
    return res


NAME_RE = {
    "bfs": r"\bbfs\b|breadth[\s_-]*first", "dfs": r"\bdfs\b|depth[\s_-]*first",
    "bibfs": r"bidirectional|bi[_-]?bfs", "iddfs": r"iddfs|iterative[\s_-]*deepening|depth[\s_-]*limited",
    "astar_gbfs": r"a\*|a[_-]?star|astar|best[\s_-]*first|greedy|heuristic", "dijkstra": r"dijkstra",
    "bf_spfa": r"bellman|spfa", "bidijkstra": r"bidirectional", "floyd": r"floyd|warshall", "dial": r"\bdial|bucket",
}
DESCRIPTORS = {"backtracking": r"backtrack", "bfs_word": r"\bbfs\b|breadth", "queue_word": r"queue",
               "relaxation": r"relax", "priority_queue_word": r"priority|heap", "pruning": r"prun"}


def disguised_recurrence(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Among programs labelled with a BANNED mode, how many still name that mode anywhere in their code
    (identifiers or comments)? Recurrence without the name = the banned mechanism under another description."""
    import re

    out = []
    for ev in events:
        rec = [r for r in ev["rows"] if r["label"] in ev["banned"] and r.get("code")]
        if not rec:
            continue
        named = sum(1 for r in rec if re.search(NAME_RE[r["label"]], r["code"], re.I))
        desc = Counter()
        for r in rec:
            for k, pat in DESCRIPTORS.items():
                if re.search(pat, r["code"], re.I):
                    desc[k] += 1
        out.append({"event_id": ev["event_id"], "banned": ev["banned"], "n_recurrent": len(rec),
                    "recurrent_naming_banned_mode": named, "recurrent_without_name": len(rec) - named,
                    "share_without_name": (len(rec) - named) / len(rec), "descriptor_counts": dict(desc),
                    "recurrent_labels": dict(Counter(r["label"] for r in rec))})
    return {"per_event": out, "note": "regex over the extracted code (comments + identifiers); descriptive"}


def stage_score() -> None:
    base = json.loads((ROOT / "elicitation" / "baseline_objects.json").read_text())
    events, by_cond = load_events()
    audit = commitment_audit(events)
    pre_ok = {e["event_id"]: e["pre_committed"] for e in audit["events"]}
    # condition summaries
    summ = {}
    for key, rws in sorted(by_cond.items()):
        summ[key] = condition_summary(rws)
    write_json(DATA_DIR / "condition_summaries.json", summ)
    # event table
    table = []
    for ev in events:
        table.append({"event_id": ev["event_id"], "task": ev["task"], "kind": ev["kind"], "banned": ev["banned"],
                      "survivors": ev["out"]["survivors"], "stratum": ev["stratum"], "informative": ev["informative"],
                      "sham": ev["sham"], "pre_committed": pre_ok.get(ev["event_id"]),
                      "compliance": ev["out"]["compliance"], "recurrence": ev["out"]["recurrence"],
                      "n_code": ev["out"]["n_code"], "n_compliant": ev["out"]["n_compliant"],
                      "pass_rate": ev["out"]["pass_rate"], "realised_mode": ev["out"]["realised_mode"],
                      "realised_margin": ev["out"]["realised_margin"], "realised_counts": ev["out"]["realised_counts"],
                      "label_counts_all": ev["out"]["label_counts_all"],
                      "nominations": {k: (v["top"] if not v["is_tied"] else v["tied"])
                                      for k, v in ev["pred"]["nominations"].items()},
                      "concordant_AF": ev["pred"]["concordant_AF"], "freq_tied": ev["pred"]["freq_tied"],
                      "freq_stability": ev["pred"]["freq_stability"], "freq_stable": ev["pred"]["freq_stable"],
                      "freq_margin": ev["pred"]["freq_margin"], "clarity_S": ev["pred"]["clarity_S"],
                      "ambiguous": ev["pred"]["ambiguous"]})
    # contest on informative, pre-committed events
    inf = [e for e in events if e["informative"] and pre_ok.get(e["event_id"])]
    scored = []
    for i, ev in enumerate(inf):
        sc = score_event(ev, seed=i)
        scored.append({**ev, "score": sc})
    clar = [e["pred"]["clarity_S"] for e in scored]
    med = float(np.median(clar)) if clar else None
    strata = {
        "all_informative": [s for s in scored],
        "D-AF": [s for s in scored if not s["pred"]["concordant_AF"]],
        "STABLE-D-AF": [s for s in scored if not s["pred"]["concordant_AF"] and s["pred"]["freq_stable"]],
        "concordant-AF": [s for s in scored if s["pred"]["concordant_AF"]],
        "high-clarity": [s for s in scored if med is not None and s["pred"]["clarity_S"] > med],
    }
    contest = {"events": [{"event_id": s["event_id"], "survivors": s["out"]["survivors"],
                           "realised_mode": s["out"]["realised_mode"], "n_compliant": s["out"]["n_compliant"],
                           **s["score"]} for s in scored],
               "strata": {k: {"n_events": len(v), "effective_N": len(v), "events": [s["event_id"] for s in v],
                              "pooled_assoc_minus_freq": pooled(v) if v else None,
                              "summary": contest_summary(v) if v else None} for k, v in strata.items()},
               "robustness": {
                   "assoc_vs_freq_listall": pooled(scored, "paired_assoc_minus_freq_listall") if scored else None,
                   "assoc_vs_freq_T13": pooled(scored, "paired_assoc_minus_freq_T13") if scored else None,
                   "sharpness_matched": sharpness_matched(scored) if scored else None},
               "clarity_median": med,
               "excluded_not_precommitted": [e["event_id"] for e in events if e["informative"]
                                             and not pre_ok.get(e["event_id"])]}
    if not scored:
        contest["empty_reason"] = "no informative pre-committed events"
    t9 = t9_family_test(scored, base) if scored else {"per_event": [], "note": "no informative events"}
    s1 = s1_sham(events, by_cond)
    ment = mention_effects(by_cond)
    c4 = c4_table(events)
    land = landing_table(events, by_cond)
    write_json(RESULTS_DIR / "event_table.json", table)
    write_json(RESULTS_DIR / "contest.json", contest)
    write_json(RESULTS_DIR / "t9_family_test.json", t9)
    write_json(RESULTS_DIR / "s1_sham_control.json", s1)
    write_json(RESULTS_DIR / "mention_effects.json", ment)
    write_json(RESULTS_DIR / "c4_recurrence_vs_clarity.json", c4)
    write_json(RESULTS_DIR / "landing_table.json", land)
    write_json(RESULTS_DIR / "commitment_audit.json", audit)
    write_json(RESULTS_DIR / "disguised_recurrence.json", disguised_recurrence(events))
    logger.info(f"scored {len(scored)} informative events; audit all_pre_committed={audit['all_pre_committed']}")
    for s in scored:
        pp = s["score"]["per_predictor"]
        logger.info(f"{s['event_id']}: realised={s['out']['realised_mode']} | assoc nom={pp['assoc']['nomination']} "
                    f"hit={pp['assoc']['top1_hit']} ls={pp['assoc']['log_score']:.3f} | freq nom={pp['freq']['nomination']} "
                    f"hit={pp['freq']['top1_hit']} ls={pp['freq']['log_score']:.3f}")
