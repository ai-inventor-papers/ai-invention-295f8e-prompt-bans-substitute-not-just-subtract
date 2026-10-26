"""Persistent n-gram logit veto for vLLM V1 (AdapterLogitsProcessor; loaded with --logits-processors veto:NGramVeto).

A request carries its banned id sequences as SamplingParams.extra_args['veto'] (a JSON string, because the OpenAI
server's vllm_xargs only accepts scalar values).  For a banned sequence g = (t_1..t_n) the processor sets the logit
of t_n to -inf whenever the last n-1 generated ids equal (t_1..t_{n-1}); 1-token sequences are masked at every
step.  This is the same rule as vLLM's bad-words op, applied per request, so g can never occur in the output ids.
Requests without a veto get no processor (None) and are sampled exactly as without the plugin.
"""

from __future__ import annotations

import json
from typing import Optional

import torch
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor


def parse_veto(value) -> list[tuple[int, ...]]:
    if not value:
        return []
    seqs = json.loads(value) if isinstance(value, str) else value
    out = []
    for s in seqs:
        t = tuple(int(x) for x in s)
        if t:
            out.append(t)
    return out


class RequestVeto:
    """Per-request callable (output_ids, logits_row) -> logits_row, masking in place."""

    def __init__(self, seqs: list[tuple[int, ...]]):
        self.singles = sorted({s[0] for s in seqs if len(s) == 1})
        by_prefix: dict[tuple[int, ...], set[int]] = {}
        for s in seqs:
            if len(s) >= 2:
                by_prefix.setdefault(tuple(s[:-1]), set()).add(s[-1])
        self.by_prefix = {k: sorted(v) for k, v in by_prefix.items()}
        self.lens = sorted({len(k) for k in self.by_prefix})
        self._single_t: Optional[torch.Tensor] = None
        self._cache: dict[tuple[int, ...], torch.Tensor] = {}

    def masked_ids(self, output_ids: list[int]) -> list[int]:
        """Pure-python twin of __call__ (used by the unit tests): ids masked at the next step."""
        out = set(self.singles)
        n = len(output_ids)
        for m in self.lens:
            if n >= m:
                out.update(self.by_prefix.get(tuple(output_ids[n - m:]), []))
        return sorted(out)

    def __call__(self, output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
        dev = logits.device
        if self.singles:
            if self._single_t is None or self._single_t.device != dev:
                self._single_t = torch.tensor(self.singles, dtype=torch.long, device=dev)
            logits.index_fill_(0, self._single_t, float("-inf"))
        n = len(output_ids)
        for m in self.lens:
            if n >= m:
                key = tuple(output_ids[n - m:])
                last = self.by_prefix.get(key)
                if last:
                    t = self._cache.get(key)
                    if t is None or t.device != dev:
                        t = torch.tensor(last, dtype=torch.long, device=dev)
                        self._cache[key] = t
                    logits.index_fill_(0, t, float("-inf"))
        return logits


class NGramVeto(AdapterLogitsProcessor):
    """vLLM V1 adapter: one RequestVeto per request that carries extra_args['veto']."""

    @classmethod
    def validate_params(cls, params) -> None:  # vLLM >= 0.11 hook (optional)
        ea = getattr(params, "extra_args", None) or {}
        if "veto" in ea:
            parse_veto(ea["veto"])

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(self, params):
        ea = getattr(params, "extra_args", None) or {}
        seqs = parse_veto(ea.get("veto"))
        if not seqs:
            return None
        return RequestVeto(seqs)
