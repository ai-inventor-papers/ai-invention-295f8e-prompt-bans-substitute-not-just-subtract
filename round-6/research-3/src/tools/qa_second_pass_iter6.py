"""Step 4 QA: independent second pass over every NEW quote (evidence/quotes_iter6.jsonl) with the aii-web-tools fetch_grep
CLI. For each quote a regex is built from up to 7 consecutive word tokens of its longest [...]-segment (tokens joined by
[\\W_]{1,8} so line breaks, hyphenation remnants, markdown emphasis and curly quotes cannot break the match); the skill's
`aii_fast_web_fetch.py grep` re-fetches the LIVE url and must report >= 1 match. Three windows (middle, start, end) are tried.
Writes evidence/qa_second_pass_iter6.jsonl. Usage: python -I tools/qa_second_pass_iter6.py"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EVID, SKILL_PY, SKILL_SCRIPTS, now_utc  # noqa: E402

PY = SKILL_PY
FETCH = str(SKILL_SCRIPTS / "aii_fast_web_fetch.py")


def patterns_for(quote: str) -> list:
    seg = max(re.split(r"\s*\[\.\.\.\]\s*", quote), key=len)
    toks = re.findall(r"[A-Za-z0-9]+", seg)
    n = len(toks)
    starts = [max(0, n // 2 - 3), 0, max(0, n - 7)]
    out = []
    for s0 in starts:
        pat = r"[\W_]{1,8}".join(re.escape(w) for w in toks[s0:s0 + 7])
        if pat and pat not in out:
            out.append(pat)
    return out


def check(rec):
    n, pat, err = 0, "", ""
    for pat in patterns_for(rec["quote"]):
        try:
            out = subprocess.run([PY, FETCH, "grep", "--url", rec["url"], "--pattern", pat, "-i", "--max-matches", "1",
                                  "--context-chars", "40"], capture_output=True, text=True, timeout=240).stdout
        except subprocess.TimeoutExpired:
            out, err = "", "timeout"
        m = re.search(r"\((\d+) matches in", out)
        n = int(m.group(1)) if m else 0
        if not m and "Error" in out:
            err = out.strip().splitlines()[0][:120] if out.strip() else "error"
        if n:
            break
    return {"qid": rec["qid"], "url": rec["url"], "pattern": pat, "match_count": n,
            "second_pass": "MATCH" if n > 0 else "NO-MATCH", "error": err, "checked_utc": now_utc()}


def main():
    recs = [json.loads(l) for l in (EVID / "quotes_iter6.jsonl").read_text().splitlines()]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(check, recs))
    out = EVID / "qa_second_pass_iter6.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
    ok = sum(r["second_pass"] == "MATCH" for r in res)
    print(f"second pass: {ok}/{len(res)} quotes re-matched live via fetch_grep")
    for r in res:
        if r["second_pass"] != "MATCH":
            print("NO-MATCH:", r["qid"], r["url"][:100], r["pattern"][:80], r["error"])


if __name__ == "__main__":
    main()
