"""(0a) One-statistic knob table: one row per artifact x task x arm x dial cell, priced against its own twin."""

from __future__ import annotations

import json
import multiprocessing as mp
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.paths import ARTIFACTS, exp_name
from src.stats import DEPTH, DEPTH_LOW, h1r_cell, newcombe_diff

NONCAT_DROP_MARK = "__noncat__"


# ------------------------------------------------------------------------------------------------ arm dictionary
def classify(exp: str, arm: str, dial: dict) -> tuple[str, str, str]:
    """-> (class, family, one-line description)."""
    a = arm
    if exp == "exp13":
        m = {"twin": ("control", "twin", "neutral twin (vLLM)"), "hf_twin": ("control", "twin", "neutral twin (HF engine)"),
             "sham": ("control", "sham_veto", "sham token veto"), "ban": ("knob", "prompt:ban", "modal 'do not use X' ban"),
             "nonce": ("knob", "prompt:nonce", "nonce ban"), "novelty": ("knob", "prompt:novelty", "novelty instruction"),
             "oneshot": ("knob", "veto", "one-shot token veto"), "persistent": ("knob", "veto", "persistent token veto"),
             "iter1": ("knob", "veto", "iterated veto round 1"), "iter2": ("knob", "veto", "iterated veto round 2"),
             "iter3": ("knob", "veto", "iterated veto round 3"),
             "bandpatch": ("knob", "activation-ban-derived", "ban task-spec states patched into the twin (ban-derived)")}
        if a in m:
            return m[a]
        if a.startswith("rand"):
            return ("knob", "activation-random", "matched-norm isotropic random direction at task-spec states, layers 12-23")
    if exp == "exp17":
        if a == "NEUTRAL":
            return ("control", "twin", "neutral twin (HF, FP8 linears)")
        if a.startswith("BAN"):
            return ("knob", "prompt:ban", "modal ban" + (" (top-up samples)" if "TOPUP" in a else ""))
        if a.startswith("ADD"):
            return ("knob", "activation-structured", "leave-one-task-out prohibition direction added to the twin")
        if a.startswith("RAND"):
            return ("knob", "activation-random", "norm-matched random direction added to the twin")
        if a.startswith("SUB") or a.startswith("HEADS"):
            return ("ablation", "ablation-on-ban", "intervention on the ban (projection / head ablation); not a knob")
        if a.startswith("U7"):
            return ("control", "engine_check", "U7 engine reproduction check")
    if exp == "exp15":
        if a in ("neutral_baseline", "vetofree"):
            return ("control", "twin", "Llama neutral twin" + (" (veto chain pass-1)" if a == "vetofree" else ""))
        if a == "pilot_fp8":
            return ("control", "pilot", "Llama FP8 pilot (no ban)")
        if a in ("nonce", "novelty"):
            return ("knob", f"prompt:{a}", f"{a} prompt (Llama)")
        if a.startswith("rand_"):
            return ("knob", "activation-random", "matched-norm random direction at spec positions, layers 11-21 (Llama)")
        if a.startswith("ban_"):
            return ("knob", "prompt:ban", f"{a.split(':')[0][4:]} ban of {a.split(':')[1]} (Llama)")
        if a.startswith("veto_"):
            return ("knob", "veto", f"{a[5:]} signature-n-gram veto (Llama)")
    if exp == "exp16":
        return ("control", "route_diagnostic", {"a": "full ban", "b": "token-matched neutral twin",
                                                "c": "prompt route (twin condition + ban spec states)",
                                                "d": "direct route (ban condition + twin spec states)",
                                                "K0": "condition span invisible to generated tokens",
                                                "V1": "one-shot veto of the default's n-gram"}.get(a, "route/prefill diagnostic arm"))
    if exp == "exp14":
        kind = a.split(":")[0]
        if kind == "copy":
            return ("control", "copy", "COPY: shown programs of Y, no ban")
        if kind == "baseline":
            return ("control", "twin", "no-exposure baseline")
        if kind in ("named", "unnamed"):
            return ("knob", "prompt:exposure_ban", f"{kind.upper()} exposure ban of the shown algorithm")
        if kind == "veto":
            return ("knob", "veto", "in-context signature veto of the shown algorithm")
        if kind.startswith("W"):
            return ("knob", "prompt:exposure_ban", f"exposure ban, template arm {kind}")
    if exp == "exp18":
        if a == "walk_twin":
            return ("control", "twin", "neutral twin (walk step 0)")
        if a.startswith("walk_step"):
            return ("knob", "veto", "persistent token-walk veto")
        if a == "sham":
            return ("control", "sham_veto", "matched sham veto")
        if a == "fixed_top5":
            return ("knob", "veto", "fixed TOP5 veto")
        if a.startswith("los:"):
            return ("knob", "prompt:list", "leave-one-survivor list ban")
        if a.startswith("two_step:"):
            return ("knob", "prompt:ban", "two-step ban")
        if a.startswith("longform:"):
            return ("knob", "prompt:instruction", "2,000-word 'make a (fully) novel algorithm' instruction")
    if exp == "exp9":
        if a == "baseline":
            return ("control", "twin", "no-ban baseline")
        if a.startswith("single:"):
            return ("knob", "prompt:ban", "single-name ban")
        if a.startswith("los:"):
            return ("knob", "prompt:list", "leave-one-survivor list")
        if a.startswith("multi:"):
            return ("knob", "prompt:list", "multi-name ban list")
    if exp == "exp4":
        if a == "baseline":
            return ("control", "twin", "vLLM baseline")
        if a == "steer:dc":
            if dial.get("c", 0) == 0:
                return ("control", "twin", "HF c=0 hook")
            return ("knob", "activation-structured", "decommitment direction d_dc")
        if a in ("steer:rand1", "steer:rand2"):
            return ("knob", "activation-random", "random direction (iteration 1)")
        if a == "steer:placebo":
            return ("knob", "activation-structured", "variable-name placebo direction")
        if a == "steer:breadth":
            return ("knob", "activation-structured", "breadth direction")
        if a == "steer:dcxfer":
            return ("knob", "activation-structured", "cross-task transferred d_dc")
        if a.startswith("enumerate"):
            return ("knob", "prompt:instruction", "enumeration prompt")
        if a.startswith("ban:"):
            return ("knob", "prompt:ban", "modal ban")
        if a.startswith("mention:"):
            return ("control", "mention_twin", "mention twin")
        if a.startswith("succession"):
            return ("knob", "prompt:ban", "succession ban")
    if exp == "exp6":
        kind, cond = a.split(":", 1)
        if kind == "A0":
            return ("control", "twin", "no-cue baseline T=1.0, pure sampling, thinking off")
        if kind in ("A1", "A6a", "A6b", "A6c", "A6d"):
            return ("knob", "decoding", "temperature x sampler grid" + (" (thinking on)" if dial.get("thinking") else ""))
        if kind == "A2":
            return ("knob", "prompt:seed", f"{cond.replace('seed_', '')} seed")
        if kind == "A3":
            return ("knob", "prompt:instruction", f"creativity instruction {cond}")
        if kind.startswith("A4"):
            return ("ceiling", "generate_then_select", "generate-then-select (ceiling, never ranked)")
    if exp == "exp11":
        return ("control", "pilot", "FP8 pilot (no ban)")
    return ("unclassified", "unclassified", a)


