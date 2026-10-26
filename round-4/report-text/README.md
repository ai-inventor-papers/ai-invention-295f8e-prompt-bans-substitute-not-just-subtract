# Internal research report, iteration 4 (gen_report_text)

This workspace holds the run's internal research report: a chronological lab notebook of an
algorithm-choice study on open-weight code models (Qwen3-8B, Llama-3.1-8B-Instruct, gemma-3-4b-it).
The report asks what changes the algorithm a model writes for a coding task (temperature, seeds,
instructions, prompt prohibitions, token vetoes, activation edits) and records every experiment of
iterations 1 to 4 with its tables, dead ends and corrections. This step appended the iteration-4
section, made marked in-place corrections to the iteration-2 and iteration-3 sections requested by
the review, rewrote the closing section, and extended the bibliography.

## Layout

| Path | What it is |
|---|---|
| `paper_draft.md` | The report: framing, one section per iteration (1 to 4), "What we have learned so far", numbered references [1] to [86]. Figure placeholders appear as `[FIGURE:id]` markers; their specs are emitted in the step's structured output. |
| `references.bib` | BibTeX for the outside work the iteration-4 section relies on, fetched by the Semantic Scholar script (34 entries; never hand-written). |
| `references.json` | The fetch record that accompanies `references.bib` (source database, ids, titles). |
| `style_exemplars.md` | Verbatim passages from best-cited papers in the field, used only as sentence-level style exemplars, plus their section outlines. |
| `domain_terms.json` | The field's vocabulary (173 terms with glosses and source titles) that the report's terminology is checked against. |
| `.aii/manifest.yaml` | Heavy-path decisions (none needed: text only). |

## How it was produced

1. Read the seven iteration-4 artifacts (record audit, plan noise, site, same seed, plan subspace,
   held-out family experiments, and the positioning audit) from their output files and typeset
   their tables.
2. Applied the review's corrections in place, each marked "Correction, iteration 4" or
   "Added in iteration 4".
3. Appended the iteration-4 section before the closing section and rewrote the closing section.
4. Fetched BibTeX with
   `aii_semscholar_bib__fetch.py --out ./references.bib --refs '[...]'` (34 references, all found).

## How to rebuild

The report is a markdown file; there is nothing to run. To refetch the bibliography, rerun the
Semantic Scholar fetch script from the aii-semscholar-bib skill with the arXiv ids listed in
`references.json`.

## Restoring removed files

No file in this workspace is marked for deletion in `.aii/manifest.yaml`, so nothing needs to be
restored. All files are text and stay in place on the run's volume and in the published repository.
