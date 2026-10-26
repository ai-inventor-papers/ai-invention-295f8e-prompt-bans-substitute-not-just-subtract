"""S13/S14: judge adjudication, screen readouts, swap, knob table, probes, verdict, figures and method_out.json."""

from __future__ import annotations

import ast
import collections
import json
import keyword
import math
import re
import time
from pathlib import Path

import numpy as np
from loguru import logger

from analysis.cpd import binseg, pelt_cv, perm_chi2
from common import (FIG_DIR, GEN_DIR, LOG_DIR, ROOT, STATE_DIR, SUM_DIR, entropy_bits, hill1, js_div, read_jsonl,
                    sha256_file, stable_seed, tvd, wilson)
from labeller.evidence import PAT
from tasks import t1_grid, t2_wsp

CATS = {"T1": t1_grid.CATALOGUE + ["other", "no_code"], "T2": t2_wsp.CATALOGUE + ["other", "no_code"]}
BANNED = {"T1": t1_grid.BANNED_MODE, "T2": t2_wsp.BANNED_MODE}
TASKN = {"T1": "T1_unweighted_grid_path", "T2": "T2_weighted_shortest_path"}
GRID_FULL = list(range(4, 93, 4))
GRID_BASELINE = [4, 8, 16, 32, 64]
KNOB_ARMS = [("global_T0.3", "G3_T0.3"), ("global_T0.7", "G3_T0.7"), ("global_T1.0", "G1"),
             ("global_T1.3", "G3_T1.3"), ("FORK", "A4_FORK"), ("RANDOM_WINDOW", "A4_RANDOM_WINDOW"),
             ("ANCHORED", "A4_ANCHORED")]


def counts_of(task, labels):
    c = np.zeros(len(CATS[task]))
    for lab in labels:
        c[CATS[task].index(lab if lab in CATS[task] else "other")] += 1
    return c


