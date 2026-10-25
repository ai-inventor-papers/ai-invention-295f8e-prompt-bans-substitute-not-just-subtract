#!/usr/bin/env python3
"""Wrappers around the vendored (unmodified) iteration-9 source files.

analysis_v9 / stats_v9 / common (art_8nXdw3_lDAll) import cleanly from vendor/art_8nXdw3_lDAll/.
stage_analysis.py (art_VVA3P0ocZNA2) imports the whole TP-G pipeline at module level, so the three functions the
plan names (_perms, mantel_exact, model_rdms) are compiled from the vendored file's own source text (via ast) into a
namespace with the globals they use; the file itself stays byte-identical.
"""

from __future__ import annotations

import ast
import itertools
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata, spearmanr

from io_util import A_GEO, A_REN, VENDOR, dep_path, read_json

_V1 = VENDOR / A_REN
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

import analysis_v9 as A  # noqa: E402  (vendored, unmodified)
import common as C  # noqa: E402
import stats_v9 as S  # noqa: E402


class _Geo:
    """Functions compiled from vendor/art_VVA3P0ocZNA2/stage_analysis.py, unmodified."""

    def __init__(self) -> None:
        src = (VENDOR / A_GEO / "stage_analysis.py").read_text()
        tree = ast.parse(src)
        want = {"_perms", "mantel_exact", "model_rdms", "partial_spearman"}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
        assert {n.name for n in nodes} == want, "vendored stage_analysis.py lacks a named function"
        mod = ast.Module(body=nodes, type_ignores=[])

        class _P:
            def __init__(self, base: str) -> None:
                self.base = base

            def __truediv__(self, rel: str) -> Path:
                return dep_path(A_GEO, f"{self.base}/{rel}")

        ns: dict[str, Any] = {"np": np, "itertools": itertools, "rankdata": rankdata, "spearmanr": spearmanr,
                              "Any": Any, "_PERMS": {}, "read_json": read_json,
                              "RESULTS": _P("results"), "DATA": _P("data")}
        exec(compile(mod, str(VENDOR / A_GEO / "stage_analysis.py"), "exec"), ns)
        self.ns = ns
        self.mantel_exact = ns["mantel_exact"]
        self.model_rdms = ns["model_rdms"]
        self.partial_spearman = ns["partial_spearman"]
        self._perms = ns["_perms"]


GEO = None


def geo() -> _Geo:
    global GEO
    if GEO is None:
        GEO = _Geo()
    return GEO
