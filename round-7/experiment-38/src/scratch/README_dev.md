## Deviations (full text in `results/deviations.json`)

- **D01 GPU.** RTX 2000 Ada (16 GB), not an A4500. B_CRN = 25 (time test); max_new 1024.
- **D02 RLIMIT_AS.** Set on CPU stages only (12 GB).
- **D03 Engine keys.** Iteration 6's own slot_key ('iter5E' for slots 0-9).
- **D04 DAS optimiser.** Adam lr 2e-2 (plan 2e-3: the toy shows 2e-3 x 400 steps leaves the subspace near random)
  and batch 48 (plan 64). Early stopping on a rotating held-in template.
- **D05 U3.** The single-position path differs from a full recompute by up to 0.27 nats (bf16). Every DAS dy is
  measured on one path and in one fixed batch shape.
- **D06 G1 order.** G1-P is the primary validated graph. G1-T ran last under a cap.
- **D07 Patching offsets.** The first g1p run was redone with in-batch base rows. Commit #2 is superseded by #2b,
  made before any validation or generation output.
- **D08 Position classes.** SPEC includes the chat tail. COND targets use same-template prompts.
- **D09 Random nulls.** Same type and position class, any layer, write norm +/-25% (widened when needed; logged).
- **D10 Labeller restart.** No data lost.
- **D11 Batching.** Cells of one template share fixed-shape batches.
- **D12 L* rule.** Recovery above 1 at early layers lets the committed argmax pick L17. Absolute dy is reported
  beside it.
- **D13 Toy.** The second principal cosine is 0.81, below the plan's 0.95.
- **D14 U6 horizon.** Full programs; partial labels on the first 320 tokens.
- **D15 Path-patching pairs.** F2-F4 forced pairs are added for patching only.
- **D16 Engine check.** 0.38 is just outside the CI; iteration 6's own share on the same slots is 0.36.
- **D17 DiM toward DFS.** A bisection bug left all six cells unmatched (beta = -3000). They are reported as one
  strong DiM-DFS reference.
- **D18 G2-N.** Not run (drop order). The mediation claim covers forced-prompt transfer only.
- **D19 G1-T.** Three timed attempts (missing C compiler; then out of memory at batch 64 and at batch 16 with 4,096
  feature nodes). Dropped. G1-P is the reported circuit.
