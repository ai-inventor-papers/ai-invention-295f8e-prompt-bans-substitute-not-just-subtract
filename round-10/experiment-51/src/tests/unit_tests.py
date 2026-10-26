#!/usr/bin/env python3
"""Testing plan items 2 (sandbox), 4 (prompt and trim), 5 (DTB/RPB synthetic), 6 (islands), 7 (clusters).
Writes results/unit_tests.json; exits non-zero on any failure."""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import bp  # noqa: E402
import cluster  # noqa: E402
import engine  # noqa: E402
import islands  # noqa: E402
import prompts  # noqa: E402
import sandbox  # noqa: E402

R: dict = {}


def check(name: str, ok: bool, detail=None) -> None:
    R[name] = {"pass": bool(ok), "detail": detail}
    print(("PASS " if ok else "FAIL ") + name + ("" if detail is None else f"  {str(detail)[:200]}"))


def t_sandbox() -> None:
    pool = sandbox.EvalPool(3, ROOT, as_gib=2.0)
    cases = {
        "import_os": "import os\ndef priority(item, bins):\n    return bins\n",
        "open": "def priority(item, bins):\n    open('x')\n    return bins\n",
        "eval": "def priority(item, bins):\n    return eval('bins')\n",
        "dunder": "def priority(item, bins):\n    return bins.__class__\n",
        "loop": "def priority(item, bins):\n    while True:\n        pass\n",
        "mem": "def priority(item, bins):\n    x = np.ones(10_000_000_000 // 8)\n    return bins\n",
        "shape": "def priority(item, bins):\n    return np.zeros(3)\n",
        "nan": "def priority(item, bins):\n    s = -(bins - item).astype(float)\n    s[0] = np.nan\n    return s\n",
    }
    futs = {k: pool.submit({"code": v, "sets": ["SEL-OR"], "limit": 2.0, "fail_fast": True, "probes": []})
            for k, v in cases.items()}
    res = {k: f.result() for k, f in futs.items()}
    exp = {"import_os": "forbidden", "open": "forbidden", "eval": "forbidden", "dunder": "forbidden",
           "loop": "timeout", "mem": "memory", "shape": "shape"}
    for k, e in exp.items():
        check(f"sandbox_{k}", res[k]["error_type"] == e, res[k]["error_type"] + " " + res[k]["msg"][:80])
    # NaN behaves like np.argmax (first NaN wins) -> same bins as a direct pack with that priority
    fn, _, _ = sandbox.compile_program(cases["nan"])
    direct = [bp.pack(x["items"], x["capacity"], fn) for x in bp.load_set("SEL-OR")]
    check("sandbox_nan_like_argmax", res["nan"]["error_type"] == "ok" and res["nan"]["bins"]["SEL-OR"] == direct)
    # the respawned worker still works after the timeout / memory cases
    f = pool.submit({"code": bp.SRC_BF, "sets": ["SEL-OR"], "limit": 5.0, "fail_fast": True, "probes": []})
    check("sandbox_respawn_ok", f.result()["error_type"] == "ok", pool.n_respawn)
    pool.close()


