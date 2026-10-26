#!/usr/bin/env python3
"""EXPLORATORY (post hoc): does forcing ONE early token decide the algorithm under the unchanged neutral twin prompt?

For each task with a token-level decision point, the canonical default opening o_t[0:f] is teacher-forced, the fork
token x is appended, and the model completes the program with the slot's own CRN uniforms from generated position
f + 1 on (u_stream(task, w, k)[f + 1:]); N = 30 slots (W1-W5 x k 0-5), no hook. The frozen labeller labels prefix +
continuation. Arms:
  T10  f = 10 (o_t = '```python\\ndef solve(n, edges):\\n   '): ' parent', ' #', ' from', ' def' (free after it);
       f = 11 after ' def': ' find', ' dfs'
  T03  f = first body token of the canonical twin opening: the twin's own token and the first divergent tokens of
       the quickselect / size_k_heap base paths (LCP with o_t)
  T2   the same construction at the first body token (the screen found no early fork; a negative control)
Rows -> data/samples_raw_force.jsonl (labelled by src/label7.py --once).
"""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import DATA, FENCE, MAX_NEW, TEMPLATES, append_jsonl, read_json, read_jsonl, setup_logging, utc_now  # noqa: E402
import engine7 as E  # noqa: E402
import fork7 as F  # noqa: E402
import prompts7 as PR  # noqa: E402

RAW = DATA / "samples_raw_force.jsonl"


def first_body_pos(tok, opening: list[int]) -> int:
    """Index of the first token after 'def solve(...):\\n' + indentation in the canonical opening."""
    text = ""
    for i, t in enumerate(opening):
        text += tok.decode([t])
        if "):\n" in text and i + 1 < len(opening):
            return i + 1
    return 8


def arms_for(task: str, tok, forks: dict) -> tuple[list[int], list[tuple[str, list[int]]]]:
    d = forks["tasks"][task]
    twins = [p for p in F.labelled_programs(task) if p["arm"] == "TWIN" and p["label"] == common.DEFAULTS[task]]
    if task == "T10":
        o = d["opening_ids"]
        f1 = d["forks"][0]
        def_tok = o[f1]
        enc = lambda s: tok(s, add_special_tokens=False)["input_ids"]  # noqa: E731
        arms = [(f"F10_{tok.decode([x]).strip() or 'sp'}", o[:f1] + [x]) for x in (enc(" parent")[0], enc(" #")[0],
                                                                                  enc(" from")[0], def_tok)]
        arms += [(f"F11_{w}", o[:f1] + [def_tok] + enc(" " + w)[:1]) for w in ("find", "dfs")]
        return o, arms
    o = []
    for Lo in range(40, 4, -1):      # longest modal twin opening available (T03 programs are ~20 tokens)
        o, share = F.canonical_opening([p["ids"] for p in twins], Lo)
        if o and share >= 0.3:
            break
    f = first_body_pos(tok, o)
    cands = Counter()
    for bp in d.get("base_paths", []):
        if bp["class"] == common.DEFAULTS[task]:
            continue
        rows = [p for p in F.labelled_programs(task) if p["src"] == bp["src"] and p["arm"] == bp["arm"]
                and p["template"] == bp["template"] and int(p["sample_id"]) == int(bp["sample_id"])]
        if rows and rows[0]["ids"][:f] == o[:f]:
            cands[(bp["class"], rows[0]["ids"][f])] += 1
    arms = [(f"FB_default_{tok.decode([o[f]]).strip() or 'sp'}", o[:f + 1])]
    seen = {o[f]}
    for (c, x), _ in cands.most_common():
        if x not in seen:
            arms.append((f"FB_{c}_{tok.decode([x]).strip() or 'sp'}", o[:f] + [x]))
            seen.add(x)
    if len(arms) == 1:      # no base path shares the opening up to f: force a comment line as the alternative
        arms.append((f"FB_comment_#", o[:f] + tok(" #", add_special_tokens=False)["input_ids"][:1]))
    return o, arms[:4]


def main() -> None:
    from engine4 import u_stream
    setup_logging("force_token")
    forks = read_json(common.forks_path())
    tok, model = E.load()
    done = {f"{r['task']}|{r['arm']}|{r['template']}|{r['sample_id']}" for r in read_jsonl(RAW)}
    for task in ("T10", "T03", "T2"):
        o, arms = arms_for(task, tok, forks)
        logger.info(f"{task}: arms {[(a, tok.decode(p[-3:])) for a, p in arms]}")
        mx = MAX_NEW[task]
        for w in TEMPLATES:
            pr = PR.twin(task, w)
            for name, prefix in arms:
                ks = [k for k in range(6) if f"{task}|{name}|{w}|{k}" not in done]
                if not ks:
                    continue
                t0 = time.time()
                pre = E.prefill(model, pr["ids"] + prefix)
                L = len(prefix)
                groups = [{"pre": pre, "us": [u_stream(task, w, k, n=mx + L)[L:] for k in ks]}]
                res = E.sample(model, tok, groups, FENCE[task], mx - L)
                rows = []
                for k, r in zip(ks, res):
                    ids = prefix + r["token_ids"]
                    rows.append({"task": task, "arm": name, "template": w, "sample_id": k, "slot": f"{task}|{w}|{k}",
                                 "seed": common.stable_seed(task, w, k), "family": "FORCETOK",
                                 "forced_prefix_len": L, "forced_token": tok.decode(prefix[-1:]),
                                 "prompt_sha256": pr["prompt_sha256"], "text": tok.decode(ids, skip_special_tokens=True),
                                 "token_ids": ids, "n_new_tokens": len(ids), "finish_reason": r["finish_reason"],
                                 "block_id": f"force:{task}:{w}:{name}", "utc": utc_now()})
                append_jsonl(RAW, rows)
                logger.info(f"{task}/{w}/{name}: {len(rows)} rows in {time.time() - t0:.1f}s")
            pre = None
            E.free_cuda()


if __name__ == "__main__":
    main()
