#!/usr/bin/env python3
"""Short independent re-derivation of the headline numbers, standard library only, no code shared with src/ or
audit/rederive.py. It reads the rawest files on disk (per-sample label rows, per-event landing records, per-direction
escape cells, raw judge responses) and recomputes through its own code; every test is also run on placebo input,
where it must fail. Run: uv run python audit/headline_check.py  (AII_DEPS_ROOT as for eval.py)."""
import csv
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("AII_DEPS_ROOT", str(WS.parent)))
SIB = {"art_mWn-MQEnNelg": "round-4/experiment-19/src", "art_SHaWv77P1XCI": "round-4/experiment-22/src",
       "art_CcZLW-9NX00l": "round-5/experiment-24/src", "art_8WbrpoEFslk9": "round-5/experiment-25/src",
       "art_9a8LrIv2lHbV": "round-5/experiment-26/src", "art_jR6Pyy3W9xum": "round-5/experiment-27/src",
       "art_hG0QPiaIPNhP": "round-5/experiment-28/src"}
OUT = []


def art(aid):
    for c in (ROOT / aid, ROOT / SIB[aid].split("/")[-1], ROOT / SIB[aid]):
        if c.is_dir():
            return c
    raise FileNotFoundError(aid)


def jl(p):
    return json.loads(Path(p).read_text())


def report(name, value, expected, ok, placebo=None):
    OUT.append({"headline": name, "value": value, "expected": expected, "reproduced": bool(ok), "placebo": placebo})
    print(f"{'OK ' if ok else 'BAD'} {name}: {value} (expected {expected})" + (f" | placebo: {placebo}" if placebo else ""))


def fisher_p(a, n1, b, n2, tail):
    """Exact Fisher by enumerating the hypergeometric table; tail 'two' or 'less' (group 1 lower)."""
    k, n = a + b, n1 + n2
    pr = {x: math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k) for x in range(max(0, k - n2), min(k, n1) + 1)}
    if tail == "less":
        return sum(v for x, v in pr.items() if x <= a)
    return min(1.0, sum(v for v in pr.values() if v <= pr[a] * (1 + 1e-9)))


def pbin_tail(h, ps):
    d = [1.0]
    for p in ps:
        d = [(d[i] if i < len(d) else 0) * (1 - p) + (d[i - 1] * p if i else 0) for i in range(len(d) + 1)]
    return sum(d[h:])


def rank(v):
    s = sorted(v)
    first = {}
    for i, x in enumerate(s):
        first.setdefault(x, i)
    cnt = Counter(v)
    return [first[x] + (cnt[x] + 1) / 2 for x in v]


def rho(a, b):
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


# ----------------------------------------------------------------------------- H1 engine non-replication
def rows(path, tasks, arms):
    out = defaultdict(list)
    for line in open(path):
        r = json.loads(line)
        if r["task"] in tasks and r["arm"] in arms:
            out[(r["task"], r["arm"])].append((r["label"], r["passed"] is True))
    return out


bf = rows(art("art_jR6Pyy3W9xum") / "data/labels.jsonl", {"T10", "T2"}, {"TWIN", "PN_a1", "PN_a2"})
fp = rows(art("art_mWn-MQEnNelg") / "data/labels.jsonl", {"T10", "T2"}, {"PN_a1", "PN_a2"})
rng = random.Random(1)
for t, exp_p in (("T10", 7.2e-11), ("T2", 5.3e-05)):
    default = Counter(l for l, ok in bf[(t, "TWIN")] if ok).most_common(1)[0][0]
    cell = {}
    for eng, src in (("bf16", bf), ("fp8", fp)):
        for arm in ("PN_a1", "PN_a2"):
            cor = [l for l, ok in src[(t, arm)] if ok]
            cell[(eng, arm)] = (sum(l != default for l in cor), len(cor))
    (kb, nb), (kf, nf) = cell[("bf16", "PN_a2")], cell[("fp8", "PN_a2")]
    p2 = fisher_p(kb, nb, kf, nf, "two")
    kf1, nf1 = cell[("fp8", "PN_a1")]
    pbr = fisher_p(kb, nb, kf1, nf1, "less")
    # placebo: engine labels permuted over the pooled correct programs of the two alpha-2 cells
    pool = [1] * kb + [0] * (nb - kb) + [1] * kf + [0] * (nf - kf)
    sig = 0
    for _ in range(200):
        rng.shuffle(pool)
        sig += fisher_p(sum(pool[:nb]), nb, sum(pool[nb:]), nf, "two") < 0.01
    report(f"{t} bf16 vs FP8 at alpha 2 (correct programs off the default)", f"{kb}/{nb} vs {kf}/{nf}, Fisher p {p2:.2g}; "
           f"bracket {kb}/{nb} vs {kf1}/{nf1}, one-sided p {pbr:.3f}", f"p {exp_p}", abs(p2 - exp_p) <= 0.1 * exp_p,
           f"engine labels permuted: Fisher p < 0.01 in {sig}/200 (must be <= 10)")

