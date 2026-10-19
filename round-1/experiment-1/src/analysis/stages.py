#!/usr/bin/env python3
"""Analysis stages: elicit, external, assoc, freeze, bans, succession, score, outputs."""

from __future__ import annotations

import asyncio
import json
import os
from collections import Counter
from typing import Any

from loguru import logger

from common import (CATALOGUE, DATA_DIR, DECODING_MAIN, ELICIT_DIR, EXT_MODEL, MODES, OTHER, PRED_DIR, ROOT,
                    TASKS, THRESHOLDS, commit_file, read_commitments, read_jsonl, request_seed, sha256_file,
                    sha256_text, utc_now, write_json, write_jsonl)

RAW_PREBAN = DATA_DIR / "raw_preban.jsonl"
RAW_RETRY = DATA_DIR / "raw_elicit_retry.jsonl"
RAW_BANS = DATA_DIR / "raw_bans.jsonl"
RAW_SUCC = DATA_DIR / "raw_succession.jsonl"
LABELLED = DATA_DIR / "labelled.jsonl"
ASSOC_FILE = ELICIT_DIR / "assoc_objects.json"
BASELINE_FILE = ELICIT_DIR / "baseline_objects.json"
MAX_RETRY = 3


def conds() -> dict[str, Any]:
    return json.loads((ROOT / "prompts" / "conditions.json").read_text())


# ------------------------------------------------------------------------------------------------ elicit
def _rank_rows_with_retries(rows: list[dict[str, Any]], regen) -> list[dict[str, Any]]:
    """rows: one row per (task, X, sample_id) first attempt. Invalid parses are resampled (new seed, same
    prompt) up to MAX_RETRY times via regen(list_of_retry_requests) -> rows."""
    from analysis.assoc import parse_ranking

    final: dict[str, dict[str, Any]] = {}
    pending = []
    for r in rows:
        k = f"{r['task']}|{r['mode_X']}|{r['paraphrase_id']}"
        parsed, why = parse_ranking(r["text"], len(MODES[r["task"]]) - 1)
        rec = {"task": r["task"], "mode_X": r["mode_X"], "sample_id": r["paraphrase_id"],
               "option_order": r["option_order"], "raw": r["text"], "attempt": 0, "valid": parsed is not None,
               "parse_status": why, "model": r.get("model"),
               "parsed": [r["option_order"][ord(ch) - ord("A")] for ch in parsed] if parsed else None}
        final[k] = rec
        if parsed is None:
            pending.append((k, r))
    n_invalid_first = len(pending)
    for attempt in range(1, MAX_RETRY + 1):
        if not pending:
            break
        reqs = []
        for k, r in pending:
            rq = {kk: r[kk] for kk in ("task", "condition", "mode_X", "paraphrase_id", "option_order", "kind",
                                       "prompt", "n", "temperature", "max_tokens", "decoding") if kk in r}
            stage = f"retry{attempt}"
            rq.update({"req_id": f"{r['task']}|{r['condition']}|{r['paraphrase_id']}|{stage}", "stage": stage,
                       "seed": request_seed(r["task"], r["condition"], r["paraphrase_id"], stage)})
            reqs.append(rq)
        outs = regen(reqs)
        by = {f"{o['task']}|{o['mode_X']}|{o['paraphrase_id']}": o for o in outs}
        nxt = []
        for k, r in pending:
            o = by.get(k)
            if o is None:
                nxt.append((k, r))
                continue
            parsed, why = parse_ranking(o["text"], len(MODES[o["task"]]) - 1)
            rec = final[k]
            rec.update({"raw_retry": o["text"], "attempt": attempt, "valid": parsed is not None, "parse_status": why,
                        "parsed": [o["option_order"][ord(ch) - ord("A")] for ch in parsed] if parsed else None})
            if parsed is None:
                nxt.append((k, {**r, **{"text": o["text"]}}))
        pending = nxt
    logger.info(f"rankings: {len(rows)} first attempts, {n_invalid_first} invalid first time, "
                f"{len(pending)} still invalid after {MAX_RETRY} retries")
    return list(final.values())


