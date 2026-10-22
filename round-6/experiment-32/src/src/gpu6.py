#!/usr/bin/env python3
"""HF bf16 GPU daemon (Qwen3-8B instruct only; the exp8 CRN sampler in batches of B = 20 rows of one (unit,
template)). Tasks, picked in priority order whenever ready (time-only drop rules applied by the caller):

  twin_hf(u)   TWIN k 0-9 per template (50 CRN slots; iteration-5 units replicate their iteration-5 streams; batch
               pads are TWIN_EXTRA k 10-19)
  qlik(u)      teacher-forced scoring of the verified forced programs (src/qlik6.py), before the unit's commit
  esc1(u, A)   ESC stage 1: 8 fresh directions x alphas A x k 0-1 (N 10), ONLY after a verified unit commit
  conf(u)      ESC confirmation k 2-5 for every stage-1 passer (iteration-6 escape rule, src/labels6.py)
  pn(u, a)     PN: a fresh isotropic direction per sample, k 0-9 (N 50)
  gtn(u, a)    GTN at generated tokens 1-32 with teacher-forced shadow rows (src/gtn6.py), k 0-9 (N 50)
The daemon stops when data/STOP_GPU exists or the queue file data/gpu_queue.json says so."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import (B, DATA_DIR, EDIT_BLOCKS, LABELS, MODEL_ID, MODEL_REVISION, PRECISION, RAW, REALISED,  # noqa: E402
                  RESULTS_DIR, TEMPLATE_IDS, TIMING, append_jsonl, direction_seed, gtn_seed, read_json, read_jsonl,
                  setup_logging, utc_now)

STOP = DATA_DIR / "STOP_GPU"
QUEUE = DATA_DIR / "gpu_queue.json"


def torch_oom():
    import torch
    return torch.cuda.OutOfMemoryError


def raw_keys() -> set[tuple]:
    return {(r["unit"], r["template"], r["arm"], int(r["slot"])) for r in read_jsonl(RAW) if r["model_tag"] == "instruct"}


def labelled_keys() -> set[str]:
    return {l["key"] for l in read_jsonl(LABELS)}


class Daemon:
    def __init__(self) -> None:
        from engine5 import load_model
        from prompts5 import load_prompts
        from sampling5 import Runner

        self.tok, self.model = load_model(MODEL_ID, MODEL_REVISION, vram_fraction=0.95)
        self.pr = load_prompts()
        self.runner = Runner(self.model, self.tok, "instruct", self.pr)

    # ------------------------------------------------------------------ tasks
    def twin_hf(self, u: str) -> None:
        cells = {w: [("TWIN", list(range(10)))] for w in TEMPLATE_IDS}
        self.runner.run_cells(u, cells, stage="twin_hf")

    def qlik(self, u: str) -> None:
        from labels6 import all_final
        from qlik6 import score_unit
        from labels_view import frozen_catalogue
        rows = [r for r in all_final({u}) if str(r["arm"]).startswith("FORCED_")]
        progs: dict[str, list[dict]] = {}
        for m in frozen_catalogue(u):
            ok = sorted([r for r in rows if r["arm"] == f"FORCED_{m}" and r["passed"] and r["label"] == m and
                         r.get("code")], key=lambda r: (r["slot"], r["template"]))
            progs[m] = [{"key": r["key"], "code": r["code"]} for r in ok[:10]]
        score_unit(self.model, self.tok, u, self.pr, progs)

    def esc1(self, u: str, alphas: tuple[float, ...]) -> None:
        from commit5 import verify_unit_commit
        v = verify_unit_commit(u)
        if not v.get("ok"):
            raise RuntimeError(f"{u}: no verified commit before the first nudge: {v}")
        cells = {w: [(f"ESC_d{direction_seed(u, k)}_a{a}", [0, 1]) for a in alphas for k in range(8)]
                 for w in TEMPLATE_IDS}
        self.runner.run_cells(u, cells, stage="esc1")

    def conf(self, u: str, alphas: tuple[float, ...]) -> list[str]:
        from labels6 import all_final, committed, escape_table
        c = committed(u)
        d = c["default"]
        rows = all_final({u})
        if u.startswith("B") and not any(r["arm"] == "TWIN" and r.get("engine") == "hf" for r in rows):
            from quantities6 import iter5_twin_rows
            rows = rows + iter5_twin_rows(u)   # SCREEN twin baseline: iteration-5 HF k 0-9 + new vLLM k 10-39
        eng = (c.get("engine_check_twin") or {}).get("pass", True)
        tab = escape_table(rows, u, d, alphas, engine_ok=eng)
        need = [c["arm"] for c in tab["cells"] if c["needs_confirmation"]]
        logger.info(f"{u}: stage-1 passers needing confirmation: {need}")
        if need:
            cells = {w: [(arm, [2, 3, 4, 5]) for arm in need] for w in TEMPLATE_IDS}
            self.runner.run_cells(u, cells, stage="esc_conf")
        return need

    def pn(self, u: str, a: float) -> None:
        cells = {w: [(f"PN_a{a}", list(range(10)))] for w in TEMPLATE_IDS}
        self.runner.run_cells(u, cells, stage=f"pn_a{a}")

    def gtn(self, u: str, a: float) -> None:
        import numpy as np
        from ctx5 import r_at, rand_dir
        from engine5 import u_stream  # noqa: F401
        from gtn6 import sample_gtn
        from sampling5 import uniforms, HOOK_SHA
        from cfg5 import DECODING_STR, MODEL_ID as MID
        done = raw_keys()
        rq = {l: r_at(l) for l in EDIT_BLOCKS}
        arm = f"GTN_a{a}"
        ctx = self.runner.unit_ctx(u, False)
        for w in TEMPLATE_IDS:
            ks = [k for k in range(10) if (u, w, arm, k) not in done]
            if not ks:
                continue
            t0 = time.time()
            pre = ctx.twin(w)["pre"]
            p = self.pr[f"{u}|twin|-|{w}"]
            seeds = [gtn_seed(u, a, w, k) for k in ks]
            dirs = [rand_dir(s) for s in seeds]
            us = [uniforms(u, w, "TWIN", k, 1024) for k in ks]
            res = sample_gtn(self.model, self.tok, pre, us, dirs, a, rq)
            out = []
            for k, sd, r in zip(ks, seeds, res):
                out.append({"unit": u, "arm": arm, "template": w, "slot": k, "model_tag": "instruct", "model": MID,
                            "model_revision": MODEL_REVISION, "precision": PRECISION, "decoding": DECODING_STR,
                            "temperature": 1.0, "top_k": None, "thinking": False,
                            "site": "generated_tokens_1_32_blocks_12_23", "family": "GTN", "alpha": a,
                            "direction_seed": sd, "stage": f"gtn_a{a}", "prompt_pid": p["pid"],
                            "prompt_sha256": p["prompt_sha256"], "rel_err_max": r["gtn_rel_err_max"],
                            "text": self.tok.decode(r["token_ids"], skip_special_tokens=True),
                            "token_ids": r["token_ids"], "n_tokens": r["n_tokens"],
                            "finish_reason": r["finish_reason"], "fence_step": r["fence_step"],
                            "logprob_sum": r["logprob_sum"], "utc": utc_now(), "engine_check": False, "engine": "hf",
                            "kernel": "sdpa_bf16_torch2.8.0_transformers4.57.6", "hook_sha256": HOOK_SHA,
                            "batch_rows": 2 * len(ks), "gtn_rel_err_max": r["gtn_rel_err_max"],
                            "gtn_disp_mean": r["gtn_disp_mean"], "gtn_target_mean": r["gtn_target_mean"]})
            append_jsonl(RAW, out)
            append_jsonl(REALISED, [{"unit": u, "template": w, "arm": arm, "stage": f"gtn_a{a}", "utc": utc_now(),
                                     "rel_err_max": res[0]["gtn_rel_err_max"], "disp_mean": res[0]["gtn_disp_mean"],
                                     "target_mean": res[0]["gtn_target_mean"], "n_rows": len(ks)}])
            dt = time.time() - t0
            append_jsonl(TIMING, [{"stage": f"gtn_a{a}", "unit": u, "w": w, "arms": [arm], "model_tag": "instruct",
                                   "seconds": dt, "steps": res[0]["steps"], "utc": utc_now()}])
            logger.info(f"gtn {u}/{w} a{a}: {dt:.1f}s, {res[0]['steps']} steps, rel_err {res[0]['gtn_rel_err_max']}")


def pending_labels(u: str, fams: tuple[str, ...]) -> int:
    lab = labelled_keys()
    n = 0
    for r in read_jsonl(RAW):
        if r["unit"] == u and r.get("family") in fams:
            n += f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}" not in lab
    return n


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="JSON list of [task, unit, args] in priority order")
    a = ap.parse_args()
    setup_logging("gpu6")
    import json
    d = Daemon()
    done: set[str] = set()
    fails: dict[str, int] = {}
    t_start = time.time()
    while True:
        if STOP.exists():
            logger.warning("STOP_GPU found: exiting")
            break
        plan = json.loads(Path(a.plan).read_text())
        progressed = False
        for item in plan:
            task, u = item[0], item[1]
            args = item[2] if len(item) > 2 else None
            key = f"{task}|{u}|{args}"
            if key in done:
                continue
            ready, why = is_ready(task, u, args)
            if not ready:
                continue
            t0 = time.time()
            logger.info(f"=== task {key} ({why})")
            try:
                if task == "twin_hf":
                    d.twin_hf(u)
                elif task == "qlik":
                    d.qlik(u)
                elif task == "esc1":
                    d.esc1(u, tuple(args))
                elif task == "conf":
                    d.conf(u, tuple(args))
                elif task == "pn":
                    d.pn(u, float(args))
                elif task == "gtn":
                    d.gtn(u, float(args))
            except torch_oom() as e:
                logger.error(f"task {key}: CUDA OOM ({str(e)[:120]}); releasing contexts and retrying later")
                d.runner.release()
                from engine5 import free_cuda
                free_cuda()
                fails[key] = fails.get(key, 0) + 1
                if fails[key] < 3:
                    continue
            except RuntimeError as e:
                logger.error(f"task {key} failed: {e}")
            d.runner.release()
            from engine5 import free_cuda
            free_cuda()
            done.add(key)
            append_jsonl(RESULTS_DIR / "gpu_tasks.jsonl", [{"task": key, "seconds": round(time.time() - t0, 1),
                                                             "utc": utc_now()}])
            progressed = True
            break
        if not progressed:
            remaining = [f"{i[0]}|{i[1]}|{i[2] if len(i) > 2 else None}" for i in plan]
            if all(k in done for k in remaining):
                logger.info(f"all {len(done)} tasks done after {time.time() - t_start:.0f}s; waiting for new plan items")
            time.sleep(15)


def is_ready(task: str, u: str, args) -> tuple[bool, str]:
    from labels6 import committed
    if task == "twin_hf":
        return True, "always"
    if task == "qlik":
        res = read_json(RESULTS_DIR / "qlik.json") if (RESULTS_DIR / "qlik.json").exists() else {}
        if u in res:
            return False, "done"
        n = pending_labels(u, ("FORCED",))
        flag = DATA_DIR / f"FORCED_FINAL_{u}"
        return (n == 0 and flag.exists()), f"pending forced labels {n}, final flag {flag.exists()}"
    c = committed(u)
    if c is None:
        return False, "no commit"
    from commit5 import verify_unit_commit
    if task in ("esc1", "pn", "gtn"):
        v = verify_unit_commit(u)
        return bool(v.get("ok")) and c.get("enrol", True), f"commit ok {v.get('ok')}"
    if task == "conf":
        n_esc = sum(1 for r in read_jsonl(RAW) if r["unit"] == u and r.get("family") == "ESC" and r["slot"] in (0, 1)
                    and any(r["arm"].endswith(f"_a{float(a)}") for a in args))
        if n_esc < 8 * len(args) * 10:
            return False, f"ESC stage 1 incomplete ({n_esc})"
        n = pending_labels(u, ("ESC", "TWIN"))
        if n:
            return False, f"pending ESC labels {n}"
        from labels_view import adjudicate_pending
        adjudicate_pending([u])
        return True, "stage-1 labels complete"
    return False, "unknown"


if __name__ == "__main__":
    main()
