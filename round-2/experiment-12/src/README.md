# Reading a coding ban inside the model (Qwen3-8B)

A **descriptive** readout study of what happens inside Qwen3-8B when a coding prompt forbids the model's default
algorithm. Two tasks come from the canonical iteration-1 suite: T1 grid path, where BFS is banned, and T2 weighted
shortest path, where Dijkstra is banned. Every readout sits next to a matched baseline on identical rows and folds.
Nothing here is a confirmatory test.

| Arm | What ran | Baseline(s) beside it |
|---|---|---|
| 5c SAE readout (i) | Qwen-Scope `Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50` at layers 15/20/27. Discovery on exp3 states (nested leave-one-paraphrase-out, 200 within-paraphrase permutations, max-statistic null). Replication on a fresh 200-run protocol-v2 ban pool. | DiM, raw-residual logistic probe, top-20 raw dimensions ("neurons"), DiM on the SAE code |
| SAE transfer test | Spliced-in CE, base vs instruct, 200 exp1 sequences | base model with the same splice |
| (ii) attention to the ban | k_pre-query attention to the condition segment: ban prompt vs mention / neutral twins, same teacher-forced continuation, 36 x 32 heads | neutral twin (same token count), mention twin |
| (iii) prime-veto | NAME(X) / NAME(X') / IMPL latent sets plus the DiM projection at R, k_pre and the generated-token mean | neutral and mention twins, DiM |
| 5d thought anchors | 10 thinking-on W1-ban traces; 4 traces/task x 9 resample points x 6 continuations (432); 8 validation completions | multinomial noise floor (10,000 simulated pairs) |
| 5e same-seed CRN | 30 seeds x T{0.3,0.7,1.0,1.3} x {baseline, W1 ban} x 2 tasks (480 rows); inverse-CDF coupling over the sorted top-10 | different-seed pairs |
| 0e NLA / J-lens | NLA: dated "not available for Qwen3-8B". J-lens: community lens gated against the logit lens. | logit lens on the same states |

## Key results

All numbers are from `results/*.json`; the headline numbers are re-derived by `src/verify_headlines.py`.

- **Fresh ban pool.** Banned-approach share was 0.15 for T1 (Wilson 0.09–0.23) and 0.13 for T2 (0.08–0.21), and both pass the event gate. The share depends strongly on the template: on T1, W4 ("BFS is not allowed here.") gives 15/20 BFS, while the other templates give 0/20. The commit locator reproduced exp3's `commit_idx` on 20/20 rows.
- **SAE transfer test fails at all three layers** (F4). dCE_inst/dCE_base is 3.29 [3.14, 3.45] at L15, 1.95 [1.84, 2.06] at L20 and 1.59 [1.50, 1.67] at L27, against a pass threshold of 1.5. Relative reconstruction MSE is similar for the two models (0.20 vs 0.17 at L15). The instruct model's clean CE on its own code is far lower (0.030 vs 0.26 nats), so the same reconstruction error costs more CE. **Every latent result below is therefore labelled "transfer failed: latents computed on out-of-distribution activations", and the DiM baselines lead.**
- **Positive and negative controls of the layer probe.** The k_post control is weak: within-paraphrase DiM AUC peaks at only 0.75 (T1) and 0.79 (T2). exp3's commit token is the ` deque` import line for most rows of *both* classes (T1 DFS 55/78, T2 Bellman-Ford/SPFA 78/80; see `confounds` in `results/layer_probe.json`). The 'identifying token' therefore often does not identify the algorithm, and k_pre/k_post readouts mean 'state at the first lexicon match', not 'state at the algorithm decision'. R within-paraphrase AUC is 0.37–0.62: identical prompts, so 0.5 plus float noise.
- **Readout (i), discovery on exp3 states.**
  - T2 (Dijkstra vs Bellman-Ford/SPFA) is decodable at k_pre and k16 with every method. Within-paraphrase held-out AUC is 0.67–0.86 with permutation p ≤ 0.025. At L27 k16: top-1 latent 0.856, DiM 0.810, raw logistic 0.838, top-20 neurons 0.806. All 20 in-sample top latents pass the max-statistic null.
  - T1 (BFS vs DFS) is not decodable within paraphrase at the commitment point. Most p-values exceed 0.05, no latent passes the max-statistic null, and there are only 57 within-paraphrase pairs.
  - SAE latents never beat DiM or the neurons by a margin outside the CIs. This matches AxBench and MIB.
- **Readout (i), replication** (exp3-fitted objects applied to the fresh pool's k_pre states). DiM transfers best:
  - T1: within-template AUC 0.93 / 0.97 / 1.00 at L15 / L20 / L27. Only W4 holds both classes (15 vs 5), so this rests on 75 pairs. The single top latent reaches 0.27 / 0.80 / 0.52.
  - T2: DiM 0.66 / 0.66 / 0.76, and the top-20-latent probe 0.65 / 0.66 / 0.77.
  - The top-20 latent lists overlap above chance for T1 k_pre (8 vs 1.8 expected at L15) and at chance for T2.
  - Shuffled labels give AUC ≈ 0.50.
- **Readout (ii), attention.** The same three heads carry the ban-specific attention on both tasks: L21H17, L26H21 and L26H25. L21H17 sends +0.207 (T1) and +0.098 (T2) more of the k_pre query's attention mass to the ban segment than to the neutral segment. The mass sits on the banned name's tokens (" breadth", "-first", "ijkstra"). On T1, compliant runs put more top-head attention on the ban than non-compliant runs: 0.135 vs 0.105, within-template permutation p = 0.0025. All non-compliant runs are in W4, so this is a within-W4 contrast. T2 shows no difference (p = 0.96). This is descriptive only; attention is not a causal test.
- **Readout (iii), prime-veto.** The pre-stated "activated in order to be suppressed" pattern appears in none of the 6 task x layer configs. The NAME(X) latents are silent at R. At L27, both NAME(X) and IMPL(X) activations at k_pre are *lower* under the ban than under both twins for the same text: T1 IMPL 124 vs 169 (neutral), NAME 94 vs 129 (mention); IMPL ban−neutral sign test p = 2e-24. The DiM projection agrees in sign in 2 of the 6 configs only, so most latent results are flagged as not reproduced by DiM.
- **Thought anchors.**
  - T2 traces complete in 2.5k–3.7k thinking tokens (5/5).
  - T1 traces think for 8.4k–9.3k tokens. None complete within the 8,192 cap, though 4/5 still emit DFS code.
  - On T1, DFS is fixed at the first resample point in 4 of 4 traces: D_0 max share 1.0, no anchors (F6: consistent with a decision at or before R).
  - T2 shows one anchor among 32 sentences, a problem restatement.
  - Early-label validity is 13/16 = 0.81.
- **Same-seed CRN.**
  - Ideas do not move with temperature under this coupling: label change vs T=0.3 is 0/30 in 10 of 12 cells and 1/30 in the other two, for same-seed and different-seed pairs alike. With no idea-level noise left, the same-seed vs different-seed difference is exactly 0.
  - Phrasing (identifier-normalised AST 4-gram Jaccard < 0.8) changes less within a seed than across seeds, e.g. T2 ban T1.3: 0.55 vs 0.76, T1 baseline T0.7: 0.60 vs 0.84.
  - The first divergence from the T=0.3 program falls at a median of 13–117 tokens.
  - vLLM run-to-run identity was 5/8 rows.
- **J-lens.** The gate failed. Top-1 agreement with the model's own next token was below the logit lens at every source layer (L27: 0.104 vs 0.291). Lens readouts are reported descriptively only. **NLA was not run**: no Qwen3-8B checkpoint exists as of 2026-10-20.
- **Labeller re-check (A2):** combined-vs-adjudicated agreement 0.965 on 141 gold programs (≥ 0.9). OpenRouter spend was USD 0.042 (112 judge calls).

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator: `--stage A/B/vllm1/vllm2/label/hf/analyse/anchors/final/figures/verify` |
| `src/core.py` | Paths, models, seeds, templates, label maps, IO, deviations, timing and spend helpers |
| `src/prompts.py` | A3 prompt builder: W1–W5 ban / mention / neutral / substitute-mention twins, token spans, neutral filler {N} |
| `src/readout_i.py` | Stage B: layer probe, layer choice, SAE alignment, nested selection with nulls, readout objects |
| `src/vllm_stage.py` | vLLM session 1: C1 fresh pool, E5 CRN logits processor, determinism rerun |
| `src/anchors_stage.py` | vLLM session 2: C2 base traces, C3 chunked resampling, C4 completions |
| `src/early_label.py` | C5 early-label detector and the D1 sentence taxonomy |
| `src/labelling.py` | Canonical exp1 labeller wrapper (hidden tests, tracer, AST, judge on disagreement), exp3 commit locator |
| `src/hf_stage.py` | HF block: E2 states and attention rows under twins, prompt-only passes, E1 transfer test, E4 J-lens |
| `src/analysis.py` | E3 readouts (i)/(ii)/(iii), latent contexts, transfer verdicts, J-lens summary, D1 thought anchors |
| `src/final.py` | A2 check, fresh-pool and same-seed (D2) analyses, 0e record, `method_out.json` |
| `src/figures.py` | `figures/fig_*.png|pdf` from the results JSON |
| `src/verify_headlines.py` | Independent re-derivation of headline numbers, with placebo checks (`results/verify_headlines.json`) |
| `prompts/prompts_v2.json` | Every prompt: text, chat-template token ids (thinking off/on), token spans |
| `inputs/` | Read-only copies of the iteration-1 exp1 suite and labeller, exp3 meta and labeller, exp6 analysis code |
| `results/raw/` | Raw generations: C1 pool, E5 CRN, C2 traces, C3 continuations, C4 completions |
| `results/labelled_*.jsonl`, `results/samples.jsonl` | Labelled generations (canonical labeller); one row per generated sample |
| `results/*.json` | Per-readout results, listed in `reproducibility.md`; `deviations.json`, `timing.json`, `spend.json` |
| `results/tensors/` | E2 states, attention masses, prompt-only states, J-lens states, context-corpus SAE codes, exp3 sparse codes |
| `figures/` | 8 figures (layer probe, transfer, latent vs DiM, attention, prime-veto, thought anchors, same seed, J-lens) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out` output with 4 datasets (1,122 examples); all analyses are in `metadata` |
| `logs/` | Stage logs (loguru) |
| `tools/zigcc`, `tools/memwatch.sh` | C-compiler shim for Triton (no system cc); PID-scoped memory watchdog for the 31 GB cgroup |

`results/tensors/` stays on this run's storage volume. Each file is under 100 MB, so it is also published.

## How to run

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml
uv run method.py --stage B            # CPU: layer probe, SAE alignment, readout (i) discovery
uv run method.py --stage vllm1        # GPU: C1 fresh pool + E5 CRN (C1_PER_TEMPLATE=20, CRN_SEEDS_N=30)
uv run method.py --stage vllm2 --part traces --n 5
uv run method.py --stage label
uv run method.py --stage hf           # GPU: E2, E1, E4
uv run method.py --stage vllm2 --part resample --n 4
uv run method.py --stage vllm2 --part complete --n 1
uv run method.py --stage label && uv run method.py --stage analyse
uv run method.py --stage final && uv run method.py --stage figures && uv run method.py --stage verify
uv run method.py --stage final        # re-embeds the verification record
```

See `reproducibility.md` for runtimes, inputs and environment variables.

## Deviations

`results/deviations.json` lists every departure from the plan with its cost:
- FP8 twin for generation;
- 16 GB GPU layout;
- 200-run pool and 30 CRN seeds;
- thought-anchor reductions;
- no Gumbel-max sensitivity;
- J-lens applied from `lens.pt`;
- matplotlib figures, and others.

`results/not_run.json` lists what did not run: E6 thinking-on CRN, Gumbel-max sensitivity, NLA, the adaptive top-up, and the OpenRouter latent descriptions.

## Restoring removed files

`.aii/manifest.yaml` marks `.venv/` and every Python bytecode cache (`__pycache__/`) for deletion after the round:

```bash
# .venv/ (regenerable)
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r pyproject.toml
# src/__pycache__/ (regenerable): recreated by any `uv run method.py --stage ...`
# inputs/exp1/__pycache__/, inputs/exp1/labeller/__pycache__/, inputs/exp1/tasks/__pycache__/,
# inputs/exp3/labeller/__pycache__/ (regenerable): bytecode of the copied iteration-1 labeller / harness /
#   commit locator, recreated by `uv run method.py --stage label`
# inputs/exp6/__pycache__/, inputs/exp6/analysis/__pycache__/ (regenerable): bytecode of the copied exp6
#   phrasing / thinking code, recreated by `uv run method.py --stage final`
```

The models and SAEs live in the shared Hugging Face cache, not in this folder. To re-download them:

```bash
huggingface-cli download Qwen/Qwen3-8B
huggingface-cli download Qwen/Qwen3-8B-FP8
huggingface-cli download Qwen/Qwen3-8B-Base
huggingface-cli download Qwen/SAE-Res-Qwen3-8B-Base-W64K-L0_50 layer15.sae.pt layer20.sae.pt layer27.sae.pt config.json README.md
huggingface-cli download senku21x/cot-oracle-jlens Qwen3-8B/lens.pt Qwen3-8B/lens.meta.json
```
