#!/usr/bin/env python3
"""vLLM request builder and ingester (HF venv side; CPU only).

Slots are per template (W1-W5), as in exp26:
  TWIN   instruct, twin prompt, T 1.0, k 0-39 (k 0-9 = HF CRN slots = the iteration-5 twin; k 10-39 vLLM)
  T13    instruct, twin prompt, T 1.3, k 0-19 (vLLM)
  FORCED_<mode>  instruct, 'Implement {display name} for this task.' (exp11 bench templates 0-4 as F0-F4), k per
         template; programs verified by the label worker (tests + label == mode) feed q_lik
  ASSOC6 instruct, association prompt naming the default (vLLM, 64 tokens); ASSOCALL_<mode> before the default is
         known (plan C3)
  BASE   base, twin prompt (identical ids), k 0-39 (k 0-5 = PILOT); BASEX = engine-check extra chat draws k 40-49
  PLAIN  base, plain completion, k 0-99 (exp26 plain template)
  BINTI  base, intent sentence after the IFG frame (exp27), k per template
build(): writes data/vllm_req/<job>.jsonl; ingest(): converts data/vllm_out/<job>.jsonl into data/samples_raw.jsonl
rows (engine 'vllm') with the HF row schema so that the label worker treats both engines alike.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg5 import (ASSOC6_TEMPLATE, BASE_ID, BASE_REVISION, DATA_DIR, FORCED_TEMPLATES, MODEL_ID, MODEL_REVISION,  # noqa: E402
                  RAW, TEMPLATE_IDS, append_jsonl, cap_first, read_jsonl, setup_logging, sha256_text, utc_now,
                  vllm_seed, write_jsonl)

REQ_DIR = DATA_DIR / "vllm_req"
OUT_DIR = DATA_DIR / "vllm_out"
REQ_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
IFG_INSTR = ("Before writing any code, state in one sentence the algorithm you will use, on a single line that "
             "starts with Intent:. Then write the code.")   # exp27 cfg5.IFG_INSTR (verbatim)
INTENT_PREFIX = "Intent:"
_TOK: dict[str, Any] = {}


def tok():
    if "t" not in _TOK:
        from transformers import AutoTokenizer
        from cfg5 import model_path
        _TOK["t"] = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
    return _TOK["t"]


def chat_ids(user_text: str) -> list[int]:
    ids = tok().apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                    add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def prompt_table() -> dict[str, dict[str, Any]]:
    from prompts5 import load_prompts
    return load_prompts()


def forced_prompt_rows(u: str) -> list[dict[str, Any]]:
    """Forced 'Implement X' prompts for every catalogue mode (exp11 bench templates 0-4)."""
    from units_spec import UNITS, spec_text
    from labels_view import frozen_catalogue
    spec = spec_text(u)
    rows = []
    for m in frozen_catalogue(u):
        dn = UNITS[u]["modes"][m][0] if m in UNITS[u]["modes"] else m.replace("_", " ")
        for j, tpl in enumerate(FORCED_TEMPLATES):
            text = cap_first(tpl.format(j=dn)) + "\n\n" + spec
            ids = chat_ids(text)
            rows.append({"pid": f"{u}|forced|{m}|F{j}", "unit": u, "kind": "forced", "X": m, "template_id": f"F{j}",
                         "user_text": text, "ids": ids, "P": len(ids), "prompt_sha256": sha256_text(json.dumps(ids))})
    return rows


def assoc6_rows(u: str, modes: list[str]) -> list[dict[str, Any]]:
    from units_spec import UNITS
    desc = cap_first(UNITS[u]["description"])
    out = []
    for m in modes:
        q = ASSOC6_TEMPLATE.format(x=UNITS[u]["modes"][m][0])
        text = desc + "\n\n" + cap_first(q)
        ids = chat_ids(text)
        out.append({"pid": f"{u}|assoc6|{m}|-", "unit": u, "kind": "assoc6", "X": m, "template_id": "ASSOC6",
                    "user_text": text, "ids": ids, "P": len(ids), "prompt_sha256": sha256_text(json.dumps(ids))})
    return out


def ifg_rows(u: str, pr: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """BINT frame (exp27 'ifg' kind): twin W-sentence + ' ' + IFG_INSTR + blank line + spec; forced prefix
    'Intent:' appended to the prompt ids."""
    from units_spec import spec_text
    spec = spec_text(u)
    out = []
    for w in TEMPLATE_IDS:
        tw = pr[f"{u}|twin|-|{w}"]
        text = tw["segment"] + " " + IFG_INSTR + "\n\n" + spec
        ids = chat_ids(text)
        f = tok()(INTENT_PREFIX, add_special_tokens=False)["input_ids"]
        out.append({"pid": f"{u}|ifg|-|{w}", "unit": u, "kind": "ifg", "X": None, "template_id": w,
                    "user_text": text, "ids": ids, "forced_ids": f, "P": len(ids),
                    "prompt_sha256": sha256_text(json.dumps(ids))})
    return out


def save_extra_prompts(rows: list[dict[str, Any]]) -> None:
    p = DATA_DIR / "prompts_extra.jsonl"
    have = {r["pid"] for r in read_jsonl(p)}
    new = [r for r in rows if r["pid"] not in have]
    if new:
        append_jsonl(p, new)


def req(rid: str, ids: list[int], T: float, max_tokens: int, fence: str | None, seed_parts: tuple) -> dict:
    return {"rid": rid, "prompt_token_ids": ids, "temperature": T, "max_tokens": max_tokens, "fence": fence,
            "seed": vllm_seed(*seed_parts)}


def rid_of(u: str, w: str, arm: str, k: int, model_tag: str) -> str:
    return f"{u}|{w}|{arm}|{k}|{model_tag}"


def build_instruct(u: str, arms: list[str], pr: dict[str, dict[str, Any]], forced_k: list[int] | None = None,
                   forced_modes: list[str] | None = None, assoc_modes: list[str] | None = None,
                   twin_k: list[int] | None = None, t13_k: list[int] | None = None) -> list[dict]:
    out = []
    if "TWIN" in arms:
        for w in TEMPLATE_IDS:
            ids = pr[f"{u}|twin|-|{w}"]["ids"]
            for k in (twin_k or range(10, 40)):
                out.append(req(rid_of(u, w, "TWIN", k, "instruct"), ids, 1.0, 1024, "bench", (u, w, "TWIN", k)))
    if "T13" in arms:
        for w in TEMPLATE_IDS:
            ids = pr[f"{u}|twin|-|{w}"]["ids"]
            for k in (t13_k or range(0, 20)):
                out.append(req(rid_of(u, w, "T13", k, "instruct"), ids, 1.3, 1024, "bench", (u, w, "T13", k)))
    if "FORCED" in arms:
        fr = forced_prompt_rows(u)
        save_extra_prompts(fr)
        for r in fr:
            if forced_modes is not None and r["X"] not in forced_modes:
                continue
            for k in (forced_k or range(0, 4)):
                arm = f"FORCED_{r['X']}"
                out.append(req(rid_of(u, r["template_id"], arm, k, "instruct"), r["ids"], 1.0, 1024, "bench",
                               (u, r["template_id"], arm, k)))
    if "ASSOC6" in arms:
        ar = assoc6_rows(u, assoc_modes or [])
        save_extra_prompts(ar)
        for r in ar:
            arm = f"ASSOC6_{r['X']}"
            for k in range(20):
                out.append(req(rid_of(u, "ASSOC6", arm, k, "instruct"), r["ids"], 1.0, 64, None, (u, arm, k)))
    return out


def build_base(u: str, arms: list[str], pr: dict[str, dict[str, Any]], chat_k: list[int] | None = None,
               plain_k: list[int] | None = None, bint_k: list[int] | None = None) -> list[dict]:
    out = []
    if "BASE" in arms:
        for w in TEMPLATE_IDS:
            ids = pr[f"{u}|twin|-|{w}"]["ids"]
            for k in (chat_k or range(0, 40)):
                arm = "BASE" if k < 40 else "BASEX"
                out.append(req(rid_of(u, w, arm, k, "base"), ids, 1.0, 1024, "bench", (u, w, arm, k, "base")))
    if "PLAIN" in arms:
        p = pr[f"{u}|plain|-|PLAIN"]
        for k in (plain_k or range(0, 100)):
            out.append(req(rid_of(u, "PLAIN", "PLAIN", k, "base"), p["ids"], 1.0, 768, "plain",
                           (u, "PLAIN", k, "base")))
    if "BINTI" in arms:
        rows = ifg_rows(u, pr)
        save_extra_prompts(rows)
        for r in rows:
            for k in (bint_k or range(0, 6)):
                out.append(req(rid_of(u, r["template_id"], "BINTI", k, "base"), r["ids"] + r["forced_ids"], 1.3, 64,
                               None, (u, r["template_id"], "BINTI", k, "base")))
    return out


def intent_ids_of(row: dict) -> tuple[list[int], str, bool]:
    """Base intent: generated ids up to and including the first newline (exp27); EOS-terminated or newline-free
    intents get a newline appended. Returns (ids, text, valid) with exp27's intent_valid rule."""
    t = tok()
    ids = []
    for x in row["token_ids"]:
        ids.append(int(x))
        if "\n" in t.decode([int(x)]):
            break
    txt = t.decode(ids, skip_special_tokens=True)
    if "\n" not in txt:
        ids = ids + t("\n", add_special_tokens=False)["input_ids"]
    line = txt.split("\n", 1)[0].strip()
    valid = bool(line) and "```" not in line and len(line.split()) <= 40
    return ids, line, valid


