#!/usr/bin/env python3
"""Summarise the three judge passes of stage 0f (the first two had run-dependent timings in their prompts)."""
import json
from pathlib import Path

WS = Path(__file__).resolve().parent.parent


def summ(r: dict) -> dict:
    f6 = r["F6"]
    return {"novel_primary": r["readj_novel_k"], "novel_second": r["readj_novel_k_second"],
            "gate_primary": f6["judge_primary"]["controls_correct"], "gate_second": f6["judge_second"]["controls_correct"],
            "raw_agree_14_primary": f6["judge_primary"]["disputed_14"]["raw_agree_4class"],
            "raw_agree_14_second": f6["judge_second"]["disputed_14"]["raw_agree_4class"],
            "contested_control_calls": f6.get("contested_control", {}).get("judge_calls"),
            "spend_usd_this_pass": r["spend_usd"], "paid_calls_this_pass": r["n_calls"]}


runs = {"pass 1 (05:21, prompts with timings, max_tokens 400)": {
            "novel_primary": 0, "novel_second": 0, "gate_primary": 9, "gate_second": 8, "raw_agree_14_primary": 13 / 14,
            "raw_agree_14_second": 11 / 14, "contested_control_calls": {"judge_primary": ["CATALOGUE_VARIANT"],
                                                                         "judge_second": ["CATALOGUE_VARIANT"]},
            "spend_usd_this_pass": 0.1037832, "paid_calls_this_pass": 164,
            "note": "transcribed from logs/stage_0f.log and the first results/0f.json (overwritten); 3 Kimi outputs empty at the 400-token cap"},
        "pass 2 (05:34, prompts with timings, max_tokens 1500)": summ(json.loads((WS / "results" / "0f_run2_prompts_with_timings.json").read_text())),
        "pass 3 (05:48, deterministic prompts, max_tokens 1500)": {
            "novel_primary": 1, "novel_primary_items": ["P13 (three of three calls; reason 'linear search with early termination')"],
            "novel_second": 0, "gate_primary": 9, "gate_second": 8, "raw_agree_14_primary": 12 / 14,
            "raw_agree_14_second": 11 / 14, "contested_control_calls": {"judge_primary": ["CATALOGUE_VARIANT"],
                                                                         "judge_second": ["CATALOGUE_VARIANT"]},
            "spend_usd_this_pass": 0.0987838, "paid_calls_this_pass": 148,
            "note": "transcribed from that pass's results/0f.json; Kimi spent its 1,500-token cap on hidden reasoning for P12 and P41"},
        "pass 4 (pass 3 cache + the 2 empty Kimi outputs re-queried with a 4,000-token cap)": {
            **summ(json.loads((WS / "results" / "0f.json").read_text())),
            "spend_usd_this_pass": 0.0018001, "paid_calls_this_pass": 2,
            "note": "verdict fields read from the current results/0f.json; later reruns are fully cached (USD 0) and identical"}}
(WS / "audit" / "judge_runs_summary.json").write_text(json.dumps(runs, indent=1))
print(json.dumps(runs, indent=1))
