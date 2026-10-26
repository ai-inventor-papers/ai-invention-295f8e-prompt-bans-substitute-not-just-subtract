# Transplanting the base model's plan (iteration 5, Step 1)

Qwen3-8B (instruct, thinking off) writes the same algorithm for almost every coding task. Examples: a full sort for
the k-th smallest element, union-find for connected components, Dijkstra for weighted shortest paths. Its base model,
Qwen3-8B-Base, is often more varied when it sees the **identical token ids** under the same chat template. This
repository asks whether that lost variety is still *recoverable at the plan site*.

The intervention is a **cross-model state transplant**, in the spirit of cross-model activation patching (Prakash et
al., ICLR 2024). During the instruct model's prompt prefill, the task-specification states at decoder blocks 12–23
are replaced by

`h[l,p] <- h_instr[l,p] + lambda * (h_base[l,p] - h_instr[l,p])`, for lambda in {0.25, 0.5, 1}.

The hooked states are *set*, not added to, so nothing compounds across blocks. At lambda = 1 the hooked blocks carry
the base state exactly: unit test U3 finds a maximum difference of 0.0 at block 23, and block 24 is recomputed.

**Claim B** (primary, causal, pre-registered): the transplant reopens the base model's repertoire. To pass on a task,
it must beat three controls, all on the same common-random-number slots:

- **MR**: a norm-matched random displacement, matched per block and position.
- **XT**: a cross-task base shift. This is another task's mean base-minus-instruct direction, norm-matched.
- **MRP**: a pass-matched random push, used where MR breaks the model.

The transplant must also land on the base model's own runner-up algorithm `r_t`. It is tested on the
**BASE-DIVERSE** tasks: those where at least 20% of the base model's correct programs are non-default.

The same pipeline also runs:

- **Claim D**: a de-sharpening push along unit(D), against an isotropic push.
- **Reverse interchange**: instruct states transplanted into the base model.
- **Site controls**: the read position R, blocks 0–11 and blocks 24–35.
- **Dose curves**: one for the transplant and one for the random control.
- **Plan-site geometry**.
- **A descriptive Claim A screen check**: does base diversity predict iteration-4 movability?
- **A novelty audit**.

All arms share exact common random numbers: one uniform stream per (task, template, slot), with a fixed batch shape of
B = 20. Unit test U2 confirms that T(0) equals the twin token for token, on 20 of 20 slots. Rules, thresholds and
predictions were hash-committed before the samples they govern (`commitments.log`, `predictions/`).

## Results

### Bottom line

**Claim B is DISCONFIRMED by the frozen rule.**

- The rule needs PASS on at least 4 of the 5 BASE-DIVERSE tasks: T03, T2, T10, T1, T14. Only T14 passes.
- On the other 4 tasks, condition (iii) fails: the transplant does not beat its controls after Holm correction.
- Two sensitivities give the same verdict: stable-stratum tasks only, and noise-robust specificity.
- The outcome-blind N = 100 power extension (COMMIT3_EXT, descriptive) still passes only T14. Its verdict is PARTIAL
  rather than DISCONFIRMED for a mechanical reason: at N = 100, T1's transplant pass rate (0.68) falls below
  0.8 x twin (0.91), so the rule's "valid pass" precondition for DISCONFIRMED no longer holds.

**T14 (top-k frequent): one large, specific effect.**

- Under the full transplant T(1), the instruct model writes the base model's runner-up (a heap) in 21 of 49 correct S2
  programs. The twin writes none (0 of 39).
- The pass rate rises from 0.78 to 0.98.
- T(1) beats all three controls (Holm-adjusted p ≤ 7e-4 against each, ahead on 5 of 5 templates):
  - MR(1): 2 heap programs, pass 0.78;
  - XT(1): 5 heap programs;
  - MRP(0.5): 0 heap programs.
- With N = 100, the McNemar discordant pairs are 44:0 against MR, 35:3 against XT and 49:0 against MRP.

**T03 (k-th smallest): the base state holds the default *more* firmly than matched random noise.**

- On S2, T(1) gives 3 of 50 off-default correct programs. MR(1), with the same per-position norm in a random
  direction, gives 21 of 50, mostly quickselect.
- McNemar, T vs MR: 2 vs 20 discordant pairs, two-sided p = 1.2e-4.
- So the base-minus-instruct displacement disrupts the plan *less* than an isotropic displacement of equal size.

**T10, T2 and T1 are not reopened at an intact pass rate.**

- T10: T(0.5) gives 6 of 50 dfs programs at S1 (p = 0.016 against the twin), but only 4 of 50 on S2.
- In the extension, T(0.5) beats the cross-task control on T10 (7:0, raw p = 0.008, Holm 0.06), and T(1) does on T03
  (6:0, raw p = 0.016, Holm 0.11). Neither beats MR.
- T2 and T1: lambda ≥ 0.5 breaks the pass rate (T2: 0.72 at lambda 0.5, 0.54 at lambda 1; T1: 0.50, 0.30). The lambda
  = 0.25 that survives moves nothing.

**Site controls.**

