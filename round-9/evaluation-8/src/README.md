# Repairing the iteration-8 research record (iteration 9, Step 0)

This repository answers the blocking review of the iteration-8 record of the AI Inventor run on *how "creativity" (which algorithm a code model writes) is decided inside open models*. It does not run any model. It reads iteration 8's result files in place, recomputes every number that a correction quotes, and writes 49 verbatim edits into the research report. It also runs one new CPU computation, which asks whether iteration 8's "opposite" landing is a property of the alias-named manifold. Each edit maps one `old_text`, found exactly once in the report, to one `new_text` tagged `(iteration-9 correction)`.

Run date 2026-10-23. Plan id `gen_plan_evaluation_1_idx1`. Entry point: `eval.py`.

## Headline results

| Item | What the review asked | Result |
|-|-|-|
| 0a (must-fix) | Circuit "same shape as Gemma" and an exact-zero held-out effect | Recomputed, the layer-0 condition-span MLP has a held-out effect of exactly 0.00 under ablation and steering. The edit was never applied. `MeanCache.get` (`src/k3circuit.py` lines 482, 485 and 488 of the circuit artifact) takes condition-span means only from pair prompts of the same template. The held-out prompts are templates F11-F15 and the pair prompts F1-F10, so 0 of 10 held-out prompts match. All 20 stored held-out rows (node and 50 random components) are exactly 0. The identity mean×30 = pair×20 + held-out×10 holds for every node, and the L0 node is the only exact-zero node. It rests on its 20 pair prompts (8.14 and 7.41 nats). On the natural contrast its held-out effect is 0.28 nats (p 0.031 = 1/32, the floor for 5 prompts). The committed motif test reads **different motif**: condition share 0.01 against the band [0.21, 0.51], and depth 0.86 against [0.45, 0.80]. The post hoc sweep still misses both bands (0.17; depths 0.86-0.96). Tables 395 and 396 gain held-out columns |
| 0b (must-fix) | DAS verdict at Qwen3-8B's fork | **NO HANDLE** under the committed rule. Toward BFS the edit writes BFS in 29 of 30 programs, but only 5 are correct (24 fail; pass 0.20 against 0.83; 5:0 against random, exact p 0.0625). Gemma's fork is a SUFFICIENT HANDLE (22 of 30 against 6 unedited and 5 random). All 29 '29 of 30' occurrences are classified (`tables/occurrences_29of30.csv`) |
| 0c (must-fix) | Entropy superlative; law scope | The fork's entropy exceeds the twin's 90th per-token percentile (0.0003-0.05 nats) in all 209 twin samples that reach it. It is the highest-entropy position among the first 64 tokens on 44/44 (Gemma), 32/39 (MST) and 21/39 (anagram) slots, but on only 2/50 (connected components) and 0/37 (trapped rain water). The temperature law holds on 5 of 6 units, but its rivals stay close: the flat law is better on valid anagram (0.030 against 0.054), tempering on substring search (0.023 against 0.033), the sign test against flat gives p 0.34, and Llama fails (0.142). H(algorithm given the fork classes) is at most 0.004 bits on the five Qwen3-8B and Gemma units, and 0.63 on Llama |
| 0d (must-fix) | Positioning of the iteration-8 claims | A new subsection, 8.10b, adds Table 416b (7 claims) and 5 references. 11 neighbours were checked live with fetch_grep: 8 VERIFIED, 3 VERIFIED-ABSTRACT, 0 NOT-FOUND. Both NeurIPS 2026 pages of Cantarero et al. (172378 and 164442) are **workshop posters**. The pages quote 18.4-57.1×, 1.06-1.70× and FPD 32.8% against 4.7%. Venues confirmed live: Sparse but Critical (ICLR 2026), MIB (ICML 2025), Position-aware ACD (ACL 2025 long) and Many Circuits, One Mechanism (TMLR 2026, from the arXiv journal reference). Three venue statements stay unverified: Invisible Lottery, Manifold Steering and denial prompting. The base sub-arm's contribution narrows to the algorithm-level outcome on code |
| 0e (must-fix) | Alias-named manifold | Gates E1-E3 pass. E4: an independent kNN-geodesic recomputation from the stored states matches the stored k15 matrix at Spearman 1.000. The 15-alias Spearman of g against committed lexical overlap is **-0.61** at k15 (exact p 0.0093 over 360,360 assignments; template-bootstrap CI -0.71 to -0.59) and -0.77 at k10 (p 0.0007). At the 5-centroid level it is -0.63 (p 0.133; floor 0.033). The **within-algorithm** stratified test on content words gives -0.12 (p 0.46; 216 effective relabelings), and the fixed-effects slope has the wrong sign (+2.36, p 0.78). Committed wording: *g follows alias overlap across algorithms, but the pattern is carried by algorithm identity; on this manifold names and mechanisms are confounded, and TP-G's name-free manifolds decide.* An optional sensitivity on the model's own BPE tokens gives a borderline within-algorithm statistic of -0.50 (p 0.057; at k10, -0.40 with p 0.11), so a small name effect is not excluded; the report says so. Placebos fail as required (P1 4.8%, P2 5.0%, P3 mean 0.007), and the planted control succeeds (rho -0.92, p 3e-6) |
| 0f (minor) | Gemma comparators | Gemma ran A0, A1, A3g and A5. It did not run A2 (T 1.6), A4 (min-p) or A6 (block-start). The entropy-triggered arm A5 costs 0.18 in pass rate, above the 5-point rule, so min-p, EDT and AdapT are all scored at the twin's Hill (1.64). The sentence now reads: the filtered dial beats the twin-level fallback of the entropy-triggered family (p 0.023) and ties global T (+0.08, p 0.23); min-p and block-start were not run on Gemma |
| 0g (minor) | Missing figure markers | 7 markers added for the iteration-8 geometry figures, plus `fig_alias_overlap` from this repository. Each caption states positions, block, projection, N, centroid sizing and the caveat, with sha256 hashes of the PNG and PDF (`figure_markers.json`). 8.6 gains a paragraph describing Gemma's F4 |

