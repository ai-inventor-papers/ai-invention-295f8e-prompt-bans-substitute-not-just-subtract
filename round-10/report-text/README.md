# Internal research report, iteration 10 (report-writing step)

This folder is the report-writing step of iteration 10, the last iteration of an AI Inventor run on algorithmic
diversity in open-weight code models: does a model asked for a path search always write the same algorithm, which
knobs change the algorithm rather than its wording, and can the model produce truly novel solutions?

The step did three things:

1. **Applied the record repair.** The iteration-10 record-repair artifact (`art_7KO_qYLRZxXL`) re-derived every number
   the blocking iteration-9 review questioned and wrote 27 verbatim edits marked "(iteration-10 correction)". Its input
   report was byte-identical to this step's starting `paper_draft.md` (sha256 `27545375…e4ff0e0`), so its corrected copy
   was adopted unchanged; every earlier `[ARTIFACT:id]` marker is carried through.
2. **Appended the iteration-10 section** (Sections 10.1 to 10.12): the record repair, two evaluator-guided program
   searches on online bin packing, the constructive TSP replication, prohibition on bin packing with an exact
   behavioural instrument, the discipline-by-container program map, and the weight-level localisation of the
   default at the fork token. Every table is typeset from the artifacts' output files, and each new artifact carries an
   `[ARTIFACT:id]` marker at its first mention.
3. **Rewrote the closing section** ("What we have learned so far") for the whole run and appended references [156] to
   [174].

## Layout

| Path | What it holds |
|-|-|
| `paper_draft.md` | The full internal report: iterations 1 to 10, the closing section and the numbered reference list |
| `figures/` | Charts for the new figure markers: `<id>_v<k>.png` and `.pdf` renders and `<id>_spec.json` chart specs; the highest-numbered render of each id is the one used |
| `figures/fig_s0_kcurves_v0.*`, `figures/fig_s0_placement_v0.*` | The two figures of the record repair, copied from that artifact's own renders (hand-written matplotlib in the artifact) |
| `references.bib`, `references.json` | BibTeX for the iteration-10 references and the fetch record of each entry, written by the bibliography fetch script |
| `domain_terms.json` | Field vocabulary with one-line glosses; iteration 10 added 24 bin-packing, TSP and statistics terms |
| `style_exemplars.md` | Sentence-level register exemplars written by an earlier iteration |
| `.terminal_claude_agent_struct_out.json` | Structured output of this step: title, abstract, the six figure specs and the run summary |
| `.aii/manifest.yaml` | Storage manifest with no entries: every file here is text or a small figure below the auto-keep floor, so none needs a keep or delete decision |

## How to rebuild the figures

Each figure with a spec is rendered deterministically by the `aii-data-fig-gen` skill's chart generator:

```bash
python <aii-data-fig-gen>/scripts/chart_gen.py --spec figures/fig_search_clusters_spec.json --out figures/fig_search_clusters_v1
python <aii-data-fig-gen>/scripts/chart_gen.py --spec figures/fig_bp_heldout_spec.json --out figures/fig_bp_heldout_v2
python <aii-data-fig-gen>/scripts/chart_gen.py --spec figures/fig_novr_kcurves_spec.json --out figures/fig_novr_kcurves_v1
python <aii-data-fig-gen>/scripts/chart_gen.py --spec figures/fig_basew_dose_spec.json --out figures/fig_basew_dose_v0
```

The two record-repair figures are rebuilt inside that artifact (`uv run eval.py figures`). The bibliography is rebuilt
by rerunning the `aii-semscholar-bib` fetch script with `--out ./references.bib` on the identifiers listed in
`references.json`.

## Kept artifacts

All files here are small text, JSON, PNG or PDF files (the folder is about 8 MB) and stay at these relative paths on
the run's volume and in the published repository. No file reaches 100 MB.

## Restoring removed files

Nothing in this folder is marked for deletion, so nothing needs restoring.