def ref_of(exp: str, arm: str, dial: dict, task: str, precision: str, cells: set) -> tuple[tuple | None, list[str]]:
    """Own-twin reference cell key (exp, task, arm, dial_json, precision) and flags."""
    flags: list[str] = []
    dj = json.dumps({}, sort_keys=True)
    cand = None
    if exp == "exp13":
        hf = arm.startswith("rand") or arm in ("bandpatch", "hf_twin")
        cand = (task, "hf_twin" if hf else "twin", dj)
    elif exp == "exp17":
        cand = (task, "NEUTRAL", dj)
    elif exp == "exp15":
        cand = (task, "vetofree" if arm.startswith("veto_") else "neutral_baseline", dj)
    elif exp == "exp16":
        cand = (task, "b", dj)
    elif exp == "exp14":
        kind = arm.split(":")[0]
        y = arm.split(":", 1)[1] if ":" in arm else None
        cand = (task, "baseline", dj) if kind == "copy" else (task, f"copy:{y}", dj)
    elif exp == "exp18":
        cand = (task, "walk_twin", dj)
    elif exp == "exp9":
        cand = (task, "baseline", dj)
    elif exp == "exp4":
        if arm in ("baseline",) or arm.startswith(("ban:", "mention:", "enumerate", "succession")):
            cand = (task, "baseline", dj)
        else:
            cand = (task, "steer:dc", json.dumps({"c": 0.0, "layer": 18}, sort_keys=True))
    elif exp == "exp6":
        cand = (task, "A0:baseline", json.dumps({"T": 1.0, "sampler": "pure", "thinking": False}, sort_keys=True))
        if dial.get("thinking"):
            flags.append("ref_thinking_off")
    if cand is None:
        return None, flags
    key = (exp,) + cand + (precision,)
    if key in cells:
        return key, flags
    others = [c for c in cells if c[:4] == key[:4]]
    if others:
        flags.append("cross_precision_ref")
        return others[0], flags
    return None, flags + ["no_own_twin"]