The repair's own checks:

- **Apply test** passes: 49 edits, each `old_text` occurs exactly once, no two spans overlap, and every `new_text` is present after application.
- **Whole-report lint**: 28 unallowed hits before, 0 after. The 8 hits that remain sit in pre-iteration-8 text and are allowlisted with a reason (`lint_allowlist.json`).
- **Value ledger**: 298 values, 147 MATCH, 151 NEW, 0 CORRECTED and 0 CARRIED.
- **Stdlib audit**: 400 checks with 0 mismatches. 393 are independent and 7 are consistency-only (bootstrap, placebo and E4 values). 4 of 4 placebos fail as they must.
- **Raw-row headline check** (`audit/headline_rederive.py`): every headline is recomputed from raw per-row files, not from aggregated result fields, through a separate stdlib code path. These are the 0a pair and held-out means, the 0b counts and McNemar p, the 0c hit counts, and the 0e rho with its exact p. All reproduce. Its placebos fail as they must: a non-condition node, shuffled point labels, and random dose positions (3 of 209 hits against 99).
- **Inputs**: hashed before and after the run; they are unchanged.

## Layout

| Path | What it is |
|-|-|
| `eval.py` | Orchestrator. Stages: setup (input hashes), 0e, value ledger, edits, apply test and lint, audit, and `eval_out.json` |
| `src/recompute.py` | Recomputes every quoted number for 0a, 0b, 0c and 0f into the value ledger (with source keys `<artifact_id>:<path>#<key>`) |
| `src/alias_geometry.py`, `src/stage_0e.py` | Item 0e: lexical detectors, alias-level g, exact nulls, the stratified test, the template bootstrap, placebos, the planted control, gates E1-E4 and the figure. Both are hash-committed |
| `src/commit_s0e.py` | Writes `predictions/commit_s0e.json` and appends its sha256 to `commitments.log`, before any alias-level number exists |
| `src/tertiary_bpe.py` | The optional BPE-token overlap sensitivity (uses the cached Qwen3-32B tokenizer, offline) |
| `src/edits_spec.py` | All 49 edits (old_text → new_text). Every number is filled from the ledger |
| `src/s0_extra.py` | Builders for the 0d positioning (six `positioning.json` adapters plus live checks), the 0g markers and the 0e text |
| `src/apply_lint.py` | Apply test, unified diff and the L1-L10 residual-claim lint |
| `audit/rederive.py` | Independent standard-library re-derivation, with its own npz/npy reader. Writes `audit/rederive_result.json` |
| `audit/headline_rederive.py` | Short stdlib re-derivation of the headline numbers from raw per-row files, with placebos. Writes `audit/headline_rederive.json` |
| `inputs/forced_index_C6_nf4.json`, `src/vendor_index.py` | Vendored prompt index (kind, algorithm, group, template, blocks) of iteration 8's 181 MB states file. It lets a published copy run 0e without that file; only the E4 cross-check is then skipped |
| `reproducibility.md` | Step-by-step reproduction: what was run, in what order, with which versions, and what you should get |
| `audit/web_verify.sh`, `audit/web_jobs.tsv`, `audit/web/` | Live fetch_grep verification of the neighbours: jobs, script and raw outputs (UTC time in `audit/web/_run_utc.txt`) |
| `inputs/report/current_report.md` | Vendored copy of the report under repair (sha256 `8b3804f3…d7438`) |
| `inputs_manifest.json` | sha256 of all 53 input files, checked unchanged at the end of the run |
| `corrections.json` | edits[], values[], values_by_status, n_edits_by_item, apply {apply_test_pass, n_edits, lint_before, lint_after}, item_checklist |
| `report_corrected.md`, `report.diff` | The corrected report and its unified diff |
| `apply_test.json`, `lint_allowlist.json` | Apply-test summary; allowlisted lint hits with reasons |
| `figure_markers.json` | The 8 markers with six-field captions, sha256 hashes and code references |
| `predictions/commit_s0e.json`, `commitments.log` | The 0e pre-commitment and its hash chain. One amendment, a figure-legend placement, is logged with its reason |
| `results/s0e.json`, `results/s0e_tertiary.json`, `results/s0_core.json` | Full 0e results, the BPE sensitivity, and the 0a/0b/0c/0f details |
| `tables/*.csv` | circuit_heldout, occurrences_29of30, entropy_scope, law_scope, positioning_rows, alias_g, alias_stats, alias_tertiary, gemma_arms, ledger, lint_hits |
| `figures/alias_overlap.(pdf|png)` | Panels A and B: alias-level g against overlap at k15 and k10. Panel C: classical MDS of the stored k15 geodesics (stress-1 0.18) |
| `eval_out.json` (= `full_eval_out.json`), `mini_eval_out.json`, `preview_eval_out.json` | exp_eval_sol_out output (schema-validated). The metadata holds sections 0a-0g |
| `logs/` | Run logs |

