#!/usr/bin/env python3
"""V5 (descriptive; commit #4 precedes the first call): do new behaviours hinge on a few 'birth' tokens?

Founders: per arm-seed, leader clustering in call order; a founder is a valid offspring that starts a new leader
cluster with F below every prompt parent. The first 40 pooled in birth order (round, arm order, call index).
Per founder: one /v1/completions request on prompt + completion ids (max_tokens 1, prompt_logprobs 20); birth
positions = completion positions where the realised token is not the argmax and the top-20 entropy >= the founder's
own 90th percentile; for each of the first <= 3 birth positions p: prompt + completion[:p] + argmax, 20 continuations
at T 1.0 (max_tokens 512 - p - 1). Controls: as many positions drawn uniformly from the other non-argmax positions.
Each continuation's P1 vector only is scored; it REVERTS if it agrees >= 0.95 with either parent."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import aiohttp
import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402
import bp  # noqa: E402
import cluster  # noqa: E402
import engine  # noqa: E402
import prompts  # noqa: E402
import sandbox  # noqa: E402

ROOT = bp.ROOT
URL = "http://127.0.0.1:8051/v1/completions"
N_FOUNDERS, N_CONT, MAX_POS = 40, 20, 3
ARM_ORDER = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]


def founders(rows: list[dict], c_s: int) -> list[dict]:
    out = []
    by_pid = {r["pid"]: r for r in rows}
    for s in (0, 1):
        for arm in ARM_ORDER:
            rs = analysis.stream_rows(rows, s, arm, c_s)
            D = analysis.load_decisions("main", s, arm)[:len(rs)]
            vm = [analysis.valid(r) and not r.get("probe_failed") for r in rs]
            vr = [r for r, m in zip(rs, vm) if m]
            Dv = D[np.array(vm, dtype=bool)]
            _, leaders = cluster.leader(Dv)
            for li in leaders:
                r = vr[li]
                pf = [1.0 if p == "seed-BF" else by_pid[p]["F"] for p in r["parent_ids"]]
                if all(f is not None and r["F"] < f for f in pf):
                    out.append(dict(r, _dec=Dv[li]))
    out.sort(key=lambda r: (r["round"], ARM_ORDER.index(r["arm"]), r["call_id"], r["seed"]))
    return out[:N_FOUNDERS]


def entropy(d: dict) -> float:
    lp = np.array(sorted((v["logprob"] for v in d.values()), reverse=True)[:20])
    p = np.exp(lp - lp.max())
    p /= p.sum()
    return float(-(p * np.log(np.clip(p, 1e-300, None))).sum())


async def post(session, payload, sem) -> dict:
    for _ in range(3):
        try:
            async with sem:
                async with session.post(URL, json=payload) as r:
                    if r.status == 200:
                        return await r.json()
                    err = await r.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            err = repr(e)
    return {"error": str(err)[:300]}


async def run() -> dict:
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8", revision="220b46e3b2180893580a4454f21f22d3ebb187d3")
    rows = analysis.load_rows("main")
    cl = json.loads((ROOT / "results" / "clusters.json").read_text())
    c_s = cl["C_s"]
    by_pid = {r["pid"]: r for r in rows}
    ids = {}
    for ln in (ROOT / "data" / "main" / "completion_ids.jsonl").read_text().splitlines():
        d = json.loads(ln)
        ids[d["pid"]] = d["ids"]
    F = founders(rows, c_s)
    names, CV = None, None
    corpus = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    ent = {e["name"]: e for e in corpus["entries"]}
    seed_dec = {"seed-BF": np.array(ent["BF"]["decisions"], dtype=np.uint16),
                "seed-FF": np.array(ent["FF"]["decisions"], dtype=np.uint16)}
    decs = {(a, s): analysis.load_decisions("main", s, a) for a in ARM_ORDER for s in (0, 1)}

    def dec_of(pid):
        if pid in seed_dec:
            return seed_dec[pid]
        r = by_pid[pid]
        return decs[(r["arm"], r["seed"])][r["dec_ref"][1]]

    sem = asyncio.Semaphore(3)  # prompt_logprobs materialise full-vocab logprobs per prompt token (OOM at 32)
    plan = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
        for fi, r in enumerate(F):
            parents = [by_pid[p] if p in by_pid else {"pid": p, "code": bp.SRC_BF if p == "seed-BF" else bp.SRC_FF}
                       for p in r["parent_ids"]]
            _, pids = prompts.render(tok, [prompts.body_of(p["code"]) for p in parents], idea=(r["arm"] == "IDEA"))
            import hashlib  # noqa: PLC0415
            sha_ok = hashlib.sha256(json.dumps(pids).encode()).hexdigest()[:16] == r["prompt_sha"]
            comp = ids[r["pid"]]
            d = await post(session, {"model": "qwen3-8b", "prompt": pids + comp, "max_tokens": 1, "temperature": 0,
                                     "prompt_logprobs": 20}, sem)
            pl = (d.get("choices") or [{}])[0].get("prompt_logprobs") if "error" not in d else None
            rec = {"pid": r["pid"], "arm": r["arm"], "seed": r["seed"], "round": r["round"], "F": r["F"],
                   "parent_ids": r["parent_ids"], "prompt_sha_ok": sha_ok, "n_comp": len(comp)}
            if not pl:
                rec["error"] = d.get("error", "no prompt_logprobs")
                plan.append(rec)
                continue
            texts = [tok.decode([t]) for t in comp]
            limit = engine.body_char_limit(tok.decode(comp))
            pos_info, off = [], 0
            for k, t in enumerate(comp):
                dd = pl[len(pids) + k]
                if dd is None:
                    off += len(texts[k])
                    continue
                top = {int(kk): vv for kk, vv in dd.items()}
                am = max(top.items(), key=lambda kv: kv[1]["logprob"])[0]
                if off < limit:
                    pos_info.append({"p": k, "H": entropy(top), "argmax": am, "realised": t, "is_argmax": am == t})
                off += len(texts[k])
            if not pos_info:
                rec["error"] = "no body positions"
                plan.append(rec)
                continue
            q90 = float(np.percentile([x["H"] for x in pos_info], 90))
            births = [x for x in pos_info if not x["is_argmax"] and x["H"] >= q90][:MAX_POS]
            others = [x for x in pos_info if not x["is_argmax"] and x not in births]
            rng = np.random.default_rng([20261031, fi])
            ctrl = [others[i] for i in sorted(rng.choice(len(others), min(len(births), len(others)), replace=False))] \
                if others and births else []
            rec.update(q90=q90, births=[{k: v for k, v in b.items()} for b in births],
                       controls=[{k: v for k, v in c.items()} for c in ctrl], k=r["k"])
            rec["_pids"], rec["_comp"] = pids, comp
            plan.append(rec)
        # continuations
        sem = asyncio.Semaphore(12)
        jobs, keys = [], []
        for fi, rec in enumerate(plan):
            if "error" in rec:
                continue
            for kind in ("births", "controls"):
                for x in rec[kind]:
                    p = x["p"]
                    pref = rec["_comp"][:p] + [x["argmax"]]
                    jobs.append(post(session, {"model": "qwen3-8b", "prompt": rec["_pids"] + pref, "n": N_CONT,
                                               "max_tokens": prompts.MAX_TOKENS - p - 1, "temperature": 1.0,
                                               "top_p": 1.0, "seed": engine.call_seed(20261031, fi, p),
                                               "stop": prompts.STOPS}, sem))
                    keys.append((fi, kind, p, tok.decode(pref)))
        logger.info(f"V5: {len(F)} founders, {len(jobs)} positions x {N_CONT} continuations")
        t0 = time.time()
        res = await asyncio.gather(*jobs)
        logger.info(f"V5 generations done in {time.time() - t0:.0f}s")
    # score P1 vectors
    pool = sandbox.EvalPool(2, ROOT, as_gib=2.0)
    futs = []
    for (fi, kind, p, pref_text), d in zip(keys, res):
        conts = [c["text"] for c in (d.get("choices") or [])]
        for c in conts:
            code = prompts.program_from(pref_text + c, plan[fi]["k"])
            futs.append(((fi, kind, p), pool.submit({"code": code, "sets": [], "probes": ["P1"], "probe_limit": 10.0})))
    outs: dict = {}
    for key, f in futs:
        r = f.result()
        outs.setdefault(key, []).append(r)
    pool.close()
    per_pos = []
    for (fi, kind, p), rs in outs.items():
        rec = plan[fi]
        pdecs = [dec_of(pp) for pp in rec["parent_ids"]]
        n_inv = n_rev = n_val = 0
        for r in rs:
            pb = r.get("probes", {}).get("P1")
            if r["error_type"] != "ok" or pb is None:
                n_inv += 1
                continue
            d = np.frombuffer(pb, dtype=np.uint16)
            n_val += 1
            n_rev += int(max(cluster.agreement(d, q) for q in pdecs) >= 0.95)
        per_pos.append({"founder": fi, "pid": rec["pid"], "arm": rec["arm"], "kind": kind, "p": p, "n": len(rs),
                        "valid": n_val, "invalid": n_inv, "reverted": n_rev,
                        "reversion_rate": n_rev / n_val if n_val else None})
    # per-founder maxima, birth vs random (sign test)
    fmax = []
    for fi, rec in enumerate(plan):
        b = [x["reversion_rate"] for x in per_pos if x["founder"] == fi and x["kind"] == "births" and x["reversion_rate"] is not None]
        c = [x["reversion_rate"] for x in per_pos if x["founder"] == fi and x["kind"] == "controls" and x["reversion_rate"] is not None]
        if b and c:
            fmax.append({"founder": fi, "arm": rec["arm"], "birth_max": max(b), "control_max": max(c)})
    from scipy.stats import binomtest  # noqa: PLC0415
    pos = sum(x["birth_max"] > x["control_max"] for x in fmax)
    neg = sum(x["birth_max"] < x["control_max"] for x in fmax)
    sign = binomtest(pos, pos + neg, 0.5).pvalue if pos + neg else None
    by_arm = {}
    for arm in ARM_ORDER:
        fr = [fi for fi, rec in enumerate(plan) if rec["arm"] == arm and "error" not in rec]
        hit = [fi for fi in fr if any(x["founder"] == fi and x["kind"] == "births" and (x["reversion_rate"] or 0) >= 0.5
                                      for x in per_pos)]
        by_arm[arm] = {"n_founders": sum(1 for rec in plan if rec["arm"] == arm), "n_scored": len(fr),
                       "share_with_birth_reversion_ge_0.5": len(hit) / len(fr) if fr else None}
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_founders": len(plan),
           "founders": [{k: v for k, v in rec.items() if not k.startswith("_")} for rec in plan],
           "per_position": per_pos, "per_founder_max": fmax,
           "sign_test": {"birth_gt_control": pos, "birth_lt_control": neg, "p_two_sided": sign},
           "by_arm": by_arm,
           "mean_reversion": {k: float(np.mean([x["reversion_rate"] for x in per_pos if x["kind"] == k and
                                                x["reversion_rate"] is not None] or [np.nan])) for k in ("births", "controls")}}
    (ROOT / "results" / "v5.json").write_text(json.dumps(out, indent=1, default=float))
    logger.info(f"V5 done: mean reversion {out['mean_reversion']}, sign test {out['sign_test']}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "v5.log", rotation="30 MB", level="DEBUG")
    asyncio.run(run())


if __name__ == "__main__":
    main()
