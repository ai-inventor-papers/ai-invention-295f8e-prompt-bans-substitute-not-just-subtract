#!/usr/bin/env python3
"""q_lik (S5): the it model's teacher-forced likelihood of each catalogue algorithm's opening under the twin prompts.

select (CPU):  for every unit and catalogue algorithm a: forced programs written by gemma-3-4b-it (raw_forced6) that
               pass all hidden tests AND are labelled a; name-scrubbed (bench scrub_code; path tasks: bench scrub +
               a path-alias pass), re-tested and re-labelled (kept only if still passing with label a); first 10 by
               slot order (paraphrase k, draw j). Fill < 10 from the ITER2 bench forced_programs.jsonl (Qwen-written,
               scrubbed, test-passing) and then the exp8 suite references (flag source). < 3 -> THIN_QLIK.
               Also the Qwen-written sensitivity set (bench tasks: ITER2 programs only).
               The opening prefix = the modal pre-code text of the twin outputs (frozen before scoring).
score (GPU):   ids = twin_ids(W) + ids(prefix) + ids(code)[:48] (tokenised separately, concatenated); batch-1
               teacher forcing (exp28 tf_logprobs), lm_head only at the 48 target positions; raw = sum, norm = mean;
               s_u(a) = mean over programs x W1-W5. fp32 re-score of a 10% subsample; committed switch rule.
Outputs: data/qlik_programs.jsonl, data/qlik_tf.jsonl, results/qlik_scores.json, results/qlik_numerics.json.
"""

from __future__ import annotations

import ast
import collections
import gc
import io
import json
import keyword
import random
import re
import sys
import time
import tokenize
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, BENCH, DATA_DIR, E28_DATA, FORCED_KEEP, PATH_TASKS, QLIK_WINDOW, RESULTS_DIR, SUITE,
                 TEMPLATE_IDS, append_jsonl, bench_paths, read_json, read_jsonl, setup_logging, sha256_text,
                 utc_now, write_json, write_jsonl)
import prompts as PG
import prompts6 as P6

bench_paths()
PROG = DATA_DIR / "qlik_programs.jsonl"
TF = DATA_DIR / "qlik_tf.jsonl"
PATH_ALIASES = ("bfs", "dfs", "bibfs", "bidir", "iddfs", "deepening", "astar", "a_star", "gbfs", "best_first",
                "bestfirst", "dijkstra", "bellman", "ford", "spfa", "dial", "floyd", "warshall")
SUITE_REF_MODE = {"t1": {"astar_fg": "astar_gbfs", "gbfs_counter": "astar_gbfs", "bfs_deque_parent": "bfs",
                         "bfs_listpop_pathcarry": "bfs", "bibfs_deques": "bibfs", "bibfs_sets": "bibfs",
                         "dfs_recursive": "dfs", "dfs_stack": "dfs", "dijkstra_counter": "dijkstra",
                         "dijkstra_lazy": "dijkstra", "iddfs_iterative": "iddfs", "iddfs_recursive": "iddfs"},
                  "t2": {"bellman_ford": "bf_spfa", "spfa": "bf_spfa", "bidijkstra_alternate": "bidijkstra",
                         "bidijkstra_reverse": "bidijkstra", "dial_dict": "dial", "dial_list": "dial",
                         "dijkstra_decreasekey": "dijkstra", "dijkstra_lazy": "dijkstra", "floyd_bigint": "floyd",
                         "floyd_inf": "floyd"}}


# ------------------------------------------------------------------------------------------------ scrubbing
def _strip_docstrings(code: str) -> str:
    tree = ast.parse(code)
    lines = code.split("\n")
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body:
            f = node.body[0]
            if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str):
                spans.append((f.lineno, f.end_lineno, len(node.body) == 1))
    for lo, hi, only in sorted(spans, reverse=True):
        indent = re.match(r"\s*", lines[lo - 1]).group(0)
        lines[lo - 1:hi] = [indent + "pass"] if only else []
    return "\n".join(lines)


