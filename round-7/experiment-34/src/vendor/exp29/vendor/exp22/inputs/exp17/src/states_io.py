#!/usr/bin/env python3
"""State arrays on disk: one '<stem>.npy' when small, otherwise row-wise parts '<stem>.part001.npy', '.part002.npy', ...
each under MAX_PART_BYTES (GitHub's 100 MB file limit). load() returns the full array either way."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

MAX_PART_BYTES = 90 * 1024 ** 2


def part_paths(stem: Path) -> list[Path]:
    stem = Path(stem)
    return sorted(stem.parent.glob(stem.name + ".part[0-9][0-9][0-9].npy"))


def exists(stem: Path) -> bool:
    stem = Path(stem)
    return stem.with_name(stem.name + ".npy").exists() or bool(part_paths(stem))


def load(stem: Path) -> np.ndarray:
    """Memory-mapped single file, or the row-wise concatenation of its parts."""
    stem = Path(stem)
    single = stem.with_name(stem.name + ".npy")
    if single.exists():
        return np.load(single, mmap_mode="r")
    parts = part_paths(stem)
    if not parts:
        raise FileNotFoundError(f"no states for {stem.name}")
    return np.concatenate([np.load(p) for p in parts], axis=0)


def save(stem: Path, arr: np.ndarray, max_bytes: int = MAX_PART_BYTES) -> list[Path]:
    """Write arr as one file if small enough, else as row-wise parts; removes any previous file or parts."""
    stem = Path(stem)
    single = stem.with_name(stem.name + ".npy")
    for p in part_paths(stem) + ([single] if single.exists() else []):
        p.unlink()
    if arr.nbytes <= max_bytes or arr.shape[0] <= 1:
        np.save(single, arr)
        return [single]
    n_parts = math.ceil(arr.nbytes / max_bytes)
    rows = math.ceil(arr.shape[0] / n_parts)
    out = []
    for i, a in enumerate(range(0, arr.shape[0], rows), start=1):
        p = stem.with_name(f"{stem.name}.part{i:03d}.npy")
        np.save(p, np.ascontiguousarray(arr[a:a + rows]))
        out.append(p)
    return out
