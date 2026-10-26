#!/usr/bin/env python3
"""EXPLORATORY local positive control for the instrument (not pre-registered).

The committed readout reads states at the end of the prompt (SPEC-3..READ), ~170 tokens after the sentence that names
an algorithm. Here the same NLA reads states AT the algorithm name: the last token of the display name inside the
condition sentence ('NAME') and the sentence's final period ('SENT'), for the forced prompts of the three read-out
modes and the ban prompts. If explanations name the algorithm here, the instrument can verbalise algorithm identity
when it is local, and the end-of-prompt null says the identity is not carried there in verbalisable form.

Steps (one model on the GPU at a time): target states -> AV (3 explanations per state) -> AR (cosine) -> judges
(J1/J2, J3 on disagreement; same rubric v2 and calibration). Writes results/local_control.json.
"""

from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, DATA_DIR, PRED_DIR, RESULTS_DIR, read_json, read_jsonl, set_ram_limit, setup_logging,
                 stable_seed, write_json, write_jsonl)
import prompts as PR

OUT_IDX = CACHE_DIR / "local_states_index.jsonl"
OUT_NPZ = CACHE_DIR / "local_states.npz"
OUT_EXPL = DATA_DIR / "local_explanations.jsonl"


def name_positions(tok: Any, p: dict[str, Any], name: str) -> dict[str, int]:
    text = tok.apply_chat_template([{"role": "user", "content": p["user_text"]}], tokenize=False,
                                   add_generation_prompt=True)
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    assert enc["input_ids"] == p["ids"], "chat string does not re-tokenise to the prompt ids"
    u0 = text.index(p["user_text"])
    seg = p["segment"]
    a = text.lower().index(name.lower(), u0)  # the segment may capitalise a sentence-initial name
    name_end = a + len(name) - 1
    sent_end = u0 + len(seg) - 1
    out = {}
    for key, ch in (("NAME", name_end), ("SENT", sent_end)):
        out[key] = next(i for i, (s, e) in enumerate(enc["offset_mapping"]) if s <= ch < e)
    return out


