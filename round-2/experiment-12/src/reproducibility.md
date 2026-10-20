# Reproducing "Reading a coding ban inside the model"

This file describes what was actually run on 2026-10-20, in order. All paths are relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/gen_art_experiment_12   # this folder
```

## 2. System, Python and libraries

- **OS and tools:** Ubuntu (container), NVIDIA driver with CUDA 12.8 support, `uv` (any recent version).
- **Hardware used:** one **NVIDIA RTX 2000 Ada, 16 GB** (15.58 GiB usable) and a cgroup quota of ~5 CPUs and **31 GB RAM**. The host reports more; the cgroup limits are what count.
- **Python:** 3.12.14.
- **Libraries:** every package is pinned in `pyproject.toml` to the exact version in the `.venv` used (173 packages, including torch 2.8.0+cu128, vllm 0.11.0, transformers 4.57.6, accelerate 1.15.0, scikit-learn 1.9.1, numpy, scipy, pandas, loguru, openai, matplotlib).

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r pyproject.toml
```

- **No system C compiler:** Triton in vLLM needs one. `method.py` sets `CC=tools/zigcc`, a shim around the pinned `ziglang` wheel.
- **vLLM mode:** vLLM runs with `enforce_eager=True`, because torch.compile / inductor failed on this machine.

## 3. Data, models and environment variables

- **Models**, downloaded into the standard Hugging Face cache via `HF_HOME`:
  - `Qwen/Qwen3-8B` (bf16; all states, attention and CE readouts)
  - `Qwen/Qwen3-8B-FP8` (all vLLM generation, deviation D01)
  - `Qwen/Qwen3-8B-Base` (transfer test)
  - `Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50`, files `layer15.sae.pt`, `layer20.sae.pt` and `layer27.sae.pt`; these layers are picked by the B3 rule before any SAE download
  - `senku21x/cot-oracle-jlens`, files `Qwen3-8B/lens.pt` and `lens.meta.json`

  The download commands are in `README.md` under "Restoring removed files".
- **Environment variables (by name only):**
  - `HF_HOME` / `HF_HUB_CACHE`: cache location.
  - `HF_TOKEN`: optional.
  - `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`: the blind judge, `openai/gpt-4.1-mini`, which labels only programs whose runtime and AST labels disagree. USD 0.042 was spent.
  - `ITER1_GEN_ART`: the folder holding the iteration-1 artifacts. The default, set in `src/core.py`, is the run's sibling layout `../../../../run_4VFKidE1bxPG/3_invention_loop/iter_1/gen_art` relative to the runs directory.
- **Input artifacts:**
  - `art_j3Rm_lr2nzR6` (`gen_art_dataset_1`, published as a sibling folder) supplies `concreteness_norms`, the neutral-noun bank for the {N} filler. It is read once by `src/prompts.py`, which caches it in `prompts/noun_bank_cache.json`.
  - The iteration-1 exp1 suite and labeller, exp3 meta and labeller, and exp6 analysis code are copied into `inputs/`.
  - The exp3 activation states (`gen_art_experiment_3/states/T{1,2}_part_*.npz`, about 800 MB) are **read in place** through `ITER1_GEN_ART` and are not part of this folder. Stage B needs them.
- **No user-uploaded inputs** were used.

## 4. Commands, in the order they were run

