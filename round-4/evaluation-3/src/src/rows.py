"""STEP G2: unified row table (rows.parquet) from the labelled rows of the declared dependencies.

One row per labelled program. Arm names are each artifact's own: exp13 condition (src/analyze.py ARMS), exp17
c2d.json arm keys, exp15 condition, exp16 arm, exp14 arm(+shown Y), exp18 arm/condition/step, exp9 condition,
exp4 condition, exp6 arm + decoding key, exp11 pilots.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from loguru import logger

from src.labels import attempted, default_of, is_catalogue, norm_label, norm_task
from src.paths import BY_EXP, p

FIELDS = ["artifact_id", "src_file", "model", "engine", "precision", "task", "arm", "dial", "template", "sample_id",
          "label", "label_norm", "is_catalogue", "is_default", "attempted", "passed", "code_sha256", "extra"]


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def _b(v: Any) -> bool:
    return v is True or str(v).lower() == "true"


def _row(exp: str, rel: str, r: dict, *, model: str, engine: str, precision: str, task: str, arm: str,
         dial: dict | None = None, template: Any = None, extra: dict | None = None) -> dict:
    task = norm_task(task)
    lab = norm_label(r.get("label"))
    d = default_of(task, model)
    return {"artifact_id": BY_EXP[exp], "src_file": rel, "model": model, "engine": engine, "precision": precision,
            "task": task, "arm": arm, "dial": json.dumps(dial or {}, sort_keys=True),
            "template": str(template if template is not None else r.get("template")),
            "sample_id": str(r.get("sample_id") or r.get("key") or r.get("uid")), "label": str(r.get("label")),
            "label_norm": lab, "is_catalogue": is_catalogue(task, lab), "is_default": bool(d is not None and lab == d),
            "attempted": attempted(lab), "passed": _b(r.get("passed")), "code_sha256": str(r.get("code_sha256") or ""),
            "extra": json.dumps(extra or {}, sort_keys=True)}


QWEN = "Qwen/Qwen3-8B"
LLAMA = "meta-llama/Llama-3.1-8B-Instruct"


def load_exp17() -> list[dict]:
    rel = "data/labels.jsonl"
    out = []
    for r in _jsonl(p("exp17", rel)):
        arm = r["arm"]
        m = re.search(r"_a(\d+(?:\.\d+)?)$", arm)
        dial = {"alpha": float(m.group(1))} if m else {}
        out.append(_row("exp17", rel, r, model=QWEN, engine="hf", precision="fp8", task=r["task"], arm=arm, dial=dial))
    return out


def load_exp13() -> list[dict]:
    rel = "data/samples.jsonl"
    return [_row("exp13", rel, r, model=QWEN, engine=str(r.get("engine", "vllm")), precision="bf16", task=r["task"],
                 arm=r["condition"]) for r in _jsonl(p("exp13", rel))]


def load_exp15() -> list[dict]:
    rel = "data/samples.jsonl"
    ev_type = {}
    for line in p("exp15", "results/c1_events.jsonl").read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            ev_type[(e["task"], e["banned"])] = e["event_type"]
    out = []
    for r in _jsonl(p("exp15", rel)):
        c = str(r["condition"])
        model = LLAMA
        prec, eng = "bf16", "vllm"
        dial: dict = {}
        if c == "pilot_fp8":
            prec = "fp8"
            arm = "pilot_fp8"
        elif c.startswith("forced:"):
            continue  # forced programs are not an arm
        elif c.startswith("ban:"):
            x = c.split(":", 1)[1]
            arm = f"ban_{ev_type.get((r['task'], x), 'unknown')}:{x}"
        elif c.startswith("randdir:"):
            arm = "rand_" + c.split(":", 1)[1]
            eng = "vllm"
        elif c.startswith("veto:"):
            _, kind, rnd = c.split(":")
            arm = f"veto_{kind}"
            dial = {"round": int(rnd.lstrip("r"))}
        else:
            arm = c
        out.append(_row("exp15", rel, r, model=model, engine=eng, precision=prec, task=r["task"], arm=arm, dial=dial,
                        extra={"event_id": r.get("event_id"), "phase": r.get("phase")}))
    return out


def load_exp16() -> list[dict]:
    rel = "data/samples.jsonl"
    out = []
    seen = set()
    for r in _jsonl(p("exp16", rel)):
        if r.get("uid") in seen:
            continue
        seen.add(r.get("uid"))
        out.append(_row("exp16", rel, r, model=QWEN, engine="hf", precision="bf16", task=r["task"], arm=r["arm"],
                        extra={"k": r.get("k"), "stage": r.get("stage")}))
    return out


def load_exp14() -> list[dict]:
    rel = "data/samples.jsonl"
    out = []
    for r in _jsonl(p("exp14", rel)):
        arm = str(r["arm"])
        dial = {"round": int(r["round"])} if arm == "veto" and r.get("round") not in (None, "None") else {}
        y = r.get("Y")
        arm_full = arm if arm in ("baseline",) else f"{arm}:{y}"
        out.append(_row("exp14", rel, r, model=QWEN, engine="vllm", precision="bf16", task=r["task"], arm=arm_full,
                        dial=dial, extra={"Y": y, "arm_kind": arm}))
    return out


def load_exp18() -> list[dict]:
    out = []
    for kind in ("walk", "los", "two_step", "longform", "sham", "fixed_top5"):
        rel = f"data/samples_{kind}.jsonl"
        for r in _jsonl(p("exp18", rel)):
            prec = str(r.get("engine_dtype", "bf16"))
            dial: dict = {}
            if kind == "walk":
                step = int(r["step"])
                arm = "walk_twin" if step == 0 else f"walk_step{step}"
                dial = {"step": step, "round": int(r.get("round") or 0)} if step else {}
            elif kind in ("los", "two_step"):
                arm = str(r["condition"])
            elif kind == "longform":
                arm = f"longform:{r['prompt_id']}"
                dial = {"thinking": _b(r.get("thinking"))}
            else:
                arm = kind
            out.append(_row("exp18", rel, r, model=QWEN, engine="vllm", precision=prec, task=r["task"], arm=arm,
                            dial=dial))
    return out


def load_exp9() -> list[dict]:
    rel = "data/samples.jsonl"
    out = []
    for r in _jsonl(p("exp9", rel)):
        c = str(r["condition"])
        if c.startswith("forced"):
            continue
        out.append(_row("exp9", rel, r, model=QWEN, engine="vllm", precision="bf16", task=r["task"], arm=c))
    return out


def load_exp4() -> list[dict]:
    rel = "data/samples.jsonl"
    out = []
    for r in _jsonl(p("exp4", rel)):
        c = str(r["condition"])
        dial: dict = {}
        arm = c
        m = re.match(r"steer:([a-z0-9]+):c=([\d.]+):L=(\d+)", c)
        if m:
            arm = f"steer:{m.group(1)}"
            dial = {"c": float(m.group(2)), "layer": int(m.group(3))}
        out.append(_row("exp4", rel, r, model=QWEN, engine=str(r.get("engine")), precision="bf16", task=r["task"],
                        arm=arm, dial=dial))
    return out


def load_exp6() -> list[dict]:
    rel = "results/samples.jsonl"
    out = []
    for r in _jsonl(p("exp6", rel)):
        if str(r["condition"]).startswith("forced"):
            continue
        k = r["key"].split("|")
        temp = float(k[5].lstrip("T"))
        sampler = k[6]
        think = k[7] == "think1"
        arm = f"{r['arm']}:{r['condition']}"
        out.append(_row("exp6", rel, r, model=QWEN, engine="vllm", precision="bf16", task=r["task"], arm=arm,
                        dial={"T": temp, "sampler": sampler, "thinking": think}))
    return out


def load_exp11() -> list[dict]:
    out = []
    rel = "data/samples_pilot.jsonl"
    for r in _jsonl(p("exp11", rel)):
        out.append(_row("exp11", rel, r, model=QWEN, engine="vllm", precision="fp8", task=r["task"], arm="pilot_fp8"))
    rel = "data/samples_llama_pilot.jsonl"
    for r in _jsonl(p("exp11", rel)):
        out.append(_row("exp11", rel, r, model=LLAMA, engine="vllm", precision="fp8", task=r["task"],
                        arm="llama_pilot_fp8"))
    return out


LOADERS = {"exp17": load_exp17, "exp13": load_exp13, "exp15": load_exp15, "exp16": load_exp16, "exp14": load_exp14,
           "exp18": load_exp18, "exp9": load_exp9, "exp4": load_exp4, "exp6": load_exp6, "exp11": load_exp11}


def build_rows(out_path: Path) -> pd.DataFrame:
    frames = []
    for name, fn in LOADERS.items():
        try:
            rows = fn()
            logger.info(f"rows: {name} -> {len(rows)}")
            frames.append(pd.DataFrame(rows, columns=FIELDS))
        except FileNotFoundError as e:
            logger.error(f"rows: {name} missing input {e}")
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(out_path, index=False)
    logger.info(f"rows.parquet: {len(df)} rows -> {out_path.name}")
    return df


def load_codes(exp: str, rel: str, key_field: str = "code_sha256") -> dict[str, str]:
    """sha256 -> code text for one dependency file (used only by the 0d audit)."""
    out = {}
    for r in _jsonl(p(exp, rel)):
        h = r.get(key_field)
        if h and r.get("code") and h not in out:
            out[h] = r["code"]
    return out
