#!/usr/bin/env python3
"""R_margin inputs (plan section 8): teacher-forced log p(opening) of every catalogue reference under each twin prompt
W1-W5 (instruct model). Opening = the reference's first <= 16 body tokens after the def line; the assistant prefix is
'```python\\n' + the def line + '\\n'. The default is not needed here (it is chosen later from the twin labels);
R_margin = -(mean_W [lp(default) - max_{survivor} lp(survivor)]) is computed in src/quantities.py."""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from cfg5 import RESULTS_DIR, TEMPLATE_IDS, read_json, utc_now, write_json
from engine5 import teacher_forced_logprob
from unitlib import unit_mod

OUT = RESULTS_DIR / "margins.json"


def split_def(code: str) -> tuple[str, str]:
    lines = code.lstrip("\n").splitlines()
    for i, l in enumerate(lines):
        if re.match(r"def\s+solve\s*\(", l):
            return l, "\n".join(lines[i + 1:]) + "\n"
    raise ValueError("no def solve")


def opening_margins(runner: Any, u: str) -> dict[str, Any]:
    res = read_json(OUT) if OUT.exists() else {}
    if u in res:
        return res[u]
    tok = runner.tok
    mod = unit_mod(u)
    refs = dict(mod.REFERENCES)
    refs.update(getattr(mod, "EXTRA_REFERENCES", {}))
    out: dict[str, Any] = {"utc": utc_now(), "by_mode": {}}
    for m, code in refs.items():
        dline, body = split_def(code)
        body_ids = tok(body, add_special_tokens=False)["input_ids"][:16]
        pre_ids = tok("```python\n" + dline + "\n", add_special_tokens=False)["input_ids"]
        lp = {}
        for w in TEMPLATE_IDS:
            p = runner.pr[f"{u}|twin|-|{w}"]
            lp[w] = teacher_forced_logprob(runner.model, p["ids"] + pre_ids, [body_ids])[0]
        out["by_mode"][m] = {"logp": lp, "n_tokens": len(body_ids), "opening_text": tok.decode(body_ids)}
    res[u] = out
    write_json(OUT, res)
    summ = {m: round(sum(v["logp"].values()) / 5, 2) for m, v in out["by_mode"].items()}
    logger.info(f"margins {u}: {summ}")
    return out
