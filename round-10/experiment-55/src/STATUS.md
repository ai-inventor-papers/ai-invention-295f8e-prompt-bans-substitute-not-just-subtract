# STATUS (final)

All plan stages are done. The outputs are validated: `method_out.json` passes the exp_gen_sol_out schema, with
full / mini / preview variants alongside.

| stage | state | key output |
|---|---|---|
| 0 setup + reproduction gate | done; both models pass (cosine >= 0.99999, frozen g reproduced exactly) | `results/repro_gate.json` |
| 1.1-1.3 cells, prompts, instrument, COMMIT0a / 0b | done; gate 18/18 planted, 13/15 catalogue | `predictions/cells.json`, `results/instrument_gate.json` |
| 1.4 generation | done; 1,020 calls in 3 rounds; amendments COMMIT0c / 0d | `data/raw_factorial.jsonl` |
| 1.5 acceptance + hand reads | done; 15 G1 cells (>= 10 each, cap 16); 158 hand reads | `data/factorial.jsonl`, `data/hand_reads.jsonl` |
| 1.6-1.8 top-ups, survivors, covert set | done; jps and biastar below the floor (F7) | `data/frames.json` |
| 1.10 design check | done | `results/design.json` |
| T4 + COMMIT1 | done | `results/t4_synthetic.json`, `predictions/commit1.json` |
| 3 states | done; 412 programs x 2 models | `cache/states/tpg2_{8b,32b}.npz` |
| 4 G1 | done; NOT SUPPORTED (rho_d 0.104 / 0.090 vs rho_c 0.46 / 0.59) | `results/g1_*.json` |
| 5 G2 | done; NOT SUPPORTED as preregistered (within-container mechanism, cross-container surface) | `results/g2_*.json` |
| 6 figures | done | `figures/` |
| 7 independent re-derivation | done; 0 mismatches | `audit/rederive.json` |
| 8 positioning | done; 7 works | `results/positioning.json` |
| 9 outputs | done | `method_out.json`, `README.md`, `.aii/manifest.yaml` |
| exploratory | done | `results/explore_confusion.json`, `results/explore_dbeh.json`, `results/t4b_bootstrap_coverage.json` |

**Resume:** `python method.py <stage> --force`. Stage names are in the `method.py` docstring.

## Finalization TODOs (all done)

- [x] TODO 1: full / mini / preview variants regenerated from `method_out.json` with the aii-json format script; schema
  validation PASSED.
- [x] TODO 2: size check against the 100 MB limit. `method_out.json` is 1.3 MB and `full_method_out.json` 1.4 MB, so
  no split was needed. No workspace file outside `.venv` exceeds 100 MB.
- [x] TODO 3: `pyproject.toml` pins all 70 packages to the exact `.venv` versions, from
  `uv pip freeze --python .venv/bin/python` (the uv venv has no pip). The list is identical to
  `requirements.lock.txt`.
- [x] TODO 4: `reproducibility.md` and `restore.sh` written. Every path is relative.
  - Code now reads prior artifacts through relative sibling-folder constants (overridable by environment variables)
    named by artifact id.
  - Bit-identical reduced copies of iteration 9's cached states ship in `cache/e46_states/`.
- [x] TODO 5: independent re-derivations `audit/rederive.py` and `audit/rederive2.py` (stdlib + numpy, own code paths)
  give 0 mismatches.
  - Re-derived: G1 rho_d, rho_c, exact p and cell RDM; G2 F0 classes; covert shares; LOO accuracy and the error split;
    PROBE landing; Delta; AST-baseline rho_d.
  - Placebos fail as expected for the LOO accuracy, the error split and rho_d / rho_c.
  - Norm-matched Gaussian states do not remove the Delta magnitudes or the 32B covert F1 share, so those two are
    reported as descriptive.
