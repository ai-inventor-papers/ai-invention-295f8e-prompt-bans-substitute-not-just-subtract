#!/usr/bin/env python3
"""Novelty audit (plan 6.2) and nearest-known-solution pass.

Corpus: every code-bearing 'output' (else 'input') of ALL 10 datasets of the declared dependency art_j3Rm_lr2nzR6
(inputs/dep_art_j3Rm/full_data_out.json; leetcodedataset, mercury, llm_creativity [labels only], thealgorithms_python,
clrs_text, humanevalplus, enamel, concreteness_norms [no code], kodcode_algorithmic, xlcost_python) -- exp29 known6's
tokeniser (identifiers abstracted, algorithm-revealing names kept), 5-token shingles, Jaccard.

Audited programs: every CORRECT 'other' program (passed, label 'other') of the rows this artifact uses (its own
generations and the relabelled exp27 knob rows that enter the S3 hull). Each goes to two blind judges of different
families (mistralai/mistral-medium-3.1, moonshotai/kimi-k2) with the task specification, the task's catalogue of
known modes and its 3 nearest known solutions; a third judge (deepseek/deepseek-chat-v3.1) on disagreement. Ten
control programs of known catalogue class (correct, runtime label == AST label) are judged the same way to measure
judge accuracy. Classes: NOVEL / CATALOGUE_VARIANT (named) / LABELLER_MISS (named catalogue mode) / DEGENERATE.
The final class is the agreed judge class, recorded beside a manual pass (results/novelty_manual.json) when present.
Every call's usage.cost is ledgered; the batch stops at the first 403 'AI Inventor per-run OpenRouter budget'.
Descriptive: max-Jaccard class (KNOWN-CLOSE >= 0.5, VARIANT 0.25-0.5, DISTANT < 0.25) of every distinct correct
off-default program per (task, arm family).

usage: .venv/bin/python src/novelty_k.py
"""

from __future__ import annotations

import asyncio
import io
import json
import keyword
import os
import re
import sys
import tokenize
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import k_cfg as K  # noqa: E402
from k_cfg import BUDGET_MSG, DEFAULTS, LABELS, RESULTS, read_json, read_jsonl, sha256_text, write_json  # noqa: E402

DEP_FULL = K.INPUTS / "dep_art_j3Rm" / "full_data_out.json"
KEEP = {"heapq", "heappush", "heappop", "heapify", "deque", "popleft", "append", "pop", "parent", "find", "union",
        "rank", "visited", "seen", "dist", "inf", "float", "range", "len", "min", "max", "sorted", "set", "dict",
        "defaultdict", "list", "stack", "queue", "graph", "adj", "edges", "add", "get", "items", "extend", "insert"}
DIM = 1 << 20
SH = 5
JUDGES = ("mistralai/mistral-medium-3.1", "moonshotai/kimi-k2")
TIE_JUDGE = "deepseek/deepseek-chat-v3.1"
CAP_USD = 0.25
CLASSES = ("NOVEL", "CATALOGUE_VARIANT", "LABELLER_MISS", "DEGENERATE")
LEDGER = RESULTS / "novelty_costs.json"


def toks(code: str) -> list[str]:
    out = []
    try:
        for t in tokenize.generate_tokens(io.StringIO(code).readline):
            if t.type == tokenize.NAME:
                out.append(t.string if (keyword.iskeyword(t.string) or t.string in KEEP) else "ID")
            elif t.type == tokenize.OP:
                out.append(t.string)
            elif t.type == tokenize.NUMBER:
                out.append("NUM")
            elif t.type == tokenize.STRING:
                out.append("STR")
            elif t.type in (tokenize.INDENT, tokenize.DEDENT):
                out.append(tokenize.tok_name[t.type])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def shingles(code: str) -> set[int]:
    t = toks(code)
    return {hash(" ".join(t[i:i + SH])) % DIM for i in range(max(len(t) - SH + 1, 0))}


def matrix(sets: list[set[int]]) -> sparse.csr_matrix:
    rows, cols = [], []
    for i, s in enumerate(sets):
        rows += [i] * len(s)
        cols += list(s)
    return sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(len(sets), DIM))