# =============================================================================================== judge
def adjudicate(rows_by_file: dict) -> dict:
    from labeller.judge import JUDGE_A, JUDGE_B, JUDGE_C, Budget, make_prompt, run_judge
    budget = Budget()
    out: dict = {"models": [JUDGE_A, JUDGE_B, JUDGE_C]}
    pools = rows_by_file["pools"]
    # ---------------- gold set: references + 10 G1 + 5 G2 per task
    gold = []
    for task, T in (("T1", t1_grid), ("T2", t2_wsp)):
        for name, (lab, code) in T.REFERENCES.items():
            gold.append({"task": task, "id": name, "code": code, "ref_label": lab, "kind": "reference"})
        for arm, k in (("G1", 10), ("G2", 5)):
            cand = [r for r in pools if r["task"] == task and r["arm"] == arm and r.get("code")]
            cand.sort(key=lambda r: (r["paraphrase_id"], r["sample_id"]))
            step = max(1, len(cand) // k)
            for r in cand[::step][:k]:
                gold.append({"task": task, "id": f"{arm}|{r['paraphrase_id']}|{r['sample_id']}", "code": r["code"],
                             "ref_label": None, "kind": arm, "runtime_label": r["runtime_label"],
                             "ast_label": r["ast_label"], "final_label": r["label"]})
    # tracer/AST labels for references come from logs/test_labeller.json (sandboxed run)
    tl = json.loads((LOG_DIR / "test_labeller.json").read_text()) if (LOG_DIR / "test_labeller.json").exists() else {}
    ref_rt = {(x["task"], x["name"]): x for x in tl.get("rows", [])}
    from labeller.ast_rules import ast_label
    for g in gold:
        if g["kind"] == "reference":
            x = ref_rt.get((g["task"], g["id"]), {})
            g["runtime_label"] = x.get("runtime_label")
            g["ast_label"] = ast_label(g["task"], g["code"])[0]
            g["final_label"] = g["runtime_label"] or g["ast_label"]
    items = []
    for g in gold:
        pr, labels = make_prompt(g["task"], g["code"])
        items.append({"model": JUDGE_A, "prompt": pr, "labels": labels})
        items.append({"model": JUDGE_B, "prompt": pr, "labels": labels})
    t0 = time.time()
    res = run_judge(items, budget)
    adj_items, adj_idx = [], []
    for i, g in enumerate(gold):
        a, b = res[2 * i]["label"], res[2 * i + 1]["label"]
        g["judge_a"], g["judge_b"] = a, b
        if a is not None and a == b:
            g["adjudicated"] = a
        else:
            pr, labels = make_prompt(g["task"], g["code"])
            adj_items.append({"model": JUDGE_C, "prompt": pr, "labels": labels})
            adj_idx.append(i)
    for i, r in zip(adj_idx, run_judge(adj_items, budget)):
        g = gold[i]
        g["adjudicated"] = r["label"] or g.get("judge_a") or g.get("judge_b")
    logger.info(f"gold set judged: {len(gold)} programs, spent ${budget.spent:.4f} in {time.time() - t0:.0f}s")

    def kappa(a, b):
        labs = sorted(set(a) | set(b))
        if len(a) == 0:
            return float("nan")
        po = np.mean([x == y for x, y in zip(a, b)])
        pe = sum((a.count(l) / len(a)) * (b.count(l) / len(b)) for l in labs)
        return float((po - pe) / (1 - pe)) if pe < 1 else 1.0

    gate = {}
    for task in ("T1", "T2"):
        gs = [g for g in gold if g["task"] == task]
        refs = [g for g in gs if g["kind"] == "reference"]
        rt = [str(g["runtime_label"]) for g in gs]
        al = [str(g["ast_label"]) for g in gs]
        fin = [str(g["final_label"]) for g in gs]
        adj = [str(g.get("adjudicated")) for g in gs]
        gate[task] = {
            "n_gold": len(gs),
            "refs_runtime_correct": sum(g["runtime_label"] == g["ref_label"] for g in refs),
            "refs_ast_correct": sum(g["ast_label"] == g["ref_label"] for g in refs),
            "refs_final_correct": sum(g["final_label"] == g["ref_label"] for g in refs),
            "n_refs": len(refs),
            "kappa_tracer_vs_ast": kappa(rt, al),
            "kappa_final_vs_ast": kappa(fin, al),
            "agree_final_vs_adjudicated": float(np.mean([x == y for x, y in zip(fin, adj)])),
            "agree_tracer_vs_adjudicated": float(np.mean([x == y for x, y in zip(rt, adj)])),
            "judges_agree_rate": float(np.mean([g.get("judge_a") == g.get("judge_b") for g in gs])),
            "refs_adjudicated_correct": sum(g.get("adjudicated") == g["ref_label"] for g in refs),
        }
        gt = gate[task]
        gt["pass"] = bool(gt["refs_final_correct"] == gt["n_refs"] and gt["refs_ast_correct"] == gt["n_refs"]
                          and gt["kappa_final_vs_ast"] >= 0.8 and gt["agree_final_vs_adjudicated"] >= 0.9)
    out["gold"] = [{k: v for k, v in g.items() if k != "code"} for g in gold]
    out["gate"] = gate
    # ---------------- disagreements / 'other' in confirmation, swap, knob and decoder sets (single judge B)
    targets = []
    for fname in ("confirm", "swap", "knob", "pools"):
        for r in rows_by_file.get(fname, []):
            if fname == "pools" and r["arm"] not in ("G1", "G2"):
                continue
            if not r.get("code"):
                continue
            if (r.get("runtime_label") and r.get("ast_label") and r["runtime_label"] != r["ast_label"]) or \
                    r["label"] == "other":
                targets.append(r)
    uniq = {}
    for r in targets:
        uniq.setdefault((r["task"], r["code_sha256"]), r)
    keys = list(uniq.keys())
    est = len(keys) * 0.0006
    logger.info(f"judging {len(keys)} distinct disputed programs (est ${est:.3f}); spent so far ${budget.spent:.4f}")
    items = []
    for k in keys:
        pr, labels = make_prompt(k[0], uniq[k]["code"])
        items.append({"model": JUDGE_B, "prompt": pr, "labels": labels})
    jres = run_judge(items, budget) if not budget.stopped else []
    jmap = {k: r["label"] for k, r in zip(keys, jres) if r.get("label")}
    out["disputed_judged"] = len(jmap)
    out["disputed_total"] = len(keys)
    out["cost_usd"] = budget.spent
    out["calls"] = budget.calls
    out["budget_stopped"] = budget.stopped
    out["jmap"] = {f"{k[0]}|{k[1]}": v for k, v in jmap.items()}
    return out


def apply_final_labels(rows_by_file: dict, jmap: dict) -> None:
    for fname, rows in rows_by_file.items():
        for r in rows:
            r["label_final"] = r["label"]
            disputed = r.get("runtime_label") and r.get("ast_label") and r["runtime_label"] != r["ast_label"]
            key = f"{r['task']}|{r.get('code_sha256')}"
            judged_set = fname in ("confirm", "swap", "knob") or (fname == "pools" and r["arm"] in ("G1", "G2"))
            if judged_set and key in jmap and (disputed or r["label"] == "other"):
                r["judge_label"] = jmap[key]
                r["label_final"] = jmap[key]
                r["labeller_source_final"] = "judge"
            elif disputed:
                r["labeller_source_final"] = "runtime_unadjudicated" if fname in ("screen", "localise") else \
                    (r.get("labeller_source") or "runtime")
            else:
                r["labeller_source_final"] = r.get("labeller_source")


# =============================================================================================== T6
def t6_sensitivity(n_sim: int = 200) -> dict:
    p = SUM_DIR / "t6_sensitivity.json"
    if p.exists():
        return json.loads(p.read_text())
    rng = np.random.default_rng(6)
    out = {}
    for tv in (0.0, 0.2, 0.3, 0.5):
        hit = anycp = 0
        for s in range(n_sim):
            p0 = np.array([0.7, 0.3, 0.0, 0.0])
            p1 = np.array([0.7 - tv, 0.3, tv, 0.0])
            cut = int(rng.integers(3, 21))
            C = np.stack([rng.multinomial(8, p0 if i < cut else p1) for i in range(23)])
            cps = binseg(C, n_perm=1000, seed=s)
            anycp += len(cps) > 0
            hit += any(c["index"] == cut for c in cps)
        out[str(tv)] = {"detect_right_bracket": hit / n_sim, "any_cp": anycp / n_sim}
    out["note"] = "23 positions x S=8, planted change at a random position; 1000 permutations; tv=0 is the null FP rate"
    p.write_text(json.dumps(out, indent=1))
    return out


# =============================================================================================== screen
def token_type(tok_str: str, prefix_text: str, task: str) -> str:
    s = tok_str.strip()
    if "```" in tok_str:
        return "code_fence"
    if s == "":
        return "whitespace_newline"
    if s in ("import", "from"):
        return "import_token"
    if PAT[task].search(s) and len(s) >= 3:
        return "lexicon_term"
    if keyword.iskeyword(s):
        return "python_keyword"
    if re.fullmatch(r"[0-9.]+", s):
        return "number"
    if re.fullmatch(r"[^\w\s]+", s):
        return "punctuation"
    in_code = "```python" in prefix_text and prefix_text.count("```") % 2 == 1
    if s.isidentifier() or re.fullmatch(r"\w+", s):
        return "identifier" if in_code else "natural_language_word"
    return "punctuation"


def screen_readouts(R: dict, tok) -> dict:
    pools = R["pools"]
    by_pos = collections.defaultdict(list)
    for fname in ("screen", "localise", "confirm"):
        for r in R.get(fname, []):
            if fname == "confirm" and r.get("is_control"):
                by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label_final"])
            else:
                by_pos[(r["base_path_id"], r["prefix_len"])].append(r["label_final"])
    prov = json.loads((SUM_DIR / "gen2_provisional.json").read_text()) if (SUM_DIR / "gen2_provisional.json").exists() \
        else {"candidates": [], "controls": [], "paths": []}
    nts = json.loads((SUM_DIR / "next_token.json").read_text()) if (SUM_DIR / "next_token.json").exists() else []
    ntmap = {(x["bp_id"], x["p"], x["kind"]): x for x in nts}
    paths = []
    for r in pools:
        if r["sample_id"] != 0 or not ((r["arm"] == "G1") or r["arm"] == "G2"):
            continue
        bp = f"{r['task']}|{r['condition']}|{r['paraphrase_id']}"
        o0 = [x["label_final"] for x in pools if x["arm"] == r["arm"] and x["task"] == r["task"]
              and x["paraphrase_id"] == r["paraphrase_id"] and x["sample_id"] != 0]
        final = r["label_final"]
        grid = [p for p in (GRID_FULL if r["condition"] == "ban" else GRID_BASELINE) if (bp, p) in by_pos]
        if not grid:
            continue
        a = {0: float(np.mean([x == final for x in o0]))}
        for p in grid:
            labs = by_pos[(bp, p)]
            a[p] = float(np.mean([x == final for x in labs]))
        positions = [0] + grid
        C = np.stack([counts_of(r["task"], o0 + by_pos.get((bp, 0), []))] +
                     [counts_of(r["task"], by_pos[(bp, p)]) for p in grid])
        cps = binseg(C, n_perm=1000, seed=stable_seed(bp, "final") % 2 ** 32)
        cps_no0 = binseg(C[1:], n_perm=1000, seed=stable_seed(bp, "final0") % 2 ** 32) if len(grid) > 1 else []
        lab_lists = [[CATS[r["task"]].index(l if l in CATS[r["task"]] else "other") for l in (o0 if i == 0 else
                      by_pos[(bp, positions[i])])] for i in range(len(positions))]
        try:
            pelt = pelt_cv(C, lab_lists, len(CATS[r["task"]]), seed=1)
        except Exception as e:  # noqa: BLE001
            pelt = {"error": str(e)}
        fixed_by = {}
        for k in (0, 8, 16, 32, 64):
            ps = [p for p in positions if p >= k]
            fixed_by[k] = bool(ps) and all(a[p] >= 7 / 8 for p in ps)
        paths.append({"bp_id": bp, "task": r["task"], "condition": r["condition"], "pid": r["paraphrase_id"],
                      "final_label": final, "commit_idx": r["commit_idx"], "evidence_term": r["evidence_term"],
                      "agreement": {str(k): v for k, v in a.items()}, "o0_counts": counts_of(r["task"], o0).tolist(),
                      "R0_decided": a[0] >= 0.8, "fixed_by": fixed_by,
                      "change_points": [{"bracket": [positions[c["index"] - 1], positions[c["index"]]],
                                         "G": c["G"], "threshold": c["threshold"], "p_perm": c["p_perm"]} for c in cps],
                      "change_points_without_o0": [{"bracket": [grid[c["index"] - 1], grid[c["index"]]],
                                                    "p_perm": c["p_perm"]} for c in cps_no0],
                      "pelt": pelt, "gen_ids": r["gen_token_ids"],
                      "tvd_o0_final": tvd(counts_of(r["task"], o0), counts_of(r["task"], [final]))})
    pmap = {p["bp_id"]: p for p in paths}

    def o_at(bp, p):
        labs = list(by_pos.get((bp, p), []))
        if p == 0:
            pr = pools_o0.get(bp, [])
            labs = pr + labs
        return counts_of(bp.split("|")[0], labs)

    pools_o0 = {}
    for r in pools:
        if r["arm"] in ("G1", "G2") and r["sample_id"] != 0:
            pools_o0.setdefault(f"{r['task']}|{r['condition']}|{r['paraphrase_id']}", []).append(r["label_final"])
    forks = []
    for c in prov.get("candidates", []):
        bp, t = c["bp_id"], int(c["t"])
        a_, b_ = o_at(bp, t), o_at(bp, t + 1)
        v = tvd(a_, b_)
        pv = perm_chi2(a_, b_, n_perm=2000, seed=stable_seed(bp, t) % 2 ** 32)
        lo, hi = c["bracket"]
        coarse = tvd(o_at(bp, lo), o_at(bp, hi))
        sharp = v / coarse if coarse and coarse > 0 else float("nan")
        p = pmap.get(bp)
        gen_ids = p["gen_ids"] if p else []
        tok_str = tok.decode([gen_ids[t]]) if t < len(gen_ids) else ""
        prefix_text = tok.decode(gen_ids[:t]) if gen_ids else ""
        nt = ntmap.get((bp, t, "fork_candidate"), {})
        rec = {"bp_id": bp, "task": bp.split("|")[0], "condition": bp.split("|")[1], "bracket": [lo, hi], "t": t,
               "token": tok_str, "token_type": token_type(tok_str, prefix_text, bp.split("|")[0]),
               "n_t": int(a_.sum()), "n_t1": int(b_.sum()), "tvd": v, "p_perm": pv, "coarse_tvd": coarse,
               "sharpness": sharp, "commit_idx": p["commit_idx"] if p else None,
               "precedes_commit": (p["commit_idx"] is not None and t < p["commit_idx"]) if p else None,
               "is_commit_token": (p["commit_idx"] == t) if p else None,
               "next_token_entropy_bits": nt.get("entropy_bits_top20"), "next_token_top": nt.get("top"),
               "outcome_entropy_before_bits": entropy_bits(a_), "outcome_entropy_after_bits": entropy_bits(b_),
               "o_t": a_.tolist(), "o_t1": b_.tolist()}
        for thr in (0.10, 0.15, 0.20, 0.30):
            rec[f"confirmed_tvd{thr:.2f}"] = bool(pv < 0.05 and v >= thr and sharp == sharp and sharp >= 0.5)
        rec["confirmed"] = rec["confirmed_tvd0.20"]
        forks.append(rec)
    controls = []
    for c in prov.get("controls", []):
        bp, q = c["bp_id"], int(c["q"])
        a_, b_ = o_at(bp, q), o_at(bp, q + 1)
        v = tvd(a_, b_)
        pv = perm_chi2(a_, b_, n_perm=2000, seed=stable_seed(bp, q) % 2 ** 32)
        nt = ntmap.get((bp, q, "control"), {})
        controls.append({"bp_id": bp, "q": q, "tvd": v, "p_perm": pv, "n_q": int(a_.sum()), "n_q1": int(b_.sum()),
                         "false_positive": bool(pv < 0.05 and v >= 0.20),
                         "next_token_entropy_bits": nt.get("entropy_bits_top20")})
    for p in paths:
        p["confirmed_forks"] = [f["t"] for f in forks if f["bp_id"] == p["bp_id"] and f["confirmed"]]
    # aggregate readouts
    agg = {}
    groups = {f"{t}|{c}": [p for p in paths if p["task"] == t and p["condition"] == c]
              for t in ("T1", "T2") for c in ("baseline", "ban")}
    groups["pooled|baseline"] = [p for p in paths if p["condition"] == "baseline"]
    groups["pooled|ban"] = [p for p in paths if p["condition"] == "ban"]
    for g, ps in groups.items():
        n = len(ps)
        if n == 0:
            continue
        r0 = sum(p["R0_decided"] for p in ps)
        nonfixed = [p for p in ps if not p["fixed_by"][0]]
        f1n = sum(1 for p in nonfixed if p["confirmed_forks"])
        f2 = []
        for p in ps:
            fs = [f for f in forks if f["bp_id"] == p["bp_id"] and f["confirmed"]]
            if fs and p["tvd_o0_final"] and p["tvd_o0_final"] > 0:
                f2.append(min(1.0, sum(f["tvd"] for f in fs) / p["tvd_o0_final"]))
        cond = g.split("|")[1]
        ctl = [c for c in controls if c["bp_id"].split("|")[1] == cond and (g.startswith("pooled") or
                                                                           c["bp_id"].startswith(g.split("|")[0]))]
        agg[g] = {"n_paths": n, "R0": wilson(r0, n), "R0_k": r0,
                  "fixed_by": {str(k): wilson(sum(p["fixed_by"][k] for p in ps), n) for k in (0, 8, 16, 32, 64)},
                  "n_nonfixed": len(nonfixed), "F1": wilson(f1n, len(nonfixed)) if nonfixed else None,
                  "F1_k": f1n, "F2_median": float(np.median(f2)) if f2 else None, "F2_n": len(f2),
                  "F3": wilson(sum(c["false_positive"] for c in ctl), len(ctl)) if ctl else None,
                  "n_controls": len(ctl), "n_candidates": sum(1 for f in forks if f["bp_id"] in {p["bp_id"] for p in ps}),
                  "n_confirmed": sum(1 for f in forks if f["confirmed"] and f["bp_id"] in {p["bp_id"] for p in ps}),
                  "n_paths_with_cp": sum(1 for p in ps if p["change_points"]),
                  "n_paths_with_cp_pelt": sum(1 for p in ps if p["pelt"].get("breakpoints")),
                  "label_counts_final": dict(collections.Counter(p["final_label"] for p in ps))}
    tt = collections.Counter((f["token_type"], f["confirmed"]) for f in forks)
    fork_nt = [f["next_token_entropy_bits"] for f in forks if f["confirmed"] and f["next_token_entropy_bits"] is not None]
    ctl_nt = [c["next_token_entropy_bits"] for c in controls if c["next_token_entropy_bits"] is not None]
    ent = {"fork_next_token_entropy_mean_bits": float(np.mean(fork_nt)) if fork_nt else None,
           "control_next_token_entropy_mean_bits": float(np.mean(ctl_nt)) if ctl_nt else None,
           "n_fork": len(fork_nt), "n_control": len(ctl_nt),
           "outcome_entropy_drop_mean_bits": float(np.mean([f["outcome_entropy_before_bits"] -
                                                            f["outcome_entropy_after_bits"] for f in forks
                                                            if f["confirmed"]])) if any(f["confirmed"] for f in forks) else None}
    for p in paths:
        p.pop("gen_ids", None)
    return {"paths": paths, "forks": forks, "controls": controls, "aggregate": agg,
            "token_type_table": {f"{k[0]}|{'confirmed' if k[1] else 'unconfirmed'}": v for k, v in tt.items()},
            "entropy": ent}


# =============================================================================================== swap
def swap_readouts(R: dict) -> dict:
    rows = R.get("swap", [])
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["base_path_id"], r["swap_side"], r["swap_prompt"])].append(r["label_final"])
    paths = sorted({r["base_path_id"] for r in rows})
    out = []
    for bp in paths:
        task = bp.split("|")[0]
        ban_lab = BANNED[task]
        rec = {"bp_id": bp, "task": task}
        cut = next(r["cut"] for r in rows if r["base_path_id"] == bp)
        rec["cut"] = cut
        rec["cut_source"] = next(r["cut_source"] for r in rows if r["base_path_id"] == bp)
        for side in ("pre", "post"):
            bl = by[(bp, side, "ban")]
            bs = by[(bp, side, "baseline")]
            rec[f"{side}_ban_banned_share"] = float(np.mean([x == ban_lab for x in bl])) if bl else None
            rec[f"{side}_base_banned_share"] = float(np.mean([x == ban_lab for x in bs])) if bs else None
            rec[f"{side}_js_ban_vs_base"] = js_div(counts_of(task, bl), counts_of(task, bs)) if bl and bs else None
            rec[f"{side}_ban_effect"] = (rec[f"{side}_base_banned_share"] - rec[f"{side}_ban_banned_share"]) \
                if bl and bs else None
            rec[f"{side}_n_ban"], rec[f"{side}_n_base"] = len(bl), len(bs)
        rec["lock_in"] = rec["post_ban_banned_share"]
        out.append(rec)
    agg = {}
    rng = np.random.default_rng(10)
    for g in ("T1", "T2", "pooled"):
        ps = [p for p in out if g == "pooled" or p["task"] == g]
        if not ps:
            continue
        d = {}
        for key in ("pre_ban_effect", "post_ban_effect", "pre_ban_banned_share", "post_ban_banned_share",
                    "pre_js_ban_vs_base", "post_js_ban_vs_base"):
            v = np.array([p[key] for p in ps if p[key] is not None], float)
            if len(v):
                bs = [rng.choice(v, len(v)).mean() for _ in range(1000)]
                d[key] = {"mean": float(v.mean()), "ci": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                          "n": int(len(v))}
        diff = np.array([p["pre_ban_effect"] - p["post_ban_effect"] for p in ps
                         if p["pre_ban_effect"] is not None and p["post_ban_effect"] is not None])
        if len(diff):
            bs = [rng.choice(diff, len(diff)).mean() for _ in range(1000)]
            d["pre_minus_post_effect"] = {"mean": float(diff.mean()), "ci": [float(np.quantile(bs, .025)),
                                                                            float(np.quantile(bs, .975))]}
            d["prediction_pre_gt_post_holds"] = bool(diff.mean() > 0 and np.quantile(bs, .025) > 0)
        d["lock_in_rate"] = d.get("post_ban_banned_share")
        agg[g] = d
    return {"paths": out, "aggregate": agg}


