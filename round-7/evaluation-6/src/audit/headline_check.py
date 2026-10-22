#!/usr/bin/env python3
"""Headline re-derivation (stdlib only, shares no code with eval.py, src/ or audit/rederive.py).

Every headline number quoted in README.md and the final summary is recomputed from the rawest file available through
a different code path (Counter over raw rows, span splicing instead of sequential replace, exact binomial sums with
fractions). Each statistical test is also run on a placebo input that must NOT reach p < 0.05.
Writes audit/headline_check.json.
"""

import json
import random
import re
from collections import Counter, defaultdict
from fractions import Fraction
from math import comb
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
IN = WS / "inputs"
rows_of = lambda p: [json.loads(l) for l in open(p) if l.strip()]
yes = lambda v: v is True or str(v).lower() == "true"
out = {"checks": [], "placebos": []}


def binom2(k, n, p0=Fraction(1, 2)):
    """Exact two-sided binomial p by summing every outcome no more likely than k (exact rational arithmetic)."""
    pmf = [comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(n + 1)]
    return float(sum(x for x in pmf if x <= pmf[k]))


def check(name, got, want):
    out["checks"].append({"name": name, "got": got, "want": want, "ok": got == want})


# 1. corrections: count each old_text by regex, apply by splicing spans, compare with report_corrected.md
rep = (IN / "report" / "current_report.md").read_text()
cs = json.loads((WS / "corrections.json").read_text())["corrections"]
spans = []
for c in cs:
    hits = [m.start() for m in re.finditer(re.escape(c["old_text"]), rep)]
    spans.append((hits[0] if len(hits) == 1 else -1, c))
ok_once = sum(s >= 0 for s, _ in spans)
pieces, cur = [], 0
for s, c in sorted(spans, key=lambda t: t[0]):
    end = s + len(c["old_text"])
    pieces.append(rep[cur:s] + (c["old_text"] + c["new_text"] if c["kind"] == "insert_after" else c["new_text"]))
    cur = end
spliced = "".join(pieces) + rep[cur:]
check("n_corrections", len(cs), 54)
check("old_text_found_exactly_once", ok_once, 54)
check("spliced_equals_report_corrected", spliced == (WS / "report_corrected.md").read_text(), True)
check("markers_in_corrected", spliced.count("(iteration-7 correction)"), 54)
bad = cs[0]["old_text"][:-3] + "@@@"
out["placebos"].append({"name": "perturbed old_text is found", "value": len(re.findall(re.escape(bad), rep)),
                        "fails_as_it_must": len(re.findall(re.escape(bad), rep)) == 0})

# 2. phrase lint, iteration-6 sections only (plain lower-case substring counts, not the regexes of the lint)
phr = ["post-hoc form survives", "measured in three models", "in all three the read position",
       "in all three models the read position", "essentially one direction", "post-hoc ordering of noise sites",
       "every fork edit breaks", "every edit at the fork lowered", "every edit toward the minority algorithm breaks"]
sec = lambda t: t[t.find("# Iteration 6:"): t.find("# References")].lower()
before = sum(sec(rep).count(p) for p in phr)
after = sum(sec(spliced).count(p) for p in phr)
check("phrase_flags_uncorrected_gt_0", before > 0, True)
check("phrase_flags_corrected", after, 0)

# 3. Stage A counts from the raw label rows (Counter over (task, arm, label is Y, passed))
sa = json.loads((IN / "art_rMlbrjVB1c__" / "results" / "stage_a.json").read_text())["tasks"]
Y = {t: v["Y"] for t, v in sa.items()}
lab = rows_of(IN / "art_rMlbrjVB1c__" / "data" / "labels.jsonl")
cnt = Counter((r["task"], r["arm"], r["label"] == Y.get(r["task"]), yes(r["passed"])) for r in lab if r["task"] in Y)
att = lambda t, a: cnt[(t, a, True, True)] + cnt[(t, a, True, False)]
cor = lambda t, a: cnt[(t, a, True, True)]
for (t, a), (wa, wc) in {("T2", "X_0-35"): (24, 21), ("T2", "X_12-23"): (18, 11), ("T03", "X_0-35"): (17, 16),
                         ("T1", "X_0-35"): (14, 3), ("T1", "COND"): (10, 7), ("T2", "FORCEDX_0-35"): (30, 30),
                         ("T10", "FORCEDX_0-35"): (28, 24)}.items():
    check(f"stageA_{t}_{a}", (att(t, a), cor(t, a)), (wa, wc))

