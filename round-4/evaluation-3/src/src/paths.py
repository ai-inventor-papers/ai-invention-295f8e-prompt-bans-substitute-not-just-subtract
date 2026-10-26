"""Artifact-id -> workspace-root mapping for the 11 declared dependencies (read-only inputs).

Roots come from AII_ITER1/2/3 or the unpublished paths.local.json on the run server, else from published sibling
folders under AII_DEPS_DIR (default: this workspace's parent). Every output cites
'<artifact_id>:<relative path>' and never an absolute path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

WS = Path(__file__).resolve().parent.parent


def _local_roots() -> dict[str, str]:
    """Machine-specific roots live in paths.local.json (not published); environment variables take precedence."""
    f = WS / "paths.local.json"
    return json.loads(f.read_text()) if f.exists() else {}


_DEFAULT_ROOTS = _local_roots()

# artifact id -> (root env var, workspace folder, short experiment name)
ARTIFACTS: dict[str, tuple[str, str, str]] = {
    "art_U5UKkFrOgSsE": ("AII_ITER1", "gen_art_experiment_4", "exp4"),
    "art_UoCVh2Qe5RZ0": ("AII_ITER1", "gen_art_experiment_6", "exp6"),
    "art_6zBfl3kDjeiP": ("AII_ITER2", "gen_art_experiment_7", "exp7"),
    "art_IVZc3TWCeE9f": ("AII_ITER2", "gen_art_experiment_9", "exp9"),
    "art_0ndRfWKBWclR": ("AII_ITER2", "gen_art_experiment_11", "exp11"),
    "art_1AYTO1Epb_7t": ("AII_ITER3", "gen_art_experiment_13", "exp13"),
    "art_WiY4wqHLb9Gy": ("AII_ITER3", "gen_art_experiment_14", "exp14"),
    "art_Q-qh-9HhPoWo": ("AII_ITER3", "gen_art_experiment_15", "exp15"),
    "art__5akZ9W9iZM4": ("AII_ITER3", "gen_art_experiment_16", "exp16"),
    "art_pVlCZ272hDV7": ("AII_ITER3", "gen_art_experiment_17", "exp17"),
    "art_ccAbfJVcv0LO": ("AII_ITER3", "gen_art_experiment_18", "exp18"),
}
BY_EXP = {v[2]: k for k, v in ARTIFACTS.items()}


def root(aid: str) -> Path:
    """Dependency workspace: AII_ITERn (or the unpublished paths.local.json) on the run server; otherwise the
    published sibling folder under AII_DEPS_DIR (default: this workspace's parent), named by artifact id or by the
    original workspace folder name."""
    env, folder, _ = ARTIFACTS[aid]
    base = os.environ.get(env) or _DEFAULT_ROOTS.get(env)
    if base:
        return Path(base) / folder
    deps = Path(os.environ.get("AII_DEPS_DIR") or WS.parent)
    for cand in (deps / aid, deps / folder, *sorted(deps.glob(f"*{aid}*"))):
        if cand.is_dir():
            return cand
    raise FileNotFoundError(f"dependency {aid} ({folder}) not found under {deps}; set AII_DEPS_DIR or {env}")


def p(exp_or_aid: str, rel: str) -> Path:
    """Absolute path of a dependency file, addressed by 'exp13' or by artifact id."""
    aid = BY_EXP.get(exp_or_aid, exp_or_aid)
    return root(aid) / rel


def cite(exp_or_aid: str, rel: str) -> str:
    aid = BY_EXP.get(exp_or_aid, exp_or_aid)
    return f"{aid}:{rel}"


def exp_name(aid: str) -> str:
    return ARTIFACTS[aid][2]
