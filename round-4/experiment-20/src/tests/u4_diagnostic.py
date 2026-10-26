#!/usr/bin/env python3
"""U4 follow-up (run after sampling, GPU free): is the shadow's divergence from an independent teacher-forced forward
an S3 artefact or a property of the FP8 engine's decode path?  S3 at alpha 0 (hooked == shadow, both clean): compare
decode-path block-23 states of clean rows with a batch-1 teacher-forced forward of the same tokens, per step, on T03
and T1 (W1, slots 300-309). Writes results/u4_diagnostic.json."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import schedule as SCH  # noqa: E402
from cfg import RESULTS_DIR, S3_STEPS, setup_logging, utc_now, write_json  # noqa: E402
from engine import forward_capture, load_model  # noqa: E402
from gpu_main import Ctx, load_units, run_batch  # noqa: E402
from prompts import load_base  # noqa: E402


@torch.no_grad()
def main() -> None:
    setup_logging("u4_diagnostic")
    tok, model = load_model(fp8=True)
    base = load_base(tok)
    units = load_units()
    out = {"utc": utc_now()}
    for t in ("T03", "T1"):
        ctx = Ctx(model, base, units, t, "W1")
        rows = [x for k in range(300, 310) for x in (dict(SCH._row(t, "W1", k, "S3_a0", 0)),
                                                       dict(SCH._row(t, "W1", k, "S3_a0", 0, True)))]
        od = run_batch(model, tok, ctx, rows, f"U4diag:{t}", write=False, keep_shadow_states=True)
        res = od[-1]["_res"]
        sh = res[0].get("_shadow_states") or []
        hk_rows = sorted([i for i, r in enumerate(rows) if not r["shadow"]], key=lambda i: rows[i]["k"])
        per_row = []
        for j, i in enumerate(hk_rows):
            gen = res[i]["token_ids"][:S3_STEPS]
            n = min(len(sh), len(gen))
            if n == 0:
                continue
            tf = forward_capture(model, ctx.ids + gen, [23])[23][ctx.P:ctx.P + n]
            dec = torch.stack([sh[s][j] for s in range(n)]).to(tf.device)
            cos = torch.nn.functional.cosine_similarity(dec, tf, dim=-1).cpu().numpy()
            rel = ((dec - tf).norm(dim=-1) / tf.norm(dim=-1)).cpu().numpy()
            per_row.append({"k": rows[i]["k"], "n": n, "cos_first": float(cos[0]), "cos_min": float(cos.min()),
                            "rel_max": float(rel.max()), "cos_by_step": [round(float(x), 5) for x in cos]})
        # prompt-position check: the decode path never recomputes prompt states; compare clean prefill block-23
        # states (captured in Ctx) with forward_capture of the prompt alone
        tfp = forward_capture(model, ctx.ids, [23])[23]
        pc = torch.nn.functional.cosine_similarity(tfp, ctx.H[23], dim=-1)
        out[t] = {"rows": per_row, "median_cos_min": float(np.median([r["cos_min"] for r in per_row])),
                  "median_cos_first": float(np.median([r["cos_first"] for r in per_row])),
                  "prompt_states_prefill_vs_forward_min_cos": float(pc.min())}
    out["reading"] = ("clean decode-path states (S3 alpha 0, no edit applied) diverge from a teacher-forced forward "
                      "of the same tokens by the same order as the U4 shadow -> the U4 failure is a property of the "
                      "FP8 decode path, not of the shadow coupling" if all(out[t]["median_cos_min"] < 0.999 for t in
                                                                            ("T03", "T1"))
                      else "clean decode states match the teacher-forced forward -> U4 failure is specific to S3")
    write_json(RESULTS_DIR / "u4_diagnostic.json", out)
    print({t: {k: v for k, v in out[t].items() if k != "rows"} for t in ("T03", "T1")}, out["reading"])


if __name__ == "__main__":
    main()
