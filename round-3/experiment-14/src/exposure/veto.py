"""Persistent n-gram veto as a vLLM V1 per-request logits processor (AdapterLogitsProcessor, vllm==0.11.0).

A request opts in with SamplingParams(extra_args={"veto": [[t1, ..., tn], ...]}).  At every decoding step the last
token of each vetoed n-gram gets logit -inf whenever the preceding n-1 GENERATED tokens equal the n-gram's prefix
(a 1-gram is banned at every step).  Only generated ids are inspected, never the prompt, so a vetoed id sequence
can never occur inside the generated ids.  Requests without the key get no processor (the batch is untouched).
Loaded by the engine-core process through its FQCN "exposure.veto:NgramVeto" (the workspace is on PYTHONPATH).
"""

from __future__ import annotations

from typing import Optional

import torch
from vllm import SamplingParams
from vllm.v1.sample.logits_processor import AdapterLogitsProcessor


class RequestVeto:
    """Per-request callable f(output_ids, logits_row) -> logits_row (modified in place)."""

    __slots__ = ("table", "lens", "_dev")

    def __init__(self, ngrams: list[list[int]]):
        table: dict[tuple[int, ...], set[int]] = {}
        for g in ngrams:
            g = tuple(int(x) for x in g)
            if g:
                table.setdefault(g[:-1], set()).add(g[-1])
        self.table = {k: torch.tensor(sorted(v), dtype=torch.long) for k, v in table.items()}
        self.lens = sorted({len(k) for k in table})
        self._dev = None

    def __call__(self, output_ids: list[int], logits: torch.Tensor) -> torch.Tensor:
        if self._dev is None or self._dev != logits.device:
            self.table = {k: v.to(logits.device) for k, v in self.table.items()}
            self._dev = logits.device
        n_out = len(output_ids)
        for length in self.lens:
            if length > n_out:
                break
            key = tuple(output_ids[n_out - length:]) if length else ()
            banned = self.table.get(key)
            if banned is not None:
                logits[banned] = float("-inf")
        return logits


class NgramVeto(AdapterLogitsProcessor):
    @classmethod
    def validate_params(cls, params: SamplingParams):
        ea = params.extra_args or {}
        v = ea.get("veto")
        if v is not None and not (isinstance(v, list) and all(isinstance(g, list) and g for g in v)):
            raise ValueError("extra_args['veto'] must be a list of non-empty token-id lists")

    def is_argmax_invariant(self) -> bool:
        return False

    def new_req_logits_processor(self, params: SamplingParams) -> Optional[RequestVeto]:
        ea = params.extra_args or {}
        v = ea.get("veto")
        if not v:
            return None
        return RequestVeto(v)
