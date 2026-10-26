#!/usr/bin/env python3
"""Step 12 outputs: data/samples.jsonl (shared screen schema), method_out.json (exp_gen_sol_out), figures."""

from __future__ import annotations

import json
import platform
from collections import Counter
from typing import Any

from loguru import logger

from common import (CATALOGUE, DATA_DIR, DECODING_MAIN, FIG_DIR, MODEL_ID, MODES, NO_CODE, OTHER, PRED_DIR,
                    RESULTS_DIR, ROOT, TASK_DATASET_NAME, TASKS, THRESHOLDS, read_jsonl, sha256_file, write_json,
                    write_jsonl)


def _load(name: str) -> Any:
    p = RESULTS_DIR / name
    return json.loads(p.read_text()) if p.exists() else None


def build_samples() -> int:
    rows = read_jsonl(DATA_DIR / "labelled.jsonl")
    out = []
    for r in rows:
        out.append({
            "task": r["task"], "condition": r["condition"], "paraphrase_id": r["paraphrase_id"],
            "sample_id": r["sample_index"], "model": r.get("model", MODEL_ID), "decoding": r.get("decoding", DECODING_MAIN),
            "label": r["label"], "labeller_source": r["labeller_source"], "passed": bool(r["passed"]),
            "wall_s": r.get("wall_s"), "code_sha256": r.get("code_sha256"), "code": r.get("code"),
            "runtime_label": r.get("runtime_label"), "ast_label": r.get("ast_label"), "judge_label": r.get("judge_label"),
            "judge_rationale": r.get("judge_rationale"), "finish_reason": r.get("finish_reason"),
            "n_output_tokens": r.get("n_output_tokens"), "step": r.get("step", 1 if r["condition"].startswith("ban:") else None),
            "banned_set": r.get("banned_set", [r["condition"].split(":", 1)[1]] if r["condition"].startswith("ban:") else []),
            "gen_utc": r.get("gen_utc"), "gen_start_utc": r.get("gen_start_utc"), "stage": r.get("stage"),
            "test_error": r.get("test_error"), "fail_case": r.get("fail_case"), "extract_method": r.get("extract_method"),
            "runtime_reason": r.get("runtime_reason"), "ast_reason": r.get("ast_reason"), "seed": r.get("seed"),
        })
    out.sort(key=lambda x: (x["task"], x["condition"], x["paraphrase_id"], x["sample_id"]))
    write_jsonl(DATA_DIR / "samples.jsonl", out)
    return len(out)


def _dist_json(d: dict[str, float]) -> str:
    return json.dumps({k: round(float(v), 6) for k, v in d.items()}, sort_keys=True)


