"""(0d) 'Other' audit: pool, deterministic features (Step A), two blind judges + tie-break (Step B).

Judges never see the condition, the banned algorithm or the model. Correctness comes from the recorded hidden-test
outcome (and re-runs for NOVEL candidates), never from a judge.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.labels import catalogue_descriptions, spec
from src.paths import WS, cite, p
from src.rows import load_codes
from src.stats import cell_seed

AUDIT = WS / "audit"
CACHE = AUDIT / "judge_cache.jsonl"
JUDGES = {"A": "openai/gpt-4.1-mini", "B": "google/gemini-2.5-flash"}
TIEBREAK = "deepseek/deepseek-chat-v3.1"
PRICES = {"openai/gpt-4.1-mini": (0.40, 1.60), "google/gemini-2.5-flash": (0.30, 2.50),
          "deepseek/deepseek-chat-v3.1": (0.25, 0.95)}
STOP_USD = 1.8
CLASSES = ("CATALOGUE_VARIANT", "LABELLER_MISS", "NOVEL", "DEGENERATE")
EXTENDED_VARIANTS = {
    "T08": "Binet's closed form (golden-ratio power with rounding); naive exponential recursion; generator loops",
    "T03": "counting sort over the value range or a value->count map walked in sorted order; nsmallest",
    "T13": "coverage/marking array over the coordinate range; sorting by end; stack-based merging",
    "T06": "counting array of occurrences; XOR/sum tricks (invalid when values repeat more than twice)",
    "T05": "dict of value->list of indices; enumerate-based double loop",
    "T10": "iterative DFS with an explicit stack; BFS with collections.deque",
    "T04": "str.find / str.index (builtin); slicing comparisons",
    "T14": "Counter.most_common; sorting items by (-count, value)",
}


# ------------------------------------------------------------------------------------------------ pool
def build_pool(rows: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Every iteration-3 ban event with >= 5 'other' attempts: exp13 ban, exp16 a, exp15 modal/present-minor,
    exp14 named/unnamed per shown algorithm."""
    sel = []
    specs = [
        ("art_1AYTO1Epb_7t", lambda a: a == "ban", "exp13", "data/samples.jsonl"),
        ("art__5akZ9W9iZM4", lambda a: a == "a", "exp16", "data/samples.jsonl"),
        ("art_Q-qh-9HhPoWo", lambda a: a.startswith("ban_"), "exp15", "data/samples.jsonl"),
        ("art_WiY4wqHLb9Gy", lambda a: a.startswith("named:") or a.startswith("unnamed:"), "exp14", "data/samples.jsonl"),
    ]
    events = []
    for aid, armf, exp, rel in specs:
        sub = rows[(rows.artifact_id == aid) & rows.arm.map(armf)]
        for (task, arm), g in sub.groupby(["task", "arm"]):
            oth = g[g.label_norm == "other"]
            if len(oth) >= 5:
                events.append({"event_id": f"{exp}:{task}:{arm}", "artifact_id": aid, "exp": exp, "src": rel,
                               "task": task, "arm": arm, "n_other_attempts": int(len(oth)),
                               "n_attempted": int(g.attempted.sum()), "rows": oth})
    # dedupe within event by sha, then cap
    uniq_all = set()
    for e in events:
        e["shas"] = list(dict.fromkeys(e["rows"].code_sha256.tolist()))
        uniq_all.update(e["shas"])
    cap = 25 if len(uniq_all) > 220 else 40
    logger.info(f"0d pool: {len(events)} events, {len(uniq_all)} unique 'other' programs; cap {cap}/event")
    codes: dict[str, dict[str, str]] = {}
    out_rows = []
    for e in events:
        if e["exp"] not in codes:
            codes[e["exp"]] = load_codes(e["exp"], e["src"])
        shas = sorted(e["shas"])
        rnd = random.Random(cell_seed(e["event_id"]))
        sampled = shas if len(shas) <= cap else sorted(rnd.sample(shas, cap))
        e["n_unique"] = len(shas)
        e["n_sampled"] = len(sampled)
        passed_by_sha = e["rows"].groupby("code_sha256").passed.max().to_dict()
        mult = e["rows"].code_sha256.value_counts().to_dict()
        for h in sampled:
            out_rows.append({"event_id": e["event_id"], "artifact_id": e["artifact_id"], "task": e["task"],
                             "code_sha256": h, "passed": bool(passed_by_sha.get(h, False)),
                             "multiplicity": int(mult.get(h, 1)), "code": codes[e["exp"]].get(h, ""),
                             "source": cite(e["exp"], e["src"])})
    ev_meta = [{k: v for k, v in e.items() if k not in ("rows", "shas")} for e in events]
    return pd.DataFrame(out_rows), ev_meta


