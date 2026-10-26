#!/usr/bin/env python3
"""S0-GPU validation (non-decisive). Weight set Q: U1 (native vs emulated vs fp64 reference of the _scaled_mm
semantics), U2 (e4m3 round trip; weight quantiser == FP8Linear), U3 (batch-mate invariance at fixed B; logit change
over B in {1, B/2, B}), U4 (alpha 0 -> bitwise twin; alpha 2 -> displacement 2 n along u), U5 (CRN determinism).
Weight set B runs U3/U4/U5 for c and d."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from loguru import logger

import c6  # noqa: F401
import engines as EN
from c6 import MODEL_ID, MODEL_REVISION


def bf16_ulp_diff(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Distance in bf16 representable steps (monotone integer mapping of the bit patterns)."""
    def key(t):
        i = t.contiguous().view(torch.int16).to(torch.int32)
        return torch.where(i < 0, -(i & 0x7FFF), i)
    return (key(a) - key(b)).abs()


def u2_codes() -> dict[str, Any]:
    codes = torch.arange(256, dtype=torch.uint8).view(torch.float8_e4m3fn)
    f, b = codes.float(), codes.to(torch.bfloat16).float()
    ok = bool(((f == b) | (f.isnan() & b.isnan())).all())
    return {"all_256_e4m3_codes_exact_in_bf16": ok}


def u2_weights(model: Any) -> dict[str, Any]:
    from safetensors import safe_open

    from cfg import model_path

    path = model_path()
    idx = __import__("json").load(open(f"{path}/model.safetensors.index.json"))["weight_map"]
    names = [("model.layers.0.self_attn.q_proj.weight", 0, "self_attn", "q_proj"),
             ("model.layers.17.mlp.gate_proj.weight", 17, "mlp", "gate_proj"),
             ("model.layers.35.mlp.down_proj.weight", 35, "mlp", "down_proj")]
    out = {}
    for name, l, sub, lin in names:
        with safe_open(f"{path}/{idx[name]}", framework="pt", device="cpu") as f:
            W = f.get_tensor(name).to("cuda")
        q, s = EN.weight_quant(W)
        mod = getattr(getattr(model.model.layers[l], sub), lin)
        same_codes = bool(torch.equal(q.view(torch.uint8), mod.wq_t.t().contiguous().view(torch.uint8)))
        same_scale = bool(torch.equal(s.t().contiguous(), mod.w_scale))
        out[name] = {"codes_bitwise_equal": same_codes, "scales_bitwise_equal": same_scale}
        del W, q, s
    return out


def capture_linear_inputs(model: Any, ids: list[int], blocks=(3, 17, 30)) -> dict[str, torch.Tensor]:
    sites = {"qkv_in": ("self_attn", "q_proj"), "o_in": ("self_attn", "o_proj"), "gateup_in": ("mlp", "gate_proj"),
             "down_in": ("mlp", "down_proj")}
    got: dict[str, torch.Tensor] = {}
    hs = []
    for l in blocks:
        for sname, (sub, lin) in sites.items():
            mod = getattr(getattr(model.model.layers[l], sub), lin)

            def pre(m, args, key=f"b{l}_{sname}"):
                got[key] = args[0].detach().reshape(-1, args[0].shape[-1]).clone()
            hs.append(mod.register_forward_pre_hook(pre))
    try:
        with torch.no_grad():
            model.model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
    finally:
        for h in hs:
            h.remove()
    return got


