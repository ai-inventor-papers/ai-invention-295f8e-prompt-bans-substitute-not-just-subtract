#!/usr/bin/env python3
"""L: retrospective forecast contest on the recorded push-landing events (plan STEP 3).

  events   (CPU) the event table from the records, frozen in commit #1 before any opening pass:
           ITER4 exp22 escape (FP8 Qwen: T03 T10 T2 T05 T1), ITER5 exp25 extra_arm_a (bf16 Qwen: T03 T10),
           panel A (exp25: A1 A3 A7), panel B (exp26: B2 B3 B4 B7), exp28 Gemma (7 events) -> data/l_events.json
  open     (GPU) teacher-forced opening ranking: for each event task and catalogue algorithm, LL48 = summed log-prob of
           the first 48 program tokens after chat(twin) + '```python\\n'; programs = bench/unit references (+ bench
           forced_programs); logmeanexp over programs, mean over twin templates -> data/tf_scores.jsonl
  score    (CPU) forecasts BASE / TWINMIN / OPEN (+ 1/rank sensitivity), 5% uniform mixing, 'other' floored at 2%;
           commit of the forecast values; top-1 hits, log scores, exact one-sided sign test BASE > OPEN on the
           events where their top-1 differ and exactly one hits; Wilcoxon on log-score differences
usage: .venv/bin/python src/lcontest.py events | open | score
"""

from __future__ import annotations

import gc
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import INPUTS, ROOT, read_json, read_jsonl, setup_logging, utc_now, write_json
from cfg6 import EXP

EVENTS = ROOT / "data" / "l_events.json"
TF = ROOT / "data" / "tf_scores.jsonl"
OUT = ROOT / "results" / "landing_forecast.json"
BENCH = INPUTS / "exp11" / "bench"
SUITE_TASKS = INPUTS / "exp8" / "suite" / "tasks"
GEMMA_ID, GEMMA_REV = "google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"
N_OPEN = 48
MIX, OTHER_FLOOR = 0.05, 0.02


def bench_dir(task: str) -> Path | None:
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return d
    return None


def _norm(comp: dict[str, float]) -> dict[str, float]:
    s = sum(comp.values())
    return {k: v / s for k, v in comp.items()} if s > 0 else {}


