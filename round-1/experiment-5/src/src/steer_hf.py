"""Steering arms (STEP 6) on Qwen3-8B with HF, band-incremental subtraction of the sharpening direction.

  .venv/bin/python src/steer_hf.py --stage S                      # hook unit tests, S0 (c=0), S2, S1, S3
  .venv/bin/python src/steer_hf.py --stage R --cstar t1=1.0,t2=0.5 # R1, R2 random directions at c*, + manipulation
Rows -> runs/raw_steer__<arm>.jsonl ; tests -> results/hook_tests.json ; manipulation -> results/manipulation_*.json

Decoding: pure ancestral sampling at T=1.0 over the full vocabulary (no top-k / top-p, so HF generation_config
defaults (T=0.6, top_p=0.95, top_k=20) can never leak in), implemented as Gumbel-max with one CUDA generator per
(task, paraphrase, sample) so the noise at step t is identical across arms: samples are coupled (common random
numbers) regardless of batch composition. Each batch = one paraphrase x 10 samples x 2 arms (no padding).
Hook on model.model.layers[L], L = 8..28: prefill -> subtract at R (last prompt position) only; decode -> subtract
at every generated position. Cumulative subtraction after layer L = c * delta_L (increments v_L).
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ACTS, EOS_IDS, MI, RESULTS, RUNS, append_jsonl, read_jsonl, setup_logging, stable_seed, time_log  # noqa: E402
from extract import FENCE_RE  # noqa: E402
from prompts import load_prompts  # noqa: E402

BAND = list(range(8, 29))
MAX_NEW = 1024
CHECK_EVERY = 16
NOCODE_CUTOFF = 512  # uniform rule for every HF arm: stop a row at 512 tokens if neither ``` nor 'def solve' appeared
ARM_SUFFIX = ""      # "+nocutoff" for the cutoff-validation arm


class Steerer:
    """Forward hooks that subtract a per-row vector at each band layer."""

    def __init__(self, model):
        self.model = model
        self.cur: dict[int, "torch.Tensor | None"] = {L: None for L in BAND}
        self.cur_dec: dict[int, "torch.Tensor | None"] = {L: None for L in BAND}
        self.fired: dict[int, int] = {L: 0 for L in BAND}
        self.handles = [model.model.layers[L].register_forward_hook(self._mk(L)) for L in BAND]

    def _mk(self, L: int):
        def hook(mod, inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            vec = self.cur[L] if hs.shape[1] > 1 else self.cur_dec[L]
            if vec is None:
                return None
            self.fired[L] += hs.shape[0]
            if hs.shape[1] > 1:
                hs = hs.clone()
                hs[:, -1, :] = hs[:, -1, :] - vec[:, 0, :]
            else:
                hs = hs - vec
            if isinstance(out, tuple):
                return (hs,) + tuple(out[1:])
            return hs
        return hook

    def set_rows(self, per_row: list, device, dtype, per_row_decode: list | None = None) -> None:
        """per_row: list (len B) of [21, D] arrays (already scaled) or None (= zeros), applied at R in prefill.
        per_row_decode: same for decode steps (defaults to per_row)."""
        import torch
        D = self.model.config.hidden_size
        B = len(per_row)
        for target, rows in ((self.cur, per_row), (self.cur_dec, per_row if per_row_decode is None else per_row_decode)):
            if all(v is None for v in rows):
                for L in BAND:
                    target[L] = None
                continue
            mats = np.zeros((len(BAND), B, D), dtype=np.float32)
            for b, v in enumerate(rows):
                if v is not None:
                    mats[:, b, :] = v
            t = torch.tensor(mats, device=device, dtype=dtype)
            for i, L in enumerate(BAND):
                target[L] = t[i][:, None, :]

    def clear(self) -> None:
        for L in BAND:
            self.cur[L] = None
            self.cur_dec[L] = None

    def remove(self) -> None:
        for h in self.handles:
            h.remove()


def has_closed_solve_block(text: str) -> bool:
    return any("def solve" in m.group(2) for m in FENCE_RE.finditer(text))


def repeated(text: str, n: int = 6, k: int = 5) -> bool:
    w = text.split()
    if len(w) < n * k:
        return False
    cnt: dict = {}
    for i in range(len(w) - n + 1):
        g = tuple(w[i:i + n])
        cnt[g] = cnt.get(g, 0) + 1
        if cnt[g] >= k:
            return True
    return False


def generate_batch(model, tok, steerer: Steerer, prompt_ids: list[int], row_vecs: list, row_seeds: list[int],
                   greedy: bool = False, max_new: int = MAX_NEW, row_vecs_decode: list | None = None) -> list[dict]:
    import torch
    from transformers import DynamicCache
    B = len(row_vecs)
    dev = model.device
    if isinstance(steerer, Steerer):
        steerer.set_rows(row_vecs, dev, model.dtype, row_vecs_decode)
    else:
        steerer.set_rows(row_vecs, dev, model.dtype)
    gens = []
    for s in row_seeds:
        g = torch.Generator(device=dev)
        g.manual_seed(int(s))
        gens.append(g)
    ids = torch.tensor([prompt_ids] * B, device=dev)
    cache = DynamicCache()
    out_tokens = [[] for _ in range(B)]
    finish = [None] * B
    eos = torch.tensor(EOS_IDS, device=dev)
    with torch.inference_mode():
        logits = model(input_ids=ids, past_key_values=cache, use_cache=True, logits_to_keep=1).logits[:, -1, :].float()
        V = logits.shape[-1]
        for step in range(max_new):
            if greedy:
                nxt = logits.argmax(-1)
            else:
                noise = torch.stack([torch.rand(V, generator=g, device=dev) for g in gens])
                gumbel = -torch.log(-torch.log(noise.clamp_(1e-20, 1.0 - 1e-7)))
                nxt = (logits + gumbel).argmax(-1)
            nl = nxt.tolist()
            is_eos = torch.isin(nxt, eos).tolist()
            for b in range(B):
                if finish[b] is None:
                    if is_eos[b]:
                        finish[b] = "stop"
                    else:
                        out_tokens[b].append(nl[b])
            if (step + 1) % CHECK_EVERY == 0:
                for b in range(B):
                    if finish[b] is None:
                        txt = tok.decode(out_tokens[b], skip_special_tokens=False)
                        if has_closed_solve_block(txt):
                            finish[b] = "fence"
                        elif repeated(txt):
                            finish[b] = "repetition"
                        elif step + 1 >= NOCODE_CUTOFF and not ARM_SUFFIX and "```" not in txt and "def solve" not in txt:
                            finish[b] = "nocode_cutoff"
            if all(f is not None for f in finish) or step == max_new - 1:
                break
            logits = model(input_ids=nxt[:, None], past_key_values=cache, use_cache=True).logits[:, -1, :].float()
    steerer.clear()
    res = []
    for b in range(B):
        res.append({"text": tok.decode(out_tokens[b], skip_special_tokens=False), "n_tokens": len(out_tokens[b]),
                    "finish_reason": finish[b] or "length", "tokens": out_tokens[b]})
    del cache
    return res


def scaled(v: np.ndarray, c: float) -> np.ndarray:
    return (v * c).astype(np.float32)


def random_increments(delta: np.ndarray, c: float, seed: int) -> np.ndarray:
    """Unit isotropic direction r; cumulative shift after band layer L = ||c delta_L|| r (norm-matched)."""
    D = delta.shape[1]
    r = np.random.default_rng(seed).standard_normal(D)
    r /= np.linalg.norm(r)
    norms = np.array([np.linalg.norm(c * delta[L + 1]) for L in BAND])
    inc = np.diff(np.concatenate([[0.0], norms]))
    return (inc[:, None] * r[None, :]).astype(np.float32)


def arm_vectors(task: str, kind: str, c: float, seed: int | None = None) -> np.ndarray | None:
    if kind == "none" or c == 0:
        return None
    if kind in ("sharpen", "sharpenR"):
        return scaled(np.load(ACTS / f"steer_{task}.npy"), c)
    if kind in ("random", "randomR"):
        return random_increments(np.load(ACTS / f"delta_{task}.npy"), c, seed)
    if kind == "single18":  # ADL-style: subtract c * delta_18 at decoder layer 18 only
        delta = np.load(ACTS / f"delta_{task}.npy")
        v = np.zeros((len(BAND), delta.shape[1]), dtype=np.float32)
        v[BAND.index(18)] = c * delta[19]
        return v
    raise ValueError(kind)


def decode_vectors(kind: str, vec: np.ndarray | None) -> np.ndarray | None:
    """sharpenR = read-state-only control: subtract at R in prefill, nothing at generated positions."""
    return None if kind in ("sharpenR", "randomR") else vec


def arm_name(kind: str, c: float, seed: int | None) -> str:
    return _arm_name(kind, c, seed) + ARM_SUFFIX


def _arm_name(kind: str, c: float, seed: int | None) -> str:
    if kind == "none":
        return "steer:none:c=0"
    if kind == "sharpen":
        return f"steer:sharpen:c={c}"
    if kind == "sharpenR":
        return f"steer:sharpen_Ronly:c={c}"
    if kind == "single18":
        return f"steer:single18:c={c}"
    if kind == "randomR":
        return f"steer:random{seed}_Ronly:c={c}"
    return f"steer:random{seed}"


def run_arms(model, tok, steerer, prompts, task: str, arms: list[tuple[str, float, int | None]], pids: list[int],
             n_per: int, stage: str) -> None:
    """arms run two at a time in one batch (rows: arm A x n_per, arm B x n_per) for each paraphrase."""
    for i in range(0, len(arms), 2):
        pair = arms[i:i + 2]
        for pi in pids:
            p = prompts["chat"][task]["baseline"][pi]
            todo = []
            for kind, c, seed in pair:
                name = arm_name(kind, c, seed)
                done = {(r["paraphrase_id"], r["sample_id"]) for r in read_jsonl(RUNS / f"raw_steer__{name.replace(':', '_')}.jsonl")
                        if r["task"] == task}
                for j in range(n_per):
                    if (pi, j) not in done:
                        todo.append((kind, c, seed, name, j))
            if not todo:
                continue
            vecs = {}
            rows_v, rows_d, rows_s = [], [], []
            for kind, c, seed, name, j in todo:
                if name not in vecs:
                    vecs[name] = arm_vectors(task, kind, c, seed)
                rows_v.append(vecs[name])
                rows_d.append(decode_vectors(kind, vecs[name]))
                rows_s.append(stable_seed("steer", task, p["id"], j))
            t0 = time.time()
            outs = generate_batch(model, tok, steerer, p["token_ids"], rows_v, rows_s, row_vecs_decode=rows_d)
            dt = time.time() - t0
            by_arm: dict[str, list] = {}
            for (kind, c, seed, name, j), o in zip(todo, outs):
                by_arm.setdefault(name, []).append({
                    "task": task, "arm": name, "template": "chat", "condition": "baseline", "model": MI,
                    "prompt_id": p["id"], "paraphrase_id": pi, "sample_id": j, "seed": stable_seed("steer", task, p["id"], j), "stage": stage, "engine": "hf-custom-sampler",
                    "text": o["text"], "finish_reason": o["finish_reason"], "stop_reason": None, "n_tokens": o["n_tokens"],
                    "steer": {"kind": kind, "c": c, "layers": [BAND[0], BAND[-1]], "seed": seed}})
            for name, rows in by_arm.items():
                append_jsonl(RUNS / f"raw_steer__{name.replace(':', '_')}.jsonl", rows)
            ntok = sum(o["n_tokens"] for o in outs)
            logger.info(f"[{stage}] {task} P{pi} arms={[a[3] for a in todo[:1]] + [todo[-1][3]]} rows={len(todo)} "
                        f"{dt:.0f}s maxlen={max(o['n_tokens'] for o in outs)} tok/s={ntok / dt:.0f} "
                        f"finish={ {f: sum(o['finish_reason'] == f for o in outs) for f in ('stop', 'fence', 'repetition', 'nocode_cutoff', 'length')} }")


def hook_tests(model, tok, steerer, prompts) -> dict:
    import torch
    res = {}
    task = "t1"
    v = np.load(ACTS / f"steer_{task}.npy")
    delta = np.load(ACTS / f"delta_{task}.npy")
    # (a) c=0 greedy identical to unhooked, 3 prompts, 48 tokens
    same = []
    for pi in range(3):
        ids = prompts["chat"][task]["baseline"][pi]["token_ids"]
        steerer.remove()
        a = generate_batch(model, tok, _NullSteerer(), ids, [None], [1], greedy=True, max_new=48)
        steerer.__init__(model)
        b = generate_batch(model, tok, steerer, ids, [np.zeros_like(v)], [1], greedy=True, max_new=48)
        same.append(a[0]["tokens"] == b[0]["tokens"])
    res["a_c0_greedy_identical"] = all(same)
    # (b) single prefill at c=1: positions < R unchanged at layer 28; h_R at layer 8 shifted by -delta_8
    ids = prompts["chat"][task]["baseline"][0]["token_ids"]
    rec = {}

    def mk(idx):
        def h(mod, inp, out):
            rec[idx] = (out[0] if isinstance(out, tuple) else out).detach().float().clone()
        return h
    with torch.inference_mode():
        hs = [model.model.layers[L].register_forward_hook(mk(L)) for L in (8, 28)]
        steerer.clear()
        model(input_ids=torch.tensor([ids], device=model.device), use_cache=False, logits_to_keep=1)
        base8, base28 = rec[8].clone(), rec[28].clone()
        steerer.set_rows([v.astype(np.float32)], model.device, model.dtype)
        model(input_ids=torch.tensor([ids], device=model.device), use_cache=False, logits_to_keep=1)
        st8, st28 = rec[8].clone(), rec[28].clone()
        steerer.clear()
        for h in hs:
            h.remove()
    d8 = (st8[0, -1] - base8[0, -1]).cpu().numpy()
    exp8 = -delta[9]
    res["b_prefix_unchanged_L28"] = bool(torch.allclose(st28[0, :-1], base28[0, :-1], atol=1e-3))
    res["b_R_shift_L8_max_abs_err"] = float(np.abs(d8 - exp8).max())
    res["b_R_shift_L8_rel_err"] = float(np.linalg.norm(d8 - exp8) / np.linalg.norm(exp8))
    res["b_ok"] = res["b_prefix_unchanged_L28"] and res["b_R_shift_L8_rel_err"] < 0.02
    d28 = (st28[0, -1] - base28[0, -1]).cpu().numpy()
    res["d_cum_change_L28_cos_with_minus_delta28"] = float(np.dot(d28, -delta[29]) / (np.linalg.norm(d28) * np.linalg.norm(delta[29])))
    res["d_cum_change_L28_norm_ratio"] = float(np.linalg.norm(d28) / np.linalg.norm(delta[29]))
    # (c) decode fires on every row
    steerer.fired = {L: 0 for L in BAND}
    generate_batch(model, tok, steerer, ids, [v, v, v], [1, 2, 3], greedy=False, max_new=4)
    # prefill (3 rows) + 3 decode forwards (3 rows each), unless a row hit EOS early: equal counts at every layer
    res["c_decode_fires_all_rows"] = len(set(steerer.fired.values())) == 1 and steerer.fired[8] == 3 * 4
    res["c_fired_counts_sample"] = steerer.fired[8]
    # (e) sampler is pure: T=1, full vocabulary, no generation_config merge (custom loop never calls generate)
    gc_ = model.generation_config
    res["e_hf_generation_config_defaults"] = {"temperature": gc_.temperature, "top_p": gc_.top_p, "top_k": gc_.top_k}
    res["e_sampler"] = "gumbel-max over full-vocab float32 logits at T=1.0 (generate() never called)"
    # (f) determinism: same seeds, c=0, twice -> identical samples
    r1 = generate_batch(model, tok, steerer, ids, [None] * 4, [11, 12, 13, 14], max_new=64)
    r2 = generate_batch(model, tok, steerer, ids, [None] * 4, [11, 12, 13, 14], max_new=64)
    res["f_determinism_identical"] = all(a["tokens"] == b["tokens"] for a, b in zip(r1, r2))
    # (f2) coupling across batch composition: row seed 11 alone vs within a batch of 4
    r3 = generate_batch(model, tok, steerer, ids, [None], [11], max_new=64)
    res["f2_coupling_batch_invariant_prefix_tokens"] = int(_common_prefix(r1[0]["tokens"], r3[0]["tokens"]))
    return res


def _common_prefix(a: list, b: list) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


class _NullSteerer:
    def set_rows(self, *a, **k):
        pass

    def clear(self):
        pass


def manipulation(model, steerer, prompts, task: str, arms: list[tuple[str, float, int | None]]) -> dict:
    """gap_closed = 1 - ||mean h_steered - mean h_B|| / ||mean h_I - mean h_B|| at layers 8, 18, 28 (outputs, at R)."""
    import torch
    hB = np.load(ACTS / f"base_{task}_R.npy").astype(np.float32)
    hI = np.load(ACTS / f"instruct_{task}_R.npy").astype(np.float32)
    rec = {}

    def mk(L):
        def h(mod, inp, out):
            rec[L] = (out[0] if isinstance(out, tuple) else out)[0, -1].detach().float().cpu().numpy()
        return h
    hs = [model.model.layers[L].register_forward_hook(mk(L)) for L in (8, 18, 28)]  # after steering hooks
    out = {}
    try:
        for kind, c, seed in arms:
            vec = arm_vectors(task, kind, c, seed)
            acc = {L: [] for L in (8, 18, 28)}
            with torch.inference_mode():
                for p in prompts["chat"][task]["baseline"]:
                    steerer.set_rows([vec], model.device, model.dtype)
                    model(input_ids=torch.tensor([p["token_ids"]], device=model.device), use_cache=False, logits_to_keep=1)
                    for L in acc:
                        acc[L].append(rec[L])
            steerer.clear()
            g = {}
            for L in (8, 18, 28):
                ms = np.mean(acc[L], 0)
                mb, mi = hB[:, L + 1].mean(0), hI[:, L + 1].mean(0)
                g[f"L{L}"] = float(1 - np.linalg.norm(ms - mb) / np.linalg.norm(mi - mb))
            out[arm_name(kind, c, seed)] = g
            logger.info(f"manipulation {task} {arm_name(kind, c, seed)}: {g}")
    finally:
        for h in hs:
            h.remove()
    return out


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["S", "R", "X"])
    ap.add_argument("--cstar", default="")
    ap.add_argument("--n_per", type=int, default=10)
    ap.add_argument("--s3_n", type=int, default=100)
    ap.add_argument("--extra", default="", help="X stage: kind:c:seed:npara;... (run two at a time)")
    ap.add_argument("--skip_tests", action="store_true")
    ap.add_argument("--nocutoff", action="store_true", help="validation arm: no 512-token no-code stop (suffix +nocutoff)")
    ap.add_argument("--n_paraphrases", type=int, default=10)
    args = ap.parse_args()
    setup_logging(f"steer_{args.stage}")
    global ARM_SUFFIX
    if args.nocutoff:
        ARM_SUFFIX = "+nocutoff"
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.cuda.set_per_process_memory_fraction(0.97)
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MI)
    model = AutoModelForCausalLM.from_pretrained(MI, dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    model.eval()
    logger.info(f"loaded {MI} in {time.time() - t0:.0f}s")
    prompts = load_prompts()
    steerer = Steerer(model)
    time_log(f"steer_{args.stage}_start")
    pids = list(range(args.n_paraphrases))
    if args.stage == "S":
        if args.skip_tests and (RESULTS / "hook_tests.json").exists():
            tests = json.loads((RESULTS / "hook_tests.json").read_text())
            logger.info("hook tests already passed in an earlier launch of this stage; skipping")
        else:
            tests = hook_tests(model, tok, steerer, prompts)
            (RESULTS / "hook_tests.json").write_text(json.dumps(tests, indent=1))
            logger.info(f"hook tests: {tests}")
        if not (tests["a_c0_greedy_identical"] and tests["b_ok"] and tests["c_decode_fires_all_rows"]
                and tests["f_determinism_identical"]):
            logger.error("HOOK UNIT TESTS FAILED")
            raise SystemExit(2)
        # staged: S2 (c=1.0) and S0 at 10 samples per task first (one paraphrase), then everything
        for task in ("t1", "t2"):
            run_arms(model, tok, steerer, prompts, task, [("none", 0.0, None), ("sharpen", 1.0, None)], [0], args.n_per, "10")
        for task in ("t1", "t2"):
            run_arms(model, tok, steerer, prompts, task, [("sharpen", 0.5, None), ("sharpen", 1.5, None)], [0], args.n_per, "10")
        for task in ("t1", "t2"):
            run_arms(model, tok, steerer, prompts, task, [("none", 0.0, None), ("sharpen", 1.0, None)], pids, args.n_per, "full")
            run_arms(model, tok, steerer, prompts, task, [("sharpen", 0.5, None), ("sharpen", 1.5, None)],
                     pids[: max(1, math.ceil(args.s3_n / args.n_per))], args.n_per, "full")
            # S1 also needs the paraphrases S3 may skip
            run_arms(model, tok, steerer, prompts, task, [("sharpen", 0.5, None)], pids, args.n_per, "full")
        man = {t: manipulation(model, steerer, prompts, t, [("sharpen", c, None) for c in (0.5, 1.0, 1.5)]) for t in ("t1", "t2")}
        (RESULTS / "manipulation_S.json").write_text(json.dumps(man, indent=1))
    elif args.stage == "R":
        cstar = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in args.cstar.split(",") if kv}
        for task in ("t1", "t2"):
            c = cstar[task]
            run_arms(model, tok, steerer, prompts, task, [("random", c, 1), ("random", c, 2)], pids, args.n_per, "full")
        man = {t: manipulation(model, steerer, prompts, t, [("random", cstar[t], 1), ("random", cstar[t], 2)])
               for t in ("t1", "t2")}
        (RESULTS / "manipulation_R.json").write_text(json.dumps({"cstar": cstar, "gap_closed": man}, indent=1))
    else:
        arms = []
        for a in args.extra.split(";"):
            kind, c, seed, npara = a.split(":")
            arms.append((kind, float(c), int(seed) if seed != "None" else None, int(npara)))
        for i in range(0, len(arms), 2):
            pair = arms[i:i + 2]
            npara = max(a[3] for a in pair)
            for task in ("t1", "t2"):
                if len(pair) == 2 and pair[0][3] != pair[1][3]:
                    for a in pair:
                        run_arms(model, tok, steerer, prompts, task, [a[:3]], list(range(a[3])), args.n_per, "extra")
                else:
                    run_arms(model, tok, steerer, prompts, task, [a[:3] for a in pair], list(range(npara)), args.n_per, "extra")
        man = {t: manipulation(model, steerer, prompts, t, [a[:3] for a in arms]) for t in ("t1", "t2")}
        prev = json.loads((RESULTS / "manipulation_X.json").read_text()) if (RESULTS / "manipulation_X.json").exists() else {}
        for t in man:
            prev.setdefault(t, {}).update(man[t])
        (RESULTS / "manipulation_X.json").write_text(json.dumps(prev, indent=1))
    steerer.remove()
    del model
    gc.collect()
    time_log(f"steer_{args.stage}_end", seconds=round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
