#!/usr/bin/env python3
"""Stage 3 (arms, after COMMIT #1) and Stage 4 (HR, after COMMIT #2), registered into gpu8.STAGES as s3 / s4.

Stage 3: every arm shares the unit's 50 CRN slot streams; rows record the full schedule. Identity shortcut (after U2):
in the fork-dosed and class-forcing arms, a slot whose replayed decision token equals the twin's is byte-identical
to the twin, so its row is copied from the twin (copied_from_twin = true; T10: only when the token is not one that
triggers the index-11 dose); every 10th copied slot is regenerated as a running check (arm suffix '_chk').
Stage 4 (HR): at every decision node, tokens ranked 21-64 by the template-averaged T = 1 probability are forced and
continued 5 times at T = 1 with dedicated HR streams; ranks 1-20 reuse the first 5 Stage 2 continuations.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (ADAPT, CONTS, EDT, GLOBAL_ARMS, HR_RANKS, K_HR, MINP, PRED_DIR, SAMPLES, SEED_HR, TEMPLATES,  # noqa
                  TOP_P_GLOBAL, TOPK_DOSE, UNITS, WINDOW_BOUNDARY, append_jsonl, log_deviation, read_json, read_jsonl,
                  slot_template, slot_ukey, u_stream, utc_now)
import gpu8 as G8  # noqa: E402
import predict8 as PR  # noqa: E402
import units8 as U8  # noqa: E402

COMMIT1 = PRED_DIR / "commit1_dose_table.json"
COMMIT2 = PRED_DIR / "commit2_hr.json"
FLAGS = PRED_DIR / "stage3_flags.json"


def _spec(unit: str, s: int, arm: str, **kw: Any) -> dict[str, Any]:
    return G8.twin_spec(unit, s, arm=arm, stage="S3", **kw)


def arm_specs(unit: str, e: dict[str, Any], c1: dict[str, Any], arms: list[str]) -> list[dict[str, Any]]:
    """Generated specs of the full (non-copied) arms of one unit."""
    out = []
    for s in range(50):
        for a in arms:
            if a in GLOBAL_ARMS:
                out.append(_spec(unit, s, a, T=GLOBAL_ARMS[a], top_p=TOP_P_GLOBAL))
            elif a == "A4":
                out.append(_spec(unit, s, a, T=MINP["T"], min_p=MINP["min_p"]))
            elif a == "A5":
                out.append(_spec(unit, s, a, edt={"q": e["q90"], "T": EDT["T_hi"]}))
            elif a == "A6":
                out.append(_spec(unit, s, a, adapt={"T": ADAPT["T_hi"]}))
            elif a == "A7":
                j = e["jstar"].get(str(s), e["jstar"].get(s))
                if j is not None:
                    out.append(_spec(unit, s, a, fixed_pos={"pos": [int(j)], "T": e["dose"]["d2"], "k": TOPK_DOSE}))
            elif a == "A8":
                rp = e["rpos"].get(str(s), e["rpos"].get(s))
                out.append(_spec(unit, s, a, fixed_pos={"pos": [int(x) for x in rp], "T": e["dose"]["d2"],
                                                        "k": TOPK_DOSE}))
            elif a == "B1":
                out.append(_spec(unit, s, a, window={"n": WINDOW_BOUNDARY, "T": c1["boundary_window_T"],
                                                     "k": TOPK_DOSE}))
    return out


def fork_specs(unit: str, e: dict[str, Any], twin: dict[int, dict[str, Any]], arm: str, use_copy: bool
               ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(generated specs, copied rows) for A9/A10/A11."""
    gen, copies = [], []
    n_copied = 0
    second_tokens = set()
    if unit == "T10":
        second_tokens = {int(t) for t in e.get("second_dose_tokens", [])}
    for s in range(50):
        r = twin.get(s)
        if r is None:
            continue
        kw: dict[str, Any] = {}
        if arm in ("A9", "A10"):
            T = e["dose"]["d1" if arm == "A9" else "d2"]
            kw["dose"] = {"T": T, "k": TOPK_DOSE}
            if unit == "T10" and second_tokens:
                kw["dose2"] = {"tokens": second_tokens, "T": T, "k": TOPK_DOSE}
            pred_tok = None
            if r.get("reached_decision"):
                u = u_stream(*slot_ukey(unit, s))
                pred_tok = PR.replay_token(r["dec_top_ids"], r["dec_top_z"], float(u[r["decision_pos"]]), T,
                                           TOPK_DOSE)
            same = (not r.get("reached_decision")) or (pred_tok == r["decision_token"] and
                                                       pred_tok not in second_tokens)
        else:  # A11
            cs = e["arms"]["A11"]["class_draws"].get(str(s), e["arms"]["A11"]["class_draws"].get(s))
            fd = {}
            if cs is not None:
                for ni, toks in e["arms"]["A11"]["tokens_by_node"].items():
                    if cs in toks:
                        fd[int(ni)] = toks[cs]
            kw["force_dec"] = fd
            node = r.get("decision_node", -1)
            forced = fd.get(node) if node is not None and node >= 0 else None
            same = (not r.get("reached_decision")) or (not forced) or (len(forced) == 1 and
                                                                        forced[0] == r["decision_token"])
        if use_copy and same:
            n_copied += 1
            if n_copied % 10 == 0:
                gen.append(_spec(unit, s, arm + "_chk", **kw))
            row = {k: v for k, v in r.items() if k not in ("label", "cls", "passed")}
            row.update({"sid": f"{unit}|{arm}|{s}", "arm": arm, "stage": "S3", "copied_from_twin": True,
                        "schedule": {k: (sorted(v["tokens"]) and {**v, "tokens": sorted(int(t) for t in v["tokens"])}
                                         if k == "dose2" else v) for k, v in kw.items()},
                        "utc": utc_now(), "copied_from_sid": r["sid"]})
            copies.append(row)
        else:
            gen.append(_spec(unit, s, arm, **kw))
    return gen, copies


