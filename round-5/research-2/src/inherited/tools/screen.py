"""Screening of the saturation candidates (plan 3.6): date window, then a documented keyword pre-screen on
title+abstract, then a closeness score that orders the manual title/abstract screen.

Writes evidence/screening.jsonl (one line per unique candidate with window flag, matched groups, score) and prints the
in-window, keyword-passing candidates ranked by score for manual screening.
Usage: python -I tools/screen.py [N_TO_PRINT]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, append_jsonl  # noqa: E402

GROUPS = {
    "G1_activation_diversity": (r"steer|activation|hidden[- ]state|latent|residual|noise|perturb|inject|soft prompt|embedding",
                                r"divers|explor|pass@|creativ|novel|mode collapse|homogen"),
    "G2_compliance_prediction": (r"complian|instruction[- ]follow|constraint|negat|prohibit|refus|obey",
                                 r"predict|probe|steerab|hidden|internal|activation|represent|forecast"),
    "G3_plan_representation": (r"plan|algorithm|strateg|lookahead|look-ahead|future token|intent|decision",
                               r"probe|probing|hidden|represent|internal|latent|activation|decodab"),
    "G4_temperature_idea": (r"temperature|sampling|decoding", r"semantic|idea|intent|paraphras|surface|phrasing"),
    "G5_code_algorithm": (r"\bcode\b|program|coding", r"algorithm|monocult|mode collapse|divers|homogen"),
    "G6_negation": (r"negat|prohibit|\bdo not\b|forbid|negative constraint|negative instruction",
                    r"mechanism|attention|suppress|circuit|neuron|layer|represent"),
    "G7_novelty": (r"novel|discover|creativ|original", r"algorithm|\bcode\b|program"),
}
CODEALG = re.compile(r"\bcode\b|program|algorithm", re.I)
ACT = re.compile(r"steer|activation|hidden[- ]state|latent|residual stream|noise injection|perturb", re.I)


def in_window(c):
    aid = c.get("arxiv_id") or ""
    if aid[:2] == "26":
        return True
    if c.get("openreview_id") and any("ICLR 2027" in v for v in c.get("venue", [])):
        return True
    if "E5" in c.get("engines", []):
        return True
    return any(str(d).startswith("2026") for d in c.get("dates", []))


def main():
    n_print = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    cands = [json.loads(l) for l in (EVID / "saturation_candidates.jsonl").read_text().splitlines()]
    out = EVID / "screening.jsonl"
    out.write_text("")
    rows = []
    for c in cands:
        text = (c.get("title", "") + " " + c.get("abstract", "")).lower()
        groups = [g for g, (a, b) in GROUPS.items() if re.search(a, text) and re.search(b, text)]
        win = in_window(c)
        score = len(groups) + 2 * bool(CODEALG.search(text) and ACT.search(text)) + \
            (1 if "G2_compliance_prediction" in groups and re.search(r"steer|perturb", text) else 0)
        rec = {"key": c["key"], "arxiv_id": c.get("arxiv_id"), "openreview_id": c.get("openreview_id"),
               "title": c.get("title"), "in_window": win, "groups": groups, "score": score,
               "families": c.get("families"), "engines": c.get("engines"), "cites": c.get("cites"),
               "keyword_pass": bool(groups)}
        append_jsonl(out, rec)
        rows.append(rec)
    w = [r for r in rows if r["in_window"]]
    kp = [r for r in w if r["keyword_pass"]]
    print(f"unique={len(rows)} in_window={len(w)} keyword_pass_in_window={len(kp)}")
    for r in sorted(kp, key=lambda r: -r["score"])[:n_print]:
        ident = r["arxiv_id"] or ("OR:" + r["openreview_id"] if r["openreview_id"] else "-")
        print(f"{r['score']}|{ident}|{','.join(r['families'])}|{','.join(r['engines'])}|{(r['title'] or '')[:110]}")


if __name__ == "__main__":
    main()
