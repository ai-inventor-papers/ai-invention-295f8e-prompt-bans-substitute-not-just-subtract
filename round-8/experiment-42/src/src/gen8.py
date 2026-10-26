#!/usr/bin/env python3
"""Free-generation runner for iteration 8: decode-time edits at a per-row response index, per-step fork
diagnostics, and the decision-position rule.

decode8() is iteration 7's engine.decode (exact inverse-CDF CRN sampler, fixed batch shape, fence stop) with three
additions that never change an unedited row:
  - sched {step s: [(rows, fn, name)]}: a forward hook on decoder block L applies fn to the block-L output of the
    listed rows during the decode forward whose INPUT token is response index s (its logits choose token s + 1),
    so the edited state enters the KV cache of blocks L+1..33 and persists, exactly as a prefill edit at p_f does;
  - per-step records for response indices 0..rec_upto-1: p_B, p_D, p(' queue'), margin m and the top-1 token of the
    distribution that chooses token s (fp32 logits, T = 1);
  - force (U3' only): response tokens fed instead of the sampled ones for the first len(force) steps.
run_cell_free() mirrors gen7.Runner.run_cell (one prompt, fixed-shape batches of B_CRN rows, CRN stream index =
response index) with no prefill edit, so a free row that reproduces c* consumes exactly the uniforms a prefilled run
of the same slot skips.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

import engine as EG
from cfg import B_IDS, D_IDS, EOT_ID, FORK_INDEX, IT_ID, STOP_CHECK_EVERY, STOP_IDS, append_jsonl, utc_now
from cfg8 import ALG_STRINGS, DEC_MAX, DEC_MIN, L, MAX_NEW, Q_ID, REC_UPTO
from gen7 import TIMING, Runner


# ------------------------------------------------------------------------------------------------ decision rule
def decide(tokens: list[int], pB: list[float], pD: list[float], cstar: list[int],
           decode: Callable[[list[int]], str]) -> dict[str, Any]:
    """Committed decision-position rule (R1 / R2 / NOT_REACHED) on the unedited free twin's trajectory.
    pB[i], pD[i] = class masses of the distribution that chooses response token i (NaN once the row is done)."""
    n = len(tokens)
    if n >= 32 and list(tokens[:32]) == list(cstar):
        return {"reach_type": "R1", "i_d": 32}
    indent = cstar[31]
    for i in range(DEC_MIN, DEC_MAX + 1):
        if i >= n or i >= len(pB):
            break
        if any(s in decode(list(tokens[:i])).lower() for s in ALG_STRINGS):
            break                       # the prefix only grows: no later index qualifies
        if tokens[i - 1] != indent:
            continue
        b, d = pB[i], pD[i]
        if not (np.isfinite(b) and np.isfinite(d)):
            break
        if b + d >= 0.5 and d >= 0.01:
            return {"reach_type": "R2", "i_d": i}
    return {"reach_type": "NOT_REACHED", "i_d": None}


def literal_rule(pB: list[float], pD: list[float], upto: int = DEC_MAX) -> int | None:
    """Diagnostic only: the direction's literal rule (first i <= 96 with p_B + p_D >= 0.5)."""
    for i in range(0, min(upto + 1, len(pB))):
        if np.isfinite(pB[i]) and pB[i] + pD[i] >= 0.5:
            return i
    return None


