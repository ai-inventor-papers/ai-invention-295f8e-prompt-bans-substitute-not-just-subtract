#!/usr/bin/env python3
"""Iteration-6 prompt builders on top of exp28's frozen prompts.py (same tokenizer, same twin prompts).

FEW-SHOT pt prompt (S2): '<bos>' + block(EX1) + block(EX2) + stub(task), where
  block(x) = '\"\"\"' + description(x) + '\\n' + 'Use only the Python standard library.' + '\"\"\"\\n\\ndef ' + sig(x)
             + ':\\n' + body(x) + '\\n\\n\\n'          (exp28's plain-completion format, with the solved body)
  stub(task) = exp28 plain_text(task) without its '<bos>'  (ends with 'def <signature>:\\n')
Exemplar families alternate by draw index k (even = F_bench, odd = F_he):
  F_bench: the first two tasks of [T08, T04, R6, T13] that are not the target and not in the target's family group;
           body = the exemplar task's reference for its it default (loop-only bodies).
  F_he:    the two lowest-id HumanEval+ problems (declared dependency) whose canonical solution passes the AST filter
           (no sort/sorted/heapq/dict/set/Counter/deque/bisect/defaultdict/recursion/imports; single function).
FORCED prompt (S5, the q_lik writers): bench tasks: FORCED_TEMPLATES[k] (k = 0-4) with the catalogue display name +
blank line + SPEC (bench scaffold); path tasks: exp7 prompts_v2 forced 'plain' segments k0-k4 + blank line + SPEC.
Rendered with the Gemma chat template exactly like the twins (exp28 PG.build).
"""

from __future__ import annotations

import ast
import json
import re
import sys
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (BENCH, BOS_ID, DEP1, E7, EXEMPLAR_BENCH_ORDER, EXEMPLAR_REF, EXP8_TASK, EXT_DIR, EXTENDED_DISPLAY,
                 FAMILY_GROUP, PATH_TASKS, PLAIN_STDLIB, bench_paths, cap_first, ids_sha, read_json, read_jsonl)
import prompts as PG

bench_paths()
from bench.common import catalogue as CAT  # noqa: E402
from regate_rules import EXTENDED_LABELS  # noqa: E402

HE_FORBIDDEN_NAMES = {"sort", "sorted", "heapq", "heappush", "heappop", "heapify", "dict", "set", "Counter", "deque",
                      "bisect", "bisect_left", "bisect_right", "insort", "defaultdict", "OrderedDict", "frozenset"}


# ------------------------------------------------------------------------------------------------ catalogue helpers
def catalogue(task: str) -> list[str]:
    """Frozen catalogue modes + named extended labels (R6 linear_scan), exp28's definition."""
    return list(PG.modes(task)) + [m for m in EXTENDED_LABELS.get(task, []) if m not in PG.modes(task)]


def display6(task: str, mode: str) -> str:
    if (task, mode) in EXTENDED_DISPLAY:
        return EXTENDED_DISPLAY[(task, mode)]
    return PG.display(task, mode)


# ------------------------------------------------------------------------------------------------ few-shot blocks
def block_text(description: str, signature: str, body: str) -> str:
    return '"""' + description + "\n" + PLAIN_STDLIB + '"""\n\ndef ' + signature + ":\n" + body.rstrip("\n") + "\n\n\n"


def bench_reference_body(task: str, mode: str) -> tuple[str, str]:
    """(signature, body) of the reference program; the file must be one `def solve(...)` function."""
    if task == "R6" and mode == "linear_scan":
        p = EXT_DIR / "R6" / "linear_scan.py"
    else:
        p = BENCH / CAT.TASKS[task]["task_id"] / "references" / f"{mode}.py"
    src = p.read_text()
    tree = ast.parse(src)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(fns) == 1 and fns[0].name == "solve", f"{p.name}: one solve() expected"
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)), f"{p.name}: imports"
    lines = src.rstrip("\n").split("\n")
    assert lines[0].startswith("def solve(") and lines[0].endswith(":"), p.name
    sig = lines[0][len("def "):-1]
    assert sig == PG.signature(task), (sig, PG.signature(task))
    return sig, "\n".join(lines[1:]) + "\n"


def f_bench_exemplars(target: str) -> list[str]:
    grp = FAMILY_GROUP[target]
    out = [t for t in EXEMPLAR_BENCH_ORDER if t != target and FAMILY_GROUP[t] != grp]
    return out[:2]


def he_records() -> list[dict[str, Any]]:
    return read_jsonl(DEP1 / "humanevalplus_all.jsonl")


def _he_docstring(prompt: str, entry: str) -> str | None:
    tree = ast.parse(prompt)
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(fns) != 1 or fns[0].name != entry:
        return None
    doc = ast.get_docstring(fns[0])
    if not doc:
        return None
    keep = []
    for ln in doc.split("\n"):
        s = ln.strip()
        if s.startswith(">>>") or re.match(r"(?i)^(for example|example|examples|e\.g\.)\b", s):
            break
        keep.append(ln)
    d = " ".join(x.strip() for x in keep if x.strip())
    return d or None


def he_filter(rec: dict[str, Any]) -> tuple[bool, str]:
    prompt, entry = rec["prompt"], rec["entry_point"]
    body = rec["solution"]
    for ln in prompt.split("\n"):
        if ln.startswith(("import ", "from ")) and not ln.startswith("from typing import"):
            return False, "non-typing import in prompt"
    try:
        tree = ast.parse(prompt + body)
    except SyntaxError:
        return False, "does not parse"
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if len(fns) != 1:
        return False, "more than one function"
    fn = fns[0]
    for n in ast.walk(fn):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            return False, "import in solution"
        if isinstance(n, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)):
            return False, "dict/set literal"
        if isinstance(n, ast.Name) and n.id in HE_FORBIDDEN_NAMES:
            return False, f"forbidden name {n.id}"
        if isinstance(n, ast.Attribute) and n.attr in HE_FORBIDDEN_NAMES:
            return False, f"forbidden attribute {n.attr}"
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == entry:
            return False, "recursion"
        if isinstance(n, (ast.FunctionDef, ast.Lambda)) and n is not fn:
            return False, "nested function"
    if _he_docstring(prompt, entry) is None:
        return False, "no usable docstring"
    return True, "ok"


