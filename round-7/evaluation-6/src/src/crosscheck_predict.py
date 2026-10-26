"""Cross-check of the raw-row recomputation against the predict_* fields of each dependency's full_method_out.json.

The record repair recomputes from the rawest rows (labels.jsonl, samples.jsonl, judgements.jsonl); this module
re-derives the same counts from the exp_gen_sol_out datasets the dependencies published, so a disagreement between
an artifact's raw rows and its own published predictions would show up here. Files are read in place (hashed, not
vendored: together they are 36 MB) and released one at a time.
"""

from __future__ import annotations

import gc
import json
from collections import defaultdict
from typing import Any

from common import DEP_DIRS, sha256_file

DEFAULT = {"T10": "union_find", "T2": "dijkstra"}


def _load(art: str) -> tuple[dict, str]:
    p = DEP_DIRS[art] / "full_method_out.json"
    return json.loads(p.read_text()), sha256_file(p)


def crosscheck(items_0a_cells: dict, g8_pn: dict, nla_units: list[dict]) -> dict[str, Any]:
    out: dict[str, Any] = {"checks": [], "files": {}}
    absent = [a for a in ("art_lpQalcAXMGr1", "art_rMlbrjVB1c__", "art_dbUtqBjT0tPf")
              if not (DEP_DIRS[a] / "full_method_out.json").exists()]
    if absent:  # the published folder alone does not carry the dependencies' full_method_out.json files
        return {"checks": [], "files": {}, "n_checks": 0, "n_mismatches": 0,
                "skipped": f"full_method_out.json not reachable for {absent}; set AII_DEPS_ROOT"}

    def chk(name: str, got: Any, want: Any) -> None:
        out["checks"].append({"check": name, "from_predict": got, "from_raw_rows": want, "ok": got == want})

    # engine control: engine_pn predict_a..d = 'label|pass' per CRN slot
    d, h = _load("art_lpQalcAXMGr1")
    out["files"]["art_lpQalcAXMGr1:full_method_out.json"] = h
    agg = defaultdict(lambda: [0, 0])
    for ds in d["datasets"]:
        if ds["dataset"] != "engine_pn":
            continue
        for ex in ds["examples"]:
            t = ex["metadata_task"]
            arm = ex["metadata_arm"]
            for e in "abcd":
                v = ex.get(f"predict_{e}")
                if not v:
                    continue
                lab, _, ps = v.partition("|")
                ok = ps == "pass"
                a = agg[f"{e}|{t}|{arm}"]
                a[0] += ok
                a[1] += ok and lab not in (DEFAULT[t], "other", "invalid", "")
    for k, v in g8_pn.items():
        if k in agg:
            chk(f"engine_pn|{k}|correct", agg[k][0], v["correct"])
            chk(f"engine_pn|{k}|correct_off_default", agg[k][1], v["correct_off"])
    del d
    gc.collect()
    # exchange experiment: stage_a_exchange, one example per task x cell x slot
    d, h = _load("art_rMlbrjVB1c__")
    out["files"]["art_rMlbrjVB1c__:full_method_out.json"] = h
    sa = defaultdict(lambda: [0, 0, 0])
    for ds in d["datasets"]:
        if ds["dataset"] != "stage_a_exchange":
            continue
        for ex in ds["examples"]:
            k = f"{ex['metadata_task']}|{ex['metadata_cell']}"
            Y = ex["metadata_Y"]
            ok = bool(ex["metadata_passed"]) if not isinstance(ex["metadata_passed"], str) else \
                ex["metadata_passed"].lower() == "true"
            sa[k][0] += 1
            sa[k][1] += ex["metadata_label"] == Y
            sa[k][2] += ex["metadata_label"] == Y and ok
    n_cmp = 0
    for k, (n, att, cor) in sorted(sa.items()):
        if k in items_0a_cells and items_0a_cells[k]["n"] == n:
            chk(f"stage_a_exchange|{k}|attempted_Y", att, items_0a_cells[k]["attempted_Y"])
            chk(f"stage_a_exchange|{k}|correct_Y", cor, items_0a_cells[k]["correct_Y"])
            n_cmp += 1
    out["stage_a_cells_compared"] = n_cmp
    out["stage_a_cells_in_dataset"] = len(sa)
    del d
    gc.collect()
    # NLA: nla_readout_states predict_nla / predict_outside_reader at the N6 units
    d, h = _load("art_dbUtqBjT0tPf")
    out["files"]["art_dbUtqBjT0tPf:full_method_out.json"] = h
    st = {}
    for ds in d["datasets"]:
        if ds["dataset"] != "nla_readout_states":
            continue
        for ex in ds["examples"]:
            st[ex["metadata_state_id"]] = ex
    del d
    gc.collect()
    b = c = found = 0
    for u in nla_units:
        ex = st.get(u["sid"])
        if ex is None:
            continue
        found += 1
        x = int(ex.get("predict_nla") == ex["output"])
        y = int(ex.get("predict_outside_reader") == ex["output"])
        b += x == 1 and y == 0
        c += x == 0 and y == 1
    out["nla_units_found_in_dataset"] = found
    chk("nla_readout_states|N6_units_found", found, len(nla_units))
    chk("nla_readout_states|N6_b", b, sum(1 for u in nla_units if u["x"] == 1 and u["y"] == 0))
    chk("nla_readout_states|N6_c", c, sum(1 for u in nla_units if u["x"] == 0 and u["y"] == 1))
    out["n_checks"] = len(out["checks"])
    out["n_mismatches"] = sum(not r["ok"] for r in out["checks"])
    return out
