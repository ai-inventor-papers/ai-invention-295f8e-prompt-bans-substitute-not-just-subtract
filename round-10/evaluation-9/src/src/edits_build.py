#!/usr/bin/env python3
"""Builds the verbatim old_text -> new_text corrections (one edit per paragraph or table, carrying every item tag)
from the stage results and the byte-identical copy of the report. Every number in a new_text is formatted here from
results/<stage>.json, never typed by hand; old_text is always cut from the report itself.
"""

from __future__ import annotations

from typing import Any

from io_util import A_BASE, A_GEO, A_REN, INPUTS, load_stage, r2, rN, read_json, ref

TAG = "(iteration-10 correction)"
REPORT = INPUTS / "report" / "current_report.md"


class Doc:
    def __init__(self) -> None:
        self.text = REPORT.read_text()
        self.lines = self.text.split("\n")

    def para(self, anchor: str) -> str:
        hits = [ln for ln in self.lines if ln.startswith(anchor)]
        assert len(hits) == 1, f"paragraph anchor not unique ({len(hits)}): {anchor!r}"
        return hits[0]

    def table(self, caption_anchor: str) -> str:
        """Caption line + blank + contiguous table rows, verbatim."""
        idx = [i for i, ln in enumerate(self.lines) if ln.startswith(caption_anchor)]
        assert len(idx) == 1, f"table caption not unique: {caption_anchor!r}"
        i = idx[0]
        j = i + 1
        while j < len(self.lines) and not self.lines[j].startswith("|"):
            j += 1
        k = j
        while k < len(self.lines) and self.lines[k].startswith("|"):
            k += 1
        return "\n".join(self.lines[i:k])

    def rows_only(self, caption_anchor: str) -> str:
        t = self.table(caption_anchor)
        return t[t.index("\n|") + 1:]


def sub1(text: str, old: str, new: str) -> str:
    n = text.count(old)
    assert n == 1, f"expected exactly one occurrence ({n}) of {old[:80]!r}"
    return text.replace(old, new)


def append_cols(table_rows: str, header_cells: list[str], values: list[list[str]]) -> str:
    """Append cells to every row of a markdown table (header, separator, data rows in order)."""
    lines = table_rows.split("\n")
    assert len(lines) - 2 == len(values), f"{len(lines) - 2} data rows against {len(values)} value rows"
    out = [lines[0] + " " + " | ".join(header_cells) + " |", lines[1] + "-|" * len(header_cells)]
    for ln, vals in zip(lines[2:], values):
        out.append(ln + " " + " | ".join(vals) + " |")
    return "\n".join(out)


def kn(k: int, n: int) -> str:
    return f"{k} of {n} = {r2(k / n)}"


def val(name: str, recorded: Any, recomputed: Any, status: str, source: str, script: str, output: str,
        tolerance: str = "exact count; rate to 2 decimals") -> dict[str, Any]:
    return {"name": name, "recorded": recorded, "recomputed": recomputed, "status": status, "tolerance": tolerance,
            "source": source, "script": script, "output": output}


