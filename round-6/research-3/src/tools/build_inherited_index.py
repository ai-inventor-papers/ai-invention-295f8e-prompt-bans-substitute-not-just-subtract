"""Step 0(b): index every inherited source of Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS).

For each source: artifact, table, source index, url, title, parsed arXiv id, year, number of supporting passages, and the
claim/row labels (first cell of every table line of the inherited answer that cites [n]). Inherited quotes are cited by id,
never re-fetched. Writes evidence/inherited_index.json and prints presence checks for the plan's named references.
Usage: python3 -I tools/build_inherited_index.py
"""
import json
import re
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
ARTS = {"art_kjrCpQnPaniY": "92b/92c", "art_ObxQOIlAM9MS": "92d"}


def cites_in(cell_text):
    out = set()
    for grp in re.findall(r"\[([0-9,\s]+)\]", cell_text):
        out |= {int(x) for x in re.findall(r"\d+", grp)}
    return out


def main():
    index = []
    for art, table in ARTS.items():
        d = json.loads((WS / "inherited" / art / "research_out.json").read_text())
        rows_by_src = {}
        for line in d["answer"].split("\n"):
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            label = cells[0][:80]
            for n in cites_in(line):
                rows_by_src.setdefault(n, []).append(label)
        for s in d["sources"]:
            m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", s["url"])
            index.append({"artifact": art, "table": table, "source_index": s["index"], "url": s["url"],
                          "title": s["title"], "arxiv_id": m.group(1) if m else "", "url_version": (m.group(2) or "") if m else "",
                          "year": s.get("year"), "n_passages": len(s.get("supporting_passages") or []),
                          "rows_citing": sorted(set(rows_by_src.get(s["index"], [])))[:12],
                          "cite_as": f"{art} {table} source [{s['index']}]"})
    (WS / "evidence" / "inherited_index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False))
    print(f"inherited sources indexed: {len(index)}")
    checks = {
        "Before the First Token": r"before the first token", "AJR": r"\bAJR\b|joint.*representation", "STARS": r"2601\.22010|STARS",
        "Noise Steering": r"noise steering|2604\.03380", "random embedding injection": r"2605\.11936|random embedding",
        "NC-GRPO": r"2608\.21595|NC-GRPO", "Emergent Response Planning": r"2502\.06258", "Where's the Plan": r"2605\.07984",
        "Brewing": r"2606\.17648", "Future Lens": r"future lens", "2404.00859": r"2404\.00859", "2606.10302": r"2606\.10302",
        "IFG": r"intent factored|\bIFG\b", "PlanSearch": r"plansearch|2409\.03733", "Gacha": r"gacha", "Peeperkorn": r"temperature.*creativ|peeperkorn|2405\.00492",
        "Forking Paths": r"forking", "PASTA": r"pasta|2605\.30526", "BACo": r"baco|base-aligned", "Zhou cross-patching": r"2605\.07284",
        "Verbalized Sampling": r"verbali[sz]ed sampling", "Manifold Steering": r"manifold steering", "Beneath the Diff": r"beneath the diff",
        "AdapT": r"adapt\b|2309\.02772", "ASTEER": r"2606\.11599|asteer", "Gumbel counterfactual": r"gumbel|counterfactual token",
        "Lee et al. 2503.00691": r"2503\.00691", "2603.18353 knowledge-action": r"2603\.18353", "2504.04635 steering off course": r"2504\.04635",
        # expected ABSENT
        "DAS 2303.02536": r"2303\.02536|distributed alignment search", "Boundless DAS 2305.08809": r"2305\.08809", "MIB 2504.13151": r"2504\.13151",
        "Sutter 2507.08802": r"2507\.08802", "Makelov 2311.17030": r"2311\.17030", "Wu reply 2401.12631": r"2401\.12631",
        "NLA": r"natural language autoencoder|transformer-circuits\.pub/2026/nla", "Gemma Scope 2": r"gemma scope 2|gemma-scope-2",
        "circuit-tracer": r"circuit-tracer", "AxBench 2501.17148": r"2501\.17148|axbench", "AxBench rebuttal 2605.31183": r"2605\.31183",
        "2609.06473": r"2609\.06473", "2604.19884": r"2604\.19884", "2609.01587": r"2609\.01587", "2606.03002": r"2606\.03002",
        "LatentQA 2412.08686": r"2412\.08686|latentqa", "SelfIE 2403.10949": r"2403\.10949|selfie", "Patchscopes 2401.06102": r"2401\.06102|patchscope",
        "SAE-Steering 2601.03595": r"2601\.03595", "Rahman 2603.23629": r"2603\.23629", "2506.09501": r"2506\.09501",
    }
    for name, rx in checks.items():
        hits = [f"{r['artifact'][4:9]}[{r['source_index']}]" for r in index
                if re.search(rx, (r["title"] + " " + r["url"]), re.I)]
        print(f"{name:32s} -> {', '.join(hits) if hits else 'ABSENT'}")


if __name__ == "__main__":
    main()
