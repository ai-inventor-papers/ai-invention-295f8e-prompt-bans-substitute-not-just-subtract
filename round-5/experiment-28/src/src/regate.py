#!/usr/bin/env python3
"""STAGE 0 STYLE RE-GATE (CPU + OpenRouter judges; before commit #1 and before any push sample).

5a re-check (results/labeller_recheck.json, src/stage_inputs.py --recheck) and the T2 fix (src/regate_rules.py,
CPU tests T2/T3) are produced elsewhere; this module adds:
5c RE-GATE SAMPLE: 30 it-twin programs (2 per task, stratified by runtime label) + 30 pt programs (2 per task; pt-chat
   where valid code exists, else pt plain completion) judged blind by google/gemini-2.5-flash and openai/gpt-4.1-mini
   (task description + catalogue mechanism texts + 'other'; no condition, no model identity), tie-break
   deepseek/deepseek-chat-v3.1 -> adjudicated labels. Gate per labeller family (bench / exp8 suite): references 100%,
   runtime-vs-AST Cohen kappa >= 0.8 (pooled over tasks, all valid Stage-1 programs), runtime vs adjudicated >= 0.9.
5d STRUCTURAL AUDIT: per task up to 3 programs each of the it default, the it runner-up, the pt default and the pt
   runner-up read by the two judges (+ deterministic structure counts: heap vs array Dijkstra, deque vs list queue,
   recursion vs explicit stack, nsmallest vs explicit heap); a modal 'other' structure is reported.
5e APPENDIX: exp23's 10,730 iteration-4 rows re-scored under the re-gated T2 rule (results/iter4_rescored.json).
"""

from __future__ import annotations

import ast
import asyncio
import collections
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BUDGET_MSG, DATA_DIR, E23, LOG_DIR, OPENROUTER_CAP_USD, PATH_TASKS, RESULTS_DIR,
                 read_json, read_jsonl, setup_logging, write_json)
from regate_rules import EXTENDED_LABELS, apply_t2, t2_array_dijkstra

LEDGER = LOG_DIR / "openrouter_spend_regate.jsonl"
JUDGES = ("google/gemini-2.5-flash", "openai/gpt-4.1-mini")
TIEBREAK = "deepseek/deepseek-chat-v3.1"
CACHE = DATA_DIR / "judge_cache_regate.jsonl"


def total_spend() -> float:
    s = 0.0
    for p in sorted(LOG_DIR.glob("openrouter_spend*.jsonl")):
        s += sum((json.loads(l).get("cost") or 0.0) for l in p.read_text().splitlines() if l.strip())
    for p in sorted(RESULTS_DIR.glob("openrouter_cost_paths*.json")):
        s += float(read_json(p).get("total_usd", 0.0))
    return s


def catalogue_text(t: str) -> tuple[str, list[str]]:
    import prompts as PG

    mech = PG.mechanism_texts(t)
    labs = list(mech) + [m for m in EXTENDED_LABELS.get(t, []) if m not in mech]
    ext = {"linear_scan": "scan the list element by element (no halving search) to find the first and last index"}
    lines = [f"- {m}: {mech.get(m, ext.get(m, m))}" for m in labs]
    return "\n".join(lines), labs


def judge_prompt(t: str, code: str) -> str:
    import prompts as PG

    cat, _ = catalogue_text(t)
    return (f"You label which algorithm a Python program implements.\n\nTask given to the programmer:\n"
            f"{PG.description(t)}\n\nCandidate labels (choose exactly one):\n{cat}\n- other: the program's main "
            "mechanism matches none of the labels above\n\nJudge the mechanism the code actually executes (data "
            "structures, selection and exploration order), not identifiers or comments. Recursion versus iteration "
            "does not change the label unless the labels say so. If the program is buggy, label the mechanism it "
            "attempts.\n\nProgram:\n```python\n" + code[:6000] + "\n```\n\nAnswer with JSON only: "
            '{"label": "<one label id>", "rationale": "<one short sentence>"}')


def parse_label(txt: str | None, labs: list[str]) -> str | None:
    if not txt:
        return None
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            lab = str(json.loads(m.group(0)).get("label", "")).strip()
            if lab in labs or lab == "other":
                return lab
        except json.JSONDecodeError:
            pass
    for l in labs + ["other"]:
        if re.search(rf'"{re.escape(l)}"', txt):
            return l
    return None