def build_bint_code(u: str, pr: dict[str, dict[str, Any]]) -> list[dict]:
    """BINT code stage (unhooked, vLLM): ifg prompt + 'Intent:' + the committed base intent of the same (w, k)."""
    rows = [r for r in read_jsonl(RAW) if r["unit"] == u and r["arm"] == "BINTI"]
    ifg = {r["pid"]: r for r in read_jsonl(DATA_DIR / "prompts_extra.jsonl") if r["unit"] == u and r["kind"] == "ifg"}
    out = []
    meta = []
    for r in sorted(rows, key=lambda r: (r["template"], r["slot"])):
        p = ifg[f"{u}|ifg|-|{r['template']}"]
        ids, line, valid = intent_ids_of(r)
        out.append(req(rid_of(u, r["template"], "BINT", r["slot"], "instruct"), p["ids"] + p["forced_ids"] + ids,
                       1.0, 1024, "bench", (u, r["template"], "BINT", r["slot"])))
        meta.append({"unit": u, "template": r["template"], "slot": r["slot"], "intent": line, "valid": valid,
                     "n_intent_tokens": len(ids)})
    append_jsonl(DATA_DIR / "base_intents.jsonl", meta)
    return out


def write_job(job: str, rows: list[dict]) -> Path:
    p = REQ_DIR / f"{job}.jsonl"
    write_jsonl(p, rows)
    logger.info(f"job {job}: {len(rows)} requests -> {p.name}")
    return p


