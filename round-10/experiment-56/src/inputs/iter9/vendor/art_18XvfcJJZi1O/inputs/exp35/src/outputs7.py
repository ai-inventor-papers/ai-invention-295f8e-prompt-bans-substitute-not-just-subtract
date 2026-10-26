#!/usr/bin/env python3
"""method_out.json in the exp_gen_sol_out schema. Datasets: twin, fork_scan, sweep, collapsed, s4a, s4b.
Each example: input = the prompt's user text (+ slot / prefix context), output = '<label>|<pass>';
predict_onefork = the committed per-slot replay label (sweep) or the OC label (continuations); predict_cell_share =
the committed predicted attempted A_min share of the example's cell; metadata_* = protocol fields."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg7 import (CONTS, DATA_DIR, RESULTS_DIR, ROOT, UNITS, read_json, read_jsonl, utc_now)  # noqa: E402
from prompts7 import load_prompts  # noqa: E402

TEMPLATE_TAIL_TXT = "<|im_end|>"


def user_text(tok: Any, ids: list[int], p0: int) -> str:
    txt = tok.decode(ids[p0:])
    return txt.split(TEMPLATE_TAIL_TXT)[0]


def build() -> dict[str, Any]:
    from transformers import AutoTokenizer
    from cfg7 import model_path
    from analysis_T import rows_with_labels
    tok = AutoTokenizer.from_pretrained(model_path())
    P = load_prompts()
    pv = read_json(RESULTS_DIR / "predictions_view.json")
    F = read_json(RESULTS_DIR / "forks.json")
    rows = rows_with_labels()
    utext: dict[tuple, str] = {}

    def ut(unit: str, w: str, kind: str) -> str:
        k = (unit, w, kind)
        if k not in utext:
            p = P.get(k)
            utext[k] = user_text(tok, p["ids"], p["p0"]) if p else ""
        return utext[k]
    ds: dict[str, list[dict[str, Any]]] = {"twin": [], "sweep": [], "collapsed": [], "s4a": [], "s4b": [],
                                           "fork_scan": []}
    for r in rows:
        u = r["unit"]
        arm = r["arm"]
        kind = "forced" if r["cell"] == "FORCED" else ("forced_pad" if arm == "S4B" else "twin")
        w = r["template"]
        ex = {"input": ut(u, w, kind) + f"\n\n[slot {r['slot']}, cell {r['cell']}]",
              "output": f"{r['label']}|{'pass' if r['passed'] else 'fail'}",
              "metadata_unit": u, "metadata_arm": arm, "metadata_cell": r["cell"], "metadata_template": w,
              "metadata_slot": r["slot"], "metadata_temperature": r["T"], "metadata_top_k": r["top_k"],
              "metadata_crn_key": "|".join(str(x) for x in r["ukey"]), "metadata_n_new_tokens": r["n_new_tokens"],
              "metadata_finish_reason": r["finish_reason"], "metadata_batch_B": r["batch_B"],
              "metadata_generation": r["text"][:6000]}
        if u in UNITS and u in F:
            cl = F[u]["opening"]["clusters"]
            on = any(r["token_ids"][:len(c["O"])] == c["O"] for c in cl)
            ex["metadata_on_opening"] = on
            c0 = next((c for c in cl if r["token_ids"][:len(c["O"])] == c["O"]), None)
            if c0 is not None and len(r["token_ids"]) > len(c0["O"]):
                ex["metadata_fork_index"] = len(c0["O"])
                ex["metadata_fork_token_id"] = r["token_ids"][len(c0["O"])]
                ex["metadata_fork_token"] = tok.decode([r["token_ids"][len(c0["O"])]])
        if arm == "SWEEP" and u in pv["units"]:
            U = pv["units"][u]
            rp = U["replay"].get(f"{w}|{r['slot']}|{r['cell']}")
            ex["predict_onefork"] = str(rp["pred"]) if rp else "none"
            ex["predict_cell_share"] = f"{U['cells'][r['cell']]['a_min']:.4f}"
            ex["metadata_a_min"] = U["A_min"]
            ds["sweep"].append(ex)
        elif arm == "TWIN":
            if u in pv["units"]:
                ex["predict_cell_share"] = f"{pv['units'][u]['cells']['T1.0_p1']['a_min']:.4f}"
            ds["twin"].append(ex)
        elif arm in ("TWIN6", "T13CHK"):
            col = pv.get("collapsed", {}).get(u, {})
            if col:
                ex["predict_cell_share"] = f"{col['pred_p_off']['T1.3_p1' if arm == 'T13CHK' else 'T1.0_p1']:.6f}"
            ds["collapsed"].append(ex)
        elif arm == "S4A":
            if u in pv["units"] and "s4" in pv["units"][u]:
                d = r.get("direction")
                pr = pv["units"][u]["s4"]["push"].get(str(d)) if d else pv["units"][u]["s4"]["twin"]
                ex["predict_cell_share"] = f"{pr['s_pred']:.4f}" if pr else "none"
            ds["s4a"].append(ex)
        elif arm == "S4B":
            m = {"FORCED": "forced", "FORCEDPAD": "forced_pad", "EXCH": "exchange", "MR": "MR"}[r["cell"]]
            s4 = pv["units"].get(u, {}).get("s4", {}).get("exchange", {}).get(m)
            ex["predict_cell_share"] = f"{s4['s_pred']:.4f}" if s4 else "none"
            ds["s4b"].append(ex)
    full = {r["sid"]: r for r in read_jsonl(DATA_DIR / "continuation_labels.jsonl")}
    for r in read_jsonl(CONTS):
        lab = r.get("label") or (full.get(r["cid"]) or {}).get("label") or "other"
        ex = {"input": f"[{r['unit']} {r.get('kind')} continuation; template {r['w']}; prefix length "
                       f"{r.get('prefix_len')}; base path {r.get('bid') or r.get('cluster')}]",
              "output": lab, "predict_onefork": str(r.get("oc_label")),
              "metadata_unit": r["unit"], "metadata_kind": r.get("kind"), "metadata_base_path_id": r.get("bid"),
              "metadata_prefix_len": r.get("prefix_len"), "metadata_cluster": r.get("cluster"),
              "metadata_fork_token_id": r.get("tok"), "metadata_temperature": r.get("T"),
              "metadata_first_token": r.get("first_token"), "metadata_finish_reason": r.get("finish_reason"),
              "metadata_label_source": r.get("label_source") or "full_labeller",
              "metadata_crn_key": "|".join(str(x) for x in r["ukey"])}
        ds["fork_scan"].append(ex)
    out = {"metadata": {"method_name": "Where temperature can change the chosen algorithm (claim T, iteration 7)",
                        "model": "Qwen/Qwen3-8B@b968826d (bf16, thinking off)",
                        "verdict": read_json(RESULTS_DIR / "verdict.json") if (RESULTS_DIR / "verdict.json").exists()
                        else None, "utc": utc_now(),
                        "description": "Prefix-resampling fork location, committed temperature predictions from "
                                       "teacher-forced logits, a same-seed temperature sweep (baseline: the observed "
                                       "twin share and the per-slot replay), collapsed-task margins and task-state "
                                       "push/exchange links."},
           "datasets": [{"dataset": k, "examples": v} for k, v in ds.items() if v]}
    return out


if __name__ == "__main__":
    o = build()
    p = ROOT / "method_out.json"
    p.write_text(json.dumps(o))
    print({d["dataset"]: len(d["examples"]) for d in o["datasets"]}, f"{p.stat().st_size / 1e6:.1f} MB")
