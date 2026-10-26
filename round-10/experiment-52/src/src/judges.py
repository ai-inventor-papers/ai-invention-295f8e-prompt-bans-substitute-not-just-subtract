#!/usr/bin/env python3
"""S11 novelty judges (OpenRouter; hard cap USD 0.6). Two judge families (deepseek-chat-v3.1, kimi-k2; mistral-medium-3.1
as the one-time replacement) are gated on 10 controls (5 disguised corpus heuristics, 5 executor-written compositions
absent from the literature; >= 9/10 right), then asked about every judged V3 candidate. The manual read (done first,
arm-blind) is decisive; judges are advisory if fewer than two families pass. Responses are cached in
results/judge_cache.jsonl; spend is tracked from usage.cost and GET /key; the first budget 403 stops the batch."""
from __future__ import annotations

import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import common as C  # noqa: E402
import corpus as CO  # noqa: E402

BASE = os.environ["OPENROUTER_BASE_URL"].rstrip("/")
KEY = os.environ["OPENROUTER_API_KEY"]
JUDGES = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2"]
REPLACEMENT = "mistralai/mistral-medium-3.1"
CAP_USD = 0.6
CACHE = C.RESULTS / "judge_cache.jsonl"
CLASSES = ("KNOWN_FAMILY_NEW_PARAMETERS", "KNOWN", "NOT_KNOWN", "DEGENERATE")


class BudgetStop(Exception):
    pass


class Spend:
    def __init__(self):
        self.total = 0.0
        self.lock = threading.Lock()
        self.stopped = False

    def add(self, c: float) -> None:
        with self.lock:
            self.total += float(c or 0.0)
            if self.total >= CAP_USD:
                self.stopped = True


SPEND = Spend()


def key_status() -> dict:
    try:
        r = httpx.get(f"{BASE}/key", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"error": repr(e)}


def pick_provider(model: str) -> str | None:
    """First full-precision endpoint from GET /models/{id}/endpoints."""
    try:
        r = httpx.get(f"{BASE}/models/{model}/endpoints", headers={"Authorization": f"Bearer {KEY}"}, timeout=30)
        eps = r.json().get("data", {}).get("endpoints", [])
    except (httpx.HTTPError, ValueError, AttributeError):
        return None
    for e in eps:
        q = (e.get("quantization") or "").lower()
        if q in ("fp16", "bf16", "fp32", ""):
            return e.get("provider_name") or e.get("name")
    return None


def _cache() -> dict:
    out = {}
    for r in C.read_jsonl(CACHE):
        out[(r["model"], r["item_id"])] = r
    return out