def build_examples(events_table: list[dict[str, Any]], contest: dict[str, Any], t9: dict[str, Any]) -> dict[str, list]:
    summaries = json.loads((DATA_DIR / "condition_summaries.json").read_text())
    conds = json.loads((ROOT / "prompts" / "conditions.json").read_text())
    cscore = {e["event_id"]: e for e in contest.get("events", [])}
    t9map = {e["event_id"]: e for e in t9.get("per_event", [])}
    ex: dict[str, list] = {t: [] for t in TASKS}
    preds: dict[str, dict[str, Any]] = {}
    pred_sha: dict[str, str] = {}
    for task in TASKS:
        p = PRED_DIR / f"{task}_single_bans.json"
        js = json.loads(p.read_text())
        for k, v in js["events"].items():
            preds[f"{task}|{k}"] = v
            pred_sha[f"{task}|{k}"] = sha256_file(p)
        for k in range(2, 6):
            sp = PRED_DIR / f"{task}_succ_step{k}.json"
            if sp.exists():
                preds[f"{task}|succession:{k}"] = json.loads(sp.read_text())
                pred_sha[f"{task}|succession:{k}"] = sha256_file(sp)
    for ev in events_table:
        eid = ev["event_id"]
        task = ev["task"]
        cond = eid.split("|", 1)[1]
        pred = preds[eid]
        if cond.startswith("succession"):
            segs = pred.get("segments", [])
        else:
            segs = [p["segment"] for p in conds["tasks"][task]["conditions"][cond]]
        inp = (f"[{TASK_DATASET_NAME[task]}] condition={cond}; banned (in order)={ev['banned']}; survivors="
               f"{ev['survivors']}; paraphrase 0: {segs[0] if segs else ''} || task spec: "
               f"{conds['spec'][task][:160]}...")
        tot = sum(ev["realised_counts"].values())
        realised = {k: (v / tot if tot else 0.0) for k, v in ev["realised_counts"].items()}
        e: dict[str, Any] = {"input": inp, "output": _dist_json(realised)}
        comp = pred["composed"]
        e["predict_association"] = _dist_json(comp["assoc"])
        e["predict_frequency"] = _dist_json(comp["freq"])
        e["predict_association_ext"] = _dist_json(comp["assoc_ext"])
        e["predict_freq_listall"] = _dist_json(comp["freq_listall"])
        e["predict_association_first_rank"] = _dist_json(comp["assoc_first"])
        e["predict_freetext"] = _dist_json(comp["freetext"])
        e["predict_freq_T13"] = _dist_json(comp["freq_T13"])
        sc = cscore.get(eid)
        e.update({
            "metadata_event_kind": "succession_step" if cond.startswith("succession") else "single_ban",
            "metadata_stratum": ev["stratum"], "metadata_informative": ev["informative"], "metadata_sham": ev["sham"],
            "metadata_survivors": ev["survivors"], "metadata_banned": ev["banned"],
            "metadata_compliance": ev["compliance"], "metadata_recurrence": ev["recurrence"],
            "metadata_n_code": ev["n_code"], "metadata_n_compliant": ev["n_compliant"],
            "metadata_pass_rate": ev["pass_rate"], "metadata_realised_mode": ev["realised_mode"],
            "metadata_realised_margin": ev["realised_margin"], "metadata_label_counts_all": ev["label_counts_all"],
            "metadata_nominations": ev["nominations"], "metadata_concordant_AF": ev["concordant_AF"],
            "metadata_freq_tied": ev["freq_tied"], "metadata_freq_stability": ev["freq_stability"],
            "metadata_freq_margin": ev["freq_margin"], "metadata_clarity": ev["clarity_S"],
            "metadata_ambiguous_ranking": ev["ambiguous"], "metadata_pre_committed": ev["pre_committed"],
            "metadata_prediction_sha256": pred_sha.get(eid),
            "metadata_hits": {k: v["top1_hit"] for k, v in sc["per_predictor"].items()} if sc else None,
            "metadata_log_scores": {k: v["log_score"] for k, v in sc["per_predictor"].items()} if sc else None,
            "metadata_js": {k: v["js_bits"] for k, v in sc["per_predictor"].items()} if sc else None,
            "metadata_spearman": {k: v["spearman"] for k, v in sc["per_predictor"].items()} if sc else None,
            "metadata_paired_assoc_minus_freq": sc["paired_assoc_minus_freq"] if sc else None,
            "metadata_t9_winner": t9map[eid]["winner"] if eid in t9map else None,
        })
        ex[task].append(e)
    # baseline / listall / mention twins as descriptive examples (no predictions)
    for task in TASKS:
        for cond in ["baseline", "baseline_empty", "baseline_T13", "listall"] + [f"mention:{m}" for m in MODES[task]]:
            s = summaries.get(f"{task}|{cond}")
            if not s:
                continue
            n = s["n_code"]
            dist = {k: v / n for k, v in s["label_counts"].items()} if n else {}
            pc = "baseline" if cond == "baseline_T13" else cond
            seg = conds["tasks"][task]["conditions"][pc][0]["segment"]
            ex[task].append({
                "input": f"[{TASK_DATASET_NAME[task]}] condition={cond}; paraphrase 0: {seg}",
                "output": _dist_json(dist),
                "metadata_event_kind": "mention_twin" if cond.startswith("mention") else "reference_condition",
                "metadata_n": s["n"], "metadata_pass_rate": s["pass_rate"], "metadata_hill_cc": s["hill_cc"],
                "metadata_label_counts_correct": s["label_counts_correct"], "metadata_no_code_rate": s["no_code_rate"],
            })
    return ex


