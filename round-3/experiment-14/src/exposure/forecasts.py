"""Plan step 0 (CPU, before any generation): bench copy + sha256 verification, labeller re-check, defaults,
eligibility + ASSOCIATE, shown-program pools, distinctive n-grams + shown sets, allocation, PROXIMITY (Zhang-Shasha on
identifier-normalised ASTs; token-distance sensitivity), LADDER and every rendered prompt."""

from __future__ import annotations

import io
import multiprocessing as mp
import random
import shutil
import statistics
import tokenize
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

from loguru import logger

from . import ngram as NG
from .core import (BENCH, COVETO_SHARE, DATA, EXP11, INTRO, LOGS, MAX_MODEL_LEN, MAX_NEW_TOKENS, MAX_SHOWN,
                   MAX_SHOWN_TOKENS, N_PER_ARM, NGRAM_MAX, NL, PRED, PRESENCE_MIN, RESULTS, ROOT, SHUFFLE_SEED,
                   TASK_ORDER, TEMPLATES_W1_W4, WORDINGS, canon_json, deviation, ensure_bench_importable, fenced,
                   load_spec, read_json, read_jsonl, sha256_file, sha256_text, task_dir, write_json)

ensure_bench_importable()

INPUTS = ROOT / "inputs"
THINK_SUFFIX = "<|im_start|>assistant\n<think>\n\n</think>\n\n"


# ----------------------------------------------------------------------------------------------- 0.2 copy + verify
def copy_and_verify() -> dict:
    if not (EXP11 / "bench" / "commitment.json").exists():
        raise FileNotFoundError(f"exp11 bench not readable at {EXP11} (F8: stop before any sampling)")
    if BENCH.exists():
        shutil.rmtree(BENCH)
    shutil.copytree(EXP11 / "bench", BENCH, ignore=shutil.ignore_patterns("__pycache__"))
    INPUTS.mkdir(exist_ok=True)
    for src, dst in [("results/stageA_nominations.json", "exp11_stageA_nominations.json"),
                     ("commitments.log", "exp11_commitments.log"), ("results/gate_summary.json", "exp11_gate_summary.json"),
                     ("results/frozen_tasks.json", "exp11_frozen_tasks.json")]:
        shutil.copy2(EXP11 / src, INPUTS / dst)
    DATA.mkdir(exist_ok=True)
    jc = DATA / "judge_cache.jsonl"
    if not jc.exists():
        shutil.copy2(EXP11 / "data" / "judge_cache.jsonl", jc)
        shutil.copy2(EXP11 / "data" / "judge_cache.jsonl", INPUTS / "exp11_judge_cache.jsonl")
    doc = read_json(BENCH / "commitment.json")
    mism, checked = [], 0
    for t in TASK_ORDER:
        v = doc["tasks"][t]
        d = task_dir(t)
        for f, h in v["files"].items():
            got = sha256_text(canon_json(read_json(d / "spec.json")["catalogue"])) if f == "catalogue" else sha256_file(d / f)
            checked += 1
            if got != h:
                mism.append(f"{t}:{f}")
        if sha256_text(canon_json(v["files"])) != v["task_sha256"]:
            mism.append(f"{t}:task_sha256")
    combined = sha256_text("".join(doc["tasks"][t]["task_sha256"] for t in sorted(doc["tasks"])))
    if combined != doc.get("combined_sha256"):
        mism.append("combined_sha256")
    from bench_copy.common.commit import verify_chain
    exp11_chain_ok = verify_chain(INPUTS / "exp11_commitments.log")
    freeze_line = [l for l in read_jsonl(INPUTS / "exp11_commitments.log") if l["kind"] == "bench_freeze"]
    freeze_ok = bool(freeze_line) and freeze_line[-1]["sha256"] == combined
    if set(doc["tasks"]) != set(TASK_ORDER):
        mism.append(f"task set {sorted(doc['tasks'])} != frozen 12")
    # inputs the commitment does not list -> hashed into COMMIT #0
    extra = {}
    for t in TASK_ORDER:
        d = task_dir(t)
        for f in ["forced_programs.jsonl", "pilot_rows.jsonl", "association.jsonl"]:
            extra[f"{t}/{f}"] = sha256_file(d / f)
    extra["exp11/data/judge_cache.jsonl"] = sha256_file(INPUTS / "exp11_judge_cache.jsonl") if (INPUTS / "exp11_judge_cache.jsonl").exists() else sha256_file(EXP11 / "data" / "judge_cache.jsonl")
    extra["exp11/results/stageA_nominations.json"] = sha256_file(INPUTS / "exp11_stageA_nominations.json")
    out = {"n_files_checked": checked, "mismatches": mism, "combined_sha256": combined, "exp11_chain_ok": exp11_chain_ok,
           "exp11_bench_freeze_line_matches": freeze_ok, "uncommitted_input_sha256": extra}
    write_json(RESULTS / "bench_verification.json", out)
    if mism or not exp11_chain_ok or not freeze_ok:
        raise RuntimeError(f"bench verification failed: {out['mismatches']} chain={exp11_chain_ok} freeze={freeze_ok}")
    logger.info(f"bench verified: {checked} committed hashes over 12 tasks, combined {combined[:12]}..., chain ok")
    return out


