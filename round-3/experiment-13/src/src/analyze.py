#!/usr/bin/env python3
"""S3 analysis (committed before the first ban sample; run after the bans).

3.1 one row per task (results/c1_events.jsonl); 3.2 advance rule (+ Wilcoxon/Holm at >= 10 events), camp contest,
verdict, co-veto sensitivity; 3.3 C2b (one-shot) + descriptive C2b for persistent / last iterated round / sham;
3.4 descriptives (avoidance, landing, pass rate, other/invalid shares, correct-only landing, Hill_cc, Wilson CIs,
re-emergence surfaces, DISGUISE, leak and fire rates, sham vs distinctive, LADDER_EXISTS, bf16 twin vs FP8 pilot,
HF twin vs vLLM twin, band-patch control); 3.5 template effect; 3.6 figures.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from typing import Any

import numpy as np
from loguru import logger

from c2b import c2b_event, event_seed, verdict as c2b_verdict
from common import (DEFAULTS, FIGS, FROZEN_CONSTANTS, MODEL_ID, PRED, RESULTS, TASK_ORDER, WS, read_json, read_jsonl,
                    spec, survivors, task_dir, write_json, write_jsonl)
from score import (DESCRIPTIVE, PRIMARY, advance, hill1, logscore, p_from_counts, realised_top1, smooth, top1,
                   wilson)

ARMS = ["twin", "oneshot", "sham", "persistent", "iter1", "iter2", "iter3", "nonce", "novelty", "rand1", "rand2",
        "rand3", "hf_twin", "ban", "bandpatch"]
FEATURES = {"sorted(": r"\bsorted\(", ".sort(": r"\.sort\(", "heapq": r"\bheapq\b", "PriorityQueue": r"PriorityQueue",
            "set(": r"\bset\(", "dict/{}": r"\bdict\(|=\s*\{\}", "Counter": r"\bCounter\b",
            "defaultdict": r"\bdefaultdict\b", "bisect": r"\bbisect\b", "deque": r"\bdeque\b",
            "lru_cache/cache": r"lru_cache|@cache\b", "recursion": r"def (\w+)\(.*\):[\s\S]*\b\1\(",
            "while": r"\bwhile\b", "find(": r"\.find\(|\bfind\(", "index(": r"\.index\("}


def load_arms(store) -> dict[str, list[dict]]:
    arms = {}
    for a in ["twin", "oneshot", "sham", "persistent", "iter1", "iter2", "iter3", "nonce", "novelty", "hf_twin",
              "ban", "bandpatch"]:
        arms[a] = store.lab_rows(a)
    rand = store.lab_rows("rand")
    for k in (1, 2, 3):
        arms[f"rand{k}"] = [r for r in rand if r.get("arm") == f"rand{k}"]
    return arms


def mapped(label: str, S: list[str]) -> str:
    return label if label in S else "other"


def summarize(labs: list[dict], task: str) -> dict[str, Any]:
    D = DEFAULTS[task]
    S = survivors(task)
    rows = [r for r in labs if r["task"] == task]
    if not rows:
        return {}
    att = [r for r in rows if r["label"] != "invalid"]
    nd = [r for r in att if r["label"] != D]
    k_d = len(att) - len(nd)
    corr = [r for r in att if r.get("passed")]
    corr_nd = [r for r in nd if r.get("passed")]
    lo, hi = wilson(len(nd), len(att)) if att else (None, None)
    return {"n": len(rows), "n_attempted": len(att), "n_default": k_d, "n_non_default": len(nd),
            "avoidance": len(nd) / len(att) if att else None, "avoidance_wilson95": [lo, hi],
            "default_share": k_d / len(att) if att else None,
            "landing": dict(Counter(mapped(r["label"], S) for r in nd)),
            "correct_landing": dict(Counter(mapped(r["label"], S) for r in corr_nd)),
            "pass_rate": sum(1 for r in rows if r.get("passed")) / len(rows),
            "pass_rate_attempted": len(corr) / len(att) if att else None,
            "other_share": sum(1 for r in att if r["label"] == "other") / len(att) if att else None,
            "invalid_share": (len(rows) - len(att)) / len(rows),
            "hill_attempted": hill1([r["label"] for r in att]), "hill_correct": hill1([r["label"] for r in corr]),
            "hill_correct_non_banned": hill1([r["label"] for r in corr_nd])}


# ------------------------------------------------------------------------------------------------ 3.1 / 3.2
def c1_events(arms: dict, fc: dict, chain_head: str) -> list[dict]:
    events = []
    for t in TASK_ORDER:
        if t not in fc["tasks"] or not any(r["task"] == t for r in arms["ban"]):
            continue
        F = fc["tasks"][t]
        D = DEFAULTS[t]
        S = survivors(t)
        sm = summarize(arms["ban"], t)
        nb = [mapped(r["label"], S) for r in arms["ban"] if r["task"] == t and r["label"] not in ("invalid", D)]
        gate = (sm["avoidance"] or 0) >= FROZEN_CONSTANTS["gate"]["min_avoidance"] and \
            len(nb) >= FROZEN_CONSTANTS["gate"]["min_non_banned_attempts"]
        fams = {}
        for f in PRIMARY + DESCRIPTIVE:
            pr = F["families"][f].get("p_raw")
            ps = smooth(pr, S)
            fams[f] = {"defined": pr is not None, "p_raw": pr, "p": ps, "top1": top1(pr, S)[0],
                       "logscore": logscore(ps, nb) if nb else None}
        real = realised_top1(nb, S)
        ev = {"model": MODEL_ID, "task": t, "event_type": "modal", "banned": D, "n_samples": sm["n"],
              "n_attempts": sm["n_attempted"], "avoidance": sm["avoidance"],
              "avoidance_wilson95": sm["avoidance_wilson95"], "gate_pass": bool(gate), "n_non_banned": len(nb),
              "landing_counts": sm["landing"], "correct_counts": sm["correct_landing"],
              "other_share": sm["other_share"], "invalid_share": sm["invalid_share"],
              "forecasts": {f: v["p_raw"] for f, v in fams.items()},
              "forecasts_smoothed": {f: v["p"] for f, v in fams.items()},
              "defined": {f: v["defined"] for f, v in fams.items()},
              "top1": {f: v["top1"] for f, v in fams.items()}, "realised_top1": real,
              "hits": {f: (v["top1"] in real) if v["top1"] else False for f, v in fams.items()},
              "logscore": {f: v["logscore"] for f, v in fams.items()},
              "disagreeing": F["disagreeing"], "co_vetoed": F.get("co_veto", []),
              "hill_cc": {"attempted": sm["hill_attempted"], "correct": sm["hill_correct"],
                          "correct_non_banned": sm["hill_correct_non_banned"]},
              "pass_rate": sm["pass_rate"], "commit_sha256": chain_head}
        events.append(ev)
    return events


def camp_forecast(F: dict) -> str:
    return "SUBTRACT" if F["families"]["SUBTRACT"].get("p_raw") is not None else "LADDER"


def c1_decision(events: list[dict], fc: dict) -> dict[str, Any]:
    cfg = FROZEN_CONSTANTS["advance"]
    gated = [e for e in events if e["gate_pass"]]
    dis = [e for e in gated if e["disagreeing"]]
    out: dict[str, Any] = {"n_events": len(events), "n_gated": len(gated), "n_gated_disagreeing": len(dis),
                           "gated_tasks": [e["task"] for e in gated], "disagreeing_tasks": [e["task"] for e in dis]}
    adv = advance([{"task": e["task"], "logscore": {f: e["logscore"][f] for f in PRIMARY}} for e in dis], PRIMARY,
                  cfg["margin_nats"], cfg["min_wins"])
    out["advance"] = adv
    # advance count also over all gated events (descriptive)
    out["advance_all_gated_descriptive"] = advance(
        [{"task": e["task"], "logscore": {f: e["logscore"][f] for f in PRIMARY}} for e in gated], PRIMARY,
        cfg["margin_nats"], cfg["min_wins"])
    # Wilcoxon (Holm) only with >= 10 disagreeing gated events
    if len(dis) >= FROZEN_CONSTANTS["wilcoxon_min_events"]:
        from scipy.stats import wilcoxon

        tests = []
        for a in ["SUBTRACT", "LADDER"]:
            for b in ["ASSOCIATE", "PROXIMITY"]:
                d = [e["logscore"][a] - e["logscore"][b] for e in dis]
                try:
                    p = float(wilcoxon(d).pvalue)
                except ValueError:
                    p = 1.0
                tests.append({"a": a, "b": b, "median_diff": float(np.median(d)), "p": p})
        order = sorted(range(len(tests)), key=lambda i: tests[i]["p"])
        m = len(tests)
        running = 0.0
        for rank, i in enumerate(order):
            running = max(running, min(1.0, (m - rank) * tests[i]["p"]))
            tests[i]["p_holm"] = running
        out["wilcoxon_holm"] = tests
    else:
        out["wilcoxon_holm"] = f"not run: {len(dis)} < {FROZEN_CONSTANTS['wilcoxon_min_events']} disagreeing gated events"
    # camp contest (secondary)
    camp_ev = []
    for e in gated:
        F = fc["tasks"][e["task"]]
        bf = camp_forecast(F)
        tops = [e["top1"][bf], e["top1"]["ASSOCIATE"], e["top1"]["PROXIMITY"]]
        d = [x for x in tops if x is not None]
        if len(d) >= 2 and len(set(d)) > 1:
            camp_ev.append({"task": e["task"], "logscore": {"BAN-FREE": e["logscore"][bf],
                                                            "ASSOCIATE": e["logscore"]["ASSOCIATE"],
                                                            "PROXIMITY": e["logscore"]["PROXIMITY"]},
                            "ban_free_family": bf})
    out["camp_contest"] = advance(camp_ev, ["BAN-FREE", "ASSOCIATE", "PROXIMITY"], cfg["margin_nats"], cfg["min_wins"])
    out["camp_contest"]["n_events"] = len(camp_ev)
    out["camp_contest"]["ban_free_family_per_event"] = {e["task"]: e["ban_free_family"] for e in camp_ev}
    # verdict
    a = set(adv["advancing"])
    bf, sb = {"SUBTRACT", "LADDER"}, {"ASSOCIATE", "PROXIMITY"}
    unaimed = sum(1 for e in gated if not any(e["top1"][f] in e["realised_top1"] for f in PRIMARY if e["top1"][f]))
    out["n_gated_no_family_hits"] = unaimed
    if len(dis) < 3:
        v = "UNDETERMINED"
    elif a and a <= bf:
        v = "SUBTRACTION/LADDER (" + "+".join(sorted(a)) + ")"
    elif a and a <= sb:
        v = "SUBSTITUTION (" + "+".join(sorted(a)) + ")"
    elif a:
        v = "MIXED (" + "+".join(sorted(a)) + ")"
    elif gated and unaimed >= 0.5 * len(gated):
        v = "X-SPECIFIC BUT UNAIMED"
    else:
        v = "NO FAMILY ADVANCES"
    out["verdict"] = v
    out["hit_rates_gated"] = {f: (sum(e["hits"][f] for e in gated) / len(gated) if gated else None)
                              for f in PRIMARY + DESCRIPTIVE}
    out["mean_logscore_gated"] = {f: (float(np.mean([e["logscore"][f] for e in gated])) if gated else None)
                                  for f in PRIMARY + DESCRIPTIVE}
    return out


def covetosensitivity(events: list[dict], fc: dict) -> dict[str, Any]:
    """Co-vetoed survivors removed from the outcome space; every forecast renormalised."""
    rows = []
    for e in events:
        if not e["gate_pass"] or not e["disagreeing"]:
            continue
        S = survivors(e["task"])
        cv = set(e["co_vetoed"])
        S2 = [s for s in S if s not in cv]
        labs = []
        for k, v in e["landing_counts"].items():
            if k not in cv:
                labs += [k if k in S2 else "other"] * v
        ls = {}
        for f in PRIMARY:
            pr = e["forecasts"][f]
            if pr is not None:
                pr2 = {k: v for k, v in pr.items() if k not in cv}
                tot = sum(pr2.values())
                pr2 = {k: v / tot for k, v in pr2.items()} if tot > 0 else None
            else:
                pr2 = None
            ls[f] = logscore(smooth(pr2, S2), labs) if labs else None
        rows.append({"task": e["task"], "logscore": ls})
    cfg = FROZEN_CONSTANTS["advance"]
    ok = [r for r in rows if all(v is not None for v in r["logscore"].values())]
    return {"n_events": len(ok), "any_co_veto": any(e["co_vetoed"] for e in events),
            "advance": advance(ok, PRIMARY, cfg["margin_nats"], cfg["min_wins"])}


# ------------------------------------------------------------------------------------------------ 3.3 C2b
def c2b_all(arms: dict, events: list[dict], fc: dict, chain: dict) -> dict[str, Any]:
    cfg = FROZEN_CONSTANTS["c2b"]
    out = {}
    for arm_key in ["oneshot", "persistent", "last_iterated", "sham"]:
        evs = []
        for e in events:
            t = e["task"]
            if not e["gate_pass"]:
                continue
            D = DEFAULTS[t]
            S = survivors(t)
            arm = arm_key
            if arm_key == "last_iterated":
                rounds = chain.get(t, {}).get("rounds", [0])
                arm = "persistent" if rounds[-1] == 0 else f"iter{rounds[-1]}"
            vl = [r for r in arms[arm] if r["task"] == t]
            if not vl:
                continue
            va = [r for r in vl if r["label"] != "invalid"]
            v_avoid = sum(1 for r in va if r["label"] != D) / len(va) if va else 0.0
            cv = set(e["co_vetoed"])
            space = [s for s in S if s not in cv] + ["other"]
            v_lab = [mapped(r["label"], S) for r in va if r["label"] != D]
            v_lab = [l for l in v_lab if l in space]
            b_by_t = {w: [mapped(r["label"], S) for r in arms["ban"] if r["task"] == t and r["template"] == w
                          and r["label"] not in ("invalid", D)] for w in WS}
            b_by_t = {w: [l for l in ls if l in space] for w, ls in b_by_t.items()}
            n_b = sum(len(v) for v in b_by_t.values())
            elig = v_avoid >= cfg["min_one_shot_avoidance"] and len(v_lab) >= cfg["min_attempts_in_S_prime"] and \
                n_b >= cfg["min_attempts_in_S_prime"]
            rec = {"task": t, "arm": arm, "veto_avoidance": v_avoid, "eligible": bool(elig), "n_veto_S": len(v_lab),
                   "n_ban_S": n_b}
            if elig:
                rec.update(c2b_event(t, v_lab, b_by_t, space, event_seed(cfg["null_seed"], t, arm_key),
                                     cfg["null_replicates"]))
            evs.append(rec)
        el = [x for x in evs if x["eligible"]]
        out[arm_key] = {"events": evs, **c2b_verdict(el, cfg["min_eligible_events"], cfg["confirm_share"],
                                                       cfg["elsewhere_share"])}
    out["primary"] = "oneshot"
    return out


# ------------------------------------------------------------------------------------------------ 3.4
def aliases_of(task: str, mode: str) -> list[str]:
    sp = spec(task)
    names = [c["display_name"] for c in sp["catalogue"] if c["mode"] == mode]
    return [a.lower() for a in names + list(sp.get("aliases", {}).get(mode, []))]


def first_lines(code: str | None, k: int = 3) -> str:
    if not code:
        return ""
    lines = [re.sub(r"\s+", " ", l.strip()) for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
    return " | ".join(lines[:k])


def reemergence(store, arms: dict, chain: dict) -> dict[str, Any]:
    from bench.common.harness import extract_code

    out = {"per_task": {}}
    every = 0
    n_tasks = 0
    for t in TASK_ORDER:
        rounds = chain.get(t, {}).get("rounds", [0])
        names = ["persistent" if r == 0 else f"iter{r}" for r in rounds]
        D = DEFAULTS[t]
        rec = {"rounds": names, "per_round": {}}
        all_rounds = True
        for a in names:
            raw = {r["sample_id"]: r for r in store.raw_rows(a) if r["task"] == t}
            labs = [r for r in arms[a] if r["task"] == t]
            dl = [r for r in labs if r["label"] == D]
            if not dl:
                all_rounds = False
            feats = Counter()
            fl = Counter()
            leak = 0
            for r in dl:
                rr = raw.get(r["sample_id"], {})
                code = extract_code(rr.get("text", "")) or ""
                fl[first_lines(code)] += 1
                leak += bool(rr.get("text_leak"))
                for k, pat in FEATURES.items():
                    if re.search(pat, code):
                        feats[k] += 1
            rec["per_round"][a] = {"n_default": len(dl), "n": len(labs), "text_leak_among_default": leak,
                                   "top_first_lines": fl.most_common(3), "features": dict(feats)}
        rec["default_reemerges_every_round"] = all_rounds
        if labs:
            n_tasks += 1
            every += all_rounds
        out["per_task"][t] = rec
    out["share_tasks_default_in_every_round"] = every / n_tasks if n_tasks else None
    return out


def disguise(store, arms: dict) -> dict[str, Any]:
    out = {}
    raw = {r["sample_id"]: r for r in store.raw_rows("ban")}
    for t in TASK_ORDER:
        D = DEFAULTS[t]
        al = aliases_of(t, D)
        dl = [r for r in arms["ban"] if r["task"] == t and r["label"] == D]
        n_dis = sum(1 for r in dl if not any(a in (raw.get(r["sample_id"], {}).get("text", "") or "").lower()
                                             for a in al))
        out[t] = {"n_banned_mechanism": len(dl), "n_no_alias_mention": n_dis,
                  "share_disguised": n_dis / len(dl) if dl else None}
    return out


def veto_stats(store) -> dict[str, Any]:
    out = {}
    for a in ["oneshot", "sham", "persistent", "iter1", "iter2", "iter3"]:
        rows = store.raw_rows(a)
        if not rows:
            continue
        per = {}
        for t in TASK_ORDER:
            rr = [r for r in rows if r["task"] == t]
            if not rr:
                continue
            per[t] = {"n": len(rr), "fire_rate": sum(1 for r in rr if r["n_vetoes"] > 0) / len(rr),
                      "mean_vetoes": float(np.mean([r["n_vetoes"] for r in rr])),
                      "text_leak_rate": sum(r["text_leak"] for r in rr) / len(rr),
                      "veto_cap_hits": sum(r["veto_cap"] for r in rr),
                      "remaining_completions": sum(r["remaining_completions"] for r in rr)}
        out[a] = {"per_task": per, "fire_rate": sum(1 for r in rows if r["n_vetoes"] > 0) / len(rows),
                  "text_leak_rate": sum(r["text_leak"] for r in rows) / len(rows)}
    return out


def descriptives(store, arms: dict, fc: dict, chain: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"per_task_arm": {}}
    for t in TASK_ORDER:
        out["per_task_arm"][t] = {a: summarize(arms[a], t) for a in ARMS if arms.get(a)
                                  and any(r["task"] == t for r in arms[a])}
    out["veto"] = veto_stats(store)
    out["reemergence"] = reemergence(store, arms, chain)
    out["disguise"] = disguise(store, arms)
    sv = {}
    for t in TASK_ORDER:
        pa = out["per_task_arm"][t]
        if "sham" in pa and "oneshot" in pa:
            sv[t] = {"oneshot_avoidance": pa["oneshot"]["avoidance"], "sham_avoidance": pa["sham"]["avoidance"],
                     "sham_invalid_share": pa["sham"]["invalid_share"],
                     "oneshot_invalid_share": pa["oneshot"]["invalid_share"]}
    out["sham_vs_distinctive"] = sv
    out["ladder_exists"] = {t: fc["tasks"][t]["families"]["LADDER"].get("LADDER_EXISTS") for t in fc["tasks"]}
    tw = {}
    for t in TASK_ORDER:
        pilot = read_jsonl(task_dir(t) / "pilot_rows.jsonl")
        pd_share = sum(1 for r in pilot if r["label"] == DEFAULTS[t]) / len(pilot)
        pa = out["per_task_arm"][t]
        tw[t] = {"fp8_pilot_default_share": pd_share,
                 "bf16_vllm_twin_default_share": pa.get("twin", {}).get("default_share"),
                 "bf16_hf_twin_default_share": pa.get("hf_twin", {}).get("default_share"),
                 "flag_twin_below_0.9": (pa.get("twin", {}).get("default_share") or 0) < 0.9}
    out["twin_vs_pilot_and_engine"] = tw
    return out


# ------------------------------------------------------------------------------------------------ 3.6 figures
def figures(arms: dict, events: list[dict], c2: dict, te: dict) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGS.mkdir(parents=True, exist_ok=True)
    made = []
    plot_arms = ["twin", "oneshot", "sham", "persistent", "iter1", "nonce", "novelty", "rand1", "rand2", "rand3",
                 "ban", "bandpatch"]
    fig, axes = plt.subplots(3, 4, figsize=(18, 11), sharey=True)
    cmap = plt.get_cmap("tab10")
    for ax, t in zip(axes.ravel(), TASK_ORDER):
        D = DEFAULTS[t]
        cats = [D] + survivors(t) + ["other", "invalid"]
        colors = {c: ("#444444" if c == D else "#bbbbbb" if c == "invalid" else "#999999" if c == "other"
                      else cmap(i % 10)) for i, c in enumerate(cats)}
        xs = [a for a in plot_arms if any(r["task"] == t for r in arms.get(a, []))]
        bottom = np.zeros(len(xs))
        for c in cats:
            vals = []
            for a in xs:
                rows = [r for r in arms[a] if r["task"] == t]
                lab = [r["label"] if (r["label"] in cats) else "other" for r in rows]
                vals.append(lab.count(c) / len(rows) if rows else 0)
            ax.bar(range(len(xs)), vals, bottom=bottom, color=colors[c], label=c, edgecolor="white", linewidth=0.3)
            bottom += np.array(vals)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels(xs, rotation=70, fontsize=7)
        ax.set_title(f"{t} (D = {D})", fontsize=9)
        ax.legend(fontsize=5, loc="lower left", ncol=2)
    axes[0, 0].set_ylabel("share of samples")
    fig.suptitle("Label composition per arm (dark = banned default D)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"composition_per_task.{ext}", dpi=150)
    plt.close(fig)
    made.append("figures/composition_per_task.png")
    # log scores per family per event
    fams = PRIMARY + ["SUBTRACT_1SHOT", "UNIFORM"]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ev = [e for e in events if e["n_non_banned"] > 0]
    for j, f in enumerate(fams):
        ys = [e["logscore"][f] for e in ev]
        ax.scatter(np.arange(len(ev)) + (j - len(fams) / 2) * 0.1, ys, label=f, s=22)
    for i, e in enumerate(ev):
        if e["disagreeing"] and e["gate_pass"]:
            ax.axvspan(i - 0.45, i + 0.45, color="#f3e6b3", alpha=0.5, lw=0)
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels([e["task"] + ("" if e["gate_pass"] else "*") for e in ev])
    ax.set_ylabel("mean log score (nats)")
    ax.set_title("Log score of each forecast family on the ban's non-banned attempts (shaded: gated disagreeing; "
                 "* = gate failed)", fontsize=9)
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"logscores_by_family.{ext}", dpi=150)
    plt.close(fig)
    made.append("figures/logscores_by_family.png")
    # C2b JS vs null p95
    evs = [x for x in c2["oneshot"]["events"] if x.get("eligible")]
    if evs:
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(len(evs))
        ax.bar(x - 0.2, [e["js"] for e in evs], width=0.4, label="JS(one-shot veto, ban)")
        ax.bar(x + 0.2, [e["null_p95"] for e in evs], width=0.4, label="template-resampling null p95")
        for i, e in enumerate(evs):
            ax.text(i, max(e["js"], e["null_p95"]) + 0.01, "agree" if e["agree"] else "differs", ha="center",
                    fontsize=7)
        ax.set_xticks(x)
        ax.set_xticklabels([e["task"] for e in evs])
        ax.set_ylabel("Jensen-Shannon divergence (bits)")
        ax.legend(fontsize=8)
        ax.set_title("C2b: one-shot veto landing vs ban landing")
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIGS / f"c2b_js_vs_null.{ext}", dpi=150)
        plt.close(fig)
        made.append("figures/c2b_js_vs_null.png")
    # template x task heatmap
    pt = te.get("per_template", {})
    if pt:
        M = np.full((len(TASK_ORDER), len(WS)), np.nan)
        for i, t in enumerate(TASK_ORDER):
            for j, w in enumerate(WS):
                v = pt.get(t, {}).get(w)
                if v and v["share"] is not None:
                    M[i, j] = v["share"]
        fig, ax = plt.subplots(figsize=(6, 7))
        im = ax.imshow(M, cmap="viridis", vmin=0, vmax=1, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if not np.isnan(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7,
                            color="white" if M[i, j] < 0.5 else "black")
        ax.set_xticks(range(len(WS)))
        ax.set_xticklabels(WS)
        ax.set_yticks(range(len(TASK_ORDER)))
        ax.set_yticklabels(TASK_ORDER)
        fig.colorbar(im, ax=ax, label="banned share among attempts")
        ax.set_title("Banned (default) share under the named ban, per template")
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(FIGS / f"template_task_banned_share.{ext}", dpi=150)
        plt.close(fig)
        made.append("figures/template_task_banned_share.png")
    return made


# ------------------------------------------------------------------------------------------------ main
def run(sub: str = "", fake_ban_from: str | None = None, fc_path=None, head: str | None = None,
        out_dir=None, make_figures: bool | None = None) -> dict[str, Any]:
    import template_effect as TE
    from common import bench_import
    from vllm_stage import Store

    bench_import()
    store = Store(sub)
    sfx = f"_{sub}" if sub else ""
    fc = read_json(fc_path or PRED / f"forecasts{sfx}.json")
    chain = read_json(PRED / f"iterated_chain{sfx}.json")
    if head is None:
        head = read_json(RESULTS / f"commitment_head{sfx}.json")["chain_head"]
    arms = load_arms(store)
    if fake_ban_from:  # dry run only: a ban-free arm stands in for the ban (no ban is sampled before the seal)
        arms["ban"] = [dict(r, template=r["template"] if r["template"] in WS else WS[r["idx"] % 5])
                       for r in arms[fake_ban_from]]
    events = c1_events(arms, fc, head)
    res: dict[str, Any] = {"model": MODEL_ID, "chain_head": head, "dry_run_fake_ban": fake_ban_from}
    res["c1"] = c1_decision(events, fc)
    res["c1_coveto_sensitivity"] = covetosensitivity(events, fc)
    res["c2b"] = c2b_all(arms, events, fc, chain)
    res["descriptives"] = descriptives(store, arms, fc, chain)
    res["template_effect"] = TE.analyse([r for r in arms["ban"]], DEFAULTS)
    res["template_effect_placebo_shuffled"] = TE.placebo([r for r in arms["ban"]], DEFAULTS)
    mk = (not sub and not fake_ban_from) if make_figures is None else make_figures
    res["figures"] = figures(arms, events, res["c2b"], res["template_effect"]) if mk else []
    out_dir = out_dir or (RESULTS if not sub else RESULTS / f"dryrun_{sub}")
    write_jsonl(out_dir / "c1_events.jsonl", events)
    write_json(out_dir / "template_effect.json", {"main": res["template_effect"],
                                                  "placebo_template_shuffled": res["template_effect_placebo_shuffled"]})
    write_json(out_dir / "analysis.json", res)
    logger.info(f"C1 verdict: {res['c1']['verdict']} | gated {res['c1']['n_gated']} disagreeing "
                f"{res['c1']['n_gated_disagreeing']} | wins {res['c1']['advance']['wins']}")
    logger.info(f"C2b verdict (one-shot): {res['c2b']['oneshot']['verdict']} "
                f"(eligible {res['c2b']['oneshot']['n_eligible']})")
    return res


if __name__ == "__main__":
    from common import setup_logging

    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="smoke data with the nonce arm standing in for the ban")
    a = ap.parse_args()
    setup_logging("s3_analyze" + ("_dryrun" if a.dryrun else ""))
    if a.dryrun:
        run("smoke", fake_ban_from="nonce")
    else:
        run("")
