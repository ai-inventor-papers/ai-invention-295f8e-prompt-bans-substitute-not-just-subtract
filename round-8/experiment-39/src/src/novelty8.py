#!/usr/bin/env python3
"""Stage 5: novelty audit of every CORRECT 'other' program (all stages) and adjudication of cells with > 20% 'other'.

Known-solution corpus: every code-bearing field of all ten datasets of the declared dependency art_j3Rm_lr2nzR6
(full_data_out.json: LeetCode references, Mercury, TheAlgorithms, KodCode, XLCoST, HumanEval+, ENAMEL, CLRS traces...)
plus iteration-3 exp18 known_solutions_summary.json when it carries code. Retrieval: identifier-normalised token
4-gram Jaccard prefilter (top 40), then Zhang-Shasha tree edit distance (zss) between identifier-normalised ASTs;
the 3 nearest are shown to the judges. Judges (blind to arm): deepseek/deepseek-chat-v3.1 and google/gemini-2.5-flash,
each gated on 10 controls of known class; moonshotai/kimi-k2 breaks disagreements. A manual read (results/
manual_reads.json, written by the analyst after reading every audited program) gives the final class; if no judge
passes its gate the manual read plus an arm-blind rule replication decides.
Usage: novelty8.py index | audit | adjudicate
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import pickle
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (BUDGET_MSG, CACHE_DIR, CONT_LABELS, CONTS, DEP_DIR, INPUTS, JUDGE_CAP_USD, LABELS,  # noqa: E402
                  RESULTS_DIR, SAMPLES, THRESH, UNITS, label_task, read_json, read_jsonl, setup_logging, utc_now,
                  write_json)
import analysis_k1 as AK  # noqa: E402

KNOWN = CACHE_DIR / "known_index.pkl"
JUDGES = ["deepseek/deepseek-chat-v3.1", "google/gemini-2.5-flash"]
TIEBREAK = "moonshotai/kimi-k2"
CLASSES = ["NOVEL ALGORITHM", "KNOWN OUTSIDE CATALOGUE", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
SPEND = {"usd": 0.0, "calls": 0, "stopped": False}


# ------------------------------------------------------------------------------------------------ AST utils
def norm_ast(code: str) -> ast.AST | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        for f in ("id", "arg", "name", "attr"):
            if hasattr(node, f) and isinstance(getattr(node, f), str):
                setattr(node, f, "_")
    return tree


def zss_tree(tree: ast.AST):
    import zss
    def build(n: ast.AST) -> Any:
        node = zss.Node(type(n).__name__)
        for c in ast.iter_child_nodes(n):
            node.addkid(build(c))
        return node
    return build(tree)


def tree_size(tree: ast.AST) -> int:
    return sum(1 for _ in ast.walk(tree))


def grams(code: str) -> set:
    t = AK.norm_tokens(code)
    return {tuple(t[i:i + 4]) for i in range(max(len(t) - 3, 0))}


def extract_code(text: str) -> str | None:
    m = re.search(r"```[^\n]*\n(.*?)```", text, re.S)
    code = m.group(1) if m else text
    return code if ("def " in code or "class " in code) else None


# ------------------------------------------------------------------------------------------------ index
def build_index() -> None:
    p = DEP_DIR / "full_data_out.json"
    logger.info(f"loading dependency {p.name} ({p.stat().st_size / 1e6:.0f} MB)")
    data = json.loads(p.read_text())
    out = []
    for ds in data["datasets"]:
        n0 = len(out)
        for i, ex in enumerate(ds["examples"]):
            for field in ("output", "input"):
                v = ex.get(field)
                if isinstance(v, str) and len(v) < 20000:
                    code = extract_code(v) if "```" in v else (v if ("def " in v and "\n" in v) else None)
                    if code and norm_ast(code) is not None:
                        out.append({"ds": ds["dataset"], "i": i, "field": field,
                                    "task": ex.get("metadata_bench_task") or ex.get("metadata_task_slug")
                                    or ex.get("metadata_slug"), "code": code})
                        break
        logger.info(f"  {ds['dataset']}: {len(out) - n0} code entries")
    del data
    e18 = INPUTS / "iter3_exp18" / "results" / "known_solutions_summary.json"
    if e18.exists():
        try:
            j = read_json(e18)
            items = j if isinstance(j, list) else j.get("solutions", j.get("items", []))
            for it in items if isinstance(items, list) else []:
                c = it.get("code") if isinstance(it, dict) else None
                if c and norm_ast(c) is not None:
                    out.append({"ds": "iter3_exp18", "i": len(out), "field": "code", "task": it.get("task"),
                                "code": c})
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"exp18 summary unreadable: {e}")
    for o in out:
        o["grams"] = grams(o["code"])
    with open(KNOWN, "wb") as fh:
        pickle.dump(out, fh)
    write_json(RESULTS_DIR / "known_index_summary.json", {"n": len(out), "by_dataset": dict(Counter(o["ds"] for o in out)),
                                                          "utc": utc_now()})
    logger.info(f"known index: {len(out)} solutions")


def nearest(code: str, known: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    import zss
    g = grams(code)
    sims = []
    for j, o in enumerate(known):
        u = len(g | o["grams"])
        sims.append((len(g & o["grams"]) / u if u else 0.0, j))
    sims.sort(reverse=True)
    t0 = norm_ast(code)
    if t0 is None:
        return []
    z0 = zss_tree(t0)
    cand = []
    if tree_size(t0) > 600:
        return [{"dist": None, "jaccard4": round(s_, 3), "ds": known[j]["ds"], "task": known[j]["task"],
                 "code": known[j]["code"][:1800]} for s_, j in sims[:k]]
    for s, j in sims[:8]:
        t1 = norm_ast(known[j]["code"])
        if t1 is None or tree_size(t1) > 600:
            continue
        d = zss.simple_distance(z0, zss_tree(t1))
        cand.append({"dist": int(d), "jaccard4": round(s, 3), "ds": known[j]["ds"], "task": known[j]["task"],
                     "code": known[j]["code"][:1800]})
    return sorted(cand, key=lambda c: c["dist"])[:k]


# ------------------------------------------------------------------------------------------------ judges
PROMPT = """You audit whether a correct Python program for a coding task uses a NOVEL algorithm.
Task: {task}
Catalogue of known algorithms for this task: {catalogue}
Program under audit:
```python
{code}
```
The three most similar known solutions from public corpora:
{near}
Classify the program's algorithm as exactly one of:
NOVEL ALGORITHM / KNOWN OUTSIDE CATALOGUE / CATALOGUE VARIANT / LABELLER MISS / DEGENERATE
(LABELLER MISS = it is plainly one of the catalogue algorithms; CATALOGUE VARIANT = a variant of a catalogue algorithm;
KNOWN OUTSIDE CATALOGUE = a named, published technique not in the catalogue; DEGENERATE = hard-coded or trivial.)
Answer with one JSON object: {{"class": "...", "name": "<algorithm or technique name>", "reason": "<one sentence>"}}"""


JCACHE = CACHE_DIR / "judge_cache.jsonl"
_JC: dict[str, dict[str, Any]] = {}


def _jkey(model: str, prompt: str) -> str:
    import hashlib
    return hashlib.sha256((model + "\n" + prompt).encode()).hexdigest()


async def call(session: Any, model: str, prompt: str) -> dict[str, Any]:
    if not _JC and JCACHE.exists():
        for r in read_jsonl(JCACHE):
            _JC[r["key"]] = r["res"]
    k = _jkey(model, prompt)
    if k in _JC:
        return _JC[k]
    res = await _call(session, model, prompt)
    if "error" not in res:
        _JC[k] = res
        with open(JCACHE, "a") as fh:
            fh.write(json.dumps({"key": k, "model": model, "res": res}) + "\n")
    return res


async def _call(session: Any, model: str, prompt: str) -> dict[str, Any]:
    if SPEND["stopped"] or SPEND["usd"] >= JUDGE_CAP_USD:
        return {"error": "budget_stop"}
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 300,
            "usage": {"include": True}}
    import aiohttp
    for attempt in range(3):
        try:
            async with session.post(url, json=body, headers=hdr, timeout=aiohttp.ClientTimeout(total=90)) as r:
                txt = await r.text()
                if r.status == 403 and BUDGET_MSG in txt:
                    SPEND["stopped"] = True
                    return {"error": "budget_403"}
                if r.status != 200:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                j = json.loads(txt)
                SPEND["usd"] += float((j.get("usage") or {}).get("cost") or 0.0)
                SPEND["calls"] += 1
                out = j["choices"][0]["message"].get("content") or ""
                if not out.strip():
                    await asyncio.sleep(1)
                    continue
                logger.debug(f"judge {model}: {out[:200]}")
                m = re.search(r"\{.*\}", out, re.S)
                res = json.loads(m.group(0)) if m else {"class": None}
                cl = str(res.get("class", "")).upper()
                res["class"] = next((c for c in CLASSES if c in cl), None)
                return res
        except (asyncio.TimeoutError, json.JSONDecodeError, KeyError, TypeError, IndexError) as e:
            logger.warning(f"judge call failed ({model}): {e}")
            await asyncio.sleep(2)
    return {"error": "failed"}


def family(c: str | None) -> str | None:
    if c in ("LABELLER MISS", "CATALOGUE VARIANT"):
        return "catalogue"
    return {"NOVEL ALGORITHM": "novel", "KNOWN OUTSIDE CATALOGUE": "known_outside", "DEGENERATE": "degenerate"}.get(c)


def controls() -> list[dict[str, Any]]:
    """10 controls of known class: 6 correct catalogue programs (twins), 2 known-outside-catalogue programs written
    here (named techniques absent from the catalogue) and 2 degenerate hard-coded programs."""
    rows = read_jsonl(SAMPLES)
    labels = {r["sid"]: r for r in read_jsonl(LABELS)}
    out = []
    for u in ("B3", "T10", "A3", "B6", "G", "T1"):
        r = next((x for x in rows if x["unit"] == u and x["arm"] == "A0" and labels.get(x["sid"], {}).get("passed")
                  and labels[x["sid"]]["label"] in UNITS[u]["catalogue"]), None)
        if r:
            out.append({"unit": u, "code": labels[r["sid"]]["code"], "want": "catalogue"})
    out.append({"unit": "B6", "want": "known_outside", "code":
                "def solve(s, t):\n    if len(s) != len(t):\n        return False\n    P = [2,3,5,7,11,13,17,19,23,29,31,"
                "37,41,43,47,53,59,61,67,71,73,79,83,89,97,101]\n    M = (1 << 61) - 1\n    a = b = 1\n    for x, y in "
                "zip(s, t):\n        a = a * P[ord(x) - 97] % M\n        b = b * P[ord(y) - 97] % M\n    return a == b\n"})
    out.append({"unit": "T10", "want": "known_outside", "code":
                "def solve(n, edges):\n    # Laplacian rank: components = n - rank(L)\n    import numpy as np\n"
                "    L = np.zeros((n, n))\n    for u, v in edges:\n        L[u][u] += 1; L[v][v] += 1\n"
                "        L[u][v] -= 1; L[v][u] -= 1\n    return int(n - np.linalg.matrix_rank(L))\n"})
    out.append({"unit": "B3", "want": "degenerate", "code": "def solve(n, roads):\n    return 0\n"})
    out.append({"unit": "A3", "want": "degenerate", "code": "def solve(height):\n    return 6 if height else 0\n"})
    return out[:10]


async def judge_all(items: list[dict[str, Any]], ctrl: list[dict[str, Any]]) -> dict[str, Any]:
    import aiohttp
    sem = asyncio.Semaphore(8)
    async with aiohttp.ClientSession() as session:
        async def one(model: str, it: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                if SPEND["stopped"]:
                    return {"error": "budget_stop"}
                u = it["unit"]
                near = "\n".join(f"[{i + 1}] ({n['ds']}, AST edit distance {n['dist']})\n{n['code'][:900]}"
                                 for i, n in enumerate(it.get("nearest", []))) or "(none)"
                pr = PROMPT.format(task=UNITS[u]["task"], catalogue=", ".join(UNITS[u]["catalogue"]),
                                   code=(it["code"] or "")[:3000], near=near)
                return await call(session, model, pr)
        res: dict[str, Any] = {"controls": {}, "items": {}}
        for m in JUDGES:
            res["controls"][m] = await asyncio.gather(*[one(m, c) for c in ctrl])
        gate = {m: sum(family(r.get("class")) == c["want"] for r, c in zip(res["controls"][m], ctrl))
                for m in JUDGES}
        res["gate"] = {m: {"correct": g, "n": len(ctrl), "pass": g >= 8} for m, g in gate.items()}
        for m in JUDGES:
            res["items"][m] = await asyncio.gather(*[one(m, it) for it in items])
        dis = [i for i, it in enumerate(items) if family(res["items"][JUDGES[0]][i].get("class")) !=
               family(res["items"][JUDGES[1]][i].get("class"))]
        res["tiebreak"] = {}
        if dis:
            tb = await asyncio.gather(*[one(TIEBREAK, items[i]) for i in dis])
            res["tiebreak"] = {str(i): t for i, t in zip(dis, tb)}
    return res


def audit() -> dict[str, Any]:
    labels = {r["sid"]: r for r in read_jsonl(LABELS)}
    labels.update({r["sid"]: r for r in read_jsonl(CONT_LABELS)})
    adj_p = RESULTS_DIR / "adjudicated_labels.json"
    adj = read_json(adj_p) if adj_p.exists() else {}
    items = []
    for src in (SAMPLES, CONTS):
        for r in read_jsonl(src):
            L = labels.get(r["sid"])
            if not L or not L.get("passed") or L.get("labeller_source") == "oc_partial":
                continue
            u = r["unit"]
            manual_p = RESULTS_DIR / "manual_reads.json"
            manual_sids = read_json(manual_p) if manual_p.exists() else {}
            if r["sid"] not in manual_sids and (adj.get(r["sid"]) or AK.cls(u, L.get("label"))) != "other":
                continue
            items.append({"sid": r["sid"], "unit": u, "arm": r.get("arm"), "label": L.get("label"),
                          "labeller_source": L.get("labeller_source"), "code": L.get("code")})
    # deduplicate identical programs (keep all sids)
    by_code: dict[str, dict[str, Any]] = {}
    for it in items:
        key = re.sub(r"\s+", " ", it["code"] or "")
        if key in by_code:
            by_code[key]["sids"].append(it["sid"])
        else:
            by_code[key] = {**it, "sids": [it["sid"]]}
    uniq = list(by_code.values())
    logger.info(f"correct 'other' programs: {len(items)} ({len(uniq)} distinct)")
    known = pickle.load(open(KNOWN, "rb")) if KNOWN.exists() else []
    for it in uniq:
        it["nearest"] = nearest(it["code"] or "", known) if known else []
    ctrl = controls()
    jres = asyncio.run(judge_all(uniq, ctrl)) if uniq or ctrl else {}
    manual = read_json(RESULTS_DIR / "manual_reads.json") if (RESULTS_DIR / "manual_reads.json").exists() else {}
    final = []
    for i, it in enumerate(uniq):
        js = [jres["items"][m][i] for m in JUDGES] if jres else []
        tb = jres.get("tiebreak", {}).get(str(i)) if jres else None
        mr = manual.get(it["sid"])
        final.append({"sid": it["sid"], "sids": it["sids"], "unit": it["unit"], "arm": it["arm"],
                      "label": it["label"], "judges": js, "tiebreak": tb, "manual_read": mr,
                      "nearest": [{k: v for k, v in n.items() if k != "code"} for n in it["nearest"]],
                      "final_class": (mr or {}).get("class") or (family(js[0].get("class")) if js else None),
                      "code": it["code"]})
    n_novel = sum(1 for f in final if (f["manual_read"] or {}).get("class") == "NOVEL ALGORITHM")
    out = {"utc": utc_now(), "n_correct_other": len(items), "n_distinct": len(uniq), "items": final,
           "judge_gate": jres.get("gate") if jres else None,
           "control_answers": {m: [r.get("class") for r in jres["controls"][m]] for m in JUDGES} if jres else None,
           "control_wants": [c["want"] for c in ctrl], "spend_usd": SPEND["usd"], "calls": SPEND["calls"],
           "budget_stopped": SPEND["stopped"], "n_novel_manual": n_novel,
           "rule_of_three_upper_95": (3.0 / len(items)) if items else None}
    write_json(RESULTS_DIR / "novelty_audit.json", out)
    ledger("novelty_audit")
    return out




def ledger(what: str) -> None:
    """Append this process's OpenRouter spend to results/openrouter_ledger.jsonl (summed in results/costs.json)."""
    with open(RESULTS_DIR / "openrouter_ledger.jsonl", "a") as fh:
        fh.write(json.dumps({"utc": utc_now(), "what": what, "usd": SPEND["usd"], "calls": SPEND["calls"]}) + "\n")


