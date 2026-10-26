import sys, json, asyncio, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "labeller")); sys.path.insert(0, str(ROOT / "tasks"))
from common import read_jsonl, setup_logger
from label import judge_prompt, JUDGE_MODEL
from openai import OpenAI
rows = [r for r in read_jsonl(ROOT / "data" / "raw_phaseA.jsonl")[:24] if r["condition"] == "forced:dial"]
c = OpenAI(base_url=os.environ["OPENROUTER_BASE_URL"], api_key=os.environ["OPENROUTER_API_KEY"])
for r in rows[1:3]:
    resp = c.chat.completions.create(model=JUDGE_MODEL, messages=[{"role": "user", "content": judge_prompt("t2", r["code"])}], temperature=0, max_tokens=2000, extra_body={"reasoning": {"effort": "low"}})
    print(repr(resp.choices[0].message.content)[:800], resp.choices[0].finish_reason, resp.usage)
