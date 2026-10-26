"""Write the figure specs of iteration 7 (six new figures, seven geometry figures placed by the record audit).

Every number is read from an artifact file or from work/geom/*.json (recomputed from the artifacts' cached states).
Output: work/figures7.json (list of figure specs).
"""
import json
import statistics as st
import sys
from pathlib import Path

W = Path(__file__).parent
G7 = Path(__file__).resolve().parents[3] / "round-7"
G6 = Path(__file__).resolve().parents[3] / "round-6"
T = json.loads((W / "tables7.json").read_text())
STYLE = ("White background, sans-serif font, colourblind-safe palette (Okabe-Ito), axis labels at least 10 pt, light grey gridlines, "
         "no 3D effects, no title inside the image (the caption carries it).")
figs = []


def r(x, nd=2):
    return round(float(x), nd)


# ---------- 1. DAS manifold, shortest path ----------
rows = [ln.split("|")[1:-1] for ln in T["x33_mplace"].splitlines()[2:]]
pts = "; ".join(f"'{c[0].strip()}' at (axis {c[4].strip()}, D {c[1].strip()})" for c in rows)
cent = [ln.split("|")[1:-1] for ln in T["x33_centroids"].splitlines()[2:]]
cents = "; ".join(f"{c[0].strip()} {c[1].strip()}" for c in cent)
figs.append(dict(
    id="fig_das_manifold_sp", title="Shortest path prompts in the fitted DAS coordinates",
    caption=("Prompts of the shortest path task placed in the rank-16 DAS coordinates of Qwen3-8B (blocks 12-23, task-specification positions). "
             "Horizontal axis: coordinate along the axis from the Dijkstra centroid to the Bellman-Ford/SPFA centroid; vertical axis: distance D from the default (Dijkstra) centroid. "
             "Dashed lines mark the paraphrase null (median 0.52, 95th percentile 1.13). All five ban templates lie outside the null on the runner-up side; "
             "random seeds and novelty instructions lie inside it, and the semantic seed, predicted outside, lies inside at the 94th percentile."),
    figure_type="data", aspect_ratio="4:3",
    image_gen_detailed_description=(
        "Scatter plot. X-axis: 'coordinate along the default-to-runner-up axis (DAS rank-16 coordinates)', range -0.8 to 2.0. "
        "Y-axis: 'distance D from the Dijkstra centroid', range 0 to 3.0. Two horizontal dashed grey lines: y = 0.52 labelled 'paraphrase null median' and y = 1.13 labelled 'null 95th percentile'; "
        "shade the band from 0 to 1.13 very light grey. Points (exact values): " + pts + ". "
        "Colour the five ban points vermillion (filled circles, label them 'ban 1' to 'ban 5' by template number, first to fifth), the neutral prompt black (filled square), "
        "the two random seeds blue (triangles), the two instructions ('Make a new algorithm.', 2,000-word novelty instruction) green (diamonds), the semantic seed orange (star). "
        "Below the scatter, a thin strip axis (same x scale) with the five algorithm centroids along the runner-up axis drawn as labelled ticks: " + cents + ". "
        "Legend top left. " + STYLE),
    summary="Bans leave the paraphrase null on the runner-up side in the fitted coordinates; seeds and instructions stay inside it and leave the algorithm unchanged."))

# ---------- 2. Fork margin scatter ----------
fa = json.loads((G7 / "experiment-34/src/results/f_analysis.json").read_text())
cells = fa["F"]["calibration"]["cells"]
t10, t2 = [], []
for c in cells:
    t, nm = c["cell"].split("|", 1)
    if nm.startswith("POP_"):
        (t10 if t == "T10" else t2).append((r(c["m"]), r(c["y"])))
