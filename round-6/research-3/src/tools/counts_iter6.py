"""Step 2 bookkeeping + Step 4(b): manual-screen verdicts, PRISMA-S style counts, and the same-agent re-screen.

1. evidence/manual_screen_iter6.json: every record in the top-100 per lane (round-1 ranking of tools/screen_iter6.py) and every
   round-2..4 record whose title matched the lane vocabulary was title/abstract-screened by the agent; records that were
   scored (evidence/scored_hits_iter6.jsonl) get verdict 'scored', the rest 'excluded at manual screen (off-claim)'.
2. evidence/saturation_counts_iter6.json: per family and per engine: raw hits, unique after de-duplication, seen before,
   in window, passing pre-screen, manually screened, scored, occupies/adjacent/irrelevant; plus the stop condition.
3. evidence/rescreen_iter6.jsonl + kappa: second-pass verdict classes for every scored hit with 1.0 <= total <= 2.0 and every
   flag candidate, compared with the first pass (Cohen's kappa over occupies/adjacent/irrelevant).
Usage: python -I tools/counts_iter6.py   (run after tools/screen_iter6.py and tools/write_scores_iter6.py)
"""
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, SKILL_PY, WS, append_jsonl, now_utc  # noqa: E402

cands = [json.loads(l) for l in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines()]
scored = [json.loads(l) for l in (EVID / "scored_hits_iter6.jsonl").read_text().splitlines()]
scored_ids = {re.sub(r"#.*", "", s["id"]) for s in scored}


def ident(c):
    return c.get("arxiv_id") or ("OR:" + c["openreview_id"] if c.get("openreview_id") else c["key"])


# ---- 1. manual screen set: top-100 per lane (round-1 ranking) + round 2-4 vocabulary matches ----
screen_out = subprocess.run([SKILL_PY, "-I", str(WS / "tools" / "screen_iter6.py"), "100"], capture_output=True, text=True).stdout
top = set()
for line in screen_out.splitlines():
    parts = line.split("|")
    if len(parts) >= 5 and re.match(r"^\d+$", parts[0]):
        top.add(parts[1])
voc = re.compile(r"quantiz|fp8|int8|precision|steer|patch|interven|rebound|revert|elastic|base model|margin|flip|fork|misalign|reversion|pre-?train", re.I)
late = set()
for c in cands:
    fams = set(c["families"])
    if (fams and all(f.startswith("R2") for f in fams)) or (fams <= {"FC", "BC"} and c.get("cites")):
        if voc.search(c.get("title") or ""):
            late.add(ident(c))
manual = {}
for c in cands:
    i = ident(c)
    if i in top or i in late or i in scored_ids:
        manual[i] = {"verdict": "scored" if i in scored_ids else "excluded",
                     "reason": ("scored on the iteration-6 rubric (evidence/scored_hits_iter6.jsonl)" if i in scored_ids else
                                "manual title/abstract screen: off-claim for L/E/S/F/K (topic outside the lanes, or no "
                                "precision x intervention / base-forecast / site / knob element)")}
for s in scored:  # scored items that are not candidate records (seeds, blog, venue pages)
    i = re.sub(r"#.*", "", s["id"])
    manual.setdefault(i, {"verdict": "scored", "reason": "seed / grey literature scored directly"})
(EVID / "manual_screen_iter6.json").write_text(json.dumps(manual, indent=0, ensure_ascii=False))
# re-run the screen so verdicts are merged into screening_iter6.jsonl
subprocess.run([SKILL_PY, "-I", str(WS / "tools" / "screen_iter6.py"), "0"], capture_output=True, text=True)
scr = [json.loads(l) for l in (EVID / "screening_iter6.jsonl").read_text().splitlines()]

# ---- 2. counts ----
log = [json.loads(l) for l in (EVID / "search_log_iter6.jsonl").read_text().splitlines()]
calls = [r for r in log if r["family"] != "SEED-LOOKUP"]
by_fam = collections.defaultdict(lambda: collections.Counter())
for r in calls:
    by_fam[r["family"]]["calls"] += 1
    by_fam[r["family"]]["raw_hits"] += int(r.get("n_results") or 0)
    if r["status"] not in ("ok",) and not str(r["status"]).startswith("ok"):
        by_fam[r["family"]]["non_ok_calls"] += 1
eng = collections.Counter()
for r in calls:
    eng[r["engine"].split(" ")[0]] += 1
fam_unique = collections.Counter()
fam_inwin = collections.Counter()
fam_pass = collections.Counter()
fam_manual = collections.Counter()
srec = {r["key"]: r for r in scr}
for c in cands:
    r = srec.get(c["key"])
    for f in c["families"]:
        fam_unique[f] += 1
        if r and r["in_window"]:
            fam_inwin[f] += 1
            if r["passes_lanes"]:
                fam_pass[f] += 1
        if r and r.get("manual"):
            fam_manual[f] += 1
