#!/usr/bin/env python3
"""Stage 0.5 (screen file), 5.4 (reused rows) and the screen-derived forecast committed in 4.3.

Screen: iteration-3 exp17 data/labels.jsonl (NEUTRAL, RAND9001..9015_a1.0, RAND9001..9003_a2.0; FP8 HF) and exp13
data/samples.jsonl (rand1-3 at alpha 1 against exp13's engine-matched HF twin 'hf_twin'; bf16 HF), at the N run
there with no top-up. Escape of a direction: off-default share minus the twin's >= 0.20 AND pass >= 0.8 x the
twin's pass (off-default = label not in {default, invalid}; the variant counting invalid as off-default is also
reported). CONFIRMED: additionally a one-sided exact binomial p < 0.05 of the off-default count against
p0 = (k_twin + 0.5) / (n_twin + 1).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from loguru import logger
from scipy.stats import binomtest

from cfg import (DATA_DIR, DEFAULT, E13, E16, E17, E6_TASKS, PRED_DIR, RESULTS_DIR, read_jsonl, sha256_file,
                 utc_now, write_json, write_jsonl)

QUOTED = {"T03": "7/15 at alpha 1", "T2": "3/15 at alpha 1", "T05": "0/3 at alpha 1, 2/3 at alpha 2",
          "T06": "1/3 at alpha 2", "T04": "0/6"}


def _lab(r: dict[str, Any]) -> str:
    lab = r.get("label")
    if lab == "disputed":
        lab = r.get("fallback_label") or "other"
    return lab


def screen_rows() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """{task: {arm: [rows with label, passed]}} for the screen arms."""
    out: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    pat = re.compile(r"^RAND(90(0[1-9]|1[0-5]))_a(1\.0|2\.0)$")
    for r in read_jsonl(E17 / "data" / "labels.jsonl"):
        a = r["arm"]
        if a == "NEUTRAL" or pat.match(a):
            out[r["task"]]["exp17:" + a].append({"label": _lab(r), "passed": bool(r.get("passed")),
                                                 "template": r["template"], "slot": r["sample_id"]})
    for r in read_jsonl(E13 / "data" / "samples.jsonl"):
        c = r["condition"]
        if c in ("hf_twin", "twin", "rand1", "rand2", "rand3"):
            out[r["task"]]["exp13:" + c].append({"label": r["label"], "passed": str(r["passed"]) == "True"
                                                 or r["passed"] is True, "template": r["template"],
                                                 "slot": r["sample_id"]})
    return out


def off_default(rows: list[dict[str, Any]], task: str, invalid_counts: bool = False) -> int:
    D = DEFAULT[task]
    if invalid_counts:
        return sum(1 for r in rows if r["label"] != D)
    return sum(1 for r in rows if r["label"] not in (D, "invalid"))


def build_screen() -> dict[str, Any]:
    rows = screen_rows()
    res: dict[str, Any] = {"tasks": {}, "E6": list(E6_TASKS), "utc": utc_now(),
                           "rule": "escape: off-default share - twin's >= 0.20 AND pass >= 0.8 x twin pass; confirmed: "
                                   "one-sided exact binomial p < 0.05 vs p0 = (k_twin + 0.5) / (n_twin + 1)"}
    for t, arms in sorted(rows.items()):
        tres: dict[str, Any] = {"directions": {}}
        for src, twin_arm in (("exp17", "exp17:NEUTRAL"), ("exp13", "exp13:hf_twin")):
            if twin_arm not in arms:
                continue
            tw = arms[twin_arm]
            n0 = len(tw)
            k0 = off_default(tw, t)
            k0i = off_default(tw, t, True)
            p_tw = np.mean([r["passed"] for r in tw])
            tres[f"twin_{src}"] = {"n": n0, "off_default": k0, "pass": float(p_tw)}
            for a, rs in arms.items():
                if not a.startswith(src + ":") or a in (twin_arm, "exp13:twin"):
                    continue
                n = len(rs)
                k = off_default(rs, t)
                ki = off_default(rs, t, True)
                pas = float(np.mean([r["passed"] for r in rs]))
                exc = k / n - k0 / n0
                esc = exc >= 0.20 and pas >= 0.8 * p_tw
                p0 = (k0 + 0.5) / (n0 + 1)
                pv = float(binomtest(k, n, p0, alternative="greater").pvalue)
                alpha = 2.0 if a.endswith("_a2.0") else 1.0
                land = Counter(r["label"] for r in rs if r["label"] not in (DEFAULT[t], "invalid"))
                tres["directions"][a] = {"alpha": alpha, "n": n, "off_default": k, "off_default_share": k / n,
                                         "excess": exc, "excess_invalid_counts": ki / n - k0i / n0, "pass": pas,
                                         "escape": bool(esc), "confirmed": bool(esc and pv < 0.05), "binom_p": pv,
                                         "landing": dict(land.most_common()),
                                         "composition_all": dict(Counter(r["label"] for r in rs).most_common()),
                                         "correct_comp": dict(Counter(r["label"] for r in rs if r["passed"]
                                                                      and r["label"] != "invalid").most_common())}
        for al in (1.0, 2.0):
            ds = [d for d in tres["directions"].values() if d["alpha"] == al]
            tres[f"E_alpha{al:g}"] = {"n_escape": sum(d["escape"] for d in ds), "n_confirmed":
                                      sum(d["confirmed"] for d in ds), "n_run": len(ds)}
        land: Counter = Counter()
        for d in tres["directions"].values():
            if d["confirmed"]:
                tot = sum(d["landing"].values())
                for lab, c in d["landing"].items():
                    land[lab] += d["excess"] * c / max(tot, 1)
        tres["push_landing_weighted"] = {k: round(v, 4) for k, v in land.most_common()}
        res["tasks"][t] = tres
    recon = []
    for t, q in QUOTED.items():
        tr = res["tasks"].get(t, {})
        recon.append({"task": t, "quoted": q,
                      "recomputed": {f"alpha{al}": f"{tr.get(f'E_alpha{al}', {}).get('n_escape')}/"
                                                  f"{tr.get(f'E_alpha{al}', {}).get('n_run')}" for al in ("1", "2")}})
    res["reconciliation"] = recon
    write_json(RESULTS_DIR / "screen.json", res)
    h = sha256_file(RESULTS_DIR / "screen.json")
    (RESULTS_DIR / "screen.json.sha256").write_text(h + "\n")
    for r in recon:
        logger.info(f"screen reconciliation {r['task']}: quoted {r['quoted']} | recomputed {r['recomputed']}")
    return res


# ------------------------------------------------------------------------------------------------ reused rows
EXP13_MAP = {"twin": "REUSED_TWIN", "oneshot": "VETO_1SHOT", "persistent": "VETO_PERSIST", "iter1": "VETO_ITER1",
             "iter2": "VETO_ITER2", "iter3": "VETO_ITER3"}
EXP16_MAP = {"b": "REUSED_TWIN", "V1": "VETO_1SHOT", "VP": "VETO_PERSIST", "R2": "VETO_ITER2", "R3": "VETO_ITER3"}


def build_reused() -> dict[str, Any]:
    rows13 = read_jsonl(E13 / "data" / "samples.jsonl")
    conds = sorted(Counter(r["condition"] for r in rows13).items())
    out = []
    for r in rows13:
        arm = EXP13_MAP.get(r["condition"])
        if arm is None:
            continue
        out.append({"task": r["task"], "arm": arm, "source_condition": r["condition"], "template": r["template"],
                    "slot": r["sample_id"], "sample_id": f"exp13|{r['sample_id']}", "label": r["label"],
                    "passed": str(r["passed"]) == "True" or r["passed"] is True, "code": r.get("code"),
                    "code_sha256": r.get("code_sha256"), "engine": "vllm_bf16_iter3", "source": "exp13"})
    n16 = 0
    p16 = E16 / "data" / "path_screen_rows.jsonl"
    if p16.exists():
        for r in read_jsonl(p16):
            t = {"t1": "T1", "t2": "T2"}[r["task"]]
            arms = [EXP16_MAP[r["arm"]]] if r["arm"] in EXP16_MAP else []
            if r["arm"] == "V1":
                arms.append("VETO_ITER1")  # round 1 of the iterated dial is the one-shot V1 round
            for arm in arms:
                out.append({"task": t, "arm": arm, "source_condition": r["arm"], "template": r.get("w"),
                            "slot": r.get("k"), "sample_id": f"exp16|{r['uid']}|{arm}", "label": r["label"],
                            "passed": bool(r["passed"]), "code": r.get("code"), "code_sha256": r.get("code_sha256"),
                            "engine": "hf_iter3", "source": "exp16"})
                n16 += 1
    write_jsonl(DATA_DIR / "reused_rows.jsonl", out)
    m = {"exp13_conditions": dict(conds), "exp13_map": EXP13_MAP, "excluded": ["sham (control, not a knob)", "ban",
         "nonce/novelty (re-run here)", "rand1-3/hf_twin/bandpatch (screen, not knob rows)"],
         "exp16_map": EXP16_MAP, "exp16_note": "path screen: V1 one-shot (also round 1 of VETO_ITER), VP persistent, "
         "R2/R3 iterated rounds 2-3; reference 'b' (exp16 twin) exists for T2 only (20 rows); for T1 the veto "
         "classes are priced against this artifact's TWIN (flagged engine mismatch)", "n_rows": len(out),
         "n_exp16_rows": n16, "utc": utc_now()}
    write_json(RESULTS_DIR / "reused_map.json", m)
    logger.info(f"reused rows: {len(out)} ({n16} from exp16)")
    return m


def extract_exp16_path_rows(src_file) -> int:
    """Copy only the T1/T2 veto rows (+ T2 twin 'b') of exp16 samples.jsonl into inputs/exp16/data."""
    keep = []
    for r in read_jsonl(src_file):
        if r["task"] in ("t1", "t2") and r["arm"] in ("V1", "VP", "R2", "R3", "b"):
            keep.append({k: r.get(k) for k in ("uid", "task", "arm", "w", "k", "label", "passed", "code",
                                                "code_sha256", "decoding", "prompt_kind")})
    (E16 / "data").mkdir(parents=True, exist_ok=True)
    write_jsonl(E16 / "data" / "path_screen_rows.jsonl", keep)
    return len(keep)


if __name__ == "__main__":
    import sys

    from cfg import ITER3, setup_logging

    setup_logging("screen")
    n = extract_exp16_path_rows(ITER3 / "gen_art_experiment_16" / "data" / "samples.jsonl")
    logger.info(f"exp16 path rows copied: {n}")
    build_screen()
    build_reused()