t10.sort(); t2.sort()
figs.append(dict(
    id="fig_fork_margin", title="Fork margin against the effect of 40 random pushes",
    caption=("Each point is one of iteration 4's 40 random directions at alpha 2 in Qwen3-8B bf16. (a) Connected components: the teacher-forced fork margin at generated tokens 10-11 "
             "against the correct off-default share (Spearman 0.80, 95% interval 0.62 to 0.91; a placebo that shuffles which fork tokens lead to which algorithm reaches 0.80 "
             "in 18% of 200 permutations, so the margin acts through the probability that stays on the default fork tokens). (b) Shortest path, which has no single fork: the committed fallback, the 48-token opening "
             "log-likelihood ratio, against the same share (Spearman 0.15, p 0.18). The fork claim holds where a fork exists and fails where the decision falls late."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Two side-by-side scatter panels, labelled (a) and (b). Panel (a) 'Connected components': x-axis 'fork margin m under the push (nats)', y-axis 'correct off-default share y' (0 to 1). "
        f"Points (m, y), 40 directions: {t10}. Annotate 'Spearman 0.80 [0.62, 0.91]' in the upper left. Mark the twin margin -3.51 nats with a vertical dashed grey line labelled 'twin'. "
        "Panel (b) 'Shortest path': x-axis '48-token opening LLR under the push (nats)', y-axis 'correct off-default share y' (0 to 1). "
        f"Points (LLR, y), 40 directions: {t2}. Annotate 'Spearman 0.15 (p 0.18)'. Mark the twin value -6.02 with a vertical dashed grey line labelled 'twin'. "
        "Blue filled circles in (a), orange filled circles in (b), alpha 0.8, size 30. " + STYLE),
    summary="The fork margin predicts which random pushes change the algorithm on connected components, and the opening LLR fails on shortest path where no early fork exists."))

# ---------- 3. Temperature through the fork ----------
lines = [ln.split("|")[1:-1] for ln in T["x35_test2"].splitlines()[2:]]
q = {}
for c in lines:
    unit, cell = c[0].strip(), c[1].strip()
    if "top-p 1" not in cell:
        continue
    temp = cell.split(",")[0].replace("T", "").strip()
    pred = c[2].strip(); obs = c[3].strip()
    q.setdefault(unit, []).append(f"T {temp}: predicted {pred}, observed {obs}")
qs = " | ".join(f"{u}: " + "; ".join(v) for u, v in q.items())
figs.append(dict(
    id="fig_temperature_fork", title="Temperature acts through the fork logits",
    caption=("Minority (or BFS) share across temperature under the same seed, predicted from the teacher-forced fork logits divided by T before any temperature sample (line) "
             "against the observed share with its Wilson 95% interval (points), top-p 1, N = 50 per cell after the fork calibration. Qwen3-8B: minimum spanning tree weight "
             "(mean absolute error 0.083), trapped rain water (0.105), valid anagram (0.043, the drop not observed). gemma-3-4b-it, grid task: attempted BFS (0.026)."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Four small-multiple panels in one row, shared x-axis 'temperature T' with ticks 0.3, 0.7, 1.0, 1.3; y-axis 'minority share' from 0 to 0.7. "
        "In each panel draw the predicted share as a dark grey line with open circle markers and the observed share as filled coloured points with vertical Wilson 95% error bars. "
        "Values (Qwen3-8B, observed given as share [Wilson lower, upper]): " + qs + ". "
        "Panel 4 'Gemma grid (attempted BFS)': T 0.3 predicted 0.015, observed 0.02 [0.00, 0.10]; T 0.7 predicted 0.166, observed 0.24 [0.14, 0.37]; "
        "T 1.0 predicted 0.323, observed 0.34 [0.22, 0.48]; T 1.3 predicted 0.450, observed 0.46 [0.33, 0.60]. "
        "Panel titles: 'Qwen3-8B, minimum spanning tree weight (Prim)', 'Qwen3-8B, trapped rain water (two pointers)', 'Qwen3-8B, valid anagram (fixed count array)', 'gemma-3-4b-it, grid (BFS)'. "
        "Annotate MAE in each panel: 0.083, 0.105, 0.043, 0.026. Colours: blue, orange, green, purple for the four panels. " + STYLE),
    summary="Fork logits divided by T predict the temperature response closely on one Qwen3-8B unit and on Gemma, loosely on a second unit, and not in direction on the third."))

