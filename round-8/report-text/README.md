# Algorithm-choice study: research report after iteration 8

This repository holds the cumulative research report of a study of how open-weight instruction-tuned code models
choose an algorithm, and what moves that choice, together with the figures, references and vocabulary that the
iteration-8 section uses.

## What was done in this step

- Applied the 84 corrections of the iteration-8 record audit in place in the earlier sections of `paper_draft.md`,
  each marked "(iteration-8 correction)".
- Appended the iteration-8 section (8.1 to 8.11, Tables 373 to 416): why the iteration ran what it ran, every
  experiment and table in full (temperature at the fork, one DAS protocol for two model families, a circuit in
  Qwen3-8B, a prefill-matched test of Gemma's dial, a temperature law on held-out families, a top-five prohibition
  across ten configurations), comparisons across experiments, verdicts, dead ends and the leads for the next
  iteration.
- Rewrote the closing section "What we have learned so far" to reflect the evidence after eight iterations.
- Rendered seven data charts from the experiments' own numbers, fetched five new references ([137] to [141]) and
  added 25 terms to the vocabulary list.

## Layout

| path | what it is |
|---|---|
| `paper_draft.md` | The cumulative report. Iteration 8 follows iteration 7 and precedes the closing section and the References. |
| `figures/<id>_spec.json` | The JSON spec of each iteration-8 chart, holding every plotted number. |
| `figures/<id>_v<N>.png`, `figures/<id>_v<N>.pdf` | The rendered charts (one final render per id): `fig_forkdose_hill`, `fig_das_controls`, `fig_gemma_dial_2x2`, `fig_templaw_heldout`, `fig_circuit_dose`, `fig_ban_screen`, `fig_ban_pca_states`. |
| `references.bib`, `references.json` | BibTeX entries and fetch records of the five outside works first cited in iteration 8, written by the bibliography fetch script. |
| `domain_terms.json` | The field vocabulary list (term, gloss, source title). |
| `style_exemplars.md` | Style exemplars read before writing (unchanged). |
| `.aii/manifest.yaml` | Keep/delete decisions for large files; empty, because nothing here needs one. |

## How to run

Nothing here needs a GPU. Each chart is drawn deterministically from its spec with the aii-data-fig-gen skill, for
example:

```bash
python <aii-data-fig-gen skill>/scripts/chart_gen.py --spec figures/fig_forkdose_hill_spec.json --out figures/fig_forkdose_hill_v2
```

The same command with another id re-draws any chart; the PNG output is byte-identical. The bibliography entries come
from the aii-semscholar-bib fetch script run with `--out ./references.bib` on the arXiv ids 2403.14541, 2407.01082,
2506.01939, 2610.04967 and 2511.04638 (the min-p entry's year was set to 2025, its ICLR publication year).

The numbers in the iteration-8 section come from the result files of the seven iteration-8 artifacts, named in the
text by their `[ARTIFACT:id]` markers.

## Restoring removed files

No file in this repository is marked for deletion, so nothing needs restoring. If a rendered chart is lost, re-draw
it from its spec with the command above; the specs hold every number the charts show.
