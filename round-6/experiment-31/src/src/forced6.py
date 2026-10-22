#!/usr/bin/env python3
"""Forced-program verification (plan S4 'AFTER A UNIT GATES'): keep a forced program only if it passes every hidden test
and its RUNTIME label equals the requested mode; name-scrub it (user-defined identifiers that contain a word of the
mode's id or aliases are renamed h1, h2, ...; comments and docstrings stripped), re-test and re-label the scrubbed
program, and keep the first 10 in slot order (seed k, then wording F1..F5). A mode with fewer than 10 is flagged
(q_lik uses the >= 3 available; < 3 -> undefined, uniform fill). Writes units/<u>/forced_verified.json.
Usage: python src/forced6.py I1,I2
"""

from __future__ import annotations

import ast
import builtins
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from cfg6 import N_FORCED_KEEP, UNITS_DIR, setup_logging, sha256_text, utc_now, write_json  # noqa: E402
from labels_view6 import load_final  # noqa: E402
from units_spec6 import UNITS, catalogue  # noqa: E402
from unitlib6 import label_code, load_tests, strip_comments_docstrings  # noqa: E402

STOP = {"the", "and", "with", "for", "of", "a", "an", "to", "in", "on", "by", "at", "each", "all", "one", "two",
        "number", "numbers", "function", "array", "list", "lists", "value", "values", "solution", "approach"}


def mode_words(u: str, m: str) -> set[str]:
    w = {p for p in m.split("_") if len(p) >= 3}
    for a in UNITS[u]["aliases"].get(m, []):
        for t in re.split(r"[^a-z]+", a.lower()):
            if len(t) >= 3 and t not in STOP:
                w.add(t)
    return w


def scrub(code: str, u: str, m: str) -> str:
    code = strip_comments_docstrings(code)
    t = ast.parse(code)
    words = mode_words(u, m)
    builtin_names = set(dir(builtins))
    imported = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                imported.add((a.asname or a.name).split(".")[0])
    defined = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != "solve":
            defined.add(n.name)
        elif isinstance(n, ast.arg):
            defined.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            defined.add(n.id)
    targets = sorted(x for x in defined if x not in builtin_names and x not in imported and x != "solve"
                     and any(wd in x.lower() for wd in words))
    ren = {x: f"h{i + 1}" for i, x in enumerate(targets)}
    if not ren:
        return code
    for n in ast.walk(t):
        if isinstance(n, ast.Name) and n.id in ren:
            n.id = ren[n.id]
        elif isinstance(n, ast.arg) and n.arg in ren:
            n.arg = ren[n.arg]
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ren:
            n.name = ren[n.name]
        elif isinstance(n, ast.keyword) and n.arg in ren and False:
            pass
    return ast.unparse(t)


def verify_unit(u: str) -> dict:
    labs = [l for l in load_final([u]) if l["arm"].startswith("FORCED_") and l.get("src") == "vllm"]
    tests = load_tests(u)
    out: dict = {"unit": u, "utc": utc_now(), "programs": {}, "counts": {}, "flags": {}}

    def check(l):
        m = l["arm"][len("FORCED_"):]
        if not (l.get("passed") and l.get("runtime_label") == m and l.get("code")):
            return m, l, None, "orig_fail"
        try:
            sc = scrub(l["code"], u, m)
        except SyntaxError:
            return m, l, None, "scrub_error"
        L = label_code(u, sc, cases=tests)
        if not (L.get("passed") and L.get("runtime_label") == m):
            return m, l, None, "scrubbed_fail"
        return m, l, sc, "ok"

    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(check, labs))
    for m in catalogue(u):
        rs = sorted([r for r in res if r[0] == m], key=lambda r: (r[1]["slot"], r[1]["template"]))
        ok = [r for r in rs if r[3] == "ok"]
        kept = ok[:N_FORCED_KEEP]
        out["programs"][m] = [{"code": sc, "orig_key": l["key"], "slot": l["slot"], "template": l["template"]}
                              for _, l, sc, _ in kept]
        out["counts"][m] = {"attempts": len(rs), "orig_pass_and_label": sum(1 for r in rs if r[3] != "orig_fail"),
                            "verified": len(ok), "kept": len(kept),
                            "reasons": {k: sum(1 for r in rs if r[3] == k) for k in
                                        ("orig_fail", "scrub_error", "scrubbed_fail", "ok")}}
        if len(kept) < N_FORCED_KEEP:
            out["flags"][m] = "FEWER_THAN_10" if len(kept) >= 3 else "UNDEFINED_LT3"
    out["sha256"] = sha256_text(str(out["programs"]))
    write_json(UNITS_DIR / u / "forced_verified.json", out)
    logger.info(f"{u} forced verification: " + ", ".join(f"{m}={c['kept']}/{c['attempts']}"
                                                         for m, c in out["counts"].items()))
    return out


if __name__ == "__main__":
    setup_logging("forced6")
    for uu in sys.argv[1].split(","):
        verify_unit(uu)
