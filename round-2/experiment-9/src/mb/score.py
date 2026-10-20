#!/usr/bin/env python3
"""S5 / S7 / S9 HF scoring (teacher forcing) with residual hooks.

score(chat_prompt, responses): prompt and response are tokenised separately (add_special_tokens=False) and
concatenated; the prompt is prefilled once into a DynamicCache; responses are scored in right-padded chunks of B=8
over a deep copy of the cache repeated B times; model.model then lm_head + log-softmax in fp32 over 256-token chunks;
l = sum of response-token log-probs. Forward hooks on model.model.layers[20..28] keep float16 residuals at R (last
prompt token, once per prompt), g8 / g16 / g32 (response-token indices) and 'pre' (the token just before the first
token overlapping the program's earliest label-signature construct; fallback g16, flagged).
"""

from __future__ import annotations

import copy
import gc
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

from common import (DATA_DIR, LAYERS, MODEL_ID, MODEL_REVISION, RESULTS_DIR, STATES_DIR, logmeanexp, logsumexp,
                    read_json, read_jsonl, sha256_text, timing, utc_now, write_json)

B = 8
CHUNK = 128
POS_NAMES = ("g8", "g16", "g32", "pre")
FRLP_CELLS = RESULTS_DIR / "frlp_cells.jsonl"
SCORES = DATA_DIR / "scores.jsonl"


# ------------------------------------------------------------------------------------------------ evidence locator
EVIDENCE = {
    "fifo": [r"\bdeque\b", r"\.popleft\(", r"\.pop\(0\)"],
    "heap": [r"\bheapq\b", r"\bheappush\b"],
    "manh": [r"abs\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*\)\s*\+\s*abs\("],
    "lifo": [r"\.pop\(\)"],
    "edges": [r"for\s+[^\n]*\bin\s+edges\b", r"\bdeque\b", r"\.popleft\("],
    "floyd": [r"for\s+k\s+in\b"],
}
LABEL_EVIDENCE = {
    "bfs": ["fifo"], "bibfs": ["fifo"], "astar": ["heap", "manh"], "gbfs": ["heap", "manh"],
    "dijkstra_unit": ["heap"], "jps": ["heap", "manh"], "biastar": ["heap", "manh"], "dijkstra": ["heap"],
    "dial": ["heap"], "dfs": ["lifo", "selfcall"], "iddfs": ["lifo", "selfcall"], "idastar": ["lifo", "selfcall", "manh"],
    "bf_spfa": ["edges"], "floyd": ["floyd"],
}


def _selfcall_offsets(code: str) -> list[int]:
    import ast

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    lines = code.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))
    out = []
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name and n is not fn:
                    out.append(offs[n.lineno - 1] + n.col_offset)
    return out


def evidence_char(text: str, code_start: int, code: str, label: str) -> int | None:
    """Earliest char offset (in `text`) of the label's signature constructs, searched from the code start."""
    kinds = LABEL_EVIDENCE.get(label) or sorted({k for v in LABEL_EVIDENCE.values() for k in v})
    best = None
    sub = text[code_start:]
    for k in kinds:
        if k == "selfcall":
            cands = [code_start + o for o in _selfcall_offsets(code)]
            # map code offsets to text offsets: code appears verbatim at code_start
        else:
            cands = []
            for pat in EVIDENCE[k]:
                m = re.search(pat, sub)
                if m:
                    cands.append(code_start + m.start())
        for c in cands:
            if best is None or c < best:
                best = c
    return best


def token_index_at(offsets: list[tuple[int, int]], ch: int) -> int | None:
    for i, (a, b) in enumerate(offsets):
        if a <= ch < b or (a >= ch and b > a):
            return i
    return None


