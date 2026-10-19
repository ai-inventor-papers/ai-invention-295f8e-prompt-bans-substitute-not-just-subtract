#!/usr/bin/env python3
"""LLM judge (OpenRouter) for labeller disagreements, blind to condition.

Input: task spec, catalogue with one-line definitions, the rule 'recursion vs iteration is not a mode;
answer other if none fits', and the code. Output JSON {label, confidence, rationale}. Results are cached
per (model, code sha256). A running total of usage.cost is kept; bulk labelling hard-stops at the cap,
and the first 403 'AI Inventor per-run OpenRouter budget' refusal stops every queued call.

  python labeller/judge.py --bulk          # adjudicate every sample whose runtime and AST labels disagree
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CACHE_DIR, CATALOGUE, DEFINITIONS, LABEL_CACHE, LOGS_DIR, SPEC, append_jsonl, setup_logger, sha256_text  # noqa: E402
from loguru import logger  # noqa: E402

BULK_MODEL = "google/gemini-2.5-flash-lite"
PRICES = {  # USD per token (prompt, completion), fallback when usage.cost is absent
    "google/gemini-2.5-flash-lite": (1e-7, 4e-7), "openai/gpt-4.1-mini": (4e-7, 1.6e-6),
    "anthropic/claude-haiku-4.5": (1e-6, 5e-6), "google/gemini-2.5-flash": (3e-7, 2.5e-6),
}
JUDGE_DIR = CACHE_DIR / "judge"
COST_LOG = LOGS_DIR / "openrouter_cost.jsonl"


class BudgetStop(Exception):
    pass


class Judge:
    def __init__(self, cap_usd: float):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"],
                                  timeout=60.0, max_retries=2)
        self.cap = cap_usd
        self.spent = 0.0
        self.stopped = False
        self.n_calls = 0

    @staticmethod
    def prompt(task: str, code: str) -> str:
        cat = "\n".join(f"- {m}: {DEFINITIONS[task][m]}" for m in CATALOGUE[task])
        return (f"You classify which search/shortest-path algorithm a Python program implements.\n\n"
                f"TASK GIVEN TO THE PROGRAMMER:\n{SPEC[task]}\n\nCATALOGUE OF MODES:\n{cat}\n- other: none of the above\n\n"
                "RULES: Recursion versus iteration is not a mode (a recursive DFS is dfs). Judge the algorithm the code "
                "actually executes, not its comments or names. Answer 'other' if no catalogue mode fits.\n\n"
                f"CODE:\n```python\n{code[:6000]}\n```\n\n"
                'Reply with JSON only: {"label": "<one of: ' + ", ".join(CATALOGUE[task] + ["other"]) +
                '>", "confidence": <0..1>, "rationale": "<one sentence>"}')

    async def call(self, model: str, task: str, code: str, sem: asyncio.Semaphore) -> dict | None:
        cf = JUDGE_DIR / model.replace("/", "__") / f"{sha256_text(task + code)}.json"
        if cf.exists():
            return json.loads(cf.read_text())
        async with sem:
            if self.stopped or self.spent >= self.cap:
                self.stopped = True
                return None
            try:
                resp = await self.client.chat.completions.create(
                    model=model, temperature=0, max_tokens=300,
                    messages=[{"role": "user", "content": self.prompt(task, code)}],
                    extra_body={"usage": {"include": True}})
            except Exception as e:  # noqa: BLE001 - classify budget refusals vs transient failures
                msg = str(e)
                if "AI Inventor per-run OpenRouter budget" in msg or getattr(e, "status_code", None) == 403:
                    logger.error(f"budget refusal from OpenRouter; stopping all judge calls: {msg[:200]}")
                    self.stopped = True
                    return None
                logger.warning(f"judge call failed ({model}): {msg[:200]}")
                return None
            if self.stopped:
                return None
            self.n_calls += 1
            u = resp.usage
            cost = None
            if u is not None:
                extra = getattr(u, "model_extra", None) or {}
                cost = extra.get("cost", getattr(u, "cost", None))
                if cost is None:
                    pp, pc = PRICES.get(model, (1e-6, 5e-6))
                    cost = (u.prompt_tokens or 0) * pp + (u.completion_tokens or 0) * pc
            cost = float(cost or 0.0)
            self.spent += cost
            text = resp.choices[0].message.content or ""
            out = parse(task, text)
            out.update({"model": model, "cost": cost, "raw": text[:600]})
            append_jsonl(COST_LOG, [{"model": model, "cost": cost, "purpose": "judge"}])
            logger.debug(f"judge {model} -> {out['label']} ({out.get('confidence')}): {out.get('rationale', '')[:120]}")
            cf.parent.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps(out))
            return out


def parse(task: str, text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    lab, conf, rat = "other", None, ""
    if m:
        try:
            d = json.loads(m.group(0))
            lab = str(d.get("label", "other")).strip().lower()
            conf = d.get("confidence")
            rat = str(d.get("rationale", ""))
        except json.JSONDecodeError:
            pass
    if lab not in CATALOGUE[task] + ["other"]:
        lab = "other"
    return {"label": lab, "confidence": conf, "rationale": rat}


def total_spent() -> float:
    if not COST_LOG.exists():
        return 0.0
    return sum(json.loads(x).get("cost", 0.0) for x in COST_LOG.read_text().splitlines() if x.strip())


async def bulk(cap: float) -> dict:
    judge = Judge(cap_usd=cap)
    sem = asyncio.Semaphore(16)
    items = []
    for task in ("T1", "T2"):
        for f in sorted((LABEL_CACHE / task).glob("*.json")):
            rec = json.loads(f.read_text())
            if rec.get("needs_judge") and rec.get("label_judge") is None and rec.get("code"):
                items.append((task, f, rec))
    logger.info(f"bulk judge: {len(items)} samples need adjudication")
    res = await asyncio.gather(*[judge.call(BULK_MODEL, t, r["code"], sem) for t, _, r in items])
    n_ok = 0
    for (task, f, rec), out in zip(items, res):
        if out is None:
            rec["label"] = rec["label_ast"] if rec["label_ast"] in CATALOGUE[task] + ["other"] else "other"
            rec["labeller_source"] = "ast_judge_unavailable"
            rec["judge_unavailable"] = True
        else:
            rec["label_judge"] = out["label"]
            rec["judge_rationale"] = out.get("rationale")
            rec["label"] = out["label"]
            rec["labeller_source"] = "judge"
            n_ok += 1
        rec["needs_judge"] = False
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec))
        tmp.replace(f)
    summary = {"n_items": len(items), "n_judged": n_ok, "spent_usd": judge.spent, "stopped": judge.stopped,
               "calls": judge.n_calls}
    logger.info(f"bulk judge summary: {summary}")
    return summary


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bulk", action="store_true")
    ap.add_argument("--cap", type=float, default=0.80)
    args = ap.parse_args()
    setup_logger("judge")
    if args.bulk:
        s = asyncio.run(bulk(args.cap))
        (LOGS_DIR / "judge_bulk_last.json").write_text(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