class Client:
    def __init__(self, cap: float):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=90, max_retries=2)
        self.cap = cap
        self.stop = False
        self.reason = None
        self.cache = {}
        if CACHE.exists():
            for l in CACHE.read_text().splitlines():
                if l.strip():
                    r = json.loads(l)
                    self.cache[r["key"]] = r["text"]

    async def ask(self, sem: asyncio.Semaphore, model: str, prompt: str, purpose: str, max_tokens: int = 200) -> str | None:
        key = f"{model}|" + __import__("hashlib").sha256(prompt.encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        async with sem:
            if self.stop:
                return None
            if total_spend() >= self.cap:
                self.stop, self.reason = True, "artifact cap reached"
                return None
            try:
                r = await self.client.chat.completions.create(model=model, temperature=0, max_tokens=max_tokens,
                                                              messages=[{"role": "user", "content": prompt}])
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if BUDGET_MSG in msg:
                    self.stop, self.reason = True, "budget_403"
                    logger.error("OpenRouter phase budget exhausted: stopping the batch")
                else:
                    logger.warning(f"{model} call failed: {msg[:200]}")
                return None
            if self.stop:
                return None
            cost = float(getattr(r.usage, "cost", 0.0) or 0.0) if r.usage else 0.0
            txt = r.choices[0].message.content or ""
            with LEDGER.open("a") as f:
                f.write(json.dumps({"purpose": purpose, "model": model, "cost": cost}) + "\n")
            with CACHE.open("a") as f:
                f.write(json.dumps({"key": key, "text": txt}) + "\n")
            self.cache[key] = txt
            return txt


async def adjudicate(items: list[dict[str, Any]], purpose: str, cl: Client) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(12)
    out = []
    labs_of = {it["task"]: catalogue_text(it["task"])[1] for it in items}
    res = await asyncio.gather(*[asyncio.gather(*[cl.ask(sem, j, judge_prompt(it["task"], it["code"]), purpose)
                                                  for j in JUDGES]) for it in items])
    need = []
    for it, (a, b) in zip(items, res):
        A_, B_ = parse_label(a, labs_of[it["task"]]), parse_label(b, labs_of[it["task"]])
        rec = {**{k: it[k] for k in it if k != "code"}, "judge_A": A_, "judge_B": B_}
        if A_ and A_ == B_:
            rec["adjudicated"] = A_
        else:
            need.append(len(out))
        out.append(rec)
    if need and not cl.stop:
        rc = await asyncio.gather(*[cl.ask(sem, TIEBREAK, judge_prompt(items[i]["task"], items[i]["code"]), purpose)
                                    for i in need])
        for i, c in zip(need, rc):
            C_ = parse_label(c, labs_of[items[i]["task"]])
            out[i]["judge_C"] = C_
            votes = collections.Counter(x for x in (out[i]["judge_A"], out[i]["judge_B"], C_) if x)
            top = votes.most_common(1)
            out[i]["adjudicated"] = top[0][0] if top and top[0][1] >= 2 else (C_ or "UNRESOLVED")
    for o in out:
        o.setdefault("adjudicated", "UNRESOLVED")
    return out


def kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def family(t: str) -> str:
    return "suite" if t in PATH_TASKS else "bench"


# ------------------------------------------------------------------------------------------------ structure counts
def structure_tags(t: str, code: str | None) -> dict[str, Any]:
    if not code:
        return {}
    tags: dict[str, Any] = {}
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return {"parse_error": True}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    names = {getattr(c.func, "attr", getattr(c.func, "id", "")) for c in calls}
    fn_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    recursive = any(isinstance(c.func, ast.Name) and c.func.id in fn_names for c in calls)
    if t == "T2":
        tags["heap"] = bool(names & {"heappush", "heappop"})
        tags["array_dijkstra"] = t2_array_dijkstra(code)[0]
    if t in ("T1", "T10", "R2", "R3"):
        tags["deque_popleft"] = "popleft" in names
        tags["list_pop0"] = any(getattr(c.func, "attr", "") == "pop" and c.args and isinstance(c.args[0], ast.Constant)
                                and c.args[0].value == 0 for c in calls)
        tags["recursive"] = recursive
        tags["explicit_stack_pop"] = any(getattr(c.func, "attr", "") == "pop" and not c.args for c in calls)
    if t == "T03":
        tags["nsmallest"] = "nsmallest" in names
        tags["explicit_heap"] = bool(names & {"heappush", "heappushpop", "heapreplace"})
    return tags


# ------------------------------------------------------------------------------------------------ main pieces
def sample_regate(labs: list[dict[str, Any]], seed: int = 0) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    items = []
    for t in ALL_TASKS:
        tw = [r for r in labs if r.get("stage") == "twin" and r["task"] == t and r.get("valid") and r.get("code")]
        by = collections.defaultdict(list)
        for r in tw:
            by[r.get("runtime_label")].append(r)
        strata = sorted(by, key=lambda k: -len(by[k]))
        pick = []
        for k in strata:
            if len(pick) < 2 and by[k]:
                pick.append(rng.choice(sorted(by[k], key=lambda r: r["row_id"])))
        while len(pick) < 2 and len(tw) > len(pick):
            c = rng.choice(sorted(tw, key=lambda r: r["row_id"]))
            if c not in pick:
                pick.append(c)
        pt = [r for r in labs if r.get("stage") == "ptchat" and r["task"] == t and r.get("valid") and r.get("code")]
        src = "pt_chat"
        if len(pt) < 2:
            pt += [r for r in labs if r.get("stage") == "ptplain" and r["task"] == t and r.get("valid") and r.get("code")]
            src = "pt_chat+pt_plain"
        pp = rng.sample(sorted(pt, key=lambda r: r["row_id"]), min(2, len(pt)))
        for r in pick:
            items.append({"row_id": r["row_id"], "task": t, "model": "it", "runtime_label": r.get("runtime_label"),
                          "ast_label": r.get("ast_label"), "label": r["label"], "code": r["code"], "source": "it_twin"})
        for r in pp:
            items.append({"row_id": r["row_id"], "task": t, "model": "pt", "runtime_label": r.get("runtime_label"),
                          "ast_label": r.get("ast_label"), "label": r["label"], "code": r["code"],
                          "source": src if r.get("stage") == "ptchat" else "pt_plain"})
    return items


def gate(labs: list[dict[str, Any]], adj: list[dict[str, Any]]) -> dict[str, Any]:
    lr = read_json(RESULTS_DIR / "labeller_recheck.json")
    tc = read_json(RESULTS_DIR / "tests_cpu.json")
    out = {}
    for fam in ("bench", "suite"):
        st1 = [r for r in labs if r.get("stage") in ("twin", "novelty", "ptchat", "ptplain") and r.get("valid")
               and family(r["task"]) == fam and r.get("runtime_label") is not None]
        rt = [str(r["runtime_label"]) for r in st1]
        at = [str(r["ast_label"]) for r in st1]
        k = kappa(rt, at)
        sam = [a for a in adj if family(a["task"]) == fam and a["adjudicated"] not in ("UNRESOLVED", None)]
        acc = (sum(1 for a in sam if a["runtime_label"] == a["adjudicated"]) / len(sam)) if sam else None
        acc_final = (sum(1 for a in sam if a["label"] == a["adjudicated"]) / len(sam)) if sam else None
        if fam == "bench":
            refs_ok = all(v["references_pass"] for v in lr["bench"].values())
        else:
            refs_ok = lr["exp8_suite"]["references_ok"] == lr["exp8_suite"]["n_references"] \
                and tc["T2_t2_rule_references"]["all_references_ok"]
        per_task = {}
        for t in sorted({a["task"] for a in sam}):
            ss = [a for a in sam if a["task"] == t]
            per_task[t] = {"n": len(ss), "runtime_vs_adj": sum(1 for a in ss if a["runtime_label"] == a["adjudicated"]) / len(ss),
                           "final_vs_adj": sum(1 for a in ss if a["label"] == a["adjudicated"]) / len(ss)}
        failing = sorted(t for t, v in per_task.items() if v["final_vs_adj"] < 0.75)
        out[fam] = {"n_stage1_valid": len(st1), "kappa_runtime_vs_ast": k, "n_sample": len(sam),
                    "runtime_vs_adjudicated": acc, "final_label_vs_adjudicated": acc_final, "references_100": refs_ok,
                    "pass": bool(refs_ok and k is not None and k >= 0.8 and acc is not None and acc >= 0.9),
                    "per_task": per_task, "tasks_below_0.75": failing,
                    "runtime_ast_disagreement_rate": (sum(1 for x, y in zip(rt, at) if x != y) / len(rt)) if rt else None}
    return out


def structural_audit(labs: list[dict[str, Any]], cl: Client, per_group: int = 3) -> dict[str, Any]:
    from predictors import catalogue

    rng = random.Random(5)
    items = []
    summary: dict[str, Any] = {}
    for t in ALL_TASKS:
        cat = catalogue(t)
        groups = {}
        for model, stages in (("it", ("twin",)), ("pt", ("ptchat", "ptplain"))):
            rr = [r for r in labs if r.get("stage") in stages and r["task"] == t and r.get("passed") and r.get("code")]
            cnt = collections.Counter(r["label"] for r in rr)
            ranked = [m for m, _ in cnt.most_common()]
            dflt = ranked[0] if ranked else None
            ru = next((m for m in ranked[1:] if m in cat), None)
            groups[f"{model}_default"] = (dflt, [r for r in rr if r["label"] == dflt])
            groups[f"{model}_runner_up"] = (ru, [r for r in rr if r["label"] == ru])
            tags = collections.Counter()
            for r in rr:
                for k, v in structure_tags(t, r["code"]).items():
                    if v is True:
                        tags[f"{r['label']}:{k}"] += 1
            summary.setdefault(t, {})[f"{model}_structure_counts"] = dict(tags)
            summary[t][f"{model}_correct_composition"] = dict(cnt)
            summary[t][f"{model}_modal_other"] = dflt == "other"
        for g, (lab, rr) in groups.items():
            if not lab:
                continue
            for r in rng.sample(sorted(rr, key=lambda x: x["row_id"]), min(per_group, len(rr))):
                items.append({"row_id": r["row_id"], "task": t, "group": g, "runtime_label": r.get("runtime_label"),
                              "ast_label": r.get("ast_label"), "label": r["label"], "code": r["code"]})
    adj = asyncio.run(adjudicate(items, "structural_audit", cl)) if items and not cl.stop else []
    for a in adj:
        s = summary[a["task"]].setdefault("judged", collections.Counter())
        s[f"{a['group']}|{a['label']}->{a['adjudicated']}"] += 1
    for t in summary:
        if "judged" in summary[t]:
            summary[t]["judged"] = dict(summary[t]["judged"])
    n = len([a for a in adj if a["adjudicated"] != "UNRESOLVED"])
    agree = sum(1 for a in adj if a["adjudicated"] == a["label"])
    misreads = [{k: a[k] for k in ("row_id", "task", "group", "label", "adjudicated", "judge_A", "judge_B")}
                for a in adj if a["adjudicated"] not in ("UNRESOLVED", a["label"])]
    return {"n_items": len(items), "n_resolved": n, "agreement": agree / n if n else None, "per_task": summary,
            "misreads": misreads, "rows": adj}


def iter4_rescore() -> dict[str, Any]:
    """Apply the re-gated T2 rule to exp23's stored T2 programs (runtime/AST labels as stored; a new runtime/AST
    agreement replaces a judge/disputed label; R6 already carried 'linear_scan'). Recompute exp23's E_t for T2 with
    exp23's own escape rule (off-default = not D / invalid / disputed, 8 directions, max over alpha) and A_t."""
    from scipy import stats

    rows = read_jsonl(E23 / "data" / "samples.jsonl")
    changed = 0
    new = []
    for r in rows:
        r2 = dict(r)
        if r["task"] == "T2" and r.get("code"):
            rl, _ = apply_t2(r.get("runtime_label"), r["code"])
            al, _ = apply_t2(r.get("ast_label"), r["code"])
            if rl == al and rl not in ("unknown", "inconsistent", None):
                lab = rl
            elif r["label"] in ("bf_spfa", "disputed", "unknown") and (rl == "dijkstra" or al == "dijkstra"):
                lab = "dijkstra"
            else:
                lab = r["label"]
            if lab != r["label"]:
                changed += 1
            r2["label"] = lab
        new.append(r2)
    out: dict[str, Any] = {"n_rows": len(rows), "n_T2_labels_changed": changed}
    D = "dijkstra"
    tw = [r for r in new if r["task"] == "T2" and r.get("stage") == "A" and r["arm"] == "twin"]

    def off(rr):
        return sum(1 for r in rr if r["label"] not in (D, "invalid", "disputed")) / len(rr) if rr else float("nan")

    def pas(rr):
        return sum(1 for r in rr if r.get("passed")) / len(rr) if rr else float("nan")
    p0, pt = off(tw), pas(tw)
    conf = {}
    for s in range(9001, 9009):
        for a in (1, 2):
            arm = f"esc{s}_a{a}"
            s1 = [r for r in new if r["task"] == "T2" and r.get("stage") == "A" and r["arm"] == arm]
            if not (s1 and off(s1) - p0 >= 0.2 and pas(s1) >= 0.8 * pt):
                continue
            allr = s1 + [r for r in new if r["task"] == "T2" and r.get("stage") == "B" and r["arm"] == arm]
            k = sum(1 for r in allr if r["label"] not in (D, "invalid", "disputed"))
            pb = float(stats.binom.sf(k - 1, len(allr), max(p0, 0.01)))
            conf[arm] = {"n": len(allr), "off": k / len(allr), "pass": pas(allr), "binom_p": pb,
                         "confirmed": len(allr) >= 30 and k / len(allr) - p0 >= 0.2 and pas(allr) >= 0.8 * pt and pb < 0.05}
    E = max(sum(1 for k, v in conf.items() if v["confirmed"] and k.endswith(f"_a{a}")) / 8 for a in (1, 2))
    bans = [r for r in new if r["task"] == "T2" and r.get("stage") == "BAN" and r["arm"] == "ban"]
    surv = {"bf_spfa", "bidijkstra", "dial", "floyd"}
    A_t = sum(1 for r in bans if r["label"] in surv) / len(bans) if bans else None
    out["T2"] = {"E_t_iter4_frozen": 0.25, "E_t_rescored": E, "cells": conf, "A_t_iter4_frozen": 0.96,
                 "A_t_rescored": A_t, "ban_composition_rescored": dict(collections.Counter(r["label"] for r in bans))}
    tasks_twin = collections.defaultdict(collections.Counter)
    for r in new:
        if r.get("stage") == "A" and r["arm"] == "twin":
            tasks_twin[r["task"]][r["label"]] += 1
    out["twin_compositions_rescored"] = {t: dict(c) for t, c in tasks_twin.items()}
    out["label"] = "descriptive appendix: iteration-4 rows under the re-gated T2 rule (no new judge calls)"
    return out


def main() -> None:
    setup_logging("regate")
    labs = read_jsonl(DATA_DIR / "labels.jsonl")
    cl = Client(OPENROUTER_CAP_USD)
    items = sample_regate(labs)
    logger.info(f"re-gate sample: {len(items)} programs")
    adj = asyncio.run(adjudicate(items, "regate_sample", cl))
    g = gate(labs, adj)
    logger.info(f"gate: { {k: (v['pass'], v['kappa_runtime_vs_ast'], v['runtime_vs_adjudicated']) for k, v in g.items()} }")
    sa = structural_audit(labs, cl)
    logger.info(f"structural audit: {sa['n_items']} items, agreement {sa['agreement']}, misreads {len(sa['misreads'])}")
    i4 = iter4_rescore()
    write_json(RESULTS_DIR / "iter4_rescored.json", i4)
    logger.info(f"iter4 rescored: T2 {i4['T2']['E_t_rescored']} (frozen 0.25), A_t {i4['T2']['A_t_rescored']}")
    res = {"sample": adj, "gate": g, "judges": list(JUDGES), "tiebreak": TIEBREAK,
           "t2_fix": {"rule": "src/regate_rules.py", "reference": "extensions/t2_wsp/dijkstra_array.py",
                      "tests": "results/tests_cpu.json T2/T3"},
           "extended_labels": EXTENDED_LABELS,
           "r6_linear_scan_reference": "extensions/R6/linear_scan.py (passes 56/56 hidden tests; labelled linear_scan)",
           "revision_round": "none needed" if all(v["pass"] for v in g.values()) else "see flagged tasks",
           "flagged_tasks": sorted(set(sum((v["tasks_below_0.75"] for v in g.values()), []))),
           "spend_usd_total_artifact": total_spend(), "stopped": cl.reason}
    write_json(RESULTS_DIR / "regate.json", res)
    write_json(RESULTS_DIR / "structural_audit.json", sa)
    logger.info(f"re-gate done; spend so far {total_spend():.3f} USD")


if __name__ == "__main__":
    main()