# ------------------------------------------------------------------------------------------------ cells
def _cell_job(args: tuple) -> dict:
    cid, labels, templates, noncat = args
    prim = h1r_cell(labels, templates, cid, DEPTH)
    cat = h1r_cell(labels, templates, cid + "|cat", DEPTH, drop=noncat, with_ci=False)
    low = h1r_cell(labels, templates, cid, DEPTH_LOW, with_ci=False) if prim["n_c"] < DEPTH else None
    return {"cid": cid, "prim": prim, "cat": cat, "low": low}


def build_knob_table(rows: pd.DataFrame, n_workers: int = 5) -> pd.DataFrame:
    rows = rows.copy()
    rows["exp"] = rows.artifact_id.map(exp_name)
    keys = ["exp", "artifact_id", "task", "arm", "dial", "precision"]
    groups = list(rows.groupby(keys, sort=True))
    cellset = {(k[0], k[2], k[3], k[4], k[5]) for k, _ in groups}
    base = []
    jobs = []
    for (exp, aid, task, arm, dial, prec), g in groups:
        cid = f"{aid}|{task}|{arm}|{dial}|{prec}"
        att = g[g.attempted]
        cor = g[g.passed]
        noncat = sorted(set(cor.label_norm[~cor.is_catalogue]))
        jobs.append((cid, cor.label_norm.tolist(), cor.template.tolist(), noncat))
        base.append({"cid": cid, "exp": exp, "artifact_id": aid, "src_file": g.src_file.iloc[0], "model": g.model.iloc[0],
                     "engine": ",".join(sorted(set(g.engine))), "precision": prec, "task": task, "arm": arm,
                     "dial": dial, "n": int(len(g)), "n_attempted": int(len(att)), "n_correct": int(len(cor)),
                     "n_default_att": int(att.is_default.sum()),
                     "n_cat_nondefault_att": int((att.is_catalogue & ~att.is_default).sum()),
                     "correct_composition": json.dumps(dict(Counter(cor.label_norm).most_common())),
                     "attempted_composition": json.dumps(dict(Counter(att.label_norm).most_common())),
                     "offdef_attempted_cat_composition": json.dumps(dict(Counter(
                         att.label_norm[att.is_catalogue & ~att.is_default]).most_common())),
                     "other_share": float((att.label_norm == "other").mean()) if len(att) else float("nan")})
    logger.info(f"knob table: {len(base)} cells; computing rarefied Hill-1 with {n_workers} workers")
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn")) as ex:
        res = {r["cid"]: r for r in ex.map(_cell_job, jobs, chunksize=8)}
    out = []
    for b in base:
        r = res[b["cid"]]
        prim, cat, low = r["prim"], r["cat"], r["low"]
        dial = json.loads(b["dial"])
        cls, fam, desc = classify(b["exp"], b["arm"], dial)
        b.update({"class": cls, "family": fam, "description": desc,
                  "pass_rate": b["n_correct"] / b["n"] if b["n"] else float("nan"),
                  "offdef_share": 1 - b["n_default_att"] / b["n_attempted"] if b["n_attempted"] else float("nan"),
                  "cat_only_avoidance": b["n_cat_nondefault_att"] / b["n_attempted"] if b["n_attempted"] else float("nan"),
                  "H1r25": prim["value"], "H1r25_ci90": json.dumps([round(x, 4) for x in prim["ci90"]]),
                  "H1r25_ci90_iid": json.dumps([round(x, 4) for x in prim["ci90_iid"]]), "ci_unit": prim["ci_unit"],
                  "H1r25_cat": cat["value"], "H1r10": (low or {}).get("value", float("nan")),
                  "S_obs": prim["S_obs"], "coverage": prim["coverage"]})
        ref, flags = ref_of(b["exp"], b["arm"], dial, b["task"], b["precision"], cellset)
        b["ref_key"] = json.dumps(ref) if ref else ""
        b["flags_list"] = flags + (["below_depth"] if prim["n_c"] < DEPTH else [])
        out.append(b)
    df = pd.DataFrame(out)
    idx = {(r.exp, r.task, r.arm, r.dial, r.precision): i for i, r in df.iterrows()}
    ref_pass, ref_arm, cost, cost_ci, ref_off, esc, qual = [], [], [], [], [], [], []
    for _, r in df.iterrows():
        if not r.ref_key:
            ref_pass.append(np.nan); ref_arm.append(""); cost.append(np.nan); cost_ci.append("[]"); ref_off.append(np.nan)
            esc.append(None); qual.append(None)
            continue
        rk = tuple(json.loads(r.ref_key))
        rr = df.loc[idx[rk]]
        ref_arm.append(f"{rr.arm}{'' if rr.dial == '{}' else ' ' + rr.dial}")
        ref_pass.append(rr.pass_rate)
        d, lo, hi = newcombe_diff(int(rr.n_correct), int(rr.n), int(r.n_correct), int(r.n))
        cost.append(100 * d)
        cost_ci.append(json.dumps([round(100 * lo, 2), round(100 * hi, 2)]))
        ref_off.append(rr.offdef_share)
        if r["class"] == "control":
            esc.append(None); qual.append(None)
        else:
            esc.append(bool((r.offdef_share - rr.offdef_share) >= 0.20 and r.pass_rate >= 0.8 * rr.pass_rate))
            qual.append(bool(np.isfinite(r.H1r25) and r.H1r25 >= 2 and 100 * d <= 20))
    df["ref_arm"], df["ref_pass"], df["pass_cost_pts"], df["pass_cost_ci95"] = ref_arm, ref_pass, cost, cost_ci
    df["ref_offdef_share"], df["escape"], df["qualify"] = ref_off, esc, qual
    df["flags"] = df.flags_list.map(lambda x: ";".join(x))
    df["sources"] = df.artifact_id + ":" + df.src_file
    df["row_id"] = [f"K{i:04d}" for i in range(len(df))]
    return df


