#!/usr/bin/env python3
"""Stage 4: program pools (S1 iteration-2 Qwen3-8B forced programs, S2 Qwen3-32B top-ups, S3 T1 references), ACCEPT,
SCRUB with the G-scrub assertions, the M-code sets (PRIMARY, M32, M8), the placement sets (SURV, BASE, DISOBEY),
the M-desc prompt set from the descriptions that passed the naming gate; then COMMIT #1b."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from loguru import logger

import expansion
import label_tp
import programs
import prompts_tp
import stage_cpu
from common import (CANON_ORDER, cap_first, commit, deviation, read_json, read_jsonl, sha256_file, sha256_text,
                    utc_now, write_json)
from tpg import B5, DATA, IN_E44, INPUTS, MCODE_MIN, MCODE_PER_ALG, PRED, RESULTS, ROOT, SEED, UDIJ


def _s1() -> list[dict[str, Any]]:
    out = []
    for r in read_jsonl(INPUTS / "exp9_forced.jsonl"):
        cond = r["condition"]
        alg = cond.split(":", 1)[1]
        code = r.get("code") or label_tp.extract_last_fence(r.get("text"))[0]
        out.append({"source": "S1", "author": "Qwen3-8B (iteration 2, thinking off)", "algorithm": alg,
                    "condition": cond, "code": code, "uid": f"S1|{cond}|{r.get('sample_id')}|{r.get('paraphrase_id')}",
                    "seed": r.get("seed")})
    return out


def _s2() -> list[dict[str, Any]]:
    out = []
    for r in read_jsonl(DATA / "topups.jsonl"):
        code = label_tp.extract_last_fence(r.get("content"))[0]
        out.append({"source": "S2", "author": "Qwen3-32B (OpenRouter DeepInfra fp8, thinking off)",
                    "algorithm": r["algorithm"], "condition": r["prompt_id"], "code": code,
                    "uid": f"S2|{r['algorithm']}|{r['slot']}", "provider": r.get("provider"), "seed": r.get("seed"),
                    "truncated": r.get("finish_reason") == "length"})
    return out


def _s3() -> list[dict[str, Any]]:
    return [{"source": "S3", "author": "hand-written reference (iteration 2)", "algorithm": r["algorithm"],
             "condition": "reference", "code": r["code"], "uid": f"S3|{r['file']}"} for r in stage_cpu.references()]


def _c6_rows() -> list[dict[str, Any]]:
    manual = {r["code_sha256"]: r for r in read_jsonl(IN_E44 / "data" / "manual_reads.jsonl")}
    rows = []
    for arm, f in (("screen", "labelled_C6_ban.jsonl"), ("confirm", "labelled_C6_confirm.jsonl"),
                   ("baseline", "labelled_C6_baseline.jsonl")):
        for r in read_jsonl(IN_E44 / "data" / f):
            lab = r.get("adj_label")
            other = r.get("adj_other_name")
            if r.get("code_sha256") in manual:
                lab = manual[r["code_sha256"]].get("label", lab)
                other = manual[r["code_sha256"]].get("other_name", other)
            rows.append({"arm": arm, "uid": r["uid"], "code": r.get("code"), "adj_label": lab, "other_name": other,
                         "passed": bool(r.get("passed")), "template": r.get("template"), "slot": r.get("slot"),
                         "code_sha256_original": r.get("code_sha256")})
    return rows


def g_scrub(items: list[dict[str, Any]], grids: list[dict[str, Any]], check_label: bool) -> list[dict[str, Any]]:
    """Scrub every item's code and attach the G-scrub assertion results."""
    for it in items:
        try:
            sc, mp = programs.scrub(it["code"])
            it["scrubbed"], it["rename_map"] = sc, mp
            it["dump_equal"] = programs.normalised_dump(it["code"]) == programs.normalised_dump(sc)
            it["alias_free"] = not programs.text_names_algorithm(sc)
        except (SyntaxError, ValueError, RecursionError) as e:
            it["scrubbed"], it["rename_map"], it["dump_equal"], it["alias_free"] = None, {}, False, False
            it["scrub_error"] = type(e).__name__
    ok = [it for it in items if it["scrubbed"]]
    ev_o = programs.evaluate([it["code"] for it in ok])
    ev_s = programs.evaluate([it["scrubbed"] for it in ok])
    tr_o = expansion.trace_many([it["code"] for it in ok], grids, timeout_s=1.5)
    tr_s = expansion.trace_many([it["scrubbed"] for it in ok], grids, timeout_s=1.5)
    for it, to, ts in zip(ok, tr_o, tr_s):
        eo, es = ev_o[sha256_text(it["code"])], ev_s[sha256_text(it["scrubbed"])]
        it["suites_pass_after"] = es["passed"] and es["passed_exp2"]
        it["suites_same"] = (eo["passed"], eo["passed_exp2"]) == (es["passed"], es["passed_exp2"])
        it["expansion_identical"] = expansion.expansion_signature(to) == expansion.expansion_signature(ts)
        it["labels_unchanged"] = (eo["runtime_label"], eo["ast_label"]) == (es["runtime_label"], es["ast_label"])
        it["runtime_label"], it["ast_label"] = eo["runtime_label"], eo["ast_label"]
        it["ds_flags"] = ts["flags"]
        it["scrubbed_sha256"] = sha256_text(it["scrubbed"])
        it["lexical_flag"] = programs.text_names_algorithm(it["code"])
        need_pass = it.get("must_pass", False)
        it["g_scrub_pass"] = bool(it["dump_equal"] and it["alias_free"] and it["expansion_identical"] and
                                  (it["labels_unchanged"] if check_label else True) and
                                  (it["suites_pass_after"] if need_pass else it["suites_same"]))
    for it in items:
        it.setdefault("g_scrub_pass", False)
    return items


