#!/usr/bin/env python3
"""Offline tests (no LLM call): sandbox, harness extensions, prompts and body extraction, DTB/RPB on synthetic top-20
tables, island sampling/reset, clusters. Writes results/tests_offline.json; exits 1 on any failure."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402

import bp  # noqa: E402
import clusters as CL  # noqa: E402
import common as C  # noqa: E402
import islands as IS  # noqa: E402
import operators as OP  # noqa: E402
import prompts as P  # noqa: E402
import sandbox  # noqa: E402

R: dict = {}


def check(name: str, ok: bool, info=None) -> None:
    R[name] = {"ok": bool(ok), "info": info}
    print(("PASS " if ok else "FAIL ") + name + (f"  {info}" if info is not None else ""))


def test_sandbox(pool) -> None:
    def ev(code, **kw):
        t = dict(sandbox.selection_task(code), **kw)
        return pool.submit(t).result()
    hdr = P.PROGRAM_HEADER + "\n"
    check("reject import os", ev(hdr + "    import os\n    return bins")["error_type"] == "forbidden")
    check("reject open()", ev(hdr + "    open('x')\n    return bins")["error_type"] == "forbidden")
    check("reject eval", ev(hdr + "    return eval('bins')")["error_type"] == "forbidden")
    check("reject dunder", ev(hdr + "    return bins.__class__")["error_type"] == "forbidden")
    t = time.time()
    r = ev(hdr + "    while True:\n        pass\n    return bins")
    check("while True -> timeout within budget", r["error_type"] == "timeout" and time.time() - t < 60,
          round(time.time() - t, 1))
    slow_w = hdr + ("    if bins.max() == 100:\n        s = 0\n        for i in range(80000):\n            s += i\n"
                    "    return -(bins - item)")
    t = time.time()
    r = ev(slow_w)
    check("slow only on SEL-W fails within 20 s total", r["error_type"] == "timeout" and r["eval_s"] < 25,
          {"et": r["error_type"], "eval_s": round(r.get("eval_s", 0), 1), "wall": round(time.time() - t, 1)})
    r = ev(hdr + "    x = np.ones(int(1.3e9))\n    return -(bins - item)")
    check("10 GB allocation -> memory", r["error_type"] == "memory", r["error_type"])
    r = ev(hdr + "    return np.zeros(len(bins) + 1)")
    check("wrong shape -> shape", r["error_type"] == "shape", r["error_type"])
    r = ev(hdr + "    s = -(bins - item).astype(float)\n    s[0] = np.inf\n    return s")
    check("inf -> nonfinite (strict)", r["error_type"] == "nonfinite", r["error_type"])
    check("nonfinite program re-scored under FunSearch semantics", r.get("fs", {}).get("error_type") == "ok")
    check("nonfinite program gets a probe vector (argmax semantics)", r["probes"].get("P10") is not None)
    r = ev(hdr + "    s = -(bins - item).astype(float)\n    s[-1] = np.nan\n    return s")
    check("NaN -> nonfinite (strict)", r["error_type"] == "nonfinite")
    r = ev(hdr + "    return priority_v1(item, bins)")
    check("call to priority_v1 -> runtime", r["error_type"] == "runtime")
    check("empty body -> syntax", ev(P.program_from_completion("```"))["error_type"] == "syntax")
    # priority forms equal hand-coded packers
    import gate
    ok = {}
    for nm, prio, hand in [("FF", bp.prio_ff, gate.hand_ff), ("BF", bp.prio_bf, gate.hand_bf),
                           ("WF", bp.prio_wf, gate.hand_wf), ("AWF", bp.prio_awf, bp.hand_awf)]:
        ok[nm] = all(bp.pack(x["items"], x["capacity"], prio) == hand(x["items"], x["capacity"])
                     for x in bp.load_set("SEL-OR")[:3] + bp.load_set("SEL-W")[:1])
    check("priority forms == hand-coded packers (FF/BF/WF/AWF)", all(ok.values()), ok)
    r1 = ev(P.seed_program(P.BF_BODY))
    F = bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), 0.05997931747673214, 0.042309606769537086)
    check("BF via sandbox: F == 1", r1["error_type"] == "ok" and
          abs(F.F(r1["bins"]["SEL-OR"] + r1["bins"]["SEL-W"]) - 1.0) < 1e-12)
    cache = sandbox.EvalCache(pool)
    k1, f1, c1 = cache.submit(P.seed_program(P.BF_BODY))
    a = f1.result()
    k2, f2, c2 = cache.submit(P.seed_program(P.BF_BODY) + "\n    # comment only")
    b = f2.result()
    check("cached duplicate returns identical result", c2 and k1 == k2 and a["bins"] == b["bins"] and
          a["probes"]["P10"] == b["probes"]["P10"])
    check("stochastic flag", sandbox.is_stochastic(P.PROGRAM_HEADER + "\n    return np.random.rand(len(bins))")
          and not sandbox.is_stochastic(P.seed_program(P.BF_BODY)))
    check("next_fit sane", bp.next_fit([60, 50, 50, 60], 100) == 3)


def test_prompts(tok) -> None:
    bf = P.seed_program(P.BF_BODY)
    ff = P.seed_program(P.FF_BODY)
    txt, ids = P.render(tok, P.user_turn(ff, bf))
    check("render: empty think block present, ends with prefill", "<think>\n\n</think>" in txt and txt.endswith(P.PREFILL))
    check("render: tokens decode back", tok.decode(ids) == txt)
    t1, ti = P.user_turn(ff, bf), P.user_turn(ff, bf, idea=True)
    check("IDEA differs from T1.0 by exactly one sentence", ti == t1 + "\n\n" + P.IDEA_SENTENCE)
    check("NS prompt constant", P.user_turn(ff, bf) == P.user_turn(ff, bf))
    cases = {
        "fence stop": ("    return bins - item\n```\nextra", "    return bins - item"),
        "trailing def": ("    x = 1\n    return x * bins\n\ndef foo():\n    pass", "    x = 1\n    return x * bins"),
        "top-level print": ("    return bins\nprint(priority_v2(1, bins))", "    return bins"),
        "truncation": ("    s = bins - item\n    return s[", "    s = bins - item\n    return s["),
        "tabs": ("\treturn bins - item", "\treturn bins - item"),
        "empty": ("```", ""),
        "indent0 text": ("    return bins\nThis function ...", "    return bins"),
        "blank lines kept inside": ("    a = 1\n\n    return a + bins", "    a = 1\n\n    return a + bins"),
        "class stop": ("    return bins\nclass X:\n    pass", "    return bins"),
        "main stop": ("    return bins\nif __name__ == '__main__':\n    pass", "    return bins"),
        "decorator stop": ("    return bins\n@foo\ndef g(): pass", "    return bins"),
        "trailing spaces": ("    return bins   \n   \n", "    return bins"),
    }
    bad = {k: (P.extract_body(c), e) for k, (c, e) in cases.items() if P.extract_body(c) != e}
    check("12 crafted completions give the expected bodies", not bad and len(cases) == 12, bad or None)
    check("body_of drops a model-written docstring", P.body_of(P.PROGRAM_HEADER + '\n    """doc"""\n    return bins')
          == "    return bins")


def test_branch(tok) -> None:
    tt = OP.TokText(tok)
    ids = tok("    remaining = bins - item  # gap\n    return -remaining", add_special_tokens=False)["input_ids"]
    rng = np.random.default_rng(0)
    vocab = [i for i in tok("x y z a b c d e f g h k m n p q r s t u v w", add_special_tokens=False)["input_ids"]]
    top = []
    for t, g in enumerate(ids):
        others = [v for v in vocab if v != g][:19]
        lp = np.sort(rng.normal(-3, 1, size=19))[::-1]
        pairs = [(g, -0.1 - 0.05 * t)] + [(int(o), float(min(x, -0.2))) for o, x in zip(others, lp)]
        top.append(pairs)
    hi = 2
    top[hi] = [(p[0], -2.9957 + 0.0001 * k) for k, p in enumerate(top[hi])]  # near-uniform -> max entropy
    plan = OP.branch_plan(tt, ids, top, 2, "DTB", 5)
    Hs = plan["H"]
    best = max(plan["E"], key=lambda t: (Hs[t], -t))
    check("DTB: j = argmax of H over E (ties earliest)", plan["j"] == best, {"j": plan["j"], "best": best})
    cs = set(plan["in_comment_string"])
    check("comment positions excluded from E", cs and not (cs & set(plan["E"])), sorted(cs))
    check("forced rank in 2..8", 2 <= plan["r"] <= 8)
    check("forced id is a filtered candidate", tt.cand_ok(plan["forced_id"]))
    plan2 = OP.branch_plan(tt, ids, top, 2, "DTB", 5)
    check("DTB plan deterministic (re-derivation)", plan2["j"] == plan["j"] and plan2["forced_id"] == plan["forced_id"])
    pr = OP.branch_plan(tt, ids, top, 2, "RPB", 5)
    check("RPB uses the same E and rank rule", pr["E"] == plan["E"] and 2 <= pr["r"] <= 8)
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    nl = tok("\nx", add_special_tokens=False)["input_ids"]
    fence = tok("```", add_special_tokens=False)["input_ids"][0]
    sp = tok("   ", add_special_tokens=False)["input_ids"][0]
    check("EOS / fence / whitespace / dedent candidates excluded",
          not tt.cand_ok(im_end) and not tt.cand_ok(fence) and not tt.cand_ok(sp) and
          all(not tt.cand_ok(i) for i in nl if "\n" in tt.text(i) and tt.text(i).strip()) )
    # shuffled entropy vector must disagree with the logged j (audit placebo d)
    dis = 0
    for k in range(20):
        Hs2 = list(np.random.default_rng(k).permutation(Hs))
        dis += int(max(plan["E"], key=lambda t: (Hs2[t], -t)) != plan["j"])
    check("shuffled entropy re-derivation disagrees with j (>= 10 of 20 shuffles)", dis >= 10, dis)


def test_islands() -> None:
    bf = {"pid": "seed-BF", "code": "x" * 30, "F": 1.0, "sig": [1] * 25}
    db = IS.ArmDB(2, "T1.0", bf)
    for isl in db.islands:
        isl.register({"pid": "a", "code": "y" * 40, "F": 0.9, "sig": [2] * 25})
        isl.register({"pid": "b", "code": "z" * 50, "F": 0.95, "sig": [3] * 25})
    counts = {}
    n = 20000
    for _ in range(n):
        i, w, b = db.draw_parents()
        for p in (w, b):
            counts[p["pid"]] = counts.get(p["pid"], 0) + 1
    p = IS.softmax(np.array([-1.0, -0.9, -0.95]), 0.1 * (1 - 3 / 30000))
    exp = {"seed-BF": p[0], "a": p[1], "b": p[2]}
    ok = all(abs(counts.get(k, 0) / (2 * n) - v) < 2 * np.sqrt(v * (1 - v) / (2 * n)) + 0.004 for k, v in exp.items())
    check("cluster sampling within 2 SE of the softmax", ok, {k: round(counts.get(k, 0) / (2 * n), 4) for k in exp})
    db2 = IS.ArmDB(2, "T1.0", bf)
    db2.islands[0].register({"pid": "short", "code": "s" * 10, "F": 0.8, "sig": [4] * 25})
    db2.islands[0].register({"pid": "long", "code": "l" * 400, "F": 0.8, "sig": [4] * 25})
    cnt = {"short": 0, "long": 0}
    for _ in range(4000):
        i, w, b = db2.draw_parents()
        for q in (w, b):
            if q["pid"] in cnt:
                cnt[q["pid"]] += 1
    check("shorter programs preferred within a cluster", cnt["short"] > cnt["long"], cnt)
    db3 = IS.ArmDB(2, "T1.0", bf)
    db3.islands[3].register({"pid": "good", "code": "g", "F": 0.5, "sig": [5] * 25})
    db3.calls = 400
    ev = db3.maybe_reset()
    check("2 worst of 5 islands reset at 400 calls", ev is not None and len(ev["reset"]) == 2 and 3 not in ev["reset"]
          and db3.maybe_reset() is None, ev)


def test_clusters() -> None:
    rng = np.random.default_rng(3)
    base = rng.integers(1, 100, size=(5, 2000)).astype(np.uint16)
    vecs = []
    for b in base:
        for _ in range(20):
            v = b.copy()
            idx = rng.choice(2000, size=20, replace=False)
            v[idx] = rng.integers(1, 100, size=20)
            vecs.append(v)
    vecs = np.stack(vecs)
    lab = CL.complete_linkage(vecs, 0.95)
    led = CL.leader_clusters(vecs, 0.95)
    check("planted 5x20 -> 5 clusters (complete linkage and leader)", len(set(lab)) == 5 and len(set(led)) == 5,
          [len(set(lab)), len(set(led))])
    check("complete-linkage invariant", CL.linkage_invariant(vecs, lab, 0.95))
    A = CL.agreement_matrix(vecs, vecs)
    ok = True
    for _ in range(100):
        i, j = rng.integers(0, len(vecs), size=2)
        bf_ = float(np.mean((vecs[i] == vecs[j]) & (vecs[i] != 65535)))
        ok &= abs(A[i, j] - bf_) < 1e-6
    check("one-hot agreement == brute force (100 pairs)", ok)
    v = vecs[:2].copy()
    v[0, :10] = 65535
    v[1, :10] = 65535
    check("ERR never agrees", abs(CL.agreement_matrix(v[:1], v[1:])[0, 0] - np.mean(v[0, 10:] == v[1, 10:]) * 1990 / 2000) < 1e-9)


def main() -> None:
    import engine
    tok = engine.load_tokenizer()
    pool = sandbox.EvalPool(6, ROOT)
    try:
        test_sandbox(pool)
    finally:
        pool.close()
    test_prompts(tok)
    test_branch(tok)
    test_islands()
    test_clusters()
    n_fail = sum(not v["ok"] for v in R.values())
    C.write_json(C.RESULTS / "tests_offline.json", {"utc": C.utc(), "n": len(R), "n_fail": n_fail, "results": R})
    print(f"{len(R) - n_fail}/{len(R)} passed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
