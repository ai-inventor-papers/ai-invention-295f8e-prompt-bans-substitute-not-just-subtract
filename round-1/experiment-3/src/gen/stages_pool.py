"""S6 pools (arm A0) plus engine tests T4/T5. Runs inside the single vLLM process of phase 'gen1'."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from loguru import logger

from common import GEN_DIR, LOG_DIR, MODEL_ID, append_jsonl, read_jsonl, stable_seed, wilson
from gen.engine import ENGINE_INFO, generate, sample_scheduled, sp
from labeller.evidence import commitment

POOL_FILE = GEN_DIR / "pools.jsonl"


def base_row(**kw) -> dict:
    row = {"task": None, "condition": None, "paraphrase_id": None, "sample_id": None, "model": MODEL_ID,
           "decoding": None, "label": None, "labeller_source": None, "passed": None, "wall_s": None,
           "code_sha256": None, "code": None, "arm": None, "stage": None, "base_path_id": None, "prefix_len": 0,
           "seed": None, "n_gen_tokens": None, "finish_reason": None, "runtime_label": None, "ast_label": None,
           "judge_label": None, "commit_idx": None, "evidence_term": None}
    row.update(kw)
    return row


def attach_label(row: dict, res: dict) -> dict:
    for k in ("label", "labeller_source", "passed", "wall_s", "code_sha256", "code", "runtime_label", "ast_label"):
        row[k] = res.get(k)
    row["runtime_rule"] = res.get("runtime_rule")
    row["first_error"] = res.get("first_error")
    row["n_failed"] = res.get("n_failed")
    return row


def flush(pending: list, path: Path) -> list[dict]:
    rows = []
    for row, fut in pending:
        rows.append(attach_label(row, fut.result()))
    append_jsonl(path, rows)
    return rows


def run_t45(llm, tok, prompts: dict, pool) -> dict:
    """T4 prefix handling + seed reproducibility; T5 segmented sampler (schedule log + equivalence at T=1)."""
    res: dict = {}
    P = prompts["T1|baseline|0"]["prompt_token_ids"]
    g = generate(llm, [P], [sp(0.0, 300, 1)])[0].outputs[0]
    base = list(g.token_ids)
    ident = {}
    for p in (10, 40):
        c = generate(llm, [P + base[:p]], [sp(0.0, 120, 2)])[0].outputs[0]
        a, b = list(c.token_ids), base[p:p + len(c.token_ids)]
        m = min(len(a), len(b))
        ident[p] = float(np.mean([x == y for x, y in zip(a[:m], b[:m])])) if m else float("nan")
    res["T4_greedy_prefix_identity"] = ident
    r1 = generate(llm, [P], [sp(1.0, 120, 777)])[0].outputs[0].token_ids
    r2 = generate(llm, [P], [sp(1.0, 120, 777)])[0].outputs[0].token_ids
    res["T4_same_seed_reproduces"] = list(r1) == list(r2)
    # T5a: schedule log on a FORK-like schedule
    sched = [(0.3, 2, None), (1.3, 5, None), (0.3, 3, None), (1.3, 4, None), (0.3, None, None)]
    jobs = [{"prompt_ids": P, "segments": sched, "seed": stable_seed("t5a", i)} for i in range(5)]
    st = sample_scheduled(llm, jobs, max_total=200)
    exp_fn = []
    for T, L, _ in sched:
        exp_fn += [T] * (L if L is not None else 400)
    ok = all(s["temps"] == exp_fn[:len(s["temps"])] for s in st)
    res["T5_schedule_log_matches"] = bool(ok)
    # T5b: T_hot = T_cold = 1.0 versus plain T = 1.0 (50 samples each), labels + mean length
    P2 = prompts["T2|ban|0"]["prompt_token_ids"]
    jobs = [{"prompt_ids": P2, "segments": [(1.0, 3, None), (1.0, 5, None), (1.0, None, None)],
             "seed": stable_seed("t5b", i)} for i in range(50)]
    st = sample_scheduled(llm, jobs, max_total=1024)
    seg_texts = [tok.decode(s["ids"], skip_special_tokens=True) for s in st]
    plain = generate(llm, [P2], [sp(1.0, 1024, stable_seed("t5b_plain"), n=50)])[0].outputs
    plain_texts = [c.text for c in plain]
    seg_labels = [pool.submit("T2", t).result()["label"] for t in seg_texts]
    plain_labels = [pool.submit("T2", t).result()["label"] for t in plain_texts]
    labs = sorted(set(seg_labels) | set(plain_labels))
    comp = {}
    overlap = True
    for lab in labs:
        a = wilson(seg_labels.count(lab), 50)
        b = wilson(plain_labels.count(lab), 50)
        comp[lab] = {"segmented": a, "plain": b}
        overlap &= not (a[2] < b[1] or b[2] < a[1])
    res["T5_label_dists"] = comp
    res["T5_intervals_overlap"] = bool(overlap)
    res["T5_mean_len"] = {"segmented": float(np.mean([len(s["ids"]) for s in st])),
                          "plain": float(np.mean([len(c.token_ids) for c in plain]))}
    sl = np.array([len(s["ids"]) for s in st], float)
    pl = np.array([len(c.token_ids) for c in plain], float)
    se = np.sqrt(sl.var(ddof=1) / len(sl) + pl.var(ddof=1) / len(pl))
    res["T5_mean_len_z"] = float((sl.mean() - pl.mean()) / se) if se > 0 else 0.0
    logger.info(f"T4/T5: {json.dumps({k: v for k, v in res.items() if k != 'T5_label_dists'})}")
    (LOG_DIR / "test_engine.json").write_text(json.dumps(res, indent=1))
    return res


def run_s6(llm, tok, prompts: dict, pool, stage_tag: str = "full", limit_paras: int | None = None) -> list[dict]:
    """G1 baseline T=1.0 (20/para), G2 ban T=1.0 (10/para), G3 global T in {0.3, 0.7, 1.3} (10/para)."""
    done = {(r["arm"], r["task"], r["paraphrase_id"]) for r in read_jsonl(POOL_FILE)}
    specs = []
    for task in ("T1", "T2"):
        paras = range(10 if limit_paras is None else limit_paras)
        for pid in paras:
            specs.append(("G1", task, "baseline", pid, 1.0, 20))
            specs.append(("G2", task, "ban", pid, 1.0, 10))
            for T in (0.3, 0.7, 1.3):
                specs.append((f"G3_T{T}", task, "baseline", pid, T, 10))
    specs = [s for s in specs if (s[0], s[1], s[3]) not in done]
    if not specs:
        logger.info("S6 already complete")
        return read_jsonl(POOL_FILE)
    t0 = time.time()
    plist, params = [], []
    for arm, task, cond, pid, T, n in specs:
        seed = stable_seed(task, cond, pid, arm, "pool")
        plist.append(prompts[f"{task}|{cond}|{pid}"]["prompt_token_ids"])
        params.append(sp(T, 1024, seed, n=n))
    outs = generate(llm, plist, params)
    gen_s = time.time() - t0
    pending = []
    ntok = 0
    for (arm, task, cond, pid, T, n), o in zip(specs, outs):
        seed = stable_seed(task, cond, pid, arm, "pool")
        for c in o.outputs:
            ids = list(c.token_ids)
            ntok += len(ids)
            ev = commitment(tok, task, ids, None)
            row = base_row(task=task, condition=cond, paraphrase_id=pid, sample_id=c.index, arm=arm,
                           stage=stage_tag, seed=seed + c.index, decoding=f"T={T},top_p=1.0,top_k=-1",
                           n_gen_tokens=len(ids), finish_reason=c.finish_reason,
                           stop_reason=str(c.stop_reason) if c.stop_reason is not None else None,
                           gen_token_ids=ids, text=c.text, temperature=T, **ev)
            pending.append((row, pool.submit(task, c.text)))
    rows = flush(pending, POOL_FILE)
    logger.info(f"S6 {stage_tag}: {len(rows)} samples, {ntok} tokens, gen {gen_s:.1f}s "
                f"({ntok / max(gen_s, 1e-6):.0f} tok/s), total {time.time() - t0:.1f}s; engine {ENGINE_INFO}")
    with open(LOG_DIR / "throughput.log", "a") as fh:
        fh.write(json.dumps({"stage": f"S6_{stage_tag}", "n": len(rows), "tokens": ntok, "gen_s": gen_s,
                             "tok_s": ntok / max(gen_s, 1e-6), "s_per_sample": gen_s / max(1, len(rows))}) + "\n")
    return read_jsonl(POOL_FILE)