def stage_pools(*args: str) -> None:
    label = args[0] if args else "COMMIT1b"
    if label != "COMMIT1b":
        deviation("D-gscrub-fix", "G-scrub re-run before any M-code state: the first run required tier-B programs to "
                                  "pass the hidden suites after scrubbing (they were never required to pass them); the "
                                  "check is now 'suites outcome unchanged' (placement SURV/BASE still must pass); the "
                                  "code-span check counts boundary-straddling tokens; commit " + label)
    rng = random.Random(SEED)
    grids = read_json(DATA / "probe_grids.json")["grids"]
    refs = stage_cpu.references()
    rt = read_json(DATA / "reference_traces.json")["traces"]
    ref_algs = [r["algorithm"] for r in refs]
    pool = _s1() + _s2() + _s3()
    logger.info(f"pool: {Counter(p['source'] for p in pool)}")
    acc = programs.accept([(p["code"], p["algorithm"]) for p in pool], grids, rt, ref_algs)
    for p, a in zip(pool, acc):
        p["accept"] = a
    deviation("D-accept-B", "M-code sets use tier-B acceptance (mechanism labels + committed AST rules + trace check + "
                            "valid paths on >= 38/40 probe grids) instead of the two hidden suites, for every source and "
                            "algorithm alike: under tier A (committed ACCEPT) 4 of 5 non-banned classes have < 10 "
                            "programs, mostly IDDFS/IDA*-style timeouts on the 30x30 hidden cases; tier-A counts are "
                            "reported in results/acceptance.json")
    accepted = [p for p in pool if p["accept"].get("accepted_b")]
    # dedupe by code
    seen = set()
    uniq = []
    for p in accepted:
        k = sha256_text(p["code"])
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    logger.info(f"accepted (unique): {Counter((p['source'], p['algorithm']) for p in uniq)}")
    g_scrub(uniq, grids, check_label=True)
    good = [p for p in uniq if p["g_scrub_pass"]]
    logger.info(f"G-scrub pass {len(good)}/{len(uniq)}")
    acc_summary = {}
    for src in ("S1", "S2", "S3"):
        for a in CANON_ORDER:
            cand = [p for p in pool if p["source"] == src and p["algorithm"] == a]
            if not cand:
                continue
            reasons = Counter(r for p in cand for r in p["accept"].get("reasons", []))
            acc_summary[f"{src}|{a}"] = {"candidates": len(cand), "accepted": sum(bool(p["accept"].get("accepted"))
                                                                                  for p in cand),
                                         "accepted_tier_b": sum(bool(p["accept"].get("accepted_b")) for p in cand),
                                         "g_scrub_pass": sum(1 for p in good if p["source"] == src and
                                                             p["algorithm"] == a), "reasons": dict(reasons)}
            dis = reasons.get("labeller_disagreement", 0)
            if len(cand) >= 10 and dis / len(cand) > 0.3:
                deviation(f"F9-{src}-{a}", f"{dis}/{len(cand)} labeller disagreements for {src} {a} (excluded; no "
                                           f"manual adjudication within the time box)")

    def pick(srcs: list[str], a: str) -> list[dict[str, Any]]:
        out = []
        for s in srcs:
            c = [p for p in good if p["source"] == s and p["algorithm"] == a]
            rng.shuffle(c)
            out += c
        dd, res = set(), []
        for p in out:
            if p["scrubbed_sha256"] not in dd:
                dd.add(p["scrubbed_sha256"])
                res.append(p)
        return res[:MCODE_PER_ALG]

    sets: dict[str, dict[str, list[dict[str, Any]]]] = {"PRIMARY": {}, "M32": {}, "M8": {}}
    for a in CANON_ORDER:
        sets["PRIMARY"][a] = pick(["S1", "S2", "S3"], a)
        sets["M32"][a] = pick(["S2"], a)
        sets["M8"][a] = pick(["S1"], a)
    flags = {name: {a: len(v) for a, v in s.items()} for name, s in sets.items()}
    excluded = {name: [a for a, n in f.items() if n < MCODE_MIN] for name, f in flags.items()}
    for name, ex in excluded.items():
        if ex:
            logger.warning(f"{name}: algorithms with < {MCODE_MIN} programs: {ex}")
    # placement sets from iteration 8's C6 rows
    c6 = _c6_rows()
    surv = [r for r in c6 if r["arm"] in ("screen", "confirm") and r["passed"] and r["code"] and
            r["adj_label"] not in B5 + ["invalid", "no_code", None] and
            (r["adj_label"] in CANON_ORDER or (r["adj_label"] == "other" and r["other_name"]))]
    base = [r for r in c6 if r["arm"] == "baseline" and r["passed"] and r["code"]]
    rng.shuffle(base)
    base = base[:50]
    dis = [r for r in c6 if r["arm"] in ("screen", "confirm") and r["code"] and r["adj_label"] in B5][:30]
    place = []
    for name, rows in (("SURV", surv), ("BASE", base), ("DISOBEY", dis)):
        for r in rows:
            place.append({"set": name, "source": "C6", "author": "Qwen3-32B thinking on (iteration 8 C6)",
                          "algorithm": r["adj_label"], "other_name": r["other_name"], "arm": r["arm"],
                          "uid": r["uid"], "code": r["code"], "passed": r["passed"], "template": r["template"],
                          "must_pass": name != "DISOBEY"})
    g_scrub(place, grids, check_label=False)
    logger.info(f"placement: {Counter((p['set'], p['algorithm']) for p in place)}; G-scrub pass "
                f"{sum(p['g_scrub_pass'] for p in place)}/{len(place)}")

    def slim(p: dict[str, Any], variant: int) -> dict[str, Any]:
        return {k: p.get(k) for k in ("source", "author", "algorithm", "uid", "condition", "scrubbed", "scrubbed_sha256",
                                      "rename_map", "ds_flags", "lexical_flag", "runtime_label", "ast_label",
                                      "g_scrub_pass", "set", "other_name", "arm", "template", "provider", "seed")} | \
            {"code_sha256": sha256_text(p["code"]), "context_variant": variant}

    out_sets = {name: {a: [slim(p, i % 5) for i, p in enumerate(v)] for a, v in s.items()} for name, s in sets.items()}
    out_place = [slim(p, i % 5) for i, p in enumerate(place) if p.get("scrubbed")]
    write_json(DATA / "mcode_sets.json", {"sets": out_sets, "counts": flags, "excluded_lt_min": excluded,
                                          "placement": out_place, "utc": utc_now(),
                                          "source_mix_primary": {a: dict(Counter(p["source"] for p in v))
                                                                 for a, v in sets["PRIMARY"].items()}})
    gs_all = uniq + place
    write_json(RESULTS / "g_scrub.json", {
        "n_checked": len(gs_all), "n_pass": sum(p["g_scrub_pass"] for p in gs_all),
        "failures": [{"uid": p["uid"], "dump_equal": p.get("dump_equal"), "alias_free": p.get("alias_free"),
                      "expansion_identical": p.get("expansion_identical"), "labels_unchanged":
                          p.get("labels_unchanged"), "suites_pass_after": p.get("suites_pass_after")}
                     for p in gs_all if not p["g_scrub_pass"]][:200],
        "planted": _planted_scrub_test(grids)})
    write_json(RESULTS / "acceptance.json", acc_summary)
    # M-desc prompts from the descriptions that passed the naming gate
    ng = read_json(RESULTS / "naming_gate.json")
    final = [r["final"] for r in ng["rows"] if r["passed"]]
    rows = []
    for d in sorted(final, key=lambda x: (CANON_ORDER.index(x["algorithm"]), x["desc_index"])):
        for t, tpl in enumerate(prompts_tp.forced_templates()):
            seg = tpl.replace("{X}", d["text"])
            rows.append({"algorithm": d["algorithm"], "template": t, "desc_index": d["desc_index"],
                         "desc_id": d["key"], "group": 3 * t + d["desc_index"], "text": d["text"],
                         "prompt": prompts_tp.make_prompt(seg), "naming_rate": d["rate"]})
    write_json(DATA / "mdesc_prompts.json", {"rows": rows, "n": len(rows),
                                            "per_algorithm": dict(Counter(r["algorithm"] for r in rows))})
    payload = {"label": "COMMIT1b", "utc": utc_now(),
               "files": {p: sha256_file(ROOT / p) for p in ["results/naming_gate.json", "data/mdesc_prompts.json",
                                                            "data/mcode_sets.json", "results/g_scrub.json",
                                                            "results/acceptance.json"]},
               "mcode_counts": flags, "mdesc_per_algorithm": dict(Counter(r["algorithm"] for r in rows)),
               "note": "final descriptions with naming results; M-code and placement program lists (code sha256, "
                       "source, context variant); before any M-desc or M-code state"}
    pth = PRED / ("commit1b.json" if label == "COMMIT1b" else f"{label.lower()}.json")
    payload["label"] = label
    write_json(pth, payload)
    commit(pth, label, "descriptions + program sets")
    _ = cap_first, UDIJ