# ------------------------------------------------------------------------------------------------ events
def build_events() -> list[dict[str, Any]]:
    ev: list[dict[str, Any]] = []
    # (1) FP8 Qwen existing tasks: exp22 escape push_landing_v4 (fractions), runner-up from exp22 explore.json
    esc = read_json(EXP[22] / "results" / "escape.json")
    exp_ru = {t: v.get("runner_up") for t, v in read_json(EXP[22] / "results" / "explore.json")["tasks"].items()}
    defaults = {"T03": "full_sort", "T10": "union_find", "T2": "dijkstra", "T05": "hash_map", "T1": "bfs"}
    for t in ("T03", "T10", "T2", "T05", "T1"):
        land = esc[t]["push_landing_v4"]
        ev.append({"event": f"qwen_fp8|{t}", "set": "FP8 Qwen existing (exp22)", "model": "qwen", "engine": "FP8",
                   "task": t, "default": defaults[t], "landing_top1": max(land, key=land.get),
                   "landing_comp": {k: round(100 * v, 3) for k, v in land.items()}, "r_u": exp_ru.get(t),
                   "q_base_counts": None, "base_support": "runner-up only (exp22 explore.json); no base composition "
                                                         "on disk", "twin_nondefault": {},
                   "source": "exp22 results/escape.json push_landing_v4; explore.json runner_up"})
    # (2) bf16 Qwen existing tasks: exp25 extra_arm_a (landing field + summed confirmed landing counts)
    xa = read_json(EXP[25] / "results" / "extra_arm_a.json")
    for t in ("T03", "T10"):
        comp: Counter = Counter()
        for c in xa[t]["cells"]:
            if c.get("confirmed"):
                comp.update(c.get("landing_counts") or {})
        tw = {k: v for k, v in (xa[t]["twin"].get("landing_correct") or {}).items()}
        ev.append({"event": f"qwen_bf16|{t}", "set": "bf16 Qwen existing (exp25 extra arm)", "model": "qwen",
                   "engine": "bf16", "task": t, "default": xa[t]["default"], "landing_top1": xa[t]["landing"],
                   "landing_comp": dict(comp), "r_u": exp_ru.get(t), "q_base_counts": None,
                   "base_support": "runner-up only (exp22 explore.json)", "twin_nondefault": tw,
                   "flag": "recorded landing top-1 differs from the summed confirmed-cell composition"
                   if comp and max(comp, key=comp.get) != xa[t]["landing"] else None,
                   "source": "exp25 results/extra_arm_a.json"})
    # (3) panel A (exp25): A1 A3 A7
    pa = {u["unit_id"]: u for u in read_json(EXP[25] / "pooled_inputs.json")["units"]}
    for u in ("A1", "A3", "A7"):
        r = pa[u]
        comp: Counter = Counter()
        for c in r["escape"]["cells"]:
            if c.get("confirmed"):
                comp.update(c.get("landing_counts") or {})
        D = r["default"]
        qb = {k: v for k, v in r["base"]["chat"]["comp_correct"].items() if k != D}
        tw = {k: v for k, v in r["twin"]["comp_correct"].items() if k != D}
        ev.append({"event": f"qwen_panelA|{u}", "set": "panel A (exp25)", "model": "qwen", "engine": "bf16",
                   "task": u, "default": D, "catalogue": r.get("catalogue"), "landing_top1": r["escape"]["landing"],
                   "landing_comp": dict(comp), "r_u": r["base"]["r"], "q_base_counts": qb,
                   "base_support": {"n_valid": r["base"]["chat"]["n_valid"], "n_correct": r["base"]["chat"]["n_correct"]},
                   "twin_nondefault": tw, "source": "exp25 pooled_inputs.json"})
    # (4) panel B (exp26): B2 B3 B4 B7
    pb = {r["unit_id"]: r for r in read_json(EXP[26] / "pooled_inputs.json")["records"]}
    for u in ("B2", "B3", "B4", "B7"):
        r = pb[u]
        D = r["unit_facts"]["default"]
        qb = {k: v for k, v in r["base"]["correct_composition"].items() if k != D}
        tw = {k: v for k, v in r["twin"]["correct_composition"].items() if k != D}
        ev.append({"event": f"qwen_panelB|{u}", "set": "panel B (exp26)", "model": "qwen", "engine": "bf16",
                   "task": u, "default": D, "catalogue": r["unit_facts"]["catalogue"],
                   "landing_top1": r["outcomes"]["push_landing"],
                   "landing_comp": r["outcomes"].get("push_landing_composition") or {},
                   "r_u": r["base"]["r_u"], "q_base_counts": qb,
                   "base_support": {"n_correct": r["base"]["n_correct_base"], "n": r["base"]["n_base"]},
                   "twin_nondefault": tw, "source": "exp26 pooled_inputs.json"})
    # (5) Gemma (exp28 e_a2 events + predictors twin attempts)
    ga = read_json(EXP[28] / "results" / "e_a2.json")["events"]
    gp = read_json(EXP[28] / "results" / "predictors.json")["units"]
    for e in ga:
        t = e["unit"]
        D = gp[t]["D"]
        tw = {k: v for k, v in (gp[t]["default"].get("attempt_counts") or {}).items() if k not in (D, "invalid",
                                                                                                   "other")}
        ev.append({"event": f"gemma|{t}", "set": "Gemma (exp28)", "model": "gemma", "engine": "bf16", "task": t,
                   "default": D, "catalogue": gp[t].get("catalogue"), "survivors": e["survivors"],
                   "landing_top1": e["landing"], "landing_comp": e["landing_composition"], "r_u": e["r_u"],
                   "q_base_probs": e["q_base"], "q_base_counts": None,
                   "base_support": {k: gp[t]["pt_chat"].get(k) for k in ("n_rows", "n_correct", "attempt_counts")},
                   "twin_nondefault": tw, "source": "exp28 results/e_a2.json + predictors.json"})
    for e in ev:
        e["hit_base_recorded"] = bool(e["r_u"] == e["landing_top1"])
    write_json(EVENTS, {"events": ev, "n": len(ev), "hits_base_top1": sum(e["hit_base_recorded"] for e in ev),
                        "utc": utc_now()})
    logger.info(f"L events: {len(ev)}; base runner-up top-1 hits {sum(e['hit_base_recorded'] for e in ev)}")
    return ev


