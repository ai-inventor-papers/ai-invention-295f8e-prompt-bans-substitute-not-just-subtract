#!/usr/bin/env python3
"""Extension (pre-registered as COMMIT #4 before any of its tokens): a generation dose-response of the readout-row
edit. Can a stronger edit of the fork-class rows steer which algorithm the model writes, and is that specific to the
base-row delta? Arms (same CRN engine, slots and fixed batch shape B = 6 as W1-GEN):
  ROWS_L2, ROWS_L3          fork-class rows w_I,t + lambda * Delta_t, lambda = 2, 3 (fork step only)
  RAND_MED_L2, RAND_MED_L3  the committed RAND_ISO median-share draw scaled by the same lambda (matched control)
Committed first: teacher-forced shares at these doses and the predicted counts from the fork distributions.

Second extension (COMMIT #5, before any of its tokens): the STRONGER nulls at the strongest dose (lambda = 3), because
isotropic rows are a straw man and the teacher-forced residual-subspace null matched the base rows: the RAND_RESID and
DELTA_SWAP draws with the median and the maximum teacher-forced share (lambda = 1), each scaled x3.

Third extension (COMMIT #7, before any of its tokens): power. 60 additional CRN slots (12 per template, slot
s = 30 + 12 * template_index + k, uniforms np.random.default_rng(9101 + s)) for TWIN, ROWS and RAND_MED at lambda = 1,
pooled with the committed 30 into 90 McNemar pairs. The committed 30-slot verdict is unchanged by this extension.

Usage: w1_dose_gen.py commit | gpu | commit_strong | gpu_strong | commit_power | gpu_power | analyze_power
"""

from __future__ import annotations

import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import (DATA_DIR, I9_RES, MAX_NEW, PRED_DIR, RESULTS_DIR, ROOT, SEED0, SLOTS_PER_T, UNITS_TF,
                   append_jsonl, commit, import_iter9, ledger, model_path, read_json, read_jsonl, setup_logging,
                   sha256_text, utc_now)

import_iter9()
from b2gen9 import slot_prompts, token_map  # noqa: E402

LAMS = (2.0, 3.0)
DOSE_ARMS = ("ROWS_L2", "ROWS_L3", "RAND_MED_L2", "RAND_MED_L3")


def rows_for(arm: str, WI_S: torch.Tensor, Delta: torch.Tensor, iso_med: torch.Tensor) -> torch.Tensor:
    lam = float(arm.split("_L")[1])
    return WI_S + lam * (Delta if arm.startswith("ROWS") else iso_med)


def commit_plan() -> dict[str, Any]:
    from transformers import AutoTokenizer
    from w1_tf import UnitData, load_readout, share
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    plan = read_json(PRED_DIR / "commit2_w1tf_genplan.json")["gen_predictions"]
    out: dict[str, Any] = {"lams": LAMS, "arms": DOSE_ARMS, "units": {}}
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB)
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        iso_med = torch.from_numpy(nul["RAND_ISO"][plan[u]["rand_draws"]["RAND_MED"]])
        bins, tmap = token_map(u, d.fork)
        idx_of = {pid: i for i, pid in enumerate(d.pids)}
        sp = slot_prompts(units[u])
        rec: dict[str, Any] = {"tf_share": {}, "predicted_shares": {}, "predicted_unmapped": {}, "top": {}}
        for a in DOSE_ARMS:
            r = rows_for(a, d.WI_S, d.Delta, iso_med)
            rec["tf_share"][a] = share(d.mI, d.m_rows(r), d.mB)
            z = d.z_with_rows(r)
            mix_all, unm, tops = [], [], {}
            for _, p in sp:
                i = idx_of[p["pid"]]
                pr = torch.softmax(z[i].double(), -1).numpy()
                mix = np.zeros(len(bins))
                mapped = 0.0
                for t, v in tmap.items():
                    mix += pr[t] * v
                    mapped += pr[t]
                mix_all.append(mix)
                unm.append(1 - mapped)
                tops[p["pid"]] = [(tok.decode([int(t)]), float(pr[t])) for t in np.argsort(-pr)[:6]]
            m = np.mean(mix_all, 0)
            rec["predicted_shares"][a] = dict(zip(bins, m.tolist()))
            rec["predicted_unmapped"][a] = float(np.mean(unm))
            rec["top"][a] = tops
        corr = ["dfs"] if u == "T10" else ["prim_heap", "prim_array"]
        rec["predicted_correct_count_of_30"] = {a: 30 * sum(rec["predicted_shares"][a][b] for b in corr)
                                                for a in DOSE_ARMS}
        rec["rand_med_draw"] = plan[u]["rand_draws"]["RAND_MED"]
        out["units"][u] = rec
        logger.info(f"dose plan {u}: TF shares {rec['tf_share']}; predicted correct {rec['predicted_correct_count_of_30']}"
                    f"; unmapped {rec['predicted_unmapped']}")
    out["tests"] = ["ROWS_L2_vs_TWIN", "ROWS_L3_vs_TWIN", "ROWS_L2_vs_RAND_MED_L2", "ROWS_L3_vs_RAND_MED_L3"]
    out["note"] = "extension beyond the plan (dose-response in generation); descriptive, no verdict threshold"
    commit("commit4_dose_gen", out, files=[ROOT / "src" / "w1_dose_gen.py"])
    ledger("COMMIT4")
    return out