def t_prompts(tok) -> None:
    text, ids = prompts.render(tok, [prompts.SEED_BODY_BF], idea=False)
    check("prompt_think_block", "<think>\n\n</think>\n\n" in text)
    check("prompt_ends_with_prefill", text.endswith(prompts.prefill(1)))
    t2, _ = prompts.render(tok, [prompts.SEED_BODY_FF, prompts.SEED_BODY_BF], idea=False)
    check("prompt_k2_versions", "def priority_v0(" in t2 and "def priority_v1(" in t2 and t2.endswith(prompts.prefill(2))
          and "Improved version of `priority_v0`." in t2)
    for k, bodies in ((1, [prompts.SEED_BODY_BF]), (2, [prompts.SEED_BODY_FF, prompts.SEED_BODY_BF])):
        a, b = prompts.user_message(bodies, False), prompts.user_message(bodies, True)
        extra = b[len(a):]
        check(f"idea_one_sentence_k{k}", b.startswith(a) and extra.count(".") == 1 and extra.startswith(" Write")
              and ("both functions above" in extra) == (k == 2), extra)
    crafted = [
        ("    return -(bins - item)\n", "    return -(bins - item)\n"),
        ("    return bins\n\n\ndef helper():\n    pass", "    return bins\n"),
        ("    x = bins - item\n    return -x\nprint(1)", "    x = bins - item\n    return -x\n"),
        ("    s = bins\n\n    return s\n\nimport os\n", "    s = bins\n\n    return s\n"),
        ("\treturn bins - item\n", "\treturn bins - item\n"),
        ("    return priority_v1(item, bins)\n", "    return priority(item, bins)\n"),
        ("    if item > 50:\n        return -bins\n    return bins\n", "    if item > 50:\n        return -bins\n    return bins\n"),
        ("", ""),
        ("    # comment only\n", "    # comment only\n"),
        ("    return bins  # trailing\nclass X:\n", "    return bins  # trailing\n"),
        ("    a = 1\n    b = 2\n    return a * bins + b\n```", "    a = 1\n    b = 2\n    return a * bins + b\n```"),
        ("    return bins\nif __name__ == '__main__':\n    pass", "    return bins\n"),
    ]
    ok = True
    bad = []
    for comp, exp in crafted:
        got = prompts.trim_body(comp, 1)
        exp2 = exp if exp.strip() or not exp else exp
        if comp.endswith("```"):
            exp2 = prompts.trim_body(comp.replace("```", ""), 1)  # the server strips the fence stop
        if got != exp2 and not comp.endswith("```"):
            ok = False
            bad.append((comp, got, exp2))
    check("trim_12_crafted", ok and len(crafted) == 12, bad)
    check("program_from_k2_rename", prompts.program_from("    return priority_v2(item, bins)\n", 2) ==
          "def priority(item, bins):\n    return priority(item, bins)\n")


class FakeTok:
    eos_token_id, pad_token_id = 0, 0

    def __init__(self, vocab):
        self.v = vocab

    def decode(self, ids):
        return "".join(self.v[i] for i in ids)

    def convert_tokens_to_ids(self, t):
        return {"<|im_end|>": 1, "<|endoftext|>": 2}.get(t)


def t_dtb() -> None:
    vocab = {0: "<eos>", 1: "<|im_end|>", 2: "<|endoftext|>", 3: "    ", 4: "return", 5: " -", 6: "(", 7: "bins", 8: " #",
             9: " note", 10: "\n", 11: " '", 12: "str", 13: "'", 14: " +", 15: " item", 16: ")", 17: "```", 18: "\nx",
             19: " *", 20: " 2", 21: " np", 22: ".", 23: "max", 24: " ", 25: "abs"}
    eng = engine.Engine.__new__(engine.Engine)
    eng.tok = FakeTok(vocab)
    eng.special = {0, 1, 2}
    eng._tok_text = {}
    ids = [3, 4, 5, 6, 7, 14, 15, 16, 8, 9, 10]
    peak = 2  # ' -' gets the highest entropy among code tokens; the comment token ' note' is made even higher

    def top(i, flat):
        cands = [17, 18, 0, 19, 20, 21, 22, 23, 25, 14, 15, 6, 7, 16, 24, 9, 12, 13, 5, 4]
        lp = np.linspace(0, -1 if flat else -12, 20)
        return [(ids[i], 0.0)] + [(c, float(v)) for c, v in zip(cands[:19], lp[1:])]

    tops = [top(i, flat=(i == peak or i == 9)) for i in range(len(ids))]
    gen1 = {"ids": ids, "tops": tops, "text": "".join(vocab[i] for i in ids)}
    rng = np.random.default_rng(0)
    f = engine.choose_fork(eng, gen1, "entropy", rng)
    check("dtb_argmax_over_E", f.get("j") == peak, f.get("j"))
    check("dtb_skips_comment_ws", 9 not in f["E"] and 8 not in f["E"] and 0 not in f["E"] and 10 not in f["E"], f["E"])
    check("dtb_forced_rank_2_8", 2 <= f["forced_rank"] <= 8)
    check("dtb_excluded_tokens", all(c not in (17, 18, 0) for _, c in f["cands"]), f["cands"])
    f2 = engine.choose_fork(eng, gen1, "random", np.random.default_rng(1))
    check("rpb_same_E", f2["E"] == f["E"] and f2["j"] in f["E"])
    # string scanning
    s = "    x = 'ab # c' + \"\"\"q\nr\"\"\"  # tail\n    return x"
    ins = engine.scan_inside(s)
    check("scanner_strings_comments", ins[s.index("'")] and ins[s.index("#")] and ins[s.index("q")] and
          not ins[s.index("return")] and ins[s.index("tail")])


