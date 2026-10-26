#!/usr/bin/env python3
"""GPU stages (HF engine5, bf16, batch-1 prompt prefills with block-output hooks, the exp8/exp17 CRN sampler).

  instr1  instruct model: GPU unit tests (CRN determinism, T(0) == twin, memory probe), engine check, twin on slots
          j 0-19 (S1 = 0-9 for selection; 10-19 = TWIN_S2, sampled in the same B = 20 batches, never used for
          selection), clean states of the 75 twin prompts at ALL 36 blocks for p in S U {R} (cache/states), forced
          'Implement X' prompt states for the geometry (cache/geometry).
  base1   base model: the same state captures; waits for COMMIT #1, then the reverse interchange (Stage 6:
          BTWIN, RT(1), BMR(1) on the base model's own CRN slots).
  instr2  instruct model: hook-placement test, Stage 3 selection (S1), COMMIT #2 (src/commits5.py, after the labels of
          every Stage-3 row exist), Stage 4 confirmation (fresh S2 slots), Stage 5 de-sharpening push (Claim D).
Every batch holds exactly B rows of ONE (task, template) prompt (pad rows complete a batch and are discarded), so the
batch shape is identical in every arm and the CRN coupling is exact (T(0) == TWIN slot by slot, unit test U2).
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine5 as E  # noqa: E402
from cfg import (ALL_BLOCKS, BASE_ID, BASE_KEY, BASE_REVISION, CACHE_DIR, D_MODEL, DATA_DIR, E17, E23,  # noqa: E402
                 EARLY_BLOCKS, ENDOFTEXT, GEO_BLOCKS_R, GEO_BLOCKS_S, IM_START, LATE_BLOCKS, MAX_NEW_BASE_PATH,
                 MAX_NEW_PATH, MAX_NEW_TOKENS, MODEL_ID, MODEL_REVISION, N_LAYERS, NORM_BLOCKS, PATH_TASKS, PRED_DIR,
                 RESULTS_DIR, STATES_DIR, TASKS15, TEMPLATE_IDS, V_BLOCKS, append_deviation, append_jsonl, read_json,
                 read_jsonl, set_ram_limit, setup_logging, stable_seed, utc_now, write_json)
from hooks5 import edits_along, edits_setto, unit_rows  # noqa: E402
from prompts5 import load_prompts  # noqa: E402

INSTR_RAW = DATA_DIR / "instr_raw.jsonl"
BASEHOOK_RAW = DATA_DIR / "basehook_raw.jsonl"
EC_RAW = DATA_DIR / "engine_check_raw.jsonl"
REALISED = DATA_DIR / "realised.jsonl"
TIMING = RESULTS_DIR / "timing_batches.jsonl"
GEO_DIR = CACHE_DIR / "geometry"
GEO_DIR.mkdir(parents=True, exist_ok=True)
DBAR = CACHE_DIR / "dbar.npy"
B_DEFAULT = 20


# ------------------------------------------------------------------------------------------------ io helpers
def to_u16(t: torch.Tensor) -> np.ndarray:
    return t.detach().contiguous().cpu().view(torch.int16).numpy().view(np.uint16)


def from_u16(a: np.ndarray, device: Any) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(a).view(np.int16)).to(device).view(torch.bfloat16)


def state_path(tag: str, task: str, w: str) -> Path:
    return STATES_DIR / f"{tag}_{task}_{w}.npy"


def load_states(tag: str, task: str, w: str, device: Any) -> torch.Tensor:
    return from_u16(np.load(state_path(tag, task, w)), device)


def r_q() -> dict[int, float]:
    q = read_json(E23 / "qwen_ratio.json")["r_Q"]
    return {int(k): float(v["median"]) for k, v in q.items()}


# ------------------------------------------------------------------------------------------------ arm registry
ARM_RE = re.compile(r"^(TWIN|BTWIN|T|READ|EARLY|LATE|MR|READMR|XT|DS|ISO|RT|BMR|TS|TSMR|MRP|PAD|EC_NEUTRAL|"
                    r"EC_RAND9002_a|EC_RAND9004_a)([0-9.]*)$")


def arm_spec(name: str) -> dict[str, Any]:
    m = ARM_RE.match(name)
    assert m, f"unknown arm {name}"
    pre, num = m.group(1), m.group(2)
    x = float(num) if num else None
    if pre in ("TWIN", "BTWIN", "PAD", "EC_NEUTRAL"):
        return {"kind": "TWIN", "site": None, "blocks": [], "lam": None, "alpha": None, "per_sample": False}
    if pre in ("EC_RAND9002_a", "EC_RAND9004_a"):
        return {"kind": "EC", "site": "S", "blocks": V_BLOCKS, "lam": None, "alpha": x, "per_sample": False,
                "seed": int(pre[7:11])}
    table = {"T": ("SET", "S", V_BLOCKS), "READ": ("SET", "R", V_BLOCKS), "EARLY": ("SET", "S", EARLY_BLOCKS),
             "LATE": ("SET", "S", LATE_BLOCKS), "MR": ("MR", "S", V_BLOCKS), "MRP": ("MR", "S", V_BLOCKS),
             "READMR": ("MR", "R", V_BLOCKS), "XT": ("XT", "S", V_BLOCKS), "DS": ("DS", "S", V_BLOCKS),
             "ISO": ("ISO", "S", V_BLOCKS), "RT": ("SET", "S", V_BLOCKS), "BMR": ("MR", "S", V_BLOCKS),
             "TS": ("TS", "S", V_BLOCKS), "TSMR": ("TSMR", "S", V_BLOCKS)}
    kind, site, blocks = table[pre]
    per = kind in ("MR", "ISO", "TSMR")
    if kind in ("DS", "ISO"):
        return {"kind": kind, "site": site, "blocks": blocks, "lam": None, "alpha": x, "per_sample": per}
    return {"kind": kind, "site": site, "blocks": blocks, "lam": x, "alpha": None, "per_sample": per}


def iso_unit(*key: Any) -> np.ndarray:
    x = np.random.Generator(np.random.PCG64(stable_seed(*key))).standard_normal(D_MODEL)
    return (x / np.linalg.norm(x)).astype(np.float32)


# ------------------------------------------------------------------------------------------------ context
class Ctx:
    """One loaded model ('instr' or 'base'): clean prefills and captured states of the current task's prompts."""

    def __init__(self, model: Any, tok: Any, tag: str, B: int):
        self.model, self.tok, self.tag, self.B = model, tok, tag, B
        self.dev = model.device
        self.prompts = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
        self.clean: dict[tuple[str, str], dict[str, Any]] = {}
        self.donor: dict[tuple[str, str], torch.Tensor] = {}
        self.geo: list[dict[str, Any]] = []
        self.rq = r_q()
        self.partner: dict[str, str] = {}
        self.dbar: np.ndarray | None = None

    def idx(self, task: str, w: str) -> tuple[list[int], int, int]:
        p = self.prompts[(task, w)]
        pos = list(range(p["p1"], p["spec_end"])) + [p["P"] - 1]
        return pos, p["spec_end"] - p["p1"], p["P"]

    def clean_prefill(self, task: str, w: str) -> dict[str, Any]:
        key = (task, w)
        if key not in self.clean:
            pos, nS, P = self.idx(task, w)
            pos_t = torch.tensor(pos, device=self.dev)
            H = torch.empty(N_LAYERS, len(pos), D_MODEL, dtype=torch.bfloat16, device=self.dev)

            def mk(l):
                def g(h):
                    H[l] = h[0, pos_t]
                return g
            pre = E.prefill(self.model, self.prompts[key]["ids"], capture={l: mk(l) for l in ALL_BLOCKS})
            self.clean[key] = {"pre": pre, "H": H, "nS": nS, "P": P}
        return self.clean[key]

    def drop_task(self) -> None:
        self.clean.clear()
        self.donor.clear()
        gc.collect()
        torch.cuda.empty_cache()

    def donor_states(self, task: str, w: str) -> torch.Tensor:
        key = (task, w)
        if key not in self.donor:
            other = "base" if self.tag == "instr" else "instr"
            self.donor[key] = load_states(other, task, w, self.dev)
        return self.donor[key]

    # -------------------------------------------------------------------------------------------- edits
    def make_edits(self, arm: str, task: str, w: str, j: int | None) -> tuple[dict, dict[str, Any]]:
        sp = arm_spec(arm)
        c = self.clean_prefill(task, w)
        H, nS = c["H"], c["nS"]
        pos, _, P = self.idx(task, w)
        if sp["kind"] == "TWIN":
            return {}, {"seed": None}
        if sp["site"] == "R":
            loc = [nS]
        else:
            loc = list(range(nS))
        abs_idx = torch.tensor([pos[i] for i in loc], device=self.dev)
        blocks = sp["blocks"]
        info: dict[str, Any] = {"seed": None}
        if sp["kind"] in ("SET", "MR", "XT", "TS", "TSMR"):
            zero = sp["kind"] == "SET" and sp["lam"] == 0.0   # T(0): identity, no donor needed
            Hd = None if zero else self.donor_states(task, w)
            targets = {}
            u = None
            if sp["kind"] in ("MR", "TSMR"):
                seed_key = ("iter5d2", "MR" if self.tag == "instr" else "BMR", task, w, j, sp["lam"])
                info["seed"] = stable_seed(*seed_key)
                u = torch.tensor(iso_unit(*seed_key), device=self.dev)
            if sp["kind"] == "XT":
                pt = self.partner[task]
                info["partner"] = pt
                ub = torch.tensor(self.dbar[TASKS15.index(pt)], device=self.dev)  # [36, D]
            for l in blocks:
                href = H[l, loc].float()
                if zero:
                    targets[l] = href
                    continue
                D = Hd[l, loc].float() - href
                if sp["kind"] in ("TS", "TSMR"):
                    D = D - torch.tensor(self.dbar_gen[l], device=self.dev)[None]
                if sp["kind"] == "SET" or sp["kind"] == "TS":
                    targets[l] = href + sp["lam"] * D
                elif sp["kind"] in ("MR", "TSMR"):
                    targets[l] = href + sp["lam"] * D.norm(dim=-1, keepdim=True) * u[None]
                else:  # XT
                    targets[l] = href + sp["lam"] * D.norm(dim=-1, keepdim=True) * unit_rows(ub[l][None])
            return edits_setto(blocks, abs_idx, targets), info
        if sp["kind"] in ("DS", "ISO"):
            Hd = self.donor_states(task, w)
            dirs, tgt, href = {}, {}, {}
            if sp["kind"] == "ISO":
                seed_key = ("iter5d2", "ISO", task, w, j, sp["alpha"])
                info["seed"] = stable_seed(*seed_key)
                u = torch.tensor(iso_unit(*seed_key), device=self.dev)
            for l in blocks:
                hr = H[l, loc].float()
                href[l] = hr
                n = hr.norm(dim=-1) * self.rq[l]
                tgt[l] = sp["alpha"] * n
                dirs[l] = unit_rows(Hd[l, loc].float() - hr) if sp["kind"] == "DS" else u
            return edits_along(blocks, abs_idx, dirs, tgt, href), info
        if sp["kind"] == "EC":
            seed = sp["seed"]
            info["seed"] = seed
            u = torch.tensor(np.load(E17 / "directions" / f"rand_{seed}.npy").astype(np.float32), device=self.dev)
            nm = np.load(E17 / "directions" / f"norms_{task}.npy").astype(np.float32)
            assert nm.shape[1] == nS, f"exp17 norm positions {nm.shape} != |S| {nS}"
            dirs = {l: u for l in V_BLOCKS}
            tgt = {l: sp["alpha"] * torch.tensor(nm[i], device=self.dev) for i, l in enumerate(V_BLOCKS)}
            href = {l: H[l, loc].float() for l in V_BLOCKS}
            return edits_along(V_BLOCKS, abs_idx, dirs, tgt, href), info
        raise ValueError(arm)

    def hooked_prefill(self, arm: str, task: str, w: str, j: int | None) -> tuple[dict[str, Any], dict[str, Any]]:
        """Edited prefill + realised displacement (blocks 12-35 at S, and at R) + geometry vectors."""
        edits, info = self.make_edits(arm, task, w, j)
        c = self.clean_prefill(task, w)
        pos, nS, P = self.idx(task, w)
        pos_t = torch.tensor(pos, device=self.dev)
        cap: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                cap[l] = h[0, pos_t].float()
            return g
        cb = sorted(set(NORM_BLOCKS) | set(GEO_BLOCKS_S))
        pre = E.prefill(self.model, self.prompts[(task, w)]["ids"], edits=edits, capture={l: mk(l) for l in cb})
        H = c["H"]
        disp_S = {l: float((cap[l][:nS] - H[l, :nS].float()).norm(dim=-1).mean()) for l in NORM_BLOCKS}
        disp_R = {l: float((cap[l][nS] - H[l, nS].float()).norm()) for l in NORM_BLOCKS}
        rel23 = float(((cap[23][:nS] - H[23, :nS].float()).norm(dim=-1) /
                       H[23, :nS].float().norm(dim=-1).clamp(min=1e-6)).mean())
        rec = {"S_b12": round(disp_S[12], 3), "S_b18": round(disp_S[18], 3), "S_b23": round(disp_S[23], 3),
               "S_b24": round(disp_S[24], 3), "S_b27": round(disp_S[27], 3), "S_b35": round(disp_S[35], 3),
               "R_b23": round(disp_R[23], 3), "R_b35": round(disp_R[35], 3), "rel_S_b23": round(rel23, 5)}
        geo = {f"S{l}": cap[l][:nS].mean(0).cpu().numpy().astype(np.float32) for l in GEO_BLOCKS_S}
        geo.update({f"R{l}": cap[l][nS].cpu().numpy().astype(np.float32) for l in GEO_BLOCKS_R})
        self.geo.append({"task": task, "arm": arm, "w": w, "j": j, "model": self.tag, **geo})
        info["realised"] = rec
        info["cap23"] = cap[23][:nS] if arm.startswith(("T", "RT")) and arm_spec(arm)["kind"] == "SET" else None
        del cap
        return pre, info

    # -------------------------------------------------------------------------------------------- batches
    def run_rows(self, task: str, w: str, rows: list[tuple[str, int]], block_id: str, raw: Path,
                 write: bool = True) -> list[dict[str, Any]]:
        """rows: [(arm, j)] of ONE (task, template), at most B; padded to exactly B rows."""
        assert 0 < len(rows) <= self.B
        t0 = time.time()
        base = self.tag == "base"
        if base:
            mx = MAX_NEW_BASE_PATH if task in PATH_TASKS else MAX_NEW_TOKENS
            fence, stops = "base", (IM_START,)
        else:
            mx = MAX_NEW_PATH if task in PATH_TASKS else MAX_NEW_TOKENS
            fence, stops = ("path" if task in PATH_TASKS else "bench"), ()
        groups, meta = [], []
        shared: dict[str, tuple[dict, dict]] = {}
        for arm, j in rows:
            sp = arm_spec(arm)
            ukey = (task, w, j, BASE_KEY) if base else (task, w, j)
            if sp["kind"] == "TWIN":
                pre = self.clean_prefill(task, w)["pre"]
                info = {"seed": None, "realised": None}
            elif sp["per_sample"]:
                pre, info = self.hooked_prefill(arm, task, w, j)
            else:
                if arm not in shared:
                    shared[arm] = self.hooked_prefill(arm, task, w, None)
                pre, info = shared[arm]
            groups.append({"pre": pre, "us": [E.u_stream(*ukey, n=mx)]})
            meta.append((arm, j, info))
        n_pad = self.B - len(rows)
        for i in range(n_pad):
            groups.append({"pre": self.clean_prefill(task, w)["pre"], "us": [E.u_stream(task, w, "pad", i, n=mx)]})
        res = E.sample(self.model, groups, max_new=mx, fence=fence, tok=self.tok, stop_ids=stops)
        nv = E.vocab_len(self.tok)
        p = self.prompts[(task, w)]
        out = []
        for (arm, j, info), r in zip(meta, res[:len(rows)]):
            sp = arm_spec(arm)
            text = self.tok.decode([t for t in r["token_ids"] if t < nv], skip_special_tokens=True)
            out.append({"task": task, "arm": arm, "knob_class": sp["kind"], "template": w, "slot": j,
                        "sample_id": f"{task}|{arm}|{w}|{j}",
                        "crn_key": f"{task}|{w}|{j}" + (f"|{BASE_KEY}" if base else ""),
                        "u_seed": stable_seed(*((task, w, j, BASE_KEY) if base else (task, w, j))),
                        "direction_seed": info.get("seed"), "alpha": sp["alpha"], "lambda": sp["lam"],
                        "site": (f"{sp['site']}:{min(sp['blocks'])}-{max(sp['blocks'])}" if sp["blocks"] else None),
                        "partner": info.get("partner"), "temperature": 1.0, "top_k": 0, "min_p": 0.0,
                        "thinking": False, "prompt_kind": "twin", "prompt_sha256": p["prompt_sha256"], "P": p["P"],
                        "model": BASE_ID if base else MODEL_ID,
                        "model_revision": BASE_REVISION if base else MODEL_REVISION,
                        "quant": "bf16", "engine": "hf_bf16_engine5", "precision": "bf16", "max_new": mx,
                        "stop_rule": f"im_end|endoftext{'|im_start' if base else ''}|fence:{fence}",
                        "block_id": block_id, "batch_B": self.B, "n_pad": n_pad, "text": text,
                        "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"],
                        "finish_reason": r["finish_reason"], "logprob_sum": r["logprob_sum"],
                        "realised_disp": info.get("realised"), "utc": utc_now()})
        if write:
            append_jsonl(raw, out)
        dt = time.time() - t0
        append_jsonl(TIMING, [{"block_id": block_id, "task": task, "w": w, "model": self.tag, "B": self.B,
                               "n_rows": len(rows), "n_pad": n_pad, "seconds": round(dt, 2),
                               "steps": res[0]["steps"], "max_len": max(r["n_tokens"] for r in res),
                               "arms": sorted({a for a, _ in rows}), "utc": utc_now()}])
        logger.info(f"{block_id} {task}/{w} {sorted({a for a, _ in rows})} rows {len(rows)}+{n_pad}pad: "
                    f"{dt:.1f}s, {res[0]['steps']} steps")
        return out

    def run_cells(self, task: str, cells: list[tuple[str, list[int]]], block_id: str, raw: Path,
                  templates: list[str] = TEMPLATE_IDS) -> int:
        """cells [(arm, slots)] for every template; rows already in `raw` are skipped (resumable)."""
        done = {r["sample_id"] for r in read_jsonl(raw)}
        n = 0
        for w in templates:
            rows = [(a, j) for a, js in cells for j in js if f"{task}|{a}|{w}|{j}" not in done]
            for i in range(0, len(rows), self.B):
                self.run_rows(task, w, rows[i:i + self.B], block_id, raw)
                n += len(rows[i:i + self.B])
        return n

    def save_geo(self, name: str) -> None:
        if not self.geo:
            return
        keys = [k for k in self.geo[0] if k[0] in "SR" and k[1:].isdigit()]
        meta = [{k: g[k] for k in ("task", "arm", "w", "j", "model")} for g in self.geo]
        arrs = {k: np.stack([g[k] for g in self.geo]).astype(np.float16) for k in keys}
        p = GEO_DIR / f"{name}.npz"
        if p.exists():  # append
            old = np.load(p, allow_pickle=False)
            om = json.loads(str(old["meta"]))
            arrs = {k: np.concatenate([old[k], arrs[k]]) for k in keys}
            meta = om + meta
        np.savez(p, meta=json.dumps(meta), **arrs)
        self.geo.clear()


