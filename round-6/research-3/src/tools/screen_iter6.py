"""Screening of the iteration-6 saturation candidates (plan Step 3a): date window, a documented keyword pre-screen on
title+abstract per lane (groups G1-G7 below), then a closeness score that orders the manual title/abstract screen.

Writes evidence/screening_iter6.jsonl (one line per unique candidate: window flag, matched groups, score) and prints the
in-window, keyword-passing candidates ranked by score. Usage: python3 -I tools/screen_iter6.py [N_TO_PRINT]
"""
import json
import re
import sys
from pathlib import Path

EVID = Path(__file__).resolve().parents[1] / "evidence"
GROUPS = {
    "G1_das_strategy": (r"distributed alignment search|\bDAS\b|interchange intervention|causal abstraction|causal variable",
                        r"strateg|algorithm|plan|\bcode\b|program|generat|steer"),
    "G2_plan_before_generation": (r"\bplan|lookahead|look-ahead|future token|before generation|pre-generation|response length|latent intent",
                                  r"probe|probing|hidden|represent|internal|latent|activation|subspace|causal"),
    "G3_controls": (r"illusion|alignment map|causal abstraction|interchange|activation patching|subspace patching|divergent represent",
                    r"random|baseline|illusion|non-linear|off-distribution|out-of-distribution|dormant|faithful|validity|expressiv"),
    "G4_verbaliser": (r"natural language autoencoder|verbali[sz]|latentqa|activation oracle|selfie|patchscope|decod\w* activations|explain\w* activations|self-interpret",
                      r"steer|control|edit|interven|explan|readout|read out"),
    "G5_sae_transcoder": (r"sparse autoencoder|\bSAEs?\b|transcoder|crosscoder|attribution graph|gemma scope",
                          r"steer|strateg|reason|\bcode\b|algorithm|difference-in-means|prompting|plan"),
    "G6_quantization": (r"quantiz|\bFP8\b|\bINT8\b|W8A8|\bbf16\b|bfloat16|low-precision|numerical precision|nondetermin|non-determin",
                        r"steer|patching|interpretab|sparse autoencoder|\bSAE|circuit|activation|reproducib|perturb"),
    "G7_resample_diversity": (r"latent|\bplan|intent|activation|hidden[- ]state|noise|perturb|resampl",
                              r"divers|explor|pass@|creativ|novel|mode collapse|homogen"),
}
CODEALG = re.compile(r"\bcode\b|program|algorithm", re.I)
CAUSAL = re.compile(r"distributed alignment search|interchange|steer|activation patching|causal intervention", re.I)
QUANT = re.compile(r"quantiz|\bFP8\b|\bINT8\b|W8A8", re.I)
INTERP = re.compile(r"steer|patching|sparse autoencoder|\bSAE|interpretab|circuit", re.I)
VERB = re.compile(r"natural language autoencoder|verbali[sz]|latentqa|activation oracle|selfie", re.I)
EDIT = re.compile(r"steer|edit|control", re.I)


def in_window(c):
    aid = c.get("arxiv_id") or ""
    if aid[:2] == "26":
        return True
    if "E5" in c.get("engines", []):
        return True
    return any(str(d).startswith("2026") for d in c.get("dates", []))


def main():
    n_print = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    cands = [json.loads(l) for l in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines()]
    out = EVID / "screening_iter6.jsonl"
    rows = []
    with out.open("w", encoding="utf-8") as fh:
        for c in cands:
            text = (c.get("title", "") + " " + c.get("abstract", ""))
            tl = text.lower()
            groups = [g for g, (a, b) in GROUPS.items() if re.search(a, tl, re.I) and re.search(b, tl, re.I)]
            score = (len(groups) + 2 * bool(CODEALG.search(text) and CAUSAL.search(text))
                     + 2 * bool(QUANT.search(text) and INTERP.search(text)) + 2 * bool(VERB.search(text) and EDIT.search(text)))
            rec = {"key": c["key"], "arxiv_id": c.get("arxiv_id"), "openreview_id": c.get("openreview_id"), "title": c.get("title"),
                   "in_window": in_window(c), "groups": groups, "score": score, "lanes": c.get("lanes"), "queries": c.get("queries"),
                   "engines": c.get("engines"), "cites": c.get("cites"), "keyword_pass": bool(groups)}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            rows.append(rec)
    w = [r for r in rows if r["in_window"]]
    kp = [r for r in w if r["keyword_pass"]]
    print(f"unique={len(rows)} in_window={len(w)} keyword_pass_in_window={len(kp)}")
    for r in sorted(kp, key=lambda r: -r["score"])[:n_print]:
        ident = r["arxiv_id"] or ("OR:" + r["openreview_id"] if r["openreview_id"] else "-")
        print(f"{r['score']}|{ident}|{','.join(r['lanes'])}|{','.join(r['engines'])}|{(r['title'] or '')[:105]}")


if __name__ == "__main__":
    main()
