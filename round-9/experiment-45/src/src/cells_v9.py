#!/usr/bin/env python3
"""Cell plan and prompts of the iteration-9 sampling (Stage 3).

Every prompt is rendered with the iteration-8 renderer (prompts_tp.ban_prompt): the committed k order decides WHICH
algorithms are in B_k (its first k entries); the renderer displays B_k's display names in CANON_ORDER rotated by
W_ROT[template] and joined 'A, B or C', so k = 5 is byte-identical to iteration 8's literal ban. N5 sets use the same
call. N3-D uses the same frames with the five name-free descriptions joined by '; ' in the same rotated order.
Seed = 1000 * cell_index + slot + 1 (fresh draws, not seed replays of iteration 8's rows).
"""

from __future__ import annotations

from typing import Any

from common import (CANON_ORDER, CONFIRM_SLOTS, K_ORDER, LITERAL5, PRED, SCREEN_SLOTS, W_ROT, W_TEMPLATES, cap_first,
                    read_json, rotate, sha256_text)
from prompts_tp import ban_prompt, baseline_prompt, make_prompt, split_slots

# cell id -> (cell_index, model key, kind, payload, N, slot plan)
#   kind 'ban_k'     payload = k               (B_k = first k of K_ORDER)
#   kind 'ban_set'   payload = 'R1'..'R6'      (rotated sets, committed in commit #1b)
#   kind 'described' payload = None            (N3-D descriptions, committed in commit #1b)
#   kind 'baseline'  payload = None            (scale models: baseline templates B0..B9)
#   kind 'ban_top5'  payload = None            (scale models: their own top five, fixed by commit #2)
CELLS: dict[str, dict[str, Any]] = {}


def _add(cid: str, idx: int, mkey: str, kind: str, payload: Any, n: int, plan: str, group: str) -> None:
    CELLS[cid] = {"cell": cid, "cell_index": idx, "model_key": mkey, "kind": kind, "payload": payload, "n": n,
                  "slot_plan": plan, "group": group}


for _k in range(1, 6):
    _add(f"A_k{_k}", _k, "q32", "ban_k", _k, 50, "screen", "A")
_add("A_k5_ho", 6, "q32", "ban_k", 5, 50, "confirm", "A")
for _i, _r in enumerate(["R1", "R2", "R3", "R4"]):
    _add(f"B_{_r}", 7 + _i, "q32", "ban_set", _r, 50, "screen", "B")
_add("C_desc", 11, "q32", "described", None, 50, "screen", "C")
_add("D_R5", 12, "q32", "ban_set", "R5", 50, "screen", "D")
_add("D_R6", 13, "q32", "ban_set", "R6", 50, "screen", "D")
for _k in range(1, 6):
    _add(f"E_k{_k}", 13 + _k, "q14", "ban_k", _k, 50, "screen", "E")
_add("E_k5_ho", 19, "q14", "ban_k", 5, 50, "confirm", "E")
# Scale check: qwen/qwen3-235b-a22b-thinking-2507 is served only by Venice at USD 3.5/M output tokens (~USD 0.03 per
# thinking row, 5x the planned 0.006), so its cells (indices 20 and 22) are dropped before commit #1a (deviation
# D-scale); the scale check runs on gpt-oss-120b only, and only if the budget allows after E.
_add("F_gptoss_base", 21, "gptoss", "baseline", None, 50, "baseline", "F")
_add("F_gptoss_ban", 23, "gptoss", "ban_top5", None, 50, "screen", "F")

RUN_ORDER = ["A", "B", "C", "D", "E", "F"]          # the reverse of the drop order (F, E, D, C; never A)


def banned_for(cell: dict[str, Any]) -> list[str] | None:
    kind = cell["kind"]
    if kind == "ban_k":
        return sorted(K_ORDER[: cell["payload"]], key=CANON_ORDER.index)
    if kind == "ban_set":
        sets = read_json(PRED / "n5_sets.json")
        return sorted(sets["sets"][cell["payload"]]["set"], key=CANON_ORDER.index)
    if kind == "described":
        return list(LITERAL5)
    if kind == "ban_top5":
        top = read_json(PRED / "commit2.json")["scale_top5"][cell["cell"].replace("_ban", "_base")]
        return sorted(top, key=CANON_ORDER.index)
    return None


def described_segment(template: str, desc: dict[str, str]) -> str:
    order = [k for k in CANON_ORDER if k in LITERAL5]
    text = "; ".join(desc[k] for k in rotate(order, W_ROT[template]))
    return cap_first(W_TEMPLATES[template].replace("{X}", text))


def prompts_for(cid: str) -> list[dict[str, Any]]:
    cell = CELLS[cid]
    n = cell["n"]
    out: list[dict[str, Any]] = []
    if cell["kind"] == "baseline":
        for s in range(n):
            p = baseline_prompt(s)
            out.append({**p, "banned": []})
    else:
        plan = SCREEN_SLOTS if cell["slot_plan"] == "screen" else CONFIRM_SLOTS
        tpls = split_slots(n, plan)
        banned = banned_for(cell)
        if cell["kind"] == "described":
            desc = read_json(PRED / "n3d_descriptions.json")["descriptions"]
            for s, tpl in enumerate(tpls):
                seg = described_segment(tpl, desc)
                out.append({"arm": "described", "slot": s, "template": tpl, "segment": seg,
                            "prompt": make_prompt(seg), "banned": banned})
        else:
            for s, tpl in enumerate(tpls):
                p = ban_prompt(banned, tpl, s, "ban")
                out.append(p)
    rows = []
    for p in out:
        rows.append({**p, "cell": cid, "cell_index": cell["cell_index"], "model_key": cell["model_key"],
                     "kind": cell["kind"], "k": cell["payload"] if cell["kind"] == "ban_k" else
                     (len(p.get("banned") or []) if cell["kind"] != "baseline" else 0),
                     "group": cell["group"], "seed": 1000 * cell["cell_index"] + int(p["slot"]) + 1,
                     "prompt_sha256": sha256_text(p["prompt"]), "slot": int(p["slot"])})
    return rows


def templates_text() -> dict[str, str]:
    return dict(W_TEMPLATES)
