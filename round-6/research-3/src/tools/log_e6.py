"""Append E6 (grey literature, built-in WebSearch restricted to the protocol's domains) calls to evidence/search_log_iter6.jsonl.
Input: a JSON file of [{"query_id", "lane", "string", "top_urls": [...], "note"}]. The built-in tool's call time is recorded as the
logging time (calls were logged within minutes of being made). Usage: python3 -I tools/log_e6.py FILE"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "evidence" / "search_log_iter6.jsonl"
DOMAINS = ["transformer-circuits.pub", "lesswrong.com", "alignmentforum.org", "huggingface.co", "github.com", "neuronpedia.org", "substack.com"]
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with LOG.open("a", encoding="utf-8") as fh:
    for r in json.loads(Path(sys.argv[1]).read_text()):
        fh.write(json.dumps({"round": r.get("round", "R1"), "query_id": r["query_id"], "lane": r["lane"], "string": r["string"],
                             "engine": "E6 grey literature (built-in WebSearch, allowed_domains=" + ",".join(DOMAINS) + ")",
                             "n_results": len(r["top_urls"]), "status": "ok", "top20_ids": r["top_urls"][:20],
                             "note": r.get("note", ""), "timestamp_utc": now}, ensure_ascii=False) + "\n")
print("logged", len(json.loads(Path(sys.argv[1]).read_text())))