@torch.no_grad()
def u1(model: Any, ids: list[int]) -> dict[str, Any]:
    """Emulated W8A8 and native kernel vs an fp64 reference of the _scaled_mm semantics."""
    EN.set_mode("a")
    caps = capture_linear_inputs(model, ids)
    res: dict[str, Any] = {}
    gen = torch.Generator(device="cuda").manual_seed(1234)
    xr = torch.randn(64, 4096, generator=gen, device="cuda")
    xr[:, [7, 300, 2049, 4000]] *= 60.0
    caps["random_outlier_x"] = xr.to(torch.bfloat16)
    tot = {"native_vs_ref_eq": 0, "emul_vs_ref_eq": 0, "emul_vs_native_eq": 0, "n": 0}
    maxulp = {"native_vs_ref": 0, "emul_vs_ref": 0, "emul_vs_native": 0}
    for key, x in caps.items():
        if key == "random_outlier_x":
            mod = model.model.layers[17].self_attn.q_proj
        else:
            l = int(key.split("_")[0][1:])
            site = key.split("_", 1)[1]
            sub, lin = {"qkv_in": ("self_attn", "q_proj"), "o_in": ("self_attn", "o_proj"),
                        "gateup_in": ("mlp", "gate_proj"), "down_in": ("mlp", "down_proj")}[site]
            mod = getattr(getattr(model.model.layers[l], sub), lin)
        EN.set_mode("a")
        y_nat = mod(x)
        EN.set_mode("a_emul")
        y_emu = mod(x)
        EN.set_mode("a")
        q, s = EN.actq(x)
        W8 = mod.wq_t.t()
        ref = ((q.double() @ W8.double().t()) * s.double() * mod.w_scale.double()).float().to(torch.bfloat16)
        n = ref.numel()
        big = ref.float().abs() >= 1e-2 * ref.float().abs().max()
        rel_nat = ((y_nat.float() - ref.float()).abs() / ref.float().abs().clamp(min=1e-30))[big]
        rel_emu = ((y_emu.float() - ref.float()).abs() / ref.float().abs().clamp(min=1e-30))[big]
        r_extra = {"le1ulp_native_vs_ref_nonsmall": float((bf16_ulp_diff(y_nat, ref)[big] <= 1).float().mean()),
                   "le1ulp_emul_vs_ref_nonsmall": float((bf16_ulp_diff(y_emu, ref)[big] <= 1).float().mean()),
                   "median_rel_err_native": float(rel_nat.median()), "p99_rel_err_native": float(rel_nat.quantile(0.99)),
                   "median_rel_err_emul": float(rel_emu.median()), "p99_rel_err_emul": float(rel_emu.quantile(0.99)),
                   "rms_rel_err_native_vs_ref": float(((y_nat.float() - ref.float()).pow(2).mean() /
                                                       ref.float().pow(2).mean()).sqrt())}
        r = {"n": n, **r_extra, "native_vs_ref_eq": float((y_nat == ref).float().mean()),
             "emul_vs_ref_eq": float((y_emu == ref).float().mean()),
             "emul_vs_native_eq": float((y_emu == y_nat).float().mean()),
             "max_ulp_native_vs_ref": int(bf16_ulp_diff(y_nat, ref).max()),
             "max_ulp_emul_vs_ref": int(bf16_ulp_diff(y_emu, ref).max()),
             "max_ulp_emul_vs_native": int(bf16_ulp_diff(y_emu, y_nat).max())}
        res[key] = r
        tot["n"] += n
        for k2 in ("native_vs_ref_eq", "emul_vs_ref_eq", "emul_vs_native_eq"):
            tot[k2] += r[k2] * n
        maxulp["native_vs_ref"] = max(maxulp["native_vs_ref"], r["max_ulp_native_vs_ref"])
        maxulp["emul_vs_ref"] = max(maxulp["emul_vs_ref"], r["max_ulp_emul_vs_ref"])
        maxulp["emul_vs_native"] = max(maxulp["emul_vs_native"], r["max_ulp_emul_vs_native"])
    summary = {k: tot[k] / tot["n"] for k in ("native_vs_ref_eq", "emul_vs_ref_eq", "emul_vs_native_eq")}
    for k in ("le1ulp_native_vs_ref_nonsmall", "le1ulp_emul_vs_ref_nonsmall", "rms_rel_err_native_vs_ref",
              "p99_rel_err_native", "p99_rel_err_emul"):
        summary[k + "_worst_input"] = (min if k.startswith("le1ulp") else max)(v[k] for v in res.values())
    summary["max_ulp"] = maxulp
    summary["note"] = ("reference = exact e4m3 products summed in fp64, x s_x x s_w, rounded fp64->fp32->bf16 "
                       "(double rounding possible in rare ties); 12 real linear inputs (blocks 3/17/30 x 4 sites, "
                       "T10 W1 twin prefill) + one random 64x4096 input with 4 outlier channels (x60)")
    return {"summary": summary, "per_input": res}