def corpus() -> tuple[list[set[int]], list[str], list[str], dict[str, int], dict[str, int]]:
    full = json.loads(DEP_FULL.read_text())
    sets, src, codes, per, n_ex = [], [], [], Counter(), Counter()
    for d in full["datasets"]:
        per[d["dataset"]] += 0
        for ex in d["examples"]:
            n_ex[d["dataset"]] += 1
            for fld in ("output", "input"):
                v = ex.get(fld)
                if isinstance(v, str) and ("def " in v or "class " in v) and len(v) < 20000:
                    s = shingles(v)
                    if len(s) >= 5:
                        sets.append(s)
                        src.append(d["dataset"])
                        codes.append(v)
                        per[d["dataset"]] += 1
                    break
    del full
    return sets, src, codes, dict(per), dict(n_ex)


def nearest(progs: dict[str, str], top: int = 3) -> tuple[dict[str, list[tuple[float, int]]], dict[str, Any]]:
    os.environ.setdefault("PYTHONHASHSEED", "0")
    shas = sorted(progs)
    sets, src, codes, per, n_ex = corpus()
    if not shas:
        return {}, {"corpus_code_solutions_per_dataset": per, "examples_per_dataset": n_ex, "n_corpus": len(sets),
                    "src": src, "codes": codes}
    P = matrix([shingles(progs[s]) for s in shas])
    C = matrix(sets)
    inter = (P @ C.T).tocsr()
    pn = np.asarray(P.sum(1)).ravel()
    cn = np.asarray(C.sum(1)).ravel()
    best: dict[str, list[tuple[float, int]]] = {}
    for i, s in enumerate(shas):
        row = inter.getrow(i)
        if row.nnz == 0:
            best[s] = []
            continue
        j = row.indices
        jac = row.data / (pn[i] + cn[j] - row.data)
        order = np.argsort(-jac)[:top]
        best[s] = [(float(jac[o]), int(j[o])) for o in order]
    return best, {"corpus_code_solutions_per_dataset": per, "examples_per_dataset": n_ex, "n_corpus": len(sets),
                  "src": src, "codes": codes}


# ------------------------------------------------------------------------------------------------ judges
def task_spec(task: str) -> str:
    for line in open(K.V22 / "prompts" / "prompts4.jsonl"):
        r = json.loads(line)
        if r["kind"] == "twin" and r["task"] == task and r["template_id"] == "W1":
            txt = r["user_text"]
            return txt[txt.find("Task:"):]
    return ""


def catalogue_text(task: str) -> str:
    if task in ("T1", "T2"):
        import cfg4
        return "; ".join(f"{m} ({v[0]})" for m, v in cfg4.PATH_CATALOGUE[task].items())
    sys.path.insert(0, str(K.V22 / "inputs" / "exp11"))
    from bench.common.catalogue import TASKS
    return "; ".join(f"{m} ({v[0]}: {v[1]})" for m, v in TASKS[task]["modes"].items())


PROMPT = """You are auditing whether a Python program uses a genuinely new algorithm for a task.

TASK:
{spec}

KNOWN CATALOGUE OF ALGORITHMS FOR THIS TASK (label: description):
{cat}

THE 3 MOST SIMILAR KNOWN SOLUTIONS FROM A PUBLIC CORPUS (token-shingle Jaccard similarity in brackets):
{near}

PROGRAM TO AUDIT (it passes the hidden tests):
```python
{code}
```

Classify the PROGRAM's algorithmic mechanism into exactly one class:
- LABELLER_MISS: it is one of the catalogue algorithms (name which one).
- CATALOGUE_VARIANT: a recognisable variant/combination of catalogue algorithms or a standard textbook technique not in the catalogue (name it).
- NOVEL: a mechanism not in the catalogue and not a standard known technique.
- DEGENERATE: trivial, hard-coded, library call that hides the algorithm, or not really solving the task.
Answer with ONE line of JSON only: {{"class": "<LABELLER_MISS|CATALOGUE_VARIANT|NOVEL|DEGENERATE>", "name": "<algorithm name>", "reason": "<one sentence>"}}"""


class Ledger:
    def __init__(self) -> None:
        self.d = read_json(LEDGER) if LEDGER.exists() else {"total_usd": 0.0, "n_calls": 0, "refusals": 0}
        self.stop = False

    def add(self, cost: float) -> None:
        self.d["total_usd"] += float(cost or 0.0)
        self.d["n_calls"] += 1
        write_json(LEDGER, self.d)


