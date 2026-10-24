"""Read the declared dependency art_j3Rm_lr2nzR6 (full_data_out.json): scan ALL 10 datasets for TSP-related code,
extract the thealgorithms TSP records (corpus textbook members) and 20 HumanEval+ canonical solutions, and run the
sandbox fork+rlimit harness check (20 canonical solutions must pass, 5 planted mutants must fail).

The dependency folder is read through ONE setting: env ART_J3RM_DIR (default: sibling folder ../art_j3Rm_lr2nzR6).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESULTS, ROOT, setup_logging, utc_now, write_json  # noqa: E402

logger = setup_logging("dep_extract")
DEP_DIR = Path(os.environ.get("ART_J3RM_DIR", str(ROOT.parent / "art_j3Rm_lr2nzR6")))
TSP_RE = re.compile(r"salesman|\btsp\b|nearest[ _-]?neighbou?r tour|hamiltonian (cycle|circuit)", re.I)
PROFIT_RE = re.compile(r"maximi[sz]e the profit as the salesman", re.I)


def main() -> None:
    full = DEP_DIR / "full_data_out.json"
    logger.info(f"loading {full}")
    d = json.loads(full.read_text())
    usage = {"utc": utc_now(), "source": "art_j3Rm_lr2nzR6/full_data_out.json",
             "sha256": hashlib.sha256(full.read_bytes()).hexdigest(), "datasets": {}}
    tsp_records, he = [], []
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        hits = []
        for i, e in enumerate(ex):
            text = (e.get("input") or "") + "\n" + (e.get("output") or "")
            if TSP_RE.search(text) and not PROFIT_RE.search(text):
                hits.append(i)
        usage["datasets"][name] = {"n_examples": len(ex), "n_tsp_mentions": len(hits)}
        if name == "thealgorithms_python":
            tsp_records = [ex[i] for i in hits]
        if name == "humanevalplus":
            he = ex[:20]
        if hits and name != "thealgorithms_python":
            usage["datasets"][name]["tsp_examples_head"] = [(ex[i].get("input") or "")[:160] for i in hits[:5]]
    del d
    (DATA / "dep").mkdir(exist_ok=True)
    (DATA / "dep" / "thealgorithms_tsp.json").write_text(json.dumps(tsp_records, indent=1))
    (DATA / "dep" / "humanevalplus_20.json").write_text(json.dumps(he, indent=1))
    t9 = ROOT / "inputs" / "tsp9" / "data" / "dep" / "thealgorithms_tsp.json"
    if t9.exists():
        old = json.loads(t9.read_text())
        old_inputs = sorted(hashlib.sha256((r.get("input") or "").encode()).hexdigest() for r in old.get("tsp", []))
        new_inputs = sorted(hashlib.sha256((r.get("input") or "").encode()).hexdigest() for r in tsp_records)
        usage["tsp9_crosscheck"] = {"tsp9_n": len(old_inputs), "new_n": len(new_inputs),
                                    "identical_record_set": old_inputs == new_inputs,
                                    "overlap": len(set(old_inputs) & set(new_inputs))}
    usage["thealgorithms_tsp_titles"] = [(r.get("metadata_path") or r.get("metadata_file_path") or
                                          (r.get("input") or "")[:120]) for r in tsp_records]
    usage["used_for"] = {
        "thealgorithms_python": "TSP records -> textbook corpus members (ant-colony construction step without "
                                "pheromone = argmax d^-beta; nearest-neighbour routines)",
        "humanevalplus": "20 canonical solutions + 5 planted mutants through the sandbox fork+rlimit path",
        "other datasets": "scanned for TSP-related code (counts above); none is a constructive-TSP heuristic, so "
                          "they enter no comparison (bench data for other tasks)"}
    # ------------------------------------------------ harness check through the same fork + rlimit path
    import sandbox

    res = []
    for e in he:
        code = (e["input"] + e["output"] + "\n\n" + e["metadata_test"] + f"\n\ncheck({e['metadata_entry_point']})\n")
        r = sandbox.fork_pycheck(code, cpu_limit=20)
        res.append({"task": e.get("metadata_task_id"), "ok": r["ok"], "cls": r.get("cls")})
    mut = []
    for e in he[:5]:
        ep = e["metadata_entry_point"]
        bad = (e["input"] + e["output"] + f"\n\n_orig = {ep}\ndef {ep}(*a, **k):\n    r = _orig(*a, **k)\n"
               "    return r[::-1] if isinstance(r, (list, str)) and len(r) > 1 else (not r if isinstance(r, bool) "
               "else (r + 1 if isinstance(r, (int, float)) else None))\n\n" + e["metadata_test"] + f"\n\ncheck({ep})\n")
        r = sandbox.fork_pycheck(bad, cpu_limit=20)
        mut.append({"task": e.get("metadata_task_id"), "failed_as_required": not r["ok"], "cls": r.get("cls")})
    usage["harness_check"] = {"canonical_pass": sum(x["ok"] for x in res), "n": len(res), "rows": res,
                              "mutants_failed": sum(x["failed_as_required"] for x in mut), "n_mutants": len(mut),
                              "mutant_rows": mut}
    write_json(RESULTS / "dependency_usage.json", usage)
    logger.info(f"dependency: { {k: v['n_tsp_mentions'] for k, v in usage['datasets'].items()} }; harness "
                f"{usage['harness_check']['canonical_pass']}/20 pass, {usage['harness_check']['mutants_failed']}/5 "
                f"mutants fail; crosscheck {usage.get('tsp9_crosscheck')}")


if __name__ == "__main__":
    main()