def stage_elicit() -> None:
    from analysis.assoc import map_freetext
    from gen.run_vllm import run_requests

    rows = read_jsonl(RAW_PREBAN)
    rank = [r for r in rows if r["kind"] == "rank"]
    c = conds()

    def regen(reqs):
        for q in reqs:
            q["prompt"] = c["tasks"][q["task"]]["elicit_rank"][q["mode_X"]][q["paraphrase_id"]]["prompt"]
        run_requests(reqs, RAW_RETRY, concurrency=16)
        ids = {q["req_id"] for q in reqs}
        return [o for o in read_jsonl(RAW_RETRY) if o["req_id"] in ids]

    ranks = _rank_rows_with_retries(rank, regen)
    write_jsonl(ELICIT_DIR / "qwen_rankings.jsonl", ranks)
    free = []
    for r in rows:
        if r["kind"] == "free":
            free.append({"task": r["task"], "mode_X": r["mode_X"], "sample_id": r["sample_index"], "raw": r["text"],
                         "finish_reason": r["finish_reason"], "parsed": map_freetext(r["task"], r["mode_X"], r["text"]),
                         "model": r["model"]})
    write_jsonl(ELICIT_DIR / "qwen_freetext.jsonl", free)
    c = Counter((f["task"], f["parsed"]) for f in free)
    logger.info(f"free-text map: {dict(c)}")
    inval = Counter((r["task"], r["valid"]) for r in ranks)
    logger.info(f"ranking validity: {dict(inval)}")


# ---------------------------------------------------------------------------------------------- external
async def _ext_calls(reqs: list[dict[str, Any]], cap_usd: float, model: str = EXT_MODEL,
                     purpose: str = "external_elicitation") -> list[dict[str, Any] | None]:
    from openai import AsyncOpenAI

    from labeller.judge import BUDGET_MSG, add_cost, purpose_spent

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=60.0, max_retries=0)
    sem = asyncio.Semaphore(8)
    stop = {"stop": False}

    async def one(rq):
        async with sem:
            if stop["stop"] or purpose_spent(purpose) >= cap_usd:
                stop["stop"] = True
                return None
            for attempt in range(4):
                if stop["stop"]:
                    return None
                try:
                    resp = await client.chat.completions.create(
                        model=model, messages=[{"role": "user", "content": rq["prompt"]}], temperature=1.0,
                        top_p=1.0, max_tokens=rq["max_tokens"], seed=rq["seed"],
                        extra_body={"usage": {"include": True}})
                    text = resp.choices[0].message.content or ""
                    u = getattr(resp, "usage", None)
                    cost = float(getattr(u, "cost", None) or ((u.model_extra or {}).get("cost", 0.0) if u else 0.0)
                                 or 0.0) if u else 0.0
                    add_cost(purpose, cost)
                    return {**{k: v for k, v in rq.items() if k != "prompt"}, "text": text, "model": model,
                            "gen_utc": utc_now()}
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    if BUDGET_MSG in msg:
                        stop["stop"] = True
                        logger.error("OpenRouter budget refusal -- stopping external elicitation")
                        return None
                    await asyncio.sleep(2 * (attempt + 1))
            return None

    out = await asyncio.gather(*[one(r) for r in reqs])
    await client.close()
    return list(out)


