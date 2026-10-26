# Iteration 9 record audit (REVIEW_REPORT)

An adversarial audit of the run's internal research report after iteration 9 (code-LLM algorithm
choice: rename gap under bans, cumulative-ban exhaustion curve, name-free manifolds, base against
instruct at the fork). The audit walks every iteration-9 artifact, recomputes the headline numbers
from the artifacts' own result files, checks the previous review's MUST-FIX items, and writes a
structured review.

The review itself is `.terminal_claude_agent_struct_out.json` (ReviewerFeedback schema). Its main
finding: the report's 'Established' claim that Qwen3-32B's mechanistic compliance falls to 0.22 under
the five-name cumulative ban is contradicted by the record's own hand reads (0.59 with the reads
substituted, 0.67 by the tracer), so soundness is scored 1 and the review is blocking.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review (overall assessment, strengths, dimension scores, ranked critiques, flags) |
| `work/recompute_n1.py` | Recomputes the pooled and per-configuration rename gap from `results/retrace.jsonl` of the rename artifact, with the coarse class map and a sensitivity that counts unit-weight Dijkstra, IDA* and jump point search labels as compliant |
| `work/n3_comp.py` | Runtime-label composition of every cumulative-ban, described-ban and gpt-oss cell (`data/samples_v9.jsonl`), including the greedy best-first programs counted as violations at k = 4 |
| `work/n3_reads.py` | Substitutes the executor's hand reads (`data/manual_reads_v9.jsonl`, `results/manual_reads_summary.json`) into the k = 5 cells and compares runtime label, hand reads and tracer |
| `work/geometry_checks.py` | Recomputes every g/median of Table 435 from `results/rederive.json`, lists all seven RSA model matrices, and tabulates the placement of every iteration-8 survivor family per program frame |
| `work/base_checks.py` | Base-against-instruct checks: per-fork gains and unmapped base mass, random patching sets with repeated components, the nulls, and the held-out rerun split by clean and forced rows |
| `.aii/manifest.yaml` | Disposable-output manifest (no heavy paths in this workspace) |

## How to run

Each script takes the path of one artifact directory of the run (the `gen_art` outputs of
iteration 9) and only reads from it. Run them with an isolated interpreter:

```bash
python3 -I work/recompute_n1.py <rename artifact dir>      # gen_art_experiment_45
python3 -I work/n3_comp.py      <rename artifact dir>
python3 -I work/n3_reads.py     <rename artifact dir>
python3 -I work/geometry_checks.py <geometry artifact dir>  # gen_art_experiment_46
python3 -I work/base_checks.py     <base-model artifact dir> # gen_art_experiment_50
```

Only the Python standard library is needed. No file in this workspace is large; nothing was downloaded.

## Restoring removed files

Nothing is marked `delete` in `.aii/manifest.yaml`, so there is nothing to restore. All files here
are small text files and stay in the published repository.
