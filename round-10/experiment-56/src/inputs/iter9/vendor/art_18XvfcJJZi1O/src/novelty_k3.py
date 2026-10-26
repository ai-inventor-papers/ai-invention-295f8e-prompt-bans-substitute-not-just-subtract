#!/usr/bin/env python3
"""Novelty audit (stage 13.1, CPU + OpenRouter): every CORRECT generated program labelled 'other' goes to two blind
judges of different families (deepseek/deepseek-chat-v3.1, google/gemini-2.5-flash-lite), each shown its three nearest
known solutions (token-sequence similarity over the art_j3Rm_lr2nzR6 corpus: LeetCode, Mercury, TheAlgorithms, KodCode,
XLCoST programs of the same problem family), gated on 10 controls of known class; mistralai/mistral-medium-3.1
resolves disagreements. Running usage.cost; the first 403 'AI Inventor per-run OpenRouter budget' stops the batch;
cap USD 0.30. With no 'other' program the rule-of-three bound is reported and no call is made."""

from __future__ import annotations

import ast
import difflib
import io
import json
import os
import re
import sys
import tokenize
from pathlib import Path
from typing import Any

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from k3cfg import BUDGET_MSG, DATA_DIR, JUDGE_CAP_USD, RESULTS_DIR, read_jsonl, setup_logging, write_json  # noqa: E402

DEP = Path(__file__).resolve().parents[8] / "round-1/dataset-1/src/full_data_out.json"
JUDGES = ("deepseek/deepseek-chat-v3.1", "google/gemini-2.5-flash-lite")
TIEBREAK = "mistralai/mistral-medium-3.1"
CLASSES = {"B3": ["kruskal", "prim_heap", "prim_array", "boruvka", "other"],
           "T10": ["union_find", "dfs", "bfs", "label_propagation", "other"]}
KEYS = {"B3": re.compile(r"spanning|kruskal|prim|mst|boruvka", re.I),
        "T10": re.compile(r"connected component|union.?find|disjoint set|number of (connected )?(components|provinces)"
                          r"|find\(", re.I)}


