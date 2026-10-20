#!/usr/bin/env python3
"""Veto session (D1-D3): signature n-grams per event target, then one-shot / persistent / iterated vetoes by exact
truncate-and-redraw on the frozen pass-1 samples, labelled between rounds.

Modal events: pass-1 = the 50 B4 vetofree samples of the task (X0-family twins).
Present-minor events: pass-1 = the 100 bf16 free samples (B1 + B4); only hit samples are continued, with 2
continuations each weighted 1/2.  Iterated rounds: if A re-emerges in >= 20% of round-r (persistent) attempts, a new
n-gram g_{r+1} is computed from the re-emerged A programs and round r+1 masks {g_1..g_{r+1}}; at most 3 rounds."""

from __future__ import annotations

import collections
import re
from typing import Any

from loguru import logger

from src import label as L
from src import prompts_llama as P
from src.jobs import RAW, raw_rows
from src.ngrams import find_ngram, share_containing
from src.veto import continuation_reqs, in_code_at, plan_sample
from src.ws import (DATA, MODEL_TAG, PRED, RESULTS, append_jsonl, read_json, read_jsonl, write_json)

MAX_ROUNDS = 3
REEMERGE = 0.20


def _decision_programs(task: str, labels_by_id: dict, raw_by_id: dict, dec_ids: list[str], mode: str):
    codes, gen_ids = [], []
    for rid in dec_ids:
        lab = labels_by_id.get(rid)
        if not lab or lab["label"] != mode:
            continue
        raw = raw_by_id.get(rid)
        code, _ = L.extract(raw["text"]) if raw else (None, None)
        if code:
            codes.append(code)
            if raw.get("out_ids"):
                gen_ids.append(raw["out_ids"])
    return codes, gen_ids


def _forced_programs(task: str, labels: list[dict], raw_by_id: dict, correct_only: bool = False) -> dict[str, list[str]]:
    out: dict[str, list[str]] = collections.defaultdict(list)
    for r in labels:
        c = r.get("condition") or ""
        if r["task"] != task or not c.startswith("forced:"):
            continue
        req = c.split(":")[1]
        if r["label"] != req or (correct_only and not r.get("passed")):
            continue
        code, _ = L.extract(raw_by_id[r["row_id"]]["text"])
        if code:
            out[req].append(code)
    return out


def compute_ngram(task: str, A: str, codes: list[str], gen_ids: list[list[int]], forced: dict[str, list[str]],
                  exclude: list[list[int]] | None = None) -> dict[str, Any]:
    others = {j: forced.get(j, []) for j in P.modes(task) if j != A}
    res = find_ngram(task, A, codes, gen_ids, others, exclude=[tuple(g) for g in (exclude or [])])
    return res


def _prompt_ids_for(row: dict) -> list[int]:
    t = row["task"]
    x0 = read_json(PRED / "x0.json")["x0"]
    return P.p_twin(t, x0[t], int(row["template"]), int(row["h"]))["ids"]


def _decode(ids: list[int]) -> str:
    return P.tokenizer().decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)