# ------------------------------------------------------------------------------------------------ Step A
def _ast_tokens(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    toks: list[str] = []

    def visit(n: ast.AST) -> None:
        t = type(n).__name__
        if isinstance(n, ast.Attribute):
            t += ":" + n.attr
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            t += ":" + (n.func.id if n.func.id in BUILTIN_NAMES else "f")
        elif isinstance(n, ast.Constant):
            t += ":" + (repr(n.value) if n.value in (0, 1, -1, True, False, None) else type(n.value).__name__)
        elif isinstance(n, (ast.BinOp, ast.AugAssign)):
            t += ":" + type(n.op).__name__
        elif isinstance(n, ast.Compare):
            t += ":" + ",".join(type(o).__name__ for o in n.ops)
        toks.append(t)
        for c in ast.iter_child_nodes(n):
            visit(c)

    visit(tree)
    return toks


BUILTIN_NAMES = {"sorted", "len", "range", "min", "max", "sum", "set", "dict", "list", "enumerate", "zip", "abs",
                 "int", "float", "round", "pow", "map", "reversed", "any", "all", "bytearray", "divmod", "tuple"}


def ngrams(toks: list[str], n: int = 4) -> set[tuple[str, ...]]:
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def known_pool() -> dict[str, list[tuple[str, set]]]:
    """task -> [(label, 4-gram set)] from exp11 references and correct, adherent forced programs."""
    from src.labels import BENCH_DIRS
    out: dict[str, list[tuple[str, set]]] = defaultdict(list)
    for task, d in BENCH_DIRS.items():
        for f in sorted(p("exp11", f"bench/{d}/references").glob("*.py")):
            out[task].append((f.stem, ngrams(_ast_tokens(f.read_text()))))
    for line in p("exp11", "data/samples_forced.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if (r.get("passed") is True or str(r.get("passed")) == "True") and r.get("label") == r.get("forced_mode"):
            out[r["task"]].append((r["label"], ngrams(_ast_tokens(r.get("code") or ""))))
    return out


def features(code: str, passed: bool) -> dict[str, Any]:
    f: dict[str, Any] = {"passed": bool(passed), "n_lines": len(code.splitlines())}
    f["imports"] = sorted(set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", code, re.M)))
    f["uses_sort"] = bool(re.search(r"\bsorted\(|\.sort\(", code))
    f["uses_heapq"] = "heapq" in code
    f["uses_deque"] = "deque" in code
    f["uses_set"] = bool(re.search(r"\bset\(|\{\s*\}|\.add\(", code))
    f["uses_dict"] = bool(re.search(r"\bdict\(|defaultdict|Counter|\{\s*\}|\[\s*\w+\s*\]\s*=", code))
    f["mark_array"] = bool(re.search(r"\[\s*(False|0|None)\s*\]\s*\*|bytearray\(|\b(covered|cover|mark|marked|"
                                     r"visited_pos|line|timeline)\b", code))
    f["binet"] = bool(re.search(r"sqrt\(\s*5|5\s*\*\*\s*0?\.5|1\.618|golden|phi\b", code))
    try:
        tree = ast.parse(code)
        fn_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        f["recursion"] = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in fn_names
                             for fd in ast.walk(tree) if isinstance(fd, ast.FunctionDef) for n in ast.walk(fd)
                             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == fd.name)

        def depth(n: ast.AST, d: int = 0) -> int:
            here = d + isinstance(n, (ast.For, ast.While))
            return max([here] + [depth(c, here) for c in ast.iter_child_nodes(n)])

        f["loop_depth"] = depth(tree)
        f["parses"] = True
    except (SyntaxError, ValueError, RecursionError):
        f["recursion"], f["loop_depth"], f["parses"] = None, None, False
    return f


def step_a(pool: pd.DataFrame) -> pd.DataFrame:
    kp = known_pool()
    feats, near_lab, near_j = [], [], []
    for _, r in pool.iterrows():
        feats.append(features(r.code, r.passed))
        g = ngrams(_ast_tokens(r.code))
        best = ("", 0.0)
        for lab, s in kp.get(r.task, []):
            j = jaccard(g, s)
            if j > best[1]:
                best = (lab, j)
        near_lab.append(best[0])
        near_j.append(round(best[1], 4))
    pool = pool.copy()
    pool["features"] = [json.dumps(f, sort_keys=True) for f in feats]
    pool["nearest_known_label"] = near_lab
    pool["nearest_known_jaccard"] = near_j
    return pool


# ------------------------------------------------------------------------------------------------ Step B
SYSTEM = ("You are a careful algorithms auditor. You classify ONE Python program written for a programming task. "
          "Answer with a single JSON object only.")


def judge_prompt(task: str, code: str, passed: bool) -> str:
    sp = spec(task)
    cat = catalogue_descriptions(task)
    cat_txt = "\n".join(f"- {m}: {d}" for m, d in cat.items())
    ext = EXTENDED_VARIANTS.get(task, "none listed")
    return (f"TASK ({task}):\n{sp.get('spec_text') or sp.get('description')}\n\n"
            f"CATALOGUE of known algorithms for this task (mode: description):\n{cat_txt}\n\n"
            f"KNOWN EXTENDED VARIANTS (not catalogue modes, but well known): {ext}\n\n"
            f"PROGRAM:\n```python\n{code[:6000]}\n```\n"
            f"HIDDEN-TEST OUTCOME: {'passed all hidden tests' if passed else 'failed at least one hidden test'}\n\n"
            "Classify the program's algorithm into exactly one class:\n"
            "- LABELLER_MISS: it implements one of the catalogue modes as described (possibly with cosmetic changes);\n"
            "- CATALOGUE_VARIANT: a recognisable known algorithm that is not exactly a catalogue mode (an extended "
            "variant, a textbook algorithm outside the catalogue, or a hybrid of catalogue modes);\n"
            "- NOVEL: a genuinely new algorithmic idea for this task that you cannot find in textbooks or common "
            "solutions;\n"
            "- DEGENERATE: not a coherent algorithm for the task (hard-coded or truncated output, broken or "
            "incomplete code, solves a different problem).\n"
            'Return JSON: {"class": "...", "nearest_catalogue_mode": "<one catalogue mode or none>", '
            '"named_algorithm": "<short name>", "rationale": "<under 60 words>"}')


def _pkey(model: str, prompt: str) -> str:
    return model + "|" + hashlib.sha256(prompt.encode()).hexdigest()


def load_cache() -> dict[str, dict]:
    out = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["key"]] = r
    return out


def parse_json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    c = str(d.get("class", "")).upper().replace(" ", "_")
    d["class"] = c if c in CLASSES else None
    return d


class Budget:
    def __init__(self, spent: float) -> None:
        self.spent = spent
        self.stop = False
        self.reason = ""


async def _call(client, model: str, prompt: str, sem: asyncio.Semaphore, budget: Budget, cache: dict,
                fh) -> dict | None:
    key = _pkey(model, prompt)
    if key in cache:
        return cache[key]
    async with sem:
        if budget.stop:
            return None
        extra: dict[str, Any] = {"usage": {"include": True}}
        if model.startswith("google/"):
            extra["reasoning"] = {"max_tokens": 0}
        kw: dict[str, Any] = {}
        if model.startswith("openai/"):
            kw["response_format"] = {"type": "json_object"}
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=model, temperature=0, max_tokens=400,
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                    extra_body=extra, timeout=90, **kw)
                break
            except Exception as e:  # noqa: BLE001 - classify API errors below
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg or ("403" in msg and "budget" in msg.lower()):
                    budget.stop = True
                    budget.reason = "openrouter_budget_403"
                    logger.error(f"budget 403 from {model}: stopping all judge calls")
                    return None
                logger.warning(f"{model} attempt {attempt}: {msg[:200]}")
                await asyncio.sleep(2 + 3 * attempt)
        else:
            return None
        text = resp.choices[0].message.content or ""
        u = resp.usage
        cost = None
        if u is not None:
            cost = getattr(u, "cost", None)
            if cost is None and getattr(u, "model_extra", None):
                cost = u.model_extra.get("cost")
            if cost is None:
                pi, po = PRICES.get(model, (1.0, 4.0))
                cost = (u.prompt_tokens * pi + u.completion_tokens * po) / 1e6
        budget.spent += float(cost or 0.0)
        if budget.spent >= STOP_USD:
            budget.stop = True
            budget.reason = f"running total reached USD {budget.spent:.3f}"
        rec = {"key": key, "model": model, "text": text, "parsed": parse_json(text), "cost": cost,
               "prompt_tokens": getattr(u, "prompt_tokens", None), "completion_tokens": getattr(u, "completion_tokens", None)}
        cache[key] = rec
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        logger.debug(f"judge {model}: {text[:160]!r} cost={cost}")
        return rec