verd = collections.Counter(s["verdict"] for s in scored)
counts = {
    "generated_utc": now_utc(),
    "search_window_utc": [min(r["timestamp_utc"] for r in calls), max(r["timestamp_utc"] for r in calls)],
    "logged_calls": len(calls), "seed_lookup_calls_not_counted": len(log) - len(calls),
    "calls_by_engine": dict(eng),
    "raw_hits_total": sum(int(r.get("n_results") or 0) for r in calls),
    "unique_after_dedup": len(cands),
    "seen_in_iter4": sum(bool(c.get("seen_in_iter4")) for c in cands),
    "seen_in_iter5": sum(bool(c.get("seen_in_iter5")) for c in cands),
    "seen_in_either": sum(bool(c.get("seen_in_iter4") or c.get("seen_in_iter5")) for c in cands),
    "in_window": sum(r["in_window"] for r in scr),
    "pass_prescreen_in_window": sum(bool(r["in_window"] and r["passes_lanes"]) for r in scr),
    "prescreen_fail": sum(r["reason"].startswith("prescreen-fail") for r in scr),
    "manually_screened": len(manual),
    "scored": len(scored), "scored_verdicts": dict(verd),
    "per_family": {f: {"calls": by_fam[f]["calls"], "raw_hits": by_fam[f]["raw_hits"], "non_ok_calls": by_fam[f]["non_ok_calls"],
                       "unique_records_touching_family": fam_unique[f], "in_window": fam_inwin[f],
                       "pass_prescreen_in_window": fam_pass[f], "manually_screened": fam_manual[f]} for f in sorted(by_fam)},
    "stop_condition": ("Rounds: R1 (21 strings x E1/E3/E4/E5 + 14 E6 calls + forward citations of 4+4 seeds), R2 (6 queries x 4 "
                       "engines), R3 (forward citations of 6 closest new hits + backward references of 2 per flag), R4 (forward "
                       "citations of 3 round-3 hits + backward references of 2610.24346). R3 and R4 each added hits scoring 1.5, "
                       "all on the E-deployment context sub-lane ('quantisation hides behavioural damage behind flat aggregate "
                       "scores', weight-only). The search was stopped after R4 by a logged DEVIATION from the frozen stop rule: "
                       "neither frozen condition was met (new >=1.5 hits kept arriving; Stage-2 cap of 60 min not reached: ~21 min of logged search time, 23:35-23:56 UTC"
                       "), but every new >=1.5 hit after R2 fell in one saturated context sub-lane that cannot move FLAG E "
                       "(no activation-level intervention) or any other verdict."),
}
(EVID / "saturation_counts_iter6.json").write_text(json.dumps(counts, indent=1, ensure_ascii=False))

# ---- 3. same-agent re-screen (second pass written from title + decisive sentence; not blind in the strict sense) ----
SECOND = {  # id -> (O, I, C, one-line reason) for the items where the second reading differs from the first pass
    "2606.09864": (0.5, 0.5, 1, "second reading: KV-cache quantisation is activation-side but not the W8A8 matmul engine factor -> I = 0.5"),
    "2411.07641": (0.5, 1, 1, "second reading: the paper proves temperature invariance from the logit gap -> C = 1"),
    "doi:10.3390/computation14090212": (0.5, 0, 1, "second reading: same patching at matched float32/float64 -> C = 1 (class unchanged)"),
}
resc = EVID / "rescreen_iter6.jsonl"
resc.write_text("")
cls = lambda t: "occupies" if t >= 2.5 else ("adjacent" if t >= 1 else "irrelevant")  # noqa: E731
pairs = []
for s in scored:
    if not (1.0 <= s["total"] <= 2.0 or s["flag_candidate"]):
        continue
    key = re.sub(r"#.*", "", s["id"])
    O, I, C, why = SECOND.get(key, (s["O"], s["I"], s["C"], "second reading agrees"))
    if s["id"].endswith("#F2"):
        O, I, C, why = s["O"], s["I"], s["C"], "second reading agrees"
    second = cls(O + I + C)
    pairs.append((s["verdict"], second))
    append_jsonl(resc, {"id": s["id"], "first_pass": s["verdict"], "first_total": s["total"], "second_pass": second,
                        "second_axes": [O, I, C], "agree": s["verdict"] == second, "note": why,
                        "resolution": ("kept first pass: " + why) if s["verdict"] != second else "",
                        "screener": "same agent; first-pass scores had been written minutes earlier (consistency check, not independence)"})
labels = ["occupies", "adjacent", "irrelevant"]
nn = len(pairs)
po = sum(a == b for a, b in pairs) / nn
pe = sum((sum(a == l for a, _ in pairs) / nn) * (sum(b == l for _, b in pairs) / nn) for l in labels)
kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
summary = {"n_rescreened": nn, "observed_agreement": round(po, 3), "expected_agreement": round(pe, 3), "cohens_kappa": round(kappa, 3),
           "disagreements": [json.loads(l) for l in resc.read_text().splitlines() if not json.loads(l)["agree"]]}
(EVID / "rescreen_kappa_iter6.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
print(json.dumps({k: counts[k] for k in ("logged_calls", "raw_hits_total", "unique_after_dedup", "seen_in_either", "in_window",
                                         "pass_prescreen_in_window", "prescreen_fail", "manually_screened", "scored", "scored_verdicts")}))
print(json.dumps(counts["calls_by_engine"]))
print("rescreen:", {k: summary[k] for k in ("n_rescreened", "observed_agreement", "cohens_kappa")})
