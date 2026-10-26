"""Run the pipeline's vocabulary lint locally and list every flagged term with an example.

Loads the pipeline's prose_lint module by path (pure functions, no I/O) and applies it to the draft,
with the bibliography titles from references.bib and the vocabulary from a domain-terms JSON file.
Usage: python3 -I work/vocab_lint_local.py <prose_lint.py> paper_draft.md domain_terms.json [references.bib]
"""
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def load(path):
    spec = importlib.util.spec_from_file_location("prose_lint_local", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["prose_lint_local"] = mod
    spec.loader.exec_module(mod)
    return mod


def bib_titles(path):
    if not path or not Path(path).exists():
        return []
    txt = Path(path).read_text(encoding="utf-8")
    return [" ".join(m.group(1).replace("{", "").replace("}", "").split())
            for m in re.finditer(r"\btitle\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", txt)]


def main():
    lint = load(sys.argv[1])
    text = Path(sys.argv[2]).read_text(encoding="utf-8")
    terms = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
    titles = bib_titles(sys.argv[4] if len(sys.argv) > 4 else None)
    issues = lint.lint_vocabulary(text, terms, bib_titles=titles)
    print("lint_vocabulary:", "clean" if not issues else "")
    for issue in issues:
        print("  -", issue[:400])
    body = lint.strip_latex(text)
    known, blob = lint._known_vocabulary(terms, titles)
    codes = sorted(set(lint.BARE_CODE_RE.findall(body)))
    print("bare codes:", codes)
    hits = defaultdict(list)
    for sentence, window in lint._sentence_windows(body):
        cands = [(m, m) for m in lint.HYPHEN_COMPOUND_RE.findall(sentence)]
        cands += [(m, f'"{m}"') for m in lint.QUOTED_COINAGE_RE.findall(sentence)]
        for raw, shown in cands:
            key = lint._fold(raw)
            if " " not in key and "-" not in key:
                continue
            spaced = key.replace("-", " ")
            if key in lint._HYPHEN_ALLOW or {key, spaced} & known:
                continue
            if key in blob or spaced in blob:
                continue
            if lint._is_defined(window, key):
                continue
            hits[shown].append(sentence[:120].replace("\n", " "))
    print(f"flagged coinages: {len(hits)}")
    for shown, sents in sorted(hits.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(f"{len(sents):4d}  {shown}  ||  {sents[0]}")
    print("lint_draft:", lint.lint_draft(text) or "clean")


if __name__ == "__main__":
    main()