async def _call(client, sem, ledger: Ledger, model: str, prompt: str) -> dict[str, Any] | None:
    async with sem:
        if ledger.stop or ledger.d["total_usd"] >= CAP_USD:
            return None
        try:
            r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                     temperature=0.0, max_tokens=200, extra_body={"usage": {"include": True}})
        except Exception as e:  # noqa: BLE001 - classify budget refusals, log others
            msg = str(e)
            if BUDGET_MSG in msg:
                ledger.stop = True
                ledger.d["refusals"] += 1
                logger.error("OpenRouter budget refusal: stopping the novelty batch")
            else:
                logger.error(f"judge call failed ({model}): {msg[:200]}")
            return None
        cost = getattr(r, "usage", None)
        c = 0.0
        if cost is not None:
            c = float(getattr(cost, "cost", 0.0) or (cost.model_extra or {}).get("cost", 0.0) or 0.0)
        ledger.add(c)
        txt = (r.choices[0].message.content or "").strip()
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            out = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            out = {}
        cls = str(out.get("class", "")).upper()
        return {"model": model, "class": cls if cls in CLASSES else "UNPARSED", "name": out.get("name"),
                "reason": str(out.get("reason", ""))[:300], "raw": txt[:400], "cost": c}


async def judge_all(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                         timeout=120)
    sem = asyncio.Semaphore(8)
    ledger = Ledger()
    first = await asyncio.gather(*[asyncio.gather(*[_call(client, sem, ledger, m, it["prompt"]) for m in JUDGES])
                                   for it in items])
    for it, js in zip(items, first):
        it["judges"] = [j for j in js if j]
    tie = [it for it in items if len(it["judges"]) == 2 and it["judges"][0]["class"] != it["judges"][1]["class"]]
    third = await asyncio.gather(*[_call(client, sem, ledger, TIE_JUDGE, it["prompt"]) for it in tie])
    for it, j in zip(tie, third):
        if j:
            it["judges"].append(j)
    for it in items:
        cs = Counter(j["class"] for j in it["judges"] if j["class"] in CLASSES)
        top = cs.most_common(1)
        it["judge_class"] = top[0][0] if top and top[0][1] >= 2 else ("disputed" if it["judges"] else "unaudited")
    await client.close()
    return items


# ------------------------------------------------------------------------------------------------ main
def rows_used() -> list[dict[str, Any]]:
    labs = {l["key"]: l for l in read_jsonl(LABELS)}
    s3 = read_json(RESULTS / "s3_prices.json") if (RESULTS / "s3_prices.json").exists() else None
    used_e27 = set()
    if s3:
        for t, d in s3["knob_sources"].items():
            for knob, arm in d.items():
                if arm.startswith("E27:"):
                    used_e27.add((t, arm))
    out = []
    for name in ("raw_k.jsonl", "knobs_norm.jsonl", "reuse_exp27.jsonl"):
        for r in read_jsonl(K.RAW_DIR / name):
            if name == "reuse_exp27.jsonl" and (r["task"], r["arm"]) not in used_e27:
                continue
            l = labs.get(K.row_key(r))
            if l and l.get("code"):
                out.append({"task": r["task"], "arm": r["arm"], "template": r["template"], "k": int(r["sample_id"]),
                            "label": l["label"], "passed": bool(l.get("passed")), "code": l["code"],
                            "runtime_label": l.get("runtime_label"), "ast_label": l.get("ast_label"),
                            "source": name})
    return out


def family(arm: str) -> str:
    a = arm.replace("E27:", "")
    return a.split("_a")[0] if re.match(r"^(D\d|P[A-Z]+)_a", a) else a


def reapply_manual() -> None:
    """Re-apply results/novelty_manual.json to an existing audit without calling the judges again."""
    out = read_json(RESULTS / "novelty_audit.json")
    manual = read_json(RESULTS / "novelty_manual.json") if (RESULTS / "novelty_manual.json").exists() else {}
    for it in out["items"]:
        it["manual_class"] = manual.get(it["sha"])
        it["final_class"] = it["manual_class"] or it["judge_class"]
    out["audit_classes"] = dict(Counter(i["final_class"] for i in out["items"] if i["kind"] == "audit"))
    out["n_novel"] = sum(1 for i in out["items"] if i["kind"] == "audit" and i["final_class"] == "NOVEL")
    out["manual_note"] = manual.get("_note")
    write_json(RESULTS / "novelty_audit.json", out)
    logger.info(f"manual classes re-applied: {out['audit_classes']}")