def run_round(llm, events: list[dict], pass1: dict[str, list[dict]], grams: dict[str, list[list[int]]], rnd: int,
              arms_oneshot: bool) -> list[dict]:
    """One round for all events: redraws, continuations, assembled rows appended to RAW (labels copied for unchanged)."""
    from src.engine_vllm import generate

    have = {r["row_id"] for r in read_jsonl(RAW)}
    plans = []
    for ev in events:
        eid = ev["event_id"]
        phase = "D2" if ev["event_type"] == "modal" else "D3"
        n_cont = 1 if phase == "D2" else 2
        for row in pass1[eid]:
            pids = _prompt_ids_for(row)
            y = row["out_ids"]
            pl = plan_sample(task=ev["task"], tag=f"{eid}:r{rnd}", w=row["template"], sid=row["row_id"],
                             prompt_ids=pids, y=y, grams=grams[eid], n_cont=n_cont)
            plans.append((ev, phase, row, pids, pl))
    # redraws
    red = [(i, pl["redraw_req"]) for i, (_, _, _, _, pl) in enumerate(plans) if pl["hit"]]
    outs = generate(llm, [r for _, r in red]) if red else []
    tok_by = {i: o["out_ids"][0] if o["out_ids"] else None for (i, _), o in zip(red, outs)}
    # continuations
    conts = []
    for i, (ev, phase, row, pids, pl) in enumerate(plans):
        if not pl["hit"]:
            continue
        tok = tok_by.get(i)
        pl["redraw_tok"] = tok
        if tok is None:
            continue
        cr = continuation_reqs(task=ev["task"], tag=f"{ev['event_id']}:r{rnd}", w=row["template"], sid=row["row_id"],
                               prompt_ids=pids, y=row["out_ids"], t=pl["t"], tok=tok, grams=grams[ev["event_id"]],
                               n_cont=pl["n_cont"], persistent=True, oneshot=arms_oneshot)
        for c in cr:
            conts.append((i, c))
    couts = generate(llm, [c for _, c in conts]) if conts else []
    by_plan = collections.defaultdict(list)
    for (i, c), o in zip(conts, couts):
        by_plan[i].append((c, o))
    rows, copied = [], []
    lab_raw = {r["row_id"]: r for r in read_jsonl(L.LABELS_RAW)}
    arms = ["persistent"] + (["oneshot"] if arms_oneshot else [])
    for i, (ev, phase, row, pids, pl) in enumerate(plans):
        eid = ev["event_id"]
        base = {"phase": phase, "task": ev["task"], "event_id": eid, "round": rnd, "pass1_row_id": row["row_id"],
                "template": row["template"], "h": row["h"], "mode": ev["banned"], "model": MODEL_TAG,
                "grams": grams[eid], "prompt_sha256": row["prompt_sha256"]}
        if not pl["hit"]:
            if phase == "D3":
                continue  # present-minor: unchanged samples are taken from pass-1 directly (weight 1)
            for arm in arms:
                rid = f"{phase}|{ev['task']}|veto:{arm}:r{rnd}|{eid}|{row['row_id']}|u"
                if rid in have:
                    continue
                r2 = dict(base, row_id=rid, condition=f"veto:{arm}:r{rnd}", arm=arm, hit=False, t=None, c=0, weight=1.0,
                          text=row["text"], out_ids=row["out_ids"], finish_reason=row["finish_reason"],
                          n_new_tokens=row["n_new_tokens"])
                rows.append(r2)
                lr = lab_raw.get(row["row_id"])
                if lr:
                    copied.append(dict(lr, row_id=rid, phase=phase, condition=r2["condition"], copied_from=row["row_id"]))
            continue
        t = pl["t"]
        y = row["out_ids"]
        before = _decode(y[:t])
        ctxt = _decode(y[max(0, t - 12): t + 1])
        tok = pl.get("redraw_tok")
        got = by_plan.get(i, [])
        if not got:  # redraw was EOS (or no budget): the generation ends at y[:t] + [tok]
            for arm in arms:
                for c in range(pl["n_cont"]):
                    rid = f"{phase}|{ev['task']}|veto:{arm}:r{rnd}|{eid}|{row['row_id']}|{c}"
                    if rid in have:
                        continue
                    ids = list(y[:t]) + ([tok] if tok is not None else [])
                    rows.append(dict(base, row_id=rid, condition=f"veto:{arm}:r{rnd}", arm=arm, hit=True, t=t, c=c,
                                     weight=1.0 / pl["n_cont"], text=_decode(ids), out_ids=ids, finish_reason="stop",
                                     n_new_tokens=len(ids), hit_context=ctxt, hit_in_code=in_code_at(before),
                                     redraw_tok=tok, mask_tokens=pl["mask_tokens"]))
            continue
        for c, o in got:
            rid = f"{phase}|{ev['task']}|veto:{c['arm']}:r{rnd}|{eid}|{row['row_id']}|{c['c']}"
            if rid in have:
                continue
            ids = list(y[:t]) + [tok] + o["out_ids"]
            rows.append(dict(base, row_id=rid, condition=f"veto:{c['arm']}:r{rnd}", arm=c["arm"], hit=True, t=t,
                             c=c["c"], weight=1.0 / pl["n_cont"], text=_decode(ids), out_ids=ids,
                             finish_reason=o["finish_reason"], n_new_tokens=len(ids), hit_context=ctxt,
                             hit_in_code=in_code_at(before), redraw_tok=tok, mask_tokens=pl["mask_tokens"]))
    append_jsonl(RAW, rows)
    if copied:
        append_jsonl(L.LABELS_RAW, copied)
    logger.info(f"veto round {rnd}: {len(plans)} pass-1 samples, {len(red)} hits, {len(conts)} continuations, "
                f"{len(rows)} rows ({len(copied)} labels copied)")
    return rows


