#!/usr/bin/env python3
"""Headline re-derivation through a DIFFERENT code path (float64 NumPy, no src/ imports), from raw files only:
  W1-TF   shares of ROWS_ALL / ROWS_A / ROWS_D and the RAND_ISO null (median, max, empirical p) from the cached bf16
          fork states (cache/fork_*.pt), the raw safetensors lm_head rows and the committed null draws (npz)
  W1-GEN  correct counts and exact McNemar (main 30, pooled 90, x3 dose) from data/gen_samples + data/gen_labels
  W2      late-joint vs early-joint shares from the raw per-prompt margins in results/w2_rows.jsonl
Placebos that must FAIL: each RAND_ISO draw treated as the observed arm (its empirical p among the other 49 should
be ~uniform, ~5% below 0.05); arm labels randomly swapped within CRN pairs (median McNemar p >= 0.3); a constant
arm (m_arm = m_I, share exactly 0). Usage: .venv/bin/python audit/rederive_headline.py -> results/rederive_headline.json
"""
import json
import math
import os
import random
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open

ROOT = Path(__file__).resolve().parents[1]
REV = {"qwen": ("Qwen--Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"),
       "qwen_base": ("Qwen--Qwen3-8B-Base", "49e3418fbbbca6ecbdf9608b4d22e5a407081db4")}


def rows(key, ids):
    hub = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
    snap = hub / f"models--{REV[key][0]}" / "snapshots" / REV[key][1]
    fn = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]["lm_head.weight"]
    with safe_open(str(snap / fn), framework="pt") as fh:
        sl = fh.get_slice("lm_head.weight")
        return np.stack([sl[i:i + 1][0].double().numpy() for i in ids])


def lse(x):
    m = x.max(-1, keepdims=True)
    return (m + np.log(np.exp(x - m).sum(-1, keepdims=True)))[..., 0]


def margin(h, R, nD):
    z = h @ R.T
    return lse(z[..., :nD]) - lse(z[..., nD:])


def share(mI, mX, mB):
    return float(np.sum(mI - mX) / np.sum(mI - mB))


def mcnemar(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


out = {"W1_TF": {}, "W1_GEN": {}, "W2": {}, "placebos": {}}
units = json.loads((ROOT / "inputs/iter9/results/units.json").read_text())
rng = random.Random(5)
for u in ("T10", "B3"):
    f = units[u]["forks"][0]
    S, nD = [int(t) for t in f["D"]] + [int(t) for t in f["A"]], len(f["D"])
    ci = torch.load(ROOT / f"cache/fork_instr_{u}.pt")["caps"]
    cb = torch.load(ROOT / f"cache/fork_base_{u}.pt")["caps"]
    hI = np.stack([c["h_fin"].double().numpy() for c in ci])
    hB = np.stack([c["h_fin"].double().numpy() for c in cb])
    WI, WB = rows("qwen", S), rows("qwen_base", S)
    mI, mB = margin(hI, WI, nD), margin(hB, WB, nD)
    arms = {"ROWS_ALL": WB, "ROWS_A": np.concatenate([WI[:nD], WB[nD:]]), "ROWS_D": np.concatenate([WB[:nD], WI[nD:]])}
    sh = {a: share(mI, margin(hI, R, nD), mB) for a, R in arms.items()}
    iso = np.load(ROOT / f"results/null_draws_{u}.npz")["RAND_ISO"].astype(np.float64)
    null = np.array([share(mI, margin(hI, WI + iso[k], nD), mB) for k in range(len(iso))])
    p = (1 + (null >= sh["ROWS_ALL"]).sum()) / (1 + len(null))
    out["W1_TF"][u] = {"gap_mean": float((mI - mB).mean()), **sh, "RAND_ISO_median": float(np.median(null)),
                       "RAND_ISO_max": float(null.max()), "empirical_p_vs_RAND_ISO": float(p)}
    # placebo: each null draw as the 'observed' arm against the other 49 -> p should be ~uniform
    pl = [(1 + (np.delete(null, k) >= null[k]).sum()) / len(null) for k in range(len(null))]
    out["placebos"][f"W1_{u}_null_as_observed_frac_p_le_0.05"] = float(np.mean(np.array(pl) <= 0.05))
    out["placebos"][f"W1_{u}_constant_arm_share"] = share(mI, mI.copy(), mB)

lab = {r["sid"]: r for r in jl(ROOT / "data/gen_labels.jsonl")}
good = {"T10": {"dfs"}, "B3": {"prim_heap", "prim_array"}}
ind = {}
for r in jl(ROOT / "data/gen_samples.jsonl"):
    L = lab[r["sid"]]
    ind.setdefault((r["unit"], r["arm"]), {})[(r["template"], r["slot"])] = int(L["label"] in good[r["unit"]] and L["passed"])


def test(u, a, b, pool=False):
    x = dict(ind[(u, a)]); y = dict(ind[(u, b)])
    if pool:
        x.update(ind[(u, a + "_EXTRA60")]); y.update(ind[(u, b + "_EXTRA60")])
    ks = sorted(set(x) & set(y))
    bb = sum(x[k] and not y[k] for k in ks); cc = sum(y[k] and not x[k] for k in ks)
    swp = []
    for _ in range(300):
        b2 = c2 = 0
        for k in ks:
            p_, q_ = (x[k], y[k]) if rng.random() < 0.5 else (y[k], x[k])
            b2 += p_ and not q_; c2 += q_ and not p_
        swp.append(mcnemar(b2, c2))
    return {"a_correct": sum(x.values()), "b_correct": sum(y.values()), "n": len(ks), "b": bb, "c": cc,
            "p": mcnemar(bb, cc), "placebo_label_swap_median_p": float(np.median(swp))}


for u in ("T10", "B3"):
    out["W1_GEN"][u] = {"ROWS_vs_TWIN_30": test(u, "ROWS", "TWIN"), "ROWS_vs_RAND_MED_30": test(u, "ROWS", "RAND_MED"),
                        "ROWS_vs_TWIN_pooled90": test(u, "ROWS", "TWIN", True),
                        "ROWS_vs_RAND_MED_pooled90": test(u, "ROWS", "RAND_MED", True),
                        "FPD_vs_TWIN_30": test(u, "FPD", "TWIN"),
                        "ROWS_L3_vs_RAND_MED_L3": test(u, "ROWS_L3", "RAND_MED_L3"),
                        "ROWS_L3_vs_RAND_RESID_MED_L3": test(u, "ROWS_L3", "RAND_RESID_MED_L3")}

w2 = jl(ROOT / "results/w2_rows.jsonl")
for u in ("T10", "B3"):
    def sh2(cfg):
        r = {x["pid"]: x for x in w2 if x["unit"] == u and x["scope"] == "A" and x["config"] == cfg}
        return float(sum(v["m_I"] - v["m"] for v in r.values()) / sum(v["m_I"] - v["m_B"] for v in r.values()))
    out["W2"][u] = {"W_late_joint": sh2("W_late_joint"), "E_joint": sh2("E_joint"),
                    "late_minus_early": sh2("W_late_joint") - sh2("E_joint")}

# comparison with the reported (aggregated) numbers
rep = json.loads((ROOT / "results/w1_tf_summary.json").read_text())["units"]
out["agreement_vs_reported"] = {u: {a: abs(out["W1_TF"][u][a] - rep[u]["arms"][a]["share"]) for a in ("ROWS_ALL", "ROWS_A",
                                                                                                    "ROWS_D")}
                                for u in ("T10", "B3")}
(ROOT / "results/rederive_headline.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1)[:4000])