def norm_tokens(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append("ID" if t.string not in __import__("keyword").kwlist else t.string)
            elif t.type in (tokenize.OP, tokenize.NUMBER):
                out.append(t.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        out = code.split()
    return out


def corpus(unit: str) -> list[dict[str, Any]]:
    d = json.loads(DEP.read_text())
    rows = []
    for ds in d["datasets"]:
        if ds["dataset"] not in ("leetcodedataset", "mercury", "thealgorithms_python", "kodcode_algorithmic",
                                 "xlcost_python"):
            continue
        for e in ds["examples"]:
            txt = (e.get("input") or "") + " " + (e.get("output") or "")[:400]
            if KEYS[unit].search(txt) and e.get("output") and "def " in e["output"]:
                rows.append({"src": ds["dataset"], "id": e.get("metadata_row_index"), "code": e["output"]})
    return rows


def nearest(code: str, corp: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    a = norm_tokens(code)
    sc = []
    for r in corp:
        sm = difflib.SequenceMatcher(None, a, norm_tokens(r["code"]), autojunk=False)
        sc.append((sm.ratio(), r))
    sc.sort(key=lambda x: -x[0])
    return [{"similarity": round(s, 3), "src": r["src"], "id": r["id"], "code": r["code"][:1500]} for s, r in sc[:k]]


def judge(client: Any, model: str, unit: str, code: str, near: list[dict[str, Any]], spent: list[float]) -> str:
    labels = CLASSES[unit]
    msg = (f"Classify the algorithm of this Python program for the task "
           f"{'minimum spanning tree weight' if unit == 'B3' else 'number of connected components'}. Answer with exactly "
           f"one label from {labels}. Use 'other' only if it is none of the named algorithms (a renamed or disguised "
           f"named algorithm is that algorithm). Three nearest known solutions are shown for reference.\n\nPROGRAM:\n"
           f"{code[:4000]}\n\n" + "\n\n".join(f"KNOWN {i + 1}:\n{n['code']}" for i, n in enumerate(near)) +
           "\n\nLabel:")
    r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": msg}], temperature=0,
                                       max_tokens=10, extra_body={"usage": {"include": True}})
    cost = float(getattr(r, "usage", None) and getattr(r.usage, "cost", 0) or 0)
    spent[0] += cost
    txt = (r.choices[0].message.content or "").strip().lower()
    for lab in labels:
        if lab in txt:
            return lab
    return "unparsed"


def main() -> None:
    setup_logging("novelty")
    progs = []
    for f in sorted(DATA_DIR.glob("gen_labels_*.jsonl")) + [DATA_DIR / "engine_check_labels.jsonl"]:
        for r in read_jsonl(f):
            progs.append(r)
    n_correct = sum(bool(r.get("passed")) for r in progs)
    others = [r for r in progs if r.get("label") == "other" and r.get("passed")]
    out: dict[str, Any] = {"n_programs": len(progs), "n_correct": n_correct, "n_correct_other": len(others)}
    if not others:
        out["rule_of_three_upper_bound_other_rate"] = 3.0 / max(n_correct, 1)
        out["judge_calls"] = 0
        out["usd"] = 0.0
        out["note"] = "no correct program was labelled 'other': no judge call; 95% upper bound on the novel-class " \
                      "rate among correct programs = 3 / n_correct"
        write_json(RESULTS_DIR / "novelty_audit.json", out)
        logger.info(out)
        return
    from openai import OpenAI
    client = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    spent = [0.0]
    rows = []
    stopped = None
    # gate: each judge must label >= 9 of 10 controls of known class correctly (B3 + T10 references, T10 gold items)
    ctrl = []
    for f in sorted((ROOT / "inputs" / "iter5_exp26" / "units" / "B3" / "references").glob("*.py")):
        ctrl.append(("B3", f.read_text(), f.stem))
    t10 = ROOT / "inputs" / "iter6_exp30" / "inputs" / "exp11" / "bench" / "T10_connected_components"
    for f in sorted((t10 / "references").glob("*.py")):
        ctrl.append(("T10", f.read_text(), f.stem))
    for l in (t10 / "gold_set.jsonl").read_text().splitlines()[:2]:
        g = json.loads(l)
        ctrl.append(("T10", g["code"], g["adjudicated"]))
    gate = {}
    for jm in JUDGES + (TIEBREAK,):
        ok = 0
        for unit, code, lab in ctrl[:10]:
            try:
                ok += int(judge(client, jm, unit, code, [], spent) == lab)
            except Exception as e:  # noqa: BLE001
                if BUDGET_MSG in str(e):
                    stopped = "budget_403"
                    break
        gate[jm] = {"correct": ok, "n": min(10, len(ctrl)), "pass": ok >= 9}
    out["judge_gate"] = gate
    for r in others:
        unit = r["unit"]
        corp = corpus(unit)
        near = nearest(r.get("code") or "", corp)
        try:
            if spent[0] >= JUDGE_CAP_USD:
                stopped = "cap"
                break
            a = judge(client, JUDGES[0], unit, r.get("code") or "", near, spent)
            b = judge(client, JUDGES[1], unit, r.get("code") or "", near, spent)
            c = judge(client, TIEBREAK, unit, r.get("code") or "", near, spent) if a != b else None
        except Exception as e:  # noqa: BLE001
            if BUDGET_MSG in str(e):
                stopped = "budget_403"
                break
            logger.error(f"judge error {e}")
            a = b = c = "error"
        final = a if a == b else (c or "disputed")
        rows.append({"sid": r["sid"], "unit": unit, "judge_a": a, "judge_b": b, "judge_c": c, "final": final,
                     "nearest": [{k: v for k, v in n.items() if k != "code"} for n in near]})
    out.update({"rows": rows, "usd": spent[0], "stopped": stopped,
                "n_novel_after_adjudication": sum(x["final"] == "other" for x in rows)})
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    logger.info({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
