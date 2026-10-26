#!/usr/bin/env python3
"""STEP 1 (CPU): every prompt of iteration 7 with its positions and split -> prompts/prompts7.jsonl.

Per task t in (T2, T10, T03):
  ban[w]        W1-W5 frozen ban records (exp30 prompts6.jsonl, verbatim ids)
  twin[w][n]    12 neutral twins per template; noun 0 = exp30's frozen twin (verbatim ids); nouns 1-11 follow the
                frozen noun rule (rank by |tokens(' ' + noun) - tokens(' ' + X)|, ties -> higher SUBTLEX frequency,
                NOUN_EXCLUSIONS, no reuse within a task; pool = bench neutral_nouns.json U art_j3Rm_lr2nzR6 noun bank)
                and are padded with ' .' after the sentence to the ban's exact token length
  forced[k][Y]  FORCED_TEMPLATES k = 0..4 x every catalogue mode Y (Y = default gives the NULL source)
  padtwin[k][Y] the forced prompt with its segment tokens replaced by ' .' (exp30 pad_record)
  p0            the specification alone
  M-only (T2)   sham bans of every catalogue mode (W1-W5), leave-one-survivor multi-name bans (exp9 rule, W1/W5),
                two random seeds, exp30's semantic seed, 'Make a new algorithm.', exp18's LF2 novelty instruction
ASSERTIONS (stop on failure): within a task every prompt has identical ids from p1 on; twin and ban have equal length;
padtwin and forced have equal length; T2 forced k=0 bf_spfa reproduces exp30's FORCED prompt (sha256); the semantic
seed reproduces exp30's (sha256).
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

import prompts_v4 as P4
from cfg import INPUTS, TEMPLATES, cap_first, read_json, read_jsonl, setup_logging, sha256_text, write_json, \
    write_jsonl
from cfg7 import (CATALOGUE7, DEFAULT7, E30, FORCED_TEMPLATES7, HELD_FAM, HELD_W, INSTR, N_NOUNS, PROMPTS7,
                  SEED_STRINGS, TASKS7, TRAIN_FAM, TRAIN_NOUNS, TRAIN_W, VAL_NOUNS)

EXTRA_EXCL = {"sort", "set", "union", "label", "search", "depth", "breadth", "bucket", "dial", "flood", "order",
              "count", "number", "graph", "node", "edge", "tree", "path", "list", "value", "component", "heap",
              "select", "pivot", "median", "weight", "distance", "cycle", "loop", "group", "class", "function",
              "code", "task", "solution", "algorithm", "program", "problem", "answer", "result", "test"}
ALL_W = ("W1", "W2", "W3", "W4", "W5")


def load_tokenizer():
    from transformers import AutoTokenizer

    from cfg import model_path

    return AutoTokenizer.from_pretrained(model_path())


def task_spec(task: str) -> tuple[str, dict[str, str]]:
    """(spec text, {mode: display name}) for a task."""
    if task == "T2":
        fp = read_json(INPUTS / "exp8" / "prompts" / "frozen_prompts.json")
        return fp["spec"]["t2"], dict(fp["display"]["t2"])
    d = next(x for x in (INPUTS / "exp11" / "bench").iterdir() if x.name.startswith(task + "_"))
    sp = read_json(d / "spec.json")
    return sp["spec_text"], {c["mode"]: c["display_name"] for c in sp["catalogue"]}


def bench_nouns(task: str) -> list[dict[str, Any]]:
    if task == "T2":
        fp = read_json(INPUTS / "exp8" / "prompts" / "frozen_prompts.json")
        out = []
        for v in fp["tasks"]["t2"]["nouns"].values():
            out.append({"word": v["noun"], "freq": float(v.get("freq") or 0)})
            out += [{"word": c, "freq": 0.0} for c in v.get("companions", [])]
        return out
    d = next(x for x in (INPUTS / "exp11" / "bench").iterdir() if x.name.startswith(task + "_"))
    nn = read_json(d / "neutral_nouns.json")
    out = []
    for v in nn.values():
        out += [{"word": c["word"], "freq": float(c.get("subtlex_freq") or 0)} for c in v.get("nouns", [])]
    return out


def noun_rule(tok: Any, task: str, spec: str, x_display: str, noun0: str, dep_nouns: list[dict[str, Any]],
              n_needed: int) -> list[dict[str, Any]]:
    """Frozen noun rule: rank pool nouns by |ntok(' ' + noun) - ntok(' ' + X)|, ties -> higher frequency, then word."""
    pool: dict[str, float] = {}
    for r in bench_nouns(task) + dep_nouns:
        w = str(r["word"]).strip()
        if not w or not w.isalpha():
            continue
        pool[w.lower()] = max(pool.get(w.lower(), 0.0), float(r.get("freq") or 0))
    nx = len(tok(" " + x_display, add_special_tokens=False)["input_ids"])
    excl = set(P4.NOUN_EXCLUSIONS) | EXTRA_EXCL | {noun0.lower()}
    cands = []
    for w, f in pool.items():
        if w in excl or re.search(rf"\b{re.escape(w)}\b", spec, re.I) or re.search(rf"\b{re.escape(w)}\b",
                                                                                    x_display, re.I):
            continue
        nt = len(tok(" " + w, add_special_tokens=False)["input_ids"])
        cands.append({"word": w, "freq": f, "ntok": nt, "dist": abs(nt - nx)})
    cands.sort(key=lambda r: (r["dist"], -r["freq"], r["word"]))
    return cands[:n_needed]


def rec(task: str, kind: str, ids: list[int], p0: int, p1: int, se: int, segment: str, *, w: str | None = None,
        noun_idx: int | None = None, noun: str | None = None, fam: int | None = None, Y: str | None = None,
        cond: list[int] | None = None, source: str = "", split: str = "m_only", extra: dict | None = None
        ) -> dict[str, Any]:
    key = "|".join(str(x) for x in (task, kind, w if w is not None else (f"F{fam}" if fam is not None else "-"),
                                    f"n{noun_idx}" if noun_idx is not None else (Y or "-")))
    if kind in ("forced", "padtwin", "shamban"):
        key = f"{task}|{kind}|{w if kind == 'shamban' else 'F' + str(fam)}|{Y}"
    r = {"key": key, "task": task, "kind": kind, "w": w, "noun_idx": noun_idx, "noun": noun, "fam": fam, "Y": Y,
         "ids": list(ids), "P": len(ids), "p0": int(p0), "p1": int(p1), "spec_end": int(se), "R": len(ids) - 1,
         "cond": cond, "segment": segment, "source": source, "split": split,
         "prompt_sha256": sha256_text(json.dumps(list(ids)))}
    if extra:
        r.update(extra)
    return r


def pad_ids(tok: Any, ids: list[int], p0: int, p1: int) -> tuple[list[int], list[int]]:
    """exp30 pad_record: tokens [p0, k) -> ' .' where k is the first trailing newline-bearing token before p1."""
    dot = tok(" .", add_special_tokens=False)["input_ids"]
    assert len(dot) == 1
    out = list(ids)
    k = p1
    while k > p0 and "\n" in tok.decode([out[k - 1]]):
        k -= 1
    for i in range(p0, k):
        out[i] = dot[0]
    return out, [p0, k]


def build(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from prompts6 import dep_extract  # reads all ten datasets of art_j3Rm_lr2nzR6 (data/dep_extract.json)

    dep = dep_extract()
    dep_nouns = [{"word": n["word"], "freq": n["freq"]} for n in dep["noun_bank_single_token"]]
    p6 = {(r["task"], r["w"], r["kind"]): r for r in read_jsonl(E30 / "prompts" / "prompts6.jsonl")}
    ext30 = read_json(E30 / "ext_prompts.json")
    rows: list[dict[str, Any]] = []
    report: dict[str, Any] = {"nouns": {}, "excluded": [], "n_by_kind": {}}
    for task in TASKS7:
        spec, disp = task_spec(task)
        D = DEFAULT7[task]
        assert set(disp) == set(CATALOGUE7[task]), f"{task}: catalogue {sorted(disp)} != {CATALOGUE7[task]}"
        tw0 = p6[(task, "W1", "twin")]
        p1_ref = tw0["p1"]
        spec_ids = tw0["ids"][p1_ref:]
        # ---------------------------------------------------------------- bans + noun-0 twins (exp30 verbatim)
        noun0 = None
        for w in ALL_W:
            bn, tw = p6[(task, w, "ban")], p6[(task, w, "twin")]
            assert bn["ids"][bn["p1"]:] == spec_ids and tw["ids"][tw["p1"]:] == spec_ids
            sp = "train" if w in TRAIN_W else ("held" if w == HELD_W else "w4")
            rows.append(rec(task, "ban", bn["ids"], 3, bn["p1"], bn["spec_end"], bn["segment"], w=w, Y=None,
                            cond=bn["cond"], source="exp30 prompts6 ban", split=sp))
            if noun0 is None:
                seg0 = tw["segment"]
                m = re.search(r"use (\w+)", seg0) or re.search(r"rely on (\w+)", seg0) or re.search(r"Avoid (\w+)",
                                                                                                 seg0)
                noun0 = m.group(1) if m else "man"
        x_disp = disp[D]
        nouns = noun_rule(tok, task, spec, x_disp, noun0, dep_nouns, 3 * N_NOUNS)
        used: list[dict[str, Any]] = [{"word": noun0, "source": "exp30 twin noun (noun 0)"}]
        twin_rows: dict[tuple[str, int], dict[str, Any]] = {}
        for w in ALL_W:
            tw = p6[(task, w, "twin")]
            sp = ("train" if 0 in TRAIN_NOUNS else "val") if w in TRAIN_W else ("held" if w == HELD_W else "w4")
            twin_rows[(w, 0)] = rec(task, "twin", tw["ids"], 3, tw["p1"], tw["spec_end"], tw["segment"], w=w,
                                    noun_idx=0, noun=noun0, Y=D, cond=tw["cond"], source="exp30 prompts6 twin",
                                    split=sp)
        ci = 0
        n_idx = 1
        while n_idx < N_NOUNS:
            assert ci < len(nouns), f"{task}: noun pool exhausted"
            cand = nouns[ci]["word"]
            ci += 1
            made = {}
            ok = True
            for w in ALL_W:
                bn = p6[(task, w, "ban")]
                base_seg = TEMPLATES[w][1].format(N=cand)
                got = None
                for d in range(0, 30):
                    seg = base_seg + " ." * d
                    ids = P4.chat_ids(tok, cap_first(seg) + "\n\n" + spec)
                    if len(ids) > bn["P"]:
                        break
                    if len(ids) == bn["P"]:
                        p0, p1, se = P4.positions(tok, ids, spec)
                        if p1 == bn["p1"] and se == bn["spec_end"] and ids[p1:] == bn["ids"][p1:]:
                            got = (seg, ids, p0, p1, se, d)
                        break
                if got is None:
                    ok = False
                    report["excluded"].append({"task": task, "noun": cand, "w": w, "why": "no exact length match"})
                    break
                made[w] = got
            if not ok:
                continue
            for w, (seg, ids, p0, p1, se, d) in made.items():
                bn = p6[(task, w, "ban")]
                diff = [i for i in range(len(ids)) if ids[i] != bn["ids"][i]]
                c0, c1 = (diff[0], diff[-1] + 1) if diff else (p0, p0)
                assert c1 <= p1
                if w in TRAIN_W:
                    sp = "train" if n_idx in TRAIN_NOUNS else "val"
                else:
                    sp = "held" if w == HELD_W else "w4"
                twin_rows[(w, n_idx)] = rec(task, "twin", ids, p0, p1, se, seg, w=w, noun_idx=n_idx, noun=cand, Y=D,
                                            cond=[c0, c1], source=f"noun rule #{n_idx} (pad {d})", split=sp)
            used.append({"word": cand, "freq": nouns[ci - 1]["freq"], "ntok": nouns[ci - 1]["ntok"]})
            n_idx += 1
        rows += [twin_rows[k] for k in sorted(twin_rows)]
        report["nouns"][task] = used
        # ---------------------------------------------------------------- forced + padding twins
        for k in range(5):
            for Y in CATALOGUE7[task]:
                seg = FORCED_TEMPLATES7[k].format(j=disp[Y])
                ids = P4.chat_ids(tok, cap_first(seg) + "\n\n" + spec)
                p0, p1, se = P4.positions(tok, ids, spec)
                assert ids[p1:] == spec_ids, f"{task}/F{k}/{Y}: spec ids differ"
                sp = "train" if k in TRAIN_FAM else "held"
                fr = rec(task, "forced", ids, p0, p1, se, cap_first(seg), fam=k, Y=Y, cond=None,
                         source=f"FORCED_TEMPLATES[{k}]", split=sp, extra={"is_null": Y == D})
                rows.append(fr)
                pids, cond = pad_ids(tok, ids, p0, p1)
                assert len(pids) == len(ids) and pids[p1:] == ids[p1:]
                rows.append(rec(task, "padtwin", pids, p0, p1, se, tok.decode(pids[cond[0]:cond[1]]), fam=k, Y=Y,
                                cond=cond, source=f"padding twin of forced F{k}/{Y}", split=sp,
                                extra={"padded_of": fr["key"]}))
                if task == "T2" and k == 0 and Y == "bf_spfa":
                    ref = next(r for r in ext30 if r["task"] == "T2" and r["kind"] == "forced")
                    assert fr["prompt_sha256"] == ref["prompt_sha256"], "T2 F0 bf_spfa != exp30 FORCED prompt"
                    pref = next(r for r in ext30 if r["task"] == "T2" and r["kind"] == "forced_pad")
                    assert rows[-1]["prompt_sha256"] == pref["prompt_sha256"], "T2 padtwin != exp30 FORCEDPAD"
                    report["exp30_forced_reproduced"] = True
        # ---------------------------------------------------------------- spec only
        ids = P4.chat_ids(tok, spec)
        p0, p1, se = P4.positions(tok, ids, spec)
        assert ids[p1:] == spec_ids
        rows.append(rec(task, "p0", ids, p0, p1, se, "", source="specification only"))
        # ---------------------------------------------------------------- M-only prompts (T2)
        if task == "T2":
            fp9 = read_json(Path("/dev/null")) if False else None  # noqa: F841 - exp9 rule reproduced below
            order = CATALOGUE7["T2"]  # exp9 canonical order of t2: dijkstra, bf_spfa, bidijkstra, floyd, dial
            for w in ALL_W:
                for Y in order:
                    if Y == D:
                        continue
                    seg = TEMPLATES[w][0].format(X=disp[Y])
                    ids = P4.chat_ids(tok, cap_first(seg) + "\n\n" + spec)
                    p0, p1, se = P4.positions(tok, ids, spec)
                    assert ids[p1:] == spec_ids
                    rows.append(rec(task, "shamban", ids, p0, p1, se, cap_first(seg), w=w, Y=Y,
                                    source="sham single-name ban of a non-default mode"))
            for w in ("W1", "W5"):
                for surv in order:
                    banned = [m for m in order if m != surv]
                    r_ = (int(w[1]) - 1) % len(banned)
                    banned = banned[r_:] + banned[:r_]
                    names = [disp[m] for m in banned]
                    joined = ", ".join(names[:-1]) + " or " + names[-1]
                    seg = TEMPLATES[w][0].format(X=joined)
                    ids = P4.chat_ids(tok, cap_first(seg) + "\n\n" + spec)
                    p0, p1, se = P4.positions(tok, ids, spec)
                    assert ids[p1:] == spec_ids
                    rows.append(rec(task, "multiban", ids, p0, p1, se, cap_first(seg), w=w, Y=surv,
                                    source="exp9 leave-one-survivor rule (names joined, order rotated by w-1)",
                                    extra={"banned": banned, "survivor": surv}))
            for kind, text in list(SEED_STRINGS.items()) + list(INSTR.items()):
                ids = P4.chat_ids(tok, text + "\n\n" + spec)
                p0, p1, se = P4.positions(tok, ids, spec)
                assert ids[p1:] == spec_ids
                rows.append(rec(task, kind, ids, p0, p1, se, text, source="seed / instruction before the spec"))
            sem = next(r for r in ext30 if r["task"] == "T2" and r["kind"] == "semseed")
            ids = P4.chat_ids(tok, cap_first(sem["segment"]) + "\n\n" + spec)
            p0, p1, se = P4.positions(tok, ids, spec)
            assert ids[p1:] == spec_ids
            r_sem = rec(task, "seed_sem", ids, p0, p1, se, cap_first(sem["segment"]),
                        source="exp30 semantic seed (exp6 wording, W1)")
            report["semseed_matches_exp30"] = r_sem["prompt_sha256"] == sem["prompt_sha256"]
            rows.append(r_sem)
    # ---------------------------------------------------------------- global checks
    for task in TASKS7:
        rs = [r for r in rows if r["task"] == task]
        tails = {json.dumps(r["ids"][r["p1"]:]) for r in rs}
        assert len(tails) == 1, f"{task}: ids from p1 differ across prompts"
        assert len({r["spec_end"] - r["p1"] for r in rs}) == 1
        keys = [r["key"] for r in rs]
        assert len(keys) == len(set(keys)), f"{task}: duplicate keys {[k for k, c in Counter(keys).items() if c > 1]}"
    report["n_by_kind"] = {t: dict(Counter(r["kind"] for r in rows if r["task"] == t)) for t in TASKS7}
    report["n_prompts"] = len(rows)
    return rows, report


def cpu_tests(rows: list[dict[str, Any]], tok: Any) -> dict[str, Any]:
    """Plan CPU tests (1) and (2)."""
    out: dict[str, Any] = {}
    by = {r["key"]: r for r in rows}
    n_pairs = 0
    for r in rows:
        if r["kind"] == "twin":
            bn = by[f"{r['task']}|ban|{r['w']}|-"]
            assert r["P"] == bn["P"] and r["ids"][r["p1"]:] == bn["ids"][bn["p1"]:] and r["p1"] == bn["p1"]
            n_pairs += 1
        if r["kind"] == "padtwin":
            fr = by[r["padded_of"]]
            assert r["P"] == fr["P"] and r["ids"][r["p1"]:] == fr["ids"][fr["p1"]:]
            n_pairs += 1
    out["T1_equal_length_identical_spec_pairs"] = n_pairs
    # determinism of the noun rule
    rows2, _ = build(tok)
    out["T1_noun_rule_deterministic"] = [r["prompt_sha256"] for r in rows2] == [r["prompt_sha256"] for r in rows]
    assert out["T1_noun_rule_deterministic"]
    # split disjointness
    for t in TASKS7:
        tr = {(r["w"], r["noun_idx"]) for r in rows if r["task"] == t and r["kind"] == "twin" and r["split"] == "train"}
        va = {(r["w"], r["noun_idx"]) for r in rows if r["task"] == t and r["kind"] == "twin" and r["split"] == "val"}
        he = {(r["w"], r["noun_idx"]) for r in rows if r["task"] == t and r["kind"] == "twin" and r["split"] == "held"}
        assert not (tr & va) and not (tr & he) and not (va & he)
        assert all(w in ("W1", "W2", "W3") for w, _ in tr | va) and all(w == "W5" for w, _ in he)
        assert not ({n for _, n in tr} & {n for _, n in va})
        ftr = {r["fam"] for r in rows if r["task"] == t and r["kind"] in ("forced", "padtwin") and r["split"] == "train"}
        fhe = {r["fam"] for r in rows if r["task"] == t and r["kind"] in ("forced", "padtwin") and r["split"] == "held"}
        assert ftr == {0, 1, 2} and fhe == {3, 4}
    out["T2_split_disjoint"] = True
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("prompts7")
    tok = load_tokenizer()
    rows, report = build(tok)
    write_jsonl(PROMPTS7, rows)
    tests = cpu_tests(rows, tok)
    report["cpu_tests"] = tests
    write_json(Path(PROMPTS7).parent / "prompt_report7.json", report)
    logger.info(f"prompts7: {len(rows)} prompts; kinds {report['n_by_kind']}; nouns "
                f"{ {t: [n['word'] for n in v] for t, v in report['nouns'].items()} }; tests {tests}")


def load_prompts7() -> dict[str, dict[str, Any]]:
    return {r["key"]: r for r in read_jsonl(PROMPTS7)}


if __name__ == "__main__":
    main()
