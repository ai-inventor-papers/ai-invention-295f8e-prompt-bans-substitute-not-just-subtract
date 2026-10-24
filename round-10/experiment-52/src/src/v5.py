#!/usr/bin/env python3
"""V5 (descriptive): are discoveries carried by single decision tokens? Offspring that founded a new behaviour cluster
in their arm-seed with F better than both parents (up to 40, birth order) are teacher-forced (prompt + completion,
max_tokens 1, prompt_logprobs 20). At the first position where the realised token is not the argmax and its entropy is
at or above the offspring's own 90th percentile, the argmax is forced and 20 continuations are sampled at T 1.0;
control = one random non-argmax position of the same offspring. Every continuation is evaluated; reversion = agreement
>= 0.95 with a parent. Completion token ids are re-tokenised from the text for non-branch arms (stated)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx  # noqa: E402
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import analysis as AN  # noqa: E402
import clusters as CL  # noqa: E402
import common as C  # noqa: E402
import engine as EN  # noqa: E402
import prompts as P  # noqa: E402
import sandbox  # noqa: E402
import search as SE  # noqa: E402

N_OFFSPRING = 40
N_CONT = 20
ARMS = ["T1.0", "T1.6", "DTB", "RPB", "IDEA"]


def entropy_from_dict(d: dict) -> tuple[float, int]:
    lp = np.array([v["logprob"] if isinstance(v, dict) else float(v) for v in d.values()], dtype=float)
    ids = [int(k) for k in d.keys()]
    p = np.exp(lp - lp.max())
    p /= p.sum()
    return float(-(p * np.log(np.clip(p, 1e-300, None))).sum()), ids[int(np.argmax(lp))]


def select_offspring(gen: dict, ev: dict, dec: np.ndarray) -> list[dict]:
    Cs = AN.matched_calls(ev)
    out = []
    for S in C.SEEDS:
        for arm in ARMS:
            es = AN.arm_calls(ev, S, arm, Cs[S])
            vecs, kept = AN.offspring_vectors(es, dec)
            if not kept:
                continue
            lab, _ = AN.cluster_programs(vecs)
            seen = set()
            for e, l in zip(kept, lab):
                if int(l) in seen:
                    continue
                seen.add(int(l))
                g = gen[(S, arm, e["call"])]
                if e["F"] < min(g["parent_F"]):
                    out.append({"seed": S, "arm": arm, "call": e["call"], "F": e["F"], "parent_ids": g["parent_ids"],
                                "parent_F": g["parent_F"], "row": g})
    out.sort(key=lambda r: (r["call"], ARMS.index(r["arm"]), r["seed"]))
    return out[:N_OFFSPRING]


async def run() -> dict:
    gen, ev = AN.load_rows()
    dec = AN.load_decisions()
    sel = select_offspring(gen, ev, dec)
    logger.info(f"V5: {len(sel)} offspring selected")
    tok = EN.load_tokenizer()
    eng = EN.Engine(64)
    pool = sandbox.EvalPool(10, C.ROOT)
    cache = sandbox.EvalCache(pool)
    # parent decision vectors
    pid_vec = {}
    for (S, arm, c), e in ev.items():
        if e["valid"] and e.get("probe_row") is not None:
            pid_vec[f"S{S}-{arm}-c{c}"] = dec[e["probe_row"]]
    cor = json.loads((C.RESULTS / "corpus.json").read_text())
    cdec = np.load(C.DATA / "corpus_decisions.npy")
    names = [e["name"] for e in cor["entries"]]
    pid_vec["seed-BF"], pid_vec["seed-FF"] = cdec[names.index("BF")], cdec[names.index("FF")]
    rng = np.random.default_rng(55)
    client = httpx.AsyncClient(base_url=EN.BASE_URL, timeout=180)
    rows_path = C.RESULTS / "v5_rows.jsonl"
    results = [r for r in C.read_jsonl(rows_path)]
    done = {(r["seed"], r["arm"], r["call"]) for r in results}
    try:
        for o in sel:
            if (o["seed"], o["arm"], o["call"]) in done:
                continue
            g = o["row"]
            prompt_txt, prompt_ids = _prompt_ids(tok, gen, g)
            if g.get("branch") and not g["branch"].get("no_branch"):
                j = g["branch"]["j"]
                pre = g["r1_ids"][:j] + [g["branch"]["forced_id"]]
                rest = g["completion"][len(tok.decode(pre)):]
                comp_ids = pre + tok(rest, add_special_tokens=False)["input_ids"]
            else:
                comp_ids = tok(g["completion"], add_special_tokens=False)["input_ids"]
            body = {"model": C.SERVED_NAME, "prompt": prompt_ids + comp_ids, "max_tokens": 1, "temperature": 0.0,
                    "prompt_logprobs": 20}
            r = await client.post("/v1/completions", json=body)
            d = r.json()
            if "choices" not in d:
                raise RuntimeError(f"teacher-forcing request failed: {str(d)[:300]}")
            plp = d["choices"][0].get("prompt_logprobs") or []
            n0 = len(prompt_ids)
            H, amax, realised = [], [], []
            for t in range(len(comp_ids)):
                dd = plp[n0 + t] or {}
                h, a = entropy_from_dict(dd) if dd else (0.0, comp_ids[t])
                H.append(h)
                amax.append(a)
                realised.append(comp_ids[t])
            H = np.array(H)
            if len(H) == 0:
                continue
            p90 = float(np.percentile(H, 90))
            nonarg = [t for t in range(len(H)) if realised[t] != amax[t]]
            dpos = [t for t in nonarg if H[t] >= p90]
            if not dpos:
                rec0 = {**_meta(o), "decision_position": None, "n_nonargmax": len(nonarg)}
                results.append(rec0)
                C.append_jsonl(rows_path, rec0)
                continue
            tdec = dpos[0]
            ctrl_pool = [t for t in nonarg if t != tdec]
            tctl = int(rng.choice(ctrl_pool)) if ctrl_pool else None
            rec = {**_meta(o), "decision_position": tdec, "H_decision": float(H[tdec]), "p90": p90,
                   "control_position": tctl, "n_nonargmax": len(nonarg),
                   "realised_text": tok.decode([realised[tdec]]), "argmax_text": tok.decode([amax[tdec]])}
            for kind, t in (("decision", tdec), ("control", tctl)):
                if t is None:
                    continue
                prefix = prompt_ids + comp_ids[:t] + [amax[t]]
                reqs = [eng.complete(prefix, max_tokens=max(1, P.MAX_TOKENS - t - 1), temperature=1.0, top_p=1.0,
                                     seed=900000 + 1000 * len(results) + k + (500 if kind == "control" else 0),
                                     stop=P.STOPS) for k in range(N_CONT)]
                outs = await asyncio.gather(*reqs)
                head = tok.decode(comp_ids[:t] + [amax[t]])
                codes = [P.program_from_completion(head + x["text"]) for x in outs]
                futs = [cache.submit(c)[1] for c in codes]
                revs, valid = [], 0
                for f in futs:
                    res = await asyncio.wrap_future(f)
                    v = (res.get("probes") or {}).get("P10")
                    if res.get("error_type") == "ok" and v is not None:
                        valid += 1
                        vv = np.frombuffer(v, dtype=np.uint16)
                        ag = max(float(CL.agreement_matrix(vv, pid_vec[p])[0, 0]) for p in o["parent_ids"] if p in pid_vec)
                        revs.append(ag >= 0.95)
                rec[f"{kind}_n_valid"] = valid
                rec[f"{kind}_reversion"] = float(np.mean(revs)) if revs else None
            results.append(rec)
            C.append_jsonl(rows_path, rec)
            logger.info(f"V5 {o['arm']} S{o['seed']} c{o['call']}: pos {tdec} rev={rec.get('decision_reversion')} "
                        f"ctl={rec.get('control_reversion')}")
    finally:
        await client.aclose()
        await eng.close()
        pool.close()
    ok = [r for r in results if r.get("decision_reversion") is not None and r.get("control_reversion") is not None]
    diff = np.array([r["decision_reversion"] - r["control_reversion"] for r in ok])
    boot = np.random.default_rng(3)
    bs = [float(diff[boot.integers(0, len(diff), len(diff))].mean()) for _ in range(2000)] if len(diff) else []
    summ = {"n_offspring": len(results), "n_paired": len(ok),
            "decision_reversion_mean": float(np.mean([r["decision_reversion"] for r in ok])) if ok else None,
            "control_reversion_mean": float(np.mean([r["control_reversion"] for r in ok])) if ok else None,
            "diff_mean": float(diff.mean()) if len(diff) else None,
            "diff_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if bs else None,
            "note": "completion ids re-tokenised from text for non-branch arms; reversion = agreement >= 0.95 with a parent"}
    out = {"summary": summ, "offspring": results}
    C.write_json(C.RESULTS / "v5.json", out)
    logger.info(f"V5 summary: {summ}")
    return out


def _meta(o: dict) -> dict:
    return {k: o[k] for k in ("seed", "arm", "call", "F", "parent_ids", "parent_F")}


def _pid_key(pid: str):
    if pid.startswith("seed-"):
        return None
    S, arm, c = pid.split("-", 2)
    return (int(S[1:]), arm, int(c[1:]))


def _prompt_ids(tok, gen: dict, g: dict) -> tuple[str, list[int]]:
    """Rebuild the exact prompt from the parents' stored code (the prompt sha is checked)."""
    seeds = {"seed-BF": SE.seed_record("BF")["code"], "seed-FF": SE.seed_record("FF")["code"]}
    codes = []
    for pid in g["parent_ids"]:
        if pid in seeds:
            codes.append(seeds[pid])
        else:
            codes.append(gen[_pid_key(pid)]["code"])
    txt, ids = P.render(tok, P.user_turn(codes[0], codes[1], idea=(g["arm"] == "IDEA")))
    if C.sha256_text(txt) != g["prompt_sha256"]:
        logger.warning(f"prompt sha mismatch for {g['label']}")
    return txt, ids


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("v5")
    if not EN.wait_ready(60):
        raise RuntimeError("vLLM not up")
    asyncio.run(run())


if __name__ == "__main__":
    main()
