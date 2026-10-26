#!/usr/bin/env python3
"""Row-wise split storage for the large state arrays (GitHub's 100 MB file limit).

A logical file `states/<name>.npz` is stored as `states/<name>.partNNN.npz` parts, each under MAX_BYTES. Row arrays
(first axis = prompt / prefill index) are split along axis 0; constant arrays are repeated in every part. `load`
returns {array name: array} for either form (a single legacy .npz or its parts), so readers never see the split.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

MAX_BYTES = 45 * 2 ** 20


def parts(path: Path) -> list[Path]:
    path = Path(path)
    return sorted(path.parent.glob(f"{path.stem}.part*.npz"))


def exists(path: Path) -> bool:
    path = Path(path)
    return path.exists() or bool(parts(path))


def save(path: Path, rows: dict[str, np.ndarray], const: dict[str, np.ndarray] | None = None,
         max_bytes: int = MAX_BYTES) -> list[Path]:
    """Write `rows` (equal first dimension) split along axis 0 into parts of at most `max_bytes` each."""
    path = Path(path)
    const = const or {}
    n = len(next(iter(rows.values())))
    assert all(len(a) == n for a in rows.values()), "row arrays must share their first dimension"
    per_row = sum(a[:1].nbytes for a in rows.values()) or 1
    fixed = sum(a.nbytes for a in const.values())
    per = max(1, int((max_bytes - fixed) // per_row))
    for p in parts(path):
        p.unlink()
    if path.exists():
        path.unlink()
    out = []
    for k, i in enumerate(range(0, n, per), start=1):
        p = path.parent / f"{path.stem}.part{k:03d}.npz"
        np.savez(p, **{name: a[i:i + per] for name, a in rows.items()}, **const,
                 _row_keys=np.array(sorted(rows)))
        out.append(p)
    return out


def load(path: Path) -> dict[str, np.ndarray]:
    path = Path(path)
    if path.exists():
        z = np.load(path)
        return {k: z[k] for k in z.files}
    ps = parts(path)
    if not ps:
        raise FileNotFoundError(f"{path} (and no {path.stem}.part*.npz)")
    out: dict[str, np.ndarray] = {}
    rows: dict[str, list[np.ndarray]] = {}
    for p in ps:
        z = np.load(p)
        rk = {str(x) for x in z["_row_keys"]}
        for k in z.files:
            if k == "_row_keys":
                continue
            if k in rk:
                rows.setdefault(k, []).append(z[k])
            elif k not in out:
                out[k] = z[k]
    for k, v in rows.items():
        out[k] = np.concatenate(v, 0)
    return out
