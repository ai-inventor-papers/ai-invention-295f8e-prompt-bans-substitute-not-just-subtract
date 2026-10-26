"""Normalise every per-program record of the ORIGIN files (exactly the files named in the plan's builds_on) to one row
schema:

  {exp, task, model, condition, kind, banned_set, template, T, top_k, top_p, thinking, label, label_fine, passed,
   code, code_sha256, source, line, arm, decoding_key, dedup_key}

Copies of exp1/exp2/exp4 that exp7, exp8 and exp12 carry under inputs/, data_in/ or canon/ are never read (the exp3
pools copy inside exp8 is the single exception: it is the only legitimate route to exp3 programs).
"""

from __future__ import annotations

import ast
import re
from typing import Any, Iterator

from common.paths import code_key, dep, read_jsonl, src

MODAL = {"t1": "bfs", "t2": "dijkstra"}
T1_K6 = ["bfs", "dfs", "bibfs", "iddfs", "astar_gbfs", "dijkstra"]          # exp7 analysis catalogue (T1)
T2_K5 = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]               # exp7 analysis catalogue (T2)
E9_T1_K7 = ["bfs", "dfs", "bibfs", "iddfs", "astar", "gbfs", "idastar"]      # exp9 analysis catalogue (T1)

# raw name -> (canonical K=6/K=5 label, fine label)
_T1 = {"bfs": "bfs", "dfs": "dfs", "bibfs": "bibfs", "bidir_bfs": "bibfs", "bidirectional_bfs": "bibfs",
       "iddfs": "iddfs", "astar_gbfs": "astar_gbfs", "astar_greedy": "astar_gbfs", "astar": "astar_gbfs",
       "gbfs": "astar_gbfs", "dijkstra": "dijkstra", "dijkstra_unit": "dijkstra", "unit_dijkstra": "dijkstra",
       "idastar": "idastar", "jps": "other_ext", "biastar": "other_ext"}
_T2 = {"dijkstra": "dijkstra", "bf_spfa": "bf_spfa", "bellman_ford": "bf_spfa", "spfa": "bf_spfa",
       "bellman_ford_spfa": "bf_spfa", "bidijkstra": "bidijkstra", "bidir_dijkstra": "bidijkstra",
       "bidirectional_dijkstra": "bidijkstra", "floyd": "floyd", "floyd_warshall": "floyd", "dial": "dial",
       "johnson": "other_ext", "dag_dp": "other_ext"}
_OTHER = {"other", "unknown", "none"}
_UNPARSE = {"no_code", "unparseable", "invalid", "parse_error", "no code"}


def _s(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v)
    return None if s in ("None", "", "nan") else s


def norm_task(t: Any) -> str:
    s = str(t)
    return s.lower() if s.upper() in ("T1", "T2") else s


def norm_model(m: Any) -> str:
    s = str(m or "")
    if "Base" in s:
        return "Qwen/Qwen3-8B-Base"
    if "llama" in s.lower():
        return "meta-llama/Llama-3.1-8B-Instruct"
    if "Qwen3-8B" in s:
        return "Qwen/Qwen3-8B"
    return s


def norm_label(task: str, raw: Any, code: str | None, parse_ok: bool | None = None, exp: str = "") -> tuple[str, str]:
    """Returns (label, label_fine). label is 'other' / 'other_ext' / 'unparseable' or a catalogue name."""
    r = _s(raw)
    has_code = bool(code and code.strip())
    if parse_ok is None:
        parse_ok = has_code
    if r is None:
        return ("other", "other:null_label") if parse_ok else ("unparseable", "unparseable")
    low = r.strip().lower()
    if low in _UNPARSE:
        return ("unparseable", low)
    if low in _OTHER or low.startswith("other"):
        return ("other", low)
    if task == "t1":
        if exp == "exp9" and low in ("dijkstra_unit", "unit_dijkstra", "jps", "biastar"):
            return ("other_ext", low)        # outside exp9's K=7 analysis catalogue
        if low in _T1:
            lab = _T1[low]
            return (lab, low if low in ("astar", "gbfs", "astar_greedy") else lab)
        return ("other_ext", low)
    if task == "t2":
        if low in _T2:
            return (_T2[low], _T2[low])
        return ("other_ext", low)
    return (low, low)                         # bench tasks keep their own mode names


