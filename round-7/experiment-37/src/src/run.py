#!/usr/bin/env python3
"""GPU stages.

calib : instruct model. ENGINE CHECK (B0 twin, N=20 per task, non-decisive), CALIBRATION POOL (forced 'Implement Y',
        30 children per catalogue mode per task) and the THROUGHPUT pilot (64-prompt S-shaped batch, 64-prompt B0
        batch on T03).
base  : Qwen3-8B-Base BINT intents for every task (after commit #1), then the process exits (one 8B model at a time).
run   : instruct model. Per task (T03, T2, then A3 if the ladder includes it): EAP stage 1 in one batch, then rounds:
        each engine call = the S round's 12 prompts (4 islands x 3 prompts x 4 children) + the next slice of the
        precomputed i.i.d. queue (NE, I0, EAP stage 2, BINT code stage, B0). S children are evaluated in the CPU pool
        while the GPU generates the next round (one-round lag); the archive updates after each round.
Rows: data/rows_<task>.jsonl (one per child), raw prompts/outputs data/raw/<arm>_<task>.jsonl, search state
data/search_state_<task>.json, archive snapshots results/archive_<task>.json.
"""

from __future__ import annotations

import gc
import random
import time
from collections import Counter, defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from loguru import logger

from common import (DATA, MAX_TOKENS, MODEL_ID, PRED, RAW, RESULTS, TASKS, append_jsonl, read_json, read_jsonl,
                    sha256_text, stable_seed, utc_now, write_json, write_jsonl)
from critic import Critic
from engine import Req, VLLMEngine
from inputs import load_task
from labels import ds_signature, mech_label
from prompts import (EAP_B, INTENT_PREFIX, W_TEMPLATES, b0_user_text, cal_user_text, eap_stage1_text, i0_user_text,
                     idea_of, ifg_text, parsers, s_user_text)
from sandbox import evaluate, extract_code
from search import CHILDREN_PER_PROMPT, N_ISLANDS, PROMPTS_PER_ISLAND, FrozenSeedPool, SearchDB, cell_key

EVAL_WORKERS = 8
GPU_NAME = "NVIDIA RTX A4500"
ROUND_CHILDREN_S = N_ISLANDS * PROMPTS_PER_ISLAND * CHILDREN_PER_PROMPT  # 48


def rows_path(task: str):
    return DATA / f"rows_{task}.jsonl"


def sample10(code: str | None) -> bool:
    return bool(code) and int(sha256_text(code)[:8], 16) % 10 == 0


# ------------------------------------------------------------------------------------------------ evaluation
class Evaluator:
    def __init__(self, task_objs: dict[str, dict[str, Any]], critic: Critic, workers: int = EVAL_WORKERS) -> None:
        self.objs = task_objs
        self.critic = critic
        self.pool = ThreadPoolExecutor(workers)
        self.bg = ThreadPoolExecutor(1)

    def _one(self, task: str, code: str | None) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
        ev = evaluate(self.objs[task], code)
        lab = None
        if code and ev["valid"] and (ev["correct"] or sample10(code)):
            lab = mech_label(task, code)
        ds = ds_signature(code) if code and ev["valid"] else None
        return ev, lab, ds

    def eval_many(self, task: str, codes: list[str | None], exclude_self: bool = False) -> list[dict[str, Any]]:
        res = list(self.pool.map(lambda c: self._one(task, c), codes))
        out = []
        corr = [i for i, (ev, _, _) in enumerate(res) if ev["correct"]]
        scores = self.critic.score([codes[i] for i in corr], exclude_self=exclude_self) if corr else []
        sc = dict(zip(corr, scores))
        for i, (ev, lab, ds) in enumerate(res):
            r = {"eval": ev, "lab": lab, "ds_signature": ds, "critic": sc.get(i)}
            out.append(r)
        return out

    def submit(self, task: str, codes: list[str | None]) -> Future:
        return self.bg.submit(self.eval_many, task, codes)


