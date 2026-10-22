#!/usr/bin/env python3
"""S6 label worker (CPU, concurrent with sampling): exp17 label_worker unchanged (exp8 suite for T1/T2, exp11 bench
label_one for the 13 bench tasks incl. R2; runtime tracer primary, AST second, blind judge only on disagreement),
with the iteration-4 default map (R2 -> dfs_parent) and this artifact's judge caps (paths USD 0.30, bench USD 0.20,
cumulative; exp17's judge caches are reused so an identical program is never re-judged). Unjudged disagreements are
'disputed' (excluded from shares, counted). Rows go to data/labels.jsonl keyed task|template|arm|sample_id.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import cfg4  # noqa: E402,F401  (sets sys.path to src_base)
import label_worker as LW  # noqa: E402
from cfg4 import DATA_DIR, DEFAULT4, E17, LABELS, RAW, append_jsonl, read_jsonl, setup_logging  # noqa: E402

LW.JUDGE_CAP_USD = 0.40   # path judge gets 0.75 x = 0.30 (label_path_rows); bench cap set below
LW.N_WORKERS = 5


def _init_caches() -> None:
    for f in ("judge_cache.jsonl", "judge_cache_paths.jsonl"):
        dst = DATA_DIR / f
        if not dst.exists() and (E17 / "data" / f).exists():
            shutil.copy2(E17 / "data" / f, dst)


_orig_bench = LW.label_bench_rows


def _bench(rows):
    import bench.common.judge as BJ
    out = _orig_bench(rows)
    BJ.PERSONAL_CAP = 0.20
    return out


def label_rows(rows):
    import bench.common.judge as BJ
    BJ.PERSONAL_CAP = 0.20
    path = [r for r in rows if r["task"] in LW.EXP8_TASK]
    bench = [r for r in rows if r["task"] not in LW.EXP8_TASK]
    out = []
    if path:
        out += LW.label_path_rows(path)
    if bench:
        out += _bench(bench)
    for o in out:
        o["is_default"] = o["label"] == DEFAULT4[o["task"]]
    return out


def run_worker(follow: bool = True, chunk: int = 60, stop_file: Path | None = None) -> None:
    _init_caches()
    t0 = time.time()
    n_total = 0
    while True:
        done = {r["key"] for r in read_jsonl(LABELS)}
        raw = [r for r in read_jsonl(RAW) if LW.row_key(r) not in done]
        if raw:
            # label the confirmation-critical population rows first, then everything else in file order
            raw.sort(key=lambda r: (0 if r["arm"].startswith(("POP", "TWIN", "SCR")) else 1))
            for i in range(0, len(raw), chunk):
                part = raw[i:i + chunk]
                tb = time.time()
                try:
                    out = label_rows(part)
                except Exception as e:  # noqa: BLE001 - log and retry on the next pass
                    logger.exception(f"labelling chunk failed: {e}")
                    time.sleep(5)
                    break
                append_jsonl(LABELS, out)
                n_total += len(out)
                logger.info(f"labelled {len(out)} ({part[0]['task']}/{part[0]['arm']}...) in {time.time() - tb:.1f}s;"
                            f" total {n_total}; backlog {len(raw) - i - len(part)}")
        else:
            if not follow or (stop_file is not None and stop_file.exists()):
                break
            time.sleep(10)
    logger.info(f"label worker finished: {n_total} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    setup_logging("label4")
    follow = "--once" not in sys.argv
    run_worker(follow=follow, stop_file=DATA_DIR / "STOP_LABELLER")