def ingest(job: str, model_tag: str) -> int:
    """data/vllm_out/<job>.jsonl -> data/samples_raw.jsonl rows (skips rids already ingested)."""
    outp = OUT_DIR / f"{job}.jsonl"
    reqs = {r["rid"]: r for r in read_jsonl(REQ_DIR / f"{job}.jsonl")}
    have = {f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}" for r in read_jsonl(RAW)}
    pr = prompt_table()
    pr.update({r["pid"]: r for r in read_jsonl(DATA_DIR / "prompts_extra.jsonl")})
    rows = []
    for o in read_jsonl(outp):
        if o["rid"] in have:
            continue
        u, w, arm, k, mt = o["rid"].split("|")
        rq = reqs.get(o["rid"], {})
        fam = arm.split("_")[0] if arm.startswith(("FORCED_", "ASSOC6_", "ASSOCALL_")) else arm
        if arm.startswith("FORCED_"):
            pid = f"{u}|forced|{arm[7:]}|{w}"
        elif arm.startswith("ASSOC6_"):
            pid = f"{u}|assoc6|{arm[7:]}|-"
        elif arm in ("PLAIN",):
            pid = f"{u}|plain|-|PLAIN"
        elif arm in ("BINTI", "BINT"):
            pid = f"{u}|ifg|-|{w}"
        else:
            pid = f"{u}|twin|-|{w}"
        p = pr.get(pid, {})
        rows.append({"unit": u, "arm": arm, "template": w, "slot": int(k), "model_tag": mt,
                     "model": MODEL_ID if mt == "instruct" else BASE_ID,
                     "model_revision": MODEL_REVISION if mt == "instruct" else BASE_REVISION,
                     "precision": "bf16_vllm", "engine": "vllm", "vllm_version": o.get("vllm_version"),
                     "decoding": f"T{rq.get('temperature')}_topp1.0_topk-off_max{rq.get('max_tokens')}_thinkoff_"
                                 f"{'fencestop' if rq.get('fence') else 'nofence'}",
                     "temperature": rq.get("temperature"), "top_k": None, "thinking": False, "site": None,
                     "family": fam, "alpha": None, "direction_seed": None, "stage": f"vllm:{job}",
                     "prompt_pid": pid, "prompt_sha256": p.get("prompt_sha256"), "rel_err_max": None,
                     "text": o["text"], "token_ids": o["token_ids"], "n_tokens": o["n_tokens"],
                     "finish_reason": o["finish_reason"], "fence_step": None, "logprob_sum": None,
                     "utc": o["utc"], "engine_check": False, "vllm_seed": o.get("seed")})
    if rows:
        append_jsonl(RAW, rows)
    logger.info(f"ingested {len(rows)} rows of {job}")
    return len(rows)


if __name__ == "__main__":
    setup_logging("requests6")
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["ingest"])
    ap.add_argument("job")
    ap.add_argument("--model-tag", default="instruct")
    a = ap.parse_args()
    ingest(a.job, a.model_tag)
