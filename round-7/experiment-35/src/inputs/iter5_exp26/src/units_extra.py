#!/usr/bin/env python3
"""Extra arm B (plan section 10): narrative-disguised variants V_<t> with paired parent re-measures P_<t>.

Parents (bench tasks of ITER2 exp11, vendored under vendor/exp11/bench): T03, T10, T05, T06 in the plan's order; the
path tasks T2 and T1 are skipped (their variants need the exp8 suite and the heap-vs-array Dijkstra structural
re-gate; logged deviation, F7). The I/O, signature, parameter names, constraints and hidden tests are the parent's,
so the parent's labellers apply unchanged (no wrapping needed: same function name solve and argument names).
P_<t> uses the parent's FROZEN exp17 twin prompts (exact token ids); V_<t> uses twins rendered with the parent's
neutral noun and the parent default's display name (exp22 R2 padding rule). Both share the parent's CRN uniforms
u_stream(<t>, w, k) and the parent's 8 direction seeds seed(<t>, k).
Importing this module registers the P_/V_ cards in units_spec.UNITS (the committed file is not edited).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from cfg5 import DATA_DIR, UNITS_DIR, VENDOR, cap_first, read_json, read_jsonl, utc_now, write_json, write_jsonl
from units_spec import UNITS, grep_banned

BENCH = VENDOR / "exp11" / "bench"
PARENT_DIRS = {"T03": "T03_kth_smallest", "T10": "T10_connected_components", "T05": "T05_two_sum",
               "T06": "T06_find_duplicate", "T04": "T04_substring_search", "T08": "T08_fibonacci",
               "T14": "T14_top_k_frequent", "R1": "R1_non_overlapping_intervals"}
PARENT_ORDER = ["T03", "T10", "T05", "T06", "T04", "T08", "T14", "R1"]
PROMPTS_EXTRA = DATA_DIR / "prompts_extra.jsonl"

VARIANT_DESCRIPTIONS = {
    "T03": ("Task: write a Python function solve(nums, k) that returns the k-th lowest score awarded by a panel of "
            "judges. The argument nums is the list of scores the judges gave, with 1 <= len(nums) <= 2000; every "
            "score is an integer between -10000 and 10000 inclusive, and several judges may give the same score. "
            "The argument k is an integer with 1 <= k <= len(nums), counted from 1, so k = 1 asks for the lowest "
            "score and k = len(nums) for the highest. Equal scores from different judges are counted separately: "
            "for nums = [3, 1, 3] and k = 3 the answer is 3."),
    "T10": ("Task: write a Python function solve(n, edges) that returns the number of separate island groups in an "
            "archipelago. The islands are numbered 0 to n - 1, with 1 <= n <= 300. The argument edges is a list of "
            "pairs [u, v] with 0 <= u, v < n and u != v, each meaning that a two-way ferry route joins islands u and "
            "v; 0 <= len(edges) <= 1500 and no two islands are joined by more than one route. Two islands belong to "
            "the same group when one can be reached from the other by a chain of ferry routes; an island with no "
            "routes forms a group on its own. Return the number of groups as an int."),
    "T05": ("Task: write a Python function solve(nums, target) that returns the positions of the two receipts whose "
            "amounts add up to the value of a gift voucher. The argument nums is the list of receipt amounts, with "
            "2 <= len(nums) <= 2000 and every amount an integer between -10**9 and 10**9 inclusive; target is the "
            "voucher value, an integer. Exactly one pair of receipts adds up to target, so the answer is unique. "
            "Return the two positions as a list [i, j] with i < j and nums[i] + nums[j] == target; the two receipts "
            "must be different positions, although their amounts may be equal."),
    "T06": ("Task: write a Python function solve(nums) that returns the ticket number that was printed more than "
            "once. The argument nums lists the numbers printed on n + 1 raffle tickets, where 1 <= n <= 10000, and "
            "every ticket number lies between 1 and n inclusive. Exactly one number appears on more than one ticket, "
            "possibly on two or more tickets; every other number appears on at most one ticket. Return the repeated "
            "ticket number as an int."),
    "T04": ("Task: write a Python function solve(haystack, needle) that returns where a password fragment first "
            "appears inside a long access log. The argument haystack is the log and needle is the fragment; both "
            "consist only of lowercase English letters, with 1 <= len(haystack) <= 2000 and 1 <= len(needle) <= 200. "
            "Return the 0-based position of the first character of the earliest place where needle appears as a run "
            "of consecutive characters of haystack, or -1 if it never appears there (in particular when needle is "
            "longer than haystack)."),
    "T08": ("Task: write a Python function solve(n) that returns how many pairs of rabbits a breeder has in month n "
            "under the classic breeding model, as an exact Python int. In month 0 there are 0 pairs and in month 1 "
            "there is 1 pair; from then on, the number of pairs in each month equals the sum of the numbers in the "
            "two previous months, so month 10 has 55 pairs. The argument n is an integer with 0 <= n <= 500, and the "
            "result must be exact for every n in that range."),
    "T14": ("Task: write a Python function solve(nums, k) that returns the k song identifiers that were played most "
            "often at a radio station, as a list in any arrangement. The argument nums is the play log, a list of "
            "integers with 1 <= len(nums) <= 10000 and every identifier between -10000 and 10000 inclusive; k is an "
            "integer between 1 and the number of distinct identifiers in nums. The play logs are chosen so that the "
            "answer is unique: the k-th and (k+1)-th highest play counts always differ."),
    "R1": ("Task: write a Python function solve(intervals) that returns the smallest number of meeting bookings that "
           "must be cancelled so that no two of the remaining bookings clash in a single meeting room. The argument "
           "intervals is a list of bookings [start, end] of integers with start < end, 1 <= len(intervals) <= 1000 "
           "and every value between -50000 and 50000 inclusive. Two bookings clash when they overlap in time; "
           "bookings that only touch, such as [1, 2] and [2, 3], do not clash. Return the number of cancellations "
           "as an int."),
}


def parent_of(u: str) -> str | None:
    return u[2:] if u[:2] in ("P_", "V_") else None


def bench_spec(t: str) -> dict[str, Any]:
    return read_json(BENCH / PARENT_DIRS[t] / "spec.json")


def exp17_twins(t: str) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(VENDOR / "exp17" / "prompts" / "prompts.jsonl") if r["task"] == t
            and r["kind"] == "twin"]


def register() -> None:
    for t in PARENT_ORDER:
        s = bench_spec(t)
        modes = {c["mode"]: (c["display_name"], c["mechanism"]) for c in s["catalogue"]}
        tw = exp17_twins(t)
        base = {"signature": s["signature"], "args": None, "modes": modes, "aliases": s["aliases"],
                "dataset_reference_mode": None, "excluded_by_limit": [], "whitelist": [], "bounds": s.get("bounds"),
                "parent": t, "parent_x_display": tw[0].get("x_display"), "parent_noun": tw[0].get("noun")}
        UNITS[f"P_{t}"] = {**base, "unit_id": f"P_{t}_parent_remeasure", "name": f"parent_{t}",
                           "source_ids": [f"bench:{PARENT_DIRS[t]}"], "description": s["description"]}
        UNITS[f"V_{t}"] = {**base, "unit_id": f"V_{t}_disguised_variant", "name": f"variant_{t}",
                           "source_ids": [f"bench:{PARENT_DIRS[t]} (re-worded)"],
                           "description": VARIANT_DESCRIPTIONS[t]}


register()


def build_prompts(tok: Any) -> list[dict[str, Any]]:
    """P_: exp17 frozen twins (exact ids); V_: twins W1-W5 rendered on the variant spec."""
    from prompts5 import render, twin_rows
    from cfg5 import FORMAT_LINE
    rows = []
    report = {}
    for t in PARENT_ORDER:
        for r in exp17_twins(t):
            pid = f"P_{t}|twin|-|{r['w']}"
            rows.append({"pid": pid, "unit": f"P_{t}", "kind": "twin", "segment": r["segment"],
                         "user_text": r["user_text"], "ids": r["ids"], "P": r["P"], "p0": r["p0"], "p1": r["p1"],
                         "spec_end": r["spec_end"], "prompt_sha256": r["prompt_sha256"], "template_id": r["w"],
                         "X": None, "noun": r.get("noun"), "n_pad": r.get("n_pad"),
                         "source": "exp17 prompts.jsonl (frozen parent twin)"})
        spec = cap_first(VARIANT_DESCRIPTIONS[t]) + "\n\n" + cap_first(FORMAT_LINE)
        noun = {"word": UNITS[f"P_{t}"]["parent_noun"], "display_name": UNITS[f"P_{t}"]["parent_x_display"]}
        vr = twin_rows(tok, f"V_{t}", noun, spec)
        rows += vr
        hits = grep_banned(f"V_{t}", VARIANT_DESCRIPTIONS[t])
        report[t] = {"variant_banned_hits": hits, "noun": noun, "n_tokens_spec": len(tok(spec)["input_ids"])}
        for u in (f"P_{t}", f"V_{t}"):
            d = UNITS_DIR / u
            d.mkdir(parents=True, exist_ok=True)
            write_json(d / "catalogue_frozen.json", {"unit": u, "utc": utc_now(),
                                                     "catalogue": list(UNITS[u]["modes"]),
                                                     "frozen_at": "parent bench catalogue (ITER2 exp11, gated)"})
    write_jsonl(PROMPTS_EXTRA, rows)
    write_json(UNITS_DIR / "extra_arm_build.json", report)
    return rows


_BENCH_CASES: dict[str, list] = {}


def label_bench(u: str, code_text: str) -> dict[str, Any]:
    """Parent's bench labeller (runtime primary, AST second) on a raw response text."""
    t = parent_of(u)
    if str(VENDOR / "exp11") not in sys.path:
        sys.path.insert(0, str(VENDOR / "exp11"))
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests
    if t not in _BENCH_CASES:
        _BENCH_CASES[t] = read_tests(BENCH / PARENT_DIRS[t] / "tests.jsonl")
    o = label_one({"sample_id": 0, "task": t, "condition": "twin", "text": code_text, "seed": 0}, _BENCH_CASES[t])
    rt = o.get("runtime_label")
    al = o.get("ast_label")
    rt = None if rt in ("unknown", None) else rt
    al = None if al in ("unknown", None) else al
    out = {"valid": o.get("valid", False), "passed": bool(o.get("passed")), "runtime_label": rt, "ast_label": al,
           "code_sha256": o.get("code_sha256")}
    if not out["valid"]:
        out.update(label_pre="invalid", labeller_source="invalid", runtime_label="invalid", ast_label="invalid")
    elif rt is not None and rt == al:
        out.update(label_pre=rt, labeller_source="agree")
    elif rt is None and al is not None:
        out.update(label_pre=al, labeller_source="ast_only_untraceable")
    elif al is None and rt is not None:
        out.update(label_pre=rt, labeller_source="runtime_only")
    elif rt is None and al is None:
        out.update(label_pre="other", labeller_source="neither")
    else:
        out.update(label_pre=None, labeller_source="disagree")
    return out


