#!/usr/bin/env python3
"""GPU process 2 on weight set Q (after weight set B): engine b (W8A16), diagnostics for a and b, and the
B-sensitivity control (engine a numerics at weight set B's batch size, tag 'aB').

W8A16 implementation choice (made before any b row, recorded in results/w8a16_impl.json): the fused Triton kernel
is used if, on captured real linear inputs at decode (M = 20) and prefill (M = P) shapes, it agrees with the
reference implementation torch.mm(x, codes_bf16^T, out_dtype=float32) * s_w to within 1 bf16 ulp on >= 99.9% of
outputs, has no non-finite value, and is faster per decode step; otherwise the reference implementation is used.
Order: b screen -> b PN -> diagnostics (a, b) -> b confirmations -> aB control.
"""

from __future__ import annotations

import time
from typing import Any

import torch
from loguru import logger

import c6  # noqa: F401
from c6 import (DEFAULTS, K_CONFIRM, K_PN, K_SCREEN, K_TWIN, POSCTRL_SEED, REPRO_SEEDS, RESULTS, SEEDS_POP,
                read_json, utc_now, write_json)


@torch.no_grad()
def choose_b_impl(model: Any, prompts: dict) -> dict[str, Any]:
    import engines as EN
    import gpu_tests6 as GT
    import w8a16_triton as WT

    EN.set_mode("a")
    ids = prompts["T2|twin|-|W3|-"]["ids"]
    caps = GT.capture_linear_inputs(model, ids, blocks=(2, 18, 33))
    rep: dict[str, Any] = {"per_input": {}}
    n_tot = n_le1 = 0
    nonfinite = False
    for key, x in caps.items():
        l = int(key.split("_")[0][1:])
        site = key.split("_", 1)[1]
        sub, lin = {"qkv_in": ("self_attn", "q_proj"), "o_in": ("self_attn", "o_proj"),
                    "gateup_in": ("mlp", "gate_proj"), "down_in": ("mlp", "down_proj")}[site]
        mod = getattr(getattr(model.model.layers[l], sub), lin)
        for M in (20, x.shape[0]):
            xx = x[:M].contiguous()
            codes = mod.wq_t.t()
            ref = (torch.mm(xx, codes.to(torch.bfloat16).t(), out_dtype=torch.float32) * mod.w_scale).to(torch.bfloat16)
            tri = WT.w8a16_mm(xx, codes, mod.w_scale)
            exact = ((xx.double() @ codes.double().t()) * mod.w_scale.double()).float().to(torch.bfloat16)
            u = GT.bf16_ulp_diff(tri, ref)
            nonfinite |= not bool(torch.isfinite(tri).all())
            n_tot += u.numel()
            n_le1 += int((u <= 1).sum())
            rep["per_input"][f"{key}|M{M}"] = {"eq_ref": float((tri == ref).float().mean()),
                                              "le1ulp_ref": float((u <= 1).float().mean()),
                                              "eq_fp64": float((tri == exact).float().mean()),
                                              "ref_eq_fp64": float((ref == exact).float().mean())}
    rep["frac_le1ulp"] = n_le1 / n_tot
    rep["nonfinite"] = nonfinite

    def step_time(impl: str) -> float:
        EN.MODE["b_impl"] = impl
        EN.set_mode("b")
        x = torch.randn(20, 1, 4096, device="cuda", dtype=torch.bfloat16)
        for _ in range(2):
            for layer in model.model.layers:
                for mod in (layer.self_attn.q_proj, layer.mlp.gate_proj, layer.mlp.down_proj):
                    mod(x if mod is not layer.mlp.down_proj else torch.randn(20, 1, 12288, device="cuda",
                                                                              dtype=torch.bfloat16))
        torch.cuda.synchronize()
        t0 = time.time()
        for layer in model.model.layers:
            layer.self_attn.q_proj(x), layer.self_attn.k_proj(x), layer.self_attn.v_proj(x)
            layer.self_attn.o_proj(x), layer.mlp.gate_proj(x), layer.mlp.up_proj(x)
            layer.mlp.down_proj(torch.randn(20, 1, 12288, device="cuda", dtype=torch.bfloat16))
        torch.cuda.synchronize()
        return time.time() - t0
    rep["linear_time_per_decode_step_s"] = {"cast": step_time("cast"), "triton": step_time("triton")}
    ok = (rep["frac_le1ulp"] >= 0.999 and not nonfinite
          and rep["linear_time_per_decode_step_s"]["triton"] < rep["linear_time_per_decode_step_s"]["cast"])
    rep["chosen"] = "triton" if ok else "cast"
    EN.MODE["b_impl"] = rep["chosen"]
    EN.set_mode("a")
    rep["utc"] = utc_now()
    return rep


def catalogue(task: str) -> set[str]:
    import cfg4  # noqa: F401
    from screen import catalogue as cat
    return set(cat(task))


