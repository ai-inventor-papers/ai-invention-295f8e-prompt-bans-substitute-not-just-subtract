#!/usr/bin/env python3
"""GPU stages after the twins (called from gpu7.py): forkscan (Part C), predict (Part D), sweep / collapsed / s4
(Part E), geometry (F7). Every stage resumes from data/continuations.jsonl and data/samples_raw.jsonl."""

from __future__ import annotations

import json
import math
import random
import time
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import torch
from loguru import logger
from scipy.stats import fisher_exact

import engine7 as EN
import forks as FK
import opening_cls as OC
from cfg7 import (CACHE_DIR, COLLAPSED, COLLAPSED_INFO, CONT_BATCH, CONTS, DATA_DIR, LABELS, N_CONFIRM, N_SCAN,
                  PRED_DIR, RESULTS_DIR, ROOT, SAMPLES_RAW, SCAN_HORIZON, SCAN_MAX, SCAN_STEP, TEMPLATES, THRESH,
                  UNITS, append_jsonl, log_deviation, read_json, read_jsonl, stable_seed, u_stream, utc_now, write_json)
from gpu7 import clear_prefills, label_pending, max_new_of
from prompts7 import load_prompts

CONT_LABELS = DATA_DIR / "continuation_labels.jsonl"


# ------------------------------------------------------------------------------------------------ helpers
def labels_by_sid() -> dict[str, dict[str, Any]]:
    return {r["sid"]: r for r in read_jsonl(LABELS)}


def twin_table(unit: str, arm: str = "TWIN") -> list[dict[str, Any]]:
    L = labels_by_sid()
    out = []
    for r in read_jsonl(SAMPLES_RAW):
        if r["unit"] == unit and r["arm"] == arm and r["sid"] in L:
            out.append({**r, "label": L[r["sid"]]["label"], "passed": bool(L[r["sid"]]["passed"])})
    return out


def cats(unit: str) -> list[str]:
    return UNITS[unit]["catalogue"] + ["other"]


def cat_index(unit: str, lab: str) -> int:
    c = cats(unit)
    return c.index(lab) if lab in c else len(c) - 1


def a_min_of(unit: str) -> str:
    p = RESULTS_DIR / "twins.json"
    if p.exists():
        t = read_json(p)
        if unit in t and t[unit].get("a_min"):
            return t[unit]["a_min"]
    return UNITS[unit]["a_min_plan"]