def stage_i(t: str) -> dict[str, Any]:
    """Parent's labellers on the parent's references (100% required) -> gate_stage_i.json for P_ and V_."""
    res = {}
    for ref in sorted((BENCH / PARENT_DIRS[t] / "references").glob("*.py")):
        o = label_bench(f"P_{t}", "```python\n" + ref.read_text() + "\n```")
        res[ref.stem] = {"runtime": o["runtime_label"], "ast": o["ast_label"], "passed": o["passed"],
                         "ok": o["runtime_label"] == ref.stem and o["ast_label"] == ref.stem and o["passed"]}
    ok = all(v["ok"] for v in res.values())
    for u in (f"P_{t}", f"V_{t}"):
        write_json(UNITS_DIR / u / "gate_stage_i.json", {"unit": u, "utc": utc_now(),
                                                         "status": "PROVISIONAL" if ok else "FAIL",
                                                         "labellers_on_parent_references": res,
                                                         "parent_bench_gate": read_json(BENCH / PARENT_DIRS[t] /
                                                                                        "gate.json")["status"]})
    return res


if __name__ == "__main__":
    from transformers import AutoTokenizer
    from cfg5 import MODEL_ID, MODEL_REVISION, model_path
    tk = AutoTokenizer.from_pretrained(model_path(MODEL_ID, MODEL_REVISION))
    rows = build_prompts(tk)
    print(len(rows), json.dumps(read_json(UNITS_DIR / "extra_arm_build.json"), indent=1))
    for t in PARENT_ORDER:
        print(t, stage_i(t))