def main(deadline_min: float = 60.0) -> None:
    import engines as EN
    import gpu_tests6 as GT
    from escape import needs_confirmation
    from gen import PRECISION, Runner
    from prompts4 import load_prompts4
    from rows6 import engine_rows, wait_labels

    t_start = time.time()
    deadline = t_start + deadline_min * 60
    tok, model = EN.load_q()
    prompts = load_prompts4()
    log: dict[str, Any] = {"start_utc": utc_now(), "deadline_min": deadline_min, "stages": []}
    try:
        imp = choose_b_impl(model, prompts)
    except Exception as e:  # noqa: BLE001 - an untested fused kernel must never cost engine b: fall back to the reference
        logger.exception(f"Triton W8A16 validation failed: {e}")
        EN.MODE["b_impl"] = "cast"
        EN.set_mode("a")
        imp = {"chosen": "cast", "error": f"{type(e).__name__}: {str(e)[:300]}", "utc": utc_now(),
               "frac_le1ulp": None, "linear_time_per_decode_step_s": None}
    write_json(RESULTS / "w8a16_impl.json", imp)
    logger.info(f"W8A16 impl: {imp['chosen']} frac<=1ulp {imp['frac_le1ulp']} times {imp['linear_time_per_decode_step_s']}")
    PRECISION["b"] += f" [impl: {imp['chosen']}]"
    ut: dict[str, Any] = {"utc": utc_now()}
    for name, fn in (("U3_U5_b", lambda: GT.u3_u5(model, tok, prompts, "b", B=20)),
                     ("U4_b", lambda: GT.u4(model, prompts, "b")),
                     ("U1_relative", lambda: GT.u1(model, prompts["T10|twin|-|W1|-"]["ids"]))):
        try:
            ut[name] = fn()
        except Exception as e:  # noqa: BLE001 - non-decisive tests are recorded, never fatal
            logger.exception(f"{name} failed: {e}")
            ut[name] = {"error": str(e)[:300]}
        torch.cuda.empty_cache()
    write_json(RESULTS / "unit_tests_q2.json", ut)
    logger.info(f"U b: {ut.get('U3_U5_b')} {ut.get('U4_b')}")

    def stage(name, fn):
        t0 = time.time()
        if time.time() > deadline:
            log["stages"].append({"stage": name, "status": "dropped (deadline)"})
            write_json(RESULTS / "gpu_q2_log.json", log)
            return
        try:
            res = fn()
            status = "done"
        except Exception as e:  # noqa: BLE001 - one failed stage must not cost the next ones
            logger.exception(f"stage {name} failed: {e}")
            res, status = None, f"error: {type(e).__name__}: {str(e)[:200]}"
            torch.cuda.empty_cache()
        log["stages"].append({"stage": name, "status": status, "minutes": (time.time() - t0) / 60, "result": res})
        write_json(RESULTS / "gpu_q2_log.json", log)

    def b_screen():
        EN.set_mode("b")
        run = Runner(model, tok, prompts, "b", B=20)
        for task in ("T10", "T2"):
            cells = [("TWIN", K_TWIN)] + [(f"POP_d{s}_a2.0", K_SCREEN) for s in SEEDS_POP]
            if task == "T2":
                cells.append((f"POP_d{POSCTRL_SEED}_a1.0", [0, 1, 2, 3]))
            run.run_cells(task, cells, "S1S3_screen", deadline=deadline)

    def b_pn():
        EN.set_mode("b")
        run = Runner(model, tok, prompts, "b", B=20)
        for task in ("T10", "T2"):
            run.run_cells(task, [("PN_a1", K_PN), ("PN_a2", K_PN)], "S4_PN", deadline=deadline)

    def diags():
        import diag6
        return diag6.run_weight_set(model, tok, prompts, ("a", "b"), deadline)

    def a_bsmall():
        bl = read_json(RESULTS / "gpu_b_log.json")
        Bs = int(bl["probe"]["B"])
        PRECISION["aB"] = PRECISION["a"] + f" at B = {Bs} (B-sensitivity control)"
        EN.set_mode("a")
        run = Runner(model, tok, prompts, "aB", B=Bs)
        for task in ("T10",):   # T10 only (time); U3 already shows bitwise B-invariance for B >= 10 (Q) / >= 3 (B)
            run.run_cells(task, [("TWIN", K_TWIN)] + [(f"POP_d{s}_a2.0", K_SCREEN) for s in REPRO_SEEDS],
                          "BSENS", deadline=deadline)
        return {"B": Bs}

    def b_confirm():
        EN.set_mode("b")
        run = Runner(model, tok, prompts, "b", B=20)
        todo = {}
        for task in ("T10", "T2"):
            wait_labels("b", task, timeout=600)
            dirs = needs_confirmation(engine_rows("b", task), SEEDS_POP, catalogue(task), DEFAULTS[task], 2.0)
            todo[task] = dirs
            if dirs:
                run.run_cells(task, [(f"POP_d{s}_a2.0", K_CONFIRM) for s in dirs], "S3_confirm", deadline=deadline)
        return todo

    stage("b screen", b_screen)
    stage("b PN", b_pn)
    stage("diagnostics Q", diags)
    stage("b confirm", b_confirm)
    stage("aB control", a_bsmall)
    log["end_utc"] = utc_now()
    write_json(RESULTS / "gpu_q2_log.json", log)
    logger.info("gpu_q2 done")