# ------------------------------------------------------------------------------------------------ continuations
def run_conts(model: Any, tok: Any, unit: str, items: list[dict[str, Any]], tag: str, batch: int = CONT_BATCH,
              horizon: int = SCAN_HORIZON) -> None:
    """Prefix-resampling continuations: prompt + prefix -> up to `horizon` new tokens, stopped early once OC_u decides
    (or the fence closes). Undecided rows are completed to the fence and fully labelled (label7)."""
    have = {r["cid"] for r in read_jsonl(CONTS)}
    todo = [it for it in items if it["cid"] not in have]
    if not todo:
        return
    t_all = time.time()
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        t0 = time.time()
        pres: dict[Any, dict[str, Any]] = {}
        rows = []
        for it in part:
            key = (it.get("pkey", it["w"]), it.get("edit_key"), tuple(it["prefix"]))
            if key not in pres:
                pres[key] = EN.prefill(model, it["prompt_ids"] + list(it["prefix"]), edits=it.get("edits"))
            rows.append({"pre": pres[key], "u": u_stream(*it["ukey"]), "T": it["T"], "top_k": it["top_k"],
                         "max_new": horizon, "fence": True, "text_prefix": tok.decode(list(it["prefix"]))})
        decided: dict[int, str] = {}

        def stop_fn(r: int, ids: list[int]) -> bool:
            lab = OC.classify(unit, rows[r]["text_prefix"] + tok.decode(ids, skip_special_tokens=True))
            if lab != "undecided":
                decided[r] = lab
                return True
            return False
        res = EN.decode_stop(model, rows, tok, "bench", stop_fn, check_every=8)
        recs = []
        need_completion = []
        for j, (it, r) in enumerate(zip(part, res)):
            txt = rows[j]["text_prefix"] + tok.decode(r["token_ids"], skip_special_tokens=True)
            lab = decided.get(j) or OC.classify(unit, txt)
            rec = {k: v for k, v in it.items() if k not in ("prompt_ids", "edits", "prefix")}
            rec.update({"prefix_len": len(it["prefix"]), "token_ids": r["token_ids"], "first_token":
                        r["token_ids"][0] if r["token_ids"] else None, "finish_reason": r["finish_reason"],
                        "n_tokens": r["n_tokens"], "oc_label": lab, "label": lab if lab != "undecided" else None,
                        "label_source": "OC" if lab != "undecided" else None, "utc": utc_now()})
            if lab == "undecided":
                rec["full_text"] = txt
                if r["finish_reason"] == "length":
                    need_completion.append((j, rec, it))
            recs.append(rec)
        # completion of undecided rows that hit the horizon
        if need_completion:
            crow = []
            for j, rec, it in need_completion:
                ids = it["prompt_ids"] + list(it["prefix"]) + rec["token_ids"]
                pre = EN.prefill(model, ids, edits=it.get("edits"))
                rest = max(16, max_new_of(unit) - len(it["prefix"]) - len(rec["token_ids"]))
                crow.append({"pre": pre, "u": u_stream(*it["ukey"])[len(rec["token_ids"]):], "T": it["T"],
                             "top_k": it["top_k"], "max_new": rest, "fence": True,
                             "text_prefix": rec["full_text"]})
            cres = EN.decode_stop(model, crow, tok, "bench", None, check_every=8)
            for (j, rec, it), cr in zip(need_completion, cres):
                rec["completion_ids"] = cr["token_ids"]
                rec["full_text"] = rec["full_text"] + tok.decode(cr["token_ids"], skip_special_tokens=True)
                lab = OC.classify(unit, rec["full_text"])
                if lab != "undecided":
                    rec.update({"oc_label": lab, "label": lab, "label_source": "OC_after_completion"})
            del crow, cres
        append_jsonl(CONTS, recs)
        del pres, rows, res
        torch.cuda.empty_cache()
        append_jsonl(RESULTS_DIR / "timing.jsonl", [{"tag": tag, "rows": len(part), "seconds":
                                                     round(time.time() - t0, 2), "utc": utc_now()}])
        logger.info(f"[{tag}] conts {i + len(part)}/{len(todo)} ({time.time() - t0:.1f}s; "
                    f"{(time.time() - t_all) / (i + len(part)):.3f}s/row)")
    label_undecided_conts()


def label_undecided_conts() -> None:
    """Full frozen labeller for continuations still undecided after OC (completed programs)."""
    rows = read_jsonl(CONTS)
    have = {r["sid"] for r in read_jsonl(CONT_LABELS)}
    todo = [{"sid": r["cid"], "unit": r["unit"], "text": r["full_text"]} for r in rows
            if r.get("label") is None and r.get("full_text") and r["cid"] not in have]
    if not todo:
        return
    tmp = CACHE_DIR / "tmp" / "conts_undecided.jsonl"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("".join(json.dumps(r) + "\n" for r in todo))
    out = CACHE_DIR / "tmp" / "conts_undecided_out.jsonl"
    import subprocess
    import sys
    pr = subprocess.run([sys.executable, str(ROOT / "src" / "label7.py"), str(tmp), str(out)], capture_output=True,
                        text=True, timeout=3600)
    if pr.returncode != 0:
        logger.error(pr.stderr[-2000:])
        raise RuntimeError("label worker failed on continuations")
    append_jsonl(CONT_LABELS, read_jsonl(out))
    logger.info(f"full-labelled {len(todo)} undecided continuations")


_CC: dict[str, Any] = {}


def _conts_cached() -> list[dict[str, Any]]:
    st = CONTS.stat() if CONTS.exists() else None
    key = (st.st_size, st.st_mtime) if st else None
    if _CC.get("key") != key:
        _CC["rows"] = read_jsonl(CONTS)
        _CC["key"] = key
    return _CC["rows"]


