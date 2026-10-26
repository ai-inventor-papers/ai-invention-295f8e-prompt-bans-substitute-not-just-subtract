#!/usr/bin/env python3
"""S6 base sub-arm ('is the model's answer the mean answer?'): Qwen3-8B (instruct) vs Qwen3-8B-Base teacher-forced on
IDENTICAL chat-templated token ids at the instruct model's decision positions and at phrasing positions.

Decision positions and classes:
  T1, T2, T10  art_MZAfDPVhM6Ui predictions/collapsed_raw.json: the fork node (generated index 3 / 3 / 10), the default
               class D (fork tokens whose forced continuations stay on the default, P(off) < 0.5) and the runner-up
               (T1, T2: the 16-token runner-up path segment; T10: the alternative-class tokens). Margin
               m = log P(D | prefix) - log P(runner-up | prefix) at T 1.
  B3, A3       this artifact's COMMIT #1-qwen openings: D = first-decision tokens classed as the default algorithm,
               runner-up = tokens classed as the minority algorithm.
Phrasing positions: the first 64 generated tokens of 20 programs per task (T1/T2/T10: the 20 iteration-7 Qwen3-8B
collapsed twin programs stored in art_MZAfDPVhM6Ui data/samples_raw.jsonl; B3/A3: this artifact's fit twins, slots 0-3
x W1-W5), minus the decision position. Per position: entropy under both models, the URIAL rank of the instruct
model's token under the base model (1 / 2-3 / >3), and the Jensen-Shannon divergence between the two next-token
distributions (top-256 supports, tail mass lumped), with an entropy-matched control (phrasing positions in the decision
position's base-entropy decile) and a rate-matched random-position control.
Template-free sensitivity: the user text + '\\n\\n' + the identical generated prefix, no chat tokens (margins only).
Committed predictions (COMMIT #0 protocol): on T1, T10, T2, m_instr - m_base >= 2 nats and |mean(H_base - H_instr)|
over phrasing positions < 0.5 nats. B3 and A3 are descriptive.
Usage: base_arm.py gpu qwen | gpu qwen_base | analyze
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg8 import (BOOT_SEED, RESULTS_DIR, SAMPLES_RAW, SRCS, TEMPLATES, THRESH, read_json, read_jsonl,
                  setup_logging, write_json)

TASKS = ("T1", "T10", "T2", "B3", "A3")
COLLAPSED = ("T1", "T10", "T2")
NPOS = 64
TOPK = 256


def _user_text(tok: Any, ids: list[int]) -> str:
    s = tok.decode(ids)
    m = re.search(r"<\|im_start\|>user\n([\s\S]*?)<\|im_end\|>", s)
    return m.group(1) if m else s


def decision_specs() -> dict[str, dict[str, Any]]:
    cr = read_json(SRCS["exp35"] / "predictions" / "collapsed_raw.json")
    sam = read_jsonl(SRCS["exp35"] / "data" / "samples_raw.jsonl")
    specs = {}
    for t in COLLAPSED:
        r = cr[t]
        f = int(r["fork_node_index"])
        progs = [s["token_ids"] for s in sam if s["unit"] == t and s.get("arm") == "TWIN6"]
        prefix = list(Counter(tuple(p[:f]) for p in progs).most_common(1)[0][0])
        D = [int(k) for k in r["tokens"] if r["phat_off"][str(k)] < 0.5]
        seg = (r.get("path") or {}).get("segment")
        alt = {"kind": "path", "ids": [int(x) for x in seg]} if seg else \
            {"kind": "tokens", "ids": [int(x) for x in r.get("alt_class_tokens") or []]}
        specs[t] = {"prefix": prefix, "D": D, "alt": alt, "d": f, "default": r["default"],
                    "instr_margin_iter7": r["margin_nats"]}
    for u in ("B3", "A3"):
        p = RESULTS_DIR / f"locate_{u}.json"
        if not p.exists():
            continue
        loc = read_json(p)
        if not loc["openings"]:
            continue
        o = max(loc["openings"], key=lambda o: sum(loc["on_cover_fit"][o["id"]].values()))
        co = o["classes"]["class_of"]
        D = [t for t in o["tokens"] if co.get(str(t)) == loc["default"]]
        A = [t for t in o["tokens"] if co.get(str(t)) == loc["minority"]]
        specs[u] = {"prefix": o["O"], "D": D, "alt": {"kind": "tokens", "ids": A}, "d": o["d"],
                    "default": loc["default"], "minority": loc["minority"], "opening": o["id"],
                    "phat": o["phat"], "tokens": o["tokens"], "bins": loc["bins"]}
    return specs


def phrasing_programs() -> dict[str, list[dict[str, Any]]]:
    sam = read_jsonl(SRCS["exp35"] / "data" / "samples_raw.jsonl")
    out: dict[str, list[dict[str, Any]]] = {}
    for t in COLLAPSED:
        rows = [s for s in sam if s["unit"] == t and s.get("arm") == "TWIN6"]
        rows = sorted(rows, key=lambda s: (s["template"], s["slot"]))[:20]
        out[t] = [{"w": s["template"], "ids": s["token_ids"][:NPOS]} for s in rows]
    mine = read_jsonl(SAMPLES_RAW)
    for u in ("B3", "A3"):
        rows = [s for s in mine if s["unit"] == u and s["arm"] == "fit" and s["slot"] < 4]
        out[u] = [{"w": s["template"], "ids": s["token_ids"][:NPOS]} for s in sorted(rows, key=lambda s: (s["template"],
                                                                                                         s["slot"]))]
    return out


@torch.no_grad()
def gpu(family: str) -> None:
    import engine8 as E
    from prompts8 import load_prompts
    setup_logging(f"base_arm_{family}")
    tok, model, info = E.load(family)
    P = load_prompts()
    specs = decision_specs()
    progs = phrasing_programs()
    out: dict[str, Any] = {"family": family, "load": info, "decision": {}, "phrasing": {}}
    for t, sp in specs.items():
        recs = {}
        for w in TEMPLATES:
            pr = P[(t, w)]["ids"]
            for mode, ids in (("chat", pr), ("plain", tok(_user_text(tok, pr) + "\n\n",
                                                          add_special_tokens=False)["input_ids"])):
                Z = E.teacher_force(model, ids, sp["prefix"])[-1].double()
                lp = torch.log_softmax(Z, -1)
                lD = float(torch.logsumexp(lp[torch.tensor(sp["D"], device=lp.device)], 0)) if sp["D"] else -math.inf
                if sp["alt"]["kind"] == "path":
                    Zp = E.teacher_force(model, ids, sp["prefix"] + sp["alt"]["ids"][:-1]).double()
                    lpp = torch.log_softmax(Zp[len(sp["prefix"]):], -1)
                    lA = float(sum(lpp[i, x] for i, x in enumerate(sp["alt"]["ids"])))
                else:
                    ids_a = sp["alt"]["ids"]
                    lA = float(torch.logsumexp(lp[torch.tensor(ids_a, device=lp.device)], 0)) if ids_a else -math.inf
                ent = float(-(lp.exp() * lp).sum())
                top = torch.topk(lp, TOPK)
                rec = {"logP_D": lD, "logP_alt": lA, "margin": lD - lA, "entropy": ent}
                if mode == "chat":
                    rec["top_ids"] = top.indices.tolist()
                    rec["top_lp"] = [round(float(x), 5) for x in top.values]
                    if "tokens" in sp:
                        rec["p_tokens"] = [float(lp[int(x)].exp()) for x in sp["tokens"]]
                recs[f"{w}|{mode}"] = rec
        out["decision"][t] = recs
        logger.info(f"{family} {t}: margins chat {[round(recs[f'{w}|chat']['margin'], 2) for w in TEMPLATES]}")
    for t, plist in progs.items():
        res = []
        for p in plist:
            pr = P[(t, p["w"])]["ids"]
            Z = E.teacher_force(model, pr, p["ids"][:-1]).double()[:len(p["ids"])]
            lp = torch.log_softmax(Z, -1)
            ids_t = torch.tensor(p["ids"], device=lp.device)
            ent = (-(lp.exp() * lp).sum(-1)).tolist()
            lpt = lp.gather(-1, ids_t[:, None]).squeeze(-1)
            rank = ((lp > lpt[:, None]).sum(-1) + 1).tolist()
            top = torch.topk(lp, TOPK, -1)
            res.append({"w": p["w"], "ids": p["ids"], "entropy": ent, "logp": lpt.tolist(), "rank": rank,
                        "top_ids": top.indices.cpu().numpy().astype(np.int32).tolist(),
                        "top_lp": np.round(top.values.cpu().numpy(), 4).tolist()})
        out["phrasing"][t] = res
    write_json(RESULTS_DIR / f"base_tf_{family}.json", out)
    E.free(model)


def js_div(ia: list[int], la: list[float], ib: list[int], lb: list[float]) -> float:
    """JS divergence (nats) between two distributions given by top-K supports; tail mass lumped into one bucket."""
    pa = {i: math.exp(l) for i, l in zip(ia, la)}
    pb = {i: math.exp(l) for i, l in zip(ib, lb)}
    keys = set(pa) | set(pb)
    ta = max(0.0, 1 - sum(pa.values()))
    tb = max(0.0, 1 - sum(pb.values()))
    js = 0.0
    for k in list(keys) + ["_tail"]:
        a = pa.get(k, 0.0) if k != "_tail" else ta
        b = pb.get(k, 0.0) if k != "_tail" else tb
        m = 0.5 * (a + b)
        if a > 0:
            js += 0.5 * a * math.log(a / m)
        if b > 0:
            js += 0.5 * b * math.log(b / m)
    return js


def analyze() -> dict[str, Any]:
    setup_logging("base_arm_analyze")
    I = read_json(RESULTS_DIR / "base_tf_qwen.json")
    B = read_json(RESULTS_DIR / "base_tf_qwen_base.json")
    specs = decision_specs()
    rng = np.random.default_rng(BOOT_SEED + 5)
    out: dict[str, Any] = {}
    for t in TASKS:
        if t not in I["decision"] or t not in B["decision"]:
            continue
        mi = [I["decision"][t][f"{w}|chat"]["margin"] for w in TEMPLATES]
        mb = [B["decision"][t][f"{w}|chat"]["margin"] for w in TEMPLATES]
        mb_plain = [B["decision"][t][f"{w}|plain"]["margin"] for w in TEMPLATES]
        mi_plain = [I["decision"][t][f"{w}|plain"]["margin"] for w in TEMPLATES]
        js_dec = [js_div(I["decision"][t][f"{w}|chat"]["top_ids"], I["decision"][t][f"{w}|chat"]["top_lp"],
                         B["decision"][t][f"{w}|chat"]["top_ids"], B["decision"][t][f"{w}|chat"]["top_lp"])
                  for w in TEMPLATES]
        H_dec_i = [I["decision"][t][f"{w}|chat"]["entropy"] for w in TEMPLATES]
        H_dec_b = [B["decision"][t][f"{w}|chat"]["entropy"] for w in TEMPLATES]
        # phrasing positions
        pi, pb = I["phrasing"][t], B["phrasing"][t]
        d = specs[t]["d"]
        dH, jsP, ranks, Hb_all, Hi_all, prog_dh = [], [], Counter(), [], [], []
        dec_rank = Counter()
        for a, b in zip(pi, pb):
            on_dec = a["ids"][:d] == specs[t]["prefix"]
            per = []
            for k in range(min(len(a["entropy"]), len(b["entropy"]))):
                if k == d and on_dec:
                    r = b["rank"][k]
                    dec_rank["1" if r == 1 else ("2-3" if r <= 3 else ">3")] += 1
                    continue
                per.append(b["entropy"][k] - a["entropy"][k])
                Hb_all.append(b["entropy"][k])
                Hi_all.append(a["entropy"][k])
                r = b["rank"][k]
                ranks["1" if r == 1 else ("2-3" if r <= 3 else ">3")] += 1
                jsP.append((js_div(a["top_ids"][k], a["top_lp"][k], b["top_ids"][k], b["top_lp"][k]), b["entropy"][k]))
            dH += per
            prog_dh.append(per)
        boots = []
        for _ in range(1000):
            idx = rng.integers(0, len(prog_dh), len(prog_dh))
            v = [x for i in idx for x in prog_dh[i]]
            boots.append(float(np.mean(v)) if v else 0.0)
        Hb_dec = float(np.mean(H_dec_b))
        Hb_arr = np.array(Hb_all)
        js_arr = np.array([x for x, _ in jsP])
        Hjs = np.array([h for _, h in jsP])
        dec_q = np.searchsorted(np.quantile(Hb_arr, np.linspace(0, 1, 11)[1:-1]), Hb_dec)
        qs = np.quantile(Hb_arr, np.linspace(0, 1, 11))
        lo, hi = qs[min(dec_q, 9)], qs[min(dec_q + 1, 10)]
        matched = js_arr[(Hjs >= lo) & (Hjs <= hi)]
        rand = rng.choice(js_arr, size=min(len(js_arr), 5 * len(js_dec)), replace=False) if len(js_arr) else js_arr
        rec = {"margin_instr": mi, "margin_base": mb, "margin_gain": [x - y for x, y in zip(mi, mb)],
               "margin_gain_mean": float(np.mean([x - y for x, y in zip(mi, mb)])),
               "margin_base_template_free": mb_plain, "margin_instr_template_free": mi_plain,
               "margin_gain_template_free_mean": float(np.mean([x - y for x, y in zip(mi_plain, mb_plain)])),
               "phrasing_dH_mean": float(np.mean(dH)) if dH else None,
               "phrasing_dH_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
               "n_phrasing_positions": len(dH), "urial_rank_phrasing": dict(ranks), "urial_rank_decision": dict(dec_rank),
               "js_decision_mean": float(np.mean(js_dec)), "js_phrasing_mean": float(np.mean(js_arr)) if len(js_arr) else None,
               "js_entropy_matched_mean": float(np.mean(matched)) if len(matched) else None,
               "js_random_positions_mean": float(np.mean(rand)) if len(rand) else None,
               "js_ratio_decision_vs_phrasing": float(np.mean(js_dec) / np.mean(js_arr)) if len(js_arr) else None,
               "js_ratio_decision_vs_entropy_matched": float(np.mean(js_dec) / np.mean(matched)) if len(matched) else None,
               "entropy_decision_base": H_dec_b, "entropy_decision_instr": H_dec_i,
               "pctile_base_entropy_at_decision": float((Hb_arr < Hb_dec).mean() * 100) if len(Hb_arr) else None,
               "pctile_instr_entropy_at_decision": float((np.array(Hi_all) < np.mean(H_dec_i)).mean() * 100)
               if Hi_all else None}
        if t in COLLAPSED:
            rec["prediction_margin_gain_ge_2"] = bool(rec["margin_gain_mean"] >= THRESH["base_margin_gain"])
            rec["prediction_phrasing_abs_dH_lt_0.5"] = bool(rec["phrasing_dH_mean"] is not None and
                                                            abs(rec["phrasing_dH_mean"]) < THRESH["base_phrasing_dH"])
        else:
            sp = specs[t]
            cf = np.zeros(len(sp["bins"]))
            for w in TEMPLATES:
                pt = B["decision"][t][f"{w}|chat"]["p_tokens"]
                for tk, p in zip(sp["tokens"], pt):
                    cf += p * np.asarray(sp["phat"][str(tk)]) / 5
            rec["base_fork_counterfactual_shares"] = {b: float(x) for b, x in zip(sp["bins"], cf / max(cf.sum(), 1e-12))}
        out[t] = rec
        logger.info(f"base arm {t}: gain {rec['margin_gain_mean']:.2f} nats, phrasing dH {rec['phrasing_dH_mean']}")
    coll = [out[t] for t in COLLAPSED if t in out]
    verdict = {"n_collapsed": len(coll),
               "margin_gain_ge_2_all": all(r["prediction_margin_gain_ge_2"] for r in coll) if coll else None,
               "phrasing_abs_dH_lt_0.5_all": all(r["prediction_phrasing_abs_dH_lt_0.5"] for r in coll) if coll else None}
    verdict["pass"] = bool(verdict["margin_gain_ge_2_all"] and verdict["phrasing_abs_dH_lt_0.5_all"])
    res = {"tasks": out, "verdict": verdict, "base_repertoire": base_repertoire()}
    write_json(RESULTS_DIR / "base_subarm.json", res)
    return res


def base_repertoire() -> dict[str, Any]:
    """Descriptive: the base model's sampled repertoire from art_CcZLW-9NX00l (plain completion, Qwen3-8B-Base)."""
    try:
        d = read_json(SRCS["exp24"] / "method_out.json")
    except (FileNotFoundError, ValueError):
        return {}
    out: dict[str, Counter] = {}
    for ds in d["datasets"]:
        if ds["dataset"] != "base_repertoire":
            continue
        for ex in ds["examples"]:
            out.setdefault(ex.get("metadata_task"), Counter())[str(ex.get("predict_BASE_PLAIN"))] += 1
    return {k: dict(v) for k, v in out.items()}


if __name__ == "__main__":
    if sys.argv[1] == "gpu":
        gpu(sys.argv[2])
    else:
        analyze()
