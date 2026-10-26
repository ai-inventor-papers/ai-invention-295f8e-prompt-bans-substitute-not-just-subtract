"""Build the iteration-7 report tables from the artifacts' own output files.

Every number in the generated tables is read from an artifact file; nothing is typed by hand.
Output: work/tables7.json (key -> markdown table, with caption lines where given).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "round-7"
E6 = ROOT / "evaluation-6/src"
X33 = ROOT / "experiment-33/src"
X34 = ROOT / "experiment-34/src"
X35 = ROOT / "experiment-35/src"
X36 = ROOT / "experiment-36/src"
X37 = ROOT / "experiment-37/src"
X38 = ROOT / "experiment-38/src"
OUT = Path(__file__).with_name("tables7.json")

ALG = {
    "bf_spfa": "Bellman-Ford/SPFA", "dijkstra": "Dijkstra", "floyd": "Floyd-Warshall", "bidijkstra": "bidirectional Dijkstra",
    "dial": "Dial", "union_find": "union find", "dfs": "DFS", "bfs": "BFS", "full_sort": "full sort", "quickselect": "quickselect",
    "size_k_heap": "size-k heap", "heapify_pop": "heapify and pop", "counting_sort": "counting sort",
    "median_of_medians": "median of medians", "prim_heap": "Prim with heap", "kruskal": "Kruskal",
    "prefix_suffix_max": "prefix and suffix maxima", "two_pointers": "two pointers", "peak_split": "peak split",
    "sort_compare": "sort and compare", "fixed_count_array": "fixed count array", "hash_count": "hash count",
    "dijkstra_unit": "unit weight Dijkstra", "bibfs": "bidirectional BFS", "idastar": "IDA*", "jps": "jump point search",
    "biastar": "bidirectional A*", "gbfs": "greedy best first", "astar": "A*", "iddfs": "IDDFS", "other": "other",
    "disputed": "disputed", "invalid": "invalid", "unknown": "unknown", "hash_map": "hash map",
    "quickselect+size_k_heap": "quickselect or size-k heap",
}


def alg(x):
    return ALG.get(x, x)


def comp(d):
    """{'dijkstra': 29, 'bf_spfa': 1} -> 'Dijkstra 29, Bellman-Ford/SPFA 1'"""
    if not d:
        return "none"
    return ", ".join(f"{alg(k)} {v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))


def compstr(s):
    """Translate a printed python dict string."""
    s = s.strip()
    if s in ("{}", ""):
        return "none"
    try:
        d = eval(s, {"__builtins__": {}})  # noqa: S307  (artifact-printed literal dicts only)
        if isinstance(d, dict):
            return comp(d)
    except Exception:
        pass
    return s


def f(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, str):
        return x
    if x == float("inf"):
        return "not reached"
    if isinstance(x, int):
        return str(x)
    if abs(x) < 1e-3 and x != 0:
        return f"{x:.1e}"
    return f"{x:.{nd}f}"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["-"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def src_name(s):
    m = {"ban": "fifth-template ban source", "W4": "fourth-template ban source", "F_bf_spfa": "forced Bellman-Ford/SPFA source",
         "F_floyd": "forced Floyd-Warshall source", "F_bfs": "forced BFS source", "F_dfs": "forced DFS source",
         "F_quickselect": "forced quickselect source", "F_counting_sort": "forced counting sort source"}
    return m.get(s, s)


def arm_name(code):
    code = code.strip()
    pats = [
        (r"^DASLY2_(.+)_k(\d+)$", lambda m: f"DAS (likelihood objective), second seed, {src_name(m[1])}, rank {m[2]}"),
        (r"^DASLY_W4_k(\d+)$", lambda m: f"DAS (likelihood objective), fourth-template ban source, rank {m[1]}"),
        (r"^DASLY_(.+)_k(\d+)$", lambda m: f"DAS (likelihood objective), {src_name(m[1])}, rank {m[2]}"),
        (r"^DAS_(.+)_k(\d+)$", lambda m: f"DAS (committed contrastive objective), {src_name(m[1])}, rank {m[2]}"),
        (r"^PERMLY_(.+)_k(\d+)$", lambda m: f"permuted-label DAS, {src_name(m[1])}, rank {m[2]}"),
        (r"^RAND_(.+)_k(\d+)_d(\d)$", lambda m: f"random subspace {m[3]}, {src_name(m[1])}, rank {m[2]}"),
        (r"^RAND_(.+)_k(\d+)$", lambda m: f"random subspace, {src_name(m[1])}, rank {m[2]}"),
        (r"^RPOSLY_(.+)_k(\d+)$", lambda m: f"read-position DAS, {src_name(m[1])}, rank {m[2]}"),
        (r"^RPOSFULL_(.+)$", lambda m: f"read-position full-state exchange, {src_name(m[1])}"),
        (r"^DIM1_(.+)$", lambda m: f"difference in means (rank 1), {src_name(m[1])}"),
        (r"^PCA16_(.+)$", lambda m: f"PCA-16 subspace, {src_name(m[1])}"),
        (r"^NULLLY_k(\d+)$", lambda m: f"null source (forced default), DAS rank {m[1]}"),
        (r"^NULL_full$", lambda m: "null source (forced default), full-state exchange"),
        (r"^BASE_PAD$", lambda m: "padding twin (base for forced sources)"),
        (r"^BASE_W(\d)$", lambda m: f"neutral twin of template {m[1]} (base)"),
        (r"^FULL_W4$", lambda m: "full-state exchange, fourth-template ban source"),
        (r"^FULL_ban_L(\d+)$", lambda m: f"full-state exchange, ban source, block {m[1]} only"),
        (r"^FULL_ban_band$", lambda m: "full-state exchange, ban source, blocks 12-23"),
        (r"^FULL_F_(.+)$", lambda m: f"full-state exchange, forced {alg(m[1])} source"),
        (r"^FULLF3_(.+)_L(\d+)$", lambda m: f"full-state exchange, forced {alg(m[1])} (family 3), block {m[2]} only"),
        (r"^FULLF3_(.+)_band$", lambda m: f"full-state exchange, forced {alg(m[1])} (family 3), blocks 12-23"),
        (r"^PADBASE_F3_(.+)$", lambda m: f"padding twin of forced {alg(m[1])} (family 3)"),
        (r"^LAM([\d.]+)_ban_k(\d+)$", lambda m: f"rank-{m[2]} DAS edit scaled by lambda {m[1]}, ban source"),
        (r"^MGEN_instr_new$", lambda m: "short instruction to make a new algorithm"),
        (r"^MGEN_instr_novel$", lambda m: "2,000-word novelty instruction"),
        (r"^MGEN_p0$", lambda m: "neutral prompt"),
        (r"^MGEN_seed_rand1$", lambda m: "random seed 1 (seed=d32qxk4nt43)"),
        (r"^MGEN_seed_rand2$", lambda m: "random seed 2 (seed=(horse chair roof love))"),
        (r"^MGEN_seed_sem$", lambda m: "semantic seed"),
        (r"^REVLY_k(\d+)$", lambda m: f"reverse interchange, DAS rank {m[1]}"),
        (r"^REV_full$", lambda m: "reverse interchange, full state"),
    ]
    for p, fn in pats:
        m = re.match(p, code)
        if m:
            return fn(m)
    return code


TF_EDIT = [
    (r"^full$", lambda m: "full-state exchange"),
    (r"^DASLY_k(\d+)$", lambda m: f"DAS, likelihood objective, rank {m[1]}"),
    (r"^PERMLY_k(\d+)$", lambda m: f"permuted-label DAS, likelihood objective, rank {m[1]}"),
    (r"^PROJLY_k(\d+)$", lambda m: f"DAS (likelihood) projected on top-64 natural PCs, rank {m[1]}"),
    (r"^RPOSLY_k(\d+)$", lambda m: f"read-position DAS, likelihood objective, rank {m[1]}"),
    (r"^DAS_k(\d+)$", lambda m: f"DAS, committed contrastive objective, rank {m[1]}"),
    (r"^PERM_k(\d+)$", lambda m: f"permuted-label DAS, contrastive objective, rank {m[1]}"),
    (r"^PROJ_k(\d+)$", lambda m: f"DAS (contrastive) projected on top-64 natural PCs, rank {m[1]}"),
    (r"^RPOS_k(\d+)$", lambda m: f"read-position DAS, contrastive objective, rank {m[1]}"),
    (r"^RAND1_k(\d+)$", lambda m: f"random subspace, rank {m[1]}"),
    (r"^DIM1$", lambda m: "difference in means (rank 1)"),
    (r"^PCA16$", lambda m: "PCA-16 subspace"),
    (r"^RPOSFULL$", lambda m: "read-position full-state exchange"),
]


def tf_edit(code):
    for p, fn in TF_EDIT:
        m = re.match(p, code.strip())
        if m:
            return fn(m)
    return code


def md_tables(path):
    """Return list of (heading, [table lines]) from a markdown file."""
    lines = Path(path).read_text().splitlines()
    out, head, cur = [], None, []
    for ln in lines:
        if ln.startswith("#"):
            if cur:
                out.append((head, cur)); cur = []
            head = ln.lstrip("#").strip()
        elif ln.startswith("|"):
            cur.append(ln)
        else:
            if cur:
                out.append((head, cur)); cur = []
    if cur:
        out.append((head, cur))
    return out


def rows_of(tl):
    return [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in tl[2:]]


T = {}

# ---------------- record audit (evaluation 6) ----------------
cj = json.loads((E6 / "corrections.json").read_text())
rows = []
for c in cj["corrections"]:
    vals = c.get("values") or []
    st = {}
    for v in vals:
        s = v.get("status") if isinstance(v, dict) else None
        if s:
            st[s] = st.get(s, 0) + 1
    rat = (c.get("rationale") or "").replace("|", "/").replace("\n", " ")
    rat = re.split(r"(?<=[.;])\s", rat)[0][:260]
    loc = c["section"] + (f", {c['table']}" if c.get("table") else "")
    ITEM = {"0a": "Stage A metric", "0b": "post-hoc site", "0c": "Gemma claims", "0d": "synthesis", "0e": "geometry figures", "0f": "top-five dose",
            "0g": "Table 238", "0h": "NLA pseudoreplication", "0i": "executed checks", "0j": "Section 4.9", "0k": "positioning", "0l": "verdict tags"}
    rows.append([c["id"].replace("C7-", ""), ITEM.get(c["item"], c["item"]), loc, c["kind"].replace("_", " "),
                 ", ".join(f"{k} {v}" for k, v in sorted(st.items())) or "wording only", rat])
T["e6_corrections"] = table(["No.", "Review item", "Location", "Kind", "Values behind it", "What changed (first sentence of the rationale)"], rows)

# ---------------- DAS experiment (exp 33) ----------------
S33 = md_tables(X33 / "results/summary.md")


def tr_cell(c):
    c = c.strip()
    if c.startswith("{") and c.endswith("}"):
        return compstr(c)
    c = re.sub(r"\(p([\d.]+)\)", r"(pass \1)", c)
    c = c.replace("PERMLYk16", "permuted rank 16").replace("PERMLYk2", "permuted rank 2").replace("PERMLYk1", "permuted rank 1")
    for k, v in ALG.items():
        c = re.sub(rf"\b{re.escape(k)}\b", v, c) if "_" in k or k in ("bf_spfa", "floyd", "dijkstra", "bfs", "dfs") else c
    return c


def grab(heading_prefix, idx=0):
    hits = [t for h, t in S33 if h and h.startswith(heading_prefix)]
    return hits[idx] if len(hits) > idx else None


# site selection
tl = grab("Site selection")
rows = []
for r in rows_of(tl):
    rows.append([r[0], r[1], r[2], r[3], r[4], tr_cell(r[5]), r[6]])
T["x33_site"] = table(["Task", "Block chosen by teacher forcing (L*)", "Single-block teacher-forced gain at L* (nats)", "Band 12-23 teacher-forced gain (nats)",
                       "Ban source, correct Y of 30: full state at L* / band 12-23 / base", "Forced source (family 3), correct Y of 30: at L* / band / base", "Site used"], rows)

# P1 tables per task
p1 = [t for h, t in S33 if h and h.startswith("P1: held-out generation")]
allp1 = [t for h, t in S33 if h and h.startswith("P1")]
# the P1 section holds 6 tables: per task source table + pooled table
p1tabs = [t for h, t in S33 if h and h.startswith("P1:")]
names = ["T2", "T10", "T03"]
for i, task in enumerate(names):
    st = p1tabs[2 * i]
    pt = p1tabs[2 * i + 1]
    rows = []
    for r in rows_of(st):
        rows.append([src_name(r[0]), alg(r[1])] + [tr_cell(x) for x in r[2:]])
    T[f"x33_p1_{task}"] = table(["Source", "Target Y", "Base (twin)", "Full-state exchange", "DAS rank 1", "rank 2", "rank 4", "rank 8", "rank 16",
                                 "Random subspaces, rank 16", "Permuted-label DAS", "Pass rate base / full state"], rows)
    rows = [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows_of(pt)]
    T[f"x33_pool_{task}"] = table(["Rank k", "Pooled recovery [slot bootstrap 95%]", "Random-subspace recovery", "McNemar DAS against random b:c (p)",
                                   "Permuted-label transfer (max)", "Smallest pass ratio"], rows)

for task in names:
    tl = grab(f"Controls {task}")
    rows = [[(arm_name(r[0].replace(" (N = 10)", "")) + (" (N = 10)" if "(N = 10)" in r[0] else "")).replace("DAS (likelihood objective), W4", "DAS (likelihood objective), fourth-template ban source"), r[1], r[2], r[3], r[4]] for r in rows_of(tl)] if tl else []
    T[f"x33_ctrl_{task}"] = table(["Arm", "Correct Y (or correct off-default) count of 30", "Base", "Transfer", "Pass"], rows) if rows else "(no control rows were run on this task)"

tl = grab("C: routing")
rows = []
for r in rows_of(tl):
    rows.append([r[0], alg(r[1])] + [x for x in r[2:6]] + [compstr(r[6]), compstr(r[7])])
T["x33_routing"] = table(["Task", "Forced Y", "Full-state exchange: correct Y / correct off-default [CP 95%]", "DAS rank 1", "DAS rank 4", "DAS rank 16",
                          "Landing under the full-state exchange", "Landing under DAS rank 16"], rows)

tl = grab("Committed contrastive map")
rows = []
for r in rows_of(tl):
    rows.append([r[0], arm_name(r[1]), r[2], r[3], compstr(r[4]), r[5], compstr(r[6]).replace("fence", "fence stop").replace("stop ", "end-of-text ").replace("length", "length cap")])
T["x33_pilot"] = table(["Task", "Arm (committed contrastive map)", "Correct Y (base)", "Pass (base)", "Labels", "Mean new tokens", "Finish reason"], rows)

fits = [(h, t) for h, t in S33 if h and h.startswith("Fits ")]
rows = []
for h, t in fits:
    obj = "likelihood (amended)" if "_ly_" in h else "contrastive (committed)"
    task = h.split("_")[-1]
    for r in rows_of(t):
        fitname = {"MAIN": "main", "PERM": "permuted labels", "RPOS": "read position", "MAIN_LY": "main", "PERM_LY": "permuted labels", "RPOS_LY": "read position"}.get(r[0], r[0])
        rows.append([task, obj, fitname, r[1], r[2], r[3], r[4], r[5], r[6]])
T["x33_fits"] = table(["Task", "Objective", "Fit", "Steps run (budget)", "Best step", "Best validation gain (nats)", "Rank-16 validation gain at the last step", "Orthonormality error", "Seconds"], rows)

for h, t in S33:
    if h and h.startswith("Held-out teacher-forced evaluation"):
        key = h.split()[-1]
        rows = [[r[0], tf_edit(r[1]), r[2], r[3], r[4], r[5], r[6], r[7]] for r in rows_of(t)]
        T[f"x33_{key}"] = table(["Pairs", "Edit", "n", "Mean gain (nats)", "Full-state gain", "Teacher-forced recovery", "Change in log-likelihood of Y programs", "Change in log-likelihood of default programs"], rows)

tl = grab("Dormant-subspace checks")
T["x33_dormant"] = table(["Task", "Rank k", "Natural variance share", "Random mean", "Percentile against 1,000 random subspaces", "Top-k PCA (upper bound)", "Twin-only share",
                          "Held-out displacement share (random k/4096)", "Projected-map teacher-forced retention"], rows_of(tl))

tl = grab("M behaviour")
mapn = {"instr_new": "short instruction to make a new algorithm", "instr_novel": "2,000-word novelty instruction", "p0": "neutral prompt",
        "seed_rand1": "random seed 1 (seed=d32qxk4nt43)", "seed_rand2": "random seed 2 (seed=(horse chair roof love))", "seed_sem": "semantic seed"}
rows = [[mapn.get(r[0], r[0]), r[1], compstr(r[2]), r[3], r[4]] for r in rows_of(tl)]
T["x33_mbeh"] = table(["Prompt", "Pass", "Correct composition", "Correct off-default [CP 95%]", "Truncated"], rows)

tl = grab("Second DAS init seed")
rows = [[arm_name(r[0]), r[1], r[2], r[3], r[4]] for r in rows_of(tl)]
T["x33_seed2"] = table(["Arm", "Seed 1 correct Y of 30", "Seed 2 correct Y of 30", "Discordant seed-1-only : seed-2-only (p)", "Pass, seed 2"], rows)

tl = grab("M: manifold placement")
mp = {"T2|ban|W1|-": "ban, first template", "T2|ban|W2|-": "ban, second template", "T2|ban|W3|-": "ban, third template",
      "T2|ban|W4|-": "ban, fourth template", "T2|ban|W5|-": "ban, fifth template", "T2|p0|-|-": "neutral prompt",
      "T2|seed_rand1|-|-": "random seed 1 (seed=d32qxk4nt43)", "T2|seed_rand2|-|-": "random seed 2 (seed=(horse chair roof love))",
      "T2|instr_new|-|-": "short instruction to make a new algorithm", "T2|instr_novel|-|-": "2,000-word novelty instruction", "T2|seed_sem|-|-": "semantic seed"}
rows = [[mp.get("|".join(r[0:4]), "|".join(r[0:4])), r[4], r[5], r[6], r[7]] for r in rows_of(tl)]
T["x33_mplace"] = table(["Prompt (shortest path)", "Distance D to the default centroid (rank-16 DAS coordinates)", "Null percentile", "Inside the null 95%", "Coordinate along the runner-up axis"], rows)

tl = grab("R: discreteness")
rows = [[r[0], r[1], r[2], r[3], compstr(r[4])] for r in rows_of(tl)]
T["x33_lambda"] = table(["Lambda", "Correct Bellman-Ford/SPFA (of 20)", "Correct Dijkstra", "Pass", "Labels"], rows)

tl = grab("Every generation cell")
rows = []
for r in rows_of(tl):
    rows.append([r[0], arm_name(r[1]), r[2], r[3], r[4], compstr(r[5])])
T["x33_cells"] = table(["Task", "Arm", "n", "Pass", "Truncated", "Correct composition"], rows)

# M section text lines (geodesic tables) from summary
txt = (X33 / "results/summary.md").read_text()
m = re.search(r"Centroid coordinates along the runner-up axis: (\{.*?\})", txt)
cent = eval(m.group(1), {"__builtins__": {}})
m2 = re.search(r"Implemented counts: (\{.*\}\})", txt)
imp = eval(m2.group(1), {"__builtins__": {}})
algs = ["dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"]
rows = []
for a in algs:
    rows.append([alg(a), cent[a], imp["twin"][a], imp["base_model"][a], imp["knobs_this_artifact"][a], imp["knobs_exp29_random_directions"][a], imp["knobs"][a]])
T["x33_centroids"] = table(["Algorithm", "Centroid coordinate along the runner-up axis", "Implemented under the twin", "Implemented by Qwen3-8B-Base",
                            "Implemented under this artifact's knobs", "Implemented under the 40 random directions of the engine control", "All knobs"], rows)
geo = re.findall(r"- kNN (\d+): leave-one-survivor bans, mean survivor rank ([\d.]+) of 5 \(random relabelling p ([\d.]+)\); unreachable pairs (\d+)\n  - geodesic centroid table: (\{.*?\}\})", txt)
rows = []
for k, rank, p, unreach, tab in geo:
    g = eval(tab, {"__builtins__": {}})
    rows.append([k, rank, p, unreach] + [g["dijkstra"][a] for a in algs] + [g["bf_spfa"]["floyd"]])
T["x33_geodesic"] = table(["k of the neighbour graph", "Mean survivor rank of leave-one-survivor bans (of 5)", "Random relabelling p", "Unreachable pairs",
                           "Geodesic Dijkstra to Dijkstra (spread)", "to Bellman-Ford/SPFA", "to bidirectional Dijkstra", "to Floyd-Warshall", "to Dial", "Bellman-Ford/SPFA to Floyd-Warshall"], rows)

# ---------------- fork / axis experiment (exp 34) ----------------
fk = json.loads((X34 / "results/forks.json").read_text())
t10 = fk["tasks"]["T10"]
rows = []
for pos in ("10", "11"):
    for tid, v in sorted(t10["token_maps"][pos].items(), key=lambda kv: -kv[1]["n"]):
        rows.append([pos, f"`{v['tok']}`", v["n"], comp(v["labels"]), f(v["q"]), "yes" if v["mapped"] else "no"])
T["x34_t10map"] = table(["Generated token index", "Token", "Continuations", "Labels of the continuations", "Off-default share q", "Mapped"], rows)
rows = []
for task in ("T10", "T2", "T03"):
    v = fk["tasks"][task]
    paths = v.get("per_path", {})
    bycell = {}
    for p in paths.values():
        c = p.get("cell"); bycell.setdefault(c, [0, 0]); bycell[c][0] += 1; bycell[c][1] += 1 if p.get("fork") else 0
    ent = v.get("entropy", {})
    ent_s = "; ".join(f"token {k}: H(label) {e['H_label_bits']:.2f} -> H(label | token) {e['H_label_given_token_bits']:.2f} bits (n {e['n']})" for k, e in ent.items()) or "-"
    rows.append([task, v["status"], ", ".join(map(str, v["forks"])) or "none", json.dumps(v["forks_off_default_by_class"]).replace('"', "") or "-",
                 v["n_paths"], v["n_paths_sig"], "; ".join(f"{c} {n[0]} ({n[1]} with a fork)" for c, n in bycell.items()), v.get("opening_len_majority"), ent_s])
T["x34_forks"] = table(["Task", "Status", "Forks along the default opening (token index)", "Change points off the default opening", "Base paths", "Paths with a significant change point",
                        "Base paths by cell", "Majority opening length (tokens)", "Label entropy at the forks"], rows)

fa = json.loads((X34 / "results/f_analysis.json").read_text())
rows = []
for task in ("T10", "T2"):
    v = fa["F"][task]
    rows.append([task, v["n"], f(v["rho"]), f(v["p_perm"], 4), f"[{v['ci'][0]:.2f}, {v['ci'][1]:.2f}]", f(v["kendall"]), f(v["rho_max_ties"]), v["n_y_pos"],
                 f(v["auc_confirmed"]), v["n_confirmed"], f(v["attempted"]["rho"]), f(v["llr48"]["rho"]), f(v["twin_m"])])
T["x34_F"] = table(["Task", "Directions", "Spearman (margin, correct off-default share)", "Permutation p", "95% CI", "Kendall tau", "Tie ceiling", "Directions with y > 0",
                    "AUC for confirmed escapers", "Confirmed escapers", "Spearman with the attempted share", "Spearman with the 48-token opening LLR", "Twin margin (nats)"], rows)
cal = fa["F"]["calibration"]
T["x34_Fcal"] = ("Pooled within-task Spearman " + f(fa["F"]["pooled"]["rho"]) + " (permutation p " + f(fa["F"]["pooled"]["p_perm"], 4) + "); binomial GLM over "
                 + str(cal["n_cells"]) + " cells: intercept " + f(cal["b0"]) + ", slope " + f(cal["b1"]) + ", held-out MAE " + f(cal["mae_heldout_mean"]) +
                 " (10 splits " + ", ".join(f(x) for x in cal["mae_heldout_splits"]) + "); parameter-free MAE " + f(cal["mae_param_free_correct"]) +
                 " (correct) and " + f(cal["mae_param_free_attempted"]) + " (attempted); all-cell Spearman " + f(cal["all_cell_spearman"]) + ".")

cell_name = {"BAN": "ban (fifth template)", "FORCED": "forced runner-up prompt", "FORCEDPAD": "padding twin of the forced prompt",
             "FORCEDX_0-35": "forced prompt's task-specification states exchanged in, blocks 0-35", "PLACEBO": "placebo twin", "PN_a1": "per-sample plan noise, alpha 1",
             "PN_a2": "per-sample plan noise, alpha 2", "TWIN": "neutral twin", "X_0-11": "ban states exchanged in, blocks 0-11", "X_0-35": "ban states exchanged in, blocks 0-35",
             "X_12-23": "ban states exchanged in, blocks 12-23", "X_24-35": "ban states exchanged in, blocks 24-35"}
cells = cal["cells"]
rows = []
for task in ("T10", "T2"):
    for c in cells:
        t, nm = c["cell"].split("|", 1)
        if t != task or nm.startswith("POP_"):
            continue
        rows.append([task, cell_name.get(nm, nm), f(c["m"]), f(c["Pbar"], 3), f(c["y"]), f(c["att"]), c["n"]])
T["x34_cells"] = table(["Task", "Cell", "Teacher-forced margin m (nats; 48-token LLR on T2)", "Implied off-default probability", "Correct off-default share y", "Attempted off-default share", "n"], rows)
rows = []
byseed = {}
for c in cells:
    t, nm = c["cell"].split("|", 1)
    if nm.startswith("POP_"):
        s = nm.split("_")[1][1:]
        byseed.setdefault(s, {})[t] = c
pa = json.loads((X34 / "results/p2_analysis.json").read_text())
for s in sorted(byseed):
    a, b = byseed[s].get("T10"), byseed[s].get("T2")
    rows.append([s, f(a["m"]), f(a["y"]), f(a["att"]), a["n"], f(b["m"]), f(b["y"]), f(b["att"]), b["n"]])
T["x34_dirs"] = table(["Direction seed", "Connected components: margin m (nats)", "correct off-default y", "attempted", "n", "Shortest path: 48-token LLR (nats)", "correct off-default y", "attempted", "n"], rows)

t3 = json.loads((X34 / "results/t03_confirmation.json").read_text())
rows = [[r["seed"], f(r["b"], 3), f(r["m"]), f(r["y"]), f(r["att"])] for r in t3["rows"]]
T["x34_t03"] = table(["Fresh direction seed", "Axis projection b", "Opening margin m (20-token LLR, nats)", "Correct off-default y (of 10)", "Attempted"], rows)
T["x34_t03_sum"] = (f"Directions {t3['n_directions']}, with y > 0 on {t3['n_y_pos']}; Spearman of m with y {f(t3['m']['rho'])} (one-sided p {f(t3['m']['p_one_sided'], 4)}), "
                    f"of b with y {f(t3['b']['rho'])} (p {f(t3['b']['p_one_sided'], 3)}); with the attempted share m {f(t3['attempted']['m_rho'])}, b {f(t3['attempted']['b_rho'])}; tie ceiling {f(t3['rho_max_ties'])}.")

rows = []
for task in ("T10", "T2"):
    v = pa["P2"][task]
    c = v["competitors"]
    rows.append([task, f(v["rho_b"]), f(v["p_perm"], 3), f"[{v['ci'][0]:.2f}, {v['ci'][1]:.2f}]", f(v["kendall"]), f(v["rho_b_m"]), f(c["pi_Pt"]["rho"]), f(c["norm"]["rho"]), f(c["a_share"]["rho"]),
                 f"{c['pi_Pt']['diff']['diff']:.2f} [{c['pi_Pt']['diff']['lo']:.2f}, {c['pi_Pt']['diff']['hi']:.2f}]", f(v["attempted"]["rho"]), f(v["auc_confirmed"]), "no" if not v["ahead_all"] else "yes"])
T["x34_P2"] = table(["Task", "Spearman of the axis projection b with y", "Permutation p", "95% CI", "Kendall tau", "Spearman of b with the fork margin", "Forced-prompt subspace energy",
                     "Raw displacement norm", "Energy share of the iteration-4 subspace", "b minus forced-subspace energy [95%]", "b with the attempted share", "AUC for confirmed escapers", "Ahead of every competitor"], rows)
lp = {t: pa["P2"][t]["layer_profile"] for t in ("T10", "T2")}
rows = [[L, f(lp["T10"][L]), f(lp["T2"][L])] for L in sorted(lp["T10"], key=int)]
T["x34_layers"] = table(["Block", "Connected components: Spearman of b with y", "Shortest path"], rows)

cl = json.loads((X34 / "results/clamp.json").read_text())
rows = []
for k, v in cl.items():
    if "|" in k:
        rows.append([k.split("|")[0], k.split("|")[1], f(v["CLU"]["y"]), f(v["CLA"]["y"]), f(v["CLR"]["y"]), v["CLU"]["n"]])
T["x34_clamp"] = table(["Task", "Direction seed", "Push without clamp: y", "Axis component clamped: y", "Random direction clamped: y", "n"], rows)
T["x34_clamp_sum"] = (f"Pooled escapes: no clamp {cl['pooled']['escapes']['CLU']}, axis clamp {cl['pooled']['escapes']['CLA']}, random clamp {cl['pooled']['escapes']['CLR']}; "
                      f"removed share {f(cl['pooled']['removed_share']['CLA'], 3)} (axis) and {f(cl['pooled']['removed_share']['CLR'], 3)} (random); McNemar axis clamp {cl['pooled']['mcnemar']['CLA']['removed']}:{cl['pooled']['mcnemar']['CLA']['added']} (p {f(cl['pooled']['mcnemar']['CLA']['p_exact'])}), random clamp {cl['pooled']['mcnemar']['CLR']['removed']}:{cl['pooled']['mcnemar']['CLR']['added']} (p {f(cl['pooled']['mcnemar']['CLR']['p_exact'])}); verdict {cl['verdict']}.")

tp = json.loads((X34 / "results/targeted_push.json").read_text())
rows = []
for task in ("T10", "T2", "T03"):
    v = tp[task]
    mc = v["mcnemar_axis_vs_random"]
    for s in ("0.1", "0.25", "0.5", "1", "2", "4", "8"):
        a = v["arms"][f"AX_s{s}"]; r = v["arms"][f"RX_s{s}"]
        m = mc.get(f"s{s}", {})
        rows.append([task, s, f(a["y_runner_up"]), f(a["y_off"]), f(a["pass"]), comp(a["labels"]), f(r["y_runner_up"]), f(r["pass"]), comp(r["labels"]),
                     f"{m.get('axis_only', '-')}:{m.get('random_only', '-')} (p {f(m.get('p_exact'), 3)})", f(a["rho_s"])])
T["x34_targeted"] = table(["Task", "Dose s (forced-prompt distance)", "Axis: correct runner-up share", "Axis: correct off-default", "Axis: pass", "Axis: labels",
                           "Matched random: correct runner-up", "Random: pass", "Random: labels", "Axis only : random only (exact p)", "Edit norm over the escaping-direction median"], rows)
TN = {"T10": "Connected components", "T2": "shortest path", "T03": "kth smallest"}
T["x34_targeted_ref"] = "Reference norms. " + "; ".join(f"{TN[t]}: axis at block {tp[t]['L_ax']}, median RMS of escaping random directions {f(tp[t]['escape_norm_reference']['median_rms'])}, axis distance RMS {f(tp[t]['escape_norm_reference']['D_rms'])}" for t in ("T10", "T2", "T03"))

t5 = json.loads((X34 / "results/top5_landing.json").read_text())
armn = {"TWIN": "neutral twin", "AWAY_s0.25": "away from the banned centroid, s 0.25", "AWAY_s0.5": "away from the banned centroid, s 0.5", "AWAY_s1": "away from the banned centroid, s 1",
        "IDASTAR_s0.5": "toward IDA*, s 0.5", "RSURV_s0.25": "toward a random survivor, s 0.25", "RSURV_s0.5": "toward a random survivor, s 0.5", "RSURV_s1": "toward a random survivor, s 1",
        "SURV_s0.25": "toward the survivor-region centroid, s 0.25", "SURV_s0.5": "toward the survivor-region centroid, s 0.5", "SURV_s1": "toward the survivor-region centroid, s 1",
        "TOP5BAN_exp30": "prompt top-five ban (iteration 6, N = 50)"}
rows = []
for k, v in t5.items():
    if isinstance(v, dict) and "n" in v:
        rows.append([armn.get(k, k), v["n"], f(v["pass"]), comp(v["labels10"]), v["correct_nonTOP5"], v["attempted_nonTOP5"]])
T["x34_top5"] = table(["Arm (grid task)", "n", "Pass", "Labels (ten-algorithm catalogue)", "Correct programs outside the top five", "Attempted programs outside the top five"], rows)
tg = json.loads((X34 / "results/top5_geometry.json").read_text())
rows = []
for k, v in tg["per_layer"].items():
    rows.append([v["layer"], v["n_points"], f(v["isomap_k15"]["stress1_vs_geodesic"]), f(v["mds_stress1"]), ", ".join(f(x) for x in v["pca_explained_variance_ratio"]),
                 ", ".join(f"{alg(a)} {f(g)}" for a, g in v["g_geodesic"].items()), ", ".join(alg(x) for x in v["edge_survivors"]),
                 ", ".join(f"{alg(a)} {f(g)}" for a, g in sorted(v["centroid_distances_to_banned_centroid"].items(), key=lambda kv: kv[1]))])
T["x34_top5geo"] = table(["Block", "Points", "Isomap (k 15) stress-1", "MDS stress-1", "PCA variance (PC1, PC2)", "Geodesic distance from the banned region, per survivor", "Edge survivors",
                          "Distance from the banned-region centroid, every centroid"], rows)

ex = json.loads((X34 / "results/explore_llr.json").read_text())
rows = [[L, f(v["pop_spearman"]), f(v["pop_p"], 4), f(v["all_cell_spearman"])] for L, v in ex["T2"]["per_L"].items()]
T["x34_llr"] = table(["Opening length L (tokens)", "Spearman of the L-token opening LLR with y over 40 directions", "Permutation p", "All-cell Spearman"], rows)

ft = json.loads((X34 / "results/force_token.json").read_text())
fname = {"FB_comment_#": "first body token forced to ` #` (comment)", "FB_default_sp": "first body token forced to the twin's own token",
         "F10_#": "token 10 forced to ` #` (comment)", "F10_def": "token 10 forced to ` def`", "F10_from": "token 10 forced to ` from`", "F10_parent": "token 10 forced to ` parent`",
         "F11_dfs": "tokens 10-11 forced to ` def dfs`", "F11_find": "tokens 10-11 forced to ` def find`"}
rows = []
for task, v in ft.items():
    if not isinstance(v, dict):
        continue
    for k, r in v.items():
        fl = r["flips_vs_twin"]
        rows.append([task, fname.get(k, k), r["n"], comp(r["labels"]), f(r["pass"]), f(r["off_default_correct"]), f"{fl['to_off']}:{fl['to_default']} (p {f(fl.get('p_exact'), 3)})"])
T["x34_force"] = table(["Task", "Forced token under the unchanged neutral twin", "n", "Labels", "Pass", "Correct off-default share", "Flips against the twin, to off : to default (exact p)"], rows)
rm = json.loads((X34 / "results/remeasure.json").read_text())
rows = [[t, v["n"], f(v["F_rho"]), f(v["F_p"], 4), f(v["P2_rho"]), f(v["P2_p"], 3), f(v["y_this_vs_exp29d_rho"]), f(v["mean_y_this"], 3), f(v["mean_y_exp29d"], 3)] for t, v in rm.items()]
T["x34_remeasure"] = table(["Task", "Directions", "F Spearman on this engine's outcomes", "p", "P2 Spearman", "p", "Spearman of y with the engine control's bf16 y", "Mean y here", "Mean y, engine control"], rows)

# ---------------- temperature experiment (exp 35) ----------------
S35 = md_tables(X35 / "results/summary.md")
unit = {"B3": "minimum spanning tree weight", "A3": "trapped rain water", "B6": "valid anagram"}


def g35(prefix, idx=0):
    hits = [t for h, t in S35 if h and h.startswith(prefix)]
    return hits[idx]


rows = [[unit[r[0]], compstr(r[1]), alg(r[2]), r[3], r[4], r[5]] for r in rows_of(g35("S0 twins"))]
T["x35_twins"] = table(["Unit", "Labels of 100 twin programs", "Minority algorithm A_min", "A_min share", "Pass rate", "Iteration-5 record of the minority share"], rows)
rows = [[unit[r[0]], r[1].replace("ONE-TOKEN", "one token"), r[2], r[3], r[4], r[5], r[6]] for r in rows_of(g35("S1 fork location"))]
T["x35_forkloc"] = table(["Unit", "Mode", "Canonical opening length |O| (tokens)", "Coverage of the opening clusters", "Confirmed forks / base paths", "On-opening forks confirmed at |O|+1",
                          "Sampler calibration (minority share at k = 0 against the twin, Fisher p)"], rows)
rows = []
for r in rows_of(g35("Test (1)")):
    rows.append([unit[r[0]], r[1], r[2], compstr(r[3]), r[4], r[5]])
T["x35_test1"] = table(["Unit", "H(algorithm | fork class) (bits)", "Bootstrap 95% CI", "Class mass at the fork", "Mass on undecided tokens", "Pass (at most 0.3)"], rows)
tl = g35("Test (2)", 0)
rows = []
for r in rows_of(tl):
    cellname = r[1].replace("_p1", ", top-p 1").replace("_k10", ", top-k 10").replace("T", "T ")
    rows.append([unit[r[0]], cellname] + r[2:])
T["x35_test2"] = table(["Unit", "Cell", "Predicted minority share", "Observed [Wilson 95%]", "Correct minority observed / predicted", "On-opening share observed / predicted", "JS (bits)", "Per-slot replay accuracy"], rows)
tl = g35("Test (2)", 1)
rows = [[unit[r[0]]] + r[1:] for r in rows_of(tl)]
T["x35_test2sum"] = table(["Unit", "MAE", "Observed drop T 1.0 to 0.3 [slot bootstrap]", "Predicted drop", "McNemar b:c, one-sided p", "Observed change T 1.0 to 1.3", "Predicted change",
                           "Slots changing the idea across T (top-p 1)", "Pass"], rows)
rows = [r for r in rows_of(g35("Test (3)"))]
tname = {"T1": "grid", "T2": "shortest path", "T10": "connected components", "T03": "kth smallest"}
rows = [[tname[r[0]]] + r[1:] for r in rows]
T["x35_test3"] = table(["Task", "Fork margin (nats)", "At least 4", "Predicted off-default rate at T 0.3 / 1.0 / 1.3", "Predicted change 0.3 to 1.3", "Bound check at T 1.3 (off of 100 against the logit prediction)",
                        "T 1.3 check (off of 20)", "48-token opening LLR"], rows)
s4b = json.loads((X35 / "results/s4b.json").read_text())
rows = []
for u, v in s4b.items():
    for arm, nm in (("FORCEDPAD", "padding twin"), ("FORCED", "forced minority prompt"), ("EXCH", "forced prompt's task-specification states exchanged in"), ("MR", "matched-norm random exchange")):
        a = v["arms"][arm]
        rows.append([unit[u], nm, a["n"], f(a["attempted_a_min"]), f(a["correct_a_min"]), f(a["pass_rate"]), comp(a["labels"])])
T["x35_s4b"] = table(["Unit", "Arm", "n", "Attempted minority share", "Correct minority share", "Pass", "Labels"], rows)
rows = [[unit[u], f"{v['exchange_vs_pad']['b']}:{v['exchange_vs_pad']['c']} (p {f(v['exchange_vs_pad']['p_one_sided'])})", f"{v['exchange_vs_MR']['b']}:{v['exchange_vs_MR']['c']} (p {f(v['exchange_vs_MR']['p_one_sided'])})",
         f(v["d_margin_exchange"]), f(v["d_margin_MR"]), f(v["s_pred_exchange"]), f(v["exchange_pass_ratio_vs_pad"])] for u, v in s4b.items()]
T["x35_s4b_tests"] = table(["Unit", "Exchange against padding twin, b:c (one-sided p)", "Exchange against random exchange", "Fork margin change, exchange (nats)", "Fork margin change, random exchange",
                            "Predicted minority share under the exchange", "Pass ratio against the padding twin"], rows)
s4a = json.loads((X35 / "results/s4a.json").read_text())
rows = []
for u, v in s4a.items():
    for d, r in v["per_direction"].items():
        rows.append([unit[u], d, f(r["d_margin"]), f(r["s_obs"]), f(r["s_pred"]), f(r["d_s_obs"]), f(r["pass_rate"]), comp(r["labels"])])
T["x35_s4a"] = table(["Unit", "Direction seed", "Fork margin change (nats)", "Observed minority share (of 10)", "Predicted share", "Observed change against the twin", "Pass", "Labels"], rows)
rows = [[unit[u], f(v["spearman_dmargin_dshare"]), f(v["perm_p_one_sided_negative"], 4), f(v["perm_p_one_sided"], 3), f(v["mae_s_pred"], 3), f(v["log_score_gain_per_sample"], 3), f(v["pass_rate_vs_twin"], 3),
         f"{f(v['twin_slots_0_1']['s_obs'])} (pred {f(v['twin_slots_0_1']['s_pred'])})"] for u, v in s4a.items()]
T["x35_s4a_sum"] = table(["Unit", "Spearman (margin change, share change)", "Lower-tail permutation p", "Committed upper-tail p", "MAE of predicted shares", "Log-score gain per sample over no push effect",
                          "Pass ratio against the twin", "Twin minority share on these slots"], rows)
tl = [t for h, t in S35 if h and h.startswith("1a-c")][0]
rows = []
for r in rows_of(tl):
    if r[1].startswith("per-slot"):
        continue
    cellname = r[1].replace("_p1", ", top-p 1").replace("_k10", ", top-k 10").replace("T", "T ")
    ideas = ", ".join(alg(x.strip(" '")) for x in r[2].strip("[]").split(","))
    rows.append([unit[r[0]], cellname, ideas, r[3], compstr(r[4]), compstr(r[5]), compstr(r[6])])
T["x35_1ac"] = table(["Unit", "Cell", "Ideas among correct programs", "Hill-1 at depth 25", "Phrasing clusters per idea (Jaccard 0.8)", "Ten literal trajectories: ideas", "Their phrasing clusters"], rows)

# ---------------- unit / seed experiment (exp 36) ----------------
s1 = json.loads((X36 / "results/s1_2x2.json").read_text())
T["x36_s1keys"] = ",".join(list(s1.keys())[:20])
s2 = json.loads((X36 / "results/s2_profile.json").read_text())
pn = {"D1": "absolute unit, full", "PTOP": "absolute unit, top-quartile cells only", "PREST": "absolute unit, other three quartiles only", "PSHUF": "absolute unit, positions shuffled"}
rows = []
for t in ("T10", "T2"):
    for k, c in s2[t]["cells"].items():
        rm_ = c.get("realised_mean") or {}
        rows.append([t, pn.get(k, k), c["N"], f"{c['Y']['k']} ({f(c['Y']['share'])})", c["A"]["k"], f(c["pass_rate"]), comp(c["composition_correct"]), f(rm_.get("S_b12")), f(rm_.get("R_b35"))])
T["x36_s2"] = table(["Task", "Arm (all at the absolute unit's total energy, alpha 2)", "N", "Correct off-default Y (share)", "Attempted off-default", "Pass", "Correct composition",
                     "Realised displacement at block 12 (spec mean)", "Realised displacement at block 35 (read position)"], rows)
rows = []
for t in ("T10", "T2"):
    for k, v in s2[t]["tests"].items():
        if k.endswith("|Y"):
            rows.append([t, k.replace("|Y", "").replace("PTOP", "top quartile").replace("PREST", "rest").replace("PSHUF", "shuffled").replace("_vs_", " against ").replace("D1", "full unit"),
                         f"{v['n10']}:{v['n01']}", f(v["p"], 4), f(s2[t]["holm_Y"].get(k.replace('|Y', ''))) ])
T["x36_s2tests"] = table(["Task", "Contrast (correct off-default)", "Discordant first : second", "Exact p", "Holm p"], rows)
e1 = json.loads((X36 / "results/e1_sweep.json").read_text())
en = {"TWIN": "neutral twin", "D1_a1": "absolute unit, iteration-4 seeds, alpha 1", "D1_a2": "absolute unit, iteration-4 seeds, alpha 2", "D3_a1": "ban-free unit, iteration-4 seeds, alpha 1",
      "D3_a2": "ban-free unit, alpha 2", "D3_a3": "ban-free unit, alpha 3", "D3_a4": "ban-free unit, alpha 4", "D3_a6": "ban-free unit, alpha 6", "D5_a2": "ban-free profile at absolute per-block energy, alpha 2"}
rows = []
for t in ("T10", "T2"):
    for k, c in e1[t].items():
        if isinstance(c, dict) and "N" in c:
            rm_ = c.get("realised_mean") or {}
            vs = c.get("vs_D1_a2_Y")
            rows.append([t, en.get(k, k), c["N"], c["Y"]["k"], c["A"]["k"], f(c["pass_rate"]), comp(c["composition_correct"]), f(rm_.get("S_b12")), f(rm_.get("R_b35")),
                         f"{vs['n10']}:{vs['n01']} (p {f(vs['p'], 4)})" if vs else "-"])
T["x36_e1"] = table(["Task", "Arm", "N", "Correct off-default", "Attempted off-default", "Pass", "Correct composition", "Displacement at block 12", "Displacement at block 35, read position",
                     "Against the absolute unit at alpha 2: arm only : absolute only (p)"], rows)
s3 = json.loads((X36 / "results/s3_prices.json").read_text())
rows = []
kn = {"PN*": "plan noise at the moving design", "BINT": "base intent", "EAP": "enumerate and pick", "IFG": "intent factored generation (1.3, 0.7)", "TEMP": "temperature 1.3", "TOPK10": "top-k 10"}
for t, v in s3["per_task"].items():
    rd = s3["readings"][t]
    for k in ("PN*", "BINT", "EAP", "IFG", "TEMP", "TOPK10"):
        r = v[k]
        ci = rd["H5_ci95"].get(k)
        rows.append([{"T03": "kth smallest", "T10": "connected components", "T2": "shortest path", "T05": "two sum", "T1": "grid"}[t], kn[k], f(r["H5"], 3), f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "-",
                     f(r.get("P15"), 4), f(r.get("P20"), 4)])
T["x36_s3"] = table(["Task", "Knob", "5-point Hill-1", "Bootstrap 95% CI", "Price of 1.5 (pass cost)", "Price of 2 (pass cost)"], rows)
rows = []
for t, rd in s3["readings"].items():
    rows.append([{"T03": "kth smallest", "T10": "connected components", "T2": "shortest path", "T05": "two sum", "T1": "grid"}[t], rd["vs_BINT"], f(rd["P_boot_PN_gt_BINT"], 4), alg(rd["best_text"]) if rd.get("best_text") else "-",
                 f(rd["D_t"]), "yes" if rd["replay_PN_ge_best_text"] else "no", f(rd["P_boot_PN_ge_best_text"], 3)])
T["x36_s3read"] = table(["Task", "Plan noise against base intent", "Bootstrap P(plan noise ahead)", "Best text sampler", "Margin over the best text sampler", "Plan noise at least the best (iteration-5 rule)", "Bootstrap P"], rows)
rows = []
for k, c in s3["cells"].items():
    t, arm = k.split("|", 1)
    rows.append([t, arm.replace("E27:", "reused iteration-5 ").replace("D1_a1", "plan noise, alpha 1").replace("D1_a2", "plan noise, alpha 2").replace("BINT", "base intent").replace("EAP", "enumerate and pick").replace("IFG_hot", "intent factored generation").replace("TOPK10", "top-k 10").replace("TWIN", "neutral twin").replace("T1.3", "temperature 1.3"),
                 c["N"], f(c["pass"]), comp(c["correct_composition"]), c["correct_off_default"]])
T["x36_s3cells"] = table(["Task", "Arm", "N", "Pass", "Correct composition", "Correct off-default"], rows)
e3 = json.loads((X36 / "results/e3_replicate.json").read_text())
T["x36_e3keys"] = ",".join(e3.keys())

# ---------------- search experiment (exp 37) ----------------
rt = json.loads((X37 / "results/ratio_tests.json").read_text())
rows = []
for lv in ("a", "b"):
    for t, r in rt["levels"][lv]["per_task"].items():
        rows.append([lv, t, f"{r['X_S']}/{r['N_S']}", f"{r['X_K']}/{r['N_K']}", f(r.get("R_hat")), f(r.get("LB95")), f(r.get("p_one_sided"), 4), f(r.get("p_holm"), 4), r["verdict"]])
        for s, q in (r.get("secondary") or {}).items():
            rows.append([lv, t + ", secondary: " + s.replace("_vs_", " against ").replace("K(EAP)", "enumerate and pick").replace("I0", "instruction only").replace("NE", "no evolution").replace("B0", "neutral twin").replace("S ", "search ").replace("K ", "enumerate and pick "),
                         f"{q['X_S']}/{q['N_S']}", f"{q['X_K']}/{q['N_K']}", f(q.get("R_hat")), f(q.get("LB95")), f(q.get("p_one_sided"), 4), "-", q.get("verdict_if_primary_rule")])
T["x37_tests"] = table(["Level", "Task and contrast", "First arm X/N", "Second arm X/N", "Rate ratio", "One-sided LB95", "One-sided p", "Holm p", "Verdict under the primary rule"], rows)
pc = json.loads((X37 / "results/program_classes.json").read_text())
import collections
cc = collections.Counter()
for k, v in pc.items():
    if v.get("is_first_of_distinct"):
        cc[(k.split("|")[0], v["final_class"])] += 1
classes = ["CATALOGUE VARIANT", "KNOWN OUTSIDE CATALOGUE", "DEGENERATE", "LABELLER MISS", "NOVEL ALGORITHM"]
rows = [[t, sum(cc[(t, c)] for c in classes)] + [cc[(t, c)] for c in classes] for t in ("T2", "T03", "A3")]
T["x37_classes"] = table(["Task", "Distinct out-of-catalogue-screen programs with a final class (all arms)", "Catalogue variant", "Known technique outside the catalogue", "Degenerate", "Labeller miss", "Novel algorithm"], rows)
nn = collections.Counter()
for k, v in pc.items():
    if v.get("is_first_of_distinct") and "OUTSIDE" in v["final_class"]:
        nn[v.get("named_algorithm")] += 1
T["x37_named"] = table(["Known technique outside the catalogue (kth smallest; as named in the manual read)", "Distinct programs"], [[k, v] for k, v in nn.most_common()])
jg = json.loads((X37 / "results/judge_gate.json").read_text())
rows = []
for j, v in jg["judges"].items():
    rows.append([j, f"{v['accuracy']}/{v['n']}", "passed" if v["passed"] else "failed"] + [v["calls"].get(f"C{i}", "-").replace("CATALOGUE VARIANT", "variant").replace("KNOWN OUTSIDE CATALOGUE", "known outside").replace("DEGENERATE", "degenerate").replace("NOVEL ALGORITHM", "novel") for i in range(1, 11)])
T["x37_judges"] = table(["Judge", "Control accuracy", "Gate (at least 9 of 10)"] + [f"Control {i}" for i in range(1, 11)], rows)
ls = json.loads((X37 / "results/L_vs_S.json").read_text())
rows = []
for k, nm in (("L", "larger mutator (qwen3-235b), 500 calls"), ("S_first_nl", "search, first 500 calls")):
    v = ls[k]
    rows.append([nm, v["N"], v["valid"], v["correct"], v["X_a"], f(v["rate_a"], 3), f"[{v['rate_a_ci95'][0]:.3f}, {v['rate_a_ci95'][1]:.3f}]", v["X_b"], f(v["rate_b"], 3), v["clusters_a"], v["clusters_b"], f(v["hill1_correct_labels"]), comp(v["label_mix"])])
T["x37_LvS"] = table(["Arm (kth smallest)", "N", "Valid", "Correct", "X_a", "Rate a", "95% CI", "X_b", "Rate b", "Clusters a", "Clusters b", "Hill-1 of correct labels", "Label mix"], rows)
T["x37_LvS_tests"] = f"Level a: {ls['test_a']['X_S']}/{ls['test_a']['N_S']} against {ls['test_a']['X_K']}/{ls['test_a']['N_K']}, rate ratio {f(ls['test_a']['R_hat'])}, LB95 {f(ls['test_a']['LB95'])}, p {f(ls['test_a']['p_one_sided'], 3)}; level b: {ls['test_b']['X_S']}/{ls['test_b']['N_S']} against {ls['test_b']['X_K']}/{ls['test_b']['N_K']}, rate ratio {f(ls['test_b']['R_hat'])}, LB95 {f(ls['test_b']['LB95'])}, p {f(ls['test_b']['p_one_sided'], 4)}."
me = json.loads((X37 / "results/matched_effort.json").read_text())
rows = []
for t, v in me.items():
    bs = v["S_island_bootstrap"]
    rows.append([t, v["N_S"], v["S_clusters_observed"], ", ".join(f"island {i}: {x['X_a']}/{x['N']}" for i, x in v["S_per_island"].items()), f"{bs['rate_median']:.3f} [{bs['rate_lo95']:.3f}, {bs['rate_hi95']:.3f}]"]
                + [f"{v[a]['S_obs']} ({f(v[a]['S_m'], 1)})" for a in ("NE", "I0", "EAP", "BINT", "B0")])
T["x37_effort"] = table(["Task", "Search calls", "Search clusters observed", "Search X_a per island", "Search rate, island bootstrap median [95%]",
                         "No evolution: clusters (Chao-1 extrapolated to the search's effort)", "Instruction only", "Enumerate and pick", "Base intent", "Neutral twin"], rows)
li = json.loads((X37 / "results/lineage.json").read_text())
rows = []
for t, v in li.items():
    rows.append([t, ", ".join(f"{d}: {n}" for d, n in v["ooc_depth_hist"].items()), ", ".join(f"{d}: {n}" for d, n in v["levelb_depth_hist"].items()) or "none", v["levelb_n"], v["levelb_depth_ge2_nonseed_parents"], v["ooc_depth_ge2_nonseed_parents"]])
T["x37_lineage"] = table(["Task", "Search programs passing the screen, by depth (generations)", "Level-b search programs by depth", "Level-b search programs", "Level b at depth 2 or more with non-seed parents", "Screen-passing at depth 2 or more with non-seed parents"], rows)

# ---------------- Gemma circuit / dose (exp 38) ----------------
g3 = json.loads((X38 / "results/g3_sweep.json").read_text())
T["x38_g3keys"] = ",".join(list(g3.keys())[:30])

OUT.write_text(json.dumps(T, indent=1))
print("tables", len(T))
for k, v in T.items():
    print(k, len(v))


# ---------------- README tables (copied, codes translated) ----------------
TASKS = [("T10", "connected components"), ("T03", "kth smallest"), ("T05", "two sum"), ("T06", "sixth task"), ("T2", "shortest path"), ("T1", "grid"),
         ("A3", "trapped rain water"), ("B3", "minimum spanning tree weight"), ("B6", "valid anagram")]
CODES = [
    (r"D1 = U_abs × S4", "absolute unit, iteration-4 seeds"), (r"D2 = U_abs × S5", "absolute unit, iteration-5 seeds"),
    (r"D3 = U_bf × S4", "ban-free unit, iteration-4 seeds"), (r"D4 = U_bf × S5", "ban-free unit, iteration-5 seeds"),
    (r"D5 α2 \(U_bf\\\*\)", "ban-free profile at absolute per-block energy, α 2"),
    (r"\bD1 α1 / D2 α1 / D3 α1 / D4 α1\b", "the four designs at α 1 (absolute/iteration-4, absolute/iteration-5, ban-free/iteration-4, ban-free/iteration-5)"),
    (r"\bD1 α2\b", "absolute unit, iteration-4 seeds, α 2"), (r"\bD2 α2\b", "absolute unit, iteration-5 seeds, α 2"),
    (r"\bD3 α2\b", "ban-free unit, iteration-4 seeds, α 2"), (r"\bD4 α2\b", "ban-free unit, iteration-5 seeds, α 2"),
    (r"^\| D1 \|", "| absolute unit, iteration-4 seeds |"), (r"^\| D2 \|", "| absolute unit, iteration-5 seeds |"),
    (r"^\| D3 \|", "| ban-free unit, iteration-4 seeds |"), (r"^\| D4 \|", "| ban-free unit, iteration-5 seeds |"),
    (r"\bTWIN\b", "neutral twin"), (r"PN\\\*", "plan noise at the moving design"), (r"\bU_bf\\\*", "ban-free profile at absolute energy"),
    (r"\bIFG\(1\.3, 0\.7\)", "intent factored generation (1.3, 0.7)"),
    (r"\| \*\*S\*\* \|", "| **search** |"), (r"\| S \|", "| search |"), (r"\| NE \|", "| no evolution |"), (r"\| I0 \|", "| instruction only |"),
    (r"\| EAP \|", "| enumerate and pick |"), (r"\| BINT \|", "| base intent |"), (r"\| B0 \|", "| neutral twin |"), (r"\| L \(235B\) \|", "| larger mutator (qwen3-235b) |"),
    (r"\bX_a\b", "distinct screen-passing programs"), (r"\bX_b\b", "distinct adjudicated outside-catalogue programs"), (r"OOC clusters", "screen-passing idea clusters"),
    (r"R̂", "Rate ratio"), (r"\bLB95\b", "One-sided lower 95% bound"),
    (r"@ COND", "at the condition sentence"), (r"@ FORK", "at the fork position"), (r"\bSTEER\b", "steer"), (r"\bABLATE\b", "ablate"),
    (r"\bRAND rank-4", "random rank-4 subspace"), (r"DiM", "difference in means"), (r"DAS-L", "logit-only DAS"),
    (r"forced-BFS prompt F5 \(prompting ceiling\)", "forced-BFS prompt, fifth forced source (prompting ceiling)"),
    (r"P\(c\*\)", "P(shared opening)"),
    (r"\bT(\d\.\d) top-p 1\b", r"T \1, top-p 1"),
]


def tr_codes(line):
    for p, r in CODES:
        line = re.sub(p, r, line)
    for code, name in TASKS:
        line = re.sub(rf"(?<=\| ){code}(?= \||,)", name, line)
        line = re.sub(rf"\b{code}, ", f"{name}, ", line) if line.startswith(f"| {code},") else line
    return line


def readme_table(path, start):
    lines = Path(path).read_text().splitlines()
    out = []
    for ln in lines[start - 1:]:
        if ln.strip().startswith("|"):
            out.append(tr_codes(ln.strip()))
        else:
            break
    return "\n".join(out)


R = {
    "e6_checks": (E6 / "README.md", 16), "e6_stageA": (E6 / "README.md", 37), "e6_mcnemar": (E6 / "README.md", 50), "e6_t238": (E6 / "README.md", 106),
    "e6_nla": (E6 / "README.md", 117), "e6_judges": (E6 / "README.md", 139), "e6_venues": (E6 / "README.md", 159),
    "x36_2x2": (X36 / "README.md", 39), "x36_prices": (X36 / "README.md", 102), "x36_e3a": (X36 / "README.md", 159), "x36_e3b": (X36 / "README.md", 174),
    "x36_pred": (X36 / "README.md", 187), "x36_cells": (X36 / "README.md", 201),
    "x37_sstar": (X37 / "README.md", 41), "x37_counts": (X37 / "README.md", 77), "x37_primary": (X37 / "README.md", 101),
    "x38_cal": (X38 / "README.md", 116), "x38_g3": (X38 / "README.md", 129), "x38_dose": (X38 / "README.md", 186), "x38_nodes": (X38 / "README.md", 240),
    "x38_valid": (X38 / "README.md", 270), "x38_arms": (X38 / "README.md", 293),
}
for k, (p, s) in R.items():
    T[k] = readme_table(p, s)
OUT.write_text(json.dumps(T, indent=1))
print("total tables", len(T))
