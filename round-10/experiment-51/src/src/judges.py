#!/usr/bin/env python3
"""V3 novelty judges over OpenRouter (commit #3 precedes the first call).

Judges deepseek/deepseek-chat-v3.1 and moonshotai/kimi-k2 at temperature 0; mistralai/mistral-medium-3.1 replaces a
judge that fails its gate and breaks disagreements. GATE: >= 9/10 on 10 controls (5 disguised corpus heuristics
expected KNOWN*, 5 executor-written compositions absent from the literature expected NOT_KNOWN). Budget: hard cap
USD 0.6 for this artifact's judges; GET <base>/key before each batch; running usage.cost total; the whole batch stops
at the first 403 whose message starts 'AI Inventor per-run OpenRouter budget'.
Usage: judges.py gate | judges.py candidates"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cluster  # noqa: E402
import sandbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ["OPENROUTER_BASE_URL"].rstrip("/")
KEY = os.environ["OPENROUTER_API_KEY"]
JUDGES = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2"]
REPLACEMENT = "mistralai/mistral-medium-3.1"
CAP_USD = 0.6
COST_LOG = ROOT / "results" / "judge_costs.jsonl"
LABELS = ("KNOWN_FAMILY_NEW_PARAMETERS", "KNOWN", "NOT_KNOWN", "DEGENERATE")

SYSTEM = ("You are an expert on online one-dimensional bin packing heuristics: textbook rules (First/Best/Worst/Almost-"
          "Worst/Next Fit, Harmonic-k, Sum-of-Squares), genetic-programming hyper-heuristics (Burke, Hyde, Kendall), and "
          "LLM-evolved heuristics (FunSearch, EoH, ReEvo, HSEvo, MCTS-AHD, LLM4AD, the ab-heuristics of Herrmann & "
          "Pallez 2025). You judge whether a priority function decides like a known heuristic.")
QUESTION = ("Harness: priority(item, bins) scores every bin that can hold the item (bins = remaining capacities; unused "
            "bins at full capacity are included) and the item goes to the highest score (first index on ties).\n\n"
            "Does the CANDIDATE decide like any heuristic you know from the literature, up to tie-breaks or monotone "
            "transformations of the score, or is it a member of a published parametric family with other parameters?\n"
            "Answer with exactly one first line, one of:\nKNOWN:<name>\nKNOWN_FAMILY_NEW_PARAMETERS:<family>\n"
            "NOT_KNOWN\nDEGENERATE\nthen one paragraph of justification. DEGENERATE means the rule is trivial or broken "
            "(e.g. always opens a new bin, or ignores the bins).")

# ------------------------------------------------------------------------------------------------ controls
CONTROLS = [
    {"id": "ctl_c14", "expected": "KNOWN", "rule": "Score combines squared distance of the bin from the largest "
     "remaining capacity and powers of bins/item; scores of bins larger than the item are negated, then each score "
     "has the previous bin's score subtracted.",
     "code": "def priority(item, bins):\n    hi = np.max(bins)\n    b2 = bins * bins\n    sc = (bins - hi) * (bins - hi) / item + b2 / (item * item) + b2 / (item * item * item)\n    big = bins > item\n    sc[big] = -1.0 * sc[big]\n    sc[1:] = sc[1:] - sc[:-1]\n    return sc\n"},
    {"id": "ctl_abwf", "expected": "KNOWN", "rule": "If the item leaves a gap of at most 1, pick the tightest such bin; "
     "otherwise avoid bins whose gap would be at most 21; among bins leaving a larger gap prefer the one leaving the "
     "largest gap, and open a new bin last.",
     "code": "def priority(item, bins):\n    full = bins.max()\n    gap = bins - item\n    out = np.empty(len(bins))\n    for i, g in enumerate(gap):\n        if g <= 1:\n            out[i] = full - bins[i] + 1\n        elif g <= 21:\n            out[i] = -2.0\n        elif bins[i] == full:\n            out[i] = -1.0\n        else:\n            out[i] = -1.0 / g\n    return out\n"},
    {"id": "ctl_eoh", "expected": "KNOWN", "rule": "EoH-style closed-form score of bins and item: bins over the "
     "square root of log(bins - item), raised to bins/sqrt(item), times exp(item*(bins-item)) and constants.",
     "code": None},
    {"id": "ctl_wf", "expected": "KNOWN", "rule": "Place the item in the open bin with the most remaining room; open "
     "a new bin only if no open bin fits.",
     "code": "def priority(item, bins):\n    room = bins.astype(float) - item\n    is_new = bins == np.max(bins)\n    if np.all(is_new):\n        return room\n    room[is_new] = -1e12\n    return room\n"},
    {"id": "ctl_ss", "expected": "KNOWN", "rule": "Choose the bin that minimises the resulting sum over gap sizes of "
     "the squared number of open bins with that gap.",
     "code": "def priority(item, bins):\n    c = int(np.max(bins))\n    gaps = bins.astype(int)\n    cnt = np.bincount(gaps[gaps < c], minlength=c + 1)\n    change = np.zeros(len(bins))\n    o = gaps < c\n    change[o] = change[o] + (1 - 2 * cnt[gaps[o]])\n    after = gaps - int(item)\n    p = after > 0\n    change[p] = change[p] + (2 * cnt[after[p]] + 1)\n    return -change\n"},
    {"id": "ctl_new1", "expected": "NOT_KNOWN", "rule": "Prefer the bin whose leftover after placement is closest to "
     "the item's own size; new bins only when the item exceeds 70% of capacity.",
     "code": "def priority(item, bins):\n    cap = bins.max()\n    left = bins - item\n    s = -np.abs(left - item).astype(float)\n    if item <= 0.7 * cap:\n        s[bins == cap] -= 1e6\n    return s\n"},
    {"id": "ctl_new2", "expected": "NOT_KNOWN", "rule": "Score = sin(leftover / 5) plus a small preference for "
     "leftovers that are multiples of 7.",
     "code": "def priority(item, bins):\n    left = (bins - item).astype(float)\n    return np.sin(left / 5.0) + 0.5 * (np.mod(left, 7) == 0)\n"},
    {"id": "ctl_new3", "expected": "NOT_KNOWN", "rule": "Pick the bin whose leftover is closest to the median leftover "
     "of all fitting bins.",
     "code": "def priority(item, bins):\n    left = (bins - item).astype(float)\n    return -np.abs(left - np.median(left))\n"},
    {"id": "ctl_new4", "expected": "NOT_KNOWN", "rule": "Prefer leftovers whose ratio to the item is closest to the "
     "golden ratio 1.618.",
     "code": "def priority(item, bins):\n    left = (bins - item).astype(float)\n    return -np.abs(left / item - 1.618)\n"},
    {"id": "ctl_new5", "expected": "NOT_KNOWN", "rule": "Score = leftover modulo the item size (prefer leftovers that "
     "are just below a multiple of the item), ties to the fuller bin.",
     "code": "def priority(item, bins):\n    left = (bins - item).astype(float)\n    return np.mod(left, item) - 1e-3 * left\n"},
]

_lock = threading.Lock()
_state = {"spent": 0.0, "stopped": False, "stop_reason": None, "pins": {}}


def key_info() -> dict:
    try:
        r = requests.get(f"{BASE}/key", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
        return {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith(
            "application/json") else r.text[:300]}
    except requests.RequestException as e:
        return {"status": None, "error": repr(e)[:200]}


def ask(model: str, user: str, tag: str) -> dict:
    with _lock:
        if _state["stopped"]:
            return {"ok": False, "error": "batch stopped: " + str(_state["stop_reason"])}
        if _state["spent"] >= CAP_USD:
            _state["stopped"], _state["stop_reason"] = True, "artifact judge cap reached"
            return {"ok": False, "error": "cap"}
    body = {"model": model, "temperature": 0, "max_tokens": 600, "usage": {"include": True},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    if model in _state["pins"]:
        body["provider"] = {"order": [_state["pins"][model]], "allow_fallbacks": False}
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE}/chat/completions", json=body, timeout=180,
                              headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
        except requests.RequestException as e:
            err = repr(e)[:200]
            continue
        with _lock:
            if _state["stopped"]:
                return {"ok": False, "error": "batch stopped"}
        if r.status_code == 403 and "AI Inventor per-run OpenRouter budget" in r.text:
            with _lock:
                _state["stopped"], _state["stop_reason"] = True, r.text[:300]
            return {"ok": False, "error": "budget 403"}
        if r.status_code != 200:
            err = f"HTTP {r.status_code}: {r.text[:200]}"
            if body.get("provider") and r.status_code in (404, 503):
                body.pop("provider")  # pinned provider unavailable: record and fall back once
            continue
        d = r.json()
        txt = d["choices"][0]["message"]["content"] or ""
        cost = float((d.get("usage") or {}).get("cost") or 0.0)
        prov = d.get("provider")
        with _lock:
            _state["spent"] += cost
            if prov and model not in _state["pins"]:
                _state["pins"][model] = prov
        with open(COST_LOG, "a") as fh:
            fh.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tag": tag, "model": model,
                                 "provider": prov, "cost": cost, "usage": d.get("usage")}) + "\n")
        return {"ok": True, "text": txt, "label": parse_label(txt), "provider": prov, "cost": cost}
    return {"ok": False, "error": err}


def parse_label(txt: str) -> str:
    first = (txt.strip().splitlines() or [""])[0].strip().strip("*").strip()
    for lab in LABELS:
        if first.upper().startswith(lab):
            return lab
    m = re.search(r"\b(KNOWN_FAMILY_NEW_PARAMETERS|NOT_KNOWN|DEGENERATE|KNOWN)\b", txt)
    return m.group(1) if m else "UNPARSED"


def nearest3(code: str) -> list[dict]:
    c = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    ents = [e for e in c["entries"] if e.get("decisions") is not None]
    CV = np.array([e["decisions"] for e in ents], dtype=np.uint16)
    fn, et, _ = sandbox.compile_program(code)
    st = json.loads((ROOT / "data" / "probes" / "P1.json").read_text())["states"]
    arrs = [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in st]
    d = sandbox._probe_decisions(fn, arrs)
    ag = cluster.agree_counts(d[None, :], CV)[0] / cluster.N_STATES
    top = np.argsort(-ag, kind="stable")[:3]
    return [{"name": ents[i]["name"], "rule": ents[i]["adapter_note"][:160], "agreement": float(ag[i]),
             "code": ents[i]["code"][:1200]} for i in top]


def prompt_for(code: str, rule: str, near: list[dict]) -> str:
    s = QUESTION + "\n\nCANDIDATE:\n```python\n" + code.strip() + "\n```\nRule in words (from a human read): " + rule
    s += "\n\nThe three nearest corpus heuristics by exact decision agreement on 2,000 probe states:\n"
    for n in near:
        s += f"- {n['name']} (agreement {n['agreement']:.3f}): {n['rule']}\n```python\n{n['code'].strip()}\n```\n"
    return s


def eoh_best_code() -> str:
    c = json.loads((ROOT / "data" / "corpus" / "corpus.json").read_text())
    eoh = [e for e in c["entries"] if e["family"].startswith("eoh") and e.get("F") is not None]
    b = min(eoh, key=lambda e: e["F"])
    # disguise: rename variables, rewrite the division
    code = b["code"].replace("scores", "val").replace("bins", "caps").replace("def priority(item, caps)",
                                                                              "def priority(item, bins)")
    code = code.replace("def priority(item, bins):", "def priority(item, bins):\n    caps = bins")
    return code, b["name"]


def run_gate() -> dict:
    logger.info(f"key before gate: {key_info()}")
    code, eoh_name = eoh_best_code()
    for c in CONTROLS:
        if c["id"] == "ctl_eoh":
            c["code"], c["source"] = code, eoh_name
    items = []
    for c in CONTROLS:
        fn, et, msg = sandbox.compile_program(c["code"])
        assert fn is not None, (c["id"], et, msg)
        items.append((c, prompt_for(c["code"], c["rule"], nearest3(c["code"]))))
    res = {}
    models = JUDGES + [REPLACEMENT]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {(m, c["id"]): ex.submit(ask, m, p, f"gate:{c['id']}") for m in models for c, p in items}
        for k, f in futs.items():
            res[k] = f.result()
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "per_model": {}, "spent_usd": _state["spent"],
           "stopped": _state["stopped"], "stop_reason": _state["stop_reason"], "pins": _state["pins"]}
    for m in models:
        rows, score = [], 0
        for c, _ in items:
            r = res[(m, c["id"])]
            lab = r.get("label", "ERROR")
            ok = (lab in ("KNOWN", "KNOWN_FAMILY_NEW_PARAMETERS")) if c["expected"] == "KNOWN" else (lab == "NOT_KNOWN")
            score += int(ok)
            rows.append({"control": c["id"], "expected": c["expected"], "label": lab, "correct": ok,
                         "text": (r.get("text") or r.get("error", ""))[:600]})
        out["per_model"][m] = {"score": score, "pass": score >= 9, "rows": rows}
    judges = [m for m in JUDGES if out["per_model"][m]["pass"]]
    if len(judges) < 2 and out["per_model"][REPLACEMENT]["pass"]:
        judges.append(REPLACEMENT)
    out["gated_judges"] = judges[:2]
    out["tiebreaker"] = REPLACEMENT if REPLACEMENT not in out["gated_judges"] and out["per_model"][REPLACEMENT]["pass"] else None
    out["judge_gate_met"] = len(out["gated_judges"]) >= 2
    (ROOT / "results" / "judge_gate.json").write_text(json.dumps(out, indent=1))
    logger.info(f"gate: { {m: v['score'] for m, v in out['per_model'].items()} } spent ${_state['spent']:.4f}")
    return out


def run_candidates() -> dict:
    gate = json.loads((ROOT / "results" / "judge_gate.json").read_text())
    _state["pins"].update(gate.get("pins", {}))
    _state["spent"] = gate.get("spent_usd", 0.0)
    v3 = json.loads((ROOT / "results" / "v3_candidates.json").read_text())
    reads = json.loads((ROOT / "audit" / "manual_read.json").read_text())
    logger.info(f"key before candidates: {key_info()}")
    aud = v3.get("audited", [])
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "judges": gate["gated_judges"],
           "tiebreaker": gate.get("tiebreaker"), "rows": []}
    if not gate.get("judge_gate_met"):
        # fallback (plan): judges become advisory and the manual read decides; all three are asked, labelled advisory
        out["judges"] = JUDGES + [REPLACEMENT]
        out["tiebreaker"] = None
        out["advisory"] = True
        gate = dict(gate, gated_judges=out["judges"])
    if not aud:
        out["note"] = "NB set empty: no judge called"
        (ROOT / "results" / "judge_calls.json").write_text(json.dumps(out, indent=1))
        return out
    items = []
    for c in aud:
        rd = reads[c["anon_id"]]
        items.append((c, prompt_for(c["code"], rd["rule_in_words"], nearest3(c["code"]))))
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {(m, c["anon_id"]): ex.submit(ask, m, p, f"cand:{c['anon_id']}") for m in gate["gated_judges"]
                for c, p in items}
        res = {k: f.result() for k, f in futs.items()}
    tb_items = []
    for c, p in items:
        labs = [res[(m, c["anon_id"])].get("label", "ERROR") for m in gate["gated_judges"]]
        if len(set(labs)) > 1 and out["tiebreaker"]:
            tb_items.append((c, p))
    tb = {}
    if tb_items:
        with ThreadPoolExecutor(max_workers=6) as ex:
            tb = {c["anon_id"]: ex.submit(ask, out["tiebreaker"], p, f"tb:{c['anon_id']}").result() for c, p in tb_items}
    for c, _ in items:
        row = {"anon_id": c["anon_id"]}
        for m in gate["gated_judges"]:
            r = res[(m, c["anon_id"])]
            row[m] = {"label": r.get("label", "ERROR"), "text": (r.get("text") or r.get("error", ""))[:1500],
                      "provider": r.get("provider")}
        if c["anon_id"] in tb:
            row["tiebreak"] = {"model": out["tiebreaker"], "label": tb[c["anon_id"]].get("label", "ERROR"),
                               "text": (tb[c["anon_id"]].get("text") or "")[:1500]}
        out["rows"].append(row)
    out["spent_usd_total_judges"] = _state["spent"]
    out["stopped"], out["stop_reason"] = _state["stopped"], _state["stop_reason"]
    (ROOT / "results" / "judge_calls.json").write_text(json.dumps(out, indent=1))
    logger.info(f"candidates judged: {len(out['rows'])}; judge spend ${_state['spent']:.4f}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "judges.log", rotation="30 MB", level="DEBUG")
    {"gate": run_gate, "candidates": run_candidates}[sys.argv[1]]()


if __name__ == "__main__":
    main()
