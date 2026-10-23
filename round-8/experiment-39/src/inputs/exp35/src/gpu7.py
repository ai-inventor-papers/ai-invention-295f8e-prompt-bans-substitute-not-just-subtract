#!/usr/bin/env python3
"""GPU stages of iteration 7 (one process per call; every stage resumes from its files).

  tests      G1 memory probe -> predictions/hardware.json; G2 CRN determinism; G3 batch invariance; U2 replay; G5 hooks
  twins      S0 twins: N = 100 per mixed unit (slots 0-19 x W1-W5, T 1.0, top-p 1); collapsed twins T1/T10 and the
             engine-check cells T2/T03 (N = 20 each, iteration-6 slot keys)
  scan       S1 prefix resampling (8 continuations per scanned prefix length), refine, confirm (forks.py drives it)
  predict    S2 teacher-forced openings, fork logits, token conditionals, collapsed margins, S4 teacher-forced numbers
  sweep      S3 same-seed temperature sweep (N = 50 per cell x 8 cells per unit)
  collapsed  E2 collapsed tasks at T 1.3 (N = 20 each)
  s4         S4(a) pushes and S4(b) exchange arms
  geometry   F7 fork-token residual states
Generated rows -> data/samples_raw.jsonl (programs) and data/continuations.jsonl (prefix resampling); labels via the
label worker subprocess (src/label7.py) -> data/labels.jsonl.
"""

from __future__ import annotations

import gc
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine7 as EN  # noqa: E402
from cfg7 import (CACHE_DIR, COLLAPSED_INFO, CONTS, DATA_DIR, LABELS, PRED_DIR, PRECISION, RESULTS_DIR, ROOT,  # noqa
                  SAMPLES_RAW, TEMPLATES, TWIN_SLOTS, UNITS, append_jsonl, read_json, read_jsonl, setup_logging,
                  stable_seed, u_stream, utc_now, write_json)
from prompts7 import load_prompts  # noqa: E402

STATE: dict[str, Any] = {"pre": {}}


# ------------------------------------------------------------------------------------------------ generation
def fence_of(unit: str) -> str:
    return COLLAPSED_INFO[unit]["fence"] if unit in COLLAPSED_INFO else "bench"


def max_new_of(unit: str) -> int:
    return COLLAPSED_INFO[unit]["max_new"] if unit in COLLAPSED_INFO else UNITS[unit]["max_new"]


def done_sids(path: Path = SAMPLES_RAW) -> set[str]:
    return {r["sid"] for r in read_jsonl(path)}


def get_prefill(model: Any, key: str, ids: list[int], edits: dict | None = None) -> dict[str, Any]:
    if key not in STATE["pre"]:
        STATE["pre"][key] = EN.prefill(model, ids, edits=edits)
    return STATE["pre"][key]


def clear_prefills() -> None:
    STATE["pre"].clear()
    gc.collect()
    torch.cuda.empty_cache()


def run_specs(model: Any, tok: Any, specs: list[dict[str, Any]], batch: int, tag: str,
              out_path: Path = SAMPLES_RAW) -> list[dict[str, Any]]:
    """specs: {sid, unit, arm, cell, template, slot, ukey, T, top_k, max_new, pre_key, ids, edits?, extra...}.
    Batches of `batch` rows in spec order; rows sharing pre_key share one prefill."""
    have = done_sids(out_path)
    todo = [s for s in specs if s["sid"] not in have]
    out_all = []
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        t0 = time.time()
        rows = []
        for s in part:
            if s.get("edits_fn") is not None and s["pre_key"] not in STATE["pre"]:
                ed = s["edits_fn"]()                     # built lazily, freed right after its prefill
                pre = get_prefill(model, s["pre_key"], s["ids"], ed)
                del ed
            else:
                pre = get_prefill(model, s["pre_key"], s["ids"], s.get("edits"))
            rows.append({"pre": pre, "u": u_stream(*s["ukey"]), "T": s["T"], "top_k": s["top_k"], "top_p": 1.0,
                         "max_new": s["max_new"], "fence": True})
        res = EN.decode_rows(model, rows, tok, fence_kind=fence_of(part[0]["unit"]))
        if any(s.get("edits_fn") is not None for s in part):
            for s in part:
                STATE["pre"].pop(s["pre_key"], None)
            del rows
            torch.cuda.empty_cache()
        dt = time.time() - t0
        recs = []
        for s, r in zip(part, res):
            rec = {k: v for k, v in s.items() if k not in ("ids", "edits", "edits_fn")}
            rec.update({"P": len(s["ids"]), "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
                        "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"],
                        "text": tok.decode(r["token_ids"], skip_special_tokens=True), "batch_B": len(part),
                        "engine_path": r["engine_path"], "precision": PRECISION, "utc": utc_now()})
            recs.append(rec)
        append_jsonl(out_path, recs)
        out_all += recs
        steps = res[0]["steps"]
        append_jsonl(RESULTS_DIR / "timing.jsonl", [{"tag": tag, "rows": len(part), "steps": steps,
                                                     "seconds": round(dt, 2), "utc": utc_now()}])
        logger.info(f"[{tag}] batch {i // batch + 1}/{(len(todo) + batch - 1) // batch}: {len(part)} rows, "
                    f"{steps} steps, {dt:.1f}s")
    return out_all


