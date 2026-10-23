#!/usr/bin/env python3
"""Recompute every number the corrections quote, from the iteration-8 result files, into a value ledger.

Each ledger entry: name, item, recorded (as printed in the report, or None), recomputed (raw), printed (recomputed,
formatted like the report), status MATCH / CORRECTED / NEW / CARRIED, tolerance, source
'<artifact_id>:<relative path>#<key path>'.
"""
from __future__ import annotations

import csv
import json
import os
import math
import re
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# The iteration-8 artifacts this repair reads. ONE location setting: S0_DEPS_DIR (default: the run layout,
# <loop>/iter_8/gen_art). Each artifact is found by its id or by its original folder name, under S0_DEPS_DIR or as a
# sibling folder of this one (the layout of the published repository).
DEPS_DIR = Path(os.environ.get("S0_DEPS_DIR", ROOT.parents[2] / "round-8" / "."))
FOLDERS = {"art_vnyi0Fm5SyNH": "gen_art_experiment_39", "art_e-_q5mSJGrSb": "gen_art_experiment_40",
           "art_18XvfcJJZi1O": "gen_art_experiment_41", "art_FJMIE9T9_PMv": "gen_art_experiment_42",
           "art_lzuosbrb34wB": "gen_art_experiment_43", "art_R-HSmXq2t97f": "gen_art_experiment_44"}


def dep_dir(art_id: str) -> Path:
    for base in (DEPS_DIR, ROOT.parent):
        for name in (art_id, FOLDERS[art_id]):
            if (base / name).is_dir():
                return base / name
    return DEPS_DIR / FOLDERS[art_id]


ART = {a: dep_dir(a) for a in FOLDERS}
FORK, DAS, CIRC, GEM, LAW, TP = list(ART)


@lru_cache(maxsize=None)
def load(art: str, rel: str) -> Any:
    return json.loads((ART[art] / rel).read_text())


def get(art: str, rel: str, keypath: str) -> Any:
    """Navigate 'a.b[3].c[node=mlp|L0|H-1|COND].d' (dots inside [] are literal)."""
    x = load(art, rel)
    for part in re.findall(r"[^.\[\]]+|\[[^\]]*\]", keypath):
        if part.startswith("["):
            sel = part[1:-1]
            if "=" in sel:
                f, v = sel.split("=", 1)
                x = next(e for e in x if str(e.get(f)) == v)
            else:
                x = x[int(sel)]
        else:
            x = x[part]
    return x


