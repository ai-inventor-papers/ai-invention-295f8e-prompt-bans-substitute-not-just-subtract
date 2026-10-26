#!/usr/bin/env python3
"""V3 final classes. Judge gate unmet (commit #6): judges are advisory and the arm-blind manual read decides.
NOVEL = NB criteria + manual read NOT_KNOWN (+ flag 'judge gate unmet'). KNOWN_FAMILY_NEW_PARAMETERS from the manual read
is its own non-novel class. Sensitivities: also require the gate-passing judge (mistral) NOT_KNOWN; require a majority
of the three advisory judges NOT_KNOWN; V3-strict (max agreement < 0.9 against all 3,843 ab-grid points)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GATED = "mistralai/mistral-medium-3.1"


def main() -> None:
    v3 = json.loads((ROOT / "results" / "v3_candidates.json").read_text())
    reads = json.loads((ROOT / "audit" / "manual_read.json").read_text())
    jc = json.loads((ROOT / "results" / "judge_calls.json").read_text()) if (ROOT / "results" / "judge_calls.json").exists() else {"rows": []}
    gate = json.loads((ROOT / "results" / "judge_gate.json").read_text())
    arm_map = json.loads((ROOT / "audit" / "arm_map_SEALED.json").read_text())
    jrow = {r["anon_id"]: r for r in jc.get("rows", [])}
    classes = []
    for c in v3.get("audited", []):
        aid = c["anon_id"]
        man = reads[aid]["manual_class"]
        jr = jrow.get(aid, {})
        labs = {m: (jr.get(m) or {}).get("label") for m in jc.get("judges", [])}
        if man == "KNOWN_FAMILY_NEW_PARAMETERS":
            final = "KNOWN_FAMILY_NEW_PARAMETERS"
        elif man == "NOT_KNOWN" and c["NB"]:
            final = "NOVEL"
        elif man == "DEGENERATE":
            final = "DEGENERATE"
        else:
            final = "KNOWN"
        nk = sum(1 for v in labs.values() if v == "NOT_KNOWN")
        classes.append({"anon_id": aid, "pid": c["pid"], "stream": arm_map[aid]["stream"], "arm": c["arm"],
                        "seed": c["seed"], "F": c["F"], "exc_FSW5k": c["exc_FSW5k"], "exc_OR3": c["exc_OR3"],
                        "heldout_all": c.get("heldout_all"), "max_corpus_agreement": c["max_corpus_agreement"],
                        "nearest_corpus": c["nearest_corpus"], "max_abgrid_agreement": c["max_abgrid_agreement"],
                        "nearest_abgrid": c["nearest_abgrid"], "joint_size": c.get("joint_size"),
                        "manual_class": man, "rule_in_words": reads[aid]["rule_in_words"], "judge_labels": labs,
                        "judge_texts": {m: (jr.get(m) or {}).get("text", "")[:700] for m in labs},
                        "final_class": final, "NB_strict": c["NB_strict"],
                        "novel_if_gated_judge_agrees": final == "NOVEL" and labs.get(GATED) == "NOT_KNOWN",
                        "novel_if_judge_majority": final == "NOVEL" and nk >= 2, "code": c["code"]})
    novel = [c for c in classes if c["final_class"] == "NOVEL"]
    out = analysis.v3([{"anon_id": c["anon_id"], "cls": c["final_class"]} for c in classes], v3["n_NB"])
    out.update({"flag": "judge gate unmet: judges advisory, manual read decides (commit #6)",
                "judge_gate_scores": {m: v["score"] for m, v in gate["per_model"].items()},
                "n_candidates": v3["n_candidates"], "n_NB": v3["n_NB"], "n_NB_strict": v3["n_NB_strict"],
                "n_joint_clusters": v3.get("n_joint_clusters"), "n_unaudited_representatives": v3.get("n_unaudited_representatives"),
                "class_counts": dict(Counter(c["final_class"] for c in classes)),
                "manual_counts": dict(Counter(c["manual_class"] for c in classes)),
                "novel_strict_count": sum(c["NB_strict"] for c in novel),
                "novel_if_gated_judge_agrees": sum(c["novel_if_gated_judge_agrees"] for c in classes),
                "novel_if_judge_majority": sum(c["novel_if_judge_majority"] for c in classes),
                "judge_label_counts": {m: dict(Counter(c["judge_labels"].get(m) for c in classes)) for m in jc.get("judges", [])},
                "positive_control_NB_with_permuted_corpus": v3.get("positive_control_NB_with_permuted_corpus"),
                "positive_control_note": "permuting corpus vectors did not raise NB: every candidate passing both held-out bars "
                                         "already had max corpus agreement < 0.9, so the 0.9 probe filter did no work here "
                                         "(consistent with the calibration: c14~abWF(1,21) agree 0.59)",
                "closest_miss": v3.get("lowest_max_agreement_candidate") and {k: v3["lowest_max_agreement_candidate"][k] for k in
                                                                              ("pid", "nearest_corpus", "max_corpus_agreement")},
                "novel": [{k: c[k] for k in ("anon_id", "pid", "stream", "arm", "seed", "F", "exc_FSW5k", "exc_OR3", "heldout_all",
                                             "max_corpus_agreement", "nearest_corpus", "max_abgrid_agreement",
                                             "rule_in_words", "judge_labels", "code")} for c in novel],
                "per_arm": {}, "classes": classes})
    for arm in ["T1.0", "T1.6", "DTB", "RPB", "IDEA", "NS"]:
        nb = [x for x in v3["candidates"] if x["arm"] == arm and x["NB"]]
        aud = [c for c in classes if c["arm"] == arm]
        out["per_arm"][arm] = {"NB_candidates": len(nb), "audited": len(aud),
                               "NOVEL": sum(c["final_class"] == "NOVEL" for c in aud),
                               "KNOWN_FAMILY": sum(c["final_class"] == "KNOWN_FAMILY_NEW_PARAMETERS" for c in aud)}
    (ROOT / "results" / "v3_final.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("verdict", "n_audited", "n_novel", "class_counts", "novel_if_gated_judge_agrees",
                                          "novel_if_judge_majority", "per_arm", "judge_label_counts")}, indent=1))


if __name__ == "__main__":
    main()