def label_pending(rows_path: Path = SAMPLES_RAW, labels_path: Path = LABELS) -> int:
    """Label every program row without a label (subprocess: src/label7.py)."""
    have = {r["sid"] for r in read_jsonl(labels_path)}
    todo = [{"sid": r["sid"], "unit": r["unit"], "text": r["text"]} for r in read_jsonl(rows_path)
            if r["sid"] not in have]
    if not todo:
        return 0
    tmp_in = CACHE_DIR / "tmp" / f"label_in_{int(time.time() * 1000)}.jsonl"
    tmp_out = tmp_in.with_name(tmp_in.name.replace("label_in", "label_out"))
    tmp_in.parent.mkdir(parents=True, exist_ok=True)
    tmp_in.write_text("".join(json.dumps(r) + "\n" for r in todo))
    t0 = time.time()
    pr = subprocess.run([sys.executable, str(ROOT / "src" / "label7.py"), str(tmp_in), str(tmp_out)],
                        capture_output=True, text=True, timeout=3600)
    if pr.returncode != 0:
        logger.error(f"label worker failed: {pr.stderr[-2000:]}")
        raise RuntimeError("label worker failed")
    res = read_jsonl(tmp_out)
    append_jsonl(labels_path, [{**r, "utc": utc_now()} for r in res])
    tmp_in.unlink(missing_ok=True)
    tmp_out.unlink(missing_ok=True)
    logger.info(f"labelled {len(res)} rows in {time.time() - t0:.1f}s")
    return len(res)


# ------------------------------------------------------------------------------------------------ specs
def prog_spec(unit: str, arm: str, cell: str, w: str, slot: int, prompt: dict[str, Any], T: float, top_k: int,
              pre_key: str | None = None, ukey: tuple | None = None, **extra: Any) -> dict[str, Any]:
    return {"sid": f"{unit}|{arm}|{cell}|{w}|{slot}", "unit": unit, "arm": arm, "cell": cell, "template": w,
            "slot": slot, "ukey": list(ukey or ("iter7T", unit, w, slot)), "T": T, "top_k": top_k,
            "max_new": max_new_of(unit), "pre_key": pre_key or f"{unit}|{w}|{prompt['kind']}",
            "ids": prompt["ids"], "prompt_kind": prompt["kind"], "prompt_sha256": prompt["prompt_sha256"], **extra}