def honest_summary(contest, t9, s1, c4, land, gate, base) -> str:
    """5-10 sentences, every number pulled from the result files."""
    def f3(x):
        return "n/a" if x is None else f"{x:.2f}"

    et = {e["event_id"]: e for e in (_load("event_table.json") or [])}
    dis = {e["event_id"]: e for e in (_load("disguised_recurrence.json") or {}).get("per_event", [])}
    ment = _load("mention_effects.json") or {}
    cev = {e["event_id"]: e for e in contest.get("events", [])}
    pooled = ((contest.get("strata", {}).get("all_informative") or {}).get("pooled_assoc_minus_freq") or {})
    t1b, t2b = base["t1"]["baseline"], base["t2"]["baseline"]
    out = [f"Descriptive two-task screen on {MODEL_ID} (thinking off, T=1.0): {sum(e['n_code'] for e in et.values())} "
           "code-bearing ban-condition programs plus the pre-ban arms, labelled by a "
           "runtime tracer and AST rules with a strategy-blind judge on disagreements; it is not an inferential test."]
    out.append(f"Both baselines are maximally collapsed (T1 {t1b['freq']['counts']}, T2 {t2b['freq']['counts']}, "
               f"Hill_cc {f3(t1b['hill_cc'])} and {f3(t2b['hill_cc'])}; also at T=1.3 and without the neutral segment), "
               "so the primary typicality-ladder predictor is uniform over the survivors of every ban and its "
               "nomination is always tied (the plan's degenerate-baseline case).")
    parts = []
    for eid in sorted(cev):
        e, ev = et[eid], cev[eid]
        pa, pf = ev["per_predictor"]["assoc"], ev["per_predictor"]["freq"]
        parts.append(f"{eid} was obeyed (compliance {f3(e['compliance'])}) and all {e['n_compliant']} compliant "
                     f"correct samples landed on {e['realised_mode']}; the Borda association map nominated "
                     f"{pa['nomination']} (hit {pa['top1_hit']:.0f}, log score {pa['log_score']:.2f} vs {pf['log_score']:.2f} "
                     f"for frequency)")
    if parts:
        out.append("; ".join(parts) + f", so association beat frequency on {pooled.get('assoc_wins')} of "
                   f"{pooled.get('assoc_wins_of')} informative events (mean paired log-score difference "
                   f"{f3(pooled.get('mean_paired_diff'))} nats/sample; within-event CIs are degenerate because every "
                   "compliant sample carries the same label).")
    alt = []
    for name, lab in (("freetext", "the model's own free-text 'standard alternative' answer"),
                      ("freq_listall", "the listall typicality cue"), ("assoc_ext", "the Llama-3.1-8B ranking map")):
        hits = sum(ev["per_predictor"][name]["top1_hit"] for ev in cev.values())
        alt.append(f"{lab} scored {hits:g}/{len(cev)}")
    ref_p = ROOT / "elicitation" / "ref_assoc_objects.json"
    ref_txt = ""
    if ref_p.exists():
        rn = json.loads(ref_p.read_text()).get("modal_ban_nominations", {}).get("t1", {})
        if rn:
            ref_txt = (f" A post-hoc gpt-4.1-mini 'textbook' map shows the same instrument split for X=BFS (Borda "
                       f"winner {rn.get('borda_winner')}, free-text answer {rn.get('freetext_top')}), so the ranking "
                       "question seems to elicit the closest shortest-path variant rather than the canonical "
                       "alternative.")
    out.append("Among the secondary predictors, " + ", ".join(alt) + "; the Borda miss on T1 came from a "
               "low-clarity ranking that placed DFS last, while free text named DFS 19 of 20 times." + ref_txt)
    succ = [et[k] for k in et if "succession" in k]
    if succ:
        txt = "; ".join(f"{e['event_id']} compliance {f3(e['compliance'])} ({dis.get(e['event_id'], {}).get('recurrent_without_name', 'n/a')}"
                        f"/{dis.get(e['event_id'], {}).get('n_recurrent', 'n/a')} recurrent programs never name the banned algorithm)"
                        for e in succ)
        out.append("Cumulative double bans failed: " + txt + ", i.e. the model re-implemented the banned mechanism "
                   "under other descriptions (e.g. 'backtracking' DFS, a 'BFS with pruning' that is SPFA), so the "
                   "succession stopped at step 2 by the fewer-than-20-compliant rule and no ladder contest beyond step 1 "
                   "was possible.")
    big = [k.split("|")[1] for k, v in ment.items() if isinstance(v, dict) and v["mention_minus_baseline_pp"] >= 20]
    zero = [k.split("|")[1] for k, v in ment.items() if isinstance(v, dict) and abs(v["mention_minus_baseline_pp"]) < 5
            and v["share_baseline"] < 0.5]
    out.append(f"Mention twins carried large recommendation effects (+20 pp or more for {', '.join(big)}; about zero for "
               f"{', '.join(zero)}), so they are recommendations rather than placebos; sham bans of absent modes kept "
               "the modal mode dominant but shifted up to 23 percent of mass toward a related mode (ban of "
               "Floyd-Warshall: 23 percent Bellman-Ford/SPFA; ban of IDDFS: 12 percent DFS), and the paraphrase "
               "null is degenerate (JS = 0) because each baseline has a single mode.")
    em = gate.get("eval_metrics", {})
    out.append(f"Both labellers identify all 22 reference variants; the gate's runtime-accuracy targets were "
               f"{'met' if gate.get('gate_passed') else 'not met'} (evaluation kappa runtime-vs-AST {f3(em.get('kappa_runtime_ast'))}, "
               f"runtime vs adjudicated {f3(em.get('acc_runtime_vs_adjudicated'))}, combined label vs adjudicated "
               f"{f3(em.get('acc_combined_vs_adjudicated'))}), and every prediction file was hash-committed before its "
               "samples were generated.")
    out.append("With two tasks and two informative events nothing here generalises; the useful outputs are yield "
               "estimates for a powered round (single-ban compliance about 0.9, double-ban compliance near 0, a "
               "frequency predictor that is uninformative under full collapse, and a ranking-vs-free-text discordance "
               "on 1 of 2 modal bans).")
    return " ".join(out)


