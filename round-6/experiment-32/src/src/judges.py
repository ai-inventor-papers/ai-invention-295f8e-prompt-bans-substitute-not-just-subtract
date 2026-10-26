#!/usr/bin/env python3
"""S7: blind judges over OpenRouter that map every text to a catalogue algorithm.

Modes: EXPL (every AV explanation), NAME (the same rubric on the visible user text, plus the decoded generated prefix
for g positions) and PREDICT ('which catalogue algorithm will the assistant implement?' on the same texts).
Judges: J1 google/gemini-2.5-flash-lite, J2 openai/gpt-4.1-nano, J3 deepseek/deepseek-chat-v3.1 resolving 'planned'
disagreements (EXPL and NAME) or PREDICT disagreements. Temperature 0. Judges see the task title, the catalogue (ids,
display names, aliases, one-line mechanism) and the text -- never the condition, position or realised label; items are
shuffled across conditions and tasks. Calibration gate: >= 0.9 on 30 synthetic items per judge (a failing judge is
swapped for the next-cheapest model of another family). usage.cost is read on every call; the first HTTP 403 whose
message starts 'AI Inventor per-run OpenRouter budget' cancels every queued and in-flight call.

Usage: python src/judges.py calibrate | run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (BUDGET_MSG, DATA_DIR, JUDGE_CAP_USD, PRED_DIR, RESULTS_DIR, TASKS, append_jsonl, read_json,
                 read_jsonl, setup_logging, sha256_text, stable_seed, utc_now, write_json)

JUDGES = {"J1": "google/gemini-2.5-flash-lite", "J2": "openai/gpt-4.1-nano", "J3": "deepseek/deepseek-chat-v3.1"}
SWAPS = {"J1": ["meta-llama/llama-4-scout"], "J2": ["mistralai/mistral-small-3.2-24b-instruct"],
         "J3": ["qwen/qwen3-235b-a22b-2507"]}
CACHE = DATA_DIR / "judge_nla_cache.jsonl"
COSTS = RESULTS_DIR / "costs_judges.jsonl"
TITLES = {"T1": "find any valid path between two cells of a grid with walls",
          "T2": "length of the shortest path in a directed graph with integer edge weights 0-100",
          "T03": "return the k-th smallest value of a list of integers",
          "T05": "return the two indices whose values add up to a target (two-sum)",
          "T06": "return the repeated value in a list of n+1 integers in 1..n",
          "T10": "count the connected components of an undirected graph",
          "T04": "first index of a substring needle in a string haystack",
          "R6": "first and last index of a target in a sorted list"}
RUBRIC_VERSION = "v2"


def catalogue_block(task: str) -> str:
    import prompts as PR

    lines = []
    for c in PR.catalogue(task):
        al = ", ".join(c["aliases"][:6])
        lines.append(f"- {c['mode']}: {c['display_name']} (also called: {al}). Mechanism: {c['mechanism']}")
    return "\n".join(lines)


def prompt_expl(task: str, text: str) -> str:
    return (f"You read a short text and report which algorithm, if any, the text says is being used or will be used "
            f"to solve a programming task.\n\nProgramming task: {TITLES[task]}.\n\nCatalogue of algorithms for this "
            f"task (use these ids):\n{catalogue_block(task)}\n\nDefinitions:\n"
            "- planned: the id of the catalogue algorithm that the text says is being, or will be, used or implemented. "
            "An algorithm that the text names only as forbidden, avoided, banned or not allowed is NOT planned (it goes "
            "to negated). If the text says that a specific method which is NOT in the catalogue is being or will be used "
            "(for example a genetic algorithm, a neural network, random guessing or any other named technique), answer "
            "\"other\" -- never \"none_named\" in that case. Answer \"none_named\" only when the text names no method "
            "at all as being or going to be used.\n"
            "- mentioned: every catalogue id the text names in any way (by name, alias or unmistakable description).\n"
            "- negated: the catalogue ids the text names only as forbidden, avoided or excluded.\n\n"
            f"Text:\n\"\"\"\n{text}\n\"\"\"\n\n"
            "Answer with one JSON object only, no other words: "
            "{\"planned\": \"<id or none_named or other>\", \"mentioned\": [\"<id>\", ...], \"negated\": [\"<id>\", ...]}")


def prompt_predict(task: str, text: str) -> str:
    return (f"An AI assistant received the request below (if a beginning of its answer is shown, the assistant has "
            f"already written that much). Predict which algorithm from the catalogue the assistant's final Python "
            f"solution will implement.\n\nProgramming task: {TITLES[task]}.\n\nCatalogue of algorithms (use these ids):\n"
            f"{catalogue_block(task)}\n\nRequest and answer so far:\n\"\"\"\n{text}\n\"\"\"\n\n"
            "Answer with one JSON object only, no other words: {\"predicted\": \"<id or other>\"}")


def parse_json(s: str, mode: str, ids: set[str]) -> dict[str, Any] | None:
    m = re.search(r"\{.*\}", s or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if mode == "PREDICT":
        p = str(d.get("predicted", "")).strip()
        return {"predicted": p if p in ids | {"other"} else "other"}
    p = str(d.get("planned", "")).strip()
    norm = lambda xs: [x for x in (xs or []) if isinstance(x, str) and x in ids]
    return {"planned": p if p in ids | {"none_named", "other"} else ("none_named" if not p else "other"),
            "mentioned": norm(d.get("mentioned")), "negated": norm(d.get("negated"))}


class Runner:
    def __init__(self, cap: float = JUDGE_CAP_USD, conc: int = 24):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=60, max_retries=2)
        self.sem = asyncio.Semaphore(conc)
        self.cap = cap
        self.stop = False
        self.spent = sum(r.get("cost") or 0 for r in read_jsonl(COSTS))
        self.spent0 = self.spent  # spend before this run (calibration, earlier runs)
        self.cache = {r["key"]: r for r in read_jsonl(CACHE)}
        self.n_calls = 0
        self.n_bad = 0

    async def one(self, model: str, mode: str, task: str, text: str, ids: set[str]) -> dict[str, Any] | None:
        key = sha256_text(f"{RUBRIC_VERSION}|{model}|{mode}|{task}|{text}")
        if key in self.cache:
            return self.cache[key]["out"]
        async with self.sem:
            if self.stop or self.spent >= self.cap:
                return None
            prompt = prompt_predict(task, text) if mode == "PREDICT" else prompt_expl(task, text)
            for attempt in range(2):
                try:
                    msg = prompt if attempt == 0 else prompt + "\nReturn ONLY the JSON object, with no reasoning before it."
                    kw: dict[str, Any] = {"extra_body": {"usage": {"include": True}}}
                    if attempt == 1:  # stricter retry: JSON mode and room for a preamble
                        kw["response_format"] = {"type": "json_object"}
                    r = await self.client.chat.completions.create(
                        model=model, messages=[{"role": "user", "content": msg}], temperature=0,
                        max_tokens=160 if attempt == 0 else 400, **kw)
                except Exception as e:  # noqa: BLE001 - classify: budget refusal stops the batch
                    s = str(e)
                    if BUDGET_MSG in s:
                        self.stop = True
                        logger.error(f"budget refusal: {s[:200]}")
                        return None
                    logger.warning(f"{model} call failed: {s[:160]}")
                    return None
                cost = float(getattr(r.usage, "cost", 0) or 0) if r.usage else 0.0
                if not cost and r.usage:
                    cost = (r.usage.prompt_tokens or 0) * 2e-7 + (r.usage.completion_tokens or 0) * 8e-7
                self.spent += cost
                self.n_calls += 1
                append_jsonl(COSTS, [{"model": model, "mode": mode, "cost": cost, "utc": utc_now()}])
                content = r.choices[0].message.content if r.choices else ""
                out = parse_json(content, mode, ids)
                if out is not None:
                    rec = {"key": key, "model": model, "mode": mode, "task": task, "out": out,
                           "raw": (content or "")[:300]}
                    self.cache[key] = rec
                    append_jsonl(CACHE, [rec])
                    return out
                self.n_bad += 1
            return None

    async def many(self, model: str, items: list[dict[str, Any]], mode_key: str = "mode") -> list[Any]:
        import prompts as PR

        idsets = {t: {c["mode"] for c in PR.catalogue(t)} for t in TASKS}
        tasks = [self.one(model, it[mode_key], it["task"], it["text"], idsets[it["task"]]) for it in items]
        return await asyncio.gather(*tasks)


# ------------------------------------------------------------------------------------------------ calibration
def calibration_items() -> list[dict[str, Any]]:
    """30 synthetic explanation-style texts with known answers (frozen with commit #2)."""
    import prompts as PR

    items = []
    plans = [("T2", "bf_spfa", "dijkstra"), ("T10", "union_find", "dfs"), ("T06", "floyd", "hash_set"),
             ("T05", "sort_two_pointers", "hash_map"), ("T03", "quickselect", "full_sort"),
             ("T1", "dfs", "bfs")]
    for t, Y, D in plans:
        cat = {c["mode"]: c["display_name"] for c in PR.catalogue(t)}
        y, d = cat[Y], cat[D]
        items += [
            {"task": t, "expect": Y, "text": f"Technical programming prompt asking for a Python function. The phrase "
             f"\"solve\" opens the implementation, and the response will implement {y}, building the core loop next."},
            {"task": t, "expect": "none_named", "neg": D, "text": f"Formal coding instruction: the user forbids {d} "
             "for this task, followed by a precise specification of the inputs and the required return value."},
            {"task": t, "expect": "none_named", "text": "Technical prompt format with standard-library constraints; the "
             "final token closes the format line, strongly expecting the assistant to open a python code block."},
            {"task": t, "expect": "other", "text": "Code-generation context: the answer will evolve candidate answers "
             "with a genetic algorithm, mutating and selecting them over many generations."},
            {"task": t, "expect": Y, "neg": D, "text": f"The prompt rules out {d}; the assistant's plan is therefore to "
             f"rely on {y} instead, starting with the helper that the approach needs."},
        ]
    return items


async def _calibrate(rn: Runner) -> dict[str, Any]:
    items = calibration_items()
    out: dict[str, Any] = {"n_items": len(items), "judges": {}}
    for j, model in list(JUDGES.items()):
        cands = [model] + SWAPS[j]
        for m in cands:
            res = await rn.many(m, [dict(it, mode="EXPL") for it in items])
            ok = []
            for it, r in zip(items, res):
                good = r is not None and r["planned"] == it["expect"]
                if good and it.get("neg"):
                    good = it["neg"] in (r.get("negated") or []) or it["neg"] not in (r.get("mentioned") or [])
                ok.append(good)
            acc = sum(ok) / len(ok)
            out["judges"].setdefault(j, []).append({"model": m, "accuracy": acc,
                                                    "fails": [it["text"][:80] for it, g in zip(items, ok) if not g]})
            if acc >= 0.9:
                JUDGES[j] = m
                break
    out["final"] = dict(JUDGES)
    out["spent_usd"] = rn.spent
    return out


# ------------------------------------------------------------------------------------------------ items
def build_items() -> list[dict[str, Any]]:
    conv = read_json(RESULTS_DIR / "layer_convention.json")["chosen"]
    c2 = read_json(PRED_DIR / "commit2_readout.json")
    sel = set(c2["readout_state_ids"])
    items = []
    for e in read_jsonl(DATA_DIR / "explanations.jsonl"):
        if e.get("convention") != conv or e["kind"] not in ("PREFILL", "GEN", "RAND") or e["state_id"] not in sel:
            continue
        if int(e["idx"]) > 3:  # #4-#6 exist only for the edit pool (chosen by the alias lexicon, never judged)
            continue
        items.append({"item_id": f"EXPL|{e['expl_id']}", "mode": "EXPL", "task": e["task"], "text": e["text"],
                      "state_id": e["state_id"], "expl_id": e["expl_id"]})
    # text-only: one text per (task, condition, template) for prefill; per sample and g for generated positions
    st = {(r["task"], r["kind"], r["w"], r.get("mode") or "-"): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl")}
    bans = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_ban.jsonl")}
    idx = {r["state_id"]: r for r in read_jsonl(Path(DATA_DIR.parent / "cache" / "states_index.jsonl"))}
    seen = set()
    for sid in sorted(sel):
        r = idx[sid]
        if r["kind"] not in ("PREFILL", "GEN"):
            continue
        t, cond, mode, w = r["task"], r["condition"], r.get("mode"), r["template"]
        p = bans[(t, w)] if cond == "ban" else st[(t, cond, w, mode or "-")] if cond in ("forced",) else \
            st[(t, "seed", w, "-")] if cond == "seed" else st[(t, "twin", w, "-")]
        if r["kind"] == "PREFILL":
            tid = f"{t}|{cond}|{mode or '-'}|{w}|PREFILL"
            text = p["user_text"]
        else:
            tid = f"{t}|{cond}|{mode or '-'}|{w}|{r['position']}|{r['slot']}"
            text = p["user_text"] + "\n\nAssistant (beginning of its answer):\n" + r["prefix_text"]
        if tid in seen:
            continue
        seen.add(tid)
        for mode_ in ("NAME", "PREDICT"):
            items.append({"item_id": f"{mode_}|{tid}", "mode": mode_, "task": t, "text": text, "text_id": tid})
    rng = random.Random(stable_seed("judge_shuffle"))
    rng.shuffle(items)
    return items


async def _run(rn: Runner) -> dict[str, Any]:
    items = build_items()
    logger.info(f"judge items: {len(items)} ({sum(i['mode'] == 'EXPL' for i in items)} EXPL)")
    out_p = DATA_DIR / "judgements.jsonl"
    # pilot 100 calls -> cost projection
    pilot = items[:50]
    r1 = await rn.many(JUDGES["J1"], pilot)
    r2 = await rn.many(JUDGES["J2"], pilot)
    per_call = max((rn.spent - rn.spent0) / max(1, rn.n_calls), 1e-4)
    # only items without a cached answer will cost anything
    def cached(model: str, it: dict[str, Any]) -> bool:
        return sha256_text(f"{RUBRIC_VERSION}|{model}|{it['mode']}|{it['task']}|{it['text']}") in rn.cache
    n_uncached = sum((not cached(JUDGES["J1"], it)) + (not cached(JUDGES["J2"], it)) for it in items)
    proj = rn.spent0 + per_call * n_uncached * 1.12
    logger.info(f"pilot: {rn.n_calls} calls, {rn.spent:.4f} USD; projection {proj:.2f} USD")
    reductions = []
    rn.cap = JUDGE_CAP_USD + rn.spent0  # the cap applies to this artifact's judge spend
    if proj > JUDGE_CAP_USD:
        reductions.append("J2 judges only explanations #1-#2 of g states")
        reductions.append("PREDICT only at prefill")
    res: dict[str, dict[str, Any]] = {}
    for j in ("J1", "J2"):
        sub = items
        if j == "J2" and reductions:
            sub = [i for i in items if not (i["mode"] == "EXPL" and "|g" in i["state_id"] and
                                            i["expl_id"].endswith(("#3", "#4", "#5", "#6")))]
        if len(reductions) > 1:
            sub = [i for i in sub if not (i["mode"] == "PREDICT" and not i["text_id"].endswith("PREFILL"))]
        out = await rn.many(JUDGES[j], sub)
        for it, o in zip(sub, out):
            res.setdefault(it["item_id"], {})[j] = o
        logger.info(f"{j} done: spent {rn.spent:.3f} USD; stop={rn.stop}")
        if rn.stop:
            break
    # J3 on disagreements
    dis = []
    for it in items:
        d = res.get(it["item_id"], {})
        a, b = d.get("J1"), d.get("J2")
        if a is None and b is None:
            continue
        k = "predicted" if it["mode"] == "PREDICT" else "planned"
        if a is None or b is None or a[k] != b[k]:  # J3 also covers an item one judge failed to answer
            dis.append(it)
    if dis and not rn.stop:
        out = await rn.many(JUDGES["J3"], dis)
        for it, o in zip(dis, out):
            res[it["item_id"]]["J3"] = o
    rows = []
    for it in items:
        d = res.get(it["item_id"], {})
        k = "predicted" if it["mode"] == "PREDICT" else "planned"
        vals = [d[j][k] for j in ("J1", "J2", "J3") if d.get(j)]
        a = d.get("J1", {}) or {}
        b = d.get("J2", {}) or {}
        if a and b and a.get(k) == b.get(k):
            resolved = a[k]
        elif vals:
            from collections import Counter
            top, c = Counter(vals).most_common(1)[0]
            resolved = top if c >= 2 else "unresolved"
        else:
            resolved = None
        mentioned = sorted(set((a.get("mentioned") or [])) | set((b.get("mentioned") or []))) if it["mode"] != "PREDICT" else None
        rows.append({k2: it[k2] for k2 in ("item_id", "mode", "task") if k2 in it} |
                    {"state_id": it.get("state_id"), "expl_id": it.get("expl_id"), "text_id": it.get("text_id"),
                     "J1": d.get("J1"), "J2": d.get("J2"), "J3": d.get("J3"), "resolved": resolved,
                     "mentioned_any": mentioned})
    from cfg import write_jsonl
    write_jsonl(out_p, rows)
    return {"n_items": len(items), "n_disagreements": len(dis), "spent_usd": rn.spent, "n_calls": rn.n_calls,
            "n_bad_json": rn.n_bad, "reductions": reductions, "stopped_by_budget": rn.stop, "judges": dict(JUDGES),
            "projection_usd": proj}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["calibrate", "run"])
    ap.add_argument("--conc", type=int, default=24)
    args = ap.parse_args()
    setup_logging(f"judges_{args.stage}")
    rn = Runner(conc=args.conc)
    if args.stage == "calibrate":
        out = asyncio.run(_calibrate(rn))
        write_json(RESULTS_DIR / "judge_calibration.json", out)
        logger.info(f"calibration: {json.dumps({j: [(x['model'], x['accuracy']) for x in v] for j, v in out['judges'].items()})}")
    else:
        cal = read_json(RESULTS_DIR / "judge_calibration.json")
        JUDGES.update(cal["final"])
        out = asyncio.run(_run(rn))
        write_json(RESULTS_DIR / "judges_run.json", out)
        logger.info(f"judges: {out}")


if __name__ == "__main__":
    main()