| # | Command | What it does | Seeds / config | Approx. time |
|---|---|---|---|---|
| 1 | (stage A, earlier session) | Copy inputs; build `prompts/prompts_v2.json` | neutral filler {N}: T1 "man or guy or house or baby" (7 tokens = X), T2 "man or scotch" (4 tokens) | - |
| 2 | `uv run method.py --stage B` | B2 layer probe (LOPO, 200 within-paraphrase permutations); B3 layer choice -> [15, 20, 27]; B4 SAE alignment; B5 nested discovery (15 configs) | permutation seeds per layer | 4 + 2 + 5 min (CPU) |
| 3 | `C1_PER_TEMPLATE=20 CRN_SEEDS_N=30 GUMBEL_SEEDS_N=0 uv run method.py --stage vllm1` | C1 fresh pool (W1–W5 ban x 20 x 2 tasks, T=1.0, top_p=1, max 1024, thinking off); E5 CRN (480 rows) + determinism rerun (8 rows) | fresh pool seeds 20261020+i; CRN U[seed] = default_rng(seed).random(1024), seeds 0..29 | 6 min GPU |
| 4 | `uv run method.py --stage vllm2 --part traces --n 5` | C2 base traces, W1 ban, thinking on, T 0.6 / top-p 0.95 / top-k 20, max 9600 | trace seeds 7000+id (t1 ids 0–4, t2 ids 100–104) | 19 min GPU |
| 5 | `uv run method.py --stage label` | Canonical labeller (hidden tests + tracer + runtime/AST rules + judge on disagreement); commit locator check (20/20) | - | 2–3 min |
| 6 | `uv run method.py --stage hf` | Checks (identity/zero splice, eager vs SDPA attention); E2 (200 runs x ban/mention/neutral, same continuation); prompt-only passes; E1 instruct (clean + 3 splices); E4 J-lens gate + application; E1 base | transfer corpus: exp1 samples, `default_rng(0)` choice of 50 per cell | 22 min GPU |
| 7 | `uv run method.py --stage vllm2 --part resample --n 4` | C3: 4 traces/task x 9 points x 6 continuations, chunks of 384 tokens (≤ 4) | continuation seeds 9000+trace*1000+k*10+j (+100000 per chunk) | 8 min GPU |
| 8 | `uv run method.py --stage vllm2 --part complete --n 1` | C4: one random continuation per resampled trace run to the end | `random.Random(4)`; seed + 500000 | 9.5 min GPU |
| 9 | `uv run method.py --stage label` | Labels C2 traces / C3 / C4 | - | 1.5 min |
| 10 | `uv run method.py --stage analyse` | E3 readouts (i) replication (+ nested selection in the fresh pool, 100 permutations), (ii) attention (2,000 permutations), (iii) prime-veto, latent contexts, transfer verdicts (2,000 bootstraps), J-lens summary, D1 | bootstrap seeds fixed in code | 6 min CPU |
| 11 | `uv run method.py --stage anchors` | D1 rerun after C4 labels (early-label validity) | 10,000 multinomial pairs per sentence | < 1 min |
| 12 | `uv run method.py --stage final` | A2 labeller check, fresh-pool and same-seed (D2) summaries, 0e record, `method_out.json` | - | 1 min |
| 13 | `uv run method.py --stage figures` | `figures/*.png|pdf` | - | < 1 min |
| 14 | `uv run method.py --stage verify` | `src/verify_headlines.py`: independent re-derivation and placebo checks | - | 1 min |
| 15 | `uv run method.py --stage final` | Re-embeds the verification record in `method_out.json` | - | 1 min |
| 16 | `aii_json_format_mini_preview.py --input method_out.json` | `full_` / `mini_` / `preview_method_out.json` | - | seconds |

The GPU time logged in `results/timing.json` is about 1.05 h, excluding earlier interrupted sessions. Memory notes:
- vLLM and the HF model never share the GPU.
- The HF block keeps `embed_tokens` on the CPU and moves `lm_head` to the CPU while an SAE is on the GPU (deviation D08).
- `tools/memwatch.sh` kills only registered PIDs when anonymous memory exceeds 26 GB.

## 5. Expected outputs and numbers

| File | Number a reader should get |
|---|---|
| `results/fresh_pool_summary.json` | banned share: T1 0.15 (W4: 15/20), T2 0.13 |
| `results/labeller_check.json` | 0.965 agreement on 141 gold programs |
| `results/locator_check.json` | 20/20 commit indices match exp3 |
| `results/layer_probe.json` | chosen layers [15, 20, 27]. Controls: k_post within-paraphrase DiM AUC max 0.75 (T1) / 0.79 (T2), a weak positive control because the commit token is mostly ` deque` for both classes; R 0.37–0.62 (≈ 0.5) |
| `results/sae_alignment.json` | relative MSE minimal at L for each SAE (0.127 at L15 vs 0.156/0.155 at L14/L16) |
| `results/transfer_test.json`, `results/transfer_summary.json` | dCE ratios 3.29 / 1.95 / 1.59: all three layers fail the ≤ 1.5 rule |
| `results/readout_i_discovery.json` | e.g. t2 L27 k16 within-paraphrase AUC: SAE top-1 0.856, DiM 0.810 (0.796 if recomputed in float64; see `verify_headlines.json`) |
| `results/readout_i_replication.json` | DiM within-template AUC at k_pre: T1 0.93 / 0.97 / 1.00, T2 0.66 / 0.66 / 0.76 |
| `results/readout_ii_attention.json` | top ban-specific head L21H17 on both tasks |
| `results/readout_iii_prime_veto.json` | pattern absent in 6/6 configs |
| `results/thought_anchors.json` | T1 D_0 = 1.0 in 4/4 traces; early-label validity 13/16 |
| `results/same_seed.json` | idea change 0/30 in 10/12 cells; phrasing change same-seed < different-seed |
| `results/jlens.json`, `results/jlens_summary.json` | gate failed (L27 top-1: 0.104 J-lens vs 0.291 logit lens) |
| `results/nla_jlens_search.json` | dated 0e record (NLA not available for Qwen3-8B) |
| `results/verify_headlines.json` | 69 checks, 0 mismatches |

Generation uses vLLM, whose batching is not bit-deterministic. The determinism rerun reproduced 5 of 8 rows byte-for-byte, so regenerated texts can differ slightly. The analyses from the stored raw files are deterministic.