@torch.no_grad()
def u4(model: Any, prompts: dict, engine_mode: str, task: str = "T10", w: str = "W1") -> dict[str, Any]:
    from ctx4 import TaskCtx, ban_unit, push_spec, rand_dir

    EN.set_mode(engine_mode)
    ctx = TaskCtx(model, prompts, task)
    tw = ctx.twin(w)
    pre0, rec0 = ctx.arm_prefill(w, push_spec(model.device, rand_dir(9101), ban_unit(task), 0.0))
    same_logits = bool(torch.equal(pre0["r_logits"], tw["pre"]["r_logits"]))
    same_kv = all(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]) for a, b in zip(pre0["kv"], tw["pre"]["kv"]))
    pre2, rec2 = ctx.arm_prefill(w, push_spec(model.device, rand_dir(9101), ban_unit(task), 2.0))
    ctx.release()
    return {"alpha0_bitwise_twin_logits": same_logits, "alpha0_bitwise_twin_kv": bool(same_kv),
            "alpha2_rel_err_max": rec2["rel_err_max"], "alpha2_disp_S_b23": rec2["disp_smean_norm"][23],
            "alpha2_disp_S_b35": rec2["disp_smean_norm"][35], "alpha2_disp_R_b35": rec2["disp_R_norm"][35]}


@torch.no_grad()
def u3_u5(model: Any, tok: Any, prompts: dict, engine_mode: str, B: int, task: str = "T10",
          w: str = "W1") -> dict[str, Any]:
    """U5: the same batch twice -> identical tokens. U3: twin rows with different batch-mates (fixed B) -> identical;
    max |d logit| of one decode step for the same row at batch sizes {1, B/2, B}."""
    from ctx4 import TaskCtx, ban_unit, push_spec, rand_dir
    from engine4 import sample, u_stream

    EN.set_mode(engine_mode)
    ctx = TaskCtx(model, prompts, task)
    tw = ctx.twin(w)
    h = B // 2
    ks = list(range(h))
    p1, _ = ctx.arm_prefill(w, push_spec(model.device, rand_dir(9101), ban_unit(task), 2.0))
    p2, _ = ctx.arm_prefill(w, push_spec(model.device, rand_dir(9102), ban_unit(task), 2.0))
    gx = [{"pre": tw["pre"], "us": [u_stream(task, w, k) for k in ks]},
          {"pre": p1, "us": [u_stream(task, w, k) for k in range(B - h)]}]
    gy = [{"pre": tw["pre"], "us": [u_stream(task, w, k) for k in ks]},
          {"pre": p2, "us": [u_stream(task, w, k) for k in range(B - h)]}]
    rx = sample(model, tok, gx, fence="bench", max_new=128)
    rx2 = sample(model, tok, gx, fence="bench", max_new=128)
    ry = sample(model, tok, gy, fence="bench", max_new=128)
    u5 = all(a["token_ids"] == b["token_ids"] for a, b in zip(rx, rx2))
    u3 = all(rx[i]["token_ids"] == ry[i]["token_ids"] for i in range(h))
    # one decode step of the same (twin, first sampled token) row at batch sizes 1, B/2, B
    from engine import prealloc_cache
    first = rx[0]["token_ids"][0]
    P = tw["pre"]["P"]
    logit_rows = {}
    for bs in sorted({1, h, B}):
        kv = [(K.expand(bs, -1, -1, -1).contiguous(), V.expand(bs, -1, -1, -1).contiguous()) for K, V in tw["pre"]["kv"]]
        cache = prealloc_cache(kv, P + 2)
        feed = torch.full((bs, 1), first, device=model.device, dtype=torch.long)
        pos = torch.full((bs, 1), P, device=model.device, dtype=torch.long)
        import engine as VE
        VE.clear_act_cache()
        hh = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
        logit_rows[bs] = model.lm_head(hh[:, -1]).float()[0].clone()
        del cache, kv
    ref = logit_rows[B]
    dl = {str(bs): float((v - ref).abs().max()) for bs, v in logit_rows.items()}
    ctx.release()
    return {"U5_same_batch_twice_identical": bool(u5), "U3_batchmates_changed_rows_identical": bool(u3),
            "U3_max_abs_dlogit_vs_B": dl, "B": B}


def env_record() -> dict[str, Any]:
    import platform

    import transformers
    return {"gpu": torch.cuda.get_device_name(0), "cc": list(torch.cuda.get_device_capability(0)),
            "torch": torch.__version__, "cuda": torch.version.cuda, "cublas": "nvidia-cublas-cu12==12.8.4.1 (pinned)",
            "transformers": transformers.__version__, "python": platform.python_version(),
            "driver": __import__("subprocess").run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                                    capture_output=True, text=True).stdout.strip(),
            "model": MODEL_ID, "revision": MODEL_REVISION,
            "vram_total_gib": torch.cuda.get_device_properties(0).total_memory / 2 ** 30}


def np_float(x: Any) -> Any:
    return float(x) if isinstance(x, (np.floating,)) else x