def stage3_arms(R: Any, units: list[str]) -> None:
    assert COMMIT1.exists(), "COMMIT #1 must precede any Stage 3 sample"
    c1 = read_json(COMMIT1)
    flags = read_json(FLAGS) if FLAGS.exists() else {"identity_shortcut": False, "arms": {}}
    use_copy = bool(flags.get("identity_shortcut"))
    have = {r["sid"] for r in read_jsonl(SAMPLES)}
    for unit in units:
        if UNITS[unit]["model"] != R.flavor:
            continue
        e = c1["units"].get(unit)
        role = (e or {}).get("role", UNITS[unit]["role"] if unit not in c1.get("roles", {}) else c1["roles"][unit])
        twin = {r["slot"]: r for r in read_jsonl(SAMPLES) if r["unit"] == unit and r["arm"] == "A0"}
        t0 = time.time()
        if role == "boundary" or unit in ("T2", "T03"):
            specs = arm_specs(unit, e or {}, c1, ["B1"])
            R.run(specs, f"S3_{unit}_B1")
            R.clear()
            continue
        arms_full = flags.get("arms", {}).get(unit) or ["A1", "A2", "A3g", "A4", "A5", "A6", "A7", "A8"]
        fork_arms = flags.get("fork_arms", {}).get(unit) or ["A10", "A9", "A11"]
        # each arm runs alone, in batches shaped like the twin's (same rows, same order, same batch size), so a slot
        # whose decision token is unchanged sees the same kernel shapes as its twin
        twin_B = max(set(r.get("batch_B", 50) for r in twin.values()),
                     key=lambda b: sum(1 for r in twin.values() if r.get("batch_B") == b))
        twin_B = min(twin_B, UNITS[unit]["batch"]) if twin_B > 1 else UNITS[unit]["batch"]
        order = [a for a in ("A10", "A9", "A11", "A1", "A3g", "A5", "A7", "A8", "A6", "A2", "A4")
                 if a in fork_arms or a in arms_full]
        if R.flavor == "gemma":          # one prompt per batch: all arms of a template share batches (exp38 design)
            specs = []
            for a in order:
                if a in ("A9", "A10", "A11"):
                    gen, _ = fork_specs(unit, e, twin, a, False)
                    specs += gen
                else:
                    specs += arm_specs(unit, e, c1, [a])
            R.run(specs, f"S3_{unit}", batch=40, per_template=True)
            G8.logger.info(f"S3 {unit} done in {time.time() - t0:.0f}s")
            R.clear()
            continue
        for a in order:
            if a in ("A9", "A10", "A11"):
                gen, copies = fork_specs(unit, e, twin, a, use_copy)
                new_copies = [c for c in copies if c["sid"] not in have]
                if new_copies:
                    append_jsonl(SAMPLES, new_copies)
                specs = gen
            else:
                specs = arm_specs(unit, e, c1, [a])
            ta = time.time()
            R.run(specs, f"S3_{unit}_{a}", batch=twin_B, per_template=(R.flavor == "gemma"))
            G8.logger.info(f"S3 {unit}/{a}: {len(specs)} rows in {time.time() - ta:.0f}s")
        G8.logger.info(f"S3 {unit} done in {time.time() - t0:.0f}s")
        R.clear()


