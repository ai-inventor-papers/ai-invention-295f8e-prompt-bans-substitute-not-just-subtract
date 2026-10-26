"""Direction-required test: re-derive j*, the candidate set and the forced token of 50 logged DTB and RPB calls from
their logged request-1 token ids, top-20 log probabilities and RNG seeds; all 50 must match.
Run: .venv/bin/python tests/test_rederive_forcing.py [data|data/pilot]   (writes results/rederive_forcing.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from common import RESULTS, read_jsonl, write_json  # noqa: E402
from dtb import choose_branch  # noqa: E402
from prompt import tokenizer  # noqa: E402


def main() -> None:
    out_dir = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "data")
    tok = tokenizer()
    recs = []
    for arm in ("DTB", "RPB"):
        for p in sorted((out_dir / "requests").glob(f"{arm}_*.jsonl")):
            recs += [r for r in read_jsonl(p) if r.get("branch") and r.get("r1", {}).get("token_ids")]
    recs = sorted(recs, key=lambda r: (r["arm"], r["seed"], r["call_idx"]))
    pick = [r for r in recs if r["arm"] == "DTB"][:25] + [r for r in recs if r["arm"] == "RPB"][:25]
    rows, ok = [], 0
    for r in pick:
        r1 = r["r1"]
        top = [{int(k): float(v) for k, v in d.items()} for d in r1["top"]]
        br = choose_branch(tok, r1["token_ids"], top, len(r1["text"]), "entropy" if r["arm"] == "DTB" else "random",
                           r["seed"], r["arm"], r["call_idx"])
        lg = r["branch"]
        same = (br["no_branch"] == lg["no_branch"] and br.get("j_star") == lg.get("j_star") and
                br.get("forced_id") == lg.get("forced_id") and br.get("candidates") == lg.get("candidates"))
        ok += same
        rows.append({"arm": r["arm"], "seed": r["seed"], "call": r["call_idx"], "match": same,
                     "j_star": lg.get("j_star"), "forced_id": lg.get("forced_id")})
    res = {"n": len(pick), "n_match": ok, "all_match": ok == len(pick) and len(pick) == 50, "rows": rows,
           "source": str(out_dir.relative_to(ROOT))}
    write_json(RESULTS / f"rederive_forcing_{out_dir.name}.json", res)
    print(f"re-derived forcing: {ok}/{len(pick)} match")
    assert res["all_match"], "forcing re-derivation mismatch"


if __name__ == "__main__":
    main()
