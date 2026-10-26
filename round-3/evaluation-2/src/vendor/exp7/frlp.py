# Vendored verbatim from art_6zBfl3kDjeiP:src/frlp.py (iteration-2 exp7); only config.py is patched.
#!/usr/bin/env python3
"""Step 4: forced-ratio latent probabilities (FRLP).

For task t, condition c, algorithm j and a program set P of forced j-programs (draws from the balance-heuristic
mixture q_j = (1/10) sum_k P(.|F_j^k)):  lw_m = l(p_m|c) - l_q(p_m),
    L_j(c) = log y_j + logsumexp_m(lw_m) - log|P|       (yield-corrected importance-sampling estimate of log P(j|c))
    L_raw  = L_j(c) - log y_j                           (the direction's literal formula)
    ESS    = exp(2 lse(lw) - lse(2 lw)).
Cells are computed from per-program weights so the bootstrap can resample programs within algorithm-halves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from config import (DATA, MODEL_ID, MODES, RESULTS, SCORES, TASKS, logsumexp, read_json, read_jsonl, write_jsonl)

UNITS_DONE = SCORES / "units_done.jsonl"
M_SCORED = 30
SCORE_COLS = ("total", "body", "cum256")
VARIANTS = {  # name -> (score column, denominator kind, program filter, scrubbed?)
    "primary": ("total", "mixture", "all", "primary"),
    "code_body_only": ("body", "mixture", "all", "primary"),
    "correct_only": ("total", "mixture", "passed", "primary"),
    "single_proposal": ("total", "single", "all", "primary"),
    "truncated_256": ("cum256", "mixture", "all", "primary"),
    "unscrubbed": ("total", "mixture_raw", "all", "unscrubbed"),
    "unscrubbed_body_single": ("body", "single_raw", "all", "unscrubbed"),
}


def load_scores() -> pd.DataFrame:
    units = read_jsonl(UNITS_DONE)
    seen, frames = set(), []
    for u in units:
        if (u["task"], u["uid"]) in seen:  # uids are unique within a task only
            continue
        seen.add((u["task"], u["uid"]))
        p = SCORES / "cells" / u["task"] / f"{u['uid']}.parquet"
        if not p.exists():
            continue
        df = pd.read_parquet(p)
        for k in ("task", "queue", "cond_id", "progset", "variant"):
            df[k] = u[k]
        df["direction"] = u.get("direction")
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@dataclass
class TaskData:
    task: str
    progs: pd.DataFrame                       # index prog_id: j, half, passed, paraphrase_id, family
    yields: dict[str, float]
    yields_pass: dict[str, float]
    measurable: list[str]
    L: dict[str, pd.DataFrame] = field(default_factory=dict)        # column -> (variant|cond) x prog_id
    lq: dict[str, pd.Series] = field(default_factory=dict)          # denominator kind|column -> prog_id

    def key(self, cond: str, variant: str = "primary") -> str:
        return f"{variant}|{cond}"

    def lw(self, cond: str, vname: str = "primary") -> pd.Series:
        col, den, _filt, scr = VARIANTS[vname]
        k = self.key(cond, "unscrubbed" if scr == "unscrubbed" else self._variant_of(cond))
        if k not in self.L[col].index:
            raise KeyError(k)
        return self.L[col].loc[k] - self.lq[f"{den}|{col}"]

    @staticmethod
    def _variant_of(cond: str) -> str:
        if cond.startswith("edit2|"):
            return "edit2"
        if cond.startswith("edit|"):
            return "edit"
        return "primary"

    def has(self, cond: str, vname: str = "primary") -> bool:
        col, _d, _f, scr = VARIANTS[vname]
        k = self.key(cond, "unscrubbed" if scr == "unscrubbed" else self._variant_of(cond))
        return k in self.L[col].index

    def pids(self, j: str, half: str = "all", vname: str = "primary") -> list[str]:
        _c, _d, filt, _s = VARIANTS[vname]
        p = self.progs[self.progs["j"] == j]
        if half in ("h1", "h2"):
            p = p[p["half"] == half]
        if filt == "passed":
            p = p[p["passed"]]
        return list(p.index)

    def cell(self, cond: str, j: str, half: str = "all", vname: str = "primary") -> dict[str, Any]:
        """Point estimate of L_j(cond) on the given half; NaN if not scored."""
        pids = self.pids(j, half, vname)
        try:
            lw = self.lw(cond, vname).reindex(pids).to_numpy(dtype=float)
        except KeyError:
            return {"L": math.nan, "L_raw": math.nan, "ess": math.nan, "n": 0}
        lw = lw[np.isfinite(lw)]
        if len(lw) == 0:
            return {"L": math.nan, "L_raw": math.nan, "ess": math.nan, "n": 0}
        lse = logsumexp(lw)
        L_raw = lse - math.log(len(lw))
        y = self.yields_pass[j] if VARIANTS[vname][2] == "passed" else self.yields[j]
        ess = math.exp(2 * lse - logsumexp(2 * lw))
        return {"L": L_raw + math.log(max(y, 1e-12)), "L_raw": L_raw, "ess": ess, "n": int(len(lw))}


def _m_scored() -> int:
    from config import LOGS

    p = LOGS / "throughput.json"
    return int(read_json(p)["M"]) if p.exists() else 30


def build_task_data(scores: pd.DataFrame | None = None) -> dict[str, TaskData]:
    M_SCORED = _m_scored()
    globals()["M_SCORED"] = M_SCORED
    if scores is None:
        scores = load_scores()
    sel = pd.DataFrame(read_jsonl(DATA / "forced_selected.jsonl")).set_index("prog_id")
    yl = read_json(RESULTS / "yields.json")["yields"]
    out = {}
    for t in TASKS:
        df = scores[scores["task"] == t]
        progs = sel[sel["task"] == t][["j", "half", "passed", "paraphrase_id", "family", "rank", "m_j"]].copy()
        progs = progs[progs["rank"] < np.minimum(progs["m_j"], M_SCORED)]
        meas = [j for j in MODES[t] if yl.get(f"{t}|{j}", {}).get("measurable") and (progs["j"] == j).any()]
        y = {j: yl[f"{t}|{j}"]["yield"] for j in meas}
        yp = {j: yl[f"{t}|{j}"]["passed_labelled_" + yl[f"{t}|{j}"]["family"]]
              / max(1, yl[f"{t}|{j}"]["attempts_" + yl[f"{t}|{j}"]["family"]]) for j in meas}
        td = TaskData(task=t, progs=progs, yields=y, yields_pass=yp, measurable=meas)
        if df.empty:
            out[t] = td
            continue
        df = df.assign(key=df["variant"] + "|" + df["cond_id"])
        for col in SCORE_COLS:
            td.L[col] = df.pivot_table(index="key", columns="prog_id", values=col, aggfunc="first")
        # denominators: balance-heuristic mixture over the family's 10 paraphrases; single = generating paraphrase
        for col in SCORE_COLS:
            mix, single = {}, {}
            for pid, r in progs.iterrows():
                keys = [f"primary|forced|{r['j']}|{r['family']}|k{k}" for k in range(10)]
                vals = [td.L[col].at[k, pid] if (k in td.L[col].index and pid in td.L[col].columns) else np.nan
                        for k in keys]
                vals = np.array(vals, dtype=float)
                if np.isfinite(vals).all():
                    mix[pid] = logsumexp(vals) - math.log(10)
                kg = int(r["paraphrase_id"])
                single[pid] = vals[kg] if np.isfinite(vals[kg]) else np.nan
            td.lq[f"mixture|{col}"] = pd.Series(mix, dtype=float)
            td.lq[f"single|{col}"] = pd.Series(single, dtype=float)
            raw, rawmix = {}, {}
            for pid, r in progs.iterrows():
                k = f"unscrubbed|forced|{r['j']}|{r['family']}|k{int(r['paraphrase_id'])}"
                if k in td.L[col].index and pid in td.L[col].columns:
                    raw[pid] = td.L[col].at[k, pid]
                keys = [f"unscrubbed|forced|{r['j']}|{r['family']}|k{kk}" for kk in range(10)]
                vals = np.array([td.L[col].at[k2, pid] if (k2 in td.L[col].index and pid in td.L[col].columns)
                                 else np.nan for k2 in keys], dtype=float)
                if np.isfinite(vals).all():
                    rawmix[pid] = logsumexp(vals) - math.log(10)
            td.lq[f"single_raw|{col}"] = pd.Series(raw, dtype=float)
            td.lq[f"mixture_raw|{col}"] = pd.Series(rawmix, dtype=float)
        out[t] = td
    return out


def mixture_identity(tds: dict[str, TaskData]) -> dict[str, Any]:
    """Validation (v): logmeanexp_k l(p|F_j^k) - l_q(p) == 0 (recomputed independently with numpy)."""
    worst = 0.0
    n = 0
    for t, td in tds.items():
        if "total" not in td.L:
            continue
        for pid, r in td.progs.iterrows():
            keys = [f"primary|forced|{r['j']}|{r['family']}|k{k}" for k in range(10)]
            if not all(k in td.L["total"].index for k in keys) or pid not in td.lq["mixture|total"].index:
                continue
            v = td.L["total"].loc[keys, pid].to_numpy(dtype=np.float64)
            lme = np.log(np.mean(np.exp(v - v.max()))) + v.max()
            worst = max(worst, abs(lme - td.lq["mixture|total"][pid]))
            n += 1
    return {"n_programs": n, "max_abs_diff": worst, "pass": bool(n > 0 and worst < 1e-6)}


def write_cells(tds: dict[str, TaskData], path=RESULTS / "frlp_cells.jsonl") -> int:
    rows = []
    for t, td in tds.items():
        if "total" not in td.L:
            continue
        conds = sorted({k.split("|", 1)[1] for k in td.L["total"].index})
        for cond in conds:
            for vname in VARIANTS:
                if not td.has(cond, vname):
                    continue
                for j in td.measurable:
                    for half in ("all", "h1", "h2"):
                        c = td.cell(cond, j, half, vname)
                        if c["n"] == 0:
                            continue
                        parts = cond.split("|")
                        rows.append({"task": t, "model": MODEL_ID, "condition": cond,
                                     "template": next((p for p in parts if p.startswith("W")), None),
                                     "algorithm": j, "L": c["L"], "L_raw": c["L_raw"], "ess": c["ess"],
                                     "n_programs": c["n"], "half": half, "variant": vname})
    write_jsonl(path, rows)
    logger.info(f"wrote {len(rows)} FRLP cells")
    return len(rows)


# ------------------------------------------------------------------------------------------------ fast arrays
class CellArrays:
    """Vectorised cells for the bootstrap: for each condition row c and algorithm j, L over h1, h2 and all,
    recomputed from per-program multiplicity weights W (W = 1 is the point estimate)."""

    def __init__(self, td: TaskData, conds: list[str], vname: str = "primary",
                 virtual: dict[str, tuple[str, str]] | None = None) -> None:
        self.td, self.vname = td, vname
        self.conds = list(conds) + list((virtual or {}).keys())
        self.cidx = {c: i for i, c in enumerate(self.conds)}
        self.js = [j for j in td.measurable if td.pids(j, "all", vname)]  # e.g. correct_only drops j with no passes
        pids = [p for j in self.js for p in td.pids(j, "all", vname)]
        self.pids = pids
        self.pj = np.array([self.js.index(td.progs.at[p, "j"]) for p in pids])
        self.ph = np.array([0 if td.progs.at[p, "half"] == "h1" else 1 for p in pids])
        lw = np.full((len(self.conds), len(pids)), np.nan)
        for i, c in enumerate(conds):
            if td.has(c, vname):
                lw[i] = td.lw(c, vname).reindex(pids).to_numpy(dtype=float)
        for name, (ca, cb) in (virtual or {}).items():
            i = self.cidx[name]
            a = td.lw(ca, vname).reindex(pids).to_numpy(dtype=float) if td.has(ca, vname) else np.full(len(pids), np.nan)
            b = td.lw(cb, vname).reindex(pids).to_numpy(dtype=float) if td.has(cb, vname) else np.full(len(pids), np.nan)
            lw[i] = np.where(self.ph == 0, a, b)
        self.lw = lw
        self.valid = np.isfinite(lw)
        shift = np.zeros((len(self.conds), len(self.js)))
        for k in range(len(self.js)):
            m = self.pj == k
            if not m.any():
                continue
            sub = np.where(self.valid[:, m], lw[:, m], -np.inf)
            mx = sub.max(axis=1)
            shift[:, k] = np.where(np.isfinite(mx), mx, 0.0)
        self.shift = shift
        self.E = np.where(self.valid, np.exp(np.where(self.valid, lw, 0.0) - shift[:, self.pj]), 0.0)
        self.E2 = self.E ** 2
        y = td.yields_pass if VARIANTS[vname][2] == "passed" else td.yields
        self.logy = np.log(np.maximum(np.array([y[j] for j in self.js]), 1e-12))

    def cells(self, W: np.ndarray | None = None, with_ess: bool = False):
        """Returns L[h] arrays (n_cond x K) for h in ('h1','h2','all'); NaN where not scored."""
        if W is None:
            W = np.ones(len(self.pids))
        out, ess = {}, {}
        for hname, hmask in (("h1", self.ph == 0), ("h2", self.ph == 1), ("all", np.ones(len(self.pids), bool))):
            L = np.full((len(self.conds), len(self.js)), np.nan)
            Es = np.full((len(self.conds), len(self.js)), np.nan)
            for k in range(len(self.js)):
                m = (self.pj == k) & hmask
                if not m.any():
                    continue
                Wm = W[m]
                Vm = self.valid[:, m]
                n = Vm.astype(float) @ Wm
                s = self.E[:, m] @ Wm
                ok = (n > 0) & (s > 0)
                L[ok, k] = self.logy[k] + self.shift[ok, k] + np.log(s[ok]) - np.log(n[ok])
                if with_ess:
                    s2 = self.E2[:, m] @ Wm
                    Es[ok, k] = s[ok] ** 2 / s2[ok]
            out[hname] = L
            ess[hname] = Es
        return (out, ess) if with_ess else out

    def boot_weights(self, rng: np.random.Generator) -> np.ndarray:
        W = np.zeros(len(self.pids))
        for k in range(len(self.js)):
            for h in (0, 1):
                idx = np.where((self.pj == k) & (self.ph == h))[0]
                if len(idx):
                    W[idx] = rng.multinomial(len(idx), np.full(len(idx), 1 / len(idx)))
        return W


def coverage(td_progs: pd.DataFrame | None = None) -> dict[str, Any]:
    """AST 4-gram shingles (identifier-normalised) of forced programs vs natural exp1 programs of the same label."""
    import ast

    from config import DATA_IN

    def shingles(code: str) -> set:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return set()
        toks = []
        for n in ast.walk(tree):
            name = type(n).__name__
            if isinstance(n, ast.Name):
                name = "Name"
            elif isinstance(n, ast.Attribute):
                name = f"Attr.{n.attr}"
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                name = f"Call.{n.func.attr}"
            toks.append(name)
        return {tuple(toks[i:i + 4]) for i in range(max(0, len(toks) - 3))}

    sel = pd.DataFrame(read_jsonl(DATA / "forced_selected.jsonl"))
    nat = [r for r in read_jsonl(DATA_IN / "exp1" / "labelled.jsonl") if r.get("code") and r["label"] != "no_code"
           and r["decoding"].startswith("T1.0") and not r["condition"].startswith("forced")]
    out = {}
    for t in TASKS:
        for j in MODES[t]:
            fs = [shingles(c) for c in sel[(sel["task"] == t) & (sel["j"] == j)]["code_scrubbed"]]
            ns = [shingles(r["code"]) for r in nat if r["task"] == t and r["label"] == j]
            if not fs or not ns:
                out[f"{t}|{j}"] = {"n_forced": len(fs), "n_natural": len(ns), "share_nn_jaccard_ge_0.5": None,
                                   "mean_nn_jaccard": None}
                continue
            nn = []
            for a in ns:
                best = max((len(a & b) / max(1, len(a | b)) for b in fs), default=0.0)
                nn.append(best)
            out[f"{t}|{j}"] = {"n_forced": len(fs), "n_natural": len(ns),
                               "share_nn_jaccard_ge_0.5": float(np.mean([x >= 0.5 for x in nn])),
                               "mean_nn_jaccard": float(np.mean(nn))}
    return out
