#!/usr/bin/env python3
"""S0.4: build units.json (CPU; tokenizers only).

Qwen B2 units (CMAP): B3 (MST; 20 = exp41 C1nat set-A clean prompts + the k=4 set-B clean prompt per template; 61-token
opening; D = Kruskal-class tokens, A = Prim-class tokens of locate_B3 o0) and T10 (CC; 20 = exp41 C2a clean prompts
W1-W5 x ship/man/guy + 'baby'; prefix up to ' def'; D = {' find'}, A = {' dfs', ' bfs'}).
Qwen engine-check units: the iteration-8 base_subarm twins (prompts8) at the base_subarm decision specs (B3, T10).
Gemma B1 units: G-GRID (exp31 grid fork, index 32), G-T04 (token 31), G-R6 (tokens 12 and 24).
Llama B1 unit: L-GRID (locate_L-T1 openings o1 d=52 and o2 d=121).
D / A at the B1 forks: the two non-UNDECIDED classes with the largest instruct mass at the fork (locate mass_T1).
Template-free ids: [BOS if the family has one] + user text + blank line (+ the same opening), as base_arm 'plain'.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from typing import Any

from loguru import logger

from cfg9 import (TEMPLATES, V31, V35, V41, V43, ids_sha, model_path, read_json, read_jsonl, setup_logging,
                  write_json, ROOT)

UNITS_JSON = ROOT / "results" / "units.json"
GEMMA_HEAD = "<bos><start_of_turn>user\n"
GEMMA_TAIL = "<end_of_turn>\n<start_of_turn>model\n"
NOUN_SKIP = {"house"}


def _k3():
    p = str(V41 / "src")
    if p not in sys.path:
        sys.path.insert(0, p)
    import k3prompts as KP  # noqa: E402
    return KP


def _classes_from_locate(o: dict[str, Any], key_tokens: str = "tokens", key_mass: str = "mass_T1",
                         class_of: dict[str, str] | None = None) -> dict[str, Any]:
    toks = [int(t) for t in o[key_tokens]]
    mass = [float(m) for m in o[key_mass]]
    co = class_of if class_of is not None else {str(k): v for k, v in o["classes"]["class_of"].items()}
    agg: Counter = Counter()
    for t, m in zip(toks, mass):
        c = co.get(str(t), "UNDECIDED")
        if c not in ("UNDECIDED", "other", "invalid"):
            agg[c] += m
    (dcls, _), (acls, _) = agg.most_common(2)
    D = [t for t in toks if co.get(str(t)) == dcls]
    A = [t for t in toks if co.get(str(t)) == acls]
    return {"D": D, "A": A, "D_class": dcls, "A_class": acls, "class_of": {str(t): co.get(str(t), "UNDECIDED")
                                                                          for t in toks},
            "instr_mass_ref": {str(t): m for t, m in zip(toks, mass)}, "class_mass_ref": dict(agg)}


def _phat_class(phat: dict[str, list[float]], bins: list[str], thr: float = 0.7) -> dict[str, str]:
    out = {}
    for t, v in phat.items():
        j = max(range(len(v)), key=lambda i: v[i])
        out[str(t)] = bins[j] if v[j] >= thr else "UNDECIDED"
    return out


def _plain(tok: Any, text: str, bos: bool) -> list[int]:
    ids = tok(text + "\n\n", add_special_tokens=False)["input_ids"]
    return ([tok.bos_token_id] if bos and tok.bos_token_id is not None else []) + list(ids)


def _user_text_qwen(tok: Any, ids: list[int]) -> str:
    import re
    s = tok.decode(ids)
    m = re.search(r"<\|im_start\|>user\n([\s\S]*?)<\|im_end\|>", s)
    return m.group(1) if m else s


def qwen_units(tok: Any) -> dict[str, Any]:
    KP = _k3()
    ctr = read_json(V41 / "results" / "contrasts.json")
    nouns = read_json(V41 / "results" / "nouns.json")["nouns"]
    out = {}
    # ---------------- B3 (MST)
    vs = {v["vid"]: v for v in KP.b3_variants(tok, nouns, 24)}
    clean_A = [p["clean"] for p in ctr["C1nat_A"]["pairs"]]
    clean_B = [p["clean"] for p in ctr["C1nat_B"]["pairs"]]
    pick = []
    for w in TEMPLATES:
        pick += [v for v in clean_A if v.startswith(w + "|")][:3]
        pick += [v for v in clean_B if v.startswith(w + "|")][:1]
    O = KP.b3_opening()
    loc = read_json(V43 / "results" / "locate_B3.json")
    o0 = loc["openings"][0]
    assert [int(x) for x in o0["O"]] == list(O), "locate_B3 o0 opening differs from the exp41 opening"
    cl = _classes_from_locate(o0)
    m_clean = {p["clean"]: p["m_clean"] for p in ctr["C1nat_A"]["pairs"] + ctr["C1nat_B"]["pairs"]}
    prompts = []
    for vid in pick:
        r = vs[vid]
        prompts.append({"pid": vid, "template": r["template"], "noun": r.get("noun"), "ids": r["ids"],
                        "ids_plain": _plain(tok, _user_text_qwen(tok, r["ids"]), False), "pos": r["pos"],
                        "sha": ids_sha(r["ids"]), "exp41_m_clean": m_clean.get(vid)})
    out["B3"] = {"unit": "B3", "family": "qwen", "kind": "b2", "name": "minimum spanning tree weight",
                 "forks": [dict(fork_id="B3", opening=list(O), tok_a=" Kr", tok_b=" Prim",
                                bins=loc["bins"], phat={str(k): v for k, v in o0["phat"].items()}, **cl)],
                 "prompts": prompts}
    # ---------------- T10 (CC)
    t_nouns = ["ship"] + nouns[:2] + [nouns[2]]
    tv = KP.t10_variants(tok, t_nouns)
    pre = KP.t10_prefix()
    m_c2a = {p["clean"]: p["m_clean"] for p in ctr["C2a_tries"][0]["pairs"]}
    prompts = []
    for r in tv:
        prompts.append({"pid": r["vid"], "template": r["template"], "noun": r.get("noun", "ship"), "ids": r["ids"],
                        "ids_plain": _plain(tok, _user_text_qwen(tok, r["ids"]), False), "pos": r["pos"],
                        "sha": ids_sha(r["ids"]), "exp41_m_clean": m_c2a.get(r["vid"])})
    t1 = lambda s: tok(s, add_special_tokens=False)["input_ids"]  # noqa: E731
    D, A = t1(" find"), t1(" dfs") + t1(" bfs")
    out["T10"] = {"unit": "T10", "family": "qwen", "kind": "b2", "name": "connected components",
                  "forks": [{"fork_id": "T10", "opening": list(pre), "D": D, "A": A, "D_class": "union_find",
                             "A_class": "dfs|bfs", "tok_a": " find", "tok_b": " dfs",
                             "class_of": {str(D[0]): "union_find", str(A[0]): "dfs", str(A[1]): "bfs"}}],
                  "prompts": prompts}
    # ---------------- engine-check units (iteration-8 base_subarm decision specs)
    P8 = {(r["unit"], r["w"]): r for r in read_jsonl(V43 / "prompts" / "prompts8.jsonl")}
    cr = read_json(V35 / "predictions" / "collapsed_raw.json")["T10"]
    sam = read_jsonl(V35 / "data" / "samples_raw.jsonl")
    f = int(cr["fork_node_index"])
    progs = [s["token_ids"] for s in sam if s["unit"] == "T10" and s.get("arm") == "TWIN6"]
    prefix = list(Counter(tuple(p[:f]) for p in progs).most_common(1)[0][0])
    Dt = [int(k) for k in cr["tokens"] if cr["phat_off"][str(k)] < 0.5]
    out["CHK_T10"] = {"unit": "CHK_T10", "family": "qwen", "kind": "check",
                      "forks": [{"fork_id": "CHK_T10", "opening": prefix, "D": Dt,
                                 "A": [int(x) for x in cr["alt_class_tokens"]]}],
                      "prompts": [{"pid": f"T10|{w}|twin", "template": w, "ids": P8[("T10", w)]["ids"],
                                   "ids_plain": _plain(tok, _user_text_qwen(tok, P8[("T10", w)]["ids"]), False),
                                   "sha": ids_sha(P8[("T10", w)]["ids"])} for w in TEMPLATES]}
    out["CHK_B3"] = {"unit": "CHK_B3", "family": "qwen", "kind": "check",
                     "forks": [{"fork_id": "CHK_B3", "opening": list(O), "D": cl["D"], "A": cl["A"]}],
                     "prompts": [{"pid": f"B3|{w}|twin", "template": w, "ids": P8[("B3", w)]["ids"],
                                  "ids_plain": _plain(tok, _user_text_qwen(tok, P8[("B3", w)]["ids"]), False),
                                  "sha": ids_sha(P8[("B3", w)]["ids"])} for w in TEMPLATES]}
    return out


def _programs_exp43(unit: str) -> list[dict[str, Any]]:
    rows = [s for s in read_jsonl(V43 / "data" / "samples_raw.jsonl") if s["unit"] == unit and s["arm"] == "fit"
            and int(s["slot"]) < 4]
    rows = sorted(rows, key=lambda s: (s["template"], int(s["slot"])))
    return [{"template": s["template"], "slot": int(s["slot"]), "ids": [int(x) for x in s["token_ids"]],
             "source": f"art_lzuosbrb34wB samples_raw {s['sid']}"} for s in rows]


def gemma_units(tok: Any) -> dict[str, Any]:
    out = {}
    P8 = {(r["unit"], r["w"]): r for r in read_jsonl(V43 / "prompts" / "prompts8.jsonl")}
    # ---------------- G-GRID
    fk = read_json(V31 / "results" / "fork.json")
    pf = read_jsonl(V31 / "data" / "prompts_fed.jsonl")
    cstar = [int(x) for x in fk["cstar_ids"]]
    prompts = []
    for w in TEMPLATES:
        tw = [p for p in pf if p["task"] == "T1" and p["kind"] == "twin" and p["cond"].endswith(":" + w)][0]
        cands = [tw] + [p for p in pf if p["task"] == "T1" and p["kind"] == "variant" and
                        p["cond"].startswith(f"variant:{w}:") and p["cond"].split(":")[-1] not in NOUN_SKIP][:6]
        for rank, p in enumerate(cands):
            text = p["text"]
            ids = tok(GEMMA_HEAD + text + GEMMA_TAIL, add_special_tokens=False)["input_ids"]
            noun = "house" if p["kind"] == "twin" else p["cond"].split(":")[-1]
            prompts.append({"pid": f"{w}|{noun}", "template": w, "noun": noun, "ids": ids, "rank": rank,
                            "ids_plain": _plain(tok, text, True), "sha": ids_sha(ids), "text_sha": p["text_sha256"]})
    s3 = [r for r in read_jsonl(V31 / "data" / "raw_s3.jsonl") if r["task"] == "T1" and r["arm"] == "twin"]
    s3 = sorted(s3, key=lambda r: (r["template"], int(r["slot"])))
    progs = []
    for w in TEMPLATES:
        progs += [{"template": r["template"], "slot": int(r["slot"]), "ids": [int(x) for x in r["token_ids"]],
                   "source": f"art_zNyBP6zieI5u raw_s3 {r['row_id']}"} for r in s3 if r["template"] == w][:4]
    D = [int(x) for x in fk["D_set"]]
    A = [int(x) for x in fk["B_set"]]
    tt = fk["token_table"]
    out["G-GRID"] = {"unit": "G-GRID", "family": "gemma", "kind": "b1", "name": "grid path (BFS vs DFS)",
                     "forks": [{"fork_id": "G-GRID@32", "opening": cstar, "D": D, "A": A, "D_class": "dfs",
                                "A_class": "bfs", "bins": ["bfs", "dfs"],
                                "phat": {str(k): [v["p_bfs"], 1 - v["p_bfs"]] for k, v in tt.items()},
                                "class_of": {**{str(t): "dfs" for t in D}, **{str(t): "bfs" for t in A}}}],
                     "prompts": prompts, "programs": progs, "max_prompts": 20}
    # ---------------- G-T04, G-R6
    for unit in ("G-T04", "G-R6"):
        loc = read_json(V43 / "results" / f"locate_{unit}.json")
        o0 = loc["openings"][0]
        forks = [dict(fork_id=f"{unit}@{o0['d']}", opening=[int(x) for x in o0["O"]], bins=loc["bins"],
                      phat={str(k): v for k, v in o0["phat"].items()}, **_classes_from_locate(o0))]
        if unit == "G-R6":
            for t1, sec in o0["second"].items():
                if not sec.get("found"):
                    continue
                co2 = _phat_class(sec["phat2"], loc["bins"])
                c2 = _classes_from_locate(sec, "tokens2", "mass2_T1", co2)
                forks.append(dict(fork_id=f"{unit}@{sec['d2']}", opening=[int(x) for x in o0["O"]] + [int(t1)] +
                                  [int(x) for x in sec["O2"]], bins=loc["bins"],
                                  phat={str(k): v for k, v in sec["phat2"].items()}, **c2))
        prompts = []
        for w in TEMPLATES:
            r = P8[(unit, w)]
            prompts.append({"pid": f"{w}|twin", "template": w, "noun": None, "ids": r["ids"], "rank": 0,
                            "ids_plain": _plain(tok, r["text"], True), "sha": r["prompt_sha256"]})
        out[unit] = {"unit": unit, "family": "gemma", "kind": "b1", "name": {"G-T04": "substring search",
                                                                             "G-R6": "first and last position"}[unit],
                     "forks": forks, "prompts": prompts, "programs": _programs_exp43(unit), "max_prompts": 5}
    return out


def llama_units(tok: Any) -> dict[str, Any]:
    P8 = {(r["unit"], r["w"]): r for r in read_jsonl(V43 / "prompts" / "prompts8.jsonl")}
    loc = read_json(V43 / "results" / "locate_L-T1.json")
    forks = []
    for o in loc["openings"]:
        if not o.get("decision"):
            continue
        forks.append(dict(fork_id=f"L-GRID@{o['d']}", opening=[int(x) for x in o["O"]], bins=loc["bins"],
                          phat={str(k): v for k, v in o["phat"].items()}, **_classes_from_locate(o)))
    prompts = []
    for w in TEMPLATES:
        r = P8[("L-T1", w)]
        prompts.append({"pid": f"{w}|twin", "template": w, "noun": None, "ids": r["ids"], "rank": 0,
                        "ids_plain": _plain(tok, r["text"], True), "sha": r["prompt_sha256"]})
    return {"L-GRID": {"unit": "L-GRID", "family": "llama", "kind": "b1", "name": "grid path (Llama)",
                       "forks": forks, "prompts": prompts, "programs": _programs_exp43("L-T1"), "max_prompts": 5}}


def build() -> dict[str, Any]:
    from transformers import AutoTokenizer
    units: dict[str, Any] = {}
    tq = AutoTokenizer.from_pretrained(model_path("qwen"))
    units.update(qwen_units(tq))
    tg = AutoTokenizer.from_pretrained(model_path("gemma"))
    units.update(gemma_units(tg))
    tl = AutoTokenizer.from_pretrained(model_path("llama"))
    units.update(llama_units(tl))
    toks = {"qwen": tq, "gemma": tg, "llama": tl}
    # decode checks of the class tokens (recorded; asserted in the CPU tests)
    for u, U in units.items():
        tk = toks[U["family"]]
        for f in U["forks"]:
            f["D_str"] = [tk.decode([t]) for t in f["D"]]
            f["A_str"] = [tk.decode([t]) for t in f["A"]]
            f["opening_text"] = tk.decode(f["opening"])
    write_json(UNITS_JSON, units)
    logger.info({u: (len(U["prompts"]), [(f["fork_id"], f["D_str"][:4], f["A_str"][:4]) for f in U["forks"]])
                 for u, U in units.items()})
    return units


def load_units() -> dict[str, Any]:
    return read_json(UNITS_JSON)


if __name__ == "__main__":
    setup_logging("units9")
    build()