# ------------------------------------------------------------------------------------------------ programs
def catalogue_of(e: dict[str, Any]) -> list[str]:
    t = e["task"]
    if e.get("survivors"):
        return list(e["survivors"])
    if e.get("catalogue"):
        return [a for a in e["catalogue"] if a != e["default"]]
    bd = bench_dir(t)
    if bd is not None:
        sp = read_json(bd / "spec.json")
        return [c["mode"] if "mode" in c else c.get("name") for c in sp["catalogue"] if
                (c.get("mode") or c.get("name")) != e["default"]]
    return [a for a in programs_for(e) if a not in (e["default"], "other")]


def programs_for(e: dict[str, Any]) -> dict[str, list[str]]:
    """{alg: [program text, ...]}: bench references + forced programs; unit references; path-suite references."""
    t = e["task"]
    out: dict[str, list[str]] = defaultdict(list)
    bd = bench_dir(t)
    if bd is not None:
        for f in sorted((bd / "references").glob("*.py")):
            out[f.stem].append(f.read_text())
        fpath = bd / "forced_programs.jsonl"
        for r in read_jsonl(fpath):
            m = r.get("mode") or r.get("label") or r.get("target")
            code = r.get("code") or r.get("program")
            if m and code and (r.get("passed", True)) and (r.get("adherent", True)):
                out[m].append(code)
    elif t in ("T1", "T2"):
        d = SUITE_TASKS / ("t1_grid" if t == "T1" else "t2_wsp") / "references"
        for f in sorted(d.glob("*.py")):
            stem = f.stem
            alg = {"astar_fg": "astar_gbfs", "gbfs_counter": "astar_gbfs"}.get(stem, stem.split("_")[0])
            if t == "T2":
                alg = {"bf": "bf_spfa", "spfa": "bf_spfa", "bellman": "bf_spfa"}.get(alg, alg)
            out[alg].append(f.read_text())
    else:
        base = None
        if t.startswith("A"):
            for d in (EXP[25] / "newbench").iterdir():
                if d.name.startswith(t + "_"):
                    base = d
        else:
            base = EXP[26] / "units" / t
        if base is not None and (base / "references").exists():
            for f in sorted((base / "references").glob("*.py")):
                out[f.stem].append(f.read_text())
    return dict(out)


def twin_texts(e: dict[str, Any]) -> list[str]:
    t = e["task"]
    if t.startswith("A"):
        rows = read_jsonl(EXP[25] / "data" / "prompts_new.jsonl")
        return [r["user_text"] for r in rows if r["task"] == t and r["kind"] == "twin" and r["w"] != "W4"]
    if t.startswith("B"):
        rows = read_jsonl(EXP[26] / "data" / "prompts.jsonl")
        return [r["user_text"] for r in rows if r["unit"] == t and r["kind"] == "twin" and
                r.get("template_id") != "W4"]
    rows = read_jsonl(ROOT / "prompts" / "prompts.jsonl")
    return [r["user_text"] for r in rows if r["task"] == t and r["kind"] == "twin" and r["w"] != "W4"]