def parse_decoding(dec: Any, row: dict[str, Any]) -> dict[str, Any]:
    s = str(dec or "")
    out = {"T": None, "top_k": None, "top_p": None, "thinking": None}
    m = re.search(r"(?:^|[^a-z])T(?:=|')?\s*:?\s*([0-9.]+)", s) or re.search(r"temperature'?\s*[:=]\s*([0-9.]+)", s)
    if m:
        out["T"] = float(m.group(1).rstrip("."))
    m = re.search(r"top_?p'?\s*[:=]?\s*([0-9.]+)", s) or re.search(r"topp([0-9.]+)", s)
    if m:
        try:
            out["top_p"] = float(m.group(1).rstrip("._"))
        except ValueError:
            pass
    m = re.search(r"top_?k'?\s*[:=]?\s*'?(-?[0-9]+|off|disabled)", s) or re.search(r"topk-?(off|[0-9]+)", s)
    if m:
        v = m.group(1)
        out["top_k"] = None if v in ("off", "disabled", "0", "-1") else int(v)
    if "thinkoff" in s or "thinking=off" in s or "'thinking': False" in s:
        out["thinking"] = False
    elif "thinkon" in s or "thinking=on" in s or "'thinking': True" in s:
        out["thinking"] = True
    if row.get("T") not in (None, "None"):
        try:
            out["T"] = float(row["T"])
        except (TypeError, ValueError):
            pass
    if row.get("temperature") not in (None, "None"):
        try:
            out["T"] = float(row["temperature"])
        except (TypeError, ValueError):
            pass
    if row.get("thinking") not in (None, "None"):
        out["thinking"] = str(row["thinking"]) in ("True", "true", "1")
    # defaults of every experiment in this study: thinking off, top-p 1.0, no top-k unless stated otherwise
    if out["thinking"] is None:
        out["thinking"] = False
    if out["top_p"] is None:
        out["top_p"] = 1.0
    return out


def _banned_from_str(s: Any) -> list[str]:
    if s is None:
        return []
    if isinstance(s, list):
        return [str(x) for x in s]
    t = str(s)
    if t in ("None", "", "[]"):
        return []
    try:
        v = ast.literal_eval(t)
        if isinstance(v, (list, tuple)):
            return [str(x) for x in v]
    except (ValueError, SyntaxError):
        pass
    return [t]


def _norm_banned(task: str, names: list[str], exp: str = "") -> list[str]:
    out = []
    for n in names:
        lab, fine = norm_label(task, n.lower(), "x", True, exp)
        out.append(fine if (exp == "exp9" and fine in ("astar", "gbfs")) else lab)
    return sorted(set(out))


def banned_for(exp: str, task: str, cond: str, r: dict[str, Any]) -> list[str]:
    c = cond or ""
    if exp == "exp1":
        return _norm_banned(task, _banned_from_str(r.get("banned_set")))
    if exp == "exp9":
        return _norm_banned(task, _banned_from_str(r.get("banned")), "exp9")
    if exp == "exp10":
        if c.startswith("ban:"):
            return _norm_banned(task, [c.split(":")[1]])
        if c.startswith("twostep:"):
            return _norm_banned(task, c.split(":")[1].split("+"))
        return []
    if exp in ("exp8",):
        return [MODAL[task]] if c in ("a", "c", "d", "K0", "K1", "K2") else []
    if exp in ("exp12", "exp3"):
        return [MODAL[task]] if c == "ban" else []
    if exp == "exp4" and c.startswith("succession"):
        return ["bfs", "dfs"] if task == "t1" else ["dijkstra", "bf_spfa"]
    if c.startswith("ban:"):
        return _norm_banned(task, c.split(":", 1)[1].split("+"))
    return []


