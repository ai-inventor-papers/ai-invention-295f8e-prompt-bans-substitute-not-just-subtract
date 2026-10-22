#!/usr/bin/env python3
"""Blind judges (labeller disagreements only) and the Part G novelty audit, plus the dependency extract.

dep     scan ALL ten datasets of art_j3Rm_lr2nzR6 (full_data_out.json) for rows relevant to the three mixed units
        (LeetCode 42 / 242 / MST problems, rain water / anagram / spanning-tree programs) -> inputs/dep_extract.json
judge   every 'disputed' program (runtime and AST labellers disagree) -> two blind judges from different families
        (google/gemini-2.5-flash-lite, mistralai/mistral-small-3.2-24b-instruct, T 0) + deepseek on disagreement ->
        data/judge_labels.jsonl (majority label, else stays disputed)
audit   every CORRECT program labelled 'other' (all arms, incl. continuations completed to the fence): nearest known
        solutions (token-shingle Jaccard + AST 4-gram distance over unit references, the dependency extract and the
        iteration-6 known-solution pool), two blind judges with 10 controls of known class, a third on disagreement
        -> results/novelty_audit.json (manual class filled from the read: NOVEL ALGORITHM / CATALOGUE VARIANT /
        LABELLER MISS / DEGENERATE)
Spending: GET <base_url>/key at the start, running total of usage.cost, hard cap JUDGE_CAP_USD, stop at the first
HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget'.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg7 import (BUDGET_MSG, DATA_DIR, DEP_DIR, E25, E26, INPUTS, JUDGE_CAP_USD, LABELS, RESULTS_DIR,  # noqa: E402
                  SAMPLES_RAW, UNITS, append_jsonl, read_json, read_jsonl, setup_logging, utc_now, write_json)

JUDGES = ("google/gemini-2.5-flash-lite", "mistralai/mistral-small-3.2-24b-instruct")
TIEBREAK = "deepseek/deepseek-chat-v3.1"
COSTS = RESULTS_DIR / "costs.json"
STATE = {"spent": 0.0, "stop": False, "calls": 0}

SPEC = {"B3": "minimum total cost of roads linking all n cities (minimum spanning tree weight), -1 if impossible",
        "A3": "total rain water trapped between bars of the given heights",
        "B6": "whether t is a rearrangement (anagram) of s"}
MECH = {
    "B3": {"kruskal": "take roads in increasing cost (sorted or from a heap of all roads) and keep a road when it joins "
                      "two different components (union-find)",
           "prim_heap": "grow one component from a start city, adding the cheapest road leaving it, found with a heap",
           "prim_array": "grow one component, keeping the cheapest known cost per city in an array and scanning all "
                         "cities each round (O(n^2))",
           "boruvka": "in rounds, add the cheapest road leaving every component"},
    "A3": {"two_pointers": "move a left and a right index inward with running maxima on each side",
           "prefix_suffix_max": "precompute left-maximum and right-maximum arrays, then sum min(left, right) - h",
           "monotonic_stack": "a stack of indices with decreasing heights, popping to fill bounded basins",
           "peak_split": "split at the highest bar and sweep from each end towards it"},
    "B6": {"sort_compare": "sort the letters of both strings and compare",
           "hash_count": "count letters in a dict or Counter and compare or decrement",
           "fixed_count_array": "26 integer counters indexed by ord(c) - ord('a')"},
}


# ------------------------------------------------------------------------------------------------ dependency
def dep_extract() -> dict[str, Any]:
    p = DEP_DIR / "full_data_out.json"
    out_p = INPUTS / "dep_extract.json"
    if out_p.exists():
        return read_json(out_p)
    d = json.loads(p.read_text())
    pats = {"A3": re.compile(r"trap(ping)?[\s_-]*rain|rain\s*water|trapped water", re.I),
            "B6": re.compile(r"anagram", re.I),
            "B3": re.compile(r"spanning tree|kruskal|\bprim'?s?\b|min[_ ]?cost[_ ]?to[_ ]?connect|connecting cities",
                             re.I)}
    qids = {"A3": {42}, "B6": {242}, "B3": {1135, 1584, 1168}}
    rows, per_ds = [], {}
    for ds in d["datasets"]:
        n_hit = 0
        for e in ds["examples"]:
            txt = (e.get("input") or "")[:3000] + "\n" + (e.get("output") or "")[:6000]
            qid = e.get("metadata_question_id")
            for u in ("A3", "B6", "B3"):
                hit = (qid is not None and str(qid).isdigit() and int(qid) in qids[u]) or pats[u].search(txt)
                if hit:
                    n_hit += 1
                    rows.append({"unit": u, "dataset": ds["dataset"], "qid": qid, "input": (e.get("input") or "")[:1500],
                                 "code": e.get("output") or ""})
                    break
        per_ds[ds["dataset"]] = {"n_examples": len(ds["examples"]), "n_relevant": n_hit}
    out = {"source": "art_j3Rm_lr2nzR6 full_data_out.json (all ten datasets scanned)", "per_dataset": per_ds,
           "rows": rows, "utc": utc_now()}
    write_json(out_p, out)
    return out


# ------------------------------------------------------------------------------------------------ OpenRouter
def _client():
    from openai import AsyncOpenAI
    return AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                       timeout=90)


async def _call(client, sem, model: str, prompt: str) -> str | None:
    async with sem:
        if STATE["stop"] or STATE["spent"] >= JUDGE_CAP_USD:
            return None
        for attempt in range(3):
            try:
                r = await client.chat.completions.create(model=model, temperature=0,
                                                         messages=[{"role": "user", "content": prompt}],
                                                         max_tokens=300, extra_body={"usage": {"include": True}})
                cost = float(getattr(r, "usage", None) and (getattr(r.usage, "cost", None) or
                                                            (r.usage.model_extra or {}).get("cost") or 0.0) or 0.0)
                STATE["spent"] += cost
                STATE["calls"] += 1
                txt = r.choices[0].message.content or ""
                logger.debug(f"judge {model}: {txt[:200]!r} cost {cost:.6f}")
                return txt
            except Exception as e:  # noqa: BLE001 - budget stop or transient error
                msg = str(e)
                if "403" in msg and BUDGET_MSG in msg:
                    STATE["stop"] = True
                    logger.error("OpenRouter budget exhausted: stopping every judge call")
                    return None
                logger.warning(f"judge call failed ({model}, attempt {attempt}): {msg[:200]}")
                await asyncio.sleep(2 * (attempt + 1))
        return None


def judge_prompt(unit: str, code: str) -> str:
    modes = "\n".join(f"- {m}: {d}" for m, d in MECH[unit].items())
    return (f"You classify the algorithm of a Python program that solves this task: {SPEC[unit]}.\n"
            f"Mechanism catalogue:\n{modes}\n- other: a mechanism not in the catalogue\n\n"
            f"Program:\n```python\n{code[:6000]}\n```\n\nAnswer with exactly one label from "
            f"{list(MECH[unit]) + ['other']} on the first line, then one sentence of reason.")


def parse_label(unit: str, txt: str | None) -> str | None:
    if not txt:
        return None
    first = txt.strip().splitlines()[0].lower()
    for m in sorted(list(MECH[unit]) + ["other"], key=len, reverse=True):
        if m in first:
            return m
    for m in sorted(list(MECH[unit]) + ["other"], key=len, reverse=True):
        if m in txt.lower():
            return m
    return None


async def _adjudicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    client = _client()
    sem = asyncio.Semaphore(8)
    out = []

    async def one(it: dict[str, Any]) -> dict[str, Any]:
        p = judge_prompt(it["unit"], it["code"])
        a, b = await asyncio.gather(_call(client, sem, JUDGES[0], p), _call(client, sem, JUDGES[1], p))
        la, lb = parse_label(it["unit"], a), parse_label(it["unit"], b)
        lc = None
        if la != lb and not STATE["stop"]:
            lc = parse_label(it["unit"], await _call(client, sem, TIEBREAK, p))
        votes = [x for x in (la, lb, lc) if x]
        maj = None
        for v in set(votes):
            if votes.count(v) >= 2:
                maj = v
        return {**{k: v for k, v in it.items() if k != "code"}, "j1": la, "j2": lb, "j3": lc, "label": maj,
                "utc": utc_now()}
    out = await asyncio.gather(*[one(it) for it in items])
    return list(out)


def budget() -> dict[str, Any]:
    import requests
    try:
        r = requests.get(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key",
                         headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]}, timeout=30)
        return r.json().get("data", {})
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def save_costs(tag: str) -> None:
    cur = read_json(COSTS) if COSTS.exists() else {"calls": 0, "usd": 0.0, "by_step": {}}
    cur["by_step"][tag] = cur["by_step"].get(tag, 0.0) + STATE["spent"]
    cur["usd"] = sum(cur["by_step"].values())
    cur["calls"] += STATE["calls"]
    cur["budget_after"] = budget()
    write_json(COSTS, cur)


def judge_disputed() -> dict[str, Any]:
    have = {r["sid"] for r in read_jsonl(DATA_DIR / "judge_labels.jsonl")}
    L = read_jsonl(LABELS)
    items = [{"sid": r["sid"], "unit": r["unit"], "code": r.get("code") or ""} for r in L
             if r["label"] == "disputed" and r["sid"] not in have and r.get("code") and r["unit"] in MECH]
    cl = read_jsonl(DATA_DIR / "continuation_labels.jsonl")
    items += [{"sid": r["sid"], "unit": r["unit"], "code": r.get("code") or ""} for r in cl
              if r["label"] == "disputed" and r["sid"] not in have and r.get("code") and r["unit"] in MECH]
    if not items:
        return {"n": 0}
    logger.info(f"judging {len(items)} disputed programs; budget {budget()}")
    res = asyncio.run(_adjudicate(items))
    append_jsonl(DATA_DIR / "judge_labels.jsonl", res)
    save_costs("judge_disputed")
    return {"n": len(res), "resolved": sum(r["label"] is not None for r in res), "spent": STATE["spent"]}


# ------------------------------------------------------------------------------------------------ novelty audit
def shingles(code: str, k: int = 5) -> set:
    toks = re.findall(r"[A-Za-z_]+|\d+|[^\sA-Za-z_\d]", code or "")
    toks = ["ID" if re.fullmatch(r"[A-Za-z_]+", t) and t not in KEYWORDS else t for t in toks]
    return {tuple(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


KEYWORDS = {"def", "return", "for", "while", "if", "else", "elif", "in", "not", "and", "or", "import", "from",
            "range", "len", "sorted", "sort", "heapq", "heappush", "heappop", "min", "max", "Counter", "dict", "list",
            "set", "append", "pop", "True", "False", "None", "break", "continue", "lambda", "ord", "sum", "zip"}


def known_pool(unit: str) -> list[dict[str, Any]]:
    pool = []
    refs = (E26 / "units" / unit / "references") if unit in ("B3", "B6") else None
    if refs and refs.exists():
        pool += [{"src": f"reference:{f.stem}", "code": f.read_text()} for f in refs.glob("*.py")]
    if unit == "A3":
        import importlib.util
        spec = importlib.util.spec_from_file_location("a3d", E25 / "newbench" / "A3_trapping_rain_water" / "unit_def.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        pool += [{"src": f"reference:{k}", "code": v} for k, v in m.REFERENCES.items()]
    dep = dep_extract()
    pool += [{"src": f"dep:{r['dataset']}:{r.get('qid')}", "code": r["code"]} for r in dep["rows"] if r["unit"] == unit]
    return pool


def nearest(code: str, pool: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    from analysis_T import ast_ngrams, jaccard
    s = shingles(code)
    a = ast_ngrams(code)
    sc = []
    for p in pool:
        js = len(s & shingles(p["code"])) / max(1, len(s | shingles(p["code"])))
        ja = jaccard(a, ast_ngrams(p["code"]))
        sc.append({"src": p["src"], "shingle_jaccard": js, "ast_distance": 1 - ja})
    return sorted(sc, key=lambda x: -x["shingle_jaccard"])[:k]


def audit() -> dict[str, Any]:
    from analysis_T import rows_with_labels
    def off_catalogue(u: str, y: str) -> bool:
        return y not in UNITS[u]["catalogue"] and y not in ("invalid", "disputed", "label_error")
    rows = [r for r in rows_with_labels() if r["unit"] in MECH and r["passed"] and off_catalogue(r["unit"], r["label"])]
    cl = {r["sid"]: r for r in read_jsonl(DATA_DIR / "continuation_labels.jsonl")}
    J = {r["sid"]: r["label"] for r in read_jsonl(DATA_DIR / "judge_labels.jsonl") if r.get("label")}
    cont_other = [{"sid": s, "unit": r["unit"], "code": r.get("code") or "", "arm": "continuation",
                   "labeller": r["label"]}
                  for s, r in cl.items() if r["unit"] in MECH and r.get("passed") and
                  off_catalogue(r["unit"], J.get(s, r["label"]) if r["label"] == "disputed" else r["label"])]
    progs = [{"sid": r["sid"], "unit": r["unit"], "code": r["code"] or "", "arm": r["arm"], "labeller": r["label"]}
             for r in rows] + cont_other
    seen, uniq = set(), []
    for p in progs:
        k = (p["unit"], p["code"].strip())
        if k not in seen and p["code"]:
            seen.add(k)
            uniq.append(p)
    res = {"n_correct_other_rows": len(progs), "n_distinct": len(uniq), "programs": [],
           "scope": "every CORRECT program whose label is outside the frozen catalogue ('other' or a named extra mode)"}
    if uniq:
        controls = []
        for u in {p["unit"] for p in uniq}:
            for x in known_pool(u)[:4]:
                if x["src"].startswith("reference:"):
                    controls.append({"sid": "control|" + x["src"], "unit": u, "code": x["code"],
                                     "known": x["src"].split(":")[1]})
        items = [{"sid": p["sid"], "unit": p["unit"], "code": p["code"]} for p in uniq] + controls[:10]
        judged = {r["sid"]: r for r in asyncio.run(_adjudicate(items))}
        save_costs("novelty_audit")
        ctrl = [c for c in controls[:10]]
        res["controls"] = [{"known": c["known"], "judge": judged[c["sid"]]["label"]} for c in ctrl]
        res["control_accuracy"] = (sum(judged[c["sid"]]["label"] == c["known"] for c in ctrl) / len(ctrl)) \
            if ctrl else None
        for p in uniq:
            j = judged[p["sid"]]
            res["programs"].append({"sid": p["sid"], "unit": p["unit"], "arm": p["arm"], "labeller": p.get("labeller"),
                                    "nearest_known": nearest(p["code"], known_pool(p["unit"])),
                                    "judges": {"j1": j["j1"], "j2": j["j2"], "j3": j["j3"], "majority": j["label"]},
                                    "manual_class": None, "code": p["code"][:4000]})
    res["no_correct_novel_algorithm_claim"] = "only at a count of 0 after the manual read"
    res["utc"] = utc_now()
    write_json(RESULTS_DIR / "novelty_audit.json", res)
    return {k: v for k, v in res.items() if k != "programs"}


if __name__ == "__main__":
    setup_logging("novelty7")
    what = sys.argv[1] if len(sys.argv) > 1 else "judge"
    if what == "dep":
        d = dep_extract()
        print(json.dumps(d["per_dataset"], indent=1))
    elif what == "judge":
        print(judge_disputed())
    elif what == "audit":
        print(audit())


def regate(n_per_unit: int = 30, seed: int = 20261022) -> dict[str, Any]:
    """B3 style re-gate: 30 twin programs per mixed unit (stratified: >= 8 of A_min, every 'other', the rest default)
    go to the two blind judges (+ tiebreak); labeller-vs-adjudicated agreement must be >= 0.9."""
    import random
    from analysis_T import rows_with_labels
    tw = read_json(RESULTS_DIR / "twins.json")
    rows = [r for r in rows_with_labels() if r["arm"] == "TWIN" and r["unit"] in MECH and r.get("code")]
    rng = random.Random(seed)
    items, meta = [], {}
    for u in MECH:
        A, D = tw[u]["a_min"], UNITS[u]["default"]
        ru = [r for r in rows if r["unit"] == u]
        rng.shuffle(ru)
        pick = [r for r in ru if r["label"] not in UNITS[u]["catalogue"]]
        pick += [r for r in ru if r["label"] == A][:max(8, n_per_unit // 3)]
        pick += [r for r in ru if r["label"] not in [p["label"] for p in pick] or r not in pick][:0]
        rest = [r for r in ru if r not in pick]
        pick += rest[:max(0, n_per_unit - len(pick))]
        for r in pick[:n_per_unit]:
            items.append({"sid": r["sid"], "unit": u, "code": r["code"]})
            meta[r["sid"]] = r["label"]
    res = asyncio.run(_adjudicate(items))
    save_costs("regate")
    out: dict[str, Any] = {}
    for u in MECH:
        rr = [r for r in res if r["unit"] == u]
        dec = [r for r in rr if r["label"]]
        agree = sum(r["label"] == meta[r["sid"]] for r in dec)
        out[u] = {"n": len(rr), "n_adjudicated": len(dec), "agreement": agree / max(len(dec), 1),
                  "pass_0.9": agree / max(len(dec), 1) >= 0.9,
                  "disagreements": [{"sid": r["sid"], "labeller": meta[r["sid"]], "judges": [r["j1"], r["j2"], r["j3"]]}
                                    for r in dec if r["label"] != meta[r["sid"]]],
                  "n_a_min": sum(meta[r["sid"]] == tw[u]["a_min"] for r in rr)}
    out["judges"] = list(JUDGES) + [TIEBREAK]
    out["utc"] = utc_now()
    write_json(RESULTS_DIR / "regate.json", out)
    return out
