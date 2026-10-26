# Research report, iteration 7

This workspace holds the run's chronological research report after iteration 7, the scripts that built the
iteration-7 additions from the artifacts' own output files, and the bibliography entries fetched for them.

## What this iteration added to the report

- The record audit's 54 corrections to the iteration-6 record are applied in place, each marked
  "(iteration-7 correction)"; the corrected text is byte-identical to the audit's own corrected report.
- A new section, "Iteration 7", sits before the closing. It reports the seven artifacts of iteration 7 in full:
  the record audit, the DAS experiment, the fork experiment, the temperature experiment, the dose unit experiment,
  the evolutionary search experiment and the Gemma experiment (Tables 280 to 372, with 364b, 364c and 365b).
- The closing section, "What we have learned so far", is rewritten for the whole run.
- Five references are added to the numbered list ([132] to [136]).
- Thirteen figure specifications are written: six for the new section and seven for the activation-space
  geometry figures that the record audit placed in Sections 6.4, 6.5 and 6.6.

A second pass over the section, against the artifacts' result files, corrected these points before submission:
the statement that temperature above 1 never raised the minority share (in Gemma it rose from 0.34 to 0.46, as
predicted); a Spearman correlation of 0.87 that had been reported as an AUC; the denominator of the correct-only
Table 286 (correct programs, not directions); a rounded lower bound (1.82, not 1.83); three placeholder cells; and
missing results that the artifacts had executed (the fork experiment's token-map placebo and screen power, the
dose unit experiment's displacement, per-sample and reuse checks, the temperature experiment's post-hoc readings,
the Gemma DAS controls by rank and block, the Gemma edits toward DFS, and the Gemma deviation log).

A last check of the closing section against the section's own tables corrected six statements: the axis push at
four times the centroid distance gives 29 DFS and 1 BFS programs, not 30 DFS; low temperature collapses the output
on two of the four mixed units, not on all; the fork-margin correlation on connected components now carries its
token-map placebo; the difference-in-means edit that destroys programs is the one toward BFS; the minority shares of
the three mixed tasks are stated as the range of the twin's baseline samples; and the search counts name each
comparison arm. The closing also again carries the whole-run results on the noise site, the bf16 status of
earlier internal results, the route of a ban and the landing of a push. The geometry figure specifications now label
points with algorithm and template names instead of the artifacts' internal codes; every plotted number is unchanged.

A terminology pass (`work/vocab7.py`) then renamed every hyphenated compound in the text written this
iteration that the report step's vocabulary lint flags (149 in the section and closing before the pass, none
after). Standard terms take their field spelling (post hoc, log odds, log likelihood); ordinary compound modifiers
become plain words (a fork of a single token, cells of the top quartile); the run's own names are written out
(share off the default, DAS with permuted labels, DAS at the read position) or renamed and defined once at first
use: the *relative unit* is the ban-free unit of earlier sections, the *second choice* is their runner-up, the
*full state exchange* is the Stage A exchange of every state at the site, and the *catalogue screen* is the
out-of-catalogue screen. Earlier sections keep their words. Numbers, citations and markers are unchanged by the
pass; the only digit it drops is the "2" of a judge model's name, written "Kimi k2". The figure specifications
use the same names. What the lint still reports lies outside this iteration's text: compounds in earlier
sections, hyphenated reference titles and author names, and "FP8" in the title of reference [115].

## Layout

| Path | What it is |
|-|-|
| `paper_draft.md` | The report: iterations 1 to 7, the closing section and the references |
| `references.bib`, `references.json` | BibTeX entries fetched for this iteration's citations, with their fetch record |
| `domain_terms.json` | Field vocabulary with glosses and sources (eight terms added this iteration) |
| `style_exemplars.md` | Register exemplars the prose follows |
| `work/build7.py` | Reads the iteration-7 artifacts' result files and writes every generated table to `work/tables7.json` |
| `work/iter7_part1.md`, `work/iter7_part2.md`, `work/iter7_part3.md` | The section's prose, with `{{key}}` slots for the generated tables |
| `work/gemma_tables7.py` | Regenerates Tables 364b, 364c and 365b, which sit as static text in `work/iter7_part3.md` |
| `work/closing7.md` | The rewritten closing section |
| `work/assemble7.py` | Fills the slots, applies the terminology pass, inserts the section before the closing, replaces the closing and appends the new references |
| `work/vocab7.py` | The terminology pass: ordered renames applied to the section, the closing and the figure specs, sparing markers, code spans and `⟦guarded⟧` earlier names quoted in a definition |
| `work/figspecs7.py`, `work/figures7.json` | Figure specifications with every plotted value taken from the artifacts |
| `work/geom/gemma_geom.py`, `work/geom/nla_geom.py`, `work/geom/*.json` | Recomputed PCA coordinates for the iteration-6 geometry figures, from the cached activation states of those artifacts |
| `work/paper_draft_before_iter7.md` | The report as it stood before this iteration |
| `work/paper_draft_corrected.md` | The report after the 54 corrections and before the new section |
| `work/TODO.md`, `work/bibfetch.log` | Working notes and the bibliography fetch log |
| `.aii/manifest.yaml` | Keep or delete decisions for non-text paths (only `work/__pycache__/`, marked for deletion) |

## How to rebuild

The tables and the assembled report need only Python 3 and the standard library, plus read access to the
iteration-7 artifact directories named at the top of `work/build7.py`:

```bash
python3 work/build7.py        # artifact result files -> work/tables7.json
python3 work/assemble7.py     # work/paper_draft_corrected.md + section + closing -> paper_draft.md
python3 work/figspecs7.py     # -> work/figures7.json
python3 work/gemma_tables7.py # prints the three static Gemma tables for checking
```

The geometry coordinates need numpy, and the Gemma one also torch and scikit-learn; any environment with those
packages works:

```bash
python3 work/geom/nla_geom.py
<python with torch and scikit-learn> work/geom/gemma_geom.py
```

## Restoring removed files

`.aii/manifest.yaml` marks one path for deletion: `work/__pycache__/`, the Python bytecode cache of
`work/vocab7.py` and `work/assemble7.py`. No script needs it, and both build scripts now run with bytecode
writing switched off, so it is not recreated by a rebuild. To restore it exactly:

```bash
python3 -m compileall -q work/vocab7.py work/assemble7.py   # recreates work/__pycache__/
```

Every other file is text and stays in place.
