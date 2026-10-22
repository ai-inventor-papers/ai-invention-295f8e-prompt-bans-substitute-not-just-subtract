#!/usr/bin/env python3
"""q_lik (plan 0.9): the tuned model's own teacher-forced likelihood ranking of the catalogue algorithms.

For each algorithm a in CAT: up to 10 verified forced programs (passed every hidden test, final label == a), comments
and docstrings removed (ast round trip), then NAME-SCRUBBED (user identifiers whose sub-words contain any catalogue
alias word of the unit are renamed v1, v2, ...; API names, attributes, solve and the signature arguments are never
touched). For each program j and twin template w: tokens = chat_template(twin prompt w, thinking off) + '```python\\n'
+ program; lp(a, j, w) = sum of log-softmax(fp32 logits) over the first 48 program tokens after the fence.
Fixed-shape batches: one batch per (a, w) of exactly 10 rows (missing rows padded with copies, discarded), left
padding with attention mask and explicit position ids. Sensitivities: UNSCRUBBED programs (raw extracted code);
noise floor = median |delta lp| of 20 (a, j, w) items re-scored alone (batch of 1, no padding)."""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import re
import tokenize
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg5 import QLIK_TOKENS, RESULTS_DIR, TEMPLATE_IDS, read_json, utc_now, write_json
from unitlib import strip_comments_docstrings

OUT = RESULTS_DIR / "qlik.json"
STOP = {"a", "an", "the", "of", "with", "and", "on", "in", "by", "to", "for", "over", "list", "lists", "value",
        "values", "one", "per", "from", "each", "every", "all", "x", "n", "s", "t", "k", "loop", "count", "find",
        "first", "last", "use", "using", "new", "two", "set", "map", "array", "sum", "max", "min"}


def alias_words(unit: str) -> set[str]:
    from units_spec import UNITS
    sp = UNITS[unit]
    words = set()
    for m, (dn, _) in sp["modes"].items():
        words |= set(re.findall(r"[a-z0-9]+", m.lower()))
        words |= set(re.findall(r"[a-z0-9]+", dn.lower()))
    for al in sp["aliases"].values():
        for a in al:
            words |= set(re.findall(r"[a-z0-9]+", a.lower()))
    return {w for w in words if w not in STOP and len(w) >= 3 and not w.isdigit()}


def subwords(name: str) -> list[str]:
    parts = []
    for chunk in name.split("_"):
        parts += re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+", chunk)
    return [p.lower() for p in parts if p]


def scrub(code: str, unit: str) -> tuple[str, dict[str, Any]]:
    """Remove comments/docstrings, then rename user identifiers that contain an alias word."""
    from units_spec import UNITS
    info: dict[str, Any] = {"renamed": {}, "ok": True}
    clean = strip_comments_docstrings(code)
    try:
        tree = ast.parse(clean)
    except SyntaxError as e:
        return clean, {"ok": False, "error": str(e)}
    words = alias_words(unit)
    protected = {"solve"} | set(UNITS[unit]["args"]) | set(dir(builtins)) | set(keyword.kwlist)
    defined = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(n.name)
            if not isinstance(n, ast.ClassDef):
                for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs:
                    defined.add(a.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            defined.add(n.id)
        elif isinstance(n, ast.arg):
            defined.add(n.arg)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                defined.discard((a.asname or a.name).split(".")[0])
    ren: dict[str, str] = {}
    for nm in sorted(defined - protected):
        if any(w in words for w in subwords(nm)) or nm.lower() in words:
            ren[nm] = f"v{len(ren) + 1}"
    if not ren:
        return clean, info
    out = []
    prev = None
    try:
        for t in tokenize.generate_tokens(io.StringIO(clean).readline):
            if t.type == tokenize.NAME and t.string in ren and not (prev is not None and prev.string == "."):
                out.append((t.type, ren[t.string]))
            else:
                out.append((t.type, t.string))
            if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT):
                prev = t
        res = tokenize.untokenize(out)
        compile(res, "<scrub>", "exec")
        res = ast.unparse(ast.parse(res))
    except (SyntaxError, tokenize.TokenError, ValueError) as e:
        return clean, {"ok": False, "error": str(e)}
    info["renamed"] = ren
    return res, info


def _prog_ids(tok: Any, program: str) -> tuple[list[int], list[int]]:
    pre = tok("```python\n", add_special_tokens=False)["input_ids"]
    joint = tok("```python\n" + program, add_special_tokens=False)["input_ids"]
    if joint[:len(pre)] == pre:
        return pre, joint[len(pre):]
    return pre, tok(program, add_special_tokens=False)["input_ids"]


