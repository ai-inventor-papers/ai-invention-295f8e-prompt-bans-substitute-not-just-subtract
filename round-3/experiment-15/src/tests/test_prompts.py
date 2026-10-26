#!/usr/bin/env python3
"""T1 prompt unit tests: BOS, date line, twin length/suffix identity, spec_start decodes to 'Task', nonce/novelty share
the spec ids, spec.json spec_text equals the bench scaffold, and every (task, mode, w, h) twin exists."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ws import FROZEN_TASKS, RESULTS, write_json  # noqa: E402
from src import prompts_llama as P  # noqa: E402
from bench.common import prompts as BP  # noqa: E402


def main() -> None:
    tok = P.tokenizer()
    res = {"n_pairs": 0, "max_k": 0, "noun_fallbacks": [], "fail": []}
    for t in FROZEN_TASKS:
        assert P.spec_json(t)["spec_text"] == BP.spec_text(t), f"spec text mismatch {t}"
        base = P.build(t, "baseline", None, cond="baseline")
        spec_ids = base["ids"][base["spec_start"]:]
        assert tok.decode(base["ids"][base["spec_start"]]).strip().startswith("Task"), t
        for mode in P.modes(t):
            for w in range(1, 6):
                ban = P.p_ban(t, mode, w)
                assert ban["ids"][ban["spec_start"]:] == spec_ids, f"ban spec suffix {t} {mode} {w}"
                assert tok.decode(ban["ids"][ban["spec_start"]]).strip().startswith("Task")
                for h in (0, 1):
                    tw = P.p_twin(t, mode, w, h)
                    ok = (len(tw["ids"]) == len(ban["ids"]) and tw["ids"][tw["spec_start"]:] == ban["ids"][ban["spec_start"]:])
                    res["n_pairs"] += 1
                    res["max_k"] = max(res["max_k"], tw["k"])
                    if len(tw["nouns_tried"]) > 1:
                        res["noun_fallbacks"].append({"task": t, "mode": mode, "w": w, "h": h, "tried": tw["nouns_tried"]})
                    if not ok:
                        res["fail"].append([t, mode, w, h])
        for w in range(1, 6):
            nz = P.p_nonce(t, w)
            assert nz["ids"][nz["spec_start"]:] == spec_ids
        nv = P.p_novelty(t)
        assert nv["ids"][nv["spec_start"]:] == spec_ids
        for mode in P.modes(t):
            for k in list(range(10)) + [-1]:
                f = P.p_forced(t, mode, k)
                assert f["ids"][f["spec_start"]:] == spec_ids
            a = P.p_assoc(t, mode)
            assert a["ids"][0] == tok.bos_token_id
    res["examples"] = {"ban": P.p_ban("T04", "naive", 1)["text"][:200], "twin": P.p_twin("T04", "naive", 1, 0)["text"][:200],
                       "nonce": P.p_nonce("T04", 3)["text"][:120], "novelty": P.p_novelty("T04")["text"][:120],
                       "forced": P.p_forced("T04", "kmp", 0)["text"][:120], "forced_desc": P.p_forced("T04", "kmp", -1)["text"][:200],
                       "assoc": P.p_assoc("T04", "naive")["text"][-200:]}
    res["passed"] = not res["fail"]
    write_json(RESULTS / "tests_prompts.json", res)
    print({k: v for k, v in res.items() if k != "examples"}, flush=True)
    assert res["passed"], res["fail"][:5]


if __name__ == "__main__":
    main()
