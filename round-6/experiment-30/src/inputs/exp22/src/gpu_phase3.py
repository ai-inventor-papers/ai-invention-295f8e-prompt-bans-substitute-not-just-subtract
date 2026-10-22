#!/usr/bin/env python3
"""GPU phase 3 (after sampling; forward passes only):
(1) C3b opening ladder: for every catalogue mode X of the 14 tasks with forced programs, X's modal OPENING among its
    correct, adherent forced programs = the response tokens of '```python\\n' + code from the first token through the
    first 16 tokens after the 'def solve' line (fewer if shorter; the forced programs store only the extracted code,
    so the fence is reconstructed -- flagged). Teacher-forced log-probability under each of the 5 neutral twins
    (batch 1), averaged -> results/opening_lp.json. Modes without a correct adherent program use the bench reference.
(2) Geometry: realised S-mean displacement vectors of the C2c arms (r at s 0.25/0.5/1.0, rand, rm, r2) and the
    sweep arms, per template (prefill only) -> states/disp_c2c_<task>.npz.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

from cfg4 import (DEFAULT4, E7, MOVABLE, PATH_TASKS, RESULTS_DIR, SEEDS_C2C, STATES_DIR, TASKS15,  # noqa: E402
                  TEMPLATE_IDS, read_jsonl, setup_logging, utc_now, write_json)
from describe import bench_dir  # noqa: E402


def forced_programs(task: str) -> list[dict[str, Any]]:
    if task in PATH_TASKS:
        et = {"T1": "t1", "T2": "t2"}[task]
        return [{"mode": r["j"], "label": r["label"], "passed": bool(r["passed"]), "code": r["code_raw"]}
                for r in read_jsonl(E7 / "data" / "forced_selected.jsonl") if r["task"] == et]
    return [{"mode": r["forced_mode"], "label": r["label"], "passed": bool(r["passed"]), "code": r["code"]}
            for r in read_jsonl(bench_dir(task) / "forced_programs.jsonl")]


def opening_ids(tok: Any, code: str, n_after: int = 16) -> list[int]:
    text = "```python\n" + code.strip("\n") + "\n```"
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    i = text.find("def solve")
    if i < 0:
        return ids[:48]
    eol = text.find("\n", i)
    eol = len(text) if eol < 0 else eol
    k = next((j for j, (a, b) in enumerate(offs) if b > eol), len(ids))
    return ids[:min(len(ids), k + n_after)]


@torch.no_grad()
def opening_lp(model: Any, tok: Any, prompts: dict) -> dict[str, Any]:
    from engine import clear_act_cache
    out: dict[str, Any] = {}
    for t in TASKS15:
        if t == "R2":
            continue
        fp = forced_programs(t)
        res: dict[str, Any] = {}
        modes = sorted({r["mode"] for r in fp})
        for m in modes:
            good = [r for r in fp if r["mode"] == m and r["label"] == m and r["passed"] and r["code"]]
            src = "modal opening of correct adherent forced programs"
            if not good:
                ref = bench_dir(t) / "references" / f"{m}.py" if t not in PATH_TASKS else None
                if ref is not None and ref.exists():
                    good = [{"code": ref.read_text()}]
                    src = "bench reference (no correct adherent forced program) [flagged]"
                else:
                    res[m] = {"lp": None, "source": "none available"}
                    continue
            ops = Counter(tuple(opening_ids(tok, r["code"])) for r in good)
            op, cnt = ops.most_common(1)[0]
            lps = []
            for w in TEMPLATE_IDS:
                p = prompts[f"{t}|twin|-|{w}|-"]
                ids = p["ids"] + list(op)
                clear_act_cache()
                h = model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False).last_hidden_state
                lg = torch.log_softmax(model.lm_head(h[0, p["P"] - 1:len(ids) - 1]).float(), dim=-1)
                tgt = torch.tensor(op, device=model.device)
                lps.append(float(lg.gather(1, tgt[:, None]).sum()))
                clear_act_cache()
            res[m] = {"lp": float(np.mean(lps)), "lp_per_template": lps, "n_tokens": len(op), "source": src,
                      "modal_count": cnt, "n_candidates": len(good), "fence_reconstructed": True}
        out[t] = res
        logger.info(f"opening lp {t}: {({m: round(v['lp'], 2) if v['lp'] is not None else None for m, v in res.items()})}")
    return out


@torch.no_grad()
def c2c_vectors(model: Any, prompts: dict) -> None:
    from ctx4 import TaskCtx
    from sampling4 import arm_spec
    for t in MOVABLE:
        ctx = TaskCtx(model, prompts, t)
        arms = ["C2C_r_s0.25", "C2C_r_s0.5", "C2C_r_s1.0", f"C2C_rand{SEEDS_C2C[t]}_s0.5", "C2C_rm_s0.5",
                "C2C_r2_s0.5", "SWEEP_r_a4.0", "SWEEP_r_a8.0"]
        keys, D = [], []
        for w in TEMPLATE_IDS:
            for a in arms:
                pre, rec = ctx.arm_prefill(w, arm_spec(ctx, a), want_vectors=True)
                del pre
                D.append(rec["_delta"])
                keys.append(f"{a}|{w}")
            ctx.release()
        np.savez(STATES_DIR / f"disp_c2c_{t}.npz", delta=np.stack(D), keys=np.array(keys))
        logger.info(f"c2c vectors {t}: {len(keys)}")


def main() -> None:
    setup_logging("gpu_phase3")
    from engine4 import load_model
    from prompts4 import load_prompts4
    torch.cuda.set_per_process_memory_fraction(0.97, 0)
    tok, model = load_model()
    prompts = load_prompts4()
    write_json(RESULTS_DIR / "opening_lp.json", {"utc": utc_now(), "by_task": opening_lp(model, tok, prompts)})
    c2c_vectors(model, prompts)
    write_json(RESULTS_DIR / "gpu_phase3_done.json", {"utc": utc_now()})


if __name__ == "__main__":
    main()
