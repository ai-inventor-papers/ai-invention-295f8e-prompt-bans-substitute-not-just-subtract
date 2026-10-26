#!/usr/bin/env python3
"""Phase D (HF hooks): affine mean-anchored directional ablation of the modal mode over the 7-layer band.

Edit at every hooked position (prompt suffix during prefill, every generated position during decoding):
    d_X arm    : h <- h - alpha * ((h - m) . d) d
    random arm : h <- h - alpha * ((h - m) . d) r      (same scalar, random unit r: identical edit norm)
m = per-position anchor (prompt-suffix anchors by offset; generated anchors by index t<64, pooled for t>=64),
d = d_hat at prompt positions and d_gen at generated positions (d_gen = d_hat when its generated AUC >= 0.9).
Common random numbers: torch.manual_seed(1000 + b) per batch b, identical batch composition across arms.
Outputs: data/samples_phaseD.jsonl, results/phaseD_tests.json, cache/hR_ablated_{task}.npz
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "gen"))
sys.path.insert(0, str(ROOT / "labeller"))
sys.path.insert(0, str(ROOT / "tasks"))
from common import (CATALOGUE, DECODING_HOOK, MODEL_TAG, TASKS, add_deviation, append_jsonl, log_timing,  # noqa: E402
                    read_jsonl, setup_logger, sha256_file, sha256_text)

logger = setup_logger("phase_d")
GEN_T = 64


class Editor:
    """Holds the per-layer edit parameters and the decode-step counter shared by all hooks."""

    def __init__(self, model, band, d_hat, d_gen, anchors, L_s, device):
        import torch

        self.torch = torch
        self.band = list(band)
        self.d_hat = {l: torch.tensor(d_hat[i], device=device, dtype=torch.float32) for i, l in enumerate(band)}
        self.d_gen = {l: torch.tensor(d_gen[i], device=device, dtype=torch.float32) for i, l in enumerate(band)}
        self.m_prompt = {l: torch.tensor(anchors["m_prompt"][i], device=device, dtype=torch.float32) for i, l in enumerate(band)}
        self.m_gen = {l: torch.tensor(anchors["m_gen"][i], device=device, dtype=torch.float32) for i, l in enumerate(band)}
        self.m_pool = {l: torch.tensor(anchors["m_gen_pool"][i], device=device, dtype=torch.float32) for i, l in enumerate(band)}
        self.has_gen = {l: bool(anchors["has_gen"][i]) for i, l in enumerate(band)}
        self.L_s = L_s
        self.gen_edit = True  # False -> 'R-plus-prompt' variant: edit the prompt suffix (incl. R) only
        self.alpha = 0.0
        self.out_dir = None  # None -> along d itself; else {l: tensor} random directions
        self.active = False
        self.step = -1
        self.T_pad = 0
        self.capture = {}
        self.capture_layers = set()
        self.log_stats = False
        self.stats = []
        self.cache_pos_check = []
        self.handles = []
        self.handles.append(model.model.register_forward_pre_hook(self._pre, with_kwargs=True))
        for l in self.band:
            self.handles.append(model.model.layers[l].register_forward_hook(self._make(l)))

    def _pre(self, module, args, kwargs):
        x = kwargs.get("input_ids")
        if x is None and args:
            x = args[0]
        if x is None:
            x = kwargs.get("inputs_embeds")
        T = x.shape[1]
        cp = kwargs.get("cache_position")
        if T > 1:
            self.step = -1
            self.T_pad = T
        else:
            self.step += 1
            if cp is not None and len(self.cache_pos_check) < 50:
                self.cache_pos_check.append(int(cp.reshape(-1)[0].item()) - self.T_pad == self.step)

    def _make(self, l):
        def hook(module, inputs, output):
            torch = self.torch
            h = output[0] if isinstance(output, tuple) else output
            if self.active and self.alpha != 0.0 and (self.step < 0 or self.gen_edit):
                hf = h.float()
                if self.step < 0:
                    sl = slice(h.shape[1] - self.L_s, h.shape[1])
                    m = self.m_prompt[l]
                    d = self.d_hat[l]
                else:
                    sl = slice(h.shape[1] - 1, h.shape[1])
                    t = self.step
                    if self.has_gen[l]:
                        m = self.m_gen[l][t] if t < GEN_T else self.m_pool[l]
                    else:
                        m = torch.zeros_like(self.m_pool[l])
                    d = self.d_gen[l]
                seg = hf[:, sl, :]
                coef = (seg - m) @ d  # [B, P]
                v = d if self.out_dir is None else self.out_dir[l]
                edit = self.alpha * coef[..., None] * v
                new = seg - edit
                if self.log_stats:
                    post = (new - m) @ d
                    self.stats.append({"layer": l, "step": self.step,
                                       "pre_abs": float(coef.abs().mean()), "post_abs": float(post.abs().mean()),
                                       "edit_norm": float(edit.norm(dim=-1).mean())})
                hf[:, sl, :] = new
                h2 = hf.to(h.dtype)
            else:
                h2 = h
            if l in self.capture_layers and self.step < 0:
                self.capture[l] = h2[:, -1, :].float().cpu().numpy()
            if isinstance(output, tuple):
                return (h2,) + tuple(output[1:])
            return h2

        return hook

    def remove(self):
        for hd in self.handles:
            hd.remove()


def gen_arm(model, tok, ed: Editor, prompts_cycle, n: int, batch: int, alpha: float, out_dir, label: str, task: str,
            max_new: int = 768) -> list[dict]:
    import torch
    from hf_engine import EOS_IDS, PAD_ID, gen_config, left_pad
    from vllm_engine import CLOSE_FENCE_STOP, extract_code

    rows = []
    ed.alpha, ed.out_dir, ed.active = alpha, out_dir, True
    for b in range(0, n, batch):
        idx = list(range(b, min(n, b + batch)))
        ps = [prompts_cycle[i % len(prompts_cycle)] for i in idx]
        ids, att = left_pad([p["prompt_ids"] for p in ps], "cuda")
        torch.manual_seed(1000 + b // batch)
        t0 = time.time()
        with torch.inference_mode():
            gen = model.generate(input_ids=ids, attention_mask=att, generation_config=gen_config(max_new),
                                 stop_strings=[CLOSE_FENCE_STOP], tokenizer=tok)
        dt = time.time() - t0
        new = gen[:, ids.shape[1]:].cpu()
        for i, p, row in zip(idx, ps, new):
            toks = row.tolist()
            nn = len(toks)
            while nn > 0 and toks[nn - 1] == PAD_ID:
                nn -= 1
            toks = toks[:nn]
            eos = bool(toks) and toks[-1] in EOS_IDS
            toks = [t for t in toks if t not in EOS_IDS]
            text = tok.decode(toks, skip_special_tokens=False)
            finish = "stop"
            if CLOSE_FENCE_STOP in text:
                text = text[: text.index(CLOSE_FENCE_STOP) + len(CLOSE_FENCE_STOP)]
            elif not eos and nn >= max_new:
                finish = "length"
            code = extract_code(text) if finish != "length" else None
            rows.append({"task": task, "condition": f"removal:{label}", "arm": label, "alpha": alpha,
                         "paraphrase_id": p["paraphrase_id"], "sample_id": i, "prompt_id": p["prompt_id"],
                         "model": MODEL_TAG, "decoding": DECODING_HOOK, "batch_seed": 1000 + b // batch,
                         "raw_text": text, "finish_reason": finish, "n_gen_tokens": len(toks), "code": code,
                         "code_sha256": sha256_text(code) if code else None, "utc": time.time(), "phase": "D"})
        logger.info(f"{task} {label} batch {b // batch}: {len(idx)} rows, {new.shape[1]} steps in {dt:.0f}s")
        log_timing("D", f"{task}:{label}", len(idx), dt)
        del gen, new, ids, att
    ed.active = False
    return rows


def run_tests(model, tok, ed: Editor, prompts_cycle, task) -> dict:
    """Testing plan 5: alpha=0 logits identity, projection removal at alpha=1, random edit norm equality,
    decode index from cache_position."""
    import torch
    from hf_engine import left_pad

    ids, att = left_pad([p["prompt_ids"] for p in prompts_cycle[:4]], "cuda")
    pos = (att.cumsum(-1) - 1).clamp(min=0)
    res = {}
    with torch.inference_mode():
        ed.active = False
        base = model(input_ids=ids, attention_mask=att, position_ids=pos).logits[:, -1].float()
        ed.active, ed.alpha, ed.out_dir = True, 0.0, None
        hz = model(input_ids=ids, attention_mask=att, position_ids=pos).logits[:, -1].float()
        res["alpha0_logit_maxdiff"] = float((base - hz).abs().max())
        ed.alpha, ed.log_stats, ed.stats = 1.0, True, []
        model(input_ids=ids, attention_mask=att, position_ids=pos)
        st = ed.stats
        res["alpha1_post_over_pre_projection"] = float(max(s["post_abs"] / max(s["pre_abs"], 1e-9) for s in st))
        # the first band layer sees identical inputs in both runs (later layers see the earlier edits)
        dn = [s["edit_norm"] for s in st if s["layer"] == ed.band[0]]
        ed.stats = []
        ed.out_dir = RAND_CACHE[task][0]
        model(input_ids=ids, attention_mask=att, position_ids=pos)
        rn = [s["edit_norm"] for s in ed.stats if s["layer"] == ed.band[0]]
        res["random_vs_dX_edit_norm_ratio_max_dev"] = float(max(abs(a / b - 1) for a, b in zip(rn, dn)))
        ed.log_stats, ed.active, ed.out_dir = False, False, None
    # decode-step index vs cache_position (short generate)
    ed.cache_pos_check = []
    ed.active, ed.alpha = True, 1.0
    from hf_engine import gen_config

    with torch.inference_mode():
        torch.manual_seed(0)
        model.generate(input_ids=ids, attention_mask=att, generation_config=gen_config(8))
    ed.active = False
    res["decode_index_matches_cache_position"] = bool(all(ed.cache_pos_check)) if ed.cache_pos_check else None
    res["pass"] = (res["alpha0_logit_maxdiff"] < 1e-2 and res["alpha1_post_over_pre_projection"] < 2e-2 and
                   res["random_vs_dX_edit_norm_ratio_max_dev"] < 1e-3)
    logger.info(f"{task} hook tests: {res}")
    return res


RAND_CACHE: dict = {}


@logger.catch(reraise=True)
def main() -> None:
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--n-rand", type=int, default=25)
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--alphas", default="1.0,0.5")
    ap.add_argument("--rand-alphas", default="1.0,0.5")
    ap.add_argument("--deadline-min", type=float, default=60)
    ap.add_argument("--exploratory-full", action="store_true",
                    help="post-hoc exploratory arms: full affine variant (prompt suffix + generated positions)")
    args = ap.parse_args()
    if args.exploratory_full:
        return exploratory_full(args)
    t_start = time.time()
    pf = ROOT / "predictions" / "predictions_v1.json"
    log = read_jsonl(ROOT / "predictions" / "commit_log.jsonl")
    assert log and sha256_file(pf) == log[-1]["sha256"], "predictions hash mismatch: refusing to run removal"
    preds = json.loads(pf.read_text())
    summA = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    gate = json.loads((ROOT / "results" / "gate.json").read_text())
    geoB = json.loads((ROOT / "results" / "geometry_b.json").read_text())
    prompts = [p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl") if p["kind"] == "geom"]
    from hf_engine import load_model
    from label import label_rows

    model, tok = load_model(logger)
    (ROOT / "data" / "samples_phaseD.jsonl").unlink(missing_ok=True)
    tests = {}
    summary = {}
    for t in TASKS:
        X = summA[t]["modal"]
        assert f"{t}|removal:{X}" in preds["events"], "removal event not committed"
        D = np.load(ROOT / "cache" / f"directions_{t}.npz")
        A = np.load(ROOT / "cache" / f"anchors_{t}.npz")
        band = [int(x) for x in D["band"]]
        L_s = next(p["suffix_len"] for p in prompts if p["task"] == t)
        ed = Editor(model, band, D["d_hat"], D["d_gen"], A, L_s, "cuda")
        # pre-declared GEOMETRY fallback: d_X AUC at R < 0.9 AND generated-position AUC < 0.9 (even with d_X_gen)
        # -> run the removal at R and the prompt suffix only (the 'R-plus-prompt' variant)
        dirs = geoB[t]["directions"]
        lstar_ = gate[t]["l_star"]
        aucR = dirs["auc_R_heldout"][str(lstar_)]
        aucG = max(dirs["auc_gen_Rdir"][str(lstar_)], dirs["auc_gen_dgen_heldout"][str(lstar_)])
        both_fail = aucR < 0.9 and aucG < 0.9
        ed.gen_edit = not both_fail
        variant = "R-plus-prompt (prompt suffix incl. R only)" if both_fail else "affine at prompt suffix + generated positions"
        add_deviation(f"{t}: removal variant = {variant}; held-out d_X AUC at R (l*={lstar_}) = {aucR:.3f}, "
                      f"best generated-position AUC = {aucG:.3f} (pre-declared rule: both < 0.9 -> R-plus-prompt).")
        logger.info(f"{t}: removal variant {variant} (aucR {aucR:.3f}, aucGen {aucG:.3f})")
        RAND_CACHE[t] = [{l: torch.tensor(D[k][i], device="cuda", dtype=torch.float32) for i, l in enumerate(band)}
                         for k in ("r1", "r2")]
        base_ps = sorted([p for p in prompts if p["task"] == t and p["condition"] == "baseline"],
                         key=lambda p: p["paraphrase_id"])
        tests[t] = run_tests(model, tok, ed, base_ps, t)
        # ablated-baseline read-position states for the manifold figure (alpha=1, d_X)
        lstar = gate[t]["l_star"]
        ed.capture_layers = set(band)
        ed.active, ed.alpha, ed.out_dir = True, 1.0, None
        from hf_engine import left_pad

        ids, att = left_pad([p["prompt_ids"] for p in base_ps], "cuda")
        pos = (att.cumsum(-1) - 1).clamp(min=0)
        with torch.inference_mode():
            model.model(input_ids=ids, attention_mask=att, position_ids=pos, use_cache=False)
        np.savez(ROOT / "cache" / f"hR_ablated_{t}.npz", band=np.array(band),
                 h=np.stack([ed.capture[l] for l in band]).astype(np.float16), l_star=lstar)
        ed.capture_layers, ed.capture, ed.active = set(), {}, False
        rows_all = []
        # core arms first: hooked alpha=0, d_X alpha=1.0, both random controls at alpha=1.0
        arms = [("hooked_alpha0", 0.0, None, args.n), ("dX_a1.0", 1.0, None, args.n),
                ("r1_a1.0", 1.0, RAND_CACHE[t][0], args.n_rand), ("r2_a1.0", 1.0, RAND_CACHE[t][1], args.n_rand)]
        for name, a, od, n in arms:
            rows = gen_arm(model, tok, ed, base_ps, n, args.batch, a, od, name, t)
            label_rows(rows, logger, workers=5)
            for r in rows:
                r["compliant"] = bool(r["passed"]) and r["label"] not in (X, "no_code")
            append_jsonl(ROOT / "data" / "samples_phaseD.jsonl", rows)
            rows_all += rows
        # escalation check (pre-declared): first 8 samples at alpha=1.0
        a0 = [r for r in rows_all if r["arm"] == "hooked_alpha0"]
        a1 = [r for r in rows_all if r["arm"] == "dX_a1.0"]
        moved8 = sum(r["label"] not in (X, "no_code") for r in a1[:8])
        pr0 = np.mean([r["passed"] for r in a0])
        pr1 = np.mean([r["passed"] for r in a1[:8]])
        escalate = moved8 < 2 and pr1 >= 0.8 * pr0
        extra = []
        if escalate:
            add_deviation(f"{t}: pre-declared alpha escalation triggered (moved {moved8}/8 at alpha=1.0, pass "
                          f"{pr1:.2f} vs {pr0:.2f}); alpha=2.0 added.")
            extra += [("dX_a2.0", 2.0, None, args.n), ("r1_a2.0", 2.0, RAND_CACHE[t][0], args.n_rand)]
        extra += [("dX_a0.5", 0.5, None, args.n)]
        extra += [("r1_a0.5", 0.5, RAND_CACHE[t][0], args.n_rand), ("r2_a0.5", 0.5, RAND_CACHE[t][1], args.n_rand)]
        for name, a, od, n in extra:
            el = (time.time() - t_start) / 60
            budget_left = args.deadline_min * (1 if t == TASKS[-1] else 0.5) - el
            if name.startswith("r") and "0.5" in name and budget_left < 4:
                add_deviation(f"{t}: random controls at alpha 0.5 dropped (time drop order 4).")
                continue
            if budget_left < 3 and name != "dX_a2.0":
                add_deviation(f"{t}: arm {name} dropped for time.")
                continue
            rows = gen_arm(model, tok, ed, base_ps, n, args.batch, a, od, name, t)
            label_rows(rows, logger, workers=5)
            for r in rows:
                r["compliant"] = bool(r["passed"]) and r["label"] not in (X, "no_code")
            append_jsonl(ROOT / "data" / "samples_phaseD.jsonl", rows)
            rows_all += rows
        summary[t] = {"modal": X, "band": band, "variant": variant, "gen_edit": ed.gen_edit,
                      "escalated": bool(escalate), "moved_first8_alpha1": int(moved8),
                      "arms": sorted({r["arm"] for r in rows_all})}
        ed.remove()
        torch.cuda.empty_cache()
    (ROOT / "results" / "phaseD_tests.json").write_text(json.dumps({"tests": tests, "summary": summary,
                                                                    "elapsed_min": (time.time() - t_start) / 60}, indent=1))
    logger.info(f"Phase D done in {(time.time() - t_start) / 60:.1f} min")



def exploratory_full(args) -> None:
    """EXPLORATORY (decided after the pre-declared R-plus-prompt arms moved nothing): the full affine variant,
    editing the prompt suffix AND every generated position (d_X_gen + generated anchors), at alpha 2 and 4, with
    a random control at alpha 4; N=25 each, same first batch (common random numbers with the hooked alpha=0 arm)."""
    import torch

    from hf_engine import load_model
    from label import label_rows

    pf = ROOT / "predictions" / "predictions_v1.json"
    log = read_jsonl(ROOT / "predictions" / "commit_log.jsonl")
    assert log and sha256_file(pf) == log[-1]["sha256"], "predictions hash mismatch: refusing to run removal"
    summA = json.loads((ROOT / "results" / "phaseA_summary.json").read_text())
    prompts = [p for p in read_jsonl(ROOT / "prompts" / "prompts.jsonl") if p["kind"] == "geom"]
    model, tok = load_model(logger)
    t_start = time.time()
    for t in TASKS:
        X = summA[t]["modal"]
        D = np.load(ROOT / "cache" / f"directions_{t}.npz")
        A = np.load(ROOT / "cache" / f"anchors_{t}.npz")
        band = [int(x) for x in D["band"]]
        L_s = next(p["suffix_len"] for p in prompts if p["task"] == t)
        ed = Editor(model, band, D["d_hat"], D["d_gen"], A, L_s, "cuda")
        ed.gen_edit = True
        r1 = {l: torch.tensor(D["r1"][i], device="cuda", dtype=torch.float32) for i, l in enumerate(band)}
        base_ps = sorted([p for p in prompts if p["task"] == t and p["condition"] == "baseline"],
                         key=lambda p: p["paraphrase_id"])
        for name, a, od in (("full_dX_a2.0", 2.0, None), ("full_dX_a4.0", 4.0, None), ("full_r1_a4.0", 4.0, r1)):
            rows = gen_arm(model, tok, ed, base_ps, args.n_rand, args.batch, a, od, name, t)
            label_rows(rows, logger, workers=6)
            for r in rows:
                r["compliant"] = bool(r["passed"]) and r["label"] not in (X, "no_code")
                r["exploratory"] = True
            append_jsonl(ROOT / "data" / "samples_phaseD.jsonl", rows)
        ed.remove()
        torch.cuda.empty_cache()
    add_deviation("EXPLORATORY removal arms (post hoc, after the pre-declared R-plus-prompt arms): full affine variant "
                  "editing the prompt suffix and every generated position (d_X_gen, generated anchors) at alpha 2 and 4 "
                  "plus a random control at alpha 4, N=25 each, sharing the first common-random-number batch with the "
                  "hooked alpha=0 arm. Reported separately; not part of the pre-declared C2 verdict.")
    logger.info(f"exploratory full-variant arms done in {(time.time() - t_start) / 60:.1f} min")


if __name__ == "__main__":
    main()
