#!/usr/bin/env python3
"""EXPLORATORY (post hoc, not committed; written after the F verdict): does a longer teacher-forced opening recover
the margin where the decision is made late? The fork screen put T2's only change point at generated token ~92 (off
the default opening) and T03's decision inside the first ~20 tokens. For every POP cell and the prompt / exchange /
noise cells, the opening log-likelihood ratio LLR_L = logsumexp_nondefault logmeanexp log p(first L tokens of the
class's base-path programs) - same for the default class, at L in {16, 32, 48, 96, 128, 160} (T03: up to its
shortest pooled program). Spearman with y per task. Output: results/explore_llr.json."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import SEEDS40, SEEDS_T03, TEMPLATES, RESULTS, read_json, setup_logging, write_json  # noqa: E402
import engine7 as E  # noqa: E402
import fork7 as F  # noqa: E402
import gen7 as G  # noqa: E402
import predict7 as P7  # noqa: E402
import prompts7 as PR  # noqa: E402
import stats7 as S  # noqa: E402

LS = (16, 32, 48, 96, 128, 160)


def programs(task: str, forks_task: dict) -> dict[str, list[list[int]]]:
    rows = {(p["src"], p["arm"], p["template"], int(p["sample_id"])): p for p in F.labelled_programs(task)}
    by: dict[str, list[list[int]]] = {}
    for bp in forks_task.get("base_paths", []):
        p = rows.get((bp["src"], bp["arm"], bp["template"], int(bp["sample_id"])))
        if p:
            by.setdefault(bp["class"], []).append(p["ids"])
    return {c: v[:6] for c, v in by.items() if len(v) >= 5}


def llr_curve(model, rec, edits, progs, default, Ls) -> dict[int, float]:
    """One teacher-forced pass per program up to max(L); cumulative log-probs give every L at once."""
    Lmax = max(Ls)
    cum = {}
    for c, ps in progs.items():
        arr = []
        for x in ps:
            x = x[:Lmax]
            lp = E.forward_lp(model, [rec["ids"] + x], list(range(len(rec["ids"]) - 1, len(rec["ids"]) - 1 + len(x))),
                              edits=edits)[0]
            tok = np.array(x)
            v = lp[np.arange(len(x)), tok].double().cpu().numpy()
            arr.append(np.cumsum(v))
        cum[c] = arr
    out = {}
    for L in Ls:
        lc = {}
        for c, arr in cum.items():
            vals = [a[L - 1] for a in arr if len(a) >= L]
            if len(vals) >= 3:
                lc[c] = float(np.logaddexp.reduce(vals) - math.log(len(vals)))
        non = [v for c, v in lc.items() if c != default]
        if default in lc and non:
            out[L] = float(np.logaddexp.reduce(non) - lc[default])
    return out


def main() -> None:
    setup_logging("explore_llr")
    forks = read_json(common.forks_path())["tasks"]
    import analysis7 as A
    Y = A.outcomes()
    tok, model = E.load()
    res = {}
    for task in ("T2", "T10", "T03"):
        progs = programs(task, forks[task])
        Ls = [L for L in LS if L <= min(len(x) for v in progs.values() for x in v)] if task == "T03" else list(LS)
        if task == "T03":
            Ls = sorted(set(Ls + [min(len(x) for v in progs.values() for x in v)]))
        tm = P7.TaskModel(model, tok, task, {"forks": [], "opening_ids": []}, {})
        cells = {}
        seeds = SEEDS_T03 if task == "T03" else SEEDS40
        for w in TEMPLATES:
            rec_t = tm.ctx.twin(w)["prompt"]
            for s in seeds:
                cur = llr_curve(model, rec_t, P7.pop_edits(tm, w, s), progs, common.DEFAULTS[task], Ls)
                cells.setdefault(f"POP_d{s}_a2.0", []).append(cur)
            cells.setdefault("TWIN", []).append(llr_curve(model, rec_t, None, progs, common.DEFAULTS[task], Ls))
            Hb = P7.capture_all(model, PR.ban(task, w))
            a, b = rec_t["p1"], rec_t["spec_end"]
            for band in ("X_0-35", "X_12-23", "X_24-35", "X_0-11"):
                cells.setdefault(band, []).append(llr_curve(model, rec_t, P7.set_rows(a, b, Hb, P7.BANDS[band]), progs,
                                                            common.DEFAULTS[task], Ls))
            cells.setdefault("BAN", []).append(llr_curve(model, PR.ban(task, w), None, progs, common.DEFAULTS[task], Ls))
            del Hb
            logger.info(f"{task}/{w} done")
        agg = {c: {L: float(np.mean([d[L] for d in v if L in d])) for L in Ls} for c, v in cells.items()}
        out = {"L": Ls, "per_L": {}}
        for L in Ls:
            m = [agg[f"POP_d{s}_a2.0"][L] for s in seeds if f"{task}|POP_d{s}_a2.0" in Y]
            y = [Y[f"{task}|POP_d{s}_a2.0"]["y"] for s in seeds if f"{task}|POP_d{s}_a2.0" in Y]
            allm = [agg[c][L] for c in agg if f"{task}|{c}" in Y]
            ally = [Y[f"{task}|{c}"]["y"] for c in agg if f"{task}|{c}" in Y]
            out["per_L"][str(L)] = {"pop_spearman": S.spearman(m, y), "pop_p": S.perm_p(m, y, 5000, seed=L),
                                    "all_cell_spearman": S.spearman(allm, ally), "n_pop": len(y)}
        out["cells"] = {c: {str(L): v for L, v in d.items()} for c, d in agg.items()}
        res[task] = out
        tm.ctx.release()
        logger.info(f"{task}: {out['per_L']}")
    res["note"] = ("EXPLORATORY, post hoc (after the committed F verdict); not a pre-registered test; Holm not "
                   "applied")
    write_json(RESULTS / "explore_llr.json", res)


if __name__ == "__main__":
    main()