# ------------------------------------------------------------------------------------------ 0.3 labeller re-check
def labeller_recheck(workers: int) -> dict:
    from bench_copy.common.stats import cohen_kappa
    from .labels import label_many
    rows = []
    for t in TASK_ORDER:
        d = task_dir(t)
        for g in read_jsonl(d / "gold_set.jsonl"):
            rows.append({"task": t, "condition": "recheck", "sample_id": f"{t}:gold:{g['gold_id']}", "seed": 0,
                         "text": fenced(g["code"]), "_gold": g})
        for rf in sorted((d / "references").glob("*.py")):
            rows.append({"task": t, "condition": "recheck", "sample_id": f"{t}:ref:{rf.stem}", "seed": 0,
                         "text": fenced(rf.read_text()), "_mode": rf.stem})
    logger.info(f"labeller re-check: {len(rows)} programs (gold rows + references)")
    labs = label_many(rows, workers)
    per = {}
    for t in TASK_ORDER:
        gate = read_json(task_dir(t) / "gate.json")
        g_rows = [(r, l) for r, l in zip(rows, labs) if r["task"] == t and "_gold" in r]
        f_rows = [(r, l) for r, l in zip(rows, labs) if r["task"] == t and "_mode" in r]
        rt = [l["runtime_label"] for _, l in g_rows]
        ast_ = [l["ast_label"] for _, l in g_rows]
        adj = [r["_gold"]["adjudicated"] for r, _ in g_rows]
        rva = sum(a == b for a, b in zip(rt, adj)) / max(len(g_rows), 1)
        kap = cohen_kappa(rt, ast_)
        stored_rt = sum(l["runtime_label"] == r["_gold"]["runtime"] for r, l in g_rows) / max(len(g_rows), 1)
        stored_ast = sum(l["ast_label"] == r["_gold"]["ast"] for r, l in g_rows) / max(len(g_rows), 1)
        ref_rt = sum(l["runtime_label"] == r["_mode"] for r, l in f_rows) / max(len(f_rows), 1)
        ref_ast = sum(l["ast_label"] == r["_mode"] for r, l in f_rows) / max(len(f_rows), 1)
        ref_pass = sum(bool(l.get("passed")) for _, l in f_rows) / max(len(f_rows), 1)
        g0 = gate["gold"]
        flag = (rva < g0["runtime_vs_adjudicated"] - 0.05) or (kap < g0["kappa_runtime_ast"] - 0.05) or ref_rt < 1.0 \
            or ref_ast < 1.0
        per[t] = {"n_gold": len(g_rows), "runtime_vs_adjudicated": rva, "gate_runtime_vs_adjudicated": g0["runtime_vs_adjudicated"],
                  "kappa_runtime_ast": kap, "gate_kappa_runtime_ast": g0["kappa_runtime_ast"],
                  "fresh_vs_stored_runtime": stored_rt, "fresh_vs_stored_ast": stored_ast,
                  "n_refs": len(f_rows), "ref_acc_runtime": ref_rt, "ref_acc_ast": ref_ast, "ref_pass_rate": ref_pass,
                  "flag": bool(flag),
                  "mismatches": [{"id": r["sample_id"], "runtime": l["runtime_label"], "ast": l["ast_label"],
                                  "expected": r.get("_mode") or r["_gold"]["adjudicated"]} for r, l in g_rows + f_rows
                                 if l["runtime_label"] != (r.get("_mode") or r["_gold"]["adjudicated"])]}
        logger.info(f"  {t}: runtime-vs-adjudicated {rva:.3f} (gate {g0['runtime_vs_adjudicated']:.3f}), kappa "
                    f"{kap:.3f} (gate {g0['kappa_runtime_ast']:.3f}), refs runtime {ref_rt:.2f} AST {ref_ast:.2f} "
                    f"pass {ref_pass:.2f}{'  FLAG' if flag else ''}")
    write_json(RESULTS / "labeller_recheck.json", per)
    return per