def scrub_path(code: str) -> tuple[str, dict[str, Any]]:
    """Path-task pass on top of the bench scrubber: drop comments and docstrings that name a path alias, rename
    user-defined identifiers that contain one (helperN / varN)."""
    info: dict[str, Any] = {"renamed": {}, "ok": True, "error": None}
    try:
        code = _strip_docstrings(code) if any(a in code.lower() for a in PATH_ALIASES) else code
        tree = ast.parse(code)
    except SyntaxError as e:
        return code, {**info, "ok": False, "error": f"syntax: {e}"}
    defined: set[str] = set()
    funcs: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(n.name)
            for a in n.args.args + n.args.kwonlyargs:
                defined.add(a.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            defined.add(n.id)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | funcs | defined
    rename = {}
    for nm in sorted(defined | funcs):
        if nm == "solve" or nm in P6.PG.signature("T1") or not any(a in nm.lower() for a in PATH_ALIASES):
            continue
        if nm in ("grid", "start", "goal", "n", "edges", "source", "target"):
            continue
        base = "helper" if nm in funcs else "var"
        i = 1
        while f"{base}{i}" in used:
            i += 1
        rename[nm] = f"{base}{i}"
        used.add(rename[nm])
    edits = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError) as e:
        return code, {**info, "ok": False, "error": f"tokenize: {e}"}
    prev = None
    for tk in toks:
        if tk.type == tokenize.NAME and tk.string in rename and not keyword.iskeyword(tk.string):
            is_attr = prev is not None and prev.type == tokenize.OP and prev.string == "."
            if not is_attr:
                edits.append((tk.start[0], tk.start[1], tk.end[1], rename[tk.string]))
        elif tk.type == tokenize.COMMENT and any(a in tk.string.lower() for a in PATH_ALIASES):
            edits.append((tk.start[0], tk.start[1], tk.end[1], ""))
        if tk.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            prev = tk
    lines = code.split("\n")
    for row, c0, c1, rep in sorted(edits, key=lambda e: (e[0], -e[1])):
        ln = lines[row - 1]
        lines[row - 1] = (ln[:c0] + rep + ln[c1:]).rstrip() if rep == "" else ln[:c0] + rep + ln[c1:]
    out = "\n".join(lines)
    try:
        compile(out, "<scrubbed>", "exec")
    except SyntaxError as e:
        info.update(ok=False, error=f"scrubbed does not compile: {e}")
    info["renamed"] = rename
    return out, info


def scrub(task: str, code: str) -> tuple[str, dict[str, Any]]:
    from bench.common.scrub import scrub_code

    s, info = scrub_code(code)
    if task in PATH_TASKS and info.get("ok", True):
        s2, info2 = scrub_path(s)
        info = {**info, "path_pass": info2}
        s = s2
        info["ok"] = bool(info2.get("ok"))
    return s.rstrip() + "\n", info


# ------------------------------------------------------------------------------------------------ selection (CPU)
def relabel(task: str, code: str, tag: str) -> dict[str, Any]:
    import label_worker as LW

    row = {"row_id": f"qlik_scrub|{task}|{tag}", "task": task, "arm": "forced_scrub", "stage": "qlik_scrub",
           "text": "```python\n" + code.rstrip() + "\n```", "template": None}
    return LW.label_rows([row], judge=True)[0]


def opening_prefix() -> dict[str, Any]:
    """Modal pre-code text of the twin outputs (exp28 slots 0-9 + iteration-6 twin rows)."""
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    labs.update({r["row_id"]: r for r in read_jsonl(E28_DATA / "labels.jsonl") if r.get("stage") == "twin"})
    cnt: collections.Counter = collections.Counter()
    n = 0
    for f in (E28_DATA / "raw_twin.jsonl", DATA_DIR / "raw_twin6.jsonl"):
        for r in read_jsonl(f):
            lab = labs.get(r["row_id"])
            code = (lab or {}).get("code")
            if not code:
                continue
            first = code.split("\n")[0]
            i = r["text"].find(first)
            if i < 0:
                continue
            cnt[r["text"][:i]] += 1
            n += 1
    top = cnt.most_common(5)
    return {"prefix": top[0][0] if top else "```python\n", "n_rows": n, "top5": top,
            "share": (top[0][1] / n) if (top and n) else None}