# =============================================================================================== knob
def shingles(code: str) -> set:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    toks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and \
                isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.Constant):
            toks.append("CONST")
        elif isinstance(node, ast.Name):
            toks.append("ID")
        elif isinstance(node, ast.Attribute):
            toks.append(f"Attr.{node.attr}")
        elif isinstance(node, (ast.FunctionDef, ast.arg)):
            toks.append(type(node).__name__)
        else:
            toks.append(type(node).__name__)
    return {tuple(toks[i:i + 4]) for i in range(max(0, len(toks) - 3))}


def components(sh: list[set], theta: float) -> list[int]:
    n = len(sh)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(n):
        for j in range(i + 1, n):
            a, b = sh[i], sh[j]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac >= theta:
                parent[find(i)] = find(j)
    return [find(i) for i in range(n)]


def phrasing(rows: list[dict], theta: float, rng) -> dict:
    ok = [r for r in rows if r["passed"] and r.get("code")]
    by_mode = collections.defaultdict(list)
    for r in ok:
        by_mode[r["label_final"]].append(shingles(r["code"]))
    n_clusters = 0
    hills = []
    for mode, sh in by_mode.items():
        comp = components(sh, theta)
        cnt = collections.Counter(comp)
        n_clusters += len(cnt)
        hills.append((len(sh), hill1(comp)))
    tot = sum(n for n, _ in hills)
    wh = sum(n * h for n, h in hills) / tot if tot else float("nan")
    rare = []
    if len(ok) >= 20:
        allsh = [(r["label_final"], shingles(r["code"])) for r in ok]
        for _ in range(30):
            pick = rng.choice(len(allsh), 20, replace=False)
            sub = collections.defaultdict(list)
            for i in pick:
                sub[allsh[i][0]].append(allsh[i][1])
            rare.append(sum(len(set(components(v, theta))) for v in sub.values()))
    return {"n_clusters": n_clusters, "within_mode_phrasing_hill": wh,
            "rarefied_clusters_n20": float(np.mean(rare)) if rare else None}


