"""Stage 1 (ban-free forecasts: copy twin, iterated persistent signature veto, bf16 baseline check, SUBTRACT-IN-CONTEXT)
and stage 2 (NAMED / UNNAMED exposure bans, optional W1-W4 template arm) orchestration."""

from __future__ import annotations

import re
import time
from collections import Counter

from loguru import logger

from . import ngram as NG
from .core import (COMMIT_LOG, LOGS, MAX_ROUNDS, MIN_NONY_SUBTRACT, PRED, REEMERGE_MIN, RESULTS, TASK_ORDER,
                   TEMPLATES_W1_W4, Timer, deviation, read_json, read_jsonl, wilson, write_json)
from .forecasts import allocation, task_groups
from .labels import LabelPool, openrouter_key_info
from .sampling import (GEN_PATH, LABELS_RAW, Engine, PromptIds, arm_requests, baseline_requests, combined_labels,
                       load_design, ordered_keys, priority_of, reemergence_ngram, run_staged, smoke_tests, surfaces)

GPU_BUDGET_S = 2 * 3600
TEMPLATE_ARM_MIN_LEFT_S = 45 * 60


def _norm(label: str, y: str, survivors: list[str]) -> str | None:
    if label == "invalid":
        return None
    if label == y or label in survivors:
        return label
    return "other"


def kv_cache_tokens(log_name: str) -> int | None:
    p = LOGS / log_name
    if not p.exists():
        return None
    m = re.findall(r"GPU KV cache size:\s*([\d,]+)\s*tokens", p.read_text(errors="ignore"))
    return int(m[-1].replace(",", "")) if m else None


def survivors_of(design: dict, key: str) -> list[str]:
    t, y = key.split(":")
    return [m for m in design["elig"]["tasks"][t]["modes"] if m != y]


def round_summary(rows: list[dict], labs: dict, y: str, survivors: list[str], default: str, g_list: list) -> dict:
    lab = [labs[r["sample_id"]] for r in rows if r["sample_id"] in labs]
    att = [l for l in lab if l["label"] != "invalid"]
    n_y = sum(1 for l in att if l["label"] == y)
    non = [l for l in att if l["label"] != y]
    land = Counter(_norm(l["label"], y, survivors) for l in non)
    occ = sum(1 for r in rows if any(NG.contains(r["token_ids"], g) for g in g_list))
    return {"n_programs": len(rows), "n_labelled": len(lab), "n_invalid": len(lab) - len(att), "n_attempts": len(att),
            "n_Y": n_y, "reemerge": (n_y / len(att)) if att else float("nan"), "n_nonY": len(non),
            "landing": dict(land), "pass_rate": (sum(1 for l in lab if l.get("passed")) / len(lab)) if lab else float("nan"),
            "default_share": (sum(1 for l in att if l["label"] == default) / len(att)) if att else float("nan"),
            "vetoed_ngram_occurrences": occ}


