#!/usr/bin/env python3
"""Row access for the rename artifact (art_8nXdw3_lDAll): the labelled cell rows that results/n3*.json were
computed from (data/labelled_v9_<cell>.jsonl, read in place), the retraced rows (results/retrace.jsonl) and the
76 manual reads (data/manual_reads_v9.jsonl)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from io_util import A_REN, dep_path, read_jsonl

MODEL_PREFIX = {"q32": "A", "q14": "E"}
MODEL_NAME = {"q32": "Qwen3-32B", "q14": "Qwen3-14B"}


@lru_cache(maxsize=None)
def cell(cid: str) -> tuple[dict[str, Any], ...]:
    return tuple(read_jsonl(dep_path(A_REN, f"data/labelled_v9_{cid}.jsonl")))


def cells_for(mk: str) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    pre = MODEL_PREFIX[mk]
    return ({k: list(cell(f"{pre}_k{k}")) for k in range(1, 6)}, list(cell(f"{pre}_k5_ho")))


@lru_cache(maxsize=None)
def retrace() -> tuple[dict[str, Any], ...]:
    return tuple(read_jsonl(dep_path(A_REN, "results/retrace.jsonl")))


def retrace_by_config() -> dict[str, list[dict[str, Any]]]:
    order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
    ret = list(retrace())
    return {c: [r for r in ret if r["config"] == c] for c in order if any(r["config"] == c for r in ret)}


@lru_cache(maxsize=None)
def manual_reads() -> tuple[dict[str, Any], ...]:
    return tuple(read_jsonl(dep_path(A_REN, "data/manual_reads_v9.jsonl")))


@lru_cache(maxsize=None)
def samples_v9() -> tuple[dict[str, Any], ...]:
    return tuple(read_jsonl(dep_path(A_REN, "data/samples_v9.jsonl")))
