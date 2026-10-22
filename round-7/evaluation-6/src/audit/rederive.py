#!/usr/bin/env python3
"""Independent re-derivation of every recomputed number (Python standard library only; imports nothing from eval.py
or src/). Reads the vendored raw rows under inputs/ and the values eval.py wrote (corrections.json,
results/items.json), recomputes each from the rawest rows, and runs placebos that must FAIL:
P1 Y swapped to the default; P2 passed inverted; P3 labels shuffled within task; P4 the NLA predictors swapped;
P5 Table 238's engines swapped; P6 the apply test with one old_text perturbed; P7 the lint on the uncorrected report.
Writes audit/rederive_report.json.
"""

from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
IN = WS / "inputs"
EX, EN, GE, NL = "art_rMlbrjVB1c__", "art_lpQalcAXMGr1", "art_zNyBP6zieI5u", "art_dbUtqBjT0tPf"


def jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def tb(v) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() == "true"


def binom_p(k: int, n: int, p0: float = 0.5) -> float:
    """Exact two-sided binomial p (minimum-likelihood rule)."""
    if n == 0:
        return 1.0
    pmf = [math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(n + 1)]
    obs = pmf[k]
    return min(1.0, sum(x for x in pmf if x <= obs * (1 + 1e-7)))


class Checks:
    def __init__(self):
        self.rows = []

    def eq(self, name: str, got, want, tol: float = 0.0) -> bool:
        if isinstance(want, (int, float)) and isinstance(got, (int, float)) and not isinstance(want, bool):
            ok = abs(float(got) - float(want)) <= tol + 1e-12 or (
                tol == -1 and (abs(got - want) <= 0.01 * max(abs(want), 1e-300) or (got < 1e-6 and want < 1e-6)))
        else:
            ok = got == want
        self.rows.append({"check": name, "got": got, "want": want, "ok": bool(ok)})
        return bool(ok)


# ---------------------------------------------------------------- Stage A
def stage_a(rows: list[dict], y_of: dict[str, str], passed_flip: bool = False) -> dict:
    out = defaultdict(lambda: {"n": 0, "att": 0, "cor": 0, "pass": 0})
    for r in rows:
        if r["task"] not in y_of or r["arm"].startswith(("ST_", "DMD", "TOP5")):
            continue
        if r["arm"] == "TWIN" and int(r["slot_index"] if r.get("slot_index") is not None else r["slot"]) >= 30:
            continue
        ok = tb(r["passed"]) != passed_flip
        c = out[f"{r['task']}|{r['arm']}"]
        c["n"] += 1
        c["att"] += r["label"] == y_of[r["task"]]
        c["cor"] += (r["label"] == y_of[r["task"]]) and ok
        c["pass"] += ok
    return dict(out)


def stage_a_checks(ch: Checks, cells: dict, items: dict, tag: str = "") -> int:
    bad = 0
    for k, c in cells.items():
        if k not in items:
            continue
        w = items[k]
        bad += not ch.eq(f"{tag}stageA|{k}|n", c["n"], w["n"])
        bad += not ch.eq(f"{tag}stageA|{k}|attempted_Y", c["att"], w["attempted_Y"])
        bad += not ch.eq(f"{tag}stageA|{k}|correct_Y", c["cor"], w["correct_Y"])
        bad += not ch.eq(f"{tag}stageA|{k}|pass", round(c["pass"] / c["n"], 6), round(w["pass"], 6), 1e-6)
    return bad


