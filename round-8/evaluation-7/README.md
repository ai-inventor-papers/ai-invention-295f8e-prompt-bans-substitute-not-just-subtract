# Fixing errors in the iteration-7 research record

`demo/` — Self-contained demo (Colab-ready notebook or markdown). Run without setup.  
`src/` — Full source code, data, and outputs from the experiment execution.

**Type:** evaluation  
**ID:** `art_vjtPMtWGMjsB`

## Layman Summary

Checks and corrects the previous round's research report: relabels misread programs, recomputes the affected numbers from raw files, tones down overstated claims, and proves every fix with independent re-checks.

## Full Summary

Iteration-8 Step 0 record repair (CPU only, USD 0.095 of judge calls). It answers all 11 items (0a-0k) of the blocking iteration-7 review in place. report_corrected.md is the iteration-7 report (inputs/report/current_report.md) with 84 machine-checked edits, each marked '(iteration-8 correction)'. report.diff is the unified diff. corrections.json holds the edits and a 141-value ledger (recorded, recomputed, status MATCH 68 / CORRECTED 7 / NEW 63 / CARRIED 3, source artifact:file#key). The residual-claim lint drops from 35 hits to 0. KEY CORRECTIONS. (0a) The kth-smallest labeller missed counting sort in dictionary form. The extension in labeller_v2/ was validated before any relabel: references 6/6, gold kappa 0.951 unchanged, controls 5/5. After the relabel, the full-state exchange of the forced counting-sort source gives 29/30 counting sort (was 0/30). Pooled kth recovery falls from 1.59/1.57/1.55 to 1.01 [0.95,1.08] / 1.00 / 0.99 at ranks 1/4/16 (exp33's own slot bootstrap, which reproduces Tables 293/295 exactly). DAS routes more cleanly than the full state on ONE task (shortest path, Floyd-Warshall 28/28 vs 8/20); on kth smallest it changes the form (array of counts) but not the algorithm. 29 of the 36 catalogue variants of 7.3.9 come from that cell. Judges deepseek-chat-v3.1 10/10 and mistral-medium-3.1 9/10 on the gate; 48 programs were read manually (tables/counting_sort_adjudication.csv). (0b) Recovery is now reported per source (new Table 297b, tables/recovery_by_source.csv): forced Bellman-Ford/SPFA 0.17-0.43, forced BFS 0.06-0.53, rank 2 never generated for forced sources. Untrained-network ratios, shortest path only: 0.013 (against the diverged fit, meaningless), 0.92 (fit value), 5.08 (matched LME_Y gain, 43.6 vs 8.6 nats). (0c) Gemma's 42-vs-35 is not a comparison. DAS and twin cells have the 32-token opening prefilled (g2.py:877, prefix_len 32); the forced-BFS cell is sampled from index 0 (g2.py:878-885) on the same CRN slots. (0d) The fork margin is a readout, not a predictor: Spearman 0.804, opening LLR 0.869; no direction-level property predicts (axis 0.17/0.01). (0e) Gemma natural variance is below the random 95th percentile at ranks 1, 2 and 4 and above at rank 8; block 22 rank 1 is above. dormant_flag was false only via |rho|=0.497. Dormancy checks were not run. Recovery 1.98-2.81x is the Makelov off-manifold signature. Qwen and Gemma controls are not comparable (new Table 364d, tables/control_protocols.csv). (0f) New Table 371b and positioning.json: 12 neighbours plus 2 ICML 2026 workshop posters, all verified live 2026-10-23 (raw grep outputs in audit/web/). 'A Tale of Two Temperatures' is COLM (no year) plus AdaptFM and SPIGM workshop posters, and is about diffusion LMs. (0g) New 7.3.10 quotes deviations D-drop, D-tfsets, D-targets and D-cap verbatim. (0h) Table 346 fresh-slot rows, recomputed from slot rows: top quartile 24/50 vs rest 9/50 (15:0); full unit 21/50 vs shuffled 4/50 (17:0); RD_seed -0.10. (0i) Search as rates (tables/search_by_arm.csv): 78/2,500 (12 clusters) vs instruction 2/500; ratio 7.8, LB 2.41, short of 10x. (0j) MST's T1.0 prediction lies outside the Wilson interval [0.28,0.54]. W1-W3 are training templates. The semantic seed sits on the boundary (93.9th percentile). (0k) Step K tags are replaced from retag.json; 10 lost file names are restored. AUDITS. audit/rederive.py (stdlib, separate code path): 97 checks, 0 mismatches, 6/6 placebos fail. audit/headline_check.py: 11/11 headline numbers re-derived through different code paths (regex relabel of raw code, counting ranks, bisection bound), 5/5 placebos fail. NOT RUN (stated in the record): Gemma reverse interchange and projection; the Qwen untrained network beyond shortest path; a prefill-matched instruction cell. OUTPUTS: eval_out.json (exp_eval_sol_out; datasets corrections, report_edits, counting_sort_adjudication, recovery_by_source, gemma_natural_variance, control_protocols, search_by_arm, positioning_rows), tables/*.csv, README.md, reproducibility.md. Rerun: uv sync && uv run eval.py --stages all (about 25 s, judges cached).

## Dependencies

- `art_veI9l_Rb9wDY` — DAS rows
- `art_HY7uYZz-OjRW` — Gemma rows
- `art_8O5eaNc5gxJs` — dose rows
- `art_VhaHGe7SxV95` — search rows
- `art_MZAfDPVhM6Ui` — temperature rows
- `art_pHL7LWNhpcCS` — fork rows

## Output Files

- `eval.py`
- `full_eval_out.json`
- `mini_eval_out.json`
- `preview_eval_out.json`
- `reproducibility.md`

## Demo Files

- **eval.py** — Evaluation script with metrics computation

---
*Generated by AI Inventor Pipeline*
