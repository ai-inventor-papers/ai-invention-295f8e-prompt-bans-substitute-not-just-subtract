"""QA (plan step 5): independent second pass over every verified quote with the aii-web-tools fetch_grep CLI.

For each quote, a regex is built from a run of ~7 consecutive plain words of its longest [...]-segment (words joined by
[\\W_]{1,8} so PDF line breaks, hyphenation remnants and markdown emphasis cannot break the match); the skill's
`aii_fast_web_fetch.py grep` re-fetches the live URL and must report >= 1 match.
Writes evidence/qa_second_pass.jsonl. Usage: python -I tools/qa_second_pass.py
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, now_utc  # noqa: E402

PY = "/ai-inventor/.claude/skills/.ability_client_venv/bin/python"
FETCH = str(Path(__file__).resolve().parents[5] / "tools/aii-web-tools/scripts/aii_fast_web_fetch.py")
INDEX = {}
for line in (CACHE / "index.jsonl").read_text().splitlines():
    r = json.loads(line)
    INDEX[r["url"]] = r


def patterns_for(quote: str) -> list[str]:
    """Up to three windows of 7 consecutive word tokens (middle, start, end) of the longest [...]-segment."""
    seg = max(re.split(r"\s*\[\.\.\.\]\s*", quote), key=len)
    toks = re.findall(r"[A-Za-z0-9]+", seg)
    n = len(toks)
    starts = [max(0, n // 2 - 3), 0, max(0, n - 7)]
    out = []
    for s0 in starts:
        pat = r"[\W_]{1,8}".join(re.escape(w) for w in toks[s0:s0 + 7])
        if pat not in out:
            out.append(pat)
    return out


def check(rec):
    url = rec["url"]
    via = INDEX.get(url, {}).get("via")          # OpenReview notes are re-read through the public API
    target = via or url
    n, pat = 0, ""
    for pat in patterns_for(rec["quote"]):
        try:
            out = subprocess.run([PY, FETCH, "grep", "--url", target, "--pattern", pat, "-i", "-m", "1", "-C", "40"],
                                 capture_output=True, text=True, timeout=240).stdout
        except subprocess.TimeoutExpired:
            out = ""
        m = re.search(r"\((\d+) matches in", out)
        n = int(m.group(1)) if m else 0
        if n:
            break
    return {"ref_key": rec["ref_key"], "url": target, "pattern": pat, "match_count": n,
            "second_pass": "MATCH" if n > 0 else "NO-MATCH", "checked_utc": now_utc()}


def main():
    recs = [json.loads(l) for l in (EVID / "quotes.jsonl").read_text().splitlines()]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(check, recs))
    out = EVID / "qa_second_pass.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    ok = sum(r["second_pass"] == "MATCH" for r in res)
    print(f"second pass: {ok}/{len(res)} quotes re-matched live via fetch_grep")
    for r in res:
        if r["second_pass"] != "MATCH":
            print("NO-MATCH:", r["ref_key"], r["url"], r["pattern"][:80])


if __name__ == "__main__":
    main()
