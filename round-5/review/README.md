# Review of the iteration-5 research record (review_report)

This workspace holds an adversarial audit of the run's internal research report after iteration 5
(the section "Iteration 5: the base model's repertoire against nudge movability ...", plus the in-place
corrections to iterations 3 and 4 and the rewritten closing section). The audit walks the seven
iteration-5 artifacts, recomputes the headline numbers from their own output files, checks that the
previous review's must-fix items were addressed, and checks coverage against the user's original request.

## Layout

| Path | What it is |
|---|---|
| `.terminal_claude_agent_struct_out.json` | The review in the pipeline's ReviewerFeedback schema (scores, strengths, critiques). |
| `checks/recompute_iter5.py` | Standard-library script that recomputes the numbers the review relies on from the artifacts' result files (read-only). |
| `checks/recompute_iter5.json` | Its output: pooled movability and landing statistics, the instruct-twin confound counts, FP8 against bf16 plan-noise shares at near-matched dose, the literal-cell phrasing counts, transplant McNemar counts, and the Llama knob cells missing from the record. |
| `.aii/manifest.yaml` | Heavy-path decisions (none: every file here is small text). |

## How to run

From this workspace, inside the run's directory tree (the script reads the sibling `iter_4/gen_art` and
`iter_5/gen_art` folders of the invention loop):

```bash
python3 -I checks/recompute_iter5.py            # or: python3 -I checks/recompute_iter5.py <path to 3_invention_loop>
```

It needs only the Python 3.12 standard library and finishes in a few seconds.

## Restoring removed files

Nothing in this workspace is marked for deletion, so nothing needs restoring.
