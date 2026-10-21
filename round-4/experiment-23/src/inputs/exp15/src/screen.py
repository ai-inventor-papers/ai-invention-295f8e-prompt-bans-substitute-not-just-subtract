#!/usr/bin/env python3
"""Path-task SCREEN (B6 / D4 / H6): descriptive, never pooled.

The same ban-free forecast families are scored against exp10's existing Llama ban landings on its two path tasks
(T1 grid path: ban BFS; T2 weighted shortest path: ban Dijkstra).  Prompts are exp10's own builders (src/config.py,
copied with its workspace paths patched; neutral twins with filler ' -'), labels come from the exp10 canonical labeller
(run from a writable copy, screen10/canon/), n-grams from exp10's Llama baseline programs against exp10's forced set,
ASSOCIATE from exp10's free answers, PROXIMITY from exp10's forced set.  Forecasts are hash-chained before scoring
(the landings themselves were sampled in iteration 2, so this is a screen, not a confirmation)."""

from __future__ import annotations

import collections
import json
import os
import shutil
import stat
import sys
from typing import Any

from loguru import logger

from src.ws import DATA, EXP10, PRED, RESULTS, WS, append_jsonl, read_json, read_jsonl, request_seed, write_json

SCREEN_DIR = WS / "screen10"
CANON_RW = SCREEN_DIR / "canon"
RAW = DATA / "screen_raw.jsonl"
LAB = DATA / "screen_labels.jsonl"
EVENTS = {"t1": "bfs", "t2": "dijkstra"}
WS_PY = '''"""exp10 workspace bridge, patched: canon from the writable copy screen10/canon, exp10 data/results read-only."""
import sys
from pathlib import Path

WS10 = Path(__file__).resolve().parent.parent / "inputs" / "exp10"
CANON = Path(__file__).resolve().parent / "canon"
DATA = WS10 / "data"
RESULTS = WS10 / "results"
if str(CANON) not in sys.path:
    sys.path.insert(0, str(CANON))
import common as C  # noqa: E402,F401


def model_path() -> str:
    from src.ws import model_path as mp
    return mp()
'''


def setup() -> Any:
    if not CANON_RW.exists():
        shutil.copytree(EXP10 / "canon", CANON_RW, ignore=shutil.ignore_patterns("__pycache__"))
        for root, dirs, files in os.walk(CANON_RW):
            for n in dirs + files:
                p = os.path.join(root, n)
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
        cf = CANON_RW / "results" / "openrouter_cost.json"  # exp10's own spend ledger: this artifact starts at 0
        if cf.exists():
            cf.unlink()
    (SCREEN_DIR / "__init__.py").write_text("")
    (SCREEN_DIR / "ws.py").write_text(WS_PY)
    src = (EXP10 / "src" / "config.py").read_text().replace("from src.ws import", "from screen10.ws import")
    (SCREEN_DIR / "config.py").write_text(src)
    if str(CANON_RW) not in sys.path:
        sys.path.insert(0, str(CANON_RW))
    import screen10.config as K
    return K


def _row(K, p: dict, *, cond: str, t: str, w: Any, s: int, h: Any = None, mode: str | None = None) -> dict:
    return {"row_id": f"S6|{t}|{cond}|{w}|{s}", "phase": "S6", "task": t, "condition": cond, "kind": p["kind"],
            "template": w, "h": h, "mode": mode, "sample_id": s, "seed": request_seed(t, f"screen_{cond}", w, s),
            "prompt_sha256": p["sha"], "prompt_len": len(p["ids"]), "spec_start": p["spec_start"], "spec_end": p["R"] - 5,
            "seg_start": p["seg_start"], "noun": p.get("noun"), "pad_k": p.get("k"), "prompt_ids": p["ids"],
            "max_tokens": 1024}


def b6_requests(K) -> list[dict]:
    out = []
    for t, x in EVENTS.items():
        for w in range(1, 6):
            for s in range(10):
                h = 1 if s < 5 else 2
                out.append(_row(K, K.p_neutral(t, x, w, h), cond="screen_vetofree", t=t, w=w, s=s, h=h, mode=x))
            for s in range(10):
                out.append(_row(K, K.p_nonce(t, w), cond="nonce", t=t, w=w, s=s))
        for s in range(50):
            out.append(_row(K, K.p_novelty(t), cond="novelty", t=t, w=None, s=s))
    return out


