# Prior work on base landings and 8-bit nudges (iteration-6 positioning audit, Table 92e)

This is a dated, quote-verified positioning and saturation audit of the iteration-6 claims of the AI Inventor run `run_aRfWvcSWjssb`:

- **L**: landing identity, i.e. whether a content-free nudge sends the tuned model to its base model's runner-up algorithm.
- **E**: whether an FP8 W8A8 engine explains the earlier plan-site sensitivity, tested with a 2x2 weight-by-activation precision factorial.
- **S/F**: the site of content-free nudges, forks and margins.
- **K**: diversity knobs (base intent, base/instruct interpolation, proxy tuning).

The audit extends Tables 92b/92c (art_kjrCpQnPaniY) and 92d (art_ObxQOIlAM9MS) and produces a paste-ready **Table 92e** plus two frozen flag verdicts:

- **FLAG E: PARTLY FIRED.** The closest full-text evidence is weight-only (Steering Under Compression) or joint weight+activation 8-bit quantisation of patching-based circuit discovery (PAHQ). Two contemporaneous ICLR 2027 submissions report, at abstract level, that steering effects are not preserved across precision; neither abstract says whether activations are quantised.
- **FLAG L: PARTLY FIRED.** Reversion of fine-tune-perturbed tuned models toward base behaviour is published at distribution or likelihood level (Re-Emergent Misalignment, Language Models Resist Alignment, Gravitational Interpretation of Safety Reversion). No work forecasts the landing identity from the base model and scores the forecast against the tuned model's own tail or likelihood.

Read `research_report.md` first. It holds the answer box, per-claim verdicts, permitted wording, reviewer baselines, Table 92e, PRISMA-S counts, corrections and follow-ups.

## Layout

| Path | What it is |
|---|---|
| `research_report.md` | The report: answer box, verdicts, permitted wording, Table 92e, counts, corrections, confidence, follow-ups |
| `reproducibility.md` | Every logged search call in order, every page fetched, verification steps and outcomes, deviations |
| `evidence/protocol_iter6.json` (+ `.sha256`, `protocol_amendments_iter6.jsonl`) | Frozen protocol (claims, 6 families / 21 strings, engines, rubric, flags, stop rule), written before the first search call |
| `evidence/search_log_iter6.jsonl` | One line per call (UTC, engine, family, query, params, status, n) |
| `evidence/saturation_candidates_iter6.jsonl` | 3,798 unique records (de-duplicated against both earlier audits; seen-before flags) |
| `evidence/screening_iter6.jsonl`, `evidence/manual_screen_iter6.json` | Window, keyword groups per lane, and machine/manual verdicts for every record |
| `evidence/scored_hits_iter6.jsonl`, `evidence/saturation_hits_iter6.jsonl` | 61 scored hits with O/I/C axes, totals, relation and decisive row |
| `evidence/flags_iter6.json` | FLAG E / FLAG L (and secondary S, K) definitions, verdicts, candidates, consequences for wording |
| `evidence/quotes_iter6.jsonl` | 84 new quote records (row, URL, section, version, v1 date, venue evidence, status) |
| `evidence/qa_second_pass_iter6.jsonl`, `evidence/passages_live_check_iter6.jsonl` | Live re-match of every quote (84/84) and literal check of every supporting passage (64/64) |
| `evidence/rescreen_iter6.jsonl`, `evidence/rescreen_kappa_iter6.json` | Same-agent re-screen and Cohen's kappa |
| `evidence/corrections_iter6.jsonl`, `evidence/saturation_counts_iter6.json`, `evidence/round2_queries_iter6.json` | Corrections log, PRISMA-S counts and stop condition, round-2 queries |
| `evidence/arxiv_meta.json` | arXiv API metadata (versions, v1 dates, authors, comments) for every arXiv id used |
| `inherited/` | Copies of the dependency audits' research_out/quotes/candidates (their `research_verification.json` copies are kept on the volume but not published, because they contain absolute dependency paths), `row_index.json` (key -> inherited rows), `citation_map.json` |
| `tools/` | All scripts (adapted from the iteration-5 audit's tools where noted in each docstring) |
| `cache/` | Fetched page texts used for verification, raw search-result lists, grep outputs, `sources_iter6.json`. Kept on the run volume; full paper texts are not published |
| `logs/` | Background-job logs and the grep spec files |

## How to run

Everything runs with the aii-web-tools interpreter (`PY=$(bash tools/skill_py.sh)`). Set `SEMANTIC_SCHOLAR_API_KEY` for the Semantic Scholar calls. The full ordered command list is in `reproducibility.md` section 6. Short version:

```bash
PY=$(bash tools/skill_py.sh)
$PY -I tools/sat_search_iter6.py                     # round 1 + forward citations
$PY -I tools/sat_search_iter6.py --round2 evidence/round2_queries_iter6.json
$PY -I tools/round3_citations_iter6.py && $PY -I tools/round4_citations_iter6.py
$PY -I tools/build_quotes_iter6.py && $PY -I tools/qa_second_pass_iter6.py
$PY -I tools/write_scores_iter6.py && $PY -I tools/counts_iter6.py
$PY -I tools/render_report_iter6.py && $PY -I tools/check_passages_live_iter6.py
```

Search results drift over time, so re-runs reproduce the method and the verified quotes but not the exact counts.

## Kept artifacts

`cache/` (about 16 MB of text: fetched page texts, raw search results, grep outputs) is plain text, so it is kept automatically and needs no manifest entry. It stays on this run's storage volume at that relative path and is the exact corpus the quotes were verified against. The publish step excludes the full paper texts (`cache/*.txt`) and grep outputs from the public repository (see the upload ignore patterns); `cache/index.jsonl` lists every URL so the corpus can be re-fetched.

## Restoring removed files

Only one path is marked for deletion:

- `tools/__pycache__/` (Python bytecode). Restore it with `python3 -m compileall -q tools`, or simply by running any script in `tools/`.

To rebuild `cache/` if it is ever lost, re-fetch the pages listed in `cache/index.jsonl`:

```bash
PY=$(bash tools/skill_py.sh)
python3 -c "import json;[print(json.loads(l)['key'], json.loads(l)['url']) for l in open('cache/index.jsonl')]" | \
  while read k u; do $PY -I tools/fetch_texts.py --url "$k" "$u"; done
```

Live pages may have changed since retrieval (2026-10-21/22). The OpenReview PDFs and the mdpi.com page returned HTTP 403 at retrieval.
