# Internal research report, iteration 6 (gen_report_text)

This folder holds the run's internal research report after iteration 6: a chronological lab notebook of a study of
how an open-weight code model chooses which algorithm to write (BFS or DFS, Dijkstra or Bellman-Ford, and one
default per task on 13 further coding tasks), and which knobs change that choice. Iteration 6 appended its own
section (an engine control for the FP8 W8A8 plan-noise results, a bf16 exchange of ban states, a bf16 noise-site
rerun, Gemma Scope 2 features on Gemma's natural BFS-against-DFS split, a natural language autoencoder readout on
Qwen2.5-7B-Instruct, a positioning audit and a record audit), applied 29 audited corrections in place in earlier
sections, and rewrote the closing section.

## Layout

| Path | What it holds |
|-|-|
| `paper_draft.md` | The whole report: framing, one section per iteration (1 to 6), "What we have learned so far", numbered references [1] to [131]. Figures appear as `[FIGURE:fig_id]` markers whose specs travel with the pipeline output. |
| `references.bib`, `references.json` | BibTeX and fetch records for the 22 works cited for the first time in iteration 6 ([110] to [131]); written only by the Semantic Scholar fetch script (two batches). |
| `domain_terms.json` | The field's vocabulary (term, gloss, source title) that the final paper is checked against; iteration 6 added 29 terms. |
| `style_exemplars.md` | Verbatim passages from well-cited papers of the field, used for sentence register only, plus their section outlines. |
| `work/apply_corrections.py` | Applies the record audit's corrections (`corrections.json` of the iteration-6 record audit) to the report, with report-writer overrides where the same iteration's engine control supersedes the audit's engine wording. |
| `work/iter6_part1.md` ... `work/iter6_part4.md`, `work/closing.md` | First drafts of the iteration-6 section and the closing section, with table placeholders; later edits were made in `paper_draft.md` only. |
| `work/stageA_*.md`, `work/site_*.md`, `work/firth_*.md`, `work/gemma_sweep.md`, `work/table92e*.md` | Result tables converted from the experiment and research artifacts' own result files, with descriptive row labels. |
| `work/iter6_section.md` | The final iteration-6 section, extracted from `paper_draft.md`. |
| `work/figures.json` | The data-figure specifications of iteration 6 (four new figures and one corrected spec), with every plotted value taken unrounded from the artifacts' result files. |
| `work/paper_draft_before_iter6.md` | The report exactly as it stood at the start of this step, for diffing. |
| `work/paper_draft_before_termfix.md`, `work/changed_lines.txt`, `work/quote_spans.py` | The report before the terminology pass (bare codes and quoted spans in this iteration's text), the earlier-section lines this iteration changed, and the scan that lists close pairs of quote marks in that text. |
| `work/bibfetch.log`, `work/bibfetch2.log` | Output of the two bibliography fetches (20 of 22 found in the first, 2 of 2 in the second, from a final search with the report's own terms). |
| `work/references_before_iter6b.bib`, `work/references_before_iter6b.json` | The bibliography as it stood before the second fetch. |

## How to reproduce

The corrections and the assembly are deterministic given the artifact folders of iteration 6:

```bash
cp work/paper_draft_before_iter6.md paper_draft.md
python3 work/apply_corrections.py      # applies the 29 in-place corrections and three marked notes
```

The iteration-6 section, closing and references were then spliced in front of and in place of the old closing
section; the table placeholders in `work/iter6_part*.md` were filled from the `work/*.md` tables.

## Restoring removed files

Nothing is marked for deletion: `.aii/manifest.yaml` has no entries, because every file here is a small text file.
