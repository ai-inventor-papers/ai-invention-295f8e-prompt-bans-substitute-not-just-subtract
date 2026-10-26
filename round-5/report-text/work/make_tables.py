"""Build the markdown tables of the iteration-5 section from the artifacts' own output files."""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from names import TASK, ALG, task

W = Path(__file__).resolve().parents[3] / "."
EV, X24, X25, X26, X27, X28, RS = (W / d for d in [
    "gen_art_evaluation_4", "experiment-24/src", "experiment-25/src", "experiment-26/src",
    "experiment-27/src", "experiment-28/src", "research-2/src"])
T = {}

def a(x, t=None):
    if x is None or x == "None":
        return "none"
    if x == "floyd" and t == "T06":
        return "Floyd cycle detection"
    return ALG.get(x, x.replace("_", " "))

def comp(d, t=None, n=None):
    items = sorted(d.items(), key=lambda kv: -kv[1])
    if n: items = items[:n]
    return ", ".join(f"{a(k, t)} {v}" for k, v in items) if items else "none"

def f2(x, nd=2):
    if x is None or x == "": return "n/a"
    try: return f"{float(x):.{nd}f}"
    except Exception: return str(x)

def md(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("-" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)

EXTRA = {"opening_margin": "opening margin", "merit_runtime_min": "minimum runtime merit ratio", "merit_length_min": "minimum length merit ratio",
         "twin_modal_share": "twin modal share", "novelty_share": "novelty instruction share", "n_correct": "correct programs"}
def conv_cell(cell, t=None):
    def rep(m):
        w = m.group(0)
        if w == "floyd" and t == "T06": return "Floyd cycle detection"
        if w in EXTRA: return EXTRA[w]
        return ALG.get(w, w)
    cell = re.sub(r"\b[a-z][a-z0-9_]*\b", rep, cell)
    cell = re.sub(r"\bNone\b", "none", cell)
    return cell

def conv_md_table(text):
    text = re.sub(r"(?<=\| )(T\d+|R\d)\|(?=[A-Za-z])", r"\1 / ", text)
    lines = [l for l in text.strip().splitlines() if l.startswith("|")]
    out = []
    for i, l in enumerate(lines):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if i == 1:
            out.append("|" + "|".join("-" for _ in cells) + "|"); continue
        tcode = None
        if i > 1:
            m = re.match(r"^(T\d+|R\d|A\d|B\d)\b", cells[0])
            if m: tcode = m.group(1)
            if not re.match(r"^[AB]\d \w", cells[0]):
                cells[0] = re.sub(r"^(T\d+|R\d|A\d|B\d)\b", lambda mm: (mm.group(1) + " " + TASK[mm.group(1)]) if mm.group(1)[0] in "AB" else TASK[mm.group(1)], cells[0])
            cells = [conv_cell(c, tcode) for c in cells]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)

def grab(md_text, start_marker, n_lines=None):
    """Return the first markdown table after a marker line."""
    i = md_text.index(start_marker)
    rest = md_text[i:].splitlines()
    tab, started = [], False
    for l in rest[1:]:
        if l.startswith("|"):
            tab.append(l); started = True
        elif started:
            break
    return "\n".join(tab)

# ---------------- evaluation_4 ----------------
corr = json.load(open(EV / "corrections.json"))
rows = []
for e in corr:
    st = {}
    for v in e.get("values", []):
        st[v["status"]] = st.get(v["status"], 0) + 1
    rows.append([e["item"], e["report_location"].replace("|", "/"), ", ".join(f"{k} {v}" for k, v in sorted(st.items())) or "wording only"])