def main() -> None:
    ch = Checks()
    items = json.loads((WS / "results" / "items.json").read_text())
    corr = json.loads((WS / "corrections.json").read_text())
    sa = json.loads((IN / EX / "results" / "stage_a.json").read_text())
    y_of = {t: v["Y"] for t, v in sa["tasks"].items()}
    dflt = {t: v["default"] for t, v in sa["tasks"].items()}
    rows = jl(IN / EX / "data" / "labels.jsonl")
    cells_items = items["0a"]["cells"]
    cells = stage_a(rows, y_of)
    stage_a_checks(ch, cells, cells_items)
    # recorded record values in stage_a.json against the raw rows
    for t, T in sa["tasks"].items():
        for cell, s in T["cells"].items():
            c = cells[f"{t}|{cell}"]
            ch.eq(f"record|{t}|{cell}|attempted_comp", c["att"], s["attempted_comp"].get(T["Y"], 0))
            ch.eq(f"record|{t}|{cell}|correct_comp", c["cor"], s["correct_comp"].get(T["Y"], 0))
            tw = cells[f"{t}|TWIN"]
            ch.eq(f"record|{t}|{cell}|transfer", round(c["att"] / c["n"] - tw["att"] / tw["n"], 6),
                  round(s["transfer"], 6), 1e-6)
    # post-hoc MR McNemar on correct Y
    by = defaultdict(dict)
    for r in rows:
        if r["arm"] in ("X_0-35", "MR_0-35"):
            by[(r["task"], r["arm"])][r["crn_key"]] = (r["label"] == y_of[r["task"]]) and tb(r["passed"])
    for t, rec in items["0a"]["mr_posthoc"].items():
        X, M = by[(t, "X_0-35")], by[(t, "MR_0-35")]
        ks = sorted(set(X) & set(M))
        b = sum(1 for k in ks if X[k] and not M[k])
        c = sum(1 for k in ks if M[k] and not X[k])
        ch.eq(f"mr_posthoc|{t}|b", b, rec["correct_b"])
        ch.eq(f"mr_posthoc|{t}|c", c, rec["correct_c"])
        ch.eq(f"mr_posthoc|{t}|p", binom_p(b, b + c) if b + c else 1.0, rec["correct_p"], -1)
    # ---- 0b values read from site_grid.json
    sg = json.loads((IN / EX / "results" / "site_grid.json").read_text())
    for t in ("T03", "T10"):
        ph = sg["tasks"][t]["indicator_alpha_le4_posthoc"]
        b, cb, pr = items["0b"]["posthoc_S2"][t]
        ch.eq(f"site|{t}|S2_beta", round(ph["beta"]["S2"], 6), round(b, 6), 1e-6)
        ch.eq(f"site|{t}|S2_boot", [round(x, 6) for x in ph["cluster_bootstrap"]["ci95"]["S2"]], [round(x, 6) for x in cb])
    ch.eq("site|rule_label", sg["RULE"]["verdict"], items["0b"]["rule_label"])
    x011 = cells["T10|X_0-11"]
    off011 = sum(1 for r in rows if r["task"] == "T10" and r["arm"] == "X_0-11" and r["label"] not in
                 (dflt["T10"], "other", "invalid", None)) / x011["n"]
    ch.eq("site|T10|X_0-11_off_default", round(off011, 6), round(items["0b"]["depth_redundancy"]["X_0-11_off_default"], 6), 1e-6)
    # ---- 0f
    t5 = json.loads((IN / EX / "results" / "top5_push.json").read_text())
    pc1 = [c[0] for c in t5["geometry"]["centroids_pc"]]
    ch.eq("top5|pc1_min", round(min(pc1), 6), round(items["0f"]["centroid_pc1_range"][0], 6), 1e-6)
    ch.eq("top5|pass_a1", t5["cells"]["TOP5_a1"]["pass"], items["0f"]["pass"]["1"], 1e-9)
    # ---- 0g Table 238 from samples.jsonl
    sm = jl(IN / EN / "data" / "samples.jsonl")
    d238 = {"T10": "union_find", "T2": "dijkstra"}

    def pn(rows_, swap: bool = False) -> dict:
        agg = defaultdict(lambda: [0, 0, 0])
        sw = {"a": "d", "d": "a", "b": "b", "c": "c"}
        for r in rows_:
            if not str(r["arm"]).startswith("PN_a"):
                continue
            e = sw[r["engine"]] if swap else r["engine"]
            ok = tb(r["passed"])
            off = tb(r["valid"]) and r["label"] not in (d238[r["task"]], "other", "invalid", None)
            a = agg[f"{e}|{r['task']}|{r['arm']}"]
            a[0] += 1
            a[1] += ok
            a[2] += off and ok
        return agg

    agg = pn(sm)
    for k, v in items["0g"]["pn_correct"].items():
        ch.eq(f"t238|{k}|correct", agg[k][1], v["correct"])
        ch.eq(f"t238|{k}|correct_off", agg[k][2], v["correct_off"])
    # ---- 0h NLA
    c2 = json.loads((IN / NL / "predictions" / "commit2_readout.json").read_text())["tasks"]
    idx = {r["state_id"]: r for r in jl(IN / NL / "cache" / "states_index.jsonl")}
    labels = {r["sample_id"]: r for r in jl(IN / NL / "data" / "labels.jsonl")}
    expl, text = defaultdict(list), {}
    for r in jl(IN / NL / "data" / "judgements.jsonl"):
        if r["mode"] == "EXPL":
            expl[r["state_id"]].append(r)
        else:
            text[(r["mode"], r["text_id"])] = r["resolved"]
    units = []
    for sid, r in idx.items():
        if r["kind"] != "GEN" or not c2.get(r["task"], {}).get("regate_pass", True):
            continue
        lab = labels.get(r["sample_id"])
        if lab is None:
            continue
        rs = [e for e in expl.get(sid, []) if int(e["expl_id"].split("#")[-1]) <= 3]
        x = None if not rs else int(sum(e["resolved"] == lab["label"] for e in rs) >= (2 if len(rs) >= 2 else 1))
        tid = f"{r['task']}|{r['condition']}|{r.get('mode') or '-'}|{r['template']}|{r['position']}|{r['slot']}"
        yv = text.get(("PREDICT", tid))
        units.append({"task": r["task"], "s": r["sample_id"], "g": int(r["position"][1:]), "mixed": bool(r.get("mixed")),
                      "x": x, "y": None if yv is None else int(yv == lab["label"]), "name": text.get(("NAME", tid))})
    first_id = {}
    for u in sorted(units, key=lambda u: u["g"]):
        if u["name"] not in ("none_named", "other", "unresolved", None) and u["s"] not in first_id:
            first_id[u["s"]] = u["g"]
    sel = [u for u in units if u["mixed"] and u["g"] < first_id.get(u["s"], 10 ** 6) and u["x"] is not None
           and u["y"] is not None]

    def nla_counts(us, swap=False):
        b = sum(1 for u in us if (u["y"] if swap else u["x"]) == 1 and (u["x"] if swap else u["y"]) == 0)
        c = sum(1 for u in us if (u["y"] if swap else u["x"]) == 0 and (u["x"] if swap else u["y"]) == 1)
        return b, c

    rec = json.loads((IN / NL / "results" / "readout.json").read_text())["N6_per_sample"]
    b, c = nla_counts(sel)
    ch.eq("nla|n_units", len(sel), rec["n"])
    ch.eq("nla|b", b, rec["b"])
    ch.eq("nla|c", c, rec["c"])
    ch.eq("nla|p", binom_p(b, b + c), rec["p"], -1)
    bys = defaultdict(list)
    for u in sel:
        bys[u["s"]].append(u)
    first = [min(v, key=lambda u: u["g"]) for k, v in sorted(bys.items())]
    b1, c1 = nla_counts(first)
    h = items["0h"]
    ch.eq("nla|one_unit|b", b1, h["one_unit_first"]["b"])
    ch.eq("nla|one_unit|c", c1, h["one_unit_first"]["c"])
    ch.eq("nla|one_unit|p", binom_p(b1, b1 + c1), h["one_unit_first"]["p"], -1)
    diffs = [sum(u["x"] for u in v) / len(v) - sum(u["y"] for u in v) / len(v) for v in bys.values()]
    pos, neg = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    ch.eq("nla|sign|p", binom_p(pos, pos + neg), h["sign_test_per_sample"]["p"], -1)
    bk = [(sum(1 for u in v if u["x"] == 1 and u["y"] == 0), sum(1 for u in v if u["x"] == 0 and u["y"] == 1))
          for v in bys.values()]
    B, C = sum(x for x, _ in bk), sum(y for _, y in bk)
    den = sum((x - y) ** 2 for x, y in bk)
    chi2 = (B - C) ** 2 / den
    ch.eq("nla|durkalski|p", math.erfc(math.sqrt(chi2 / 2)), h["durkalski"]["p"], -1)
    ch.eq("nla|n_clusters", len({u["task"] for u in sel}), len(h["clusters"]))
    ch.eq("nla|cluster_floor", 2 * 0.5 ** len({u["task"] for u in sel}), h["cluster_floor_p"], 1e-12)
    # ---- 0c / 0i read-backs
    das = json.loads((IN / GE / "results" / "das.json").read_text())
    ch.eq("gemma|das_k1", das["per_k"]["1"]["das"]["heldout_mean_dy"], items["0c"]["das"]["1"]["das"], 1e-9)
    cl = json.loads((IN / GE / "results" / "clamps.json").read_text())["cells"]
    ch.eq("gemma|top5_pass", cl["FORK|FEATin|k5"]["pass_rate"], items["0c"]["top5"]["pass"], 1e-9)
    ch.eq("gemma|das_k4_passing", int(round(cl["FORK|DAS|k4"]["pass_rate"] * cl["FORK|DAS|k4"]["n"])),
          items["0c"]["das_gen"]["passing"])
    u6 = json.loads((IN / GE / "results" / "fork.json").read_text())["U6"]
    k = int(round(u6["t0_bfs_share"] * u6["t0_n"]))
    ch.eq("gemma|U6_p", binom_p(k, u6["t0_n"], u6["s3_bfs_share"]), items["0i"]["U6"]["exact_binomial_p"], -1)
    # ---- apply test, independently
    report = (IN / "report" / "current_report.md").read_text()

    def apply(cs: list[dict]) -> tuple[bool, str]:
        ok = all(report.count(x["old_text"]) == 1 for x in cs)
        out = report
        for x in sorted(cs, key=lambda x: report.find(x["old_text"])):
            if out.count(x["old_text"]) != 1:
                ok = False
                continue
            rep = x["old_text"] + x["new_text"] if x["kind"] == "insert_after" else x["new_text"]
            out = out.replace(x["old_text"], rep, 1)
        ok = ok and all(x["new_text"] in out for x in cs)
        return ok, out

    ok, corrected = apply(corr["corrections"])
    ch.eq("apply|all", ok, True)
    ch.eq("apply|matches_report_corrected", corrected == (WS / "report_corrected.md").read_text(), True)

    def lint_count(txt: str) -> int:
        pats = [r"post-hoc form survives", r"measured in three models", r"In all three (models )?the read position",
                r"essentially one direction", r"every (fork )?edit[^.]{0,80}?(pass rate|breaks)",
                r"post-hoc ordering of noise sites"]
        lines = txt.split("\n")
        end = next((i for i, l in enumerate(lines) if l.startswith("# References")), len(lines))
        body = "\n".join(lines[5496:end])
        return sum(len(re.findall(p, body, re.I)) for p in pats)

    ch.eq("lint|corrected", lint_count(corrected), 0)
    # ---------------------------------------------------------------- placebos (each must FAIL its check)
    plac = []

    def placebo(name: str, checks_fn) -> None:
        pc = Checks()
        n_bad = checks_fn(pc)
        plac.append({"placebo": name, "n_checks": len(pc.rows), "n_mismatch": n_bad, "fails": n_bad > 0})

    placebo("P1 Y swapped to the default", lambda pc: stage_a_checks(pc, stage_a(rows, dflt), cells_items, "P1|"))
    placebo("P2 passed inverted", lambda pc: stage_a_checks(pc, stage_a(rows, y_of, passed_flip=True), cells_items, "P2|"))

    def p3(pc):
        rng = random.Random(3)
        sh = [dict(r) for r in rows]
        by_t = defaultdict(list)
        for i, r in enumerate(sh):
            by_t[r["task"]].append(i)
        for t, ii in by_t.items():
            labs = [sh[i]["label"] for i in ii]
            rng.shuffle(labs)
            for i, l in zip(ii, labs):
                sh[i]["label"] = l
        return stage_a_checks(pc, stage_a(sh, y_of), cells_items, "P3|")

    placebo("P3 labels shuffled within task", p3)

    def p4(pc):
        bb, cc = nla_counts(sel, swap=True)
        return (not pc.eq("P4|nla|b", bb, rec["b"])) + (not pc.eq("P4|nla|c", cc, rec["c"]))

    placebo("P4 NLA predictors swapped", p4)

    def p5(pc):
        ag = pn(sm, swap=True)
        return sum(not pc.eq(f"P5|{k}", ag[k][2], v["correct_off"]) for k, v in items["0g"]["pn_correct"].items())

    placebo("P5 Table 238 engines swapped", p5)

    def p6(pc):
        cs = json.loads(json.dumps(corr["corrections"]))
        cs[0]["old_text"] = cs[0]["old_text"][:-1] + ("#" if cs[0]["old_text"][-1] != "#" else "%")
        ok6, _ = apply(cs)
        return int(not pc.eq("P6|apply", ok6, True))

    placebo("P6 apply test with one old_text perturbed", p6)
    placebo("P7 lint on the uncorrected report", lambda pc: int(not pc.eq("P7|lint", lint_count(report), 0)))
    n_bad = sum(not r["ok"] for r in ch.rows)
    out = {"n_checks": len(ch.rows), "n_mismatches": n_bad, "mismatches": [r for r in ch.rows if not r["ok"]],
           "n_placebos": len(plac), "n_placebos_failing": sum(p["fails"] for p in plac), "placebos": plac,
           "checks": ch.rows}
    (WS / "audit" / "rederive_report.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"audit: {len(ch.rows)} checks, {n_bad} mismatches; placebos failing {out['n_placebos_failing']}/{len(plac)}")


if __name__ == "__main__":
    main()