- **Read position R.** The base and instruct states differ there by about the size of the residual itself:
  ||D|| / ||h|| ≈ 1.0–1.1 at blocks 12–23. Transplanting the base state at R destroys the output (at most 16 of 30
  programs pass on 13 of 15 tasks) but moves no algorithm significantly (exact McNemar p ≥ 0.5 on every task).
- **Early blocks (0–11).** The same transplant there moves T03 (15 of 50 size-k heap) and T10 (14 of 50 dfs) *more*
  than the main band does (p ≤ 1e-4 against the twin, S1).
- **Late blocks (24–35).** Inert.

**Specificity.**

- The three BASE-COLLAPSED tasks do not move under T(1): a change of 0.00.
- READ(1) shifts the off-default share by more than 0.05 on T10 and T11. This happens only among the few programs that
  still pass (5 and 16 correct of 30), and never significantly.
- So the pre-registered point-estimate specificity check fails, while its noise-robust version holds.

**Claim D is DISCONFIRMED.**

- A push along unit(D) never escapes the default on any of the 4 tasks, at doses of 0.5–2 ban-free units.
- The isotropic push escapes on T03 at alpha = 2 (8 of 30 off-default).

**The reverse interchange shows asymmetric control.** Instruct task-spec states written into the base model make it
write *more correct* programs, mostly of the instruct default:

| Task | correct programs, BTWIN → RT(1) | default share among attempts |
|---|---|---|
| T03 | 20 → 31 | +0.11 |
| T2 | 15 → 20 | +0.11 |
| T1 | 5 → 11 | +0.33 |
| T10 | 18 → 19 | +0.17 |

The committed prediction was that the default share among correct programs rises by at least half the
instruct-minus-base gap. It is met only on T1 (0.80 → 1.00; McNemar on default-and-correct 9:2, one-sided p = 0.033).
The norm-matched random control into the base model lowers the pass count instead (16, 6, 2 and 16 correct).

**The Claim A screen check (descriptive) is strongly positive.**

- The base model's off-default share beta_t ranks the 15 tasks almost exactly as iteration 4's random pushes could
  move them: Spearman 0.78 against the escape fraction E_t at alpha 1 (one-sided permutation p = 2e-4), Kendall 0.69.
- The base runner-up r_t is the push's top-1 landing on 5 of 5 movable tasks.
- So the base model's alternatives are where random pushes land. Its *states*, however, do not steer the instruct model
  there, except on T14.

**D is mostly a generic base–instruct difference.**

- The per-task mean D is shared across tasks: cross-task cosine 0.76–0.88 at blocks 12–27.
- It is template-invariant: split-half cosine (W1–W2 vs W4–W5) 0.96–1.00.
- At lambda = 1, 71% of the hooked (block, position) cells exceed iteration 4's breakage dose of 4 ban-free units.

**Geometry: the transplanted plan state does not survive at R.** After a full transplant, the task-spec state at block
27 stays 88–89% of the way to the base twin (T03, T14). The read-position state at blocks 18 and 23 moves only 18–31%
of the way. Blocks 24 and later, and the chat-tail positions, pull the computation back toward the instruct model.

**Novelty audit: no correct novel algorithm.**

- 48 unique correct programs fall outside the catalogue (all arms, the base model included).
- The judges call 14 of them NOVEL. Manual adjudication against the nearest known solution finds that every one is a
  linear scan, a count loop or a threshold binary search: known techniques that happen to lie outside the frozen
  catalogue.
- Count of novel algorithms: 0 (rule-of-three 95% upper bound 0.063).

**Checks.**

- Labellers: every bench labeller recovers 100% of its references and reproduces its gold agreement exactly.
  The exp8 path suite recovers 22 of 22 references; its mechanical gold accuracy is 0.80 here against the
  gate's 0.84. That gate relies on the judge fallback (0.97 combined), as this pipeline does.
- Base extraction: agreement with ITER1 labels is 0.95 on 40 ITER1 base programs (it was 0.725 without the judge; see
  `results/extraction_test.json`).
- Base-label judge audit: agreement ≥ 0.86 on every task, so no task is LOW-CONFIDENCE.
- Engine check (bf16 here, FP8 in the exp17 screen): twins agree slot by slot 1.00 and 0.98; pushed rows agree 0.74 and
  0.88, both within the template-resampling null.
- Re-derivation: 56 of 56 checks match (`audit/rederive.py`). A second, raw-row re-derivation of every headline number
  matches 34 of 34 (`audit/rederive_headlines.py`). The placebos fail as required: arm-shuffled McNemar rejects at
  0.012–0.036, self-comparison gives p = 1, and permuted Claim-A ranks reject at 0.042.
- Hash chain: unbroken. Every hooked row follows COMMIT #1, and every Stage-4 row follows COMMIT #2.

### What the results mean for the research question

- **The instruct model's narrowing is not carried by the task-spec states at blocks 12–23 alone.** Giving it the base
  model's exact states there changes the algorithm on 1 of 5 diverse tasks (T14). On T03 the base states are
  *stickier* than random noise of the same size.
- **The algorithm-relevant signal sits outside the main band.**
  - Early-block states (blocks 0–11) move T03 and T10 when transplanted.
  - The read-position state R is the largest base–instruct difference of all, but transplanting it only breaks the
    output.
