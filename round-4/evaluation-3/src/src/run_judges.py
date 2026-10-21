"""Background stage for (0d) Steps A-B: build the pool, compute deterministic features, run the judges.

Writes audit/pool.parquet, audit/pool_events.json and audit/judge_results.json. Re-running reuses
audit/judge_cache.jsonl (keyed by model + sha256 of the prompt), so no call is paid twice.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.other_audit import AUDIT, run_judges, step_a, build_pool  # noqa: E402
from src.paths import WS  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "judges.log", rotation="30 MB", level="DEBUG")


def key_remaining() -> float | None:
    try:
        r = requests.get(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key",
                         headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=30)
        return float(r.json()["data"]["limit_remaining"])
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.error(f"/key check failed: {e}")
        return None


@logger.catch(reraise=True)
def main() -> None:
    rows = pd.read_parquet(WS / "data" / "rows.parquet")
    pool, events = build_pool(rows)
    pool = step_a(pool)
    pool.to_parquet(AUDIT / "pool.parquet", index=False)
    (AUDIT / "pool_events.json").write_text(json.dumps(events, indent=1, default=str))
    logger.info(f"pool: {len(pool)} event-program rows, {pool.code_sha256.nunique()} unique programs")
    rem = key_remaining()
    logger.info(f"OpenRouter shared pot remaining: {rem}")
    if rem is not None and rem < 3.0:
        logger.error("less than USD 3 left in the shared pot: judges skipped, manual pass only")
        (AUDIT / "judge_results.json").write_text(json.dumps({"skipped": "pot_below_3usd", "pot_remaining": rem}))
        return
    if "--no-judges" in sys.argv:
        return
    res = asyncio.run(run_judges(pool))
    res["pot_remaining_before"] = rem
    (AUDIT / "judge_results.json").write_text(json.dumps(res, indent=1, default=str))
    logger.info(f"judges done: items={res['n_items']} tiebreak={res['n_tiebreak']} spent=${res['spent_usd']:.3f} "
                f"stopped={res['stopped']} {res['stop_reason']}")


if __name__ == "__main__":
    main()
