#!/usr/bin/env python3
"""Engine check (positive control, plan section 3): T03 x rand_9002 and T2 x rand_9004 at alpha 1 in exp17's own ban
unit, plus twins, on the exp17 slots (W1-W5 x k 0-9, uniforms u_stream(task, w, k)), compared slot by slot with
the exp17 rows (FP8 W8A8 engine on an RTX 2000 Ada; this artifact: bf16 on an RTX 4090).
Reported: per-slot code-sha and label agreement, compositions, pass rates, JS(ours, exp17) and its template-resampling
null (q95 over 1,000 resamples of exp17's five template groups). A bf16 difference is precision sensitivity and never
blocks the run; a gross failure (pass < 0.5 x exp17) would halt the run for a hook/sampler bug hunt.
Labels: T03 by the vendored bench labeller (runtime + AST); T2 by the vendored exp8 suite labeller; a runtime/AST
disagreement takes exp17's label when the program is byte-identical, else 'disputed'.
"""

from __future__ import annotations

import hashlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import RAW, RESULTS_DIR, VENDOR, read_jsonl, setup_logging, utc_now, write_json  # noqa: E402

ARMS = {"T03": ("SCR_d9002_a1.0", "RAND9002_a1.0"), "T2": ("SCR_d9004_a1.0", "RAND9004_a1.0")}


def sha(s: str | None) -> str:
    return hashlib.sha256((s or "").encode()).hexdigest()


def js(p: Counter, q: Counter) -> float:
    keys = sorted(set(p) | set(q))
    P = np.array([p.get(k, 0) for k in keys], float)
    Q = np.array([q.get(k, 0) for k in keys], float)
    P, Q = P / P.sum(), Q / Q.sum()
    M = (P + Q) / 2

    def kl(a, b):
        m = a > 0
        return float((a[m] * np.log(a[m] / b[m])).sum())
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def label_t03(rows):
    sys.path.insert(0, str(VENDOR / "exp11"))
    from bench.common.harness import extract_code
    from bench.common.labeling import label_one
    from bench.common.testgen import read_tests
    cases = read_tests(VENDOR / "exp11" / "bench" / "T03_kth_smallest" / "tests.jsonl")
    out = {}
    for r in rows:
        o = label_one({"sample_id": r["slot"], "task": "T03", "condition": "twin", "text": r["text"], "seed": 0}, cases)
        rt, al = o.get("runtime_label"), o.get("ast_label")
        out[(r["arm"], r["template"], r["slot"])] = {"code_sha": sha(extract_code(r["text"])), "passed": o["passed"],
                                                      "rt": rt, "ast": al}
    return out


def label_t2(rows):
    suite = VENDOR / "exp8" / "suite"
    sys.path.insert(0, str(suite))
    from labeller import ast_rules, runtime_rules
    from labeller.extract import extract_code
    from tasks.harness import evaluate_program
    out = {}
    for r in rows:
        code, _ = extract_code(r["text"])
        if not code:
            out[(r["arm"], r["template"], r["slot"])] = {"code_sha": None, "passed": False, "rt": "invalid",
                                                          "ast": "invalid"}
            continue
        ev = evaluate_program("t2", code)
        rl, _, _ = runtime_rules.label("t2", ev["probes"])
        al, _, _ = ast_rules.label(code, "t2")
        out[(r["arm"], r["template"], r["slot"])] = {"code_sha": sha(code), "passed": bool(ev["tests"].get("passed")),
                                                      "rt": rl, "ast": al}
    return out


def main() -> None:
    setup_logging("engine_check")
    mine = [r for r in read_jsonl(RAW) if r.get("engine_check")]
    e17 = [r for r in read_jsonl(VENDOR / "exp17" / "data" / "labels.jsonl") if r["task"] in ARMS]
    res = {"utc": utc_now(), "engine": "bf16_hf (RTX 4090)", "reference": "exp17 rows (FP8 W8A8, RTX 2000 Ada)"}
    for task, (my_arm, e_arm) in ARMS.items():
        rows = [r for r in mine if r["unit"] == task and r["slot"] < 10]
        lab = label_t03(rows) if task == "T03" else label_t2(rows)
        for mine_arm, ref_arm in ((my_arm, e_arm), ("TWIN", "NEUTRAL")):
            ref = {(r["template"], r["sample_id"]): r for r in e17 if r["task"] == task and r["arm"] == ref_arm
                   and r["sample_id"] < 10}
            agree_code = agree_lab = n = 0
            comp, comp_ref, passed, passed_ref = Counter(), Counter(), 0, 0
            for (arm, w, k), L in lab.items():
                if arm != mine_arm:
                    continue
                rr = ref.get((w, k))
                if rr is None:
                    continue
                n += 1
                same_code = L["code_sha"] is not None and L["code_sha"] == rr.get("code_sha256")
                L = {**L, "rt": None if L["rt"] == "unknown" else L["rt"], "ast": None if L["ast"] == "unknown"
                     else L["ast"]}
                if L["rt"] is not None and L["rt"] == L["ast"]:
                    lbl = L["rt"]
                elif L["rt"] in (None, "unknown") and L["ast"] not in (None, "unknown"):
                    lbl = L["ast"]
                elif L["ast"] in (None, "unknown") and L["rt"] not in (None, "unknown"):
                    lbl = L["rt"]
                else:
                    lbl = rr["label"] if same_code else "disputed"
                agree_code += same_code
                agree_lab += (lbl == rr["label"])
                comp[lbl] += 1
                comp_ref[rr["label"]] += 1
                passed += bool(L["passed"])
                passed_ref += bool(rr.get("passed"))
            groups = {}
            for (w, k), rr in ref.items():
                groups.setdefault(w, []).append(rr["label"])
            rng = np.random.default_rng(17)
            ws = sorted(groups)
            null = []
            for _ in range(1000):
                pick = rng.choice(ws, size=len(ws), replace=True)
                null.append(js(Counter(l for w in pick for l in groups[w]), comp_ref))
            compv = Counter({k: v for k, v in comp.items() if k not in ("disputed", "invalid")})
            J = js(compv, comp_ref) if n and compv else None
            q95 = float(np.quantile(null, 0.95))
            res[f"{task}|{mine_arm}"] = {"n_slots": n, "composition": dict(comp), "exp17_composition": dict(comp_ref),
                                         "per_slot_label_agreement": agree_lab / n if n else None,
                                         "per_slot_code_sha_agreement": agree_code / n if n else None,
                                         "pass": passed / n if n else None, "exp17_pass": passed_ref / n if n else None,
                                         "JS": J, "null_q95": q95,
                                         "reading": ("within template-resampling null" if J is not None and J <= q95
                                                     else "outside null (precision sensitivity, reported)"),
                                         "gross_failure": bool(n and passed / n < 0.5 * max(passed_ref / n, 1e-9))}
            logger.info(f"{task}|{mine_arm}: {res[f'{task}|{mine_arm}']}")
    write_json(RESULTS_DIR / "engine_check.json", res)


if __name__ == "__main__":
    main()