def label(rows: list[dict], cap: float = 0.12) -> list[dict]:
    import pipeline as PP

    have = {r["row_id"] for r in read_jsonl(LAB)}
    todo = [r for r in rows if r["row_id"] not in have]
    if not todo:
        return read_jsonl(LAB)
    lab = PP.label_rows([{k: v for k, v in r.items() if k not in ("out_ids",)} for r in todo], judge_cap=cap)
    keep = ("row_id", "phase", "task", "condition", "mode", "template", "label", "labeller_source", "passed",
            "runtime_label", "ast_label", "judge_label", "code_sha256", "event_id", "round", "arm", "hit", "weight")
    append_jsonl(LAB, [{k: r.get(k) for k in keep} for r in lab])
    return read_jsonl(LAB)


def exp10_rows() -> list[dict]:
    return read_jsonl(EXP10 / "data" / "labelled.jsonl")


def ngram_for(t: str, x: str, K) -> dict:
    from src.ngrams import find_ngram

    base = [r for r in exp10_rows() if r["task"] == t and r["kind"] == "baseline" and r["label"] == x and r.get("code")]
    codes = [r["code"] for r in base]
    gen = [r["gen_ids"] for r in base if r.get("gen_ids")]
    forced = collections.defaultdict(list)
    for r in read_jsonl(EXP10 / "data" / "forced_set.jsonl"):
        if r["task"] == t and r["label"] == r["j"] and r.get("code"):
            forced[r["j"]].append(r["code"])
    others = {j: forced.get(j, []) for j in K.MODES[t] if j != x}
    return find_ngram(t, x, codes, gen, others)


def veto_rounds(llm, K, labels: list[dict], max_rounds: int = 3) -> dict:
    """D4: one-shot / persistent / iterated vetoes on the screen pass-1 (50 per task), canon labels between rounds."""
    from src.engine_vllm import generate
    from src.ngrams import find_ngram
    from src.veto import continuation_reqs, plan_sample

    tok = K.tokenizer()
    raw = {r["row_id"]: r for r in read_jsonl(RAW)}
    summ = {}
    grams = {}
    for t, x in EVENTS.items():
        ng = ngram_for(t, x, K)
        summ[t] = {"X": x, "ngrams": [ng], "rounds": []}
        if ng.get("defined"):
            grams[t] = [ng["ids"]]
            logger.info(f"screen n-gram {t} {x}: {ng['decoded']!r} max collateral {ng['max_collateral']:.2f}")
    active = [t for t in EVENTS if t in grams]
    for rnd in range(1, max_rounds + 1):
        if not active:
            break
        plans = []
        for t in active:
            p1 = sorted([r for r in raw.values() if r["task"] == t and r["condition"] == "screen_vetofree"],
                        key=lambda r: r["row_id"])
            for r in p1:
                pids = K.p_neutral(t, EVENTS[t], int(r["template"]), int(r["h"]))["ids"]
                pl = plan_sample(task=t, tag=f"screen:{t}:r{rnd}", w=r["template"], sid=r["row_id"], prompt_ids=pids,
                                 y=r["out_ids"], grams=grams[t])
                plans.append((t, r, pids, pl))
        red = [(i, pl["redraw_req"]) for i, (_, _, _, pl) in enumerate(plans) if pl["hit"]]
        outs = generate(llm, [q for _, q in red]) if red else []
        tok_by = {i: (o["out_ids"][0] if o["out_ids"] else None) for (i, _), o in zip(red, outs)}
        conts = []
        for i, (t, r, pids, pl) in enumerate(plans):
            if pl["hit"] and tok_by.get(i) is not None:
                for c in continuation_reqs(task=t, tag=f"screen:{t}:r{rnd}", w=r["template"], sid=r["row_id"],
                                           prompt_ids=pids, y=r["out_ids"], t=pl["t"], tok=tok_by[i], grams=grams[t],
                                           oneshot=(rnd == 1)):
                    conts.append((i, c))
        couts = generate(llm, [c for _, c in conts]) if conts else []
        by = collections.defaultdict(list)
        for (i, c), o in zip(conts, couts):
            by[i].append((c, o))
        rows = []
        arms = ["persistent"] + (["oneshot"] if rnd == 1 else [])
        for i, (t, r, pids, pl) in enumerate(plans):
            for arm in arms:
                rid = f"S6|{t}|veto:{arm}:r{rnd}|{r['row_id']}"
                if not pl["hit"]:
                    ids, hit = r["out_ids"], False
                else:
                    got = [(c, o) for c, o in by.get(i, []) if c["arm"] == arm]
                    ids = list(r["out_ids"][:pl["t"]]) + ([tok_by[i]] if tok_by.get(i) is not None else []) + \
                        (got[0][1]["out_ids"] if got else [])
                    hit = True
                rows.append({"row_id": rid, "phase": "S6", "task": t, "condition": f"veto:{arm}:r{rnd}", "arm": arm,
                             "round": rnd, "hit": hit, "weight": 1.0, "pass1_row_id": r["row_id"], "mode": EVENTS[t],
                             "out_ids": ids, "grams": grams[t],
                             "text": tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)})
        append_jsonl(RAW, rows)
        labels = label(rows)
        lab_by = {l["row_id"]: l for l in labels}
        nxt = []
        for t in active:
            rr = [r for r in rows if r["task"] == t and r["arm"] == "persistent"]
            att = [(lab_by[r["row_id"]]["label"], r) for r in rr if lab_by.get(r["row_id"], {}).get("label") not in (None, "no_code")]
            share = sum(1 for l, _ in att if l == EVENTS[t]) / max(len(att), 1)
            summ[t]["rounds"].append({"round": rnd, "A_share": share, "n_attempts": len(att),
                                      "n_hit": sum(1 for r in rr if r["hit"]),
                                      "decoded": [tok.decode(g) for g in grams[t]]})
            logger.info(f"screen {t} r{rnd}: {EVENTS[t]} share {share:.2f} over {len(att)} attempts")
            if share >= 0.2 and rnd < max_rounds:
                re = [r for l, r in att if l == EVENTS[t] and r["hit"]]
                codes, gen = [], []
                import pipeline as PP  # noqa: F401
                from labeller.extract import extract_code
                for r in re:
                    code, _ = extract_code(r["text"])
                    if code:
                        codes.append(code)
                        gen.append(r["out_ids"])
                forced = collections.defaultdict(list)
                for f in read_jsonl(EXP10 / "data" / "forced_set.jsonl"):
                    if f["task"] == t and f["label"] == f["j"] and f.get("code"):
                        forced[f["j"]].append(f["code"])
                ng = find_ngram(t, EVENTS[t], codes, gen, {j: forced.get(j, []) for j in K.MODES[t] if j != EVENTS[t]},
                                exclude=[tuple(g) for g in grams[t]])
                summ[t]["ngrams"].append(ng)
                if ng.get("defined"):
                    grams[t] = grams[t] + [ng["ids"]]
                    nxt.append(t)
        active = nxt
    write_json(DATA / "screen_veto_summary.json", summ)
    return summ


