#!/usr/bin/env python3
"""AMENDMENT (COMMIT #3, after the primary Stage 3 results of T10/B3/G were seen, before any of its own samples):
the pass-filtered fork dose. Same knob as A9/A10 (T = d, top-20, at the decision index only; T10 also at index 11
after ' def'), but the tokens whose Stage 2 continuations fail >= 50% of the time (Pfail >= 0.5 in the COMMITTED
token map) are removed from the top-20 at the dosed step. Units: T10 (format-breaking index-10 tokens) and G (the
` queue` token). Doses by the committed rules applied to the filtered composition. It never replaces A9/A10.
Usage: amend8.py  -> predictions/commit3_amendment.json + COMMIT3_amendment
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import PRED_DIR, SAMPLES, SRC, read_json, read_jsonl, utc_now, write_json  # noqa: E402
import commit8 as CM  # noqa: E402
import dose8 as D  # noqa: E402
import units8 as U8  # noqa: E402

PFAIL_BAN = 0.5


def main() -> None:
    assert not any(r.get("arm") in ("A9f", "A10f") for r in read_jsonl(SAMPLES)), "amendment samples exist"
    labels = D.load_labels()
    out = {"utc": utc_now(), "rule": f"ban tokens with committed Pfail >= {PFAIL_BAN} at each dosed node",
           "units": {}}
    for unit in ("T10", "G"):
        M = D.UnitModel(unit, labels)
        bans = {}
        for nd in M.nodes:
            bans[f"{unit}:{nd['id']}"] = {int(t) for t, m in nd["tmap"].items() if m["pfail"] >= PFAIL_BAN}
        if unit == "T10" and M.second:
            bans["T10:n11"] = {int(t) for t, m in M.second["tmap"].items() if m["pfail"] >= PFAIL_BAN}
        D.BAN.clear()
        D.BAN.update(bans)
        role = "collapsed" if unit == "T10" else "mixed"
        dt = D.dose_table(M, role)
        base = M.predict(1.0)
        arms = {}
        for name, T in (("A9f", dt["d1"]), ("A10f", dt["d2"])):
            pr = M.predict(T)
            rp = M.replay_cell(T)
            arms[name] = {"T": T, "attempted": dict(zip(M.C, np.round(pr["P"], 5).tolist())),
                          "correct": dict(zip(M.C, np.round(pr["Pc"], 5).tolist())),
                          "pass_cost": float(pr["fail"] - base["fail"]),
                          "off_default_attempted": M.off_default_share(pr["P"]),
                          "replay": {"attempted": dict(zip(M.C, np.round(rp["P"], 5).tolist())),
                                     "n_changed": rp["n_changed"]}}
        out["units"][unit] = {"bans": {k: sorted(v) for k, v in bans.items()},
                              "ban_str": {k: [M.nodes[0]["info"]["map_token_str"].get(str(t), "?") if not
                                              k.endswith("n11") else
                                              (M.second["info"]["map_token_str"].get(str(t), "?")) for t in sorted(v)]
                                          for k, v in bans.items()},
                              "dose": {k: dt[k] for k in ("d1", "d2", "rule", "max_share", "target_share_d1",
                                                          "T_at_max")},
                              "share_curve": dt["share_curve"], "classes": M.C, "arms": arms}
        D.BAN.clear()
    write_json(PRED_DIR / "commit3_amendment.json", out)
    e = CM.commit("COMMIT3_amendment", [PRED_DIR / "commit3_amendment.json", SRC / "amend8.py", SRC / "dose8.py",
                                        SRC / "engine8.py", SRC / "arms8.py"])
    print("COMMIT #3", e["utc"])
    for u, x in out["units"].items():
        print(u, x["dose"], {a: (round(v["off_default_attempted"], 3), round(v["pass_cost"], 3)) for a, v in
                             x["arms"].items()}, x["ban_str"])


if __name__ == "__main__":
    main()