def _labelled(rows_filter) -> list[dict]:
    L.label_rows([r for r in raw_rows({"D2", "D3"})], workers=5)
    raw_by_id = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
    labs = L.combine(raw_by_id)
    return [r for r in labs if rows_filter(r)]


def surfaces(rows: list[dict], A: str, grams: list[list[int]]) -> dict[str, Any]:
    imp = collections.Counter()
    same_surface = 0
    dec = [P.tokenizer().decode(g) for g in grams]
    for r in rows:
        code, _ = L.extract(r["text"])
        if not code:
            continue
        for line in code.splitlines():
            s = line.strip()
            if re.match(r"^(from\s+\S+\s+import|import\s+)", s):
                imp[s] += 1
        if any(d.strip() and d.strip() in code for d in dec):
            same_surface += 1
    return {"n_reemerged": len(rows), "top_imports": imp.most_common(6), "vetoed_text_present_via_other_tokens":
            same_surface, "vetoed_decoded": dec}


def run(llm, args) -> dict[str, Any]:
    evs = read_json(PRED / "events.json")
    events = evs["events"]
    dec_meta = read_json(RESULTS / "decision_sets.json")
    raw_all = L.pilot_rows() + raw_rows()
    raw_by_id = {r["row_id"]: r for r in raw_all}
    labels = read_jsonl(L.LABELS)
    labels_by_id = {r["row_id"]: r for r in labels}
    summary: dict[str, Any] = {}
    grams: dict[str, list[list[int]]] = {}
    pass1: dict[str, list[dict]] = {}
    for ev in events:
        t, A, eid = ev["task"], ev["banned"], ev["event_id"]
        dec_ids = dec_meta[t]["decision_row_ids"]
        codes, gen_ids = _decision_programs(t, labels_by_id, raw_by_id, dec_ids, A)
        forced = _forced_programs(t, labels, raw_by_id)
        pooled_forced = False
        if len(codes) < 10:
            fc = _forced_programs(t, labels, raw_by_id, correct_only=True).get(A, [])
            codes = codes + fc
            pooled_forced = True
        ng = compute_ngram(t, A, codes, gen_ids, forced)
        ent = {"event_id": eid, "task": t, "A": A, "event_type": ev["event_type"], "n_ref": len(codes),
               "n_gen": len(gen_ids), "pooled_forced": pooled_forced, "rounds": [], "ngrams": [ng]}
        if ev["event_type"] == "present_minor" and ng.get("defined"):
            dcodes, _ = _decision_programs(t, labels_by_id, raw_by_id, dec_ids, ev["D"])
            sh = share_containing(ng["ids"], dcodes)
            ent["share_in_D_programs"] = sh
            ent["veto_removes_D_too"] = bool(sh is not None and sh >= 0.5)
        summary[eid] = ent
        if not ng.get("defined"):
            ent["undefined_reason"] = ng.get("reason")
            continue
        grams[eid] = [ng["ids"]]
        if ev["event_type"] == "modal":
            p1 = [raw_by_id[r] for r in raw_by_id if raw_by_id[r].get("phase") == "B4" and raw_by_id[r]["task"] == t]
        else:
            p1 = [raw_by_id[r] for r in raw_by_id if raw_by_id[r].get("phase") in ("B1", "B4") and raw_by_id[r]["task"] == t]
        pass1[eid] = sorted(p1, key=lambda r: r["row_id"])
        logger.info(f"n-gram {eid}: {ng['decoded']!r} n={ng['n']} presence={ng['presence']:.2f} "
                    f"gen={ng['gen_presence']} max_collateral={ng['max_collateral']:.2f} co-veto={ng['co_vetoed']}")
    write_json(PRED / "ngrams_round1.json", summary)
    active = [ev for ev in events if ev["event_id"] in grams]
    # T3 GPU checks (must pass before any veto job)
    import sys as _sys
    _sys.path.insert(0, str(PRED.parent / "tests"))
    import test_veto as TV
    syn = TV.synthetic()
    ev0 = active[0]
    x0 = read_json(PRED / "x0.json")["x0"]
    pids = P.p_twin(ev0["task"], x0[ev0["task"]], 1, 0)["ids"]
    gc = TV.gpu_checks(llm, pids, grams[ev0["event_id"]][0])
    write_json(RESULTS / "tests_veto.json", {"synthetic": syn, "gpu": gc})
    logger.info(f"T3 veto tests: synthetic {syn['passed']} gpu {gc}")
    assert syn["passed"] and gc["passed"], "T3 veto tests failed"
    for rnd in range(1, MAX_ROUNDS + 1):
        if not active:
            break
        run_round(llm, active, pass1, grams, rnd, arms_oneshot=(rnd == 1))
        labs = _labelled(lambda r: r.get("phase") in ("D2", "D3"))
        lab_by = {r["row_id"]: r for r in labs}
        raw_now = {r["row_id"]: r for r in raw_rows({"D2", "D3"})}
        nxt = []
        for ev in active:
            eid, A, t = ev["event_id"], ev["banned"], ev["task"]
            rr = [r for r in raw_now.values() if r["event_id"] == eid and r["round"] == rnd and r["arm"] == "persistent"]
            labs_r = [(lab_by.get(r["row_id"], {}).get("label"), r) for r in rr]
            if ev["event_type"] == "present_minor":  # add unchanged pass-1 samples (weight 1)
                hit_ids = {r["pass1_row_id"] for r in rr}
                for p in pass1[eid]:
                    if p["row_id"] not in hit_ids:
                        labs_r.append((labels_by_id.get(p["row_id"], {}).get("label"), dict(p, weight=1.0, hit=False)))
            att = [(l, r) for l, r in labs_r if l not in (None, "invalid", "unresolved")]
            wA = sum(r.get("weight", 1.0) for l, r in att if l == A)
            wT = sum(r.get("weight", 1.0) for l, r in att)
            share = wA / wT if wT else float("nan")
            hits = sum(1 for r in rr if r.get("hit"))
            reem = [r for l, r in att if l == A and r.get("hit")]
            rec = {"round": rnd, "n_rows": len(rr), "n_hit_rows": hits, "A_share_weighted": share,
                   "n_attempts_w": wT, "grams": grams[eid],
                   "decoded": [P.tokenizer().decode(g) for g in grams[eid]],
                   "surfaces": surfaces([r for l, r in att if l == A], A, grams[eid]),
                   "hit_in_code_share": (sum(1 for r in rr if r.get("hit") and r.get("hit_in_code")) / max(hits, 1)),
                   "hit_contexts": [r.get("hit_context") for r in rr if r.get("hit")][:8]}
            summary[eid]["rounds"].append(rec)
            logger.info(f"{eid} r{rnd}: A share {share:.2f} over {wT:.1f} attempts ({hits} hit rows)")
            if share >= REEMERGE and rnd < MAX_ROUNDS:
                codes = []
                gen_ids = []
                for l, r in att:
                    if l == A and r.get("hit"):
                        code, _ = L.extract(r["text"])
                        if code:
                            codes.append(code)
                            gen_ids.append(r["out_ids"])
                if not codes:
                    codes = [L.extract(r["text"])[0] for l, r in att if l == A]
                    codes = [c for c in codes if c]
                    gen_ids = [r["out_ids"] for l, r in att if l == A]
                forced = _forced_programs(t, labs + read_jsonl(L.LABELS), raw_by_id)
                ng = compute_ngram(t, A, codes, gen_ids, forced, exclude=grams[eid])
                summary[eid]["ngrams"].append(ng)
                if ng.get("defined"):
                    grams[eid] = grams[eid] + [ng["ids"]]
                    nxt.append(ev)
                    logger.info(f"{eid}: next n-gram {ng['decoded']!r} (max collateral {ng['max_collateral']:.2f})")
                else:
                    summary[eid]["stopped"] = f"no further n-gram after round {rnd}"
            elif share >= REEMERGE and rnd == MAX_ROUNDS:
                summary[eid]["not_carried_by_surface_tokens"] = True
        active = nxt
    write_json(DATA / "veto_summary.json", summary)
    ph = TV.posthoc(raw_rows({"D2", "D3"}), P.tokenizer())
    tv = read_json(RESULTS / "tests_veto.json")
    tv["posthoc"] = ph
    write_json(RESULTS / "tests_veto.json", tv)
    logger.info(f"T3 post-hoc: {ph}")
    return summary