# ---------- 4. Unit x seed ----------
figs.append(dict(
    id="fig_unit_seed", title="Dose unit against direction seeds",
    caption=("Correct off-default share under per-sample plan noise at alpha 2 in Qwen3-8B bf16 for the four designs of the 2x2: absolute unit or ban-free unit, crossed with "
             "iteration-4 or iteration-5 direction seeds. The unit decides (connected components +0.45 [0.35, 0.55]; fresh slots +0.42; kth smallest +0.27; shortest path +0.115); "
             "the seeds do not (+0.03 on connected components)."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Grouped bar chart. X-axis groups (four): 'connected components (50 slots)', 'connected components, fresh slots (50)', 'kth smallest (50)', 'shortest path (100)'. "
        "Within each group four bars in this order and colours: 'absolute unit, iteration-4 seeds' (dark blue), 'absolute unit, iteration-5 seeds' (light blue), "
        "'ban-free unit, iteration-4 seeds' (dark orange), 'ban-free unit, iteration-5 seeds' (light orange). Y-axis 'correct off-default share' from 0 to 0.7. "
        "Values: connected components 0.50, 0.52, 0.10, 0.02 (Wilson intervals [0.37, 0.63], [0.39, 0.65], [0.04, 0.21], [0.00, 0.10] as error bars); "
        "connected components fresh slots 0.42, 0.60, 0.08, 0.10 (no error bars); kth smallest 0.56, 0.52, 0.28, 0.26 (no error bars); "
        "shortest path 0.13, 0.20, 0.05, 0.05 (Wilson [0.08, 0.21], [0.13, 0.29], [0.02, 0.11], [0.02, 0.11]). Print each value above its bar. "
        "Above each group print the unit effect: '+0.45 [0.35, 0.55]', '+0.42 [0.32, 0.52]', '+0.27 [0.18, 0.37]', '+0.115 [0.06, 0.17]'. Legend at the top. " + STYLE),
    summary="The ban-free dose unit, not the direction seeds, made iteration 5's plan noise weak, on three tasks."))

# ---------- 5. Search rates ----------
rows = [ln.split("|")[1:-1] for ln in T["x37_counts"].splitlines()[2:]]
data = {}
for c in rows:
    task = c[0].strip(); arm = c[1].strip().strip("*")
    xa = c[4].strip().replace("*", ""); xb = c[5].strip().replace("*", "")
    n = c[2].strip()
    data.setdefault(task, []).append(f"{arm}: N {n}, level a {xa}, level b {xb}")
ds = " | ".join(f"{t}: " + "; ".join(v) for t, v in data.items())
figs.append(dict(
    id="fig_search_rates", title="Programs outside the catalogue: evolutionary search against arms that draw single samples",
    caption=("Distinct correct programs passing the out-of-catalogue screen per call (level a, bars, log scale) and distinct programs adjudicated as known techniques outside "
             "the catalogue (level b, numbers above bars), for each arm on three tasks in Qwen3-8B. Search reaches 6.65 times enumerate and pick on kth smallest at level a and "
             "is the main source of known techniques outside the catalogue (78 level-b programs, against 23 for the larger mutator and at most 2 for every single-sample arm); no program is novel."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Three panels side by side, one per task: 'kth smallest', 'shortest path', 'trapped rain water'. In each, vertical bars per arm in this order: search, no evolution, "
        "instruction only, enumerate and pick, base intent, neutral twin, and (kth smallest only) larger mutator (qwen3-235b). Bar height = level-a rate (the number in parentheses), "
        "on a log-scale y-axis 'distinct screen-passing programs per call' from 0.001 to 0.3; a rate of 0 is drawn as a small hollow marker at 0.001 labelled '0'. "
        "Print the level-b count above each bar as 'b = <count>'. Values: " + ds + ". "
        "Colours: search dark blue, no evolution light blue, instruction only teal, enumerate and pick orange, base intent brown, neutral twin grey, larger mutator purple. " + STYLE),
    summary="Evolutionary search raises the out-of-catalogue rate on kth smallest and alone reaches known techniques outside the catalogue; it finds nothing new."))