# exactly the origin files named in builds_on: (exp, relative path, model-agnostic tag)
ORIGIN_FILES = [
    ("exp1", "data/samples.jsonl"),
    ("exp2", "data/samples_phaseA.jsonl"), ("exp2", "data/samples_phaseC.jsonl"), ("exp2", "data/samples_phaseD.jsonl"),
    ("exp4", "data/samples.jsonl"),
    ("exp5", "runs/samples.jsonl"),
    ("exp6", "results/samples.jsonl"),
    ("exp3", "inputs/iter1/exp3/generations/pools.jsonl"),
    ("exp7", "data/forced_selected.jsonl"),
    ("exp8", "data/samples.jsonl"),
    ("exp9", "data/samples.jsonl"),
    ("exp10", "data/labelled.jsonl"),
    ("exp11", "data/samples_pilot.jsonl"), ("exp11", "data/samples_llama_pilot.jsonl"),
    ("exp11", "data/samples_forced.jsonl"),
    ("exp12", "results/samples.jsonl"),
]
# extra exp12 per-readout label files: read for the novelty audit only (de-duplicated by code hash)
EXP12_EXTRA = [f"results/labelled_{k}.jsonl" for k in ("c1", "c2", "c3", "c4", "crn", "det", "rep10")]


def _passed(v: Any) -> bool | None:
    if v is None:
        return None
    s = str(v)
    if s in ("True", "true", "1"):
        return True
    if s in ("False", "false", "0"):
        return False
    return None


def iter_rows(include_exp12_extra: bool = False) -> Iterator[dict[str, Any]]:
    files = list(ORIGIN_FILES) + ([("exp12", f) for f in EXP12_EXTRA] if include_exp12_extra else [])
    for exp, rel in files:
        p = dep(exp, rel)
        if not p.exists():
            continue
        for i, r in enumerate(read_jsonl(p)):
            yield normalise(exp, rel, i, r)


def normalise(exp: str, rel: str, i: int, r: dict[str, Any]) -> dict[str, Any]:
    task = norm_task(r.get("task", r.get("task_id")))
    code = r.get("code") if isinstance(r.get("code"), str) else None
    if exp == "exp7":
        code = r.get("code_raw") or r.get("code") or r.get("code_scrubbed")
        cond = f"forced:{r.get('j')}"
        raw_label = r.get("label", r.get("j"))
    else:
        cond = str(r.get("condition"))
        raw_label = r.get("label")
    parse_ok = None
    if exp == "exp5" and r.get("parse_ok") is not None:
        parse_ok = str(r.get("parse_ok")) == "True"
    label, fine = norm_label(task, raw_label, code, parse_ok, exp)
    dec = parse_decoding(r.get("decoding"), r)
    if exp == "exp6" and r.get("key"):
        k = str(r["key"]).split("|")
        try:
            dec["T"] = float(k[5][1:])
            dec["top_k"] = 10 if k[6] == "topk10" else None
            dec["top_p"] = 0.95 if k[6] == "topp095" else 1.0
            dec["thinking"] = k[7] == "think1"
        except (IndexError, ValueError):
            pass
    if exp == "exp1" and cond == "baseline_T13":
        dec["T"] = 1.3
    arm = _s(r.get("arm")) or _s(r.get("steering")) or _s(r.get("steer"))
    model = norm_model(r.get("model"))
    if exp == "exp7":
        model = "Qwen/Qwen3-8B"
    tmpl = _s(r.get("template")) or _s(r.get("paraphrase_id"))
    banned = banned_for(exp, task, cond, r)
    dk = f"T{dec['T']}|k{dec['top_k']}|p{dec['top_p']}|think{dec['thinking']}"
    return {"exp": exp, "task": task, "model": model, "model_raw": str(r.get("model")), "condition": cond,
            "kind": _s(r.get("kind")), "banned_set": banned, "template": tmpl, **dec, "decoding_key": dk,
            "label": label, "label_fine": fine, "label_raw": _s(raw_label), "passed": _passed(r.get("passed")),
            "code": code, "code_sha256": _s(r.get("code_sha256")),
            "dedup_key": f"{task}|{code_key(code)}" if code and code.strip() else None,
            "source": src(exp, rel), "line": i + 1, "arm": arm, "phase": _s(r.get("phase")),
            "X": _s(r.get("X")), "sample_id": _s(r.get("sample_id")),
            "runtime_label": _s(r.get("runtime_label") or r.get("rt_label") or r.get("label_runtime")),
            "ast_label": _s(r.get("ast_label") or r.get("label_ast")),
            "judge_label": _s(r.get("judge_label") or r.get("label_judge")),
            "variant": _s(r.get("variant")), "algorithm": _s(r.get("algorithm") or r.get("forced_mode"))}
