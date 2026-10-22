#!/usr/bin/env python3
"""Plan 7: LLM audits through OpenRouter (base_url/api_key from the environment), inside this artifact's judge cap.

7.1 NOVELTY AUDIT: every CORRECT 'other' program (unique per task x code sha256) of every arm, two blind judges from
    different families (exp18's pair: google/gemini-2.5-flash-lite, openai/gpt-4.1-mini) classify it as NOVEL
    ALGORITHM / CATALOGUE VARIANT / LABELLER MISS / DEGENERATE given the task, the catalogue and the nearest known
    human/textbook solutions (art_j3Rm_lr2nzR6 corpus + exp18's 472-solution index) and catalogue references, never
    the arm; deepseek/deepseek-chat-v3.1 resolves disagreements (majority of three). Controls: 5 catalogue references
    presented as unknown (expected LABELLER MISS) and 5 degenerate programs (expected DEGENERATE). Output:
    audit/novelty_audit.json and audit/other_map.json (code sha256 -> mapped Hill category).
7.2 LABEL-VALIDITY AUDIT: a stratified random sample (fixed seed) of 10 correct off-default programs per E6 task from
    (i) PN alpha <= 2 pooled and (ii) the task's best NA knob; one blind judge (bench: openai/gpt-4.1-mini via the
    frozen exp11 judge prompt; path: google/gemini-2.5-flash-lite via the exp8 suite judge) names the catalogue mode
    or 'other'; agreement with the labeller per arm (< 0.85 -> labeller-sensitive).
Spend: running sum of usage.cost; caps (USD) novelty 0.45, label-validity 0.10; the first HTTP 403 'AI Inventor
per-run OpenRouter budget' cancels every queued and in-flight call (checked after every semaphore acquire).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (AUDIT_DIR, BENCH, BUDGET_MSG, DATA_DIR, DEFAULT, E8, E11, E18, EXP8_TASK, PATH_TASKS, RESULTS_DIR,
                 ROOT, SUITE, append_jsonl, bench_paths, read_json, read_jsonl, setup_logging, sha256_text, utc_now,
                 write_json)

JUDGE_A = "google/gemini-2.5-flash-lite"
JUDGE_B = "openai/gpt-4.1-mini"
JUDGE_C = "deepseek/deepseek-chat-v3.1"
CLASSES = ["NOVEL ALGORITHM", "CATALOGUE VARIANT", "LABELLER MISS", "DEGENERATE"]
CLASS_DEFS = (
    "LABELLER MISS = the program implements a catalogue algorithm of this task in substance and should have carried "
    "its label; CATALOGUE VARIANT = it implements a known algorithm (catalogue, extended catalogue, or any named "
    "textbook or published method), possibly with minor changes, hybrids or a different but equivalent data "
    "structure; DEGENERATE = it passes by hard-coding, test-specific shortcuts, library calls that bypass the "
    "algorithm, or brute force that only passes because inputs are small; NOVEL ALGORITHM = none of the above, and "
    "the judge can state the mechanism and why no known algorithm matches.")  # exp18 audit.py, verbatim
CACHE = AUDIT_DIR / "llm_cache.jsonl"
SPEND = AUDIT_DIR / "llm_spend.jsonl"


class Budget:
    def __init__(self, cap: float, tag: str):
        self.cap, self.tag = cap, tag
        self.spent = sum(r.get("cost", 0.0) for r in read_jsonl(SPEND) if r.get("tag") == tag)
        self.stop = False
        self.reason = None


_CACHE: dict[str, dict[str, Any]] = {}


def _load_cache() -> None:
    if not _CACHE:
        for r in read_jsonl(CACHE):
            _CACHE[r["key"]] = r


async def call(client, sem, budget: Budget, model: str, prompt: str, key: str, max_tokens: int = 300) -> str | None:
    _load_cache()
    if key in _CACHE:
        return _CACHE[key]["text"]
    async with sem:
        if budget.stop:
            return None
        if budget.spent >= budget.cap:
            budget.stop, budget.reason = True, f"cap {budget.cap} reached"
            return None
        try:
            r = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}],
                                                     temperature=0, max_tokens=max_tokens)
        except Exception as e:  # noqa: BLE001 - a budget refusal stops the whole batch; others are logged
            msg = str(e)
            if BUDGET_MSG in msg:
                budget.stop, budget.reason = True, "budget_403"
                logger.error("OpenRouter per-run budget refusal: stopping the audit batch")
            else:
                logger.warning(f"{model} call failed: {msg[:160]}")
            return None
        if budget.stop:
            return None
        txt = r.choices[0].message.content or ""
        cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
        budget.spent += cost
        append_jsonl(SPEND, [{"tag": budget.tag, "model": model, "cost": cost, "utc": utc_now()}])
        rec = {"key": key, "model": model, "text": txt}
        _CACHE[key] = rec
        append_jsonl(CACHE, [rec])
        logger.debug(f"{model}: {txt[:200]!r} (cost {cost:.5f}, total {budget.spent:.4f})")
        return txt


def client():
    from openai import AsyncOpenAI

    return AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                       timeout=90, max_retries=2)


# ------------------------------------------------------------------------------------------------ task text
def bench_dir(task: str) -> Path:
    for d in BENCH.iterdir():
        if d.is_dir() and d.name.startswith(task + "_"):
            return d
    raise FileNotFoundError(task)


def description(task: str) -> str:
    if task in PATH_TASKS:
        return read_json(E8 / "prompts" / "frozen_prompts.json")["spec"][EXP8_TASK[task]]
    return read_json(bench_dir(task) / "spec.json")["description"]


def catalogue_modes(task: str) -> list[str]:
    if task in PATH_TASKS:
        bench_paths()
        import common as suite_common  # exp8 suite common

        return list(suite_common.MODES[EXP8_TASK[task]])
    return [c["mode"] for c in read_json(bench_dir(task) / "spec.json")["catalogue"]]


def catalogue_text(task: str) -> str:
    if task in PATH_TASKS:
        bench_paths()
        import common as suite_common

        st = EXP8_TASK[task]
        return "\n".join(f"- {m}: {suite_common.MODE_DEFINITIONS[st][m]}" for m in suite_common.MODES[st]) + \
            "\nExtended catalogue (known, not labels): " + ", ".join(suite_common.EXTENDED_CATALOGUE[st])
    sp = read_json(bench_dir(task) / "spec.json")
    return "\n".join(f"- {c['mode']}: {c['display_name']} - {c['mechanism']}" for c in sp["catalogue"])


def references(task: str) -> list[dict[str, Any]]:
    d = (SUITE / "tasks" / {"T1": "t1_grid", "T2": "t2_wsp"}[task] / "references") if task in PATH_TASKS else \
        (bench_dir(task) / "references")
    return [{"source": "catalogue reference", "mode_hint": f.stem, "code": f.read_text()} for f in sorted(d.glob("*.py"))]


def canon(code: str) -> list[str]:
    bench_paths()
    from bench.common.canon import canon_tokens

    try:
        return canon_tokens(code)
    except Exception:  # noqa: BLE001
        return []


def nearest(code: str, pool: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    bench_paths()
    from bench.common.canon import token_distance

    a = canon(code)
    sc = []
    for p in pool:
        b = p.get("_canon")
        if b is None:
            b = p["_canon"] = canon(p["code"])
        if b:
            sc.append((token_distance(a, b), p))
    sc.sort(key=lambda x: x[0])
    return [{"source": p["source"], "mode_hint": p.get("mode_hint"), "similarity": round(1 - d, 3),
             "code": p["code"][:1500]} for d, p in sc[:k]]


def scrub(task: str, code: str) -> str:
    """exp18: bench tasks use the frozen bench scrubber; path tasks drop comments (identifiers kept)."""
    if task not in PATH_TASKS:
        bench_paths()
        try:
            from bench.common.scrub import scrub_code

            return scrub_code(code)[0]
        except Exception:  # noqa: BLE001
            return code
    return "\n".join(l for l in code.splitlines() if not l.strip().startswith("#"))


def audit_prompt(task: str, code: str, nk: list[dict], nr: list[dict]) -> str:
    def fmt(ns):
        return "\n\n".join(f"[{n['source']} | {n['mode_hint']} | similarity {n['similarity']}]\n```python\n"
                           f"{n['code'][:1200]}\n```" for n in ns)

    return (f"You audit whether a Python program is a genuinely new algorithm.\n\nTASK:\n{description(task)}\n\n"
            f"CATALOGUE OF KNOWN ALGORITHMS FOR THIS TASK:\n{catalogue_text(task)}\n\n"
            "CONTEXT: an automatic mechanism labeller could not assign any catalogue label to this program (it was "
            "labelled 'other').\n\n"
            f"CLASSES (choose exactly one):\n{CLASS_DEFS}\n\n"
            "DECISION ORDER: (1) if the program's mechanism is one of the catalogue algorithms above (even renamed, "
            "restructured, recursive vs iterative, or with a different container) -> LABELLER MISS; (2) else if it "
            "passes by hard-coding, test-specific shortcuts or a library call that bypasses the task's algorithmic "
            "work -> DEGENERATE; (3) else if it is any other known method (a named textbook or published algorithm, "
            "or a hybrid/variant of known ones) -> CATALOGUE VARIANT; (4) only if none applies -> NOVEL ALGORITHM.\n\n"
            f"PROGRAM (identifiers and comments that name algorithms were scrubbed):\n```python\n{code}\n```\n\n"
            f"NEAREST KNOWN HUMAN / TEXTBOOK SOLUTIONS (context; similarity of canonical token streams):\n"
            f"{fmt(nk)}\n\nNEAREST CATALOGUE REFERENCES:\n{fmt(nr)}\n\n"
            "Judge the mechanism the code executes. Answer with JSON only: {\"class\": \"NOVEL ALGORITHM | CATALOGUE "
            "VARIANT | LABELLER MISS | DEGENERATE\", \"closest_known_algorithm\": \"...\", \"differs_how\": \"one "
            "sentence\", \"catalogue_label_if_miss\": \"<label id or null>\", \"parent_catalogue_label\": \"<label "
            "id of the catalogue algorithm this is a variant of, or null>\", \"confidence\": <0-1>}")


def parse(txt: str | None, modes: list[str]) -> dict[str, Any]:
    if not txt:
        return {"class": None}
    m = re.search(r"\{.*\}", txt, re.S)
    js: dict[str, Any] = {}
    if m:
        try:
            js = json.loads(m.group(0))
        except json.JSONDecodeError:
            js = {}
    c = str(js.get("class", "")).upper()
    cls = next((k for k in CLASSES if k in c), None) or next((k for k in CLASSES if k in (txt or "").upper()), None)

    def lab(v):
        v = str(v or "").strip().lower()
        return v if v in modes else None
    return {"class": cls, "closest": str(js.get("closest_known_algorithm") or "")[:80],
            "miss_label": lab(js.get("catalogue_label_if_miss")), "parent": lab(js.get("parent_catalogue_label")),
            "differs_how": str(js.get("differs_how") or "")[:200], "confidence": js.get("confidence")}


def known_pool() -> dict[str, list[dict[str, Any]]]:
    by = defaultdict(list)
    for p in (E18 / "known_solutions.jsonl", DATA_DIR / "known_solutions_dep.jsonl"):
        for r in read_jsonl(p):
            by[r["task"]].append(r)
    return by


CONTROL_REFS = [("T03", "quickselect"), ("T10", "bfs"), ("T05", "brute_force"), ("T06", "sort_adjacent"),
                ("R2", "union_find")]
CONTROL_DEGEN = [
    ("T03", "def solve(nums, k):\n    if nums == [3, 2, 1, 5, 6, 4] and k == 2:\n        return 2\n    if k == 1:\n"
            "        return min(nums)\n    return nums[0]\n"),
    ("T05", "def solve(nums, target):\n    if target == 9:\n        return [0, 1]\n    return [0, len(nums) - 1]\n"),
    ("T06", "def solve(nums):\n    return nums[-1] if nums[-1] in nums[:-1] else nums[0]\n"),
    ("T10", "def solve(n, edges):\n    return max(1, n - len(edges))\n"),
    ("R2", "def solve(n, edges):\n    return len(edges) >= n\n"),
]


async def _novelty(items: list[dict[str, Any]], budget: Budget) -> list[dict[str, Any]]:
    cl = client()
    sem = asyncio.Semaphore(8)
    known = known_pool()
    refs: dict[str, list] = {}

    async def one(it):
        t = it["task"]
        if t not in refs:
            refs[t] = references(t)
        modes = catalogue_modes(t)
        nk = nearest(it["code"], known.get(t, []), 3)
        nr = nearest(it["code"], refs[t], 3)
        pr = audit_prompt(t, scrub(t, it["code"]), nk, nr)
        key = sha256_text(pr)
        ta = await call(cl, sem, budget, JUDGE_A, pr, "A|" + key)
        tb = await call(cl, sem, budget, JUDGE_B, pr, "B|" + key)
        a, b = parse(ta, modes), parse(tb, modes)
        c = None
        if a["class"] and b["class"] and a["class"] != b["class"]:
            c = parse(await call(cl, sem, budget, JUDGE_C, pr, "C|" + key), modes)
        votes = [x["class"] for x in (a, b, c) if x and x["class"]]
        final = Counter(votes).most_common(1)[0][0] if votes else None
        if c is not None and c["class"] is not None and len(set(votes)) == 3:
            final = c["class"]
        return {**{k: it[k] for k in ("task", "code_sha256", "arms", "n_programs") if k in it},
                "nearest_known": [{k: v for k, v in n.items() if k != "code"} for n in nk],
                "nearest_refs": [{k: v for k, v in n.items() if k != "code"} for n in nr],
                "judge_A": a, "judge_B": b, "judge_C": c, "final_class": final,
                "resolved": c is not None}

    return await asyncio.gather(*[one(it) for it in items])


def mapped_category(rec: dict[str, Any]) -> str:
    cls = rec["final_class"]
    js = [x for x in (rec["judge_A"], rec["judge_B"], rec.get("judge_C")) if x and x.get("class") == cls]
    if cls == "LABELLER MISS":
        labs = [x["miss_label"] for x in js if x.get("miss_label")]
        return Counter(labs).most_common(1)[0][0] if labs else "other"
    if cls == "CATALOGUE VARIANT":
        labs = [x["parent"] for x in js if x.get("parent")]
        if labs:
            return Counter(labs).most_common(1)[0][0]
        nm = (js[0]["closest"] if js else "") or "unnamed"
        return "variant:" + re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")[:40]
    if cls == "DEGENERATE":
        return "DEGENERATE"
    if cls == "NOVEL ALGORITHM":
        nm = (js[0]["closest"] if js else "") or "unnamed"
        return "novel:" + re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")[:40]
    return "other"


def run_novelty(cap: float = 0.45) -> dict[str, Any]:
    rows = read_jsonl(DATA_DIR / "samples.jsonl")
    pool: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        if r.get("label") == "other" and r.get("passed") and r.get("code"):
            k = (r["task"], r["code_sha256"])
            if k not in pool:
                pool[k] = {"task": r["task"], "code_sha256": r["code_sha256"], "code": r["code"], "arms": [],
                           "n_programs": 0}
            pool[k]["arms"].append(r["arm"])
            pool[k]["n_programs"] += 1
    items = list(pool.values())
    ctrl = []
    for t, mode in CONTROL_REFS:
        try:
            refs = {x["mode_hint"]: x["code"] for x in references(t)}
            if mode in refs:
                ctrl.append({"task": t, "code": refs[mode], "code_sha256": sha256_text(refs[mode]),
                             "expected": "LABELLER MISS", "kind": f"catalogue reference {mode}"})
        except FileNotFoundError:
            pass
    for t, code in CONTROL_DEGEN:
        ctrl.append({"task": t, "code": code, "code_sha256": sha256_text(code), "expected": "DEGENERATE",
                     "kind": "degenerate (hard-coded)"})
    budget = Budget(cap, "novelty")
    logger.info(f"novelty audit: {len(items)} unique correct 'other' programs + {len(ctrl)} controls "
                f"(spent so far {budget.spent:.4f})")
    res_c = asyncio.run(_novelty(ctrl, budget))
    res = asyncio.run(_novelty(items, budget)) if not budget.stop else []
    ctl = [{"kind": c["kind"], "task": c["task"], "expected": c["expected"], "A": r["judge_A"]["class"],
            "B": r["judge_B"]["class"], "final": r["final_class"]} for c, r in zip(ctrl, res_c)]
    by_sha: dict[str, str] = {}
    recs = []
    for it, r in zip(items, res):
        m = mapped_category(r) if r["final_class"] else "other"
        by_sha[it["code_sha256"]] = m
        recs.append({**r, "mapped": m, "code": it["code"]})
    complete = len(res) == len(items) and all(r["final_class"] for r in res)
    a = [r["judge_A"]["class"] for r in res if r["judge_A"]["class"] and r["judge_B"]["class"]]
    b = [r["judge_B"]["class"] for r in res if r["judge_A"]["class"] and r["judge_B"]["class"]]
    from analysis.stats_step0 import cohen_kappa

    kap = cohen_kappa(a, b) if a else None
    per_arm: dict[str, Counter] = defaultdict(Counter)
    for r in recs:
        for arm in set(r.get("arms", [])):
            per_arm[arm][r["final_class"] or "unaudited"] += 1
    n_novel = sum(1 for r in recs if r["final_class"] == "NOVEL ALGORITHM")
    out = {"n_unique_correct_other": len(items), "n_audited": sum(1 for r in res if r["final_class"]),
           "complete": complete, "kappa_A_B": kap, "controls": ctl,
           "controls_correct_A": sum(c["A"] == c["expected"] for c in ctl),
           "controls_correct_B": sum(c["B"] == c["expected"] for c in ctl),
           "controls_correct_final": sum(c["final"] == c["expected"] for c in ctl),
           "class_counts": dict(Counter(r["final_class"] for r in recs)), "per_arm": {k: dict(v) for k, v in
                                                                                 per_arm.items()},
           "n_confirmed_novel": n_novel,
           "claim_no_novel_allowed": bool(complete and n_novel == 0),
           "spent_usd": budget.spent, "stop_reason": budget.reason, "records": recs, "utc": utc_now()}
    write_json(AUDIT_DIR / "novelty_audit.json", out)
    write_json(AUDIT_DIR / "other_map.json", {"by_code_sha256": by_sha, "utc": utc_now(),
                                              "rule": "predictions/c1_rule.json other_mapping"})
    logger.info(f"novelty audit: {out['class_counts']}; kappa {kap}; controls A {out['controls_correct_A']}/"
                f"{len(ctl)} B {out['controls_correct_B']}/{len(ctl)}; spent {budget.spent:.4f}")
    return out


# ------------------------------------------------------------------------------------------------ label validity
def run_label_validity(best_na: dict[str, str], cap: float = 0.10, seed: int = 7) -> dict[str, Any]:
    """best_na: {task: arm list of the task's best NA knob (comma-joined)}."""
    rows = read_jsonl(DATA_DIR / "samples.jsonl")
    reused_rows = [dict(r, sample_id=r["sample_id"]) for r in read_jsonl(DATA_DIR / "reused_rows.jsonl")]
    rng = random.Random(seed)
    sample = []
    for t, arms in best_na.items():
        D = DEFAULT[t]
        groups = {"PN_alpha_le2": [r for r in rows if r["task"] == t and r["arm"] in ("PN_a0.5", "PN_a1", "PN_a2")],
                  "best_NA": [r for r in rows + reused_rows if r["task"] == t and r["arm"] in arms.split(",")]}
        for g, rs in groups.items():
            cand = sorted([r for r in rs if r.get("passed") and r["label"] not in (D, "invalid") and r.get("code")],
                          key=lambda r: r["sample_id"])
            for r in rng.sample(cand, min(10, len(cand))):
                sample.append({**r, "audit_group": g})
    sample = sample[:120]
    bench = [r for r in sample if r["task"] not in PATH_TASKS]
    path = [r for r in sample if r["task"] in PATH_TASKS]
    labels: dict[str, str | None] = {}
    spent0 = sum(r.get("cost", 0.0) for r in read_jsonl(ROOT / "logs" / "openrouter_spend.jsonl"))
    if bench:
        bench_paths()
        import bench.common.judge as BJ

        BJ.PERSONAL_CAP = spent0 + cap * 0.6
        j = BJ.Judge(ROOT)
        recs = j.label_many([("j2", r["task"], r["code"]) for r in bench])
        for r, rec in zip(bench, recs):
            labels[r["sample_id"]] = rec.get("label")
    if path:
        bench_paths()
        import labeller.judge as J

        J.CACHE = AUDIT_DIR / "label_validity_path_cache.jsonl"
        J.COST_FILE = AUDIT_DIR / "label_validity_path_cost.json"
        res, _ = J.judge_many([{"task": EXP8_TASK[r["task"]], "code": r["code"]} for r in path],
                              "google/gemini-2.5-flash-lite", "label_validity", cap * 0.4)
        for r, rec in zip(path, res):
            labels[r["sample_id"]] = (rec or {}).get("label")
    per: dict[str, dict[str, Any]] = {}
    out_rows = []
    for r in sample:
        jl = labels.get(r["sample_id"])
        key = f"{r['task']}|{r['audit_group']}"
        d = per.setdefault(key, {"n": 0, "n_judged": 0, "agree": 0})
        d["n"] += 1
        if jl:
            d["n_judged"] += 1
            d["agree"] += int(jl == r["label"])
        out_rows.append({"sample_id": r["sample_id"], "task": r["task"], "arm": r["arm"], "group": r["audit_group"],
                         "labeller": r["label"], "judge": jl})
    for d in per.values():
        d["agreement"] = d["agree"] / d["n_judged"] if d["n_judged"] else None
        d["labeller_sensitive"] = d["agreement"] is not None and d["agreement"] < 0.85
    out = {"per_task_group": per, "rows": out_rows, "n": len(sample), "best_na_arms": best_na, "utc": utc_now()}
    # sensitivity (plan 7.2): H5 of PN and of every NA class with the judge's labels on the audited programs
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from analysis.core import NA_PRIMARY, TaskData, best_na as best_of, class_price
        from analysis.hull import fixed_uniforms
        from analysis.run_all import load_other_map, task_rows

        U = fixed_uniforms(1000)
        reused = read_jsonl(DATA_DIR / "reused_rows.jsonl")
        rows2 = [dict(r, label=labels[r["sample_id"]]) if labels.get(r["sample_id"]) else r for r in rows]
        sens = {}
        for t in best_na:
            td = TaskData(t, task_rows(rows2, reused, t), load_other_map())
            h5 = {c: (s_["H5"] if (s_ := class_price(td, c, U)) else None) for c in ["PN"] + NA_PRIMARY}
            bc, bv = best_of(h5, NA_PRIMARY)
            sens[t] = {"H5": h5, "best_na": bc, "D_t": (h5["PN"] - bv) if (h5.get("PN") is not None and bv is not None)
                       else None}
        out["H5_with_judge_labels_on_audited_share"] = sens
    except Exception as e:  # noqa: BLE001 - the sensitivity must not lose the audit itself
        logger.exception(f"label-validity sensitivity failed: {e}")
    write_json(AUDIT_DIR / "label_validity.json", out)
    logger.info(f"label validity: {({k: v['agreement'] for k, v in per.items()})}")
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["novelty", "validity"])
    ap.add_argument("--best-na", default="", help="json {task: 'arm1,arm2'} for the validity audit")
    args = ap.parse_args()
    setup_logging(f"audit_{args.what}")
    if args.what == "novelty":
        run_novelty()
    else:
        run_label_validity(json.loads(args.best_na))


if __name__ == "__main__":
    main()
