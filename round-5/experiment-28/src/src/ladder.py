#!/usr/bin/env python3
"""Opening-margin rival (port of exp23's opening ladder; it model, teacher forcing, forward passes only).

For each unit: canonical openings O[m] = modal first body line of correct adherent forced programs of mode m (bench
forced_programs.jsonl; T1/T2: the exp8 suite references; R6 linear_scan: the extended reference). Contexts = the
model's own twin generations up to and including 'def solve(...):\\n' (2 per template). log p(O[m] | context) over its
first K = min(8, shortest opening) tokens (log-mean-exp over contexts). margin_D_vs_r = logp(D) - logp(r_u) (primary,
plan: tokens 1-8 between the default's and the runner-up's openings); margin_D_vs_best = logp(D) - max over survivors
(exp23's definition, sensitivity). Higher margin predicts LESS movability. Run before commit #1 and before any push."""

from __future__ import annotations

import ast as _ast
import collections
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, CHAT_HEAD, CHAT_TAIL, DATA_DIR, EXT_DIR, PATH_TASKS, PRED_DIR, RESULTS_DIR, SUITE,
                 TEMPLATE_IDS, read_json, read_jsonl, write_json)
import prompts as PG

LADDER = RESULTS_DIR / "opening_ladder.json"
K_MAX = 8


def first_body_line(code: str) -> str | None:
    try:
        tree = _ast.parse(code)
    except SyntaxError:
        return None
    fn = next((n for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef) and n.name == "solve"), None)
    if fn is None:
        return None
    body = [n for n in fn.body if not (isinstance(n, _ast.Expr) and isinstance(getattr(n, "value", None), _ast.Constant)
                                       and isinstance(n.value.value, str))]
    if not body:
        return None
    ln = code.splitlines()[body[0].lineno - 1]
    s = ln.split("#")[0].rstrip() if "#" in ln and "'" not in ln and '"' not in ln else ln.rstrip()
    return s.strip() or None


def openings(t: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = collections.defaultdict(list)
    if t in PATH_TASKS:
        sub = {"T1": "t1_grid", "T2": "t2_wsp"}[t]
        pref = {"T1": [("bfs", "bfs"), ("bibfs", "bibfs"), ("dfs", "dfs"), ("iddfs", "iddfs"), ("astar", "astar_gbfs"),
                       ("gbfs", "astar_gbfs"), ("dijkstra", "dijkstra")],
                "T2": [("bellman", "bf_spfa"), ("spfa", "bf_spfa"), ("bidijkstra", "bidijkstra"), ("dial", "dial"),
                       ("dijkstra", "dijkstra"), ("floyd", "floyd")]}[t]
        files = sorted((SUITE / "tasks" / sub / "references").glob("*.py"))
        if t == "T2":
            files.append(EXT_DIR / "t2_wsp" / "dijkstra_array.py")
        for f in files:
            m = next((mode for p, mode in pref if f.stem.startswith(p)), None)
            fl = first_body_line(f.read_text()) if m else None
            if fl:
                out[m].append(fl)
    else:
        from bench.common.catalogue import TASKS

        for r in read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl"):
            if str(r.get("passed")) == "True" and r.get("label") == r.get("forced_mode") and r.get("code"):
                fl = first_body_line(r["code"])
                if fl:
                    out[r["forced_mode"]].append(fl)
        ext = EXT_DIR / t
        if ext.exists():
            for f in sorted(ext.glob("*.py")):
                fl = first_body_line(f.read_text())
                if fl:
                    out[f.stem].append(fl)
    return dict(out)


def lme(x: list[float]) -> float:
    a = np.array(x)
    return float(np.log(np.mean(np.exp(a - a.max()))) + a.max())


def run_ladder(R: Any, tasks: list[str]) -> None:
    tok = R.tok
    draft = read_json(PRED_DIR / "predictors_draft.json")["units"]
    res = read_json(LADDER) if LADDER.exists() else {}
    raw = read_jsonl(DATA_DIR / "raw_twin.jsonl")
    for t in tasks:
        if t in res:
            continue
        D, r_u = draft[t]["D"], draft[t]["r_u"]
        if D is None:
            res[t] = {"defined": False, "reason": "NO_DEFAULT"}
            continue
        ops = openings(t)
        O = {m: collections.Counter(v).most_common(1)[0][0] for m, v in ops.items() if v}
        ctxs = []
        for w in TEMPLATE_IDS:
            got = 0
            for r in sorted((x for x in raw if x["task"] == t and x["template"] == w), key=lambda x: x["slot"]):
                m = re.search(r"```python\n(.*?def solve\([^\n]*\):\n)", r["text"], re.S)
                if not m:
                    continue
                body = r["text"][m.end():]
                ind = re.match(r"((?:[ \t]*\n)*)([ \t]*)", body)
                indent = ind.group(2) if ind and ind.group(2) else "    "
                tw = PG.p_twin(t, w)
                ctxs.append((CHAT_HEAD + tw["text"] + CHAT_TAIL + r["text"][:m.end()], indent))
                got += 1
                if got >= 2:
                    break
        if not ctxs or D not in O:
            res[t] = {"defined": False, "reason": "no contexts or no opening for D", "openings": O}
            continue
        toks_len = {m: len(tok(o, add_special_tokens=False)["input_ids"]) for m, o in O.items()}
        K = int(min(K_MAX, min(toks_len.values())))
        lp: dict[str, list[float]] = collections.defaultdict(list)
        for ctx, indent in ctxs:
            for m, o in O.items():
                full = ctx + indent + o
                enc = tok(full, add_special_tokens=False, return_offsets_mapping=True)
                ids = enc["input_ids"]
                tgt = [i for i, (a, b) in enumerate(enc["offset_mapping"]) if b > len(ctx)][:K]
                if not tgt:
                    continue
                lp[m].append(float(np.sum(R.tf(ids, tgt))))
        logp = {m: lme(v) for m, v in lp.items() if v}
        surv = [m for m in logp if m != D]
        m_r = (logp[D] - logp[r_u]) if (r_u in logp and D in logp) else None
        m_b = (logp[D] - max(logp[m] for m in surv)) if (surv and D in logp) else None
        res[t] = {"defined": m_r is not None or m_b is not None, "D": D, "r_u": r_u, "K": K, "n_contexts": len(ctxs),
                  "openings": O, "logp": logp, "margin_D_vs_r": m_r, "margin_D_vs_best": m_b,
                  "missing_modes": [m for m in PG.modes(t) if m not in O]}
        write_json(LADDER, res)
        logger.info(f"ladder {t}: K={K} margin_D_vs_r={m_r} margin_D_vs_best={m_b}")
    write_json(LADDER, res)
