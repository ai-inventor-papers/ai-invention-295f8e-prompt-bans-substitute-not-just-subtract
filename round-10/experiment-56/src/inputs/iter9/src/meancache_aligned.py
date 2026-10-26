#!/usr/bin/env python3
"""B3 fix of iteration 8's MeanCache (art_18XvfcJJZi1O src/k3circuit.py lines 468-489), as a subclass; the vendored
file is not edited.

Bug: for a COND node the original get() averages only over prompts of the reference prompt's template with an equal
span length and returns None otherwise. On C1forced every held-out prompt (templates F11-F15) has no same-template pair
prompt, so every COND edit was None and the held-out arm measured nothing (mean_d_heldout = 0.0).

Fix (primary, 'aligned'): for a COND node and a target prompt with condition-span length L*, each class prompt i's node
values over its own COND span (L_i x d) are linearly interpolated along relative position r = k / (L - 1) to L* rows,
then averaged over the class prompts. Pair prompts of C1forced are one per template, so the average pools templates
(the original same-template restriction is kept wherever a same-template prompt exists: see mode 'same_template_first').
Sensitivities: 'span_mean' (each prompt's span mean, averaged, broadcast to all L* rows) and 'exact_length' (only class
prompts whose span length equals L*, no interpolation; None if there are none). Non-COND classes behave as the original.
"""

from __future__ import annotations

import sys
from typing import Any

import torch

from cfg9 import V41

if str(V41 / "src") not in sys.path:
    sys.path.insert(0, str(V41 / "src"))
import k3circuit as KC  # noqa: E402


def interp_rows(x: torch.Tensor, L_out: int) -> torch.Tensor:
    """Linear interpolation of rows x [L, d] at relative positions k / (L_out - 1) -> [L_out, d] (fp32).
    Exact identity when L == L_out; constants stay constant."""
    x = x.float()
    L = x.shape[0]
    if L == L_out:
        return x.clone()
    if L == 1:
        return x.expand(L_out, -1).clone()
    if L_out == 1:
        return x.mean(0, keepdim=True)
    r = torch.arange(L_out, dtype=torch.float64) * (L - 1) / (L_out - 1)
    lo = r.floor().long().clamp(0, L - 1)
    hi = (lo + 1).clamp(max=L - 1)
    w = (r - lo.double()).float()[:, None]
    return x[lo] * (1 - w) + x[hi] * w


class MeanCacheAligned(KC.MeanCache):
    def __init__(self, acts: dict[int, Any], prompts: list[dict[str, Any]], mode: str = "aligned"):
        super().__init__(acts, prompts)
        assert mode in ("aligned", "span_mean", "exact_length")
        self.mode = mode

    def get(self, idx: list[int], node: tuple, ref: dict[str, Any]) -> torch.Tensor | None:
        cl = node[3]
        if cl != "COND":
            return super().get(idx, node, ref)
        L_star = len(ref["pos"]["COND"])
        key = (KC.node_key(node), tuple(idx), "aligned", self.mode, L_star)
        if key not in self.c:
            vals = []
            for i in idx:
                p = self.prompts[i]
                ps = p["pos"]["COND"]
                if not ps:
                    continue
                v = KC.node_vals(self.acts[i], node, ps).float()
                if self.mode == "aligned":
                    vals.append(interp_rows(v, L_star))
                elif self.mode == "span_mean":
                    vals.append(v.mean(0, keepdim=True).expand(L_star, -1))
                elif len(ps) == L_star:
                    vals.append(v)
            self.c[key] = torch.stack(vals).mean(0) if vals else None
        return self.c[key]