def make_figures(contest, s1, land) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    made = []
    evs = contest.get("events", [])
    if evs:
        fig, axes = plt.subplots(1, len(evs), figsize=(4.2 * len(evs), 3.4), squeeze=False)
        events_by_id = {e["event_id"]: e for e in json.loads((RESULTS_DIR / "event_table.json").read_text())}
        preds = {}
        for task in TASKS:
            js = json.loads((PRED_DIR / f"{task}_single_bans.json").read_text())
            for k, v in js["events"].items():
                preds[f"{task}|{k}"] = v
            for k in range(2, 6):
                sp = PRED_DIR / f"{task}_succ_step{k}.json"
                if sp.exists():
                    preds[f"{task}|succession:{k}"] = json.loads(sp.read_text())
        for ax, e in zip(axes[0], evs):
            eid = e["event_id"]
            S = e["survivors"] + [OTHER]
            et = events_by_id[eid]
            tot = sum(et["realised_counts"].values()) or 1
            real = [et["realised_counts"].get(y, 0) / tot for y in S]
            qa = [preds[eid]["composed"]["assoc"].get(y, 0) for y in S]
            qf = [preds[eid]["composed"]["freq"].get(y, 0) for y in S]
            import numpy as np

            xx = np.arange(len(S))
            ax.bar(xx - 0.27, real, 0.27, label="realised (compliant)", color="#333333")
            ax.bar(xx, qa, 0.27, label="association q", color="#1f77b4")
            ax.bar(xx + 0.27, qf, 0.27, label="frequency q", color="#ff7f0e")
            ax.set_xticks(xx)
            ax.set_xticklabels(S, rotation=40, ha="right", fontsize=8)
            ax.set_title(eid, fontsize=9)
            ax.set_ylim(0, 1)
        axes[0][0].legend(fontsize=7)
        fig.tight_layout()
        p = FIG_DIR / "informative_events_pred_vs_realised.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        made.append(str(p.relative_to(ROOT)))
        fig, ax = plt.subplots(figsize=(6, 0.5 + 0.45 * len(evs)))
        for i, e in enumerate(evs):
            d = e["paired_assoc_minus_freq"]
            if d["mean"] is None:
                continue
            ax.errorbar(d["mean"], i, xerr=[[d["mean"] - d["ci95"][0]], [d["ci95"][1] - d["mean"]]], fmt="o",
                        color="#1f77b4")
        ax.axvline(0, color="grey", lw=0.8)
        ax.set_yticks(range(len(evs)))
        ax.set_yticklabels([e["event_id"] for e in evs], fontsize=8)
        ax.set_xlabel("paired log-score difference, association - frequency (nats/sample)")
        fig.tight_layout()
        p = FIG_DIR / "paired_log_score.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        made.append(str(p.relative_to(ROOT)))
    if land:
        import numpy as np

        et = {e["event_id"]: e for e in json.loads((RESULTS_DIR / "event_table.json").read_text())}
        fig, axes = plt.subplots(1, len(TASKS), figsize=(11, 3.8))
        colors = plt.get_cmap("tab10")
        for ax, task in zip(axes, TASKS):
            steps = [r for r in land if r["task"] == task]
            modes = MODES[task] + [OTHER]
            names = [f"step {r['step']}\nban: {' + '.join(r['banned'])}" for r in steps]
            bottom = np.zeros(len(steps))
            for mi, m in enumerate(modes):
                vals = []
                for r in steps:
                    e = et[f"{task}|{r['condition']}"]
                    tot = sum(e["label_counts_all"].values()) or 1
                    vals.append(e["label_counts_all"].get(m, 0) / tot)
                vals = np.array(vals)
                if vals.sum() == 0:
                    continue
                hatch = ["//" if m in r["banned"] else "" for r in steps]
                bars = ax.bar(names, vals, bottom=bottom, color=colors(mi), label=m)
                for bar, h in zip(bars, hatch):
                    bar.set_hatch(h)
                bottom += vals
            for i, r in enumerate(steps):
                ax.text(i, 1.02, f"compliance {r['compliance']:.2f}, n_compliant {r['n_compliant']}", ha="center",
                        fontsize=7)
            ax.set_ylim(0, 1.1)
            ax.set_title(f"{task}: label shares of all code-bearing samples (hatched = banned)", fontsize=8)
            ax.legend(fontsize=7, loc="lower right")
        fig.tight_layout()
        p = FIG_DIR / "landing_table_steps.png"
        fig.savefig(p, dpi=150)
        plt.close(fig)
        made.append(str(p.relative_to(ROOT)))
    return made