def controls() -> list[dict]:
    from src.labels import BENCH_DIRS
    pos = [("T03", "quickselect"), ("T06", "floyd"), ("T08", "fast_doubling"), ("T10", "label_propagation"),
           ("T13", "interval_tree"), ("T04", "kmp")]
    out = []
    for t, m in pos:
        code = p("exp11", f"bench/{BENCH_DIRS[t]}/references/{m}.py").read_text()
        out.append({"control_id": f"pos:{t}:{m}", "task": t, "code": code, "passed": True, "expected": "LABELLER_MISS",
                    "expected_mode": m})
    ss = p("exp11", f"bench/{BENCH_DIRS['T13']}/references/sort_sweep.py").read_text().splitlines()
    uf = p("exp11", f"bench/{BENCH_DIRS['T10']}/references/union_find.py").read_text().splitlines()
    neg = [("T03", "def solve(nums, k):\n    return 0\n"),
           ("T05", "def solve(nums, target):\n    return [0, 1]\n"),
           ("T13", "\n".join(ss[: max(2, len(ss) // 2)]) + "\n"),
           ("T10", "\n".join(uf[: max(2, len(uf) // 3)]) + "\n")]
    for i, (t, code) in enumerate(neg):
        out.append({"control_id": f"neg:{t}:{i}", "task": t, "code": code, "passed": False, "expected": "DEGENERATE",
                    "expected_mode": None})
    return out


async def run_judges(pool: pd.DataFrame, spent_before: float = 0.0) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
    cache = load_cache()
    budget = Budget(spent_before)
    sem = asyncio.Semaphore(8)
    progs = pool.drop_duplicates("code_sha256")[["code_sha256", "task", "code", "passed"]].to_dict("records")
    ctrl = controls()
    items = [{"id": r["code_sha256"], "task": r["task"], "code": r["code"], "passed": r["passed"]} for r in progs]
    items += [{"id": c["control_id"], "task": c["task"], "code": c["code"], "passed": c["passed"]} for c in ctrl]
    with CACHE.open("a") as fh:
        tasks = []
        for it in items:
            pr = judge_prompt(it["task"], it["code"], it["passed"])
            for j, model in JUDGES.items():
                tasks.append((it["id"], j, model, pr))
        res = await asyncio.gather(*[_call(client, m, pr, sem, budget, cache, fh) for (_, _, m, pr) in tasks])
        verdicts: dict[str, dict] = defaultdict(dict)
        for (iid, j, _, _), r in zip(tasks, res):
            verdicts[iid][j] = (r or {}).get("parsed")
        # tie-break on class disagreement only
        tb_jobs = []
        for it in items:
            v = verdicts[it["id"]]
            ca = (v.get("A") or {}).get("class")
            cb = (v.get("B") or {}).get("class")
            if ca and cb and ca != cb:
                tb_jobs.append((it["id"], judge_prompt(it["task"], it["code"], it["passed"])))
        res2 = await asyncio.gather(*[_call(client, TIEBREAK, pr, sem, budget, cache, fh) for _, pr in tb_jobs])
        for (iid, _), r in zip(tb_jobs, res2):
            verdicts[iid]["C"] = (r or {}).get("parsed")
    out = {"verdicts": verdicts, "spent_usd": budget.spent, "stopped": budget.stop, "stop_reason": budget.reason,
           "n_items": len(items), "n_tiebreak": len(tb_jobs), "controls": ctrl}
    return out
