"""Step 4(a): independent live second pass over every iteration-6 quote with the aii-web-tools fetch_grep CLI.

For each quote, up to five regexes are built from runs of six consecutive plain word tokens spread across its longest
[...]-segment (tokens joined by [\\W_]{1,8} so line breaks, emphasis markup and JSON/markdown punctuation cannot break the
match); the skill's `aii_fast_web_fetch.py grep` re-fetches the live URL and must report >= 1 match for one of them.
Several windows are tried because API-JSON records escape newlines and non-ASCII characters (e.g. \\u00d7), which can
split a token. A quote that fails every window is NO-MATCH and is downgraded in the report.
Writes evidence/qa_second_pass_iter6.jsonl. Usage: python -I tools/qa_second_pass_iter6.py
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, SKILL_PY, SKILL_SCRIPTS, now_utc  # noqa: E402

FETCH = str(SKILL_SCRIPTS / "aii_fast_web_fetch.py")


def patterns_for(quote):
    seg = max(re.split(r"\s*\[\.\.\.\]\s*", quote), key=len)
    toks = re.findall(r"[A-Za-z0-9]+", seg)
    n = len(toks)
    w = min(6, n)
    starts = sorted({max(0, n // 2 - w // 2), 0, max(0, n - w), max(0, n // 4 - w // 2), max(0, (3 * n) // 4 - w // 2)},
                    key=lambda s: abs(s - (n // 2 - w // 2)))
    out = []
    for s0 in starts:
        pat = r"[\W_]{1,8}".join(re.escape(t) for t in toks[s0:s0 + w])
        if pat and pat not in out:
            out.append(pat)
    return out


def check(rec):
    n, pat, tries = 0, "", 0
    for pat in patterns_for(rec["quote"]):
        tries += 1
        try:
            out = subprocess.run([SKILL_PY, FETCH, "grep", "--url", rec["url"], "--pattern", pat, "-i", "-m", "1", "-C", "40"],
                                 capture_output=True, text=True, timeout=240).stdout
        except subprocess.TimeoutExpired:
            out = ""
        m = re.search(r"\((\d+) matches in", out)
        n = int(m.group(1)) if m else 0
        if n:
            break
    return {"row": rec["row"], "ref_key": rec["ref_key"], "url": rec["url"], "pattern": pat, "windows_tried": tries,
            "match_count": n, "second_pass": "MATCH" if n > 0 else "NO-MATCH", "checked_utc": now_utc()}


def main():
    recs = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(check, recs))
    (EVID / "qa_second_pass_iter6.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    ok = sum(r["second_pass"] == "MATCH" for r in res)
    print(f"second pass: {ok}/{len(res)} quotes re-matched live via fetch_grep")
    for r in res:
        if r["second_pass"] != "MATCH":
            print("NO-MATCH:", r["row"], r["ref_key"], r["url"][:100], r["pattern"][:80])


if __name__ == "__main__":
    main()
