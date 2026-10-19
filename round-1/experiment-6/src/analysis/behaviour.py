#!/usr/bin/env python3
"""8a BFS/Dijkstra table, 8c seeds and instructions vs A0, 8g gen-then-select, 8h BUY rows (label-based)."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.metrics import da_at_k, hill1, wilson  # noqa: E402
from common import ALIAS_LEXICON, MODES, NON_CLASSIFIED, PRIMARY_MODE, RAW, read_jsonl  # noqa: E402
from prompts.build import SEMANTIC_IMPLIED  # noqa: E402

TEMPS = [0.3, 0.7, 1.0, 1.3]


def cell_id(s: dict) -> str:
    d = s["decoding"]
    return f"{s['arm']}|{d['sampler']}|T{d['T']}|think{int(d['thinking'])}"


def classified(label) -> bool:
    return label not in NON_CLASSIFIED


def _arrays(rows: list[dict], mode: str):
    pid = np.array([r["paraphrase_id"] if r["paraphrase_id"] >= 0 else r["sample_id"] for r in rows])
    prim = np.array([r["label"] == mode for r in rows], dtype=float)
    corr = np.array([bool(r["passed"]) for r in rows], dtype=float)
    cls = np.array([classified(r["label"]) for r in rows], dtype=float)
    return pid, prim, corr, cls


def boot_share(pid, prim, mask, n_boot=2000, rng=None, q=(0.025, 0.975)):
    """Paraphrase-cluster bootstrap of sum(prim*mask)/sum(mask)."""
    rng = rng or np.random.default_rng(0)
    groups = [np.where(pid == g)[0] for g in np.unique(pid)]
    vals = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in
                              (groups[i] for i in rng.integers(0, len(groups), len(groups)))])
        den = mask[idx].sum()
        vals[b] = (prim[idx] * mask[idx]).sum() / den if den > 0 else np.nan
    vals = vals[~np.isnan(vals)]
    return [float(np.quantile(vals, x)) for x in q] if len(vals) else [None for _ in q]


def bfs_dijkstra_table(samples: list[dict]) -> list[dict]:
    rng = np.random.default_rng(1)
    cells = defaultdict(list)
    for s in samples:
        if s["arm"] in ("A0", "A1") or s["arm"].startswith("A6"):
            cells[(s["task"], cell_id(s))].append(s)
    out = []
    for (task, cid), rows in sorted(cells.items()):
        mode = PRIMARY_MODE[task]
        pid, prim, corr, cls = _arrays(rows, mode)
        n = len(rows)
        d = rows[0]["decoding"]
        rec = dict(task=task, cell=cid, arm=rows[0]["arm"], T=d["T"], sampler=d["sampler"],
                   thinking=d["thinking"], n=n, n_correct=int(corr.sum()), pass_rate=float(corr.mean()),
                   primary_mode=mode, label_counts=dict(Counter(r["label"] for r in rows)),
                   label_counts_correct=dict(Counter(r["label"] for r in rows if r["passed"])))
        if d["thinking"]:
            rec["truncated_thinking_rate"] = float(np.mean([bool(r.get("truncated_thinking")) for r in rows]))
            rec["mean_thinking_tokens"] = float(np.mean([r.get("n_thinking_tokens") or 0 for r in rows]))
        for name, mask in (("all", np.ones(n)), ("correct", corr), ("classified", cls)):
            k = int((prim * mask).sum())
            m = int(mask.sum())
            lo, hi = wilson(k, m)
            blo, bhi = boot_share(pid, prim, mask, rng=rng)
            rec[f"share_{name}"] = dict(k=k, n=m, share=k / m if m else None, wilson95=[lo, hi],
                                        cluster_boot95=[blo, bhi])
        out.append(rec)
    return out


def _share(rows, mode, correct_only=True):
    xs = [r for r in rows if r["passed"]] if correct_only else rows
    return (sum(r["label"] == mode for r in xs) / len(xs)) if xs else np.nan


def seeds_instructions(samples: list[dict], n_boot: int = 2000, n_perm: int = 5000) -> list[dict]:
    rng = np.random.default_rng(2)
    out = []
    for task in ("T1", "T2"):
        base = [s for s in samples if s["task"] == task and s["arm"] == "A0"]
        mode = PRIMARY_MODE[task]
        for cond in ("seed_entropy", "seed_word", "seed_semantic", "instr_creative", "instr_new_algo",
                     "instr_fully_novel", "instr_enumerate"):
            rows = [s for s in samples if s["task"] == task and s["condition"] == cond]
            if not rows:
                continue
            cb = [r for r in base if r["passed"]]
            cc = [r for r in rows if r["passed"]]
            labs = sorted({r["label"] for r in cb + cc})
            pb = np.array([sum(r["label"] == lab for r in cb) / max(len(cb), 1) for lab in labs])
            pc = np.array([sum(r["label"] == lab for r in cc) / max(len(cc), 1) for lab in labs])
            tv = 0.5 * np.abs(pb - pc).sum() * 100
            shift = (_share(rows, mode) - _share(base, mode)) * 100
            gb = defaultdict(list)
            gc = defaultdict(list)
            for r in base:
                gb[r["paraphrase_id"]].append(r)
            for r in rows:
                gc[r["paraphrase_id"]].append(r)
            kb, kc = list(gb), list(gc)
            boots = []
            for _ in range(n_boot):
                xb = [r for i in rng.integers(0, len(kb), len(kb)) for r in
                      (gb[kb[i]][j] for j in rng.integers(0, len(gb[kb[i]]), len(gb[kb[i]])))]
                xc = [r for i in rng.integers(0, len(kc), len(kc)) for r in
                      (gc[kc[i]][j] for j in rng.integers(0, len(gc[kc[i]]), len(gc[kc[i]])))]
                v = (_share(xc, mode) - _share(xb, mode)) * 100
                if not np.isnan(v):
                    boots.append(v)
            boots = np.array(boots)
            # cluster permutation over the 20 paraphrase clusters
            clusters = [gb[k] for k in kb] + [gc[k] for k in kc]
            obs = abs(shift)
            cnt = 0
            nb = len(kb)
            for _ in range(n_perm):
                perm = rng.permutation(len(clusters))
                xb = [r for i in perm[:nb] for r in clusters[i]]
                xc = [r for i in perm[nb:] for r in clusters[i]]
                v = abs(_share(xc, mode) - _share(xb, mode)) * 100
                cnt += v >= obs - 1e-9
            rec = dict(task=task, condition=cond, n=len(rows), n_correct=len(cc), n_base_correct=len(cb),
                       label_dist_correct=dict(Counter(r["label"] for r in cc)),
                       base_label_dist_correct=dict(Counter(r["label"] for r in cb)),
                       tv_pp=float(tv), modal_mode=mode, modal_share_shift_pp=float(shift),
                       shift_ci90=[float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95))],
                       shift_ci95=[float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
                       cluster_perm_p=(cnt + 1) / (n_perm + 1),
                       pass_rate=float(np.mean([r["passed"] for r in rows])),
                       pass_rate_change_pp=float((np.mean([r["passed"] for r in rows]) -
                                                  np.mean([r["passed"] for r in base])) * 100),
                       il_epsilon_flag=bool(abs(shift) > 15),
                       equivalence_within_15pp=bool(-15 < np.quantile(boots, 0.05) and np.quantile(boots, 0.95) < 15))
            if cond == "seed_semantic":
                from scipy.stats import fisher_exact
                imp = SEMANTIC_IMPLIED[task]
                a, b = sum(r["label"] == imp for r in cc), sum(r["label"] != imp for r in cc)
                c, d = sum(r["label"] == imp for r in cb), sum(r["label"] != imp for r in cb)
                rec["implied_mode"] = imp
                rec["implied_share_change_pp"] = float((a / max(len(cc), 1) - c / max(len(cb), 1)) * 100)
                rec["implied_fisher_one_sided_p"] = float(fisher_exact([[a, b], [c, d]], alternative="greater")[1])
                obs2 = a / max(len(cc), 1) - c / max(len(cb), 1)
                cnt2 = 0
                for _ in range(n_perm):
                    perm = rng.permutation(len(clusters))
                    xb = [r for i in perm[:nb] for r in clusters[i] if r["passed"]]
                    xc = [r for i in perm[nb:] for r in clusters[i] if r["passed"]]
                    v = (sum(r["label"] == imp for r in xc) / max(len(xc), 1) -
                         sum(r["label"] == imp for r in xb) / max(len(xb), 1))
                    cnt2 += v >= obs2 - 1e-12
                rec["implied_cluster_perm_one_sided_p"] = (cnt2 + 1) / (n_perm + 1)
            out.append(rec)
    return out


def idea_stats(rows: list[dict]) -> dict:
    corr = [r for r in rows if r["passed"] and r["label"] not in ("unresolved", "unparseable")]
    cnt = Counter(r["label"] for r in corr)
    return dict(n=len(rows), n_correct=len(corr), pass_rate=float(np.mean([r["passed"] for r in rows])) if rows
                else None, idea_counts=dict(cnt), distinct_correct_modes=len([k for k in cnt if k != "other"]),
                EA_idea=hill1(list(cnt.values())), DA_idea_25=da_at_k(list(cnt.values()), 25),
                DA_idea_10=da_at_k(list(cnt.values()), 10))


def mentioned_modes(text: str, task: str) -> set[str]:
    low = text.lower()
    found = set()
    for m in MODES[task]:
        pats = ALIAS_LEXICON.get(m, [])
        if m == "dijkstra_unit":
            pats = [r"dijkstra", r"uniform[- ]cost"]
        if any(re.search(p, low) for p in pats):
            found.add(m)
    if task == "T2" and "bidirectional_dijkstra" in found:
        pass
    if task == "T2" and re.search(r"bi-?directional", low) and "dijkstra" in low:
        found.add("bidirectional_dijkstra")
    return found


def gen_then_select(samples: list[dict]) -> dict:
    from gen.arms import parse_items
    out = {}
    for task in ("T1", "T2"):
        a4 = [s for s in samples if s["task"] == task and s["arm"] == "A4s2"]
        a0 = [s for s in samples if s["task"] == task and s["arm"] == "A0"]
        lists = [r for r in read_jsonl(RAW / "A4s1.jsonl") if r["task"] == task]
        cover = Counter()
        n_items = []
        for r in lists:
            items = parse_items(r["text"])
            n_items.append(len(items))
            named = set()
            for it in items:
                named |= mentioned_modes(it, task)
            for m in named:
                cover[m] += 1
        pooled = [s for s in samples if s["task"] == task and s["passed"] and s["arm"] != "A5"]
        pooled_all = [s for s in samples if s["task"] == task and s["passed"]]
        out[task] = dict(
            gen_then_select=idea_stats(a4), baseline_A0=idea_stats(a0),
            stage1_n_lists=len(lists), stage1_mean_items=float(np.mean(n_items)) if n_items else None,
            stage1_modes_named_in_any_list=sorted(cover), stage1_share_of_lists_naming_mode={
                m: cover[m] / max(len(lists), 1) for m in MODES[task]},
            selected_item_examples=[s.get("gts_item", "")[:120] for s in a4[:5]],
            pooled_ceiling_natural_arms=dict(distinct_correct_modes=sorted({s["label"] for s in pooled} - {"other"}),
                                             other_count=sum(s["label"] == "other" for s in pooled)),
            pooled_ceiling_all_arms_incl_forced=dict(
                distinct_correct_modes=sorted({s["label"] for s in pooled_all} - {"other", "unparseable"}),
                other_count=sum(s["label"] == "other" for s in pooled_all)))
    return out


def buy_rows(samples: list[dict]) -> list[dict]:
    """One row per knob setting with diversity gain and pass-rate price."""
    groups = defaultdict(list)
    for s in samples:
        if s["arm"] in ("A0", "A1", "A2", "A3", "A4s2") or s["arm"].startswith("A6"):
            d = s["decoding"]
            knob = s["condition"] if s["arm"] in ("A2", "A3", "A4s2") else f"{d['sampler']}|T{d['T']}"
            groups[(s["task"], d["thinking"], s["arm"] if s["arm"] in ("A0", "A2", "A3", "A4s2") else "grid",
                    knob)].append(s)
    ref = {}
    for task in ("T1", "T2"):
        ref[(task, False)] = idea_stats([s for s in samples if s["task"] == task and s["arm"] == "A0"])
    rows = []
    for (task, think, arm, knob), xs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        st = idea_stats(xs)
        if think:
            sampler = xs[0]["decoding"]["sampler"]
            base = idea_stats([s for s in samples if s["task"] == task and s["arm"].startswith("A6")
                               and s["decoding"]["sampler"] == sampler and s["decoding"]["T"] == 1.0])
        else:
            base = ref[(task, False)]
        d_pass = (st["pass_rate"] - base["pass_rate"]) * 100
        d_hill = (st["EA_idea"] or 1.0) - (base["EA_idea"] or 1.0)
        rows.append(dict(task=task, thinking=think, arm=arm, knob=knob, n=st["n"], pass_rate=st["pass_rate"],
                         hill_cc=st["EA_idea"], DA_idea_25=st["DA_idea_25"], d_pass_pp=d_pass, d_hill=d_hill,
                         price_pp_per_extra_effective_algorithm=(-d_pass / d_hill) if d_hill > 0.05 else None,
                         reached_hill2=bool((st["EA_idea"] or 0) >= 2), reached_hill3=bool((st["EA_idea"] or 0) >= 3),
                         reference="A0" if not think else "A6 T=1.0 same sampler"))
    return rows
