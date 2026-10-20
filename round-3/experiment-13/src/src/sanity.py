#!/usr/bin/env python3
"""T9 post-run sanity checks: twin D share >= 0.9 (flag otherwise), nonce D share near the twin's, sham vs
distinctive one-shot avoidance, exact per-template counts, no sample longer than 1,024 new tokens, and the first
ban request after the seal."""

from __future__ import annotations

from collections import Counter

from loguru import logger

from common import DEFAULTS, MAX_NEW, RESULTS, TASK_ORDER, WS, read_json, write_json
from vllm_stage import Store

EXPECT = {"twin": 10, "nonce": 10, "ban": 20, "hf_twin": 10, "bandpatch": 10}


def main() -> dict:
    st = Store("")
    out: dict = {"tasks": {}, "problems": []}
    for t in TASK_ORDER:
        rec = {}
        for a in ["twin", "nonce", "oneshot", "sham", "ban", "hf_twin"]:
            labs = [r for r in st.lab_rows(a) if r["task"] == t]
            att = [r for r in labs if r["label"] != "invalid"]
            rec[f"{a}_default_share"] = (sum(r["label"] == DEFAULTS[t] for r in att) / len(att)) if att else None
        rec["twin_flag_below_0.9"] = (rec["twin_default_share"] or 0) < 0.9
        rec["nonce_minus_twin"] = None if rec["nonce_default_share"] is None else \
            rec["nonce_default_share"] - rec["twin_default_share"]
        if rec["oneshot_default_share"] is not None and rec["sham_default_share"] is not None:
            rec["sham_moves_fewer_than_distinctive"] = (1 - rec["sham_default_share"]) < (1 - rec["oneshot_default_share"])
        out["tasks"][t] = rec
    for a, n in EXPECT.items():
        rows = st.raw_rows(a)
        if not rows:
            continue
        c = Counter((r["task"], r["template"]) for r in rows)
        bad = {f"{k[0]}|{k[1]}": v for k, v in c.items() if v != n}
        if bad:
            out["problems"].append({"arm": a, "unexpected_counts": bad})
    rr = Counter((r["task"], r["template"], r["arm"]) for r in st.raw_rows("rand"))
    bad = {"|".join(k): v for k, v in rr.items() if v != 10}
    if bad:
        out["problems"].append({"arm": "rand", "unexpected_counts": bad})
    longest = 0
    for a in ["twin", "oneshot", "sham", "persistent", "iter1", "iter2", "iter3", "nonce", "novelty", "rand",
              "hf_twin", "ban", "bandpatch"]:
        for r in st.raw_rows(a):
            longest = max(longest, r.get("n_tokens") or 0)
    out["max_new_tokens_observed"] = longest
    if longest > MAX_NEW:
        out["problems"].append({"too_long": longest})
    bt = RESULTS / "ban_sampling_times.json"
    if bt.exists():
        b = read_json(bt)
        out["seal_utc"], out["first_ban_request_utc"] = b["seal_utc"], b["first_ban_request_utc"]
        out["ban_after_seal"] = b["first_ban_request_utc"] > b["seal_utc"]
        if not out["ban_after_seal"]:
            out["problems"].append("first ban request not after the seal")
    out["n_problems"] = len(out["problems"])
    write_json(RESULTS / "sanity.json", out)
    logger.info(f"sanity: {out['n_problems']} problems; max new tokens {longest}; "
                f"twin<0.9: {[t for t, v in out['tasks'].items() if v['twin_flag_below_0.9']]}")
    return out


if __name__ == "__main__":
    from common import setup_logging

    setup_logging("s3_sanity")
    main()
