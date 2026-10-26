# Review of the iteration-2 research record (REVIEW_REPORT, iteration 2)

This directory is the audit of the run's internal research report after iteration 2. The study asks where a "do not use X" prompt sends Qwen3-8B (with a Llama-3.1-8B-Instruct replication) on two path-search coding tasks, and what else moves its choice of algorithm. The audit walked all 14 artifacts (7 from iteration 1, 7 from iteration 2), recomputed the headline numbers from the artifacts' own per-sample rows and result files, checked that the iteration-1 section changed only through marked corrections, checked coverage against the user's original request, and set the iteration-2 positive claims against their nearest published neighbours.

## Verdict

- Overall score 4 of 10 (confidence 4). Soundness 2, presentation 3, contribution 3. Coverage partial. Not blocking.
- All eleven must-fix items of the previous review were addressed, with corrections marked in place.
- 12 critiques (9 major), ranked by score impact:
  1. The likelihood-based substitution test (C1) is dominated by survivors with negligible mass and ESS near 1. On both modal-ban rows its X-specific residuals point away from the realised substitute: Bellman-Ford/SPFA gets -1.84 although 272 of 272 compliant programs are Bellman-Ford/SPFA.
  2. The record's two verdicts on the ladder are not reconciled.
  3. The ban-list artifact's 14 manifold figures, coloured by implemented count, are missing from the report, and the report calls that request item still open.
  4. Llama's grid "non-collapse" consists entirely of failing programs: its correct baseline programs are BFS 20 of 20.
  5. Samples, not variants, were the binding constraint, and the four frozen forecast families were never scored on any new event.
  6. The iteration-2 claims are not positioned against their neighbours: Heo et al. 2024 for compliance predictability at the last prompt token, and Kissane et al. 2024 for SAE base-to-chat transfer.
  7. The summary's "direct route none" overstates the evidence.
  8. Correct out-of-catalogue programs (25 of 22,428) were never inspected, and the request's long-form novelty prompt was not run.
  9. "No knob buys a second correct algorithm" misreads its own Hill of at least 2 threshold.

  Three minor critiques follow.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The deliverable: the structured review (ReviewerFeedback schema) |
| `build_review.py` | Holds the review text and writes the JSON. It also asserts the derived `blocking` rule |
| `verify_numbers.py` | Recomputes every number the review cites from the artifacts' raw rows and result files (read-only) |
| `verify_numbers.log` | Output of `verify_numbers.py` at review time |
| `check_chronology.py` | Diffs the iteration-1 section of the iteration-1 and iteration-2 drafts after stripping the correction markers |
| `check_chronology.log` | Output of `check_chronology.py` at review time |
| `.aii/manifest.yaml` | Disposable-output manifest (no heavy paths, so no entries) |
| `.aii_claude_session.json`, `.repl_agent.ptylog` | Session bookkeeping written by the harness |

## How to run

The scripts need only the Python 3 standard library. They read the run volume and write only into this directory.

```bash
python3 verify_numbers.py      # recompute the cited numbers
python3 check_chronology.py    # chronology / in-place correction check
python3 build_review.py        # regenerate .terminal_claude_agent_struct_out.json
```

The scripts read the artifacts from the run's storage volume, under the iteration-1 and iteration-2 `gen_art` folders of the two run ids named in `verify_numbers.py`. A machine without that volume cannot rerun them; the logs keep their output.

## Restoring removed files

Nothing in this directory is marked `delete`, so there is nothing to restore.
