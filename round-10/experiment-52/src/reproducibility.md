# Reproducing NOV-B2 (guided program search on online bin packing, seeds 2-3 + exploratory 4-5)

This file describes what was actually run, in order, on 2026-10-24 (UTC 17:47-21:45). All paths below are relative to
this folder. Nothing here needs any absolute server path.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that contains method.py
```

Files of 100 MB or more are not published (none of the deliverables here is that large). The model weights are
downloaded from Hugging Face (step 3). The virtual environment and the vLLM compile cache are rebuilt (steps 2 and 4).

## 2. System, Python and packages

- OS: Debian 12 (bookworm) container on Linux 6.8. Hardware actually used: 1x NVIDIA GeForce RTX 4090 (24 GB VRAM,
  driver 595.91, CUDA 13.2 driver API), AMD Ryzen 9 7950X with a cgroup quota of 13.6 CPUs, 56 GB RAM limit.
  `predictions/hardware.json` holds the full `nvidia-smi -q`, `df -h`, `nproc`, cgroup and `free -g` record.
- No system C compiler was present. vLLM/Triton use the `tools/cc` shim (`python -m ziglang cc`), which
  `src/engine.py` puts first on PATH.
- Python 3.12.14 and uv 0.6.14:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r <(python3 - <<'EOF'
import tomllib; print("\n".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))
EOF
)
```

`pyproject.toml` pins all 172 packages to the exact versions installed in `.venv` (output of `uv pip freeze`, also in
`logs/pip_freeze.txt`). The key ones are vllm 0.11.0, torch 2.8.0 (cu128), transformers 4.57.1, numpy 2.2.6,
scipy 1.18.1, scikit-learn 1.9.1, matplotlib 3.11.2, httpx 0.28.1, loguru 0.7.3 and ziglang 0.17.0.
The original install command was
`uv pip install vllm==0.11.0 transformers==4.57.1 numpy scipy scikit-learn matplotlib loguru openai httpx requests pyyaml ziglang accelerate psutil`,
and it took about 20 minutes over the network filesystem.

## 3. Models, data, environment variables

- Mutator: `Qwen/Qwen3-8B-FP8`, revision `220b46e3b2180893580a4454f21f22d3ebb187d3` (about 9 GB):
  `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3`
- bf16 replay only: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218` (about 16 GB):
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`
- Instance sets, the FunSearch notebook, OR-Library binpack1-4, the EoH/ReEvo/HSEvo/MCTS-AHD/LLM4AD files and the
  arXiv 2510.27353 text ship in this folder (`data/instances/`, `ext/`). They were copied from the iteration-9
  workspace and verified by sha256 (`inputs_manifest.json`, `inputs/bp9_*`). `ext/s3c/` holds one README fetched during
  the dated search. All of these are data and are never executed.
- Declared dependency `art_j3Rm_lr2nzR6`: its `full_data_out.json` is read only by the S3b scan, via the env var
  `ART_J3RM_LR2NZR6_DIR`. If the variable is unset, the scan looks in the sibling folder `../art_j3Rm_lr2nzR6`.