def knob_table(R: dict) -> dict:
    pools = R["pools"]
    knob = R.get("knob", [])
    rng = np.random.default_rng(11)
    table = {}
    arm_rows = {}
    for task in ("T1", "T2"):
        table[task] = {}
        for name, arm in KNOB_ARMS:
            src = pools if arm.startswith("G") else knob
            rows = [r for r in src if r["task"] == task and r["arm"] == arm and (arm != "G1" or r["sample_id"] < 10)]
            if not rows:
                continue
            arm_rows[(task, name)] = rows
            passed = [r for r in rows if r["passed"]]
            labs_cc = [r["label_final"] for r in passed]
            labs_all = [r["label_final"] for r in rows]
            pids = sorted({r["paraphrase_id"] for r in rows})
            bs_s, bs_c, bs_raw = [], [], []
            for _ in range(1000):
                pick = rng.integers(0, len(rows), len(rows))
                sub = [rows[i] for i in pick]
                bs_s.append(hill1([r["label_final"] for r in sub if r["passed"]]))
                cp = rng.choice(pids, len(pids))
                subc = [r for p in cp for r in rows if r["paraphrase_id"] == p]
                bs_c.append(hill1([r["label_final"] for r in subc if r["passed"]]))
                bs_raw.append(hill1([r["label_final"] for r in subc]))
            ph = {str(th): phrasing(rows, th, rng) for th in (0.7, 0.8, 0.9)}
            table[task][name] = {
                "n": len(rows), "pass_rate": wilson(len(passed), len(rows)),
                "hill_cc": hill1(labs_cc), "hill_cc_ci_sample": [float(np.nanquantile(bs_s, .025)),
                                                                float(np.nanquantile(bs_s, .975))],
                "hill_cc_ci_cluster": [float(np.nanquantile(bs_c, .025)), float(np.nanquantile(bs_c, .975))],
                "hill_raw": hill1(labs_all), "hill_raw_ci_cluster": [float(np.nanquantile(bs_raw, .025)),
                                                                     float(np.nanquantile(bs_raw, .975))],
                "label_counts": dict(collections.Counter(labs_all)),
                "label_counts_correct": dict(collections.Counter(labs_cc)), "phrasing": ph,
                "mean_len": float(np.mean([r["n_gen_tokens"] for r in rows]))}
    contrasts = {}
    for task in ("T1", "T2"):
        if (task, "FORK") not in arm_rows or (task, "RANDOM_WINDOW") not in arm_rows:
            continue

        def cl_diff(a_name, b_name):
            A, B = arm_rows[(task, a_name)], arm_rows[(task, b_name)]
            pa = sorted({r["paraphrase_id"] for r in A})
            pb = sorted({r["paraphrase_id"] for r in B})
            d = []
            for _ in range(2000):
                ca, cb = rng.choice(pa, len(pa)), rng.choice(pb, len(pb))
                ha = hill1([r["label_final"] for p in ca for r in A if r["paraphrase_id"] == p and r["passed"]])
                hb = hill1([r["label_final"] for p in cb for r in B if r["paraphrase_id"] == p and r["passed"]])
                d.append(ha - hb)
            obs = hill1([r["label_final"] for r in A if r["passed"]]) - hill1([r["label_final"] for r in B if r["passed"]])
            lo, hi = float(np.nanquantile(d, .025)), float(np.nanquantile(d, .975))
            return {"diff": obs, "ci": [lo, hi], "excludes_0_favouring_first": bool(lo > 0)}
        k1 = cl_diff("FORK", "RANDOM_WINDOW")
        k4 = cl_diff("ANCHORED", "FORK") if (task, "ANCHORED") in arm_rows else None
        # K2 frontier: global arms ordered by T, linear interpolation of hill_cc at FORK's pass rate
        pts = sorted([(table[task][n]["pass_rate"][0], table[task][n]["hill_cc"]) for n in
                      ("global_T0.3", "global_T0.7", "global_T1.0", "global_T1.3") if n in table[task]])
        fp, fh = table[task]["FORK"]["pass_rate"][0], table[task]["FORK"]["hill_cc"]
        xs = np.array([p[0] for p in pts])
        ys = np.array([p[1] for p in pts])
        order = np.argsort(xs)
        frontier_h = float(np.interp(fp, xs[order], ys[order])) if len(xs) else float("nan")
        k3 = {th: {"FORK": table[task]["FORK"]["phrasing"][th]["within_mode_phrasing_hill"],
                   "global_T1.3": table[task]["global_T1.3"]["phrasing"][th]["within_mode_phrasing_hill"],
                   "global_T0.3": table[task]["global_T0.3"]["phrasing"][th]["within_mode_phrasing_hill"]}
              for th in ("0.7", "0.8", "0.9")}
        contrasts[task] = {"K1_fork_minus_random_window": k1, "K2_fork_vs_frontier": {
            "fork_pass": fp, "fork_hill_cc": fh, "frontier_hill_cc_at_fork_pass": frontier_h,
            "fork_minus_frontier": fh - frontier_h}, "K3_phrasing_hill": k3, "K4_anchored_minus_fork": k4,
            "pred_fork_pass_ge_global_T1.0": bool(fp >= table[task]["global_T1.0"]["pass_rate"][0]),
            "pred_fork_phrasing_lt_T1.3": bool(k3["0.8"]["FORK"] < k3["0.8"]["global_T1.3"])}
    return {"table": table, "contrasts": contrasts}


