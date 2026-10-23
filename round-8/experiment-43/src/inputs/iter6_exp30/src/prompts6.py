#!/usr/bin/env python3
"""STEP 1 (CPU): every prompt of this artifact with its positions -> prompts/prompts6.jsonl + prompts/positions.json,
and STEP 0's dependency extract (art_j3Rm_lr2nzR6, all ten datasets) -> data/dep_extract.json.

Kinds per (task, template):
  twin     the frozen neutral twin (bench: exp13 prompt_ids == exp27 prompts; path: exp8 neutral_A)
  ban      the full ban of the default (bench: exp13 prompt_ids; path: exp8 'ban')
  placebo  a second neutral twin of identical token length (path: exp8 neutral_B; bench: the twin with its one-token
           noun replaced by the most frequent single-token noun-bank candidate of art_j3Rm_lr2nzR6 concreteness_norms)
  top5ban  T1 only: exp9 'multi:TOP5' literal ban segment (exp20 prompts.TOP5_SEGMENTS) + the T1 spec
Assertions (stop on failure): twin, ban and placebo have equal length and IDENTICAL ids from the first 'Task:' token
on; the twin reproduces exp27's prompt ids; COND = the span where ban and twin differ lies before 'Task:'.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger

from cfg import (INPUTS, ROOT, TEMPLATE_TAIL, cap_first, read_json, read_jsonl, setup_logging, sha256_text,
                 write_json, write_jsonl)
from cfg6 import BENCH6, DEP_DIR, EXP8_TASK6, PATH6, POSITIONS, PROMPTS6, TEMPLATES6
import prompts_v4 as P4

NOUN_EXCLUSIONS = P4.NOUN_EXCLUSIONS
TOP5_SEGMENTS = {  # exp20 src/prompts.py (exp9 session-2 'multi:TOP5' segments, verbatim)
    "W1": "Do not use breadth-first search (BFS), depth-first search (DFS), iterative deepening DFS (IDDFS), A* search "
          "or greedy best-first search for this task.",
    "W2": "Your solution must not rely on depth-first search (DFS), iterative deepening DFS (IDDFS), A* search, greedy "
          "best-first search or breadth-first search (BFS).",
    "W3": "Avoid iterative deepening DFS (IDDFS), A* search, greedy best-first search, breadth-first search (BFS) or "
          "depth-first search (DFS) entirely.",
    "W4": "A* search, greedy best-first search, breadth-first search (BFS), depth-first search (DFS) or iterative "
          "deepening DFS (IDDFS) is not allowed here.",
    "W5": "Write a correct solution that does not use greedy best-first search, breadth-first search (BFS), "
          "depth-first search (DFS), iterative deepening DFS (IDDFS) or A* search.",
}
ALL_W = TEMPLATES6 + ("W4",)


def load_tokenizer():
    from transformers import AutoTokenizer

    from cfg import model_path

    return AutoTokenizer.from_pretrained(model_path())


def _rec(task: str, w: str, kind: str, ids: list[int], p1: int, spec_end: int, cond: list[int] | None,
         segment: str, source: str) -> dict[str, Any]:
    return {"task": task, "w": w, "kind": kind, "ids": list(ids), "P": len(ids), "p1": int(p1),
            "spec_end": int(spec_end), "cond": cond, "R": len(ids) - 1, "segment": segment, "source": source,
            "prompt_sha256": sha256_text(json.dumps(list(ids)))}


# ------------------------------------------------------------------------------------------------ dependency
def dep_extract() -> dict[str, Any]:
    """Read every dataset of art_j3Rm_lr2nzR6 once; keep what this artifact uses (noun bank for placebo twins, bench
    hidden-test fallback ids, a known-solution corpus for the novelty audit, the llm-creativity T02 label reference)."""
    out_p = ROOT / "data" / "dep_extract.json"
    if out_p.exists():
        return read_json(out_p)
    src = DEP_DIR / "full_data_out.json"
    logger.info(f"reading dependency {src.name} ({src.stat().st_size / 1e6:.0f} MB)")
    d = json.loads(src.read_text())
    counts, nouns, corpus, creativity, tests_fallback, clrs_algs = {}, [], [], Counter(), {}, Counter()
    bench_q = {"215": "T03", "547": "T10", "323": "T10", "1": "T05", "287": "T06", "743": "T02"}
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        counts[name] = len(ex)
        for e in ex:
            if name == "concreteness_norms":
                if str(e.get("metadata_noun_bank_candidate")) == "True" and \
                        str(e.get("metadata_qwen3_tokens_with_leading_space")) == "1":
                    nouns.append({"word": e["input"], "conc": float(e["output"]),
                                  "freq": float(e.get("metadata_subtlex_frequency") or 0)})
            elif name == "leetcodedataset":
                q = str(e.get("metadata_question_id"))
                if q in bench_q:
                    corpus.append({"src": f"leetcodedataset:{q}", "task": bench_q[q], "code": e["output"]})
                    tests_fallback[bench_q[q] + ":" + q] = int(e.get("metadata_n_test_cases_parsed") or 0)
            elif name == "mercury":
                bt = str(e.get("metadata_bench_task") or "")
                for tq, tt in (("T03_", "T03"), ("T10_", "T10"), ("T05_", "T05"), ("T06_", "T06")):
                    if bt.startswith(tq):
                        corpus.append({"src": f"mercury:{e.get('metadata_question_id')}:"
                                              f"{e.get('metadata_solution_index')}", "task": tt, "code": e["output"]})
            elif name == "llm_creativity":
                creativity[str(e.get("metadata_t02_mode"))] += 1
            elif name in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
                named = str(e.get("metadata_bench_tasks_named") or e.get("metadata_bench_task") or "")
                code = e["input"] if name == "thealgorithms_python" else e["output"]
                for tq, tt in (("T03", "T03"), ("T10", "T10"), ("T05", "T05"), ("T06", "T06"), ("T02", "T02"),
                               ("T01", "T1")):
                    if tq in named:
                        corpus.append({"src": f"{name}:{e.get('metadata_row_index')}", "task": tt, "code": code})
            elif name == "clrs_text":
                clrs_algs[str(e.get("metadata_algorithm"))] += 1
            elif name in ("humanevalplus", "enamel"):
                pass  # counted only: harness-validation sets (no bench task); listed in dependency_usage
    nouns.sort(key=lambda r: (-r["freq"], r["word"]))
    out = {"counts": counts, "noun_bank_single_token": nouns[:200], "n_noun_bank_single_token": len(nouns),
           "known_solution_corpus": corpus, "llm_creativity_T02_labels": dict(creativity),
           "leetcode_hidden_test_counts": tests_fallback, "clrs_algorithms": dict(clrs_algs),
           "usage": {"concreteness_norms": "single-token neutral nouns for the bench placebo twins",
                     "leetcodedataset": "bench reference programs (novelty-audit corpus) + hidden-test fallback count",
                     "mercury": "human solutions of the bench tasks (novelty-audit corpus)",
                     "thealgorithms_python": "named implementations (novelty-audit corpus)",
                     "kodcode_algorithmic": "GPT-4o verified solutions naming a bench mode (novelty-audit corpus)",
                     "xlcost_python": "GeeksforGeeks programs naming a bench mode (novelty-audit corpus)",
                     "llm_creativity": "T02 label distribution of the reference repository (external reference)",
                     "clrs_text": "algorithm inventory of CLRS-30 traces (catalogue coverage check)",
                     "humanevalplus": "counted; harness-validation set, no bench task (not used in any claim)",
                     "enamel": "counted; efficiency references, no bench task (not used in any claim)"}}
    del d
    write_json(out_p, out)
    logger.info(f"dependency extract: {counts}; {len(nouns)} single-token noun-bank nouns; corpus {len(corpus)}")
    return out


# ------------------------------------------------------------------------------------------------ prompts
def build(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    e13 = read_json(INPUTS / "exp13" / "prompts" / "prompt_ids.json")
    e27 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(ROOT / "prompts" / "prompts.jsonl")}
    fp = read_json(INPUTS / "exp8" / "prompts" / "frozen_prompts.json")
    dep = dep_extract()
    nouns = [n["word"] for n in dep["noun_bank_single_token"] if n["word"].lower() not in NOUN_EXCLUSIONS]
    rows: list[dict[str, Any]] = []
    rep: dict[str, Any] = {"placebo_nouns": {}, "cond_spans": {}}
    for t in BENCH6:
        for w in ALL_W:
            tw, bn = e13[f"{t}|twin|{w}"], e13[f"{t}|ban|{w}"]
            it, ib = list(tw["ids"]), list(bn["ids"])
            p1, se = tw["spec_span"]
            assert list(bn["spec_span"]) == [p1, se] and len(it) == len(ib), f"{t}/{w}: ban/twin spans differ"
            assert it[p1:] == ib[p1:], f"{t}/{w}: ids from 'Task:' on differ"
            assert e27[(t, w, "twin")]["ids"] == it, f"{t}/{w}: twin differs from exp27 prompts"
            diff = [i for i in range(len(it)) if it[i] != ib[i]]
            c0, c1 = diff[0], diff[-1] + 1
            assert c1 <= p1, f"{t}/{w}: condition span reaches into the spec"
            seg_tw = e27[(t, w, "twin")]["segment"]
            rows.append(_rec(t, w, "twin", it, p1, se, [c0, c1], seg_tw, "exp13 prompt_ids twin (== exp27)"))
            rows.append(_rec(t, w, "ban", ib, p1, se, [c0, c1], tok.decode(ib[3:p1]).strip(), "exp13 prompt_ids ban"))
            # placebo: swap the twin's one-token noun for a second single-token noun, re-render, assert ids
            noun_tok = it[c0]
            noun = tok.decode([noun_tok]).strip()
            spec = tok.decode(it[p1:se])
            made = None
            for cand in nouns:
                if cand.lower() == noun.lower():
                    continue
                seg_pl = re.sub(rf"\b{re.escape(noun)}\b", cand, seg_tw, count=1)
                if seg_pl == seg_tw:
                    continue
                ids_pl = P4.chat_ids(tok, cap_first(seg_pl) + "\n\n" + spec)
                if len(ids_pl) == len(it) and ids_pl[p1:] == it[p1:] and ids_pl[:c0] == it[:c0] and \
                        ids_pl[c0 + 1:] == it[c0 + 1:]:
                    made = (cand, seg_pl, ids_pl)
                    break
            assert made is not None, f"{t}/{w}: no length-matched placebo noun"
            rows.append(_rec(t, w, "placebo", made[2], p1, se, [c0, c1], made[1],
                             f"twin noun '{noun}' -> '{made[0]}' (art_j3Rm_lr2nzR6 concreteness_norms)"))
            rep["placebo_nouns"][f"{t}|{w}"] = [noun, made[0]]
            rep["cond_spans"][f"{t}|{w}"] = [c0, c1]
    for t in PATH6:
        td = fp["tasks"][EXP8_TASK6[t]]
        spec = fp["spec"][EXP8_TASK6[t]]
        for w in ALL_W:
            tp = td["templates"][w]
            it, ib, ip = (json.loads(tp[k]["ids"]) if isinstance(tp[k]["ids"], str) else list(tp[k]["ids"])
                          for k in ("neutral_A", "ban", "neutral_B"))
            ref = e27[(t, w, "twin")]
            assert ref["ids"] == it, f"{t}/{w}: twin differs from exp27"
            p1, se = ref["p1"], ref["spec_end"]
            assert len(it) == len(ib) == len(ip) and it[p1:] == ib[p1:] == ip[p1:], f"{t}/{w}: ids differ after Task:"
            diff = [i for i in range(len(it)) if it[i] != ib[i]]
            c0, c1 = diff[0], diff[-1] + 1
            assert c1 <= p1
            rows.append(_rec(t, w, "twin", it, p1, se, [c0, c1], tp["neutral_A"]["segment"], "exp8 neutral_A"))
            rows.append(_rec(t, w, "ban", ib, p1, se, [c0, c1], tp["ban"]["segment"], "exp8 ban"))
            rows.append(_rec(t, w, "placebo", ip, p1, se, [c0, c1], tp["neutral_B"]["segment"], "exp8 neutral_B"))
            rep["cond_spans"][f"{t}|{w}"] = [c0, c1]
            rep["placebo_nouns"][f"{t}|{w}"] = [tp["neutral_A"].get("noun"), tp["neutral_B"].get("noun")]
            if t == "T1":
                ids5 = P4.chat_ids(tok, TOP5_SEGMENTS[w] + "\n\n" + spec)
                _p0, q1, qse = P4.positions(tok, ids5, spec)
                assert ids5[q1:] == it[p1:], "T1 TOP5 ban: spec ids differ"
                rows.append(_rec(t, w, "top5ban", ids5, q1, qse, None, TOP5_SEGMENTS[w], "exp20 TOP5_SEGMENTS"))
    pos = {f"{r['task']}|{r['w']}|{r['kind']}": {k: r[k] for k in ("P", "p1", "spec_end", "cond", "R",
                                                                    "prompt_sha256")} for r in rows}
    rep["n_prompts"] = len(rows)
    rep["kinds"] = dict(Counter(r["kind"] for r in rows))
    return rows, {"report": rep, "positions": pos}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("prompts6")
    tok = load_tokenizer()
    rows, out = build(tok)
    write_jsonl(PROMPTS6, rows)
    write_json(POSITIONS, out["positions"])
    write_json(ROOT / "results" / "prompt_report6.json", out["report"])
    logger.info(f"prompts6: {len(rows)} prompts {out['report']['kinds']}; placebo nouns "
                f"{out['report']['placebo_nouns']}")


def load_prompts6() -> dict[tuple[str, str, str], dict[str, Any]]:
    return {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(PROMPTS6)}


if __name__ == "__main__":
    main()
