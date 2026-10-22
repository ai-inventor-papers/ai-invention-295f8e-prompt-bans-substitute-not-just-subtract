The plan's preferred graph (circuit-tracer, nnsight backend, `mwhanna/gemma-scope-2-4b-it`
`transcoder_all/width_16k_l0_big_affine`, custom target m_lin) was attempted three times under the time cap.

1. The replacement model loaded (11.9 GB), but every attribution failed: the container has no C compiler for Triton.
2. With a pip-installed compiler (ziglang behind a `cc` wrapper), the replacement model with error terms reproduced
   the fork margin within 0.19 nats (-0.415 vs -0.225). That misses the 0.05 sanity bar. The replacement model runs
   eager attention in its own environment; the main engine runs sdpa. Attribution then ran out of memory at batch 64.
3. With the plan's OOM ladder (CPU offload, batch 16, 4,096 feature nodes, lazy encoders; 9.0 GB after load),
   attribution still peaked at 16.4 GB on the 16 GB GPU.

The small-L0 transcoder set and fewer prompts, the next ladder steps, were not tried. **G1-T is dropped (D19).** No
replacement score or error-node share is reported. G1-P above, on raw components and validated in the real model, is
the circuit this artifact reports. The attempt records are `results/g1t_graphs*.json`.
