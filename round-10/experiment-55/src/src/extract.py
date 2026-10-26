#!/usr/bin/env python3
"""Stages 2.2 / 3: teacher-forced program states with the frozen iteration-9 readout (exp46 stage_mcode.build and
stage_mcode.forward_readouts, imported unchanged) under the neutral-twin context, through the exact truncated
decoder (exp46 states.load_truncated: embedding on the CPU, upper blocks never built).

Per program: R [4 readouts (R1, R1g, R2, R3), n_blocks, d] float16 plus E0 = mean of the input-embedding rows over the
code span (the bag-of-tokens baseline; CPU, exact). Checks before any set (plan T3): hook_check max abs diff 0 on
2 texts; 10 cached iteration-9 M-code programs re-extracted with cosine >= 0.9999 and equal n_code_tokens.
RANDNET: the same truncated Qwen3-8B architecture with torch.manual_seed(0) random init (config.initializer_range),
bf16, block 17 R1 only. Sets are JSONL files of {uid, scrubbed, context_variant}; outputs
cache/states_v10/<model>_<set>.npz + <model>_<set>.jsonl (index). Resumable per set.

CLI: python src/extract.py <model 8b|32b|randnet> <set> [<set> ...]   (special set 'repro' = checks only)
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v10  # noqa: E402

SETS = {"placed": v10.DATA / "placed_programs.jsonl", "refs": v10.DATA / "references_set.jsonl",
        "factorial": v10.DATA / "factorial_set.jsonl", "factorial_ctx2": v10.DATA / "factorial_set_ctx2.jsonl",
        "topups": v10.DATA / "topups_set.jsonl"}


def contexts() -> list[dict[str, Any]]:
    return v10.read_json(v10.IN46 / "data" / "mcode_contexts.json")["variants"]


def load(model_tag: str) -> tuple[Any, Any, dict[str, Any]]:
    import torch

    import states

    torch.cuda.set_per_process_memory_fraction(0.93)
    if model_tag == "randnet":
        return load_randnet()
    m = v10.MODELS[model_tag]
    model, tok, info = states.load_truncated(m["repo"], m["precision"], m["n_keep"], m["revision"])
    return model, tok, info


def load_randnet() -> tuple[Any, Any, dict[str, Any]]:
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    m = v10.M8
    cfg = AutoConfig.from_pretrained(m["repo"], revision=m["revision"])
    cfg.num_hidden_layers = 18
    if getattr(cfg, "layer_types", None):
        cfg.layer_types = list(cfg.layer_types)[:18]
    torch.manual_seed(0)
    model = AutoModelForCausalLM.from_config(cfg, torch_dtype=torch.bfloat16, attn_implementation="sdpa")
    model.model.embed_tokens.to("cpu")
    model.model.layers.to("cuda")
    model.model.norm.to("cuda")
    model.model.rotary_emb.to("cuda")
    model.eval()
    tok = AutoTokenizer.from_pretrained(m["repo"], revision=m["revision"])
    info = {"repo": m["repo"] + " (random init, torch.manual_seed(0), initializer_range "
            f"{cfg.initializer_range})", "n_layers_loaded": 18, "precision": "bf16", "randnet": True}
    return model, tok, info


def blocks_for(model_tag: str) -> list[int]:
    return [17] if model_tag == "randnet" else v10.MODELS[model_tag]["blocks"]


def one(model: Any, tok: Any, code: str, ctx_prompt: str, blocks: list[int]) -> tuple[np.ndarray, np.ndarray, dict]:
    import torch

    import stage_mcode
    import states

    b = stage_mcode.build(tok, code, ctx_prompt)
    assert b["decoded_equal"], "code span decode mismatch"
    arr, info = stage_mcode.forward_readouts(model, b["input_ids"], b["idx"], b["r2"], b["r3"], blocks)
    dec = states._decoder(model)
    with torch.no_grad():
        emb = dec.embed_tokens(torch.tensor([b["input_ids"]]).cpu())[0].float()
        e0 = emb[b["idx"]].mean(0).cpu().numpy()
    meta = {"n_tokens": b["n_tokens"], "n_code_tokens": len(b["idx"]), "r2_rule": b["r2_rule"],
            "r1g_excluded_max": max(info["r1g_excluded_by_block"].values())}
    return arr.astype(np.float16), e0.astype(np.float32), meta


def hook_and_repro(model: Any, tok: Any, model_tag: str) -> dict[str, Any]:
    import states

    out: dict[str, Any] = {"utc": v10.utc_now(), "model": model_tag}
    ctx = contexts()
    t1 = ctx[0]["prompt"]
    out["hook_check"] = states.hook_check(model, tok, [t1, ctx[1]["prompt"] + "\n```python\ndef solve(g, s, t):\n"
                                                      "    return []\n```"])
    if model_tag == "randnet":
        return out
    z = np.load(v10.E46_STATES / f"mcode_{model_tag}.npz")
    keys = [str(k) for k in z["keys"]]
    zb = [int(b) for b in z["blocks"]]
    meta9 = {m["key"]: m for m in v10.read_json(v10.IN46 / "results" / f"states_mcode_{model_tag}.json")["programs"]}
    ms = v10.read_json(v10.IN46 / "data" / "mcode_sets.json")
    progs = {}
    for name, s in ms["sets"].items():
        for a, rows in s.items():
            for r in rows:
                progs.setdefault(r["scrubbed_sha256"], r)
    test_keys = [k for k in keys if k in progs][:10]
    blocks = [b for b in blocks_for(model_tag) if b in zb]
    cos, eq = [], []
    for k in test_keys:
        p = progs[k]
        arr, _e0, meta = one(model, tok, p["scrubbed"], ctx[meta9[k]["context_variant"]]["prompt"], blocks)
        ref = z["R"][keys.index(k)][:, [zb.index(b) for b in blocks]].astype(np.float32)
        a = arr.astype(np.float32)
        for ri in range(4):
            for bi in range(len(blocks)):
                x, y = a[ri, bi], ref[ri, bi]
                cos.append(float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12)))
        eq.append(meta["n_code_tokens"] == meta9[k]["n_code_tokens"])
    out["repro"] = {"n_programs": len(test_keys), "blocks": blocks, "min_cosine": min(cos), "mean_cosine":
                    float(np.mean(cos)), "n_code_tokens_equal": f"{sum(eq)}/{len(eq)}",
                    "pass": min(cos) >= 0.9999 and all(eq)}
    return out


def extract_set(model: Any, tok: Any, model_tag: str, set_name: str, ctx_shift: int = 0) -> dict[str, Any]:
    import torch

    src = SETS[set_name]
    rows = v10.read_jsonl(src)
    blocks = blocks_for(model_tag)
    out_npz = v10.STATES_V10 / f"{model_tag}_{set_name}.npz"
    out_idx = v10.STATES_V10 / f"{model_tag}_{set_name}.jsonl"
    uids = [r["uid"] for r in rows]
    if out_npz.exists():
        z = np.load(out_npz, allow_pickle=False)
        if [str(u) for u in z["uids"]] == uids:
            logger.info(f"{model_tag}/{set_name}: cached ({len(uids)})")
            return {"cached": True, "n": len(uids)}
    ctx = contexts()
    d = 4096 if model_tag in ("8b", "randnet") else 5120
    R = np.zeros((len(rows), 4, len(blocks), d), np.float16)
    E0 = np.zeros((len(rows), d), np.float32)
    metas = []
    t0 = time.time()
    for i, r in enumerate(rows):
        cv = (int(r["context_variant"]) + ctx_shift) % 5
        arr, e0, meta = one(model, tok, r["scrubbed"], ctx[cv]["prompt"], blocks)
        R[i], E0[i] = arr, e0
        metas.append({"uid": r["uid"], "context_variant": cv, **meta})
        if i in (0, 9, 49, 99) or (i + 1) % 100 == 0 or i + 1 == len(rows):
            el = time.time() - t0
            logger.info(f"{model_tag}/{set_name} {i + 1}/{len(rows)}: {el:.0f}s ({el / (i + 1):.2f}s/program), "
                        f"peak VRAM {torch.cuda.max_memory_allocated() / 1e9:.1f} GB")
    if model_tag == "randnet":
        R = R[:, :1]                     # R1 only for the random network
    np.savez(out_npz, R=R, E0=E0, uids=np.array(uids), blocks=np.array(blocks),
             readouts=np.array(v10.READOUTS if model_tag != "randnet" else ["R1"]))
    with out_idx.open("w") as fh:
        for m in metas:
            fh.write(json.dumps(m) + "\n")
    dt = time.time() - t0
    v10.append_jsonl(v10.RESULTS / "timing_states.jsonl", {"model": model_tag, "set": set_name, "n": len(rows),
                                                           "seconds": round(dt, 1), "utc": v10.utc_now()})
    return {"n": len(rows), "seconds": dt}


def main() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (60 * 1024 ** 3, 60 * 1024 ** 3))
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(str(v10.LOGS / "extract.log"), rotation="30 MB", level="DEBUG")
    model_tag, sets = sys.argv[1], sys.argv[2:]
    model, tok, info = load(model_tag)
    v10.write_json(v10.RESULTS / f"load_{model_tag}.json", {k: v for k, v in info.items()
                                                            if k != "quantization_config"} | {"utc": v10.utc_now()})
    chk_path = v10.RESULTS / f"state_checks_{model_tag}.json"
    if not chk_path.exists():
        chk = hook_and_repro(model, tok, model_tag)
        v10.write_json(chk_path, chk)
        logger.info(f"checks {model_tag}: hook {chk['hook_check']} repro {chk.get('repro')}")
    for s in sets:
        if s == "repro":
            continue
        shift = 1 if s == "factorial_ctx2" else 0
        res = extract_set(model, tok, model_tag, s, ctx_shift=0)
        _ = shift
        logger.info(f"done {model_tag}/{s}: {res}")
        gc.collect()


if __name__ == "__main__":
    main()
