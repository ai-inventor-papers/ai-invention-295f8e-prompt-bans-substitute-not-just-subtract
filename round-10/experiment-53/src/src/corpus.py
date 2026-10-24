"""Dated corpus of known TSP next-city rules (COMMIT #3 before any V3 analysis).

Each member: name, source URL, commit/version, retrieval UTC, sha256 of the extracted code, adapter (if any).
A member is ADMITTED only if it runs VALID in the sandbox (same limits as the search); others are listed as not
admitted with the reason. Admitted members are evaluated on SELECTION (+PROBES), HELDOUT, EXT and TSPLIB.
Raw fetches are kept in data/corpus_raw/ (provenance.json holds the URLs, commits and hashes).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESULTS, ROOT, setup_logging, sha256_text, utc_now, write_json  # noqa: E402

logger = setup_logging("corpus")
IMP = "import numpy as np\nimport math\n\n"
SIG = "def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):\n"

TEXTBOOK = {
    "textbook_aco_argmax": (
        "thealgorithms_python ant_colony_optimization_algorithms.py construction step without pheromone "
        "(argmax d^-beta, beta=2) [dependency art_j3Rm_lr2nzR6]",
        IMP + SIG + "    best, best_v = None, -1.0\n    for node in unvisited_nodes:\n"
        "        d = distance_matrix[current_node][node]\n        v = (1.0 / d) ** 2 if d > 0 else float('inf')\n"
        "        if v > best_v:\n            best, best_v = node, v\n    return best\n"),
    "textbook_two_step_lookahead_nn": (
        "two-step look-ahead nearest neighbour (textbook)",
        IMP + SIG + "    U = list(unvisited_nodes)\n    best, bv = None, float('inf')\n    for j in U:\n"
        "        rest = [distance_matrix[j][k] for k in U if k != j]\n"
        "        v = distance_matrix[current_node][j] + (min(rest) if rest else distance_matrix[j][destination_node])\n"
        "        if v < bv:\n            best, bv = j, v\n    return best\n"),
    "textbook_regret2_next_city": (
        "regret-2 next city (a common next-city variant: distance minus the regret between the two nearest "
        "unvisited neighbours of the candidate)",
        IMP + SIG + "    U = sorted(unvisited_nodes)\n    if len(U) < 3:\n"
        "        return min(U, key=lambda j: distance_matrix[current_node][j])\n    best, bv = None, float('inf')\n"
        "    for j in U:\n        ds = sorted(distance_matrix[j][k] for k in U if k != j)\n"
        "        v = distance_matrix[current_node][j] - (ds[1] - ds[0])\n        if v < bv:\n"
        "            best, bv = j, v\n    return best\n"),
    "textbook_angle_sweep_centroid": (
        "angle sweep around the centroid (coordinates recovered from D by classical MDS)",
        IMP + SIG + "    D = np.asarray(distance_matrix, dtype=float)\n    n = D.shape[0]\n"
        "    J = np.eye(n) - np.ones((n, n)) / n\n    B = -0.5 * J @ (D ** 2) @ J\n    w, V = np.linalg.eigh(B)\n"
        "    X = V[:, -2:] * np.sqrt(np.maximum(w[-2:], 0))\n    for k in range(2):\n"
        "        if X[0, k] < 0:\n            X[:, k] = -X[:, k]\n    c = X.mean(axis=0)\n"
        "    ang = np.arctan2(X[:, 1] - c[1], X[:, 0] - c[0])\n    a0 = ang[current_node]\n"
        "    U = sorted(unvisited_nodes)\n    adv = [((ang[j] - a0) % (2 * math.pi)) for j in U]\n"
        "    return U[int(np.argmin(adv))]\n"),
}

MCTS_URL = "https://arxiv.org/pdf/2501.08603 (Appendix E.3 example #1 and Figure 6)"
MCTS = {
    "mctsahd_E3_example1_rollout": (
        IMP + SIG + "    if not unvisited_nodes:\n        return None\n    next_node = None\n"
        "    min_combined_cost = float('inf')\n    for candidate in unvisited_nodes:\n"
        "        immediate_distance = distance_matrix[current_node][candidate]\n"
        "        connection_strength = sum(distance_matrix[candidate][n] for n in unvisited_nodes if n != candidate) / "
        "(max(len(unvisited_nodes) - 1, 1))\n        total_cost = immediate_distance\n"
        "        current_candidate = candidate\n        remaining_nodes = unvisited_nodes - {candidate}\n"
        "        while remaining_nodes:\n"
        "            best_next_node = min(remaining_nodes, key=lambda node: distance_matrix[current_candidate][node])\n"
        "            total_cost += distance_matrix[current_candidate][best_next_node]\n"
        "            current_candidate = best_next_node\n            remaining_nodes.remove(best_next_node)\n"
        "        total_cost += distance_matrix[current_candidate][destination_node]\n"
        "        combined_cost = (1.2 * immediate_distance) + (0.6 / (connection_strength + 1)) + total_cost\n"
        "        if combined_cost < min_combined_cost:\n            min_combined_cost = combined_cost\n"
        "            next_node = candidate\n    return next_node\n"),
    "mctsahd_fig6_t122": (
        IMP + SIG + "    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes "
        "if node != other_node) for node in unvisited_nodes}\n    def total_cost(node):\n"
        "        travel_cost = distance_matrix[current_node][node]\n"
        "        connectivity_penalty = (len(unvisited_nodes) - connectivity_scores[node]) / len(unvisited_nodes)\n"
        "        return travel_cost + connectivity_penalty\n    return min(unvisited_nodes, key=total_cost, default=None)\n"),
    "mctsahd_fig6_t502_t414": (
        IMP + SIG + "    scaling_factor, constant_penalty, bias_factor = 0.5, 2, 0.4\n"
        "    average_distance = sum(distance_matrix[current_node][node] for node in unvisited_nodes) / "
        "len(unvisited_nodes) if unvisited_nodes else 0\n"
        "    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes "
        "if node != other_node) for node in unvisited_nodes}\n    def adjusted_cost(node):\n"
        "        immediate_cost = distance_matrix[current_node][node]\n"
        "        distance_to_destination = distance_matrix[node][destination_node]\n"
        "        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / "
        "len(unvisited_nodes)\n        penalty = 0.5 * (immediate_cost + average_distance)\n"
        "        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * "
        "distance_to_destination)\n    return min(unvisited_nodes, key=adjusted_cost, default=None)\n"),
    "mctsahd_fig6_t528": (
        IMP + SIG + "    scaling_factor, constant_penalty, bias_factor = 0.7, 3, 0.5\n"
        "    average_distance = sum(distance_matrix[current_node][node] ** 2 for node in unvisited_nodes) / "
        "len(unvisited_nodes) if unvisited_nodes else 0\n"
        "    connectivity_scores = {node: sum(distance_matrix[node][other_node] ** 2 for other_node in "
        "unvisited_nodes if node != other_node) for node in unvisited_nodes}\n    def adjusted_cost(node):\n"
        "        immediate_cost = distance_matrix[current_node][node]\n"
        "        distance_to_destination = distance_matrix[node][destination_node]\n"
        "        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / "
        "len(unvisited_nodes)\n        penalty = 0.75 * (immediate_cost ** 2 + average_distance)\n"
        "        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * "
        "distance_to_destination ** 2)\n    return min(unvisited_nodes, key=adjusted_cost, default=None)\n"),
    "mctsahd_fig6_t784": (
        IMP + SIG + "    scaling_factor, constant_penalty, bias_factor = 0.6, 0.5, 0.7\n"
        "    average_distance = sum(distance_matrix[current_node][node] for node in unvisited_nodes) / "
        "len(unvisited_nodes) if unvisited_nodes else 0\n"
        "    connectivity_scores = {node: sum(distance_matrix[node][other_node] for other_node in unvisited_nodes "
        "if node != other_node) for node in unvisited_nodes}\n    def adjusted_cost(node):\n"
        "        immediate_cost = distance_matrix[current_node][node]\n"
        "        distance_to_destination = distance_matrix[node][destination_node]\n"
        "        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / "
        "len(unvisited_nodes)\n        penalty = 0.3 * (immediate_cost + average_distance)\n"
        "        return immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * "
        "distance_to_destination)\n    return min(unvisited_nodes, key=adjusted_cost, default=None)\n"),
    "mctsahd_fig6_t996_best": (
        IMP + SIG + "    scaling_factor, constant_penalty, bias_factor = 0.7, 0.4, 0.5\n"
        "    average_distance = calculate_average_distance(unvisited_nodes, current_node, distance_matrix)\n"
        "    connectivity_scores = calculate_connectivity_score(unvisited_nodes, distance_matrix)\n"
        "    min_total_cost, next_node = float('inf'), None\n    for node in unvisited_nodes:\n"
        "        immediate_cost = distance_matrix[current_node][node]\n"
        "        distance_to_destination = distance_matrix[node][destination_node]\n"
        "        remaining_unvisited = unvisited_nodes - {node}\n"
        "        mst_cost = minimum_spanning_tree(remaining_unvisited, distance_matrix) if remaining_unvisited else 0\n"
        "        connectivity_penalty = scaling_factor * (len(unvisited_nodes) - connectivity_scores[node]) / "
        "len(unvisited_nodes)\n        penalty = 0.4 * (immediate_cost + average_distance + mst_cost)\n"
        "        adjusted_cost = immediate_cost + penalty + constant_penalty + connectivity_penalty - (bias_factor * "
        "distance_to_destination)\n        if adjusted_cost < min_total_cost:\n"
        "            min_total_cost, next_node = adjusted_cost, node\n    return next_node\n"),
}


def members(p1_code: str | None) -> list[dict]:
    from baselines import NN_PROGRAM

    prov = json.loads((DATA / "corpus_raw" / "provenance.json").read_text())
    out = [{"name": "NN", "family": "textbook", "source": "nearest neighbour (seed program)", "code": NN_PROGRAM,
            "url": None, "commit": None, "adapter": None}]
    for k, (src, code) in TEXTBOOK.items():
        out.append({"name": k, "family": "textbook", "source": src, "code": code, "url": None, "commit": None,
                    "adapter": None})
    seed = (DATA / "corpus_raw" / "reevo_seed_func.txt").read_text()
    out.append({"name": "reevo_seed_func_eoh_derived", "family": "ReEvo/EoH",
                "source": "ai4co/reevo prompts/tsp_constructive/seed_func.txt (EoH-derived seed, ReEvo paper Prompt 11)",
                "code": "import numpy as np\nimport math\n\n" + seed.replace("select_next_node_v1", "select_next_node"),
                "url": prov["reevo_seed_func"]["url"], "commit": prov.get("reevo_commit", {}).get("sha"),
                "raw_sha256": prov["reevo_seed_func"]["sha256"], "adapter": "renamed _v1; numpy import added"})
    out.append({"name": "llm4ad_tsp_construct_template", "family": "LLM4AD",
                "source": "Optima-CityU/LLM4AD llm4ad/task/optimization/tsp_construct/template.py (placeholder)",
                "code": IMP + SIG + "    unvisited_nodes = np.array(sorted(unvisited_nodes))\n"
                        "    next_node = unvisited_nodes[0]\n    return next_node\n",
                "url": prov["llm4ad_template"]["url"], "commit": prov.get("llm4ad_commit", {}).get("sha"),
                "raw_sha256": prov["llm4ad_template"]["sha256"], "adapter": "set -> sorted np.ndarray (template expects an array)"})
    for k, code in MCTS.items():
        out.append({"name": k, "family": "MCTS-AHD", "source": MCTS_URL, "code": code,
                    "url": "https://arxiv.org/abs/2501.08603", "commit": "arXiv v-latest PDF retrieved 2026-10-24",
                    "adapter": "PDF line wraps re-joined; typographic quotes normalised"})
    if p1_code:
        out.append({"name": "tuned_P1_at_Cstar", "family": "tuned parametric", "source": "src/baselines.py P1 random "
                    "search (rng 777), best of the first C* evaluations on SELECTION", "code": p1_code, "url": None,
                    "commit": None, "adapter": None})
    for m in out:
        m["sha256"] = sha256_text(m["code"])
        m["retrieval_utc"] = utc_now()
    return out


NOT_FOUND = [
    {"name": "EoH paper heuristics", "source": "arXiv 2401.02051 PDF", "reason": "regex 'select_next_node|def .*next_node' "
     "found no code in the PDF (data/corpus_raw/eoh_grep.md); the EoH-derived seed enters via ReEvo"},
    {"name": "HSEvo paper heuristics", "source": "arXiv 2412.14995 PDF", "reason": "regex 'def select_next_node' found no "
     "code (data/corpus_raw/hsevo_grep.md)"},
    {"name": "ReEvo paper heuristics", "source": "arXiv 2402.01145 PDF", "reason": "only the signature and the seed "
     "function (identical to seed_func.txt) are printed"},
    {"name": "newer papers (Clade-AHD 2602.00549, LHS 2605.17137, RefineEvo 2607.11358, AHD Agent 2605.08756, ES-AHD "
     "2609.00023, EoH-S 2508.03082)", "source": "arXiv", "reason": "not checked within the time budget"},
]


def main() -> None:
    import evaluator as ev

    cstar = json.loads((ROOT / "predictions" / "cstar.json").read_text())
    C = int(cstar["C_star"] or 2000)
    curve = json.loads((DATA / "p1_best_so_far.json").read_text())
    k_best = curve[min(C, len(curve)) - 1]["best_k"]
    p1rows = {r["k"]: r for r in map(json.loads, (DATA / "p1_search.jsonl").read_text().splitlines())}
    from baselines import p1_program

    p1_code = p1_program(p1rows[k_best]["w"])
    mem = members(p1_code)
    refs = ev.load_references()
    nn = ev.load_baseline_nn()
    pool = ev.make_pool(1)
    res = []
    for m in mem:
        r = pool.submit(ev.job_program, m["code"], True).result()
        m2 = dict(m)
        m2["selection_label"] = r["label"]
        m2["probe_label"] = r.get("probe_label")
        if r["label"] == "valid":
            g = ev.gaps_from_lengths(r["lengths"], refs["selection"])
            F, g50, g100 = ev.fitness(g, nn["G50"], nn["G100"])
            m2.update(F=F, G50=g50, G100=g100)
        m2["admitted"] = r["label"] == "valid" and r.get("probe_label") == "probe_valid"
        if not m2["admitted"]:
            m2["not_admitted_reason"] = f"{r['label']} / {r.get('probe_label')}: {str(r.get('reason'))[:200]}"
        else:
            (DATA / "corpus_decisions").mkdir(exist_ok=True)
            (DATA / "corpus_decisions" / f"{m['name']}.json").write_text(json.dumps(r["decisions"]))
            for set_name in ("heldout", "heldout_ext", "tsplib"):
                s = pool.submit(ev.job_set, m["code"], set_name, 600).result()
                if s["label"] != "valid":
                    m2[f"{set_name}_label"] = s["label"]
                    continue
                if set_name == "tsplib":
                    names = [t for t in ev.load_payload.__globals__["load_tsplib"]()] if False else None
                    from tsp_task import load_tsplib

                    tg = ev.tsplib_gaps(s["tours"], [t["name"] for t in load_tsplib()])
                    m2["tsplib_gaps"] = tg
                    m2["tsplib_mean"] = float(np.mean(list(tg.values())))
                else:
                    g = ev.gaps_from_lengths(s["lengths"], refs[set_name])
                    m2[f"{set_name}_gaps"] = g.tolist()
                    m2["G200" if set_name == "heldout" else "G200_ext"] = float(g.mean())
        logger.info(f"corpus {m['name']}: {m2['selection_label']}/{m2.get('probe_label')} F={m2.get('F')} "
                    f"G200={m2.get('G200')} admitted={m2['admitted']}")
        res.append(m2)
    pool.shutdown()
    out = {"utc": utc_now(), "C_star_for_P1": C, "P1_eval_index": k_best, "members": res, "not_found": NOT_FOUND,
           "n_admitted": sum(m["admitted"] for m in res)}
    write_json(RESULTS / "corpus.json", out)
    from commit import amend

    amend("COMMIT#3_corpus", ["results/corpus.json", "src/corpus.py"])


if __name__ == "__main__":
    main()