# ----------------------------------------------------------------------------- H2 landing tally
pa = {u["unit_id"]: u for u in jl(art("art_8WbrpoEFslk9") / "pooled_inputs.json")["units"]}
pb = {u["unit_id"]: u for u in jl(art("art_9a8LrIv2lHbV") / "pooled_inputs.json")["records"]}
br = jl(art("art_CcZLW-9NX00l") / "results/base_repertoire.json")["per_task"]
scr = jl(art("art_CcZLW-9NX00l") / "results/screen_check.json")["r_t_vs_push_landing"]
esc = jl(art("art_SHaWv77P1XCI") / "results/escape.json")
ex = jl(art("art_8WbrpoEFslk9") / "results/extra_arm_a.json")
gem = jl(art("art_hG0QPiaIPNhP") / "results/e_a2.json")
gp = jl(art("art_hG0QPiaIPNhP") / "results/predictors.json")["units"]
ev = []  # (set, landing, runner-up, chance from the non-default catalogue size, twin wrote a correct alternative)
for t in ("T03", "T2", "T05", "T10", "T1"):
    ev.append(("screen", scr[t]["push_top1"], scr[t]["r_t"], 1 / len(br[t]["predicted_landing_composition"]), esc[t]["twin"]["k_off"] > 0))
for t in ("T03", "T10"):
    ev.append(("bf16", ex[t]["landing"], br[t]["r_t"], 1 / len(br[t]["predicted_landing_composition"]), bool(ex[t]["twin"]["landing_correct"])))
for e in jl(art("art_8WbrpoEFslk9") / "results/a2.json")["events"]:
    u = pa[e["unit"]]
    ev.append(("A", e["L"], u["base"]["r"], 1 / (len(u["catalogue"]) - 1),
               any(v for k, v in u["twin"]["comp_correct"].items() if k != u["default"])))
for e in jl(art("art_9a8LrIv2lHbV") / "results/a2_panel.json")["events"]:
    u = pb[e["unit"]]
    d = u["unit_facts"]["default"]
    ev.append(("B", e["push_landing"], u["base"]["r_u"], 1 / (len(u["unit_facts"]["catalogue"]) - 1),
               any(v for k, v in u["twin"]["correct_composition"].items() if k != d)))
for e in gem["events"]:
    g = gp[e["unit"]]
    ev.append(("G", e["landing"], g["r_u"], 1 / len(e["survivors"]),
               any(v for k, v in g["default"]["correct_counts"].items() if k != g["D"])))
hits = sum(L == r for _, L, r, _, _ in ev)
p_all = pbin_tail(hits, [c for *_, c, _ in ev])
unc = [(L == r, c) for s, L, r, c, tw in ev if s in ("A", "B", "G") and not tw]
hu = sum(h for h, _ in unc)
p_unc = pbin_tail(hu, [c for _, c in unc])
sig = 0
for _ in range(500):
    shuffled = []
    for s in ("screen", "bf16", "A", "B", "G"):
        sub = [x for x in ev if x[0] == s]
        Ls = [x[1] for x in sub]
        rng.shuffle(Ls)
        shuffled += [(L, x[2], x[3]) for L, x in zip(Ls, sub)]
    sig += pbin_tail(sum(L == r for L, r, _ in shuffled), [c for *_, c in shuffled]) < 0.001
report("landing tally (base runner-up = push landing)", f"{hits} of {len(ev)}, Poisson-binomial p {p_all:.2g}", "17 of 21, p 5.8e-07",
       hits == 17 and len(ev) == 21 and abs(p_all - 5.8e-07) < 0.1e-07 * 10, f"landings permuted within sets: p < 0.001 in {sig}/500")
