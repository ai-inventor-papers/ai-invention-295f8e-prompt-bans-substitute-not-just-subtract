"""S0 inventory: every origin file read (bytes, sha256, rows, keys, label vocabulary, pass/condition field names,
models), the label map (tables/label_map.csv) and row counts with and without code-hash duplicates. A missing declared
file is recorded in deviations rather than stopping the run."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd
from loguru import logger

from common.paths import RESULTS, TABLES, WS, dep, read_jsonl, sha256_file, src, write_json
from common.rows import EXP12_EXTRA, ORIGIN_FILES

OTHER_INPUTS = [("exp7", "results/c1.json"), ("exp7", "results/frlp_cells.jsonl"), ("exp7", "results/ess_table.json"),
                ("exp7", "results/gate.json"), ("exp7", "results/gate_events.json"), ("exp7", "results/sensitivity.json"),
                ("exp7", "results/protocol.json"), ("exp7", "results/timings.json"), ("exp7", "scores/units_done.jsonl"),
                ("exp7", "frozen/aim_profiles.json"), ("exp7", "frozen/ladder_profile.json"), ("exp7", "src/c1.py"),
                ("exp7", "src/frlp.py"), ("exp7", "src/config.py"),
                ("exp10", "results/c1.json"), ("exp10", "results/events.json"), ("exp10", "results/bootstrap_diagnostics.json"),
                ("exp10", "results/aim_null_pooled.json"), ("exp10", "results/collapse.json"), ("exp10", "frlp/cells.jsonl"),
                ("exp10", "frlp/scores_t1.parquet"), ("exp10", "frlp/scores_t2.parquet"),
                ("exp8", "results/analysis.json"), ("exp8", "results/supplementary.json"), ("exp8", "results/natural_frlp.json"),
                ("exp8", "results/c5.json"),
                ("exp9", "results/manifold.json"), ("exp9", "results/persistence.json"), ("exp9", "results/landing.json"),
                ("exp9", "results/los.json"), ("exp9", "results/catalogue_keep.json"), ("exp9", "data/labelled_forced_all.jsonl"),
                ("exp9", "analysis/manifold.py"), ("exp9", "mb/sets.py"),
                ("exp11", "full_method_out.json"), ("exp12", "results/e2_meta.json"), ("exp12", "results/deviations.json"),
                ("exp1", "tasks/t1_grid/spec.txt"), ("exp1", "tasks/t2_wsp/spec.txt")]


def run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    inv, missing = [], []
    for exp, rel in ORIGIN_FILES + [("exp12", f) for f in EXP12_EXTRA]:
        p = dep(exp, rel)
        if not p.exists():
            missing.append(src(exp, rel))
            continue
        rs = read_jsonl(p)
        keys = Counter(k for r in rs for k in r.keys())
        inv.append({"source": src(exp, rel), "kind": "per-program origin file", "bytes": p.stat().st_size,
                    "sha256": sha256_file(p), "rows": len(rs), "keys": sorted(keys),
                    "label_vocabulary": dict(Counter(str(r.get("label", r.get("j"))) for r in rs).most_common(40)),
                    "pass_field": "passed" if "passed" in keys else None,
                    "condition_field": "condition" if "condition" in keys else ("j" if "j" in keys else None),
                    "models": dict(Counter(str(r.get("model")) for r in rs))})
    for exp, rel in OTHER_INPUTS:
        p = dep(exp, rel)
        if not p.exists():
            missing.append(src(exp, rel))
            continue
        inv.append({"source": src(exp, rel), "kind": "result / code file", "bytes": p.stat().st_size,
                    "sha256": sha256_file(p)})
    for d in ("states/t1/base", "states/t2/base"):
        for p in sorted(dep("exp9", d).glob("part_*.npz")):
            inv.append({"source": src("exp9", f"{d}/{p.name}"), "kind": "activation states (read in place, not copied)",
                        "bytes": p.stat().st_size})
    # label map
    lm = Counter((r["exp"], r["task"], str(r["label_raw"]), r["label"], r["label_fine"]) for r in rows)
    pd.DataFrame([{"exp": e, "task": t, "raw_label": raw, "label": lab, "label_fine": fine, "n": n}
                  for (e, t, raw, lab, fine), n in sorted(lm.items())]).to_csv(TABLES / "label_map.csv", index=False)
    with_code = [r for r in rows if r["dedup_key"]]
    counts = {"rows_total": len(rows), "rows_with_code": len(with_code),
              "unique_programs_by_task_code_hash": len({r["dedup_key"] for r in with_code}),
              "rows_by_exp": dict(Counter(r["exp"] for r in rows)),
              "unique_by_exp": {e: len({r["dedup_key"] for r in with_code if r["exp"] == e}) for e in sorted({r["exp"] for r in rows})},
              "label_counts": dict(Counter(r["label"] for r in rows))}
    out = {"files": inv, "missing_declared_files": missing, "counts": counts,
           "excluded_copies": "every other path under inputs/, data_in/ or canon/ of exp7, exp8, exp9, exp10 and exp12 "
                              "(copies of exp1/exp2/exp4) is excluded; exp3 is read only via exp8's pools copy"}
    write_json(WS / "inputs" / "inventory.json", out)
    write_json(RESULTS / "inventory_counts.json", counts)
    logger.info(f"inventory: {len(inv)} files, missing {len(missing)}, rows {len(rows)}")
    return out
