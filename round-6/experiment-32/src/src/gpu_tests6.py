#!/usr/bin/env python3
"""GPU tests (plan testing G1-G4, G6) on unit II4, template W1, CRN slots 0-19 (nothing is written to the data files):
G1 CRN determinism: the same 20 slots sampled twice give identical token ids;
G2 alpha = 0 prefill-push identity: an ESC push with alpha 0 reproduces the twin token ids exactly;
G3 realised dose: the targeted component equals alpha x n[l, p] within 1% (from the logged rel_err of every pushed row);
G4 GTN at alpha 0 reproduces the twin token ids, and its shadow rows reproduce the clean states (rel err logged);
G6 every vLLM request used exactly the prompt token ids of the HF prompt table (CPU comparison)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from cfg5 import (DATA_DIR, EDIT_BLOCKS, MODEL_ID, MODEL_REVISION, RAW, RESULTS_DIR, read_jsonl, setup_logging,  # noqa: E402
                  utc_now, write_json)


def main() -> None:
    setup_logging("gpu_tests6")
    from ctx5 import r_at, rand_dir
    from engine5 import load_model, sample
    from gtn6 import sample_gtn
    from prompts5 import load_prompts
    from sampling5 import Runner, uniforms
    tok, model = load_model(MODEL_ID, MODEL_REVISION, vram_fraction=0.95)
    pr = load_prompts()
    run = Runner(model, tok, "instruct", pr)
    u, w = "II4", "W1"
    ctx = run.unit_ctx(u, False)
    tw = ctx.twin(w)
    us = [uniforms(u, w, "TWIN", k, 1024) for k in range(20)]
    a = sample(model, tok, [{"pre": tw["pre"], "us": us}], fence="bench")
    b = sample(model, tok, [{"pre": tw["pre"], "us": us}], fence="bench")
    g1 = all(x["token_ids"] == y["token_ids"] for x, y in zip(a, b))
    pre0, rec0 = ctx.arm_prefill(w, ctx.push_spec(w, rand_dir(12345), 0.0))
    c = sample(model, tok, [{"pre": pre0, "us": us}], fence="bench")
    g2 = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a, c))
    rq = {l: r_at(l) for l in EDIT_BLOCKS}
    d = sample_gtn(model, tok, tw["pre"], us[:10], [rand_dir(777 + i) for i in range(10)], 0.0, rq)
    g4 = sum(x["token_ids"] == y["token_ids"] for x, y in zip(a[:10], d))
    rels = [r.get("rel_err_max") for r in read_jsonl(RAW) if r.get("family") in ("ESC", "PN", "GTN")
            and r.get("rel_err_max") is not None]
    reqs = {}
    for f in (DATA_DIR / "vllm_req").glob("*.jsonl"):
        for l in f.read_text().splitlines():
            r = json.loads(l)
            reqs[r["rid"]] = r["prompt_token_ids"]
    ok = bad = 0
    for rid, ids in reqs.items():
        uu, ww, arm, k, mt = rid.split("|")
        if arm in ("TWIN", "T13", "BASE", "BASEX"):
            ref = pr.get(f"{uu}|twin|-|{ww}")
            if ref is not None:
                ok += ref["ids"] == ids
                bad += ref["ids"] != ids
    out = {"utc": utc_now(), "G1_crn_determinism_identical": g1, "G2_alpha0_esc_identical_rows": f"{g2}/20",
           "G2_alpha0_rel_err": rec0.get("rel_err_max") if rec0 else None,
           "G3_realised_dose": {"n_rows": len(rels), "max_rel_err": max(rels) if rels else None,
                                "median_rel_err": float(np.median(rels)) if rels else None,
                                "pass_1pct": bool(rels) and max(rels) < 0.01},
           "G4_gtn_alpha0_identical_rows": f"{g4}/10", "G4_gtn_shadow_rel_err": d[0].get("gtn_rel_err_max"),
           "G6_vllm_prompt_ids_identical": {"identical": ok, "different": bad}}
    write_json(RESULTS_DIR / "tests_gpu.json", out)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