def _sort_key(r: dict[str, Any]) -> tuple:
    return (int(r.get("paraphrase_id") or 0), int(str(r["row_id"]).split("|")[-1]))


def select_programs(tasks: list[str]) -> None:
    labs = {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}
    raw = read_jsonl(DATA_DIR / "raw_forced6.jsonl")
    done = {(r["task"], r["mode"]) for r in read_jsonl(PROG)}
    out_rows = []
    summary = {}
    for t in tasks:
        for m in P6.catalogue(t):
            if (t, m) in done:
                continue
            cand = sorted([r for r in raw if r["task"] == t and r.get("forced_mode") == m], key=_sort_key)
            n_gen = len(cand)
            ok_rows = [r for r in cand if (labs.get(r["row_id"]) or {}).get("passed")
                       and (labs.get(r["row_id"]) or {}).get("label") == m]
            kept = []
            n_scrub_fail = 0
            for r in ok_rows:
                if len(kept) >= FORCED_KEEP:
                    break
                code = labs[r["row_id"]]["code"]
                s, info = scrub(t, code)
                if not info.get("ok", True):
                    n_scrub_fail += 1
                    continue
                lab2 = relabel(t, s, sha256_text(s)[:16])
                if lab2.get("passed") and lab2.get("label") == m:
                    kept.append({"task": t, "mode": m, "source": "gemma_it_forced", "row_id": r["row_id"],
                                 "code": s, "code_sha256": sha256_text(s), "renamed": info.get("renamed"),
                                 "label_after_scrub": lab2["label"]})
                else:
                    n_scrub_fail += 1
            n_own = len(kept)
            fill_src = []
            if len(kept) < FORCED_KEEP and t not in PATH_TASKS:
                from bench.common.catalogue import TASKS

                q = [x for x in read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl")
                     if x.get("forced_mode") == m and x.get("passed") and x.get("label") == m]
                for x in q:
                    if len(kept) >= FORCED_KEEP:
                        break
                    kept.append({"task": t, "mode": m, "source": "iter2_qwen_forced", "row_id": x["sample_id"],
                                 "code": x["code"].rstrip() + "\n", "code_sha256": sha256_text(x["code"]),
                                 "label_after_scrub": x["label"]})
                    fill_src.append("iter2_qwen_forced")
            if len(kept) < FORCED_KEEP:
                refs = []
                if t in PATH_TASKS:
                    sub = {"T1": "t1_grid", "T2": "t2_wsp"}[t]
                    key = {"T1": "t1", "T2": "t2"}[t]
                    refs = [p for p in sorted((SUITE / "tasks" / sub / "references").glob("*.py"))
                            if SUITE_REF_MODE[key].get(p.stem) == m]
                else:
                    from bench.common.catalogue import TASKS

                    p = BENCH / TASKS[t]["task_id"] / "references" / f"{m}.py"
                    if p.exists():
                        refs = [p]
                    elif t == "R6" and m == "linear_scan":
                        refs = [Path(__file__).resolve().parents[1] / "extensions" / "R6" / "linear_scan.py"]
                for p in refs:
                    if len(kept) >= FORCED_KEEP:
                        break
                    s, info = scrub(t, p.read_text())
                    kept.append({"task": t, "mode": m, "source": "suite_or_bench_reference", "row_id": p.name,
                                 "code": s, "code_sha256": sha256_text(s), "label_after_scrub": m})
                    fill_src.append("reference")
            summary[f"{t}|{m}"] = {"generated": n_gen, "passing_and_labelled": len(ok_rows), "kept_own": n_own,
                                   "scrub_or_relabel_fail": n_scrub_fail, "filled": len(kept) - n_own,
                                   "fill_sources": sorted(set(fill_src)), "n_final": len(kept),
                                   "THIN_QLIK": len(kept) < 3}
            for j, k in enumerate(kept):
                k["j"] = j
            out_rows += kept
            append_jsonl(PROG, kept if kept else [{"task": t, "mode": m, "source": "none", "code": None, "j": -1}])
            logger.info(f"q_lik programs {t}/{m}: gen {n_gen}, ok {len(ok_rows)}, own {n_own}, final {len(kept)}")
    prev = read_json(RESULTS_DIR / "qlik_selection.json") if (RESULTS_DIR / "qlik_selection.json").exists() else {}
    prev.update(summary)
    write_json(RESULTS_DIR / "qlik_selection.json", prev)
    write_json(RESULTS_DIR / "qlik_opening_prefix.json", opening_prefix())