- **The base model's runner-up is a strong descriptive predictor.**
  - It is where iteration-4 random pushes land (5 of 5 movable tasks).
  - Base diversity ranks task movability (Spearman 0.78).
  - The exception cuts the other way: T14 is BASE-DIVERSE (beta 0.35), yet iteration-4 random pushes never moved
    it (E_t = 0). It is the one task where the base *state* works and random noise does not.
  - Yet the base state is not, in general, the causal handle. The useful follow-ups are an early-block or full-depth
    transplant, and a check of whether T14's success comes from its heap solutions being *more correct* (twin pass
    0.78, transplant 0.98).

## What was run

| Stage | What | Where |
|---|---|---|
| 0 | inputs copied with sha256 and provenance; bench files checked against `bench/commitment.json`; screen sha256 `d6a2ca97…`; labeller re-check; T2 style re-gate; base-extraction test; precision rule; GPU unit tests U1–U3; CPU tests; engine check | `src/s0.py`, `tests/test_cpu.py`, `src/gpu5.py instr1`, `results/input_hashes.json`, `results/labeller_recheck.json`, `results/unit_tests*.json`, `results/engine_check.json` |
| 1 | base repertoire, Qwen3-8B-Base on vLLM bf16: chat N = 100 per task (T1/T2 200; top-up +100 for T10, R1, R2), plain completion N = 100; instruct twin j 0–19; judge audit of base labels | `src/base_vllm.py`, `src/labels5.py`, `src/audit5.py base` |
| COMMIT #1 | default_t, beta_t with CI, r_t, strata, partner derangement, Stage 3–6 plans | `predictions/commit1.json` |
| 2 | clean prefill states of both models (75 twin prompts × 36 blocks × S ∪ {R}); D-size report; forced-prompt states | `cache/states/`, `cache/geometry/forced_*.npz`, `results/d_norms.json` |
| 3 | selection on S1: T(0.25/0.5/1), MR(0.25/0.5/1), READ(1), EARLY(1), LATE(1) | `src/gpu5.py instr2`, `results/selection.json` |
| COMMIT #2 | lambda*, MR breakage, lambda', validity gate, Stage-4 plan | `predictions/commit2.json` |
| 4 | confirmation on fresh S2 slots: T(lambda*) vs MR, XT (+ MRP on T14); outcome-blind N = 100 extension (COMMIT3_EXT) | `results/confirmation.json`, `results/claim_b.json` |
| 5 | Claim D: DS / ISO at alpha 0.5 / 1 / 2 ban-free units | `results/desharpen.json` |
| 6 | reverse interchange: BTWIN, RT(1), BMR(1) on the base model | `results/reverse.json` |
| 7 | geometry: MDS (stress-1) and Isomap k = 5 / 10 / 15 at S18, S23, S27, R18, R23 | `src/geometry5.py`, `results/geometry.json` |
| 8 | novelty audit (2 judges + deepseek tiebreak + manual adjudication), Claim A screen check, knob rows, figures, `method_out.json`, independent re-derivation | `src/audit5.py novelty`, `src/manual_novelty.py`, `src/analysis_final.py`, `src/figures5.py`, `src/outputs5.py`, `audit/rederive.py` |

**Models.**

- `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218`
- `Qwen/Qwen3-8B-Base` @ `49e3418fbbbca6ecbdf9608b4d22e5a407081db4`, the base revision pinned by ITER1 exp5

**Precision.** bf16 on an RTX 4090 (24 GiB). The frozen precision rule gives bf16 for any GPU of at least 19.5 GiB.

**Decoding.**

- T = 1.0, top-p 1, no top-k, thinking off.
- Cap: 1,024 new tokens for the instruct model; 1,536 for base T1/T2.
- Stop rules: the exp16 fence stop for the instruct model. The base model also stops on `<|im_start|>` and on a closed
  fenced block containing `def solve`.

**Labels.**

