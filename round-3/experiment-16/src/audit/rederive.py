#!/usr/bin/env python3
"""Independent re-derivation of every headline number from data/samples.jsonl (no import of src/analysis), plus:
U4 (one-shot veto: identical to arm b before the firing step, unfired rows identical throughout, the vetoed completion
never drawn at the firing step), U5 (persistent veto: the n-gram never appears), U6 (prefill text is the start of the
labelled text and generation continued), placebo shuffles (arm labels shuffled within CRN slots must destroy the
route structure; V shuffled across tasks gives a rho null centred near 0), the hash chain, and the ordering of
commits vs the first ban rows. Writes results/rederive.json; 0 mismatches against results/analysis.json expected."""

from __future__ import annotations

import collections
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXCL = {"invalid", "no_code", "disputed"}
DEFAULT = {"T03": "full_sort", "T04": "naive", "T06": "hash_set", "T05": "hash_map", "T10": "union_find",
           "R1": "greedy_end", "T08": "iteration", "R3": "kahn", "T13": "sort_sweep", "R6": "binary_search",
           "T14": "sort_by_count", "T11": "quadratic_dp", "t1": "bfs", "t2": "dijkstra"}
TASKS = ["T03", "T04", "T06", "T05", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11"]


def load(p: Path) -> list[dict]:
    out = []
    with open(p) as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def shares(rows: list[dict]) -> dict:
    out = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["label"] in EXCL:
            continue
        k = (r["task"], r["arm"])
        out[k][1] += 1
        out[k][0] += int(r["label"] == DEFAULT[r["task"]])
    return {k: (v[0] / v[1] if v[1] else float("nan"), v[0], v[1]) for k, v in out.items()}


def close(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) and math.isnan(a):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return abs(float(a) - float(b)) <= tol


def main() -> None:
    rows_all = load(ROOT / "data" / "samples.jsonl")
    last = {}
    for r in rows_all:
        last[r["uid"]] = r
    rows = list(last.values())
    bench = [r for r in rows if r["task"] in TASKS and r["stage"] != "U9"]
    sh = shares(bench)
    an = json.loads((ROOT / "results" / "analysis.json").read_text())
    mism = []
    # shares
    for (t, a), (s, nd, n) in sh.items():
        ref = an["shares"].get(t, {}).get(a)
        if ref is None or not close(s, ref["s"]) or ref["n_attempted"] != n:
            mism.append({"what": "share", "task": t, "arm": a, "mine": s, "analysis": ref and ref["s"]})
    # gate
    gated = []
    for t in TASKS:
        s, nd, n = sh.get((t, "a"), (float("nan"), 0, 0))
        if n and 1 - s >= 0.5 and n - nd >= 20:
            gated.append(t)
    if sorted(gated) != sorted(an["gated"]):
        mism.append({"what": "gated", "mine": gated, "analysis": an["gated"]})
    # pooled route fractions (ratio of sums over gated tasks with all four arms)
    full = [t for t in gated if all((t, a) in sh for a in "abcd")]
    num_p = sum(sh[(t, "b")][0] - sh[(t, "c")][0] for t in full)
    num_d = sum(sh[(t, "b")][0] - sh[(t, "d")][0] for t in full)
    den = sum(sh[(t, "b")][0] - sh[(t, "a")][0] for t in full)
    Fp, Fd = (num_p / den, num_d / den) if den else (float("nan"), float("nan"))
    rt = an["route"]
    if full and (not close(Fp, rt["point"]["F_prompt"], 1e-9) or not close(Fd, rt["point"]["F_direct"], 1e-9)):
        mism.append({"what": "pooled F", "mine": [Fp, Fd], "analysis": [rt["point"]["F_prompt"], rt["point"]["F_direct"]]})
    per_task_F = {}
    for t in full:
        sa, sb, sc, sd = (sh[(t, a)][0] for a in "abcd")
        per_task_F[t] = {"F_prompt": (sb - sc) / (sb - sa) if sb != sa else float("nan"),
                         "F_direct": (sb - sd) / (sb - sa) if sb != sa else float("nan")}
        ref = rt.get("per_task", {}).get(t, {})
        if ref and (not close(per_task_F[t]["F_prompt"], ref["F_prompt"]["point"]) or
                    not close(per_task_F[t]["F_direct"], ref["F_direct"]["point"])):
            mism.append({"what": "per-task F", "task": t})
    # V_t and C2c
    c2c = json.loads((ROOT / "predictions" / "c2c.json").read_text())
    V = {}
    for t in TASKS:
        v1 = [r for r in rows_all if r["task"] == t and r["arm"] == "V1" and r["stage"] == "S4"]
        lab = {}
        for r in v1:
            lab[r["uid"]] = r
        v1 = list(lab.values())
        # commit #2 used the labels present at commit time; compare with the committed value on those rows
        att = [r for r in v1 if r["label"] not in EXCL]
        V[t] = 1 - sum(r["label"] == DEFAULT[t] for r in att) / len(att) if att else float("nan")
    v_diff = {t: (V[t], c2c[t]["V"]) for t in TASKS if not close(V[t], c2c[t]["V"], 0.02)}
    hits = {}
    for t in full:
        cls = c2c[t]["class"]
        if cls == "LOW_DIRECT":
            hits[t] = per_task_F[t]["F_direct"] <= 0.15
        elif cls == "HIGH_DIRECT":
            hits[t] = per_task_F[t]["F_direct"] >= 0.25
    hf = float(np.mean(list(hits.values()))) if hits else float("nan")
    if hits and not close(hf, an["c2c"]["hit_fraction"]):
        mism.append({"what": "C2c hit fraction", "mine": hf, "analysis": an["c2c"]["hit_fraction"]})
    # P_open
    popen = {}
    for t in gated:
        for pf in ("SIG", "NEU"):
            if (t, f"BAN+{pf}") in sh:
                ref_s = sh[(t, f"TWIN+{pf}")][0] if (t, f"TWIN+{pf}") in sh else sh[(t, "b")][0]
                d = ref_s - sh[(t, "a")][0]
                popen[f"{t}|{pf}"] = (sh[(t, f"BAN+{pf}")][0] - sh[(t, "a")][0]) / d if d else float("nan")
                refv = an["prefill"].get(t, {}).get(pf, {}).get("P_open")
                if not close(popen[f"{t}|{pf}"], refv):
                    mism.append({"what": "P_open", "key": f"{t}|{pf}"})
    # U4 / U5 / U6 on raw rows
    raw = {}
    for r in load(ROOT / "data" / "samples_raw.jsonl"):
        raw[r["uid"]] = r
    ngr = json.loads((ROOT / "predictions" / "ngrams.json").read_text())
    u4 = {"n_fired": 0, "prefix_identical": 0, "n_unfired": 0, "unfired_identical": 0, "vetoed_token_not_drawn": 0}
    for u, r in raw.items():
        if r["arm"] != "V1":
            continue
        b = raw.get(f"{r['task']}|b|{r['w']}|{r['k']}")
        if b is None:
            continue
        if r["veto_fired"]:
            fs = r["fire_step"]
            u4["n_fired"] += 1
            u4["prefix_identical"] += int(r["token_ids"][:fs] == b["token_ids"][:fs])
            g = r["veto"]["ngrams"][0]
            u4["vetoed_token_not_drawn"] += int(len(r["token_ids"]) > fs and r["token_ids"][fs] != g[-1])
        else:
            u4["n_unfired"] += 1
            u4["unfired_identical"] += int(r["token_ids"] == b["token_ids"])
    u5 = {"n": 0, "with_ngram": 0}
    for u, r in raw.items():
        if r["arm"] in ("VP", "R2", "R3"):
            u5["n"] += 1
            ids = r["token_ids"]
            for g in r["veto"]["ngrams"]:
                n = len(g)
                if any(ids[i:i + n] == g for i in range(len(ids) - n + 1)):
                    u5["with_ngram"] += 1
                    break
    u6 = {"n": 0, "text_starts_with_prefix": 0, "continued": 0}
    for u, r in raw.items():
        if "+" in r["arm"]:
            u6["n"] += 1
            u6["text_starts_with_prefix"] += int(r["text"].startswith(r["prefix_text"]) and bool(r["prefix_text"]))
            u6["continued"] += int(r["n_new_tokens"] > 0)
    # placebo shuffles
    rng = np.random.default_rng(2026)
    slots = collections.defaultdict(dict)
    for r in bench:
        if r["task"] in full and r["arm"] in "abcd" and r["label"] not in EXCL:
            slots[(r["task"], r["template"], r["k"])][r["arm"]] = int(r["label"] == DEFAULT[r["task"]])
    keys = [k for k, v in slots.items() if len(v) == 4]
    shuffled_gap = []
    for _ in range(200):
        acc = collections.defaultdict(lambda: [0, 0])
        for k in keys:
            vals = [slots[k][a] for a in "abcd"]
            perm = rng.permutation(4)
            for a, j in zip("abcd", perm):
                acc[(k[0], a)][0] += vals[j]
                acc[(k[0], a)][1] += 1
        num = sum(acc[(t, "b")][0] / acc[(t, "b")][1] - acc[(t, "a")][0] / acc[(t, "a")][1] for t in full if acc[(t, "a")][1])
        shuffled_gap.append(num / max(len(full), 1))
    obs_gap = (sum(sh[(t, "b")][0] - sh[(t, "a")][0] for t in full) / len(full)) if full else float("nan")
    rho_null = []
    pts = [(c2c[t]["V"], per_task_F[t]["F_direct"]) for t in full if np.isfinite(per_task_F[t]["F_direct"])]
    if len(pts) >= 3:
        from scipy import stats

        v = np.array([p[0] for p in pts])
        f = np.array([p[1] for p in pts])
        for _ in range(2000):
            r_ = stats.spearmanr(rng.permutation(v), f).statistic
            if np.isfinite(r_):
                rho_null.append(r_)
    # hash chain and ordering
    chain_ok, prev, times = True, "0" * 64, {}
    for line in (ROOT / "commitments.log").read_text().splitlines():
        rec = json.loads(line)
        want = hashlib.sha256((prev + rec["file_sha256"] + rec["utc"] + rec["path"]).encode()).hexdigest()
        chain_ok &= want == rec["chain"]
        prev = rec["chain"]
        times.setdefault(rec["commit"], []).append(rec["utc"])
    ban_rows = [r for r in raw.values() if r["arm"] in ("a", "c", "d", "K0") or r["arm"].startswith("BAN")]
    bench_ban = [r for r in ban_rows if r["task"] in TASKS]
    first_ban = min((r["utc"] for r in ban_rows), default=None)
    first_bench_ban = min((r["utc"] for r in bench_ban), default=None)
    first_a = min((r["utc"] for r in raw.values() if r["arm"] == "a" and r["task"] in TASKS), default=None)
    order = {"commit1_last_utc": max(times.get("commit1", [""])), "commit2_last_utc": max(times.get("commit2", [""])),
             "first_ban_row_utc": first_ban, "first_bench_ban_row_utc": first_bench_ban, "first_arm_a_row_utc": first_a,
             "commit1_before_first_ban": bool(first_ban is None or max(times.get("commit1", [""])) < first_ban),
             "commit2_before_first_bench_ban": bool(first_bench_ban is None or max(times.get("commit2", [""])) < first_bench_ban)}
    out = {"n_rows": len(rows), "n_mismatches": len(mism), "mismatches": mism, "gated": gated, "pooled": {"F_prompt": Fp, "F_direct": Fd},
           "per_task_F": per_task_F, "V_recomputed_vs_committed_diffs_gt_0.02": v_diff, "c2c_hits": hits, "c2c_hit_fraction": hf,
           "P_open": popen, "U4": u4, "U4_pass": bool(u4["n_fired"] == u4["prefix_identical"] == u4["vetoed_token_not_drawn"]
                                                      and u4["n_unfired"] == u4["unfired_identical"]),
           "U5": u5, "U5_pass": u5["with_ngram"] == 0, "U6": u6,
           "U6_pass": bool(u6["n"] == u6["text_starts_with_prefix"] == u6["continued"]),
           "placebo_shuffle": {"observed_mean_gap_b_minus_a": obs_gap,
                               "shuffled_gap_mean": float(np.mean(shuffled_gap)) if shuffled_gap else None,
                               "shuffled_gap_q975": float(np.quantile(shuffled_gap, 0.975)) if shuffled_gap else None,
                               "route_structure_destroyed": bool(shuffled_gap and obs_gap > np.quantile(shuffled_gap, 0.975))},
           "rho_null_from_V_shuffle": {"mean": float(np.mean(rho_null)) if rho_null else None, "n": len(rho_null)},
           "hash_chain_ok": bool(chain_ok), "ordering": order}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("n_mismatches", "U4_pass", "U5_pass", "U6_pass", "hash_chain_ok")}),
          json.dumps(order))


if __name__ == "__main__":
    main()