# ------------------------------------------------------------------------------------------------ GPU: opening
def load_gemma_text():
    """exp28 engine.load_model: the language-model weights of the multimodal gemma-3-4b-it checkpoint (keys
    'language_model.model.*') loaded into a Gemma3ForCausalLM built from config.text_config (bf16, sdpa, tied head)."""
    import torch
    from safetensors import safe_open
    from transformers import AutoConfig, AutoTokenizer, Gemma3ForCausalLM

    from cfg import model_path
    path = model_path(GEMMA_ID, GEMMA_REV)
    tok = AutoTokenizer.from_pretrained(path)
    tcfg = AutoConfig.from_pretrained(path).text_config
    tcfg._attn_implementation = "sdpa"
    old = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            model = Gemma3ForCausalLM(tcfg)
    finally:
        torch.set_default_dtype(old)
    model.eval()
    model.requires_grad_(False)
    sd = model.state_dict()
    loaded = set()
    idx = json.loads((Path(path) / "model.safetensors.index.json").read_text())
    for fn in sorted(set(idx["weight_map"].values())):
        with safe_open(str(Path(path) / fn), framework="pt", device="cuda") as fh:
            for k in fh.keys():
                if not k.startswith("language_model.model."):
                    continue
                nk = "model." + k[len("language_model.model."):]
                t = fh.get_tensor(k)
                sd[nk].copy_(t.to(sd[nk].dtype))
                loaded.add(nk)
                del t
    model.tie_weights()
    missing = sorted(set(k for k in sd if not k.startswith("lm_head")) - loaded)
    assert not missing, f"gemma weights not loaded: {missing[:5]}"
    logger.info(f"gemma-3-4b-it text model loaded: {len(loaded)} tensors")
    return tok, model


def stage_open() -> None:
    import torch
    ev = read_json(EVENTS)["events"]
    done = {(r["model"], r["task"], r["alg"], r["prog_idx"], r["tmpl_idx"]) for r in read_jsonl(TF)}
    for model_name in ("qwen", "gemma"):
        tasks = sorted({e["task"] for e in ev if e["model"] == model_name})
        if model_name == "qwen":
            from engine6 import load_model_bf16
            tok, model, _ = load_model_bf16()
            dev = model.lm_head.weight.device
        else:
            tok, model = load_gemma_text()
            dev = torch.device("cuda", 0)
        t0 = time.time()
        for t in tasks:
            e = next(x for x in ev if x["model"] == model_name and x["task"] == t)
            progs = programs_for(e)
            texts = twin_texts(e)
            rows = []
            for ti, ut in enumerate(texts):
                msgs = [{"role": "user", "content": ut}]
                kw = {"enable_thinking": False} if model_name == "qwen" else {}
                pre = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw) + "```python\n"
                pre_ids = tok(pre, add_special_tokens=False)["input_ids"]
                for alg, plist in progs.items():
                    for pi, code in enumerate(plist[:6]):
                        if (model_name, t, alg, pi, ti) in done:
                            continue
                        cids = tok(code, add_special_tokens=False)["input_ids"][:N_OPEN]
                        ids = torch.tensor([pre_ids + cids], device=dev)
                        with torch.no_grad():
                            out = model(input_ids=ids) if model_name == "gemma" else None
                            if model_name == "qwen":
                                h = model.model(input_ids=ids).last_hidden_state
                                lg = model.lm_head(h[0, len(pre_ids) - 1:-1]).float()
                            else:
                                lg = out.logits[0, len(pre_ids) - 1:-1].float()
                        lp = torch.log_softmax(lg, -1).gather(-1, ids[0, len(pre_ids):, None])[:, 0]
                        rows.append({"model": model_name, "task": t, "alg": alg, "prog_idx": pi, "tmpl_idx": ti,
                                     "n_tok": len(cids), "ll48": float(lp.sum()), "utc": utc_now()})
            with open(TF, "a") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
            logger.info(f"open {model_name}/{t}: {len(rows)} teacher-forced passes ({time.time() - t0:.0f}s)")
        del model
        gc.collect()
        torch.cuda.empty_cache()


# ------------------------------------------------------------------------------------------------ scoring
def mix(p: dict[str, float], support: list[str]) -> dict[str, float]:
    keys = list(dict.fromkeys(list(support) + ["other"]))
    q = {k: p.get(k, 0.0) for k in keys}
    s = sum(q.values())
    q = {k: (v / s if s > 0 else 1 / len(keys)) for k, v in q.items()}
    q = {k: (1 - MIX) * v + MIX / len(keys) for k, v in q.items()}
    if q["other"] < OTHER_FLOOR:
        q["other"] = OTHER_FLOOR
    s = sum(q.values())
    return {k: v / s for k, v in q.items()}