def _planted_scrub_test(grids: list[dict[str, Any]]) -> dict[str, Any]:
    code = ("from collections import deque\n\ndef bfs(grid, start, goal):\n    # BFS over the grid\n    q = deque([start])\n"
            "    prev = {start: None}\n    while q:\n        cur = q.popleft()\n        if cur == goal:\n            out = []\n"
            "            while cur is not None:\n                out.append(cur)\n                cur = prev[cur]\n"
            "            return out[::-1]\n        r, c = cur\n        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n"
            "            n = (r + dr, c + dc)\n            if 0 <= n[0] < len(grid) and 0 <= n[1] < len(grid[0]) and "
            "grid[n[0]][n[1]] == '.' and n not in prev:\n                prev[n] = cur\n                q.append(n)\n"
            "    return []\n\ndef solve(grid, start, goal):\n    \"\"\"Breadth-first search.\"\"\"\n"
            "    if grid[start[0]][start[1]] != '.' or grid[goal[0]][goal[1]] != '.':\n        return []\n"
            "    return bfs(grid, start, goal)\n")
    sc, mp = programs.scrub(code)
    ev = programs.evaluate([code, sc])
    return {"clean": not programs.text_names_algorithm(sc), "passes": ev[sha256_text(sc)]["passed"],
            "rename_map": mp, "dump_equal": programs.normalised_dump(code) == programs.normalised_dump(sc),
            "scrubbed": sc}
