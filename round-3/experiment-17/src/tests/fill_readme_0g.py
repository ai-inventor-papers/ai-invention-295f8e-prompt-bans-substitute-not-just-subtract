"""Fill the README's 0g section and P5 outcome from results/sae_transfer.json (and 5a from sae_readout.json)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sae = json.loads((ROOT / "results" / "sae_transfer.json").read_text())
sr = json.loads((ROOT / "results" / "sae_readout.json").read_text()) if (ROOT / "results" / "sae_readout.json").exists() else None
L = ["15", "20", "27"]
c = sae["cells"]
rows = []
for cell, name in (("inst_own", "instruct / own text"), ("base_own", "base / own text"),
                   ("inst_on_base", "instruct / base text"), ("base_on_inst", "base / instruct text")):
    if cell not in c:
        continue
    x = c[cell]
    rows.append(f"| {name} | {x['ce_clean']:.3f} | " + " | ".join(
        f"{x['layers'][l]['fr_zero']:.4f} / {x['layers'][l]['fr_mean']:.3f} / {x['layers'][l]['dce']:.3f} / {x['layers'][l]['kl_sae']:.3f} / {x['layers'][l]['fvu']:.3f}"
        for l in L) + " |")
pl = sae["per_layer"]
passes = {l: pl[l]["frozen_pass"] for l in L}
fm = {l: pl[l]["fr_mean_pass_same_rule"] for l in L}
dp = sae.get("displacement_preservation") or {}
dps = "; ".join(f"L{l}: cos {dp[l]['cos_mean_all']:.2f}, norm ratio {min(dp[l]['norm_ratio_median_by_task'].values()):.2f}–{max(dp[l]['norm_ratio_median_by_task'].values()):.2f}"
                for l in L if l in dp)
san = sae.get("sanity") or {}
si = san.get("instruct") or {}
sb = san.get("base") or {}
u5 = sae.get("u5_fvu_vs_exp12") or {}
txt = f"""**0g: Qwen-Scope SAE transfer** (`results/sae_transfer.json`, fig 6). 2×2 design: each model (FP8) scored with
the base-model SAEs spliced into the residual stream (block L output, positions ≥ 1, chat special tokens excluded),
100 sequences per text source. Cells give FR_zero / FR_mean / dCE (nats) / KL(clean‖SAE) / FVU:

| Model / text | CE clean | L15 | L20 | L27 |
|---|---|---|---|---|
""" + "\n".join(rows) + f"""

- **Frozen rule** (FR_zero(instruct, own) ≥ 0.9 × FR_zero(base, own)): PASS at L15/L20/L27 = {passes['15']}/{passes['20']}/{passes['27']}
  ({'all layers pass' if all(passes.values()) else 'not all layers pass'}). As the plan computed in advance, the ~12–15
  nat zero-ablation denominator makes this rule lenient: it licenses little by itself.
- Stricter companions: FR_mean passes the same 0.9× rule at L15/L20/L27 = {fm['15']}/{fm['20']}/{fm['27']}; the
  dCE ratio on own text (instruct/base) is {pl['15']['dce_ratio_own_text']:.2f} / {pl['20']['dce_ratio_own_text']:.2f} / {pl['27']['dce_ratio_own_text']:.2f}
  (exp12, bf16, one shared corpus: 3.29 / 1.95 / 1.59); KL(clean‖SAE) instruct vs base on own text:
  {pl['15']['kl_sae_inst_own']:.3f} vs {pl['15']['kl_sae_base_own']:.3f} (L15), {pl['20']['kl_sae_inst_own']:.3f} vs {pl['20']['kl_sae_base_own']:.3f} (L20),
  {pl['27']['kl_sae_inst_own']:.3f} vs {pl['27']['kl_sae_base_own']:.3f} (L27).
- Displacement preservation (the task-relevant test: does the SAE keep the ban-minus-twin displacement at S?):
  {dps}.
- Sanity: identity splice equals clean CE (instruct {si.get('identity_equals_clean')}, base {sb.get('identity_equals_clean')});
  zero splice at L15 gives {si.get('zero_ce_mean', float('nan')):.1f} / {sb.get('zero_ce_mean', float('nan')):.1f} nats (exp12: 12.36). U5 FVU vs exp12 (instruct):
  {", ".join(f"L{l} {u5[l]['ours_inst_own']:.3f} vs {u5[l]['exp12_inst']:.3f}" for l in L if l in u5)}."""
if sr:
    best = []
    for t, v in sr["per_task"].items():
        for k, x in v.items():
            if isinstance(x, dict) and "dim" in x:
                best.append((t, k, x["top1"]["ba"], x["top20"]["ba"], x["dim"]["ba"], x["latent_beats_dim_beyond_ci"]))
    nb = sum(1 for b in best if b[5])
    txt += f"""

**5a (descriptive): SAE latents vs DiM** (`results/sae_readout.json`). Over {len(best)} readout cells (6 tasks ×
L15/20/27 × {{prohibition-present at S-mean; default-plan at k = 1, 2, 3 where testable}}), a latent readout (top-1
or top-20) beats DiM beyond DiM's CI in {nb} cells."""
p = ROOT / "README.md"
s = p.read_text()
s = s.replace("ZEROG_PLACEHOLDER", txt)
fz_i = [c["inst_own"]["layers"][l]["fr_zero"] for l in L]
fz_b = [c["base_own"]["layers"][l]["fr_zero"] for l in L]
p5 = (f"{'PASS' if all(passes.values()) else 'partial'} by the frozen rule; FR_zero instruct {min(fz_i):.3f}–{max(fz_i):.3f}, "
      f"base {min(fz_b):.3f}–{max(fz_b):.3f}")
s = s.replace("P5_OUTCOME", p5)
p.write_text(s)
print(txt[:3000]); print(p5)
