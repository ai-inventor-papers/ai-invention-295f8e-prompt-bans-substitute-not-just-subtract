#!/usr/bin/env python3
"""Extension (pre-registered as COMMIT #4 before any of its tokens): a generation dose-response of the readout-row
edit. Can a stronger edit of the fork-class rows steer which algorithm the model writes, and is that specific to the
base-row delta? Arms (same CRN engine, slots and fixed batch shape B = 6 as W1-GEN):
  ROWS_L2, ROWS_L3          fork-class rows w_I,t + lambda * Delta_t, lambda = 2, 3 (fork step only)
  RAND_MED_L2, RAND_MED_L3  the committed RAND_ISO median-share draw scaled by the same lambda (matched control)
Committed first: teacher-forced shares at these doses and the predicted counts from the fork distributions.

Usage: w1_dose_gen.py commit | gpu
"""

from __future__ import annotations

import sys
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg10 import (DATA_DIR, I9_RES, MAX_NEW, PRED_DIR, RESULTS_DIR, ROOT, SEED0, SLOTS_PER_T, UNITS_TF,
                   append_jsonl, commit, import_iter9, ledger, model_path, read_json, read_jsonl, setup_logging,
                   sha256_text, utc_now)

import_iter9()
from b2gen9 import slot_prompts, token_map  # noqa: E402

LAMS = (2.0, 3.0)
DOSE_ARMS = ("ROWS_L2", "ROWS_L3", "RAND_MED_L2", "RAND_MED_L3")


def rows_for(arm: str, WI_S: torch.Tensor, Delta: torch.Tensor, iso_med: torch.Tensor) -> torch.Tensor:
    lam = float(arm.split("_L")[1])
    return WI_S + lam * (Delta if arm.startswith("ROWS") else iso_med)


def commit_plan() -> dict[str, Any]:
    from transformers import AutoTokenizer
    from w1_tf import UnitData, load_readout, share
    units = read_json(I9_RES / "units.json")
    WI, gI = load_readout("qwen")
    WB, gB = load_readout("qwen_base")
    tok = AutoTokenizer.from_pretrained(model_path("qwen"))
    plan = read_json(PRED_DIR / "commit2_w1tf_genplan.json")["gen_predictions"]
    out: dict[str, Any] = {"lams": LAMS, "arms": DOSE_ARMS, "units": {}}
    for u in UNITS_TF:
        d = UnitData(u, units, WI, WB, gI, gB)
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        iso_med = torch.from_numpy(nul["RAND_ISO"][plan[u]["rand_draws"]["RAND_MED"]])
        bins, tmap = token_map(u, d.fork)
        idx_of = {pid: i for i, pid in enumerate(d.pids)}
        sp = slot_prompts(units[u])
        rec: dict[str, Any] = {"tf_share": {}, "predicted_shares": {}, "predicted_unmapped": {}, "top": {}}
        for a in DOSE_ARMS:
            r = rows_for(a, d.WI_S, d.Delta, iso_med)
            rec["tf_share"][a] = share(d.mI, d.m_rows(r), d.mB)
            z = d.z_with_rows(r)
            mix_all, unm, tops = [], [], {}
            for _, p in sp:
                i = idx_of[p["pid"]]
                pr = torch.softmax(z[i].double(), -1).numpy()
                mix = np.zeros(len(bins))
                mapped = 0.0
                for t, v in tmap.items():
                    mix += pr[t] * v
                    mapped += pr[t]
                mix_all.append(mix)
                unm.append(1 - mapped)
                tops[p["pid"]] = [(tok.decode([int(t)]), float(pr[t])) for t in np.argsort(-pr)[:6]]
            m = np.mean(mix_all, 0)
            rec["predicted_shares"][a] = dict(zip(bins, m.tolist()))
            rec["predicted_unmapped"][a] = float(np.mean(unm))
            rec["top"][a] = tops
        corr = ["dfs"] if u == "T10" else ["prim_heap", "prim_array"]
        rec["predicted_correct_count_of_30"] = {a: 30 * sum(rec["predicted_shares"][a][b] for b in corr)
                                                for a in DOSE_ARMS}
        rec["rand_med_draw"] = plan[u]["rand_draws"]["RAND_MED"]
        out["units"][u] = rec
        logger.info(f"dose plan {u}: TF shares {rec['tf_share']}; predicted correct {rec['predicted_correct_count_of_30']}"
                    f"; unmapped {rec['predicted_unmapped']}")
    out["tests"] = ["ROWS_L2_vs_TWIN", "ROWS_L3_vs_TWIN", "ROWS_L2_vs_RAND_MED_L2", "ROWS_L3_vs_RAND_MED_L3"]
    out["note"] = "extension beyond the plan (dose-response in generation); descriptive, no verdict threshold"
    commit("commit4_dose_gen", out, files=[ROOT / "src" / "w1_dose_gen.py"])
    ledger("COMMIT4")
    return out