def qwen_programs(tasks: list[str]) -> list[dict[str, Any]]:
    """Sensitivity set: ITER2 Qwen-written scrubbed forced programs (bench tasks only), first 10 per algorithm."""
    from bench.common.catalogue import TASKS

    out = []
    for t in tasks:
        if t in PATH_TASKS:
            continue
        rows = read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl")
        for m in P6.catalogue(t):
            q = [x for x in rows if x.get("forced_mode") == m and x.get("passed") and x.get("label") == m][:FORCED_KEEP]
            for j, x in enumerate(q):
                out.append({"task": t, "mode": m, "source": "iter2_qwen_forced", "row_id": x["sample_id"],
                            "code": x["code"].rstrip() + "\n", "j": j})
    return out


# ------------------------------------------------------------------------------------------------ scoring (GPU)
def window_ids(tok: Any, prompt_ids: list[int], prefix: str, code: str) -> tuple[list[int], list[int], str]:
    pre = tok(prefix, add_special_tokens=False)["input_ids"]
    cid = tok(code, add_special_tokens=False)["input_ids"][:QLIK_WINDOW]
    ids = list(prompt_ids) + list(pre) + list(cid)
    targets = list(range(len(prompt_ids) + len(pre), len(ids)))
    return ids, targets, tok.decode(cid)


def score_set(R: Any, progs: list[dict[str, Any]], prefix: str, tag: str, done: set[str]) -> list[dict[str, Any]]:
    import engine as EG

    out = []
    tw = {(t, w): PG.p_twin(t, w)["ids"] for t in {p["task"] for p in progs} for w in TEMPLATE_IDS}
    t0 = time.time()
    for i, p in enumerate(progs):
        for w in TEMPLATE_IDS:
            key = f"{tag}|{p['task']}|{p['mode']}|{p['j']}|{w}"
            if key in done:
                continue
            ids, tg, _ = window_ids(R.tok, tw[(p["task"], w)], prefix, p["code"])
            lp = EG.tf_logprobs(R.model, ids, tg)
            out.append({"key": key, "set": tag, "task": p["task"], "mode": p["mode"], "j": p["j"], "template": w,
                        "source": p["source"], "raw": float(np.sum(lp)), "norm": float(np.mean(lp)),
                        "n_tokens": len(lp), "precision": R.dtype})
        if len(out) >= 500:
            append_jsonl(TF, out)
            done |= {o["key"] for o in out}
            out = []
            logger.info(f"tf {tag}: {i + 1}/{len(progs)} programs; {time.time() - t0:.0f}s")
    append_jsonl(TF, out)
    return out