def _half_up(v: float, d: int) -> str:
    """Fixed-point rounding half away from zero, as printed tables round (0.0625 -> 0.063)."""
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(1).scaleb(-d)
    return str(Decimal(repr(float(v))).quantize(q, rounding=ROUND_HALF_UP)) if d > 0 else str(
        Decimal(repr(float(v))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def fmt(v: Any, spec: str) -> str:
    if isinstance(v, (int, float)) and re.fullmatch(r"\.\d+f", spec):
        return _half_up(v, int(spec[1:-1]))
    if spec == "int":
        return str(int(round(v)))
    if spec == "str":
        return str(v)
    if spec.startswith("sig"):           # significant figures, plain or scientific like the report prints p-values
        n = int(spec[3:])
        if v == 0:
            return "0"
        if v == 1:
            return "1"
        if abs(v) < 1e-4:
            return f"{v:.{n - 1}e}"
        return f"{v:.{n}g}"
    if spec.startswith("e"):
        return f"{v:.{int(spec[1:])}e}"
    return format(v, spec)


def like(recorded: str, v: float) -> str:
    """Format v the way `recorded` is printed (decimals or scientific mantissa)."""
    r = recorded.strip().lstrip("+")
    if r in ("1", "0") and isinstance(v, (int, float)):
        return str(int(round(v))) if abs(v - round(v)) < 1e-12 else f"{v:.2g}"
    if "e" in r:
        mant = r.split("e")[0]
        d = len(mant.split(".")[1]) if "." in mant else 0
        return f"{v:.{d}e}"
    if "." in r:
        return _half_up(v, len(r.split(".")[1]))
    return str(int(round(v)))


class Ledger:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.by: dict[str, dict[str, Any]] = {}

    def add(self, name: str, item: str, value: Any, source: str, spec: str = ".2f", recorded: str | None = None,
            status: str | None = None, note: str = "") -> str:
        printed = fmt(value, spec) if not isinstance(value, str) else value
        if status is None:
            if recorded is None:
                status = "NEW"
            else:
                cmp = like(recorded, value) if not isinstance(value, str) else value
                status = "MATCH" if cmp == recorded.strip().lstrip("+") else "CORRECTED"
                if status == "MATCH":
                    printed = recorded.strip()
        tol = ("exact" if spec in ("int", "str") or isinstance(value, str) else
               "last printed digit" if recorded is not None else "printed precision")
        row = {"name": name, "item": item, "recorded": recorded, "recomputed": value, "printed": printed,
               "status": status, "tolerance": tol, "source": source, "note": note}
        if name in self.by:
            raise ValueError(f"duplicate ledger name {name}")
        self.rows.append(row)
        self.by[name] = row
        return printed

    def p(self, name: str) -> str:
        return self.by[name]["printed"]


def src(art: str, rel: str, key: str) -> str:
    return f"{art}:{rel}#{key}"


# ================================================================================================ 0a circuit
NODE_NAMES = {"mlp|L0|H-1|COND": "MLP, layer 0, condition span"}


def node_label(k: str) -> str:
    t, L, H, c = k.split("|")
    pos = {"COND": "condition span", "SPEC": "task specification", "OPEN": "opening", "DEC": "fork"}[c]
    if t == "mlp":
        return f"MLP, layer {L[1:]}, {pos}"
    return f"Head {H[1:]} of layer {L[1:]}, {pos}"


def recompute_0a(led: Ledger, out_dir: Path) -> dict[str, Any]:
    rel = "results/summary.json"
    res: dict[str, Any] = {"tables": {}, "identity": [], "zero_heldout": [], "zero_entries": []}
    table_csv = []
    rows_by_contrast = {}
    for c in ("C1forced", "C2a", "C1nat"):
        V = get(CIRC, rel, f"validation.{c}")
        n_h = V["n_heldout"]
        vrows = [json.loads(l) for l in (ART[CIRC] / f"data/validation_rows_{c}.jsonl").read_text().splitlines() if l]
        rows_by_contrast[c] = vrows
        held_mask = [bool(r["heldout"]) for r in vrows]
        for mode in ("ablate", "steer"):
            for i, rec in enumerate(V["per_node"][mode]):
                k = rec["node"]
                n = rec["n"]
                lhs = rec["mean_d"] * n
                rhs = rec["mean_d_pair_prompts"] * (n - n_h) + rec["mean_d_heldout"] * n_h
                ok = abs(lhs - rhs) <= 1e-6 * max(1.0, abs(lhs))
                res["identity"].append({"contrast": c, "mode": mode, "node": k, "lhs": lhs, "rhs": rhs, "pass": ok})
                d = rec["d_per_prompt"]
                held_d = [x for x, h in zip(d, held_mask) if h] if len(d) == len(held_mask) else None
                n_zero = sum(1 for x in (held_d or []) if x == 0.0)
                if rec["mean_d_heldout"] == 0.0:
                    res["zero_heldout"].append({"contrast": c, "mode": mode, "node": k})
                if n_zero:
                    res["zero_entries"].append({"contrast": c, "mode": mode, "node": k, "n_zero_heldout_entries": n_zero})
                table_csv.append({"contrast": c, "mode": mode, "rank": i + 1, "node": k, "label": node_label(k),
                                  "n": n, "n_heldout": n_h, "mean_d": rec["mean_d"],
                                  "mean_d_pair_prompts": rec["mean_d_pair_prompts"],
                                  "mean_d_heldout": rec["mean_d_heldout"],
                                  "p_sign_flip_heldout": rec["p_sign_flip_heldout"], "p_holm_20": rec["p_holm_20"],
                                  "identity_pass": ok, "n_exact_zero_heldout_entries": n_zero})
    with (out_dir / "tables/circuit_heldout.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table_csv[0].keys()))
        w.writeheader()
        w.writerows(table_csv)
    res["table_rows"] = table_csv
    res["identity_check_pass"] = all(r["pass"] for r in res["identity"])
    res["n_exact_zero_heldout_nodes"] = len({(z["contrast"], z["node"]) for z in res["zero_heldout"]})
    # cause: held-out prompts of C1forced share no template with any pair prompt
    vr = rows_by_contrast["C1forced"]
    pair_t = [r["template"] for r in vr if not r["heldout"]]
    held = [r for r in vr if r["heldout"]]
    matches = [sum(1 for t in pair_t if t == r["template"]) for r in held]
    res["cond_span_matches_heldout"] = {"per_heldout_prompt": dict(zip([r["vid"] for r in held], matches)),
                                        "n_heldout_with_any_match": sum(1 for m in matches if m > 0),
                                        "n_heldout": len(held), "pair_templates": sorted(set(pair_t)),
                                        "heldout_templates": sorted({r["template"] for r in held})}
    # replication from stored raw margins: node AND every matched random component are exactly 0 on held-out prompts
    key = "mlp|L0|H-1|COND"
    zero_all = []
    for r in held:
        for mode in ("ablate", "steer"):
            vals = [v for kk, v in r["res"].items() if kk.startswith(f"{mode}|{key}|")]
            zero_all.append(all(v == 0.0 for v in vals) and len(vals) == 51)
    res["replication"] = {"heldout_rows_all_node_and_random_entries_zero": sum(zero_all), "of": len(zero_all)}
    res["cause_evidence"] = "replicated" if all(zero_all) and res["cond_span_matches_heldout"][
        "n_heldout_with_any_match"] == 0 else "code-and-pattern"
    code = (ART[CIRC] / "src/k3circuit.py").read_text().splitlines()
    res["code_quotes"] = {str(n): code[n - 1].strip() for n in (482, 485, 488)}
    # ledger: the layer-0 node and the natural contrast
    base = "validation.C1forced.per_node"
    for mode, tag in (("ablate", "abl"), ("steer", "ste")):
        r0 = get(CIRC, rel, f"{base}.{mode}[node={key}]")
        led.add(f"0a.L0.{tag}.mean_d", "0a", r0["mean_d"], src(CIRC, rel, f"{base}.{mode}[node={key}].mean_d"), ".2f",
                recorded={"abl": "5.43", "ste": "4.94"}[tag])
        led.add(f"0a.L0.{tag}.pair", "0a", r0["mean_d_pair_prompts"],
                src(CIRC, rel, f"{base}.{mode}[node={key}].mean_d_pair_prompts"), ".2f")
        led.add(f"0a.L0.{tag}.heldout", "0a", r0["mean_d_heldout"],
                src(CIRC, rel, f"{base}.{mode}[node={key}].mean_d_heldout"), ".2f")
        rn = get(CIRC, rel, f"validation.C1nat.per_node.{mode}[node={key}]")
        led.add(f"0a.nat.{tag}.heldout", "0a", rn["mean_d_heldout"],
                src(CIRC, rel, f"validation.C1nat.per_node.{mode}[node={key}].mean_d_heldout"), ".2f")
        led.add(f"0a.nat.{tag}.p_heldout", "0a", rn["p_sign_flip_heldout"],
                src(CIRC, rel, f"validation.C1nat.per_node.{mode}[node={key}].p_sign_flip_heldout"), ".3f")
    led.add("0a.nat.n_heldout", "0a", get(CIRC, rel, "validation.C1nat.n_heldout"),
            src(CIRC, rel, "validation.C1nat.n_heldout"), "int")
    led.add("0a.C1forced.n_heldout", "0a", get(CIRC, rel, "validation.C1forced.n_heldout"),
            src(CIRC, rel, "validation.C1forced.n_heldout"), "int", recorded="10")
    led.add("0a.C1forced.n_pair", "0a", get(CIRC, rel, "validation.C1forced.n_prompts") - get(
        CIRC, rel, "validation.C1forced.n_heldout"), src(CIRC, rel, "validation.C1forced.n_prompts-n_heldout"), "int")
    led.add("0a.cond_matches", "0a", res["cond_span_matches_heldout"]["n_heldout_with_any_match"],
            f"{CIRC}:data/validation_rows_C1forced.jsonl#template (pair vs heldout)", "int")
    led.add("0a.n_zero_nodes", "0a", res["n_exact_zero_heldout_nodes"], src(CIRC, rel, "validation.*.per_node"), "int")
    # Tables 395/396 recorded values (MATCH checks) and new held-out columns
    rec395 = {"mlp|L0|H-1|COND": ("5.429", "3.8e-06", "4.938", "3.8e-06"), "head|L33|H14|DEC": ("2.050", "1.9e-08", "4.251", "1.9e-08"),
              "mlp|L35|H-1|DEC": ("-2.638", "1", "-5.068", "1"), "head|L34|H28|DEC": ("1.964", "1.9e-08", "3.824", "1.9e-08"),
              "mlp|L27|H-1|DEC": ("0.777", "1.9e-08", "1.896", "1.9e-08"), "head|L29|H6|DEC": ("1.403", "1.9e-08", "2.827", "1.9e-08"),
              "mlp|L30|H-1|DEC": ("0.716", "1.9e-08", "1.529", "1.9e-08"), "head|L23|H10|OPEN": ("0.783", "1.9e-08", "1.531", "1.9e-08"),
              "mlp|L28|H-1|DEC": ("0.414", "3.4e-07", "0.904", "1.9e-08"), "mlp|L11|H-1|SPEC": ("1.162", "1.9e-08", "1.288", "1.9e-08")}
    rec396 = {"mlp|L27|H-1|DEC": ("9.596", "1.8e-11", "16.058", "1.8e-11"), "mlp|L26|H-1|DEC": ("5.088", "1.8e-11", "10.606", "1.8e-11"),
              "mlp|L32|H-1|DEC": ("1.924", "3.7e-10", "7.967", "1.8e-11"), "mlp|L30|H-1|DEC": ("0.738", "0.0015", "5.851", "1.8e-11"),
              "head|L23|H10|DEC": ("3.627", "1.8e-11", "7.964", "1.8e-11"), "head|L27|H31|DEC": ("3.047", "1.8e-11", "6.869", "1.8e-11"),
              "mlp|L28|H-1|DEC": ("0.485", "0.0077", "1.685", "3.4e-10"), "mlp|L31|H-1|DEC": ("-1.527", "1", "0.684", "0.0079"),
              "mlp|L13|H-1|SPEC": ("1.712", "2.4e-06", "2.847", "1.3e-07"), "head|L11|H13|SPEC": ("-1.802", "1", "-3.351", "1")}
    for c, recs, tab in (("C1forced", rec395, "T395"), ("C2a", rec396, "T396")):
        for k, (ae, ap, se, sp) in recs.items():
            pa = f"validation.{c}.per_node.ablate[node={k}]"
            ps = f"validation.{c}.per_node.steer[node={k}]"
            ra, rs = get(CIRC, rel, pa), get(CIRC, rel, ps)
            led.add(f"0a.{tab}.{k}.abl", "0a", ra["mean_d"], src(CIRC, rel, pa + ".mean_d"), ".3f", recorded=ae)
            led.add(f"0a.{tab}.{k}.abl_p", "0a", ra["p_holm_20"], src(CIRC, rel, pa + ".p_holm_20"), "sig2", recorded=ap)
            led.add(f"0a.{tab}.{k}.ste", "0a", rs["mean_d"], src(CIRC, rel, ps + ".mean_d"), ".3f", recorded=se)
            led.add(f"0a.{tab}.{k}.ste_p", "0a", rs["p_holm_20"], src(CIRC, rel, ps + ".p_holm_20"), "sig2", recorded=sp)
            led.add(f"0a.{tab}.{k}.abl_h", "0a", ra["mean_d_heldout"], src(CIRC, rel, pa + ".mean_d_heldout"), ".2f")
            led.add(f"0a.{tab}.{k}.ste_h", "0a", rs["mean_d_heldout"], src(CIRC, rel, ps + ".mean_d_heldout"), ".2f")
            led.add(f"0a.{tab}.{k}.abl_hp", "0a", ra["p_sign_flip_heldout"],
                    src(CIRC, rel, pa + ".p_sign_flip_heldout"), "sig2")
            led.add(f"0a.{tab}.{k}.ste_hp", "0a", rs["p_sign_flip_heldout"],
                    src(CIRC, rel, ps + ".p_sign_flip_heldout"), "sig2")
    led.add("0a.C2a.n_prompts", "0a", get(CIRC, rel, "validation.C2a.n_prompts"), src(CIRC, rel, "validation.C2a.n_prompts"),
            "int", recorded="40")
    led.add("0a.C2a.n_heldout", "0a", get(CIRC, rel, "validation.C2a.n_heldout"), src(CIRC, rel, "validation.C2a.n_heldout"),
            "int", recorded="10")
    res["C2a_top10_has_COND"] = any(k.endswith("|COND") for k in rec396)
    res["rec395"], res["rec396"] = rec395, rec396
    # motif
    pc = "motif.primary_comparison"
    led.add("0a.motif.label", "0a", get(CIRC, rel, pc + ".label"), src(CIRC, rel, pc + ".label"), "str",
            recorded="DIFFERENT MOTIF")
    led.add("0a.motif.qwen_cond", "0a", get(CIRC, rel, pc + ".qwen.COND"), src(CIRC, rel, pc + ".qwen.COND"), ".2f",
            recorded="0.01")
    led.add("0a.motif.qwen_depth", "0a", get(CIRC, rel, pc + ".qwen_dec_depth"), src(CIRC, rel, pc + ".qwen_dec_depth"),
            ".2f", recorded="0.86")
    led.add("0a.motif.gemma_depth", "0a", get(CIRC, rel, pc + ".gemma_dec_depth"), src(CIRC, rel, pc + ".gemma_dec_depth"),
            ".2f", recorded="0.69")
    led.add("0a.motif.gemma_cond", "0a", get(CIRC, rel, pc + ".gemma.COND"), src(CIRC, rel, pc + ".gemma.COND"), ".2f",
            recorded="0.36")
    led.add("0a.motif.gemma_label", "0a", get(CIRC, rel, "motif.gemma.label_vs_bands.label"),
            src(CIRC, rel, "motif.gemma.label_vs_bands.label"), "str")
    led.add("0a.motif.sweep_cond", "0a", get(CIRC, rel, "motif.qwen.C1forced.extended_top60_by_exact.COND"),
            src(CIRC, rel, "motif.qwen.C1forced.extended_top60_by_exact.COND"), ".2f", recorded="0.17")
    depths = []
    for c in ("C1nat", "C1forced", "C1mix", "C1natB"):
        q = get(CIRC, rel, f"motif.qwen.{c}")
        for kk in ("dec_stack", "extended_top60_dec_stack"):
            if kk in q and q[kk] and q[kk].get("depth") is not None:
                depths.append((c, kk, q[kk]["depth"]))
    res["mst_depths"] = depths
    led.add("0a.motif.mst_depth_min", "0a", min(d for *_, d in depths), src(CIRC, rel, "motif.qwen.{C1nat,C1forced,C1mix,"
            "C1natB}.{dec_stack,extended_top60_dec_stack}.depth (min)"), ".2f")
    led.add("0a.motif.mst_depth_max", "0a", max(d for *_, d in depths), src(CIRC, rel, "motif.qwen.{C1nat,C1forced,C1mix,"
            "C1natB}.{dec_stack,extended_top60_dec_stack}.depth (max)"), ".2f")
    bands_line = [(i + 1, l) for i, l in enumerate((ART[CIRC] / "src/k3motif.py").read_text().splitlines())
                  if l.startswith("BANDS =")][0]
    bands = eval(bands_line[1].split("=", 1)[1], {"__builtins__": {}})  # literal dict of tuples, from the source line
    res["bands"] = {"line": bands_line[0], "text": bands_line[1], "values": bands}
    for kk, nm in (("COND", "cond"), ("depth", "depth")):
        lo, hi = bands[kk]
        led.add(f"0a.band.{nm}.lo", "0a", lo, f"{CIRC}:src/k3motif.py#L{bands_line[0]} BANDS['{kk}'][0]", ".2f")
        led.add(f"0a.band.{nm}.hi", "0a", hi, f"{CIRC}:src/k3motif.py#L{bands_line[0]} BANDS['{kk}'][1]", ".2f")
    return res


# ================================================================================================ 0b DAS
def recompute_0b(led: Ledger) -> dict[str, Any]:
    rel = "results/analysis.json"
    b = "gen_T10_dec.classes.bfs"
    d = "gen_T10_dec.classes.dfs"
    g = "gen_GRID_dec.classes.bfs"
    led.add("0b.T10.verdict", "0b", get(DAS, rel, "verdicts.T10-dec.verdict"), src(DAS, rel, "verdicts.T10-dec.verdict"),
            "str", recorded="NO HANDLE")
    led.add("0b.GRID.verdict", "0b", get(DAS, rel, "verdicts.GRID-dec.verdict"), src(DAS, rel, "verdicts.GRID-dec.verdict"),
            "str", recorded="SUFFICIENT HANDLE")
    led.add("0b.band.verdict", "0b", get(DAS, rel, "verdicts.T10-band.verdict"), src(DAS, rel, "verdicts.T10-band.verdict"),
            "str", recorded="SUFFICIENT HANDLE")
    led.add("0b.bfs.written", "0b", get(DAS, rel, f"{b}.arms.DAS.attempted_target"),
            src(DAS, rel, f"{b}.arms.DAS.attempted_target"), "int", recorded="29")
    led.add("0b.bfs.correct", "0b", get(DAS, rel, f"{b}.arms.DAS.correct_target"),
            src(DAS, rel, f"{b}.arms.DAS.correct_target"), "int", recorded="5")
    led.add("0b.bfs.fail", "0b", get(DAS, rel, f"{b}.arms.DAS.attempted_target") - get(DAS, rel, f"{b}.arms.DAS.correct_target"),
            src(DAS, rel, f"{b}.arms.DAS.attempted_target - correct_target"), "int", recorded="24")
    led.add("0b.bfs.pass", "0b", get(DAS, rel, f"{b}.arms.DAS.pass_rate"), src(DAS, rel, f"{b}.arms.DAS.pass_rate"), ".2f",
            recorded="0.20")
    led.add("0b.bfs.base_pass", "0b", get(DAS, rel, f"{b}.arms.BASE.pass_rate"), src(DAS, rel, f"{b}.arms.BASE.pass_rate"),
            ".2f", recorded="0.83")
    led.add("0b.bfs.pass_ratio", "0b", get(DAS, rel, "verdicts.T10-dec.V0_by_class.bfs.pass_ratio"),
            src(DAS, rel, "verdicts.T10-dec.V0_by_class.bfs.pass_ratio"), ".2f")
    led.add("0b.V0", "0b", str(get(DAS, rel, "verdicts.T10-dec.V0")), src(DAS, rel, "verdicts.T10-dec.V0"), "str")
    mc = get(DAS, rel, f"{b}.mcnemar_DAS_vs_RAND")
    led.add("0b.bfs.mc_a", "0b", mc["a_only"], src(DAS, rel, f"{b}.mcnemar_DAS_vs_RAND.a_only"), "int", recorded="5")
    led.add("0b.bfs.mc_b", "0b", mc["b_only"], src(DAS, rel, f"{b}.mcnemar_DAS_vs_RAND.b_only"), "int", recorded="0")
    exact = 2 * 0.5 ** 5
    led.add("0b.bfs.mc_p", "0b", mc["p_two_sided"], src(DAS, rel, f"{b}.mcnemar_DAS_vs_RAND.p_two_sided"), ".3f",
            recorded="0.063", note=f"exact two-sided McNemar 2*(1/2)^5 = {exact}")
    led.add("0b.dfs.correct", "0b", get(DAS, rel, f"{d}.arms.DAS.correct_target"),
            src(DAS, rel, f"{d}.arms.DAS.correct_target"), "int", recorded="29")
    led.add("0b.dfs.full", "0b", get(DAS, rel, f"{d}.arms.FULL.correct_target"),
            src(DAS, rel, f"{d}.arms.FULL.correct_target"), "int", recorded="2")
    led.add("0b.dfs.random", "0b", get(DAS, rel, f"{d}.arms.RAND.correct_target"),
            src(DAS, rel, f"{d}.arms.RAND.correct_target"), "int", recorded="0")
    led.add("0b.grid.das", "0b", get(DAS, rel, f"{g}.arms.DAS.correct_target"), src(DAS, rel, f"{g}.arms.DAS.correct_target"),
            "int", recorded="22")
    led.add("0b.grid.base", "0b", get(DAS, rel, f"{g}.arms.BASE.correct_target"),
            src(DAS, rel, f"{g}.arms.BASE.correct_target"), "int", recorded="6")
    led.add("0b.grid.random", "0b", get(DAS, rel, f"{g}.arms.RAND.correct_target"),
            src(DAS, rel, f"{g}.arms.RAND.correct_target"), "int", recorded="5")
    led.add("0b.p_K2", "0b", get(DAS, rel, "K2.p_K2"), src(DAS, rel, "K2.p_K2"), ".3f", recorded="0.037")
    return {"mcnemar_exact_two_sided": exact, "pooled_rule_V0_parts": get(DAS, rel, "verdicts.T10-dec.V0_parts")}


def classify_29of30(text: str) -> list[dict[str, Any]]:
    """Every '29 of 30' / '29/30' occurrence in the report, classified by the nearest preceding keyword in its line
    (and the few words after it). Lines before the iteration-8 heading are marked pre-iteration-8."""
    kws = [("counting sort", "counting sort"), ("toward bfs", "DAS-fork-BFS"), ("toward dfs", "DAS-fork-DFS"),
           ("top five", "circuit top-five"), ("circuit", "circuit top-five"), ("full-state", "full-state"),
           ("full state", "full-state"), ("das", "DAS"), ("rank-4", "DAS"), ("block 22", "DAS"), ("rank 2:", "DAS"),
           ("rank 1:", "DAS")]
    lines = text.splitlines()
    it8 = next((i + 1 for i, l in enumerate(lines) if l.startswith("# Iteration 8:")), 10 ** 9)
    out = []
    for i, l in enumerate(lines):
        for m in re.finditer(r"29 of 30|29/30", l):
            pre = l[max(0, m.start() - 160): m.start()].lower()
            post = l[m.end(): m.end() + 40].lower()
            if "counting sort" in post or "counting sort" in pre[-80:]:
                cls = "counting sort"
            elif re.match(r"\s*(written|write bfs|programs, but)", post) or "toward bfs" in pre[-120:] and \
                    "toward dfs" not in pre[-120:]:
                cls = "DAS-fork-BFS"
            else:
                best, cls = -1, "other"
                for kw, c in kws:
                    pos = pre.rfind(kw)
                    if pos > best:
                        best, cls = pos, c
                if cls == "DAS":
                    cls = "DAS-fork-DFS" if "dfs" in pre + post else "DAS-other"
            if i + 1 < it8:
                cls = f"pre-iteration-8 {cls}"
            out.append({"line": i + 1, "class": cls, "context": l[max(0, m.start() - 140): m.end() + 80]})
    return out


# ================================================================================================ 0c entropy and law
UNIT_NAMES = {"T10": "connected components", "B3": "minimum spanning tree", "A3": "trapped rain water",
              "B6": "valid anagram", "G": "Gemma grid path"}


def recompute_0c(led: Ledger, out_dir: Path) -> dict[str, Any]:
    rel = "results/k1_verdict.json"
    dose = "predictions/commit1_dose_table.json"
    rec_hits = {"T10": ("2", "50"), "B3": ("32", "39"), "A3": ("0", "37"), "B6": ("21", "39"), "G": ("44", "44")}
    med = {}
    with (ART[FORK] / "data/samples.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("arm") == "A0" and r.get("stage") == "S0" and r.get("reached_decision") and r.get("decision_H1") is not None:
                med.setdefault(r["unit"], []).append(r["decision_H1"])
    rows = []
    for u in ("G", "B3", "B6", "T10", "A3"):
        k = get(FORK, rel, f"K1c.{u}")
        led.add(f"0c.{u}.hits", "0c", k["A7_hits_decision"], src(FORK, rel, f"K1c.{u}.A7_hits_decision"), "int",
                recorded=rec_hits[u][0])
        led.add(f"0c.{u}.n", "0c", k["n"], src(FORK, rel, f"K1c.{u}.n"), "int", recorded=rec_hits[u][1])
        led.add(f"0c.{u}.above", "0c", 1 - k["twin_dec_H_below_q90_frac"],
                src(FORK, rel, f"K1c.{u}.1-twin_dec_H_below_q90_frac"), ".2f")
        q = get(FORK, dose, f"units.{u}.q90")
        led.add(f"0c.{u}.q90", "0c", q, src(FORK, dose, f"units.{u}.q90"), "sig2")
        m = statistics.median(med[u])
        led.add(f"0c.{u}.median_H", "0c", m, f"{FORK}:data/samples.jsonl#arm=A0,stage=S0,reached_decision -> "
                f"median(decision_H1) [{u}]", ".2f")
        rows.append({"unit": u, "task": UNIT_NAMES[u], "n_twin_reaching_fork": k["n"],
                     "share_above_q90": 1 - k["twin_dec_H_below_q90_frac"], "q90_nats": q,
                     "argmax_entropy_hits_first64": k["A7_hits_decision"], "median_fork_entropy_nats": m,
                     "n_samples_with_entropy": len(med[u])})
    led.add("0c.n_total", "0c", sum(r["n_twin_reaching_fork"] for r in rows), src(FORK, rel, "K1c.*.n (sum)"), "int")
    q90s = [r["q90_nats"] for r in rows]
    led.add("0c.q90.min", "0c", min(q90s), src(FORK, dose, "units.*.q90 (min)"), ".4f", recorded="0.0003")
    led.add("0c.q90.max", "0c", max(q90s), src(FORK, dose, "units.*.q90 (max)"), ".2f", recorded="0.05")
    led.add("0c.T10.median_H_rec", "0c", med_v := statistics.median(med["T10"]),
            f"{FORK}:data/samples.jsonl#median decision_H1 [T10]", ".2f", recorded="0.13")
    mixed = [statistics.median(med[u]) for u in ("B3", "A3", "B6", "G")]
    led.add("0c.mixed_median.min", "0c", min(mixed), f"{FORK}:data/samples.jsonl#median decision_H1 [B3,A3,B6,G] (min)",
            ".2f", recorded="0.53")
    led.add("0c.mixed_median.max", "0c", max(mixed), f"{FORK}:data/samples.jsonl#median decision_H1 [B3,A3,B6,G] (max)",
            ".2f", recorded="0.81")
    # temperature law
    relL = "results/analysis_L.json"
    rec_mae = {"A3": "0.029", "B6": "0.054", "B3": "0.043", "G-T04": "0.033", "G-R6": "0.014", "L-T1": "0.142"}
    lrows = []
    for u, r in rec_mae.items():
        pu = get(LAW, relL, f"verdict.per_unit.{u}")
        led.add(f"0c.law.{u}.mae", "0c", pu["mae_L"], src(LAW, relL, f"verdict.per_unit.{u}.mae_L"), ".3f", recorded=r)
        led.add(f"0c.law.{u}.H", "0c", pu["H"], src(LAW, relL, f"verdict.per_unit.{u}.H"), ".3f" if pu["H"] > 0.01 else "sig1")
        mae = get(LAW, relL, f"units.{u}.mae.p1")
        lrows.append({"unit": u, "law": pu["mae_L"], "flat_B0": mae["B0"], "tempering_B1": mae["B1"],
                      "single_fork_B2": mae["B2"], "entropy_BH": mae["BH"], "H_bits": pu["H"], "pass": pu["pass"]})
    hmax = max(get(LAW, relL, f"verdict.per_unit.{u}.H") for u in ("A3", "B6", "B3", "G-T04", "G-R6"))
    led.add("0c.law.Hmax5", "0c", hmax, src(LAW, relL, "verdict.per_unit.{A3,B6,B3,G-T04,G-R6}.H (max)"), ".3f",
            recorded="0.004")
    led.add("0c.law.H_llama", "0c", get(LAW, relL, "verdict.per_unit.L-T1.H"), src(LAW, relL, "verdict.per_unit.L-T1.H"),
            ".2f", recorded="0.63")
    led.add("0c.law.B6.flat", "0c", get(LAW, relL, "units.B6.mae.p1.B0"), src(LAW, relL, "units.B6.mae.p1.B0"), ".3f",
            recorded="0.030")
    led.add("0c.law.GT04.temper", "0c", get(LAW, relL, "units.G-T04.mae.p1.B1"), src(LAW, relL, "units.G-T04.mae.p1.B1"),
            ".3f", recorded="0.023")
    led.add("0c.law.beats_flat", "0c", get(LAW, relL, "verdict.L_vs_baselines.B0.n_L_better"),
            src(LAW, relL, "verdict.L_vs_baselines.B0.n_L_better"), "int", recorded="4")
    led.add("0c.law.sign_p", "0c", get(LAW, relL, "verdict.holm_input_p_L_sign_test_vs_B0"),
            src(LAW, relL, "verdict.holm_input_p_L_sign_test_vs_B0"), ".2f", recorded="0.34")
    led.add("0c.law.n_pass", "0c", get(LAW, relL, "verdict.n_pass"), src(LAW, relL, "verdict.n_pass"), "int", recorded="5")
    led.add("0c.law.n_scored", "0c", get(LAW, relL, "verdict.n_scored"), src(LAW, relL, "verdict.n_scored"), "int",
            recorded="6")
    with (out_dir / "tables/entropy_scope.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with (out_dir / "tables/law_scope.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lrows[0].keys()))
        w.writeheader()
        w.writerows(lrows)
    return {"entropy_rows": rows, "law_rows": lrows}


# ================================================================================================ 0f Gemma arms
ARM_NAMES = {"A0": "twin T 1", "A1": "global T 1.3, top-p 0.95", "A2": "global T 1.6, top-p 0.95",
             "A3g": "global T 2.0, top-p 0.95", "A4": "min-p 0.1, T 3.0", "A5": "entropy-triggered (EDT-style) T 2",
             "A6": "block-start (AdapT-style) T 2", "A7": "high dose at highest-entropy position (placebo)",
             "A8": "high dose at random position (placebo)", "A9": "fork dose, low", "A10": "fork dose, high",
             "A11": "class-uniform forcing", "A9f": "filtered fork dose, low (amendment)",
             "A10f": "filtered fork dose, high (amendment)"}
FAMILIES = {"global_T": ["A1", "A2", "A3g"], "min_p": ["A4"], "EDT": ["A5"], "AdapT": ["A6"]}


def recompute_0f(led: Ledger, out_dir: Path) -> dict[str, Any]:
    cells = load(FORK, "results/k1_cells.json")
    am = load(FORK, "results/amendment.json")
    code = (ART[FORK] / "src/analysis_k1.py").read_text()
    fam_line = [i + 1 for i, l in enumerate(code.splitlines()) if l.startswith("COMP_FAMILIES")][0]
    doc_line = [i + 1 for i, l in enumerate(code.splitlines()) if "twin Hill if none" in l][0]
    presence = {u: sorted(cells[u].keys()) for u in ("T10", "B3", "A3", "B6", "G")}
    rows = []
    for u, arms in presence.items():
        for a in sorted(set(ARM_NAMES) - {"A9f", "A10f"} | set(arms)):
            c = cells[u].get(a) or (am["units"].get(u, {}).get("cells", {}).get(a) if u in am["units"] else None)
            rows.append({"unit": u, "arm": a, "arm_name": ARM_NAMES.get(a, a), "present": a in arms or c is not None,
                         "pass_rate": None if c is None else c.get("pass_rate"),
                         "pass_cost": None if c is None else c.get("pass_cost"),
                         "hill1_correct": None if c is None else c.get("hill1_correct_r25")})
    with (out_dir / "tables/gemma_arms.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    g_present = set(presence["G"])
    fam_status = {}
    bv = am["units"]["G"]["bootstrap_vs"]
    for fam, arms in FAMILIES.items():
        run = [a for a in arms if a in g_present]
        within = [a for a in run if (cells["G"][a].get("pass_cost") or 0) <= 0.05]
        status = "run arm" if within else "twin-level fallback"
        why = ("not run on Gemma" if not run else "run, but pass cost above 5 points on the full slot set" if not within
               else "run within the 5-point pass-cost rule")
        fam_status[fam] = {"arms_present": run, "arms_within_cost": within, "status": status, "why": why,
                           "mean_diff": bv[fam]["mean_diff"], "p_one_sided": bv[fam]["p_one_sided"],
                           "lb_97_5": bv[fam]["lb_97_5"]}
    rel = "results/amendment.json"
    led.add("0f.G.globalT.diff", "0f", bv["global_T"]["mean_diff"], src(FORK, rel, "units.G.bootstrap_vs.global_T.mean_diff"),
            ".2f", recorded="0.08")
    led.add("0f.G.globalT.p", "0f", bv["global_T"]["p_one_sided"], src(FORK, rel, "units.G.bootstrap_vs.global_T.p_one_sided"),
            ".2f", recorded="0.23")
    led.add("0f.G.EDT.p", "0f", bv["EDT"]["p_one_sided"], src(FORK, rel, "units.G.bootstrap_vs.EDT.p_one_sided"), ".3f",
            recorded="0.023")
    led.add("0f.G.minp.p", "0f", bv["min_p"]["p_one_sided"], src(FORK, rel, "units.G.bootstrap_vs.min_p.p_one_sided"),
            ".3f", recorded="0.016")
    led.add("0f.G.adapt.p", "0f", bv["AdapT"]["p_one_sided"], src(FORK, rel, "units.G.bootstrap_vs.AdapT.p_one_sided"),
            ".3f")
    led.add("0f.G.A5.pass_cost", "0f", cells["G"]["A5"]["pass_cost"], src(FORK, "results/k1_cells.json", "G.A5.pass_cost"),
            ".2f", recorded="0.18")
    led.add("0f.G.A3g.pass_cost", "0f", cells["G"]["A3g"]["pass_cost"], src(FORK, "results/k1_cells.json", "G.A3g.pass_cost"),
            ".2f", recorded="0.08")
    led.add("0f.G.twin_hill", "0f", am["units"]["G"]["point_best_hill"]["EDT"],
            src(FORK, rel, "units.G.point_best_hill.EDT (= twin Hill)"), ".2f", recorded="1.64")
    led.add("0f.G.filtered_hill", "0f", am["units"]["G"]["point_best_hill"]["filtered"],
            src(FORK, rel, "units.G.point_best_hill.filtered"), ".2f", recorded="1.98")
    return {"presence": presence, "family_status_G": fam_status, "comp_families_line": fam_line,
            "fallback_docstring_line": doc_line,
            "missing": {u: [a for a in ("A1", "A2", "A3g", "A4", "A5", "A6") if a not in presence[u]] for u in presence}}