# ------------------------------------------------------------------------------------------------ loading
def load(tag: str) -> tuple[Any, Any]:
    """(model, tok); engine_v4.load_model returns (tok, model)."""
    if tag == "base":
        tok, model = E.load_model(BASE_ID, BASE_REVISION, vram_fraction=0.97, fp8=False)
    else:
        tok, model = E.load_model(MODEL_ID, MODEL_REVISION, vram_fraction=0.97, fp8=False)
    return model, tok


def memory_probe(ctx: Ctx, task: str, w: str, max_new: int) -> dict[str, Any]:
    pre = ctx.clean_prefill(task, w)["pre"]
    out = {}
    for B in (20, 16, 12, 10, 8, 6):
        try:
            torch.cuda.reset_peak_memory_stats()
            kv = [(K.expand(B, -1, -1, -1), V.expand(B, -1, -1, -1)) for K, V in pre["kv"]]
            cache = E.prealloc_cache(kv, pre["P"] + max_new + 1)
            feed = torch.full((B, 1), 151645, device=ctx.dev)
            for s in range(3):
                pos = torch.full((B, 1), pre["P"] + s, device=ctx.dev, dtype=torch.long)
                h = ctx.model.model(input_ids=feed, past_key_values=cache, position_ids=pos,
                                    use_cache=True).last_hidden_state
                _ = ctx.model.lm_head(h[:, -1]).double().softmax(-1)
            peak = torch.cuda.max_memory_allocated() / 1e9
            del cache, kv, h
            torch.cuda.empty_cache()
            out = {"B": B, "peak_GB": round(peak, 2), "max_new": max_new, "P": pre["P"]}
            break
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            logger.warning(f"memory probe: B={B} OOM")
    return out


