# Review of the iteration-4 research record (REVIEW_REPORT step)

This is an adversarial audit of the run's internal research report after iteration 4. The run studies algorithm choice
in open-weight code models: Qwen3-8B, Llama-3.1-8B-Instruct and gemma-3-4b-it, on two path-search tasks and a 12-task
bench. The audit asks four questions:

- Is every executed artifact written up?
- Does each headline number trace back to its raw files and recompute?
- Were the earlier sections changed only by marked corrections?
- Do the conclusions match the evidence?

## What was done

- **Chronology.** Diffed Sections 1 to 3 of the report against the iteration-3 draft. All 18 changed hunks are marked
  "Correction, iteration 4" or "Added in iteration 4".
- **Artifacts.** Walked the seven iteration-4 artifacts: the record audit, plan noise, site, same seed, plan subspace,
  held-out family and positioning. Recomputed their headline numbers from per-sample rows and result files. Every
  number checked matches the report.
- **Problems found in the new section.**
  - A held-out sensitivity is reported as inconclusive when it returned DISCONFIRMED.
  - The site and route-landing conclusions outrun Tables 127 and 143 to 146.
  - Some forecast comparisons are made over unmatched event sets.
  - Executed results are missing: plan noise on the plain prompt, a hull-search deviation, and the Llama knob
    verdict.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review: scores, strengths, critiques (structured output) |
| `verify_iter4.py` | Read-only script that recomputes every number the review cites from the artifacts' raw files |
| `verify_iter4.log` | Output of `verify_iter4.py`, the evidence behind the critiques |
| `build_review.py` | Writes `.terminal_claude_agent_struct_out.json` from the review text it contains |
| `.aii/manifest.yaml` | Disposable-output manifest (no heavy paths) |

## How to run

```bash
python3 verify_iter4.py > verify_iter4.log   # Python 3.10+, standard library only, about 1 s
python3 build_review.py                      # rewrites the review JSON
```

`verify_iter4.py` reads two sets of files in place and writes only to stdout:

- the artifact workspaces under `3_invention_loop/iter_4/gen_art/` of this run;
- the iteration-3 and iteration-4 report drafts under `gen_report_text/`.

## Restoring removed files

Nothing is marked `delete`. The workspace holds only small text files, so there is nothing to restore.