- Environment variables (names only):
  - `HF_HOME` / `HF_HUB_CACHE`: where model weights live (optional).
  - `HF_TOKEN`: optional.
  - `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: the judges stage only (it spent USD 0.145).
  - `NOVB2_SEEDS` and `NOVB2_TAG`: extension run only.
  - `BP9_DIR` and `TSP9_DIR`: only to re-copy from the iteration-9 workspaces. Without them, `setup` verifies the
    shipped copies.
- No user-uploaded inputs are used.

## 4. Commands, in the order they were run

All stages are wrapped by `method.py` (`python method.py <stage>`; `python method.py all` runs them in order). The
equivalent direct commands and their wall times on the hardware above:

| # | command | what it does | wall time |
|---|---|---|---|
| 1 | `.venv/bin/python src/s0_setup.py` | sha256-verify the copied harness, run `src/gate.py` (G-HARNESS PASS: BF 212.0/5.37 %, 2067.0/3.98 %; c12 207.45/3.11 %; c14 2001.4/0.68 %), re-verify | 1 min |
| 2 | `.venv/bin/python src/probes.py` | build the 2,000 P10 probe states (sha256 `9b6a1d4f...`) and run the probe gate | 1 min |
| 3 | `.venv/bin/python src/corpus.py build` | corpus scoring: decisions for all 3,843 ab members, tuned ab (seed 20261024 permutation, 2,000 evaluations), next fit, harmonic-k, 75 published/textbook programs | 8 min |
| 4 | `.venv/bin/python tests/test_offline.py` | 40 offline tests (sandbox, prompts, DTB/RPB, islands, clusters); all pass | 2 min |
| 5 | `.venv/bin/python src/commit.py commit1` | `predictions/commit1.json` + `commitments.log` hash chain, before any generation call | <1 min |
| 6 | `python method.py engine` | `bash start_vllm.sh graphs` (TSP9 settings verbatim: FP8 Marlin, max-model-len 4096, gpu-mem 0.93, prefix caching, 64 seqs) | 5 min |
| 7 | `.venv/bin/python src/search.py smoke` | seed-99 smoke test, 10 calls x 6 arms (discarded, logged in `data/smoke_*`) | 1 min |
| 8 | `.venv/bin/python src/search.py run` | rounds 1-5, then the C* rule (C* = 2000) and commit #2, then 100 lockstep rounds x 10 arm-seeds (seeds 2, 3), then NS 1,000 calls per seed | 32 min |
| 9 | `.venv/bin/python src/analysis.py clusters`, then `best`, then `candidates` | frozen analysis: clusters, sensitivities, bootstrap, placebo, best programs, V3 candidates | 3 min |
| 10 | `.venv/bin/python src/heldout.py best`, then `candidates` | held-out scoring (8 sets, 120 s per set) and V3 filters | 14 min |
| 11 | `.venv/bin/python src/commit.py amend extension_and_corpus_additions results/amend3_payload.json` | commit #3: pre-registers the exploratory extension and the corpus additions | <1 min |
| 12 | `NOVB2_SEEDS=4,5 NOVB2_TAG=ext45 .venv/bin/python src/search.py run` | exploratory extension: same protocol, seeds 4, 5, C = 2000, no NS | 31 min |
| 13 | `python3 -I scripts/s3b_scan.py results/s3b_hits.json`; `.venv/bin/python src/corpus.py add results/corpus_additions_s3b.json` | S3b dependency scan (10 hits, 6 adapted) | 1 min |
| 14 | dated search (S3c, web), then `.venv/bin/python src/corpus.py add results/corpus_additions_s3c.json` and `.venv/bin/python src/heldout.py novelty` | `results/positioning.json` (25 sources); adds the RAISE heuristic; refreshes the novelty filter | 15 min |
| 15 | `.venv/bin/python scripts/profile_rules.py results/manual_read_blind.json results/manual_read_profiles.json` | arm-blind manual read aids (decision profiles); the reads are in `results/manual_read.json` | 1 min |
| 16 | `.venv/bin/python src/judges.py` | gated judges (DeepSeek v3.1, Kimi K2, Mistral Medium 3.1 as replacement), T 0, USD 0.145 | 2 min |
| 17 | `.venv/bin/python src/v3final.py`; `.venv/bin/python src/analysis.py verdicts` | V3 combination; frozen V1/V2/V3/V6 verdicts -> `results/verdicts.json` | 1 min |
| 18 | `.venv/bin/python src/v5.py` (engine restarted from `start_vllm_v5.sh`, gpu-mem 0.80) | V5 teacher-forcing reversion test, 40 offspring x 20+20 continuations | 11 min |
| 19 | `python method.py engine-stop`; `.venv/bin/python src/hfreplay.py` | bf16 replay of 20 DTB calls | 2 min |
| 20 | `.venv/bin/python scripts/ext_analysis.py` | frozen analysis functions on seeds 4-5 plus held-out scoring of their best programs | 5 min |
| 21 | `.venv/bin/python src/figures.py`; `.venv/bin/python src/outputs.py` | F1-F7 (`figures/`); `method_out.json` | 3 min |
| 22 | `python3 -I audit/rederive.py` | stdlib re-derivation of every headline number + placebos -> `results/audit_rederive.json` | 10 min |
| 23 | `aii_json_format_mini_preview.py --input method_out.json` (aii-json skill) | `full_/mini_/preview_method_out.json` | 1 min |
| 24 | split of the evaluation rows (152 MB) into `data/eval/eval_part_001.jsonl` + `eval_part_002.jsonl` (line-aligned, < 80 MB each, sha256 of the concatenation identical); all readers use `common.read_eval_rows()` | publish limit 100 MB | <1 min |

Seeds:
- Search arm-seeds S = 2, 3; exploratory S = 4, 5.
- Per-request seed = (S*1000003 + arm_id*100003 + call*7 + req) mod 2^31.
- Parent-draw RNG `default_rng([S, arm_id, 1])`; branching RNG `default_rng([S, arm_id, call, 7])`.
- Probe and tuned-ab RNG 20261024.

Batching can perturb FP8 logits in vLLM, so a re-run reproduces the protocol and the distributions, not byte-identical
completions. Every analysis number is recomputable byte-for-byte from the stored rows (`data/gen_s*.jsonl`,
`data/eval/eval_part_*.jsonl`, `data/decisions.bin` + `data/decisions_index.jsonl`):

```bash
.venv/bin/python src/analysis.py clusters && .venv/bin/python src/analysis.py verdicts && python3 -I audit/rederive.py
```

## 5. Expected outputs and numbers

- `results/s0_verify.json`: S0_PASS with the gate targets above.
- `results/probes.json`: P10 sha256 `9b6a1d4f0c50c19a702eae84cf8cb8b905194f7bce5fbf16b91050a87b6075e8`, gate PASS.
- `results/verdicts.json` (pre-registered, seeds 2-3; re-derived in `results/audit_rederive.json`):
  - **V1 PARTIAL.** H-FSW5k / H-OR3 excess of each arm's best program: DTB 2.395 % / 3.852 %, RPB 1.720 % / 3.703 %,
    IDEA 2.133 % / 3.554 % (all pass the 0.8 x BF rule: 3.187 % / 4.294 %). T1.0 3.672 % / 4.821 % and T1.6 3.984 % /
    5.368 % fail; T1.6's best is BF itself.
  - **V2 PARTIAL.** Behaviour clusters per 2,000 calls (seeds 2 / 3): DTB 230 / 143, RPB 269 / 233, IDEA 134 / 150,
    T1.0 13 / 8, T1.6 1 / 1, NS 5 / 3 (per 1,000 calls). Ratios: R_T1.0 = 17.76, R_T1.6 = 186.5, R_RPB = 0.743. The
    only failed condition is R_RPB >= 1.2. The shuffled-arm placebo supports V2 in 0 % of 200 shuffles.
  - **V3 DISCONFIRMED.** 151 candidates; 50 pass the 0.8 rule; 48 also pass the corpus-novelty filter (agreement
    < 0.9 with all 82 corpus programs and 3,843 ab members). The 40 best were judged and none is NOVEL in the decisive
    arm-blind manual read. No judge passed its 10-control gate, so the judges are advisory. Rule-of-three bound 7.5 %.
  - **V6 PARTIAL.** Rename share is 0.670 for IDEA vs 0.959 for T1.0. 0.4 % of IDEA offspring claim a new idea in a
    comment.
- `results/v5.json` (descriptive): reversion 0.498 at decision positions vs 0.255 at random control positions
  (diff 0.243, bootstrap 95 % CI [0.079, 0.417], n = 30; sign-flip p = 0.0086).
- `results/hf_replay.json`: bf16 vs FP8 top-1 agreement 1.00, top-20 Jaccard 0.94, the same DTB position in 20/20
  calls.
- `results/extension_ext45.json`: seeds 4-5, exploratory.
- `figures/F1-F7` (PDF + PNG) and `method_out.json` (+ full/mini/preview): these feed the paper's results section.
  F1 shows best-so-far fitness, F2 discovery curves, F3 held-out excess, F4 the behaviour map, F5 the branching
  diagnostics, F6 validity, F7 the V5/V6 rates.