def forecasts(K, labels: list[dict]) -> dict:
    from src.forecasts import argmax, counts, mass_transfer, normalise
    from src.proximity import nominate
    from src.scoring import uniform

    lab_by = {l["row_id"]: l for l in labels}
    raw = {r["row_id"]: r for r in read_jsonl(RAW)}
    ex = exp10_rows()
    fa = read_jsonl(EXP10 / "data" / "free_answers.jsonl")
    forced = collections.defaultdict(list)
    for r in read_jsonl(EXP10 / "data" / "forced_set.jsonl"):
        if r["label"] == r["j"] and r.get("code"):
            forced[(r["task"], r["j"])].append(r["code"])
    jobs = []
    for t, x in EVENTS.items():
        xs = [r["code"] for r in ex if r["task"] == t and r["kind"] == "baseline" and r["label"] == x and r.get("code")]
        jobs.append({"event_id": f"{t}|screen|{x}", "X": x, "xs": xs,
                     "survivors": {j: forced.get((t, j), []) for j in K.MODES[t] if j != x and forced.get((t, j))}})
    prox = nominate(jobs, workers=4, budget_s=600)
    out = {}
    for t, x in EVENTS.items():
        S = [m for m in K.MODES[t] if m != x]
        base = [r["label"] for r in ex if r["task"] == t and r["kind"] == "baseline" and r["label"] != "no_code"]
        cB = counts(base, x, S)
        B_S = normalise(cB, S) if sum(cB.values()) >= 5 else uniform(S)
        s_x = sum(1 for l in base if l == x) / max(len(base), 1)
        fam = {}
        # SUBTRACT
        vr = [r for r in raw.values() if r["task"] == t and r.get("arm") == "persistent"]
        rounds = sorted({r["round"] for r in vr})
        chosen = None
        for k in rounds:
            sel = [r for r in vr if r["round"] == k]
            labs = [lab_by.get(r["row_id"], {}).get("label") for r in sel]
            if sum(counts(labs, x, S).values()) >= 20:
                chosen = (k, sel, labs)
        if chosen:
            k, sel, labs = chosen
            f = normalise(counts(labs, x, S), S)
            tr = normalise(counts([l for l, r in zip(labs, sel) if r["hit"]], x, S), S)
            fam["SUBTRACT"] = {"f": f, "top1": argmax(tr or f, S), "defined": True, "round": k}
        else:
            fam["SUBTRACT"] = {"f": None, "top1": None, "defined": False}
        # LADDER: nonce + novelty (randdir not run on the screen)
        pooled, qual = collections.Counter(), []
        for cond in ("nonce", "novelty"):
            labs = [lab_by.get(r["row_id"], {}).get("label") for r in raw.values() if r["task"] == t and r["condition"] == cond]
            c = counts(labs, x, S)
            if sum(c.values()) >= 20:
                pooled.update(c)
                qual.append(cond)
        lf = normalise(pooled, S) if qual else None
        fam["LADDER"] = {"f": lf, "top1": argmax(lf, S) if lf else None, "defined": lf is not None, "pushes": qual}
        # ASSOCIATE from exp10 free answers
        ans = collections.Counter(a["label"] for a in fa if a["task"] == t and a["X"] == x and a.get("label") in S)
        tgt = sorted(ans, key=lambda m: (-ans[m], S.index(m)))[0] if ans else None
        fam["ASSOCIATE"] = {"f": mass_transfer(B_S, s_x, tgt, S), "top1": tgt, "defined": tgt is not None,
                            "answers": dict(ans)}
        pt = prox["events"][f"{t}|screen|{x}"]["nominee_zs"]
        fam["PROXIMITY"] = {"f": mass_transfer(B_S, s_x, pt, S), "top1": pt, "defined": pt is not None,
                            "zs_median": prox["events"][f"{t}|screen|{x}"]["zs_median"]}
        pm = {"ASSOCIATE": {"f": {k: float(k == tgt) for k in S + ['other']} if tgt else None, "defined": tgt is not None},
              "PROXIMITY": {"f": {k: float(k == pt) for k in S + ['other']} if pt else None, "defined": pt is not None},
              "SUBTRACT": {"f": fam["SUBTRACT"]["f"], "defined": fam["SUBTRACT"]["defined"]},
              "LADDER": {"f": fam["LADDER"]["f"], "defined": fam["LADDER"]["defined"]}}
        out[t] = {"event_id": f"{t}|screen|{x}", "task": t, "event_type": "modal", "X": x, "S": S, "B_S": B_S,
                  "s_X": s_x, "families": fam, "families_pm": pm}
    write_json(PRED / "screen_forecasts.json", {"events": out, "proximity": prox})
    return out