# ------------------------------------------------------------------------------------------------ stage 4 HR
def hr_tokens(info: dict[str, Any]) -> list[tuple[int, int]]:
    """(rank, token) for ranks 1-64 by the template-averaged T = 1 probability over the saved top-64 logits."""
    pooled: dict[int, float] = {}
    for w in TEMPLATES:
        ids = info["tf"][w]["top_ids"]
        z = np.array(info["tf"][w]["top_z"], dtype=float)
        p = np.exp(z - z.max())
        p /= p.sum()          # normalised over the top-64 (the mass outside is < 1e-3 at every node)
        for t, pp in zip(ids, p):
            pooled[int(t)] = pooled.get(int(t), 0.0) + pp / len(TEMPLATES)
    order = sorted(pooled, key=lambda t: -pooled[t])[:HR_RANKS]
    return [(i + 1, t) for i, t in enumerate(order)]


def stage4_hr(R: Any, units: list[str]) -> None:
    assert COMMIT2.exists(), "COMMIT #2 must precede HR's new branches"
    order = [("T10", "n10"), ("T10", "n11"), ("B3", "c0"), ("B3", "c1"), ("G", "cstar"), ("A3", "c0"), ("A3", "c1"),
             ("B6", "c0"), ("T1", "n3")]
    for ni, (unit, node) in enumerate(order):
        if unit not in units or UNITS[unit]["model"] != R.flavor:
            continue
        info = read_json(G8.CACHE_DIR / "nodes" / f"{unit}_{node}.json")
        mapped = {int(t) for t in info["map_tokens"]}
        specs = []
        for rank, t in hr_tokens(info):
            if t in mapped:
                continue
            for k in range(K_HR):
                specs.append({"sid": f"HR|{unit}|{node}|{t}|{k}", "unit": unit, "arm": "HR", "stage": "S4",
                              "slot": None, "w": TEMPLATES[k % 5], "node": node, "token": int(t), "rank": rank, "k": k,
                              "ukey": ("iter8hr", SEED_HR + ni * 1000 + rank * 10 + k),
                              "max_new": UNITS[unit]["max_new"], "T": 1.0, "prefix": info["opening"] + [int(t)]})
        t0 = time.time()
        R.run(specs, f"S4_hr_{unit}_{node}", out=CONTS, light=True)
        G8.logger.info(f"HR {unit}/{node}: {len(specs)} continuations in {time.time() - t0:.0f}s")
        R.clear()


STAGES: dict[str, Callable] = {"s3": stage3_arms, "s4": stage4_hr}


def stage3_amendment(R: Any, units: list[str]) -> None:
    """A9f / A10f (COMMIT #3): fork dose with the committed high-Pfail tokens removed at the dosed step(s)."""
    c3p = PRED_DIR / "commit3_amendment.json"
    assert c3p.exists(), "COMMIT #3 must precede the amendment samples"
    c3 = read_json(c3p)
    for unit in units:
        if UNITS[unit]["model"] != R.flavor or unit not in c3["units"]:
            continue
        e = c3["units"][unit]
        twin = {r["slot"]: r for r in read_jsonl(SAMPLES) if r["unit"] == unit and r["arm"] == "A0"}
        specs = []
        for a in ("A10f", "A9f"):
            T = e["arms"][a]["T"]
            for s in range(50):
                if s not in twin:
                    continue
                ban = []
                for nd in U8.nodes(unit):
                    ban += e["bans"].get(f"{unit}:{nd['id']}", [])
                kw = {"dose": {"T": T, "k": TOPK_DOSE, "ban": sorted(set(ban))}}
                if unit == "T10":
                    kw["dose2"] = {"tokens": {U8.T10_DEF}, "T": T, "k": TOPK_DOSE,
                                   "ban": e["bans"].get("T10:n11", [])}
                specs.append(_spec(unit, s, a, **kw))
        if R.flavor == "gemma":
            R.run(specs, f"S3x_{unit}", batch=40, per_template=True)
        else:
            for a in ("A10f", "A9f"):
                R.run([x for x in specs if x["arm"] == a], f"S3x_{unit}_{a}", batch=40)
        R.clear()


STAGES["s3x"] = stage3_amendment
