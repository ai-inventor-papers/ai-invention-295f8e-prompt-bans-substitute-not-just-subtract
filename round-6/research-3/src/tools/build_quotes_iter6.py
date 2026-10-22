"""Step 2/4: check every NEW quote of tools/quotes_spec_iter6.py against the cached text of its own source (normalisation and
[...]-segment rule of tools/common.py), and write evidence/quotes_iter6.jsonl with status MATCH/MISMATCH per quote.
A quote that does not match is reported (and later fixed or downgraded to UNVERIFIABLE, carrying no number).
Usage: python -I tools/build_quotes_iter6.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, load_text, normalise, now_utc, quote_matches  # noqa: E402
from quotes_spec_iter6 import Q  # noqa: E402

INDEX = {}
for line in (CACHE / "index.jsonl").read_text().splitlines():
    r = json.loads(line)
    INDEX[r["key"]] = r


def main():
    out = EVID / "quotes_iter6.jsonl"
    n_ok = 0
    norm_cache = {}
    with out.open("w", encoding="utf-8") as fh:
        for q in Q:
            if q["key"] not in norm_cache:
                norm_cache[q["key"]] = normalise(load_text(q["key"]))
            ok = quote_matches(q["quote"], norm_cache[q["key"]])
            n_ok += ok
            rec = dict(q, check="MATCH" if ok else "MISMATCH", checked_utc=now_utc(),
                       retrieved_utc=INDEX.get(q["key"], {}).get("retrieved_utc"),
                       cached_from=INDEX.get(q["key"], {}).get("url"))
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if not ok:
                print("MISMATCH", q["qid"], q["key"], "|", q["quote"][:110])
    print(f"quotes: {n_ok}/{len(Q)} MATCH; refs: {len({q['ref'].split(' (')[0] for q in Q})}")


if __name__ == "__main__":
    main()