# ------------------------------------------------------------------------------- 0.4 / 0.5 defaults + eligibility
def defaults_and_eligibility() -> dict:
    stage_a = read_json(INPUTS / "exp11_stageA_nominations.json")["table"]
    tasks, eligible = {}, []
    for t in TASK_ORDER:
        spec = load_spec(t)
        modes = [c["mode"] for c in spec["catalogue"]]
        pilot = read_jsonl(task_dir(t) / "pilot_rows.jsonl")
        pc = Counter(r["label"] for r in pilot)
        top = pc.most_common()
        dflt = top[0][0]
        if len(top) > 1 and top[1][1] == top[0][1]:
            deviation(f"{t}: tie for the modal pilot label {top[:2]}; first in Counter order taken")
        forced = read_jsonl(task_dir(t) / "forced_programs.jsonl")
        assoc = read_jsonl(task_dir(t) / "association.jsonl")
        tasks[t] = {"default": dflt, "pilot_counts": dict(pc), "pilot_modal_share": top[0][1] / len(pilot),
                    "modes": modes, "display_names": {c["mode"]: c["display_name"] for c in spec["catalogue"]}}
        for y in modes:
            if y == dflt:
                continue
            r_y = [r for r in forced if r["forced_mode"] == y and r["label"] == y and r["passed"]]
            ac = Counter(a["mapped"] for a in assoc if a["X"] == y and a["category"] == "survivor")
            mx = max(ac.values()) if ac else 0
            atop = sorted(k for k, v in ac.items() if v == mx) if ac else []
            st = stage_a[t]["events"].get(y, {}).get("association", {}).get("raw_counts", {})
            smx = max(st.values()) if st else 0
            stop_ = sorted(k for k, v in st.items() if v == smx)
            rec = {"task": t, "Y": y, "default": dflt, "n_R": len(r_y), "eligible": len(r_y) >= 1,
                   "associate": {k: 1.0 / len(atop) for k in atop}, "associate_counts": dict(ac),
                   "associate_tie": len(atop) > 1, "associate_crosscheck_stageA": stop_ == atop,
                   "priority": bool(atop) and atop != [dflt],
                   "n_assoc_answers": sum(1 for a in assoc if a["X"] == y),
                   "n_forced": sum(1 for r in forced if r["forced_mode"] == y),
                   "forced_adherence": (sum(1 for r in forced if r["forced_mode"] == y and r["label"] == y) /
                                        max(1, sum(1 for r in forced if r["forced_mode"] == y)))}
            if not rec["associate_crosscheck_stageA"]:
                deviation(f"{t}/{y}: ASSOCIATE recount {atop} differs from stageA_nominations {stop_}")
            if rec["eligible"]:
                eligible.append(rec)
            tasks[t].setdefault("ineligible", [])
            if not rec["eligible"]:
                tasks[t]["ineligible"].append(y)
    n_pr = sum(r["priority"] for r in eligible)
    logger.info(f"eligibility: {len(eligible)} eligible Y, {n_pr} priority (plan expects 33 / 19)")
    if (len(eligible), n_pr) != (33, 19):
        deviation(f"eligibility recount {len(eligible)}/{n_pr} differs from the plan's 33/19; the recount is used")
    return {"tasks": tasks, "eligible": eligible, "n_eligible": len(eligible), "n_priority": n_pr}