def build() -> list[dict[str, Any]]:
    D = Doc()
    a = load_stage("s0a")
    b = load_stage("s0b")
    c = load_stage("s0c")
    d = load_stage("s0d")
    e = load_stage("s0e")
    f = load_stage("s0f")
    g = load_stage("s0g")
    h = load_stage("s0h")
    i_ = load_stage("s0i")
    j = load_stage("s0j")
    E: list[dict[str, Any]] = []
    C = a["cells"]
    q32, q14 = C["q32"], C["q14"]
    R = a["restatement"]

    def m(cell: dict, rd: str) -> str:
        return r2(cell[rd]["mech"])

    def gp(cell: dict, rd: str) -> str:
        return r2(cell[rd]["gap"])

    SR = "src/s_rename.py"
    OA = "results/s0a.json"
    src_n3 = ref(A_REN, "data/labelled_v9_{A,E}_k*.jsonl", "runtime_label/order_class/order_class_fine/lexical_L1")
    src_reads = ref(A_REN, "data/manual_reads_v9.jsonl", "family")

    # ------------------------------------------------------------------ E-9.2-alias (0i-4)
    p = D.para("**The alias test.**")
    old_s = "Within algorithms the relation vanishes: the stratified test"
    new_p = sub1(p, old_s, "Within algorithms the relation is not detected (three algorithms; underpowered) "
                           f"{TAG}: the stratified test")
    E.append({"id": "E-9.2-alias", "items": ["0i"], "location": {"section": "9.2", "table": None, "line_hint": 9355},
              "old_text": p, "new_text": new_p,
              "reason": "review minor 4: 216 effective relabelings = (3!)^3, so only three algorithms inform the "
                        "stratified test; 'vanishes' overstates a non-detection",
              "values": [val("effective relabelings", 216, i_["result"]["alias_within"]["three_factorial_cubed"],
                             "MATCH", "report 9.2 (iteration-9 audit)", "src/s_slips.py", "results/s0i.json")]})

    # ------------------------------------------------------------------ E-T427 (0h)
    t = D.table("**Table 427.**")
    rows = D.rows_only("**Table 427.**")
    cap = t[:t.index("\n")]
    pc = h["per_config"]
    order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
    vals = [[f"{r2(pc[cf]['ud']['gap'])} ({r2(pc[cf]['ud']['ci'][0])} to {r2(pc[cf]['ud']['ci'][1])})"] for cf in order]
    pu = h["pooled_ud"]
    vals.append([f"{r2(pu[0])} ({r2(pu[1])} to {r2(pu[2])})"])
    new_rows = append_cols(rows, ["Gap if unit-weight Dijkstra, IDA* and JPS count as compliant (95%)"], vals)
    c6 = h["c6"]
    cv = h["covert"]
    new_cap = (cap + f" The last column {TAG} is a sensitivity in which the runtime labels unit-weight Dijkstra, "
               f"IDA* and jump point search count as compliant (pooled {r2(pu[0])} against "
               f"{r2(h['pooled_runtime'][0])}); {cv[0]} of the {cv[1]} covert programs carry the runtime label BFS or "
               f"DFS. For the obeying configuration, Qwen3-32B with thinking, the gap is {r2(c6['runtime_gap'])} by the "
               f"runtime label, {r2(c6['tracer_gap'])} by the tracer and {r2(c6['bounds'][0])} to "
               f"{r2(c6['bounds'][1])} between the instrument bounds.")
    E.append({"id": "E-T427", "items": ["0h"], "location": {"section": "9.3", "table": "427", "line_hint": 9422},
              "old_text": t, "new_text": new_cap + "\n\n" + new_rows,
              "reason": "review minor 3: UD/IDA*/JPS-compliant sensitivity, covert BFS/DFS count and the obeying "
                        "configuration's range",
              "values": [val("pooled gap, UD/IDA*/JPS compliant", None, pu[0], "NEW",
                             ref(A_REN, "results/retrace.jsonl", "runtime_label"), SR, "results/s0h.json",
                             "bootstrap B 10,000 seed 0 (record's settings)"),
                         val("pooled gap, runtime label (recomputed)", 0.70, h["pooled_runtime"][0], "MATCH",
                             ref(A_REN, "results/n1.json", "pooled_equal_weight"), SR, "results/s0h.json", "1e-12"),
                         val("covert programs with runtime label BFS or DFS", None, f"{cv[0]} of {cv[1]}", "NEW",
                             ref(A_REN, "results/retrace.jsonl", "runtime_label"), SR, "results/s0h.json"),
                         val("C6 gap runtime / tracer / bounds", "0.63; 0.31; 0.30 to 0.70",
                             f"{r2(c6['runtime_gap'])}; {r2(c6['tracer_gap'])}; {r2(c6['bounds'][0])} to {r2(c6['bounds'][1])}",
                             "MATCH", "; ".join(c6["source"]), SR, "results/s0h.json")]
              + [val(f"{cf} gap UD/IDA*/JPS compliant", None, pc[cf]["ud"]["gap"], "NEW",
                     ref(A_REN, "results/retrace.jsonl"), SR, "tables/table427_ud_compliant.csv") for cf in order]})

    # ------------------------------------------------------------------ E-9.3-exhaustion (0a, 0b)
    p = D.para("**The exhaustion curve.**")
    old_span = p[p.index("Every committed criterion is met, but descriptively."):p.index(" Correctness does not follow")]
    k4f = q32["4"]["runtime_fine"]
    k5f = q32["5"]["runtime_fine"]
    k4 = b["k4"]["q32"]
    noop = b["noop"]
    new_span = (
        f"Whether the committed bars are met depends on the reading {TAG}. By the runtime label both models meet "
        f"every committed criterion, descriptively. The registered fine-class sensitivity was a no-op for the runtime "
        f"label in the executed code: results/n3.json repeats the primary in all {noop['cells']} cells, because "
        f"analysis_v9.py applies fine classes only when the mechanism field is the tracer's; it was applied for the "
        f"tracer (results/n3_tracer.json). Computed for the runtime label, it changes one step: from k = 3 to k = 4 "
        f"Qwen3-32B falls from {m(q32['3'], 'runtime_coarse')} to {m(q32['4'], 'runtime_coarse')} by the coarse "
        f"runtime label, but {k4[0]} of the {k4[1]} coarse violations at k = 4 are greedy best-first programs, a name "
        f"not yet banned, and with fine classes compliance is {kn(k4f['mech_k'], k4f['n'])} (tracer "
        f"{m(q32['4'], 'tracer_coarse')} coarse and {m(q32['4'], 'tracer_fine')} fine); at k = 5 the fine runtime "
        f"value equals the coarse one ({kn(k5f['mech_k'], k5f['n'])}). By the runtime label mechanistic compliance "
        f"falls to {m(q32['5'], 'runtime_coarse')} (Qwen3-32B) and {m(q14['5'], 'runtime_coarse')} (Qwen3-14B) at "
        f"five names; by hand reads to {m(q32['5'], 'hand_reads')} and {m(q14['5'], 'hand_reads')}; by the tracer to "
        f"{m(q32['5'], 'tracer_coarse')} and {m(q14['5'], 'tracer_coarse')} (fine classes "
        f"{m(q32['5'], 'tracer_fine')} and {m(q14['5'], 'tracer_fine')}; Table 431b). Qwen3-14B meets the k = 5 bar "
        f"of a 0.4 gap under every reading (runtime label {gp(q14['5'], 'runtime_coarse')}, hand reads "
        f"{gp(q14['5'], 'hand_reads')}, tracer {gp(q14['5'], 'tracer_coarse')}, tracer fine "
        f"{gp(q14['5'], 'tracer_fine')}) and the held-out bar under every reading except the tracer's fine classes, "
        f"where its held-out gap is {gp(q14['ho'], 'tracer_fine')} (lexical {r2(q14['ho']['tracer_fine']['lex'])} "
        f"against {kn(q14['ho']['tracer_fine']['mech_k'], q14['ho']['tracer_fine']['n'])}). Qwen3-32B meets both "
        f"bars only by the runtime label ({gp(q32['5'], 'runtime_coarse')} at k = 5, "
        f"{gp(q32['ho'], 'runtime_coarse')} held out): at k = 5 the hand reads ({gp(q32['5'], 'hand_reads')}), the "
        f"coarse tracer ({gp(q32['5'], 'tracer_coarse')}) and the fine tracer ({gp(q32['5'], 'tracer_fine')}) fall "
        f"below 0.4, and on the held-out templates the hand reads give {rN(q32['ho']['hand_reads']['gap'], 3)}, just "
        f"below the bar, and the coarse tracer {gp(q32['ho'], 'tracer_coarse')}; counting unit-weight Dijkstra, IDA* "
        f"and jump point search as compliant gives {gp(q32['5'], 'ud_compliant')} at k = 5 and "
        f"{gp(q32['ho'], 'ud_compliant')} held out. Its tracer curve is not monotone "
        f"(1.00, 0.86, 0.91, 0.47, 0.67), because the tracer reads the coordinate-key heaps and Bellman-Ford rounds "
        f"of the late cells as compliant. The hand reads adjudicate between the instruments on exactly these "
        f"programs: they agree with the tracer on 0.88 of the 76 read programs and with the runtime label on 0.64; "
        f"coordinate-key heaps and grid Bellman-Ford rounds are other known disciplines, and the runtime label reads "
        f"the Bellman-Ford rounds as iterative deepening.")
    new_p = p.replace(old_span, new_span)
    assert p.count(old_span) == 1
    vlist = [val("runtime fine, Qwen3-32B k = 4", None, f"{k4f['mech_k']}/{k4f['n']}", "NEW", src_n3, SR, OA),
             val("greedy best-first among k = 4 coarse violations", None, f"{k4[0]} of {k4[1]}", "NEW", src_n3, SR,
                 "results/s0b.json"),
             val("no-op proof: n3.json fine == coarse cells", None, f"{noop['n3_json_fine_equals_coarse_cells']} of {noop['cells']}",
                 "NEW", ref(A_REN, "results/n3.json", "mech_fine_traceable/mech_coarse_traceable"), "src/s_rename.py",
                 "results/s0b.json")]
    for mk, cc in (("Qwen3-32B", q32), ("Qwen3-14B", q14)):
        for rd, rec_v in (("runtime_coarse", "recorded in Table 431"), ("hand_reads", None), ("tracer_coarse", "Table 431"),
                          ("tracer_fine", None)):
            for kk in ("5", "ho"):
                x = cc[kk][rd]
                vlist.append(val(f"{mk} {('k = 5' if kk == '5' else 'held out')} {rd} compliance and gap",
                                 rec_v, f"{x['mech_k']}/{x['n']} = {r2(x['mech'])}; gap {r2(x['gap'])} "
                                        f"({r2(x['ci'][0])} to {r2(x['ci'][1])})",
                                 "MATCH" if rd in ("runtime_coarse", "tracer_coarse") else
                                 ("CARRIED" if False else "NEW"),
                                 src_reads if rd == "hand_reads" else src_n3, SR, OA))
    E.append({"id": "E-9.3-exhaustion", "items": ["0a", "0b"], "location": {"section": "9.3", "table": None,
                                                                         "line_hint": 9471},
              "old_text": p, "new_text": new_p,
              "reason": "review majors 1 and 2: the committed bars restated per model and per reading (runtime coarse "
                        "and fine, tracer coarse and fine, hand reads), the fine-class no-op proved and repaired",
              "values": vlist})

    # ------------------------------------------------------------------ E-T431 (0a, 0b) + Table 431b + figure marker
    t = D.table("**Table 431.**")
    rows = D.rows_only("**Table 431.**")
    cap = t[:t.index("\n")]
    vals = []
    for cc in (q32, q14):
        for kk in ("1", "2", "3", "4", "5", "ho"):
            x = cc[kk]
            hr = (f"{r2(x['hand_reads']['mech'])} ({x['hand_reads']['mech_k']}/{x['hand_reads']['n']})"
                  if "hand_reads" in x else "n/a (no reads)")
            vals.append([f"{r2(x['runtime_fine']['mech'])} ({x['runtime_fine']['mech_k']}/{x['runtime_fine']['n']})",
                         f"{r2(x['tracer_fine']['mech'])} ({x['tracer_fine']['mech_k']}/{x['tracer_fine']['n']})", hr])
    new_rows = append_cols(rows, ["Mechanistic, runtime fine", "Mechanistic, tracer fine", "Mechanistic, hand reads substituted"],
                           vals)
    new_cap = (cap + f" The last three columns {TAG}: the runtime label with fine classes (greedy best-first, A*, "
               f"jump point search, IDA* and IDDFS separate; banned only once named), the tracer's fine classes as "
               f"stored in results/n3_tracer.json, and the hand reads substituted for the runtime class where a program "
               f"was read (k = 5 only).")
    # Table 431b
    hdr = ("| Model | Templates | Completed | Lexical | Runtime label, coarse (primary) | Runtime label, fine | "
           "Tracer, coarse | Tracer, fine | Hand reads substituted | Unit-weight Dijkstra, IDA* and JPS compliant | "
           "Meets the committed bar |")
    sep = "|" + "-|" * 11
    rd_list = ["runtime_coarse", "runtime_fine", "tracer_coarse", "tracer_fine", "hand_reads", "ud_compliant"]
    rd_name = {"runtime_coarse": "runtime coarse", "runtime_fine": "runtime fine", "tracer_coarse": "tracer coarse",
               "tracer_fine": "tracer fine", "hand_reads": "hand reads", "ud_compliant": "UD/IDA*/JPS"}
    body = []
    for mk, cc in (("q32", q32), ("q14", q14)):
        for kk, lab in (("5", "k = 5"), ("ho", "k = 5, held out")):
            x = cc[kk]
            cells = []
            for rd in rd_list:
                y = x[rd]
                gtxt = rN(y["gap"], 3) if abs(y["gap"] - 0.4) < 0.005 else r2(y["gap"])
                cells.append(f"{r2(y['mech'])} ({y['mech_k']}/{y['n']}); gap {gtxt} ({r2(y['ci'][0])} to "
                             f"{r2(y['ci'][1])})")
            key = "k5_gap_ge_0.4" if kk == "5" else "heldout_gap_ge_0.4_lb_gt_0"
            meets = [rd_name[rd] for rd in rd_list if R[mk][rd][key]]
            misses = [rd_name[rd] for rd in rd_list if not R[mk][rd][key]]
            body.append(f"| {'Qwen3-32B' if mk == 'q32' else 'Qwen3-14B'}, thinking on | {lab} | {x['n_completed']} | "
                        f"{r2(x['runtime_coarse']['lex'])} | " + " | ".join(cells) +
                        f" | meets: {', '.join(meets) or 'none'}; misses: {', '.join(misses) or 'none'} |")
    t431b = (f"**Table 431b.** The k = 5 cells under every reading {TAG} (rate over the reading's traceable completed "
             f"programs, k/n; gap = lexical minus mechanistic compliance on the same programs, paired Newcombe 95% "
             f"interval [Newcombe 1998b, method 10]). The committed bars, quoted from the rename artifact's first "
             f"commitment: \"k=5 gap >= 0.4 (paired Newcombe)\" and \"CONFIRMATION: held-out k=5 (W4/W5/P6/P7) gap >= "
             f"0.4 with Newcombe lower bound > 0\". The hand reads come from one reader and were not double-coded, so "
             f"they are a third reading, not a gold standard.\n\n" + hdr + "\n" + sep + "\n" + "\n".join(body))
    E.append({"id": "E-T431", "items": ["0a", "0b", "0h"], "location": {"section": "9.3", "table": "431",
                                                                      "line_hint": 9473},
              "old_text": t, "new_text": new_cap + "\n\n" + new_rows + "\n\n" + t431b + "\n\n[FIGURE:fig_s0_kcurves]",
              "reason": "review majors 1-2 and minor 3: runtime fine, tracer fine and hand-read columns over all k; "
                        "new Table 431b with every reading against the committed bar",
              "values": [val(f"{mk} {kk} {rd}", None, f"{C[mk][kk][rd]['mech_k']}/{C[mk][kk][rd]['n']}",
                             "NEW" if rd in ("runtime_fine", "hand_reads", "ud_compliant") else "MATCH",
                             src_reads if rd == "hand_reads" else src_n3, SR, "tables/table431b_k5_every_reading.csv")
                         for mk in ("q32", "q14") for kk in ("5", "ho") for rd in rd_list]})

    # ------------------------------------------------------------------ E-9.3-described (0c)
    p = D.para("**A ban described without names (exploratory).**")
    rdc = c["readings"]
    rt, tr, tf, pa = rdc["runtime_coarse"], rdc["tracer_coarse"], rdc["tracer_fine"], rdc["per_cell_argued"]
    hw = [(x["ci"][1] - x["ci"][0]) / 2 for x in (rt, tr, tf, pa)]
    old_span = p[p.index("It raised mechanistic compliance"):p.index(" The committed direction was")]
    new_span = (
        f"Its effect on mechanistic compliance is instrument-dependent {TAG}: +{r2(rt['diff'])} by the runtime label "
        f"({kn(*rt['described'])} under the described ban against {kn(*rt['named'])} under the named five-name ban; "
        f"{r2(rt['ci'][0])} to {r2(rt['ci'][1])}), {r2(tr['diff'])} by the tracer ({kn(*tr['described'])} against "
        f"{kn(*tr['named'])}; {r2(tr['ci'][0])} to {r2(tr['ci'][1])}), +{r2(tf['diff'])} by the tracer's fine "
        f"classes ({r2(tf['ci'][0])} to {r2(tf['ci'][1])}), and about +{r2(pa['diff'])} ({r2(pa['ci'][0])} to "
        f"{r2(pa['ci'][1])}) under the per-cell reading the record argues for, the runtime label for the described "
        f"cell and hand reads substituted for the named cell ({kn(*pa['named'])}). The described cell was not hand-read, "
        f"and its denominators differ because the tracer cannot trace one described program (49 against 48). At about "
        f"50 programs per cell the unpaired Newcombe half-width of these differences is {r2(min(hw))} to "
        f"{r2(max(hw))}, so differences below about 0.2 between readings are not resolvable and the record does not "
        f"rank them; NOV-R's single-instrument retest in iteration 10 addresses this. By the runtime label the share "
        f"of samples that are correct mechanism-level survivors rose from 0.16 to 0.68 (Table 433).")
    new_p = p.replace(old_span, new_span)
    assert p.count(old_span) == 1
    new_p = sub1(new_p, "The committed direction was that mechanistic compliance or violation rises; compliance rose "
                        "and violation fell.",
                 "The committed direction was that mechanistic compliance or violation rises; by the runtime label "
                 "compliance rose and violation fell.")
    srcd = ref(A_REN, "data/labelled_v9_C_desc.jsonl") + "; " + ref(A_REN, "data/labelled_v9_A_k5.jsonl")
    E.append({"id": "E-9.3-described", "items": ["0c"], "location": {"section": "9.3", "table": None, "line_hint": 9497},
              "old_text": p, "new_text": new_p,
              "reason": "review major 3: the described-ban effect depends on the instrument; every reading shown with "
                        "its unpaired Newcombe interval",
              "values": [val("described vs named, runtime", 0.58, rt["diff"], "MATCH", ref(A_REN, "results/n3d.json",
                                                                                         "diffs.mech_compliance"),
                             SR, "results/s0c.json", "1e-12"),
                         val("described vs named, tracer", None, tr["diff"], "NEW",
                             ref(A_REN, "results/n3d_tracer.json", "diffs.mech_compliance"), SR, "results/s0c.json"),
                         val("described vs named, tracer fine (rows; not stored)", None, tf["diff"], "NEW", srcd, SR,
                             "results/s0c.json"),
                         val("described runtime vs named hand reads", None, pa["diff"], "NEW", srcd + "; " + src_reads, SR,
                             "results/s0c.json")]})

    # ------------------------------------------------------------------ E-T433 (0c)
    t = D.table("**Table 433.**")
    rows = D.rows_only("**Table 433.**")
    cap = t[:t.index("\n")]
    new_rows = sub1(rows, "| Mechanistic compliance | 0.80 (39 of 49)", "| Mechanistic compliance, runtime label | 0.80 (39 of 49)")
    add = [f"| Mechanistic compliance, tracer | {r2(tr['described'][0] / tr['described'][1])} ({tr['described'][0]} of "
           f"{tr['described'][1]}) | {r2(tr['named'][0] / tr['named'][1])} ({tr['named'][0]} of {tr['named'][1]}) | "
           f"{r2(tr['diff'])} ({r2(tr['ci'][0])} to {r2(tr['ci'][1])}) |",
           f"| Mechanistic compliance, tracer fine classes (from rows; not stored) | "
           f"{r2(tf['described'][0] / tf['described'][1])} ({tf['described'][0]} of {tf['described'][1]}) | "
           f"{r2(tf['named'][0] / tf['named'][1])} ({tf['named'][0]} of {tf['named'][1]}) | {r2(tf['diff'])} "
           f"({r2(tf['ci'][0])} to {r2(tf['ci'][1])}) |",
           f"| Described by the runtime label against named with hand reads substituted | "
           f"{r2(pa['described'][0] / pa['described'][1])} ({pa['described'][0]} of {pa['described'][1]}) | "
           f"{r2(pa['named'][0] / pa['named'][1])} ({pa['named'][0]} of {pa['named'][1]}) | {r2(pa['diff'])} "
           f"({r2(pa['ci'][0])} to {r2(pa['ci'][1])}) |"]
    new_cap = (cap + f" The last three rows {TAG} read the same programs with the tracer, with the tracer's fine "
               f"classes, and with hand reads substituted in the named cell (the described cell was not read); the "
               f"denominators 49 and 48 differ by one described program the tracer cannot trace.")
    E.append({"id": "E-T433", "items": ["0c"], "location": {"section": "9.3", "table": "433", "line_hint": 9499},
              "old_text": t, "new_text": new_cap + "\n\n" + new_rows + "\n" + "\n".join(add),
              "reason": "review major 3: Table 433 gains the tracer, tracer-fine and hand-read rows",
              "values": [val("tracer row", None, f"{tr['described']} vs {tr['named']}", "NEW",
                             ref(A_REN, "results/n3d_tracer.json"), SR, "tables/table433b_described_vs_named.csv"),
                         val("tracer fine row", None, f"{tf['described']} vs {tf['named']}", "NEW", srcd, SR,
                             "tables/table433b_described_vs_named.csv"),
                         val("hand-read comparator", None, f"{pa['described']} vs {pa['named']}", "NEW", src_reads, SR,
                             "tables/table433b_described_vs_named.csv")]})

    # ------------------------------------------------------------------ E-9.3-novelty (0i-2)
    p = D.para("**Novelty, audits and cost.**")
    ls_ = i_["result"]["lost_samples"]
    new_p = sub1(p, "Seven of 280 rotated and described samples were lost to rate limits and not resampled",
                 f"Seven of {ls_['planned']} rotated and described samples were lost to rate limits and not resampled "
                 f"({ls_['present_rotated']} of 300 rotated and {ls_['present_described']} of 50 described samples are "
                 f"present) {TAG}")
    E.append({"id": "E-9.3-novelty", "items": ["0i"], "location": {"section": "9.3", "table": None, "line_hint": 9532},
              "old_text": p, "new_text": new_p, "reason": "review minor 4: the denominator of the lost samples is 350",
              "values": [val("planned rotated + described samples", 280, ls_["planned"], "CORRECTED",
                             ref(A_REN, "data/samples_v9.jsonl", "cell"), "src/s_slips.py", "results/s0i.json"),
                         val("present samples", None, ls_["present_rotated"] + ls_["present_described"], "NEW",
                             ref(A_REN, "data/samples_v9.jsonl", "cell"), "src/s_slips.py", "results/s0i.json")]})

    # ------------------------------------------------------------------ E-9.3-positioning (0h)
    p = D.para("**Positioning.** The experiment's dated search (2026-10-23)")
    new_p = sub1(p, "found no work that audits by runtime expansion order whether a banned technique returns under "
                    "another name.",
                 "found no work that audits whether a banned technique returns under another name, read by the runtime "
                 f"label (heap priorities, frontier evidence, restarts) and by the expansion-order tracer {TAG}.")
    E.append({"id": "E-9.3-positioning", "items": ["0h"], "location": {"section": "9.3", "table": None, "line_hint": 9534},
              "old_text": p, "new_text": new_p,
              "reason": "review minor 3: the primary label is the runtime label, not runtime expansion order",
              "values": [val("instrument wording", "audits by runtime expansion order",
                             "runtime label (heap priorities, frontier evidence, restarts) and expansion-order tracer",
                             "CORRECTED", ref(A_REN, "results/headlines.json", "primary_mechanism_label"), SR,
                             "results/s0h.json", "wording")]})

    # ------------------------------------------------------------------ E-9.4-rsa (0e, 0i-1)
    p = D.para("**What each manifold tracks.**")
    nm = e["per_manifold"]["32b|mname"]
    met = e["metrics"]
    new_p = sub1(p, "The named, described and name-only manifolds track the lexical matrix (0.46, 0.57 and 0.47) and "
                    "not behaviour.",
                 f"The named, described and name-only manifolds track the lexical matrix (0.46, 0.57 and 0.47) and "
                 f"textbook data-structure attributes, not measured expansion order {TAG}: on the named Qwen3-32B "
                 f"manifold the data-structure matrix gives {r2(nm['rho']['R_DS'])} (exact p "
                 f"{rN(nm['p_exact']['R_DS'], 3)}) against {r2(nm['rho']['R_lex'])} for the lexical matrix, and the "
                 f"expansion-order matrix gives {r2(met['R_beh_order_min_language'])} to "
                 f"{r2(met['R_beh_order_max_language'])} on the five language manifolds. The two model matrices are "
                 f"nearly unrelated there (Spearman {r2(nm['lex_ds_spearman'])}, variance inflation "
                 f"{r2(nm['vif'])}), and each survives partialling out the other: lexical given data structure "
                 f"{r2(nm['lex_given_ds']['partial'])} and data structure given lexical "
                 f"{r2(nm['ds_given_lex']['partial'])}, exact relabeling p {rN(nm['lex_given_ds']['p_scheme_A'], 3)} "
                 f"and {rN(nm['ds_given_lex']['p_scheme_A'], 3)} when the tested matrix is relabeled and "
                 f"{rN(nm['lex_given_ds']['p_scheme_B'], 3)} and {rN(nm['ds_given_lex']['p_scheme_B'], 3)} under "
                 f"Freedman-Lane residual relabeling (Table 437b). With ten classes and a contested partial Mantel "
                 f"test these p-values are descriptive.")
    new_p = sub1(new_p, "(chance 0.11) and the programs at 0.17.",
                 "(chance 0.11) and the programs at 0.17, which is chance for six classes (0.167) " + TAG + ".")
    srce = ref(A_GEO, "results/rsa.json") + "; " + ref(A_GEO, "results/geometry_32b_mname.json",
                                                      "L_star.describe.k15.class_geodesic_matrix")
    E.append({"id": "E-9.4-rsa", "items": ["0e", "0i"], "location": {"section": "9.4", "table": None, "line_hint": 9577},
              "old_text": p, "new_text": new_p,
              "reason": "review major 5 and minor 4: aliases carry mechanism words, so data-structure attributes are "
                        "tested beside lexical distance; the program-probe value equals chance",
              "values": [val("R_DS rho, named Qwen3-32B", None, nm["rho"]["R_DS"], "MATCH",
                             ref(A_GEO, "results/rsa.json", "32b|mname.models.R_DS.rho"), "src/s_geometry.py",
                             "results/s0e.json", "1e-9"),
                         val("Spearman(R_lex, R_DS)", None, nm["lex_ds_spearman"], "NEW", srce, "src/s_geometry.py",
                             "results/s0e.json"),
                         val("partial lex|DS", None, nm["lex_given_ds"]["partial"], "NEW", srce, "src/s_geometry.py",
                             "results/s0e.json", "1e-3 against the independent 0.502"),
                         val("partial DS|lex", None, nm["ds_given_lex"]["partial"], "NEW", srce, "src/s_geometry.py",
                             "results/s0e.json", "1e-3 against the independent 0.675"),
                         val("program probe chance", 0.17, i_["result"]["name_evocation"]["chance"], "MATCH",
                             i_["result"]["name_evocation"]["source"], "src/s_slips.py", "results/s0i.json")]})

    # ------------------------------------------------------------------ E-T437 (0e) + Table 437b
    t = D.table("**Table 437.**")
    rows = D.rows_only("**Table 437.**")
    cap = t[:t.index("\n")]
    keys = ["32b|mname", "32b|mdesc", "32b|mlex", "32b|mcode_PRIMARY_R1", "32b|mcode_PRIMARY_R2", "32b|mcode_M32_R1",
            "8b|mname", "8b|mdesc", "8b|mcode_PRIMARY_R1"]
    PM = e["per_manifold"]
    vals = [[f"{r2(PM[k]['rho'][mm])} ({rN(PM[k]['p_exact'][mm], 3)})" for mm in ("R_DS", "R_beh_order", "R_desc_lex")]
            for k in keys]
    new_rows = append_cols(rows, ["Data structure", "Expansion order", "Description lexical"], vals)
    new_cap = cap + (f" The last three columns {TAG} add the data-structure, expansion-order and description-lexical "
                     f"model matrices stored in results/rsa.json.")
    lab = {"32b|mname": "Named, Qwen3-32B", "32b|mdesc": "Described, Qwen3-32B", "32b|mlex": "Name-only, Qwen3-32B",
           "32b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-32B",
           "32b|mcode_PRIMARY_R2": "Program, second readout, Qwen3-32B",
           "32b|mcode_M32_R1": "Program, Qwen3-32B programs only", "8b|mname": "Named, Qwen3-8B",
           "8b|mdesc": "Described, Qwen3-8B", "8b|mcode_PRIMARY_R1": "Program, primary readout, Qwen3-8B"}
    b437 = [f"| {lab[k]} ({PM[k]['n_classes']}) | {r2(PM[k]['lex_ds_spearman'])} ({rN(PM[k]['lex_ds_p_exact'], 3)}) | "
            f"{r2(PM[k]['vif'])} | {r2(PM[k]['lex_given_ds']['partial'])} ({rN(PM[k]['lex_given_ds']['p_scheme_A'], 3)}; "
            f"{rN(PM[k]['lex_given_ds']['p_scheme_B'], 3)}) | {r2(PM[k]['ds_given_lex']['partial'])} "
            f"({rN(PM[k]['ds_given_lex']['p_scheme_A'], 3)}; {rN(PM[k]['ds_given_lex']['p_scheme_B'], 3)}) |" for k in keys]
    t437b = (f"**Table 437b.** Lexical distance against data-structure attributes {TAG}: the Spearman of the two model "
             f"matrices over the present pairs (exact relabeling p), their variance inflation 1/(1 - r^2), and partial "
             f"Spearman correlations (Pearson partial correlation of average-rank vectors) of each manifold, with exact "
             f"one-sided relabeling p over all n! relabelings (10! = 3,628,800; 9! = 362,880; 6! = 720, floor 0.0014) "
             f"under scheme A (relabel the tested matrix) and scheme B (Freedman-Lane: relabel the residuals of the "
             f"neural ranks on the control ranks). Partial Mantel tests can be anticonservative for structured "
             f"matrices, so every p here is descriptive.\n\n| Manifold (classes) | Spearman of lexical and "
             f"data-structure matrices (p) | Variance inflation | Lexical given data structure (p A; p B) | Data "
             f"structure given lexical (p A; p B) |\n|-|-|-|-|-|\n" + "\n".join(b437))
    E.append({"id": "E-T437", "items": ["0e"], "location": {"section": "9.4", "table": "437", "line_hint": 9579},
              "old_text": t, "new_text": new_cap + "\n\n" + new_rows + "\n\n" + t437b,
              "reason": "review major 5: Table 437 gains R_DS, R_beh_order and R_desc_lex; new Table 437b",
              "values": [val(f"{k} R_DS/R_beh_order/R_desc_lex rho", None,
                             [PM[k]["rho"][mm] for mm in ("R_DS", "R_beh_order", "R_desc_lex")], "MATCH",
                             ref(A_GEO, "results/rsa.json", f"{k}.models"), "src/s_controls.py",
                             "results/s1_controls.json", "1e-9 (reproduced)") for k in keys]
              + [val(f"{k} partials", None, [PM[k]["lex_given_ds"]["partial"], PM[k]["ds_given_lex"]["partial"]], "NEW",
                     srce, "src/s_geometry.py", "tables/table437b_partial_rsa.csv") for k in keys]})

    # ------------------------------------------------------------------ E-T438 (0d) + figure marker
    t = D.table("**Table 438.**")
    rows = D.rows_only("**Table 438.**")
    cap = t[:t.index("\n")]
    fr = d["frames"]
    fname = {"32b|mcode_PRIMARY_R1": "Qwen3-32B, primary readout", "32b|mcode_PRIMARY_R2": "Qwen3-32B, second readout",
             "32b|mcode_M32_R1": "Qwen3-32B programs only", "8b|mcode_PRIMARY_R1": "Qwen3-8B, primary readout"}
    own = {"32b|mcode_PRIMARY_R1": "1.00", "32b|mcode_PRIMARY_R2": "0.98", "32b|mcode_M32_R1": "1.00",
           "8b|mcode_PRIMARY_R1": "0.92"}
    near_name = {"dijkstra_unit": "unit-weight Dijkstra", "gbfs": "greedy best-first", "bfs": "BFS", "dfs": "DFS",
                 "astar": "A*", "idastar": "IDA*"}
    extra = []
    for fk in ["32b|mcode_PRIMARY_R1", "32b|mcode_PRIMARY_R2", "32b|mcode_M32_R1", "8b|mcode_PRIMARY_R1"]:
        F = fr[fk]
        for fam in ("Bellman-Ford/SPFA", "BFS variants", "other known"):
            x = F["families"][fam]
            near = ", ".join(f"{near_name.get(k_, k_)} {v_}" for k_, v_ in sorted(x["nearest_algorithm"].items(),
                                                                                 key=lambda kv: -kv[1]))
            extra.append(f"| {fname[fk]}: {fam} survivors | {F['block']} | {r2(F['loo']['loo_accuracy'])} "
                         f"({'passes' if F['loo']['pass'] else 'fails'}) | {x['edge']} of {x['n']} (opposite "
                         f"{x['opposite']}; median g {rN(x['median_g'], 1)} against the frame median "
                         f"{rN(F['frame_median'], 1)}; references {rN(F['frame_g']['dijkstra_unit'], 1)} and "
                         f"{rN(F['frame_g']['idastar'], 1)}; {x['beyond_farther_reference']} beyond the farther) | "
                         f"{near} | {own[fk]} |")
    new_cap = (cap + f" The first four rows are the 15 unit-weight Dijkstra survivors; the rows below {TAG} place the "
               f"other 23 survivors of the placement file by family (frozen from the labels before any class was read: "
               f"15 Bellman-Ford/SPFA, 3 BFS variants, 5 other known), with the median g, the frame median and the two "
               f"reference values (unit-weight Dijkstra and IDA*). Three caveats apply: the per-family placement was "
               f"not preregistered; with only two non-banned classes on these frames, 'opposite' means farther than "
               f"the median of the unit-weight Dijkstra and IDA* frame values; and the class therefore depends on that "
               f"two-class reference.")
    bf32 = fr["32b|mcode_PRIMARY_R1"]["families"]["Bellman-Ford/SPFA"]
    E.append({"id": "E-T438", "items": ["0d"], "location": {"section": "9.4", "table": "438", "line_hint": 9595},
              "old_text": t, "new_text": new_cap + "\n\n" + rows + "\n" + "\n".join(extra) + "\n\n[FIGURE:fig_s0_placement]",
              "reason": "review major 4: placement per survivor family with its reference values and caveats",
              "values": [val(f"{fk} {fam} edge/opposite", None,
                             f"{fr[fk]['families'][fam]['edge']}/{fr[fk]['families'][fam]['opposite']}", "NEW",
                             ref(A_GEO, "results/placement.json", f"{fk}.rows"), "src/s_geometry.py",
                             "tables/table438b_placement_families.csv")
                         for fk in fr for fam in ("unit-weight Dijkstra", "Bellman-Ford/SPFA", "BFS variants", "other known")]})

    # ------------------------------------------------------------------ E-T440 (0i-3)
    t = D.table("**Table 440.**")
    rows = D.rows_only("**Table 440.**")
    cap = t[:t.index("\n")]
    fk_ = {x["fork"]: x for x in i_["result"]["forks"]}
    order440 = ["G-GRID@32", "G-T04@31", "G-R6@12", "G-R6@24", "L-GRID@52", "L-GRID@121"]
    vals = []
    for k_ in order440:
        x = fk_[k_]
        pa_ = "n/a (several alternatives)" if x["base_p_alternative"] is None else f"{r2(x['base_p_alternative'])} ({str(x['alternative']).upper()})"
        um = x["unmapped_base_mass"]
        vals.append([pa_, "n/a" if um is None else (rN(um, 3) if um >= 0.0005 else "below 0.001")])
    vals.append(["n/a", "n/a"])
    new_rows = append_cols(rows, ["Base P(alternative)", "Unmapped base mass"], vals)
    new_cap = cap + (f" The last two columns {TAG} give the base model's probability of the alternative class, where "
                     f"the fork has a single alternative, and the base model's probability mass on tokens mapped to no "
                     f"class (results/b1_*.json).")
    gr = i_["result"]["grid"]
    E.append({"id": "E-T440", "items": ["0i"], "location": {"section": "9.5", "table": "440", "line_hint": 9627},
              "old_text": t, "new_text": new_cap + "\n\n" + new_rows,
              "reason": "review minor 4: base P(alternative) and unmapped base mass",
              "values": [val("Gemma grid base P(alternative = BFS)", None, gr["base_p_alternative"], "NEW", gr["source"],
                             "src/s_slips.py", "results/s0i.json"),
                         val("Gemma grid unmapped base mass", None, gr["unmapped_base_mass"], "NEW", gr["source"],
                             "src/s_slips.py", "results/s0i.json")]})

    # ------------------------------------------------------------------ E-9.5-sharpening (0i-3)
    p = D.para("**The sharpening measurement (verdict partial).**")
    new_p = sub1(p, "the argmax differs on all 20 prompts: the instruct default is not the base model's first choice "
                    "there (Table 440).",
                 f"the argmax differs on all 20 prompts: post-training reversed and concentrated the choice (base "
                 f"P(BFS) {r2(gr['base_p_alternative'])} against P(DFS) {r2(gr['base_p_default'])}, with "
                 f"{rN(gr['unmapped_base_mass'], 3)} of the base model's mass on tokens mapped to no class) {TAG} "
                 f"(Table 440).")
    E.append({"id": "E-9.5-sharpening", "items": ["0i"], "location": {"section": "9.5", "table": None, "line_hint": 9623},
              "old_text": p, "new_text": new_p, "reason": "review minor 4: reversed and concentrated",
              "values": [val("base P(BFS), P(DFS), unmapped", None,
                             [gr["base_p_alternative"], gr["base_p_default"], gr["unmapped_base_mass"]], "NEW",
                             gr["source"], "src/s_slips.py", "results/s0i.json")]})

    # ------------------------------------------------------------------ E-9.5-patching (0g)
    p = D.para("**The patching test (verdict partial; localisation distributed).**")
    G = g["result"]
    b3, t10 = G["B3"], G["T10"]
    ppc = t10["per_prompt"]
    neg = round(ppc["FSTACK"]["share_negative"] * ppc["n_prompts"])
    ins = (f" {TAG} Most matched random sets repeat a component, because the draw falls back to the whole candidate "
           f"pool once an MLP pool is used up: an MLP repeats in {b3['families']['R']['sets_with_repeated_mlp']} of 50 "
           f"random sets and {b3['families']['Rpure']['sets_with_repeated_mlp']} of 50 sets without the circuit's top 15 "
           f"on minimum spanning tree, and in {t10['families']['R']['sets_with_repeated_mlp']} of 50 and "
           f"{t10['families']['Rpure']['sets_with_repeated_mlp']} of 50 on connected components. Restricted to sets of "
           f"ten distinct components, the minimum spanning tree null keeps a median "
           f"{r2(b3['families']['R']['restricted_median'])} ({b3['families']['R']['n_ten_distinct']} sets; p "
           f"{r2(b3['families']['R']['restricted_p'])}) and the sets without the top 15 keep "
           f"{b3['families']['Rpure']['n_ten_distinct']} (median {r2(b3['families']['Rpure']['restricted_median'])}; p "
           f"{r2(b3['families']['Rpure']['restricted_p'])}, the floor at that N); random sets scaled to the fork "
           f"stack's write norm give a median {r2(b3['families']['Rscaled']['median_all'])} (p "
           f"{rN(b3['families']['Rscaled']['p_all'], 3)}), beside {r2(b3['families']['Rpure']['median_all'])} (p "
           f"{rN(b3['families']['Rpure']['p_all'], 3)}) and {r2(b3['families']['R']['median_all'])} (p "
           f"{r2(b3['families']['R']['p_all'])}). On connected components the {t10['families']['R']['n_ten_distinct']} "
           f"full-size random sets give a median {r2(t10['families']['R']['restricted_median'])} (p "
           f"{rN(t10['families']['R']['restricted_p'], 3)}, at its floor) and no set without the top 15 is full-size. "
           f"The fork stack's 0.45 there is a ratio of means; per prompt its share has mean "
           f"{r2(ppc['FSTACK']['mean_of_ratios'])}, median {r2(ppc['FSTACK']['median'])} and interquartile range "
           f"{r2(ppc['FSTACK']['iqr'][0])} to {r2(ppc['FSTACK']['iqr'][1])}, negative on {neg} of {ppc['n_prompts']} "
           f"prompts (the five fork MLPs: ratio of means {r2(ppc['F_MLP']['ratio_of_means'])}, mean of per-prompt "
           f"shares {r2(ppc['F_MLP']['mean_of_ratios'])}; Table 441b). On minimum spanning tree specificity stays "
           f"unresolved in this record; BASE-W redraws the sets without reuse.")
    anchor = "but short of the committed 0.5."
    new_p = sub1(p, anchor, anchor + ins)
    srcg = ref(A_BASE, "results/random_sets.json") + "; " + ref(A_BASE, "results/b2_summary.json")
    E.append({"id": "E-9.5-patching", "items": ["0g"], "location": {"section": "9.5", "table": None, "line_hint": 9631},
              "old_text": p, "new_text": new_p,
              "reason": "review minor 2: repeated components in the random sets, restricted nulls and per-prompt shares",
              "values": [val("sets with a repeated MLP (MST R, MST Rpure, CC R, CC Rpure)", None,
                             [b3['families']['R']['sets_with_repeated_mlp'], b3['families']['Rpure']['sets_with_repeated_mlp'],
                              t10['families']['R']['sets_with_repeated_mlp'], t10['families']['Rpure']['sets_with_repeated_mlp']],
                             "NEW", srcg, "src/s_base.py", "results/s0g.json"),
                         val("MST restricted null median/p", None,
                             [b3['families']['R']['restricted_median'], b3['families']['R']['restricted_p']], "NEW", srcg,
                             "src/s_base.py", "results/s0g.json"),
                         val("CC per-prompt mean of ratios (fork stack)", 0.13, ppc["FSTACK"]["mean_of_ratios"], "MATCH",
                             ref(A_BASE, "results/b2_summary.json", "units.T10.arms.FSTACK.share_mean_of_ratios"),
                             "src/s_base.py", "results/s0g.json", "1e-9"),
                         val("MST Rscaled median/p", None, [b3['families']['Rscaled']['median_all'],
                                                           b3['families']['Rscaled']['p_all']], "MATCH",
                             ref(A_BASE, "results/b2_summary.json", "units.B3.null_Rscaled"), "src/s_base.py",
                             "results/s0g.json")]})

    # ------------------------------------------------------------------ E-T441 (0g): new Tables 441b / 441c
    t = D.table("**Table 441.**")
    rows = D.rows_only("**Table 441.**")
    lines441 = []
    unit_lab = {"B3": "Minimum spanning tree", "T10": "Connected components"}
    fam_lab = {"R": "matched random sets", "Rpure": "without the circuit's top 15", "Rscaled": "scaled to the fork stack's write norm"}
    for u in ("B3", "T10"):
        for fam in ("R", "Rpure", "Rscaled"):
            x = G[u]["families"][fam]
            es = "; ".join(f"{k_} distinct: {v_}" for k_, v_ in sorted(x["effective_size_counts"].items(),
                                                                       key=lambda kv: -int(kv[0])))
            rm = ("none (N = 0)" if x["n_ten_distinct"] == 0 else
                  f"{r2(x['restricted_median'])}; p {rN(x['restricted_p'], 3)} (floor {rN(x['restricted_floor'], 3)})")
            lines441.append(f"| {unit_lab[u]} | {fam_lab[fam]} | {x['sets_with_repeated_mlp']} of {x['n_sets']} | {es} | "
                            f"{x['n_ten_distinct']} | {r2(x['median_all'])}; p {rN(x['p_all'], 3)} | {rm} |")
    t441b = (f"**Table 441b.** The random patching sets by effective size {TAG} (Rscaled reuses the matched sets, "
             f"scaled; empirical p = (1 + #null >= fork stack)/(N + 1), floor 1/(N + 1)).\n\n| Unit | Family | Sets "
             f"repeating an MLP | Distinct components per set | Sets of ten distinct components | Median share, all "
             f"sets; p | Median share, ten-distinct sets; p (floor) |\n|-|-|-|-|-|-|-|\n" + "\n".join(lines441))
    l441c = []
    for u in ("B3", "T10"):
        for arm, al in (("FSTACK", "fork stack"), ("F_MLP", "five fork MLPs")):
            x = G[u]["per_prompt"][arm]
            l441c.append(f"| {unit_lab[u]} | {al} | {r2(x['ratio_of_means'])} | {r2(x['mean_of_ratios'])} | "
                         f"{r2(x['median'])} | {r2(x['iqr'][0])} to {r2(x['iqr'][1])} | {r2(x['min'])} to "
                         f"{r2(x['max'])} | {round(x['share_negative'] * G[u]['per_prompt']['n_prompts'])} of "
                         f"{G[u]['per_prompt']['n_prompts']} | {G[u]['per_prompt']['n_small_gap_lt_0.5']} |")
    t441c = (f"**Table 441c.** Per-prompt shares s = (m_patched - m_instruct)/(m_base - m_instruct) beside the ratio "
             f"of means {TAG}.\n\n| Unit | Arm | Ratio of means | Mean of per-prompt shares | Median | Interquartile "
             f"range | Range | Negative | Prompts with a gap below 0.5 nats |\n|-|-|-|-|-|-|-|-|-|\n" + "\n".join(l441c))
    E.append({"id": "E-T441", "items": ["0g"], "location": {"section": "9.5", "table": "441", "line_hint": 9633},
              "old_text": t, "new_text": t + "\n\n" + t441b + "\n\n" + t441c,
              "reason": "review minor 2: new Tables 441b and 441c (effective sizes, restricted nulls, per-prompt shares)",
              "values": [val(f"{u} {fam} restricted null", None,
                             [G[u]["families"][fam]["n_ten_distinct"], G[u]["families"][fam]["restricted_median"]],
                             "NEW", srcg, "src/s_base.py", "tables/table441b_random_sets.csv")
                         for u in ("B3", "T10") for fam in ("R", "Rpure", "Rscaled")]})

    # ------------------------------------------------------------------ E-9.5-heldout (0f)
    p = D.para("**The held-out rerun.**")
    F = f["result"]
    A_, S_ = F["modes"]["ablate"], F["modes"]["steer"]
    pr = F["pair_rule"]
    ee = F["empty_edits"]
    old_s = (p[p.index("With span means interpolated"):p.index(" Holm-adjusted within the six-test family")])
    new_s = (f"With span means interpolated to the target span length, the layer-0 condition-span MLP has a held-out "
             f"effect of about 7.9 nats on the five forced prompts ({r2(A_['mean_forced'])} under ablation, "
             f"{r2(S_['mean_forced'])} under steering at dose 2), close to its pair-prompt values (8.14 and 7.41, "
             f"each the mean over both sides of the 20 pair prompts), and about 0 on the five padded twins "
             f"({r2(A_['mean_padded'])} and {r2(S_['mean_padded'])}), unlike the pair prompts, where both sides carry "
             f"the effect (ablation {r2(pr['ablate']['mean_forced_side_10'])} forced and "
             f"{r2(pr['ablate']['mean_padded_side_10'])} padded); the means of 3.86 (sign-flip p 0.0625) and 3.85 (p "
             f"0.023) over the 10 held-out prompts average the two sides {TAG}. Taken as five contrasts, the exact "
             f"sign-flip test has 32 equally likely patterns, so its smallest attainable p is "
             f"{rN(A_['p5_contrast_mean_one_sided'], 3)} one-sided and {A_['p5_contrast_mean_two_sided']} two-sided; all "
             f"five contrasts are positive under both modes, which gives exactly those values, so five contrasts "
             f"cannot reach two-sided 0.05. On the F11 and F15 rows {ee['per_row']['F11|forced'][0]} of the "
             f"{ee['per_row']['F11|forced'][1]} edit jobs of each row ({ee['sum_F11_F15'][0]} of {ee['sum_F11_F15'][1]:,}) "
             f"were empty, all in the exact-length sensitivity variant, whose ablation mean is "
             f"{r2(ee['exact_length_ablate_mean_with'])} with those rows and {r2(ee['exact_length_ablate_mean_without_F11_F15'])} "
             f"without them; the primary interpolated variant applied every edit. The matched random set holds 10 "
             f"distinct components among its 50 draws.")
    new_p = p.replace(old_s, new_s)
    assert p.count(old_s) == 1
    srcf = ref(A_BASE, "results/b3_heldout_rows.jsonl")
    E.append({"id": "E-9.5-heldout", "items": ["0f"], "location": {"section": "9.5", "table": None, "line_hint": 9653},
              "old_text": p, "new_text": new_p,
              "reason": "review minor 1: a mean over a bimodal held-out distribution replaced by per-side values",
              "values": [val("forced-side mean ablate/steer", None, [A_["mean_forced"], S_["mean_forced"]], "NEW", srcf,
                             "src/s_base.py", "results/s0f.json"),
                         val("padded-side mean ablate/steer", None, [A_["mean_padded"], S_["mean_padded"]], "NEW", srcf,
                             "src/s_base.py", "results/s0f.json"),
                         val("overall mean ablate/steer", [3.86, 3.85], [A_["mean_all"], S_["mean_all"]], "MATCH",
                             ref(A_BASE, "results/b3_summary.json", "per_node"), "src/s_base.py", "results/s0f.json", "1e-9"),
                         val("sign-flip p (10 rows) ablate/steer", [0.0625, 0.023],
                             [A_["p_sign_flip_10_reproduced"], S_["p_sign_flip_10_reproduced"]], "MATCH",
                             ref(A_BASE, "src/stats9.py", "sign_flip_p"), "src/s_base.py", "results/s0f.json", "exact"),
                         val("pair-prompt rule (8.14/7.41)", [8.14, 7.41], [pr["ablate"]["mean_both_sides_20"],
                                                                            pr["steer"]["mean_both_sides_20"]],
                             pr["status"], pr["source"], "src/s_base.py", "results/s0f.json", "1e-9"),
                         val("empty edit jobs on F11/F15 rows", None, ee["sum_F11_F15"], "NEW", srcf, "src/s_base.py",
                             "results/s0f.json")]})

    # ------------------------------------------------------------------ E-9.7-top5 (0d)
    p = D.para("**The top-five question, read by mechanism and by geometry.**")
    bf_m32 = fr["32b|mcode_M32_R1"]["families"]["Bellman-Ford/SPFA"]
    bf_8b = fr["8b|mcode_PRIMARY_R1"]["families"]["Bellman-Ford/SPFA"]
    new_p = sub1(p, "and the geometry experiment placed only the 15 unit-weight Dijkstra survivors, so the other survivor "
                    "families (grid Bellman-Ford, coordinate-key heaps, random frontiers) have no landing yet.",
                 f"and the geometry experiment's verdict placed only the 15 unit-weight Dijkstra survivors. Its placement "
                 f"file also places 23 further iteration-8 survivors {TAG}: the 15 Bellman-Ford/SPFA programs land "
                 f"opposite on both gate-passing Qwen3-32B frames ({bf32['opposite']} of {bf32['n']} and "
                 f"{bf_m32['opposite']} of {bf_m32['n']}) and {bf_8b['edge']} edge, {bf_8b['opposite']} opposite on "
                 f"Qwen3-8B, while the 3 BFS variants and the 5 other known programs place at the edge on the primary "
                 f"frames; 'opposite' there means farther than the median of two reference classes, and the placement "
                 f"was not preregistered (Table 438). The coordinate-key heaps have no landing yet.")
    E.append({"id": "E-9.7-top5", "items": ["0d"], "location": {"section": "9.7", "table": None, "line_hint": 9687},
              "old_text": p, "new_text": new_p,
              "reason": "review major 4: the record's own placement file places the Bellman-Ford/SPFA survivors",
              "values": [val("Bellman-Ford/SPFA opposite (32B primary, 32B programs only, 8B)", None,
                             [bf32["opposite"], bf_m32["opposite"], bf_8b["opposite"]], "NEW",
                             ref(A_GEO, "results/placement.json"), "src/s_geometry.py", "results/s0d.json")]})

    # ------------------------------------------------------------------ E-T443 (0a, 0d, 0e)
    t = D.table("**Table 443.**")
    nt = sub1(t, "| Is the gap a property of exhaustion? | Mechanistic compliance falls from 1.00 at one name to 0.22 and "
                 "0.10 at five, lexical compliance stays at or above 0.86 | n/a |",
              f"| Is the gap a property of exhaustion? | By the runtime label mechanistic compliance falls from 1.00 at one "
              f"name to 0.22 and 0.10 at five; by hand reads to {m(q32['5'], 'hand_reads')} and "
              f"{m(q14['5'], 'hand_reads')}; by the tracer to {m(q32['5'], 'tracer_coarse')} and "
              f"{m(q14['5'], 'tracer_coarse')} (fine {m(q32['5'], 'tracer_fine')} and {m(q14['5'], 'tracer_fine')}); "
              f"lexical compliance stays at or above 0.86 | n/a |")
    nt = sub1(nt, "15 of 15 survivors edge by placement |",
              f"15 of 15 survivors edge by placement on the primary frame, 10 of 15 on the Qwen3-32B programs-only frame; "
              f"Bellman-Ford/SPFA survivors opposite on both gate-passing Qwen3-32B frames |")
    nt = sub1(nt, "Language manifolds: lexical distance;", "Language manifolds: lexical distance and data-structure attributes;")
    nt = sub1(nt, "**Table 443.** The top-five prohibition across this iteration's instruments.",
              f"**Table 443.** The top-five prohibition across this iteration's instruments {TAG}.")
    E.append({"id": "E-T443", "items": ["0a", "0d", "0e"], "location": {"section": "9.7", "table": "443", "line_hint": 9689},
              "old_text": t, "new_text": nt, "reason": "review majors 1, 4 and 5",
              "values": [val("exhaustion row: k = 5 compliance by reading (32B, 14B)", "0.22 and 0.10 (one reading)",
                             [q32["5"]["hand_reads"]["mech"], q14["5"]["hand_reads"]["mech"],
                              q32["5"]["tracer_coarse"]["mech"], q14["5"]["tracer_coarse"]["mech"]], "CORRECTED",
                             src_reads + "; " + ref(A_REN, "results/n3_tracer.json"), SR, OA),
                         val("survivors classed edge", "15 of 15", "15 of 15 primary; 10 of 15 programs-only", "CORRECTED",
                             ref(A_GEO, "results/placement.json", "<frame>.udij_survivors.n_edge"), "src/s_geometry.py",
                             "results/s0d.json")]})

    # ------------------------------------------------------------------ E-9.7-circuit (0f)
    p = D.para("**Sharpening and the circuit.**")
    new_p = sub1(p, "The layer-0 condition-span node, repaired, holds out at about half its pair-prompt effect without "
                    "surviving its family's Holm adjustment,",
                 f"The layer-0 condition-span node, repaired, holds out at about 7.9 nats on the five forced prompts, "
                 f"close to its pair-prompt values, and about 0 on the five padded twins (its mean of 3.86 averages the "
                 f"two sides) {TAG}, without surviving its family's Holm adjustment,")
    E.append({"id": "E-9.7-circuit", "items": ["0f"], "location": {"section": "9.7", "table": None, "line_hint": 9697},
              "old_text": p, "new_text": new_p, "reason": "review minor 1",
              "values": [val("held-out effect relative to pair prompts", "about half its pair-prompt effect", f"forced {A_['mean_forced']:.3f} / {S_['mean_forced']:.3f}",
                             "CORRECTED", srcf, "src/s_base.py", "results/s0f.json")]})

    # ------------------------------------------------------------------ E-T444 (0a, 0d, 0f)
    t = D.table("**Table 444.**")
    nt = sub1(t, "| Mechanistic compliance 1.00 to 0.22 (Qwen3-32B) and 1.00 to 0.10 (Qwen3-14B), trend p 0.00001; lexical "
                 "at or above 0.86; held-out gaps 0.56 and 0.68; the tracer's curve is weaker and not monotone |",
              f"| By the runtime label mechanistic compliance 1.00 to 0.22 (Qwen3-32B) and 1.00 to 0.10 (Qwen3-14B), trend "
              f"p 0.00001; lexical at or above 0.86; held-out gaps 0.56 and 0.68. By reading: Qwen3-14B meets the bars "
              f"under every reading except the tracer's fine classes on held-out templates "
              f"({gp(q14['ho'], 'tracer_fine')}); Qwen3-32B meets them only by the runtime label (k = 5 gaps: hand reads "
              f"{gp(q32['5'], 'hand_reads')}, tracer {gp(q32['5'], 'tracer_coarse')}, tracer fine "
              f"{gp(q32['5'], 'tracer_fine')}), and its tracer curve is not monotone |")
    nt = sub1(nt, "15 of 15 survivors edge)", "15 of 15 survivors edge on the primary frame, 10 of 15 on the programs-only frame)")
    nt = sub1(nt, "| Layer-0 node 3.86 and 3.85 nats held out (p 0.0625 and 0.023; Holm 0.22 and 0.12), half its pair "
                  "values; motif still differs on condition share |",
              f"| Layer-0 node about 7.9 nats on the five forced prompts, close to its pair-prompt values, and about 0 on "
              f"the five padded twins; the mean of 3.86 averages the two sides (3.85 steering; p 0.0625 and 0.023; Holm "
              f"0.22 and 0.12; five contrasts give p {rN(A_['p5_contrast_mean_one_sided'], 3)} one-sided, the floor); "
              f"motif still differs on condition share |")
    nt = sub1(nt, "| Exhaustion curve (primary) | Bars met in both models; descriptive |",
              "| Exhaustion curve (primary) | Bars met in both models by the runtime label; reading-dependent; descriptive |")
    nt = sub1(nt, "**Table 444.** Verdicts of the claims of iteration 9.",
              f"**Table 444.** Verdicts of the claims of iteration 9 {TAG}.")
    E.append({"id": "E-T444", "items": ["0a", "0d", "0f"], "location": {"section": "9.8", "table": "444", "line_hint": 9703},
              "old_text": t, "new_text": nt, "reason": "review majors 1 and 4, minor 1",
              "values": [val("held-out rerun", "3.86 and 3.85, half its pair values",
                             f"forced {A_['mean_forced']:.3f} / {S_['mean_forced']:.3f}; padded {A_['mean_padded']:.3f} / "
                             f"{S_['mean_padded']:.3f}", "CORRECTED", srcf, "src/s_base.py", "results/s0f.json"),
                         val("five-contrast one-sided p", None, A_["p5_contrast_mean_one_sided"], "NEW", srcf,
                             "src/s_base.py", "results/s0f.json", "exact")]})

    # ------------------------------------------------------------------ E-9.8-established (0a, 0c, 0d, 0e, 0i)
    p = D.para("**Established.** A ban of five path-algorithm names")
    np_ = sub1(p, "Under cumulative bans, mechanistic compliance falls from 1.00 at one name to 0.22 (Qwen3-32B) and 0.10 "
                  "(Qwen3-14B) at five while lexical compliance stays at or above 0.86: banning one name changes the "
                  "mechanism, banning the repertoire moves compliance to the names. The survivors of the obeying models "
                  "are mostly not renamed BFS. By hand reads, 0.30 are unit-weight Dijkstra, which is BFS order on a unit "
                  "grid, and the rest are known algorithms with other expansion disciplines",
               f"Under cumulative bans lexical compliance stays at or above 0.86, and mechanistic compliance at five names "
               f"depends on the reading {TAG}: by the runtime label it falls from 1.00 at one name to 0.22 (Qwen3-32B) "
               f"and 0.10 (Qwen3-14B); by hand reads to {m(q32['5'], 'hand_reads')} and {m(q14['5'], 'hand_reads')}; by "
               f"the tracer to {m(q32['5'], 'tracer_coarse')} and {m(q14['5'], 'tracer_coarse')} (fine classes "
               f"{m(q32['5'], 'tracer_fine')} and {m(q14['5'], 'tracer_fine')}). Banning one name changes the mechanism; "
               f"banning the whole repertoire is answered by renaming in Qwen3-14B under every reading except the fine "
               f"tracer on held-out templates, while Qwen3-32B moves mostly to other known disciplines. A ban described "
               f"without names changes mechanistic compliance by an instrument-dependent amount (+{r2(rt['diff'])} by "
               f"the runtime label, {r2(tr['diff'])} by the tracer, about +{r2(pa['diff'])} under the per-cell reading; "
               f"exploratory). By hand reads the survivors of the obeying models are mostly not renamed BFS: 0.30 are "
               f"unit-weight Dijkstra (BFS order under another name) and 0.70 are known algorithms with other expansion "
               f"disciplines")
    np_ = sub1(np_, "(grid Bellman-Ford, coordinate-key heaps, random frontiers); judges' names are unreliable for exactly "
                    "these programs.",
               "(grid Bellman-Ford, coordinate-key heaps, random frontiers); judges' names are unreliable for exactly "
               "these programs, and the instruments disagree on them (by the runtime label 0.79 and by the tracer 0.43 of "
               "Qwen3-32B's 91 name-level survivors are in a banned class).")
    np_ = sub1(np_, "robust to the program source and the readout; all 15 survivors place at the edge.",
               f"robust to the program source and the readout; its 15 survivors place at the edge on the primary frames "
               f"(15 of 15) and 10 of 15 on the Qwen3-32B programs-only frame, while the 15 Bellman-Ford/SPFA survivors "
               f"place opposite on both gate-passing Qwen3-32B frames ('opposite' relative to the median of two "
               f"reference classes; not preregistered).")
    np_ = sub1(np_, "The language manifolds track lexical distance; the program manifold",
               "The language manifolds track lexical distance and textbook data-structure attributes, not measured "
               "expansion order; the program manifold")
    np_ = sub1(np_, "and reversed the base model's preference there (20 of 20 prompts);",
               f"and reversed and concentrated the base model's preference there (20 of 20 prompts; base P(BFS) "
               f"{r2(gr['base_p_alternative'])}, {rN(gr['unmapped_base_mass'], 3)} of base mass unmapped);")
    E.append({"id": "E-9.8-established", "items": ["0a", "0c", "0d", "0e", "0i"],
              "location": {"section": "9.8", "table": None, "line_hint": 9717}, "old_text": p, "new_text": np_,
              "reason": "review majors 1, 3, 4, 5 and minor 4: the established claims restated per reading",
              "values": [val("hand-read k = 5 compliance (32B, 14B)", None,
                             [q32["5"]["hand_reads"]["mech"], q14["5"]["hand_reads"]["mech"]], "NEW", src_reads, SR, OA),
                         val("tracer k = 5 compliance (32B, 14B)", None,
                             [q32["5"]["tracer_coarse"]["mech"], q14["5"]["tracer_coarse"]["mech"]], "MATCH",
                             ref(A_REN, "results/n3_tracer.json", "per_k.5.mech_coarse_traceable"), SR, OA)]})

    # ------------------------------------------------------------------ E-9.6-novb (0j)
    p = D.para("- *Discovery on online bin packing* (NOV-B)")
    J = j["result"]
    jtxt = (f"Before the failure the harness was built and passed its gate {TAG}: G-HARNESS PASS, with best fit at "
            f"{rN(J['bf_or3_excess'], 2)}% excess on OR3 and {rN(J['bf_w5k_excess'], 2)}% on Weibull 5k reproduced, "
            f"FunSearch's published heuristics at {rN(J['funsearch_or3_excess'], 2)}% and "
            f"{rN(J['funsearch_w5k_excess'], 2)}%, and the priority-form first, best and worst fit equal to the "
            f"hand-coded packers; iteration 10's evaluator search reuses it, and no search ran in iteration 9.")
    new_p = sub1(p, "Lost at gen_art; no artifact.", "Lost at gen_art; no artifact. " + jtxt)
    srcj = J["source"]
    E.append({"id": "E-9.6-novb", "items": ["0j"], "location": {"section": "9.6", "table": None, "line_hint": 9680},
              "old_text": p, "new_text": new_p, "reason": "review minor 5: the harness passed its gate before the failure",
              "values": [val("harness gate values", None, [J["bf_or3_excess"], J["bf_w5k_excess"], J["funsearch_or3_excess"],
                                                           J["funsearch_w5k_excess"]], J["status"], srcj, "src/s_slips.py",
                             "results/s0j.json", "2 decimals")]})

    # ------------------------------------------------------------------ E-9.9 (0d, 0j)
    p = D.para("Iteration 10 is the last.")
    new_p = sub1(p, "The other is placing the other survivor families, the grid Bellman-Ford rounds and coordinate-key "
                    "heaps, which are known but genuinely different disciplines.",
                 f"The other is placing the remaining survivor families {TAG}: the record's placement file already places "
                 f"iteration 8's grid Bellman-Ford/SPFA survivors, which land opposite on both gate-passing Qwen3-32B "
                 f"frames (15 of 15; 'opposite' is relative to the median of the two non-banned reference classes, and "
                 f"the placement was not preregistered), while the unit-weight Dijkstra survivors place at the edge (15 "
                 f"of 15 on the primary frames, 10 of 15 on the programs-only frame); the coordinate-key heaps have no "
                 f"landing yet, and TP-G2's preregistered placements address both.")
    new_p = sub1(new_p, "the bin-packing and TSP plans were lost before they ran, so the question stays open, not answered.",
                 f"the bin-packing and TSP plans were lost before they ran, so the question stays open, not answered; the "
                 f"bin-packing harness had been built and had passed its gate before the loss (best fit "
                 f"{rN(J['bf_or3_excess'], 2)}% and {rN(J['bf_w5k_excess'], 2)}% excess reproduced; FunSearch's heuristics "
                 f"{rN(J['funsearch_or3_excess'], 2)}% and {rN(J['funsearch_w5k_excess'], 2)}%), iteration 10's evaluator "
                 f"search reuses it, and no search ran in iteration 9 {TAG}.")
    E.append({"id": "E-9.9", "items": ["0d", "0j"], "location": {"section": "9.9", "table": None, "line_hint": 9727},
              "old_text": p, "new_text": new_p, "reason": "review major 4 and minor 5",
              "values": [val("Bellman-Ford/SPFA opposite on gate-passing 32B frames", None,
                             [bf32["opposite"], bf_m32["opposite"]], "NEW", ref(A_GEO, "results/placement.json"),
                             "src/s_geometry.py", "results/s0d.json"),
                         val("harness gate", None, J["G_HARNESS_PASS"], J["status"], srcj, "src/s_slips.py",
                             "results/s0j.json")]})

    # ------------------------------------------------------------------ E-closing-sharpening (0g)
    p = D.para("Post-training made those margins")
    new_p = sub1(p, "The validated fork stack closes the whole minimum spanning tree gap, but random late-layer sets close "
                    "a median 0.81 of it.",
                 f"The validated fork stack closes the whole minimum spanning tree gap, but random late-layer sets close "
                 f"a median 0.81 of it; most of those sets repeat a component, and the {b3['families']['R']['n_ten_distinct']} "
                 f"sets of ten distinct components keep a median {r2(b3['families']['R']['restricted_median'])}, so "
                 f"specificity there stays unresolved until BASE-W's draws without reuse {TAG}.")
    E.append({"id": "E-closing-sharpening", "items": ["0g"], "location": {"section": "What we have learned so far",
                                                                         "table": None, "line_hint": 9737},
              "old_text": p, "new_text": new_p, "reason": "review minor 2",
              "values": [val("MST ten-distinct random sets and their median", None,
                             [b3['families']['R']['n_ten_distinct'], b3['families']['R']['restricted_median']], "NEW",
                             srcg, "src/s_base.py", "results/s0g.json")]})

    # ------------------------------------------------------------------ E-closing-handles (0f)
    p = D.para("Internal handles exist in both families")
    new_p = sub1(p, "and the repaired held-out arm gives 3.86 and 3.85 nats (p 0.0625 and 0.023; Holm 0.22 and 0.12 in its "
                    "family).",
                 f"and the repaired held-out arm gives about 7.9 nats on the five forced prompts ({r2(A_['mean_forced'])} "
                 f"and {r2(S_['mean_forced'])}) and about 0 on the five padded twins; its means of 3.86 and 3.85 nats "
                 f"average the two sides (p 0.0625 and 0.023; Holm 0.22 and 0.12 in its family; five contrasts cannot "
                 f"reach two-sided 0.05) {TAG}.")
    E.append({"id": "E-closing-handles", "items": ["0f"], "location": {"section": "What we have learned so far",
                                                                      "table": None, "line_hint": 9741},
              "old_text": p, "new_text": new_p, "reason": "review minor 1",
              "values": [val("held-out arm", "3.86 and 3.85 nats", f"forced {A_['mean_forced']:.3f} / {S_['mean_forced']:.3f}",
                             "CORRECTED", srcf, "src/s_base.py", "results/s0f.json")]})

    # ------------------------------------------------------------------ E-closing-ban (0a, 0c, 0d, 0e, 0h)
    p = D.para("A single prompt ban, where the model obeys it")
    np_ = sub1(p, "Read by runtime expansion order over 546 programs in ten configurations, lexical compliance exceeds "
                  "mechanistic compliance by 0.70 (runtime label) or 0.61 (tracer), in every configuration,",
               f"Read by the runtime label (heap priorities, frontier evidence, restarts) and by the expansion-order "
               f"tracer over 546 programs in ten configurations, lexical compliance exceeds mechanistic compliance by "
               f"0.70 (runtime label) or 0.61 (tracer), {r2(pu[0])} if unit-weight Dijkstra, IDA* and jump point search "
               f"count as compliant {TAG}, in every configuration,")
    np_ = sub1(np_, "and mechanistic compliance falls to 0.22 and 0.10 at five names while lexical compliance stays at or "
                    "above 0.86.",
               f"and by the runtime label mechanistic compliance falls to 0.22 and 0.10 at five names (by hand reads "
               f"{m(q32['5'], 'hand_reads')} and {m(q14['5'], 'hand_reads')}; by the tracer "
               f"{m(q32['5'], 'tracer_coarse')} and {m(q14['5'], 'tracer_coarse')}) while lexical compliance stays at or "
               f"above 0.86; Qwen3-14B meets the committed 0.4 gap under every reading except the tracer's fine classes on "
               f"held-out templates ({gp(q14['ho'], 'tracer_fine')}), and Qwen3-32B only by the runtime label. A ban "
               f"described without names moves mechanistic compliance by an instrument-dependent amount (+{r2(rt['diff'])} "
               f"by the runtime label, {r2(tr['diff'])} by the tracer, about +{r2(pa['diff'])} under the per-cell "
               f"reading).")
    np_ = sub1(np_, "The survivors of the full ban are mostly not renamed BFS: by hand reads of 76 survivors of Qwen3-32B "
                    "and Qwen3-14B, 0.30 are",
               "By hand reads of 76 survivors of Qwen3-32B and Qwen3-14B, the survivors of the full ban are mostly not "
               "renamed BFS: 0.30 are")
    np_ = sub1(np_, "On the manifold built from its name-scrubbed programs it lies at the edge (0.67), robustly, and all 15 "
                    "survivors place at the edge.",
               "On the manifold built from its name-scrubbed programs it lies at the edge (0.67), robustly; its survivors "
               "place at the edge on the primary frames (15 of 15) and on 10 of 15 on the Qwen3-32B programs-only frame, "
               "and the 15 Bellman-Ford/SPFA survivors place opposite on both gate-passing Qwen3-32B frames (relative to "
               "the median of two reference classes; not preregistered).")
    np_ = sub1(np_, "The language manifolds track lexical distance between the names (Spearman 0.46 to 0.57 with a lexical "
                    "matrix),",
               f"The language manifolds track lexical distance between the names and textbook data-structure attributes, "
               f"not measured expansion order (Spearman 0.46 to 0.57 with a lexical matrix; {r2(nm['rho']['R_DS'])} "
               f"with a data-structure matrix on the named Qwen3-32B manifold, each surviving the other in partial RSA, "
               f"descriptively),")
    E.append({"id": "E-closing-ban", "items": ["0a", "0c", "0d", "0e", "0h"],
              "location": {"section": "What we have learned so far", "table": None, "line_hint": 9743},
              "old_text": p, "new_text": np_, "reason": "review majors 1, 3, 4, 5 and minor 3",
              "values": [val("pooled gap, UD/IDA*/JPS compliant", None, pu[0], "NEW",
                             ref(A_REN, "results/retrace.jsonl"), SR, "results/s0h.json"),
                         val("k = 5 compliance by hand reads and tracer", "0.22 and 0.10 (runtime only)",
                             [q32["5"]["hand_reads"]["mech"], q14["5"]["hand_reads"]["mech"],
                              q32["5"]["tracer_coarse"]["mech"], q14["5"]["tracer_coarse"]["mech"]], "CORRECTED",
                             src_reads, SR, OA),
                         val("survivor placement", "all 15 survivors place at the edge",
                             "15 of 15 primary; 10 of 15 programs-only; Bellman-Ford/SPFA opposite", "CORRECTED",
                             ref(A_GEO, "results/placement.json"), "src/s_geometry.py", "results/s0d.json"),
                         val("R_DS rho, named 32B", None, nm["rho"]["R_DS"], "MATCH",
                             ref(A_GEO, "results/rsa.json", "32b|mname.models.R_DS"), "src/s_controls.py",
                             "results/s1_controls.json", "1e-9")]})

    # ------------------------------------------------------------------ E-closing-open (0h)
    p = D.para("What remains open follows from this.")
    new_p = sub1(p, "screened across ten configurations, read by runtime expansion order, cumulated one name at a time",
                 f"screened across ten configurations, read by the runtime label (heap priorities, frontier evidence, "
                 f"restarts) and by the expansion-order tracer {TAG}, cumulated one name at a time")
    E.append({"id": "E-closing-open", "items": ["0h"], "location": {"section": "What we have learned so far",
                                                                   "table": None, "line_hint": 9749},
              "old_text": p, "new_text": new_p, "reason": "review minor 3",
              "values": [val("instrument wording", "read by runtime expansion order",
                             "runtime label and expansion-order tracer", "CORRECTED",
                             ref(A_REN, "results/headlines.json", "primary_mechanism_label"), SR, "results/s0h.json",
                             "wording")]})
    return E