Everything kept is small text or figures and is published with the repository. Nothing kept is 100 MB or larger. The iteration-8 inputs are read in place on the run's volume and are not copied. That includes the 181 MB `cache/states/smean_C6_nf4.npz` of the prohibition artifact.

## How to run

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # 29 packages, pinned to the versions used
uv run eval.py --stages all          # about 40 s on CPU; also runs both audits
# optional: re-fetch the live neighbour pages (needs the aii-web-tools skill)
AII_WEB_TOOLS_DIR=<path to aii-web-tools> bash audit/web_verify.sh
```

The six iteration-8 artifacts are found through one setting, `S0_DEPS_DIR`. Each is looked up by its artifact id or its original folder name, first under `S0_DEPS_DIR` (default `../../../round-8`) and then as a sibling folder. The report under repair is vendored in `inputs/report/`, and the optional tokenizer is read from `$HF_HUB_CACHE`. `python -I audit/rederive.py` and `python -I audit/headline_rederive.py` run the audits alone, with the standard library only. See `reproducibility.md` for the full procedure.

## Commitments and amendments

`predictions/commit_s0e.json` was written, and its sha256 appended to `commitments.log`, before any alias-level number was computed. It fixes the following:

- the 11 lexical detectors and the expected overlap vectors (asserted at run time);
- the stopwords;
- the statistics, nulls and gates;
- the placebos and the planted control;
- the verdict wording rules;
- the planner's non-blind expectation (about -0.70, -0.63 and -0.87);
- the code hashes.

`src/stage_0e.py` changed twice after the commit, and neither change touches a statistic, null or rule:

- the panel-A legend moved because it hid one point;
- a fallback to the vendored prompt index was added for copies without the 181 MB states file.

Both reasons are logged as `AMENDMENT-REASON`, and `eval.py` logged each new code hash automatically. `src/alias_geometry.py` is byte-identical to the committed version.

## Departures and limitations

- **Pseudo-replication in the committed 15-alias statistic.** It treats aliases as exchangeable, but they are nested in 5 algorithms, so its p (0.0093) is optimistic. The 5-centroid test (floor 0.033) and the within-algorithm test were added, as the plan required. Only the within-algorithm test holds mechanism fixed.
- **The lexical score is a committed string-detector count.** Two sensitivities are reported: content-word Jaccard (p from 200,000 Monte Carlo draws, because there are 5.4 million distinct arrangements) and BPE-token Jaccard. The BPE score makes the within-algorithm test borderline (p 0.057).
- **The expectation was not blind.** Iteration 8's algorithm-level g was public. Only the within-algorithm test and the interval were unseen.
- **No GPU rerun.** The layer-0 node's held-out status is *untested*, not failed, until BASE (B3) reruns it with template-matched means.
- **Geodesics are reused from iteration 8.** The kNN graph is fixed. E4 reproduces it exactly from the stored states, but robustness to the graph construction is only what iteration 8 reported.
- **The template bootstrap holds the geodesics fixed.** It understates the uncertainty that comes from the graph.
- **The value ledger has no CARRIED values.** Every quoted number was recomputable from a file, so none had to be carried. Positioning quotes taken from the iteration-8 `positioning.json` files are carried as rows (status CARRIED in `tables/positioning_rows.csv`), not as numbers.
- **Table edits are whole-table edits.** Tables 395 and 396 are each one edit (caption plus table), so that the iteration-9 marker sits in the caption. The ledger still lists every row's values.
- **Venue claims not confirmed live.** The arXiv pages of Invisible Lottery, Manifold Steering and denial prompting state no venue, so the earlier venues for these papers are carried, not verified. A NeurIPS 2026 page for Many Circuits was not fetched; its TMLR venue comes from the arXiv journal reference.

## Restoring removed files

`.aii/manifest.yaml` marks two paths for deletion after the round. Both are regenerable:

| Path | How to restore |
|-|-|
| `.venv/` | `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `src/__pycache__/` | Regenerated by any run: `uv run eval.py --stages all` |

The Qwen3-32B tokenizer for the optional sensitivity is read from the shared HF cache. If it is missing, run `huggingface-cli download unsloth/Qwen3-32B-bnb-4bit tokenizer.json`.