def ordered_eligible(elig: dict) -> list[dict]:
    """Sampling order: priority Y first in Stage-A task order, then non-priority Y (catalogue order within task)."""
    pri = [e for t in TASK_ORDER for e in elig["eligible"] if e["task"] == t and e["priority"]]
    non = [e for t in TASK_ORDER for e in elig["eligible"] if e["task"] == t and not e["priority"]]
    return pri + non


# ----------------------------------------------------------------------------------------- 0.6 shown-program pool
def _strip_comments(code: str) -> str | None:
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    lines = code.split("\n")
    for tk in sorted((t for t in toks if t.type == tokenize.COMMENT), key=lambda t: (t.start[0], -t.start[1])):
        r, c0 = tk.start
        lines[r - 1] = lines[r - 1][:c0].rstrip()
    return "\n".join(l for l in lines)


def shown_pools(elig: dict, tok, workers: int) -> dict:
    from bench_copy.common.canon import canon_tokens
    from bench_copy.common.harness import extract_code
    from bench_copy.common.scrub import scrub_code, text_has_alias
    from .labels import combine, label_many
    items = []
    for e in elig["eligible"]:
        forced = read_jsonl(task_dir(e["task"]) / "forced_programs.jsonl")
        r_y = [r for r in forced if r["forced_mode"] == e["Y"] and r["label"] == e["Y"] and r["passed"]]
        for r in r_y:
            s_code, info = scrub_code(r["code"])
            items.append({"task": e["task"], "Y": e["Y"], "src": r, "scrubbed": s_code.rstrip() + "\n",
                          "scrub_ok": info["ok"], "renamed": info["renamed"], "unscrubbed": False})
    rows = [{"task": it["task"], "condition": "shown_check", "sample_id": f"pool:{it['src']['sample_id']}", "seed": 0,
             "text": fenced(it["scrubbed"])} for it in items if it["scrub_ok"]]
    logger.info(f"shown-pool check: {len(rows)} scrubbed programs (tests + labellers)")
    labs = label_many(rows, workers)
    comb = combine(labs, {r["sample_id"]: extract_code(r["text"]) for r in rows}, {r["sample_id"]: r["task"] for r in rows})
    by_id = {c["sample_id"]: c for c in comb}
    pools = {}
    for e in elig["eligible"]:
        key = f"{e['task']}:{e['Y']}"
        cand = [it for it in items if it["task"] == e["task"] and it["Y"] == e["Y"]]
        kept, seen, drops = [], set(), Counter()
        for it in cand:
            if not it["scrub_ok"]:
                drops["scrub_failed"] += 1
                continue
            c = by_id[f"pool:{it['src']['sample_id']}"]
            if not c.get("valid"):
                drops["invalid"] += 1
                continue
            if not c.get("passed"):
                drops["fails_tests"] += 1
                continue
            if c["label"] != e["Y"]:
                drops[f"relabelled_{c['label']}"] += 1
                continue
            h = sha256_text("\x1f".join(canon_tokens(it["scrubbed"])))
            if h in seen:
                drops["duplicate"] += 1
                continue
            n_tok = len(tok(fenced(it["scrubbed"]), add_special_tokens=False)["input_ids"])
            if n_tok > MAX_SHOWN_TOKENS:
                drops["too_long"] += 1
                continue
            seen.add(h)
            kept.append({"code": it["scrubbed"], "code_sha256": sha256_text(it["scrubbed"]), "canon_sha256": h,
                         "src_sample_id": it["src"]["sample_id"], "src_code": it["src"]["code"], "n_tokens": n_tok,
                         "renamed": it["renamed"], "labeller_source": c["labeller_source"], "unscrubbed": False})
        if not kept:  # F4 fallback: comments-stripped unscrubbed program when it names no alias
            for it in cand:
                s = _strip_comments(it["src"]["code"])
                if s and not text_has_alias(s):
                    lab = combine(label_many([{"task": e["task"], "condition": "shown_check",
                                               "sample_id": f"pool_unscrubbed:{it['src']['sample_id']}", "seed": 0,
                                               "text": fenced(s)}], 1),
                                  {f"pool_unscrubbed:{it['src']['sample_id']}": s},
                                  {f"pool_unscrubbed:{it['src']['sample_id']}": e["task"]})[0]
                    if lab.get("passed") and lab["label"] == e["Y"]:
                        kept.append({"code": s.rstrip() + "\n", "code_sha256": sha256_text(s.rstrip() + "\n"),
                                     "canon_sha256": None, "src_sample_id": it["src"]["sample_id"],
                                     "src_code": it["src"]["code"], "n_tokens": None, "renamed": {},
                                     "labeller_source": lab["labeller_source"], "unscrubbed": True})
                        deviation(f"{key}: no scrubbed program survived; F4 unscrubbed fallback used")
                        break
        pools[key] = {"kept": kept, "n_R": len(cand), "drops": dict(drops)}
        logger.info(f"  pool {key}: |R_Y|={len(cand)} -> |P_Y|={len(kept)} drops={dict(drops)}")
    return pools


