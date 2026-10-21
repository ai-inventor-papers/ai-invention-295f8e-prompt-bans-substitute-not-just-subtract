#!/usr/bin/env python3
"""S2.7 prompts for 15 tasks, all through the Qwen3 chat template with thinking disabled.

kinds:
- twin   W1-W5 neutral twins: exp17 prompts.jsonl (14 tasks, exp7 frozen padding rule) and R2 (built here; the padding
         count comes from tokenising the default's DISPLAY NAME alone -- an R2 ban sentence is never constructed);
- ban    exp17's five modal-ban prompts (14 tasks; forward passes only, never sampled here; never for R2);
- plain  the specification with no condition segment;
- named  30 per algorithm: 10 forced_templates x 3 names (display name + first two aliases that are no other mode's);
- masked 30 per algorithm: 10 descriptive frames x 3 leak-checked descriptions (prompts/descriptions.json);
- knob_* C2b prompt knobs with recorded outcomes: exp13 nonce (W1-W5) and novelty for the 12 bench tasks; exp7
         novelty / mention for T1/T2 (exp17 bans are kind 'ban').
Every prompt of a task shares the identical token ids on [p1, spec_end) (asserted).
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from cfg4 import (BENCH, DEFAULT4, DESC_FRAMES, E7, E8, E13, E17, N_PARA, PAD_FILLER, PATH_CATALOGUE, PATH_TASKS,
                  PROMPTS4, PROMPTS_DIR, TASKS15, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, cap_first, read_json,
                  read_jsonl, sha256_text, write_json, write_jsonl)
from describe import bench_dir, leak_terms, leaks, norm_text, task_spec_text


def chat_ids(tok: Any, user_text: str) -> list[int]:
    ids = tok.apply_chat_template([{"role": "user", "content": user_text}], tokenize=True,
                                  add_generation_prompt=True, enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    return list(ids)


def positions(tok: Any, ids: list[int], spec: str) -> tuple[int, int, int]:
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    assert ids[:len(head)] == head, "unexpected chat header"
    suf = tok(spec + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    tail = tok(TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    return len(head), p1, len(ids) - len(tail)


def render(tok: Any, task: str, kind: str, segment: str | None, spec: str, **meta: Any) -> dict[str, Any]:
    text = spec if not segment else cap_first(segment) + "\n\n" + spec
    ids = chat_ids(tok, text)
    p0, p1, se = positions(tok, ids, spec)
    pid = "|".join(str(x) for x in (task, kind, meta.get("X") or "-", meta.get("template_id") or "-",
                                    meta.get("name_variant") if meta.get("name_variant") is not None else "-"))
    return {"pid": pid, "task": task, "kind": kind, "segment": cap_first(segment) if segment else "",
            "user_text": text, "ids": ids, "P": len(ids), "p0": p0, "p1": p1, "spec_end": se,
            "prompt_sha256": sha256_text(json.dumps(ids)), **meta}


def named_variants(task: str) -> dict[str, list[str]]:
    if task in PATH_TASKS:
        return {m: v[:3] for m, v in PATH_CATALOGUE[task].items()}
    spec = read_json(bench_dir(task) / "spec.json")
    al = spec.get("aliases", {})
    disp = {c["mode"]: c["display_name"] for c in spec["catalogue"]}
    out = {}
    for m, dn in disp.items():
        others = {norm_text(a) for mm, aa in al.items() if mm != m for a in aa} | \
                 {norm_text(d) for mm, d in disp.items() if mm != m}
        names = [dn]
        for a in al.get(m, []):
            if len(names) == 3:
                break
            na = norm_text(a)
            if na in others or na == norm_text(dn) or na in {norm_text(x) for x in names}:
                continue
            names.append(a)
        while len(names) < 3:
            names.append(re.sub(r"^(a|an|the)\s+", "", dn) if len(names) == 1 else dn)
        out[m] = names
    return out


def forced_templates(task: str) -> list[str]:
    if task in PATH_TASKS:
        return read_json(bench_dir("T03") / "spec.json")["forced_templates"]
    return read_json(bench_dir(task) / "spec.json")["forced_templates"]


def r2_twins(tok: Any, spec: str) -> list[dict[str, Any]]:
    """R2 neutral twins W1-W5 WITHOUT a ban sentence: d x ' .' padding with d = (#tokens of the default's display
    name as it would be rendered in that slot) - (#tokens of the noun in the same slot), both tokenised ALONE."""
    nn = read_json(bench_dir("R2") / "neutral_nouns.json")
    x = DEFAULT4["R2"]
    xname = nn[x]["display_name"]
    noun = nn[x]["nouns"][0]["word"]
    rows = []
    for w in TEMPLATE_IDS:
        lead = TEMPLATES[w][1].startswith("{N}")
        xr = cap_first(xname) if lead else " " + xname
        nr = cap_first(noun) if lead else " " + noun
        d = len(tok(xr, add_special_tokens=False)["input_ids"]) - len(tok(nr, add_special_tokens=False)["input_ids"])
        d = max(0, d)
        seg = TEMPLATES[w][1].format(N=noun) + PAD_FILLER * d
        rows.append(render(tok, "R2", "twin", seg, spec, template_id=w, X=None, noun=noun, n_pad=d,
                           source="built here: bench R2 neutral_nouns.json noun A, display-name-only padding"))
    return rows


def assert_no_r2_ban(rows: list[dict[str, Any]]) -> dict[str, Any]:
    names = set()
    spec = read_json(bench_dir("R2") / "spec.json")
    for c in spec["catalogue"]:
        names.add(c["display_name"])
        names.add(re.sub(r"^(a|an|the)\s+", "", c["display_name"]))
    for aa in spec.get("aliases", {}).values():
        names.update(aa)
    bad = []
    n = 0
    for r in rows:
        if r["task"] != "R2":
            continue
        n += 1
        t = norm_text(r["user_text"])
        for w in TEMPLATE_IDS:
            for nm in names:
                ban = norm_text(cap_first(TEMPLATES[w][0].format(X=nm)))
                if ban in t:
                    bad.append({"pid": r["pid"], "ban": ban})
    out = {"n_r2_prompts": n, "n_names_checked": len(names), "violations": bad, "pass": not bad}
    assert not bad, f"R2 ban string constructed: {bad[:3]}"
    return out


def build_all(tok: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    report: dict[str, Any] = {"named_variants": {}, "exp7_plain_match": {}, "knobs": {}}
    descs = read_json(PROMPTS_DIR / "descriptions.json")["by_task"]
    e17 = read_jsonl(E17 / "prompts" / "prompts.jsonl")
    for r in e17:
        meta = {"template_id": r["w"], "X": DEFAULT4[r["task"]] if r["kind"] == "ban" else None,
                "noun": r.get("noun"), "n_pad": r.get("n_pad"), "source": "exp17 prompts.jsonl"}
        pid = f"{r['task']}|{r['kind']}|{meta['X'] or '-'}|{r['w']}|-"
        rows.append({"pid": pid, "task": r["task"], "kind": r["kind"], "segment": r["segment"],
                     "user_text": r["user_text"], "ids": r["ids"], "P": r["P"], "p0": r["p0"], "p1": r["p1"],
                     "spec_end": r["spec_end"], "prompt_sha256": r["prompt_sha256"], **meta})
    for t in TASKS15:
        spec = task_spec_text(t)
        if t == "R2":
            rows += r2_twins(tok, spec)
        rows.append(render(tok, t, "plain", None, spec, template_id=None, X=None, source="spec only"))
        nv = named_variants(t)
        report["named_variants"][t] = nv
        ft = forced_templates(t)
        for m, names in nv.items():
            for vi, nm in enumerate(names):
                for ti, tpl in enumerate(ft):
                    rows.append(render(tok, t, "named", tpl.format(j=nm), spec, X=m, template_id=f"F{ti}",
                                       name_variant=vi, source="forced_templates x names"))
            dd = descs[t][m]["descriptions"]
            for di, d in enumerate(dd[:3]):
                for fi, fr in enumerate(DESC_FRAMES):
                    rows.append(render(tok, t, "masked", fr.format(d=d), spec, X=m, template_id=f"D{fi}",
                                       name_variant=di, source=descs[t][m]["source"][di]))
        if t in PATH_TASKS:
            conds = read_json(E7 / "prompts" / "prompts_v2.json")["conditions"]
            et = {"T1": "t1", "T2": "t2"}[t]
            ok = 0
            for m in nv:
                for k in range(10):
                    seg = conds.get(f"{et}|forced|{m}|plain|k{k}", {}).get("segment")
                    mine = cap_first(ft[k].format(j=nv[m][0]))
                    ok += int(seg == mine)
            report["exp7_plain_match"][t] = {"n_equal": ok, "n": 10 * len(nv)}
            for key, c in conds.items():
                if not key.startswith(et + "|"):
                    continue
                parts = key.split("|")
                if parts[1] == "novelty" or parts[1] == "mention":
                    w = parts[3] if parts[1] == "mention" else "NOV"
                    if parts[1] == "mention" and parts[2] != DEFAULT4[t]:
                        continue
                    rows.append(render(tok, t, f"knob_{parts[1]}", c["segment"], spec, template_id=w,
                                       X=parts[2] if parts[1] == "mention" else None, source=f"exp7 {key}"))
    # exp13 knob prompts (12 bench tasks): nonce W1-W5, novelty
    for r in read_jsonl(E13 / "prompts" / "prompts.jsonl"):
        if r["arm"] not in ("nonce", "novelty"):
            continue
        spec = task_spec_text(r["task"])
        assert r["text"] == cap_first(r["segment"]) + "\n\n" + spec, f"exp13 prompt text mismatch {r['task']}"
        rows.append(render(tok, r["task"], f"knob_{r['arm']}", r["segment"], spec, template_id=r["template"], X=None,
                           source="exp13 prompts.jsonl", exp13_ids_sha256=r.get("ids_sha256")))
    # alignment assertion: identical spec tokens per task
    ref: dict[str, list[int]] = {}
    for r in rows:
        s = r["ids"][r["p1"]:r["spec_end"]]
        if r["task"] not in ref:
            ref[r["task"]] = s
        assert s == ref[r["task"]], f"spec tokens differ for {r['pid']}"
    pids = [r["pid"] for r in rows]
    assert len(pids) == len(set(pids)), "duplicate prompt ids"
    report["r2_ban_check"] = assert_no_r2_ban(rows)
    # masked prompts must not leak any name of the task (checked on the condition segment)
    leak_rows = []
    for r in rows:
        if r["kind"] == "masked":
            h = leaks(r["segment"], leak_terms(r["task"]))
            if h:
                leak_rows.append({"pid": r["pid"], "hits": h})
    report["masked_leaks"] = leak_rows
    report["counts"] = {}
    for r in rows:
        report["counts"].setdefault(r["task"], {}).setdefault(r["kind"], 0)
        report["counts"][r["task"]][r["kind"]] += 1
    report["S_len"] = {t: len(v) for t, v in ref.items()}
    return rows, report


def stage_prompts() -> dict[str, Any]:
    from transformers import AutoTokenizer

    from cfg4 import MODEL_ID, MODEL_REVISION
    from cfg import model_path

    path = model_path()
    tok = AutoTokenizer.from_pretrained(path, **({"revision": MODEL_REVISION} if path == MODEL_ID else {}))
    rows, rep = build_all(tok)
    write_jsonl(PROMPTS4, rows)
    write_json(PROMPTS_DIR / "prompts4_report.json", rep)
    logger.info(f"prompts4: {len(rows)} prompts; masked leaks {len(rep['masked_leaks'])}; "
                f"R2 ban check {rep['r2_ban_check']['pass']}; exp7 match {rep['exp7_plain_match']}")
    return rep


def load_prompts4() -> dict[str, dict[str, Any]]:
    return {r["pid"]: r for r in read_jsonl(PROMPTS4)}


if __name__ == "__main__":
    from cfg4 import setup_logging

    setup_logging("prompts4")
    stage_prompts()
