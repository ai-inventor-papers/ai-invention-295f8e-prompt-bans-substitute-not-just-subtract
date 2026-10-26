"""Round 3 (stop rule fired: round 2 produced new hits scoring >= 1.5): forward citations and backward references
(Semantic Scholar) of the round-2 hits scoring >= 1.5. OpenReview-only submissions are resolved by exact title on Semantic
Scholar; unresolved ones are logged as such. Usage: python -I tools/round3_iter6.py"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sat_search_iter6 as S  # noqa: E402

S.F.init_web_fetch()
ARXIV = {"CausalSyntaxCircuits": "arXiv:2610.20683", "PRISM": "arXiv:2610.20808", "DecodeShare": "arXiv:2607.20469"}
TITLES = {"ConceptVectorsCoding": "Steering LLM Coding Behaviors with Concept Vectors",
          "RandomChoice": "Random Choice in Language Models: A Linear Choice State and Low-Rank Sampling Control"}
for name, ref in ARXIV.items():
    S.citers(ref, name, rnd="R3")
    time.sleep(1.2)
    S.references(ref, name, rnd="R3")
    time.sleep(1.2)
for name, title in TITLES.items():
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(title) + "&fields=title,externalIds&limit=5")
    js, status = S.s2_get(url)
    hits = [h for h in (js or {}).get("data", []) or [] if (h.get("title") or "").lower().strip() == title.lower()]
    S.log(f"R3-resolve-{name}", "snowball", title, "E4 Semantic Scholar title search (resolve OpenReview-only submission)",
          [{"title": h.get("title", "")} for h in hits], status, "R3", extra={"resolved": bool(hits)})
    if hits:
        S.citers(hits[0]["paperId"], name, rnd="R3")
        S.references(hits[0]["paperId"], name, rnd="R3")
    time.sleep(1.2)
S.aggregate()
