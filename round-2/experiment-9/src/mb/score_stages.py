#!/usr/bin/env python3
"""HF scoring stages.

score1a (S5): (1) every FRLP program under one baseline paraphrase (round-robin) -> l_base and 'base' states;
(2) denominators: every program under all 10 F_j paraphrases -> l_F = logmeanexp, 'forced' states under the generating
paraphrase; (3) session-1 natural programs: 'own' states (raw generated ids under their own prompt) and 'base' states
(scrubbed block under a round-robin baseline paraphrase). Scoring self-checks T3 (a)-(d) run first.
score1b (S7): FRLP cells of the planned conditions (multi-bans: ban / mention / neutral; nonce; T2 LOS; tier 3).
score2 (S9): 'own' and 'base' states of the session-2 programs.
"""

from __future__ import annotations

import collections
import gc
import json
import math
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from common import (DATA_DIR, MODEL_ID, MODES, RESULTS_DIR, logmeanexp, read_json, read_jsonl, timing, utc_now,
                    write_json)
from mb.score import (FRLP_CELLS, Scorer, StateWriter, evidence_char, frlp, load_scores, program_items, run_cell,
                      token_index_at)

DENOM = DATA_DIR / "denominators.json"


def load_psets() -> dict[str, dict[str, Any]]:
    return read_json(DATA_DIR / "program_sets.json")


def frozen() -> dict[str, Any]:
    from mb.prompts import load_frozen

    return load_frozen()


def forced_prompts(fz: dict[str, Any], task: str, key: str) -> list[str]:
    var = read_json(DATA_DIR / "variant_decisions.json")["algorithms"][f"{task}:{key}"]["variant"]
    cname = f"forced_desc:{key}" if var == "desc" else f"forced:{key}"
    return [it["prompt"] for it in fz["tasks"][task]["conditions"][cname]]