# =============================================================================================== probes
def probe_readouts() -> dict:
    from analysis.probes import run_grid
    out = {}
    for task in ("T1", "T2"):
        from analysis.states import load_state_parts
        mp_ = STATE_DIR / f"{task}_meta.json"
        loaded = load_state_parts(task)
        if loaded is None or not mp_.exists():
            continue
        X, mask, ks = loaded
        meta = json.loads(mp_.read_text())
        rows = meta["rows"]
        labels = np.array([r["label"] for r in rows])
        conds = np.array([r["condition"] for r in rows])
        groups = np.array([hash((r["condition"], r["paraphrase_id"])) % 100000 for r in rows])
        commit = np.array([r["commit_idx"] if r["commit_idx"] is not None else 10 ** 6 for r in rows])
        res = {}
        for pool_name, sel in (("pooled", np.ones(len(rows), bool)), ("baseline", conds == "baseline"),
                               ("ban", conds == "ban")):
            idx = np.where(sel)[0]
            lab = labels[idx]
            cls, cnt = np.unique(lab, return_counts=True)
            lab2 = np.array([l if cnt[list(cls).index(l)] >= 5 else "rare" for l in lab])
            if (np.unique(lab2, return_counts=True)[1] >= 10).sum() < 2:
                res[pool_name] = {"undefined": True, "label_counts": dict(zip(cls.tolist(), cnt.tolist()))}
                continue
            y = np.array([str(l) for l in lab2])
            cells = run_grid(X[idx], mask[idx], y, groups[idx], meta["positions"], meta["layers"], workers=10)
            res[pool_name] = {"cells": cells, "label_counts": dict(zip(cls.tolist(), cnt.tolist()))}
            # latent subset: samples with commit_idx > k at k = 8, 16, 32, 64
            lat = {}
            for pi, pn in enumerate(meta["positions"]):
                if pn not in ("k8", "k16", "k32", "k64"):
                    continue
                k = int(pn[1:])
                sub = np.where(commit[idx] > k)[0]
                if len(sub) >= 20:
                    yy = y[sub]
                    if (np.unique(yy, return_counts=True)[1] >= 10).sum() >= 2:
                        cl = run_grid(X[idx][sub][:, [pi]], mask[idx][sub][:, [pi]], yy, groups[idx][sub], [pn],
                                      meta["layers"], workers=10, null_every=4)
                        lat[pn] = cl
                lat.setdefault(pn, {"undefined": True, "n_latent": int(len(sub))})
            res[pool_name]["latent"] = lat
        out[task] = res
        del X
    return out


