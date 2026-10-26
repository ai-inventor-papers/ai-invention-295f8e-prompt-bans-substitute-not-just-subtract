#!/usr/bin/env python3
"""S5: AV explanations (kitft/nla-qwen2.5-7b-L20-av, bf16, HF generate with inputs_embeds -- deviation (i) from the
reference SGLang client, checked by unit tests U5/U6 and the reference-set FVE).

Mirrors nla-inference/nla_inference.py exactly: the sidecar's AV template with the injection char, one-step
apply_chat_template(tokenize=True, add_generation_prompt=True), embeds = embed_tokens(ids) (embed_scale 1.0 for Qwen),
the row at the injection token (id 149705, neighbours 29 / 522 asserted) overwritten by v * injection_scale / ||v||_fp32,
inputs_embeds only (never input_ids), sampling T 1.0 / top-p 1.0 / no top-k / no repetition penalty (= the SGLang
defaults the reference client sends: temperature 1.0, max_new_tokens 200), text parsed from <explanation> tags.

Usage: python src/nla_av.py gate      (smoke tests + reference set under BOTH layer conventions)
       python src/nla_av.py production (readout states under the chosen convention; needs commit2)
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfg import (AV_ID, AV_REVISION, CACHE_DIR, DATA_DIR, D_MODEL, PRED_DIR, RESULTS_DIR, append_jsonl, model_path,
                 read_json, read_jsonl, set_ram_limit, setup_logging, stable_seed, utc_now, write_json)

EXPL = DATA_DIR / "explanations.jsonl"
CJK_RE = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿가-힯㈀-㋿＀-￯]")
MARKER_RE = re.compile(r"(㈎|concept tag|<concept>|the marker|chinese character|cjk character|injection char|"
                       r"parenthesi[sz]ed (hangul|ideograph)|enclosed (cjk|ideograph))", re.I)


class AV:
    def __init__(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        t0 = time.time()
        path = model_path(AV_ID, AV_REVISION)
        self.meta = yaml.safe_load(Path(path, "nla_meta.yaml").read_text())
        assert self.meta["role"] == "av" and self.meta["d_model"] == D_MODEL
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                          device_map={"": 0})
        self.model.eval().requires_grad_(False)
        tk = self.meta["tokens"]
        self.inj_char, self.inj_id = tk["injection_char"], tk["injection_token_id"]
        self.left, self.right = tk["injection_left_neighbor_id"], tk["injection_right_neighbor_id"]
        self.scale = float(self.meta["extraction"]["injection_scale"])
        live = self.tok.encode(self.inj_char, add_special_tokens=False)
        assert live == [self.inj_id], f"injection char tokenises to {live}"
        content = self.meta["prompt_templates"]["av"].format(injection_char=self.inj_char)
        ids = self.tok.apply_chat_template([{"role": "user", "content": content}], tokenize=True,
                                           add_generation_prompt=True)
        self.ids = list(ids["input_ids"] if isinstance(ids, dict) else ids)
        hits = [p for p, t in enumerate(self.ids) if t == self.inj_id and 0 < p < len(self.ids) - 1
                and self.ids[p - 1] == self.left and self.ids[p + 1] == self.right]
        assert len(hits) == 1, f"injection sites with correct neighbours: {hits}"
        self.pos = hits[0]
        with torch.no_grad():
            self.base = self.model.model.embed_tokens(torch.tensor([self.ids], device=self.model.device))  # bf16
        self.rendered = self.tok.decode(self.ids)
        logger.info(f"AV loaded in {time.time() - t0:.0f}s; prompt {len(self.ids)} tokens, injection at {self.pos}; "
                    f"scale {self.scale}")

    @torch.no_grad()
    def explain(self, V: np.ndarray, seed: int, max_new: int = 200) -> list[dict[str, Any]]:
        """V: [B, D] raw vectors (any norm). One sampled explanation per row."""
        B = V.shape[0]
        v = torch.tensor(V, dtype=torch.float32, device=self.model.device)
        assert torch.isfinite(v).all()
        v = v / (v.norm(dim=-1, keepdim=True).clamp_min(1e-12) / self.scale)
        E = self.base.expand(B, -1, -1).clone()
        E[:, self.pos] = v.to(E.dtype)
        inj_norm = float(E[:, self.pos].float().norm(dim=-1).mean())
        mask = torch.ones(E.shape[:2], dtype=torch.long, device=E.device)
        torch.manual_seed(seed)
        out = self.model.generate(inputs_embeds=E, attention_mask=mask, do_sample=True, temperature=1.0, top_p=1.0,
                                  top_k=0, repetition_penalty=1.0, max_new_tokens=max_new,
                                  eos_token_id=[151645, 151643], pad_token_id=151643)
        res = []
        for r in range(B):
            ids = [int(t) for t in out[r].tolist()]
            cut = next((i for i, t in enumerate(ids) if t in (151645, 151643)), len(ids))
            raw = self.tok.decode(ids[:cut], skip_special_tokens=True)
            res.append(parse(raw) | {"n_tokens": cut, "inj_norm": inj_norm})
        return res


def parse(raw: str) -> dict[str, Any]:
    m = re.search(r"<explanation>\s*(.*?)\s*</explanation>", raw, re.S)
    truncated = False
    if m:
        text = m.group(1)
    else:
        m2 = re.search(r"<explanation>\s*(.*)$", raw, re.S)
        text = m2.group(1) if m2 else raw
        truncated = True
    chars = [c for c in text if not c.isspace()]
    cjk = (sum(bool(CJK_RE.match(c)) for c in chars) / len(chars)) if chars else 0.0
    return {"text": text.strip(), "raw": raw, "truncated": truncated, "cjk_share": round(cjk, 4),
            "flag_cjk": cjk > 0.3, "flag_marker": bool(MARKER_RE.search(text))}


def run_items(av: AV, items: list[dict[str, Any]], V: np.ndarray, batch: int, tag: str) -> list[dict[str, Any]]:
    """items[i] = {expl_id, state_id, convention, idx, ...}; V[i] = its vector. Appends to data/explanations.jsonl."""
    done = {r["expl_id"] for r in read_jsonl(EXPL)}
    order = [i for i, it in enumerate(items) if it["expl_id"] not in done]
    out = []
    t0 = time.time()
    for s in range(0, len(order), batch):
        part = order[s:s + batch]
        seed = stable_seed("av", tag, items[part[0]]["expl_id"]) % (2 ** 31)
        try:
            res = av.explain(V[part], seed)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            half = max(1, len(part) // 2)
            res = av.explain(V[part[:half]], seed) + av.explain(V[part[half:]], seed + 1)
        rows = [dict(items[i], **r, seed=seed, utc=utc_now()) for i, r in zip(part, res)]
        append_jsonl(EXPL, rows)
        out += rows
        el = time.time() - t0
        logger.info(f"{tag}: {s + len(part)}/{len(order)} explanations in {el:.0f}s "
                    f"({el / (s + len(part)):.2f} s/expl); truncated {sum(r['truncated'] for r in rows)}/{len(rows)}")
    return out


def load_states() -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    idx = read_jsonl(CACHE_DIR / "states_index.jsonl")
    z = np.load(CACHE_DIR / "states_L20.npz")
    return idx, {"hs20": z["H20"], "hs21": z["H21"]}


def stage_gate(av: AV) -> dict[str, Any]:
    idx, H = load_states()
    rng = np.random.default_rng(0)
    rand_unit = rng.standard_normal((4, D_MODEL)).astype(np.float32)
    smoke = av.explain(rand_unit, seed=1)
    sm_rows = [r for r in idx if r["kind"] == "SMOKE"]
    items, V = [], []
    for r in sm_rows:
        for conv in ("hs20", "hs21"):
            for j in range(3):
                items.append({"expl_id": f"{r['state_id']}|{conv}#{j + 1}", "state_id": r["state_id"],
                              "convention": conv, "idx": j + 1, "kind": "SMOKE", "task": None, "condition": "smoke",
                              "template": None, "position": r["position"], "pos_class": "SMOKE"})
                V.append(H[conv][r["row"]])
    ref = [r for r in idx if r["kind"] == "REF"]
    for r in ref:
        for conv in ("hs20", "hs21"):
            items.append({"expl_id": f"{r['state_id']}|{conv}#1", "state_id": r["state_id"], "convention": conv,
                          "idx": 1, "kind": "REF", "ref_class": r["ref_class"], "gate_set": r["gate_set"],
                          "task": None, "condition": r["ref_class"], "template": None, "position": r["position"],
                          "pos_class": "REF"})
            V.append(H[conv][r["row"]])
    rows = run_items(av, items, np.stack(V), batch=96, tag="gate")
    sm = [r for r in read_jsonl(EXPL) if r["kind"] == "SMOKE"]
    fr = {conv: [r["text"] for r in sm if r["convention"] == conv and r["state_id"] == "SMOKE|france"]
          for conv in ("hs20", "hs21")}
    frl = {conv: [r["text"] for r in sm if r["convention"] == conv and r["state_id"] == "SMOKE|france_long"]
           for conv in ("hs20", "hs21")}
    hit = lambda ts: sum(bool(re.search(r"france|paris|capital", t, re.I)) for t in ts)
    refx = [r for r in read_jsonl(EXPL) if r["kind"] == "REF"]
    out = {"random_unit_vector": [s["text"][:400] for s in smoke],
           "random_unit_nondegenerate": sum(len(s["text"].split()) >= 15 and not s["flag_cjk"] for s in smoke),
           "france_short": {c: {"n": len(v), "mention_france_paris_capital": hit(v), "texts": v} for c, v in fr.items()},
           "france_long": {c: {"n": len(v), "mention_france_paris_capital": hit(v), "texts": v} for c, v in frl.items()},
           "ref_cjk_rate": {c: float(np.mean([r["flag_cjk"] for r in refx if r["convention"] == c])) for c in ("hs20", "hs21")},
           "ref_marker_rate": {c: float(np.mean([r["flag_marker"] for r in refx if r["convention"] == c])) for c in ("hs20", "hs21")},
           "ref_truncated_rate": {c: float(np.mean([r["truncated"] for r in refx if r["convention"] == c])) for c in ("hs20", "hs21")},
           "injected_row_norm": smoke[0]["inj_norm"], "prompt_len": len(av.ids), "injection_pos": av.pos,
           "rendered_prompt": av.rendered}
    write_json(RESULTS_DIR / "av_smoke.json", out)
    logger.info(f"AV smoke: random non-degenerate {out['random_unit_nondegenerate']}/4; France short "
                f"{ {c: v['mention_france_paris_capital'] for c, v in out['france_short'].items()} }, long "
                f"{ {c: v['mention_france_paris_capital'] for c, v in out['france_long'].items()} }")
    return out


def stage_production(av: AV) -> None:
    c2 = read_json(PRED_DIR / "commit2_readout.json")
    conv = read_json(RESULTS_DIR / "layer_convention.json")["chosen"]
    idx, H = load_states()
    items, V = [], []
    sel = c2["readout_state_ids"]
    extra = set(c2["edit_pool_state_ids"])
    for r in idx:
        sid = r["state_id"]
        if sid not in sel:
            continue
        n = 6 if sid in extra else 3
        for j in range(n):
            items.append({"expl_id": f"{sid}|{conv}#{j + 1}", "state_id": sid, "convention": conv, "idx": j + 1,
                          "kind": r["kind"], "task": r["task"], "condition": r["condition"], "mode": r.get("mode"),
                          "template": r["template"], "position": r["position"], "pos_class": r["pos_class"],
                          "sample_id": r.get("sample_id"), "mixed": r.get("mixed")})
            V.append(H[conv][r["row"]])
    logger.info(f"production: {len(items)} explanations for {len(sel)} states")
    run_items(av, items, np.stack(V), batch=128, tag="prod")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["gate", "production"])
    args = ap.parse_args()
    setup_logging(f"av_{args.stage}")
    set_ram_limit(60)
    av = AV()
    if args.stage == "gate":
        stage_gate(av)
    else:
        stage_production(av)
    (DATA_DIR / f"flag_av_{args.stage}.done").write_text(utc_now())


if __name__ == "__main__":
    main()
