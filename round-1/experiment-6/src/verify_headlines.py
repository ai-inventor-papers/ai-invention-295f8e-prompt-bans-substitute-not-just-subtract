#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers from the RAW files, through a different code path than
labeller/label.py + analysis/*.py, plus placebo versions of the statistical tests (which must NOT be significant).

Reads: results/raw/<arm>.jsonl (generations), results/labels/code_labels.jsonl and judge.jsonl (per-program
labeller outputs keyed by code sha256), states/*.npy (R states). Writes results/verify_headlines.json.
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

WS = Path(__file__).resolve().parent
RAW, LAB = WS / "results" / "raw", WS / "results" / "labels"


def jl(p):
    return [json.loads(x) for x in open(p) if x.strip()]


# --- labels: own extraction (regex over the answer text) + own final-label rule -----------------------------
code_lab = {(r["task"], r["sha"]): r for r in jl(LAB / "code_labels.jsonl")}
judge = {(r["task"], r["sha"]): r["label"] for r in jl(LAB / "judge.jsonl")}
BLOCK = re.compile(r"```(?:python|py|python3)[^\n]*\n(.*?)(?:```|$)", re.S)


def final_label(task, text):
    text = text.split("</think>")[-1]
    blocks = BLOCK.findall(text)
    cand = [b for b in blocks if re.search(r"^\s*def\s+solve\s*\(", b, re.M)]
    code = cand[-1] if cand else (blocks[0] if blocks else None)
    if code is None:
        return "unparseable", False
    cl = code_lab.get((task, hashlib.sha256(code.encode()).hexdigest()))
    if cl is None:
        return "missing", False
    ok = bool(cl["tests"].get("passed"))
    if cl["runtime_label"] is not None and cl["runtime_label"] == cl["ast_label"]:
        return cl["runtime_label"], ok
    return judge.get((task, hashlib.sha256(code.encode()).hexdigest()), "unresolved"), ok


rows = []
for arm in ["A0", "A1", "A2", "A3", "A4s2", "A5", "A6a", "A6b", "A6c", "A6d"]:
    for r in jl(RAW / f"{arm}.jsonl"):
        lab, ok = final_label(r["task"], r.get("answer_text") or r["text"])
        d = r["decoding"]
        rows.append(dict(task=r["task"], arm=arm, cond=r["condition"], p=r["paraphrase_id"], T=d["T"],
                         sampler=d["sampler"], think=d["thinking"], label=lab, ok=ok))
out = {"n_rows": len(rows), "n_missing": sum(r["label"] == "missing" for r in rows)}

prim = {"T1": "bfs", "T2": "dijkstra"}
for task in ("T1", "T2"):
    for think in (False, True):
        xs = [r for r in rows if r["task"] == task and r["think"] == think and (r["arm"] == "A1" or r["arm"].startswith("A6"))]
        cl = [r for r in xs if r["label"] not in ("other", "unparseable", "unresolved", "missing")]
        out[f"{task}_think{int(think)}_grid_primary_share_classified"] = (
            sum(r["label"] == prim[task] for r in cl), len(cl))
        per = defaultdict(lambda: [0, 0])
        for r in cl:
            per[f"{r['sampler']}|T{r['T']}"][0] += r["label"] == prim[task]
            per[f"{r['sampler']}|T{r['T']}"][1] += 1
        out[f"{task}_think{int(think)}_min_cell_share"] = min(a / b for a, b in per.values())


def share(xs, mode):
    xs = [r for r in xs if r["ok"]]
    return sum(r["label"] == mode for r in xs) / len(xs) if xs else float("nan")


rng = np.random.default_rng(123)
for task in ("T1", "T2"):
    a0 = [r for r in rows if r["task"] == task and r["arm"] == "A0"]
    for cond in ("seed_entropy", "seed_word", "seed_semantic", "instr_fully_novel", "instr_enumerate"):
        c = [r for r in rows if r["task"] == task and r["cond"] == cond]
        out[f"{task}_{cond}_primary_shift_pp"] = round((share(c, prim[task]) - share(a0, prim[task])) * 100, 2)
    a4 = [r for r in rows if r["task"] == task and r["arm"] == "A4s2"]
    out[f"{task}_gen_then_select_correct_mode_counts"] = dict(Counter(r["label"] for r in a4 if r["ok"]))

# --- semantic-seed implied-mode test (own permutation over paraphrase clusters) and its placebo --------------
implied = {"T1": "bidirectional_bfs", "T2": "bellman_ford_spfa"}


def perm_p(group_a, group_b, mode, n=4000):
    """one-sided p for share(mode | correct) higher in group_b than group_a; clusters = paraphrase ids."""
    clus = [[r for r in group_a if r["p"] == p] for p in sorted({r["p"] for r in group_a})] + \
           [[r for r in group_b if r["p"] == p] for p in sorted({r["p"] for r in group_b})]
    na = len({r["p"] for r in group_a})

    def stat(ix):
        b = [r for i in ix[na:] for r in clus[i]]
        a = [r for i in ix[:na] for r in clus[i]]
        return share(b, mode) - share(a, mode)
    obs = stat(np.arange(len(clus)))
    null = np.array([stat(rng.permutation(len(clus))) for _ in range(n)])
    return float(obs), float((np.sum(null >= obs - 1e-12) + 1) / (n + 1))


for task in ("T1", "T2"):
    a0 = [r for r in rows if r["task"] == task and r["arm"] == "A0"]
    sem = [r for r in rows if r["task"] == task and r["cond"] == "seed_semantic"]
    out[f"{task}_semantic_implied_shift_and_p"] = perm_p(a0, sem, implied[task])
    # placebo 1: A0 split in two halves by paraphrase (no treatment) -> must not be significant
    h1 = [r for r in a0 if r["p"] < 5]
    h2 = [dict(r, p=r["p"]) for r in a0 if r["p"] >= 5]
    out[f"{task}_placebo_A0_halves_primary_p"] = perm_p(h1, h2, prim[task])
    # placebo 2: semantic-seed labels shuffled across the pooled A0+semantic rows -> must not be significant
    pool = a0 + sem
    labs = [r["label"] for r in pool]
    rng.shuffle(labs)
    sh = [dict(r, label=l) for r, l in zip(pool, labs)]
    out[f"{task}_placebo_shuffled_labels_implied_p"] = perm_p(sh[:len(a0)], sh[len(a0):], implied[task])

# --- read-position displacement ratio (own QR-based subspace) and a placebo split of the baseline ------------
meta = json.loads((WS / "states" / "meta.json").read_text())
for task in ("T1", "T2"):
    L = meta["l_star"][task]
    Hn = np.load(WS / "states" / f"R_named_{task}.npy", mmap_mode="r")[:, L].astype(np.float64)
    Hc = np.load(WS / "states" / f"R_conditions_{task}.npy", mmap_mode="r")[:, L].astype(np.float64)
    yn = np.array([r["condition"] for r in meta[f"R_named_{task}"]])
    cents = np.stack([Hn[yn == m].mean(0) for m in sorted(set(yn))])
    Q, _ = np.linalg.qr((cents[1:] - cents[0]).T)  # span of centroid differences == span of centred centroids
    idx = {(r["condition"], r["paraphrase_id"]): i for i, r in enumerate(meta[f"R_conditions_{task}"])}
    base = np.stack([Hc[idx[("baseline", p)]] for p in range(10)])
    null = [np.linalg.norm(Q.T @ (base[p] - base[q])) for p in range(10) for q in range(p + 1, 10)]
    for cond in ("seed_entropy", "seed_word", "seed_semantic", "neutral_insert"):
        H = np.stack([Hc[idx[(cond, p)]] for p in range(10)])
        d = np.linalg.norm((H - base) @ Q, axis=1)
        out[f"{task}_{cond}_R_ratio"] = round(float(np.median(d) / np.median(null)), 3)
    # placebo: 'condition' = baseline paraphrases 5-9 paired with 0-4 -> ratio should be ~1 (within the null)
    d = [np.linalg.norm(Q.T @ (base[p + 5] - base[p])) for p in range(5)]
    out[f"{task}_placebo_baseline_split_R_ratio"] = round(float(np.median(d) / np.median(null)), 3)

(WS / "results" / "verify_headlines.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