def stage_external(cap_usd: float = 0.5, model: str = EXT_MODEL, tag: str = "ext") -> None:
    """Association-map replication with another model family (default Llama-3.1-8B; tag 'ref' = the optional
    stronger non-reasoning 'textbook consensus' map, which is descriptive and post hoc -- never a contest predictor)."""
    purpose = "external_elicitation" if tag == "ext" else f"{tag}_elicitation"
    from analysis.assoc import map_freetext

    c = conds()
    reqs_rank, reqs_free = [], []
    for task in TASKS:
        tc = c["tasks"][task]
        for m in MODES[task]:
            for it in tc["elicit_rank"][m]:
                reqs_rank.append({"task": task, "condition": f"rank:{m}", "mode_X": m, "paraphrase_id": it["sample_id"],
                                  "option_order": it["option_order"], "prompt": it["prompt"], "max_tokens": 64,
                                  "seed": request_seed(task, f"rank:{m}", it["sample_id"],
                                                       "external" if tag == "ext" else tag)})
            for i in range(tc["elicit_free"][m]["n"]):
                reqs_free.append({"task": task, "condition": f"free:{m}", "mode_X": m, "paraphrase_id": i,
                                  "prompt": tc["elicit_free"][m]["prompt"], "max_tokens": 32,
                                  "seed": request_seed(task, f"free:{m}", i, "external" if tag == "ext" else tag)})
    outs = asyncio.run(_ext_calls(reqs_rank + reqs_free, cap_usd, model, purpose))
    rank_out = [o for o in outs[:len(reqs_rank)] if o]
    free_out = [o for o in outs[len(reqs_rank):] if o]
    prompts = {(r["task"], r["mode_X"], r["paraphrase_id"]): r["prompt"] for r in reqs_rank}

    def regen(reqs):
        rq2 = []
        for q in reqs:
            rq2.append({**q, "prompt": prompts[(q["task"], q["mode_X"], q["paraphrase_id"])],
                        "seed": request_seed(q["task"], q["condition"], q["paraphrase_id"], f"{tag}_" + q["stage"])})
        res = asyncio.run(_ext_calls(rq2, cap_usd, model, purpose))
        return [r for r in res if r]

    ranks = _rank_rows_with_retries(rank_out, regen)
    write_jsonl(ELICIT_DIR / f"{tag}_rankings.jsonl", ranks)
    free = [{"task": o["task"], "mode_X": o["mode_X"], "sample_id": o["paraphrase_id"], "raw": o["text"],
             "parsed": map_freetext(o["task"], o["mode_X"], o["text"]), "model": model} for o in free_out]
    write_jsonl(ELICIT_DIR / f"{tag}_freetext.jsonl", free)
    logger.info(f"external: {len(ranks)} rankings ({sum(r['valid'] for r in ranks)} valid), {len(free)} free-text")


# ------------------------------------------------------------------------------------------------ assoc
def labelled_rows(conditions: set[str] | None = None, task: str | None = None) -> list[dict[str, Any]]:
    rows = read_jsonl(LABELLED)
    return [r for r in rows if (conditions is None or r["condition"] in conditions) and (task is None or r["task"] == task)]


