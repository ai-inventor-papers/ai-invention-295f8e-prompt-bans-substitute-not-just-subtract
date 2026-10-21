"""Replace supporting passages that failed the live literal check (emphasis markup in the page text) with the longest
literal span of the same verified quote; each replacement is re-checked live and logged.
Usage: python -I tools/patch_passages_iter5.py"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, F, now_utc  # noqa: E402

REPL = {"https://arxiv.org/html/2608.11426v2": "We argue that output homogeneity is likely learned during the pretraining phase, and only",
        "https://arxiv.org/html/2607.20543v1": "where the base model contains rare correct trajectories that are recoverable by sampling but too sparse to reliably appear in finite RLVR rollout groups.",
        "https://arxiv.org/html/2510.01171v4": "we identify a fundamental, pervasive data-level driver:",
        "https://transformer-circuits.pub/2024/crosscoders/index.html": "finetuned models use similar mechanism as the base model from which they were trained",
        "https://arxiv.org/html/2504.13837v5": "elicit fundamentally new reasoning patterns"}


def main():
    F.init_web_fetch()
    src = json.loads((CACHE / "sources_iter5.json").read_text())
    pre = {s["index"]: s for s in json.loads((CACHE / "sources_iter5_prelive.json").read_text())}
    logs = []
    for s in src:
        p = REPL.get(s["url"])
        if not p or any(x["quote"] == p for x in s["supporting_passages"]):
            continue
        r = F._fetch_url(s["url"])
        ok = p in re.sub(r"\s+", " ", r.get("content", ""))
        logs.append({"index": s["index"], "url": s["url"], "passage": p, "literal_match": ok, "checked_utc": now_utc(),
                     "note": "shorter literal span of a verified quote (emphasis markup in the page text)"})
        if ok:
            loc = pre[s["index"]]["supporting_passages"][0]["locator"] if pre[s["index"]]["supporting_passages"] else ""
            s["supporting_passages"].append({"quote": p, "locator": f"literal span of verified quote; {loc}"})
    (CACHE / "sources_iter5.json").write_text(json.dumps(src, ensure_ascii=False, indent=1))
    with (EVID / "passages_live_check_iter5.jsonl").open("a", encoding="utf-8") as fh:
        for l in logs:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")
    print([(l["index"], l["literal_match"]) for l in logs], "passages:", sum(len(x["supporting_passages"]) for x in src))


if __name__ == "__main__":
    main()
