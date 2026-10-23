# Reproducibility: top-five ban screen and activation-manifold landing (iteration 8)

This file describes what was **actually run**, in order, on the machine that produced the results. Every path is relative to this artifact's folder.

## 1. Getting the artifact

This workspace is published as one folder of the run's public GitHub repository.

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>        # the folder that contains method.py and this file
```

The folder already contains everything the analysis reads:

- the prior-iteration inputs in `inputs/` (checksums in `inputs/SHA256SUMS`);
- the vendored harness and labeller in `vendor/`;
- every raw generation in `data/raw_*.jsonl` and every labelled row in `data/labelled_*.jsonl`;
- the judge cache `data/judge_cache.jsonl` and the sandbox cache `data/program_eval_cache.jsonl`;
- all results, figures and commitments.

The large activation-state files (`cache/states/smean_*.npz`, 98-181 MB each) are **not** in the repository. They stay on the run's storage volume and are rebuilt by the `states` and `quantcheck` stages (section 4).

No user-uploaded input is used. The run's `user_uploads` folder was empty.

## 2. System, Python and libraries

| Item | What was used |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) container on Linux 6.8. Ubuntu 22.04/24.04 works the same way. |
| GPU | 1x NVIDIA RTX 2000 Ada Generation, 16 GB VRAM, driver 595.91.07 (CUDA 12.8 wheels) |
| CPU / RAM | 6 vCPU (AMD EPYC 7443), 28 GB RAM (cgroup limit) |
| C compiler | None. vLLM therefore ran with `--enforce-eager` (no torch.compile / CUDA graphs). |
| Python | CPython 3.12.14 (`python3.12` on PATH). The sandbox harness runs candidates with `python3.12 -I -S`; override with `SANDBOX_PYTHON`. |
| Package manager | uv 0.6.14 (the venv has no pip) |
| Libraries | 179 packages pinned in `pyproject.toml` and `requirements.lock.txt` (identical lists), e.g. vllm 0.11.0, torch 2.8.0 (+cu128), transformers 4.57.6, bitsandbytes 0.50.2, accelerate 1.15.0, scikit-learn 1.9.1, scipy 1.18.1, numpy 2.2.6, networkx 3.x, ripser 0.6.15, zss 1.2.0, aiohttp 3.14.5, loguru 0.7.3, matplotlib 3.11.2 |

```bash
sudo apt-get install -y python3.12            # or any CPython 3.12 build; no compiler is needed
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python -c "import vllm, torch, transformers, bitsandbytes, sklearn, scipy, ripser; print(torch.cuda.is_available())"
```

`restore.sh` does the venv and model steps in one go.

## 3. Downloads, environment variables and keys (names only)

**Model weights** come from the Hugging Face Hub. Only these three are loaded locally, and the revisions are pinned in `src/common.py` (`REVISIONS`):

| Repo | Revision | Used for |
|---|---|---|
| `Qwen/Qwen3-8B-FP8` | `220b46e3b2180893580a4454f21f22d3ebb187d3` | C1 sampling in vLLM (W8A16 Marlin) |
| `unsloth/Qwen3-32B-bnb-4bit` | `7f721e74a6a8cc9ee352f7e49303a2c1705f9083` | m* = C6 states (nf4) |
| `Qwen/Qwen3-8B` | `b968826d9c46dd6066d109eabc6255188de91218` | Quantisation check (bf16 / int8 / nf4 on the fly) and the T7 check |

All other models are reached through OpenRouter with pinned providers (`src/sample_or.py: PROVIDER_PINS`):

- `meta-llama/llama-3.1-8b-instruct`: CoreWeave bf16
- `qwen/qwen3-14b` and `qwen/qwen3-32b`: DeepInfra fp8
- `google/gemma-3-27b-it`: DeepInfra fp8
- `qwen/qwen-2.5-coder-32b-instruct`: Cloudflare

Judges: `deepseek/deepseek-chat-v3.1`, `moonshotai/kimi-k2` and `mistralai/mistral-medium-3.1`. `google/gemini-2.5-flash-lite` was gated and failed.

**Environment variables:**

| Name | Needed for |
|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | Every OpenRouter call: sampling, judges, novelty |
| `HF_HOME` / `HF_HUB_CACHE` | Optional: where Hugging Face weights are cached |
| `TP_DEPS_DIR`, or one `TP_DEP_<KEY>` per input artifact | Only for re-copying `inputs/` from the prior artifacts (default: sibling folders named by artifact id: `art_IVZc3TWCeE9f`, `art_D6Z0Snf09sFL`, `art_pHL7LWNhpcCS`, `art_lpQalcAXMGr1`, `art_zNyBP6zieI5u`, `art_j3Rm_lr2nzR6`). Stage 0 skips the copy when `inputs/SHA256SUMS` verifies. |
| `TP_COST_CAP` | Optional: artifact OpenRouter cap in USD (default 3.0) |
| `SANDBOX_PYTHON` | Optional: interpreter for candidate programs |

## 4. Commands in the order they were run

Each stage is `.venv/bin/python method.py <stage> [args]` (`uv run method.py <stage>` is equivalent). Logs go to `logs/`, timings to `results/timing.jsonl`, and the OpenRouter spend to `results/costs.json`.

**Decoding and seeds.**

- Sampling: T = 1.0, top-p = 1.0, no top-k (min-p 0, no penalties); set explicitly per request, because vLLM otherwise applies Qwen's `generation_config`.
- max_tokens: 1,536 with thinking off and 9,728 with thinking on (OpenRouter). Local C1 uses a two-phase budget: 8,192 thinking tokens, a forced `</think>`, then 1,536 answer tokens.
- Seeds: vLLM seed = slot index. OpenRouter seed = slot + 1, best effort (providers may ignore it).
- Judges run at temperature 0. Bootstrap seed is 0; the U/F/C nulls use seeds 0/1/2.

**OpenRouter sampling is not bit-reproducible.** Provider-side batching makes a rerun draw a new sample. The record of the run is `data/raw_*.jsonl`, and every analysis below is deterministic given those rows.

| # | Command | What happened | Approx. time |
|---|---|---|---|
| 1 | `method.py stage0` | Hardware record, inputs copy + `inputs/SHA256SUMS`, carried rows, renderer byte check (identical to iteration 2's TOP5 W1 prompt), labeller re-validation (15/15 T1 references, 71/78 gold, 2/2 mutants fail) | 1 min |
| 2 | `vllm serve` for C1 (command below) | Server for Qwen3-8B-FP8 on port 8044; 37,392 KV tokens | 3 min load |
| 3 | `method.py smoke`, then `method.py smoke2` | Mocked-403 stop test (pass); judge gate (gemini 7/10 fails, deepseek 9/10, kimi-k2 10/10, mistral-medium 9/10); 3 calls per configuration. Fixes applied after smoke: `' /no_think'` for C3/C5, OpenRouter seed + 1, C7 → gemma-3-27b-it (deviations D10-D13) | 15 min |
| 4 | `method.py commit1` | Pre-registration `predictions/commit1.json` → `commitments.log` line 0 | <1 min |
| 5 | `method.py screen_base_local` ‖ `method.py screen_base_or` | Baselines: C1 30 rows (local); C2-C8 100 rows each (C7 got 99, one call failed after retries) | 29 min / 25 min |
| 6 | `method.py label baseline C2,C3,C4,C5`, then `... C6,C7,C8`, then `... C1` | Sandboxed hidden tests (48-case primary, 41-case secondary), runtime + AST rules, deepseek judge on disagreements | 2 min each |
| 7 | `method.py commit2` | Baseline review-class adjudication, B_c = {BFS, DFS, IDDFS, A*, greedy} for every configuration, ban prompts hashed; C1 N_ban cut to 30 (D15) → line 1 | 2 min |
| 8 | `method.py screen_ban_local` ‖ `method.py screen_ban_or` | Ban arms: C1 30, C2-C8 50 each (W1/W2/W3) | 35 min / 15 min |
| 9 | `method.py adjudicate ban C2,C3`; `... C4,C5,C7,C8`; `... C6` | Gated pair + third judge; audit-triggered full adjudication for C5 and C6 | 25 min (kimi-k2 timeouts) |
| 10 | Executor manual reads → `data/manual_reads.jsonl`; then `method.py adjudicate ban C2,C5,C8` and `... C6` again | Three-way splits resolved by reading the code (reasons logged); judge calls cached | 5 min |
| 11 | `bash run_after_screen.sh` | Waits for the C1 sampler, stops vLLM by PID, `adjudicate ban C1`, `select` (commit #3, line 2: m* = C6). Its `states` step failed twice on the pre-quantised checkpoint; fixed in `src/states.py` | 5 min |
| 12 | `bash run_resume_states.sh` | `states` (Qwen3-32B nf4, 48/64 blocks, 317 prompts), `geometry` (L*, M1, reliability, landing, robustness, F2-F4, F6), `confirm` (commit #4, line 3, then 50 held-out rows on OpenRouter, run in parallel), `m2` (59 programs), `quantcheck` (failed once on the embedding check; rerun), `circle` | 6 + 13 + 20 + 6 + 3 min |
| 13 | `method.py quantcheck` | Qwen3-8B bf16 / int8 / nf4 states and comparison (F8) | 8 min |
| 14 | `method.py screen_table`, `novelty`, `figures`, `refig`, `checks`, `t7`, `t8` | Sensitivity fields, novelty audit, F1/F7, re-rendered F2-F4/F6 + prompt-state placement, consistency checks, T7/T8 tests | 15 min |
| 15 | `.venv/bin/python src/rederive.py` and `.venv/bin/python audit_headlines.py` | Independent re-derivations (0 mismatches) and placebos | 3 min |
| 16 | `method.py outputs`, then the aii-json format script on `method_out.json` | `method_out.json` + `full_`/`mini_`/`preview_` variants, schema exp_gen_sol_out (validated) | 1 min |

vLLM server command (step 2):

```bash
VLLM_TEST_FORCE_FP8_MARLIN=1 .venv/bin/vllm serve Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3 \
  --max-model-len 10240 --gpu-memory-utilization 0.92 --enforce-eager --port 8044 --seed 0 --max-num-seqs 32 \
  --served-model-name qwen3-8b-fp8
