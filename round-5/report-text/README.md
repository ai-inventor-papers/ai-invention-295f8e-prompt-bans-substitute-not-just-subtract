# Internal research report, iteration 5 (gen_report_text)

This workspace holds the run's internal research report: a chronological lab notebook of an
algorithm-choice study on open-weight code models (Qwen3-8B and Qwen3-8B-Base, Llama-3.1-8B-Instruct,
gemma-3-4b-it and gemma-3-4b-pt). The report asks what changes the algorithm a model writes for a coding
task (temperature, seeds, instructions, prompt prohibitions, token vetoes, activation edits, base-model
states, text-level plan samplers) and records every experiment of iterations 1 to 5 with its tables,
dead ends and corrections. This step appended the iteration-5 section, applied 35 marked in-place
corrections to the iteration-3 and iteration-4 sections requested by the review, rewrote the closing
section, and extended the bibliography to [109].

## Layout

| Path | What it is |
|---|---|
| `paper_draft.md` | The report: framing, one section per iteration (1 to 5), "What we have learned so far", numbered references [1] to [109]. Figure placeholders appear as `[FIGURE:id]` markers; their specs are emitted in the step's structured output. |
| `references.bib` | BibTeX for the outside work the iteration-5 section relies on, fetched by the Semantic Scholar script (39 entries; never hand-written). |
| `references.json` | The fetch record that accompanies `references.bib` (source database, ids, titles). |
| `style_exemplars.md` | Verbatim passages from best-cited papers in the field, used only as sentence-level style exemplars, plus their section outlines (carried from earlier iterations). |
| `domain_terms.json` | The field's vocabulary (202 terms with glosses and source titles) that the report's terminology is checked against. This iteration added 22 terms; the terminology pass then removed one that was the run's own name rather than the cited paper's (departure-matched decoding), replaced a paraphrased entry by the compound in its source title (template-controlled), and added the hyphenated compounds of eight cited titles (for example base-aligned, latent-space, per-problem). |
| `work/apply_corrections_iter5.py` | Applies the iteration-5 record corrections in place, each anchored on text that must occur exactly once and marked as an iteration-5 correction. |
| `work/names.py`, `work/make_tables.py`, `work/make_tables2.py` | Build the iteration-5 tables from the artifacts' own output files, with task codes replaced by task names. |
| `work/tables_part1.json`, `work/tables_part2.json` | The generated markdown tables. |
| `work/pooled_a1a2.py`, `work/pooled_a1a2.json` | The pooled view of the two confirmation panels (Table 205), computed for this report from the panels' result files. |
| `work/sec5_part1.md` to `work/sec5_part4.md`, `work/closing.md` | The prose of the iteration-5 section and of the rewritten closing section, with table placeholders. |
| `work/assemble.py` | Fills the placeholders, inserts the section before the closing section, replaces the closing section and appends references [87] to [109]. |
| `work/terminology_pass.py` | Runs after assembly. Renames, in the iteration-5 text only (the new section, the closing and the iteration-5 correction notes in earlier sections), every label code, quoted coinage and hyphenated coinage the terminology check flagged, using the field's name or a term defined once with *we call*; numbers, citations and markers are untouched. The prose files in `work/` keep the wording from before this pass. |
| `work/lint_vocab_local.py` | Runs the pipeline's own vocabulary lint on the draft and lists the flags introduced since `work/paper_draft_before_iter5.md` (0 after the pass; the 210 remaining flags are in the text of iterations 1 to 4). |
| `work/paper_draft_before_iter5.md` | The report as it stood before this step, kept so the in-place corrections can be diffed and re-applied. |
| `work/TODO.md` | The step's task list. |
| `.aii/manifest.yaml` | Heavy-path decisions: one entry, the Python bytecode cache `work/__pycache__/`, marked for deletion as regenerable; everything else is text and stays. |

## How it was produced

1. Read the seven iteration-5 artifacts (record audit, transplant experiment, two confirmation panels,
   knob experiment, Gemma experiment, positioning audit) from their output files.
2. Applied the review's corrections in place (`python3 work/apply_corrections_iter5.py`).
3. Generated the tables (`python3 work/make_tables.py && python3 work/make_tables2.py`) and the pooled view
   (`python3 work/pooled_a1a2.py`).
4. Assembled the report (`python3 work/assemble.py`).
5. Applied the terminology pass (`python3 work/terminology_pass.py`) and checked it with `python3 work/lint_vocab_local.py`.
6. Fetched BibTeX with `aii_semscholar_bib__fetch.py --out ./references.bib --refs '[...]'` (39 references,
   all found).

The scripts read the artifact folders of the run in place (`../<artifact folder>`, relative to
this workspace's parent), so they run only inside the run's directory tree.

## How to rebuild

```bash
cp work/paper_draft_before_iter5.md paper_draft.md
python3 work/apply_corrections_iter5.py
python3 work/make_tables.py > /dev/null && python3 work/make_tables2.py > /dev/null
python3 work/pooled_a1a2.py > /dev/null
python3 work/assemble.py
python3 work/terminology_pass.py
python3 work/lint_vocab_local.py   # expects: introduced 0, no codes
```

Only the Python standard library is needed.

## Restoring removed files

One path is marked for deletion in `.aii/manifest.yaml`: `work/__pycache__/`, the Python bytecode cache
(about 32 KB) written when `work/make_tables2.py` imports `work/make_tables.py` and `work/names.py`.
Nothing reads it; to bring it back, run from this workspace:

```bash
python3 work/make_tables2.py > /dev/null
```

The report, references, vocabulary, scripts and generated tables are text and are all kept.
