#!/usr/bin/env python3
"""RAM watchdog for GPU processes, by non-reclaimable memory: cgroup total_rss + total_shmem (+ unevictable).
File-backed pages (the mmapped safetensors and the page cache of the checkpoints read from network storage) are
reclaimable and are not counted; counting them aborted two launches (deviation D6). Replaces cfg4.MemWatch for
the HF process without editing the committed cfg4.py."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from loguru import logger


def nonreclaimable_bytes() -> float:
    keys_v1 = {"total_rss": 0.0, "total_shmem": 0.0, "total_unevictable": 0.0}
    keys_v2 = {"anon": 0.0, "shmem": 0.0, "unevictable": 0.0}
    for stat, keys in (("/sys/fs/cgroup/memory/memory.stat", keys_v1), ("/sys/fs/cgroup/memory.stat", keys_v2)):
        try:
            for line in Path(stat).read_text().splitlines():
                k, v = line.split()
                if k in keys:
                    keys[k] = float(v)
            return sum(keys.values())
        except (FileNotFoundError, ValueError):
            continue
    return 0.0


class MemWatchRSS:
    def __init__(self, limit_gb: float = 26.0, every_s: float = 5.0):
        self.limit = limit_gb * 1e9
        self.every = every_s
        self.peak = 0.0
        self._stop = threading.Event()

    def _run(self) -> None:
        while not self._stop.wait(self.every):
            u = nonreclaimable_bytes()
            self.peak = max(self.peak, u)
            if u > self.limit:
                logger.error(f"non-reclaimable container RAM {u / 1e9:.1f} GB > {self.limit / 1e9:.1f} GB: aborting")
                os._exit(3)

    def start(self) -> "MemWatchRSS":
        threading.Thread(target=self._run, daemon=True).start()
        return self