# ------------------------------------------------------------------------------ 0.7 distinctive n-gram + shown set
def _ids(tok, code: str) -> list[int]:
    return tok(fenced(code), add_special_tokens=False)["input_ids"]


def task_groups(t: str, tok) -> dict:
    """Tokenised n-gram sets of every forced program (label == forced_mode) per mode and of the 50 pilot programs."""
    forced = read_jsonl(task_dir(t) / "forced_programs.jsonl")
    pilot = read_jsonl(task_dir(t) / "pilot_rows.jsonl")
    by_mode, by_mode_correct = defaultdict(list), defaultdict(list)
    for r in forced:
        if r.get("code") and r["label"] == r["forced_mode"]:
            s = NG.ngram_set(_ids(tok, r["code"]), NGRAM_MAX)
            by_mode[r["forced_mode"]].append(s)
            if r["passed"]:
                by_mode_correct[r["forced_mode"]].append(s)
    pilot_sets = [NG.ngram_set(_ids(tok, r["code"]), NGRAM_MAX) for r in pilot if r.get("code")]
    return {"by_mode": by_mode, "by_mode_correct": by_mode_correct, "pilot": pilot_sets}


def ngrams_and_shown(elig: dict, pools: dict, tok) -> tuple[dict, dict]:
    ngrams, shown = {}, {}
    for t in TASK_ORDER:
        es = [e for e in elig["eligible"] if e["task"] == t]
        if not es:
            continue
        tg = task_groups(t, tok)
        dflt = elig["tasks"][t]["default"]
        forced = read_jsonl(task_dir(t) / "forced_programs.jsonl")
        for e in es:
            y, key = e["Y"], f"{t}:{e['Y']}"
            r_y = [r for r in forced if r["forced_mode"] == y and r["label"] == y and r["passed"]]
            ref_sets = [NG.ngram_set(_ids(tok, r["code"]), NGRAM_MAX) for r in r_y]
            groups = {f"forced:{j}": tg["by_mode"][j] for j in elig["tasks"][t]["modes"] if j != y and tg["by_mode"][j]}
            groups["pilot_default"] = tg["pilot"]
            groups_c = {f"forced:{j}": tg["by_mode_correct"][j] for j in elig["tasks"][t]["modes"]
                        if j != y and tg["by_mode_correct"][j]}
            groups_c["pilot_default"] = tg["pilot"]
            pool = pools[key]["kept"]
            shown_sets = [NG.ngram_set(_ids(tok, p["code"]), NGRAM_MAX) for p in pool]
            sel = NG.select_distinctive(ref_sets, groups, shown_sets if pool else None, presence_min=PRESENCE_MIN,
                                        coveto_share=COVETO_SHARE, groups_correct=groups_c)
            if not pool or sel is None or sel.get("ids") is None:
                deviation(f"{key}: no usable shown pool or n-gram; Y dropped from the experiment")
                continue
            g = tuple(sel["ids"])
            p_g = [p for p, s in zip(pool, shown_sets) if g in s]
            order = sorted(p_g, key=lambda p: p["code_sha256"])
            random.Random(f"{SHUFFLE_SEED}:{key}:shown").shuffle(order)
            s_y = order[:MAX_SHOWN]
            assoc = list(e["associate"])
            sel.update({"task": t, "Y": y, "decoded": tok.decode(list(g)), "tokens": [tok.decode([i]) for i in g],
                        "default_coveto": f"forced:{dflt}" in sel["coveto_groups"] or "pilot_default" in sel["coveto_groups"],
                        "associate_coveto": any(f"forced:{a}" in sel["coveto_groups"] for a in assoc),
                        "n_ref_lt5": len(r_y) < 5, "n_pool": len(pool), "n_pool_with_g": len(p_g),
                        "n_shown": len(s_y), "coveto_modes": sorted({c.split(":", 1)[1] for c in sel["coveto_groups"]
                                                                     if c.startswith("forced:")} |
                                                                    ({dflt} if "pilot_default" in sel["coveto_groups"] else set()))})
            ngrams[key] = sel
            shown[key] = [{"p_index": i, **p} for i, p in enumerate(s_y)]
            logger.info(f"  n-gram {key}: g*={sel['decoded']!r} n={sel['n']} presence={sel['presence']:.2f} "
                        f"collateral={sel['collateral']:.2f} co-veto={sel['coveto_modes']} |S_Y|={len(s_y)}")
    return ngrams, shown