report("unconfounded held-out subset", f"{hu} of {len(unc)}, p {p_unc:.3f}", "5 of 8, p 0.053", hu == 5 and len(unc) == 8 and abs(p_unc - 0.053) < 0.002)

# ----------------------------------------------------------------------------- H3 movability rho from compositions and cells
beta, E = [], []
for u in ("A1", "A2", "A3", "A4", "A5", "A7"):
    comp = pa[u]["base"]["chat"]["comp_correct"]
    n = sum(comp.values())
    beta.append((n - comp.get(pa[u]["default"], 0)) / n)
    cells = pa[u]["escape"]["cells"]
    E.append(sum(c["confirmed"] for c in cells) / len(cells))
beta_correct_only = beta[:]
for u in ("B1", "B2", "B3", "B4", "B5", "B6", "B7"):
    b = pb[u]["base"]
    d = pb[u]["unit_facts"]["default"]
    cc = b["correct_composition"]
    beta_correct_only.append((sum(cc.values()) - cc.get(d, 0)) / sum(cc.values()))
    # the panel's committed rule: attempts instead of correct programs when too few base programs are correct
    comp = b["attempted_composition"] if b["beta_source"] == "attempt" else cc
    n = sum(comp.values())
    beta.append((n - comp.get(d, 0)) / n)
    cells = pb[u]["outcomes"]["per_direction"]
    E.append(sum(bool(c["confirmed"]) for c in cells) / len(cells))
r = rho(beta, E)
same = 0
for _ in range(1000):
    bp = beta[:]
    rng.shuffle(bp)
    same += abs(rho(bp, E) - r) < 0.005
report("Spearman rho(beta, E), 13 new units, beta and E rebuilt from compositions and per-direction cells", f"{r:.3f}", "0.146",
       abs(r - 0.146) < 0.0015, f"beta permuted: rho reproduced in {same}/1000 permutations")
rc = rho(beta_correct_only, E)
report("Spearman rho, sensitivity with every unit's beta from correct programs", f"{rc:.3f}",
       "eval.py metric rho_beta_E_correct_only_basis", True)

# ----------------------------------------------------------------------------- H4 novelty from raw judge responses
items = {row["blind_id"]: row for row in csv.DictReader(open(WS / "tables/novelty_readjudication.csv"))}
last = {}
for line in open(WS / "audit/judge_cache.jsonl"):
    d = json.loads(line)
    model, bid, k, _ = d["key"].split("|")
    if (d.get("content") or "").strip():
        last[(model, bid, k)] = d["content"]  # later lines are later passes


def cls(text):
    m = re.search(r'"class"\s*:\s*"([A-Z_]+)"', text or "")
    return m.group(1) if m else "UNPARSED"


def mistral(bid):
    votes = Counter(cls(last.get(("mistralai/mistral-medium-3.1", bid, str(k)))) for k in range(3))
    return votes.most_common(1)[0][0]


core = [b for b, row in items.items() if row["kind"] == "disputed_14"]
ctrl = [b for b, row in items.items() if row["kind"].startswith("control")]
novel = [b for b in core if mistral(b) == "NOVEL_ALGORITHM"]
kimi_novel = [b for b in core if cls(last.get(("moonshotai/kimi-k2-0905", b, "0"))) == "NOVEL_ALGORITHM"]
gate = sum(mistral(b) == items[b]["truth"] for b in ctrl)
final = json.loads((WS / "audit/final_read.json").read_text())
final_novel = sum(v["final_class"] == "NOVEL_ALGORITHM" for v in final.values())
verdicts = [mistral(b) for b in ctrl]
passes = 0
for _ in range(1000):
    rng.shuffle(verdicts)
    passes += sum(v == items[b]["truth"] for v, b in zip(verdicts, ctrl)) >= 8
report("second adjudication, from raw judge responses", f"Mistral novel {len(novel)} of {len(core)} {novel}, Kimi novel "
       f"{len(kimi_novel)}, Mistral control gate {gate}/10, final count {final_novel}", "Mistral 1 (P13), Kimi 0, gate 9/10, final 0",
       len(novel) == 1 and not kimi_novel and gate == 9 and final_novel == 0,
       f"verdicts shuffled over the controls: gate passed in {passes}/1000 shuffles")

(WS / "audit" / "headline_check.json").write_text(json.dumps(OUT, indent=1))
print(f"{sum(o['reproduced'] for o in OUT)}/{len(OUT)} headline numbers reproduced")