T["corrections"] = md(["Item", "Report location", "Values behind the correction (status against the record)"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/table160_variants.csv")):
    ci = json.loads(r["BA_ci95"]); rci = json.loads(r["rho_ci95"])
    rows.append([r["variant"], r["n_tasks"], r["table"], f"{float(r['BA']):.3f} [{ci[0]:.2f}, {ci[1]:.2f}]",
                 f"{float(r['fisher_p_two_sided']):.3f}", f"{float(r['spearman_rho']):.3f}", f"{float(r['spearman_p_one_sided']):.3f}",
                 f"{float(r['kendall_tau_b']):.3f}", r["verdict_frozen_rule"]])
T["gemma_variants"] = md(["Variant", "Tasks", "Confusion table (rows: predicted obey, predicted fail; columns: observed obey, observed fail)", "Balanced accuracy [95%]", "Fisher p", "Spearman", "One-sided p", "Kendall", "Verdict under the frozen rule"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/table159_grid.csv")):
    tw = json.loads(r["twin_attempts"]); bc = json.loads(r["ban_composition"])
    rows.append([task(r["task"]), a(r["D_frozen"], r["task"]), comp(tw, r["task"]), f"{a(r['twin_modal_correct'], r['task'])} ({float(r['twin_modal_correct_share']):.2f})",
                 r["iter5_default_rule"] + (" (differs from the frozen default)" if r["rule_default_differs_from_frozen_D"] == "True" else ""),
                 f"{float(r['A_catalogue_only']):.2f}", f"{float(r['default_share_drop']):.2f}", r["ban_other_failing"], f"{float(r['E_t']):.3f}", comp(bc, r["task"])])
T["gemma_defaults"] = md(["Task", "Frozen default", "Twin attempts (N = 50)", "Twin modal correct (share)", "Iteration-5 default rule", "Catalogue-only avoidance", "Drop in default share", "Failing other programs under the ban", "Escape fraction", "Ban composition (N = 100)"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/table157_matched.csv")):
    nm = {"PUSH": "push landing of this run's confirmed escapes", "PUSH_SCREEN": "push landing of the iteration-3 screen", "LADDER_OPEN": "opening ladder", "ASSOCIATE": "association", "PROXIMITY": "proximity"}[r["forecast"]]
    rows.append([nm, f"{float(r['mean_bench_push_defined']):.3f} ({r['top1_hits_push_defined']})", f"{float(r['mean_exp16_push_defined']):.3f}",
                 f"{float(r['mean_bench_push_screen_defined']):.3f} ({r['top1_hits_push_screen_defined']})", f"{float(r['mean_exp16_push_screen_defined']):.3f}",
                 f"{float(r['mean_bench_all_gated_uniform_fill']):.3f} ({r['top1_hits_all_gated_uniform_fill']})", f"{float(r['mean_exp16_all_gated_uniform_fill']):.3f}"])
T["matched"] = md(["Forecast", "3 events where this run's push is defined: bench ban (top-1)", "same, route full-ban replication", "4 events where the screen push is defined: bench ban (top-1)", "same, route replication", "all 5 gated events, undefined scored as uniform: bench ban (top-1)", "same, route replication"], rows)

ex = list(csv.DictReader(open(EV / "tables/table123_exposure.csv")))
allrow = [r for r in ex if r["task"] == "ALL"][0]
per = json.loads(allrow["rows"])
affected = {r["task"]: r for r in ex if r["task"] != "ALL"}
def kn(s):
    s = s.replace("PN_a", "plan noise alpha ").replace("NOVELTY", "novelty instruction").replace("SEMSEED", "semantic seed").replace("VETO_ITER1", "first iterated veto round").replace("T1.6", "temperature 1.6")
    return re.sub(r" at (-?\d+)$", r" at \1 points", s)
rows = []
for r in per:
    t = r["task"]
    rec = affected.get(t)
    rows.append([task(t), kn(r["best_within5"]), kn(r["best_within20"]), kn(r["best_within20_same_engine"]), "yes" if r["reaches_1.5_within20"] else "no",
                 (rec["verdict_current"] if rec else "unchanged")])
T["exposure"] = md(["Task", "Best non-exposure knob within 5 points", "Best within 20 points", "Best within 20 points, same engine only", "A non-exposure knob reaches 1.5 within 20 points", "Record verdict that rested on an exposure arm (now a control)"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/pnplain.csv")):
    h = json.loads(r["hill_correct_r25"].replace("null", "None").replace("None", "null"))
    rows.append([task(r["task"]), "plan noise, plain prompt" if r["arm"] == "PNPLAIN_a1" else "plan noise, twin frame", r["n"], f"{float(r['pass']):.2f}",
                 comp(json.loads(r["correct_comp"]), r["task"]), f"{float(r['off_default_share']):.2f}", f"{h['hill']:.2f}"])
T["pnplain"] = md(["Task", "Arm (alpha 1, same slots and direction)", "N", "Pass", "Correct programs", "Off-default share", "Hill-1 (depth 25)"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/dose_units.csv")):
    rows.append([task(r["task"]), f2(r["ban_unit_mean_norm"]), f2(r["banfree_over_ban"]), f2(r["ban_unit_over_residual_norm_exp20_S0"], 3), f2(r["exp20_S4_over_residual"], 3), f2(r["ban_unit_over_residual_norm_exp23_qwen_median"], 3), f2(r["banfree_unit_over_residual_norm"], 3)])
T["dose"] = md(["Task", "Ban unit, mean norm", "Ban-free unit / ban unit", "Ban unit / residual norm, blocks 12-23 (site experiment)", "Ban unit / residual norm, blocks 0-11 (site experiment)", "Ban unit / residual norm, Qwen median (held-out experiment)", "Ban-free unit / residual norm"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/direction_quantiles.csv")):
    q = json.loads(r["off_share_quantiles"]); h = json.loads(r["hill_quantiles"])
    rows.append([task(r["task"]), f"{float(r['alpha']):.0f}", r["K_directions"], r["n_escaping"], r["n_movers_any_off_default"],
                 f"{q['median']:.2f} / {q['q75']:.2f} / {q['max']:.2f}", f"{h['median']:.2f} / {h['q75']:.2f} / {h['max']:.2f}"])
T["dirq"] = md(["Task", "Alpha", "Directions", "Escaping", "Movers (any off-default attempt)", "Off-default share: median / q75 / max", "Correct-only Hill-1: median / q75 / max"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/split_half.csv")):
    rows.append([task(r["task"]), f"{float(r['split_half_rho']):.2f}", f"{float(r['placebo']):.2f}", r["movers_any_alpha"], r["escaping_directions"]])
T["splithalf"] = md(["Task", "Template split-half Spearman over 40 directions", "Placebo", "Movers (any alpha)", "Escaping direction-dose cells"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/signed_progress.csv")):
    qn = {"proj_r": "signed progress toward the runner-up (realised)", "proj_a": "signed progress toward the runner-up (applied)"}[r["quantity"]]
    rows.append([task(r["task"]), qn, a(r["runner_up"], r["task"]), f"{r['n_cells_p_lt_0.05']} of {r['n_block_cells']}", f"{float(r['mean_all_blocks']):.2f}", f"{float(r['mean_edited_blocks_12_23']):.2f}", f"{float(r['min_value']):.2f} (block {r['block_of_min']})", f"{float(r['max_rho_proj_r']):.2f}"])
T["signed"] = md(["Task", "Quantity", "Runner-up", "Cells with p < 0.05 (uncorrected)", "Mean, all blocks", "Mean, edited blocks 12-23", "Minimum (block)", "Largest correlation"], rows)

dep = {}
for r in csv.DictReader(open(EV / "tables/table147_depths.csv")):
    dep.setdefault(r["task"], {})[float(r["alpha"])] = r
rows = []
for t in ["T03", "T05", "T06", "T10", "T1", "T2"]:
    cells = []
    for al in [0.0, 1.0, 2.0, 4.0, 8.0]:
        r = dep[t][al]
        cells.append(f"{r['n_correct']} of {r['n']} (depth {r['hill_depth']})")
    rows.append([task(t)] + cells)
T["depths"] = md(["Task", "Alpha 0", "Alpha 1", "Alpha 2", "Alpha 4", "Alpha 8"], rows)

rows = []
for r in csv.DictReader(open(EV / "tables/rivals_values.csv")):
    rows.append([task(r["task"]), f2(r["R1"]), f2(r["R2"]), f2(r["R3"]), f2(r["R4"]), f2(r["R5"]), f2(r["R6"]), f2(r["R7"]), f2(r["R8"]), f2(r["K"], 0), f2(r["E_pool"], 3), f2(r["PN_excess_alpha_le2"]), "yes" if r["movable"] == "1" else "no"])
T["rivals_values"] = md(["Task", "Opening margin", "Forced can rate", "Association clarity", "Novelty-instruction excess", "Human-solution diversity", "Runtime merit gap", "Twin modal share", "Ban-unit ratio", "Catalogue size", "Escape fraction (pooled)", "Plan-noise excess", "Screen movable"], rows)

sc = list(csv.DictReader(open(EV / "tables/rivals_scores.csv")))
by = {}
for r in sc:
    by.setdefault(r["rival"], {})[r["target"]] = r
names_r = {"R1": "twin opening margin", "R2": "forced can rate", "R3": "association clarity", "R4": "novelty-instruction excess", "R5": "human-solution diversity", "R6": "runtime merit gap", "R7": "twin modal share", "R8": "ban-unit ratio (dose check)", "K": "catalogue size (covariate)"}
rows = []
for k in ["K", "R5", "R4", "R2", "R8", "R6", "R7", "R3", "R1"]:
    e = by[k]["E_pool"]; pn = by[k]["PN_excess_alpha_le2"]
    ci = json.loads(e["boot_ci95"])
    rows.append([names_r[k], "yes" if e["A1_transferable"] == "True" else "no", e["n"], ("+" if e["orientation"] == "1" else "-"), f"{float(e['rho']):+.2f} [{ci[0]:.2f}, {ci[1]:.2f}]", f"{float(e['rho_oriented']):+.2f}", f"{float(e['p_perm_two_sided']):.2f}",
                 f"{float(by[k]['E1']['rho_oriented']):+.2f} / {float(by[k]['E2']['rho_oriented']):+.2f}", f"{float(pn['rho_oriented']):+.2f}",
                 f2(e["partial_rho_given_K"]), f2(e["auc_oriented_movable"]), e["holm_p_descriptive"] or "n/a", e["flag"] or ""])
T["rivals_scores"] = md(["Rival", "Frozen for new tasks", "Tasks", "Predicted sign", "Spearman with pooled escape fraction [95% bootstrap]", "Oriented", "Two-sided permutation p", "Oriented Spearman, alpha 1 / alpha 2", "Oriented Spearman with plan-noise excess", "Partial given catalogue size", "AUC for screen movable", "Holm p", "Flag"], rows)

ic = list(csv.DictReader(open(EV / "tables/rivals_intercorr.csv")))
cols = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "K"]
rows = [[names_r[r["rival"]]] + [f"{float(r[c]):.2f}" for c in cols] for r in ic]
T["rivals_ic"] = md(["Rival"] + [names_r[c] for c in cols], rows)

Path(__file__).with_name("tables_part1.json").write_text(json.dumps(T, indent=0))
if __name__ == "__main__":
    for k, v in T.items():
        print("=====", k); print(v[:3000]); print()
