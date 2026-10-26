#!/usr/bin/env python3
"""Modal modes, hash-committed forecasts (PREDICT row) and the succession plan.

  modal       : X_t from the vLLM baseline (modal correct label if it leads the runner-up by >= 15 points)
  commit-ban  : forecast/predict_<t>_ban1.json over S = catalogue - {X_t}, sha256 appended to commit_log.jsonl
  commit-succ : realised mode of step 1 -> X2_t, forecast/predict_<t>_succ2.json over catalogue - {X_t, X2_t}
  verify      : re-verify every stored sha256

Forecast mix and floor (shared): q(s) = 0.98 * (0.95 * p(s) + 0.05 / |S|), q(other) = 0.02.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CATALOGUE, FORECAST_DIR, LABEL_CACHE, MODEL_ID, RAW_DIR, RESULTS_DIR, TASKS, append_jsonl, read_jsonl, setup_logger, sha256_text  # noqa: E402
from loguru import logger  # noqa: E402


def labelled(task: str, raw_name: str) -> list[dict]:
    out = []
    for r in read_jsonl(RAW_DIR / raw_name):
        f = LABEL_CACHE / task / f"{sha256_text(r['text'])}.json"
        if f.exists():
            lab = json.loads(f.read_text())
            out.append({**r, **{k: lab.get(k) for k in ("label", "passed", "format_ok", "label_runtime", "label_ast")}})
    return out


def modal(rows: list[dict], exclude: set[str] | None = None) -> dict:
    exclude = exclude or set()
    c = Counter(r["label"] for r in rows if r["passed"] and r["label"] not in exclude)
    n = sum(c.values())
    if n == 0:
        return {"X": None, "flag": "no_correct_samples", "counts": {}}
    top = c.most_common(2)
    lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / n * 100
    return {"X": top[0][0], "lead_points": lead, "flag": None if lead >= 15 else "no_clear_mode", "counts": dict(c),
            "n_correct": n}


def mix(p: dict, S: list[str]) -> dict:
    q = {s: 0.98 * (0.95 * p.get(s, 0.0) + 0.05 / len(S)) for s in S}
    q["other"] = 0.02
    return q


def freq_forecast(rows: list[dict], S: list[str]) -> dict:
    c = Counter(r["label"] for r in rows if r["passed"] and r["label"] in S)
    tot = sum(c.values()) + 0.5 * len(S)
    return mix({s: (c.get(s, 0) + 0.5) / tot for s in S}, S)


def dc_forecast(rows: list[dict], S: list[str]) -> tuple[dict, str | None]:
    c = Counter(r["label"] for r in rows if r["passed"] and r["label"] in S)
    tot = sum(c.values())
    if tot == 0:
        return mix({s: 1 / len(S) for s in S}, S), "degenerate"
    return mix({s: c.get(s, 0) / tot for s in S}, S), None


def sha_of(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def commit(obj: dict, fname: str) -> dict:
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    (FORECAST_DIR / fname).write_text(json.dumps(obj, sort_keys=True, separators=(",", ":")))
    sha = sha_of(obj)
    rec = {"file": fname, "sha256": sha, "created_utc": obj["created_utc"], "event": obj["event"]}
    append_jsonl(FORECAST_DIR / "commit_log.jsonl", [rec])
    logger.info(f"COMMITTED {fname} sha256={sha}")
    return rec


def steer_rows(task: str, layer: int, c: float, direction: str = "dc") -> list[dict]:
    return labelled(task, f"hf_{task}_steer-{direction}-c{c:g}-L{layer}.jsonl")


def cmd_modal() -> None:
    out = {}
    for t in TASKS:
        m = modal(labelled(t, f"vllm_{t}_baseline.jsonl"))
        out[t] = m
        logger.info(f"{t}: modal X = {m['X']} (lead {m.get('lead_points', 0):.1f} pts, flag={m['flag']})")
    (RESULTS_DIR / "modal_modes.json").write_text(json.dumps(out, indent=1))


def forecasts_for(task: str, S: list[str], cst: dict, layer: int) -> tuple[dict, dict]:
    cstar = cst[task]["c_star"]
    fc, flags = {}, {}
    fc["dc"], flags["dc"] = dc_forecast(steer_rows(task, layer, cstar), S)
    fc["freq_vllm"] = freq_forecast(labelled(task, f"vllm_{task}_baseline.jsonl"), S)
    fc["freq_hf"] = freq_forecast(steer_rows(task, layer, 0.0), S)
    fc["uniform"] = mix({s: 1 / len(S) for s in S}, S)
    for c in sorted(float(k) for k in cst[task]["pass_rates"]):
        if c in (0.0, cstar):
            continue
        rows = steer_rows(task, layer, c)
        if rows:
            fc[f"dc_c={c:g}"], flags[f"dc_c={c:g}"] = dc_forecast(rows, S)
    return fc, flags


def cmd_commit_ban() -> None:
    modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text())
    cst = json.loads((RESULTS_DIR / "cstar.json").read_text())
    layer = int(cst["layer"])
    for t in TASKS:
        X = modes[t]["X"]
        S = [m for m in CATALOGUE[t] if m != X]
        assert not list(RAW_DIR.glob(f"vllm_{t}_ban-*.jsonl")), "ban samples already exist: refusing to commit late"
        fc, flags = forecasts_for(t, S, cst, layer)
        obj = {"event": f"{t}_ban1", "task": t, "banned": [X], "survivors": S, "forecasts": fc, "flags": flags,
               "c_star": cst[t]["c_star"], "c_star_flag": cst[t].get("flag"), "layer": layer, "model": MODEL_ID,
               "mode_flag": modes[t]["flag"], "created_utc": datetime.now(timezone.utc).isoformat()}
        commit(obj, f"predict_{t}_ban1.json")


def compliant_mode(task: str, X: str) -> dict:
    rows = labelled(task, f"vllm_{task}_ban-{X}.jsonl")
    comp = [r for r in rows if r["passed"] and r["label"] != X]
    c = Counter(r["label"] for r in comp)
    n = sum(c.values())
    if n == 0:
        return {"realised": "no clear mode", "counts": {}, "n_compliant": 0}
    top = c.most_common(2)
    lead = (top[0][1] - (top[1][1] if len(top) > 1 else 0)) / n * 100
    return {"realised": top[0][0] if lead >= 15 else "no clear mode", "lead_points": lead, "counts": dict(c),
            "n_compliant": n}


def cmd_commit_succ() -> None:
    modes = json.loads((RESULTS_DIR / "modal_modes.json").read_text())
    cst = json.loads((RESULTS_DIR / "cstar.json").read_text())
    layer = int(cst["layer"])
    plan = {}
    for t in TASKS:
        X = modes[t]["X"]
        rm = compliant_mode(t, X)
        X2 = rm["realised"]
        if X2 in ("no clear mode", "other", "no_code") or X2 not in CATALOGUE[t]:
            plan[t] = {"skip": True, "reason": f"realised mode of step 1 = {X2}", "step1": rm}
            logger.info(f"{t}: succession skipped ({X2})")
            continue
        S2 = [m for m in CATALOGUE[t] if m not in (X, X2)]
        assert not list(RAW_DIR.glob(f"vllm_{t}_succession-2.jsonl")), "succession samples exist: refusing"
        fc, flags = forecasts_for(t, S2, cst, layer)
        obj = {"event": f"{t}_succ2", "task": t, "banned": [X, X2], "survivors": S2, "forecasts": fc, "flags": flags,
               "c_star": cst[t]["c_star"], "layer": layer, "model": MODEL_ID,
               "created_utc": datetime.now(timezone.utc).isoformat()}
        commit(obj, f"predict_{t}_succ2.json")
        plan[t] = {"skip": False, "X1": X, "X2": X2, "step1": rm}
    (RESULTS_DIR / "succession_plan.json").write_text(json.dumps(plan, indent=1))


def cmd_verify() -> dict:
    out = {}
    for rec in read_jsonl(FORECAST_DIR / "commit_log.jsonl"):
        obj = json.loads((FORECAST_DIR / rec["file"]).read_text())
        out[rec["file"]] = {"stored": rec["sha256"], "recomputed": sha_of(obj), "ok": sha_of(obj) == rec["sha256"]}
    (RESULTS_DIR / "forecast_verify.json").write_text(json.dumps(out, indent=1))
    logger.info(f"verify: {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["modal", "commit-ban", "commit-succ", "verify"])
    a = ap.parse_args()
    setup_logger("forecast")
    {"modal": cmd_modal, "commit-ban": cmd_commit_ban, "commit-succ": cmd_commit_succ, "verify": cmd_verify}[a.cmd]()


if __name__ == "__main__":
    main()
