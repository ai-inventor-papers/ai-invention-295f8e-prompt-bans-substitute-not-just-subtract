"""One-off conversion: split every states_<task>.npz / disp_<task>.npz into parts (< 45 MiB), verify exact equality
of every array through npz_parts.load, then delete the original."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import npz_parts  # noqa: E402

ROW = {"states": ("smean", "R", "pids"), "disp": ("delta", "deltaR", "keys")}
for f in sorted((ROOT / "states").glob("*.npz")):
    kind = f.name.split("_")[0]
    if kind not in ROW or ".part" in f.name or f.name.startswith("disp_c2c"):
        continue
    z = np.load(f)
    full = {k: z[k] for k in z.files}
    rows = {k: full[k] for k in ROW[kind]}
    const = {k: v for k, v in full.items() if k not in rows}
    # write parts next to the original under a temporary stem first, verify, then swap
    tmp = f.with_name(f.stem + "_tmpsplit.npz")
    ps = npz_parts.save(tmp, rows, const)
    back = npz_parts.load(tmp)
    assert set(back) == set(full), (f.name, set(back) ^ set(full))
    for k in full:
        assert back[k].dtype == full[k].dtype and np.array_equal(back[k], full[k]), (f.name, k)
    f.unlink()
    for p in ps:
        p.rename(p.with_name(p.name.replace("_tmpsplit", "")))
    again = npz_parts.load(f)
    assert all(np.array_equal(again[k], full[k]) for k in full)
    print(f.name, "->", len(ps), "parts, max", max(p.stat().st_size for p in npz_parts.parts(f)) / 2**20, "MiB; verified")