# ------------------------------------------------------------------------------------------------ adjudication
ADJ_PROMPT = """Which algorithm does this Python program implement for the task "{task}"?
Choose exactly one label from this list: {labels}, or "other" if none fits.
Judge the algorithm by its control flow (e.g. a FIFO queue expanded level by level is bfs even if it is slow or wrong).
```python
{code}
```
Answer with one JSON object: {{"label": "<one label from the list or other>", "reason": "<one sentence>"}}"""


async def _adjudicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import aiohttp
    sem = asyncio.Semaphore(8)
    async with aiohttp.ClientSession() as session:
        async def one(model: str, it: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                u = it["unit"]
                pr = ADJ_PROMPT.format(task=UNITS[u]["task"], labels=", ".join(UNITS[u]["catalogue"]),
                                       code=(it["code"] or "")[:3500])
                r = await call(session, model, pr)
                lab = str(r.get("label", "")).strip().lower() if isinstance(r, dict) else ""
                return {"label": lab if lab in UNITS[u]["catalogue"] else ("other" if lab else None),
                        "reason": r.get("reason") if isinstance(r, dict) else None}
        a = await asyncio.gather(*[one(JUDGES[0], it) for it in items])
        b = await asyncio.gather(*[one(JUDGES[1], it) for it in items])
        dis = [i for i in range(len(items)) if a[i]["label"] != b[i]["label"]]
        t = await asyncio.gather(*[one(TIEBREAK, items[i]) for i in dis])
        tb = dict(zip(dis, t))
    out = []
    for i, it in enumerate(items):
        if a[i]["label"] == b[i]["label"] and a[i]["label"]:
            fin, how = a[i]["label"], "two judges agree"
        elif i in tb and tb[i]["label"] in (a[i]["label"], b[i]["label"]):
            fin, how = tb[i]["label"], "tiebreak"
        else:
            fin, how = None, "unresolved"
        out.append({**{k: it[k] for k in ("sid", "unit", "label", "labeller_source", "runtime_label", "ast_label")},
                    "judge_a": a[i], "judge_b": b[i], "tiebreak": tb.get(i), "final": fin, "how": how})
    return out


SKIP_MAP_UNITS = {"T1"}       # T1 failed validation (boundary unit): its token map feeds no prediction


def adjudicate() -> dict[str, Any]:
    """Every sample row whose frozen label is 'disputed' or comes from an unresolved runtime/AST disagreement."""
    lab = {r["sid"]: r for r in read_jsonl(LABELS)}
    lab.update({r["sid"]: r for r in read_jsonl(CONT_LABELS)})
    items = []
    for r in read_jsonl(SAMPLES) + [c for c in read_jsonl(CONTS) if c.get("arm") in ("MAP", "HR")]:
        L = lab.get(r["sid"])
        if not L or (r.get("stage") not in ("S0", "S3") and r.get("arm") not in ("MAP", "HR")):
            continue
        src = str(L.get("labeller_source") or "")
        if r.get("arm") in ("MAP", "HR") and r["unit"] in SKIP_MAP_UNITS:
            continue
        if L.get("label") == "disputed" or "unjudged" in src or src == "disagree":
            items.append({"sid": r["sid"], "unit": r["unit"], "label": L.get("label"), "labeller_source": src,
                          "runtime_label": L.get("runtime_label"), "ast_label": L.get("ast_label"),
                          "code": L.get("code")})
    res = asyncio.run(_adjudicate(items)) if items else []
    prev_p = RESULTS_DIR / "adjudicated_labels.json"
    mapping = read_json(prev_p) if prev_p.exists() else {}
    mapping.update({x["sid"]: x["final"] for x in res if x["final"]})
    write_json(RESULTS_DIR / "adjudicated_labels.json", mapping)
    out = {"utc": utc_now(), "n_items": len(items), "n_resolved": len(mapping), "spend_usd": SPEND["usd"],
           "items": res, "by_unit": dict(Counter(x["unit"] for x in res)),
           "changes": dict(Counter(f"{x['unit']}:{x['label']}->{x['final']}" for x in res))}
    write_json(RESULTS_DIR / "adjudication.json", out)
    ledger("adjudicate")
    return out


if __name__ == "__main__":
    setup_logging("novelty8")
    cmd = sys.argv[1]
    if cmd == "index":
        build_index()
    elif cmd == "audit":
        r = audit()
        print(json.dumps({k: v for k, v in r.items() if k != "items"}, indent=1, default=str))
    elif cmd == "adjudicate":
        r = adjudicate()
        print(json.dumps({k: v for k, v in r.items() if k != "items"}, indent=1, default=str))
