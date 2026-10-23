#!/usr/bin/env python3
"""T3 scrub test (20 programs: alias audit, suites after scrub, AST node-type sequence unchanged modulo docstrings,
idempotence) and T9 commitment checks (hash chain verifies; every new state row is later than COMMIT1; no sample row
predates COMMIT0a). Writes results/t3_scrub.json and results/t9_commitments.json."""
import ast
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import programs  # noqa: E402
from common import read_json, read_jsonl, utc_now  # noqa: E402
from tpg2 import DATA, RESULTS, commit_utc, verify_chain, write_json  # noqa: E402


def node_seq(code: str) -> list[str]:
    t = ast.parse(code)
    for n in [t] + [x for x in ast.walk(t) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]:
        b = getattr(n, "body", None)
        if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
            n.body = b[1:] or [ast.Pass()]
    return [type(x).__name__ for x in ast.walk(t)]


if __name__ == "__main__":
    rows = [r for r in read_jsonl(DATA / "factorial.jsonl") if r.get("valid")]
    rng = random.Random(0)
    sample = rng.sample(rows, 20)
    res = []
    for r in sample:
        sc = r["scrubbed"]
        res.append({"uid": r["uid"], "alias_hits": len(list(programs.ALIAS_RE.finditer(sc))),
                    "suites_after_scrub": bool(r["scrubbed_passed_48"] and r["scrubbed_passed_41"]),
                    "ast_types_equal": node_seq(r["code"]) == node_seq(sc),
                    "idempotent": programs.scrub(sc)[0] == sc})
    out = {"n": len(res), "all_alias_zero": all(x["alias_hits"] == 0 for x in res),
           "all_suites_pass": all(x["suites_after_scrub"] for x in res),
           "ast_equal_share": sum(x["ast_types_equal"] for x in res) / len(res),
           "idempotent_share": sum(x["idempotent"] for x in res) / len(res), "rows": res, "utc": utc_now()}
    write_json(RESULTS / "t3_scrub.json", out)
    ch = verify_chain()
    c1, c0 = commit_utc("COMMIT1"), commit_utc("COMMIT0a")
    st = {t: [m["utc"] for m in read_json(RESULTS / f"states_{t}.json")["meta"]] for t in ("8b", "32b")}
    raw = [r["utc"] for r in read_jsonl(DATA / "raw_factorial.jsonl")] + [r["utc"] for r in read_jsonl(DATA / "raw_topups_v10.jsonl")]
    t9 = {"chain_ok": ch["ok"], "problems": ch["problems"], "n_commits": len(ch["entries"]), "commit1_utc": c1,
          "commit0a_utc": c0, "states_after_commit1": {t: min(v) > c1 for t, v in st.items()},
          "earliest_state_utc": {t: min(v) for t, v in st.items()},
          "no_sample_before_commit0a": min(raw) > c0, "earliest_sample_utc": min(raw), "utc": utc_now()}
    write_json(RESULTS / "t9_commitments.json", t9)
    print({k: v for k, v in out.items() if k != "rows"}, t9)