def child_row(task: str, arm: str, idx: int, req_rec: dict[str, Any], kid: dict[str, Any], r: dict[str, Any],
              meta: dict[str, Any], gpu_s: float) -> dict[str, Any]:
    code = extract_code(kid["text"])
    ev, lab, cr = r["eval"], r["lab"], r["critic"]
    rl = lab["runtime_label"] if lab else None
    row = {"id": f"{task}|{arm}|{idx}", "model": meta.get("model", MODEL_ID), "task": task, "arm": arm, "slot": idx,
           "site": None, "layer": None, "rank_k": None, "lambda": None, "alpha": None, "direction_seed": None,
           "template": meta.get("template"), "noun": None, "temperature": meta.get("temperature", 1.0), "top_k": None,
           "top_p": 1.0, "precision": meta.get("precision", "bf16"), "gpu": meta.get("gpu", GPU_NAME),
           "prompt_sha256": req_rec["prompt_sha256"], "seed": meta.get("seed"), "round": meta.get("round"),
           "island": meta.get("island"), "parent_ids": meta.get("parent_ids"), "depth": meta.get("depth"),
           "prompt_source": meta.get("prompt_source"), "n_new_tokens": kid.get("n_new_tokens"),
           "finish_reason": kid.get("finish_reason"), "n_prompt_tokens": req_rec.get("n_prompt_tokens"),
           "has_code": code is not None, "code": code, "code_sha256": sha256_text(code) if code else None,
           "valid": ev["valid"], "prescreen": ev["prescreen"], "stage1": ev["stage1"], "stage2": ev["stage2"],
           "stress_pass": ev["stress_pass"], "passed": ev["correct"], "correct": ev["correct"],
           "first_fail": ev["first_fail"], "median_case_ms": ev["median_case_ms"], "runtime_ratio": ev["runtime_ratio"],
           "runtime_label": rl, "ast_label": lab["ast_label"] if lab else None, "regate": lab.get("regate") if lab else None,
           "trace_error": lab.get("trace_error") if lab else None, "ds_signature": r["ds_signature"],
           "cell": cell_key(rl, r["ds_signature"]) if ev["correct"] else None,
           "idea": idea_of(code) if code else None,
           "nearest_known_sim": cr["s"] if cr else None, "novelty": cr["novelty"] if cr else None,
           "nearest_known_id": cr["nearest_id"] if cr else None, "nearest_known_dataset": cr["nearest_dataset"] if cr else None,
           "nearest_known_idx": cr["nearest_idx"] if cr else None, "top_known_ids": cr["top_ids"] if cr else None,
           "top_known_sims": cr["top_sims"] if cr else None, "ast_dist": cr["ast_dist"] if cr else None,
           "ast_dist_min": cr["ast_dist_min"] if cr else None, "gpu_seconds": round(gpu_s, 5),
           "usd": kid.get("usd", 0.0), "utc": utc_now()}
    for k in ("intent", "intent_valid", "eap_item", "eap_n_items", "cal_mode", "stage1_gpu_seconds"):
        if k in meta:
            row[k] = meta[k]
    return row


def raw_rec(task: str, arm: str, idx: int, req_rec: dict[str, Any], kid: dict[str, Any], meta: dict[str, Any]) -> dict:
    return {"id": f"{task}|{arm}|{idx}", "prompt_sha256": req_rec["prompt_sha256"], "prompt": req_rec["prompt"],
            "text": kid["text"], "finish_reason": kid.get("finish_reason"), "seed": meta.get("seed"),
            "meta": {k: v for k, v in meta.items() if k not in ("parents",)}}


