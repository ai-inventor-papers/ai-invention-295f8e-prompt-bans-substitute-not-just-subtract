"""Recompute, from the artifacts' own per-sample rows and result files, the numbers this review cites.

Read-only over the run volume; prints one line per check. Run: python3 verify_numbers.py
"""
import collections
import json
import math
import os
import random
from pathlib import Path

# Runs root: this script sits at <runs>/run_aRfWvcSWjssb/3_invention_loop/iter_2/review_report/review_report/.
RUNS = Path(os.environ.get("AII_RUNS_ROOT", Path(__file__).resolve().parents[5]))
RUN2 = RUNS / "run_aRfWvcSWjssb/3_invention_loop/iter_2/gen_art"
RUN1 = RUNS / "run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art"


def load(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def labels(rows, correct_only=False):
    return dict(collections.Counter(r["label"] for r in rows if (r.get("passed") is True or not correct_only)))


def rare_hill(comp, depth=25, draws=4000, seed=0):
    rng = random.Random(seed)
    pool = [k for k, v in comp.items() for _ in range(v)]
    total = 0.0
    for _ in range(draws):
        c = collections.Counter(rng.sample(pool, depth))
        total += math.exp(-sum((v / depth) * math.log(v / depth) for v in c.values()))
    return total / draws


def main():
    # Route experiment: behaviour per arm, template counts, import first lines.
    r8 = load(RUN2 / "experiment-8/src/data/samples.jsonl")
    for task, banned in (("t1", "bfs"), ("t2", "dijkstra")):
        for arm in ("b", "d", "c", "a", "K0", "K1", "K2"):
            rows = [r for r in r8 if r["task"] == task and r["condition"] == arm]
            share = sum(r["label"] == banned for r in rows) / len(rows)
            imp = sum(r["code"].lstrip().split("\n")[0].strip().startswith(("import", "from")) for r in rows) / len(rows)
            tmpl = collections.Counter(r["template"] for r in rows if r["label"] == banned)
            print(f"route {task} {arm}: banned {share:.2f} import-first {imp:.2f} per-template {[tmpl.get(f'W{i}', 0) for i in range(1, 6)]}")
    a = json.load(open(RUN2 / "experiment-8/src/results/analysis.json"))
    D = {t: a["route_frlp"]["per_task"][t]["D"] for t in ("t1", "t2")}
    print("route F_prompt t1/t2/pooled",
          round(D["t1"]["c"] / D["t1"]["a"], 3), round(D["t2"]["c"] / D["t2"]["a"], 3),
          round((D["t1"]["c"] + D["t2"]["c"]) / (D["t1"]["a"] + D["t2"]["a"]), 3))
    print("route survivor gains t2 full ban", a["survivor_gains"]["t2"]["survivors"], [round(x, 2) for x in a["survivor_gains"]["t2"]["G_a"]])

    # Ban-list experiment: landings, leave-one-survivor, post hoc chi-square inputs, 'other' programs.
    r9 = load(RUN2 / "experiment-9/src/data/samples.jsonl")
    for cond in ("single:bfs", "multi:TOP", "multi:ARC", "multi:SCATTER", "multi:TOP5"):
        print("banlist t1", cond, labels([r for r in r9 if r["task"] == "t1" and r["condition"] == cond]))
    for s in ("dijkstra", "bf_spfa", "bidijkstra", "floyd", "dial"):
        rows = [r for r in r9 if r["task"] == "t2" and r["condition"] == "los:" + s]
        print("los", s, "will", sum(r["label"] == s for r in rows) / len(rows))
    for cond in ("forced:bidijkstra", "forced_desc:bidijkstra", "forced:dial", "forced_desc:dial"):
        rows = [r for r in r9 if r["task"] == "t2" and r["condition"] == cond]
        print("forced", cond, len(rows), labels(rows), "passing as requested",
              sum(r["passed"] and r["label"] == cond.split(":")[1] for r in rows))
    top_other = [r for r in r9 if r["condition"] == "multi:TOP" and r["label"] == "other"]
    print("TOP 'other' programs", len(top_other), "passing", sum(r["passed"] for r in top_other))

    # Llama replication: attempted versus correct compositions.
    r10 = load(RUN2 / "experiment-10/src/data/labelled.jsonl")
    for task, prefix in (("t1", "baseline"), ("t1", "ban:bfs"), ("t2", "baseline"), ("t2", "ban:dijkstra")):
        rows = [r for r in r10 if r["task"] == task and r["condition"].startswith(prefix)]
        print("llama", task, prefix, "attempted", labels(rows), "correct", labels(rows, True))

    # Bench pilots.
    for name in ("samples_pilot.jsonl", "samples_llama_pilot.jsonl"):
        rows = load(RUN2 / "experiment-11/src/data" / name)
        by = collections.defaultdict(list)
        for r in rows:
            by[r["task"]].append(r)
        for task in ("T03", "T04", "T10"):
            print("bench", name, task, "attempted", labels(by[task]), "correct", labels(by[task], True))

    # Likelihood screen: modal-ban residuals and pooled components.
    c1 = json.load(open(RUN2 / "experiment-7/src/results/c1.json"))
    for task, x in (("t1", "bfs"), ("t2", "dijkstra")):
        print("C1 residual", task, x, c1["primary_neutral"]["tasks"][task]["rows"][x]["s"])
    pooled = c1["primary_neutral"]["pooled"]
    print("C1 pooled", pooled["share_point"], pooled["bootstrap"]["V_tot_ci"], pooled["bootstrap"]["V_u_ci"])
    print("C1 mention-reference aim", c1["reference_mention"]["aim_prime_veto"])

    # Knob-table rows (rarefied Hill-1 at depth 25).
    for name, comp in (("semantic seed T2", {"bf": 61, "d": 30, "fw": 1}), ("mention A* T1", {"a": 24, "bfs": 11, "ud": 5, "dfs": 1}),
                       ("novelty T1", {"bfs": 81, "ud": 2, "dfs": 1, "a": 1}), ("modal ban pooled T1", {"dfs": 116, "ud": 12})):
        print("hill", name, round(rare_hill(comp), 3))

    # Correct out-of-catalogue programs across sample files.
    files = {"exp8": RUN2 / "experiment-8/src/data/samples.jsonl", "exp9": RUN2 / "experiment-9/src/data/samples.jsonl",
             "exp12": RUN2 / "experiment-12/src/results/samples.jsonl", "exp10": RUN2 / "experiment-10/src/data/labelled.jsonl",
             "it1_exp1": RUN1 / "experiment-1/src/data/samples.jsonl", "it1_exp4": RUN1 / "experiment-4/src/data/samples.jsonl",
             "it1_exp5": RUN1 / "experiment-5/src/runs/samples.jsonl", "it1_exp6": RUN1 / "experiment-6/src/results/samples.jsonl"}
    n_all = n_other = 0
    for key, path in files.items():
        rows = load(path)
        hits = [r for r in rows if str(r.get("label")).lower() == "other" and r.get("passed") is True]
        n_all += len(rows)
        n_other += len(hits)
        print("correct 'other'", key, len(hits), "of", len(rows))
    print("correct 'other' total", n_other, "of", n_all)


if __name__ == "__main__":
    main()