```

**Shortest path to the published numbers without new sampling.** Uses the published `data/` rows plus a GPU for the states:

```bash
.venv/bin/python method.py states && .venv/bin/python method.py geometry && .venv/bin/python method.py m2
.venv/bin/python method.py quantcheck && .venv/bin/python method.py circle && .venv/bin/python method.py refig
.venv/bin/python src/rederive.py && .venv/bin/python audit_headlines.py && .venv/bin/python method.py outputs
```

Do not re-run `commit*`, `select` or `confirm` on the published folder. They append to the hash chain and, for `confirm`, sample again.

## 5. What a reader should get, and where

| Number | Value | File |
|---|---|---|
| Correct-survivor share under the five-name ban, per configuration | C6 Qwen3-32B thinking on 17/50 = 0.34 (Wilson 0.22-0.48); C4 0.14; C5 0.08; C1, C2, C3, C7, C8, C9, C10 all 0.00 | `results/screen.json`, `figures/F1_screen_forest.*` |
| Selection | Q = {C6}; m* = C6 (commit #3) | `results/selection.json`, `predictions/commit3.json` |
| Layer | L* = 31 of 64 (all blocks 19-45 at balanced accuracy 1.00; ceiling rule) | `results/geometry_M1.json` |
| Manifold | PCA 32.4% / 12.0%; MDS stress-1 0.42 (points) and 0.28 (centroids); Isomap components 8 / 3 / 1 at k = 5 / 10 / 15 | `results/geometry_M1.json`, `figures/F2-F4` |
| Landing (k = 15) | 6/6 catalogue survivors are unit Dijkstra; g = 21.59 (largest, OPPOSITE); p_opp: U 1e-4, F 1e-4, C 0.057, P 0.20 (floor); verdict OPPOSITE; NOT ROBUST (10/15) | `results/landing.json`, `results/landing_robustness.json`, `figures/F6_*` |
| Confirmation (held-out templates) | 21/50 = 0.42; 9/9 catalogue survivors unit Dijkstra; OPPOSITE; CONFIRMED | `results/confirmation.json`, `figures/F7_*` |
| Quantisation check | Spearman 0.954 (int8) and 0.916 (nf4) vs bf16; class agreement 5/5 | `results/quant_check.json`, `figures/F8_*` |
| Novelty | 0 novel among 27 audited correct programs (rule-of-three bound 3/661) | `results/novelty_audit.json` |
| Re-derivation | 0 mismatches (`rederive.py`); `audit_headlines.py` reproduces every count, the Wilson intervals, g (diff 1e-12) and S, with an exact uniform p_opp of 6.4e-5 | `results/rederive.json`, `results/audit_headlines.json` |
| Spend | USD 1.53 on OpenRouter | `results/costs.json` |

The paper-facing claims, deviations and caveats are summarised in `README.md`, sections 1-8 and "Deviations".