def stage1(args) -> None:
    openrouter_key_info()
    design = load_design()
    keys = ordered_keys(design)
    prio = priority_of(design)
    with Timer("stage1_gpu", gpu=True):
        eng = Engine(args.max_num_seqs, args.gpu_util)
        kv = kv_cache_tokens("stage1.out")
        logger.info(f"KV cache: {kv} tokens")
        write_json(RESULTS / "engine_stage1.json", {"config": eng.cfg, "kv_cache_tokens": kv, "load_s": eng.load_seconds})
        if kv is not None and kv < 8000:
            deviation(f"KV cache only {kv} tokens (< 8,000)")
        pid = PromptIds(eng.tok)
        t, y = keys[0].split(":")
        for arm in ("copy", "named", "unnamed"):
            prec = design["prompts"][f"{t}:{y}:{arm}:p0"]
            logger.info(f"RENDERED PROMPT {arm} ({len(pid(prec))} tokens, chat sha {prec['chat_sha256'][:12]}):\n"
                        f"{prec['user_text']}")
        smoke_tests(eng, design, pid)
        pool = LabelPool(LABELS_RAW, workers=args.label_workers)
        budget = {}
        reqs = []
        for k in keys:
            reqs += arm_requests(design, pid, k, "copy")
            reqs += arm_requests(design, pid, k, "veto", rnd=1, veto=[design["ngrams"][k]["ids"]], prompt_arm="copy")
        reqs += baseline_requests(design, pid)
        run_staged(eng, reqs, pool, "stage1_batchA", budget)
        logger.info(f"batch A generated; waiting for {pool.pending()} labels")
        pool.wait()
        labs = combined_labels()
        masks = {k: [design["ngrams"][k]["ids"]] for k in keys}
        rounds: dict[str, dict] = {k: {} for k in keys}
        gens = read_jsonl(GEN_PATH)
        tg_cache = {}
        active = list(keys)
        for r in range(1, MAX_ROUNDS + 1):
            gens = read_jsonl(GEN_PATH) if r > 1 else gens
            nxt = []
            for k in active:
                tk, yk = k.split(":")
                surv = survivors_of(design, k)
                dflt = design["elig"]["tasks"][tk]["default"]
                rows = [g for g in gens if g["arm"] == "veto" and g["task"] == tk and g["Y"] == yk and g["round"] == r]
                summ = round_summary(rows, labs, yk, surv, dflt, masks[k])
                summ["mask"] = [list(g) for g in masks[k]]
                summ["mask_text"] = [eng.tok.decode(g) for g in masks[k]]
                rounds[k][r] = summ
                if summ["reemerge"] >= REEMERGE_MIN and r < MAX_ROUNDS:
                    if tk not in tg_cache:
                        tg = task_groups(tk, eng.tok)
                        tg_cache[tk] = tg
                    tg = tg_cache[tk]
                    groups = {f"forced:{j}": tg["by_mode"][j] for j in design["elig"]["tasks"][tk]["modes"]
                              if j != yk and tg["by_mode"][j]}
                    groups["pilot_default"] = tg["pilot"]
                    y_rows = [g for g in rows if labs.get(g["sample_id"], {}).get("label") == yk]
                    sel = reemergence_ngram(eng.tok, y_rows, groups, masks[k])
                    copy_y = [g for g in gens if g["arm"] == "copy" and g["task"] == tk and g["Y"] == yk
                              and labs.get(g["sample_id"], {}).get("label") == yk]
                    summ["surfaces"] = surfaces(eng.tok, y_rows, copy_y, masks[k])
                    if sel and sel.get("ids"):
                        sel["decoded"] = eng.tok.decode(sel["ids"])
                        summ["next_ngram"] = sel
                        if sel.get("relaxed"):
                            logger.warning(f"{k} round {r + 1}: relaxed n-gram {sel['decoded']!r}")
                        masks[k] = masks[k] + [sel["ids"]]
                        nxt.append(k)
                    else:
                        summ["next_ngram"] = sel
                        logger.warning(f"{k}: no next n-gram after round {r} ({sel})")
                logger.info(f"  veto r{r} {k}: attempts {summ['n_attempts']}, re-emerge {summ['reemerge']:.2f}, non-Y "
                            f"{summ['n_nonY']} {summ['landing']}, pass {summ['pass_rate']:.2f}, vetoed occurrences "
                            f"{summ['vetoed_ngram_occurrences']}")
            if not nxt:
                break
            reqs = []
            for k in nxt:
                reqs += arm_requests(design, pid, k, "veto", rnd=r + 1, veto=masks[k], prompt_arm="copy")
            logger.info(f"veto round {r + 1}: {len(nxt)} Y re-emerged >= {REEMERGE_MIN}: {nxt}")
            run_staged(eng, reqs, pool, f"stage1_round{r + 1}", budget)
            pool.wait()
            labs = combined_labels()
            active = nxt
        pool.shutdown()
    write_json(RESULTS / "stage1_scaling.json", budget)
    _write_commit2_inputs(design, keys, prio, rounds, labs, eng.tok)


