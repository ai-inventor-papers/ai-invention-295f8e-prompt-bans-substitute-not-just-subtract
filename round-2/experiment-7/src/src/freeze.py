#!/usr/bin/env python3
"""Step 8: freeze what the confirmation bench consumes (aim profiles, ladder profile, templates/nouns/padding,
code hashes), each appended to commitments.log as a hash chain. This artifact does NOT run the confirmation."""

from __future__ import annotations

import numpy as np
from loguru import logger

from c1 import RAND_NAMES, Ctx, family_profiles, ladder_u, needed_conds
from config import (FROZEN, MODES, PROMPTS, RESULTS, ROOT, TASKS, WS, commit, read_json, setup_logging, sha256_file,
                    utc_now, write_json)
from frlp import CellArrays, build_task_data


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("freeze")
    tds = build_task_data()
    assoc = read_json(RESULTS / "association.json")
    aim, ladder = {"utc": utc_now(), "prime_and_veto": {}, "association": assoc["profiles"],
                   "rule": "PV_X(j) = mean_w [L_j(mention_w X) - L_j(neutral_w X)] on all programs (noun A on h1, "
                           "noun B on h2); association A_X(j) = (count_j + 1) / (20 + |S_X|)"}, {"utc": utc_now()}
    for t in TASKS:
        td = tds[t]
        conds, virtual = needed_conds(t)
        ca = CellArrays(td, conds, "primary", virtual)
        cx = Ctx(ca, ca.cells())
        js = ca.js
        for x in MODES[t]:
            pv = np.nanmean([cx.v(f"mention|{x}|{w}") - cx.v(f"neutral|{x}|{w}|AB") for w in WS], axis=0)
            aim["prime_and_veto"][f"{t}|{x}"] = {j: float(v) for j, v in zip(js, pv) if j != x and np.isfinite(v)}
        fp = family_profiles(cx, WS, RAND_NAMES)
        u = ladder_u(fp)
        ladder[t] = {"measurable": js, "u": dict(zip(js, u.tolist())),
                     "families": {k: dict(zip(js, v.tolist())) for k, v in fp.items()},
                     "rule": "u = mean(NONCE, RAND, NOV); NONCE = mean_w [L(nonce ban_w) - L(nonce neutral_w)]; "
                             "RAND = mean over 6 matched-norm random prompt-band edits [L(edit) - L(BASE0)]; "
                             "NOV = L(novelty) - L(BASE0)"}
    pv2 = read_json(PROMPTS / "prompts_v2.json")
    tnp = {"templates": pv2["rules"], "nouns": pv2["nouns"], "alignment": pv2["alignment"],
           "spec_suffix_tokens": pv2["spec_suffix_tokens"]}
    code = {f: sha256_file(ROOT / f) for f in ("src/frlp_score.py", "src/frlp.py", "src/gate.py", "src/c1.py",
                                               "src/scrub.py", "prompts/prompts_v2.json")}
    for name, obj in (("aim_profiles.json", aim), ("ladder_profile.json", ladder),
                      ("templates_nouns_padding.json", tnp), ("code_sha256.json", code)):
        write_json(FROZEN / name, obj)
        commit(FROZEN / name, f"frozen for the confirmation bench: {name}")


if __name__ == "__main__":
    main()