# 4. post-hoc correct-Y McNemar, exchange 0-35 against the matched-norm random exchange, paired by crn_key
pairs = defaultdict(dict)
for r in lab:
    if r["arm"] in ("X_0-35", "MR_0-35"):
        pairs[r["task"]].setdefault(r["crn_key"], {})[r["arm"]] = int(r["label"] == Y[r["task"]] and yes(r["passed"]))
rng = random.Random(0)
for t, want in (("T2", (21, 0)), ("T03", (15, 2)), ("T10", (11, 0))):
    pr = [(v["X_0-35"], v["MR_0-35"]) for v in pairs[t].values() if len(v) == 2]
    b, c = sum(x > y for x, y in pr), sum(y > x for x, y in pr)
    check(f"mr_correctY_{t}", (b, c), want)
    out["checks"].append({"name": f"mr_correctY_{t}_p", "got": binom2(b, b + c), "ok": binom2(b, b + c) < 0.01})
    flip = [(y, x) if rng.random() < 0.5 else (x, y) for x, y in pr]  # placebo: swap arms at random within pairs
    fb, fc = sum(x > y for x, y in flip), sum(y > x for x, y in flip)
    out["placebos"].append({"name": f"mr_{t}_arms_swapped_at_random", "b_c": [fb, fc], "p": binom2(fb, fb + fc),
                            "fails_as_it_must": binom2(fb, fb + fc) >= 0.05})

# 5. NLA: one unit per sample from the raw judgements (votes counted per state with a Counter)
NL = IN / "art_dbUtqBjT0tPf"
c2 = json.loads((NL / "predictions" / "commit2_readout.json").read_text())["tasks"]
labs = {r["sample_id"]: r["label"] for r in rows_of(NL / "data" / "labels.jsonl")}
votes, txt = defaultdict(list), {}
for r in rows_of(NL / "data" / "judgements.jsonl"):
    if r["mode"] == "EXPL":
        if int(r["expl_id"].rsplit("#", 1)[1]) <= 3:
            votes[r["state_id"]].append(r["resolved"])
    else:
        txt[r["mode"] + "|" + r["text_id"]] = r["resolved"]
units = []
for s in rows_of(NL / "cache" / "states_index.jsonl"):
    if s["kind"] != "GEN" or not c2.get(s["task"], {}).get("regate_pass", True) or s["sample_id"] not in labs:
        continue
    real = labs[s["sample_id"]]
    tid = "|".join([s["task"], s["condition"], s.get("mode") or "-", s["template"], s["position"], str(s["slot"])])
    v = votes.get(s["state_id"], [])
    x = None if not v else int(v.count(real) >= (2 if len(v) > 1 else 1))
    y = None if txt.get("PREDICT|" + tid) is None else int(txt["PREDICT|" + tid] == real)
    units.append((s["sample_id"], int(s["position"][1:]), bool(s.get("mixed")), x, y, txt.get("NAME|" + tid)))
first_named = {}
for smp, g, _, _, _, nm in sorted(units, key=lambda u: u[1]):
    if nm not in (None, "none_named", "other", "unresolved"):
        first_named.setdefault(smp, g)
sel = [u for u in units if u[2] and u[1] < first_named.get(u[0], 99) and u[3] is not None and u[4] is not None]
check("nla_units_b_c", (len(sel), sum(u[3] > u[4] for u in sel), sum(u[4] > u[3] for u in sel)), (364, 20, 88))
firsts = {}
for u in sorted(sel, key=lambda u: u[1]):
    firsts.setdefault(u[0], u)
b1, c1 = sum(u[3] > u[4] for u in firsts.values()), sum(u[4] > u[3] for u in firsts.values())
check("nla_one_unit_per_sample", (len(firsts), b1, c1), (104, 0, 25))
out["checks"].append({"name": "nla_one_unit_p", "got": binom2(b1, b1 + c1), "ok": abs(binom2(b1, b1 + c1) - 5.96e-8) < 1e-9})
fl = [(u[4], u[3]) if rng.random() < 0.5 else (u[3], u[4]) for u in firsts.values()]
fb, fc = sum(x > y for x, y in fl), sum(y > x for x, y in fl)
out["placebos"].append({"name": "nla_one_unit_predictors_swapped_at_random", "b_c": [fb, fc], "p": binom2(fb, fb + fc),
                        "fails_as_it_must": binom2(fb, fb + fc) >= 0.05})