# ------------------------------------------------------------------------------------------------ seeds
def seed_records(task: str, obj: dict[str, Any], critic: Critic, ev: Evaluator) -> list[dict[str, Any]]:
    names = [obj["seed_refs"][m] for m in obj["modes"]]
    codes = [obj["references"][n] for n in names]
    res = ev.eval_many(task, codes, exclude_self=True)
    out = []
    for n, m, c, r in zip(names, obj["modes"], codes, res):
        assert r["eval"]["correct"], f"seed {n} fails the evaluator"
        rl = r["lab"]["runtime_label"] if r["lab"] else m
        out.append({"id": f"seed:{task}:{n}", "code": c, "novelty": r["critic"]["novelty"], "s": r["critic"]["s"],
                    "runtime_ratio": r["eval"]["runtime_ratio"], "median_case_ms": r["eval"]["median_case_ms"],
                    "runtime_label": rl, "ds_signature": r["ds_signature"], "cell": cell_key(rl, r["ds_signature"]),
                    "origin": "seed", "depth": 0, "mode": m})
    write_json(DATA / f"seeds_{task}.json", out)
    return out


# ------------------------------------------------------------------------------------------------ calib stage
def stage_calib(n_eng: int = 20, n_cal: int = 30) -> None:
    objs = {t: load_task(t) for t in TASKS}
    critic = Critic()
    ev = Evaluator(objs, critic)
    eng = VLLMEngine()
    write_json(PRED / "engine_config.json", eng.config_used)
    out_p = DATA / "rows_calib.jsonl"
    done = {r["id"] for r in read_jsonl(out_p)}
    for task in TASKS:
        obj = objs[task]
        reqs, metas = [], []
        for i in range(n_eng):
            w = W_TEMPLATES[i % 5]
            text, src = b0_user_text(obj, w)
            sd = stable_seed(task, "ENG", i)
            reqs.append(Req(user_text=text, n=1, seed=sd, max_tokens=MAX_TOKENS[task]))
            metas.append({"arm": "ENG", "idx": i, "template": w, "seed": sd, "prompt_source": src})
        k = 0
        for mode in obj["modes"]:
            for j in range(n_cal):
                sd = stable_seed(task, "CAL", mode, j)
                reqs.append(Req(user_text=cal_user_text(obj, mode, j), n=1, seed=sd, max_tokens=MAX_TOKENS[task]))
                metas.append({"arm": "CAL", "idx": k, "cal_mode": mode, "seed": sd, "template": f"F{j % 10}",
                              "prompt_source": "forced"})
                k += 1
        keep = [(r, m) for r, m in zip(reqs, metas) if f"{task}|{m['arm']}|{m['idx']}" not in done]
        if not keep:
            continue
        t0 = time.time()
        recs = eng.generate([r for r, _ in keep])
        gen_s = time.time() - t0
        codes = [extract_code(rr["children"][0]["text"]) for rr in recs]
        res = ev.eval_many(task, codes)
        rows, raws = [], []
        for (rq, m), rr, r in zip(keep, recs, res):
            kid = rr["children"][0]
            rows.append(child_row(task, m["arm"], m["idx"], rr, kid, r, m, rr["gpu_seconds"]))
            raws.append(raw_rec(task, m["arm"], m["idx"], rr, kid, m))
        append_jsonl(out_p, rows)
        append_jsonl(RAW / f"calib_{task}.jsonl", raws)
        logger.info(f"calib {task}: {len(rows)} children in {gen_s:.0f}s; correct {sum(r['correct'] for r in rows)}")
    # throughput pilot on T03: 64 S-shaped prompts (parents = seed references) and 64 B0 prompts
    task = "T03"
    obj = objs[task]
    seeds = seed_records(task, obj, critic, ev)
    pool = FrozenSeedPool(seeds, stable_seed(task, "TP"))
    s_reqs = [Req(user_text=s_user_text(obj, pool.pick_parents()), n=1, seed=stable_seed(task, "TPS", i),
                  max_tokens=MAX_TOKENS[task]) for i in range(64)]
    b_reqs = [Req(user_text=b0_user_text(obj, W_TEMPLATES[i % 5])[0], n=1, seed=stable_seed(task, "TPB", i),
                  max_tokens=MAX_TOKENS[task]) for i in range(64)]
    tp = {}
    for name, rq in (("S_shaped", s_reqs), ("B0", b_reqs)):
        t0 = time.time()
        recs = eng.generate(rq)
        wall = time.time() - t0
        ntok = sum(c["n_new_tokens"] for r in recs for c in r["children"])
        npt = [r["n_prompt_tokens"] for r in recs]
        tp[name] = {"n": len(rq), "wall_s": round(wall, 2), "children_per_hour": round(3600 * len(rq) / wall, 1),
                    "gpu_s_per_child": round(wall / len(rq), 4), "new_tokens": ntok,
                    "prompt_tokens_median": sorted(npt)[len(npt) // 2], "prompt_tokens_max": max(npt)}
        if name == "S_shaped":
            codes = [extract_code(r["children"][0]["text"]) for r in recs]
            tp[name]["has_code_rate"] = round(sum(c is not None for c in codes) / len(codes), 3)
            tp[name]["fence_stop_rate"] = round(sum(r["children"][0]["finish_reason"] == "stop" for r in recs) / len(recs), 3)
    tp["utc"] = utc_now()
    tp["engine_config"] = eng.config_used
    write_json(PRED / "throughput_pilot.json", tp)
    logger.info(f"throughput pilot: {tp}")


# ------------------------------------------------------------------------------------------------ base intents
def stage_base(n_per_task: dict[str, int], max_attempts: int = 3) -> None:
    from transformers import AutoTokenizer

    from engine import snapshot_path
    from prompts import ChatFormatter
    from common import MODEL_REV
    objs = {t: load_task(t) for t in TASKS if n_per_task.get(t, 0) > 0}
    fmt = ChatFormatter(AutoTokenizer.from_pretrained(snapshot_path(MODEL_ID, MODEL_REV)))
    out_p = RAW / "bint_intents.jsonl"
    have = {(r["task"], r["index"]) for r in read_jsonl(out_p) if r.get("final")}
    eng = VLLMEngine(base=True)
    P = parsers()
    for task, obj in objs.items():
        todo = [i for i in range(n_per_task[task]) if (task, i) not in have]
        if not todo:
            continue
        final: dict[int, dict[str, Any]] = {}
        pending = list(todo)
        for att in range(max_attempts):
            if not pending:
                break
            reqs, metas = [], []
            for i in pending:
                w = W_TEMPLATES[i % 5]
                txt, src = ifg_text(obj, w)
                raw = fmt.user(txt) + INTENT_PREFIX
                sd = stable_seed(task, "BINT:intent", i, att)
                reqs.append(Req(raw_prompt=raw, n=1, seed=sd, max_tokens=64, stop=["\n"]))
                metas.append({"i": i, "w": w, "src": src, "seed": sd})
            t0 = time.time()
            recs = eng.generate(reqs)
            wall = time.time() - t0
            nxt = []
            for m, rr in zip(metas, recs):
                txt = rr["children"][0]["text"] or ""
                intent = P.parse_intent(txt)
                ok = P.intent_valid(intent) and rr["children"][0]["finish_reason"] in ("stop", "length")
                rec = {"task": task, "index": m["i"], "template": m["w"], "prompt_source": m["src"], "attempt": att,
                       "seed": m["seed"], "raw": txt, "intent": intent, "valid": bool(ok),
                       "capped": rr["children"][0]["finish_reason"] == "length",
                       "gpu_seconds": rr["gpu_seconds"], "base_model": "Qwen/Qwen3-8B-Base"}
                if ok or att == max_attempts - 1:
                    rec["final"] = True
                    final[m["i"]] = rec
                else:
                    nxt.append(m["i"])
                append_jsonl(out_p, [rec])
            pending = nxt
            logger.info(f"base intents {task} attempt {att}: {len(recs)} in {wall:.0f}s; invalid -> retry {len(nxt)}")


# ------------------------------------------------------------------------------------------------ the run
def interleave(lists: dict[str, list[Any]]) -> list[Any]:
    """Merge per-arm lists so that every prefix of the queue holds each arm in proportion to its size."""
    keyed = []
    for arm, lst in lists.items():
        n = len(lst)
        for i, x in enumerate(lst):
            keyed.append(((i + 0.5) / n, arm, i, x))
    keyed.sort(key=lambda k: (k[0], k[1], k[2]))
    return [k[3] for k in keyed]


def build_iid_specs(task: str, obj: dict[str, Any], N: dict[str, int], seeds: list[dict[str, Any]],
                    eap1: dict[int, dict[str, Any]], intents: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    mt = MAX_TOKENS[task]
    lists: dict[str, list[dict[str, Any]]] = {}
    # NE: prompts with 4 children each; parents = 2 distinct seed references (frozen pool, archive never read)
    pool = FrozenSeedPool(seeds, stable_seed(task, "NE", "pool"))
    ne = []
    for p in range((N.get("NE", 0) + CHILDREN_PER_PROMPT - 1) // CHILDREN_PER_PROMPT):
        par = pool.pick_parents()
        n_here = min(CHILDREN_PER_PROMPT, N["NE"] - p * CHILDREN_PER_PROMPT)
        ne.append({"arm": "NE", "first_idx": p * CHILDREN_PER_PROMPT, "n": n_here, "seed": stable_seed(task, "NE", p),
                   "req": Req(user_text=s_user_text(obj, par), n=n_here, seed=stable_seed(task, "NE", p), max_tokens=mt),
                   "meta": {"parent_ids": [x["id"] for x in par], "depth": 1, "prompt_source": "S_builder:seed_pool"}})
    lists["NE"] = ne
    lists["I0"] = [{"arm": "I0", "first_idx": i, "n": 1, "req": Req(user_text=i0_user_text(obj), n=1,
                                                                    seed=stable_seed(task, "I0", i), max_tokens=mt),
                    "meta": {"prompt_source": "I0"}} for i in range(N.get("I0", 0))]
    b0 = []
    for i in range(N.get("B0", 0)):
        w = W_TEMPLATES[i % 5]
        txt, src = b0_user_text(obj, w)
        b0.append({"arm": "B0", "first_idx": i, "n": 1, "req": Req(user_text=txt, n=1, seed=stable_seed(task, "B0", i),
                                                                   max_tokens=mt),
                   "meta": {"template": w, "prompt_source": src}})
    lists["B0"] = b0
    eap = []
    for i in range(N.get("EAP", 0)):
        e = eap1.get(i)
        if e is None:
            continue
        if not e["items"]:
            eap.append({"arm": "EAP", "first_idx": i, "n": 1, "req": None,
                        "meta": {"template": e["template"], "eap_n_items": 0, "eap_item": None,
                                 "stage1_gpu_seconds": e["gpu_seconds"], "prompt_source": e["src"]}})
            continue
        j = random.Random(stable_seed(task, "EAP:pick", i)).randrange(len(e["items"]))
        it = e["items"][j]
        msgs = [{"role": "user", "content": e["stage1_prompt_text"]}, {"role": "assistant", "content": e["text"]},
                {"role": "user", "content": EAP_B.format(i=j + 1, name=it["name"])}]
        eap.append({"arm": "EAP", "first_idx": i, "n": 1,
                    "req": Req(messages=msgs, n=1, seed=stable_seed(task, "EAP", i), max_tokens=mt),
                    "meta": {"template": e["template"], "eap_n_items": len(e["items"]), "eap_item": it,
                             "stage1_gpu_seconds": e["gpu_seconds"], "prompt_source": e["src"]}})
    lists["EAP"] = eap
    bint = []
    for i in range(N.get("BINT", 0)):
        it = intents.get(i)
        if it is None:
            continue
        txt, src = ifg_text(obj, it["template"])
        bint.append({"arm": "BINT", "first_idx": i, "n": 1,
                     "req": Req(user_text=txt, assistant_prefix=f"{INTENT_PREFIX} {it['intent'].strip()}\n", n=1,
                                seed=stable_seed(task, "BINT", i), max_tokens=mt),
                     "meta": {"template": it["template"], "intent": it["intent"], "intent_valid": it["valid"],
                              "stage1_gpu_seconds": it.get("gpu_seconds", 0.0), "prompt_source": src}})
    lists["BINT"] = bint
    return interleave(lists)


def eap_stage1(task: str, obj: dict[str, Any], n: int, eng: VLLMEngine) -> dict[int, dict[str, Any]]:
    p = RAW / f"eap1_{task}.jsonl"
    have = {r["index"]: r for r in read_jsonl(p)}
    todo = [i for i in range(n) if i not in have]
    if todo:
        P = parsers()
        reqs, metas = [], []
        for i in todo:
            w = W_TEMPLATES[i % 5]
            txt, src = eap_stage1_text(obj, w)
            reqs.append(Req(user_text=txt, n=1, seed=stable_seed(task, "EAP:stage1", i), max_tokens=400, stop=[]))
            metas.append({"i": i, "w": w, "src": src, "txt": txt})
        t0 = time.time()
        recs = eng.generate(reqs)
        logger.info(f"EAP stage 1 {task}: {len(recs)} lists in {time.time() - t0:.0f}s")
        rows = []
        for m, rr in zip(metas, recs):
            text = rr["children"][0]["text"] or ""
            items = P.parse_enum(text, max_n=8)
            rows.append({"index": m["i"], "template": m["w"], "src": m["src"], "stage1_prompt_text": m["txt"],
                         "text": text, "items": items, "gpu_seconds": rr["gpu_seconds"],
                         "n_new_tokens": rr["children"][0]["n_new_tokens"], "utc": utc_now()})
        append_jsonl(p, rows)
        for r in rows:
            have[r["index"]] = r
    return have


def stage_run(plan: dict[str, Any], deadline_epoch: float) -> None:
    objs = {t: load_task(t) for t in TASKS}
    critic = Critic()
    ev = Evaluator(objs, critic)
    eng = VLLMEngine()
    write_json(PRED / "engine_config_run.json", eng.config_used)
    intents_all = defaultdict(dict)
    for r in read_jsonl(RAW / "bint_intents.jsonl"):
        if r.get("final"):
            intents_all[r["task"]][r["index"]] = r
    for task in plan["task_order"]:
        N = plan["N"][task]
        if time.time() > deadline_epoch:
            logger.warning(f"deadline passed before task {task}; skipped")
            break
        run_task(task, objs[task], N, eng, ev, critic, intents_all[task], deadline_epoch)
        gc.collect()


def run_task(task: str, obj: dict[str, Any], N: dict[str, int], eng: VLLMEngine, ev: Evaluator, critic: Critic,
             intents: dict[int, dict[str, Any]], deadline_epoch: float, s_arm: str = "S", tag: str | None = None,
             model_meta: dict[str, Any] | None = None) -> None:
    tag = tag or task
    logger.info(f"=== task {task} ({tag}): N = {N}")
    seeds = seed_records(task, obj, critic, ev)
    db = SearchDB(seeds, rng_seed=stable_seed(task, s_arm, "db"))
    st_p = DATA / f"search_state_{tag}.json"
    rows_p = rows_path(tag)
    if s_arm != "S" and "S" in N:
        N = {s_arm: N["S"]}
    rounds_done = 0
    if st_p.exists():
        st = read_json(st_p)
        db.load_state(st["db"])
        rounds_done = st["rounds_done"]
        kept = [r for r in read_jsonl(rows_p) if r["arm"] != s_arm or r["slot"] < db.t]
        write_jsonl(rows_p, kept)
        logger.info(f"resuming {task} at round {rounds_done} (S calls {db.t})")
    existing = read_jsonl(rows_p)
    done_ids = {r["id"] for r in existing}
    eap1 = eap_stage1(task, obj, N.get("EAP", 0), eng) if N.get("EAP", 0) else {}
    specs = build_iid_specs(task, obj, N, seeds, eap1, intents)
    specs = [s for s in specs if f"{task}|{s['arm']}|{s['first_idx']}" not in done_ids]
    n_s = N.get(s_arm, 0)
    s_next = db.t                                   # next S call index (= S children already finished)

    def s_rounds_left() -> int:
        return (max(n_s - s_next, 0) + ROUND_CHILDREN_S - 1) // ROUND_CHILDREN_S
    n_rounds = rounds_done + s_rounds_left()
    logger.info(f"{task}: {s_rounds_left()} S rounds to run (S calls done {s_next}/{n_s}), "
                f"{len(specs)} i.i.d. specs pending")
    pending: tuple[Future, list[dict[str, Any]]] | None = None
    filled_history = []
    t_task0 = time.time()
    r = rounds_done
    while s_next < n_s or specs or pending is not None:
        if time.time() > deadline_epoch:
            logger.warning(f"{task}: deadline reached at round {r}; stopping (truncated)")
            break
        batch: list[dict[str, Any]] = []
        rl = s_rounds_left()
        n_slice = (len(specs) + rl - 1) // rl if rl > 0 else len(specs)
        if s_next < n_s:
            n_prompts_total = 0
            for isl in range(N_ISLANDS):
                for k in range(PROMPTS_PER_ISLAND):
                    n_here = min(CHILDREN_PER_PROMPT, n_s - s_next)
                    if n_here <= 0:
                        continue
                    par = db.pick_parents(isl)
                    pi = n_prompts_total
                    sd = stable_seed(task, s_arm, s_next)
                    first = s_next
                    s_next += n_here
                    batch.append({"arm": s_arm, "first_idx": first, "n": n_here,
                                  "req": Req(user_text=s_user_text(obj, par), n=n_here, seed=sd,
                                             max_tokens=MAX_TOKENS[task]),
                                  "meta": {"round": r, "island": isl, "parent_ids": [p["id"] for p in par],
                                           "depth": 1 + max(p.get("depth", 0) for p in par), "prompt_source": s_arm,
                                           **(model_meta or {}),
                                           "tau": round(__import__("search").tau_at(db.t), 4)}})
                    n_prompts_total += 1
        n_slice = min(n_slice, 400)
        sl, specs = specs[:n_slice], specs[n_slice:]
        batch += sl
        gen_items = [b for b in batch if b["req"] is not None]
        t0 = time.time()
        recs = eng.generate([b["req"] for b in gen_items]) if gen_items else []
        gen_s = time.time() - t0
        # collect results of the previous round while this one generated
        if pending is not None:
            _finish(task, pending, db, rows_p, critic, filled_history, s_arm, tag)
            pending = None
        # flatten children for evaluation
        flat = []
        rmap = dict(zip([id(b) for b in gen_items], recs))
        for b in batch:
            rr = rmap.get(id(b))
            if rr is None:      # EAP stage-1 failure: a call with no program
                flat.append((b, {"prompt": "", "prompt_sha256": None, "children": [], "gpu_seconds": 0.0}, 0,
                             {"text": None, "n_new_tokens": 0, "finish_reason": "eap_stage1_empty"}))
                continue
            for j, kid in enumerate(rr["children"]):
                flat.append((b, rr, j, kid))
        codes = [extract_code(k["text"]) for _, _, _, k in flat]
        fut = ev.submit(task, codes)
        pending = (fut, flat)
        if any(b["arm"] == s_arm for b in batch):
            r += 1
        n_kids = len(flat)
        toks = sum(k.get("n_new_tokens") or 0 for _, _, _, k in flat)
        append_jsonl(RESULTS / "throughput_run.jsonl", [{"task": task, "round": r, "gen_s": round(gen_s, 2),
                                                        "n_children": n_kids, "new_tokens": toks,
                                                        "n_S": sum(1 for b, _, _, _ in flat if b["arm"] == s_arm),
                                                        "tag": tag,
                                                        "specs_left": len(specs), "utc": utc_now()}])
        el = time.time() - t_task0
        logger.info(f"{task} round {r}/{n_rounds}: {n_kids} children ({toks} tok) gen {gen_s:.0f}s; "
                    f"{len(specs)} i.i.d. left; elapsed {el / 60:.1f} min; S t={db.t}")
        if s_next >= n_s and not specs:
            break
    if pending is not None:
        _finish(task, pending, db, rows_p, critic, filled_history, s_arm, tag)
        pending = None
    write_json(st_p, {"db": db.state(), "rounds_done": r, "utc": utc_now()}, indent=None)
    write_json(RESULTS / f"archive_{tag}.json", {"final": db.snapshot(), "history": db.history,
                                                  "filled_history": filled_history})
    rows = read_jsonl(rows_p)
    c = Counter((x["arm"], x["correct"]) for x in rows)
    logger.info(f"=== task {task} done in {(time.time() - t_task0) / 60:.1f} min: " +
                ", ".join(f"{a}: {c[(a, True)]}/{c[(a, True)] + c[(a, False)]}" for a in
                          (s_arm, "NE", "I0", "EAP", "BINT", "B0")))


def _finish(task: str, pending: tuple[Future, list], db: SearchDB, rows_p, critic: Critic,
            filled_history: list[dict[str, Any]], s_arm: str = "S", tag: str | None = None) -> None:
    fut, flat = pending
    res = fut.result()
    rows, raws = [], []
    n_s = 0
    new_cells = 0
    for (b, rr, j, kid), r in zip(flat, res):
        idx = b["first_idx"] + j
        meta = dict(b["meta"])
        meta["seed"] = b["req"].seed if b["req"] is not None else None
        gpu = (rr["gpu_seconds"] / max(len(rr["children"]), 1)) + float(meta.get("stage1_gpu_seconds") or 0.0)
        row = child_row(task, b["arm"], idx, rr, kid, r, meta, gpu)
        rows.append(row)
        raws.append(raw_rec(task, b["arm"], idx, rr, kid, meta))
        if b["arm"] == s_arm:
            n_s += 1
            if row["correct"] and row["novelty"] is not None:
                prog = {"id": row["id"], "code": row["code"], "novelty": row["novelty"], "s": row["nearest_known_sim"],
                        "runtime_ratio": row["runtime_ratio"], "median_case_ms": row["median_case_ms"],
                        "runtime_label": row["runtime_label"], "ds_signature": row["ds_signature"],
                        "cell": row["cell"], "origin": s_arm, "depth": meta.get("depth", 1),
                        "parent_ids": meta.get("parent_ids")}
                isl = meta["island"]
                had = prog["cell"] in db.islands[isl].cells
                if db.offer(isl, prog) and not had:
                    new_cells += 1
    append_jsonl(rows_p, rows)
    by_arm = defaultdict(list)
    for x in raws:
        by_arm[x["id"].split("|")[1]].append(x)
    for a, xs in by_arm.items():
        append_jsonl(RAW / f"{a}_{task}.jsonl", xs)
    tag = tag or task
    resets = db.advance(n_s) if n_s else []
    snap = db.snapshot()
    db.history.append({"t": db.t, "n_cells": [i["n_cells"] for i in snap["islands"]],
                       "qd_score": [i["qd_score"] for i in snap["islands"]],
                       "best_nu": [i["best_nu"] for i in snap["islands"]], "resets": resets})
    filled_history.append({"t": db.t, "new_cells": new_cells})
    rounds_done = (db.t + ROUND_CHILDREN_S - 1) // ROUND_CHILDREN_S
    write_json(DATA / f"search_state_{tag}.json", {"db": db.state(), "rounds_done": rounds_done, "utc": utc_now()},
               indent=None)