@torch.no_grad()
def gpu() -> None:
    from capture10 import CM, full_logits, load
    from w1_gen import RAW, generate, uniforms
    from w1_tf import load_readout
    t0 = time.time()
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    plan = read_json(PRED_DIR / "commit4_dose_gen.json")
    WB_cpu, _ = load_readout("qwen_base")
    W = model.lm_head.weight
    done = {r["sid"] for r in read_jsonl(RAW)}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        WI_S = W[S].float()
        Delta = WB_cpu[S].float().cuda() - WI_S
        iso_med = torch.from_numpy(nul["RAND_ISO"][plan["units"][u]["rand_med_draw"]]).cuda()
        mx = MAX_NEW[u]
        open_txt = tok.decode(f["opening"])
        for ti, (i, p) in enumerate(slot_prompts(units[u])):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            slots, Urows = uniforms(ti, mx)
            for a in DOSE_ARMS:
                sids = [f"{u}|{a}|{p['template']}|{k}" for k in range(SLOTS_PER_T)]
                if all(s in done for s in sids):
                    continue
                rows = rows_for(a, WI_S, Delta, iso_med)

                def fork_fn(h: torch.Tensor, rows: torch.Tensor = rows) -> torch.Tensor:
                    z = full_logits(W, h)
                    z[:, S] = h.float() @ rows.T
                    return z
                tb = time.time()
                gen, fin = generate(model, tok, kv, ids, fork_fn, Urows, mx)
                recs = []
                for r in range(len(gen)):
                    txt = tok.decode(gen[r])
                    if "```" in txt:
                        txt = txt[:txt.index("```") + 3]
                    full = open_txt + txt
                    recs.append({"sid": sids[r], "unit": u, "task": u, "arm": a, "template": p["template"],
                                 "prompt_id": p["pid"], "slot": slots[r], "seed": SEED0 + slots[r],
                                 "fork_token": tok.decode([gen[r][0]]), "fork_token_id": gen[r][0],
                                 "n_tokens": len(gen[r]), "truncated": not fin[r], "text": full,
                                 "code_sha256": sha256_text(full), "engine": "hf-bf16", "batch_shape": len(gen),
                                 "utc": utc_now()})
                append_jsonl(RAW, recs)
                logger.info(f"[{u}] {p['template']} {a}: {time.time() - tb:.1f}s; fork tokens "
                            f"{[x['fork_token'] for x in recs]}")
            del kv
            torch.cuda.empty_cache()
    ledger("DOSE_GEN_end", seconds=round(time.time() - t0, 1))


STRONG_ARMS = ("RAND_RESID_MED_L3", "RAND_RESID_MAX_L3", "DELTA_SWAP_MED_L3", "DELTA_SWAP_MAX_L3")