@logger.catch(reraise=True)
def main() -> None:
    K.setup_logging("novelty_k")
    if "--manual-only" in sys.argv:
        reapply_manual()
        return
    rows = rows_used()
    other = {}
    for r in rows:
        if r["passed"] and r["label"] == "other":
            other.setdefault(sha256_text(r["code"]), r)
    offd = defaultdict(dict)
    for r in rows:
        if r["passed"] and r["label"] not in (DEFAULTS[r["task"]], "invalid", "disputed", "unknown"):
            offd[(r["task"], family(r["arm"]))][sha256_text(r["code"])] = r
    progs = {s: r["code"] for s, r in other.items()}
    for d in offd.values():
        for s, r in d.items():
            progs[s] = r["code"]
    best, meta = nearest(progs)
    src, codes = meta.pop("src"), meta.pop("codes")
    # controls: 10 correct programs with runtime == AST label (known class), spread over tasks
    ctrl = []
    by_task = defaultdict(list)
    for r in rows:
        if r["passed"] and r["runtime_label"] and r["runtime_label"] == r["ast_label"] and r["label"] != "other":
            by_task[r["task"]].append(r)
    for t in K.D5_TASKS:
        seen = set()
        for r in by_task.get(t, []):
            if r["label"] not in seen and len([c for c in ctrl if c["task"] == t]) < 2:
                seen.add(r["label"])
                ctrl.append(r)
    ctrl = ctrl[:10]
    items = []
    for kind, lst in (("audit", list(other.items())), ("control", [(sha256_text(c["code"]), c) for c in ctrl])):
        for s, r in lst:
            nb = best.get(s) or nearest({s: r["code"]})[0].get(s, [])
            near = "\n".join(f"[{j:.2f}] ({src[i]})\n{codes[i][:1200]}" for j, i in nb[:3]) or "(none found)"
            items.append({"kind": kind, "sha": s[:16], "task": r["task"], "arm": r["arm"], "label": r["label"],
                          "nearest": [{"jaccard": j, "dataset": src[i]} for j, i in nb[:3]],
                          "prompt": PROMPT.format(spec=task_spec(r["task"]), cat=catalogue_text(r["task"]),
                                                  near=near, code=r["code"][:4000]), "code": r["code"]})
    logger.info(f"novelty audit: {sum(i['kind'] == 'audit' for i in items)} correct 'other' programs, "
                f"{sum(i['kind'] == 'control' for i in items)} controls")
    if items:
        items = asyncio.run(judge_all(items))
    manual = read_json(RESULTS / "novelty_manual.json") if (RESULTS / "novelty_manual.json").exists() else {}
    for it in items:
        it["manual_class"] = manual.get(it["sha"])
        it["final_class"] = it["manual_class"] or it["judge_class"]
        it.pop("prompt", None)
    ctrl_items = [i for i in items if i["kind"] == "control"]
    ctrl_acc = [i["judge_class"] == "LABELLER_MISS" for i in ctrl_items if i["judge_class"] not in ("unaudited",)]
    desc = {}
    for (t, f), d in sorted(offd.items()):
        js = [best[s][0][0] if best.get(s) else 0.0 for s in d]
        cls = Counter("KNOWN-CLOSE" if j >= 0.5 else ("VARIANT" if j >= 0.25 else "DISTANT") for j in js)
        desc[f"{t}|{f}"] = {"n_distinct_correct_off_default": len(d), "median_max_jaccard": float(np.median(js)),
                            "classes": dict(cls), "labels": dict(Counter(r["label"] for r in d.values()))}
    out = {"utc": K.utc_now(), **meta, "judges": list(JUDGES), "tie_judge": TIE_JUDGE,
           "n_audited": sum(i["kind"] == "audit" for i in items),
           "audit_classes": dict(Counter(i["final_class"] for i in items if i["kind"] == "audit")),
           "n_novel": sum(1 for i in items if i["kind"] == "audit" and i["final_class"] == "NOVEL"),
           "controls_judged_as_catalogue": f"{sum(ctrl_acc)}/{len(ctrl_acc)}",
           "items": [{k: v for k, v in i.items() if k != "code"} for i in items],
           "nearest_known_descriptive": desc,
           "costs": read_json(LEDGER) if LEDGER.exists() else {"total_usd": 0.0}}
    write_json(RESULTS / "novelty_audit.json", out)
    write_json(RESULTS / "novelty_programs.json", [{"sha": i["sha"], "task": i["task"], "arm": i["arm"],
                                                   "kind": i["kind"], "code": i["code"]} for i in items])
    logger.info(f"novelty: {out['audit_classes']}; controls {out['controls_judged_as_catalogue']}; "
                f"cost {out['costs']}")


if __name__ == "__main__":
    main()