@torch.no_grad()
def gpu() -> None:
    from capture10 import CM, full_logits, load
    from w1_gen import RAW, generate, uniforms
    from w1_tf import load_readout
    t0 = time.time()
    model, tok, info = load("qwen")
    units = read_json(I9_RES / "units.json")
    plan = read_json(PRED_DIR / "commit4_dose_gen.json")
    WB_cpu, _ = load_readout("qwen_base")
    W = model.lm_head.weight
    done = {r["sid"] for r in read_jsonl(RAW)}
    for u in UNITS_TF:
        f = units[u]["forks"][0]
        S = [int(t) for t in f["D"]] + [int(t) for t in f["A"]]
        nul = np.load(RESULTS_DIR / f"null_draws_{u}.npz")
        WI_S = W[S].float()
        Delta = WB_cpu[S].float().cuda() - WI_S
        iso_med = torch.from_numpy(nul["RAND_ISO"][plan["units"][u]["rand_med_draw"]]).cuda()
        mx = MAX_NEW[u]
        open_txt = tok.decode(f["opening"])
        for ti, (i, p) in enumerate(slot_prompts(units[u])):
            ids = p["ids"] + f["opening"]
            kv = CM.prefix_kv(model, ids)
            slots, Urows = uniforms(ti, mx)
            for a in DOSE_ARMS:
                sids = [f"{u}|{a}|{p['template']}|{k}" for k in range(SLOTS_PER_T)]
                if all(s in done for s in sids):
                    continue
                rows = rows_for(a, WI_S, Delta, iso_med)

                def fork_fn(h: torch.Tensor, rows: torch.Tensor = rows) -> torch.Tensor:
                    z = full_logits(W, h)
                    z[:, S] = h.float() @ rows.T
                    return z
                tb = time.time()
                gen, fin = generate(model, tok, kv, ids, fork_fn, Urows, mx)
                recs = []
                for r in range(len(gen)):
                    txt = tok.decode(gen[r])
                    if "```" in txt:
                        txt = txt[:txt.index("```") + 3]
                    full = open_txt + txt
                    recs.append({"sid": sids[r], "unit": u, "task": u, "arm": a, "template": p["template"],
                                 "prompt_id": p["pid"], "slot": slots[r], "seed": SEED0 + slots[r],
                                 "fork_token": tok.decode([gen[r][0]]), "fork_token_id": gen[r][0],
                                 "n_tokens": len(gen[r]), "truncated": not fin[r], "text": full,
                                 "code_sha256": sha256_text(full), "engine": "hf-bf16", "batch_shape": len(gen),
                                 "utc": utc_now()})
                append_jsonl(RAW, recs)
                logger.info(f"[{u}] {p['template']} {a}: {time.time() - tb:.1f}s; fork tokens "
                            f"{[x['fork_token'] for x in recs]}")
            del kv
            torch.cuda.empty_cache()
    ledger("DOSE_GEN_end", seconds=round(time.time() - t0, 1))


if __name__ == "__main__":
    setup_logging(f"w1_dose_gen_{sys.argv[1]}")
    {"commit": commit_plan, "gpu": gpu}[sys.argv[1]]()