def strong_draws(u: str) -> dict[str, tuple[str, int]]:
    w1 = read_json(RESULTS_DIR / "w1_tf_summary.json")["units"][u]["nulls"]
    out = {}
    for nt in ("RAND_RESID", "DELTA_SWAP"):
        sh = np.array(w1[nt]["shares"])
        out[f"{nt}_MED_L3"] = (nt, int(np.argsort(sh)[len(sh) // 2]))
        out[f"{nt}_MAX_L3"] = (nt, int(np.argmax(sh)))
    return out


def commit_strong() -> dict[str, Any]:
    from transformers import AutoTokenizer
    from w1_tf import UnitData, load_readout, share
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    out: dict[str, Any] = {"lam": 3.0, "arms": STRONG_ARMS, "units": {}}
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB)
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        dr = strong_draws(u)
        bins, tmap = token_map(u, d.fork)
        idx_of = {pid: i for i, pid in enumerate(d.pids)}
        sp = slot_prompts(units[u])
        rec: dict[str, Any] = {"draws": dr, "tf_share_lam3": {}, "tf_share_lam1": {}, "predicted_shares": {},
                               "predicted_unmapped": {}, "top": {}}
        for a, (nt, k) in dr.items():
            dl = torch.from_numpy(nul[nt][k])
            rec["tf_share_lam1"][a] = share(d.mI, d.m_rows(d.WI_S + dl), d.mB)
            r = d.WI_S + 3.0 * dl
            rec["tf_share_lam3"][a] = share(d.mI, d.m_rows(r), d.mB)
            z = d.z_with_rows(r)
            mix_all, unm, tops = [], [], {}
            for _, p in sp:
                i = idx_of[p["pid"]]
                pr = torch.softmax(z[i].double(), -1).numpy()
                mix = np.zeros(len(bins))
                mapped = 0.0
                for t, v in tmap.items():
                    mix += pr[t] * v
                    mapped += pr[t]
                mix_all.append(mix)
                unm.append(1 - mapped)
                tops[p["pid"]] = [(tok.decode([int(t)]), float(pr[t])) for t in np.argsort(-pr)[:6]]
            rec["predicted_shares"][a] = dict(zip(bins, np.mean(mix_all, 0).tolist()))
            rec["predicted_unmapped"][a] = float(np.mean(unm))
            rec["top"][a] = tops
        corr = ["dfs"] if u == "T10" else ["prim_heap", "prim_array"]
        rec["predicted_correct_count_of_30"] = {a: 30 * sum(rec["predicted_shares"][a][b] for b in corr)
                                                for a in STRONG_ARMS}
        out["units"][u] = rec
        logger.info(f"strong-null plan {u}: TF share x1 {rec['tf_share_lam1']}, x3 {rec['tf_share_lam3']}; predicted "
                    f"correct {rec['predicted_correct_count_of_30']}; unmapped {rec['predicted_unmapped']}")
    out["tests"] = [f"ROWS_L3_vs_{a}" for a in STRONG_ARMS]
    out["note"] = ("second extension: the stronger nulls at lambda = 3 in generation; descriptive; the question is "
                   "whether the base-row delta direction is special for steering the WRITTEN algorithm relative to "
                   "equally large edits aimed where the fork residual lives")
    commit("commit5_strong_null_gen", out, files=[ROOT / "src" / "w1_dose_gen.py"])
    ledger("COMMIT5")
    return out


@torch.no_grad()
def gpu_strong() -> None:
    from capture10 import CM, full_logits, load
    from w1_gen import RAW, generate, uniforms
    t0 = time.time()
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    plan = read_json(PRED_DIR / "commit5_strong_null_gen.json")
    W = model.lm_head.weight
    done = {r["sid"] for r in read_jsonl(RAW)}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        WI_S = W[S].float()
        arm_rows = {a: WI_S + 3.0 * torch.from_numpy(nul[nt][k]).cuda()
                    for a, (nt, k) in plan["units"][u]["draws"].items()}
        mx = MAX_NEW[u]
        open_txt = tok.decode(f["opening"])
        for ti, (i, p) in enumerate(slot_prompts(units[u])):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            slots, Urows = uniforms(ti, mx)
            for a in STRONG_ARMS:
                sids = [f"{u}|{a}|{p['template']}|{k}" for k in range(SLOTS_PER_T)]
                if all(s in done for s in sids):
                    continue
                rows = arm_rows[a]

                def fork_fn(h: torch.Tensor, rows: torch.Tensor = rows) -> torch.Tensor:
                    z = full_logits(W, h)
                    z[:, S] = h.float() @ rows.T
                    return z
                tb = time.time()
                gen, fin = generate(model, tok, kv, ids, fork_fn, Urows, mx)
                recs = []
                for r in range(len(gen)):
                    txt = tok.decode(gen[r])
                    if "```" in txt:
                        txt = txt[:txt.index("```") + 3]
                    full = open_txt + txt
                    recs.append({"sid": sids[r], "unit": u, "task": u, "arm": a, "template": p["template"],
                                 "prompt_id": p["pid"], "slot": slots[r], "seed": SEED0 + slots[r],
                                 "fork_token": tok.decode([gen[r][0]]), "fork_token_id": gen[r][0],
                                 "n_tokens": len(gen[r]), "truncated": not fin[r], "text": full,
                                 "code_sha256": sha256_text(full), "engine": "hf-bf16", "batch_shape": len(gen),
                                 "utc": utc_now()})
                append_jsonl(RAW, recs)
                logger.info(f"[{u}] {p['template']} {a}: {time.time() - tb:.1f}s; fork tokens "
                            f"{[x['fork_token'] for x in recs]}")
            del kv
            torch.cuda.empty_cache()
    ledger("STRONG_GEN_end", seconds=round(time.time() - t0, 1))


POWER_ARMS = ("TWIN", "ROWS", "RAND_MED")
N_EXTRA_PER_T = 12


def extra_slots(ti: int) -> list[int]:
    return [30 + N_EXTRA_PER_T * ti + k for k in range(N_EXTRA_PER_T)]


def commit_power() -> dict[str, Any]:
    plan = read_json(PRED_DIR / "commit2_w1tf_genplan.json")["gen_predictions"]
    out: dict[str, Any] = {"arms": POWER_ARMS, "n_extra": 5 * N_EXTRA_PER_T, "slot_rule": "s = 30 + 12 * ti + k, k < 12",
                           "seeds": "9101 + s (9131-9190)", "units": {}}
    for u in UNITS_TF:
        pc = plan[u]["predicted_count_correct_class_of_30"]
        out["units"][u] = {"predicted_correct_of_60": {a: 2 * pc[a] for a in POWER_ARMS},
                           "predicted_correct_of_90_pooled": {a: 3 * pc[a] for a in POWER_ARMS}}
    out["tests"] = ["pooled 90-pair exact McNemar ROWS vs TWIN and ROWS vs RAND_MED (descriptive)"]
    commit("commit7_power_gen", out, files=[ROOT / "src" / "w1_dose_gen.py"])
    ledger("COMMIT7")
    logger.info(f"power plan: {out['units']}")
    return out


@torch.no_grad()
def gpu_power() -> None:
    from capture10 import CM, full_logits, load
    from w1_gen import RAW, generate
    from w1_tf import load_readout
    t0 = time.time()
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    plan = read_json(PRED_DIR / "commit2_w1tf_genplan.json")["gen_predictions"]
    WB_cpu, _ = load_readout("qwen_base")
    W = model.lm_head.weight
    done = {r["sid"] for r in read_jsonl(RAW)}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        WI_S = W[S].float()
        rows = {"ROWS": WB_cpu[S].float().cuda(),
                "RAND_MED": WI_S + torch.from_numpy(nul["RAND_ISO"][plan[u]["rand_draws"]["RAND_MED"]]).cuda()}
        mx = MAX_NEW[u]
        open_txt = tok.decode(f["opening"])
        for ti, (i, p) in enumerate(slot_prompts(units[u])):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            sl = extra_slots(ti)
            for b0 in range(0, len(sl), SLOTS_PER_T):
                slots = sl[b0:b0 + SLOTS_PER_T]
                Urows = torch.tensor(np.stack([np.random.default_rng(SEED0 + s_).random(mx) for s_ in slots]))
                for a in POWER_ARMS:
                    arm = f"{a}_EXTRA60"
                    sids = [f"{u}|{arm}|{p['template']}|{s_}" for s_ in slots]
                    if all(x in done for x in sids):
                        continue

                    def fork_fn(h: torch.Tensor, a: str = a) -> torch.Tensor:
                        z = full_logits(W, h)
                        if a in rows:
                            z[:, S] = h.float() @ rows[a].T
                        return z
                    tb = time.time()
                    gen, fin = generate(model, tok, kv, ids, fork_fn, Urows, mx)
                    recs = []
                    for r in range(len(gen)):
                        txt = tok.decode(gen[r])
                        if "```" in txt:
                            txt = txt[:txt.index("```") + 3]
                        full = open_txt + txt
                        recs.append({"sid": sids[r], "unit": u, "task": u, "arm": arm, "template": p["template"],
                                     "prompt_id": p["pid"], "slot": slots[r], "seed": SEED0 + slots[r],
                                     "fork_token": tok.decode([gen[r][0]]), "fork_token_id": gen[r][0],
                                     "n_tokens": len(gen[r]), "truncated": not fin[r], "text": full,
                                     "code_sha256": sha256_text(full), "engine": "hf-bf16", "batch_shape": len(gen),
                                     "utc": utc_now()})
                    append_jsonl(RAW, recs)
                    logger.info(f"[{u}] {p['template']} {arm} slots {slots[0]}-{slots[-1]}: {time.time() - tb:.1f}s; "
                                f"fork tokens {[x['fork_token'] for x in recs]}")
            del kv
            torch.cuda.empty_cache()
    ledger("POWER_GEN_end", seconds=round(time.time() - t0, 1))


def analyze_power() -> dict[str, Any]:
    import stats9 as S9
    from cfg10 import CORRECT, write_json
    raw = read_jsonl(DATA_DIR / "gen_samples.jsonl")
    lab = {r["sid"]: r for r in read_jsonl(DATA_DIR / "gen_labels.jsonl")}
    plan = read_json(PRED_DIR / "commit7_power_gen.json")
    out: dict[str, Any] = {"utc": utc_now(), "units": {}}
    for u in UNITS_TF:
        ind: dict[str, dict] = {}
        for r in raw:
            if r["unit"] != u or r["sid"] not in lab:
                continue
            base = r["arm"].replace("_EXTRA60", "")
            if base not in POWER_ARMS:
                continue
            ok = int(lab[r["sid"]]["label"] in CORRECT[u] and bool(lab[r["sid"]]["passed"]))
            ind.setdefault(base, {})[(r["template"], r["slot"])] = ok
            ind.setdefault(r["arm"] if r["arm"].endswith("_EXTRA60") else base + "_MAIN30", {})[
                (r["template"], r["slot"])] = ok
        cells = {a: {"n": len(d), "n_correct": sum(d.values()), "correct_ci95": S9.wilson(sum(d.values()), len(d))}
                 for a, d in ind.items()}
        tests = {}
        for a, b in (("ROWS", "TWIN"), ("ROWS", "RAND_MED"), ("RAND_MED", "TWIN"),
                     ("ROWS_EXTRA60", "TWIN_EXTRA60"), ("ROWS_EXTRA60", "RAND_MED_EXTRA60")):
            if a not in ind or b not in ind:
                continue
            ks = sorted(set(ind[a]) & set(ind[b]))
            bb = sum(1 for k in ks if ind[a][k] == 1 and ind[b][k] == 0)
            cc = sum(1 for k in ks if ind[a][k] == 0 and ind[b][k] == 1)
            tests[f"{a}_vs_{b}"] = {"n_pairs": len(ks), "b_first_only": bb, "c_second_only": cc,
                                    "p_exact_two_sided": S9.mcnemar_exact(bb, cc)}
        out["units"][u] = {"cells": cells, "tests": tests, "predicted": plan["units"][u]}
        logger.info(f"power {u}: " + "; ".join(f"{a} {c['n_correct']}/{c['n']}" for a, c in cells.items()) + " | " +
                    "; ".join(f"{k} {t['b_first_only']}:{t['c_second_only']} p={t['p_exact_two_sided']:.3g}"
                              for k, t in tests.items()))
    write_json(RESULTS_DIR / "w1_generation_power.json", out)
    return out


if __name__ == "__main__":
    setup_logging(f"w1_dose_gen_{sys.argv[1]}")
    {"commit": commit_plan, "gpu": gpu, "commit_strong": commit_strong, "gpu_strong": gpu_strong,
     "commit_power": commit_power, "gpu_power": gpu_power, "analyze_power": analyze_power}[sys.argv[1]]()
