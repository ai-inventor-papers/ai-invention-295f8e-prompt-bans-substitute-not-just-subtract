"""Tables of the iteration-5 experiments (transplant, panels A and B, knobs, Gemma)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from make_tables import W, X24, X25, X26, X27, X28, a, comp, md, conv_md_table, grab, f2
from names import TASK, task
T = {}

# ---------------- exp24: transplant ----------------
s24 = (X24 / "results/summary.md").read_text()
br = json.load(open(X24 / "results/base_repertoire.json"))["per_task"]
rows = []
for t, v in br.items():
    bc = v["base_chat"]
    ci = v["beta_ci"]
    rows.append([task(t), f"{a(v['default'], t)} ({v['twin_default_share']:.2f})", f"{v['n_correct_base']} of {bc['n']}",
                 comp(bc["composition_correct"], t), f"{v['beta']:.2f} [{ci[0]:.2f}, {ci[1]:.2f}] ({v['beta_basis'].lower()})",
                 f"{v['stratum'].lower()} ({v['stratum_stability']:.2f})", a(v["r_t"], t),
                 f"{v['base_plain']['beta_plain']:.2f}", f"{v['base_hill1_rarefied']['hill1']:.2f}"])
T["base_rep"] = md(["Task", "Instruct default (twin share)", "Base correct / N", "Base correct programs (chat template)", "beta [95% CI] (basis)", "Stratum (stability)", "Base runner-up", "beta, plain completion", "Base Hill-1 (depth 25)"], rows)

sel = grab(s24, "### Stage 3 selection on S1")
T["selection"] = conv_md_table(sel)
conf = grab(s24, "### Stage 4 confirmation on fresh S2 slots")
conf = conf.replace("MR1.0", "matched random, lambda 1").replace("XT1.0", "cross-task, lambda 1").replace("MRP0.5", "pass-matched random, 0.5")
conf = re.sub(r"MR0\.(\d+)", r"matched random, 0.\1", conf); conf = re.sub(r"XT0\.(\d+)", r"cross-task, 0.\1", conf)
T["confirmation"] = conv_md_table(conf)
ds = grab(s24, "### Claim D (de-sharpening push")
T["claimD"] = conv_md_table(ds.replace("DS 0.5 / 1 / 2", "push along unit(D), alpha 0.5 / 1 / 2").replace("ISO 0.5 / 1 / 2", "isotropic push, alpha 0.5 / 1 / 2").replace("a_DS", "escape dose, unit(D)").replace("a_ISO", "escape dose, isotropic"))
rv = grab(s24, "### Reverse interchange")
T["reverse"] = conv_md_table(rv.replace("BTWIN", "base twin").replace("RT(1)", "instruct states into base, lambda 1").replace("BMR(1)", "matched random into base"))

# power extension lines
pe = re.findall(r"^- (T\d+|R\d): T pass ([\d.]+), off-share ([\d.]+); vs MR([\d.]+) (\d+):(\d+) p=([\de.\-]+); vs XT([\d.]+) (\d+):(\d+) p=([\de.\-]+)(?:; vs MRP([\d.]+) (\d+):(\d+) p=([\de.\-]+))?", s24, re.M)
rows = []
for m in pe:
    t = m[0]
    rows.append([task(t), m[1], m[2], f"{m[4]}:{m[5]}, p = {m[6]}", f"{m[8]}:{m[9]}, p = {m[10]}", (f"{m[12]}:{m[13]}, p = {m[14]}" if m[11] else "n/a")])
T["power_ext"] = md(["Task", "Transplant pass", "Correct off-default share", "Against matched random (transplant only : random only, one-sided p)", "Against cross-task", "Against pass-matched random"], rows)

# D size
rel_s = re.search(r"relative norm at S, blocks 12-23 \(mean over tasks\): ([\d., ]+)", s24).group(1).split(", ")
rel_r = re.search(r"relative norm at R, blocks 12-23: ([\d., ]+)", s24).group(1).split(", ")
T["dsize"] = md(["Block"] + [str(b) for b in range(12, 24)], [["norm of D / residual norm, task-specification positions"] + rel_s, ["norm of D / residual norm, read position"] + rel_r])
geo = re.findall(r"^- (T\d+|R\d) \(lambda\* ([\d.]+)\): S18 ([\d.]+) \(stress-1 ([\d.]+)\); S23 ([\d.]+) \(stress-1 ([\d.]+)\); S27 ([\d.]+) \(stress-1 ([\d.]+)\); R18 ([\d.]+) \(stress-1 ([\d.]+)\); R23 ([\d.]+) \(stress-1 ([\d.]+)\)", s24, re.M)
T["geometry"] = md(["Task", "lambda", "Task spec, block 18 (stress-1)", "Task spec, block 23", "Task spec, block 27", "Read position, block 18", "Read position, block 23"],
                   [[task(g[0]), g[1], f"{g[2]} ({g[3]})", f"{g[4]} ({g[5]})", f"{g[6]} ({g[7]})", f"{g[8]} ({g[9]})", f"{g[10]} ({g[11]})"] for g in geo])
ec = re.findall(r"^- (T\d+)\|EC_(\w+?)(?:_a1\.0)?: per-slot label agreement ([\d.]+), JS ([\d.]+) \(template-resampling null q95 ([\d.]+)\), within null (yes|no)", s24, re.M)
T["ec24"] = md(["Task", "Cell", "Per-slot label agreement", "JS", "Null 95th percentile", "Within null"], [[task(e[0]), e[1].replace("NEUTRAL", "twin").replace("RAND", "random direction "), e[2], e[3], e[4], e[5]] for e in ec])

# ---------------- exp25: panel A ----------------
s25 = (X25 / "results/summary.md").read_text()
units = grab(s25, "### Units: gate, forecast")
units = units.replace("IMMOVABLE", "immovable").replace("MOVABLE", "movable").replace("GATE_FAIL", "gate failed")
T["A_units"] = conv_md_table(units)
riv = s25.split("### A1 / A2 -- Primary set")[1]
T["A_rivals_primary"] = conv_md_table(grab(riv, "- Panel-level wording"))
riv2 = s25.split("### A1 / A2 -- With the reserve extension")[1]
T["A_rivals_ext"] = conv_md_table(grab(riv2, "- Panel-level wording"))
T["A_a2"] = conv_md_table(grab(riv, "A2: 3 events"))
T["A_assoc_corr"] = conv_md_table(grab(s25, "### POST HOC: association rival"))
T["A_extra"] = conv_md_table(grab(s25, "### Extra arm A"))
T["A_ec"] = conv_md_table(grab(s25, "### Engine check (bf16 vs the screen"))
T["A_ext_ref"] = conv_md_table(grab(s25, "### External cross-check")).replace("segmented sieve.py", "segmented_sieve.py").replace("strings/Manacher.py", "strings/manacher.py")
T["A_repertoire"] = conv_md_table(grab(s25, "### Repertoire check"))
T["A_knobs"] = conv_md_table(grab(s25, "### Knob rows").replace("PLAINC", "plain completion").replace("NOVELTY", "novelty instruction").replace("PN_a1", "plan noise alpha 1").replace("PN_a2", "plan noise alpha 2").replace("T1.3", "temperature 1.3").replace("TWIN", "twin").replace("BASE", "base model"))

# ---------------- exp26: panel B ----------------
r26 = (X26 / "README.md").read_text()
T["B_units"] = conv_md_table(grab(r26, "All 7 new units were base-diverse"))
T["B_rivals"] = conv_md_table(grab(r26, "**Rival predictors**"))
T["B_a2"] = conv_md_table(grab(r26, "**A2 (4 events"))
T["B_parents"] = conv_md_table(grab(r26, "**Within-parent (disguised variants"))

# ---------------- exp27: knobs ----------------
s27 = (X27 / "README.md").read_text()
lit = grab(s27, "- First approach named in the thinking")
T["literal"] = conv_md_table(lit.replace("LIT_REP_T0.7", "T 0.7, repeat").replace("LIT_T", "T "))
c = json.load(open(X27 / "results/claim_c.json"))
rows = []
ci = c["class_ci95"]
for t, v in c["primary"]["per_task"].items():
    th = v["text_H5"]
    pci = ci[t]["PN"]
    rows.append([task(t), f"{v['H5_PN']:.2f} [{pci[0]:.2f}, {pci[1]:.2f}]", f"{th['IFG']:.2f}", f"{th['PSL']:.2f}", f"{th['EAP']:.2f}", f"{th['BINT']:.2f}",
                 {"BINT": "base intent", "EAP": "enumerate and pick", "IFG": "intent factored generation", "PSL": "plan search"}[v["best_text_class"]],
                 "yes" if v["PN_wins"] else "no", f"{c['p_PN_ge_best_text'][t]:.2f}", "unresolved" if c["unresolved"][t] else "", f"{v['D_t']:+.2f}"])
T["claimC"] = md(["Task", "Plan noise H5 [95%]", "Intent factored generation", "Plan search (lite)", "Enumerate and pick", "Base intent", "Best text sampler", "Plan noise wins", "P(plan noise at least best)", "Flag", "Margin D_t"], rows)
rows = []
for t, v in c["nd10_descriptive"].items():
    th = v["text_H5"]
    rows.append([task(t), f"{v['H5_PN']:.2f}", f2(th.get("IFG")), f2(th.get("PSL")), f2(th.get("EAP")), f2(th.get("BINT")), {"BINT": "base intent", "EAP": "enumerate and pick", "IFG": "intent factored generation", "PSL": "plan search"}[v["best_text_class"]]])
T["claimC_nd"] = md(["Task (descriptive, N = 30 per cell)", "Plan noise H5", "Intent factored generation", "Plan search (lite)", "Enumerate and pick", "Base intent", "Best text sampler"], rows)
sens = c["sensitivities"]
rows = []
names_s = {"IFG_hot_only": "intent factored generation at (1.3, 0.7) only", "PN_plus": "plan noise hull adds the plain prompt arms", "edge_restricted_hull": "edge-restricted hull", "leftpad_arms_dropped": "left-padded multi-stage samplers dropped (intent factored generation remains)", "style_regate_flagged_excluded": "style re-gate flagged task excluded", "novelty_audit_relabelled": "novelty-audit relabels applied"}
for k, v in sens.items():
    wins = sum(1 for t in v["per_task"].values() if t["PN_wins"])
    rows.append([names_s.get(k, k), v.get("verdict", ""), f"{wins} of 5", f"{v['D_bar']:+.2f}" if "D_bar" in v else "n/a"])
T["claimC_sens"] = md(["Sensitivity", "Verdict", "Tasks where plan noise wins", "Mean margin"], rows)
pd = grab(s27, "### PN vs departure-matched decoding")
T["pn_dmd"] = conv_md_table(pd.replace("T_dmd", "DMD temperature").replace("K_PN", "plan noise KL per token").replace("f_on", "DMD KL per token").replace("| PN |", "| plan noise |").replace("| DMD |", "| DMD |"))
pt = grab(s27, "### PN plain vs PN twin")
T["pn_plain_twin"] = conv_md_table(pt)
ce = grab(s27, "### Engine check (bf16 here vs exp19")
T["ec27"] = conv_md_table(ce.replace("NEUTRAL", "twin").replace("RAND9002_a1.0", "random direction 9002, alpha 1").replace("RAND9004_a1.0", "random direction 9004, alpha 1").replace("TOPK10", "top-k 10").replace("|T1.3", "|temperature 1.3"))
cells = json.load(open(X27 / "results/cells.json"))
armn = {"TWIN": "twin", "PLAIN": "plain prompt", "PN_a1": "plan noise alpha 1", "PN_a2": "plan noise alpha 2", "PNPLAIN_a1": "plan noise alpha 1, plain prompt",
        "IFG_hot": "intent factored generation (1.3, 0.7)", "IFG_paper": "intent factored generation (0.73, 0.60)", "PSL": "plan search (lite)", "EAP": "enumerate and pick", "BINT": "base intent",
        "DMD_a1": "departure-matched decoding, alpha 1 match", "DMD_a2": "departure-matched decoding, alpha 2 match", "T1.3": "temperature 1.3", "TOPK10": "top-k 10", "NOVELTY": "novelty instruction", "SEMSEED": "semantic seed"}
rows = []
for t in ["T03", "T10", "T2", "T05", "T1"]:
    for arm in ["TWIN", "PLAIN", "PN_a1", "PN_a2", "PNPLAIN_a1", "IFG_hot", "IFG_paper", "PSL", "EAP", "BINT", "DMD_a1", "DMD_a2", "T1.3", "TOPK10", "NOVELTY", "SEMSEED"]:
        k = f"{t}|{arm}"
        if k not in cells: continue
        v = cells[k]
        rows.append([task(t), armn[arm], v["N"], f"{v['pass']:.2f}", f"{v['invalid_rate']:.2f}", comp(v["correct_composition"], t), f"{v['hill_rarefied']:.2f} ({v['hill_depth']})"])
T["c27_cells"] = md(["Task", "Arm", "N", "Pass", "Invalid", "Correct programs", "Hill-1 (depth)"], rows)

# ---------------- exp28: Gemma ----------------
r28 = (X28 / "README.md").read_text()
T["G_units"] = conv_md_table(grab(r28, "### Per-unit results").replace("INTERMEDIATE", "intermediate").replace("COLLAPSED", "collapsed").replace("DIVERSE", "diverse"))
T["G_rivals"] = conv_md_table(grab(r28, "- **Verdict: INCONCLUSIVE**").replace("twin_modal_share", "twin modal share").replace("novelty_off_cat", "novelty instruction off-default").replace("opening_margin", "opening margin").replace("merit_gap_runtime", "runtime merit gap").replace("merit_gap_tokens", "token merit gap"))
sens28 = grab(r28.split("- **Verdict: INCONCLUSIVE**")[1], "| Rival | sign")
gs = "| Sensitivity | n | ρ |" + r28.split("| Sensitivity | n | ρ |")[1].split("\n\n")[0]
for k, v in {"beta_pt_chat": "beta from the base model under the chat template only", "beta_pt_plain": "beta from plain completion only", "beta_pt_pooled": "beta pooled over both formats (primary)", "beta_excl_other": "beta with other excluded", "beta_correct_programs_only_any_n": "beta from correct programs only, any N", "beta_pooled_with_rejudged_disputed_rows": "beta with disputed rows re-judged", "E_off_any_exp23_definition": "escape defined as any off-default attempt (iteration-4 definition)", "E_off_corr": "escape counted on correct programs only", "E_u_max": "escape fraction as the maximum over alpha", "without_regate_flagged_tasks": "without the task flagged by the style re-gate", "secondary_target_pn_excess": "secondary target: plan-noise excess", "descriptive_beta_vs_exp23_E_t": "beta against the iteration-4 escape fraction"}.items():
    gs = gs.replace("| " + k + " |", "| " + v + " |")
T["G_sens"] = gs
T["G_a2"] = conv_md_table(grab(r28, "- **Verdict: PASS**"))
T["G_transplant"] = conv_md_table(grab(r28, "λ = 1.0 (0 of 7 S_T tasks broke at λ = 1)."))
T["G_collapsed"] = conv_md_table(grab(r28, "Support share among valid S_T tasks"))
T["G_pn"] = conv_md_table(grab(r28, "### Plan noise (descriptive"))

Path(__file__).with_name("tables_part2.json").write_text(json.dumps(T, indent=0))
for k, v in T.items():
    print("=====", k); print(v[:2500]); print()