def stage_assoc() -> None:
    from analysis.assoc import assoc_object, freq_from_labels, hill

    out: dict[str, Any] = {}
    for src, fname in (("qwen", "qwen_rankings.jsonl"), ("ext", "ext_rankings.jsonl")):
        ranks = read_jsonl(ELICIT_DIR / fname)
        out[src] = {}
        for task in TASKS:
            out[src][task] = {}
            for x in MODES[task]:
                rs = [r["parsed"] for r in ranks if r["task"] == task and r["mode_X"] == x and r["valid"]]
                out[src][task][x] = assoc_object(task, x, rs) if rs else None
                if out[src][task][x] is not None:
                    out[src][task][x]["invalid_after_retries"] = sum(1 for r in ranks if r["task"] == task
                                                                      and r["mode_X"] == x and not r["valid"])
    for src, fname in (("freetext", "qwen_freetext.jsonl"), ("freetext_ext", "ext_freetext.jsonl")):
        fr = read_jsonl(ELICIT_DIR / fname)
        out[src] = {}
        for task in TASKS:
            out[src][task] = {}
            for x in MODES[task]:
                c = Counter(f["parsed"] for f in fr if f["task"] == task and f["mode_X"] == x)
                out[src][task][x] = {"counts": dict(c), "n": sum(c.values())}
    # Qwen vs external agreement
    agr = {}
    from scipy.stats import kendalltau

    for task in TASKS:
        match, taus = [], []
        for x in MODES[task]:
            q, e = out["qwen"][task][x], out["ext"][task][x]
            if q is None or e is None:
                continue
            match.append(q["borda_winner"] == e["borda_winner"])
            others = [m for m in MODES[task] if m != x]
            tau = kendalltau([q["borda_points"][y] for y in others], [e["borda_points"][y] for y in others]).statistic
            taus.append(None if tau != tau else float(tau))
        agr[task] = {"borda_winner_match_rate": sum(match) / len(match) if match else None,
                     "kendall_tau_mean": (sum(t for t in taus if t is not None) / max(1, sum(t is not None for t in taus)))
                     if taus else None, "per_x_tau": taus}
    out["qwen_vs_ext"] = agr
    write_json(ASSOC_FILE, out)
    # baseline objects
    base: dict[str, Any] = {}
    for task in TASKS:
        b = {}
        for cond in ("baseline", "baseline_empty", "baseline_T13", "listall"):
            rows = labelled_rows({cond}, task)
            code_rows = [r for r in rows if r["label"] != "no_code"]
            fr = freq_from_labels(task, [r["label"] for r in code_rows])
            fr_c = freq_from_labels(task, [r["label"] for r in code_rows if r["passed"]])
            f = fr["f"]
            modal = max(MODES[task], key=lambda m: f[m])  # first maximum in catalogue order
            b[cond] = {"freq": fr, "freq_correct": fr_c, "modal": modal,
                       "strata": {m: ("modal" if m == modal else ("present" if f[m] >= THRESHOLDS["presence"] else
                                                                  "absent")) for m in MODES[task]},
                       "hill_cc": hill([r["label"] for r in code_rows if r["passed"]]),
                       "pass_rate": sum(r["passed"] for r in code_rows) / max(1, len(code_rows)),
                       "n_rows": len(rows), "n_code": len(code_rows)}
        b["weakly_collapsed"] = b["baseline"]["hill_cc"] > 2
        base[task] = b
    write_json(BASELINE_FILE, base)
    logger.info("assoc objects + baseline objects written")
    for task in TASKS:
        for x in MODES[task]:
            q = out["qwen"][task][x]
            logger.info(f"{task} X={x}: Qwen Borda winner={q['borda_winner'] if q else None} clarity="
                        f"{q['clarity'] if q else None} | ext winner="
                        f"{out['ext'][task][x]['borda_winner'] if out['ext'][task][x] else None} | free="
                        f"{out['freetext'][task][x]['counts']}")


# ------------------------------------------------------------------------------------------------ freeze
def predictor_dists(task: str, x_last: str, S: list[str], assoc: dict[str, Any], base: dict[str, Any],
                    banned: list[str]) -> dict[str, dict[str, float]]:
    """Raw (uncomposed) predictor distributions over S for an event whose most recent ban is x_last."""
    from analysis.assoc import restricted

    q = assoc["qwen"][task][x_last]
    e = assoc["ext"][task][x_last]
    fr = assoc["freetext"][task][x_last]["counts"]
    d = {
        "assoc": restricted(q["A"], S) if q else {y: 1 / len(S) for y in S},
        "assoc_first": restricted(q["F"], S) if q else {y: 1 / len(S) for y in S},
        "assoc_ext": restricted(e["A"], S) if e else {y: 1 / len(S) for y in S},
        "freetext": restricted({y: fr.get(y, 0) for y in S}, S),
        "freq": restricted(base[task]["baseline"]["freq"]["f"], S),
        "freq_listall": restricted(base[task]["listall"]["freq"]["f"], S),
        "freq_T13": restricted(base[task]["baseline_T13"]["freq"]["f"], S),
    }
    if len(banned) > 1:
        q1 = assoc["qwen"][task][banned[0]]
        d["assoc_firstban"] = restricted(q1["A"], S) if q1 else {y: 1 / len(S) for y in S}
        pooled = {y: 0.0 for y in S}
        for b in banned:
            qb = assoc["qwen"][task][b]
            rb = restricted(qb["A"], S) if qb else {y: 1 / len(S) for y in S}
            for y in S:
                pooled[y] += rb[y] / len(banned)
        d["assoc_pooled"] = pooled
    return d


