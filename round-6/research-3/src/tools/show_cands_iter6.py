"""Print title, ids, dates, venue, engines and abstract of candidates by id or title fragment (manual screen helper).
Usage: python -I tools/show_cands_iter6.py ID_OR_TITLE_FRAGMENT [...]"""
import json
import sys
from pathlib import Path

EVID = Path(__file__).resolve().parents[1] / "evidence"
cands = [json.loads(l) for l in (EVID / "saturation_candidates_iter6.jsonl").read_text().splitlines()]
for q in sys.argv[1:]:
    ql = q.lower().removeprefix("or:")
    for c in cands:
        if ql in (c.get("arxiv_id") or "").lower() or ql == (c.get("openreview_id") or "").lower() or (len(ql) > 12 and ql in (c.get("title") or "").lower()):
            print(f"=== {c.get('arxiv_id') or 'OR:' + (c.get('openreview_id') or '')} | {c['title']}\n dates={c['dates']} venue={c['venue']} engines={c['engines']} fam={c['families']} cites={c['cites']}\n {c['abstract'][:1500]}\n")