def summarize_probes(pr: dict) -> dict:
    summ = {}
    for task, res in pr.items():
        for pool_name, r in res.items():
            if r.get("undefined"):
                summ[f"{task}|{pool_name}"] = {"undefined": True, "label_counts": r.get("label_counts")}
                continue
            cells = r["cells"]
            best = {}
            for c in cells:
                b = best.get(c["position"])
                if b is None or c["ig"] > b["ig"]:
                    best[c["position"]] = c
            sig = {}
            for c in cells:
                if "significant" in c:
                    sig.setdefault(c["position"], []).append(bool(c["significant"]))
            summ[f"{task}|{pool_name}"] = {
                "best_by_position": {p: {k: b[k] for k in ("layer", "ig", "ig_ci", "acc", "bal_acc", "n")}
                                     for p, b in best.items()},
                "any_significant_by_position": {p: any(v) for p, v in sig.items()},
                "n_significant_cells_by_position": {p: int(sum(v)) for p, v in sig.items()},
                "label_counts": r.get("label_counts")}
            for anchor in ("k_fork", "k_pre"):
                if anchor in best and "R" in best:
                    summ[f"{task}|{pool_name}"][f"locus_gain_{anchor}_over_R"] = {
                        "ig": best[anchor]["ig"] - best["R"]["ig"], "acc": best[anchor]["acc"] - best["R"]["acc"]}
    return summ


# =============================================================================================== verdict
def verdict(scr: dict, knob: dict, probe_summ: dict) -> dict:
    agg = scr["aggregate"]
    ban = agg.get("pooled|ban", {})
    F1 = ban.get("F1")[0] if ban.get("F1") else None
    F3 = ban.get("F3")[0] if ban.get("F3") else None
    F2 = ban.get("F2_median")
    D1 = False
    for key, s in probe_summ.items():
        if key.endswith("|ban") or key.endswith("|pooled"):
            for anchor in ("k_pre", "k_fork"):
                if s.get("any_significant_by_position", {}).get(anchor):
                    D1 = True
    k1 = {t: c["K1_fork_minus_random_window"] for t, c in knob.get("contrasts", {}).items()}
    K1_pass = any(v["excludes_0_favouring_first"] for v in k1.values())
    K1_null_both = len(k1) == 2 and all(not v["excludes_0_favouring_first"] for v in k1.values())
    r0_all = [agg[g]["R0"][0] for g in ("T1|baseline", "T1|ban", "T2|baseline", "T2|ban") if g in agg]
    fork_ok = (F1 is not None and F1 >= 0.5 and F3 is not None and F3 <= 0.15 and F2 is not None and F2 >= 0.5
               and D1)
    trace = {"F1_ban_pooled": F1, "F3_ban_pooled": F3, "F2_ban_pooled": F2, "D1": D1, "K1": k1,
             "K1_pass_any_task": K1_pass, "R0_by_task_condition": {g: agg[g]["R0"][0] for g in agg if "|" in g},
             "fork_criteria_pass": fork_ok}
    if fork_ok and K1_pass:
        v = "SUPPORTED"
    elif (len(r0_all) == 4 and all(x >= 0.8 for x in r0_all)) or (F1 is not None and F1 < 0.25 and K1_null_both):
        v = "REFUTED"
    elif fork_ok and not K1_pass:
        v = "PARTIAL-LOCUS"
    elif K1_pass and not fork_ok:
        v = "PARTIAL-KNOB"
    else:
        v = "INCONCLUSIVE"
    trace["rule_applied"] = v
    return {"verdict": v, "trace": trace}


