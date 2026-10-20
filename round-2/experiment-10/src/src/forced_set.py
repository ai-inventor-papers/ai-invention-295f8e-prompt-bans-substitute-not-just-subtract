#!/usr/bin/env python3
"""S2 (CPU): forced set, name scrub, validation, coverage, scored text.

2.1 per (task, j): attempted forced programs whose combined label is j (passing or not), in generation order
    (round = sample_id, then paraphrase id) up to M = 30; M_j < 30 flagged, M_j < 10 -> j excluded from FRLP.
    Halves: shuffle with random.Random(f'half|{task}|{j}'); half 1 = first ceil(M/2), half 2 = the rest.
2.2 scrub (src/scrub.py); 2.3 re-run the canon tests + labeller on every scrubbed program: pass status and label must be
    unchanged, else conservative scrub (comments/strings only), else drop (logged).
    Coverage: max Jaccard of identifier-normalised AST 4-gram shingles of every natural program labelled j against j's
    forced programs vs the leave-one-out natural-to-natural maximum.
2.4 scored text '```python\\n' + code.rstrip('\\n') + '\\n```' -> token ids, n_fence (opening-fence tokens).
T3 (token part): for code-only sampled responses the rebuilt scored text must reproduce the generated ids.
"""

from __future__ import annotations

import ast
import collections
import math
import random
from typing import Any

import numpy as np
from loguru import logger

from src.ws import DATA, RESULTS, patch_canon_caches, read_jsonl, setup_logging, write_json
from src import config as K
from src.scrub import residual_names, scored_text, scrub

patch_canon_caches()
import pipeline as P  # noqa: E402  (canon)
from labeller.extract import extract_code  # noqa: E402

M_TARGET = 30
M_MIN = 10
FORCED_SET = DATA / "forced_set.jsonl"
NATURAL_PHASES = ("A1", "A4", "A5", "C")


def labelled() -> list[dict[str, Any]]:
    return read_jsonl(DATA / "labelled.jsonl")


def build_forced_set() -> dict[str, Any]:
    rows = [r for r in labelled() if r["kind"] in ("forced", "forced_desc") and r.get("code")]
    out: dict[str, Any] = {}
    for task in K.TASKS:
        for j in K.MODES[task]:
            att = [r for r in labelled() if r["task"] == task and r["kind"] in ("forced", "forced_desc") and r["X"] == j]
            cand = [r for r in rows if r["task"] == task and r["X"] == j and r["label"] == j]
            cand.sort(key=lambda r: (r["phase"] != "A2", r["sample_id"], r["paraphrase_id"], r["kind"]))
            kept = cand[:M_TARGET]
            rng = random.Random(f"half|{task}|{j}")
            sh = list(kept)
            rng.shuffle(sh)
            h1 = math.ceil(len(sh) / 2)
            for i, r in enumerate(sh):
                r["half"] = 1 if i < h1 else 2
            other_labels = collections.Counter(r["label"] for r in att if r["label"] != j)
            out[f"{task}:{j}"] = {"task": task, "j": j, "attempts": len(att), "labelled_j": len(cand), "M": len(kept),
                                  "flag_M_lt_30": len(kept) < M_TARGET, "excluded_M_lt_10": len(kept) < M_MIN,
                                  "attempts_descriptive": sum(1 for r in att if r["kind"] == "forced_desc"),
                                  "other_labels_of_attempts": dict(other_labels), "programs": sh}
    return out


UNRESOLVED = ("unknown", "inconsistent", None)