def cont_labels(filter_fn) -> list[dict[str, Any]]:
    full = {r["sid"]: r for r in read_jsonl(CONT_LABELS)}
    out = []
    for r in _conts_cached():
        if not filter_fn(r):
            continue
        lab = r.get("label")
        if lab is None:
            fl = full.get(r["cid"])
            lab = fl["label"] if fl else "other"
        out.append({**r, "final_label": lab})
    return out


# ------------------------------------------------------------------------------------------------ Part B/C
def twins_summary(tok: Any) -> dict[str, Any]:
    """Twin shares, A_min (runner-up of the new twin; amendment if it differs from the plan), OC validation."""
    out = read_json(RESULTS_DIR / "twins.json") if (RESULTS_DIR / "twins.json").exists() else {}
    for u in UNITS:
        tw = twin_table(u)
        if len(tw) < 50:
            continue
        D = UNITS[u]["default"]
        c = Counter(r["label"] for r in tw)
        cc = Counter(r["label"] for r in tw if r["passed"])
        nondef = [(m, c.get(m, 0)) for m in UNITS[u]["catalogue"] if m != D]
        runner = max(nondef, key=lambda x: x[1])[0]
        rec = {"n": len(tw), "counts": dict(c), "correct_counts": dict(cc),
               "pass_rate": sum(r["passed"] for r in tw) / len(tw), "default": D,
               "a_min_plan": UNITS[u]["a_min_plan"], "runner_up_new_twin": runner,
               "a_min": out.get(u, {}).get("a_min") or runner,
               "share_default": c.get(D, 0) / len(tw), "length_trunc": sum(r["finish_reason"] == "length"
                                                                             for r in tw)}
        rec["share_a_min"] = c.get(rec["a_min"], 0) / len(tw)
        rec["pass_rate_by_label"] = {m: (sum(r["passed"] for r in tw if r["label"] == m) /
                                         max(1, sum(r["label"] == m for r in tw))) for m in c}
        rec["record_share_iter5"] = UNITS[u]["record_share"]
        rec["within_0.15_of_record"] = abs(rec["share_a_min"] - UNITS[u]["record_share"]) <= 0.15
        if runner != UNITS[u]["a_min_plan"]:
            log_deviation(f"amend_a_min_{u}", f"{u}: the new twin's runner-up is {runner}, not the plan's "
                          f"{UNITS[u]['a_min_plan']} (amendment before COMMIT #1, as the plan prescribes)", "major")
        rec["mixed"] = rec["share_a_min"] >= 0.10
        out[u] = rec
    write_json(RESULTS_DIR / "twins.json", out)
    return out


def oc_validation(tok: Any) -> dict[str, Any]:
    """B4: OC_u agreement (first decision every 8 tokens up to 96 + 160 generated tokens) with the full labels on the
    100 new twin programs + iteration-5 instruct programs (>= 30 of A_min in total)."""
    res = {}
    e26 = read_jsonl(ROOT / "inputs" / "iter5_exp26" / "data" / "labels.jsonl")
    e25 = read_jsonl(ROOT / "inputs" / "iter5_exp25" / "data" / "labels" / "A3.jsonl")
    for u in UNITS:
        tw = twin_table(u)
        A = a_min_of(u)
        progs = [(r["token_ids"], r["label"], "new_twin") for r in tw if r["label"] in UNITS[u]["catalogue"]]
        old = [r for r in (e25 if u == "A3" else e26) if (r.get("unit", r.get("task")) == u) and
               (r.get("model_tag", r.get("model")) == "instruct") and r.get("code") and
               r.get("label") in UNITS[u]["catalogue"]]
        random.Random(7).shuffle(old)
        oldA = [r for r in old if r["label"] == A]
        nA_new = sum(1 for p in progs if p[1] == A)
        take = oldA[:max(0, 30 - nA_new)]
        take += [r for r in old if r not in take][:100 - len(take)]
        for r in take:
            progs.append((tok("```python\n" + r["code"] + "```", add_special_tokens=False)["input_ids"], r["label"],
                          "iter5"))
        agree = dec = 0
        conf = Counter()
        for ids, lab, src in progs:
            ids = ids[:SCAN_MAX + SCAN_HORIZON]
            oc = "undecided"
            for k in range(8, len(ids) + 8, 8):
                oc = OC.classify(u, tok.decode(ids[:k], skip_special_tokens=True))
                if oc != "undecided":
                    break
            if oc != "undecided":
                dec += 1
                agree += oc == lab
                if oc != lab:
                    conf[f"{lab}->{oc}"] += 1
        n = len(progs)
        res[u] = {"n": n, "n_a_min": sum(p[1] == A for p in progs), "coverage": dec / n,
                  "agreement_decided": agree / max(dec, 1), "confusions": dict(conf),
                  "pass": (agree / max(dec, 1)) >= THRESH["oc_agree"] and dec / n >= THRESH["oc_cover"],
                  "note": "iteration-5 rows were also inspected while the rules were written (not strictly held out); "
                          "the new twin programs are held out"}
    write_json(RESULTS_DIR / "opening_classifier.json", res)
    return res


