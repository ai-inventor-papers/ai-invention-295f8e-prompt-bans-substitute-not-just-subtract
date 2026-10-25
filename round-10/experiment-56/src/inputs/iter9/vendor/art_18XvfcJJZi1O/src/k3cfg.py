#!/usr/bin/env python3
"""K3 constants and utilities: the circuit behind Qwen3-8B's algorithm choice (bf16, thinking off).

Conventions:
- Node = (kind 'head'|'mlp', layer, head (-1 for mlp), position class). Head activation = the head's 128-d slice of
  the o_proj INPUT (z); MLP activation = the output of block.mlp (down_proj output). 36 x (32 + 1) x 4 = 4,752 nodes.
- Position classes per prompt: COND = [p0, p1) (the condition sentence, padding and blank line), SPEC = [0, p0) +
  [p1, P) (chat head, task spec, chat tail incl. the empty think block), OPEN = [P, P + L_open - 1) (the teacher-
  forced canonical opening except its last token), DEC = {P + L_open - 1} (the position whose logits choose the
  decision token).
- Effects follow the plan's sign: clean = default-leaning run (higher metric m), corrupt = minority-leaning run;
  TE = m_clean - m_corrupt > 0; noising effect = m_clean - m_noised; denoising effect = m_denoised - m_corrupt;
  AtP noising estimate = -grad_m(clean) . (a_corrupt - a_clean) (same sign as the noising effect).
- CRN: u_stream(key) = PCG64(stable_seed(key)) uniforms, one per generated token, mapped by the iteration-6 float64
  inverse-CDF sampler (engine5) over the full vocabulary in token-id order.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
INPUTS = ROOT / "inputs"
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIG_DIR = ROOT / "figures"
LOG_DIR = ROOT / "logs"
PRED_DIR = ROOT / "predictions"
CACHE_DIR = ROOT / "cache"
AUDIT_DIR = ROOT / "audit"
for _d in (DATA_DIR, RESULTS_DIR, FIG_DIR, LOG_DIR, PRED_DIR, CACHE_DIR, AUDIT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

I6_SRC = INPUTS / "iter6_exp30" / "src"
E26 = INPUTS / "iter5_exp26"
E35 = INPUTS / "exp35"
E34 = INPUTS / "exp34"
E38 = INPUTS / "exp38"
I6_PROMPTS = INPUTS / "iter6_exp30" / "prompts" / "prompts6.jsonl"
NOUN_BANK = INPUTS / "dep_noun_bank.json"
COMMITS = ROOT / "commitments.log"

# ------------------------------------------------------------------------------------------------ model
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
N_LAYERS = 36
N_HEADS = 32
HEAD_DIM = 128
D_MODEL = 4096
IM_END = 151645
ENDOFTEXT = 151643
TEMPLATE_TAIL = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
PRECISION = "bf16"
CLASSES = ("COND", "SPEC", "OPEN", "DEC")
TEMPLATES = ("W1", "W2", "W3", "W4", "W5")
U_LEN = 1536

# ------------------------------------------------------------------------------------------------ design (commit #0)
SEED_HELDOUT = 8301
SEED_POOL = 8302
SEED_RAND5 = 8303
SEED_REL = 8304
SEED_CAL = 8305
N_TOP_EXACT = 60
N_CAL = 20
N_REL_PER_CLASS = 40
N_EDGE = 15
N_VAL = 10
N_RAND = 50
KS_FAITH = (5, 10, 15, 30, 60)
STEER_DOSE = 2.0
TE_MIN = 0.2
EDGE_FRAC = 0.05
ATP_SPEARMAN_MIN = 0.6
GEN_SLOTS = tuple(range(6))
GEN_THRESH_PLUS = 6
GEN_PASS_RATIO = 0.8
MAX_NEW_GEN = 1024
GEN_BATCH = 15
BUDGET_MSG = "AI Inventor per-run OpenRouter budget"
JUDGE_CAP_USD = 0.30
EXCLUDED_NOUNS = {"tree", "road", "roads", "city", "cities", "bridge", "network", "map", "heap", "graph", "path", "line",
                  "edge", "node", "link", "chain", "street", "key", "cost", "weight", "forest", "ship", "house", "set",
                  "union", "queue", "stack", "list", "number", "point", "table", "train", "plane", "circle", "ring",
                  "web", "net", "wire", "cable", "pipe", "rail", "track", "route", "way", "door", "gate", "wall"}

B3_TOK = {"a": " Kr", "b": " Prim"}          # C1 metric m = z(' Kr') - z(' Prim')
T10_TOK = {"a": " find", "b": " dfs", "b2": " bfs"}  # C2a m = z(' find') - z(' dfs')


# ------------------------------------------------------------------------------------------------ utils
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(LOG_DIR / f"{name}.log"), rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float) -> None:
    lim = int(gb * 1024 ** 3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def container_ram_gb() -> float | None:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts: Any) -> int:
    """Deterministic 63-bit seed from arbitrary parts (iteration-7 convention)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest(), 16) % (2 ** 63)


def u_stream(*key: Any, n: int = U_LEN) -> np.ndarray:
    return np.random.Generator(np.random.PCG64(stable_seed(*key))).random(n)


def model_path(model_id: str = MODEL_ID, revision: str | None = MODEL_REVISION) -> str:
    cache = os.environ.get("HF_HUB_CACHE")
    if cache:
        snaps = Path(cache) / ("models--" + model_id.replace("/", "--")) / "snapshots"
        if revision and (snaps / revision).exists():
            return str(snaps / revision)
    return model_id


def _json_default(o: Any) -> Any:
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def read_json(p: Path) -> Any:
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj: Any) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(p)


def read_jsonl(p: Path) -> list[dict[str, Any]]:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"skipping malformed line in {p.name}")
    return out


def append_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
        fh.flush()


def write_jsonl(p: Path, rows: Iterable[dict[str, Any]]) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=_json_default) + "\n")
    tmp.replace(p)


def log_deviation(dev_id: str, text: str, severity: str = "minor") -> None:
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    if any(d["id"] == dev_id for d in cur):
        return
    cur.append({"id": dev_id, "severity": severity, "text": text, "utc": utc_now()})
    write_json(p, cur)
    logger.warning(f"DEVIATION {dev_id}: {text}")


def stage_time(stage: str, seconds: float, **extra: Any) -> None:
    append_jsonl(RESULTS_DIR / "stage_timing.jsonl", [{"stage": stage, "seconds": round(seconds, 1), "utc": utc_now(),
                                                       **extra}])
