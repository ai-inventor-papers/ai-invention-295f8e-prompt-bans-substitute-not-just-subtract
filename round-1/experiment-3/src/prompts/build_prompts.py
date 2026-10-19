"""S4: condition segments (10 paraphrases each), chat-templated prompt token ids, prompts.json + sha256."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BASELINE = [
    "Please solve the following programming task.",
    "Solve the programming problem below.",
    "Here is a programming task for you to complete.",
    "Complete the following coding task.",
    "Please write code for the task described below.",
    "Your job is to solve this programming exercise.",
    "Implement a solution to the following problem.",
    "Below is a coding problem. Please solve it.",
    "Write a solution for the programming task that follows.",
    "Please complete this programming assignment.",
]
BAN_BFS = [
    "Do not use breadth-first search (BFS).",
    "Your solution must not use breadth-first search (BFS).",
    "Solve the task below without using breadth-first search (BFS).",
    "Breadth-first search (BFS) is not allowed in your solution.",
    "Please avoid breadth-first search (BFS) in your code.",
    "Constraint: do not implement breadth-first search (BFS).",
    "You may use any approach except breadth-first search (BFS).",
    "Note that breadth-first search (BFS) is forbidden for this task.",
    "Write a solution that does not rely on breadth-first search (BFS).",
    "Important: your solution must avoid breadth-first search (BFS).",
]
BAN_DIJKSTRA = [
    "Do not use Dijkstra's algorithm.",
    "Your solution must not use Dijkstra's algorithm.",
    "Solve the task below without using Dijkstra's algorithm.",
    "Dijkstra's algorithm is not allowed in your solution.",
    "Please avoid Dijkstra's algorithm in your code.",
    "Constraint: do not implement Dijkstra's algorithm.",
    "You may use any approach except Dijkstra's algorithm.",
    "Note that Dijkstra's algorithm is forbidden for this task.",
    "Write a solution that does not rely on Dijkstra's algorithm.",
    "Important: your solution must avoid Dijkstra's algorithm.",
]


def segments(task: str, condition: str) -> list[str]:
    if condition == "baseline":
        return BASELINE
    return BAN_BFS if task == "T1" else BAN_DIJKSTRA


def build(tokenizer) -> dict:
    import sys
    sys.path.insert(0, str(ROOT))
    from tasks import t1_grid, t2_wsp
    specs = {"T1": t1_grid.SPEC, "T2": t2_wsp.SPEC}
    out: dict = {}
    for task in ("T1", "T2"):
        for cond in ("baseline", "ban"):
            for pid, seg in enumerate(segments(task, cond)):
                text = seg + "\n\n" + specs[task]
                ids = tokenizer.apply_chat_template([{"role": "user", "content": text}], tokenize=True,
                                                    add_generation_prompt=True, enable_thinking=False)
                if hasattr(ids, "input_ids"):
                    ids = ids["input_ids"]
                ids = [int(x) for x in ids]
                rendered = tokenizer.decode(ids)
                out[f"{task}|{cond}|{pid}"] = {"task": task, "condition": cond, "paraphrase_id": pid,
                                                "segment": seg, "user_text": text, "prompt_token_ids": ids,
                                                "prompt_len": len(ids), "rendered": rendered}
    return out


def main() -> None:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    prompts = build(tok)
    p = ROOT / "prompts" / "prompts.json"
    p.write_text(json.dumps(prompts, indent=1))
    print(len(prompts), "prompts; example rendered:\n", list(prompts.values())[0]["rendered"][-400:])


if __name__ == "__main__":
    main()
