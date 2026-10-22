"""Write the deviation log (results/deviations.json) -- every departure from the plan, with its reason."""
import sys
sys.path.insert(0, "src")
from cfg import add_deviation

D = {
 "D01_gpu_batch_maxnew": "GPU is an NVIDIA RTX 2000 Ada (16 GB), not the planned A4500 (20 GB). The S0 time test chose B_CRN = 25 "
   "(462 vs 366 rows/s for B = 20); max_new = 1024 (iteration 6's natural T1 programs: median 315, max 413 tokens).",
 "D02_rlimit": "RLIMIT_AS is set only for CPU stages (12 GB): CUDA plus memory-mapped safetensors need a large virtual address "
   "space (the first S0 run failed with 'Cannot allocate memory' under a 26 GB cap). Iteration 6 did the same.",
 "D03_engine_keys": "The engine check uses iteration 6's own slot_key ('iter5E', T1, W, k) for slots 0-9 (the plan wrote "
   "'iter6S'); those are the keys iteration 6's twin rows actually used, so per-slot agreement is meaningful.",
 "D04_das_optimiser": "DAS: Adam lr 2e-2 (plan 2e-3) and batch 48 (plan 64). The toy (results/das_toy.json) shows lr 2e-3 x 400 "
   "steps leaves the subspace near random (principal cosines 0.28/0.02); batch 48 fits the 16 GB GPU next to the base KV stacks. "
   "Early stopping: each seed trains on two of W1-W3 and validates on the third (rotating by seed). Layer scan: 150 steps per fold "
   "of the 3-fold leave-one-template-out CV; k* from a 3-fold CV with 200 steps per fold.",
 "D05_u3_numerics": "U3 failed its 1e-3 tolerance: the single-position KV-cache path differs from a full recompute by up to 0.27 "
   "nats on m, also without any edit (bf16 kernel/shape effects; Gemma has residual channels of order 1e4). Every DAS dy is "
   "therefore measured against the base's own KV-path margin under one fixed batch shape (48), so the offset cancels.",
 "D06_g1_order": "G1-P (edge-level path patching on 272 heads + 34 MLPs) is the primary, validated G1 graph. The circuit-tracer "
   "attempt (G1-T) runs last under a 25-minute cap: the 16 GB GPU cannot hold the main engine and the replacement model at once, "
   "and the never-drop items came first. Its graphs are a hypothesis generator and cross-check only.",
 "D07_patch_offsets": "The first g1p run measured dm against batch-1 clean margins; its smoke test showed an unpatched batched run "
   "differs by 0.37 nats (bf16 batch-shape offset). g1p was rerun with an unedited base row in every chunk (dm exact within the "
   "chunk). The first commit #2 is superseded by commit #2b, made before any validation or generation output; a partial g1v run "
   "with the old offsets was stopped and discarded.",
 "D08_position_classes": "SPEC = task spec + chat tail (aligned by offset from the end; identical tokens in every prompt); COND = "
   "the condition sentence, whose ablation targets use same-template opposite-class prompts only (aligned by position).",
 "D09_random_nulls": "Random matched nodes: same component type (head or MLP) and position class, any layer, write norm within "
   "+/-25% (widened to +/-50%, then nearest-norm of any type; logged per node in g1_selection).",
 "D10_labeller_restart": "The label worker crashed once on a log line (G3 rows have 'cell', not 'arm') and was restarted; no rows "
   "were lost (it resumes from data/labels.jsonl).",
 "D11_batching": "G3 sweep and dose-sweep cells of one template share fixed-shape batches (one prompt per batch; per-row "
   "temperature, top-k, edit and CRN stream), instead of one cell per batch, to cut padding.",
 "D12_lstar_rule": "The committed L* rule (argmax of train-CV median recovery) picks L17, where recovery is about 2: the "
   "full-state interchange at one position has a weak effect at early layers (+3.6 nats vs +7 to +9 at L22-29), and a trained "
   "subspace can move the margin further than the full state. Recovery above 1 is reported as such, beside absolute dy in nats.",
 "D13_toy": "The DAS toy (planted rank-2) recovers the first direction (cosine 0.96) but only 0.81 for the second at 800 steps "
   "(plan threshold 0.95 for both); held-out KL falls from 2.4 to 0.30, RAND stays at 0.05 cosine and SHUF fails held-out (1.33). "
   "A small-n run (256 pairs < 5,120 parameters) overfits (train KL 0.003, held-out 2.0), which is why held-out pairs are decisive.",
 "D14_u6_horizon": "U6 path (a) generated full programs (max_new 1024, no partial-labeller stop) so that it could also be labelled "
   "by the full labeller; its partial labels are computed on the first 320 response tokens (iteration 6's horizon).",
 "D15_extra_pairs": "Path patching also uses forced-DFS vs forced-BFS pairs for F2-F4 (equal-length display names); validation "
   "uses the planned 24 prompts.",
 "D16_engine_check_ci": "The engine-check share (19/50 = 0.38) lies just outside iteration 6's CI [0.245, 0.372]; iteration 6's "
   "own rows on the same 50 slots give 0.36 and per-slot label agreement is 0.94, so the slot subset (not the engine) is BFS-heavy. "
   "Comparisons to iteration 6 are flagged accordingly.",
}
for k, v in D.items():
    add_deviation(k, v)
print(len(D), "deviations written")