- The iteration-4 label worker, unchanged: runtime tracer first, AST second, blind judge on disagreement only.
- 'other' and 'invalid' are separate labels and never count as off-default.
- Non-catalogue labeller labels (for example R6's `linear_scan`) are treated like 'other'.

**Compute and spend.** 1.70 GPU-hours (10,860 HF programs + 3,500 vLLM programs). OpenRouter USD 0.29 against a cap
of USD 1.5.

## Pre-registration and audits

- `commitments.log` is a hash chain over `predictions/commit0.json` (protocol, thresholds, frozen-code sha256),
  `commit1.json`, `commit2.json` and `commit3_extension.json`. It has 0 breaks.
- Commit order (`results/commit_order_audit.json`):
  - COMMIT #1 at 12:55:31Z precedes the first hooked row (12:56:03Z).
  - COMMIT #2 at 13:55:38Z precedes the first Stage-4 row (13:55:43Z).
  - Two hooked runs came before COMMIT #1 by design, as Stage 0: the T(0) identity test rows in
    `data/unit_test_rows.jsonl` and the engine-check pushes in `data/engine_check_raw.jsonl`.
- `audit/rederive.py` recomputes the following from `data/samples.jsonl` without importing `src/`: default_t,
  beta_t, strata, lambda*, every Stage-4 McNemar p and the Holm family. Result: 56 of 56 checks match.
- Placebos:
  - Arm shuffle within slots: rejection rate 0.012 (nominal 0.05).
  - Base rows permuted across tasks: only 27% of tasks keep their stratum.

## Deviations (full text in `results/deviations.jsonl`)

1. **D-commit0-order.** Base sampling (vLLM), the engine check and the instruct twin ran *before* COMMIT #0 was hashed,
   to use GPU time. COMMIT #0 still precedes COMMIT #1 and every transplant, control, push and reverse sample.
2. **D-topup-engine.** The top-up rows (T10, R1, R2) came from the same vLLM engine as the main base sample, not from
   the HF engine.
3. **D-twin-s2.** TWIN slots j 10–19 (TWIN_S2) were sampled in the same B = 20 batches as TWIN S1. They are unhooked,
   and no selection computation uses them.
4. **D-states-dtype.** States are cached as exact bf16 bit patterns, not fp16.
5. **D-gpu.** The GPU was an RTX 4090, not the planned A4500. The precision rule still gives bf16.
6. **D-ustream-1536.** Stage 6 crashed on T2: the cap was 1,536 tokens but the uniform stream held only 1,024. It was
   fixed (the first 1,024 uniforms are unchanged) and the stage resumed.
7. **D-style-regate.** The array-scan O(V²) Dijkstra probe gets 'unknown' from the mechanical exp8 rules, and the
   judges then call it 'other' or 'bf_spfa'. No rule revision was made. The consequence is conservative for Claim B.
8. **D-power-extension.** An outcome-blind extension to N = 100 on the decisive tasks, reported as a sensitivity only.

## Limitations

- **Claim B is tested on the 15 screen tasks** (seen in iteration 4), not on held-out units.
- **Inference is conditional on five prompt templates per task.** The transplant is deterministic per template, so each
  task has only 5 distinct interventions.
- **The base model under the chat template is out of distribution.** T1 has only 14 correct base programs, so its beta
  rests on parseable attempts (flagged ATTEMPT). Several strata sit near the 0.05 / 0.2 cuts: T06's stratum stability
  is 0.55 and R6's is 0.53.
- **The isotropic MR control is the weaker contrast.** At lambda = 1, about 71% of the hooked cells exceed the
  iteration-4 breakage dose. This is consistent with iteration 4, where isotropic pushes moved T03 at
  alpha 1–2: MR beating T on T03 says that the base direction is less disruptive than a random one.
- **The engine check is a precision sensitivity, not a reproduction.** This run is bf16; the iteration-4 screen rows
  are FP8.
- **Manual novelty adjudication** was done by reading all 48 programs. It is encoded as explicit rules in
  `src/manual_novelty.py`.

## Layout

| Path | What |
|---|---|
| `method.py` | stage CLI: `--stage 0/1/2/3/4/5/8/all` (resumable) |
| `src/cfg.py` | constants and paths (derived from exp19 `cfg.py`) |
| `src/prompts5.py` | 75 twin prompts (exp22 ids re-rendered and asserted), plain-completion prompts, forced prompts, position and grep audits |
| `src/base_vllm.py` | Stage 1.3 base sampling (vLLM) and top-up |
| `src/labels5.py` | label worker: ITER1 base extraction, then the iteration-4 labellers |
| `src/engine_v4.py`, `src/label_worker_v4.py`, `src/s0_checks_v4.py`, `src/commit.py` | vendored iteration-4 code, verbatim |
| `src/engine5.py` | `engine_v4` + base stop ids + the 'base' fence (diff in `results/engine_diff.txt`) |
| `src/hooks5.py` | SET / MR / XT / DS / ISO / EC edits |
| `src/gpu5.py` | GPU stages `instr1`, `base1`, `instr2`, `instr3` |
| `src/analysis_b.py` | frozen statistics and decision rules (sha256 in COMMIT #0) |
| `src/commits5.py` | COMMIT #0 / #1 / #2 |
| `src/analysis_final.py`, `src/geometry5.py`, `src/figures5.py`, `src/report5.py`, `src/outputs5.py` | analyses, geometry, figures, `results/summary.md`, `method_out.json` |
| `src/audit5.py`, `src/manual_novelty.py`, `src/dep_usage.py` | judge audits, novelty adjudication, dependency usage |
| `src/vendor/` | pristine copies of the prior code used (exp19, exp20, exp22, exp23, ITER1 exp5) |
| `inputs/` | frozen input copies (bench, exp8 suite, exp13/17/18 files, exp20/22/23 results, the screen, ITER1 base rows) |
| `predictions/` | commits, precision rule, rendered prompts |
| `data/` | raw rows (`*_raw.jsonl`), labels, `samples.jsonl` (one row per program, 14,280 rows), judge caches |
| `results/` | every analysis JSON, `summary.md`, timing, costs, deviations |
| `figures/` | `fig1`–`fig6` (PNG + PDF) |
| `audit/rederive.py` | independent re-derivation of the rule inputs and tests (56 checks) |
| `audit/rederive_headlines.py` | second re-derivation of every headline number from the raw label rows, with placebos (34 checks) |
| `tests/test_cpu.py` | hook-math and statistics tests |
| `tools/` | model download, GPU stage chaining, a fallback mini/preview writer |
| `pyproject.toml`, `requirements-vllm.txt` | exact pins of `.venv` (83 packages) and `.venv_vllm` |
| `reproducibility.md` | the exact commands, order, seeds, hardware and runtimes of this run |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | exp_gen_sol_out output (schema-validated; variants from the aii-json formatter) |
| `cache/states/`, `cache/geometry/` | activation tensors (6.3 GB + 232 MB). **Kept on the run's volume, not in the published repository.** |

## How to run

```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
uv venv .venv_vllm --python 3.12 && uv pip install --python .venv_vllm/bin/python vllm==0.11.0 transformers==4.57.6 tokenizers==0.22.2 loguru==0.7.3
uv run --no-project --with huggingface_hub==0.36.2 --with hf-xet==1.7.0 python tools/download_models.py   # both pinned models
export OPENROUTER_BASE_URL=... OPENROUTER_API_KEY=...                                                    # judges only
.venv/bin/python method.py --stage all          # or stage by stage; every stage is resumable
```

The prior-iteration source paths are only read in Stage 0. They are found relative to this folder, or through
`AII_ITER1_DIR`, `AII_ITER2_DIR`, `AII_ITER4_DIR` and `ART_J3RM_DIR`.

## Restoring removed files

The `.aii/manifest.yaml` delete entries are rebuilt with:

- `.venv/`: `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `.venv_vllm/`: `uv venv .venv_vllm --python 3.12 && uv pip install --python .venv_vllm/bin/python vllm==0.11.0 transformers==4.57.6 tokenizers==0.22.2 loguru==0.7.3`
- `**/__pycache__/`: recreated automatically on import (`python -m compileall src`).

Model weights live in the run's shared Hugging Face cache, outside this folder. To fetch them again, run
`tools/download_models.py`, which downloads `Qwen/Qwen3-8B@b968826d…` and `Qwen/Qwen3-8B-Base@49e3418f…`.

The kept artifacts (`cache/states/`, `cache/geometry/`) stay on the run's volume. To regenerate them without the
volume, run `src/gpu5.py instr1` and `base1`. This takes about 5 GPU-minutes, and the prefills are deterministic on
the same GPU and precision.

## Publishing note

`cache/` holds 150 activation files of about 59 MB each (6.3 GB in all). They sit below the 100 MB publish cut, so they
must be excluded explicitly. Upload-ignore patterns: `(^|/)cache/` and `(^|/)\.venv[^/]*/`. The tensors stay on the
run's volume at `cache/states/` and `cache/geometry/`, relative to this folder.

## Full results tables (generated by `src/report5.py` from `results/*.json`)

### Base repertoire and strata (COMMIT #1)

| Task | instruct default (twin S1 share) | base correct / N | beta_t [95% CI] (basis) | stratum (stability) | r_t | beta plain | base Hill-1 (d25) |
|---|---|---|---|---|---|---|---|
| T03 | full_sort (1.00) | 47/100 | 0.43 [0.33, 0.49] (CORRECT) | BASE-DIVERSE (1.00) | quickselect | 0.10 | 3.03 |
| T2 | dijkstra (1.00) | 44/200 | 0.41 [0.33, 0.55] (CORRECT) | BASE-DIVERSE (1.00) | bf_spfa | 0.32 | 2.12 |
| T05 | hash_map (1.00) | 49/100 | 0.16 [0.12, 0.21] (CORRECT) | INTERMEDIATE (0.92) | brute_force | 0.69 | 1.63 |
| T10 | union_find (1.00) | 55/200 | 0.65 [0.58, 0.76] (CORRECT) | BASE-DIVERSE (1.00) | dfs | 0.81 | 2.34 |
| T06 | hash_set (1.00) | 51/100 | 0.20 [0.10, 0.29] (CORRECT) | INTERMEDIATE (0.55) | index_marking | 0.33 | 2.34 |
| T1 | bfs (1.00) | 14/200 | 0.38 [0.32, 0.44] (ATTEMPT) | BASE-DIVERSE (1.00) | dfs | 0.21 | 1.82 |
| T04 | naive (1.00) | 52/100 | 0.12 [0.05, 0.16] (CORRECT) | INTERMEDIATE (0.99) | builtin | 0.27 | 1.42 |
| T08 | iteration (1.00) | 37/100 | 0.16 [0.09, 0.22] (CORRECT) | INTERMEDIATE (0.90) | memo_recursion | 0.08 | 1.55 |
| T11 | quadratic_dp (1.00) | 43/100 | 0.09 [0.05, 0.12] (CORRECT) | INTERMEDIATE (0.99) | patience_bisect | 0.00 | 1.36 |
| T13 | sort_sweep (1.00) | 40/100 | 0.00 [0.00, 0.00] (CORRECT) | BASE-COLLAPSED (1.00) | None | 0.00 | 1.00 |
| T14 | sort_by_count (1.00) | 31/100 | 0.35 [0.26, 0.41] (CORRECT) | BASE-DIVERSE (1.00) | heap | 0.07 | 1.91 |
| R1 | greedy_end (1.00) | 42/200 | 0.00 [0.00, 0.00] (CORRECT) | BASE-COLLAPSED (1.00) | None | 0.06 | 1.00 |
| R3 | kahn (1.00) | 40/100 | 0.03 [0.00, 0.07] (CORRECT) | BASE-COLLAPSED (0.88) | dfs_postorder | 0.39 | 1.12 |
| R6 | binary_search (0.96) | 40/100 | 0.05 [0.00, 0.12] (CORRECT) | INTERMEDIATE (0.53) | bisect_module | 0.00 | 2.17 |
| R2 | dfs_parent (1.00) | 43/200 | 0.16 [0.07, 0.23] (CORRECT) | INTERMEDIATE (0.80) | union_find | 0.15 | 1.63 |

### Stage 3 selection on S1 (pass / correct off-default share; N = 50 for T, 30 for MR and READ)

| Task | stratum | twin | T(0.25) | T(0.5) | T(1) | MR(0.25) | MR(0.5) | MR(1) | READ(1) | EARLY(1) | LATE(1) | lambda* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T03 | BASE-DIVERSE | 1.00 / 0.00 | 1.00 / 0.02 | 1.00 / 0.00 | 1.00 / 0.06 | 1.00 / 0.10 | 1.00 / 0.07 | 0.97 / 0.34 | 0.97 / 0.00 | 1.00 / 0.30 | 1.00 / 0.04 | 1.00 |
| T2 | BASE-DIVERSE | 0.98 / 0.00 | 1.00 / 0.00 | 0.72 / 0.06 | 0.54 / 0.04 | 0.97 / 0.03 | 0.93 / 0.07 | 0.90 / 0.00 | 0.00 / – | 0.98 / 0.00 | 0.88 / 0.02 | 0.25 |
| T05 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.03 | 0.43 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T10 | BASE-DIVERSE | 1.00 / 0.00 | 1.00 / 0.04 | 1.00 / 0.12 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.03 | 1.00 / 0.10 | 0.17 / 0.20 | 1.00 / 0.28 | 1.00 / 0.00 | 0.50 |
| T06 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.17 | 0.37 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T1 | BASE-DIVERSE | 0.86 / 0.00 | 0.72 / 0.00 | 0.50 / 0.00 | 0.30 / 0.00 | 0.87 / 0.04 | 0.77 / 0.00 | 0.73 / 0.09 | 0.13 / 0.00 | 0.40 / 0.00 | 0.90 / 0.00 | 0.25 |
| T04 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T08 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.97 / 0.00 | 0.90 / 0.00 | 0.37 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T11 | INTERMEDIATE | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.93 / 0.04 | 0.53 / 0.06 | 1.00 / 0.00 | 1.00 / 0.00 | 0.25 |
| T13 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | – | – | – | 0.37 / 0.00 | – | – | – |
| T14 | BASE-DIVERSE | 0.78 / 0.00 | 0.78 / 0.00 | 0.68 / 0.00 | 0.98 / 0.47 | 0.77 / 0.00 | 0.80 / 0.08 | 0.53 / 0.19 | 0.07 / 0.00 | 0.98 / 0.00 | 0.72 / 0.00 | 1.00 |
| R1 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 0.40 / 0.00 | – | – | – | 0.30 / 0.00 | – | – | – |
| R3 | BASE-COLLAPSED | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | 1.00 / 0.00 | – | – | – | 0.13 / 0.00 | – | – | – |
| R6 | INTERMEDIATE | 0.90 / 0.00 | 0.88 / 0.00 | 0.90 / 0.00 | 0.64 / 0.00 | 0.83 / 0.00 | 0.80 / 0.00 | 0.87 / 0.00 | 0.23 / 0.00 | 0.96 / 0.00 | 0.94 / 0.00 | 0.25 |
| R2 | INTERMEDIATE | 0.94 / 0.00 | 0.98 / 0.00 | 0.98 / 0.00 | 0.90 / 0.00 | 0.90 / 0.00 | 0.77 / 0.00 | 0.43 / 0.15 | 0.17 / 0.00 | 1.00 / 0.00 | 0.96 / 0.00 | 0.25 |

### Stage 4 confirmation on fresh S2 slots (N = 50 per cell; one-sided exact McNemar on y, Holm)

| Task | lambda* | twin S2 pass | T: pass / off-share / modal | control: pass / off-share | McNemar b:c, p (Holm) | templates T > control |
|---|---|---|---|---|---|---|
| T03 | 1.00 | 1.00 | 1.00 / 0.06 / size_k_heap | MR1.0: 1.00 / 0.42 | 2:20, 1 (1) | 0/5 |
| T03 | 1.00 | 1.00 | 1.00 / 0.06 / size_k_heap | XT1.0: 1.00 / 0.00 | 3:0, 0.12 (1) | 2/5 |
| T2 | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 0.98 / 0.00 | 0:0, 1 (1) | 0/5 |
| T2 | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 0.98 / 0.00 | 0:0, 1 (1) | 0/5 |
| T10 | 0.50 | 1.00 | 1.00 / 0.08 / dfs | MR0.5: 1.00 / 0.02 | 3:0, 0.12 (1) | 3/5 |
| T10 | 0.50 | 1.00 | 1.00 / 0.08 / dfs | XT0.5: 1.00 / 0.02 | 3:0, 0.12 (1) | 3/5 |
| T1 | 0.25 | 0.88 | 0.76 / 0.00 / None | MR0.25: 0.94 / 0.00 | 0:0, 1 (1) | 0/5 |
| T1 | 0.25 | 0.88 | 0.76 / 0.00 / None | XT0.25: 0.86 / 0.00 | 0:0, 1 (1) | 0/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | MR1.0: 0.78 / 0.05 | 19:0, 1.9e-06 (1.9e-05) | 5/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | XT1.0: 0.88 / 0.11 | 17:1, 7.2e-05 (6.5e-04) | 5/5 |
| T14 | 1.00 | 0.78 | 0.98 / 0.43 / heap | MRP0.5: 0.76 / 0.00 | 21:0, 4.8e-07 (5.2e-06) | 5/5 |
| T05 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T05 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T06 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T06 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T04 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T04 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T08 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T08 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T11 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | MR0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| T11 (desc.) | 0.25 | 1.00 | 1.00 / 0.00 / None | XT0.25: 1.00 / 0.00 | 0:0, 1 (–) | 0/5 |
| R6 (desc.) | 0.25 | 0.76 | 0.78 / 0.00 / None | MR0.25: 0.80 / 0.00 | 0:0, 1 (–) | 0/5 |
| R6 (desc.) | 0.25 | 0.76 | 0.78 / 0.00 / None | XT0.25: 0.56 / 0.00 | 0:0, 1 (–) | 0/5 |
| R2 (desc.) | 0.25 | 0.84 | 0.90 / 0.00 / None | MR0.25: 0.80 / 0.00 | 0:0, 1 (–) | 0/5 |
| R2 (desc.) | 0.25 | 0.84 | 0.90 / 0.00 / None | XT0.25: 0.86 / 0.00 | 0:0, 1 (–) | 0/5 |

**Claim B (frozen rule): DISCONFIRMED** -- PASS on 1/5 decisive tasks (needed 4); (iii) fails on 4; specificity (point estimates) no, noise-robust yes.

- T03: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T2: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T10: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t yes -> PASS no
- T1: (i) pass yes, (ii) share >= 0.5 beta no, (iii) controls no, (iv) lands on r_t no -> PASS no
- T14: (i) pass yes, (ii) share >= 0.5 beta yes, (iii) controls yes, (iv) lands on r_t yes -> PASS yes

Power extension (COMMIT3_EXT, outcome-blind, descriptive; N = 100 per decisive cell): **PARTIAL** (PASS 1/5).
- T03: T pass 1.00, off-share 0.06; vs MR1.0 4:36 p=1; vs XT1.0 6:0 p=0.016
- T2: T pass 1.00, off-share 0.00; vs MR0.25 0:0 p=1; vs XT0.25 0:0 p=1
- T10: T pass 1.00, off-share 0.08; vs MR0.5 6:2 p=0.14; vs XT0.5 7:0 p=0.0078
- T1: T pass 0.68, off-share 0.00; vs MR0.25 0:0 p=1; vs XT0.25 0:0 p=1
- T14: T pass 0.99, off-share 0.49; vs MR1.0 44:0 p=5.7e-14; vs XT1.0 35:3 p=3.3e-08; vs MRP0.5 49:0 p=1.8e-15

Sensitivities: stable_stratum_only: DISCONFIRMED; noise_robust_specificity: DISCONFIRMED; power_extension_N100_verdict: PARTIAL

### Claim D (de-sharpening push along unit(D) vs isotropic, ban-free units, N = 30)

| Task | twin pass | DS 0.5 / 1 / 2 (pass, off-share) | ISO 0.5 / 1 / 2 (pass, off-share) | a_DS | a_ISO |
|---|---|---|---|---|---|
| T03 | 1.00 | 1.00, 0.00 ; 1.00, 0.00 ; 1.00, 0.00 | 1.00, 0.00 ; 1.00, 0.13 ; 1.00, 0.27 | – | 2.00 |
| T2 | 1.00 | 1.00, 0.00 ; 1.00, 0.00 ; 0.97, 0.03 | 1.00, 0.00 ; 1.00, 0.00 ; 0.90, 0.07 | – | >2 (censored) |
| T10 | 1.00 | 1.00, 0.03 ; 1.00, 0.03 ; 0.93, 0.11 | 1.00, 0.03 ; 1.00, 0.03 ; 1.00, 0.10 | – | >2 (censored) |
| T1 | 0.87 | 0.87, 0.00 ; 0.77, 0.00 ; 0.60, 0.00 | 0.93, 0.00 ; 0.70, 0.00 ; 0.77, 0.00 | – | >2 (censored) |

**Claim D: DISCONFIRMED** (PASS 0/4).

### Reverse interchange (instruct task-spec states into the base model, blocks 12-23, N = 50)

| Task | BTWIN default share (correct / attempts) | RT(1) | BMR(1) | predicted min rise | met |
|---|---|---|---|---|---|
| T10 | 0.50 / 0.38 (n_correct 18) | 0.53 / 0.55 (n_correct 19) | 0.50 / 0.36 (n_correct 16) | 0.25 | no |
| T03 | 0.65 / 0.55 (n_correct 20) | 0.74 / 0.66 (n_correct 31) | 0.56 / 0.39 (n_correct 16) | 0.17 | no |
| T2 | 0.87 / 0.63 (n_correct 15) | 0.80 / 0.74 (n_correct 20) | 0.50 / 0.41 (n_correct 6) | 0.07 | no |
| T1 | 0.80 / 0.39 (n_correct 5) | 1.00 / 0.73 (n_correct 11) | 1.00 / 0.50 (n_correct 2) | 0.10 | yes |

### Claim A screen check (descriptive; iteration-4 escape fractions)

- beta_t vs E_t (alpha_1.0): Spearman 0.78, Kendall 0.69, one-sided permutation p 2.0e-04 (n = 15)
- beta_t vs E_t (alpha_2.0): Spearman 0.79, Kendall 0.70, one-sided permutation p 4.0e-04 (n = 15)
- beta_t vs E_t (alpha_mean): Spearman 0.79, Kendall 0.71, one-sided permutation p 4.0e-04 (n = 15)
- r_t equals the iteration-4 push top-1 landing on 5/5 movable tasks

### Size of D = h_base - h_instruct

- relative norm at S, blocks 12-23 (mean over tasks): 0.39, 0.41, 0.42, 0.44, 0.44, 0.46, 0.48, 0.49, 0.51, 0.53, 0.53, 0.52
- relative norm at R, blocks 12-23: 1.06, 1.08, 1.09, 1.07, 1.06, 1.06, 0.99, 1.10, 1.07, 1.09, 1.11, 1.12
- share of hooked (l, p) above 4 ban-free units: lambda 0.25 0.00, 0.5 0.01, 1 0.71
- cross-task cosine of the per-task mean D (blocks 12/18/23/27): 12: 0.88, 18: 0.76, 23: 0.81, 27: 0.80

### Engine check (bf16 here vs the FP8 exp17 screen rows)

- T03|EC_NEUTRAL: per-slot label agreement 1.00, JS 0.000 (template-resampling null q95 0.000), within null yes
- T03|EC_RAND9002_a1.0: per-slot label agreement 0.74, JS 0.030 (template-resampling null q95 0.075), within null yes
- T2|EC_NEUTRAL: per-slot label agreement 0.98, JS 0.010 (template-resampling null q95 0.000), within null no
- T2|EC_RAND9004_a1.0: per-slot label agreement 0.88, JS 0.005 (template-resampling null q95 0.005), within null yes

### Geometry (distance of the T(lambda*) centroid; fraction of the instruct->base twin gap)

- T03 (lambda* 1.0): S18 1.00 (stress-1 0.25); S23 1.00 (stress-1 0.25); S27 0.88 (stress-1 0.22); R18 0.18 (stress-1 0.06); R23 0.30 (stress-1 0.08)
- T2 (lambda* 0.25): S18 0.25 (stress-1 0.17); S23 0.25 (stress-1 0.22); S27 0.23 (stress-1 0.21); R18 0.05 (stress-1 0.05); R23 0.07 (stress-1 0.08)
- T10 (lambda* 0.5): S18 0.50 (stress-1 0.27); S23 0.50 (stress-1 0.27); S27 0.47 (stress-1 0.23); R18 0.09 (stress-1 0.06); R23 0.15 (stress-1 0.08)
- T1 (lambda* 0.25): S18 0.25 (stress-1 0.27); S23 0.25 (stress-1 0.26); S27 0.24 (stress-1 0.23); R18 0.05 (stress-1 0.06); R23 0.07 (stress-1 0.08)
- T14 (lambda* 1.0): S18 1.00 (stress-1 0.06); S23 1.00 (stress-1 0.06); S27 0.89 (stress-1 0.08); R18 0.18 (stress-1 0.05); R23 0.31 (stress-1 0.06)

### Novelty audit

48 unique correct non-catalogue programs (every arm, base included). Judge classes (2 of 3 judges): {'NOVEL_ALGORITHM': 14, 'DISAGREE': 10, 'DEGENERATE': 14, 'CATALOGUE_VARIANT': 10}. Manual adjudication against the nearest known solution: {'KNOWN, OUTSIDE THE CATALOGUE': 27, 'DEGENERATE': 12, 'CATALOGUE VARIANT': 9}; NOVEL = 0 (rule-of-three 95% upper bound 0.062); the judges' 14 NOVEL calls are linear scans, count loops and a threshold binary search (known techniques outside the frozen catalogue).

### Re-derivation

56 checks, 0 mismatches; arm-shuffle placebo rejection 0.012; label-shuffle placebo share keeping stratum 0.27

### Compute and spend

HF engine 10860 programs (+1420 pad rows) in 1.51 GPU-h; vLLM base 3500 programs in 0.20 GPU-h; total 1.70 GPU-h. OpenRouter USD 0.287 (cap 1.5).