# ------------------------------------------------------------------------------------------------ stages
def stage_instr1(args: argparse.Namespace) -> None:
    model, tok = load("instr")
    probe = {}
    ctx = Ctx(model, tok, "instr", B_DEFAULT)
    probe["instr"] = memory_probe(ctx, "T1", "W1", 1024)
    probe["base_path_1536"] = memory_probe(ctx, "T1", "W1", 1536)
    write_json(RESULTS_DIR / "memory_probe.json", probe)
    ctx.B = probe["instr"]["B"]
    logger.info(f"memory probe: {probe}")
    ctx.drop_task()
    # U1 CRN determinism + U2 T(0) == TWIN (same batch shape), T03 and T2, slots 0-9 (written to a test file)
    tests: dict[str, Any] = {}
    tf = DATA_DIR / "unit_test_rows.jsonl"
    for task in ("T03", "T2"):
        r1 = ctx.run_rows(task, "W1", [("TWIN", j) for j in range(10)] + [("T0.0", j) for j in range(10)],
                          "U2", tf, write=True)
        r2 = ctx.run_rows(task, "W1", [("TWIN", j) for j in range(10)] + [("T0.0", j) for j in range(10)],
                          "U1", tf, write=False)
        tw = {r["slot"]: r["token_ids"] for r in r1 if r["arm"] == "TWIN"}
        t0 = {r["slot"]: r["token_ids"] for r in r1 if r["arm"] == "T0.0"}
        rep = {(r["arm"], r["slot"]): r["token_ids"] for r in r2}
        tests[task] = {"U1_determinism": sum(rep[(r["arm"], r["slot"])] == r["token_ids"] for r in r1),
                       "U2_T0_equals_twin": sum(tw[j] == t0[j] for j in range(10)), "n": 10}
        ctx.drop_task()
    tests["all_pass"] = all(v["U1_determinism"] == 20 and v["U2_T0_equals_twin"] == 10
                            for k, v in tests.items() if isinstance(v, dict))
    write_json(RESULTS_DIR / "unit_tests_gpu.json", {"instr1": tests, "utc": utc_now()})
    logger.info(f"GPU unit tests: {tests}")
    # engine check (Stage 0.4): exp17 screen rows, T03 rand_9002 and T2 rand_9004 at alpha 1 + twins, k 0-9
    for task, seed in (("T03", 9002), ("T2", 9004)):
        ctx.run_cells(task, [("EC_NEUTRAL", list(range(10))), (f"EC_RAND{seed}_a1.0", list(range(10)))],
                      "EC", EC_RAW)
        ctx.drop_task()
    # twin S1 + TWIN_S2 slots (0-19), all 15 tasks; clean states of the 75 twin prompts
    for task in TASKS15:
        ctx.run_cells(task, [("TWIN", list(range(20)))], "S1:TWIN", INSTR_RAW)
        for w in TEMPLATE_IDS:
            if not state_path("instr", task, w).exists():
                np.save(state_path("instr", task, w), to_u16(ctx.clean_prefill(task, w)["H"]))
        ctx.drop_task()
    (DATA_DIR / "instr_twin_done.flag").write_text(utc_now())
    forced_states(ctx, "instr")
    (DATA_DIR / "instr1_done.flag").write_text(utc_now())


