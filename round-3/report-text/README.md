# Internal research report, iteration 3 (report-writing step)

This folder holds the run's internal research report after its third iteration: a chronological lab notebook of a study
of algorithm choice in open-weight code models (Qwen3-8B, with Llama-3.1-8B-Instruct as a second family). It asks which
knobs change the algorithm a model implements (temperature, seeds, instructions, prompt bans, token vetoes, activation
edits), where a prompt ban acts inside the model, and what replaces the banned default.

This step appended the iteration-3 section to the report, made marked factual corrections in the iteration-1 and
iteration-2 sections where the iteration-2 review and the iteration-3 record audit showed them wrong, rewrote the closing
summary, and extended the bibliography. Nothing here generates data; every number in the new section is read from the
output files of the seven iteration-3 artifacts and their dependencies.

## Layout

| Path | What it is |
|---|---|
| `paper_draft.md` | The full report: iterations 1 to 3, the closing section "What we have learned so far", and the numbered references. Figure markers `[FIGURE:id]` point to chart specs carried by the pipeline. |
| `references.bib`, `references.json` | BibTeX for every numbered reference, fetched by the Semantic Scholar tool (68 of 70 requested entries found; Holm 1979 and an Alignment Forum post were not retrievable and are not cited by number). |
| `style_exemplars.md` | Verbatim passages from five papers used as a sentence-level style reference, with their section outlines. |
| `domain_terms.json` | The field's vocabulary used to check the report's terminology (157 terms). |
| `work/` | Scripts and intermediate files of this step: the in-place correction script, table builders, sentence-splitting edits, the reference request list, and copies of the report before this step's edits. |

## How to rebuild

The report is plain markdown and needs no build. To regenerate the bibliography:

```bash
SKILL_DIR=../../tools/aii-semscholar-bib
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py \
  --out ./references.bib --refs "$(cat work/refs_input.json)"
```

The table builders in `work/` (`step0_tables.py`, `exposure_table.py`) read the artifact output files on the run volume
and print markdown tables; `corrections.py` and `readability.py` are the exact edits applied to `paper_draft.md`.

## Restoring removed files

Nothing in this folder is marked for deletion. All files are text and stay in place.