# ------------------------------------------------------------------------------------------------ decode
@torch.no_grad()
def decode8(model: Any, tok: Any, pre: dict[str, Any], U: np.ndarray, temps: np.ndarray, max_new: int,
            sched: dict[int, list[tuple[torch.Tensor, Callable[[torch.Tensor], torch.Tensor], str]]] | None = None,
            rec_upto: int = REC_UPTO, active: np.ndarray | None = None, force: list[int] | None = None,
            fence_stop: bool = True, layer: int = L) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    B = U.shape[0]
    P = pre["P"]
    dev = torch.device("cuda")
    stop_ids = STOP_IDS[getattr(model, "_aii_kind", "it")]
    cache = EG.build_prealloc(pre["kv"], P + max_new + 1)
    pre["kv"] = None
    Ut = torch.tensor(U[:, :max_new], dtype=torch.float64, device=dev)
    Tt = torch.tensor(temps, dtype=torch.float32, device=dev)[:, None]
    logits = pre["logits"]
    V = logits.shape[-1]
    stop_t = torch.tensor(stop_ids, device=dev)
    toks = torch.full((B, max_new), -1, dtype=torch.long, device=dev)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    ended = torch.zeros(B, dtype=torch.bool, device=dev)
    fenced = torch.zeros(B, dtype=torch.bool, device=dev)
    eot_t = torch.full((B,), EOT_ID, dtype=torch.long, device=dev)
    nrec = min(rec_upto, max_new)
    rec = {k: torch.full((B, nrec), float("nan"), device=dev) for k in ("pB", "pD", "pQ", "m")}
    rec_top = torch.full((B, nrec), -1, dtype=torch.long, device=dev)
    Bt = torch.tensor(list(B_IDS), device=dev)
    cpu_ids: list[list[int]] = [[] for _ in range(B)]
    done_cpu = np.zeros(B, dtype=bool)
    if active is not None:
        inactive = torch.tensor(~np.asarray(active, dtype=bool), device=dev)
        done |= inactive
        done_cpu |= ~np.asarray(active, dtype=bool)
    reason_cpu = [""] * B
    sched = sched or {}
    state = {"step": -1}
    elog: dict[int, dict[str, Any]] = {}
    force_t = torch.tensor(force, device=dev) if force else None

    def hook(mod, inp, out):
        items = sched.get(state["step"])
        if not items:
            return None
        x = out[0] if isinstance(out, tuple) else out
        if x.shape[1] != 1:
            return None
        x = x.clone()
        for rows_t, fn, name in items:
            cur = x[rows_t, 0].float()
            new = fn(cur)
            x[rows_t, 0] = new.to(x.dtype)
            dn = (new - cur).norm(dim=-1).cpu().tolist()
            dq = (x[rows_t, 0].float() - cur).norm(dim=-1).cpu().tolist()
            for j, r in enumerate(rows_t.cpu().tolist()):
                elog[r] = {"edit_name": name, "edit_step": state["step"], "edit_norm_fp32": dn[j],
                           "edit_norm_bf16": dq[j], "h_norm": float(cur[j].norm())}
        return (x,) + tuple(out[1:]) if isinstance(out, tuple) else x

    hdl = model.model.layers[layer].register_forward_hook(hook) if sched else None
    synced = 0
    step = 0
    t0 = time.time()
    try:
        while True:
            z = logits / Tt
            probs = torch.softmax(z, dim=-1)
            if step < nrec:             # rows already finished get NaN (their distribution is meaningless)
                lz = logits.float()
                nanv = torch.full((B,), float("nan"), device=dev)
                rec["pB"][:, step] = torch.where(done, nanv, probs[:, Bt].sum(-1))
                rec["pD"][:, step] = torch.where(done, nanv, probs[:, D_IDS[0]])
                rec["pQ"][:, step] = torch.where(done, nanv, probs[:, Q_ID])
                rec["m"][:, step] = torch.where(done, nanv, torch.logsumexp(lz[:, Bt], -1) - lz[:, D_IDS[0]])
                rec_top[:, step] = torch.where(done, torch.full_like(rec_top[:, step], -1), lz.argmax(-1))
            cdf = probs.double().cumsum(dim=-1)
            cdf = cdf / cdf[:, -1:]
            nxt = torch.searchsorted(cdf, Ut[:, step:step + 1]).squeeze(-1).clamp_(max=V - 1)
            if force_t is not None and step < force_t.numel():
                nxt = force_t[step].expand(B).clone()
            live = ~done
            toks[:, step] = torch.where(live, nxt, toks[:, step])
            is_end = torch.isin(nxt, stop_t)
            ended |= live & is_end
            done |= is_end
            if step + 1 >= max_new:
                break
            if (step + 1) % STOP_CHECK_EVERY == 0:
                chunk = toks[:, synced:step + 1].cpu().numpy()
                dnow = done.cpu().numpy()
                synced = step + 1
                newly = []
                for r in range(B):
                    if done_cpu[r]:
                        continue
                    cpu_ids[r].extend(int(t) for t in chunk[r] if t >= 0)
                    if dnow[r]:
                        done_cpu[r] = True
                        continue
                    if fence_stop and "```" in tok.decode(cpu_ids[r][-24:]) and EG.fence_closed(tok.decode(cpu_ids[r])):
                        newly.append(r)
                        done_cpu[r] = True
                        reason_cpu[r] = "fence"
                if newly:
                    idx = torch.tensor(newly, device=dev)
                    done[idx] = True
                    fenced[idx] = True
                if done_cpu.all():
                    break
            feed = torch.where(done, eot_t, nxt)[:, None]
            pos = torch.full((B, 1), P + step, device=dev, dtype=torch.long)
            state["step"] = step
            h = model.model(input_ids=feed, past_key_values=cache, position_ids=pos, use_cache=True).last_hidden_state
            state["step"] = -1
            logits = EG.lm_logits(model, h[:, -1])
            step += 1
    finally:
        if hdl is not None:
            hdl.remove()
    dt = time.time() - t0
    del cache
    toks_c = toks.cpu().numpy()
    ended_c = ended.cpu().numpy()
    fenced_c = fenced.cpu().numpy()
    recs = {k: v.cpu().numpy() for k, v in rec.items()}
    top_c = rec_top.cpu().numpy()
    out = []
    for r in range(B):
        row = toks_c[r]
        n = int((row >= 0).sum())
        ids = [int(t) for t in row[:n]]
        fr = "stop" if ended_c[r] else ((reason_cpu[r] or "fence") if fenced_c[r] else "length")
        if active is not None and not active[r]:
            fr = "pad"
        nr = min(n, nrec)       # distributions exist for indices 0..n-1 (index n would follow the last token)
        out.append({"token_ids": ids, "finish_reason": fr, "n_tokens": n, "steps": step + 1,
                    "text": tok.decode(ids, skip_special_tokens=True),
                    "rec": {"pB": [float(x) for x in recs["pB"][r][:nr]], "pD": [float(x) for x in recs["pD"][r][:nr]],
                            "pQ": [float(x) for x in recs["pQ"][r][:nr]], "m": [float(x) for x in recs["m"][r][:nr]],
                            "top1": [int(x) for x in top_c[r][:nr]]},
                    "edit": elog.get(r)})
    logger.debug(f"decode8 B={B} P={P} steps={step + 1} in {dt:.1f}s ({1000 * dt / max(step + 1, 1):.1f} ms/step)")
    return out, {"seconds": dt, "steps": step + 1}