# =============================================================================================== figures
def figures(R: dict, scr: dict, swap: dict, knob: dict, pr: dict) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    made = []
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42})
    # 1 modal fraction vs T
    fig, ax = plt.subplots(figsize=(4.2, 3))
    for task, mode, col in (("T1", "BFS", "#1f77b4"), ("T2", "dijkstra", "#d62728")):
        xs, ys, lo, hi = [], [], [], []
        for T, arm in ((0.3, "G3_T0.3"), (0.7, "G3_T0.7"), (1.0, "G1"), (1.3, "G3_T1.3")):
            rows = [r for r in R["pools"] if r["task"] == task and r["arm"] == arm]
            if not rows:
                continue
            p, l, h = wilson(sum(r["label_final"] == mode for r in rows), len(rows))
            xs.append(T); ys.append(p); lo.append(max(0.0, p - l)); hi.append(max(0.0, h - p))
        ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", capsize=3, color=col, label=f"{task}: share {mode}")
    ax.set_xlabel("global temperature"); ax.set_ylabel("modal-algorithm share (baseline prompt)")
    ax.set_ylim(0, 1.05); ax.legend(frameon=False); fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_modal_share_vs_T.png", dpi=200); plt.close(fig); made.append("fig1_modal_share_vs_T.png")
    # 2 agreement curves
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, task in zip(axes, ("T1", "T2")):
        for p in scr["paths"]:
            if p["task"] != task:
                continue
            ks = sorted(int(k) for k in p["agreement"])
            ax.plot(ks, [p["agreement"][str(k)] for k in ks], color="#d62728" if p["condition"] == "ban" else
                    "#7f7f7f", alpha=0.6, lw=1)
        ax.set_title(f"{task} (red = ban, grey = baseline)"); ax.set_xlabel("prefix length k (generated tokens)")
    axes[0].set_ylabel("a_k: agreement with path's final label"); fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_agreement_curves.png", dpi=200); plt.close(fig); made.append("fig2_agreement_curves.png")
    # 3 fork index histogram by token type
    forks = [f for f in scr["forks"]]
    if forks:
        fig, ax = plt.subplots(figsize=(5, 3))
        types = sorted({f["token_type"] for f in forks})
        bins = np.arange(0, 96, 2)
        data = [[f["t"] for f in forks if f["token_type"] == t and f["confirmed"]] for t in types]
        ax.hist(data, bins=bins, stacked=True, label=types)
        ax.set_xlabel("fork token index t (confirmed forks)"); ax.set_ylabel("count"); ax.legend(frameon=False, fontsize=7)
        fig.tight_layout(); fig.savefig(FIG_DIR / "fig3_fork_index_hist.png", dpi=200); plt.close(fig)
        made.append("fig3_fork_index_hist.png")
    # 4 IG heatmaps
    for task, res in pr.items():
        for pool_name, r in res.items():
            if r.get("undefined") or pool_name == "baseline":
                continue
            cells = r["cells"]
            pos = [p for p in ["R", "k8", "k16", "k32", "k64", "k_fork", "k_pre", "k_post"]
                   if any(c["position"] == p for c in cells)]
            lays = sorted({c["layer"] for c in cells})
            M = np.full((len(pos), len(lays)), np.nan)
            for c in cells:
                M[pos.index(c["position"]), lays.index(c["layer"])] = c["ig"]
            fig, ax = plt.subplots(figsize=(6, 2.8))
            im = ax.imshow(M, aspect="auto", cmap="viridis")
            ax.set_yticks(range(len(pos))); ax.set_yticklabels(pos)
            ax.set_xticks(range(0, len(lays), 2)); ax.set_xticklabels(lays[::2])
            for c in cells:
                if c.get("significant"):
                    ax.text(lays.index(c["layer"]), pos.index(c["position"]), "*", ha="center", va="center",
                            color="w", fontsize=8)
            ax.set_xlabel("layer"); ax.set_title(f"{task} {pool_name}: IG over prompt-only (bits); * > within-prompt null")
            fig.colorbar(im, ax=ax); fig.tight_layout()
            fn = f"fig4_ig_heatmap_{task}_{pool_name}.png"
            fig.savefig(FIG_DIR / fn, dpi=200); plt.close(fig); made.append(fn)
    # 5 knob frontier
    if knob.get("table"):
        fig, axes = plt.subplots(1, 2, figsize=(8, 3))
        for ax, task in zip(axes, ("T1", "T2")):
            tb = knob["table"].get(task, {})
            for name, v in tb.items():
                ax.scatter(v["pass_rate"][0], v["hill_cc"], label=name, s=25)
                ax.annotate(name, (v["pass_rate"][0], v["hill_cc"]), fontsize=6)
            ax.set_xlabel("pass rate"); ax.set_ylabel("Hill_cc (correct programs)"); ax.set_title(task)
        fig.tight_layout(); fig.savefig(FIG_DIR / "fig5_knob_frontier.png", dpi=200); plt.close(fig)
        made.append("fig5_knob_frontier.png")
    # 6 swap bars
    if swap.get("aggregate"):
        fig, ax = plt.subplots(figsize=(4.5, 3))
        names, vals, errs = [], [], []
        for g in ("T1", "T2"):
            a = swap["aggregate"].get(g, {})
            for side in ("pre", "post"):
                k = a.get(f"{side}_ban_banned_share")
                if k:
                    names.append(f"{g} {side}"); vals.append(k["mean"])
                    errs.append([[max(0.0, k["mean"] - k["ci"][0])], [max(0.0, k["ci"][1] - k["mean"])]])
        if names:
            ax.bar(range(len(names)), vals, yerr=np.hstack(errs) if errs else None, capsize=3,
                   color=["#1f77b4", "#ff7f0e"] * (len(names) // 2))
            ax.set_xticks(range(len(names))); ax.set_xticklabels(names)
            ax.set_ylabel("banned-mode share under ban prompt"); fig.tight_layout()
            fig.savefig(FIG_DIR / "fig6_swap.png", dpi=200); made.append("fig6_swap.png")
        plt.close(fig)
    return made


# =============================================================================================== method_out
def _code(r):
    return (r.get("code") or "NO_CODE") if r else "MISSING"


def write_method_out(R: dict, payload: dict) -> None:
    prompts = json.loads((ROOT / "prompts" / "prompts.json").read_text())
    pools, knob = R["pools"], R.get("knob", [])
    idx = {}
    for r in pools + knob:
        idx[(r["task"], r["arm"], r["paraphrase_id"], r["sample_id"])] = r
    datasets = []
    for task in ("T1", "T2"):
        ex = []
        for pid in range(10):
            for k in range(10):
                g1 = idx.get((task, "G1", pid, k))
                arms = {name: idx.get((task, arm, pid, k)) for name, arm in KNOB_ARMS}
                e = {"input": prompts[f"{task}|baseline|{pid}"]["user_text"],
                     "output": _code(g1),
                     "metadata_task": task, "metadata_condition": "baseline", "metadata_paraphrase_id": pid,
                     "metadata_sample_idx": k,
                     "metadata_labels": {n: (a["label_final"] if a else None) for n, a in arms.items()},
                     "metadata_passed": {n: (bool(a["passed"]) if a else None) for n, a in arms.items()},
                     "metadata_commit_idx": {n: (a.get("commit_idx") if a else None) for n, a in arms.items()},
                     "metadata_output_is": "global T=1.0 sample (protocol baseline arm)"}
                for name, a in arms.items():
                    e["predict_" + re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())] = _code(a)
                ex.append(e)
        datasets.append({"dataset": f"{TASKN[task]}_knob_arms", "examples": ex})
    # ban-condition pool (decoder samples) so the ban outputs are also inspectable
    for task in ("T1", "T2"):
        ex = []
        for r in sorted([x for x in pools if x["task"] == task and x["arm"] == "G2"],
                        key=lambda x: (x["paraphrase_id"], x["sample_id"])):
            ex.append({"input": prompts[f"{task}|ban|{r['paraphrase_id']}"]["user_text"], "output": _code(r),
                       "metadata_task": task, "metadata_condition": "ban", "metadata_paraphrase_id": r["paraphrase_id"],
                       "metadata_sample_idx": r["sample_id"], "metadata_label": r["label_final"],
                       "metadata_passed": bool(r["passed"]), "metadata_commit_idx": r["commit_idx"],
                       "metadata_evidence_term": r["evidence_term"],
                       "predict_runtime_label": str(r.get("runtime_label")), "predict_ast_label": str(r.get("ast_label")),
                       "predict_final_label": str(r["label_final"])})
        datasets.append({"dataset": f"{TASKN[task]}_ban_pool", "examples": ex})
    # screen base paths
    ex = []
    for p in payload["screen"]["paths"]:
        task, cond, pid = p["bp_id"].split("|")
        ex.append({"input": prompts[f"{task}|{cond}|{pid}"]["user_text"], "output": str(p["final_label"]),
                   "metadata_bp_id": p["bp_id"], "metadata_agreement_curve": p["agreement"],
                   "metadata_fixed_by": {str(k): v for k, v in p["fixed_by"].items()},
                   "metadata_commit_idx": p["commit_idx"], "metadata_evidence_term": p["evidence_term"],
                   "metadata_change_points": p["change_points"],
                   "predict_decided_at_R": str(bool(p["R0_decided"])),
                   "predict_confirmed_forks": json.dumps(p["confirmed_forks"]),
                   "predict_change_point_brackets": json.dumps([c["bracket"] for c in p["change_points"]])})
    if ex:
        datasets.append({"dataset": "fork_screen_base_paths", "examples": ex})
    ex = []
    for s in payload["swap"]["paths"]:
        task, cond, pid = s["bp_id"].split("|")
        ex.append({"input": prompts[f"{task}|ban|{pid}"]["user_text"], "output": BANNED[task],
                   "metadata_bp_id": s["bp_id"], "metadata_cut": s["cut"], "metadata_cut_source": s["cut_source"],
                   "metadata_swap": {k: v for k, v in s.items() if k not in ("bp_id",)},
                   "predict_ban_prompt_banned_share_pre": str(s["pre_ban_banned_share"]),
                   "predict_ban_prompt_banned_share_post": str(s["post_ban_banned_share"]),
                   "predict_baseline_prompt_banned_share_pre": str(s["pre_base_banned_share"]),
                   "predict_baseline_prompt_banned_share_post": str(s["post_base_banned_share"])})
    if ex:
        datasets.append({"dataset": "prompt_swap_at_commit", "examples": ex})
    out = {"metadata": payload["metadata"], "datasets": datasets}
    txt = json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    (ROOT / "method_out.json").write_text(txt)
    (ROOT / "full_method_out.json").write_text(txt)
    mini = {"metadata": payload["metadata"], "datasets": [{"dataset": d["dataset"], "examples": d["examples"][:3]}
                                                          for d in datasets]}
    (ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=1, default=str))

    def trunc(o):
        if isinstance(o, str):
            return o[:200]
        if isinstance(o, list):
            return [trunc(x) for x in o]
        if isinstance(o, dict):
            return {k: trunc(v) for k, v in o.items()}
        return o
    (ROOT / "preview_method_out.json").write_text(json.dumps(trunc(json.loads(json.dumps(mini, default=str))),
                                                             indent=1))