def forced_states(ctx: Ctx, tag: str) -> None:
    out = GEO_DIR / f"forced_{tag}.npz"
    if out.exists():
        return
    rows = load_prompts(("named",))
    meta, arrs = [], {f"S{l}": [] for l in GEO_BLOCKS_S}
    arrs.update({f"R{l}": [] for l in GEO_BLOCKS_R})
    t0 = time.time()
    for r in rows:
        a, b, P = r["p1"], r["spec_end"], r["P"]
        got: dict[int, torch.Tensor] = {}

        def mk(l):
            def g(h):
                got[l] = h[0].float()
            return g
        blocks = sorted(set(GEO_BLOCKS_S) | set(GEO_BLOCKS_R))
        E.clear_act_cache()
        with torch.no_grad(), E.block_hooks(ctx.model, None, {l: mk(l) for l in blocks}):
            ctx.model.model(input_ids=torch.tensor([r["ids"]], device=ctx.dev), use_cache=False)
        for l in GEO_BLOCKS_S:
            arrs[f"S{l}"].append(got[l][a:b].mean(0).cpu().numpy())
        for l in GEO_BLOCKS_R:
            arrs[f"R{l}"].append(got[l][P - 1].cpu().numpy())
        meta.append({"task": r["task"], "X": r["X"], "pid": r["pid"]})
        del got
    np.savez(out, meta=json.dumps(meta), **{k: np.stack(v).astype(np.float16) for k, v in arrs.items()})
    logger.info(f"forced states ({tag}): {len(rows)} prompts in {time.time() - t0:.0f}s")