def aggregate(tf_rows: list[dict[str, Any]], tag: str) -> dict[str, Any]:
    by = collections.defaultdict(list)
    for r in tf_rows:
        if r["set"] == tag:
            by[(r["task"], r["mode"])].append(r)
    res: dict[str, Any] = {}
    for (t, m), rr in by.items():
        per_w = collections.defaultdict(list)
        for r in rr:
            per_w[r["template"]].append(r["norm"])
        res.setdefault(t, {})[m] = {"norm": float(np.mean([r["norm"] for r in rr])),
                                    "raw": float(np.mean([r["raw"] for r in rr])),
                                    "n_programs": len({r["j"] for r in rr}), "n_passes": len(rr),
                                    "sources": dict(collections.Counter(r["source"] for r in rr if r["template"] == "W1")),
                                    "per_template_norm": {w: float(np.mean(v)) for w, v in per_w.items()},
                                    "template_range_norm": float(max(np.mean(v) for v in per_w.values())
                                                                 - min(np.mean(v) for v in per_w.values()))}
    return res


def score_all(R: Any, tasks: list[str], fp32: bool = False) -> None:
    progs = [p for p in read_jsonl(PROG) if p.get("code")]
    progs = [p for p in progs if p["task"] in tasks]
    prefix = read_json(RESULTS_DIR / "qlik_opening_prefix.json")["prefix"]
    done = {r["key"] for r in read_jsonl(TF)}
    score_set(R, progs, prefix, "own_bf16", done)
    qp = qwen_programs(tasks)
    score_set(R, qp, prefix, "qwen_bf16", done)
    tf = read_jsonl(TF)
    out = {"prefix": prefix, "own": aggregate(tf, "own_bf16"), "qwen_only": aggregate(tf, "qwen_bf16"),
           "precision": "bf16", "window": QLIK_WINDOW, "utc": utc_now()}
    write_json(RESULTS_DIR / "qlik_scores.json", out)
    logger.info("bf16 q_lik scores written")


def top1(agg: dict[str, Any], t: str, nondef: list[str], key: str = "norm") -> str | None:
    s = {m: v[key] for m, v in agg.get(t, {}).items() if m in nondef and v.get("n_programs", 0) > 0}
    return sorted(s, key=lambda m: (-s[m], m))[0] if len(s) >= 2 else None


