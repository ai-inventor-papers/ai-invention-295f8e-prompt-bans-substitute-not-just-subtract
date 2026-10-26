# Review of the iteration-3 research record (REVIEW_REPORT step)

An adversarial audit of the run's internal research report after iteration 3: Qwen3-8B and
Llama-3.1-8B-Instruct, algorithm choice under prompt bans, on two path-search tasks and a
12-task bench. The review checks that every executed artifact is written up, that each
headline number traces back to and recomputes from its raw files, that the earlier sections
are changed only by marked corrections, and that the conclusions match the evidence.

## What was done

- Diffed the iteration-1 and iteration-2 sections of the report against the pre-iteration-3
  draft (`gen_report_text/work/paper_draft_before_iter3.md`). Every change is a correction
  marked "iteration 3".
- Walked the seven iteration-3 artifacts (record audit, bench forecast, exposure, Llama
  bench, bench route, locus, reach) and recomputed the headline numbers from their raw
  per-sample and event files. All reported headline numbers matched.
- Found evidence that is not in the report: route-specific landings, random-direction arms
  read as knobs, the alpha = 2 random controls, the Llama hit-label definition, the
  composition of the merge-intervals "other" programs, and template-specific exposure
  landings.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review: scores, strengths, critiques (structured output) |
| `verify_iter3.py` | Read-only script that recomputes every number the review cites from the artifacts' raw files |
| `verify_iter3.log` | Output of `verify_iter3.py` (the evidence behind the critiques) |
| `build_review.py` | Writes `.terminal_claude_agent_struct_out.json` from the review text it contains |
| `.aii/manifest.yaml` | Disposable-output manifest (no heavy paths) |

## How to run

```bash
python3 verify_iter3.py > verify_iter3.log   # Python 3.10+, standard library only
python3 build_review.py                      # rewrites the review JSON
```

`verify_iter3.py` reads the artifact workspaces under
`3_invention_loop/iter_3/gen_art/` of this run in place and writes only to stdout.

## Restoring removed files

Nothing is marked `delete`. This workspace holds only small text files, so there is
nothing to restore.
