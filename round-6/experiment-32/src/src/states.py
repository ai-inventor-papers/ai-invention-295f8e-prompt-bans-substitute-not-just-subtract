#!/usr/bin/env python3
"""S4: teacher-forced bf16 state cache on the target. Stores the outputs of blocks 19 and 20 (= hidden_states[20]
and [21]) in fp32 at:
  PREFILL  READ and SPEC-1..3 of every twin, ban, forced (all catalogue modes) and seed prompt;
  GEN      generated tokens g1/g2/g4/g8/16 of S3 samples (twin, ban, forced-Y*: slots 0-1 per template = 10 per
           condition; slots 0-3 = 20 for MIXED and NO-DEFAULT conditions);
  RAND     h_twin + eps at READ and SPEC-1 of every twin template of a defaulted task, eps isotropic and seeded with
           ||eps|| = ||h_ban - h_twin|| at that position and layer convention;
  REF      the broad reference set: 5 random token positions >= 50 (non-special) in each of 20 Ultra-FineWeb documents
           and 20 chat prompts (10 LeetCode texts + 10 general questions); extra classes (CLRS traces, HumanEval+
           prompts, enamel code) reported apart.
Also checks that identical prefixes give bit-identical states (twin W1 twice).
Outputs cache/states_L20.npz (H20, H21 [N, 3584] fp32) and cache/states_index.jsonl.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (CACHE_DIR, DATA_DIR, D_MODEL, GEN_POSITIONS, POS_OFFSET, PRED_DIR, RESULTS_DIR, TASKS,
                 TEMPLATE_IDS, read_json, read_jsonl, set_ram_limit, setup_logging, stable_seed, write_json,
                 write_jsonl)
from engine import capture_states, load_model, unload

BLOCKS = (19, 20)  # -> hidden_states[20], hidden_states[21]


def plan_conditions() -> dict[str, Any]:
    """Y*, MIXED and forced readout conditions from the behaviour report (same rules as commit #2)."""
    from behaviour import per_task_report

    rep = per_task_report()
    write_json(RESULTS_DIR / "behaviour_pre_states.json", rep)
    return rep


def ref_states(tok: Any, model: Any, rows: list[dict[str, Any]], H: dict[int, list[np.ndarray]]) -> None:
    src = read_json(DATA_DIR / "reference_sources.json")
    special = set(tok.all_special_ids)
    items = []
    for cls in ("fineweb", "leetcode", "general", "clrs_trace", "humanevalplus", "enamel"):
        for s in src[cls]:
            if cls in ("fineweb", "clrs_trace", "enamel"):
                ids = tok(s["text"], add_special_tokens=True)["input_ids"][:1024]
            else:
                ids = tok.apply_chat_template([{"role": "user", "content": s["text"]}], tokenize=True,
                                              add_generation_prompt=True)
                ids = list(ids["input_ids"] if isinstance(ids, dict) else ids)[:1024]
            n_pos = 5 if cls in ("fineweb", "leetcode", "general") else 1
            cand = [i for i, t in enumerate(ids) if i >= 50 and t not in special]
            if not cand:
                cand = [i for i, t in enumerate(ids) if i >= 10 and t not in special]
            rng = np.random.default_rng(stable_seed("ref", cls, s["qid"] if "qid" in s else s["idx"]) % (2 ** 32))
            pos = sorted(rng.choice(cand, size=min(n_pos, len(cand)), replace=False).tolist())
            items.append((cls, s.get("qid", s.get("idx")), ids, pos))
    for cls, qid, ids, pos in items:
        st = capture_states(model, ids, list(BLOCKS), pos)
        for j, p in enumerate(pos):
            for b in BLOCKS:
                H[b].append(st[b][j])
            rows.append({"state_id": f"REF|{cls}|{qid}|{p}", "kind": "REF", "ref_class": cls,
                         "gate_set": cls in ("fineweb", "leetcode", "general"), "task": None, "condition": cls,
                         "template": None, "position": f"tok{p}", "pos_class": "REF", "abs_pos": p,
                         "context": tok.decode(ids[max(0, p - 12):p + 1])})


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("states")
    set_ram_limit(60)
    rep = plan_conditions()
    c1 = read_json(PRED_DIR / "commit1_defaults.json")
    st = {(r["task"], r["kind"], r["w"], r.get("mode") or "-"): r for r in read_jsonl(DATA_DIR / "prompts_static.jsonl")}
    bans = {(r["task"], r["w"]): r for r in read_jsonl(DATA_DIR / "prompts_ban.jsonl")}
    raw = {r["sample_id"]: r for r in read_jsonl(DATA_DIR / "samples_raw.jsonl")}
    tok, model = load_model()
    rows: list[dict[str, Any]] = []
    H: dict[int, list[np.ndarray]] = {b: [] for b in BLOCKS}
    t0 = time.time()

    def add_prefill(p: dict[str, Any], condition: str, mode: str | None) -> None:
        pos_names = list(POS_OFFSET)
        idx = [p["P"] - POS_OFFSET[k] for k in pos_names]
        s = capture_states(model, p["ids"], list(BLOCKS), idx)
        for j, k in enumerate(pos_names):
            for b in BLOCKS:
                H[b].append(s[b][j])
            rows.append({"state_id": f"{p['task']}|{condition}|{mode or '-'}|{p['w']}|{k}", "kind": "PREFILL",
                         "task": p["task"], "condition": condition, "mode": mode, "template": p["w"], "position": k,
                         "pos_class": "READ" if k == "READ" else "SPEC", "abs_pos": idx[j],
                         "prompt_sha256": p["prompt_sha256"]})

    # bit-identity check for identical prefixes
    p0 = st[("T03", "twin", "W1", "-")]
    a = capture_states(model, p0["ids"], [20], [p0["P"] - 1])[20]
    b = capture_states(model, p0["ids"], [20], [p0["P"] - 1])[20]
    bit_identical = bool(np.array_equal(a, b))
    for t in TASKS:
        D = c1["tasks"][t]["default"]
        for w in TEMPLATE_IDS:
            add_prefill(st[(t, "twin", w, "-")], "twin", None)
            if D:
                add_prefill(bans[(t, w)], "ban", D)
        for (tt, kind, w, m), p in st.items():
            if tt == t and kind == "forced":
                add_prefill(p, "forced", m)
            if tt == t and kind == "seed":
                add_prefill(p, "seed", None)
    logger.info(f"prefill states: {len(rows)} in {time.time() - t0:.0f}s")
    # generated-token states
    for t in TASKS:
        R = rep["tasks"][t]
        D = c1["tasks"][t]["default"]
        conds = [("twin", "TWIN", None, R["twin"])]
        if D:
            conds.append(("ban", "BAN", D, R.get("ban")))
        ys = R.get("Ystar")
        if ys:
            conds.append(("forced", "FORCED", ys, None))
        for cond, arm, mode, comp in conds:
            mixed = (D is None and cond == "twin") or bool(comp and comp["correct"] and
                                                          (1 - max(comp["correct"].values()) / max(1, comp["n_correct"])) >= 0.2)
            slots = range(4) if mixed else range(2)
            for w in TEMPLATE_IDS:
                for k in slots:
                    if arm == "FORCED":
                        sid = f"{t}|FORCED|{mode}|{w}|{k}"
                    else:
                        sid = f"{t}|{arm}|{mode or '-'}|{w}|{k}"
                    r = raw.get(sid)
                    if r is None or len(r["token_ids"]) < max(GEN_POSITIONS):
                        continue
                    p = (bans[(t, w)] if arm == "BAN" else st[(t, "forced", w, mode)] if arm == "FORCED"
                         else st[(t, "twin", w, "-")])
                    ids = p["ids"] + r["token_ids"][:max(GEN_POSITIONS)]
                    idx = [p["P"] - 1 + g for g in GEN_POSITIONS]
                    s = capture_states(model, ids, list(BLOCKS), idx)
                    for j, g in enumerate(GEN_POSITIONS):
                        for b in BLOCKS:
                            H[b].append(s[b][j])
                        rows.append({"state_id": f"{t}|{cond}|{mode or '-'}|{w}|g{g}|{k}", "kind": "GEN", "task": t,
                                     "condition": cond, "mode": mode, "template": w, "position": f"g{g}",
                                     "pos_class": f"g{g}", "abs_pos": idx[j], "sample_id": sid, "slot": k,
                                     "mixed": mixed, "prefix_text": tok.decode(r["token_ids"][:g])})
    logger.info(f"+ generated states: {len(rows)} in {time.time() - t0:.0f}s")
    # random-perturbation states (eps norm = ban displacement at that position and convention)
    idx_of = {r["state_id"]: i for i, r in enumerate(rows)}
    for t in TASKS:
        D = c1["tasks"][t]["default"]
        if not D:
            continue
        for w in TEMPLATE_IDS:
            for k in ("READ", "SPEC-1"):
                it = idx_of[f"{t}|twin|-|{w}|{k}"]
                ib = idx_of[f"{t}|ban|{D}|{w}|{k}"]
                for b in BLOCKS:
                    ht, hb = H[b][it], H[b][ib]
                    rng = np.random.default_rng(stable_seed("eps", t, w, k, b) % (2 ** 32))
                    u = rng.standard_normal(D_MODEL).astype(np.float32)
                    u /= np.linalg.norm(u)
                    H[b].append(ht + u * np.linalg.norm(hb - ht))
                rows.append({"state_id": f"{t}|rand|-|{w}|{k}", "kind": "RAND", "task": t, "condition": "rand",
                             "mode": None, "template": w, "position": k, "pos_class": "READ" if k == "READ" else "SPEC",
                             "eps_norm_h20": float(np.linalg.norm(H[19][ib] - H[19][it])),
                             "eps_norm_h21": float(np.linalg.norm(H[20][ib] - H[20][it]))})
    ref_states(tok, model, rows, H)
    # AV smoke state (README smoke test): the last token of 'The capital of France is'
    long_text = ("Every year millions of visitors travel across Europe to see its famous cities, museums and old "
                 "cathedrals. Many of them start their journey with a train ride to the north, where the river winds "
                 "past bridges and markets. As every schoolchild learns, the capital of France is")
    for name, text in (("france", "The capital of France is"), ("france_long", long_text)):
        sm = tok(text, add_special_tokens=True)["input_ids"]
        s = capture_states(model, sm, list(BLOCKS), [len(sm) - 1])
        for b in BLOCKS:
            H[b].append(s[b][0])
        rows.append({"state_id": f"SMOKE|{name}", "kind": "SMOKE", "task": None, "condition": "smoke",
                     "template": None, "position": "last", "pos_class": "SMOKE", "abs_pos": len(sm) - 1})
    logger.info(f"+ random, reference and smoke states: {len(rows)} in {time.time() - t0:.0f}s")
    H20 = np.stack(H[19]).astype(np.float32)
    H21 = np.stack(H[20]).astype(np.float32)
    for i, r in enumerate(rows):
        r["row"] = i
        r["norm_h20"] = float(np.linalg.norm(H20[i]))
        r["norm_h21"] = float(np.linalg.norm(H21[i]))
    np.savez(CACHE_DIR / "states_L20.npz", H20=H20, H21=H21)
    write_jsonl(CACHE_DIR / "states_index.jsonl", rows)
    write_json(RESULTS_DIR / "states_summary.json", {
        "n_states": len(rows), "bit_identical_prefix": bit_identical, "seconds": round(time.time() - t0, 1),
        "by_kind": {k: sum(r["kind"] == k for r in rows) for k in ("PREFILL", "GEN", "RAND", "REF")},
        "mean_norm_h20": float(np.mean([r["norm_h20"] for r in rows])),
        "mean_norm_h21": float(np.mean([r["norm_h21"] for r in rows]))})
    logger.info(f"saved {len(rows)} states; bit-identical prefixes: {bit_identical}")
    unload(model)


if __name__ == "__main__":
    main()