@lru_cache(maxsize=1)
def f_he_exemplars() -> tuple[dict[str, Any], ...]:
    recs = sorted(he_records(), key=lambda r: int(r["task_id"].split("/")[1]))
    out = []
    for r in recs:
        ok, _ = he_filter(r)
        if ok:
            fn = [n for n in ast.parse(r["prompt"]).body if isinstance(n, ast.FunctionDef)][0]
            sig_line = [ln for ln in r["prompt"].split("\n") if ln.startswith(f"def {r['entry_point']}(")][0]
            sig = sig_line[len("def "):].rstrip().rstrip(":")
            body = r["solution"].strip("\n") + "\n"
            # normalise the canonical body to 4-space indentation directly under the def line (no blank lines)
            body = textwrap.indent(textwrap.dedent(body), "    ")
            out.append({"task_id": r["task_id"], "entry_point": r["entry_point"], "signature": sig,
                        "description": _he_docstring(r["prompt"], r["entry_point"]), "body": body,
                        "lineno": fn.lineno})
        if len(out) == 2:
            break
    assert len(out) == 2, "fewer than two HumanEval+ problems pass the exemplar filter"
    return tuple(out)


def exemplar_blocks(target: str, family: str) -> tuple[list[str], list[str]]:
    """(block texts, exemplar ids) for a target task and an exemplar family ('F_bench' | 'F_he')."""
    if family == "F_bench":
        ex = f_bench_exemplars(target)
        blocks = []
        for t in ex:
            sig, body = bench_reference_body(t, EXEMPLAR_REF[t])
            blocks.append(block_text(PG.description(t), sig, body))
        return blocks, [f"{t}:{EXEMPLAR_REF[t]}" for t in ex]
    he = f_he_exemplars()
    return [block_text(h["description"], h["signature"], h["body"]) for h in he], [h["task_id"] for h in he]


def p_fewshot(task: str, family: str) -> dict[str, Any]:
    tok = PG.tokenizer()
    blocks, ex_ids = exemplar_blocks(task, family)
    stub = PG.plain_text(task)
    assert stub.startswith("<bos>")
    text = "<bos>" + "".join(blocks) + stub[len("<bos>"):]
    ids = list(tok(text, add_special_tokens=False)["input_ids"])
    assert ids[0] == BOS_ID and ids.count(BOS_ID) == 1, "few-shot prompt: exactly one BOS at index 0"
    return {"task": task, "cond": f"fewshot:{family}", "kind": "fewshot", "X": None, "w": family, "text": text,
            "ids": ids, "P": len(ids), "prompt_sha256": ids_sha(ids), "seg_start": None, "spec_start": None,
            "spec_end": None, "R": len(ids) - 1, "pad": 0, "noun": None, "exemplars": ex_ids,
            "prefix": "def " + PG.signature(task) + ":\n"}


# ------------------------------------------------------------------------------------------------ forced prompts
@lru_cache(maxsize=1)
def exp7_conditions() -> dict[str, Any]:
    return read_json(E7 / "prompts" / "prompts_v2.json")["conditions"]


def forced_segment(task: str, mode: str, k: int) -> str:
    if task in PATH_TASKS:
        c = exp7_conditions()[f"{EXP8_TASK[task]}|forced|{mode}|plain|k{k}"]
        return c["segment"]
    return cap_first(CAT.FORCED_TEMPLATES[k].format(j=display6(task, mode)))


def p_forced(task: str, mode: str, k: int) -> dict[str, Any]:
    seg = forced_segment(task, mode, k)
    text = seg + "\n\n" + PG.spec_text(task)
    p = PG.build(task, "forced", text, cond=f"forced:{mode}:k{k}", X=mode, w=f"k{k}")
    p["forced_mode"] = mode
    p["paraphrase_id"] = k
    return p


def forced_modes(task: str) -> list[str]:
    """Algorithms written under force: every catalogue mode incl. extended labels; path tasks: the exp7 forced set
    restricted to the frozen suite catalogue."""
    cat = catalogue(task)
    if task in PATH_TASKS:
        have = {v.get("j") for v in exp7_conditions().values()
                if v.get("kind") == "forced" and v.get("task") == EXP8_TASK[task] and v.get("family") == "plain"}
        return [m for m in cat if m in have]
    return cat


def all_fed_texts_fewshot(tasks: list[str]) -> list[tuple[str, str]]:
    return [("fewshot", p_fewshot(t, f)["text"]) for t in tasks for f in ("F_bench", "F_he")]


if __name__ == "__main__":
    for t in ("T03", "T04", "R6", "T08", "T1"):
        print(t, f_bench_exemplars(t))
    for h in f_he_exemplars():
        print(json.dumps(h)[:400])
    p = p_fewshot("T03", "F_bench")
    print(p["P"], p["text"][:1500])
    q = p_fewshot("T03", "F_he")
    print(q["P"], q["text"][:1200])
    f = p_forced("T03", "quickselect", 0)
    print(f["P"], f["text"][:300])
    f = p_forced("T1", "bfs", 2)
    print(f["P"], f["text"][:300])
    print({t: forced_modes(t) for t in ("T1", "T2", "R6")})