def ask(model: str, provider: str | None, item_id: str, prompt: str, cache: dict) -> dict:
    if (model, item_id) in cache:
        return cache[(model, item_id)]
    if SPEND.stopped:
        raise BudgetStop("spend cap or budget refusal reached")
    body = {"model": model, "temperature": 0, "max_tokens": 500, "usage": {"include": True},
            "messages": [{"role": "user", "content": prompt}]}
    if provider:
        body["provider"] = {"order": [provider], "allow_fallbacks": False}
    r = httpx.post(f"{BASE}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json=body, timeout=180)
    if r.status_code == 403 and "AI Inventor per-run OpenRouter budget" in r.text:
        SPEND.stopped = True
        raise BudgetStop(r.text[:200])
    if r.status_code != 200 and provider:
        body.pop("provider")
        r = httpx.post(f"{BASE}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json=body, timeout=180)
        provider = f"{provider} (unavailable; fell back to default routing)"
    d = r.json()
    if "choices" not in d:
        raise RuntimeError(f"{model}: {str(d)[:300]}")
    text = d["choices"][0]["message"]["content"] or ""
    cost = (d.get("usage") or {}).get("cost") or 0.0
    SPEND.add(cost)
    row = {"model": model, "provider": provider, "served_provider": d.get("provider"), "item_id": item_id,
           "answer": text, "label": parse(text), "cost": cost, "usage": d.get("usage"), "utc": C.utc()}
    C.append_jsonl(CACHE, row)
    return row


def parse(text: str) -> str:
    t = text.upper()
    for c in CLASSES:
        if re.search(rf"\b{c}\b", t):
            return c
    return "UNPARSED"


QUESTION = ("You are an expert on online bin packing heuristics. A heuristic is a priority function: for each arriving item it "
            "scores every bin the item fits into (unused bins at full capacity included) and the item goes to the highest "
            "score (first index on ties). Question: does the CANDIDATE decide like any heuristic known from the literature "
            "(textbook rules such as first/best/worst/almost-worst/next fit, harmonic; FunSearch's evolved heuristics; EoH, "
            "ReEvo, HSEvo, MCTS-AHD, LLM4AD heuristics; the ab-heuristics of Herrmann & Pallez 2025), up to tie-breaks or "
            "monotone transformations of the score, or is it a member of a published parametric family with other parameter "
            "values? Answer on the first line with exactly one of: KNOWN:<name> | KNOWN_FAMILY_NEW_PARAMETERS:<family> | "
            "NOT_KNOWN | DEGENERATE, then give one paragraph of justification.")


def candidate_prompt(code: str, rule: str, nearest: list[dict]) -> str:
    near = "\n\n".join(f"Nearest known heuristic {i + 1}: {n['name']} (agreement {n['agreement']:.3f} on 2,000 probe states)\n"
                       f"Rule: {n['rule']}\n```python\n{n['code']}\n```" for i, n in enumerate(nearest))
    return (f"{QUESTION}\n\nCANDIDATE:\n```python\n{code}\n```\nCandidate rule in words: {rule}\n\n"
            f"For reference, the three known heuristics whose decisions agree most with the candidate:\n\n{near}")


def corpus_rule(name: str, entry: dict | None) -> tuple[str, str]:
    m = re.match(r"ab-(FF|BF|WF)\((\d+),(\d+)\)", name)
    if m:
        base, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        return (f"ab-{base} heuristic (Herrmann & Pallez 2025) with a={a}, b={b}: best fit among bins with remaining "
                f"capacity <= item + {a}; bins with remaining capacity below item + {b} avoided; otherwise {base} "
                f"(new bin last)", bp.ab_source(a, b, base))
    rules = {"FF": "first fit", "BF": "best fit", "WF": "worst fit among opened bins", "AWF": "almost-worst fit",
             "FunSearch-c12": "FunSearch OR heuristic: tiered scores by gap g = bins - item (g<=2: 4, <=3: 3, <=5: 2, <=7: 1, <=9: 0.9, <=12: 0.95, ..., else 0.99)",
             "FunSearch-c12-vec": "vectorised FunSearch OR heuristic (tiered gap scores)",
             "FunSearch-c14": "FunSearch Weibull heuristic (best fit on a perfect fit, else worst-fit-like when the gap is large, else a new bin)",
             "MCTS-AHD-gpt": "MCTS-AHD heuristic: proximity score with a gap penalty around half the average capacity and utilisation tiers",
             "RAISE-appendixE.1.1": "RAISE heuristic: rank + slot-robustness + tightness + sliver penalty + exact-fit bonus, normalised"}
    if name in rules:
        return rules[name], entry["code"] if entry else ""
    if entry and entry.get("eoh_algorithm"):
        return f"EoH published heuristic: {entry['eoh_algorithm'][:300]}", entry["code"]
    return (entry or {}).get("adapter_note", name), (entry or {}).get("code", "")


def controls() -> list[dict]:
    _, _, _, w_src = bp.funsearch_notebook()
    eoh = json.loads((C.ROOT / "ext/eoh/docs__Results__Prob1_OnlineBinPacking__run2__population_generation_20.json").read_text())[0]
    eoh_code = re.sub(r"def\s+score\s*\(", "def priority(", eoh["code"]).replace("scores", "vals")
    c14 = w_src.replace("max_bin_cap", "top").replace("score", "s")
    known = [
        ("ctl_bf", "def priority(item, bins):\n    slack = bins - item\n    return 1.0 / (1.0 + slack)\n", "KNOWN"),
        ("ctl_wf", "def priority(item, bins):\n    full = bins.max()\n    s = np.where(bins == full, -np.inf, bins.astype(float))\n    return np.zeros(len(bins)) if np.isinf(s).all() else s\n", "KNOWN"),
        ("ctl_c14", c14, "KNOWN"),
        ("ctl_abwf", ("def priority(item, bins):\n    cap = bins.max()\n    out = np.zeros(len(bins))\n    for i, b in enumerate(bins):\n"
                      "        if b <= item + 1:\n            out[i] = cap - b + 1\n        elif b <= item + 21:\n            out[i] = -2.0\n"
                      "        elif b == cap:\n            out[i] = -1.0\n        else:\n            out[i] = -1.0 / (b - item)\n    return out\n"), "KNOWN"),
        ("ctl_eoh", eoh_code, "KNOWN"),
    ]
    novel = [
        ("ctl_n1", "def priority(item, bins):\n    r = bins - item\n    return -np.abs((r % 7) - 3) - 0.01 * r\n", "NOT_KNOWN"),
        ("ctl_n2", "def priority(item, bins):\n    cap = bins.max()\n    fill = 1 - bins / cap\n    return -np.abs(fill - 0.6) + 0.001 * (bins < cap)\n", "NOT_KNOWN"),
        ("ctl_n3", "def priority(item, bins):\n    r = bins - item\n    return np.where(item > 50, -r, -np.abs(r - 2 * item))\n", "NOT_KNOWN"),
        ("ctl_n4", "def priority(item, bins):\n    r = (bins - item).astype(float)\n    return np.cos(r / (item + 1.0)) - 0.002 * r\n", "NOT_KNOWN"),
        ("ctl_n5", "def priority(item, bins):\n    r = bins - item\n    return -(r - np.median(r)) ** 2\n", "NOT_KNOWN"),
    ]
    return [{"id": i, "code": c, "truth": t} for i, c, t in known + novel]


def control_prompt(code: str) -> str:
    return f"{QUESTION}\n\nCANDIDATE:\n```python\n{code}\n```"


def correct(label: str, truth: str) -> bool:
    if truth == "KNOWN":
        return label in ("KNOWN", "KNOWN_FAMILY_NEW_PARAMETERS")
    return label == "NOT_KNOWN"


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("judges")
    cache = _cache()
    k0 = key_status()
    logger.info(f"OpenRouter key before: {json.dumps(k0)[:300]}")
    out = {"key_before": k0, "gate": {}, "judges_used": [], "candidates": {}, "stopped": None}
    providers = {m: pick_provider(m) for m in JUDGES + [REPLACEMENT]}
    out["providers"] = providers
    ctl = controls()

    def gate(model: str) -> dict:
        with ThreadPoolExecutor(5) as ex:
            res = list(ex.map(lambda c: ask(model, providers[model], c["id"], control_prompt(c["code"]), cache), ctl))
        right = [correct(r["label"], c["truth"]) for r, c in zip(res, ctl)]
        return {"n_right": int(sum(right)), "pass": sum(right) >= 9,
                "labels": {c["id"]: r["label"] for r, c in zip(res, ctl)}}

    passed = []
    replaced = False
    try:
        for m in JUDGES:
            g = gate(m)
            out["gate"][m] = g
            logger.info(f"gate {m}: {g['n_right']}/10")
            if g["pass"]:
                passed.append(m)
            elif not replaced:
                replaced = True
                g2 = gate(REPLACEMENT)
                out["gate"][REPLACEMENT] = g2
                logger.info(f"gate {REPLACEMENT} (replacement): {g2['n_right']}/10")
                if g2["pass"]:
                    passed.append(REPLACEMENT)
        out["judges_used"] = passed
        out["judges_advisory"] = len(passed) < 2
        # candidates (the judged set of the manual read), every gated-or-not judge family answers for the record
        mr = json.loads((C.RESULTS / "manual_read.json").read_text())["reads"]
        blind = {b["oid"]: b for b in json.loads((C.RESULTS / "manual_read_blind.json").read_text())}
        corpus = {e["name"]: e for e in json.loads((C.RESULTS / "corpus.json").read_text())["entries"]}
        items = []
        for oid, b in blind.items():
            nearest = []
            for n in b["nearest"][:3]:
                rule, code = corpus_rule(n["name"], corpus.get(n["name"]))
                nearest.append({"name": n["name"], "agreement": n["agreement"], "rule": rule, "code": code})
            items.append((oid, candidate_prompt(b["code"], mr[oid]["rule_in_words"], nearest)))
        ask_models = [m for m in out["gate"]]
        for m in ask_models:
            with ThreadPoolExecutor(6) as ex:
                res = list(ex.map(lambda it: ask(m, providers[m], it[0], it[1], cache), items))
            for (oid, _), r in zip(items, res):
                out["candidates"].setdefault(oid, {})[m] = {"label": r["label"], "answer": r["answer"][:1200]}
            logger.info(f"{m}: candidate labels {sorted(set(r['label'] for r in res))}")
    except BudgetStop as e:
        out["stopped"] = str(e)
        logger.warning(f"judge batch stopped: {e}")
    out["spend_usd"] = SPEND.total
    out["key_after"] = key_status()
    C.write_json(C.RESULTS / "judges.json", out)
    logger.info(f"judges done; spend ${SPEND.total:.4f}; gate {{m: g['n_right'] for m, g in out['gate'].items()}}")


if __name__ == "__main__":
    main()
