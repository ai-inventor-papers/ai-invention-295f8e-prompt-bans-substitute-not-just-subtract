# Research report, iteration 2 (gen_report_text)

This folder holds the run's internal research report after its second iteration. The report is a chronological lab
notebook of a study of algorithm choice in instruction-tuned code models: which path search algorithm Qwen3-8B (and,
from iteration 2, Llama-3.1-8B-Instruct) writes, what a "do not use X" prompt does to that choice, and where in the
model the prohibition acts.

What this step did:

1. Applied 24 marked corrections to the iteration-1 section, each answering a point of the review of that section
   (per-draw substitute counts, the cumulative-ban verdict, the selection rule's event gate, seed results, geometry
   wording, the cause of the missing locus probe, label compositions of steering arms, preregistered verdict labels,
   GPU hours). Every correction is marked in the text with what changed and why.
2. Appended the iteration-2 section (Sections 2.1 to 2.12): why the iteration ran what it ran, the shared protocol and
   likelihood instrument, the full results of all seven iteration-2 artifacts (tables 38 to 78 and 72b are new),
   comparisons across them, what was established, ruled out and abandoned, and what the next iteration takes forward.
3. Rewrote the closing section "What we have learned so far" for the evidence as it now stands, and extended the
   reference list (references 39 to 57 are new).

## Layout

| Path | What it is |
|-|-|
| `paper_draft.md` | The report: framing, Iteration 1 (with marked corrections), Iteration 2, "What we have learned so far", References. Figure markers `[FIGURE:id]` and artifact markers `[ARTIFACT:id]` are resolved by later pipeline steps |
| `references.bib`, `references.json` | Bibliography fetched by the Semantic Scholar script (57 entries) and its fetch record |
| `style_exemplars.md` | Verbatim style exemplars and section outlines from five papers (written in iteration 1, reused) |
| `domain_terms.json` | The field's vocabulary used for the terminology sweep (143 terms; 31 added in this iteration) |
| `work/part1.md` to `work/part5.md`, `work/closing.md` | Source text of the iteration-2 section and closing section, with `{{BibKey}}` citation placeholders |
| `work/apply_corrections.py` | Applies the marked corrections to the iteration-1 text; aborts unless each target passage occurs exactly once |
| `work/assemble.py` | Numbers the citations and assembles `paper_draft.md` from the corrected iteration-1 text, the parts and the closing section |
| `work/paper_draft_before_iter2.md` | The report exactly as it stood after iteration 1 (for diffing) |
| `work/paper_draft_corrected_base.md` | The iteration-1 report with the corrections applied, the base that `assemble.py` builds on |
| `work/refs_request.json`, `work/bib_fetch.log` | The reference list sent to the fetch script and its log |
| `work/vocab_lint_local.py` | Runs the pipeline's vocabulary lint (its `prose_lint.py` module, passed by path) on the draft and lists every flagged term; the draft is clean under it |
| `work/term_fix.py` | The terminology fixes applied to the iteration-2 sources after the lint: verbatim prompts in code spans, templates named by order, compounds written without hyphens |
| `work/term_detect.py`, `work/term_detect2.py`, `work/lint_report.txt` | First-pass detectors of quoted phrases and codes, and the last lint report |
| `work/*.pre_termfix.*`, `work/domain_terms_prompt.json` | Sources as they stood before the terminology fixes, and the vocabulary the check was first run against |

## How to rebuild the report

```bash
cp work/paper_draft_before_iter2.md paper_draft.md
python3 work/apply_corrections.py          # marked corrections to iteration 1
cp paper_draft.md work/paper_draft_corrected_base.md
python3 work/assemble.py                   # appends iteration 2, the closing section and references 39-57
```

To re-run the vocabulary check: `python3 -I work/vocab_lint_local.py <path to prose_lint.py> paper_draft.md domain_terms.json references.bib`.

Both scripts use only the Python standard library and paths relative to this folder.

## Restoring removed files

`.aii/manifest.yaml` marks one path for deletion after the round; everything else is small text and is kept.

| Removed path | What it is | Restore with |
|-|-|-|
| `work/__pycache__/` | Python bytecode written when the scripts in `work/` load one another | `python3 -m compileall -q work` (it is also recreated automatically the next time the scripts run) |