# ------------------------------------------------------------------------------------------------- 0.8 allocation
def allocation(k: int, n: int = N_PER_ARM) -> list[int]:
    base, rem = divmod(n, k)
    return [base + (1 if i < rem else 0) for i in range(k)]


# -------------------------------------------------------------------------------------------------- 0.9 proximity
def proximity(elig: dict, shown: dict, alloc: dict, workers: int, cap_refs: int = 20) -> dict:
    from bench_copy.common.canon import canon_tokens, token_distance
    from .astdist import pair_distance
    refs, jobs = {}, {}
    for t in TASK_ORDER:
        forced = read_jsonl(task_dir(t) / "forced_programs.jsonl")
        for j in elig["tasks"][t]["modes"]:
            cand = sorted([r for r in forced if r["forced_mode"] == j and r["label"] == j and r["passed"] and r.get("code")],
                          key=lambda r: r["code_sha256"])
            random.Random(f"{SHUFFLE_SEED}:{t}:{j}:prox").shuffle(cand)
            refs[(t, j)] = cand[:cap_refs]
    for key, s_y in shown.items():
        t, y = key.split(":")
        for p in s_y:
            for j in elig["tasks"][t]["modes"]:
                if j == y:
                    continue
                for r in refs[(t, j)]:
                    k = f"{p['code_sha256']}|{r['code_sha256']}"
                    jobs[k] = (k, p["code"], r["code"])
    logger.info(f"proximity: {len(jobs)} unique Zhang-Shasha pairs on {workers} processes")
    dist = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as ex:
        for i, (k, d) in enumerate(ex.map(pair_distance, list(jobs.values()), chunksize=8)):
            dist[k] = d
            if (i + 1) % 2000 == 0:
                logger.info(f"  {i + 1}/{len(jobs)} pairs")
    out = {}
    canon_cache: dict[str, list[str]] = {}

    def ct(code: str) -> list[str]:
        if code not in canon_cache:
            canon_cache[code] = canon_tokens(code)
        return canon_cache[code]

    for key, s_y in shown.items():
        t, y = key.split(":")
        per_p, mix, mix_tok = [], Counter(), Counter()
        for p, n_p in zip(s_y, alloc[key]):
            med, med_tok = {}, {}
            for j in elig["tasks"][t]["modes"]:
                if j == y or not refs[(t, j)]:
                    continue
                ds = [dist[f"{p['code_sha256']}|{r['code_sha256']}"] for r in refs[(t, j)]]
                ds = [d for d in ds if d is not None]
                if ds:
                    med[j] = statistics.median(ds)
                med_tok[j] = statistics.median(token_distance(ct(p["code"]), ct(r["code"])) for r in refs[(t, j)])
            best = min(med.values())
            near = sorted(j for j, v in med.items() if v == best)
            best_t = min(med_tok.values())
            near_t = sorted(j for j, v in med_tok.items() if v == best_t)
            for j in near:
                mix[j] += n_p / N_PER_ARM / len(near)
            for j in near_t:
                mix_tok[j] += n_p / N_PER_ARM / len(near_t)
            per_p.append({"p_index": p["p_index"], "code_sha256": p["code_sha256"], "weight": n_p / N_PER_ARM,
                          "median_zss": med, "nearest": near, "median_token_distance": med_tok, "nearest_token": near_t})
        no_ref = [j for j in elig["tasks"][t]["modes"] if j != y and not refs[(t, j)]]
        out[key] = {"distribution": dict(mix), "distribution_token_distance": dict(mix_tok), "per_program": per_p,
                    "survivors_without_reference": no_ref,
                    "n_refs": {j: len(refs[(t, j)]) for j in elig["tasks"][t]["modes"] if j != y}}
        logger.info(f"  PROXIMITY {key}: {dict(mix)} (token-distance sensitivity {dict(mix_tok)})")
    return out