def compute_dbar() -> None:
    """Per task and block: mean over its 5 templates and S positions of D = h_base - h_instr (fp32 [15, 36, D]);
    plus the generic cross-task mean."""
    if DBAR.exists():
        return
    out = np.zeros((len(TASKS15), N_LAYERS, D_MODEL), np.float32)
    pr = {(r["task"], r["w"]): r for r in load_prompts(("twin",))}
    for i, t in enumerate(TASKS15):
        acc = np.zeros((N_LAYERS, D_MODEL), np.float64)
        n = 0
        for w in TEMPLATE_IDS:
            nS = pr[(t, w)]["spec_end"] - pr[(t, w)]["p1"]
            hb = torch.from_numpy(np.load(state_path("base", t, w)).view(np.int16)).view(torch.bfloat16).float()
            hi = torch.from_numpy(np.load(state_path("instr", t, w)).view(np.int16)).view(torch.bfloat16).float()
            acc += (hb[:, :nS] - hi[:, :nS]).sum(1).double().numpy()
            n += nS
            del hb, hi
        out[i] = (acc / n).astype(np.float32)
    np.save(DBAR, out)


def stage_base1(args: argparse.Namespace) -> None:
    model, tok = load("base")
    ctx = Ctx(model, tok, "base", B_DEFAULT)
    probe = read_json(RESULTS_DIR / "memory_probe.json") if (RESULTS_DIR / "memory_probe.json").exists() else {}
    ctx.B = probe.get("base_path_1536", {}).get("B", 10) if probe else 10
    for task in TASKS15:
        for w in TEMPLATE_IDS:
            if not state_path("base", task, w).exists():
                np.save(state_path("base", task, w), to_u16(ctx.clean_prefill(task, w)["H"]))
        ctx.drop_task()
    (DATA_DIR / "base_states_done.flag").write_text(utc_now())
    forced_states(ctx, "base")
    compute_dbar()
    # Stage 6 waits for COMMIT #1
    c1 = PRED_DIR / "commit1.json"
    t0 = time.time()
    while not c1.exists():
        if time.time() - t0 > args.wait_min * 60:
            append_deviation("D-base1-wait", "COMMIT #1 not written in time; Stage 6 skipped in base1")
            return
        logger.info("base1: waiting for COMMIT #1 ...")
        time.sleep(30)
    com = read_json(c1)
    tasks6 = com["stage_sets"]["stage6_reverse"]
    arms = ["BTWIN", "RT1.0"] + ([] if "BMR" in com.get("dropped_arms", []) else ["BMR1.0"])
    for task in tasks6:
        ctx.run_cells(task, [(a, list(range(10))) for a in arms], "S6", BASEHOOK_RAW)
        ctx.save_geo("hooked_base")
        ctx.drop_task()
    (DATA_DIR / "base1_done.flag").write_text(utc_now())