def event_prediction(task: str, banned: list[str], assoc: dict[str, Any], base: dict[str, Any],
                     event_id: str) -> dict[str, Any]:
    from analysis.assoc import compose, freq_stability, nomination, restricted_winner_and_clarity

    S = [m for m in MODES[task] if m not in banned]
    x_last = banned[-1]
    raw = predictor_dists(task, x_last, S, assoc, base, banned)
    noms = {k: nomination(v, S) for k, v in raw.items()}
    comp = {k: compose(v, S) for k, v in raw.items()}
    q = assoc["qwen"][task][x_last]
    win, clar = restricted_winner_and_clarity(q, S) if q else (None, float("nan"))
    labels = [r["label"] for r in labelled_rows({"baseline"}, task) if r["label"] != "no_code"]
    stab = freq_stability(task, labels, S, noms["freq"], seed=int(sha256_text(event_id)[:8], 16))
    fS = raw["freq"]
    srt = sorted(fS.values(), reverse=True)
    f_point = base[task]["baseline"]["freq"]["f"]
    stratum = base[task]["baseline"]["strata"][x_last] if len(banned) == 1 else "succession"
    a_top = noms["assoc"]["top"] or (noms["assoc"]["tied"][0] if noms["assoc"]["tied"] else None)
    return {
        "event_id": event_id, "task": task, "banned_in_order": banned, "x_last": x_last, "survivors": S,
        "stratum": stratum, "baseline_share_of_banned": f_point.get(x_last), "raw": raw, "composed": comp,
        "nominations": noms, "assoc_restricted_winner": win, "clarity_S": clar,
        "clarity_cc": q["clarity_cc"] if q else None, "kendall_w": q["kendall_w"] if q else None,
        "first_entropy_norm": q["first_entropy_norm"] if q else None, "ambiguous": q["ambiguous"] if q else None,
        "concordant_AF": (a_top is not None and not noms["freq"]["is_tied"] and a_top == noms["freq"]["top"]),
        "freq_tied": noms["freq"]["is_tied"], "freq_stability": stab,
        "freq_stable": bool(stab >= THRESHOLDS["stability"] and not noms["freq"]["is_tied"]),
        "freq_margin": (srt[0] - srt[1]) if len(srt) > 1 else None,
        "composition": "q(y)=0.98*(0.95 p(y)+0.05/|S|), q(other)=0.02", "frozen_utc": utc_now(),
    }


def stage_freeze() -> None:
    assoc = json.loads(ASSOC_FILE.read_text())
    base = json.loads(BASELINE_FILE.read_text())
    for task in TASKS:
        preds = {"task": task, "kind": "single_bans", "events": {}}
        for x in MODES[task]:
            preds["events"][f"ban:{x}"] = event_prediction(task, [x], assoc, base, f"{task}|ban:{x}")
        p = PRED_DIR / f"{task}_single_bans.json"
        p.write_text(json.dumps(preds, sort_keys=True, indent=1))
        commit_file(p, note=f"{task} single-ban predictions frozen before any ban/mention generation")
    logger.info("single-ban predictions frozen")


def assert_committed(path) -> dict[str, Any]:
    sha = sha256_file(path)
    rel = str(path.relative_to(ROOT))
    for e in read_commitments():
        if e["file"] == rel and e["sha"] == sha:
            return e
    raise RuntimeError(f"{rel} is not committed with its current sha -- refusing to generate")