# ------------------------------------------------------------------------------------------------ model wrapper
class Scorer:
    def __init__(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        t0 = time.time()
        self.tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION, dtype=torch.bfloat16,
                                                          attn_implementation="sdpa").cuda().eval()
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else self.tok.eos_token_id
        # fp32 copy of the output head: bf16 logits are quantised at ~0.1 nats near |logit| ~ 30, which summed over
        # ~350 tokens gives ~1 nat of path-dependent noise; an fp32 head removes that term
        self.lm_w = self.model.lm_head.weight.detach().float()
        self.layers = LAYERS
        self._buf: dict[int, torch.Tensor] = {}
        self._hooks = [self.model.model.layers[l].register_forward_hook(self._mk_hook(l)) for l in self.layers]
        self.capture = False
        logger.info(f"HF model loaded in {time.time() - t0:.0f}s; {torch.cuda.memory_allocated() / 1e9:.1f} GB")

    def _mk_hook(self, l: int):
        def hook(_m, _inp, out):
            if self.capture:
                self._buf[l] = out[0] if isinstance(out, tuple) else out
        return hook

    def head(self, h: torch.Tensor) -> torch.Tensor:
        return h.float() @ self.lm_w.T

    def chat_ids(self, prompt: str) -> list[int]:
        from mb.prompts import chat_text

        return self.tok(chat_text(prompt), add_special_tokens=False)["input_ids"]

    def resp_tok(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        enc = self.tok(text, add_special_tokens=False, return_offsets_mapping=True)
        return enc["input_ids"], [tuple(x) for x in enc["offset_mapping"]]

    @torch.no_grad()
    def prefill(self, prompt_ids: list[int], want_states: bool):
        from transformers import DynamicCache

        ids = torch.tensor([prompt_ids], device="cuda")
        cache = DynamicCache()
        self.capture = want_states
        self._buf = {}
        out = self.model.model(input_ids=ids, past_key_values=cache, use_cache=True)
        h_last = out.last_hidden_state[:, -1:, :]
        lp_first = torch.log_softmax(self.head(h_last)[0, -1], dim=-1)
        R = None
        if want_states:
            R = np.stack([self._buf[l][0, -1].float().cpu().numpy().astype(np.float16) for l in self.layers])
        self.capture = False
        self._buf = {}
        return out.past_key_values, lp_first, R

    @torch.no_grad()
    def score_batch(self, cache, lp_first: torch.Tensor, resp: list[list[int]], P: int,
                    state_pos: list[dict[str, int | None]] | None) -> tuple[list[float], list[np.ndarray] | None]:
        n = len(resp)
        T = max(len(r) for r in resp)
        ids = torch.full((n, T), self.pad, dtype=torch.long, device="cuda")
        mask = torch.zeros((n, T), dtype=torch.long, device="cuda")
        for i, r in enumerate(resp):
            ids[i, :len(r)] = torch.tensor(r, device="cuda")
            mask[i, :len(r)] = 1
        c = copy.deepcopy(cache)
        if n > 1:
            c.batch_repeat_interleave(n)
        attn = torch.cat([torch.ones((n, P), dtype=torch.long, device="cuda"), mask], dim=1)
        self.capture = state_pos is not None
        self._buf = {}
        out = self.model.model(input_ids=ids, attention_mask=attn, past_key_values=c, use_cache=True)
        hid = out.last_hidden_state
        tot = lp_first[ids[:, 0]].clone()
        for a in range(0, T - 1, CHUNK):
            b = min(T - 1, a + CHUNK)
            logits = self.head(hid[:, a:b])
            tgt = ids[:, a + 1:b + 1]
            lse = torch.logsumexp(logits, dim=-1)
            tl = torch.gather(logits, -1, tgt.unsqueeze(-1)).squeeze(-1)
            tot += ((tl - lse) * mask[:, a + 1:b + 1]).sum(dim=1)
            del logits, lse, tl
        states = None
        if state_pos is not None:
            states = []
            for i in range(n):
                arr = np.full((len(self.layers), len(POS_NAMES), hid.shape[-1]), np.nan, dtype=np.float16)
                for j, pn in enumerate(POS_NAMES):
                    p = state_pos[i].get(pn)
                    if p is not None and 0 <= p < len(resp[i]):
                        for li, l in enumerate(self.layers):
                            arr[li, j] = self._buf[l][i, p].float().cpu().numpy().astype(np.float16)
                states.append(arr)
        self.capture = False
        self._buf = {}
        del c, out, hid
        return [float(x) for x in tot.cpu()], states

    def score(self, prompt: str, items: list[dict[str, Any]], want_states: bool = False) -> dict[str, Any]:
        """items: {'uid', 'resp_ids', 'state_pos'?}. Returns {'l': {uid: logprob}, 'states': {uid: arr}, 'R': arr}."""
        pids = self.chat_ids(prompt)
        cache, lp_first, R = self.prefill(pids, want_states)
        order = sorted(range(len(items)), key=lambda i: len(items[i]["resp_ids"]))
        res_l, res_s = {}, {}
        bs = B
        k = 0
        while k < len(order):
            idx = order[k:k + bs]
            batch = [items[i] for i in idx]
            try:
                ls, st = self.score_batch(cache, lp_first, [b["resp_ids"] for b in batch], len(pids),
                                          [b.get("state_pos") or {} for b in batch] if want_states else None)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                bs = max(1, bs // 2)
                logger.warning(f"OOM: batch size -> {bs}")
                continue
            for j, b in enumerate(batch):
                res_l[b["uid"]] = ls[j]
                if st is not None:
                    res_s[b["uid"]] = st[j]
            k += len(idx)
        del cache
        return {"l": res_l, "states": res_s, "R": R, "n_prompt_tokens": len(pids)}


# ------------------------------------------------------------------------------------------------ state storage
class StateWriter:
    """Buffers per-program state arrays and writes states/{task}/{context}/part_NNN.npz (each <= ~90 MB)."""

    def __init__(self, task: str, context: str, max_mb: float = 85.0) -> None:
        self.dir = STATES_DIR / task / context
        self.dir.mkdir(parents=True, exist_ok=True)
        self.max_n = int(max_mb * 1e6 // (len(LAYERS) * len(POS_NAMES) * 4096 * 2))
        self.buf: list[tuple[str, np.ndarray, dict[str, Any]]] = []
        self.R: dict[str, np.ndarray] = {}
        self.part = len(list(self.dir.glob("part_*.npz")))

    def add(self, uid: str, arr: np.ndarray, meta: dict[str, Any]) -> None:
        self.buf.append((uid, arr, meta))
        if len(self.buf) >= self.max_n:
            self.flush()

    def add_R(self, key: str, R: np.ndarray | None) -> None:
        if R is not None:
            self.R[key] = R

    def flush(self) -> None:
        if not self.buf and not self.R:
            return
        self.part += 1
        p = self.dir / f"part_{self.part:03d}.npz"
        uids = np.array([u for u, _, _ in self.buf], dtype=object) if self.buf else np.array([], dtype=object)
        X = np.stack([a for _, a, _ in self.buf]) if self.buf else np.zeros((0, len(LAYERS), len(POS_NAMES), 4096),
                                                                            dtype=np.float16)
        meta = json.dumps([m for _, _, m in self.buf])
        rk = list(self.R.keys())
        Rarr = np.stack([self.R[k] for k in rk]) if rk else np.zeros((0, len(LAYERS), 4096), dtype=np.float16)
        np.savez(p, uids=uids.astype(str), X=X, meta=np.array(meta), R_keys=np.array(rk, dtype=str), R=Rarr,
                 layers=np.array(LAYERS), positions=np.array(POS_NAMES))
        logger.info(f"states: wrote {p.relative_to(STATES_DIR.parent)} ({len(self.buf)} programs, {len(rk)} R)")
        self.buf, self.R = [], {}


def load_states(task: str, context: str) -> dict[str, Any]:
    d = STATES_DIR / task / context
    uids, Xs, metas, R = [], [], [], {}
    for p in sorted(d.glob("part_*.npz")):
        z = np.load(p, allow_pickle=False)
        uids += list(z["uids"])
        Xs.append(z["X"])
        metas += json.loads(str(z["meta"]))
        for k, r in zip(z["R_keys"], z["R"]):
            R[str(k)] = r
    X = np.concatenate(Xs) if Xs else np.zeros((0, len(LAYERS), len(POS_NAMES), 4096), dtype=np.float16)
    return {"uids": uids, "X": X, "meta": metas, "R": R}


# ------------------------------------------------------------------------------------------------ helpers
def program_items(sc: Scorer, progs: list[dict[str, Any]], with_pos: bool) -> list[dict[str, Any]]:
    """Scored response = fenced scrubbed code; state positions from its own offsets."""
    items = []
    for p in progs:
        ids, offs = sc.resp_tok(p["response"])
        it = {"uid": p["uid"], "resp_ids": ids}
        if with_pos:
            fence_len = len(p["response"].split("\n", 1)[0]) + 1
            ch = evidence_char(p["response"], fence_len, p["scrubbed_code"], p["algorithm"] if "algorithm" in p
                               else p.get("label", "other"))
            ti = token_index_at(offs, ch) if ch is not None else None
            pre = ti - 1 if ti is not None and ti >= 1 else None
            it["state_pos"] = {"g8": 8, "g16": 16, "g32": 32, "pre": pre if pre is not None else 16}
            it["pre_fallback"] = pre is None
            it["n_tokens"] = len(ids)
        items.append(it)
    return items


def frlp(l_c: list[float], l_F: list[float]) -> tuple[float, float]:
    r = [a - b for a, b in zip(l_c, l_F)]
    L = logsumexp(r) - math.log(len(r))
    ess = math.exp(2 * logsumexp(r) - logsumexp([2 * x for x in r]))
    return L, ess


def append_scores(rows: list[dict[str, Any]]) -> None:
    with SCORES.open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def load_scores() -> dict[tuple[str, str], float]:
    """(prompt_key, uid) -> l."""
    out = {}
    for r in read_jsonl(SCORES):
        out[(r["prompt_key"], r["uid"])] = r["l"]
    return out


def run_cell(sc: Scorer, done: dict[tuple[str, str], float], prompt_key: str, prompt: str,
             progs: list[dict[str, Any]], items_by_uid: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Score progs under one prompt unless cached; returns uid -> l."""
    todo = [p for p in progs if (prompt_key, p["uid"]) not in done]
    if todo:
        res = sc.score(prompt, [items_by_uid[p["uid"]] for p in todo], want_states=False)
        rows = [{"prompt_key": prompt_key, "uid": u, "l": l, "utc": utc_now()} for u, l in res["l"].items()]
        append_scores(rows)
        for r in rows:
            done[(prompt_key, r["uid"])] = r["l"]
    return {p["uid"]: done[(prompt_key, p["uid"])] for p in progs}


def run_score_stage(stage: str, limit: int | None = None) -> None:
    from mb.score_stages import stage_score1a, stage_score1b, stage_score2

    {"score1a": stage_score1a, "score1b": stage_score1b, "score2": stage_score2}[stage](limit=limit)


__all__ = ["Scorer", "StateWriter", "load_states", "program_items", "frlp", "run_cell", "load_scores",
           "append_scores", "evidence_char", "token_index_at", "FRLP_CELLS", "POS_NAMES", "gc", "Path", "read_json",
           "write_json", "sha256_text", "logmeanexp", "timing"]