def write_cells(rows: list[dict[str, Any]]) -> None:
    with FRLP_CELLS.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def cell_row(task: str, condition: str, template: str, alg: str, half: str, l_c: dict[str, float],
             l_F: dict[str, float], uids: list[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    L, ess = frlp([l_c[u] for u in uids], [l_F[u] for u in uids])
    row = {"task": task, "model": MODEL_ID, "condition": condition, "template": template, "algorithm": alg, "L": L,
           "ess": ess, "n_programs": len(uids), "half": half, "ess_flag": ess < 5.0, "utc": utc_now()}
    if extra:
        row.update(extra)
    return row


# ------------------------------------------------------------------------------------------------ self-checks (T3)
@torch.no_grad()
def selftest(sc: Scorer, progs: list[dict[str, Any]], prompt: str, raw_rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    items = program_items(sc, progs[:5], with_pos=False)
    res = sc.score(prompt, items)
    pids = sc.chat_ids(prompt)
    diffs, signed = [], []
    for it in items:
        ids = torch.tensor([pids + it["resp_ids"]], device="cuda")
        logits = sc.head(sc.model.model(input_ids=ids).last_hidden_state)[0]
        lp = torch.log_softmax(logits[len(pids) - 1:-1], dim=-1)
        tgt = ids[0, len(pids):]
        full = float(lp.gather(-1, tgt[:, None]).sum())
        diffs.append(abs(full - res["l"][it["uid"]]))
        signed.append(res["l"][it["uid"]] - full)
        del logits, lp
    out["a_prefix_cache_vs_full_max_abs_diff"] = max(diffs)
    out["a_ok"] = max(diffs) <= 0.05
    # (b) teacher-forcing reproduction: separate tokenisation of raw natural responses vs generated ids
    eq = []
    for r in raw_rows[:3]:
        ids, _ = sc.resp_tok(r["text"])
        gen = r.get("token_ids") or []
        if gen and gen[-1] in (sc.tok.eos_token_id, sc.tok.convert_tokens_to_ids("<|im_end|>")):
            gen = gen[:-1]
        eq.append(ids == gen)
    out["b_retokenisation_equals_generated"] = eq
    # (c) hook output at layer l equals output_hidden_states[l+1]
    it = items[0]
    ids = torch.tensor([pids + it["resp_ids"]], device="cuda")
    sc.capture = True
    sc._buf = {}
    o = sc.model(input_ids=ids, output_hidden_states=True)
    sc.capture = False
    md = max(float((sc._buf[l][0].float() - o.hidden_states[l + 1][0].float()).abs().max()) for l in sc.layers
             if l + 1 < len(o.hidden_states) - 1)
    out["c_hook_vs_hidden_states_max_abs"] = md
    out["c_ok"] = md < 1e-3
    sc._buf = {}
    # (d) chunked log-softmax sum equals unchunked on one short program
    short = min(items, key=lambda x: len(x["resp_ids"]))
    ids = torch.tensor([pids + short["resp_ids"]], device="cuda")
    # same single full pass, scored once with one log_softmax over all positions and once in 128-token chunks
    hid = sc.model.model(input_ids=ids).last_hidden_state
    logits = sc.head(hid)[0]
    lp = torch.log_softmax(logits[len(pids) - 1:-1], dim=-1)
    full = float(lp.gather(-1, ids[0, len(pids):, None]).sum())
    tgt = ids[0, len(pids):]
    chunked = 0.0
    for a in range(0, len(tgt), 128):
        lg = logits[len(pids) - 1 + a:len(pids) - 1 + min(len(tgt), a + 128)]
        chunked += float((lg.gather(-1, tgt[a:a + 128, None]).squeeze(-1) - torch.logsumexp(lg, -1)).sum())
    out["d_chunked_vs_unchunked_abs_diff"] = abs(full - chunked)
    out["d_cached_vs_full_abs_diff"] = abs(full - res["l"][short["uid"]])
    out["d_ok"] = out["d_chunked_vs_unchunked_abs_diff"] <= 0.05
    out["a_signed_diffs"] = signed
    del o, logits, lp
    torch.cuda.empty_cache()
    logger.info(f"scoring self-checks: {out}")
    return out


# ------------------------------------------------------------------------------------------------ natural programs
def natural_rows(src: str) -> list[dict[str, Any]]:
    """Labelled natural rows joined with their raw prompt and generated ids."""
    raw = {(r["req_id"], r["sample_index"]): r for r in read_jsonl(DATA_DIR / f"raw_{src}.jsonl")}
    out = []
    for r in read_jsonl(DATA_DIR / f"labelled_{src}.jsonl"):
        rr = raw.get((r["req_id"], r["sample_index"]))
        if rr is None or not r.get("code"):
            continue
        r = dict(r)
        r["prompt"] = rr["prompt"]
        r["token_ids"] = rr.get("token_ids")
        r["uid"] = f"{r['task']}|{r['condition']}|{r['template']}|{r['paraphrase_id']}|{r['sample_index']}|{r['stage']}"
        out.append(r)
    return out


def _offsets_for_ids(sc: Scorer, ids: list[int]) -> list[tuple[int, int]]:
    offs, prev = [], 0
    for i in range(len(ids)):
        cur = len(sc.tok.decode(ids[:i + 1]))
        offs.append((prev, cur))
        prev = cur
    return offs


def natural_states(sc: Scorer, rows: list[dict[str, Any]], task: str, tag: str) -> dict[str, Any]:
    """'own' context (raw generated ids under the own prompt) and 'base' context (scrubbed block under a round-robin
    baseline paraphrase) for natural programs of one task."""
    from mb.scrub import scored_response, scrub_code

    fz = frozen()
    base_prompts = [it["prompt"] for it in fz["tasks"][task]["conditions"]["baseline"]]
    stats = {"n": len(rows), "retok_equal": 0, "pre_fallback_own": 0, "pre_fallback_base": 0, "scrub_failed": 0}
    w_own, w_base = StateWriter(task, "own"), StateWriter(task, "base")
    # own context, grouped by prompt
    by_prompt: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_prompt[r["prompt"]].append(r)
    for prompt, grp in by_prompt.items():
        items = []
        for r in grp:
            text = r["text"]
            ids, offs = sc.resp_tok(text)
            gen = list(r.get("token_ids") or [])
            while gen and gen[-1] in (sc.tok.eos_token_id, sc.tok.convert_tokens_to_ids("<|im_end|>")):
                gen = gen[:-1]
            if gen and gen != ids:
                ids, offs = gen, _offsets_for_ids(sc, gen)
            else:
                stats["retok_equal"] += 1
            cs = text.find(r["code"].strip().split("\n")[0]) if r.get("code") else 0
            ch = evidence_char(text, max(cs, 0), r["code"], r["label"])
            ti = token_index_at(offs, ch) if ch is not None else None
            pre = ti - 1 if ti is not None and ti >= 1 else None
            stats["pre_fallback_own"] += int(pre is None)
            items.append({"uid": r["uid"], "resp_ids": ids, "row": r,
                          "state_pos": {"g8": 8, "g16": 16, "g32": 32, "pre": pre if pre is not None else 16},
                          "pre_fallback": pre is None})
        res = sc.score(prompt, items, want_states=True)
        pk = f"own|{grp[0]['uid']}"
        w_own.add_R(pk, res["R"])
        for it in items:
            r = it["row"]
            w_own.add(it["uid"], res["states"][it["uid"]], {
                "uid": it["uid"], "task": task, "condition": r["condition"], "template": r["template"],
                "label": r["label"], "context": "own", "kind": "natural", "prompt_key": pk,
                "pre_fallback": it["pre_fallback"], "n_tokens": len(it["resp_ids"]), "source": tag,
                "l_own": res["l"][it["uid"]]})
    w_own.flush()
    # base context: scrubbed block under a round-robin baseline paraphrase
    groups: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for i, r in enumerate(sorted(rows, key=lambda x: x["uid"])):
        groups[i % 10].append(r)
    for p, grp in groups.items():
        items = []
        for r in grp:
            try:
                code, _ = scrub_code(r["code"])
            except Exception:  # noqa: BLE001 - unparsable programs keep their raw code (flagged)
                code = r["code"]
                stats["scrub_failed"] += 1
            resp = scored_response(r["text"], code)
            ids, offs = sc.resp_tok(resp)
            fl = len(resp.split("\n", 1)[0]) + 1
            ch = evidence_char(resp, fl, code, r["label"])
            ti = token_index_at(offs, ch) if ch is not None else None
            pre = ti - 1 if ti is not None and ti >= 1 else None
            stats["pre_fallback_base"] += int(pre is None)
            items.append({"uid": r["uid"], "resp_ids": ids, "row": r,
                          "state_pos": {"g8": 8, "g16": 16, "g32": 32, "pre": pre if pre is not None else 16},
                          "pre_fallback": pre is None})
        res = sc.score(base_prompts[p], items, want_states=True)
        pk = f"{task}|baseline|{p}"
        w_base.add_R(pk, res["R"])
        for it in items:
            r = it["row"]
            w_base.add(it["uid"], res["states"][it["uid"]], {
                "uid": it["uid"], "task": task, "condition": r["condition"], "template": r["template"],
                "label": r["label"], "context": "base", "kind": "natural", "prompt_key": pk,
                "pre_fallback": it["pre_fallback"], "n_tokens": len(it["resp_ids"]), "source": tag})
    w_base.flush()
    return stats


# ------------------------------------------------------------------------------------------------ stage 1a
def stage_score1a(limit: int | None = None) -> None:
    t_all = time.time()
    psets = load_psets()
    fz = frozen()
    sc = Scorer()
    done = load_scores()
    chk_prog = psets.get("t1:bfs", next(iter(psets.values())))["programs"]
    raw_nat = read_jsonl(DATA_DIR / "raw_session1.jsonl")[:3]
    checks = selftest(sc, chk_prog, fz["tasks"]["t1"]["conditions"]["baseline"][0]["prompt"], raw_nat)
    write_json(RESULTS_DIR / "scoring_checks.json", checks)
    denom: dict[str, Any] = read_json(DENOM) if DENOM.exists() else {}
    for task in MODES:
        progs = [p for k, v in psets.items() if k.startswith(task + ":") for p in v["programs"]]
        if limit:
            per = collections.defaultdict(list)
            for p in progs:
                per[p["algorithm"]].append(p)
            progs = [p for v in per.values() for p in v[:max(1, limit // max(len(per), 1))]]
        items = {it["uid"]: it for it in program_items(sc, progs, with_pos=True)}
        meta_of = {p["uid"]: p for p in progs}
        base_prompts = [it["prompt"] for it in fz["tasks"][task]["conditions"]["baseline"]]
        # (1) baseline, round-robin over the 10 paraphrases, with 'base' states
        t0 = time.time()
        wb = StateWriter(task, "base")
        groups = collections.defaultdict(list)
        for p in progs:
            groups[p["m_index"] % 10].append(p)
        l_base: dict[str, float] = {}
        for pi, grp in sorted(groups.items()):
            pk = f"{task}|baseline|{pi}"
            res = sc.score(base_prompts[pi], [items[p["uid"]] for p in grp], want_states=True)
            wb.add_R(pk, res["R"])
            from mb.score import append_scores

            append_scores([{"prompt_key": pk, "uid": u, "l": l, "utc": utc_now()} for u, l in res["l"].items()])
            for p in grp:
                l_base[p["uid"]] = res["l"][p["uid"]]
                wb.add(p["uid"], res["states"][p["uid"]], {
                    "uid": p["uid"], "task": task, "algorithm": p["algorithm"], "label": p["algorithm"],
                    "context": "base", "kind": "forced", "prompt_key": pk, "half": p["half"],
                    "pre_fallback": items[p["uid"]]["pre_fallback"], "n_tokens": items[p["uid"]]["n_tokens"],
                    "paraphrase_id": p["paraphrase_id"], "passed": p["passed"]})
        wb.flush()
        timing(f"score:baseline:{task}", time.time() - t0, len(progs))
        # (2) denominators under all 10 F_j paraphrases, 'forced' states under the generating paraphrase
        t0 = time.time()
        wf = StateWriter(task, "forced")
        for alg in sorted({p["algorithm"] for p in progs}):
            ap = [p for p in progs if p["algorithm"] == alg]
            fps = forced_prompts(fz, task, alg)
            lk: dict[str, list[float]] = collections.defaultdict(list)
            for k, fp in enumerate(fps):
                pk = f"{task}|forced:{alg}|{k}"
                res = sc.score(fp, [items[p["uid"]] for p in ap], want_states=True)
                from mb.score import append_scores

                append_scores([{"prompt_key": pk, "uid": u, "l": l, "utc": utc_now()} for u, l in res["l"].items()])
                wf.add_R(pk, res["R"])
                for p in ap:
                    lk[p["uid"]].append(res["l"][p["uid"]])
                    if p["paraphrase_id"] == k:
                        wf.add(p["uid"], res["states"][p["uid"]], {
                            "uid": p["uid"], "task": task, "algorithm": alg, "label": alg, "context": "forced",
                            "kind": "forced", "prompt_key": pk, "half": p["half"],
                            "pre_fallback": items[p["uid"]]["pre_fallback"], "n_tokens": items[p["uid"]]["n_tokens"]})
            for p in ap:
                denom[p["uid"]] = {"l_F": logmeanexp(lk[p["uid"]]), "l_k": lk[p["uid"]],
                                   "l_gen": lk[p["uid"]][p["paraphrase_id"]], "algorithm": alg, "task": task,
                                   "half": p["half"], "l_base": l_base[p["uid"]]}
            logger.info(f"denominators {task}:{alg}: {len(ap)} programs x {len(fps)} paraphrases")
        wf.flush()
        timing(f"score:denominators:{task}", time.time() - t0, len(progs) * 10)
        write_json(DENOM, denom)
        # FRLP base cells
        rows = []
        for alg in sorted({p["algorithm"] for p in progs}):
            ap = [p["uid"] for p in progs if p["algorithm"] == alg]
            lF = {u: denom[u]["l_F"] for u in ap}
            lg = {u: denom[u]["l_gen"] for u in ap}
            for half, us in (("all", ap), ("h1", [u for u in ap if meta_of[u]["half"] == 1]),
                             ("h2", [u for u in ap if meta_of[u]["half"] == 2])):
                if us:
                    rows.append(cell_row(task, "base", "B-rr", alg, half, l_base, lF, us))
            # sensitivity: generating-paraphrase proposal; correct-only programs
            rows.append(cell_row(task, "base", "B-rr", alg, "all", l_base, lg, ap, {"variant": "generating_proposal"}))
            co = [u for u in ap if meta_of[u]["passed"]]
            if co:
                rows.append(cell_row(task, "base", "B-rr", alg, "all", l_base, lF, co, {"variant": "correct_only"}))
        write_cells(rows)
        tot = sum(math.exp(r["L"]) for r in rows if r["half"] == "all" and "variant" not in r)
        logger.info(f"{task}: sum_j exp(L_j(base)) = {tot:.3f}; " +
                    ", ".join(f"{r['algorithm']}={r['L']:.2f}(ess {r['ess']:.1f})" for r in rows
                              if r["half"] == "all" and "variant" not in r))
    # (3) natural session-1 states
    t0 = time.time()
    nat = natural_rows("session1")
    if limit:
        nat = nat[:limit]
    nstats = {}
    for task in MODES:
        nstats[task] = natural_states(sc, [r for r in nat if r["task"] == task], task, "session1")
    write_json(RESULTS_DIR / "natural_state_stats_session1.json", nstats)
    timing("score:natural_states:session1", time.time() - t0, 2 * len(nat))
    logger.info(f"score1a done in {time.time() - t_all:.0f}s")


# ------------------------------------------------------------------------------------------------ stage 1b
def stage_score1b(limit: int | None = None) -> None:
    t_all = time.time()
    psets = load_psets()
    fz = frozen()
    plan = read_json(RESULTS_DIR / "planned_conditions.json")
    denom = read_json(DENOM)
    sc = Scorer()
    done = load_scores()
    l_F = {u: d["l_F"] for u, d in denom.items()}
    by_alg = {k: v["programs"] for k, v in psets.items()}
    items: dict[str, dict[str, Any]] = {}
    for k, v in by_alg.items():
        for it in program_items(sc, v, with_pos=False):
            items[it["uid"]] = it
    rows: list[dict[str, Any]] = []
    n_pass = 0
    t0 = time.time()

    def progs_of(task: str, alg: str, half: str) -> list[dict[str, Any]]:
        ps = by_alg.get(f"{task}:{alg}", [])
        return [p for p in ps if half == "all" or p["half"] == int(half[1])]

    def score_and_cells(task: str, cond: str, tpl: str, prompt: str, plist: list[tuple[str, str]], kind: str,
                        extra: dict[str, Any] | None = None) -> None:
        """plist: (alg, half) pairs to score under this prompt; writes one cell per (alg, half)."""
        nonlocal n_pass
        progs = [p for a, h in plist for p in progs_of(task, a, h)]
        if not progs:
            return
        pk = f"{task}|{cond}|{tpl}|{kind}"
        lc = run_cell(sc, done, pk, prompt, progs, items)
        n_pass += len(progs)
        for a, h in plist:
            us = [p["uid"] for p in progs_of(task, a, h)]
            if us:
                rows.append(cell_row(task, cond, tpl, a, h, lc, l_F, us, {"twin": kind, **(extra or {})}))

    # multi-bans (T1)
    for set_name, cond in plan["t1"].items():
        surv, banned = cond["survivors"], cond["banned"]
        for it in cond["templates"]:
            w = it["template"]
            tr1, tr2 = it["halves"]["1"], it["halves"]["2"]
            cname = f"multi:{set_name}"
            pos = {a: i for i, a in enumerate([k for nm in it["names"] for k, v in fz["catalogue"]["t1"].items()
                                               if v == nm])}
            score_and_cells("t1", cname, w, tr1["prompts"]["ban"],
                            [(a, "h1") for a in surv + banned] + [(a, "h2") for a in surv], "ban",
                            {"list_position": None})
            score_and_cells("t1", cname, w, tr1["prompts"]["neutral"], [(a, "h1") for a in surv + banned], "neutral")
            score_and_cells("t1", cname, w, tr2["prompts"]["neutral"], [(a, "h2") for a in surv], "neutral")
            score_and_cells("t1", cname, w, tr1["prompts"]["mention"], [(a, "h1") for a in surv], "mention")
            for r in rows:
                if r["condition"] == cname and r["template"] == w and r["algorithm"] in pos:
                    r["list_position"] = pos[r["algorithm"]]
        logger.info(f"multi-ban {set_name}: cells so far {len(rows)}, passes {n_pass}, "
                    f"{(time.time() - t0) / max(n_pass, 1):.3f} s/pass")
        timing("score:multiban", time.time() - t0, n_pass)
        write_cells(rows)
        rows = []
    # nonce (T1): ban + its neutral twin on every algorithm's h1 programs
    t1_algs = sorted({p["algorithm"] for k, v in by_alg.items() if k.startswith("t1:") for p in v})
    for it in fz["tasks"]["t1"]["conditions"]["nonce"]:
        w = it["template"]
        score_and_cells("t1", "nonce", w, it["halves"]["1"]["prompts"]["ban"], [(a, "h1") for a in t1_algs], "ban")
        score_and_cells("t1", "nonce", w, it["halves"]["1"]["prompts"]["neutral"], [(a, "h1") for a in t1_algs],
                        "neutral")
    write_cells(rows)
    rows = []
    logger.info(f"nonce done; passes {n_pass}")
    # T2 LOS
    t2_algs = sorted({p["algorithm"] for k, v in by_alg.items() if k.startswith("t2:") for p in v})
    for s in MODES["t2"]:
        cname = f"los:{s}"
        for it in fz["tasks"]["t2"]["conditions"][cname]:
            w = it["template"]
            tr1, tr2 = it["halves"]["1"], it["halves"]["2"]
            banned = [a for a in it["banned"] if a in t2_algs]
            surv_list = [s] if s in t2_algs else []
            ban_pl = [(a, "h1") for a in surv_list] + [(a, "h2") for a in surv_list]
            neu1 = [(a, "h1") for a in surv_list]
            if w in ("W1", "W2"):
                ban_pl += [(a, "h1") for a in banned]
                neu1 += [(a, "h1") for a in banned]
            score_and_cells("t2", cname, w, tr1["prompts"]["ban"], ban_pl, "ban")
            score_and_cells("t2", cname, w, tr1["prompts"]["neutral"], neu1, "neutral")
            score_and_cells("t2", cname, w, tr2["prompts"]["neutral"], [(a, "h2") for a in surv_list], "neutral")
    write_cells(rows)
    rows = []
    logger.info(f"LOS done; passes {n_pass}")
    # tier 3: single modal bans
    for task, key, algs in (("t1", "bfs", t1_algs), ("t2", "dijkstra", t2_algs)):
        for it in fz["tasks"][task]["conditions"][f"single:{key}"]:
            w = it["template"]
            score_and_cells(task, f"single:{key}", w, it["halves"]["1"]["prompts"]["ban"], [(a, "h1") for a in algs],
                            "ban")
            score_and_cells(task, f"single:{key}", w, it["halves"]["1"]["prompts"]["neutral"],
                            [(a, "h1") for a in algs], "neutral")
            score_and_cells(task, f"single:{key}", w, it["halves"]["1"]["prompts"]["mention"],
                            [(a, "h1") for a in algs], "mention")
    write_cells(rows)
    timing("score:stage1b_total", time.time() - t0, n_pass)
    logger.info(f"score1b done: {n_pass} program-passes in {time.time() - t_all:.0f}s")


# ------------------------------------------------------------------------------------------------ stage 2
def stage_score2(limit: int | None = None) -> None:
    sc = Scorer()
    nat = natural_rows("session2")
    if limit:
        nat = nat[:limit]
    stats = natural_states(sc, nat, "t1", "session2")
    write_json(RESULTS_DIR / "natural_state_stats_session2.json", stats)
    logger.info(f"score2 done: {stats}")
    placebo(sc)


def placebo(sc: Scorer) -> None:
    """T4 placebo (run after session 2; it feeds no forecast): survivors' half-1 programs under the noun-B neutral twin
    versus the noun-A twin they were scored under at S7; |mean| should be below the template SD."""
    psets = load_psets()
    plan = read_json(RESULTS_DIR / "planned_conditions.json")
    denom = read_json(DENOM)
    l_F = {u: d["l_F"] for u, d in denom.items()}
    done = load_scores()
    by_alg = {k: v["programs"] for k, v in psets.items()}
    items = {}
    for v in by_alg.values():
        for it in program_items(sc, v, with_pos=False):
            items[it["uid"]] = it
    rows, out = [], {}
    for set_name, cond in plan["t1"].items():
        for it in cond["templates"]:
            w = it["template"]
            progs = [p for a in cond["survivors"] for p in by_alg.get(f"t1:{a}", []) if p["half"] == 1]
            pk = f"t1|multi:{set_name}|{w}|neutralB_on_h1"
            lc = run_cell(sc, done, pk, it["halves"]["2"]["prompts"]["neutral"], progs, items)
            for a in cond["survivors"]:
                us = [p["uid"] for p in progs if p["algorithm"] == a]
                if us:
                    rows.append(cell_row("t1", f"multi:{set_name}", w, a, "h1", lc, l_F, us, {"twin": "neutralB_on_h1"}))
    write_cells(rows)
    cells = [r for r in read_jsonl(FRLP_CELLS) if "variant" not in r]
    idx = {(r["condition"], r["template"], r.get("twin"), r["algorithm"], r["half"]): r for r in cells}
    for r in rows:
        a_cell = idx.get((r["condition"], r["template"], "neutral", r["algorithm"], "h1"))
        if a_cell is None:
            continue
        out.setdefault(f"{r['condition']}|{r['algorithm']}", []).append(r["L"] - a_cell["L"])
    summ = {k: {"placebo_gains": v, "mean": float(np.mean(v)), "template_sd": float(np.std(v, ddof=1)) if len(v) > 1
                else None, "pass": bool(len(v) > 1 and abs(np.mean(v)) < np.std(v, ddof=1))} for k, v in out.items()}
    write_json(RESULTS_DIR / "placebo.json", {"cells": summ, "n_pass": sum(s["pass"] for s in summ.values()),
                                              "n": len(summ), "note": "noun B vs noun A neutral twins on the same "
                                                                      "half-1 programs; run after session 2"})
    logger.info(f"placebo: {sum(s['pass'] for s in summ.values())}/{len(summ)} cells with |mean| < template SD")


__all__ = ["stage_score1a", "stage_score1b", "stage_score2", "gc", "np"]
