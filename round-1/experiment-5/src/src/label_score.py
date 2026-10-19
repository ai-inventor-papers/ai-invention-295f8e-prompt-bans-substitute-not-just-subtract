"""Extract -> score (hidden tests) -> runtime label -> AST label -> blind judge -> final label, per raw sample file.

  .venv/bin/python src/label_score.py runs/raw_base_tf__baseline.jsonl [...]   (default: every runs/raw_*.jsonl)
Writes runs/labelled_<tag>.jsonl (per-sample rows in the shared schema + extra fields). Caches by code sha256:
runs/score_cache.jsonl, runs/rt_cache.jsonl, runs/judge_cache.jsonl.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CATALOGUE, DECODING, RUNS, TESTS, WS, append_jsonl, read_jsonl, setup_logging, sha256_text, write_jsonl  # noqa: E402
from extract import FENCE_RE, extract  # noqa: E402
from harness import score_many  # noqa: E402
from judge import JUDGE_PRIMARY, judge_items, normalise  # noqa: E402
from labeller_ast import label_ast  # noqa: E402
from labeller_runtime import label_many  # noqa: E402
from prompts import load_prompts  # noqa: E402

REFUSAL_RE = re.compile(r"(?i)(i can't|i cannot|i'm sorry|as an ai|i am unable)")
LEAK_RE = re.compile(r"(^|\n)(user|assistant|system)\s*\n|(^|\n)(Human|User|Assistant):")
N_WORKERS = 5


def format_flags(row: dict) -> dict:
    text = row["text"]
    if row["template"] == "tf":
        return {"format_ok_loose": None, "format_ok_strict": None, "refusal": False,
                "degenerate": bool(row.get("finish_reason") == "length" or _repeats(text)), "chat_leak": None,
                "length_cap": row.get("finish_reason") == "length"}
    blocks = [m for m in FENCE_RE.finditer(text)]
    solve_blocks = [m for m in blocks if "def solve" in m.group(2)]
    loose = len(solve_blocks) >= 1
    outside = FENCE_RE.sub(" ", text)
    strict = len(blocks) == 1 and loose and len(outside.split()) <= 40
    refusal = (not blocks) and bool(REFUSAL_RE.search(text))
    degenerate = (row.get("finish_reason") == "length" and not blocks) or _repeats(text)
    leak = None
    if row["arm"].startswith("base_chat"):
        leak = bool(str(row.get("stop_reason")) == "151644" or LEAK_RE.search(text))
    return {"format_ok_loose": loose, "format_ok_strict": strict, "refusal": refusal, "degenerate": bool(degenerate),
            "chat_leak": leak, "length_cap": row.get("finish_reason") == "length"}


def _repeats(text: str, n: int = 6, k: int = 5) -> bool:
    w = text.split()
    if len(w) < n * k:
        return False
    cnt: dict = {}
    for i in range(len(w) - n + 1):
        g = tuple(w[i:i + n])
        cnt[g] = cnt.get(g, 0) + 1
        if cnt[g] >= k:
            return True
    return False


def prompt_text_for(row: dict, prompts: dict) -> str:
    kind = "baseline" if row["condition"] == "baseline" else "ban"
    for p in prompts[row["template"]][row["task"]][kind]:
        if p["id"] == row["prompt_id"]:
            return p["text"]
    raise KeyError(row["prompt_id"])


def process(raw_files: list[Path], use_judge: bool = True) -> None:
    prompts = load_prompts()
    score_cache = {(r["task"], r["code_sha256"]): r for r in read_jsonl(RUNS / "score_cache.jsonl")}
    rt_cache = {(r["task"], r["code_sha256"]): r for r in read_jsonl(RUNS / "rt_cache.jsonl")}
    all_rows: dict[Path, list[dict]] = {}
    todo_code: dict[tuple, str] = {}
    for f in raw_files:
        rows = read_jsonl(f)
        out = []
        for r in rows:
            code, info = extract(r, prompt_text_for(r, prompts))
            rr = dict(r)
            rr["parse_ok"] = code is not None
            rr["extract_info"] = info
            rr["code"] = code
            rr["code_sha256"] = sha256_text(code) if code else None
            rr.update(format_flags(r))
            if code:
                todo_code[(r["task"], rr["code_sha256"])] = code
            out.append(rr)
        all_rows[f] = out
    need_score = [k for k in todo_code if k not in score_cache]
    need_rt = [k for k in todo_code if k not in rt_cache]
    logger.info(f"{sum(len(v) for v in all_rows.values())} samples, {len(todo_code)} distinct programs; "
                f"to score {len(need_score)}, to runtime-label {len(need_rt)}")
    t0 = time.time()
    if need_score:
        jobs = [(t, todo_code[(t, h)], str(TESTS / f"{t}.json"), str(WS / "scratch_harness"), f"{t}|{h}") for t, h in need_score]
        res = score_many(jobs, n_workers=N_WORKERS)
        # one re-score for timeouts (CPU contention guard)
        retry = [i for i, r in enumerate(res) if r.get("error") in ("timeout", "killed_total_budget")]
        if retry:
            res2 = score_many([jobs[i] for i in retry], n_workers=2)
            for i, r2 in zip(retry, res2):
                r2["rescored_after_timeout"] = True
                res[i] = r2
        new = []
        for (t, h), r in zip(need_score, res):
            row = {"task": t, "code_sha256": h, "passed": bool(r.get("passed")), "wall_s": r.get("wall_s"),
                   "fail_case": r.get("fail_case"), "error": r.get("error"), "n_passed": r.get("n_passed"),
                   "rescored": bool(r.get("rescored_after_timeout"))}
            score_cache[(t, h)] = row
            new.append(row)
        append_jsonl(RUNS / "score_cache.jsonl", new)
        logger.info(f"scored {len(need_score)} programs in {time.time() - t0:.0f}s ({len(retry)} timeout re-scores)")
    t1 = time.time()
    if need_rt:
        res = label_many([(t, todo_code[(t, h)], str(WS / "scratch_label"), f"{t}|{h}") for t, h in need_rt],
                         n_workers=N_WORKERS)
        new = []
        for (t, h), r in zip(need_rt, res):
            row = {"task": t, "code_sha256": h, "label": r["label"], "why": r.get("why"), "errors": r.get("errors", [])}
            rt_cache[(t, h)] = row
            new.append(row)
        append_jsonl(RUNS / "rt_cache.jsonl", new)
        logger.info(f"runtime-labelled {len(need_rt)} programs in {time.time() - t1:.0f}s")
    ast_lab = {k: label_ast(c, k[0])[0] for k, c in todo_code.items()}
    # judge every distinct parseable program (blind); final label uses it only when runtime != AST
    judge_lab: dict = {}
    jinfo = {}
    if use_judge and todo_code:
        keys = list(todo_code)
        res, jinfo = judge_items([(k[0], todo_code[k]) for k in keys], model=JUDGE_PRIMARY)
        for k, r in zip(keys, res):
            if r is not None:
                judge_lab[k] = normalise(k[0], r.get("raw_label") or r["label"])
        logger.info(f"judge: {len(judge_lab)}/{len(keys)} labelled; {jinfo}")
    for f, rows in all_rows.items():
        out = []
        for rr in rows:
            k = (rr["task"], rr["code_sha256"])
            if rr["parse_ok"]:
                sc = score_cache[k]
                rt = rt_cache[k]["label"]
                al = ast_lab[k]
                jl = judge_lab.get(k)
                cat = CATALOGUE[rr["task"]]
                if rt == al and rt in cat:
                    lab, src = rt, "runtime+ast"
                elif jl is not None:
                    lab, src = jl, "judge"
                elif rt != "unknown":
                    lab, src = rt, "fallback"
                elif al != "unknown":
                    lab, src = (al if al in cat or al.startswith("other") else "other"), "fallback"
                else:
                    lab, src = "other", "fallback"
                rr.update({"passed": sc["passed"], "wall_s": sc["wall_s"], "fail_case": sc["fail_case"],
                           "error": sc["error"], "label": lab, "labeller_source": src, "runtime_label": rt,
                           "ast_label": al, "judge_label": jl, "runtime_why": rt_cache[k].get("why")})
            else:
                rr.update({"passed": False, "wall_s": None, "fail_case": None, "error": "unparseable", "label": None,
                           "labeller_source": None, "runtime_label": None, "ast_label": None, "judge_label": None})
            rr["decoding"] = DECODING
            rr.setdefault("steer", None)
            out.append(rr)
        tag = f.stem.replace("raw_", "")
        write_jsonl(RUNS / f"labelled_{tag}.jsonl", out)
        n = len(out)
        npar = sum(r["parse_ok"] for r in out)
        npass = sum(bool(r["passed"]) for r in out)
        logger.info(f"{tag}: n={n} parse={npar} pass={npass}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--no_judge", action="store_true")
    a = ap.parse_args()
    setup_logging("label_score")
    files = [Path(x) for x in a.files] if a.files else sorted(RUNS.glob("raw_*.jsonl"))
    process(files, use_judge=not a.no_judge)


if __name__ == "__main__":
    main()