# ---------- 6. Gemma dose dial ----------
figs.append(dict(
    id="fig_gemma_dose", title="Gemma: DAS dose dial against difference in means",
    caption=("Correct BFS programs (left) and pass rate (right) of 50 per cell, gemma-3-4b-it grid task, edit applied once at the fork position at block 17 with the opening prefilled. "
             "DAS (rank 4) raises correct BFS from the twin's 11 to 42 at pass 0.88, above the explicit BFS instruction (35); difference in means at matched teacher-forced effect "
             "flips the algorithm but destroys the programs."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Two side-by-side line panels with shared x-axis 'dose lambda' at 0.1, 0.2, 0.35, 0.5, 0.75, 1.0. "
        "Left panel y-axis 'correct BFS programs (of 50)' 0 to 50: DAS (blue line, circles) 20, 27, 31, 37, 38, 42; difference in means (orange line, squares) 15, 15, 12, 11, 2, 0. "
        "Also plot attempted BFS as thin dashed lines in the same colours: DAS 27, 38, 46, 47, 47, 47; difference in means 30, 36, 46, 48, 50, 50. "
        "Horizontal reference lines: twin 11 correct (grey dotted, label 'twin'), explicit BFS instruction 35 correct (green dash-dot, label 'BFS instruction'), "
        "random rank-4 subspace at lambda 1, 12 correct (black dotted, label 'random'). Mark logit-only DAS at lambda 0.5 and 1 as green triangles at 35 and 35. "
        "Right panel y-axis 'pass rate' 0 to 1: DAS 0.86, 0.78, 0.68, 0.78, 0.80, 0.88; difference in means 0.70, 0.58, 0.32, 0.26, 0.04, 0.00; twin 0.86 (grey dotted); "
        "BFS instruction 0.70 (green dash-dot). " + STYLE),
    summary="A DAS edit at Gemma's fork acts as a dose dial that keeps the programs; difference in means breaks them."))

# ---------- 7. Qwen top-five geometry (iteration 6) ----------
tp = json.loads((G6 / "experiment-30/src/results/top5_push.json").read_text())
g = tp["geometry"]
banned = {"astar", "bfs", "dfs", "gbfs", "iddfs"}
nm = {"astar": "A*", "bfs": "BFS", "biastar": "bidirectional A*", "bibfs": "bidirectional BFS", "dfs": "DFS", "dijkstra_unit": "unit weight Dijkstra",
      "gbfs": "greedy best first", "idastar": "IDA*", "iddfs": "IDDFS", "jps": "jump point search"}
cen = "; ".join(f"{nm[n]} ({'banned' if n in banned else 'survivor'}) ({r(x, 3)}, {r(y, 3)})" for n, (x, y) in zip(g["centroid_names"], g["centroids_pc"]))
COND = {"twin": "twin", "ban1": "single-name ban", "push1": "push 1 unit", "push2": "push 2 units", "push4": "push 4 units",
        "push8": "push 8 units", "top5ban": "top-five ban"}


def plabel(k):
    """'push8__W2' -> 'push 8 units, template 2'; algorithm centroids keep their readable name."""
    if "__W" in k:
        c, w = k.split("__W")
        return f"{COND[c]}, template {w}"
    return nm.get(k, k)


