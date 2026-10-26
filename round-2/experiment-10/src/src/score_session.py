#!/usr/bin/env python3
"""HF scoring sessions (one process each; never in the same process as vLLM).

--phase B (S3): T3 engine agreement, T4 KV-reuse checks, B1 proposal (every forced program of j under every forced prompt
  used for j), B2 baselines (5 segments + baseline_empty), B4 selection of the two highest-baseline-FRLP non-default bans.
--phase D (S5): full matrices per task (ban/mention x K x 5, nonce x 5, novelty, listall x 5, two-step x 5 on all
  programs; neutral / nonce-neutral / two-step-neutral per half on that half's programs), the ban displacement rho and six
  patch-style random edits on baseline_empty (T7), and the optional FRLP-only route test (arms c, d; T8).
Scores are checkpointed per (task, condition) under frlp/parts/<task>/<cond>.parquet, so a crash resumes.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from loguru import logger

from src.ws import DATA, FRLP_DIR, LOGS, RESULTS, append_jsonl, model_path, read_jsonl, setup_logging, write_json
from src import config as K
from src.frlp import Scorer, clean_store_hook, edit_hook, logmeanexp, unit_directions

BAND = list(range(11, 22))  # decoder layers 11-21 (middle third of 32)
PARTS = FRLP_DIR / "parts"
DEADLINE_FILE = LOGS / "deadline_epoch.txt"


def deadline_left_min() -> float:
    try:
        return (float(DEADLINE_FILE.read_text().strip()) - time.time()) / 60.0
    except (FileNotFoundError, ValueError):
        return 1e9


def load_programs(task: str) -> list[dict[str, Any]]:
    rows = [r for r in read_jsonl(DATA / "forced_set.jsonl") if r["task"] == task and r["scrub_mode"] != "dropped"]
    summ = json.loads((RESULTS / "forced_set_summary.json").read_text())["per_algorithm"]
    excluded = {k for k, v in summ.items() if v["excluded_M_lt_10"]}  # F5: M_j < 10 -> j leaves FRLP and C1
    return [r for r in rows if f"{task}:{r['j']}" not in excluded]


def part_path(task: str, cond: str) -> Path:
    safe = cond.replace(":", "__").replace("+", "_and_")
    return PARTS / task / f"{safe}.parquet"


class Session:
    def __init__(self):
        self.sc = Scorer(model_path())
        self.cache: dict[str, Any] = {}

    def state(self, prompt: dict[str, Any]):
        key = prompt["sha"]
        if key not in self.cache:
            if len(self.cache) > 4:
                self.cache.clear()
                torch.cuda.empty_cache()
            self.cache[key] = self.sc.prefill(prompt["ids"])
        return self.cache[key]

    def run_cond(self, task: str, cond: str, prompt: dict[str, Any] | None, progs: list[dict[str, Any]],
                 st=None, variant_ids: str = "scored_ids", meta: dict[str, Any] | None = None) -> pd.DataFrame | None:
        pp = part_path(task, cond)
        if pp.exists():
            return None
        if not progs:
            return None
        t0 = time.time()
        st = st if st is not None else self.state(prompt)
        ids = [p[variant_ids] for p in progs]
        nf = [p["n_fence"] for p in progs]
        lf, lb = self.sc.score(st, ids, nf)
        df = pd.DataFrame({"program_id": [p["program_id"] for p in progs], "cond": cond, "l_full": lf, "l_body": lb,
                           "n_tokens": [len(i) for i in ids], "prompt_sha": prompt["sha"] if prompt else "hybrid"})
        for k, v in (meta or {}).items():
            df[k] = v
        pp.parent.mkdir(parents=True, exist_ok=True)
        tmp = pp.with_suffix(".tmp")
        df.to_parquet(tmp, index=False)
        tmp.replace(pp)
        dt = time.time() - t0
        ntok = int(sum(len(i) for i in ids))
        append_jsonl(LOGS / "timing.jsonl", [{"utc": time.time(), "stage": "hf_score", "task": task, "cond": cond,
                                              "n": len(progs), "tokens": ntok, "seconds": round(dt, 3),
                                              "per_unit_s": round(dt / max(1, len(progs)), 5)}])
        logger.debug(f"{task} {cond}: {len(progs)} programs, {ntok} tokens, {dt:.2f}s")
        return df


def forced_prompts_used(task: str, j: str) -> list[dict[str, Any]]:
    """Every forced prompt actually used to generate attempts for j (standard paraphrases + descriptive if used)."""
    raw = [r for r in read_jsonl(DATA / "raw_gen.jsonl") if r["task"] == task and r["X"] == j
           and r["kind"] in ("forced", "forced_desc")]
    used = sorted({(r["kind"], r["paraphrase_id"]) for r in raw})
    return [K.p_forced(task, j, k, descriptive=(kind == "forced_desc")) for kind, k in used]


# ------------------------------------------------------------------------------------------------ tests
def t3_t4(ses: Session) -> dict[str, Any]:
    from labeller.extract import extract_code  # canon (sys.path via src.ws)
    from src.scrub import scored_text

    tok = K.tokenizer()
    res: dict[str, Any] = {"t3": [], "t4": {}}
    rows = [r for r in read_jsonl(DATA / "raw_gen.jsonl") if r.get("gen_logprobs")]
    for r in rows[:8]:
        code, _ = extract_code(r["text"])
        if code is None:
            continue
        ids = tok(scored_text(code), add_special_tokens=False)["input_ids"]
        gen = [g for g in r["gen_ids"] if g not in K.EOS_IDS]
        lp_v = [x for g, x in zip(r["gen_ids"], r["gen_logprobs"]) if g not in K.EOS_IDS]
        s = int(r["condition"].split(":s")[1])
        p = K.p_baseline(r["task"], s)
        st = ses.state(p)
        hf = ses.sc.per_token(st, gen)
        d = np.abs(np.asarray(hf) - np.asarray(lp_v, dtype=float))
        res["t3"].append({"row_id": r["row_id"], "ids_equal_scored_text": ids == gen, "n_tokens": len(gen),
                          "mean_abs_diff_nats_per_token": float(d.mean()), "max_abs_diff": float(d.max()),
                          "sum_hf": float(np.sum(hf)), "sum_vllm": float(np.sum(lp_v)),
                          "sum_abs_diff": float(abs(np.sum(hf) - np.sum(lp_v)))})
    t3 = res["t3"]
    res["t3_pass"] = bool(t3) and all(x["mean_abs_diff_nats_per_token"] < 0.05 and x["sum_abs_diff"] < 2.0 for x in t3)
    # T4: cached-prefix batched scores vs single full-sequence forward; batch-order invariance
    progs = load_programs("t1")[:8]
    prompts = [K.p_baseline("t1", 0), K.p_ban("t1", "bfs", 1)]
    diffs, order_diffs = [], []
    for p in prompts:
        st = ses.sc.prefill(p["ids"])
        lf, _ = ses.sc.score(st, [q["scored_ids"] for q in progs], [q["n_fence"] for q in progs])
        perm = np.random.default_rng(0).permutation(len(progs))
        old = ses.sc.budget
        ses.sc.budget = 1200  # different batch composition
        lf2, _ = ses.sc.score(st, [progs[i]["scored_ids"] for i in perm], [progs[i]["n_fence"] for i in perm])
        ses.sc.budget = old
        back = np.empty_like(lf2)
        back[perm] = lf2
        order_diffs += list(np.abs(back - lf))
        for q, v in zip(progs, lf):
            ref = float(ses.sc.full_sequence(p["ids"], q["scored_ids"]).sum())
            diffs.append(abs(ref - v))
    res["t4"] = {"max_abs_diff_vs_full_forward": float(max(diffs)), "mean_abs_diff_vs_full_forward": float(np.mean(diffs)),
                 "max_abs_diff_batch_order": float(max(order_diffs)), "n": len(diffs),
                 "pass_0.02": bool(max(diffs) < 0.02 and max(order_diffs) < 0.02)}
    logger.info(f"T3: {[(x['ids_equal_scored_text'], round(x['mean_abs_diff_nats_per_token'], 4), round(x['sum_abs_diff'], 3)) for x in t3]}")
    logger.info(f"T4: {res['t4']}")
    return res


# ------------------------------------------------------------------------------------------------ phase B
def phase_b() -> None:
    ses = Session()
    tests = t3_t4(ses)
    write_json(RESULTS / "tests_scoring_B.json", tests)
    for task in K.TASKS:
        progs = load_programs(task)
        by_j: dict[str, list[dict[str, Any]]] = {}
        for p in progs:
            by_j.setdefault(p["j"], []).append(p)
        for j, pj in by_j.items():
            for fp in forced_prompts_used(task, j):
                ses.run_cond(task, fp["cond"], fp, pj, meta={"role": "proposal", "proposal_for": j})
        for s in range(5):
            p = K.p_baseline(task, s)
            ses.run_cond(task, p["cond"], p, progs, meta={"role": "baseline"})
        p = K.p_baseline_empty(task)
        ses.run_cond(task, p["cond"], p, progs, meta={"role": "baseline"})
        logger.info(f"{task}: phase B scored ({len(progs)} programs)")
    select_nondefault()


def load_scores(task: str) -> pd.DataFrame:
    fs = sorted((PARTS / task).glob("*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def proposal_logq(task: str, df: pd.DataFrame, progs: list[dict[str, Any]], mode: str = "mixture") -> pd.Series:
    """l(p | F_j) per program: logmeanexp over the forced prompts used for j (mixture), or the generating paraphrase,
    or the exp1 5-template mixture (standard paraphrases 0-4)."""
    prop = df[df["role"] == "proposal"] if "role" in df else df[df["cond"].str.startswith("forced")]
    out = {}
    for p in progs:
        rows = prop[prop["program_id"] == p["program_id"]]
        if mode == "generating":
            v = rows[rows["cond"] == p["generating_cond"]]["l_full"].to_numpy()
        elif mode == "exp1_5tpl":
            v = rows[rows["cond"].isin([f"forced:{p['j']}:k{k}" for k in range(5)])]["l_full"].to_numpy()
        else:
            v = rows["l_full"].to_numpy()
        out[p["program_id"]] = float(logmeanexp(v)) if len(v) else np.nan
    return pd.Series(out)


def select_nondefault() -> None:
    sel = json.loads((RESULTS / "selections.json").read_text())
    for task in K.TASKS:
        progs = load_programs(task)
        df = load_scores(task)
        lq = proposal_logq(task, df, progs)
        d = sel[f"{task}_default"]
        L = {}
        for j in sorted({p["j"] for p in progs}):
            ids = [p["program_id"] for p in progs if p["j"] == j]
            vals = []
            for s in range(5):
                sub = df[df["cond"] == f"baseline:s{s}"].set_index("program_id").loc[ids, "l_full"]
                vals.append(float(logmeanexp((sub - lq.loc[ids]).to_numpy())))
            L[j] = float(np.mean(vals))
        ranking = sorted([j for j in L if j != d], key=lambda j: -L[j])
        sel[f"{task}_nondefault_bans"] = ranking[:2]
        sel[f"{task}_baseline_frlp_ranking"] = {j: L[j] for j in [d] + ranking}
        logger.info(f"{task}: baseline FRLP mean_s L_j = {L}; non-default bans = {ranking[:2]}")
    write_json(RESULTS / "selections.json", sel)


# ------------------------------------------------------------------------------------------------ phase D
def conditions_all(task: str, d: str, s_star: str) -> list[dict[str, Any]]:
    out = []
    for x in K.MODES[task]:
        for w in K.WS_:
            out.append(K.p_ban(task, x, w))
            out.append(K.p_mention(task, x, w))
    for w in K.WS_:
        out.append(K.p_nonce(task, w))
        out.append(K.p_twostep(task, d, s_star, w))
    out.append(K.p_novelty(task))
    for p_ in range(5):
        out.append(K.p_listall(task, p_))
    return out


def conditions_half(task: str, d: str, s_star: str, h: int) -> list[dict[str, Any]]:
    out = []
    for x in K.MODES[task]:
        for w in K.WS_:
            out.append(K.p_neutral(task, x, w, h))
    for w in K.WS_:
        out.append(K.p_nonce_neutral(task, w, h))
        out.append(K.p_twostep_neutral(task, d, s_star, w, h))
    return out


def ban_displacement(ses: Session, task: str) -> dict[str, Any]:
    path = RESULTS / f"ban_displacement_{task}.json"
    if path.exists():
        return json.loads(path.read_text())
    norms = []
    for x in K.MODES[task]:
        for w in K.WS_:
            b, n = K.p_ban(task, x, w), K.p_neutral(task, x, w, 1)
            assert b["spec_start"] == n["spec_start"] and len(b["ids"]) == len(n["ids"])
            S = slice(b["spec_start"], b["R"] + 1)
            hb = ses.sc.capture(b["ids"], BAND, S)
            hn = ses.sc.capture(n["ids"], BAND, S)
            norms.append((hb - hn).norm(dim=-1).cpu().numpy())  # [n_band, n_pos]
            # clean-state norms for reference
    rho = np.mean(np.stack(norms), axis=0)
    e = K.p_baseline_empty(task)
    Se = slice(e["spec_start"], e["R"] + 1)
    hc = ses.sc.capture(e["ids"], BAND, Se)
    out = {"task": task, "band_layers": BAND, "n_pairs": len(norms), "n_positions": int(rho.shape[1]),
           "rho": rho.tolist(), "rho_mean_per_layer": rho.mean(axis=1).tolist(),
           "clean_norm_mean_per_layer": hc.norm(dim=-1).mean(dim=1).cpu().numpy().tolist(),
           "rho_over_clean_norm_mean": float(np.mean(rho / hc.norm(dim=-1).cpu().numpy()))}
    write_json(path, out)
    return out


def edit_state(ses: Session, task: str, rho: np.ndarray, r: torch.Tensor):
    e = K.p_baseline_empty(task)
    S = slice(e["spec_start"], e["R"] + 1)
    store: dict[int, torch.Tensor] = {}
    ses.sc.prefill(e["ids"], hooks=[(l, clean_store_hook(store, l, S)) for l in BAND])
    rho_t = torch.tensor(rho, dtype=torch.float32)
    hooks = [(l, edit_hook(store[l], rho_t[i], r, S)) for i, l in enumerate(BAND)]
    return ses.sc.prefill(e["ids"], hooks=hooks), store, e, S


def t7_edit_hooks(ses: Session, task: str, rho: np.ndarray, r: torch.Tensor) -> dict[str, Any]:
    progs = load_programs(task)[:6]
    e = K.p_baseline_empty(task)
    base = ses.sc.prefill(e["ids"])
    lf0, _ = ses.sc.score(base, [p["scored_ids"] for p in progs], [p["n_fence"] for p in progs])
    st0, _, _, _ = edit_state(ses, task, np.zeros_like(rho), r)
    lfz, _ = ses.sc.score(st0, [p["scored_ids"] for p in progs], [p["n_fence"] for p in progs])
    # displacement check: capture band outputs under the edit
    S = slice(e["spec_start"], e["R"] + 1)
    store: dict[int, torch.Tensor] = {}
    ses.sc.prefill(e["ids"], hooks=[(l, clean_store_hook(store, l, S)) for l in BAND])
    rho_t = torch.tensor(rho, dtype=torch.float32)
    captured: dict[int, torch.Tensor] = {}
    pre: dict[int, torch.Tensor] = {}

    def cap(l):
        def fn(_m, _i, out):
            captured[l] = out[0, :].float().clone()
        return fn

    first_band = BAND[0]
    handles = []
    hooks = [(l, edit_hook(store[l], rho_t[i], r, S)) for i, l in enumerate(BAND)]
    for l, fn in hooks:
        handles.append(ses.sc.layers[l].register_forward_hook(fn))
    for l in BAND + [first_band - 1]:
        handles.append(ses.sc.layers[l].register_forward_hook(cap(l)))
    with torch.inference_mode():
        ses.sc.model.model(input_ids=torch.tensor([e["ids"]], device="cuda"), use_cache=False)
    for h in handles:
        h.remove()
    clean_full: dict[int, torch.Tensor] = {}
    hs = []
    for l in [first_band - 1] + BAND:
        def mk(l=l):
            def fn(_m, _i, out):
                clean_full[l] = out[0, :].float().clone()
            return fn
        hs.append(ses.sc.layers[l].register_forward_hook(mk()))
    with torch.inference_mode():
        ses.sc.model.model(input_ids=torch.tensor([e["ids"]], device="cuda"), use_cache=False)
    for h in hs:
        h.remove()
    rel = []
    for i, l in enumerate(BAND):
        disp = (captured[l][S] - clean_full[l][S]).norm(dim=-1).cpu().numpy()
        rel.append(float(np.max(np.abs(disp - rho[i]) / np.maximum(rho[i], 1e-6))))
    outside = float((captured[BAND[0]][: e["spec_start"]] - clean_full[BAND[0]][: e["spec_start"]]).abs().max())
    before = float((captured[first_band - 1] - clean_full[first_band - 1]).abs().max())
    return {"rho0_max_abs_score_diff": float(np.max(np.abs(lfz - lf0))),
            "rho0_exact": bool(np.max(np.abs(lfz - lf0)) == 0.0),
            "displacement_max_rel_err_per_layer": rel, "max_rel_err": float(max(rel)),
            "pass_1e-3": bool(max(rel) < 1e-3), "pass_bf16_tol_1e-2": bool(max(rel) < 1e-2),
            "outside_S_max_abs_change_first_band_layer": outside, "layer_before_band_max_abs_change": before}


def phase_d(do_route: bool = True, min_route_minutes: float = 75.0) -> None:
    ses = Session()
    sel = json.loads((RESULTS / "selections.json").read_text())
    tests: dict[str, Any] = {}
    for task in K.TASKS:
        d = sel[f"{task}_default"]
        s_star = sel[f"{task}_substitute"]["s_star"]
        progs = load_programs(task)
        halves = {h: [p for p in progs if p["half"] == h] for h in (1, 2)}
        t0 = time.time()
        conds = conditions_all(task, d, s_star)
        for i, p in enumerate(conds):
            ses.run_cond(task, p["cond"], p, progs, meta={"role": p["kind"]})
            if i == 2:
                logger.info(f"{task}: first 3 conditions in {time.time() - t0:.1f}s; projected all-program block "
                            f"{(time.time() - t0) / 3 * len(conds) / 60:.1f} min; deadline left {deadline_left_min():.0f} min")
        for h in (1, 2):
            for p in conditions_half(task, d, s_star, h):
                ses.run_cond(task, p["cond"], p, halves[h], meta={"role": p["kind"], "half": h})
        logger.info(f"{task}: matrices done in {(time.time() - t0) / 60:.1f} min")
        # random edits
        disp = ban_displacement(ses, task)
        rho = np.asarray(disp["rho"])
        dirs = torch.cat([unit_directions(0, 3, 4096), unit_directions(1, 3, 4096)])
        tests[f"t7_{task}"] = t7_edit_hooks(ses, task, rho, dirs[0])
        logger.info(f"T7 {task}: {tests[f't7_{task}']}")
        for k in range(6):
            cond = f"edit:k{k + 1}"
            if part_path(task, cond).exists():
                continue
            st, _, e, _ = edit_state(ses, task, rho, dirs[k])
            ses.run_cond(task, cond, e, progs, st=st, meta={"role": "edit", "edit_seed": 0 if k < 3 else 1})
        write_json(RESULTS / "tests_scoring_D.json", tests)
    # route test (optional)
    if do_route and deadline_left_min() >= min_route_minutes:
        for task in K.TASKS:
            d = sel[f"{task}_default"]
            progs = load_programs(task)
            for w in K.WS_:
                for h in (1, 2):
                    b, n = K.p_ban(task, d, w), K.p_neutral(task, d, w, h)
                    sb, sn = ses.sc.prefill(b["ids"]), ses.sc.prefill(n["ids"])
                    split = b["spec_start"]
                    hp = [p for p in progs if p["half"] == h]
                    if not tests.get(f"t8_{task}") and w == 1 and h == 1:
                        a_full = ses.sc.hybrid(sb, sb, split, sb)
                        b_full = ses.sc.hybrid(sn, sn, split, sn)
                        ids = [p["scored_ids"] for p in hp[:6]]
                        nf = [p["n_fence"] for p in hp[:6]]
                        la, _ = ses.sc.score(sb, ids, nf)
                        la2, _ = ses.sc.score(a_full, ids, nf)
                        lb, _ = ses.sc.score(sn, ids, nf)
                        lb2, _ = ses.sc.score(b_full, ids, nf)
                        tests[f"t8_{task}"] = {"max_abs_diff_a": float(np.max(np.abs(la - la2))),
                                               "max_abs_diff_b": float(np.max(np.abs(lb - lb2))),
                                               "pass_0.02": bool(max(np.max(np.abs(la - la2)), np.max(np.abs(lb - lb2))) < 0.02)}
                        logger.info(f"T8 {task}: {tests[f't8_{task}']}")
                    arm_c = ses.sc.hybrid(sn, sb, split, sb)  # neutral K/V < spec_start, ban K/V >= spec_start, ban logits
                    arm_d = ses.sc.hybrid(sb, sn, split, sn)  # ban K/V < spec_start, neutral K/V >= spec_start
                    ses.run_cond(task, f"route_c:{d}:w{w}:h{h}", b, hp, st=arm_c, meta={"role": "route_c", "half": h})
                    ses.run_cond(task, f"route_d:{d}:w{w}:h{h}", b, hp, st=arm_d, meta={"role": "route_d", "half": h})
                    del sb, sn, arm_c, arm_d
                    torch.cuda.empty_cache()
        tests["route_test_ran"] = True
    else:
        tests["route_test_ran"] = False
        tests["route_test_skip_reason"] = f"deadline left {deadline_left_min():.0f} min < {min_route_minutes}"
    write_json(RESULTS / "tests_scoring_D.json", tests)


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["B", "D", "select"], required=True)
    ap.add_argument("--no-route", action="store_true")
    a = ap.parse_args()
    setup_logging(f"score_{a.phase}")
    if a.phase == "B":
        phase_b()
    elif a.phase == "select":
        select_nondefault()
    else:
        phase_d(do_route=not a.no_route)


if __name__ == "__main__":
    main()