KNOB_COLUMNS = ["row_id", "artifact_id", "src_file", "model", "engine", "precision", "task", "arm", "class", "family",
                "dial", "n", "n_attempted", "n_correct", "pass_rate", "ref_arm", "ref_pass", "pass_cost_pts",
                "pass_cost_ci95", "offdef_share", "ref_offdef_share", "cat_only_avoidance", "other_share", "H1r25",
                "H1r25_ci90", "H1r25_ci90_iid", "ci_unit", "H1r25_cat", "H1r10", "S_obs", "coverage",
                "correct_composition", "attempted_composition", "offdef_attempted_cat_composition", "escape",
                "qualify", "flags", "sources", "description", "realised_l21_displacement_ratio"]


def arm_dictionary(knob: pd.DataFrame) -> pd.DataFrame:
    d = knob.groupby(["artifact_id", "arm"]).agg(cls=("class", "first"), family=("family", "first"),
                                                  description=("description", "first"), ref_arm=("ref_arm", "first"),
                                                  engine=("engine", "first"), precision=("precision", "first"),
                                                  n_cells=("row_id", "count")).reset_index()
    return d.rename(columns={"cls": "class"})


def direction_id(exp: str, arm: str) -> str:
    return f"{exp}:{arm}"


def is_random_direction(r: pd.Series) -> bool:
    return r["family"] == "activation-random" and r["model"].startswith("Qwen") and r["exp"] in ("exp13", "exp17")


def alpha_of(r: pd.Series) -> float:
    if r["exp"] == "exp17":
        m = re.search(r"_a(\d+(?:\.\d+)?)$", r["arm"])
        return float(m.group(1)) if m else float("nan")
    return 1.0  # exp13 matched-norm random directions (norm of the ban displacement) are the alpha-1 analogue