# 6. U6 exact binomial from the raw fork record; placebo: the null set to the observed share
u6 = json.loads((IN / "art_zNyBP6zieI5u" / "results" / "fork.json").read_text())["U6"]
k = round(u6["t0_bfs_share"] * u6["t0_n"])
p0 = Fraction(u6["s3_bfs_share"]).limit_denominator(10 ** 6)
check("u6_k_n", (k, u6["t0_n"]), (73, 192))
out["checks"].append({"name": "u6_p", "got": binom2(k, u6["t0_n"], p0), "ok": abs(binom2(k, u6["t0_n"], p0) - 0.0279) < 0.001})
pl = binom2(k, u6["t0_n"], Fraction(k, u6["t0_n"]))
out["placebos"].append({"name": "u6_null_at_observed_share", "p": pl, "fails_as_it_must": pl >= 0.05})

# 7. judges: majority classes and gates from the per-call class records; spend from the raw response cache
nov = json.loads((WS / "results" / "novelty.json").read_text())
ref = {it["blind_id"]: it["ref"] for it in nov["blind_items"]}
truth = {c["cid"]: c["truth"] for c in nov["controls"]}
calls = json.loads((WS / "audit" / "judge_runs_summary.json").read_text())["calls"]
merge = lambda c: "CAT" if c in ("LABELLER_MISS", "CATALOGUE_VARIANT") else c


def gate(model, tr):
    n = 0
    for b, rs in calls[model].items():
        if ref[b] in tr:
            cl = Counter(r["class"] for r in rs if r["class"])
            top = cl.most_common(1)[0] if cl else (None, 0)
            maj = top[0] if top[1] >= 2 or sum(cl.values()) == 1 else None
            n += merge(maj) == merge(tr[ref[b]])
    return n


for m, want in (("deepseek/deepseek-chat-v3.1", 10), ("openai/gpt-4.1-mini", 8), ("google/gemini-2.5-flash-lite", 8)):
    check(f"gate_{m}", gate(m, truth), want)
shuf = list(truth.values())
random.Random(1).shuffle(shuf)
pg = gate("deepseek/deepseek-chat-v3.1", dict(zip(truth, shuf)))
out["placebos"].append({"name": "gate_with_control_truths_shuffled", "deepseek_correct": pg, "fails_as_it_must": pg < 9})
prog_calls = Counter(r["class"] for m in calls for b, rs in calls[m].items() if ref[b].startswith("P") for r in rs)
check("no_program_call_says_novel", prog_calls.get("NOVEL", 0), 0)
spend = sum(float(json.loads(l).get("cost") or 0) for l in open(WS / "audit" / "judge_cache.jsonl") if l.strip())
check("openrouter_spend_usd_rounded", round(spend, 3), 0.077)

# 8. positioning: the four re-matched quotes have a live full-text match; the two abstract quotes are on the page
web = WS / "audit" / "web"
for a in ("2412.07961", "2508.18098", "2604.12493", "2609.18440"):
    m = re.search(r"\((\d+) matches in", (web / f"grephtml_{a}.txt").read_text())
    check(f"quote_live_match_{a}", bool(m and int(m.group(1)) >= 1), True)
pos = json.loads((WS / "positioning.json").read_text())["neighbours"]
norm = lambda s: re.sub(r"\s+", " ", s)
for k in ("forking_fast", "ma_rui"):
    a = pos[k]["arxiv"]
    check(f"abstract_quote_on_page_{a}", norm(pos[k]["quote"][:120]) in norm((web / f"abs_{a}.txt").read_text()), True)

out["n_checks"] = len(out["checks"])
out["n_failed"] = sum(not c["ok"] for c in out["checks"])
out["n_placebos"] = len(out["placebos"])
out["n_placebos_failing"] = sum(p["fails_as_it_must"] for p in out["placebos"])
(WS / "audit" / "headline_check.json").write_text(json.dumps(out, indent=1))
print(f"headline check: {out['n_checks']} checks, {out['n_failed']} failed; "
      f"placebos failing {out['n_placebos_failing']}/{out['n_placebos']}")
for c in out["checks"]:
    if not c["ok"]:
        print("  FAILED", c)
for p in out["placebos"]:
    if not p["fails_as_it_must"]:
        print("  PLACEBO PASSED (bad)", p)