def t_islands() -> None:
    rng = np.random.default_rng(5)
    isl = islands.Island()
    scores = [-100.0, -99.95, -99.9, -100.1]  # 0.05-point gaps at T 0.1 -> non-degenerate softmax
    for i, sc in enumerate(scores):
        isl.register({"pid": f"p{i}", "code": "x" * (10 + i)}, sc, (i,))
    p = islands.softmax(np.array(scores), islands.T_INIT * (1 - (isl.n_programs % 30000) / 30000))
    n, counts = 20000, np.zeros(4)
    sig_of = {f"p{i}": i for i in range(4)}
    for _ in range(n // 2):
        for prog in isl.get_prompt_parents(rng):
            counts[sig_of[prog["pid"]]] += 1
    emp = counts / counts.sum()
    se = np.sqrt(p * (1 - p) / counts.sum())
    check("islands_softmax_2SE", bool(np.all(np.abs(emp - p) <= 2 * se + 1e-12)), {"emp": emp.round(4).tolist(),
                                                                                   "p": p.round(4).tolist()})
    cl = islands.Cluster(-1.0, {"pid": "long", "code": "x" * 400})
    cl.register({"pid": "short", "code": "x" * 40})
    picks = [cl.sample(rng)["pid"] for _ in range(4000)]
    check("islands_shorter_preferred", picks.count("short") > picks.count("long"), picks.count("short"))
    seed = {"pid": "seed-BF", "code": bp.SRC_BF, "F": 1.0, "bins25": [1] * 25}
    db = islands.Database(0, 0, seed, -100.0, tuple(seed["bins25"]))
    for i in range(5):
        db.register({"pid": f"q{i}", "code": "y" * 30, "F": 1 - 0.01 * i}, -100 * (1 - 0.01 * i), (i, 9), i)
    ev = db.reset()
    check("islands_reset_2_of_5", len(ev["reset"]) == 2 and set(ev["reset"]) == {0, 1}, ev)
    db2 = pickle.loads(pickle.dumps(db))
    a = [db.draw()[1][0]["pid"] for _ in range(50)]
    b = [db2.draw()[1][0]["pid"] for _ in range(50)]
    check("islands_pickle_resume_identical", a == b)


def t_clusters() -> None:
    rng = np.random.default_rng(3)
    base = rng.integers(0, 150, size=(5, cluster.N_STATES)).astype(np.uint16)
    rows = []
    for b in range(5):
        for _ in range(20):
            v = base[b].copy()
            flip = rng.choice(cluster.N_STATES, 40, replace=False)  # 2% noise -> pairs agree >= 96%
            v[flip] = rng.integers(0, 150, size=40)
            rows.append(v)
    D = np.stack(rows)
    lab, n = cluster.complete_linkage(D)
    llab, leaders = cluster.leader(D)
    ok_pairs = True
    C = cluster.agree_counts(D)
    for c in range(n):
        m = np.nonzero(lab == c)[0]
        if len(m) > 1 and C[np.ix_(m, m)].min() < 0.95 * cluster.N_STATES:
            ok_pairs = False
    check("clusters_planted_complete", n == 5, n)
    check("clusters_planted_leader", len(leaders) == 5, len(leaders))
    check("clusters_within_pairs_ge_0.95", ok_pairs)
    err = np.full((2, cluster.N_STATES), cluster.ERR, dtype=np.uint16)
    check("clusters_err_never_agree", cluster.agreement(err[0], err[1]) == 0.0)


def main() -> None:
    from transformers import AutoTokenizer  # noqa: PLC0415
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8", revision="220b46e3b2180893580a4454f21f22d3ebb187d3")
    t_prompts(tok)
    t_dtb()
    t_islands()
    t_clusters()
    t_sandbox()
    (ROOT / "results" / "unit_tests.json").write_text(json.dumps(R, indent=1))
    n_fail = sum(not v["pass"] for v in R.values())
    print(f"{len(R) - n_fail}/{len(R)} passed")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