pts = "; ".join(f"{plabel(k)} ({r(v[0], 3)}, {r(v[1], 3)})" for k, v in g["points_pc"].items())
mds = g["mds_geodesic_knn"]
mdsp = "; ".join(f"{plabel(l)} ({r(x, 3)}, {r(y, 3)})" for l, (x, y) in zip(mds["labels"], mds["xy"]))
figs.append(dict(
    id="fig_qwen_top5_geometry", title="Qwen3-8B grid task: prompt states around the top-five ban",
    caption=("Actual activation coordinates of Qwen3-8B on the grid task (iteration 6): mean of the block outputs of blocks 12-23 over the task-specification positions, divided by the "
             "median block norm, before any generated token. (a) PCA plane of the 10 forced-prompt centroids (first and second components 36% and 25% of variance), with the twin, single-name ban, top-five ban and "
             "pushed states of each template; (b) zoom on the centroid region; (c) classical MDS of geodesic distances on a 6-nearest-neighbour graph. Centroids are coloured by the "
             "prompt-defined top-five set (banned five against survivors). Pushes of 1 to 8 ban units leave the manifold along one direction."),
    figure_type="data", aspect_ratio="21:9",
    image_gen_detailed_description=(
        "Three panels (a), (b), (c) in one row. Panel (a) 'PCA of forced-prompt centroids': x-axis 'PC1 (36%)', y-axis 'PC2 (25%)'. Plot the 10 centroids as large stars, "
        "vermillion for the banned five and blue for the five survivors, each labelled with its algorithm name: " + cen + ". Plot the 28 prompt states as small markers keyed by "
        "condition (twin: black circles; single-name ban of BFS: grey triangles; pushes of 1, 2, 4 and 8 ban units along the top-five direction: purple shades from light to dark; "
        "prompt top-five ban: red crosses), each point given as condition and template (templates 1, 2, 3 and 5): " + pts + ". Draw thin grey arrows from each template's twin to "
        "its 8-unit push point. Panel (b): the same as (a) but zoomed to x from -0.2 to 0.25 and y from -0.2 to 0.2 (the push points fall outside and are omitted), labels on every point. "
        "Panel (c) 'MDS of geodesic distances (k = 6)': x-axis 'MDS 1', y-axis 'MDS 2'; points with the same marker scheme: " + mdsp + ". " + STYLE),
    summary="The prompt top-five ban sits near the banned centroids; pushes of 1 to 8 ban units leave the forced-prompt manifold along one direction."))

# ---------- 8-11. Gemma geometry (iteration 6), four spaces ----------
gg = json.loads((W / "geom/gemma_geom.json").read_text())
kinds, modes, yv = gg["kinds"], gg["modes"], gg["yv"]
modename = {"bfs": "BFS", "dfs": "DFS", "bibfs": "bidirectional BFS", "iddfs": "IDDFS", "astar_gbfs": "A* or greedy best first", "dijkstra": "Dijkstra"}
for key, fid, blk, kind_lbl in (("raw|L17", "fig_gemma_geometry_raw_L17", 17, "raw residual (five massive channels zeroed)"),
                                ("raw|L22", "fig_gemma_geometry_raw_L22", 22, "raw residual (five massive channels zeroed)"),
                                ("sae|L17", "fig_gemma_geometry_sae_L17", 17, "Gemma Scope 2 SAE codes, log1p"),
                                ("sae|L22", "fig_gemma_geometry_sae_L22", 22, "Gemma Scope 2 SAE codes, log1p")):
    sp = gg["spaces"][key]
    xy = sp["xy"]
    var = sp["var"]
    forced = {}
    groups = {"ban_bfs": [], "ban_dfs": [], "top5": [], "top5_twin": []}
    variants = []
    for i, k in enumerate(kinds):
        p = (r(xy[i][0]), r(xy[i][1]))
        if k == "forced":
            forced.setdefault(modes[i], []).append(p)
        elif k == "variant":
            variants.append((p[0], p[1], r(yv[i], 1)))
        elif k in groups:
            groups[k].append(p)
    fdesc = "; ".join(f"{modename[m]}: centroid ({r(st.mean(a for a, _ in v))}, {r(st.mean(b for _, b in v))}), 15 points {v}" for m, v in forced.items())
    GNAME = {"ban_bfs": "BFS bans", "ban_dfs": "DFS bans", "top5": "top-five ban", "top5_twin": "top-five twin"}
    gdesc = "; ".join(f"{GNAME[k]}: {v}" for k, v in groups.items())
    figs.append(dict(
        id=fid, title=f"Gemma grid prompts at block {blk}, {('raw residual' if key.startswith('raw') else 'SAE codes')}",
        caption=(f"Actual activation coordinates of gemma-3-4b-it on the grid task (iteration 6, recomputed from the cached states): mean over the task-specification positions, "
                 f"output of block {blk}, {kind_lbl}; PCA plane fitted on all 230 points (first and second components {var[0]:.2f} and {var[1]:.2f} of variance). Prompts that force an algorithm, by mode "
                 f"(stars mark mode centroids; centroid size grows with the natural implemented count out of 200: DFS 139, BFS 61), BFS and DFS bans, the top-five ban and its twin, "
                 f"and 120 neutral variants coloured by the fork log-odds of BFS measured later at response index 32. The plotted position precedes the fork."),
        figure_type="data", aspect_ratio="4:3",
        image_gen_detailed_description=(
            f"Single scatter panel. X-axis 'PC1 ({var[0]*100:.0f}% of variance)', y-axis 'PC2 ({var[1]*100:.0f}% of variance)'. "
            f"Forced-prompt points (small filled circles, one colour per mode: BFS blue, DFS orange, bidirectional BFS sky blue, IDDFS yellow, A* or greedy best first vermillion, "
            f"Dijkstra green) with their centroids as large stars of the same colour, labelled with the mode name; make the DFS star larger (139) than the BFS star (61) and the "
            f"others the smallest: {fdesc}. Other prompts as black-edged markers: BFS bans (5, blue-edged triangles), DFS bans (5, orange-edged triangles), top-five ban (5, red crosses), "
            f"top-five twin (5, black squares): {gdesc}. Neutral variants (120) as small dots coloured on a diverging colormap (blue-white-red, red = more BFS) by the fork log-odds of BFS "
            f"(given as third value; colourbar 'fork log-odds of BFS'): {variants}. " + STYLE),
        summary=f"At block {blk} the forced modes separate in the PCA plane, the top-five ban sits beside the banned A* and greedy cluster, and neutral variants vary with their fork log-odds."))

