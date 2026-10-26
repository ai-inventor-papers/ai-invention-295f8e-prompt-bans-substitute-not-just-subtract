#!/usr/bin/env python3
"""(0f) Live re-verification of the six Table 92c positioning quotes.

arXiv: fetch https://arxiv.org/abs/<id> (and the HTML version), normalise whitespace, search for a 40-80 character
distinctive substring of each quote.  OpenReview: the api2 notes search used by the iteration-4 audit, then the forum
page; a browser challenge on both -> 'NOT RE-VERIFIED (OpenReview challenge)' and the quote is CARRIED from the
iteration-4 audit (art_kjrCpQnPaniY, as reported in iteration 4).  Hard cap 20 minutes; every request has a timeout.
Output: quotes/quotes_verified.json and tables/table92c.csv.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import urllib.parse
from datetime import date
from pathlib import Path

import requests
from loguru import logger

WS = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
CAP_S = 20 * 60
ROWS = [
    {"row": 1, "lane": "Plan noise", "kind": "arxiv", "id": "2608.21595", "version": "v1",
     "cite": "Jerge, Pelczar, Downes 2026, arXiv 2608.21595v1 (cs.CV, 21 Aug 2026)",
     "title": "Perturb the Thought, Not the Pixels: Latent-Space Rollout Diversification for Reinforcement Learning of "
              "Vision-Language Models",
     "quotes": ["We introduce Noise-Contrastive GRPO (NC-GRPO), which injects scale-calibrated Gaussian noise into the last "
                "hidden layer of the prompt-encoding pass for half of each rollout group, branching those rollouts from a "
                "displaced departure state."],
     "adds": "test-checked mechanism labels on code, a site comparison at matched dose (task-specification mid blocks vs "
             "read position vs generated tokens), seed coupling; theirs is VLM RL rollouts scored by reward",
     "relation": "partly occupied", "peer_reviewed": "no (arXiv preprint)"},
    {"row": 2, "lane": "Plan noise vs temperature", "kind": "arxiv", "id": "2504.15266", "version": "v4",
     "cite": "Nagarajan, Wu, Ding, Raghunathan, ICML 2025, arXiv 2504.15266v4 [80]", "title": "",
     "quotes": ["injecting noise at the input layer (dubbed seed-conditioning) works surprisingly as well as (and in some "
                "conditions, better than) temperature sampling from the output layer."],
     "adds": "nearest prior answer; adds task-specification-state noise against temperature with the token seed held "
             "fixed, on execution-checked algorithm labels", "relation": "adjacent", "peer_reviewed": "yes (ICML 2025)"},
    {"row": 3, "lane": "Novelty boundary", "kind": "arxiv", "id": "2608.30047", "version": "v1",
     "cite": "Bhushan, Zhang, Wang 2026, arXiv 2608.30047v1",
     "title": "Can LLM Agents Discover? Evaluating Creativity on ML Engineering Tasks",
     "quotes": ["Our findings reveal that current agents can explore novel regions of the solution space but lack the "
                "capacity to convert this novelty into improved task performance."],
     "adds": "scope: agents with iterative search on ML engineering vs single-sample generation without search; adds the "
             "no-novelty bound (0 among 14,206 correct programs; rule-of-three about 0.02%)",
     "relation": "contradicting in part", "peer_reviewed": "no (arXiv preprint)"},
    {"row": 4, "lane": "Novelty boundary", "kind": "arxiv", "id": "2610.02438", "version": "v1",
     "cite": "Maveli, Vergari, Cohen 2026, arXiv 2610.02438v1",
     "title": "Are you Synthesizing or Recalling? Evaluating LLMs on Algorithmic Code Retrieval",
     "quotes": ["code generation is better measured as parametric code retrieval: reproducing a named algorithm from "
                "internalised knowledge rather than synthesizing a novel one."],
     "adds": "execution-checked labels and the bound under activation pushes", "relation": "supporting",
     "peer_reviewed": "no (arXiv preprint)"},
    {"row": 5, "lane": "Novelty boundary / knob", "kind": "openreview", "id": "oag3wgNLRh", "version": "submission",
     "cite": "ICLR 2027 submission OpenReview oag3wgNLRh (anonymous, under review)",
     "title": "Rethinking Activation Steering for Mathematical Reasoning: What Actually Drives Its Reasoning Gains?",
     "quotes": ["they alter local decoder preferences and redirect generation among reasoning trajectories already "
                "supported by the model.",
                "ordinary stochastic decoding whose parameters are selected to match steering's aggregate departure from "
                "greedy decoding achieves comparable accuracy"],
     "adds": "adds algorithm-level labels; this run has NOT yet run departure-matched decoding (scheduled in the "
             "iteration-5 knob artifact)", "relation": "partly occupied", "peer_reviewed": "no (under review)"},
    {"row": 6, "lane": "Plan subspace", "kind": "openreview", "id": "knirOusGcq", "version": "submission",
     "cite": "ICLR 2027 submission OpenReview knirOusGcq (anonymous)",
     "title": "Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs",
     "quotes": ["We further establish its causal role by decomposing hidden-state interventions into components parallel "
                "and orthogonal to the learned subspace."],
     "adds": "adds a categorical, test-checked object; the forced-prompt subspace does not predict random-push effects "
             "(rho 0.03) and removing it keeps the effect (ratio 1.00)", "relation": "partly occupied",
     "peer_reviewed": "no (under review)"},
]


def norm(s: str) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("\ufb01", "fi").replace("-\n", "")
    s = re.sub(r"\\text(?:it|bf)\{([^}]*)\}", r"\1", s)  # LaTeX emphasis left in arXiv abstracts
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([:;,.])", r"\1", s)  # HTML renderings put a space before punctuation after <em> spans
    return s.lower()


def probe(q: str) -> str:
    """A 40-80 character distinctive substring from the middle of the quote."""
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) <= 80:
        return q
    mid = len(q) // 2
    return q[max(0, mid - 35): mid + 35].strip()


def get(url: str, t0: float) -> tuple[int, str]:
    if time.time() - t0 > CAP_S:
        return -1, "time cap"
    try:
        r = requests.get(url, headers=UA, timeout=30)
        return r.status_code, r.text
    except requests.RequestException as e:
        return -2, str(e)[:200]


def main() -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / "verify_quotes.log", rotation="30 MB", level="DEBUG")
    t0 = time.time()
    today = date.today().isoformat()
    out = []
    for row in ROWS:
        rec = {k: v for k, v in row.items() if k != "quotes"}
        rec["access_date"] = today
        texts, tried = [], []
        if row["kind"] == "arxiv":
            for url in (f"https://arxiv.org/abs/{row['id']}{row['version']}", f"https://arxiv.org/abs/{row['id']}",
                        f"https://arxiv.org/html/{row['id']}{row['version']}"):
                st, tx = get(url, t0)
                tried.append({"url": url, "status": st, "chars": len(tx)})
                if st == 200:
                    texts.append((url, tx))
        else:
            q = urllib.parse.quote(row["title"])
            for url in (f"https://api2.openreview.net/notes/search?term={q}&group=ICLR.cc/2027/Conference&limit=10",
                        f"https://api2.openreview.net/notes?forum={row['id']}",
                        f"https://openreview.net/forum?id={row['id']}"):
                st, tx = get(url, t0)
                challenge = st in (403, 429, 503) or "challenge" in tx.lower()[:5000] or "cf-chl" in tx[:5000]
                tried.append({"url": url, "status": st, "chars": len(tx), "challenge": challenge})
                if st == 200 and not challenge:
                    texts.append((url, tx))
        qres = []
        for qt in row["quotes"]:
            pb = probe(qt)
            hit = next((u for u, tx in texts if norm(pb) in norm(tx)), None)
            full = next((u for u, tx in texts if norm(qt).rstrip(".") in norm(tx)), None)
            qres.append({"quote": qt, "probe": pb, "probe_found_at": hit, "full_quote_found_at": full})
        if all(x["probe_found_at"] for x in qres):
            status, tag = "RE-VERIFIED", "RE-VERIFIED"
        elif row["kind"] == "openreview" and not texts:
            status = "NOT RE-VERIFIED (OpenReview challenge or no access); quote carried from art_kjrCpQnPaniY as reported in iteration 4"
            tag = "CARRIED"
        elif texts:
            status, tag = "PAGE REACHED, QUOTE NOT FOUND (abstract page may not hold the quote)", "CARRIED"
        else:
            status, tag = "NOT RE-VERIFIED (source unreachable)", "CARRIED"
        rec.update(quotes=qres, tried=tried, match_status=status, tag=tag,
                   url=(f"https://arxiv.org/abs/{row['id']}{row['version']}" if row["kind"] == "arxiv"
                        else f"https://openreview.net/forum?id={row['id']}"))
        logger.info(f"row {row['row']} {row['id']}: {status}")
        out.append(rec)
    (WS / "quotes").mkdir(exist_ok=True)
    (WS / "quotes" / "quotes_verified.json").write_text(json.dumps(out, indent=1))
    (WS / "tables").mkdir(exist_ok=True)
    with (WS / "tables" / "table92c.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "lane", "source", "url", "version", "access_date", "quote", "match_status", "tag", "adds",
                    "relation", "peer_reviewed"])
        for rec in out:
            w.writerow([rec["row"], rec["lane"], rec["cite"] + (f", '{rec['title']}'" if rec["title"] else ""),
                        rec["url"], rec["version"], rec["access_date"], " | ".join(q["quote"] for q in rec["quotes"]),
                        rec["match_status"], rec["tag"], rec["adds"], rec["relation"], rec["peer_reviewed"]])
    logger.info(f"quotes done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