def choose_base_paths(unit: str, op: dict[str, Any], tw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    D, A = UNITS[unit]["default"], a_min_of(unit)
    n_per = 4 if unit == "B6" else 6
    O = op["O"]
    out = []
    rng = random.Random(20261022)
    for cls in (D, A):
        cand = [r for r in tw if r["label"] == cls and r["passed"]]
        on = [r for r in cand if r["token_ids"][:len(O)] == O]
        off = [r for r in cand if r["token_ids"][:len(O)] != O]
        n_on = min(len(on), max(math.ceil(2 * n_per / 3), n_per - len(off)))
        pick = []
        for pool, m in ((on, n_on), (off, n_per - n_on)):
            byw = defaultdict(list)
            for r in pool:
                byw[r["template"]].append(r)
            for w in byw:
                rng.shuffle(byw[w])
            ws = sorted(byw)
            rng.shuffle(ws)
            got = []
            while len(got) < m and any(byw[w] for w in ws):
                for w in ws:
                    if byw[w] and len(got) < m:
                        got.append(byw[w].pop())
            pick += got
        for r in pick:
            out.append({"bid": f"{unit}_{cls}_{r['template']}_{r['slot']}", "cls": cls, "template": r["template"],
                        "slot": r["slot"], "sid": r["sid"], "token_ids": r["token_ids"],
                        "on_O": r["token_ids"][:len(O)] == O, "len": len(r["token_ids"])})
    return out


def scan_items(unit: str, bp: dict[str, Any], ks: list[int], n: int, tag: str, P: dict) -> list[dict[str, Any]]:
    w = bp["template"]
    pr = P[(unit, w, "twin")]
    return [{"cid": f"{unit}|{tag}|{bp['bid']}|{k}|{j}", "unit": unit, "w": w, "prompt_ids": pr["ids"],
             "prefix": bp["token_ids"][:k], "ukey": ["iter7fork", unit, bp["bid"], k, j] if tag == "scan" else
             ["iter7fork", unit, bp["bid"], k, tag, j], "T": 1.0, "top_k": 0, "kind": tag, "bid": bp["bid"], "k": k}
            for k in ks for j in range(n)]


def series_of(unit: str, bid: str, kinds: tuple[str, ...]) -> dict[int, np.ndarray]:
    rows = cont_labels(lambda r: r["unit"] == unit and r.get("bid") == bid and r.get("kind") in kinds)
    S: dict[int, np.ndarray] = {}
    for r in rows:
        v = S.setdefault(r["k"], np.zeros(len(cats(unit))))
        v[cat_index(unit, r["final_label"])] += 1
    return S


def stage_forkscan(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    tw_sum = twins_summary(tok)
    ocv = oc_validation(tok)
    logger.info(f"twins: { {u: (v['counts'], v['a_min']) for u, v in tw_sum.items()} }")
    logger.info(f"OC validation: { {u: (v['coverage'], v['agreement_decided']) for u, v in ocv.items()} }")
    forks_all = read_json(RESULTS_DIR / "forks.json") if (RESULTS_DIR / "forks.json").exists() else {}
    for u in units:
        if u not in UNITS or not tw_sum.get(u, {}).get("mixed", False):
            continue
        D, A = UNITS[u]["default"], a_min_of(u)
        tw = twin_table(u)
        progs = [(r["token_ids"], r["label"]) for r in tw]
        op = FK.opening(progs, D, A)
        bps = choose_base_paths(u, op, tw)
        logger.info(f"{u}: |O| = {op['len_O']}, cov {op['cov']:.2f}, clusters {[(c['id'], len(c['O']), c['cov']) for c in op['clusters']]};"
                    f" {len(bps)} base paths ({sum(b['on_O'] for b in bps)} on O)")
        # C3 scan
        items = []
        for bp in bps:
            ks = [k for k in range(0, SCAN_MAX + 1, SCAN_STEP) if k <= bp["len"] - 1]
            items += scan_items(u, bp, ks, N_SCAN, "scan", P)
        run_conts(model, tok, u, items, f"scan:{u}")
        clear_prefills()
        # C4 change points (+ F4 extension to 96-160 at step 8 when none is found)
        res_b = {}
        ext = []
        for bp in bps:
            S = series_of(u, bp["bid"], ("scan",))
            ks = sorted(S)
            arr = np.stack([S[k] for k in ks])
            cps = FK.change_points(arr, cat_index(u, bp["cls"]), THRESH["fork_pchange"], THRESH["fork_share_jump_bp"])
            if not cps and bp["len"] > SCAN_MAX + 1:
                ext += scan_items(u, bp, [k for k in range(SCAN_MAX + 8, 161, 8) if k <= bp["len"] - 1], N_SCAN,
                                  "scan", P)
            res_b[bp["bid"]] = cps
        if ext:
            log_deviation(f"F4_{u}", f"{u}: no change point within 96 tokens on some base paths -> scan extended to "
                          f"96-160 at step 8 (FALLBACK F4)")
            run_conts(model, tok, u, ext, f"scan_ext:{u}")
        # refine
        ref_items = []
        info_b = {}
        for bp in bps:
            S = series_of(u, bp["bid"], ("scan",))
            ks = sorted(S)
            arr = np.stack([S[k] for k in ks])
            own = cat_index(u, bp["cls"])
            cps = FK.change_points(arr, own, THRESH["fork_pchange"], THRESH["fork_share_jump_bp"])
            perm = FK.perm_stat(arr, own, 500, seed=stable_seed("perm", bp["bid"]) % 2 ** 31)
            prim = max(cps, key=lambda c: abs(c["jump"])) if cps else None
            info_b[bp["bid"]] = {"ks": ks, "series": arr.tolist(), "cps": [{k: v for k, v in c.items() if k != "post"}
                                                                          | {"k_tau": ks[c["tau_idx"]]} for c in cps],
                                 "primary": None if prim is None else ks[prim["tau_idx"]], "perm": perm,
                                 "own_share": [float(a[own] / max(a.sum(), 1)) for a in arr]}
            if prim is not None:
                k_tau = ks[prim["tau_idx"]]
                k_prev = ks[prim["tau_idx"] - 1]
                ref_items += scan_items(u, bp, [k for k in range(k_prev + 1, k_tau)], N_SCAN, "refine", P)
        run_conts(model, tok, u, ref_items, f"refine:{u}")
        # confirm
        conf_items = []
        for bp in bps:
            ib = info_b[bp["bid"]]
            if ib["primary"] is None:
                continue
            S = series_of(u, bp["bid"], ("scan", "refine"))
            own = cat_index(u, bp["cls"])
            k_tau = ib["primary"]
            k_prev = max(k for k in ib["ks"] if k < k_tau)
            sh = {k: float(S[k][own] / max(S[k].sum(), 1)) for k in S if k_prev <= k <= k_tau}
            f = FK.jump_position(sh)
            ib["refine_shares"] = sh
            ib["f"] = f
            if f is None:
                continue
            pos = sorted({f - 1, f, max(0, f - 9), min(bp["len"] - 1, f + 8)})
            ib["confirm_positions"] = pos
            conf_items += scan_items(u, bp, pos, N_CONFIRM, "confirm", P)
        run_conts(model, tok, u, conf_items, f"confirm:{u}")
        clear_prefills()
        for bp in bps:
            ib = info_b[bp["bid"]]
            if ib.get("f") is None:
                ib["confirmed"] = False
                continue
            S = series_of(u, bp["bid"], ("confirm",))
            own = cat_index(u, bp["cls"])
            f = ib["f"]
            cnt = {k: (int(S[k][own]), int(S[k].sum())) for k in S}
            c = FK.confirm(cnt[f - 1], cnt[f], cnt.get(max(0, f - 9)) if max(0, f - 9) != f - 1 else None,
                           cnt.get(min(bp["len"] - 1, f + 8)) if min(bp["len"] - 1, f + 8) != f else None,
                           THRESH["confirm_jump"], THRESH["confirm_fisher_p"], THRESH["control_move_max"])
            ib.update({"confirm": c, "confirmed": c["confirmed"], "confirm_counts": {str(k): v for k, v in cnt.items()},
                       "fork_token_id": bp["token_ids"][f - 1], "fork_token": tok.decode([bp["token_ids"][f - 1]]),
                       "fork_context": tok.decode(bp["token_ids"][max(0, f - 12):f]),
                       "at_O_plus_1": bool(bp["on_O"] and f == op["len_O"] + 1)})
        # C7 calibration: pooled k = 0 continuations vs the twin's A_min share
        k0 = cont_labels(lambda r: r["unit"] == u and r.get("kind") == "scan" and r.get("k") == 0)
        nA0 = sum(r["final_label"] == A for r in k0)
        nAt = sum(r["label"] == A for r in tw)
        pcal = fisher_exact([[nA0, len(k0) - nA0], [nAt, len(tw) - nAt]])[1]
        calib = {"k0_n": len(k0), "k0_a_min": nA0, "k0_share": nA0 / max(len(k0), 1), "twin_n": len(tw),
                 "twin_a_min": nAt, "twin_share": nAt / len(tw), "fisher_p": float(pcal),
                 "pass": bool(pcal > THRESH["calib_fisher_p"])}
        conf_on = [ib for b, ib in info_b.items() if ib.get("confirmed") and next(x for x in bps if x["bid"] == b)["on_O"]]
        mode = "ONE-TOKEN" if conf_on and sum(ib["at_O_plus_1"] for ib in conf_on) >= THRESH["onetoken_frac"] * len(conf_on) \
            else "TREE"
        forks_all[u] = {"D": D, "A_min": A, "opening": {"O": op["O"], "len_O": op["len_O"], "cov": op["cov"],
                                                        "O_text": tok.decode(op["O"]),
                                                        "clusters": [{**c, "O_text": tok.decode(c["O"])}
                                                                     for c in op["clusters"]]},
                        "base_paths": [{k: v for k, v in b.items() if k != "token_ids"} for b in bps],
                        "per_base_path": info_b, "calibration": calib, "mode": mode,
                        "n_confirmed": sum(bool(ib.get("confirmed")) for ib in info_b.values()),
                        "n_confirmed_on_O": len(conf_on),
                        "n_at_O_plus_1": sum(ib["at_O_plus_1"] for ib in conf_on)}
        write_json(RESULTS_DIR / "forks.json", forks_all)
        logger.info(f"{u}: mode {mode}; confirmed {forks_all[u]['n_confirmed']}/{len(bps)}; calibration {calib}")


def run_stage(st: str, model: Any, tok: Any, units: list[str]) -> None:
    if st == "forkscan":
        stage_forkscan(model, tok, units)
    else:
        import stages7b
        stages7b.run_stage(st, model, tok, units)