def stage_states(conv_block: int) -> None:
    from engine import capture_states, load_model, unload

    c2 = read_json(PRED_DIR / "commit2_readout.json")
    st = {(r["task"], r["kind"], r["w"], r.get("mode") or "-"): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl")}
    bans = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_ban.jsonl")}
    tok, model = load_model()
    rows, H = [], []
    for t, v in c2["tasks"].items():
        if not v.get("regate_pass"):
            continue
        items = [("forced", m, st[(t, "forced", w, m)]) for m in v["forced_readout_modes"] for w in
                 ("W1", "W2", "W3", "W4", "W5")]
        if v.get("default"):
            items += [("ban", v["default"], bans[(t, w)]) for w in ("W1", "W2", "W3", "W4", "W5")]
        for cond, m, p in items:
            name = PR.display_name(t, m)
            pos = name_positions(tok, p, name)
            s = capture_states(model, p["ids"], [conv_block], [pos["NAME"], pos["SENT"]])
            for j, k in enumerate(("NAME", "SENT")):
                H.append(s[conv_block][j])
                rows.append({"state_id": f"{t}|{cond}|{m}|{p['w']}|{k}", "task": t, "condition": cond, "mode": m,
                             "template": p["w"], "position": k, "abs_pos": pos[k], "row": len(H) - 1,
                             "token": tok.decode([p["ids"][pos[k]]])})
    np.savez(OUT_NPZ, H=np.stack(H).astype(np.float32))
    write_jsonl(OUT_IDX, rows)
    logger.info(f"local states: {len(rows)}")
    unload(model)


def stage_av() -> None:
    from nla_av import AV
    from engine import unload

    rows = read_jsonl(OUT_IDX)
    H = np.load(OUT_NPZ)["H"]
    av = AV()
    out = []
    items = [(r, j) for r in rows for j in (1, 2, 3)]
    for s in range(0, len(items), 128):
        part = items[s:s + 128]
        V = np.stack([H[r["row"]] for r, _ in part])
        res = av.explain(V, seed=stable_seed("local_av", s) % (2 ** 31))
        for (r, j), e in zip(part, res):
            out.append({"expl_id": f"{r['state_id']}#{j}", "state_id": r["state_id"], "idx": j, "task": r["task"],
                        "text": e["text"], "truncated": e["truncated"], "flag_cjk": e["flag_cjk"]})
    write_jsonl(OUT_EXPL, out)
    unload(av.model)


def stage_ar() -> dict[str, float]:
    from nla_ar import AR, cos_rows
    from engine import unload

    rows = {r["state_id"]: r for r in read_jsonl(OUT_IDX)}
    H = np.load(OUT_NPZ)["H"]
    ex = read_jsonl(OUT_EXPL)
    ar = AR()
    P = ar.reconstruct([e["text"] for e in ex])
    G = np.stack([H[rows[e["state_id"]]["row"]] for e in ex])
    cs = cos_rows(P, G)
    unload(ar.bb)
    return {"cos_mean": float(cs.mean()), "cos_by_position": {k: float(np.mean([c for c, e in zip(cs, ex)
                                                                                  if e["state_id"].endswith(k)]))
                                                              for k in ("NAME", "SENT")}}


def stage_judge() -> dict[str, Any]:
    import judges as J

    cal = read_json(RESULTS_DIR / "judge_calibration.json")
    J.JUDGES.update(cal["final"])
    ex = read_jsonl(OUT_EXPL)
    rn = J.Runner(conc=8)
    items = [{"mode": "EXPL", "task": e["task"], "text": e["text"]} for e in ex]
    async def run_all() -> tuple[dict[str, list[Any]], list[int], list[Any]]:
        res_ = {j: await rn.many(J.JUDGES[j], items) for j in ("J1", "J2")}
        dis_ = [i for i, (a, b) in enumerate(zip(res_["J1"], res_["J2"]))
                if not (a and b and a["planned"] == b["planned"])]
        r3_ = await rn.many(J.JUDGES["J3"], [items[i] for i in dis_]) if dis_ else []
        return res_, dis_, r3_

    res, dis, r3 = asyncio.run(run_all())  # one event loop: the Runner's semaphore is bound to it
    third = dict(zip(dis, r3))
    out = []
    for i, e in enumerate(ex):
        a, b, c = res["J1"][i], res["J2"][i], third.get(i)
        vals = [x["planned"] for x in (a, b, c) if x]
        if a and b and a["planned"] == b["planned"]:
            resolved = a["planned"]
        else:
            top = Counter(vals).most_common(1)
            resolved = top[0][0] if top and top[0][1] >= 2 else "unresolved"
        ment = sorted(set((a or {}).get("mentioned") or []) | set((b or {}).get("mentioned") or []))
        out.append(e | {"resolved": resolved, "mentioned_any": ment})
    write_jsonl(DATA_DIR / "local_judgements.jsonl", out)
    return {"spent_usd_total_judges": rn.spent}


def summarise(ar_stats: dict[str, Any], jstats: dict[str, Any]) -> dict[str, Any]:
    from collections import defaultdict

    rows = {r["state_id"]: r for r in read_jsonl(OUT_IDX)}
    ex = read_jsonl(DATA_DIR / "local_judgements.jsonl")
    by = defaultdict(list)
    for e in ex:
        by[e["state_id"]].append(e)
    agg: dict[str, Any] = {}
    for cond in ("forced", "ban"):
        for k in ("NAME", "SENT"):
            sts = [s for s, r in rows.items() if r["condition"] == cond and r["position"] == k]
            planned = [int(sum(e["resolved"] == rows[s]["mode"] for e in by[s]) >= 2) for s in sts]
            mention = [int(sum(rows[s]["mode"] in e["mentioned_any"] for e in by[s]) >= 2) for s in sts]
            negated_or_planned = [int(sum((e["resolved"] == rows[s]["mode"]) or (rows[s]["mode"] in e["mentioned_any"])
                                          for e in by[s]) >= 2) for s in sts]
            agg[f"{cond}|{k}"] = {"n_states": len(sts), "planned_majority": float(np.mean(planned)) if sts else None,
                                  "mentioned_majority": float(np.mean(mention)) if sts else None,
                                  "planned_or_mentioned": float(np.mean(negated_or_planned)) if sts else None,
                                  "per_task_mentioned": {t: float(np.mean([m for s, m in zip(sts, mention)
                                                                           if rows[s]["task"] == t]))
                                                         for t in sorted({rows[s]["task"] for s in sts})}}
    out = {"note": "exploratory local positive control (not pre-registered)", "aggregates": agg, "ar": ar_stats,
           "judges": jstats, "examples": [{"state_id": e["state_id"], "token": rows[e["state_id"]]["token"],
                                           "text": e["text"][:700], "resolved": e["resolved"],
                                           "mentioned": e["mentioned_any"]} for e in ex[:12]]}
    write_json(RESULTS_DIR / "local_control.json", out)
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("local_control")
    set_ram_limit(60)
    conv = read_json(RESULTS_DIR / "layer_convention.json")
    block = int(conv["patch_block"])
    if not OUT_IDX.exists():
        stage_states(block)
    if not OUT_EXPL.exists():
        stage_av()
    ar_stats = stage_ar()
    jstats = stage_judge()
    out = summarise(ar_stats, jstats)
    logger.info(f"local control: { {k: (v['planned_majority'], v['mentioned_majority']) for k, v in out['aggregates'].items()} }; "
                f"AR cos {ar_stats}")


if __name__ == "__main__":
    main()