# ------------------------------------------------------------------------------------------------- 0.12 prompts
def user_text(task: str, code: str, wording: str) -> str:
    from bench_copy.common.prompts import spec_text
    return INTRO + NL + NL + fenced(code) + NL + NL + wording + NL + NL + spec_text(task)


def wording_for(arm: str, task: str, y: str) -> str:
    from bench_copy.common.catalogue import display_name
    if arm in WORDINGS:
        return WORDINGS[arm].format(x=display_name(task, y))
    w = TEMPLATES_W1_W4[arm].format(x=display_name(task, y))
    return w[:1].upper() + w[1:]


def render_prompts(tok, shown: dict) -> list[dict]:
    from bench_copy.common.prompts import render_chat, spec_text
    recs = []

    def add(key: str, task: str, y: str | None, arm: str, p_index: int | None, ut: str) -> None:
        chat = render_chat(tok, ut)
        assert chat.endswith(THINK_SUFFIX), f"bad chat rendering for {key}: {chat[-80:]!r}"
        ids = tok(chat, add_special_tokens=False)["input_ids"]
        recs.append({"prompt_key": key, "task": task, "Y": y, "arm": arm, "p_index": p_index, "user_text": ut,
                     "chat_sha256": sha256_text(chat), "n_prompt_tokens": len(ids),
                     "max_tokens": min(MAX_NEW_TOKENS, MAX_MODEL_LEN - len(ids))})

    for key, s_y in shown.items():
        t, y = key.split(":")
        for p in s_y:
            for arm in ["copy", "named", "unnamed", "W1", "W2", "W3", "W4"]:
                add(f"{t}:{y}:{arm}:p{p['p_index']}", t, y, arm, p["p_index"], user_text(t, p["code"], wording_for(arm, t, y)))
    for t in TASK_ORDER:
        add(f"{t}:baseline", t, None, "baseline", None, spec_text(t))
    mx = max(r["n_prompt_tokens"] for r in recs)
    logger.info(f"rendered {len(recs)} prompts; max prompt length {mx} tokens")
    return recs