def logscore(q: dict[str, float], comp: dict[str, float]) -> float:
    n = sum(comp.values())
    if n <= 0:
        return float("nan")
    return float(sum(c * math.log(q.get(k, q["other"]) if k in q else q["other"]) for k, c in comp.items()) / n)


def sign_test_one_sided(k: int, n: int) -> float:
    return float(sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n) if n else float("nan")


def stage_score(dry: bool = False) -> dict[str, Any]:
    from scipy.stats import wilcoxon

    from commit6 import commit

    ev = read_json(EVENTS)["events"]
    tf = read_jsonl(TF)
    open_s: dict[tuple[str, str], dict[str, float]] = {}
    nprog: dict[tuple[str, str], dict[str, int]] = {}
    by = defaultdict(list)
    for r in tf:
        by[(r["model"], r["task"], r["alg"], r["tmpl_idx"])].append(r["ll48"])
    agg = defaultdict(lambda: defaultdict(list))
    for (m, t, a, ti), v in by.items():
        v = np.array(v)
        agg[(m, t)][a].append(float(np.log(np.mean(np.exp(v - v.max()))) + v.max()))
        nprog.setdefault((m, t), {})[a] = len(v)
    for k, d in agg.items():
        open_s[k] = {a: float(np.mean(v)) for a, v in d.items()}
    forecasts, rows = {}, []
    for e in ev:
        sup = [a for a in (catalogue_of(e) or []) if a != e["default"]]
        sup = list(dict.fromkeys(sup + [k for k in e["landing_comp"] if k not in (e["default"], "other")] +
                                 ([e["r_u"]] if e["r_u"] else [])))
        if e.get("q_base_counts"):
            base = {k: v + 1 for k, v in e["q_base_counts"].items()}
            for a in sup:
                base.setdefault(a, 1)
        elif e.get("q_base_probs"):
            base = dict(e["q_base_probs"])
        else:
            base = {a: (2.0 if a == e["r_u"] else 1.0) for a in sup}
        twin = {k: v + 1 for k, v in e["twin_nondefault"].items()} if e["twin_nondefault"] else None
        if twin:
            for a in sup:
                twin.setdefault(a, 1)
        os_ = open_s.get((e["model"], e["task"]), {})
        osup = {a: os_[a] for a in sup if a in os_}
        open_p = None
        open_rank = None
        if osup:
            mx = max(osup.values())
            open_p = {a: math.exp(v - mx) for a, v in osup.items()}
            order = sorted(osup, key=osup.get, reverse=True)
            open_rank = {a: 1.0 / (i + 1) for i, a in enumerate(order)}
        f = {"BASE": mix(base, sup), "TWINMIN": mix(twin, sup) if twin else None,
             "OPEN": mix(open_p, sup) if open_p else None, "OPEN_rank": mix(open_rank, sup) if open_rank else None}
        forecasts[e["event"]] = {"support": sup, "forecasts": f,
                                 "open_n_programs": nprog.get((e["model"], e["task"]), {})}
    if not dry:
        commit("commit1b_L_forecasts", {"forecasts": forecasts})
    for e in ev:
        fc = forecasts[e["event"]]["forecasts"]
        r = {"event": e["event"], "set": e["set"], "model": e["model"], "engine": e["engine"], "task": e["task"],
             "landing_top1": e["landing_top1"], "r_u": e["r_u"]}
        for name, q in fc.items():
            if q is None:
                r[f"{name}_top1"] = None
                r[f"{name}_hit"] = None
                r[f"{name}_logscore"] = None
                continue
            top = max((k for k in q if k != "other"), key=q.get)
            r[f"{name}_top1"] = top
            r[f"{name}_hit"] = bool(top == e["landing_top1"])
            r[f"{name}_logscore"] = logscore(q, e["landing_comp"] or {e["landing_top1"]: 1})
        uni = mix({}, forecasts[e["event"]]["support"])
        r["UNIFORM_logscore"] = logscore(uni, e["landing_comp"] or {e["landing_top1"]: 1})
        rows.append(r)
    out: dict[str, Any] = {"events": rows, "n_events": len(rows)}
    for name in ("BASE", "TWINMIN", "OPEN", "OPEN_rank"):
        d = [r for r in rows if r.get(f"{name}_hit") is not None]
        out[f"{name}_hits"] = {"hits": sum(r[f"{name}_hit"] for r in d), "n_defined": len(d)}
        for sub in ("FP8", "bf16"):
            for mdl in ("qwen", "gemma"):
                dd = [r for r in d if r["engine"] == sub and r["model"] == mdl]
                if dd:
                    out[f"{name}_hits"][f"{mdl}_{sub}"] = [sum(r[f"{name}_hit"] for r in dd), len(dd)]
    # primary: events where BASE top-1 != OPEN top-1 and exactly one hits
    disc = [r for r in rows if r.get("OPEN_top1") and r["BASE_top1"] != r["OPEN_top1"] and
            (r["BASE_hit"] != r["OPEN_hit"])]
    kb = sum(r["BASE_hit"] for r in disc)
    out["primary_sign_test"] = {"n_discordant": len(disc), "base_wins": kb, "open_wins": len(disc) - kb,
                                "p_one_sided_base_gt_open": sign_test_one_sided(kb, len(disc)),
                                "minimum_for_p_lt_0.05": "5 of 5 (p = 0.031)",
                                "n_top1_differ": sum(1 for r in rows if r.get("OPEN_top1") and
                                                     r["BASE_top1"] != r["OPEN_top1"])}
    p = out["primary_sign_test"]["p_one_sided_base_gt_open"]
    oh, bh = out["OPEN_hits"]["hits"], out["BASE_hits"]["hits"]
    out["verdict"] = ("the base runner-up adds information beyond the instruct model's own opening ranking"
                      if (isinstance(p, float) and p < 0.05) else
                      ("a push lands on the instruct model's own next-ranked algorithm (OPEN hits at least as often)"
                       if oh >= bh else "not resolved: BASE hits more often but the sign test is not significant"))
    for a, b in (("BASE", "OPEN"), ("BASE", "TWINMIN")):
        d = [(r[f"{a}_logscore"], r[f"{b}_logscore"]) for r in rows if r.get(f"{b}_logscore") is not None and
             r.get(f"{a}_logscore") is not None and not math.isnan(r[f"{a}_logscore"])]
        diffs = [x - y for x, y in d]
        res = {"n": len(d), "mean_diff": float(np.mean(diffs)) if diffs else None}
        if len([x for x in diffs if abs(x) > 1e-12]) >= 2:
            res["wilcoxon_p_two_sided"] = float(wilcoxon(diffs).pvalue)
        out[f"logscore_{a}_minus_{b}"] = res
    # undefined forecasts scored as uniform (the plan's convention) beside the defined-only means
    for name in ("TWINMIN", "OPEN"):
        vals = [r[f"{name}_logscore"] if r.get(f"{name}_logscore") is not None else r["UNIFORM_logscore"]
                for r in rows]
        out[f"{name}_mean_logscore_undefined_as_uniform"] = float(np.nanmean(vals))
    out["BASE_mean_logscore"] = float(np.nanmean([r["BASE_logscore"] for r in rows]))
    if not dry:
        write_json(OUT, out)
    logger.info(f"L: BASE {out['BASE_hits']} OPEN {out['OPEN_hits']} TWINMIN {out['TWINMIN_hits']}; "
                f"sign test {out['primary_sign_test']}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("lcontest")
    st = sys.argv[1]
    if st == "events":
        from commit6 import commit
        ev = build_events()
        commit("commit1_L_events", {"events": ev, "scoring_rule": "top-1 hits, mean log score of the realised "
                                    "landing composition, sign test BASE > OPEN, minimum 5 of 5"})
    elif st == "open":
        stage_open()
    elif st == "score":
        stage_score()


if __name__ == "__main__":
    main()
