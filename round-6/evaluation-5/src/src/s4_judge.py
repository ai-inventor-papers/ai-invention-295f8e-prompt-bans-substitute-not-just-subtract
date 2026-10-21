"""S4: third-family blind adjudication of the 14 transplant programs two of three judges called novel (exp24).

Design frozen in frozen/adjudication_design.json before any call. Judge: anthropic/claude-haiku-4.5 (fallbacks
mistralai/mistral-medium-3.1, meta-llama/llama-4-maverick), temperature 0, items + 8 controls shuffled with seed 6006,
two passes with the nearest known solutions in opposite orders. Running cost from usage.cost; hard stop at USD 0.45;
the whole batch stops at the first HTTP 403 whose message starts 'AI Inventor per-run OpenRouter budget'.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import io
import json
import keyword
import os
import random
import re
import threading
import time
import tokenize
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from loguru import logger

from common import WS, Inputs, cohen_kappa, gwet_ac1, parse_dictish, prov, write_json
from load import BENCH_DIR

HARD_STOP_USD = 0.45
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
CLASSES = ["NOVEL_ALGORITHM", "CATALOGUE_VARIANT", "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE", "LABELLER_MISS", "DEGENERATE"]
MANUAL_MAP = {"KNOWN, OUTSIDE THE CATALOGUE": "KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE", "CATALOGUE VARIANT": "CATALOGUE_VARIANT",
              "DEGENERATE": "DEGENERATE", "NOVEL ALGORITHM": "NOVEL_ALGORITHM", "LABELLER MISS": "LABELLER_MISS"}
SYSTEM = ("You audit whether a Python program implements a genuinely new algorithm for a coding task. Judge only the "
          "code's mechanism. Be strict: an algorithm is NOVEL only if it is neither a catalogue mode, nor a variant of "
          "one, nor a recognised textbook, library or published technique. Return only one JSON object.")


# ------------------------------------------------------------------------------------------------ code utilities
def strip_comments(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and node.body:
            b0 = node.body[0]
            if isinstance(b0, ast.Expr) and isinstance(getattr(b0, "value", None), ast.Constant) and isinstance(b0.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


class _Scrub(ast.NodeTransformer):
    def __init__(self, tokens: set[str]) -> None:
        self.tokens, self.map = tokens, {}

    def _new(self, name: str) -> str:
        if name == "solve" or not any(t in name.lower() for t in self.tokens):
            return name
        self.map.setdefault(name, f"h{len(self.map) + 1}")
        return self.map[name]

    def visit_Name(self, n: ast.Name) -> ast.Name:
        n.id = self._new(n.id)
        return n

    def visit_arg(self, n: ast.arg) -> ast.arg:
        n.arg = self._new(n.arg)
        return n

    def visit_FunctionDef(self, n: ast.FunctionDef) -> ast.FunctionDef:
        n.name = self._new(n.name)
        self.generic_visit(n)
        return n


def scrub_names(code: str, modes: list[str]) -> str:
    toks = {p for m in modes for p in m.lower().split("_") if len(p) >= 3} | {m.lower() for m in modes}
    tree = ast.parse(strip_comments(code))
    return ast.unparse(_Scrub(toks).visit(tree))


def norm_tokens(code: str) -> str:
    """Identifier-normalised token string: names -> 'v' (keywords and builtins kept), literals -> 'c'."""
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.NAME:
                out.append(tok.string if keyword.iskeyword(tok.string) or tok.string in dir(__builtins__) else "v")
            elif tok.type in (tokenize.NUMBER, tokenize.STRING):
                out.append("c")
            elif tok.type == tokenize.OP:
                out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return re.sub(r"\s+", " ", code)
    return " ".join(out)


def ast4(code: str) -> set[tuple]:
    try:
        seq = [type(n).__name__ for n in ast.walk(ast.parse(code))]
    except SyntaxError:
        return set()
    return {tuple(seq[i:i + 4]) for i in range(max(0, len(seq) - 3))}


def nearest(code: str, pool: list[dict], k: int = 3) -> list[dict]:
    nc, a4 = norm_tokens(code), ast4(code)
    scored = []
    for p in pool:
        r = difflib.SequenceMatcher(None, nc, p["_norm"], autojunk=False).ratio()
        j = len(a4 & p["_ast4"]) / max(1, len(a4 | p["_ast4"]))
        scored.append((r, j, p))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["source"]))
    return [{"source": s[2]["source"], "ratio": s[0], "ast4_jaccard": s[1], "code": s[2]["code"]} for s in scored[:k]]


def trunc_lines(code: str, n: int) -> str:
    ls = code.splitlines()
    return "\n".join(ls[:n]) + ("\n# ... (truncated)" if len(ls) > n else "")


# ------------------------------------------------------------------------------------------------ pools and prompts
def build_pools(inp: Inputs, tasks: set[str]) -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {t: [] for t in tasks}
    inp.json("exp18", "results/known_solutions_summary.json")  # counts only (no code): recorded for provenance
    for r in inp.jsonl("exp19", "data/known_solutions_dep.jsonl"):
        if r.get("task") in tasks and r.get("code"):
            pools[r["task"]].append({"source": f"{r['source']} ({prov('exp19', 'data/known_solutions_dep.jsonl')})", "code": r["code"]})
    full = inp.json("dataset", "full_data_out.json")
    for ds in full["datasets"]:
        if ds["dataset"] not in ("mercury", "kodcode_algorithmic", "xlcost_python", "thealgorithms_python"):
            continue
        for ex in ds["examples"]:
            bt = str(ex.get("metadata_bench_task") or "")
            t = bt.split("_")[0]
            if t in tasks and ex.get("output") and ex.get("metadata_duplicate_of") in (None, "None", ""):
                pools[t].append({"source": f"{ds['dataset']} ({prov('dataset', 'full_data_out.json')})", "code": ex["output"]})
    del full
    for t in tasks:
        for ref in sorted(inp.path("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/references/full_sort.py" if False else
                                   f"inputs/exp11/bench/{BENCH_DIR[t]}/spec.json").parent.joinpath("references").glob("*.py")):
            pools[t].append({"source": f"catalogue reference {ref.stem}", "code": ref.read_text()})
        seen, uniq = set(), []
        for p in pools[t]:
            h = norm_tokens(p["code"])
            if h in seen:
                continue
            seen.add(h)
            p["_norm"], p["_ast4"] = h, ast4(p["code"])
            uniq.append(p)
        pools[t] = uniq
    return pools


def prompt(spec: dict, code: str, known: list[dict]) -> str:
    cat = "\n".join(f"- {c['display_name']}: {c['mechanism']}" for c in spec["catalogue"])
    kn = "\n\n".join(f"[{i}] ```python\n{trunc_lines(strip_comments(k['code']), 60)}\n```" for i, k in enumerate(known))
    return (f"TASK SPECIFICATION:\n{spec['spec_text']}\n\nCATALOGUE OF KNOWN ALGORITHMS FOR THIS TASK:\n{cat}\n\n"
            f"PROGRAM TO CLASSIFY:\n```python\n{trunc_lines(code, 120)}\n```\n\n"
            f"NEAREST KNOWN SOLUTIONS (public human-written solutions and reference implementations), indexed:\n{kn}\n\n"
            "CLASSES:\n- NOVEL_ALGORITHM: not a catalogue mode, not a variant of one, and not a recognised textbook, "
            "library or published technique.\n- CATALOGUE_VARIANT: implements one of the catalogue algorithms, possibly "
            "with minor changes (name it).\n- KNOWN_TECHNIQUE_OUTSIDE_CATALOGUE: a recognised, documented technique "
            "(textbook algorithm, brute force, standard-library idiom) that is not in the catalogue (name it).\n"
            "- LABELLER_MISS: a catalogue algorithm written in such an unusual form that an automatic labeller would "
            "plausibly miss it.\n- DEGENERATE: hard-coded, special-cased, trivial or otherwise not a general algorithm "
            "for the task.\n\nAnswer with ONLY this JSON object: {\"class\": \"<one class>\", \"named_technique\": "
            "\"<name or empty>\", \"nearest_known_index\": <0, 1, 2 or null>, \"rationale\": \"<at most 40 words>\"}")


# ------------------------------------------------------------------------------------------------ calling
class Budget:
    def __init__(self) -> None:
        self.cost, self.calls, self.stop, self.reason = 0.0, 0, False, None
        self.lock = threading.Lock()


CACHE = WS / "results" / "judge_cache.jsonl"
_cache_lock = threading.Lock()


def _cache_get(model: str, user: str) -> dict | None:
    if not CACHE.exists():
        return None
    key = hashlib.sha256((model + "\n" + user).encode()).hexdigest()
    for ln in CACHE.read_text().splitlines():
        r = json.loads(ln)
        if r["key"] == key:
            return r["parsed"]
    return None


def _cache_put(model: str, user: str, parsed: dict, raw: str, usage: Any) -> None:
    key = hashlib.sha256((model + "\n" + user).encode()).hexdigest()
    with _cache_lock, CACHE.open("a") as f:
        f.write(json.dumps({"key": key, "model": model, "parsed": parsed, "raw": raw[:1500], "usage": usage}) + "\n")


def call(model: str, user: str, budget: Budget, log: list) -> dict | None:
    hit = _cache_get(model, user)
    if hit is not None:
        return hit
    if budget.stop:
        return None
    url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": model, "temperature": 0, "max_tokens": 400, "usage": {"include": True},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    for attempt in range(3):
        if budget.stop:
            return None
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, json=body, timeout=120)
        except requests.RequestException as e:
            logger.warning(f"request error {e}; retry {attempt}")
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 403 and BUDGET_MSG in r.text:
            with budget.lock:
                budget.stop, budget.reason = True, "HTTP 403 budget refusal"
            logger.error("budget refusal: stopping the whole batch")
            return None
        if r.status_code != 200:
            logger.warning(f"HTTP {r.status_code}: {r.text[:200]}; retry {attempt}")
            time.sleep(2 * (attempt + 1))
            continue
        j = r.json()
        cost = float((j.get("usage") or {}).get("cost") or 0.0)
        with budget.lock:
            budget.cost += cost
            budget.calls += 1
            if budget.cost >= HARD_STOP_USD:
                budget.stop, budget.reason = True, f"hard stop at USD {HARD_STOP_USD}"
        txt = j["choices"][0]["message"]["content"] or ""
        log.append({"model": model, "cost": cost, "usage": j.get("usage"), "response": txt[:1500]})
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            out = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            out = {}
        cls = str(out.get("class", "")).strip().upper()
        out["class"] = cls if cls in CLASSES else "UNPARSED"
        _cache_put(model, user, out, txt, j.get("usage"))
        return out
    return None


def run_batch(model: str, jobs: list[dict], budget: Budget, log: list) -> dict[str, dict]:
    res: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(call, model, j["prompt"], budget, log): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            out = f.result()
            if out is not None:
                res[j["key"]] = out
            if budget.stop:
                for g in futs:
                    g.cancel()
    return res


# ------------------------------------------------------------------------------------------------ main
def run(inp: Inputs) -> None:
    design = json.loads((WS / "frozen" / "adjudication_design.json").read_text())
    na = inp.json("exp24", "results/novelty_audit.json")
    items_by_sha = {it["code_sha256"]: it for it in na["items"]}
    tasks = {it["task"] for it in design["items"]} | {c["task"] for c in design["controls"]}
    specs = {t: inp.json("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/spec.json") for t in tasks}
    pools = build_pools(inp, tasks)
    entries = []
    for it in design["items"]:
        src = items_by_sha[it["code_sha256"]]
        entries.append({"id": f"ITEM_{it['code_sha256'][:10]}", "kind": "item", "task": it["task"], "code": src["code"],
                        "expect": None, "sha": it["code_sha256"]})
    for c in design["controls"]:
        if c["control_id"].startswith("CAT_"):
            t, mode = c["task"], c["control_id"].split("_", 2)[2]
            raw = inp.path("exp25", f"inputs/exp11/bench/{BENCH_DIR[t]}/references/{mode}.py").read_text()
            code = scrub_names(raw, [x["mode"] for x in specs[t]["catalogue"]])
        else:
            code = next(v["code"] for k, v in items_by_sha.items() if k == c["code_sha256"])
        entries.append({"id": c["control_id"], "kind": "control", "task": c["task"], "code": code, "expect": c["expect"],
                        "sha": c["code_sha256"]})
    random.Random(design["order_seed"]).shuffle(entries)
    for e in entries:
        pool = [p for p in pools[e["task"]] if not (e["kind"] == "control" and e["id"].startswith("CAT_") and
                                                     p["source"] == f"catalogue reference {e['id'].split('_', 2)[2]}")]
        e["known"] = nearest(e["code"], pool, 3)
    jobs = {1: [], 2: []}
    for e in entries:
        jobs[1].append({"key": e["id"], "prompt": prompt(specs[e["task"]], e["code"], e["known"])})
        jobs[2].append({"key": e["id"], "prompt": prompt(specs[e["task"]], e["code"], list(reversed(e["known"])))})
    est_tokens = sum(len(j["prompt"]) for j in jobs[1] + jobs[2]) / 3.6
    logger.info(f"S4: {len(entries)} entries x 2 passes; ~{est_tokens / 1e3:.0f}k input tokens (est. USD {est_tokens / 1e6 * 1.0 + 44 * 200 / 1e6 * 5:.3f})")
    if os.environ.get("AII_DRY") == "1":
        (WS / "logs" / "s4_dry_prompt.txt").write_text(jobs[1][0]["prompt"])
        logger.info(f"dry run: pool sizes {({t: len(p) for t, p in pools.items()})}; first prompt in logs/s4_dry_prompt.txt; "
                    f"order {[e['id'] for e in entries]}")
        return
    budget, log = Budget(), []
    judges = [design["judge_primary"]] + design["judge_fallbacks"]
    used, passes, gate, per_judge = None, {}, None, {}
    for model in judges:
        p1 = run_batch(model, jobs[1], budget, log)
        ctrl = [e for e in entries if e["kind"] == "control"]
        correct = sum(1 for e in ctrl if p1.get(e["id"], {}).get("class") == e["expect"])
        lenient = sum(1 for e in ctrl if p1.get(e["id"], {}).get("class") == e["expect"] or
                      (e["expect"] == "CATALOGUE_VARIANT" and p1.get(e["id"], {}).get("class") == "LABELLER_MISS"))
        gate = {"model": model, "controls_correct": correct, "controls_correct_lenient": lenient, "n_controls": len(ctrl),
                "valid": correct >= 6}
        logger.info(f"judge {model}: controls {correct}/{len(ctrl)} (lenient {lenient}); cost so far USD {budget.cost:.4f}")
        per_judge[model] = {"gate": gate, "pass1": p1}
        passes = {1: p1}
        if gate["valid"] or budget.stop:
            used = model
            break
    if used and not budget.stop:
        passes[2] = run_batch(used, jobs[2], budget, log)
    elif not budget.stop:  # no judge passed the frozen gate: second pass is descriptive only, for every judge
        for model in per_judge:
            per_judge[model]["pass2"] = run_batch(model, jobs[2], budget, log)
            if budget.stop:
                break
    # metrics
    items = [e for e in entries if e["kind"] == "item"]
    p1 = passes.get(1, {})
    p2 = passes.get(2, {})
    judged = [e for e in items if e["id"] in p1]
    man = [MANUAL_MAP.get(items_by_sha[e["sha"]]["manual_class"], items_by_sha[e["sha"]]["manual_class"]) for e in judged]
    jcls = [p1[e["id"]]["class"] for e in judged]
    nov_j = [int(c == "NOVEL_ALGORITHM") for c in jcls]
    nov_m = [int(c == "NOVEL_ALGORITHM") for c in man]
    n = len(judged)
    po = sum(a == b for a, b in zip(nov_j, nov_m)) / n if n else None
    k_novel_p1 = sum(nov_j)
    k_novel_any = sum(1 for e in items if p1.get(e["id"], {}).get("class") == "NOVEL_ALGORITHM" or
                      p2.get(e["id"], {}).get("class") == "NOVEL_ALGORITHM")
    def jc(e: dict, k: str) -> str:
        return str(parse_dictish(items_by_sha[e["sha"]].get(k)).get("class", ""))
    agree_abc = {k: sum(1 for e in judged if jc(e, k) == p1[e["id"]]["class"]) / n if n else None
                 for k in ("judge_a", "judge_b", "judge_c")}
    stab = [e for e in items if e["id"] in p1 and e["id"] in p2]
    metrics = {"judge_used": used, "gate": gate, "n_items_judged_pass1": n, "n_items_judged_pass2": len([e for e in items if e["id"] in p2]),
               "novel_pass1": k_novel_p1, "novel_either_pass": k_novel_any,
               "binary_raw_agreement_vs_manual": po, "binary_gwet_ac1": gwet_ac1(nov_j, nov_m) if n else None,
               "binary_pabak": (2 * po - 1) if po is not None else None,
               "binary_cohen_kappa": cohen_kappa(nov_j, nov_m) if n else None,
               "kappa_flag": "degenerate: manual prevalence of NOVEL is 0, so chance agreement is driven by one class",
               "five_class_agreement_vs_manual": sum(a == b for a, b in zip(jcls, man)) / n if n else None,
               "agreement_with_exp24_judges": agree_abc,
               "pass_to_pass_stability": sum(p1[e["id"]]["class"] == p2[e["id"]]["class"] for e in stab) / len(stab) if stab else None,
               "class_counts_pass1": dict(Counter(jcls)), "manual_counts": dict(Counter(man)),
               "cost_usd": budget.cost, "calls": budget.calls, "stopped": budget.stop, "stop_reason": budget.reason}
    descriptive = {}
    for model, pj in per_judge.items():
        lab = {e["id"]: pj["pass1"].get(e["id"], {}).get("class") for e in entries}
        jit = [e for e in items if lab.get(e["id"])]
        mm = [MANUAL_MAP.get(items_by_sha[e["sha"]]["manual_class"]) for e in jit]
        jj = [lab[e["id"]] for e in jit]
        bj, bm = [int(c == "NOVEL_ALGORITHM") for c in jj], [int(c == "NOVEL_ALGORITHM") for c in mm]
        po_ = sum(a == b for a, b in zip(bj, bm)) / len(jit) if jit else None
        lab2 = {e["id"]: (pj.get("pass2") or {}).get(e["id"], {}).get("class") for e in entries}
        both = [e for e in items if lab.get(e["id"]) and lab2.get(e["id"])]
        descriptive_extra = {"pass2_items_judged": len([e for e in items if lab2.get(e["id"])]),
                             "pass2_novel_items": sum(1 for e in items if lab2.get(e["id"]) == "NOVEL_ALGORITHM"),
                             "pass_to_pass_stability": (sum(lab[e["id"]] == lab2[e["id"]] for e in both) / len(both)) if both else None,
                             "pass2_label": "descriptive (no judge passed the frozen control gate)"}
        descriptive[model] = {**descriptive_extra, "gate": pj["gate"], "items_judged": len(jit), "novel_items": sum(bj),
                              "class_counts": dict(Counter(jj)), "binary_raw_agreement": po_,
                              "binary_ac1": gwet_ac1(bj, bm) if jit else None,
                              "binary_pabak": (2 * po_ - 1) if po_ is not None else None,
                              "five_class_agreement": sum(a == b for a, b in zip(jj, mm)) / len(jit) if jit else None,
                              "control_labels": {e["id"]: lab.get(e["id"]) for e in entries if e["kind"] == "control"}}
    metrics["per_judge_descriptive"] = descriptive
    if not used or not p1:
        outcome = "judges 14 of 48, manual 0 (third-family adjudication not completed: no judge passed the frozen control gate)"
        status = "NOT_COMPLETED"
    elif k_novel_any == 0:
        outcome = "judges 14 of 48 (two of three), manual 0, third-family blind judge 0 of 14 (rule-of-three bound 3/48 = 0.0625)"
        status = "ZERO"
    else:
        outcome = f"third-family blind judge called {k_novel_any} of 14 novel: those items go to a blind manual verdict and are 'unresolved' unless both say NOT NOVEL"
        status = "K_POSITIVE"
    rows = []
    for e in entries:
        rows.append({"id": e["id"], "kind": e["kind"], "task": e["task"], "expect": e["expect"], "code_sha256": e["sha"],
                     "pass1": p1.get(e["id"]), "pass2": p2.get(e["id"]),
                     "pass1_by_judge": {m: pj["pass1"].get(e["id"]) for m, pj in per_judge.items()},
                     "pass2_by_judge": {m: (pj.get("pass2") or {}).get(e["id"]) for m, pj in per_judge.items()},
                     "manual_class": (MANUAL_MAP.get(items_by_sha[e["sha"]]["manual_class"]) if e["sha"] in items_by_sha else None),
                     "exp24_judges": ({k: jc(e, k) for k in ("judge_a", "judge_b", "judge_c")} if e["sha"] in items_by_sha else None),
                     "nearest_known": [{k: v for k, v in kn.items() if k != "code"} for kn in e["known"]],
                     "code": e["code"]})
    write_json(WS / "results" / "adjudication.json", {"design_sha256_file": "frozen/adjudication_design.json",
                                                      "metrics": metrics, "outcome": outcome, "outcome_status": status,
                                                      "entries": rows, "pool_sizes": {t: len(p) for t, p in pools.items()}})
    write_json(WS / "results" / "adjudication_calls.json", log)
    logger.info(f"S4 done: {outcome}; cost USD {budget.cost:.4f} over {budget.calls} calls")