# ---------- 12. NLA read geometry (iteration 6) ----------
ng = json.loads((W / "geom/nla_geom.json").read_text())["tasks"]
tname = {"T1": "grid", "T2": "shortest path", "T03": "kth smallest", "T05": "two sum", "T06": "find duplicate", "T10": "connected components",
         "T04": "substring search", "R6": "first and last position"}
ALG = {"astar_gbfs": "A* or greedy best first", "bf_spfa": "Bellman-Ford/SPFA", "bfs": "BFS", "bibfs": "bidirectional BFS", "bidijkstra": "bidirectional Dijkstra",
       "binary_search": "binary search", "bisect_module": "bisect module", "bmh": "Boyer-Moore-Horspool", "brute_force": "brute force", "builtin": "built-in search",
       "counting_sort": "counting sort", "dfs": "DFS", "dial": "Dial's buckets", "dijkstra": "Dijkstra", "exponential_search": "exponential search",
       "floyd": "Floyd-Warshall", "full_sort": "full sort", "hash_map": "hash map", "hash_set": "hash set", "heapify_pop": "heapify and pop", "iddfs": "IDDFS",
       "index_marking": "index marking", "kmp": "Knuth-Morris-Pratt", "label_propagation": "label propagation", "median_of_medians": "median of medians",
       "naive": "naive scan", "other": "other", "quickselect": "quickselect", "rabin_karp": "Rabin-Karp", "size_k_heap": "size-k heap",
       "sort_adjacent": "sort and compare neighbours", "sort_binary_search": "sort and binary search", "sort_two_pointers": "sort and two pointers",
       "union_find": "union find", "value_binary_search": "binary search on values", "z_algorithm": "Z algorithm", "twin": "twin", "ban": "ban"}


def alg(k):
    if k is None:
        return None
    if isinstance(k, str) and len(k) == 2 and k[0] == "W" and k[1].isdigit():
        return f"template {k[1]}"
    return ALG[k]


def counts(d):
    if not isinstance(d, dict):
        return "none recorded" if d is None else str(d)
    if not d:
        return "none (no ban prompt on this task)"
    return ", ".join(f"{alg(k)} {n}" for k, n in d.items())


