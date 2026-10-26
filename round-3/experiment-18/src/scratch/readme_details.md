## Departures from the plan (full list with consequences: `method_out.json → metadata.deviations`)

- **Hardware and precision (D1, D2).** The pod had an NVIDIA L4 (23 GB, 300 GB/s) instead of the planned RTX A4500.
  Each task family ran at the precision its iteration-2 references were produced with. T1/T2 ran in bf16 (exp8/exp9
  baselines and forced programs). The bench tasks ran on the official Qwen3-8B-FP8 checkpoint (exp11 pilots, forced
  programs and `can`), using weight-only FP8 Marlin kernels. The bf16-vs-FP8 cross-check on LF1-T2 bounds the
  precision effect for one task only.
- **N-gram and sham rules (D3, D4).** Veto unit test u1 showed an indentation-tailed n-gram being bypassed by
  re-indenting (20/20), so distinctive n-grams must be lexical: no whitespace-only token. The plan's selection rule is
  otherwise unchanged. Shams may not contain a Python keyword or the fence tag. Shams for T03 and T06 are not
  constructible.
- **Unit test u2 (D5)** compares vetoed and unvetoed batch-mates on the same server: 17/20 token-identical (bf16) and
  19/20 (FP8). No processor-free second engine was loaded.
- **Forecast commits per family (D6).** Every forecast still precedes the samples it scores.
- **Fallback R2 (D7, D16).** T1/T2 two-step bans used the exp8/exp9 single-ban substitutes; T03 and T10 used the
  flagged step-1 fallback; T04 used the association answer.
- **One crash and two restarts (D8, D15).** No sample was lost or duplicated.
- **Long-form split branch (D9).** The stage-10 projection was 220 bf16-minutes for all 500 samples.
- **Dropped work (D10, D14; `results/not_run.json`).**
  - The optional manifold placement and the 5b temperature sweep.
  - The T1/T2 thinking-on extension to N = 25. The never-drop floor ran (T1/T2 thinking-on, N = 10 per prompt), and
    the bench thinking-on cells (T03/T04/T06, N = 10 per prompt) ran after a KV-cache-driven restart.
- **Analysis code edited after its commit (D17).** `src/analysis.py` gained additions after its hash was committed
  before the bench ban samples: corrected compositions, the post hoc sensitivity, the claim mechanism check and a
  Holm-family note. No preregistered computation changed. The edit shows as a failed file check on that chain entry
  plus a new entry. `src/rederive.py`, unchanged since before that commit, re-derives every preregistered number
  from the raw rows with 0 mismatches.
- **Audit judge prompt (D13).** The control gate failed at round 0 because the prompt lacked the labeller context.
  After the fix it passed at 5/6 for both judges.

## Limitations

- One model family (Qwen3-8B). C3 is a single-family claim.
- N = 50 per walk round and per LOS list. Minor landings below ~10% are descriptive.
- Thinking-on runs have N = 10 per prompt and per task. A count of 0 novel programs bounds the novel rate only below
  ~26% (exact one-sided 95%).
- 'Novel' is judged against:
  - the catalogue;
  - the known-solution corpus of the declared dataset (472 programs: Mercury, LeetCodeDataset, TheAlgorithms, KodCode,
    XLCoST);
  - two LLM judges and one manual reader.

  It is not judged against the literature.
- The walk is adaptive: each step's mask depends on the previous landing. Its depth is not comparable across tasks.
- Labeller re-check: runtime vs adjudicated agreement on the path gold set is 0.86 (T1) and 0.77 (T2), the same as the
  stored exp8 values. T2 is below 0.85 and is flagged. The combined label, which adds the AST check and the judge on
  disagreement, is what every table uses. All references are recovered by both labellers on all six tasks (43/43).