def fp32_check(tasks: list[str], seed: int = 0) -> None:
    """Free the bf16 model first; load text-only fp32; re-score a 10% subsample (stratified by unit) at batch 1;
    the committed switch rule: top-1 flips on >= 2 units -> re-score everything in fp32."""
    import torch

    import engine as EG

    progs = [p for p in read_jsonl(PROG) if p.get("code") and p["task"] in tasks]
    prefix = read_json(RESULTS_DIR / "qlik_opening_prefix.json")["prefix"]
    rng = random.Random(seed)
    keys = [(p, w) for p in progs for w in TEMPLATE_IDS]
    sub = rng.sample(keys, max(1, len(keys) // 10))
    R = FP32Runner()
    tw = {(t, w): PG.p_twin(t, w)["ids"] for t in tasks for w in TEMPLATE_IDS}
    bf = {r["key"]: r for r in read_jsonl(TF) if r["set"] == "own_bf16"}
    deltas, rows = [], []
    for p, w in sub:
        ids, tg, _ = window_ids(R.tok, tw[(p["task"], w)], prefix, p["code"])
        lp = EG.tf_logprobs(R.model, ids, tg)
        k = f"own_bf16|{p['task']}|{p['mode']}|{p['j']}|{w}"
        if k in bf:
            deltas.append(abs(float(np.sum(lp)) - bf[k]["raw"]))
        rows.append({"key": k.replace("own_bf16", "own_fp32sub"), "set": "own_fp32sub", "task": p["task"],
                     "mode": p["mode"], "j": p["j"], "template": w, "source": p["source"], "raw": float(np.sum(lp)),
                     "norm": float(np.mean(lp)), "n_tokens": len(lp), "precision": "fp32"})
    append_jsonl(TF, rows)
    # top-1 comparison on the subsample keys only (same programs/templates in both precisions)
    sc = read_json(RESULTS_DIR / "qlik_scores.json")
    fc = read_json(Path(__file__).resolve().parents[1] / "predictions" / "forecasts_draft.json") \
        if (Path(__file__).resolve().parents[1] / "predictions" / "forecasts_draft.json").exists() else None
    sub_bf = aggregate([dict(bf[r["key"].replace("own_fp32sub", "own_bf16")], set="sub") for r in rows
                        if r["key"].replace("own_fp32sub", "own_bf16") in bf], "sub")
    sub_fp = aggregate([dict(r, set="sub") for r in rows], "sub")
    flips = []
    for t in tasks:
        cat = P6.catalogue(t)
        D = (fc or {}).get("units", {}).get(t, {}).get("D") if fc else None
        nd = [m for m in cat if m != D]
        a, b = top1(sub_bf, t, nd), top1(sub_fp, t, nd)
        if a is not None and b is not None and a != b:
            flips.append({"task": t, "bf16": a, "fp32": b})
    res = {"n_subsample": len(rows), "median_abs_delta_raw_nats": float(np.median(deltas)) if deltas else None,
           "max_abs_delta_raw_nats": float(np.max(deltas)) if deltas else None, "top1_flips_on_subsample": flips,
           "switch_to_fp32": len(flips) >= 2, "rule": "top-1 flips on >= 2 units -> re-score all in fp32"}
    if res["switch_to_fp32"]:
        done = {r["key"] for r in read_jsonl(TF)}
        score_set(R, progs, prefix, "own_fp32", done)
        tf = read_jsonl(TF)
        sc["own_bf16"] = sc["own"]
        sc["own"] = aggregate(tf, "own_fp32")
        sc["precision"] = "fp32 (switch rule fired)"
        write_json(RESULTS_DIR / "qlik_scores.json", sc)
    write_json(RESULTS_DIR / "qlik_numerics.json", res)
    logger.info(f"fp32 check: {res}")
    del R
    gc.collect()
    torch.cuda.empty_cache()


class FP32Runner:
    """Text-only fp32 load of gemma-3-4b-it (same key map as engine.load_model)."""

    def __init__(self) -> None:
        import torch
        from safetensors import safe_open
        from transformers import AutoConfig, AutoTokenizer, Gemma3ForCausalLM

        from cfg import MODELS, model_path

        mid, rev = MODELS["it"]
        path = model_path(mid, rev)
        self.tok = AutoTokenizer.from_pretrained(path)
        cfg = AutoConfig.from_pretrained(path)
        tcfg = cfg.text_config
        tcfg._attn_implementation = "sdpa"
        old = torch.get_default_dtype()
        torch.set_default_dtype(torch.float32)
        try:
            with torch.device("cuda"):
                model = Gemma3ForCausalLM(tcfg)
        finally:
            torch.set_default_dtype(old)
        model.eval()
        model.requires_grad_(False)
        sd = model.state_dict()
        idx = json.loads((Path(path) / "model.safetensors.index.json").read_text())
        for fn in sorted(set(idx["weight_map"].values())):
            with safe_open(str(Path(path) / fn), framework="pt", device="cuda") as fh:
                for k in fh.keys():
                    if not k.startswith("language_model.model."):
                        continue
                    nk = "model." + k[len("language_model.model."):]
                    sd[nk].copy_(fh.get_tensor(k).to(torch.float32))
        model.tie_weights()
        model._aii_kind = "it"
        self.model = model
        self.dtype = "fp32"


@logger.catch(reraise=True)
def main() -> None:
    cmd = sys.argv[1]
    tasks = list(ALL_TASKS)
    if "--tasks" in sys.argv:
        tasks = sys.argv[sys.argv.index("--tasks") + 1].split(",")
    setup_logging(f"qlik6_{cmd}")
    if cmd == "select":
        select_programs(tasks)
    elif cmd == "score":
        from gen6 import Runner6

        R = Runner6("it")
        score_all(R, tasks)
        import engine as EG

        EG.free_model(R.model)
        del R
        gc.collect()
        fp32_check(tasks)
    elif cmd == "fp32":
        fp32_check(tasks)


if __name__ == "__main__":
    main()
