#!/usr/bin/env python3
"""CPU tests (1)-(8) of the testing plan -> results/tests_cpu.json (test 8 draws its uniforms on the GPU)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from loguru import logger

from cfg import TEMPLATE_IDS, V_BLOCKS, read_jsonl, setup_logging, sha256_file, stable_seed, write_json
from cfg_e import E19, E22, POP_SEEDS, RESULTS_DIR, ROOT


def t1_e4m3() -> dict[str, Any]:
    import ml_dtypes

    rng = np.random.default_rng(0)
    parts = [rng.normal(0, 50, 400_000), rng.uniform(-500, 500, 200_000),
             rng.uniform(2.0 ** -10, 2.0 ** -5, 100_000) * rng.choice([-1, 1], 100_000), rng.normal(0, 1, 300_000),
             np.array([448.0, -448.0, 449.0, 464.0, 480.0, 1e4, -1e4, 0.0, 2.0 ** -9, 2.0 ** -10, 3 * 2.0 ** -10])]
    # exact ties between adjacent e4m3 values (midpoints) at several exponents
    grid = np.unique(np.array(ml_dtypes.float8_e4m3fn(np.arange(-448, 449, 0.5)).astype(np.float32)))
    mids = (grid[:-1] + grid[1:]) / 2
    parts.append(np.repeat(mids, 3)[:300_000])
    x = np.concatenate(parts).astype(np.float32)[:1_000_000]
    xc = np.clip(x, -448, 448)
    a = torch.tensor(xc).to(torch.float8_e4m3fn).view(torch.uint8).numpy()
    b = xc.astype(ml_dtypes.float8_e4m3fn).view(np.uint8)
    same = bool(np.array_equal(a, b))
    codes = torch.arange(256, dtype=torch.uint8).view(torch.float8_e4m3fn)
    vals = codes.float()
    fin = torch.isfinite(vals)
    rt = bool(torch.equal(vals[fin].to(torch.bfloat16).float(), vals[fin]))
    v = vals[fin]
    prod32 = (v[:, None] * v[None, :])
    prod64 = (v.double()[:, None] * v.double()[None, :])
    exact = bool(torch.equal(prod32.double(), prod64))
    return {"n_values": int(len(x)), "n_ties": int(min(len(mids) * 3, 300_000)), "torch_equals_ml_dtypes_RNE": same,
            "e4m3_roundtrip_bf16_exact": rt, "e4m3_products_exact_fp32": exact, "pass": same and rt and exact}


def t2_quantisers() -> dict[str, Any]:
    from engine_v4 import FP8Linear
    from qlinear import quant_e4m3_rows_codes, quant_weight

    torch.manual_seed(0)
    lin = torch.nn.Linear(256, 96, bias=False).to(torch.bfloat16)
    lin.weight.data.mul_(torch.logspace(-2, 1, 96)[:, None].to(torch.bfloat16))
    ref = FP8Linear(lin, torch.device("cpu"))
    wq, s = quant_weight(lin.weight.data)
    w_same = bool(torch.equal(wq.view(torch.uint8), ref.wq_t.t().contiguous().view(torch.uint8)))
    s_same = bool(torch.equal(s, ref.w_scale))
    x = (torch.randn(50, 256) * torch.logspace(-3, 2, 50)[:, None]).to(torch.bfloat16)
    xq, xs = quant_e4m3_rows_codes(x)
    xs_ref = x.abs().amax(dim=1, keepdim=True).float().clamp_(min=1e-12) / 448.0   # FP8Linear.forward's lines
    xq_ref = (x.float() / xs_ref).clamp_(-448.0, 448.0).to(torch.float8_e4m3fn)
    a_same = bool(torch.equal(xq.view(torch.uint8), xq_ref.view(torch.uint8))) and bool(torch.equal(xs, xs_ref))
    return {"weight_codes_equal": w_same, "weight_scales_equal": s_same, "activation_codes_scales_equal": a_same,
            "pass": w_same and s_same and a_same}


def t3_hooks() -> dict[str, Any]:
    from hooks import make_edits

    src = (E22 / "src" / "hooks4.py").read_text().replace("from cfg4 import EDIT_BLOCKS", "EDIT_BLOCKS = list(range(12, 24))")
    ns: dict[str, Any] = {"__name__": "hooks4_copy"}
    exec(compile(src, "hooks4.py", "exec"), ns)
    torch.manual_seed(1)
    ok = True
    for slot in range(2):
        a, b, D = 5, 17, 64
        h = (torch.randn(1, 20, D) * 3).to(torch.bfloat16)
        u = torch.randn(D)
        u = u / u.norm()
        n = {l: torch.rand(b - a) * 5 for l in V_BLOCKS}
        href = {l: (h[0, a:b].float() + torch.randn(b - a, D) * 0.1) for l in V_BLOCKS}
        e1 = make_edits("RAND", a, b, {l: u for l in V_BLOCKS}, n, href, alpha=2.0)
        e2 = ns["make_edits_v4"]("TARGET", a, b, {l: u for l in V_BLOCKS}, {l: 2.0 * n[l] for l in V_BLOCKS}, href)
        for l in V_BLOCKS:
            ok &= bool(torch.equal(e1[l](h), e2[l](h)))
    sha = sha256_file(ROOT / "src" / "hooks.py") == sha256_file(E19 / "src" / "hooks.py")
    return {"hooks_sha256_equal_exp19": sha, "make_edits_RAND_equals_make_edits_v4_TARGET": ok, "pass": sha and ok}


def t4_seeds() -> dict[str, Any]:
    from engine_v4 import u_stream
    from sampling_v4 import pn_direction

    rows = [r for r in read_jsonl(E19 / "data" / "samples.jsonl")
            if r["task"] in ("T10", "T2", "T03") and r["arm"] in ("PN_a1", "PN_a2", "TWIN")]
    dir_ok = all(pn_direction(r["task"], r["arm"], r["template"], int(r["slot"]))[0] == r["direction_seed"]
                 for r in rows if r["arm"] != "TWIN")
    u_ok = all(stable_seed(r["task"], r["template"], int(r["slot"])) == r["u_seed"] for r in rows)
    pop_ok = True
    for s in POP_SEEDS:
        x = np.random.Generator(np.random.PCG64(s)).standard_normal(4096)
        u = (x / np.linalg.norm(x)).astype(np.float32)
        pop_ok &= bool(np.array_equal(u, np.load(E22 / "directions" / f"rand_{s}.npy").astype(np.float32)))
    us = u_stream("T2", "W1", 0)
    return {"pn_direction_seeds_match_exp19": dir_ok, "u_seed_matches_exp19": u_ok,
            "pop_directions_regenerate_exp22_files": pop_ok, "u_stream_len": int(len(us)),
            "note": "first-step logits are not logged by exp19; u_stream equality is checked through the seeds and "
                    "through the REAL engine check's token identity",
            "pass": dir_ok and u_ok and pop_ok}


def t5_units() -> dict[str, Any]:
    from sampling_v4 import load_norms

    prompts = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "data" / "prompts.jsonl")}
    res = {}
    ok = True
    for t in ("T10", "T2", "T03"):
        nm = load_norms(t)
        for w in TEMPLATE_IDS:
            p = prompts[(t, w, "twin")]
            good = nm.shape == (12, p["spec_end"] - p["p1"])
            ok &= good
        res[t] = list(nm.shape)
    return {"shapes": res, "pass": ok}


def t6_labeller() -> dict[str, Any]:
    p = RESULTS_DIR / "labeller_recheck.json"
    if not p.exists():
        return {"pass": False, "missing": True}
    d = json.loads(p.read_text())
    a, b = d["exp19"]["agreement"], d["exp22_pop_a2"]["agreement"]
    return {"exp19_agreement": a, "exp22_agreement": b, "n_exp19": d["exp19"]["n"], "n_exp22": d["exp22_pop_a2"]["n"],
            "pass": a == 1.0 and b == 1.0}


def t7_analysis() -> dict[str, Any]:
    from analysis_e import synthetic_test

    res = synthetic_test(RESULTS_DIR / "synthetic")
    return {**res, "pass": res["all_ok"]}


def t8_dither() -> dict[str, Any]:
    if not torch.cuda.is_available():
        return {"pass": False, "skipped": "no CUDA"}
    from dither import _uniforms, dither_rows, step_size

    torch.manual_seed(2)
    x = (torch.randn(64, 4096, device="cuda") * torch.logspace(-2, 2, 64, device="cuda")[:, None]).to(torch.bfloat16)
    U = _uniforms(12345, 64, 4096)
    xd, noise = dither_rows(x, U)
    xs = x.abs().amax(dim=1, keepdim=True).float() / 448.0
    st = step_size(x.float() / xs) * xs
    bound = bool((noise.abs() <= st / 2 + 1e-12).all())
    rel_mean = float((noise / st).mean())
    U2 = _uniforms(12345, 64, 4096)
    repro = bool(torch.equal(U, U2))
    return {"abs_noise_le_half_step": bound, "mean_noise_over_step": rel_mean, "reproducible": repro,
            "pass": bound and abs(rel_mean) < 0.01 and repro}


def main() -> None:
    setup_logging("tests_cpu")
    res = {}
    for name, fn in (("1_e4m3", t1_e4m3), ("2_quantisers", t2_quantisers), ("3_hooks", t3_hooks),
                     ("4_seeds", t4_seeds), ("5_units", t5_units), ("6_labeller", t6_labeller),
                     ("7_analysis_synthetic", t7_analysis), ("8_dither", t8_dither)):
        try:
            res[name] = fn()
        except Exception as e:  # noqa: BLE001 - a failing test is recorded, not hidden
            logger.exception(f"test {name} failed")
            res[name] = {"pass": False, "error": repr(e)}
        logger.info(f"{name}: pass={res[name].get('pass')}")
    res["all_pass"] = all(v.get("pass") for v in res.values() if isinstance(v, dict))
    write_json(RESULTS_DIR / "tests_cpu.json", res)
    logger.info(f"CPU tests all_pass={res['all_pass']}")


if __name__ == "__main__":
    main()
