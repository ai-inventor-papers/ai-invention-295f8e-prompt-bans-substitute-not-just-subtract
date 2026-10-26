# TODO (copied verbatim from the task; status tracked below)

TODO 1. Read and STRICTLY follow these skills: aii-paper-writing, aii-semscholar-bib, aii-web-tools.
TODO 2. REFERENCES: Cite only the outside work this iteration's section actually relies on — a dataset, a baseline, a method it reused. The report has no Related Work section; the paper step writes its own at the end of the run. Batch-fetch real BibTeX for those citations with the aii_semscholar_bib__fetch script and `--out ./references.bib`. Only a paper that script returns is cited: never hand-write an entry, and leave out one it cannot find.
TODO 3. STYLE EXEMPLARS: (file exists -> read it and skip the search; add missing domain terms only)
TODO 4. READ ARTIFACTS: read the 7 new artifacts' code, outputs, data; extract specifics; [ARTIFACT:id] markers.
TODO 5. WRITE THE SECTION: append Iteration 7 to ./paper_draft.md (why / what happened (all tables) / learned / next), figures, references at the end; rewrite closing section.
TODO 6. APPEND PASS (7 checks: nothing earlier rewritten, nothing summarised away, dead ends kept, reasoning there, closing current, summary current, it reads).
TODO 7. TERMINOLOGY SWEEP; ls paper_draft.md; emit structured JSON to ./.terminal_claude_agent_struct_out.json

## Status (second session, after the step restarted with paper_draft.md, domain_terms.json and style_exemplars.md restored)
- [x] 1 skills re-read (aii-paper-writing incl. REVISION_CHECKLIST.md, aii-semscholar-bib, aii-web-tools)
- [x] 2 references: the 13 entries fetched in the first session kept (references.bib, references.json); numbered refs [132]-[136]
- [x] 3 style exemplars read; 8 field terms re-added to domain_terms.json (296 terms)
- [x] 4 artifacts re-read against the section; tables rebuilt (byte-identical to the first session's tables7.json)
- [x] 5 report re-assembled from the audit's corrected report; second-pass fixes to the prose and three new Gemma tables
- [x] 6 append pass: earlier sections untouched apart from the audit's 54 marked corrections; 104 earlier artifact markers kept; closing current
- [x] 7 terminology sweep (no bare codes in prose; definitions for noising, attribution graph, forking token link); structured JSON written
- [x] manifest .aii/manifest.yaml (no heavy paths) + README.md

## Terminology check (pipeline bounce after submission)
- [x] Reproduced the step's lint exactly (aii_pipeline/utils/prose_lint.py, lint_vocabulary on paper_draft.md with domain_terms.json): FP8 + 482 coinages, 149 of them in the iteration-7 section and closing
- [x] work/vocab7.py renames them at assembly (field spelling, plain words, or a renamed run term defined at first use: relative unit, second choice, full state exchange, catalogue screen); earlier sections untouched
- [x] After the pass: 0 flagged compounds in the section and closing; the 391 left are in earlier sections or reference titles/authors; FP8 is the title of reference [115]
- [x] Numbers, citations and markers identical before and after the pass (only the "2" of the judge model name, now "Kimi k2"); lint_draft clean; figure captions and the abstract and summary lint clean
- [x] Structured output re-emitted
