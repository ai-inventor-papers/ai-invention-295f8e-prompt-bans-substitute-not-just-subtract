# Iteration-10 research-record audit (REVIEW_REPORT)

This workspace holds an adversarial audit of the run's internal research report on how algorithmic
"creativity" shows up inside code models, and whether it can be moved. The report covers ten
iterations: path-search bans, temperature and forks, DAS, circuits, geometry, and in iteration 10
evaluator-guided bin-packing and TSP search.

The audit followed these steps:

1. Read the report.
2. Checked that each of the 66 supplementary artifacts is reported. All are cited.
3. Recomputed the iteration-10 headline numbers from the artifacts' own result files.
4. Checked coverage against the user's original request.
5. Ran the nearest-neighbour check on the one positive novelty claim.

The verdict is in `.terminal_claude_agent_struct_out.json`, in the ReviewerFeedback schema.
Summary: score 5, confidence 4, soundness/presentation/contribution 3/3/3, `results_reported` true,
coverage partial, not blocking.

## Main findings

- **The whole-multiple-of-item novelty claim (report Section 10.3) does not hold up.** `checks/ablate_whole_multiple.py`
  removes the multiple-of-item term from the four "novel" programs where that term is a separate line.
  It then re-scores them with the harness's own packing loop and probe states. After removing the term:
  - every program still beats both held-out bars;
  - held-out excess changes by at most 0.2 points;
  - corpus agreement stays below 0.9.

  So the gain over best fit comes from ab-type components, not from the new term. The nearest
  published neighbours are the ab principle of Herrmann and Pallez and Harmonic-k (Lee and Lee 1985).
  The artifact computed Harmonic-k as a baseline, but the report never names it.
- **The replication omits its own sensitivity counts (report Section 10.4).** `checks/replication_sensitivities.py`
  recomputes the committed cluster ratios under every sensitivity stored in the replication's
  `analysis_clusters.json`. Excluding stochastic programs moves the pooled ratios from 17.8, 186.5 and
  0.74 to 14.2, 149.5 and 0.61.
- **Smaller issues:**
  - two of the three bootstrap intervals in Table 454 exclude their own point estimates;
  - the activation-space geometry figures of Sections 10.8 and 10.9 have no figure markers;
  - two reproduction-gate shortfalls appear only in the artifacts' deviations files.

## Layout

| Path | What it is |
|-|-|
| `.terminal_claude_agent_struct_out.json` | The review (ReviewerFeedback JSON), read by the next pipeline step |
| `checks/ablate_whole_multiple.py` | Ablates the multiple-of-item term in cand_22, cand_20, cand_09 and cand_29. It first verifies that it reproduces best fit (3.98%, 5.37%) and each full program's reported held-out excess and corpus agreement |
| `checks/replication_sensitivities.py` | Recomputes the replication's per-seed and pooled cluster ratios for the primary count and each stored sensitivity |
| `results/ablation_whole_multiple.json` | Output of the ablation: held-out excess, pass/fail against the 0.8 bars, max corpus and ab-grid agreement per variant |
| `results/replication_sensitivities.json` | Output of the sensitivity recomputation: counts and ratios per seed and pooled |
| `logs/` | Loguru logs of the two check scripts |
| `pyproject.toml` | Dependencies of the check scripts (numpy, loguru) |
| `.aii/manifest.yaml` | Heavy-path decisions. It is empty because nothing here is heavy |

Everything here is small text and stays in the published repository. Nothing is kept only on the
run's volume.

## How to run

The scripts read the run's artifact workspaces and never write into them. Pass the experiment
directory as an argument. Inside the run it is
`<run>/round-10/experiment-51/src` for the first bin-packing search and
`.../gen_art_experiment_52` for the replication.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python numpy==2.2.6 loguru==0.7.3
.venv/bin/python checks/ablate_whole_multiple.py --exp-dir <path>/gen_art_experiment_51 \
    --out results/ablation_whole_multiple.json        # about 35 s on one CPU core
.venv/bin/python checks/replication_sensitivities.py --exp-dir <path>/gen_art_experiment_52 \
    --out results/replication_sensitivities.json      # under 1 s
```

The ablation script stops with an error if it fails to reproduce best fit or any full program's
reported values. Its ablated numbers are therefore on the same harness as the report's tables.

## Restoring removed files

No path is marked `delete` in `.aii/manifest.yaml`, so nothing needs restoring. If you create the
optional `.venv/` with the command above, rebuild it with that same command.