@torch.no_grad()
def score_batch(model: Any, rows: list[tuple[list[int], list[int]]], width: int = 10) -> list[tuple[float, int]]:
    """rows: [(context_ids, scored_ids)] -> [(sum lp of scored ids, n scored)]; fixed batch of `width` rows."""
    if not rows:
        return []
    real = len(rows)
    rows = rows + [rows[0]] * (width - real) if real < width else rows
    seqs = [c + s for c, s in rows]
    L = max(len(x) for x in seqs)
    dev = model.device
    pad = 151643
    inp = torch.full((len(seqs), L), pad, dtype=torch.long, device=dev)
    mask = torch.zeros((len(seqs), L), dtype=torch.long, device=dev)
    for i, x in enumerate(seqs):
        inp[i, L - len(x):] = torch.tensor(x, device=dev)
        mask[i, L - len(x):] = 1
    pos = (mask.cumsum(-1) - 1).clamp(min=0)
    logits = model(input_ids=inp, attention_mask=mask, position_ids=pos, use_cache=False).logits
    out = []
    for i, (c, s) in enumerate(rows[:real]):
        off = L - len(c) - len(s)
        idx = torch.arange(off + len(c) - 1, off + len(c) + len(s) - 1, device=dev)
        lp = torch.log_softmax(logits[i, idx].float(), dim=-1)
        tgt = torch.tensor(s, device=dev)
        out.append((float(lp.gather(-1, tgt[:, None]).sum()), len(s)))
    del logits
    return out


def score_unit(model: Any, tok: Any, unit: str, prompts: dict[str, dict], programs: dict[str, list[dict]],
               noise_items: int = 20) -> dict[str, Any]:
    """programs: {mode: [{'key', 'code'}]} (verified forced programs, <= 10 each)."""
    res: dict[str, Any] = {"utc": utc_now(), "unit": unit, "by_mode": {}, "n_programs": {}, "scrub_info": {}}
    variants = {"scrubbed": {}, "unscrubbed": {}}
    for mode, progs in programs.items():
        res["n_programs"][mode] = len(progs)
        for kind in variants:
            items = []
            for p in progs[:10]:
                code = p["code"]
                if kind == "scrubbed":
                    code, info = scrub(code, unit)
                    res["scrub_info"][p["key"]] = info.get("renamed") or {}
                items.append((p["key"], code))
            variants[kind][mode] = items
    noise = []
    for kind, by_mode in variants.items():
        for mode, items in by_mode.items():
            lps: dict[str, dict[str, Any]] = {}
            for w in TEMPLATE_IDS:
                ctx = prompts[f"{unit}|twin|-|{w}"]["ids"]
                rows = []
                for key, code in items:
                    pre, body = _prog_ids(tok, code)
                    rows.append((ctx + pre, body[:QLIK_TOKENS]))
                sc = score_batch(model, rows)
                for (key, _), (lp, nt) in zip(items, sc):
                    lps.setdefault(key, {})[w] = {"lp": lp, "n": nt}
                if kind == "scrubbed" and len(noise) < noise_items and rows:
                    single = score_batch(model, [rows[0]], width=1)[0][0]
                    noise.append(abs(single - sc[0][0]))
            raw = [v["lp"] for d in lps.values() for v in d.values()]
            tokn = [v["lp"] / max(v["n"], 1) for d in lps.values() for v in d.values()]
            res["by_mode"].setdefault(mode, {})[kind] = {"score_raw": float(np.mean(raw)) if raw else None,
                                                          "score_tok": float(np.mean(tokn)) if tokn else None,
                                                          "lp": lps}
    res["noise_floor"] = float(np.median(noise)) if noise else None
    res["noise_items"] = len(noise)
    allr = read_json(OUT) if OUT.exists() else {}
    allr[unit] = res
    write_json(OUT, allr)
    logger.info(f"q_lik {unit}: " + ", ".join(f"{m}: tok {v['scrubbed']['score_tok']:.3f} raw "
                                             f"{v['scrubbed']['score_raw']:.1f} (n={res['n_programs'][m]})"
                                             for m, v in res["by_mode"].items() if v["scrubbed"]["score_tok"]
                                             is not None) + f"; noise floor {res['noise_floor']}")
    return res