# ------------------------------------------------------------------------------------------------ stages
def stage_tests(model: Any, tok: Any, info: dict[str, Any]) -> None:
    import transformers
    import replay
    P = load_prompts()
    hw = {"gpu": torch.cuda.get_device_name(0), "total_vram_GB": info["total_vram_GB"],
          "free_vram_after_load_GB": info["free_vram_after_GB"], "free_vram_before_load_GB": info["free_vram_before_GB"],
          "driver_cuda": torch.version.cuda, "torch": torch.__version__, "transformers": transformers.__version__,
          "precision": PRECISION, "cpu_embedding": info["cpu_embedding"], "engine": "hf_bf16 (iteration-6 engine5)",
          "batch_sizes": {u: UNITS[u]["batch"] for u in UNITS}, "max_new": {u: max_new_of(u) for u in UNITS},
          "planned_gpu": "RTX A4500 (20 GB)", "utc": utc_now()}
    write_json(PRED_DIR / "hardware.json", hw)
    rep: dict[str, Any] = {}
    tw = P[("B3", "W1", "twin")]
    # G2 CRN determinism: the same 10 slots twice (64 new tokens)
    def gen(B: int, slots: list[int], max_new: int = 64) -> list[list[int]]:
        out = []
        for i in range(0, len(slots), B):
            pre = EN.prefill(model, tw["ids"])
            rows = [{"pre": pre, "u": u_stream("iter7test", s), "T": 1.0, "top_k": 0, "top_p": 1.0,
                     "max_new": max_new, "fence": True} for s in slots[i:i + B]]
            out += [r["token_ids"] for r in EN.decode_rows(model, rows, tok, fence_kind="bench")]
        return out
    a = gen(10, list(range(10)))
    b = gen(10, list(range(10)))
    rep["G2_crn_determinism_identical"] = sum(x == y for x, y in zip(a, b)) / 10
    # G3 batch invariance: B=1 vs B=16 (first 10 rows)
    c = gen(1, list(range(10)))
    d = gen(16, list(range(16)))[:10]
    first_div = []
    for x, y in zip(c, d):
        j = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), None)
        first_div.append(j)
    rep["G3_B1_vs_B16_identical_rows"] = sum(j is None for j in first_div) / 10
    rep["G3_first_divergence_index"] = first_div
    rep["G3_B10_vs_B16_identical_rows"] = sum(x == y for x, y in zip(a, d)) / 10
    # U2 replay vs engine transform on real logits (prefill + 63 decode steps of slot 0 -> 64 logit vectors)
    pre = EN.prefill(model, tw["ids"])
    ids = tw["ids"] + a[0][:63]
    tf = EN.teacher_force(model, ids, len(tw["ids"]))
    Z = tf["logits"].double()                                    # [64, V]
    rng = np.random.default_rng(7)
    n_ok = n = 0
    mism = []
    for T in (0.3, 0.7, 1.0, 1.3):
        for k in (0, 10):
            for _ in range(10000 // 8):
                i = int(rng.integers(0, Z.shape[0]))
                uu = float(rng.random())
                z = Z[i:i + 1]
                pr = EN.step_probs5(z, torch.tensor([[T]], dtype=torch.float64, device=z.device),
                                    torch.tensor([k], device=z.device), torch.ones(1, dtype=torch.float64,
                                                                                      device=z.device), k > 0, False)
                t_eng = int(EN.inverse_cdf(pr, torch.tensor([uu], dtype=torch.float64, device=z.device))[0])
                t_rep = replay.pick(Z[i].cpu().numpy(), uu, T, k)
                n += 1
                n_ok += t_eng == t_rep
                if t_eng != t_rep and len(mism) < 5:
                    mism.append({"T": T, "k": k, "u": uu, "engine": t_eng, "replay": t_rep})
    rep["U2_replay_agreement"] = n_ok / n
    rep["U2_n"] = n
    rep["U2_mismatches"] = mism
    # G4-lite: teacher-forced vs prefill read logits at the first generated position
    rep["G4_prefill_vs_tf_first_pos_max_abs_logit_diff"] = float((pre["r_logits"] - tf["logits"][0]).abs().max())
    # G5 identity hooks: twin->twin exchange == twin; alpha 0 push == twin (prefill read logits)
    S = torch.arange(tw["p1"], tw["spec_end"], device=EN.dev_of(model))
    H: dict[int, torch.Tensor] = {}
    pre_c = EN.prefill(model, tw["ids"], capture=EN.capture_hooks(H, S, list(range(36))))
    pre_x = EN.prefill(model, tw["ids"], edits=EN.set_rows_edit(S, {l: H[l] for l in range(36)}))
    rep["G5_twin_into_twin_exchange_max_abs_logit_diff"] = float((pre_c["r_logits"] - pre_x["r_logits"]).abs().max())
    u0 = torch.from_numpy(np.load(ROOT / "inputs" / "iter4_exp22" / "directions" / "rand_9101.npy")).float().to(S.device)
    n0 = {l: torch.ones(len(S), device=S.device) for l in range(12, 24)}
    pre_p = EN.prefill(model, tw["ids"], edits=EN.push_edits(tw["p1"], tw["spec_end"], u0, n0,
                                                             {l: H[l] for l in range(12, 24)}, 0.0))
    rep["G5_alpha0_push_max_abs_logit_diff"] = float((pre_c["r_logits"] - pre_p["r_logits"]).abs().max())
    norms = {l: torch.full((len(S),), 3.0, device=S.device) for l in range(36)}
    _, real = EN.mr_edit(S, {l: H[l] for l in range(36)}, norms, 123)
    rep["G5_mr_norm_rel_err_max"] = max(abs(v - 3.0) / 3.0 for v in real.values())
    rep["utc"] = utc_now()
    write_json(RESULTS_DIR / "gpu_tests.json", rep)
    logger.info(f"GPU tests: {rep}")
    del pre, pre_c, pre_x, pre_p, H, tf, Z
    clear_prefills()


def stage_twins(model: Any, tok: Any, units: list[str]) -> None:
    P = load_prompts()
    for u in units:
        if u in UNITS:
            for w in TEMPLATES:
                specs = [prog_spec(u, "TWIN", "TWIN", w, s, P[(u, w, "twin")], 1.0, 0) for s in TWIN_SLOTS]
                run_specs(model, tok, specs, len(TWIN_SLOTS), f"twin:{u}:{w}")
                clear_prefills()
        else:
            # collapsed twins and engine check: iteration-6 slot keys (crn_key task|w|k, u_stream(task, w, k, n=1536))
            for w in ("W1", "W2", "W3", "W5"):
                specs = [prog_spec(u, "TWIN6", "TWIN6", w, k, P[(u, w, "twin")], 1.0, 0, ukey=(u, w, k))
                         for k in range(5)]
                run_specs(model, tok, specs, 10 if u in ("T03", "T10") else (8 if u == "T2" else 6),
                          f"twin6:{u}:{w}")
                clear_prefills()
    label_pending()


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("stages")
    ap.add_argument("--units", default="B3,A3,B6")
    args = ap.parse_args()
    setup_logging("gpu7")
    torch.manual_seed(0)
    tok, model, info = EN.load_model()
    units = [u for u in args.units.split(",") if u]
    for st in args.stages.split(","):
        t0 = time.time()
        logger.info(f"=== stage {st} ===")
        if st == "tests":
            stage_tests(model, tok, info)
        elif st == "twins":
            stage_twins(model, tok, units)
        else:
            import stages7
            stages7.run_stage(st, model, tok, units)
        logger.info(f"=== stage {st} done in {time.time() - t0:.0f}s ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("gpu7 failed")
        raise