# =============================================================================================== main
def run_analysis() -> None:
    from transformers import AutoTokenizer
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    R = {k: read_jsonl(GEN_DIR / f"{k}.jsonl") for k in ("pools", "screen", "localise", "confirm", "swap", "knob")}
    logger.info({k: len(v) for k, v in R.items()})
    jpath = SUM_DIR / "judge.json"
    import os
    if os.environ.get("SKIP_JUDGE"):
        judge = {"skipped": True, "jmap": {}, "cost_usd": 0.0}
    elif jpath.exists():
        judge = json.loads(jpath.read_text())
    else:
        try:
            judge = adjudicate(R)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"judge failed: {e}")
            judge = {"error": str(e), "jmap": {}, "cost_usd": 0.0}
        if R["knob"] and R["swap"]:
            jpath.write_text(json.dumps(judge, indent=1))
    apply_final_labels(R, judge.get("jmap", {}))
    t6 = t6_sensitivity()
    scr = screen_readouts(R, tok)
    swap = swap_readouts(R)
    knob = knob_table(R)
    pr = probe_readouts()
    probe_summ = summarize_probes(pr)
    ver = verdict(scr, knob, probe_summ)
    figs = figures(R, scr, swap, knob, pr)
    (SUM_DIR / "screen.json").write_text(json.dumps({k: v for k, v in scr.items() if k != "forks"}, indent=1,
                                                    default=str))
    (ROOT / "forks.json").write_text(json.dumps({"forks": scr["forks"], "controls": scr["controls"]}, indent=1,
                                                default=str))
    (ROOT / "swap.json").write_text(json.dumps(swap, indent=1, default=str))
    (ROOT / "knob_table.json").write_text(json.dumps(knob, indent=1, default=str))
    (ROOT / "probes.json").write_text(json.dumps({"summary": probe_summ, "cells": pr}, default=str))
    pool_summ = {}
    for task in ("T1", "T2"):
        for arm in ("G1", "G2", "G3_T0.3", "G3_T0.7", "G3_T1.3"):
            rows = [r for r in R["pools"] if r["task"] == task and r["arm"] == arm]
            if rows:
                pool_summ[f"{task}|{arm}"] = {"n": len(rows), "label_counts": dict(collections.Counter(
                    r["label_final"] for r in rows)), "pass_rate": wilson(sum(bool(r["passed"]) for r in rows), len(rows)),
                    "hill_cc": hill1([r["label_final"] for r in rows if r["passed"]]),
                    "modal_share": wilson(sum(r["label_final"] == ("BFS" if task == "T1" else "dijkstra")
                                              for r in rows), len(rows))}
    (SUM_DIR / "pools.json").write_text(json.dumps(pool_summ, indent=1))
    hashes = (LOG_DIR / "hashes.log").read_text() if (LOG_DIR / "hashes.log").exists() else ""
    import importlib.metadata as im
    vers = {}
    for pkg in ("vllm", "transformers", "torch", "scikit-learn", "numpy", "ruptures"):
        try:
            vers[pkg] = im.version(pkg)
        except im.PackageNotFoundError:
            vers[pkg] = None
    tests = {}
    for fn in ("test_engine.json", "test_labeller.json", "test_states.json"):
        if (LOG_DIR / fn).exists():
            tests[fn] = json.loads((LOG_DIR / fn).read_text())
    if "test_labeller.json" in tests:
        tests["test_labeller.json"] = {"all_ok": tests["test_labeller.json"]["all_ok"],
                                       "failures": [x for x in tests["test_labeller.json"]["rows"] if not x["ok"]]}
    devs = json.loads((ROOT / "prereg.json").read_text())["declared_deviations"]
    if (SUM_DIR / "gen2_deviations.json").exists():
        devs += json.loads((SUM_DIR / "gen2_deviations.json").read_text())
    devs += ["vLLM engine initialised with enforce_eager=True after the 0.92/0.95 memory settings failed (plan retry "
             "ladder step 3); throughput ~1,150 tok/s", "swap: 20 continuations per cut under the ban prompt, 10 under "
             "the baseline prompt (reduction ladder step 3 applied to the baseline side only)",
             "T2 Dial has no runtime signature (runtime unresolved -> AST fallback label)",
             "S7 staged as 1 path per task x condition then the rest (plan: 1, 3, 10)",
             "AST rules revised once after S6 (Bellman-Ford over adjacency lists; IDDFS loop-variable rule) and all "
             "labels recomputed"]
    meta = {
        "title": "Do a few early tokens decide the algorithm? (screen, Qwen3-8B)",
        "model": "Qwen/Qwen3-8B", "versions": vers, "verdict": ver["verdict"], "verdict_trace": ver["trace"],
        "prereg_sha256": sha256_file(ROOT / "prereg.json"),
        "predictions_sha256": sha256_file(ROOT / "predictions.json") if (ROOT / "predictions.json").exists() else None,
        "hashes_log": hashes.strip().splitlines(), "deviations": devs,
        "openrouter_cost_usd": judge.get("cost_usd"), "judge_models": judge.get("models"),
        "labeller_gate": judge.get("gate"), "judge_disputed": [judge.get("disputed_judged"), judge.get("disputed_total")],
        "pools_summary": pool_summ, "screen_aggregate": scr["aggregate"], "screen_entropy": scr["entropy"],
        "token_type_table": scr["token_type_table"], "n_fork_candidates": len(scr["forks"]),
        "n_confirmed_forks": sum(f["confirmed"] for f in scr["forks"]),
        "confirmed_forks": [{k: f[k] for k in ("bp_id", "t", "token", "token_type", "tvd", "p_perm", "sharpness",
                                               "precedes_commit", "is_commit_token", "next_token_entropy_bits",
                                               "outcome_entropy_before_bits", "outcome_entropy_after_bits")}
                            for f in scr["forks"] if f["confirmed"]],
        "controls_summary": {"n": len(scr["controls"]), "false_positives": sum(c["false_positive"]
                                                                               for c in scr["controls"])},
        "t6_sensitivity": t6, "swap_aggregate": swap["aggregate"], "knob_table": knob["table"],
        "knob_contrasts": knob["contrasts"], "probe_summary": probe_summ, "tests": tests, "figures": figs,
        "row_counts": {k: len(v) for k, v in R.items()},
        "analysis_runtime_s": round(time.time() - t0, 1),
        "notes": "screen estimates with intervals, not inferential tests; Wilson tuples are (p, lo, hi)"}
    write_method_out(R, {"metadata": meta, "screen": scr, "swap": swap})
    logger.info(f"verdict {ver['verdict']}; method_out.json written in {time.time() - t0:.0f}s")
