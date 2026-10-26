#!/usr/bin/env python3
"""Audit support: next-token probabilities of every MAPPED fork token at T10's forks (10, 11) for the 40 POP cells and
the twin, per template, from the same teacher-forced pass predict7 uses (prompt + push edit + o_t[0:11]).
-> results/fork_token_probs.json, so audit/rederive.py can (i) re-derive every committed T10 margin from token
probabilities and the committed token maps with the standard library, and (ii) run the shuffled-token-map placebo."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import c7 as common  # noqa: E402
from c7 import RESULTS, SEEDS40, TEMPLATES, read_json, setup_logging, write_json  # noqa: E402
import engine7 as E  # noqa: E402
import predict7 as P7  # noqa: E402


def main() -> None:
    setup_logging("fork_probs")
    forks = read_json(common.forks_path())["tasks"]["T10"]
    tok, model = E.load()
    tm = P7.TaskModel(model, tok, "T10", forks, {})
    fl = [int(f) for f in forks["forks"]]
    o = forks["opening_ids"]
    mapped = {str(f): [int(k) for k, v in forks["token_maps"][str(f)].items() if v["mapped"]] for f in fl}
    out = {"forks": fl, "default_token": {str(f): int(o[f]) for f in fl}, "mapped_tokens": mapped, "cells": {}}
    for w in TEMPLATES:
        rec = tm.ctx.twin(w)["prompt"]
        P = len(rec["ids"])
        ids = rec["ids"] + o[:max(fl)]
        for cell, edits in [("TWIN", None)] + [(f"POP_d{s}_a2.0", P7.pop_edits(tm, w, s)) for s in SEEDS40]:
            lp = E.forward_lp(model, [ids], [P - 1 + f for f in fl], edits=edits)[0]
            d = {}
            for j, f in enumerate(fl):
                p = lp[j].double().exp()
                d[str(f)] = {str(k): float(p[k]) for k in mapped[str(f)]}
            out["cells"].setdefault(cell, {})[w] = d
    tm.ctx.release()
    write_json(RESULTS / "fork_token_probs.json", out)


if __name__ == "__main__":
    main()
