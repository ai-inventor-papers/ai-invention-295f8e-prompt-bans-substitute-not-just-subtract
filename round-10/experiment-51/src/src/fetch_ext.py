#!/usr/bin/env python3
"""Fetch external primary sources into ext/<source>/ (data only, never executed) and record provenance."""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "ext"

SOURCES = [
    ("funsearch", "google-deepmind/funsearch", "2a2c8641f8590ae17ad98e82435cb1781a917957", "bin_packing/bin_packing.ipynb"),
    ("eoh", "FeiLiu36/EoH", "472545785c936dcfc863d2bc0d6109cf23c7ce62", "docs/Results/Prob1_OnlineBinPacking/run1/population_generation_20.json"),
    ("eoh", "FeiLiu36/EoH", "472545785c936dcfc863d2bc0d6109cf23c7ce62", "docs/Results/Prob1_OnlineBinPacking/run2/population_generation_20.json"),
    ("eoh", "FeiLiu36/EoH", "472545785c936dcfc863d2bc0d6109cf23c7ce62", "docs/Results/Prob1_OnlineBinPacking/run3/population_generation_20.json"),
    ("reevo", "ai4co/reevo", "6dce18257da5e11db2d138e417a2fffc5c72d05f", "prompts/bpp_online/seed_func.txt"),
    ("reevo", "ai4co/reevo", "6dce18257da5e11db2d138e417a2fffc5c72d05f", "problems/bpp_online/readme.md"),
    ("reevo", "ai4co/reevo", "6dce18257da5e11db2d138e417a2fffc5c72d05f", "problems/bpp_online/eval.py"),
    ("hsevo", "datphamvn/HSEvo", "f3afffabc2b458fddf70a42a8678758039671297", "problems/bpp_online/gpt.py"),
    ("hsevo", "datphamvn/HSEvo", "f3afffabc2b458fddf70a42a8678758039671297", "baselines/reevo/prompts/bpp_online/seed_func.txt"),
    ("mctsahd", "zz1358m/MCTS-AHD-master", "ee9c4f424503c65a5fd2b899e6620ce86079fedb", "problems/bpp_online/gpt.py"),
    ("mctsahd", "zz1358m/MCTS-AHD-master", "ee9c4f424503c65a5fd2b899e6620ce86079fedb", "problems/bpp_online/eval.py"),
    ("llm4ad", "Optima-CityU/llm4ad", "ffb6acf64497be93932c98d25369352efd3865cf", "llm4ad/task/optimization/online_bin_packing/template.py"),
    ("llm4ad", "Optima-CityU/llm4ad", "ffb6acf64497be93932c98d25369352efd3865cf", "example/tasks/online_bin_packing/online_bin_packing_tutorial.ipynb"),
    ("llm4ad", "Optima-CityU/llm4ad", "ffb6acf64497be93932c98d25369352efd3865cf", "llm4ad/task/optimization/online_bin_packing/evaluation.py"),
]
URLS = [
    ("orlib", f"http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/binpack{i}.txt") for i in range(1, 5)
] + [("arxiv_2510.27353", "https://arxiv.org/html/2510.27353")]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research fetch)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> None:
    prov = []
    for src, repo, sha, path in SOURCES:
        url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
        out = EXT / src / path.replace("/", "__")
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            b = fetch(url)
            out.write_bytes(b)
            prov.append(dict(source=src, repo=repo, commit=sha, path=path, url=url, local=str(out.relative_to(ROOT)),
                             utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), sha256=hashlib.sha256(b).hexdigest(), bytes=len(b), status="ok"))
        except Exception as e:  # noqa: BLE001 - provenance records every failure
            prov.append(dict(source=src, repo=repo, commit=sha, path=path, url=url, status=f"error: {e!r}"))
    for src, url in URLS:
        name = url.rsplit("/", 1)[-1] or "index"
        if not name.endswith((".txt", ".html")):
            name += ".html"
        out = EXT / src / name
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            b = fetch(url)
            out.write_bytes(b)
            prov.append(dict(source=src, url=url, local=str(out.relative_to(ROOT)), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             sha256=hashlib.sha256(b).hexdigest(), bytes=len(b), status="ok"))
        except Exception as e:  # noqa: BLE001
            prov.append(dict(source=src, url=url, status=f"error: {e!r}"))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "ext_sources.json").write_text(json.dumps(prov, indent=1))
    for p in prov:
        print(p.get("status"), p.get("source"), p.get("path", p.get("url")), p.get("bytes"))


if __name__ == "__main__":
    sys.exit(main())