parts = []
for t, v in ng.items():
    c = "; ".join(f"{alg(k)} ({r(a)}, {r(b)})" for k, (a, b) in v["centroids"].items())
    tw = "; ".join(f"{alg(k)} ({r(a)}, {r(b)})" for k, (a, b) in v.get("twin", {}).items())
    bn = "; ".join(f"{alg(k)} ({r(a)}, {r(b)})" for k, (a, b) in v.get("ban", {}).items())
    ad = ", ".join(f"{alg(k)} {a}" for k, a in v.get("adherence", {}).items())
    parts.append(f"Panel '{tname[t]}' (PC1 {v['var'][0]:.2f}, PC2 {v['var'][1]:.2f}): centroids {c}; twins {tw or 'none'}; bans {bn or 'none (no ban prompt on this task)'}; forced adherence {ad}")
figs.append(dict(
    id="fig_nla_read_geometry", title="Qwen2.5-7B-Instruct read-position states per task",
    caption=("Actual activation coordinates of Qwen2.5-7B-Instruct (iteration 6, recomputed from the cached states): the read position (last prompt token) at the output of block 20, "
             "projected per task on the plane of the first two principal components of that task's forced-prompt states. Stars: forced-algorithm centroids (legend gives forced adherence); "
             "circles: twin prompts per template, joined by arrows to the ban prompt of the same template (triangles). Every forced algorithm occupies its own region; twins and bans lie apart from them."),
    figure_type="data", aspect_ratio="16:9",
    image_gen_detailed_description=(
        "Grid of 8 small scatter panels (2 rows by 4 columns), one per task, each with axes 'PC1' and 'PC2' (variance share in the panel title). In each panel: forced-algorithm "
        "centroids as large coloured stars labelled with the algorithm name; twin prompts of templates 1 to 5 as black circles labelled 1 to 5; ban prompts of the same templates as red triangles; a thin grey "
        "arrow from each twin to the ban of the same template. Exact coordinates: " + " || ".join(parts) + ". " + STYLE),
    summary="At the read position every forced algorithm has its own region and twin and ban prompts sit apart from all of them, on all eight tasks."))

# ---------- 13. NLA MDS centroids (iteration 6) ----------
geo = json.loads((G6 / "experiment-32/src/results/geometry.json").read_text())["tasks"]
parts = []
for t, v in geo.items():
    md = v["READ"].get("mds") or {}
    pts = "; ".join(f"{alg(k)} ({r(a)}, {r(b)})" for k, (a, b) in md.items())
    parts.append(f"Panel '{tname[t]}' (default {alg(v.get('default')) or 'none recorded'}): {pts}; implemented under the twin {counts(v.get('implemented_twin'))}; under the ban {counts(v.get('implemented_ban'))}")
figs.append(dict(
    id="fig_nla_mds_centroids", title="Qwen2.5-7B-Instruct: MDS of read-position centroids",
    caption=("Classical MDS of the read-position centroids (block 20 output) per task in Qwen2.5-7B-Instruct (iteration 6): forced-algorithm centroids, the twin centroid and the ban "
             "centroid. Filled marker area grows with the number of twin programs that implemented the algorithm, the dashed ring with the number under the ban. MDS stress was not recorded."),
    figure_type="data", aspect_ratio="16:9",
    image_gen_detailed_description=(
        "Grid of 8 small panels (2 rows by 4 columns), one per task, axes 'MDS 1' and 'MDS 2'. Each point is a centroid labelled by name; 'twin' as a black square and 'ban' as a red "
        "triangle; algorithm centroids as coloured circles whose filled area is proportional to the twin's implemented count for that algorithm (minimum size for 0) and a dashed ring "
        "whose radius grows with the ban's implemented count. Exact coordinates and counts: " + " || ".join(parts) + ". " + STYLE),
    summary="Per task, the centroids of forced algorithms, the twin and the ban in classical MDS, sized by how often each algorithm was implemented."))

# Same terminology as the section text (work/vocab7.py); numbers are untouched.
sys.path.insert(0, str(W))
sys.dont_write_bytecode = True  # keep work/__pycache__/ out of the workspace
import vocab7  # noqa: E402

for f_ in figs:
    for k in ("title", "caption", "image_gen_detailed_description", "summary"):
        f_[k] = vocab7.apply(f_[k])

(W / "figures7.json").write_text(json.dumps(figs, indent=1))
for f_ in figs:
    print(f_["id"], len(f_["image_gen_detailed_description"]))