# ------------------------------------------------------------------------------------------------ bans
def stage_bans() -> None:
    from gen.run_vllm import run_requests
    from method import program_req
    from pipeline import stage_label

    c = conds()
    for task in TASKS:
        assert_committed(PRED_DIR / f"{task}_single_bans.json")
    reqs = []
    for task in TASKS:
        tc = c["tasks"][task]["conditions"]
        for x in MODES[task]:
            for p in tc[f"ban:{x}"]:
                reqs.append(program_req(task, f"ban:{x}", p["paraphrase_id"], "bans", p["prompt"], 10))
            for p in tc[f"mention:{x}"]:
                reqs.append(program_req(task, f"mention:{x}", p["paraphrase_id"], "bans", p["prompt"], 5))
    logger.info(f"ban arms: {len(reqs)} requests, {sum(r['n'] for r in reqs)} programs")
    stats = run_requests(reqs, RAW_BANS, concurrency=24)
    write_json(DATA_DIR / "bans_gen_stats.json", stats)
    stage_label(str(RAW_BANS.relative_to(ROOT)))


REF_MODEL = "openai/gpt-4.1-mini"


def stage_reference_map() -> None:
    """Optional (plan step 6): stronger non-reasoning 'textbook consensus' association map. Collected AFTER the
    freeze, so it is reported descriptively and labelled post hoc; it never enters the frozen contest."""
    from analysis.assoc import assoc_object, restricted_winner_and_clarity

    stage_external(cap_usd=0.3, model=REF_MODEL, tag="ref")
    ranks = read_jsonl(ELICIT_DIR / "ref_rankings.jsonl")
    fr = read_jsonl(ELICIT_DIR / "ref_freetext.jsonl")
    out: dict[str, Any] = {"model": REF_MODEL, "status": "post hoc, descriptive (collected after the freeze)",
                           "maps": {}, "freetext": {}, "modal_ban_nominations": {}}
    base = json.loads(BASELINE_FILE.read_text())
    for task in TASKS:
        out["maps"][task], out["freetext"][task] = {}, {}
        for x in MODES[task]:
            rs = [r["parsed"] for r in ranks if r["task"] == task and r["mode_X"] == x and r["valid"]]
            obj = assoc_object(task, x, rs) if rs else None
            if obj:
                obj.pop("rankings", None)
            out["maps"][task][x] = obj
            out["freetext"][task][x] = dict(Counter(f["parsed"] for f in fr if f["task"] == task and f["mode_X"] == x))
        modal = base[task]["baseline"]["modal"]
        rs = [r["parsed"] for r in ranks if r["task"] == task and r["mode_X"] == modal and r["valid"]]
        if rs:
            obj = assoc_object(task, modal, rs)
            S = [m for m in MODES[task] if m != modal]
            win, clar = restricted_winner_and_clarity(obj, S)
            ftc = out["freetext"][task][modal]
            out["modal_ban_nominations"][task] = {"banned": modal, "borda_winner": win, "clarity_S": clar,
                                                  "freetext_top": max(ftc, key=ftc.get) if ftc else None}
    write_json(ELICIT_DIR / "ref_assoc_objects.json", out)
    logger.info(f"reference map: {out['modal_ban_nominations']}")


def run_analysis_stage(args) -> None:
    st = args.stage
    if st == "elicit":
        stage_elicit()
    elif st == "external":
        stage_external()
    elif st == "reference_map":
        stage_reference_map()
    elif st == "assoc":
        stage_assoc()
    elif st == "freeze":
        stage_freeze()
    elif st == "bans":
        stage_bans()
    elif st == "succession":
        from analysis.succession import stage_succession

        stage_succession()
    elif st == "score":
        from analysis.score import stage_score

        stage_score()
    elif st == "outputs":
        from analysis.outputs import stage_outputs

        stage_outputs()
    else:
        raise SystemExit(f"unknown stage {st}")
    _ = (CATALOGUE, DECODING_MAIN, OTHER)
