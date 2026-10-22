"""Items 0a (Stage A metric), 0b (site of the choice), 0f (top-five dose) and 0g (Table 238), all from raw rows.

Each function returns its recomputed values and registers paragraph-level edits with the shared editor. Old text
is always copied from the vendored report by the editor (a full paragraph line, or a whole table block).
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from typing import Any

from common import MARK, TABLES, inp, read_json, read_jsonl, src_ref, truthy
from corrections import V
from stats import clopper_pearson, mcnemar_exact

EX = "art_rMlbrjVB1c__"
EN = "art_lpQalcAXMGr1"
TASK_NAME = {"T03": "kth smallest", "T10": "connected components", "T2": "shortest path", "T05": "two sum",
             "T06": "find duplicate", "T1": "grid"}
Y_NAME = {"quickselect": "quickselect", "bfs": "BFS", "bf_spfa": "Bellman-Ford/SPFA", "brute_force": "brute force",
          "index_marking": "index marking", "dfs": "DFS"}
TABLE_TASK = {"244": "T03", "245": "T10", "246": "T2", "247": "T05", "248": "T06", "249": "T1"}
CELL_OF_LABEL = {"full ban": "BAN", "exchange, blocks 0-11": "X_0-11", "exchange, blocks 12-23": "X_12-23",
                 "exchange, blocks 24-35": "X_24-35", "exchange, blocks 0-35": "X_0-35",
                 "condition-span splice": "COND", "read-position exchange": "RPOS",
                 "matched-norm random exchange, blocks 0-35": "MR_0-35",
                 "matched-norm random exchange, blocks 12-23": "MR_12-23", "placebo twin": "PLACEBO"}
EXT_CELL = {("kth smallest", "fourth-template ban"): ("T03", "BAN_W4"),
            ("kth smallest", "fourth-template twin"): ("T03", "TWIN_W4"),
            ("kth smallest", "fourth-template exchange, blocks 0-35"): ("T03", "X_0-35_W4"),
            ("connected components", "fourth-template ban"): ("T10", "BAN_W4"),
            ("connected components", "forced BFS"): ("T10", "FORCED"),
            ("connected components", "padding twin of forced BFS"): ("T10", "FORCEDPAD"),
            ("connected components", "forced BFS exchange, blocks 0-35"): ("T10", "FORCEDX_0-35"),
            ("connected components", "fourth-template twin"): ("T10", "TWIN_W4"),
            ("connected components", "fourth-template exchange, blocks 0-35"): ("T10", "X_0-35_W4"),
            ("shortest path", "fourth-template ban"): ("T2", "BAN_W4"),
            ("shortest path", "forced Bellman-Ford or SPFA"): ("T2", "FORCED"),
            ("shortest path", "padding twin of the forced prompt"): ("T2", "FORCEDPAD"),
            ("shortest path", "forced exchange, blocks 0-35"): ("T2", "FORCEDX_0-35"),
            ("shortest path", "semantic seed"): ("T2", "SEED"),
            ("shortest path", "padding twin of the seed"): ("T2", "SEEDPAD"),
            ("shortest path", "seed exchange, blocks 0-35"): ("T2", "SEEDX_0-35"),
            ("shortest path", "fourth-template twin"): ("T2", "TWIN_W4"),
            ("shortest path", "fourth-template exchange, blocks 0-35"): ("T2", "X_0-35_W4")}
# expected values written in the plan; the recomputed value wins on disagreement (listed as discrepancies)
PLAN_EXPECT = {("T2", "X_0-35"): (24, 21), ("T2", "X_12-23"): (18, 11), ("T03", "X_0-35"): (17, 16),
               ("T1", "X_0-35"): (14, 3), ("T1", "COND"): (10, 7), ("T2", "FORCEDX_0-35"): (30, 30)}


def _cp(k: int, n: int) -> str:
    lo, hi = clopper_pearson(k, n)
    f = lambda x: f"{x:.2f}" if x >= 0.01 or x == 0 else f"{x:.1e}"
    return f"[{f(lo)}, {f(hi)}]"


def _table_block(report: str, caption_prefix: str) -> str:
    """The caption line, the blank line and every table row that follows, verbatim."""
    i = report.find(caption_prefix)
    assert i >= 0 and report.count(caption_prefix) == 1, caption_prefix
    lines = report[i:].split("\n")
    out = [lines[0]]
    j = 1
    while j < len(lines) and not lines[j].startswith("|"):
        out.append(lines[j])
        j += 1
    while j < len(lines) and lines[j].startswith("|"):
        out.append(lines[j])
        j += 1
    return "\n".join(out)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


# ======================================================================== 0a
def stage_a_cells() -> dict[str, Any]:
    rows = read_jsonl(inp(EX, "data/labels.jsonl"))
    sa = read_json(inp(EX, "results/stage_a.json"))["tasks"]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        arm = r["arm"]
        if arm == "TWIN" and int(r["slot_index"] if r.get("slot_index") is not None else r["slot"]) >= 30:
            continue
        groups[(r["task"], arm)].append(r)
    out: dict[str, Any] = {}
    for (task, arm), rs in groups.items():
        if task not in sa or arm.startswith(("ST_", "DMD", "TOP5")):
            continue
        Y = sa[task]["Y"]
        n = len(rs)
        att = sum(r["label"] == Y for r in rs)
        cor = sum(r["label"] == Y and truthy(r["passed"]) for r in rs)
        npass = sum(truthy(r["passed"]) for r in rs)
        off = sum(r["label"] not in (sa[task]["default"], "other", "invalid", None) for r in rs)
        corr_comp = Counter(r["label"] for r in rs if truthy(r["passed"]))
        att_comp = Counter(r["label"] for r in rs)
        out[f"{task}|{arm}"] = {"task": task, "cell": arm, "Y": Y, "default": sa[task]["default"], "n": n,
                                "attempted_Y": att, "correct_Y": cor, "pass_k": npass, "pass": npass / n,
                                "off_default": off / n, "Y_share": att / n, "correct_Y_share": cor / n,
                                "Y_ci95_cp": clopper_pearson(att, n), "correct_Y_ci95_cp": clopper_pearson(cor, n),
                                "attempted_comp": dict(att_comp), "correct_comp": dict(corr_comp),
                                "rows": {r["crn_key"]: (r["label"], truthy(r["passed"])) for r in rs}}
    # twin-relative quantities (each extension cell against its own twin)
    twin_of = {"FORCEDX_0-35": "FORCEDPAD", "SEEDX_0-35": "SEEDPAD", "X_0-35_W4": "TWIN_W4", "BAN_W4": "TWIN_W4",
               "FORCED": "FORCEDPAD", "SEED": "SEEDPAD"}
    for k, c in out.items():
        tw = out.get(f"{c['task']}|{twin_of.get(c['cell'], 'TWIN')}")
        if tw:
            c["transfer"] = c["Y_share"] - tw["Y_share"]
            c["correct_transfer"] = c["correct_Y_share"] - tw["correct_Y_share"]
            c["pass_ratio"] = c["pass"] / tw["pass"] if tw["pass"] else None
            c["gate_ok"] = c["pass_ratio"] is not None and c["pass_ratio"] >= 0.8 - 1e-12
            c["twin_cell"] = tw["cell"]
    return out


def item_0a(ed, report: str) -> dict[str, Any]:
    cells = stage_a_cells()
    sa = read_json(inp(EX, "results/stage_a.json"))
    c0 = read_json(inp(EX, "predictions/commit0.json"))["rules"]["stage_A"]
    values, discrepancies = [], []
    # cross-check against stage_a.json
    for task, T in sa["tasks"].items():
        Y = T["Y"]
        for cell, s in list(T["cells"].items()) + [("TWIN", T["TWIN"])]:
            c = cells.get(f"{task}|{cell}")
            if c is None:
                values.append(V(f"{task}|{cell}|n", None, s.get("n"), source=src_ref(EX, "results/stage_a.json")))
                continue
            ref = src_ref(EX, "results/stage_a.json", f"tasks.{task}.cells.{cell}")
            values += [V(f"{task}|{cell}|n", c["n"], s.get("n"), source=ref),
                       V(f"{task}|{cell}|attempted_Y", c["attempted_Y"], s.get("attempted_comp", {}).get(Y, 0), source=ref),
                       V(f"{task}|{cell}|correct_Y", c["correct_Y"], s.get("correct_comp", {}).get(Y, 0), source=ref),
                       V(f"{task}|{cell}|pass", c["pass"], s.get("pass"), tol="prop", source=ref)]
            if cell != "TWIN":
                values += [V(f"{task}|{cell}|Y_share", c["Y_share"], s.get("Y_share"), tol="prop", source=ref),
                           V(f"{task}|{cell}|transfer_commit0", c["transfer"], s.get("transfer"), tol="effect", source=ref),
                           V(f"{task}|{cell}|pass_ratio", c["pass_ratio"], s.get("pass_ratio"), tol="prop", source=ref),
                           V(f"{task}|{cell}|correct_Y_share", c["correct_Y_share"], None, tol="prop",
                             source=src_ref(EX, "data/labels.jsonl"))]
    for (task, cell), (ea, ec) in PLAN_EXPECT.items():
        c = cells[f"{task}|{cell}"]
        for nm, got, exp in (("attempted", c["attempted_Y"], ea), ("correct", c["correct_Y"], ec)):
            if got != exp:
                discrepancies.append({"value": f"{task}|{cell}|{nm}_Y", "plan_expected": exp, "recomputed": got})
    # NEW post hoc: correct-Y McNemar of X_0-35 against MR_0-35 on crn-paired slots
    mr = {}
    for task in ("T2", "T03", "T10"):
        X, M = cells[f"{task}|X_0-35"], cells[f"{task}|MR_0-35"]
        Y = X["Y"]
        keys = sorted(set(X["rows"]) & set(M["rows"]))
        xs = [int(X["rows"][k][0] == Y and X["rows"][k][1]) for k in keys]
        ys = [int(M["rows"][k][0] == Y and M["rows"][k][1]) for k in keys]
        xa = [int(X["rows"][k][0] == Y) for k in keys]
        ya = [int(M["rows"][k][0] == Y) for k in keys]
        b = sum(1 for x, y in zip(xs, ys) if x and not y)
        c = sum(1 for x, y in zip(xs, ys) if y and not x)
        ba = sum(1 for x, y in zip(xa, ya) if x and not y)
        ca = sum(1 for x, y in zip(xa, ya) if y and not x)
        rec = sa["MR"][task]
        mr[task] = {"n_pairs": len(keys), "correct_b": b, "correct_c": c, "correct_p": mcnemar_exact(b, c),
                    "attempted_b": ba, "attempted_c": ca, "attempted_p": mcnemar_exact(ba, ca)}
        ref = src_ref(EX, "results/stage_a.json", f"MR.{task}")
        values += [V(f"{task}|MR_contrast|attempted_b", ba, rec["b_X_only"], source=ref),
                   V(f"{task}|MR_contrast|attempted_c", ca, rec["c_MR_only"], source=ref),
                   V(f"{task}|MR_contrast|attempted_p", mr[task]["attempted_p"], rec["p"], tol="p", source=ref),
                   V(f"{task}|MR_contrast|correct_b_posthoc", b, None, source=src_ref(EX, "data/labels.jsonl")),
                   V(f"{task}|MR_contrast|correct_c_posthoc", c, None, source=src_ref(EX, "data/labels.jsonl")),
                   V(f"{task}|MR_contrast|correct_p_posthoc", mr[task]["correct_p"], None, tol="p",
                     source=src_ref(EX, "data/labels.jsonl"))]
    values.append(V("commit0_transfer_text", c0["transfer"],
                    "share(label == Y | cell) - share(label == Y | TWIN), all samples (invalid rows count as not-Y)",
                    tol="text", source=src_ref(EX, "predictions/commit0.json", "rules.stage_A.transfer")))
    C = lambda t, cell: cells[f"{t}|{cell}"]

    def ac(t: str, cell: str) -> str:
        c = C(t, cell)
        return f"{c['attempted_Y']} of 30 attempts, {c['correct_Y']} of 30 correct programs"

    # ---- 6.4.1 definition sentence
    old_def = ("The outcome is the share of correct programs implementing the substitute Y of the ban; the *transfer* "
               "of a cell is its Y share minus that of the twin, and its *recovery* is the transfer divided by that of "
               "the full ban.")
    new_def = (f"The outcome, as committed before sampling (commit0: \"{c0['transfer']}\"), is the *Y share*: the share "
               "of all attempted programs labelled Y, invalid rows counting as not-Y; the *transfer* of a cell is that "
               "share minus the twin's; a cell counts only if its pass rate is at least 0.8 times the twin's (commit0: "
               f"\"{c0['pass_ratio']}\"); and its *recovery* is the transfer divided by that of the full ban. The "
               "*correct Y* column added to Tables 244 to 250 counts programs labelled Y that pass every hidden test, "
               "because an attempted share counts broken programs as Y: on the grid task the exchange at blocks 0-35 "
               f"has {C('T1', 'X_0-35')['attempted_Y']} attempts labelled DFS but {C('T1', 'X_0-35')['correct_Y']} "
               "correct DFS programs.")
    ed.sub("We call a *full-state exchange* the replacement", "0a", old_def, new_def, values=[])
    # ---- 6.4.1 results paragraph
    P = "The prediction held where the route data said it should"
    t2x = C("T2", "X_0-35")
    ed.sub(P, "0a", "turns 24 of 30 slots from Dijkstra to Bellman-Ford/SPFA (transfer 0.80,",
           f"turns {t2x['attempted_Y']} of 30 slots from Dijkstra to Bellman-Ford/SPFA ({ac('T2', 'X_0-35')}; "
           f"transfer {t2x['transfer']:.2f},")
    x12, x24 = C("T2", "X_12-23"), C("T2", "X_24-35")
    ed.sub(P, "0a", "Blocks 12 to 23 alone carry 0.60 and blocks 24 to 35 alone 0.37; blocks 0 to 11 carry none.",
           f"Blocks 12 to 23 alone carry {x12['transfer']:.2f} ({ac('T2', 'X_12-23')}, at a pass ratio of "
           f"{x12['pass_ratio']:.2f}, below the 0.8 gate) and blocks 24 to 35 alone {x24['transfer']:.2f} "
           f"({ac('T2', 'X_24-35')}); blocks 0 to 11 carry none.")
    k0, k011, kc = C("T03", "X_0-35"), C("T03", "X_0-11"), C("T03", "COND")
    ed.sub(P, "0a", "On kth smallest the same exchange transfers 0.57 to quickselect with every slot leaving the full "
                    "sort, blocks 0 to 11 alone already transfer 0.40, and here the condition span also carries the ban "
                    "(0.93).",
           f"On kth smallest the same exchange transfers {k0['transfer']:.2f} to quickselect ({ac('T03', 'X_0-35')}) "
           f"with every slot leaving the full sort, blocks 0 to 11 alone already transfer {k011['transfer']:.2f} "
           f"({ac('T03', 'X_0-11')}), and here the condition span also carries the ban ({kc['transfer']:.2f}; "
           f"{ac('T03', 'COND')}).")
    c35, c12 = C("T10", "X_0-35"), C("T10", "X_12-23")
    ed.sub(P, "0a", "but only 0.37 to 0.47 land on the ban's BFS and the rest on DFS.",
           f"but only {c35['transfer']:.2f} to {c12['transfer']:.2f} land on the ban's BFS ({c35['attempted_Y']} and "
           f"{c12['attempted_Y']} of 30 attempts, {c35['correct_Y']} and {c12['correct_Y']} of 30 correct programs) "
           "and the rest on DFS.")
    g0, gc = C("T1", "X_0-35"), C("T1", "COND")
    ed.sub(P, "0a", "the exchange at all blocks transfers 0.47 toward DFS and the condition-span splice 0.33, so each "
                    "carries part of the ban.",
           f"the exchange at all blocks transfers {g0['transfer']:.2f} toward DFS ({ac('T1', 'X_0-35')}, pass ratio "
           f"{g0['pass_ratio']:.2f}, below the 0.8 gate) and the condition-span splice {gc['transfer']:.2f} "
           f"({ac('T1', 'COND')}, pass ratio {gc['pass_ratio']:.2f}), so each carries part of the ban in attempts and "
           "only the splice passes the committed validity gate.")
    a5, a6, x5 = C("T05", "COND"), C("T06", "COND"), C("T05", "X_0-35")
    ed.sub(P, "0a", "(two sum 1.00, find duplicate 0.90), as predicted, but on two sum the task-specification states also "
                    "transfer brute force at 0.43, above the predicted ceiling of 0.2.",
           f"(two sum {a5['transfer']:.2f}, {ac('T05', 'COND')}; find duplicate {a6['transfer']:.2f}, "
           f"{ac('T06', 'COND')}), as predicted, but on two sum the task-specification states also transfer brute "
           f"force at {x5['transfer']:.2f} ({ac('T05', 'X_0-35')}), above the predicted ceiling of 0.2.")
    ed.sub(P, "0a", "(shortest path 23:0, kth smallest 16:2, connected components 11:0).",
           f"(shortest path {mr['T2']['attempted_b']}:{mr['T2']['attempted_c']}, kth smallest "
           f"{mr['T03']['attempted_b']}:{mr['T03']['attempted_c']}, connected components "
           f"{mr['T10']['attempted_b']}:{mr['T10']['attempted_c']}, on attempted Y as preregistered); counted on "
           f"correct Y instead, a post-hoc contrast added in iteration 7, the same pairs give "
           f"{mr['T2']['correct_b']}:{mr['T2']['correct_c']} (exact p {mr['T2']['correct_p']:.1e}), "
           f"{mr['T03']['correct_b']}:{mr['T03']['correct_c']} (p {mr['T03']['correct_p']:.1e}) and "
           f"{mr['T10']['correct_b']}:{mr['T10']['correct_c']} (p {mr['T10']['correct_p']:.1e}).")
    # ---- Tables 244 to 249
    for tnum, task in TABLE_TASK.items():
        block = _table_block(report, f"**Table {tnum}.** Stage A on")
        lines = block.split("\n")
        hdr_i = next(i for i, l in enumerate(lines) if l.startswith("|"))
        cap = lines[0]
        extra = (" The Y share is commit0's outcome (all attempted programs labelled Y; invalid rows count as not-Y); "
                 "the added column *Correct Y / N* counts programs labelled Y that pass every hidden test, with "
                 "Clopper-Pearson 95% intervals; a cell meets commit0's validity gate when its pass ratio is at least 0.8.")
        if task in mr:
            m = mr[task]
            extra += (f" Post hoc, on correct Y, the exchange at blocks 0-35 against the matched-norm random exchange "
                      f"gives {m['correct_b']}:{m['correct_c']} (exact p {m['correct_p']:.1e}).")
        cap = cap + extra + " " + MARK
        hdr = _split_row(lines[hdr_i])
        yi = hdr.index("Y share [CP 95%]")
        new_rows = [_join_row(hdr[:yi + 1] + ["Correct Y / N [CP 95%]"] + hdr[yi + 1:]),
                    "|" + "-|" * (len(hdr) + 1)]
        tv = []
        for l in lines[hdr_i + 2:]:
            cells_ = _split_row(l)
            key = CELL_OF_LABEL[cells_[0]]
            c = C(task, key)
            printed = float(cells_[yi].split()[0])
            tv.append(V(f"T{tnum}|{key}|Y_share_printed", round(c["Y_share"], 2), printed, tol="prop",
                        source=src_ref(EX, "data/labels.jsonl")))
            if abs(printed - c["Y_share"]) > 0.005 + 1e-9:
                cells_[yi] = f"{c['Y_share']:.2f} {_cp(c['attempted_Y'], c['n'])}"
            new_rows.append(_join_row(cells_[:yi + 1] + [f"{c['correct_Y']}/{c['n']} {_cp(c['correct_Y'], c['n'])}"]
                                      + cells_[yi + 1:]))
        new_block = "\n".join([cap] + lines[1:hdr_i] + new_rows)
        ed.whole(block, "0a", "table_replace", new_block, values=tv, section="6.4.1", table=f"Table {tnum}",
                 rationale="commit0's outcome restored as primary; correct-Y column added beside it")
    # ---- Table 250
    block = _table_block(report, "**Table 250.** Extensions")
    lines = block.split("\n")
    hdr_i = next(i for i, l in enumerate(lines) if l.startswith("|"))
    hdr = _split_row(lines[hdr_i])
    yi = hdr.index("Y share (Y) / default share")
    new_rows = [_join_row(hdr[:yi + 1] + ["Correct Y / n"] + hdr[yi + 1:]), "|" + "-|" * (len(hdr) + 1)]
    tv = []
    for l in lines[hdr_i + 2:]:
        cells_ = _split_row(l)
        task, key = EXT_CELL[(cells_[0], cells_[1])]
        c = C(task, key)
        printed = float(cells_[yi].split()[0])
        tv.append(V(f"T250|{task}|{key}|Y_share_printed", round(c["Y_share"], 2), printed, tol="prop",
                    source=src_ref(EX, "data/labels.jsonl")))
        tv.append(V(f"T250|{task}|{key}|n", c["n"], int(cells_[2]), source=src_ref(EX, "data/labels.jsonl")))
        new_rows.append(_join_row(cells_[:yi + 1] + [f"{c['correct_Y']}/{c['n']}"] + cells_[yi + 1:]))
    fx = C("T2", "FORCEDX_0-35")
    cap = (lines[0] + f" The added column counts programs labelled Y that pass every hidden test. Under commit0's "
           f"definition the forced Bellman-Ford/SPFA exchange transfers {fx['transfer']:.3f} "
           f"({fx['attempted_Y']} of 30 against {C('T2', 'FORCEDPAD')['attempted_Y']} of 30 for its padding twin). " + MARK)
    ed.whole(block, "0a", "table_replace", "\n".join([cap] + lines[1:hdr_i] + new_rows), values=tv,
             section="6.4.1", table="Table 250", rationale="correct-Y column for the extension cells")
    return {"cells": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in cells.items()},
            "mr_posthoc": mr, "values": values, "discrepancies": discrepancies, "commit0": c0}


def occurrence_ledger(report: str, corrected_line_ids: dict[int, str]) -> list[dict]:
    """Step 6 of 0a: every hit of the Stage A decimals, classified; written to tables/occurrence_ledger.csv."""
    rx = re.compile(r"(?<![\d.])0\.(?:80|57|47|33|567|467|333)(?!\d)")
    ctx = re.compile(r"exchang|Stage A|task-specification states|transfer", re.I)
    out = []
    for ln, line in enumerate(report.splitlines(), 1):
        for m in rx.finditer(line):
            s0 = max(line.rfind(". ", 0, m.start()), line.rfind("|", 0, m.start()), 0)
            s1 = [p for p in (line.find(". ", m.end()), line.find("|", m.end())) if p >= 0]
            sent = line[s0: min(s1) if s1 else len(line)]
            stage = bool(ctx.search(sent)) and not re.search(r"noise|alpha|Spearman|escape|odds ratio", sent, re.I)
            if 5497 <= ln <= 6211 and stage:
                action = f"replaced by {corrected_line_ids[ln]}" if ln in corrected_line_ids else "keep (checked)"
            elif stage:
                action = "keep: outside iteration 6 (pre-Stage-A use of the decimal)"
            else:
                action = "keep: not a Stage A share"
            out.append({"line": ln, "value": m.group(0), "snippet": sent.strip()[:160],
                        "class": "stageA_share" if stage and 5497 <= ln <= 6211 else "other", "action": action})
    TABLES.mkdir(exist_ok=True)
    with (TABLES / "occurrence_ledger.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["line", "value", "class", "action", "snippet"])
        w.writeheader()
        w.writerows(out)
    return out


# ======================================================================== 0b
def item_0b(ed, report: str, cells: dict) -> dict[str, Any]:
    sg = read_json(inp(EX, "results/site_grid.json"))
    ref = lambda k: src_ref(EX, "results/site_grid.json", k)
    ph = {t: sg["tasks"][t]["indicator_alpha_le4_posthoc"] for t in ("T03", "T10")}
    vals = []
    s2 = {}
    for t in ("T03", "T10"):
        b = ph[t]["beta"]["S2"]
        cb = ph[t]["cluster_bootstrap"]["ci95"]["S2"]
        pr = ph[t]["profile_ci95"]["S2"]
        s2[t] = (b, cb, pr)
        k = f"tasks.{t}.indicator_alpha_le4_posthoc"
        plan = {"T03": (-1.70, [-3.96, 0.42]), "T10": (-0.56, [-4.93, 2.91])}[t]
        vals += [V(f"{t}|posthoc_S2_beta", b, plan[0], tol="effect", source=ref(k + ".beta.S2")),
                 V(f"{t}|posthoc_S2_cluster_ci", cb, plan[1], tol="ci", source=ref(k + ".cluster_bootstrap.ci95.S2")),
                 V(f"{t}|posthoc_S2_profile_ci", pr, None, tol="ci", source=ref(k + ".profile_ci95.S2")),
                 V(f"{t}|posthoc_S1_beta", ph[t]["beta"]["S1"], {"T03": -3.76, "T10": -4.98}[t], tol="effect",
                   source=ref(k + ".beta.S1"))]
    prim = sg["tasks"]["T10"]["indicator"]
    s4 = (prim["beta"]["S4"], prim["profile_ci95"]["S4"])
    flips = sg["tasks"]["T10"]["paired_flips"]["S0_vs_S4"]
    vals += [V("T10|S4_beta_primary", s4[0], 2.51, tol="effect", source=ref("tasks.T10.indicator.beta.S4")),
             V("T10|S4_profile_ci", s4[1], [1.39, 3.80], tol="ci", source=ref("tasks.T10.indicator.profile_ci95.S4")),
             V("T10|flips_S0_vs_S4", f"{flips['S0_only']}:{flips['other_only']}", "4:18", tol="text",
               source=ref("tasks.T10.paired_flips.S0_vs_S4")),
             V("T10|flips_S0_vs_S4_p", flips["p"], 0.004, tol="effect", source=ref("tasks.T10.paired_flips.S0_vs_S4.p")),
             V("rule_label", sg["RULE"]["verdict"], "WITHDRAWN as FP8-specific: the site of the choice is open",
               tol="text", source=ref("RULE.verdict"))]
    # concordance table (NEW): per task and band, the noise share against the exchange transfer
    band_site = {"0-11": "S4", "12-23": "S0", "24-35": "S5"}
    conc = {}
    for t in ("T03", "T10"):
        cg = sg["tasks"][t]["cells"]
        noise = {b: max(cg[f"{s}|a{a}"]["correct_off_default"] for a in (1, 2, 4)) for b, s in band_site.items()}
        noise_at = {b: max((cg[f"{s}|a{a}"]["correct_off_default"], a) for a in (1, 2, 4))[1] for b, s in band_site.items()}
        noise_mean = {b: sum(cg[f"{s}|a{a}"]["correct_off_default"] for a in (1, 2, 4)) / 3 for b, s in band_site.items()}
        exch = {b: cells[f"{t}|X_{b}"]["transfer"] for b in band_site}
        exch_off = {b: cells[f"{t}|X_{b}"]["off_default"] for b in band_site}
        # the artifact's own band rule: mean correct off-default share over alpha 1, 2 and 4 (the maximum ties on kth
        # smallest, 0.37 at blocks 0-11 and at blocks 12-23, so it is reported only as a description)
        nb, xb = max(noise_mean, key=noise_mean.get), max(exch, key=exch.get)
        rec = sg["ST_x_StageA_concordance"][t]
        conc[t] = {"noise_max_by_band": noise, "noise_alpha_at_max": noise_at, "noise_mean_by_band": noise_mean,
                   "exchange_Y_transfer_by_band": exch, "exchange_off_default_by_band": exch_off,
                   "noise_band": nb, "exchange_band": xb, "concordant": nb == xb}
        vals += [V(f"{t}|concordant", nb == xb, rec["concordant"], tol="text", source=ref(f"ST_x_StageA_concordance.{t}")),
                 V(f"{t}|noise_band", nb, rec["noise_band"], tol="text", source=ref(f"ST_x_StageA_concordance.{t}")),
                 V(f"{t}|exchange_band", xb, rec["exchange_band"], tol="text", source=ref(f"ST_x_StageA_concordance.{t}"))]
    uf011, uf2435 = cells["T10|X_0-11"]["off_default"], cells["T10|X_24-35"]["off_default"]
    vals += [V("T10|X_0-11_off_default", uf011, 0.87, tol="prop", source=src_ref(EX, "data/labels.jsonl")),
             V("T10|X_24-35_off_default", uf2435, 0.63, tol="prop", source=src_ref(EX, "data/labels.jsonl"))]
    f2 = lambda x: f"{x:.2f}"
    ci = lambda c: f"[{c[0]:.2f}, {c[1]:.2f}]"
    s2txt = (f"beta {f2(s2['T03'][0])} {ci(s2['T03'][1])} on kth smallest; {f2(s2['T10'][0])} {ci(s2['T10'][1])} on "
             f"connected components, cluster bootstrap; profile intervals {ci(s2['T03'][2])} and {ci(s2['T10'][2])}")
    cc = conc["T10"]
    ed.sub("The committed rule fitted a Firth logistic regression", "0b",
           "The prefill-site claim is therefore withdrawn as preregistered, and its post-hoc form survives in bf16 at the "
           "ban-free unit.",
           "The prefill-site claim is therefore withdrawn as preregistered. Post hoc (alpha of at most 4) the read "
           f"position is below the task-specification site on both tasks; the condition-span clause fails post hoc as "
           f"well ({s2txt}), so the site of the choice remains open, as the artifact concludes; its rule label reads "
           f"'{sg['RULE']['verdict']}'. The 'FP8-specific' half of that label cannot apply: Section 6.3 shows that bf16 "
           "reproduces the escapes direction by direction (Spearman 0.96 and 0.87) and that activation rounding adds "
           "nothing, so the withdrawal comes from the missing common support and the breakage at alpha 8 in bf16, not "
           "from the engine. Noise sites and Stage A agree on the band on kth smallest and disagree on connected "
           f"components (Table 254b): there noise moves the algorithm most at blocks 0 to 11 (mean "
           f"{cc['noise_mean_by_band']['0-11']:.2f} over alpha 1 to 4 against {cc['noise_mean_by_band']['12-23']:.2f} at "
           f"blocks 12 to 23; {cc['noise_max_by_band']['0-11']:.2f} "
           f"correct off-default at alpha {cc['noise_alpha_at_max']['0-11']}; coefficient {s4[0]:+.2f} "
           f"{ci(s4[1])} against the plan site; paired flips {flips['S0_only']}:{flips['other_only']}, p "
           f"{flips['p']:.3f}, between the plan site and blocks 0-11), while the exchange transfers BFS at blocks 12 to "
           f"23. The removal of the default there is depth-redundant: the exchange at blocks 0-11 alone takes "
           f"{uf011:.2f} of attempts off union find and at blocks 24-35 alone {uf2435:.2f}.")
    rows = ["", "", f"**Table 254b.** Noise sites against Stage A, per task and block band (NEW in iteration 7): the "
            "largest correct off-default share of spec-position noise at alpha 1 to 4 (with its alpha), the full-state "
            "exchange's Y share (commit0) and off-default share at the same band, and whether the band where noise acts "
            "most (by the mean over alpha 1, 2 and 4, the artifact's band rule) is the band where the exchange transfers "
            "most. Sources: exchange and site experiment "
            "`results/site_grid.json`, `data/labels.jsonl`. " + MARK, "",
            "| Task | Band | Noise, mean correct off-default over alpha 1-4 | Noise, max correct off-default (alpha) | "
            "Exchange Y share | Exchange off-default share | Noise band / exchange band | Concordant |",
            "|-|-|-|-|-|-|-|-|"]
    for t in ("T03", "T10"):
        c = conc[t]
        for i, b in enumerate(("0-11", "12-23", "24-35")):
            rows.append(f"| {TASK_NAME[t] if i == 0 else ''} | blocks {b} | {c['noise_mean_by_band'][b]:.2f} | "
                        f"{c['noise_max_by_band'][b]:.2f} "
                        f"({c['noise_alpha_at_max'][b]}) | {c['exchange_Y_transfer_by_band'][b]:.2f} | "
                        f"{c['exchange_off_default_by_band'][b]:.2f} | "
                        f"{(c['noise_band'] + ' / ' + c['exchange_band']) if i == 0 else ''} | "
                        f"{('yes' if c['concordant'] else 'no') if i == 0 else ''} |")
    anchor = _table_block(report, "**Table 254.** Firth logistic regression").split("\n")[-1]
    ed.insert(anchor, "0b", "\n".join(rows), values=[], section="6.4.2", table="Table 254b",
              rationale="NEW concordance table of noise sites against Stage A")
    ed.sub("- *The prefill-site claim in its preregistered form* in bf16", "0b",
           "Its post-hoc form (alpha 4 or less) puts the read position below the task-specification site on both tasks.",
           "Post hoc (alpha 4 or less) the read position is below the task-specification site on both tasks, but the "
           f"condition-span clause fails ({f2(s2['T03'][0])} {ci(s2['T03'][1])} and {f2(s2['T10'][0])} "
           f"{ci(s2['T10'][1])}), so the site of the choice is open, as the artifact's rule label says "
           f"('{sg['RULE']['verdict']}'); its engine half is refuted by Section 6.3.")
    ed.sub("A random displacement of the task-specification states", "0b",
           "and a post-hoc model at alpha 4 or less puts the read position below the task-specification site on both tasks.",
           "and a post-hoc model at alpha 4 or less puts the read position below the task-specification site on both "
           f"tasks but not the condition span (beta {f2(s2['T03'][0])} {ci(s2['T03'][1])} and {f2(s2['T10'][0])} "
           f"{ci(s2['T10'][1])}), so the site of the choice remains open; on connected components noise acts most at "
           "blocks 0 to 11 while the exchange transfers at blocks 12 to 23.")
    ed.sub("The internal results that hold under bf16 are therefore", "0b",
           "the read-position transplant that breaks the output without moving the algorithm, and the post-hoc ordering "
           "of noise sites.",
           "and the read-position transplant that breaks the output without moving the algorithm; the post-hoc site "
           "ordering is not among them, because its condition-span clause fails post hoc.")
    return {"posthoc_S2": s2, "S4": s4, "flips_S0_vs_S4": flips, "rule_label": sg["RULE"]["verdict"],
            "concordance": conc, "depth_redundancy": {"X_0-11_off_default": uf011, "X_24-35_off_default": uf2435},
            "values": vals}


# ======================================================================== 0f
def item_0f(ed) -> dict[str, Any]:
    t = read_json(inp(EX, "results/top5_push.json"))
    g = t["geometry"]
    pc1 = [c[0] for c in g["centroids_pc"]]
    pts = defaultdict(list)
    for k, xy in g["points_pc"].items():
        pts[k.split("__")[0]].append(xy[0])
    mean = lambda v: sum(v) / len(v)
    pas = {a: t["cells"][f"TOP5_a{a}"]["pass"] for a in (1, 2, 4, 8)}
    ref = src_ref(EX, "results/top5_push.json")
    vals = [V("centroid_PC1_min", min(pc1), -0.098, tol="effect", source=ref + "#geometry.centroids_pc"),
            V("centroid_PC1_max", max(pc1), 0.144, tol="effect", source=ref + "#geometry.centroids_pc"),
            V("twin_PC1_mean", mean(pts["twin"]), 0.09, tol="effect", source=ref + "#geometry.points_pc"),
            V("push1_PC1_mean", mean(pts["push1"]), -0.44, tol="effect", source=ref + "#geometry.points_pc")]
    vals += [V(f"pass_alpha{a}", p, {1: 0.67, 2: 0.30, 4: 0.03, 8: 0.00}[a], tol="prop", source=ref + f"#cells.TOP5_a{a}")
             for a, p in pas.items()]
    dose = ("at doses of 1 to 8 ban units, which overshoot the forced-prompt manifold, the push breaks programs before it "
            "moves the algorithm; an in-manifold dose was not tried")
    ed.sub("On the grid task, iteration 4's top-five direction", "0f",
           "It breaks programs before it moves the algorithm: the pass rate falls from 0.67 to 0.30, 0.03 and 0.00,",
           f"{dose[0].upper() + dose[1:]}: the pass rate falls from {pas[1]:.2f} at alpha 1 to {pas[2]:.2f}, "
           f"{pas[4]:.2f} and {pas[8]:.2f},")
    ed.sub("On the grid task, iteration 4's top-five direction", "0f",
           "already at alpha 1 it moves farther along the first component than the whole spread of the ten centroids.",
           f"already at alpha 1 it moves farther along the first component than the whole spread of the ten centroids "
           f"(the four alpha-1 points move from a twin mean of {mean(pts['twin']):+.2f} to {mean(pts['push1']):+.2f} on "
           f"PC1, against centroids spread from {min(pc1):+.3f} to {max(pc1):+.3f}).")
    ed.sub("**The top-five prohibition in two families.**", "0f",
           "The activation version of the prohibition breaks programs before it moves the algorithm.",
           "At doses of 1 to 8 ban units, which overshoot the forced-prompt manifold, the activation version of the "
           "prohibition breaks programs before it moves the algorithm; an in-manifold dose was not tried.")
    ed.sub("A single prompt ban, where the model obeys it", "0f",
           "a push along the top-five direction breaks programs before it moves the algorithm.",
           "at doses of 1 to 8 ban units, which overshoot the forced-prompt manifold, a push along the top-five direction "
           "breaks programs before it moves the algorithm; an in-manifold dose was not tried.")
    return {"centroid_pc1_range": [min(pc1), max(pc1)], "twin_pc1": mean(pts["twin"]),
            "push_pc1": {k: mean(v) for k, v in pts.items() if k.startswith("push")}, "pass": pas, "values": vals}


# ======================================================================== 0g
ENG = {"a": "W8A8", "b": "W8A16", "c": "W16A8", "d": "bf16"}
DEFAULT = {"T10": "union_find", "T2": "dijkstra"}


def item_0g(ed, report: str) -> dict[str, Any]:
    rows = read_jsonl(inp(EN, "data/samples.jsonl"))
    pn = read_json(inp(EN, "results/pn.json"))
    esc = read_json(inp(EN, "results/escape_by_engine.json"))
    ver = read_json(inp(EN, "results/verdict.json"))
    agg: dict = {}
    for r in rows:
        if not str(r["arm"]).startswith("PN_a"):
            continue
        k = (r["engine"], r["task"], r["arm"])
        a = agg.setdefault(k, {"n": 0, "valid": 0, "correct": 0, "off": 0, "correct_off": 0})
        a["n"] += 1
        lab, ok, valid = r["label"], truthy(r["passed"]), truthy(r["valid"])
        a["valid"] += valid
        a["correct"] += ok
        off = valid and lab not in (DEFAULT[r["task"]], "other", "invalid", None)
        a["off"] += off
        a["correct_off"] += off and ok
    vals, table_rows = [], []
    for (e, t, arm), a in sorted(agg.items()):
        rec = pn[t][arm][e]
        ref = src_ref(EN, "results/pn.json", f"{t}.{arm}.{e}")
        vals += [V(f"{e}|{t}|{arm}|n", a["n"], rec["n"], source=ref),
                 V(f"{e}|{t}|{arm}|k_off", a["off"], rec["k_off"], source=ref),
                 V(f"{e}|{t}|{arm}|k_pass", a["correct"], rec["k_pass"], source=ref),
                 V(f"{e}|{t}|{arm}|correct_off", a["correct_off"], None, source=src_ref(EN, "data/samples.jsonl"))]
    plan = {("a", "T2", "PN_a2"): (14, 37), ("d", "T2", "PN_a2"): (9, 31), ("a", "T2", "PN_a1"): (9, 43),
            ("d", "T2", "PN_a1"): (5, 43)}
    disc = []
    for k, (co, cp) in plan.items():
        a = agg[k]
        if (a["correct_off"], a["correct"]) != (co, cp):
            disc.append({"value": "|".join(k), "plan_expected": f"{co}/{cp}",
                         "recomputed": f"{a['correct_off']}/{a['correct']}"})
    # Table 238 with two added columns
    block = _table_block(report, "**Table 238.** Per-sample plan noise per engine")
    lines = block.split("\n")
    hdr_i = next(i for i, l in enumerate(lines) if l.startswith("|"))
    hdr = _split_row(lines[hdr_i])
    new = [_join_row(hdr + ["Correct off-default / correct programs (W8A8; W8A16; W16A8; bf16)",
                            "Correct off-default / 50 (W8A8; W8A16; W16A8; bf16)"]),
           "|" + "-|" * (len(hdr) + 2)]
    tname = {"connected components": "T10", "shortest path": "T2"}
    for l in lines[hdr_i + 2:]:
        c = _split_row(l)
        t, arm = tname[c[0]], "PN_a" + c[1].split()[-1]
        aa = [agg[(e, t, arm)] for e in "abcd"]
        new.append(_join_row(c + ["; ".join(f"{x['correct_off']}/{x['correct']}" for x in aa),
                                  "; ".join(f"{x['correct_off']}/{x['n']}" for x in aa)]))
    cap = (lines[0] + " The two added columns count only programs that pass every hidden test (from the per-row labels "
           "of `data/samples.jsonl`, the engine-a rows being iteration 4's), first over the engine's correct programs "
           "and then over all 50. " + MARK)
    ed.whole(block, "0g", "table_replace", "\n".join([cap] + lines[1:hdr_i] + new), values=vals, section="6.3",
             table="Table 238", rationale="correct-only columns beside the attempted counts")
    # screen-level verdict
    a2 = {e: esc[e]["T2"]["alpha"]["2.0"] for e in "abcd"}
    scr = {e: a2[e]["n_screen_pass"] for e in "abcd"}
    excess_fail = {e: a2[e]["n_excess_met_but_pass_clause_failed"] for e in "abcd"}
    vals2 = [V(f"T2|screen_passes|{e}", scr[e], {"a": 15, "b": 8, "c": 8, "d": 9}[e],
               source=src_ref(EN, "results/escape_by_engine.json", f"{e}.T2.alpha.2.0.n_screen_pass")) for e in "abcd"]
    vals2 += [V(f"T2|excess_met_pass_failed|{e}", excess_fail[e], 17 if e in "ad" else None,
                source=src_ref(EN, "results/escape_by_engine.json", f"{e}.T2.alpha.2.0")) for e in "abcd"]
    vals2.append(V("T2|screen_level_verdict", ver["T2"]["screen_level_verdict"], "MIXED", tol="text",
                   source=src_ref(EN, "results/verdict.json", "T2.screen_level_verdict")))
    vals2.append(V("T2|literal_verdict", ver["T2"]["literal_verdict"], "NOT_REPRODUCED_HIGH", tol="text",
                   source=src_ref(EN, "results/verdict.json", "T2.literal_verdict")))
    oth = sorted(scr[e] for e in "bcd")
    ed.sub("**bf16 escapes on almost the same directions.**", "0g",
           "because the pushed Bellman-Ford/SPFA programs often fail the hidden tests.",
           "because the pushed Bellman-Ford/SPFA programs often fail the hidden tests. At the screen level the shortest "
           f"path verdict is {ver['T2']['screen_level_verdict']} (the artifact's `screen_level_verdict`), beside the "
           f"literal {ver['T2']['literal_verdict']}: W8A8 passes the screen on {scr['a']} of 40 directions against "
           f"{oth[0]} to {oth[-1]} for the other engines, and {excess_fail['a']} (W8A8) and {excess_fail['d']} (bf16) of "
           "40 directions reach the +0.20 excess but fail the pass clause.")
    return {"pn_correct": {"|".join(k): v for k, v in agg.items()}, "screen": scr, "excess_met_pass_failed": excess_fail,
            "verdict_T2": {"literal": ver["T2"]["literal_verdict"], "screen_level": ver["T2"]["screen_level_verdict"]},
            "values": vals + vals2, "discrepancies": disc}
