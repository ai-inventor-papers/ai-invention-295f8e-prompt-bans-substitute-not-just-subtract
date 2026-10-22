"""Association map, ladder / association / proximity nominations, disagreement, Stage-A / Stage-B task orders.

Disagreement per event = (minimum number of distinct modes that hit every family's tie set) - 1, i.e. two families
agree iff their tie sets intersect, generalised to three families as a minimum hitting set.
"""

from __future__ import annotations

import itertools
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger

from .canon import canon_tokens, token_distance
from .catalogue import TASK_ORDER, TASKS, display_name
from .refs import REFS


def _phrases(task: str, mode: str) -> set[str]:
    ph = {a.lower() for a in TASKS[task]["aliases"][mode]}
    d = re.sub(r"^(a|an|the)\s+", "", display_name(task, mode).lower())
    ph.add(re.sub(r"\s*\(.*?\)", "", d).strip())
    return {p for p in ph if len(p) >= 2}


def mentions(task: str, text: str) -> dict[str, int]:
    low = text.lower()
    pos = {}
    for m in TASKS[task]["modes"]:
        for p in _phrases(task, m):
            for mm in re.finditer(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", low):
                pos[m] = min(pos.get(m, 10**9), mm.start())
    return pos


def map_association(root: Path) -> list[dict]:
    """Map each association answer to a catalogue id; unmapped answers go to the judge (j1)."""
    from .judge import Judge
    rows = [json.loads(l) for l in (root / "data" / "association_raw.jsonl").open()]
    out, need = [], []
    for r in rows:
        x = r["mode"]
        pos = mentions(r["task"], r["text"])
        surv = {m: p for m, p in pos.items() if m != x}
        if surv:
            lab, src = min(surv, key=surv.get), "lexicon"
        else:
            lab, src = None, "judge"
            need.append(r)
        out.append({"task": r["task"], "X": x, "sample_id": r["sample_id"], "seed": r["seed"], "answer": r["text"],
                    "mapped": lab, "map_source": src})
    if need:
        j = Judge(root)
        items = []
        for r in need:
            c = TASKS[r["task"]]
            cat = "\n".join(f"- {m}: {d[1]}" for m, d in c["modes"].items())
            items.append((r, f"Task:\n{c['description']}\n\nSomeone was asked for the standard alternative to "
                             f"'{display_name(r['task'], r['mode'])}' (label {r['mode']}) for this task and answered:\n"
                             f"\"{r['text'].strip()[:600]}\"\n\nWhich label does the answer propose? Labels:\n{cat}\n- other: "
                             "none of these\n\nAnswer with JSON only: {\"label\": \"<label id>\", \"rationale\": \"<short>\"}"))
        recs = j.label_prompts([("j1", r["task"], p) for r, p in items])
        lab_by = {r["sample_id"]: rec.get("label") for (r, _), rec in zip(items, recs)}
        for o in out:
            if o["sample_id"] in lab_by:
                lab = lab_by[o["sample_id"]]
                o["mapped"] = lab if lab else "unmapped"
    for o in out:
        o["category"] = ("names_X" if o["mapped"] == o["X"] else "off_catalogue" if o["mapped"] in ("other", "unmapped", None)
                         else "survivor")
    with (root / "data" / "association.jsonl").open("w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    return out


def a_free(assoc: list[dict], task: str, x: str) -> dict:
    surv = [m for m in TASKS[task]["modes"] if m != x]
    rs = [a for a in assoc if a["task"] == task and a["X"] == x]
    valid = [a for a in rs if a["category"] == "survivor"]
    cnt = Counter(a["mapped"] for a in valid)
    dist = {j: (cnt.get(j, 0) + 1) / (len(valid) + len(surv)) for j in surv}
    return {"dist": dist, "n_answers": len(rs), "n_valid": len(valid),
            "n_names_X": sum(1 for a in rs if a["category"] == "names_X"),
            "n_off_catalogue": sum(1 for a in rs if a["category"] == "off_catalogue"), "raw_counts": dict(cnt)}


def _argmax_set(d: dict, tol: float = 1e-12) -> list[str]:
    if not d:
        return []
    m = max(d.values())
    return sorted(k for k, v in d.items() if abs(v - m) <= tol)


def _argmin_set(d: dict, tol: float = 1e-12) -> list[str]:
    if not d:
        return []
    m = min(d.values())
    return sorted(k for k, v in d.items() if abs(v - m) <= tol)


def min_hitting(sets: list[list[str]]) -> int:
    sets = [set(s) for s in sets if s]
    if not sets:
        return 0
    universe = sorted(set().union(*sets))
    for k in range(1, len(sets) + 1):
        for comb in itertools.combinations(universe, k):
            if all(s & set(comb) for s in sets):
                return k
    return len(sets)


def proximity(task: str, x: str, prog_by_label: dict, forced_by_label: dict, stage: str) -> dict[str, float]:
    xs = prog_by_label.get(x, [])
    if len(xs) < 10:
        xs = forced_by_label.get(x, [])
    xs = xs[:30]
    xt = [canon_tokens(c) for c in xs]
    xt = [t for t in xt if t]
    out = {}
    for j in TASKS[task]["modes"]:
        if j == x:
            continue
        if stage == "A":
            js = [canon_tokens(REFS[task][j])]
        else:
            js = [canon_tokens(c) for c in forced_by_label.get(j, [])[:30]]
            js = [t for t in js if t] or [canon_tokens(REFS[task][j])]
        if not xt:
            xt_use = [canon_tokens(REFS[task][x])]
        else:
            xt_use = xt
        out[j] = statistics.median(token_distance(a, b) for a in xt_use for b in js)
    return out


def nominations(root: Path, stage: str, frlp: dict | None = None) -> dict:
    labs = [json.loads(l) for l in (root / "data" / "samples_pilot.jsonl").open()]
    forced = [json.loads(l) for l in (root / "data" / "samples_forced.jsonl").open()]
    assoc = [json.loads(l) for l in (root / "data" / "association.jsonl").open()]
    table = {}
    for t in TASK_ORDER:
        modes = list(TASKS[t]["modes"])
        pil = [r for r in labs if r["task"] == t]
        att = [r for r in pil if r["label"] != "invalid"]
        share = {m: sum(r["label"] == m for r in att) / max(len(att), 1) for m in modes}
        modal = max(modes, key=lambda m: share[m])
        prog_by_label = defaultdict(list)
        for r in pil:
            prog_by_label[r["label"]].append(r["code"])
        forced_by_label = defaultdict(list)
        for r in sorted(forced, key=lambda r: (r["round"] or 0, r["paraphrase_id"] or 0)):
            if r["task"] == t and r["label"] == r["forced_mode"]:
                forced_by_label[r["label"]].append(r["code"])
        planned = [modal] + [m for m in modes if m != modal and share[m] >= 0.10]
        events = {}
        for x in modes:
            surv = [m for m in modes if m != x]
            sh = {m: share[m] for m in surv}
            if stage == "B" and frlp is not None:
                # ladder ties broken by baseline L_corr
                ties = _argmax_set(sh)
                lc = {m: frlp.get((t, m), {}).get("L_corr") for m in ties}
                lc = {m: v for m, v in lc.items() if v is not None and math.isfinite(v)}
                ladder = _argmax_set(lc) if lc else ties
            else:
                ladder = _argmax_set(sh)
            af = a_free(assoc, t, x)
            assoc_nom = _argmax_set(af["dist"])
            prox = proximity(t, x, prog_by_label, forced_by_label, stage)
            prox_nom = _argmin_set(prox)
            fams = {"ladder": ladder, "association": assoc_nom, "proximity": prox_nom}
            dis = min_hitting(list(fams.values())) - 1
            pair = {f"{a}-{b}": bool(set(fams[a]) & set(fams[b]))
                    for a, b in (("ladder", "association"), ("ladder", "proximity"), ("association", "proximity"))}
            events[x] = {"nominations": fams, "disagreement": dis, "pairwise_agree": pair, "association": af,
                         "proximity_median_distance": prox, "planned": x in planned}
        d_task = sum(events[x]["disagreement"] for x in planned)
        d_all = sum(e["disagreement"] for e in events.values())
        table[t] = {"modal": modal, "pilot_shares": share, "planned_events": planned, "events": events,
                    "D_task": d_task, "D_allK": d_all, "K": len(modes)}
    order = sorted(TASK_ORDER, key=lambda t: (-table[t]["D_task"], -table[t]["D_allK"], -table[t]["K"],
                                               TASK_ORDER.index(t)))
    return {"stage": stage, "table": table, "order": order}
