#!/usr/bin/env python3
"""CPU checks from the testing plan that need no GPU: scaffold, forecast guard, sha256, statistics.

  .venv/bin/python tests/test_screen.py      -> results/unit_tests.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS_DIR, SPEC, TASKS, resolve_model_path  # noqa: E402


def main() -> None:
    from transformers import AutoTokenizer
    from analysis import stats
    from analysis.forecast import cmd_verify
    from prompts.scaffold import TEMPLATE_TAIL, all_groups, build_prompt, build_prompt_text, check_suffix, segments
    import gpu.vllm_gen as vg  # importing does not start an engine

    tok = AutoTokenizer.from_pretrained(resolve_model_path())
    out = {}
    out["spec_tokens"] = {t: len(tok(SPEC[t], add_special_tokens=False)["input_ids"]) for t in TASKS}
    out["spec_ge_50_tokens"] = all(v >= 50 for v in out["spec_tokens"].values())
    n, last = 0, {}
    for t in TASKS:
        for g in all_groups(t) + ["listall"]:
            for s in segments(t, g):
                ids = build_prompt(tok, s, task=t)
                check_suffix(tok, ids, t)
                last.setdefault(t, set()).add(ids[-1])
                n += 1
        txt = build_prompt_text(tok, segments(t, "baseline")[0], t)
        out[f"empty_think_block_{t}"] = txt.endswith(TEMPLATE_TAIL) and "<think>\n\n</think>" in txt
    out["n_prompts_suffix_checked"] = n
    out["R_token_identical_across_conditions"] = all(len(v) == 1 for v in last.values())
    out["guard_refuses_uncommitted_event"] = vg.committed("predict_T9_ban1.json") is None
    out["guard_finds_committed_events"] = all(vg.committed(f"predict_{t}_ban1.json") is not None for t in TASKS)
    ver = cmd_verify()
    out["sha256_reverified"] = all(v["ok"] for v in ver.values()) and len(ver) > 0
    stats.self_test()
    out["stats_self_test"] = True
    out["all_pass"] = all(v for k, v in out.items() if isinstance(v, bool))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "unit_tests.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
