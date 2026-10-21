"""Screening of the iteration-5 saturation candidates (plan 2d-2e): date window, the four keyword groups frozen in
evidence/protocol.json (MODEL, OUTCOME, INTERVENTION, DOMAIN) on title+abstract, and a closeness score that orders the
manual title/abstract screen. Records already seen by the iteration-4 audit are kept and re-screened.

Writes evidence/screening_iter5.jsonl (window flag, matched groups, lane signals, score per candidate) and prints the
in-window, keyword-passing candidates ranked by score.
Usage: python -I tools/screen_iter5.py [N_TO_PRINT]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, append_jsonl  # noqa: E402

PROTO = json.loads((EVID / "protocol.json").read_text())
GROUPS = {k: re.compile(v, re.I) for k, v in PROTO["prescreen_keyword_groups"].items()}
# lane signals used only to order the manual screen (not to exclude anything)
LANE = {
    "base_vs_tuned": re.compile(r"base (model|llm|lm)s?\b.{0,80}(aligned|instruct|chat|post-?train|rlhf|rlvr|fine-?tun)|"
                                r"(aligned|instruct|chat|post-?trained|rlhf|rlvr|fine-?tuned) (model|llm)s?.{0,80}base (model|llm)", re.I | re.S),
    "transfer_into_tuned": re.compile(r"patch|transplant|interpolat|graft|splice|swap", re.I),
    "diversity": re.compile(r"divers|mode collapse|homogen|monocult|pass@k|creativ|sharpen", re.I),
    "prediction": re.compile(r"predict|forecast|anticipat|diagnos", re.I),
    "code_alg": re.compile(r"\bcode\b|program|algorithm", re.I),
}


def in_window(c):
    aid = c.get("arxiv_id") or ""
    if re.match(r"26(0[1-9]|1[0-2])\.", aid):
        return True
    if "E5" in c.get("engines", []):
        return True
    return any(str(d).startswith("2026") for d in c.get("dates", []))


def main():
    n_print = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    cands = [json.loads(l) for l in (EVID / "saturation_candidates_iter5.jsonl").read_text().splitlines()]
    out = EVID / "screening_iter5.jsonl"
    out.write_text("")
    rows = []
    for c in cands:
        text = (c.get("title", "") + " " + c.get("abstract", "")).lower()
        groups = [g for g, rx in GROUPS.items() if rx.search(text)]
        lanes = [k for k, rx in LANE.items() if rx.search(text)]
        win = in_window(c)
        score = len(groups) + 2 * ("base_vs_tuned" in lanes) + ("transfer_into_tuned" in lanes and "base_vs_tuned" in lanes) \
            + ("diversity" in lanes) + ("prediction" in lanes and "base_vs_tuned" in lanes)
        rec = {"key": c["key"], "arxiv_id": c.get("arxiv_id"), "openreview_id": c.get("openreview_id"),
               "title": c.get("title"), "in_window": win, "groups": groups, "lane_signals": lanes, "score": score,
               "families": c.get("families"), "engines": c.get("engines"), "cites": c.get("cites"),
               "seen_in_iter4": c.get("seen_in_iter4"), "keyword_pass": len(groups) >= 2,
               "has_abstract": bool(c.get("abstract"))}
        append_jsonl(out, rec)
        rows.append(rec)
    w = [r for r in rows if r["in_window"]]
    kp = [r for r in w if r["keyword_pass"]]
    print(f"unique={len(rows)} in_window={len(w)} keyword_pass_in_window(>=2 groups)={len(kp)} "
          f"seen_in_iter4_in_window={sum(bool(r['seen_in_iter4']) for r in w)}")
    for r in sorted(kp, key=lambda r: -r["score"])[:n_print]:
        ident = r["arxiv_id"] or ("OR:" + r["openreview_id"] if r["openreview_id"] else "-")
        print(f"{r['score']}|{ident}|{','.join(r['families'])}|{','.join(r['engines'])}|"
              f"{'S4' if r['seen_in_iter4'] else ''}|{(r['title'] or '')[:120]}")


if __name__ == "__main__":
    main()