def _validate(progs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-run the canon tests + mechanical labellers on scrubbed variants (rows built so extract_code returns the
    scrubbed code). Label unchanged <=> (i) the (runtime, AST) pair is unchanged (the judge saw the same pair before), or
    (ii) the new pair agrees on the original label, or (iii) the blind judge (only when the pair changed and disagrees,
    within the remaining judge cap) returns the original label."""
    import labeller.judge as J
    from common import JUDGE_MODEL
    from src.label_worker import judge_cap

    rows = [{"task": p["task"], "text": scored_text(p["code_try"]), "row_id": p["row_id"]} for p in progs]
    lab = P.label_rows(rows, use_judge=False)
    out: list[dict[str, Any]] = []
    need: list[int] = []
    for i, (p, l) in enumerate(zip(progs, lab)):
        new_pair = (l["runtime_label"], l["ast_label"])
        orig_pair = (p["runtime_label"], p["ast_label"])
        rec = {"passed": l["passed"], "runtime_label": new_pair[0], "ast_label": new_pair[1]}
        if new_pair == orig_pair:
            rec.update({"label": p["label"], "labeller_source": "mechanical_pair_unchanged"})
        elif new_pair[0] == new_pair[1] and new_pair[0] not in UNRESOLVED:
            rec.update({"label": new_pair[0], "labeller_source": "agree"})
        else:
            rec.update({"label": None, "labeller_source": "needs_judge"})
            need.append(i)
        out.append(rec)
    if need:
        # exactly the code extract_code returns from the scored text
        items = [{"task": progs[i]["task"], "code": progs[i]["code_try"].rstrip() + "\n"} for i in need]
        js, stop = J.judge_many(items, JUDGE_MODEL, "judge", judge_cap("judge"))
        for i, jr in zip(need, js):
            if jr and jr.get("label"):
                out[i].update({"label": jr["label"], "labeller_source": "judge"})
            else:
                out[i].update({"label": "unverified_no_judge_budget", "labeller_source": "fallback_no_judge"})
    return out


def scrub_and_validate(fs: dict[str, Any]) -> dict[str, Any]:
    tok = K.tokenizer()
    all_progs = [p for v in fs.values() for p in v["programs"]]
    for p in all_progs:
        try:
            p["code_try"], p["scrub_info"] = scrub(p["code"], rename=True)
            p["scrub_mode"] = "full"
        except (SyntaxError, ValueError, IndentationError) as e:  # unparsable original (e.g. Python-2 tuple params)
            logger.warning(f"scrub failed for {p['row_id']}: {e} -> dropped (cannot be name-scrubbed)")
            p["code_try"], p["scrub_info"], p["scrub_mode"] = p["code"], {"error": str(e)}, "dropped"
    todo = [p for p in all_progs if p["scrub_mode"] != "dropped"]
    lab = _validate(todo)
    redo = []
    for p, l in zip(todo, lab):
        ok = (l["passed"] == p["passed"]) and (l["label"] == p["label"])
        p["validation_full"] = {"passed": l["passed"], "label": l["label"], "source": l["labeller_source"], "ok": ok}
        if not ok:
            redo.append(p)
    logger.info(f"scrub validation (full): {len(todo) - len(redo)}/{len(todo)} unchanged; "
                f"{len(all_progs) - len(todo)} unparsable programs dropped")
    if redo:
        for p in redo:
            p["code_try"], p["scrub_info"] = scrub(p["code"], rename=False)
            p["scrub_mode"] = "conservative"
        lab2 = _validate(redo)
        for p, l in zip(redo, lab2):
            ok = (l["passed"] == p["passed"]) and (l["label"] == p["label"])
            p["validation_conservative"] = {"passed": l["passed"], "label": l["label"], "source": l["labeller_source"],
                                            "ok": ok}
            if not ok:
                p["scrub_mode"] = "dropped"
    report = {"n": len(all_progs), "unparsable_dropped": len(all_progs) - len(todo), "full_ok": len(todo) - len(redo),
              "conservative": sum(1 for p in all_progs if p["scrub_mode"] == "conservative"),
              "dropped": sum(1 for p in all_progs if p["scrub_mode"] == "dropped"), "per_algorithm": {}}
    for key, v in fs.items():
        kept = [p for p in v["programs"] if p["scrub_mode"] != "dropped"]
        nd = len(v["programs"]) - len(kept)
        report["per_algorithm"][key] = {"M_before": len(v["programs"]), "dropped": nd,
                                        "drop_rate": nd / max(1, len(v["programs"])),
                                        "flag_drop_gt_20pct": nd > 0.2 * max(1, len(v["programs"]))}
        v["programs"] = kept
        v["M"] = len(kept)
        v["excluded_M_lt_10"] = len(kept) < M_MIN
        v["flag_M_lt_30"] = len(kept) < M_TARGET
    for p in all_progs:
        p["code_scrubbed"] = p.pop("code_try")
        p["residual_names"] = residual_names(p["code_scrubbed"])
        txt = scored_text(p["code_scrubbed"])
        enc = tok(txt, add_special_tokens=False, return_offsets_mapping=True)
        p["scored_ids"] = list(enc["input_ids"])
        p["n_fence"] = sum(1 for (a, _b) in enc["offset_mapping"] if a < len("```python\n"))
        p["n_tokens"] = len(p["scored_ids"])
        txt0 = scored_text(p["code"])  # unscrubbed (sensitivity)
        p["unscrubbed_ids"] = tok(txt0, add_special_tokens=False)["input_ids"]
    report["n_with_residual_names"] = sum(1 for p in all_progs if p["residual_names"] and p["scrub_mode"] == "full")
    return report


# ------------------------------------------------------------------------------------------------ coverage
def shingles(code: str, n: int = 4) -> set[tuple[str, ...]]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return set()
    seq = []
    for node in ast.walk(tree):
        t = type(node).__name__
        if isinstance(node, ast.Constant):
            t = f"Const:{type(node.value).__name__}"
        elif isinstance(node, ast.Attribute):
            t = f"Attr:{node.attr}"  # library attributes (popleft, heappush) are mechanism-bearing
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in dir(__builtins__):
            t = f"Call:{node.func.id}"
        seq.append(t)
    return {tuple(seq[i:i + n]) for i in range(max(0, len(seq) - n + 1))}


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def coverage(fs: dict[str, Any]) -> dict[str, Any]:
    nat = [r for r in labelled() if r["phase"] in NATURAL_PHASES and r.get("code")]
    out = {}
    for key, v in fs.items():
        task, j = v["task"], v["j"]
        fsh = [shingles(p["code"]) for p in v["programs"]]
        nj = [r for r in nat if r["task"] == task and r["label"] == j]
        nsh = [shingles(r["code"]) for r in nj]
        f2n = [max((jacc(s, f) for f in fsh), default=float("nan")) for s in nsh]
        n2n = [max((jacc(s, t) for k2, t in enumerate(nsh) if k2 != k), default=float("nan")) for k, s in enumerate(nsh)]
        out[key] = {"n_natural": len(nj), "n_forced": len(fsh),
                    "forced_to_natural_max_jaccard_mean": float(np.nanmean(f2n)) if f2n else None,
                    "natural_loo_max_jaccard_mean": float(np.nanmean(n2n)) if len(nsh) > 1 else None,
                    "forced_to_natural_median": float(np.nanmedian(f2n)) if f2n else None,
                    "natural_loo_median": float(np.nanmedian(n2n)) if len(nsh) > 1 else None}
    return out


# ------------------------------------------------------------------------------------------------ T3 (token part)
def t3_token_check() -> dict[str, Any]:
    tok = K.tokenizer()
    rows = [r for r in read_jsonl(DATA / "raw_gen.jsonl") if r["kind"] != "free" and r.get("gen_ids")]
    n_single, n_match, mism = 0, 0, []
    for r in rows:
        text = r["text"]
        s = text.strip()
        single = s.startswith("```") and s.endswith("```") and s.count("```") == 2 and text == s
        if not single:
            continue
        n_single += 1
        code, how = extract_code(text)
        if code is None:
            continue
        ids = tok(scored_text(code), add_special_tokens=False)["input_ids"]
        gen = [g for g in r["gen_ids"] if g not in K.EOS_IDS]
        if ids == gen:
            n_match += 1
        elif len(mism) < 5:
            mism.append({"row_id": r["row_id"], "n_scored": len(ids), "n_gen": len(gen),
                         "first_diff": next((i for i, (a, b) in enumerate(zip(ids, gen)) if a != b), min(len(ids), len(gen)))})
    return {"n_responses": len(rows), "n_single_fenced_block": n_single,
            "share_single_fenced_block": n_single / max(1, len(rows)), "n_token_exact": n_match,
            "share_token_exact_among_single": n_match / max(1, n_single), "mismatch_examples": mism,
            "flag_single_block_below_80pct": n_single / max(1, len(rows)) < 0.8}


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s2_forced_set")
    fs = build_forced_set()
    for key, v in fs.items():
        logger.info(f"{key}: attempts={v['attempts']} labelled_j={v['labelled_j']} M={v['M']}")
    rep = scrub_and_validate(fs)
    logger.info(f"scrub report: {rep}")
    rows = []
    for key, v in fs.items():
        for p in v["programs"]:
            rows.append({"program_id": f"{v['task']}|{v['j']}|{p['row_id']}", "task": v["task"], "j": v["j"],
                         "half": p["half"], "row_id": p["row_id"], "phase": p["phase"], "kind": p["kind"],
                         "paraphrase_id": p["paraphrase_id"], "sample_id": p["sample_id"],
                         "generating_cond": p["condition"], "passed": p["passed"], "label": p["label"],
                         "labeller_source": p["labeller_source"], "scrub_mode": p["scrub_mode"],
                         "scrub_info": p.get("scrub_info"), "residual_names": p["residual_names"],
                         "code": p["code"], "code_scrubbed": p["code_scrubbed"], "scored_ids": p["scored_ids"],
                         "unscrubbed_ids": p["unscrubbed_ids"], "n_fence": p["n_fence"], "n_tokens": p["n_tokens"]})
    from src.ws import C

    C.write_jsonl(FORCED_SET, rows)
    summary = {k: {kk: vv for kk, vv in v.items() if kk != "programs"} for k, v in fs.items()}
    write_json(RESULTS / "forced_set_summary.json", {"per_algorithm": summary, "scrub": rep})
    write_json(RESULTS / "coverage.json", coverage(fs))
    write_json(RESULTS / "t3_token_check.json", t3_token_check())
    logger.info(f"forced set: {len(rows)} programs written")


if __name__ == "__main__":
    main()
