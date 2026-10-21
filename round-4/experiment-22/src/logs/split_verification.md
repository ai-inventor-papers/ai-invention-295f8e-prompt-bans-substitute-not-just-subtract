# Splitting the state files under the 100 MB limit (verification record)

- `logs/split_states.py` split 30 files (`states/states_<task>.npz`, `states/disp_<task>.npz`) row-wise into 81 parts
  `<name>.partNNN.npz`. The largest part is 44.7 MiB. Before each original was deleted, every array was reloaded
  through `src/npz_parts.load` and compared with the original: dtype and values were identical (`np.array_equal`).
- Every reader and writer now goes through `src/npz_parts.py` (`load` and `exists` accept either form):
  `src/subspace.py`, `src/gpu_phase1.py`, `analysis/c2b.py`, `analysis/geometry.py` and `analysis/explore.py`.
- The analyses were re-run on the parts (`analysis/run_all.py c2b explore geometry`):
  - `results/c2b.json`, `results/explore.json` and `results/escape.json` are byte-identical to the pre-split files;
  - `results/geometry.json` differs only at floating-point level (Isomap stress-1 at the 8th decimal, embedding
    coordinates by ≤ 1.3e-4), which is eigen-solver / BLAS-thread nondeterminism, since the inputs are identical.
- `logs/test_split_subspace.py` re-ran `src/subspace.py` end to end on the parts, with its writes captured in memory:
  - all 15 subspace arrays are bit-identical to the committed `states/subspace_*.npz` (max abs diff 0.0);
  - the 7,460 predictor values equal the committed `predictions/c2_commit.json` (max abs diff 7.6e-18).
- `src/gpu_phase1.py`:
  - `states_pass` and `realised_pass` recognise the parts and skip all 15 tasks;
  - `units()` re-reads the parts and reproduces `results/units.json` and `results/units_nfree_R2.npy` exactly.
- `npz_parts` round trips pass: a forced 10-part split and the legacy single-file form.
- After the change: `audit/rederive.py` has 0 mismatches, the commitment chain has 56 entries with no breaks, and
  all four method_out files pass exp_gen_sol_out validation.