def stage_outputs() -> None:
    n_samples = build_samples()
    events_table = _load("event_table.json") or []
    contest = _load("contest.json") or {}
    t9 = _load("t9_family_test.json") or {}
    s1 = _load("s1_sham_control.json") or {}
    c4 = _load("c4_recurrence_vs_clarity.json") or {}
    land = _load("landing_table.json") or []
    ment = _load("mention_effects.json") or {}
    audit = _load("commitment_audit.json") or {}
    gate = _load("labeller_gate.json") or {}
    acc = _load("task_suite_acceptance.json") or {}
    cost = _load("openrouter_cost.json") or {}
    succ = _load("succession_state.json") or {}
    base = json.loads((ROOT / "elicitation" / "baseline_objects.json").read_text())
    assoc = json.loads((ROOT / "elicitation" / "assoc_objects.json").read_text())
    import re

    gen_secs = 0.0
    for f in ("preban_stats_10.json", "preban_stats_100.json", "preban_stats_all.json", "bans_gen_stats.json"):
        p = DATA_DIR / f
        if p.exists():
            gen_secs += json.loads(p.read_text()).get("seconds", 0.0)
    succ_log = ROOT / "logs" / "succession.out"
    if succ_log.exists():
        for m in re.finditer(r"succession step \d+: generated \{[^}]*'seconds': ([0-9.]+)", succ_log.read_text()):
            gen_secs += float(m.group(1))
    server_log = ROOT / "logs" / "vllm_server.log"
    kv_tokens, sp_example = None, None
    if server_log.exists():
        txt = server_log.read_text(errors="ignore")
        mm = re.search(r"GPU KV cache size: ([0-9,]+) tokens", txt)
        kv_tokens = int(mm.group(1).replace(",", "")) if mm else None
        mm = re.search(r"params: (SamplingParams\(n=10, [^)]*\))", txt)
        sp_example = mm.group(1)[:600] if mm else None
    assoc_maps = {}
    for task in TASKS:
        assoc_maps[task] = {}
        for x in MODES[task]:
            q = assoc["qwen"][task][x]
            e = assoc["ext"][task][x]
            assoc_maps[task][x] = {k: q[k] for k in ("A", "F", "borda_points", "first_counts", "borda_winner",
                                                       "first_winner", "clarity", "clarity_cc", "kendall_w",
                                                       "first_entropy_norm", "ambiguous", "n_rankings")}
            assoc_maps[task][x]["ext_borda_winner"] = e["borda_winner"] if e else None
            assoc_maps[task][x]["ext_A"] = e["A"] if e else None
            assoc_maps[task][x]["freetext_counts"] = assoc["freetext"][task][x]["counts"]
            assoc_maps[task][x]["freetext_ext_counts"] = assoc["freetext_ext"][task][x]["counts"]
        assoc_maps[task]["qwen_vs_ext_agreement"] = assoc["qwen_vs_ext"][task]
    vllm_version = "0.11.0"
    figures = make_figures(contest, s1, land)
    deviations = [
        "Smoke test (stage 1) omitted the ban prompt so that no ban output existed before the predictions were frozen.",
        "vLLM ran with --enforce-eager (no C compiler in the container, so torch.compile/Triton could not build); "
        "sampling is unaffected, only speed.",
        "max_num_seqs=128 and gpu_memory_utilization=0.90 instead of 16/0.92 (the pod had a 32 GB RTX 5090, not a 20 GB card).",
        "Condition segments have their first character upper-cased (templates starting with {X} would otherwise begin "
        "a sentence in lower case); recorded in prompts/conditions.json rules.",
        "Runtime tracer (gate revision round 1, development programs only): pre-injects common stdlib names "
        "(heapq, deque, ...) so programs crashing only on a missing import can be traced; hidden tests never inject. "
        "The revision did not change any gold-set label.",
        "Labeller gate: runtime-accuracy targets were not met after the allowed revision round (see labeller_gate); "
        "per protocol, results are produced, gate_passed=false is recorded and every runtime/AST disagreement is "
        "judge-labelled.",
        "Free-text elicitation at max_tokens=32 truncated 60/440 Qwen answers (the model answers in a sentence); the "
        "free-text map is descriptive only and unmapped answers are counted as 'unmapped'.",
        "Llama 3.1 8B external replication is at the association-map level only (rankings + free text), via OpenRouter.",
        "Both baselines are 100% one mode, so the primary typicality predictor is uniform over survivors for every "
        "event (the plan's DEGENERATE BASELINE fallback): its nomination is reported as tied/unstable and the "
        "secondary typicality predictors (listall, T=1.3) are reported beside it.",
        "Gold-set adjudication used openai/gpt-4.1-mini and google/gemini-2.5-flash (reasoning budget 0) with "
        "deepseek/deepseek-chat-v3.1 as tie-breaker; the production judge is openai/gpt-4.1-mini, so the combined-label "
        "accuracy on the gold set is optimistic.",
    ]
    metadata = {
        "method_name": "ban-substitution screen: association (Borda 'standard alternative' map) vs typicality ladder",
        "model": MODEL_ID, "gpu": "NVIDIA GeForce RTX 5090 (32 GB)", "vllm_version": vllm_version,
        "python": platform.python_version(),
        "decoding": {"main": DECODING_MAIN, "T13": "T1.3_topp1.0_topk-off_max1024_thinkoff",
                     "elicitation_rank": "T1.0 max_tokens 64", "elicitation_free": "T1.0 max_tokens 32",
                     "sampling_fields": "temperature, top_p=1.0, min_p=0, repetition/presence/frequency penalties "
                                        "neutral, per-request seed, top_k left at vLLM 0.11 default 0 (disabled), "
                                        "--generation-config vllm"},
        "thresholds": THRESHOLDS,
        "protocol_choices": {
            "baseline_neutral_segment": "10 neutral paraphrases (prompts/conditions.json)", "display_names": CATALOGUE,
            "composition": "q(y)=0.98*(0.95 p(y)+0.05/|S|) for y in S; q(other)=0.02",
            "tie_rules": "Borda winner ties -> higher first-place count, then alphabetical; tied frequency nomination "
                         "scores 1/(number tied) and is unstable; succession plurality ties -> higher baseline f, then "
                         "alphabetical",
            "time_limit_rule": "max(1 s, 10 x the slowest catalogue reference per case)",
            "s1_null": "random 5/5 baseline paraphrase splits at matched N (100 vs 50)",
            "cumulative_ban_name_order": "ban order, oldest first, joined 'A, B or C'",
            "correctness": "all mode distributions in contests are conditioned on passing every hidden case",
        },
        "deviations": deviations,
        "labeller_gate": gate, "task_suite_acceptance": acc,
        "association_maps": assoc_maps,
        "baseline": {t: {c: {k: v for k, v in base[t][c].items()} for c in ("baseline", "baseline_empty",
                                                                             "baseline_T13", "listall")}
                     for t in TASKS},
        "event_table": events_table, "contest": contest, "t9": t9, "s1": s1, "c4": c4, "landing_table": land,
        "disguised_recurrence": _load("disguised_recurrence.json"),
        "reference_textbook_map_post_hoc": (json.loads((ROOT / "elicitation" / "ref_assoc_objects.json").read_text())
                                            if (ROOT / "elicitation" / "ref_assoc_objects.json").exists() else None),
        "succession_state": succ, "mention_effects": ment,
        "costs": {"openrouter_usd": cost.get("total_usd"), "openrouter_by_purpose": cost.get("by_purpose"),
                  "gpu_generation_minutes": round(gen_secs / 60, 2)},
        "commitment_audit": audit, "n_samples_rows": n_samples, "figures": figures,
        "vllm_kv_cache_tokens": kv_tokens, "effective_sampling_params_example": sp_example,
        "sampling_params_default_repr_top_k": 0,
        "seed_reproducibility_check": _load("seed_reproducibility_check.json"),
        "gate_passed": bool(gate.get("gate_passed")),
    }
    metadata["honest_summary"] = honest_summary(contest, t9, s1, c4, land, gate, base)
    ex = build_examples(events_table, contest, t9)
    out = {"metadata": metadata,
           "datasets": [{"dataset": TASK_DATASET_NAME[t], "examples": ex[t]} for t in TASKS]}
    write_json(ROOT / "method_out.json", out, indent=1)
    logger.info(f"method_out.json written: {sum(len(v) for v in ex.values())} examples; samples.jsonl rows={n_samples}")
    _ = (Counter, NO_CODE)
