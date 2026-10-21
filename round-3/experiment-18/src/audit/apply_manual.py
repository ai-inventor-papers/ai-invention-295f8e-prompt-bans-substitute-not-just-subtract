"""Apply the executor's manual-pass decisions (audit/manual_round*.py, written after reading every program they
cover) to the audit records and write results/manual_audit.json.  A record no rule covers is left unresolved and
listed, so nothing is silently classified."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_rules():
    rules = []
    for p in sorted((ROOT / "audit").glob("manual_round*.py"), reverse=True):  # latest round first
        spec = importlib.util.spec_from_file_location(p.stem, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        rules += [(p.stem, r) for r in m.RULES]
    return rules


def main():
    d = json.loads((ROOT / "results" / "novelty_audit_judges.json").read_text())
    rules = load_rules()
    out, uncovered = {}, []
    for r in d["records"]:
        code = r.get("code") or ""
        hit = None
        for src, (pred, cls, lab, why) in rules:
            if pred(r["task"], code):
                hit = (src, cls, lab, why)
                break
        if hit is None:
            uncovered.append(r["sample_id"])
            continue
        et = r.get("extra_tests") or {}
        out[r["sample_id"]] = {"final_class": hit[1], "catalogue_label_if_miss": hit[2], "justification": hit[3],
                               "rule_source": hit[0], "extra_tests_pass": et.get("n_pass"), "extra_tests_n": et.get("n"),
                               "judge_A": r["judge_A"].get("class"), "judge_B": r["judge_B"].get("class"),
                               "disagreement_resolved": r["judge_A"].get("class") != r["judge_B"].get("class")}
    res = {"note": "executor's manual pass: every program was read next to its nearest known solutions and both judge "
                   "verdicts, and run on 3 extra seeded random inputs; decisions are recorded as rules in "
                   "audit/manual_round*.py, each written after reading the programs it covers",
           "n_records": len(d["records"]), "n_classified": len(out), "uncovered": uncovered, "records": out}
    (ROOT / "results" / "manual_audit.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"n": len(d["records"]), "classified": len(out), "uncovered": uncovered[:20]}))


if __name__ == "__main__":
    main()
