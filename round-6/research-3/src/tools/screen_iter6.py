"""Screening of the iteration-6 saturation candidates (plan Step 2): date window, the per-lane keyword groups frozen in
evidence/protocol_iter6.json (LE, LL, LS, LK; three groups each) on title+abstract, and a closeness score per lane that
orders the manual title/abstract screen. Records seen by the iteration-4/5 audits are kept and RE-SCREENED against the
iteration-6 claims (those audits asked different questions).

Writes evidence/screening_iter6.jsonl (one line per unique candidate: window flag, groups matched per lane, best lane,
lane score, machine verdict 'prescreen-fail' when fewer than 2 groups match in every lane; manual verdicts are merged
in from evidence/manual_screen_iter6.json when present) and prints the top-N keyword-passing in-window records per lane.
Usage: python -I tools/screen_iter6.py [N_PER_LANE]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, append_jsonl  # noqa: E402

PROTO = json.loads((EVID / "protocol_iter6.json").read_text())
GROUPS = {lane: {g: re.compile(rx, re.I) for g, rx in grp.items()} for lane, grp in PROTO["prescreen_keyword_groups"].items()}
# closeness signals used only to ORDER the manual screen (never to exclude)
BONUS = {
    "LE": [re.compile(r"(quantiz|fp8|int8|w8a8|low.?precision|bf16|fp16).{0,120}(steer|patch|interven|ablat|noise inject|activation addition|sae)|"
                      r"(steer|patch|interven|ablat|activation addition|sae).{0,120}(quantiz|fp8|int8|w8a8|low.?precision|bf16|fp16)", re.I | re.S)],
    "LL": [re.compile(r"base (model|llm|lm)s?.{0,100}(rank|top-?k|top-?1|candidate|support|tail|revert|rebound|return)|"
                      r"(rank|top-?k|top-?1|candidate|support|revert|rebound|return).{0,100}base (model|llm|lm)", re.I | re.S),
           re.compile(r"predict|forecast|anticipat", re.I)],
    "LS": [re.compile(r"(fork|anchor|first token|pre-?generation|plan|prefill|prompt token|layer).{0,100}(perturb|noise|steer|patch|interven)|"
                      r"(perturb|noise|steer|patch|interven).{0,100}(fork|anchor|first token|pre-?generation|plan|prefill|prompt token|site)", re.I | re.S),
           re.compile(r"temperature|margin|entropy", re.I)],
    "LK": [re.compile(r"\bcode\b|program|algorithm", re.I),
           re.compile(r"base (model|llm)s?.{0,80}(aligned|instruct|chat|tuned)|(aligned|instruct|chat|tuned) (model|llm)s?.{0,80}base (model|llm)", re.I | re.S)],
}


def in_window(c):
    aid = c.get("arxiv_id") or ""
    if re.match(r"26(0[1-9]|1[0-2])\.", aid):
        return True
    if "E5" in c.get("engines", []):
        return True
    return any(str(d).startswith("2026") for d in c.get("dates", []))


def main():
    n_print = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    cands = [json.loads(l) for l in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines()]
    manual_path = EVID / "manual_screen_iter6.json"
    manual = json.loads(manual_path.read_text()) if manual_path.exists() else {}
    out = EVID / "screening_iter6.jsonl"
    out.write_text("")
    rows = []
    for c in cands:
        text = (c.get("title", "") + " " + c.get("abstract", "")).lower()
        lanes = {}
        for lane, grp in GROUPS.items():
            g = [name for name, rx in grp.items() if rx.search(text)]
            bonus = sum(bool(rx.search(text)) for rx in BONUS[lane])
            lanes[lane] = {"groups": g, "score": len(g) + bonus}
        best = max(lanes, key=lambda k: (len(lanes[k]["groups"]), lanes[k]["score"]))
        passes = [k for k, v in lanes.items() if len(v["groups"]) >= 2]
        win = in_window(c)
        ident = c.get("arxiv_id") or ("OR:" + c["openreview_id"] if c.get("openreview_id") else c["key"])
        rec = {"key": c["key"], "id": ident, "title": c.get("title"), "in_window": win,
               "lanes": lanes, "best_lane": best, "passes_lanes": passes,
               "families": c.get("families"), "engines": c.get("engines"), "cites": c.get("cites"),
               "seen_in_iter4": c.get("seen_in_iter4"), "seen_in_iter5": c.get("seen_in_iter5"),
               "has_abstract": bool(c.get("abstract"))}
        if not passes:
            rec["verdict"], rec["reason"] = "excluded", "prescreen-fail (<2 keyword groups in every lane)"
        elif not win:
            rec["verdict"], rec["reason"] = "out-of-window", "pre-2026 record: not counted; flag-axis check in scored_hits if relevant"
        else:
            rec["verdict"], rec["reason"] = "to-screen", "passes pre-screen in " + ",".join(passes)
        m = manual.get(c["key"]) or manual.get(ident)
        if m:
            rec["verdict"], rec["reason"] = m["verdict"], m["reason"]
            rec["manual"] = True
        append_jsonl(out, rec)
        rows.append(rec)
    w = [r for r in rows if r["in_window"]]
    kp = [r for r in w if r["passes_lanes"]]
    print(f"unique={len(rows)} in_window={len(w)} pass_prescreen_in_window={len(kp)} "
          f"prescreen_fail={sum(r['verdict'] == 'excluded' and not r.get('manual') for r in rows)} "
          f"seen_before_in_window={sum(bool(r['seen_in_iter4'] or r['seen_in_iter5']) for r in w)}")
    for lane in GROUPS:
        lr = sorted([r for r in kp if lane in r["passes_lanes"]], key=lambda r: -r["lanes"][lane]["score"])
        print(f"\n##### {lane}: {len(lr)} in-window records pass the {lane} pre-screen; top {n_print}:")
        for r in lr[:n_print]:
            seen = ("S4" if r["seen_in_iter4"] else "") + ("S5" if r["seen_in_iter5"] else "")
            print(f"{r['lanes'][lane]['score']}|{r['id']}|{','.join(r['engines'])}|{seen}|{(r['title'] or '')[:115]}")


if __name__ == "__main__":
    main()
