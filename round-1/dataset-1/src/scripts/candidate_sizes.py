#!/usr/bin/env python3
"""Report repo size, downloads, licence and last-modified date for candidate HF datasets (used for the 300 MB screen)."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from huggingface_hub import HfApi

api = HfApi()


def info(repo: str) -> dict:
    try:
        d = api.dataset_info(repo, files_metadata=True)
        files = [(s.rfilename, s.size or 0) for s in d.siblings]
        total = sum(sz for _, sz in files)
        lic = next((t.split(":", 1)[1] for t in (d.tags or []) if t.startswith("license:")), "?")
        data_files = [f for f, _ in files if f.endswith((".parquet", ".json", ".jsonl", ".csv", ".arrow", ".zip", ".gz", ".tar"))]
        scripts = [f for f, _ in files if f.endswith(".py")]
        return {"repo": repo, "total_mb": round(total / 1e6, 1), "n_files": len(files), "downloads": d.downloads,
                "likes": d.likes, "license": lic, "last_modified": str(d.last_modified)[:10], "gated": d.gated,
                "n_data_files": len(data_files), "loader_scripts": scripts[:3]}
    except Exception as e:  # noqa: BLE001 - report any Hub error per repo instead of aborting the batch
        return {"repo": repo, "error": f"{type(e).__name__}: {str(e)[:150]}"}


def main() -> None:
    repos = [r.strip() for r in Path(sys.argv[1]).read_text().splitlines() if r.strip() and not r.startswith("#")]
    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(info, repos))
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1))
    for r in res:
        if "error" in r:
            print(f"{r['repo']:<45} ERROR {r['error']}")
        else:
            print(f"{r['repo']:<45} {r['total_mb']:>9.1f} MB dl={r['downloads']:<7} likes={r['likes']:<4} lic={r['license']:<14} mod={r['last_modified']} gated={r['gated']} scripts={r['loader_scripts']}")


if __name__ == "__main__":
    main()