def score(fcs: dict) -> dict:
    from src import scoring as SC

    ev10 = read_json(EXP10 / "results" / "events.json")
    res = {}
    for t, x in EVENTS.items():
        row = next(e for e in ev10[t] if e["name"].startswith(f"ban:{x}"))
        labs = [k for k, v in row["attempted_counts"].items() for _ in range(int(v))]
        fc = fcs[t]
        sc = SC.score_event({"event_type": "modal", "X": x, "S": fc["S"]}, fc, labs)
        fpm = dict(fc, families={k: dict(v, f=fc["families_pm"][k]["f"], defined=fc["families_pm"][k]["defined"])
                                 for k, v in fc["families"].items()})
        sc_pm = SC.score_event({"event_type": "modal", "X": x, "S": fc["S"]}, fpm, labs)
        res[t] = {"exp10_ban_landing": row["attempted_counts"], "scored": sc, "logscore_pm": sc_pm["logscore"],
                  "forecast_top1": {k: v["top1"] for k, v in fc["families"].items()}}
        logger.info(f"screen {t} ban {x}: hit {sc['hit_label']} top1 {res[t]['forecast_top1']} "
                    f"logscore { {k: round(v, 3) for k, v in sc['logscore'].items()} }")
    write_json(RESULTS / "screen.json", res)
    return res
