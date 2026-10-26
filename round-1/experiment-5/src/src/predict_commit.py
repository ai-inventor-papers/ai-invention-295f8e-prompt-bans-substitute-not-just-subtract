"""PHASE P: hash-committed forecast of where the instruct model lands under the modal ban, made from the BASE model's
template-free distribution, BEFORE phase C is sampled.

p(s) = 0.98 * (0.95 * q(s) + 0.05 / |S|) for s in survivors S;  p(other) = 0.02.
q = base_tf:baseline label distribution over CORRECT samples restricted to S (fallbacks flagged).
Secondaries / references committed in the same file: base_chat version, base_tf all-samples version,
instruct_chat:baseline restricted to S (typicality), uniform over S.
  .venv/bin/python src/predict_commit.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BAN_COND, PRED, RUNS, SURVIVORS, WS, read_jsonl, setup_logging, sha256_file, utc_now  # noqa: E402


def dist_over(rows: list[dict], S: list[str], correct_only: bool) -> tuple[dict, int]:
    cnt = {s: 0 for s in S}
    for r in rows:
        if not r.get("parse_ok") or r.get("label") is None:
            continue
        if correct_only and not r.get("passed"):
            continue
        if r["label"] in cnt:
            cnt[r["label"]] += 1
    return cnt, sum(cnt.values())


def to_pred(cnt: dict, n: int, S: list[str]) -> dict:
    q = {s: (cnt[s] / n if n else 1.0 / len(S)) for s in S}
    p = {s: 0.98 * (0.95 * q[s] + 0.05 / len(S)) for s in S}
    p["other"] = 0.02
    return {"q": q, "p": p, "counts": cnt, "n": n, "top1": max(S, key=lambda s: (p[s], -S.index(s)))}


def main() -> None:
    setup_logging("predict_commit")
    out = {"created_utc": utc_now(), "rule": "p(s)=0.98*(0.95*q(s)+0.05/|S|), p(other)=0.02; q from base_tf:baseline correct samples restricted to S",
           "events": {}}
    src = {
        "base_tf_correct": ("labelled_base_tf__baseline.jsonl", True),
        "base_chat_correct": ("labelled_base_chat__baseline.jsonl", True),
        "base_tf_all": ("labelled_base_tf__baseline.jsonl", False),
        "instruct_chat_correct": ("labelled_instruct_chat__baseline.jsonl", True),
    }
    for task in ("t1", "t2"):
        S = SURVIVORS[task]
        ev = {"event": f"{task} {BAN_COND[task]}", "survivors": S, "predictors": {}, "flags": []}
        for name, (fname, corr) in src.items():
            rows = [r for r in read_jsonl(RUNS / fname) if r["task"] == task]
            cnt, n = dist_over(rows, S, corr)
            if name == "base_tf_correct" and n == 0:
                ev["flags"].append("primary: no correct base_tf samples in S; used all parseable labelled samples")
                cnt, n = dist_over(rows, S, False)
                if n == 0:
                    ev["flags"].append("primary: no labelled base_tf samples in S; uniform")
            ev["predictors"][name] = to_pred(cnt, n, S)
        ev["predictors"]["uniform"] = to_pred({s: 0 for s in S}, 0, S)
        rows_tf = [r for r in read_jsonl(RUNS / "labelled_base_tf__baseline.jsonl") if r["task"] == task]
        n_corr = sum(bool(r.get("passed")) for r in rows_tf)
        ev["n_correct_base_tf"] = n_corr
        if n_corr < 40:
            # fallback 3 (pre-registered): fewer than 40 correct base_tf samples -> all-samples base distribution is primary
            ev["primary"] = "base_tf_all"
            ev["flags"].append(f"fallback-3: only {n_corr} correct base_tf samples (<40); primary = base_tf_all, "
                               "base_tf_correct kept as first secondary")
        else:
            ev["primary"] = "base_tf_correct"
        ev["top1_primary"] = ev["predictors"][ev["primary"]]["top1"]
        out["events"][task] = ev
        logger.info(f"{task}: primary={ev['primary']} p={ev['predictors'][ev['primary']]['p']} "
                    f"(n={ev['predictors'][ev['primary']]['n']}) top1={ev['top1_primary']} flags={ev['flags']}")
    f = PRED / "predict_modal_ban.json"
    f.write_text(json.dumps(out, indent=1, sort_keys=True))
    h = sha256_file(f)
    entry = {"utc_time": utc_now(), "file": "predictions/predict_modal_ban.json", "sha256": h}
    # git commit in a dedicated git dir (the workspace root is published as-is, so no nested .git at its root)
    gd = PRED / ".commit_git"
    env = {"GIT_DIR": str(gd), "GIT_WORK_TREE": str(WS), "GIT_AUTHOR_NAME": "aii", "GIT_AUTHOR_EMAIL": "aii@localhost",
           "GIT_COMMITTER_NAME": "aii", "GIT_COMMITTER_EMAIL": "aii@localhost", "PATH": "/usr/bin:/bin:/usr/local/bin"}
    try:
        if not gd.exists():
            subprocess.run(["git", "init", "-q"], env=env, check=True, cwd=WS)
        log = PRED / "hash_log.txt"
        with open(log, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        subprocess.run(["git", "add", "-f", "predictions/predict_modal_ban.json", "predictions/hash_log.txt"], env=env, check=True, cwd=WS)
        subprocess.run(["git", "commit", "-q", "-m", f"PREDICT commit {h[:12]}"], env=env, check=True, cwd=WS)
        rev = subprocess.run(["git", "rev-parse", "HEAD"], env=env, check=True, cwd=WS, capture_output=True, text=True).stdout.strip()
        (PRED / "git_commit.txt").write_text(rev + "\n")
        logger.info(f"committed {h} as git {rev}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"git commit failed: {e!r} (hash log still written)")


if __name__ == "__main__":
    main()