class FreeRunner(Runner):
    """gen7.Runner plus free-generation cells with decode-time edits."""

    def run_cell_free(self, ids: list[int], rows: list[dict[str, Any]], raw_path: Path, tag: str,
                      steps_path: Path | None = None, max_new: int = MAX_NEW) -> list[dict[str, Any]]:
        """rows: {row_id, ukey, temperature?, edit: None | {'i_d': int, 'fn': f(h [r, D] fp32) -> [r, D],
        'name': str, 'log': dict}, meta}. The edit is applied at decode step i_d - 1 (input token = response index
        i_d - 1). No prefill edit, response prefix empty (stream index = response index)."""
        B = self.B
        out_all = []
        for b0 in range(0, len(rows), B):
            chunk = rows[b0:b0 + B]
            n_real = len(chunk)
            pad = B - n_real
            t0 = time.time()
            pre = self.prefill(ids, B, [])
            Us = [EG.u_stream(*r["ukey"], n=max_new) for r in chunk] + [np.full(max_new, 0.5)] * pad
            temps = np.array([float(r.get("temperature", 1.0)) for r in chunk] + [1.0] * pad)
            active = np.array([True] * n_real + [False] * pad)
            groups: dict[tuple[int, int], tuple[Callable, str, list[int]]] = {}
            for i, r in enumerate(chunk):
                e = r.get("edit")
                if e is None:
                    continue
                key = (int(e["i_d"]) - 1, id(e["fn"]))
                groups.setdefault(key, (e["fn"], e["name"], []))[2].append(i)
            sched: dict[int, list[tuple[torch.Tensor, Callable, str]]] = {}
            for (s, _), (fn, name, ix) in groups.items():
                sched.setdefault(s, []).append((torch.tensor(ix, device="cuda", dtype=torch.long), fn, name))
            res, info = decode8(self.model, self.tok, pre, np.stack(Us), temps, max_new, sched=sched, active=active)
            del pre
            out, steps_rows = [], []
            for r, g in zip(chunk, res[:n_real]):
                resp = g["token_ids"]
                e = r.get("edit")
                out.append({"row_id": r["row_id"], "task": "T1", "model": IT_ID, "ukey": list(r["ukey"]),
                            "temperature": float(r.get("temperature", 1.0)), "top_k": 0, "prefix_len": 0,
                            "text": g["text"], "token_ids": resp, "finish_reason": g["finish_reason"],
                            "n_new_tokens": g["n_tokens"],
                            "fork_token": resp[FORK_INDEX] if len(resp) > FORK_INDEX else None,
                            "B": B, "max_new": max_new, "logit_only": False, "batch_id": f"{tag}:{b0 // B}",
                            "utc": utc_now(), "edit_scheduled_i_d": (int(e["i_d"]) if e else None),
                            "edit_log": ([dict(e.get("log") or {}, name=e["name"], **(g["edit"] or {}))] if e else []),
                            "edit_applied": bool(g["edit"]), **(r.get("meta") or {})})
                steps_rows.append({"row_id": r["row_id"], "rec": g["rec"]})
            append_jsonl(raw_path, out)
            if steps_path is not None:
                append_jsonl(steps_path, steps_rows)
            out_all += out
            dt = time.time() - t0
            append_jsonl(TIMING, [{"batch_id": f"{tag}:{b0 // B}", "n_real": n_real, "B": B, "seconds": dt,
                                   "steps": info["steps"], "max_new": max_new, "utc": utc_now()}])
            fr: dict[str, int] = {}
            for g in res[:n_real]:
                fr[g["finish_reason"]] = fr.get(g["finish_reason"], 0) + 1
            logger.info(f"{tag}:{b0 // B}: {n_real}/{B} rows {dt:.1f}s, {info['steps']} steps, {fr}")
        return out_all
