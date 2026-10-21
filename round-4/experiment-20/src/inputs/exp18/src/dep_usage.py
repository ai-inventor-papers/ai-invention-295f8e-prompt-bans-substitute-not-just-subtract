"""How every dataset of the declared dependency (art_j3Rm_lr2nzR6, full_data_out.json) enters this artifact.

- leetcodedataset, mercury, thealgorithms_python, kodcode_algorithmic, xlcost_python: the known-solution corpus of the
  novelty audit (audit.build_known_solutions -> inputs/known_solutions.jsonl).
- llm_creativity: an external label prior for T2 (blind-judge labels of 225 programs from another study), compared
  with this artifact's T2 step-0 composition.
- concreteness_norms: provenance check of every neutral noun this artifact rendered (bench twins: first noun of the
  default's slot; path twins: exp8 nouns), with concreteness, frequency and Qwen3 token counts.
- clrs_text: the bench tracer's access-order tests come from it (exp11); counted per bench-linked algorithm here.
- humanevalplus, enamel: harness smoke-test / stress material of the bench build (exp11); counted, not re-run.
Writes results/dependency_usage.json.
"""

from __future__ import annotations

import json
from collections import Counter

from config import DEP_DATASET, RESULTS, TASKS, read_jsonl, setup_logging, utc_now, write_json
from prompts import bench_noun


def main() -> None:
    import ijson

    setup_logging("dep_usage")
    nouns = {TASKS[t]["default"]: bench_noun(t, TASKS[t]["default"]) for t in ("T03", "T04", "T06", "T10")}
    path_nouns = {"man", "house", "baby", "car", "guy"}
    want = set(nouns.values()) | path_nouns
    out: dict = {"utc": utc_now(), "datasets": {}}
    llm = Counter()
    noun_rows = {}
    clrs = Counter()
    counts = Counter()
    with (DEP_DATASET / "full_data_out.json").open("rb") as f:
        for ds in ijson.items(f, "datasets.item"):
            name = ds["dataset"]
            counts[name] = len(ds["examples"])
            for ex in ds["examples"]:
                if name == "llm_creativity":
                    llm[str(ex.get("metadata_t02_mode"))] += 1
                elif name == "concreteness_norms" and ex.get("input") in want:
                    noun_rows[ex["input"]] = {"concreteness": ex.get("output"),
                                              "subtlex_frequency": ex.get("metadata_subtlex_frequency"),
                                              "qwen3_tokens_with_leading_space":
                                                  ex.get("metadata_qwen3_tokens_with_leading_space"),
                                              "noun_bank_candidate": ex.get("metadata_noun_bank_candidate")}
                elif name == "clrs_text":
                    for link in json.loads(str(ex.get("metadata_bench_links") or "[]").replace("'", '"')):
                        clrs[link] += 1
    t2_step0 = Counter(r["label"] for r in read_jsonl(RESULTS.parent / "data" / "samples_walk.jsonl")
                       if r["task"] == "T2" and r["step"] == 0)
    n_llm = sum(llm.values())
    out["datasets"] = {
        "leetcodedataset": {"n": counts["leetcodedataset"], "use": "known-solution corpus (reference solutions)"},
        "mercury": {"n": counts["mercury"], "use": "known-solution corpus (human solutions)"},
        "thealgorithms_python": {"n": counts["thealgorithms_python"], "use": "known-solution corpus (textbook code)"},
        "kodcode_algorithmic": {"n": counts["kodcode_algorithmic"], "use": "known-solution corpus (named-mode code)"},
        "xlcost_python": {"n": counts["xlcost_python"], "use": "known-solution corpus (named-mode code)"},
        "llm_creativity": {"n": counts["llm_creativity"], "use": "external T2 label prior",
                           "t2_mode_counts": dict(llm),
                           "dijkstra_share": llm.get("dijkstra", 0) / n_llm if n_llm else None,
                           "this_artifact_T2_step0": dict(t2_step0)},
        "concreteness_norms": {"n": counts["concreteness_norms"], "use": "provenance of the rendered neutral nouns",
                               "bench_default_nouns": nouns, "rows": noun_rows,
                               "all_found": all(w in noun_rows for w in want)},
        "clrs_text": {"n": counts["clrs_text"], "use": "bench tracer access-order tests (exp11)",
                      "traces_per_bench_link": dict(clrs)},
        "humanevalplus": {"n": counts["humanevalplus"], "use": "bench harness smoke test (exp11); not re-run here"},
        "enamel": {"n": counts["enamel"], "use": "bench stress calibration material (exp11); not re-run here"},
    }
    write_json(RESULTS / "dependency_usage.json", out)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("n", "dijkstra_share", "all_found")}
                      for k, v in out["datasets"].items()}))


if __name__ == "__main__":
    main()
