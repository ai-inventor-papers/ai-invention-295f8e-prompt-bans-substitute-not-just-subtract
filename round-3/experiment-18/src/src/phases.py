"""GPU phase drivers.

Phase A (bf16 Qwen3-8B server): T1/T2 token walk + sham + fixed-TOP5, then (after the committed forecasts) the
T1/T2 two-step bans as filler.  Phase B (FP8 server): the bench walk (T03, T04, T06, T10) + bench shams, LOS lists
after the step-1 commit and two-step bans after the step-2 commit.  Each family runs at the precision its
iteration-2 reference programs and 'can' estimates were produced with (path: bf16 exp8/exp9; bench: FP8 exp11).
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from loguru import logger

from client import run_batch
from config import (BENCH_DIR, INPUTS, MAX_TOKENS_SHORT, RESULTS, ROOT, TASKS, seed_unit, setup_logging, sha256_file,
                    utc_now, write_json)
from ngram import occurrences, string_leak, unit_tests as ngram_unit_tests
from prompts import ids_of, neutral_twins, tokenizer
from reach import commit_reach, commit_two_step, los_jobs, two_step_jobs
from walk import MaskArm, Scheduler, WalkArm, build_sham, build_top5, decode, encode, mask_item, veto_seqs


# ------------------------------------------------------------------------------------------------ S0
def verify_bench() -> dict[str, Any]:
    from bench.common.commit import canon_json  # the bench's own canonical JSON (report.py freeze rule)
    from config import sha256_text

    com = json.loads((BENCH_DIR / "commitment.json").read_text())
    out = {}
    for t in ("T03", "T04", "T06", "T10"):
        files = com["tasks"][t]["files"]
        d = BENCH_DIR / TASKS[t]["task_id"]
        bad = []
        for f, h in files.items():
            if f == "catalogue":
                got = sha256_text(canon_json(json.loads((d / "spec.json").read_text())["catalogue"]))
            else:
                got = sha256_file(d / f) if (d / f).exists() else None
            if got != h:
                bad.append(f)
        task_ok = sha256_text(canon_json(files)) == com["tasks"][t]["task_sha256"]
        out[t] = {"n_files": len(files), "mismatches": bad, "task_sha256_ok": task_ok, "ok": not bad and task_ok}
    common = com.get("common") or com.get("common_files") or {}
    if common:
        badc = [f for f, h in common.items() if sha256_file(BENCH_DIR / "common" / f) != h]
        out["common"] = {"n_files": len(common), "mismatches": badc, "ok": not badc}
    return out


def write_sha256sums() -> int:
    lines = []
    for p in sorted(INPUTS.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {p.relative_to(INPUTS)}")
    (INPUTS / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    return len(lines)


# ------------------------------------------------------------------------------------------------ unit tests
def veto_unit_tests(kind: str) -> dict[str, Any]:
    """u1-u4 (S3) on the running server, before any walk sample."""
    res: dict[str, Any] = {"utc": utc_now(), "engine": kind}
    task = "T2" if kind == "bf16" else "T10"
    tw = neutral_twins(task)
    w = WalkArm(task)
    item = mask_item("distinctive", w.D, 1, 0, w.d_default)
    seqs = veto_seqs([item])
    # u1: vetoed generations never contain a banned id sequence
    reqs = [{"prompt_ids": tw["W1"]["ids"], "seed": seed_unit(i), "max_tokens": MAX_TOKENS_SHORT, "veto": seqs}
            for i in range(20)]
    outs, _ = run_batch(kind, reqs)
    occ = [occurrences(o["token_ids"], seqs) for o in outs]
    res["u1"] = {"task": task, "vetoed": item["string"], "seqs": seqs, "occurrences": occ, "pass": sum(occ) == 0,
                 "string_in_text": sum(item["string"].strip() in o["text"] for o in outs)}
    # u2: no-veto requests are reproducible across batches and unaffected by vetoed neighbours in the batch
    base = [{"prompt_ids": tw["W1"]["ids"], "seed": seed_unit(100 + i), "max_tokens": MAX_TOKENS_SHORT} for i in range(20)]
    o1, _ = run_batch(kind, base)
    mixed = []
    for i, r in enumerate(base):
        mixed.append(r)
        mixed.append({"prompt_ids": tw["W2"]["ids"], "seed": seed_unit(200 + i), "max_tokens": MAX_TOKENS_SHORT,
                      "veto": seqs})
    om, _ = run_batch(kind, mixed)
    o2 = om[0::2]
    eq = [a["token_ids"] == b["token_ids"] for a, b in zip(o1, o2)]
    res["u2"] = {"n": len(eq), "identical_token_for_token": sum(eq), "rate": sum(eq) / len(eq),
                 "note": "same seeds, no veto, batch A alone vs interleaved with vetoed rows; a processor-free engine "
                         "was not loaded (second ~6 min engine load), so this measures batch/plugin invariance and "
                         "vLLM nondeterminism together", "pass": sum(eq) / len(eq) >= 0.8}
    # u3: rows with different veto lists respect only their own
    other_item = mask_item("unit", "unit", 0, 0, {"ids": ids_of(" print"), "string": " print"})
    seqs_b = veto_seqs([other_item])
    rq = []
    for i in range(10):
        rq.append({"prompt_ids": tw["W1"]["ids"], "seed": seed_unit(300 + i), "max_tokens": MAX_TOKENS_SHORT,
                   "veto": seqs})
        rq.append({"prompt_ids": tw["W1"]["ids"], "seed": seed_unit(400 + i), "max_tokens": MAX_TOKENS_SHORT,
                   "veto": seqs_b})
    ou, _ = run_batch(kind, rq)
    a_occ = sum(occurrences(o["token_ids"], seqs) for o in ou[0::2])
    b_occ_own = sum(occurrences(o["token_ids"], seqs_b) for o in ou[1::2])
    b_has_a = sum(occurrences(o["token_ids"], seqs) > 0 for o in ou[1::2])
    res["u3"] = {"rows_A_own_occurrences": a_occ, "rows_B_own_occurrences": b_occ_own,
                 "rows_B_containing_A_seq": b_has_a, "pass": a_occ == 0 and b_occ_own == 0 and b_has_a > 0}
    # u4: the string-leak detector flags a synthetic non-canonical spelling of the vetoed string
    core = item["string"].strip()
    pieces = [ids_of(ch)[0] for ch in core]  # one token per character: non-canonical tokenisation
    synth_ids = ids_of("x = ") + pieces + ids_of("()\n")
    synth_text = decode(synth_ids)
    lk = string_leak(synth_text, synth_ids, [item], decode)
    res["u4"] = {"synthetic_text": synth_text, "leak": lk["leak"], "spans": lk["items"][0]["spans"] if lk["items"]
                 else [], "pass": lk["leak"] and core in synth_text}
    res["ngram_unit_tests"] = {k: v for k, v in ngram_unit_tests(decode, encode).items()
                               if k in ("planted_found", "tie_smaller_n", "sham_generic", "expand_variants",
                                        "occurrences", "all_pass")}
    res["all_pass"] = all(res[k]["pass"] for k in ("u1", "u3", "u4")) and res["ngram_unit_tests"]["all_pass"]
    write_json(RESULTS / f"veto_unit_tests_{kind}.json", res)
    logger.info(f"veto unit tests ({kind}): u1 {res['u1']['pass']} u2 {res['u2']['rate']:.2f} u3 {res['u3']['pass']} "
                f"u4 {res['u4']['pass']} ngram {res['ngram_unit_tests']['all_pass']}")
    return res


# ------------------------------------------------------------------------------------------------ hooks
def make_hooks(group: str, walkers: list[WalkArm], with_los: bool) -> list:
    state = {"reach": False, "two": False}

    def done_step(w: WalkArm, k: int) -> bool:
        return (not w.active) or w.step > k

    def hook(sched: Scheduler, arms: list) -> None:
        if not state["reach"] and all(done_step(w, 1) for w in walkers):
            commit_reach(walkers, group)
            state["reach"] = True
            if with_los:
                for w in walkers:
                    if TASKS[w.task]["family"] == "bench":
                        sched.add_filler(los_jobs(w.task))
                logger.info(f"[{group}] reach forecasts committed; LOS jobs queued ({len(sched.filler)})")
        if state["reach"] and not state["two"] and all(done_step(w, 2) for w in walkers):
            fc = commit_two_step(walkers, group)
            state["two"] = True
            for w in walkers:
                r2 = fc["tasks"][w.task]["R2"]["R2"]
                if r2:
                    sched.add_filler(two_step_jobs(w.task, r2))
            logger.info(f"[{group}] two-step forecasts committed; two-step jobs queued")

    return [hook]


def run_group(kind: str, tasks: list[str], with_sham: bool, with_top5: bool, group: str) -> None:
    walkers = [WalkArm(t) for t in tasks]
    arms: list = list(walkers)
    if with_sham:
        for w in walkers:
            sh, _ = build_sham(w)
            if sh is not None:
                arms.append(sh)
    if with_top5 and "T1" in tasks:
        arms.append(build_top5(next(w for w in walkers if w.task == "T1")))
    sched = Scheduler(kind)
    sched.hooks = make_hooks(group, walkers, with_los=(group == "bench"))
    t0 = time.time()
    sched.run(arms)
    write_json(RESULTS / f"group_{group}_done.json", {"utc": utc_now(), "wall_s": round(time.time() - t0, 1),
                                                     "status": {a.arm + ":" + a.task: a.status for a in arms}})


def main() -> None:
    which = sys.argv[1]
    setup_logging(f"phase_{which}")
    if which == "s0":
        vb = verify_bench()
        n = write_sha256sums()
        write_json(RESULTS / "inputs_check.json", {"bench_commitment": vb, "n_input_files_hashed": n, "utc": utc_now()})
        logger.info(f"bench verify: {vb}; hashed {n} input files")
    elif which == "unit_bf16":
        veto_unit_tests("bf16")
    elif which == "unit_fp8":
        veto_unit_tests("fp8")
    elif which == "A":
        run_group("bf16", ["T1", "T2"], with_sham=True, with_top5=True, group="path")
    elif which == "two_step":
        group, kind = sys.argv[2], sys.argv[3]
        fc = json.loads((ROOT / "predictions" / f"two_step_forecasts_{group}.json").read_text())
        sched = Scheduler(kind)
        for t, v in fc["tasks"].items():
            if v["R2"]["R2"]:
                sched.add_filler(two_step_jobs(t, v["R2"]["R2"]))
        sched.run([])
    elif which == "B":
        tasks = sys.argv[2].split(",") if len(sys.argv) > 2 else ["T03", "T04", "T06", "T10"]
        run_group("fp8", tasks, with_sham=True, with_top5=False, group="bench")


if __name__ == "__main__":
    main()