def _write_commit2_inputs(design: dict, keys: list[str], prio: dict, rounds: dict, labs: dict, tok) -> None:
    gens = read_jsonl(GEN_PATH)
    sub, vr, cp = {}, {}, {}
    for k in keys:
        tk, yk = k.split(":")
        surv = survivors_of(design, k)
        dflt = design["elig"]["tasks"][tk]["default"]
        rr = rounds[k]
        last = max(rr)
        used = next((r for r in sorted(rr, reverse=True) if rr[r]["n_nonY"] >= MIN_NONY_SUBTRACT), None)
        not_surface = rr[last]["reemerge"] >= REEMERGE_MIN and last == MAX_ROUNDS
        if used is None:
            sub[k] = {"distribution": None, "undefined": True, "round_used": None, "n_nonY": 0,
                      "not_carried_by_surface_tokens": not_surface}
        else:
            land = rr[used]["landing"]
            n = sum(land.values())
            sub[k] = {"distribution": {lab: c / n for lab, c in land.items()}, "counts": land, "undefined": False,
                      "round_used": used, "n_nonY": n, "not_carried_by_surface_tokens": not_surface}
        vr[k] = {"rounds": {str(r): v for r, v in rr.items()}, "n_rounds": len(rr), "last_round": last,
                 "round_used": used, "final_mask_text": rr[last]["mask_text"]}
        rows = [g for g in gens if g["arm"] == "copy" and g["task"] == tk and g["Y"] == yk]
        s = round_summary(rows, labs, yk, surv, dflt, [])
        s["copy_rate"] = s["reemerge"]  # Y share among COPY-twin attempts
        s["copy_rate_ci95"] = wilson(s["n_Y"], s["n_attempts"])
        s.pop("vetoed_ngram_occurrences", None)
        cp[k] = s
    base = {}
    for t in TASK_ORDER:
        rows = [g for g in gens if g["arm"] == "baseline" and g["task"] == t]
        lab = [labs[g["sample_id"]]["label"] for g in rows if g["sample_id"] in labs]
        att = [x for x in lab if x != "invalid"]
        dflt = design["elig"]["tasks"][t]["default"]
        share = (sum(1 for x in att if x == dflt) / len(att)) if att else float("nan")
        base[t] = {"default_fp8_pilot": dflt, "n": len(rows), "label_counts": dict(Counter(lab)), "default_share": share,
                   "default_share_ci95": wilson(sum(1 for x in att if x == dflt), len(att)), "flag_below_0.8": share < 0.8}
        if share < 0.8:
            deviation(f"bf16 baseline check: {t} default share {share:.2f} < 0.8")
    tm = read_json(RESULTS / "timings.json")
    gpu_used = tm.get("stage1_gpu", {}).get("gpu_s", 0.0)
    write_json(PRED / "subtract_in_context.json", sub)
    write_json(PRED / "veto_rounds.json", vr)
    write_json(PRED / "copy_twin_summary.json", cp)
    write_json(PRED / "bf16_baseline_check.json", base)
    write_json(PRED / "optional_template_arm.json", {
        "planned": True, "condition": "runs after the NAMED and UNNAMED arms only if >= 45 min of the 2-GPU-hour sampling "
                                      "budget remains; descriptive template sensitivity only, never enters C1",
        "templates": TEMPLATES_W1_W4, "n_per_template_per_priority_Y": 10, "allocation": "10 split evenly over |S_Y|",
        "gpu_seconds_used_by_stage1": gpu_used})
    n_def = sum(1 for v in sub.values() if v["undefined"])
    logger.info(f"SUBTRACT-IN-CONTEXT written for {len(sub)} Y ({n_def} undefined); copy rates "
                f"{ {k: round(v['reemerge'], 2) for k, v in cp.items()} }")


def stage2(args) -> None:
    from bench_copy.common.commit import verify_chain
    log = read_jsonl(COMMIT_LOG)
    c2 = [r for r in log if r["kind"] == "COMMIT2"]
    if not c2 or not verify_chain(COMMIT_LOG):
        raise RuntimeError("COMMIT #2 missing or chain broken: no ban sample may be drawn")
    logger.info(f"COMMIT #2 present ({c2[-1]['ts']}); chain verifies; drawing ban samples")
    design = load_design()
    keys = ordered_keys(design)
    prio = priority_of(design)
    budget = {}
    with Timer("stage2_gpu", gpu=True):
        eng = Engine(args.max_num_seqs, args.gpu_util)
        pid = PromptIds(eng.tok)
        pool = LabelPool(LABELS_RAW, workers=args.label_workers)
        reqs = []
        for k in keys:
            reqs += arm_requests(design, pid, k, "named")
            reqs += arm_requests(design, pid, k, "unnamed")
        t0 = time.time()
        run_staged(eng, reqs, pool, "stage2_main", budget)
        main_s = time.time() - t0
        tm = read_json(RESULTS / "timings.json")
        used = tm.get("stage1_gpu", {}).get("gpu_s", 0.0) + main_s + eng.load_seconds
        left = GPU_BUDGET_S - used
        plan = read_json(PRED / "optional_template_arm.json")
        run_tpl = plan.get("planned") and left >= TEMPLATE_ARM_MIN_LEFT_S and not args.no_template_arm
        logger.info(f"GPU used so far {used / 60:.1f} min; {left / 60:.1f} min of the 2 h budget left -> template arm "
                    f"{'RUNS' if run_tpl else 'skipped'}")
        budget["template_arm"] = {"gpu_used_s": used, "left_s": left, "run": bool(run_tpl)}
        if run_tpl:
            reqs = []
            for k in keys:
                if not prio[k]:
                    continue
                n_s = len(design["shown"][k])
                per = allocation(n_s, 10)
                for w in TEMPLATES_W1_W4:
                    for p, n_p in zip(design["shown"][k], per):
                        rr = arm_requests(design, pid, k, w, per_program=n_p)
                        reqs += [q for q in rr if q["p_index"] == p["p_index"]]
            run_staged(eng, reqs, pool, "stage2_templates", budget)
        logger.info(f"stage 2 generated; waiting for {pool.pending()} labels")
        pool.shutdown()
        combined_labels()
    write_json(RESULTS / "stage2_scaling.json", budget)
