#!/usr/bin/env python3
"""S11 P3 audit. Candidates = VALID programs that are better than best fit on BOTH held-out sets (H-OR3 <= 4.294%,
H-FSW5k <= 3.187%) and novel (maximum agreement < 0.9 with every corpus heuristic, ab family included). Each is listed
with its 3 nearest corpus heuristics. With zero candidates no judge call is made (plan S11). Otherwise two judge
families (deepseek-chat-v3.1, kimi-k2; third: mistral-medium-3.1) are each gated on 10 controls of known class
(>= 9/10) and then judge every candidate (KNOWN:<name> / KNOWN FAMILY, NEW PARAMETERS / NOT_KNOWN / DEGENERATE).
NOVEL needs both gated judges to answer NOT_KNOWN and the manual read (results/p3_manual_read.json) to find no
equivalent. Sub-cap USD 0.3."""
from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from loguru import logger

import analysis
from common import RESULTS, add_cost, read_json, setup_logging, write_json

JUDGES = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2", "mistralai/mistral-medium-3.1"]
SUB_CAP = 0.3
PROMPT = ("You are an expert in online bin packing heuristics (first fit, best fit, worst fit, almost worst fit, "
          "last fit, random fit, harmonic, FunSearch-discovered heuristics, EoH/ReEvo/HSEvo/MCTS-AHD heuristics, "
          "and the two-parameter ab rules of Herrmann and Pallez). The Python function below scores bins for an "
          "arriving item (the item goes to the highest score). Is the rule it implements a KNOWN heuristic? Answer "
          "on the first line with exactly one of: KNOWN:<name> | KNOWN FAMILY, NEW PARAMETERS | NOT_KNOWN | "
          "DEGENERATE. Then give one paragraph describing the rule.\n\n```python\n{code}\n```")
CONTROLS = [  # (code, expected first-line class)
    ("def priority(item, bins):\n    import numpy as np\n    slack = bins - item\n    return -slack\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    return -np.arange(len(bins), dtype=float)\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    u = bins < bins.max()\n    return np.where(u, bins, -1.0)\n",
     "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    return 1.0 / (bins - item + 1e-9)\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    u = bins < bins.max()\n    if u.sum() < 2:\n"
     "        return u.astype(float)\n    t = np.sort(bins[u])[-2]\n    return np.where(u & (bins == t), 2.0, "
     "np.where(u, 1.0, 0.0))\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    return np.where(bins == item, 1e6, -(bins - item))\n",
     "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    u = bins < bins.max()\n    return np.where(u, "
     "np.arange(len(bins)), -1.0)\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    return np.zeros(len(bins))\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    return np.ones(len(bins)) * 3.0\n", "KNOWN"),
    ("def priority(item, bins):\n    import numpy as np\n    u = bins < bins.max()\n    r = np.random.random(len(bins))\n"
     "    return np.where(u, r, -1.0)\n", "KNOWN"),
]


def call(model: str, text: str) -> tuple[str, float]:
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": model, "messages": [{"role": "user", "content": text}], "temperature": 0, "max_tokens": 400,
            "usage": {"include": True}}
    r = requests.post(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, json=body,
                      timeout=180)
    if r.status_code == 403 and "AI Inventor per-run OpenRouter budget" in r.text:
        raise RuntimeError("budget 403")
    r.raise_for_status()
    d = r.json()
    cost = float((d.get("usage") or {}).get("cost") or 0.0)
    add_cost("p3_judges", cost)
    return d["choices"][0]["message"]["content"] or "", cost


def first_class(ans: str) -> str:
    line = ans.strip().splitlines()[0].upper() if ans.strip() else ""
    for c in ("KNOWN FAMILY", "NOT_KNOWN", "DEGENERATE", "KNOWN"):
        if re.search(re.escape(c), line):
            return c
    return "UNPARSED"


def run_all() -> dict[str, Any]:
    setup_logging("judges")
    rows = analysis.load_rows()
    cand = [r for r in rows if r.get("valid") and analysis.better(r) and analysis.novel(r)]
    out: dict[str, Any] = {"n_candidates": len(cand), "rule": __doc__.split("Candidates = ")[1].split(" With zero")[0],
                           "candidates": [{"row_id": r["row_id"], "h_or3_excess": r.get("h_or3_excess"),
                                           "h_fsw5k_excess": r.get("h_fsw5k_excess"),
                                           "corpus_top3": r.get("corpus_top3"), "code": r.get("code")} for r in cand],
                           "judge_calls": 0, "spend_usd": 0.0, "confirmed_novel_ids": [],
                           "near_misses": {
                               "better_not_novel": [r["row_id"] for r in rows if r.get("valid") and analysis.better(r)
                                                    and not analysis.novel(r)],
                               "passed_or3": [{"row_id": r["row_id"], "h_or3_excess": r.get("h_or3_excess"),
                                               "h_fsw5k_excess": r.get("h_fsw5k_excess"),
                                               "corpus_max_agree": r.get("corpus_max_agree"),
                                               "corpus_nearest": r.get("corpus_nearest")}
                                              for r in rows if r.get("valid") and r.get("h_or3_excess") is not None
                                              and r["h_or3_excess"] <= 4.294]}}
    if not cand:
        logger.info("P3: zero candidates, no judge call (plan S11)")
        write_json(RESULTS / "p3_audit.json", out)
        return out
    spend = 0.0
    gated: list[str] = []
    gate: dict[str, Any] = {}
    for jm in JUDGES:
        if len(gated) >= 2:
            break
        ok = 0
        answers = []
        for code, exp in CONTROLS:
            if spend >= SUB_CAP:
                break
            ans, c = call(jm, PROMPT.format(code=code))
            spend += c
            out["judge_calls"] += 1
            cls = first_class(ans)
            ok += int(cls.startswith(exp))
            answers.append(cls)
        gate[jm] = {"correct": ok, "n": len(CONTROLS), "passed": ok >= 9, "answers": answers}
        if ok >= 9:
            gated.append(jm)
    out["judge_gate"] = gate
    manual = read_json(RESULTS / "p3_manual_read.json") if (RESULTS / "p3_manual_read.json").exists() else {}
    for c in out["candidates"]:
        c["judges"] = {}
        for jm in gated:
            if spend >= SUB_CAP:
                break
            ans, cost = call(jm, PROMPT.format(code=c["code"]))
            spend += cost
            out["judge_calls"] += 1
            c["judges"][jm] = {"class": first_class(ans), "answer": ans[:1500]}
        c["manual_read"] = manual.get(c["row_id"])
        all_nk = len(c["judges"]) >= 2 and all(v["class"] == "NOT_KNOWN" for v in c["judges"].values())
        c["novel_confirmed"] = bool(all_nk and c["manual_read"] and c["manual_read"].get("no_equivalent"))
        if c["novel_confirmed"]:
            out["confirmed_novel_ids"].append(c["row_id"])
    out["spend_usd"] = spend
    out["label"] = "judged" if len(gated) >= 2 else "manually audited (fewer than two judges passed the gate)"
    write_json(RESULTS / "p3_audit.json", out)
    logger.info(f"P3 audit: {len(cand)} candidates, {len(out['confirmed_novel_ids'])} confirmed, ${spend:.4f}")
    return out


if __name__ == "__main__":
    print(json.dumps(run_all(), default=str)[:2000])