def wait_labels(sample_ids: set[str], max_min: float) -> bool:
    t0 = time.time()
    while True:
        have = {r["sample_id"] for r in read_jsonl(DATA_DIR / "labels.jsonl")}
        miss = sample_ids - have
        if not miss:
            return True
        if time.time() - t0 > max_min * 60:
            logger.warning(f"labels missing for {len(miss)} rows after {max_min} min")
            return False
        logger.info(f"waiting for labels: {len(miss)} missing")
        time.sleep(15)


def stage_instr2(args: argparse.Namespace) -> None:
    import commits5

    com1 = read_json(PRED_DIR / "commit1.json")
    model, tok = load("instr")
    probe = read_json(RESULTS_DIR / "memory_probe.json")
    ctx = Ctx(model, tok, "instr", probe["instr"]["B"])
    ctx.partner = com1["partner"]
    ctx.dbar = np.load(DBAR)
    ctx.dbar_gen = ctx.dbar.mean(0)  # type: ignore[attr-defined]
    # U3 hook placement: SET(1) at block 23 carries the base state; blocks 24+ are recomputed
    t = "T03"
    pre, info = ctx.hooked_prefill("T1.0", t, "W1", None)
    hb = ctx.donor_states(t, "W1")
    nS = ctx.clean_prefill(t, "W1")["nS"]
    rel = float(((info["cap23"] - hb[23, :nS].float()).abs().max() /
                 hb[23, :nS].float().abs().max()).item())
    rel_mean = float(((info["cap23"] - hb[23, :nS].float()).norm(dim=-1) /
                      hb[23, :nS].float().norm(dim=-1)).max().item())
    d24 = float(info["realised"]["S_b24"])
    u = read_json(RESULTS_DIR / "unit_tests_gpu.json")
    u["U3_hook_placement"] = {"max_abs_rel_diff_b23": rel, "max_row_rel_diff_b23": rel_mean,
                              "pass": rel_mean < 2e-2, "S_b24_displacement_vs_clean": d24}
    write_json(RESULTS_DIR / "unit_tests_gpu.json", u)
    ctx.geo.clear()
    ctx.drop_task()
    logger.info(f"U3: {u['U3_hook_placement']}")
    # ---------------------------------------------------------------- Stage 3 (selection on S1)
    plan3 = com1["stage3_plan"]
    for task, cells in plan3.items():
        ctx.run_cells(task, [(a, js) for a, js in cells], "S3", INSTR_RAW)
        ctx.save_geo("hooked_instr")
        ctx.drop_task()
    (DATA_DIR / "stage3_done.flag").write_text(utc_now())
    ids3 = {f"{t}|{a}|{w}|{j}" for t, cells in plan3.items() for a, js in cells for j in js for w in TEMPLATE_IDS}
    # Stage 5 (Claim D) does not use lambda*: run it while the Stage-3 labels finish (F8)
    plan5 = com1["stage5_plan"]
    for task, cells in plan5.items():
        ctx.run_cells(task, [(a, js) for a, js in cells], "S5", INSTR_RAW)
        ctx.save_geo("hooked_instr")
        ctx.drop_task()
    wait_labels(ids3, args.wait_min)
    com2 = commits5.commit2()
    # ---------------------------------------------------------------- Stage 4 (confirmation on fresh S2 slots)
    for task, cells in com2["stage4_plan"].items():
        ctx.run_cells(task, [(a, js) for a, js in cells], "S4", INSTR_RAW)
        ctx.save_geo("hooked_instr")
        ctx.drop_task()
    for task, cells in com2.get("stage5_extra", {}).items():
        ctx.run_cells(task, [(a, js) for a, js in cells], "S5", INSTR_RAW)
        ctx.drop_task()
    (DATA_DIR / "instr2_done.flag").write_text(utc_now())


