#!/usr/bin/env python3
"""Second opinions (plan 1.2 / 1.5): gated LLM judges (deepseek/deepseek-chat-v3.1, moonshotai/kimi-k2; tie-break
mistralai/mistral-medium-3.1) classify the expansion discipline of the RLX / RND / CRD factorial programs in the frames;
each judge must score >= 9/10 on 10 planted controls first. NOVELTY AUDIT: valid programs measured OTHER go to the
same judges with the 3 nearest known programs (AST 4-gram Jaccard) from the dataset's known-solution pool + the
catalogue references -> NOVEL / KNOWN / VARIANT / DEGENERATE. Writes results/judges.json, results/novelty_audit.json."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aiohttp  # noqa: E402
from loguru import logger  # noqa: E402

from accept import jaccard, shingles  # noqa: E402
from common import BUDGET_MSG, add_cost, append_jsonl, read_jsonl, total_cost, trunc, utc_now  # noqa: E402
from tpg2 import DATA, DS_FILE, LOGS, RESULTS, ROOT, write_json  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(LOGS / "judges.log"), rotation="30 MB", level="DEBUG")
JUDGES = ["deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2"]
THIRD = "mistralai/mistral-medium-3.1"
CAP = 0.80
DISC_DEF = """Classify the EXPANSION DISCIPLINE of this grid path-search program (4-connected grid, solve(grid, start, goal)).
Answer with exactly one label:
LEV = cells expanded in nondecreasing distance from start (FIFO queue, heap keyed by steps, ring-by-ring sets, level-by-level array scans)
DFS = most recently discovered cell expanded first (LIFO stack, recursion, deque used at one end, heap keyed by a decreasing counter)
HEU = cell with the smallest goal-distance key (Manhattan h, or g + h) expanded first
RLX = relaxation: repeated full sweeps over the grid until nothing changes, or a worklist that re-inserts a cell whenever its distance label improves (label-correcting)
RND = random order (random priorities, random.choice from the frontier)
CRD = goal-independent coordinate order (heap or sorted list keyed only by the cell's (row, col) or similar)
OTHER = none of these
Reply with the label only."""
NOV_DEF = """You audit whether a grid path-search program is a NEW algorithm. You see the program and the 3 most similar
known programs. Reply with one word: NOVEL (a genuinely new search procedure), KNOWN (a known algorithm, say which in
2-5 words after a colon), VARIANT (a minor variant of a known algorithm, name it after a colon) or DEGENERATE
(a trivial or broken-but-passing procedure). Format: LABEL: name"""


async def call(session: aiohttp.ClientSession, sem: asyncio.Semaphore, stop: dict, model: str, prompt: str,
               tag: str) -> str | None:
    async with sem:
        if stop["flag"] or total_cost() >= CAP:
            stop["flag"] = True
            return None
        url = os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/chat/completions"
        hdr = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0,
                "max_tokens": 400, "usage": {"include": True}}
        for attempt in range(3):
            if stop["flag"]:
                return None
            try:
                async with session.post(url, json=body, headers=hdr, timeout=aiohttp.ClientTimeout(total=120)) as r:
                    txt = await r.text()
                    if r.status == 403 and BUDGET_MSG in txt:
                        stop["flag"] = True
                        add_cost("judges", 0.0, refused=True)
                        return None
                    if r.status != 200:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    d = json.loads(txt)
                    usage = d.get("usage") or {}
                    add_cost(f"judge:{model}", float(usage.get("cost") or 0.0))
                    ans = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                    append_jsonl(LOGS / "judge_calls.jsonl", {"utc": utc_now(), "model": model, "tag": tag,
                                                              "answer": ans[:200], "cost": usage.get("cost")})
                    return ans.strip()
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError):
                await asyncio.sleep(2 * (attempt + 1))
        return None


def parse_disc(a: str | None) -> str | None:
    if not a:
        return None
    m = re.search(r"\b(LEV|DFS|HEU|RLX|RND|CRD|OTHER)\b", a.upper())
    return m.group(1) if m else None


async def run(jobs: list[tuple[str, str, str]]) -> dict[str, str | None]:
    sem = asyncio.Semaphore(8)
    stop = {"flag": False}
    async with aiohttp.ClientSession() as s:
        res = await asyncio.gather(*[call(s, sem, stop, m, p, t) for t, m, p in jobs])
    return {t + "|" + m: r for (t, m, _), r in zip(jobs, res)}


def known_pool() -> list[tuple[str, str]]:
    pool = []
    for f in sorted((ROOT / "vendor/exp9/tasks/t1_grid/references").glob("*.py")):
        pool.append((f"catalogue:{f.stem}", f.read_text()))
    try:
        d = json.loads(DS_FILE.read_text())
        for ds in d["datasets"]:
            if ds["dataset"] not in ("thealgorithms_python", "xlcost_python", "kodcode_algorithmic"):
                continue
            for ex in ds["examples"]:
                code = (ex.get("input") if ds["dataset"] == "thealgorithms_python" else ex.get("output")) or ""
                hint = str(ex.get("metadata_named_algorithms") or "")
                if re.search(r"grid|maze|bfs|dfs|a\*|astar|dijkstra|path", hint + code[:400], re.IGNORECASE) and \
                        "def " in code and len(code) < 6000:
                    pool.append((f"{ds['dataset']}:{ex.get('metadata_id', len(pool))}", code))
    except (OSError, json.JSONDecodeError, KeyError) as e:
        logger.warning(f"dataset pool not loaded: {e}")
    return pool


def main() -> None:
    fr = json.loads((DATA / "frames.json").read_text())
    items = {it["id"]: it for it in json.loads((DATA / "state_items.json").read_text())["items"]}
    planted = ROOT / "references" / "planted"
    controls = [("RLX_ARR", "RLX"), ("RLX_STK", "RLX"), ("RND_HEAP", "RND"), ("RND_SET", "RND"), ("CRD_HEAP", "CRD"),
                ("CRD_SLIST", "CRD"), ("LEV_DEQ", "LEV"), ("DFS_STK", "DFS"), ("HEU_HEAP", "HEU"), ("LEV_ARR", "LEV")]
    jobs = [(f"control:{c}", m, DISC_DEF + "\n\n```python\n" + (planted / f"{c}.py").read_text() + "\n```")
            for c, _ in controls for m in JUDGES + [THIRD]]
    res = asyncio.run(run(jobs))
    gate = {m: sum(parse_disc(res.get(f"control:{c}|{m}")) == want for c, want in controls) for m in JUDGES + [THIRD]}
    passed = [m for m in JUDGES + [THIRD] if gate[m] >= 9]
    logger.info(f"judge gate: {gate}; passed {passed}")
    use = [m for m in JUDGES if m in passed][:2]
    if len(use) < 2 and THIRD in passed:
        use.append(THIRD)
    if not use:
        write_json(RESULTS / "judges.json", {"gate": gate, "gate_threshold": 9, "judges_used": [],
                                              "note": "no judge reached 9/10 on the planted controls (plan F4: judges optional, the executor's hand reads decide)",
                                              "spend_usd_total": total_cost(), "utc": utc_now()})
        logger.info("no judge passed the gate; skipping judge second opinions and the judged novelty audit")
    targets = [f for f in fr["factorial"] if f["disc"] in ("RLX", "RND", "CRD")] if use else []
    jobs = [(f["id"], m, DISC_DEF + "\n\n```python\n" + items[f["id"]]["scrubbed"] + "\n```") for f in targets for m in use]
    res2 = asyncio.run(run(jobs))
    hand = {}
    for h in read_jsonl(DATA / "hand_reads.jsonl"):
        hand[h["uid"]] = h
    rows = []
    for f in targets:
        votes = {m: parse_disc(res2.get(f"{f['id']}|{m}")) for m in use}
        hr = hand.get(f["id"], {}).get("read_disc", f["disc"])
        rows.append({"id": f["id"], "cell": f["cell"], "hand_read": hr, "judges": votes,
                     "agree_all": all(v == hr for v in votes.values()),
                     "majority": Counter(votes.values()).most_common(1)[0][0] if votes else None})
    agree = sum(r["agree_all"] for r in rows)
    if use:
        write_json(RESULTS / "judges.json", {"gate": gate, "gate_threshold": 9, "judges_used": use, "n_programs": len(rows),
                                          "n_all_judges_agree_with_hand_read": agree,
                                              "disagreements": [r for r in rows if not r["agree_all"]], "rows": rows,
                                              "spend_usd_total": total_cost(), "utc": utc_now()})
    logger.info(f"judges: {agree}/{len(rows)} programs where every judge agrees with the hand read")
    # novelty audit
    fact = read_jsonl(DATA / "factorial.jsonl")
    other = [r for r in fact if r.get("valid") and r.get("disc") == "OTHER"]
    pool = known_pool()
    psh = [(n, shingles(c), c) for n, c in pool]
    jobs = []
    near_map = {}
    for r in other:
        sh = shingles(r["scrubbed"])
        near = sorted(psh, key=lambda x: -jaccard(sh, x[1]))[:3]
        near_map[r["uid"]] = [(n, round(jaccard(sh, s), 3)) for n, s, _ in near]
        ctx = "\n\n".join(f"Known program {i + 1} ({n}):\n```python\n{trunc(c, 2500)}\n```" for i, (n, _, c) in enumerate(near))
        prompt = NOV_DEF + f"\n\nProgram under audit:\n```python\n{r['scrubbed']}\n```\n\n" + ctx
        for m in use:
            jobs.append((r["uid"], m, prompt))
    res3 = asyncio.run(run(jobs)) if jobs else {}
    nov = []
    for r in other:
        v = {m: (res3.get(f"{r['uid']}|{m}") or "")[:120] for m in use}
        nov.append({"uid": r["uid"], "requested_cell": r["requested_cell"], "fine": r.get("fine"),
                    "container": r.get("cont"), "nearest_known": near_map[r["uid"]], "judges": v})
    write_json(RESULTS / "novelty_audit.json", {"n_other_valid": len(other), "pool_size": len(pool), "rows": nov,
                                                "judges_used": use, "utc": utc_now()})
    logger.info(f"novelty audit: {len(other)} OTHER programs; pool {len(pool)}")


if __name__ == "__main__":
    main()