def stage_instr3(args: argparse.Namespace) -> None:
    """Post-hoc POWER EXTENSION (descriptive; committed as COMMIT #3 before any Stage-4 outcome was inspected):
    S2 slots j 20-29 for the decisive tasks, same arms as Stage 4 plus TWIN, so each decisive cell reaches N = 100."""
    com1 = read_json(PRED_DIR / "commit1.json")
    plan = read_json(PRED_DIR / "commit3_extension.json")["plan"]
    model, tok = load("instr")
    probe = read_json(RESULTS_DIR / "memory_probe.json")
    ctx = Ctx(model, tok, "instr", probe["instr"]["B"])
    ctx.partner = com1["partner"]
    ctx.dbar = np.load(DBAR)
    ctx.dbar_gen = ctx.dbar.mean(0)  # type: ignore[attr-defined]
    for task, cells in plan.items():
        ctx.run_cells(task, [(a, js) for a, js in cells], "S4X", INSTR_RAW)
        ctx.geo.clear()
        ctx.drop_task()
    (DATA_DIR / "instr3_done.flag").write_text(utc_now())


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["instr1", "base1", "instr2", "instr3"])
    ap.add_argument("--wait-min", type=float, default=60.0)
    args = ap.parse_args()
    setup_logging(f"gpu_{args.stage}")
    set_ram_limit(48)
    torch.manual_seed(0)
    t0 = time.time()
    {"instr1": stage_instr1, "base1": stage_base1, "instr2": stage_instr2, "instr3": stage_instr3}[args.stage](args)
    logger.info(f"{args.stage} finished in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
