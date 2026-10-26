#!/usr/bin/env python3
"""GPU stages, part B (plan STEPS 5-9, 11): targets (CPU), layer profile + generation confirmation, caches + DAS fits
with every control, held-out teacher-forced evaluation, held-out generation cells, the R lambda sweep, M states and
the Sutter random-initialisation control.

Arms of the held-out generation (N = 30, CRN slots 0-29 shared by every arm; W5 bases cycle nouns slot mod 12; forced
bases alternate families 3/4; transfer baselines BASE_W5 and the pooled padding-twin cell BASE_PAD):
  FULL_ban / FULL_F_<Y>            full-state exchange at the site
  DAS_ban_k<k> / DAS_F_<Y>_k<k>    fitted DAS map, rank k
  RAND_ban_k16_d<i> / RAND_F_<Y>_k16 / RAND_ban_k<k*>   random rank-k subspaces (seeds 9001-9003)
  PERM_ban_k16 / PERM_ban_k<k*> / PERM_F_<Y>_k16        permuted-label DAS
  RPOS_ban_k16 / RPOSFULL_ban      read-position DAS and full-state exchange at the read position
  NULL_k16 / NULL_full             'Implement <default>' (families 3/4) -> its padding twin
  REV_k<k*> / REV_full             reverse interchange: twin W5 value written into the W5 ban (outcome: default)
  DIM1_ban / PCA16_ban             unlearned subspaces; W4_*: ban W4 -> W4 twin (N = 10, reported separately)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import RESULTS_DIR, ROOT, append_jsonl, read_json, read_jsonl, sha256_file, utc_now, write_json
from cfg7 import (BAND, CATALOGUE7, DEFAULT7, HELD_FAM, K_MAX, LABELS7, MAPS7, N_PI, N_PI_VAL, N_TGT,
                  PROFILE_LAYERS, RANKS, SAMPLES7, SEEDS, TRAIN_FAM, TRAIN_NOUNS, TRAIN_W, VAL_NOUNS, results7)
from das7 import (DASMap, Site, TFContext, fit_das, orthonormal_rows, pack, proj_edit, random_basis, run_blocks,
                  score_ll, lme)
from gpu7 import capture_states, dev_of, make_edit, prefill7, run_specs, spec_row
from stages_a7 import ban_key, forced_key, pad_key, twin_key

BAN_PHRASES = ("not allowed", "instead of", "avoid", "not use", "without using", "don't use", "do not use",
               "must not", "not rely")
T2_ALIASES = {"dijkstra": ["dijkstra"], "bf_spfa": ["bellman", "spfa"], "bidijkstra": ["bidirectional"],
              "floyd": ["floyd", "warshall"], "dial": ["dial", "bucket"]}


# ------------------------------------------------------------------------------------------------ labels
def label_rows(task: str, stage: str | None = None) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(LABELS7) if r["task"] == task and (stage is None or r.get("stage") == stage)]


def wait_labels(sample_ids: set[str], timeout_s: float = 900) -> None:
    t0 = time.time()
    while True:
        have = {r["sample_id"] for r in read_jsonl(LABELS7)}
        miss = sample_ids - have
        if not miss:
            return
        if time.time() - t0 > timeout_s:
            logger.warning(f"wait_labels: {len(miss)} rows still unlabelled after {timeout_s}s; continuing")
            return
        time.sleep(5)


def is_correct(r: dict[str, Any], Y: str | list[str]) -> bool:
    ys = [Y] if isinstance(Y, str) else list(Y)
    return bool(r.get("passed")) and r.get("label") in ys


# ------------------------------------------------------------------------------------------------ STEP 5 targets
def aliases(task: str) -> list[str]:
    if task == "T2":
        return [a for v in T2_ALIASES.values() for a in v]
    from cfg import INPUTS
    d = next(x for x in (INPUTS / "exp11" / "bench").iterdir() if x.name.startswith(task + "_"))
    sp = read_json(d / "spec.json")
    out = [c["display_name"].lower() for c in sp["catalogue"]]
    for v in sp.get("aliases", {}).values():
        out += [a.lower() for a in v]
    return out


def select_targets(task: str, tok: Any) -> dict[str, Any]:
    D = DEFAULT7[task]
    labs = {r["sample_id"]: r for r in label_rows(task, "stage0")}
    raw = {r["sample_id"]: r for r in read_jsonl(SAMPLES7) if r["task"] == task and r.get("stage") == "stage0"}
    al = aliases(task)
    # kept Y (forced adherence over all 5 families, N = 20)
    adher, pad_def, excl_cells = {}, {}, []
    for Y in CATALOGUE7[task]:
        rs = [labs[s] for s in labs if labs[s]["cell"] == "FORCED" and labs[s]["arm"].split("_", 1)[1] == Y]
        adher[Y] = {"n": len(rs), "correct_Y": sum(is_correct(r, Y) for r in rs),
                    "share": sum(is_correct(r, Y) for r in rs) / max(1, len(rs)),
                    "labels": dict(Counter(r["label"] for r in rs))}
        if Y != D:
            ps = [labs[s] for s in labs if labs[s]["cell"] == "PADCHK" and labs[s]["arm"].split("_", 1)[1] == Y]
            pad_def[Y] = {"n": len(ps), "default": sum(r["label"] == D for r in ps),
                          "share": sum(r["label"] == D for r in ps) / max(1, len(ps))}
            for k in range(5):
                c = [r for r in ps if r["arm"] == f"PAD{k}_{Y}"]
                if c and sum(r["label"] == D for r in c) < 3:
                    excl_cells.append([k, Y])
    kept = [Y for Y in CATALOGUE7[task] if Y != D and adher[Y]["share"] >= 0.7 and pad_def[Y]["share"] >= 0.9]
    # ban landing set (W1-W3, N = 30)
    bans = [labs[s] for s in labs if labs[s]["cell"] == "BAN"]
    cnt = Counter(r["label"] for r in bans if r.get("passed"))
    landing_share = {a: c / max(1, len(bans)) for a, c in cnt.items()}
    landing = sorted([a for a, s in landing_share.items() if s >= 0.2 and a != D and a in CATALOGUE7[task]],
                     key=lambda a: -landing_share[a])
    # programs
    min_len = 16 if task == "T03" else N_TGT

    def cand(rows: list[dict[str, Any]], Y: str) -> list[dict[str, Any]]:
        out = []
        seen = set()
        for r in rows:
            if not is_correct(r, Y):
                continue
            ids = raw[r["sample_id"]]["token_ids"]
            if len(ids) < min_len:
                continue
            t = tuple(ids[:N_TGT])
            if t in seen:
                continue
            seen.add(t)
            txt = tok.decode(list(t)).lower()
            clean = not any(a in txt for a in al) and not any(b in txt for b in BAN_PHRASES)
            out.append({"sample_id": r["sample_id"], "ids": list(t), "clean": clean, "n_tok": len(t),
                        "code_sha256": r.get("code_sha256")})
        out.sort(key=lambda x: (not x["clean"],))  # stable: clean first, original order kept
        return out

    def by_slot(rows):
        return sorted(rows, key=lambda r: (r["arm"], r["slot_index"]))

    pools: dict[str, list[dict[str, Any]]] = {}
    for Y in set(kept) | set(landing):
        ban_rows = by_slot([labs[s] for s in labs if labs[s]["cell"] == "BAN"])
        f_rows = by_slot([labs[s] for s in labs if labs[s]["cell"] == "FORCED" and labs[s]["arm"].split("_", 1)[1] == Y
                          and int(labs[s]["arm"][1]) in TRAIN_FAM])
        first, second = (ban_rows, f_rows) if Y in landing else (f_rows, ban_rows)
        c1, c2 = cand(first, Y), cand(second, Y)
        pools[Y] = sorted(c1, key=lambda x: not x["clean"]) + sorted(c2, key=lambda x: not x["clean"])
        # keep clean-first ordering over the pooled list while preferring the first pool on ties
        pools[Y] = sorted(pools[Y], key=lambda x: not x["clean"])
    tw_rows = by_slot([labs[s] for s in labs if labs[s]["cell"] == "TWIN"])
    # amendment v2: the default pool continues with the TRAIN-family padding-twin samples (default prompts) because
    # the noun-0 twins repeat the same 48-token openings (few distinct programs)
    pc_rows = by_slot([labs[s] for s in labs if labs[s]["cell"] == "PADCHK" and int(labs[s]["arm"][3]) in TRAIN_FAM])
    pools[D] = cand(tw_rows, D) + cand(pc_rows, D)
    pools[D] = sorted(pools[D], key=lambda x: not x["clean"])
    targets, targets_val, meta, flags = {}, {}, {}, []
    for a, pl in pools.items():
        dedup, seen = [], set()
        for p in pl:
            if tuple(p["ids"]) not in seen:
                seen.add(tuple(p["ids"]))
                dedup.append(p)
        tr, va = dedup[:N_PI], dedup[N_PI:N_PI + N_PI_VAL]
        if len(tr) < N_PI:
            flags.append(f"{a}: only {len(tr)} training programs")
        if len(va) < N_PI_VAL:
            va = va + tr[:N_PI_VAL - len(va)]
            flags.append(f"{a}: validation set filled from training programs ({N_PI_VAL - len(dedup[N_PI:])})")
        if sum(not p["clean"] for p in tr):
            flags.append(f"{a}: {sum(not p['clean'] for p in tr)} unclean openings in the training set")
        if task == "T03" and any(p["n_tok"] < N_TGT for p in tr):
            flags.append(f"{a}: T03 short-program fallback (min {min(p['n_tok'] for p in tr)} tokens)")
        targets[a] = [p["ids"] for p in tr]
        targets_val[a] = [p["ids"] for p in va]
        meta[a] = {"train": [{k: p[k] for k in ("sample_id", "code_sha256", "clean", "n_tok")} for p in tr],
                   "val": [{k: p[k] for k in ("sample_id", "code_sha256", "clean", "n_tok")} for p in va]}
    groups = {}
    if landing:
        groups["+".join(sorted(landing))] = sorted(landing)
    for Y in kept:
        groups.setdefault(Y, [Y])
    usable = {g: a for g, a in groups.items() if all(len(targets.get(x, [])) >= 2 for x in a)}
    out = {"task": task, "default": D, "kept_Y": kept, "adherence": adher, "pad_default": pad_def,
           "excluded_pad_cells": excl_cells, "landing": landing, "landing_share": landing_share,
           "ban_group": "+".join(sorted(landing)) if landing else None, "groups": usable, "targets": targets,
           "targets_val": targets_val, "target_meta": meta, "flags": flags}
    write_json(results7(f"targets_{task}.json"), out)
    return out


def load_targets(task: str) -> dict[str, Any]:
    return read_json(results7(f"targets_{task}.json"))


# ------------------------------------------------------------------------------------------------ pairs
def train_sources(task: str, T: dict[str, Any]) -> list[tuple[str, str]]:
    out = []
    if T["ban_group"]:
        out += [(ban_key(task, w), T["ban_group"]) for w in TRAIN_W]
    for Y in T["kept_Y"]:
        if Y in T["groups"]:
            out += [(forced_key(task, k, Y), Y) for k in TRAIN_FAM]
    return out


def train_bases(task: str, T: dict[str, Any]) -> list[str]:
    ex = {(k, Y) for k, Y in T["excluded_pad_cells"]}
    out = [twin_key(task, w, n) for w in TRAIN_W for n in TRAIN_NOUNS]
    out += [pad_key(task, k, Y) for k in TRAIN_FAM for Y in T["kept_Y"] if (k, Y) not in ex and Y in T["groups"]]
    return out


def val_bases(task: str) -> list[str]:
    return [twin_key(task, w, n) for w in TRAIN_W for n in VAL_NOUNS]


def held_pairs(task: str, T: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """(source, base, group, kind) for held-out TF evaluation (aligned pairs only)."""
    out = []
    if T["ban_group"]:
        out += [(ban_key(task, "W5"), twin_key(task, "W5", n), T["ban_group"], "ban") for n in range(12)]
    ex = {(k, Y) for k, Y in T["excluded_pad_cells"]}
    for Y in T["kept_Y"]:
        if Y in T["groups"]:
            out += [(forced_key(task, k, Y), pad_key(task, k, Y), Y, f"forced_{Y}") for k in HELD_FAM
                    if (k, Y) not in ex]
    D = DEFAULT7[task]
    if T["ban_group"]:
        out += [(forced_key(task, k, D), pad_key(task, k, D), T["ban_group"], "null") for k in HELD_FAM]
    return out


# ------------------------------------------------------------------------------------------------ STEP 6 profile
@torch.no_grad()
def layer_profile(model: Any, P7: dict, task: str, T: dict[str, Any]) -> dict[str, Any]:
    dev = dev_of(model)
    D = DEFAULT7[task]
    pairs = []
    if T["ban_group"]:
        pairs += [(ban_key(task, w), twin_key(task, w, n), T["ban_group"], "ban") for w in TRAIN_W for n in range(4)]
    ex = {(k, Y) for k, Y in T["excluded_pad_cells"]}
    for Y in T["kept_Y"]:
        if Y in T["groups"]:
            pairs += [(forced_key(task, k, Y), pad_key(task, k, Y), Y, f"forced_{Y}") for k in TRAIN_FAM
                      if (k, Y) not in ex]
    edits = [("none", None, None)] + [(f"full@{l}", [l], "spec") for l in PROFILE_LAYERS] + \
        [("band12-23", list(BAND), "spec"), ("band0-35", list(range(36)), "spec"), ("rpos_all", list(range(36)), "R")]
    src_cache: dict[str, dict[int, torch.Tensor]] = {}
    rows = []
    for (s, b, g, kind) in pairs:
        if s not in src_cache:
            src_cache[s] = capture_states(model, P7[s], list(range(36)))
        src = src_cache[s]
        progs = [p for a in T["groups"][g] for p in T["targets"][a]]
        nY = len(progs)
        progs = progs + T["targets"][D]
        rec = P7[b]
        pk = pack(rec["ids"], progs, dev)
        spec_pos = torch.arange(rec["p1"], rec["spec_end"], device=dev)
        r_pos = torch.tensor([rec["P"] - 1], device=dev)
        h = model.model.embed_tokens(pk["ids"]).expand(len(edits), -1, -1)

        def edit_fn(l: int, hh: torch.Tensor) -> torch.Tensor:
            for i, (_, blocks, pk_) in enumerate(edits):
                if blocks is None or l not in blocks:
                    continue
                if pk_ == "spec":
                    hh = proj_edit(hh, i, spec_pos, src[l][:-1], None)
                else:
                    hh = proj_edit(hh, i, r_pos, src[l][-1:], None)
            return hh
        hout = run_blocks(model, h, pk, 0, 36, edit_fn)
        ll = score_ll(model, hout, pk)
        C = (lme(ll[:, :nY]) - lme(ll[:, nY:])).cpu().numpy()
        for i, (nm, _, _) in enumerate(edits):
            rows.append({"task": task, "source": s, "base": b, "group": g, "kind": kind, "edit": nm,
                         "C": float(C[i]), "gain": float(C[i] - C[0])})
        if len(src_cache) > 6:
            src_cache.pop(next(iter(src_cache)))
    torch.cuda.empty_cache()
    gains = defaultdict(list)
    for r in rows:
        gains[r["edit"]].append(r["gain"])
    mean = {e: float(np.mean(v)) for e, v in gains.items()}
    single = {l: mean[f"full@{l}"] for l in PROFILE_LAYERS}
    best = max(single.values())
    L_star = min(l for l, v in single.items() if v >= best - 0.25)
    by_kind = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_kind[r["kind"].split("_")[0]][r["edit"]].append(r["gain"])
    out = {"task": task, "n_pairs": len(pairs), "mean_gain": mean, "single_layer_gain": single, "L_star": L_star,
           "rule": "argmax mean gain over single blocks, ties within 0.25 nats -> smaller block",
           "by_kind": {k: {e: float(np.mean(v)) for e, v in d.items()} for k, d in by_kind.items()}}
    append_jsonl(ROOT / "data" / "tf_profile.jsonl", rows)
    return out


# ------------------------------------------------------------------------------------------------ generation helpers
class Gen:
    """Builds edited-prefill row specs; source states cached per (source key, blocks)."""

    def __init__(self, model: Any, P7: dict, task: str):
        self.model, self.P7, self.task = model, P7, task
        self.dev = dev_of(model)
        self.src: dict[tuple[str, tuple[int, ...]], dict[int, torch.Tensor]] = {}
        self.pre_plain: dict[str, Any] = {}

    def states(self, key: str, blocks: list[int]) -> dict[int, torch.Tensor]:
        k = (key, tuple(blocks))
        if k not in self.src:
            if len(self.src) > 24:
                self.src.pop(next(iter(self.src)))
            self.src[k] = capture_states(self.model, self.P7[key], blocks)
        return self.src[k]

    def plain(self, key: str) -> dict[str, Any]:
        if key not in self.pre_plain:
            if len(self.pre_plain) > 40:
                self.pre_plain.pop(next(iter(self.pre_plain)))
            self.pre_plain[key] = prefill7(self.model, self.P7[key]["ids"])
        return self.pre_plain[key]

    def make(self, base: str, source: str | None, blocks: list[int], pos_kind: str = "spec",
             B: torch.Tensor | None = None, full: bool = False, lam: float = 1.0):
        """Return a closure producing (prefill, realised displacement) for an edited base prompt."""
        def f():
            if source is None:
                return self.plain(base), None
            rec = self.P7[base]
            st = self.states(source, blocks)
            if pos_kind == "spec":
                pos = torch.arange(rec["p1"], rec["spec_end"], device=self.dev)
                src = {l: st[l][:-1] for l in blocks}
            else:
                pos = torch.tensor([rec["P"] - 1], device=self.dev)
                src = {l: st[l][-1:] for l in blocks}
            log: dict[int, list[float]] = {}
            ed = make_edit(pos, src, "full" if full else "proj", B=None if full else B.to(self.dev), lam=lam,
                           log=log)
            pre = prefill7(self.model, rec["ids"], edits=ed)
            disp = {int(l): round(v[0], 4) for l, v in log.items()}
            return pre, disp
        return f


def slot_base_ban(task: str, s: int) -> str:
    return twin_key(task, "W5", s % 12)


def slot_forced(task: str, s: int, Y: str) -> tuple[str, str]:
    k = 3 + (s % 2)
    return forced_key(task, k, Y), pad_key(task, k, Y)


def site_of(task: str) -> dict[str, Any]:
    return read_json(results7(f"site_{task}.json"))


def site_blocks(task: str) -> list[int]:
    s = site_of(task)
    return list(BAND) if s["site"] == "band" else [int(s["L_star"])]


# ------------------------------------------------------------------------------------------------ transfer
def counts(task: str, arm: str, Y: list[str] | str, n: int = 30) -> dict[str, Any]:
    rs = [r for r in label_rows(task) if r["arm"] == arm and r["slot_index"] < n]
    ys = [Y] if isinstance(Y, str) else Y
    return {"n": len(rs), "correct_Y": sum(is_correct(r, ys) for r in rs), "pass": sum(bool(r.get("passed"))
                                                                                       for r in rs)}


# ------------------------------------------------------------------------------------------------ stage runners
def stage_targets(task: str, tok: Any, suffix: str = "_v2") -> dict[str, Any]:
    ids = {r["sample_id"] for r in read_jsonl(SAMPLES7) if r["task"] == task and r.get("stage") == "stage0"}
    wait_labels(ids)
    T = select_targets(task, tok)
    from commit7 import commit
    commit(f"commit1_{task}{suffix}", {"amendment": "v2: default pool extended to TRAIN-family padding-twin "
                                                     "samples (duplicated twin openings)" if suffix else None,
                                       "kept_Y": T["kept_Y"], "landing": T["landing"], "groups": T["groups"],
                               "excluded_pad_cells": T["excluded_pad_cells"], "adherence": T["adherence"],
                               "pad_default": T["pad_default"], "target_meta": T["target_meta"], "flags": T["flags"],
                               "targets_sha256": hashlib.sha256(json.dumps(T["targets"]).encode()).hexdigest()})
    logger.info(f"targets {task}: kept {T['kept_Y']} landing {T['landing']} groups {T['groups']} flags {T['flags']}")
    return T


def stage_profile(model: Any, tok: Any, P7: dict, task: str) -> dict[str, Any]:
    T = load_targets(task)
    prof = layer_profile(model, P7, task, T)
    L = prof["L_star"]
    logger.info(f"profile {task}: L* = {L}; single-layer gains {prof['single_layer_gain']}")
    G = Gen(model, P7, task)
    specs = []
    # BASE_W5 + FULL at L* and band on the W5 ban source; one held-out forced Y at family 3
    for s in range(30):
        b = slot_base_ban(task, s)
        specs.append(spec_row(task, "BASE_W5", "BASE", s, P7[b], make=G.make(b, None, []), stage="gen"))
        specs.append(spec_row(task, f"FULL_ban_L{L}", "CONFIRM", s, P7[b], make=G.make(b, ban_key(task, "W5"), [L],
                                                                                        full=True),
                              stage="gen", source_key=ban_key(task, "W5"), site=f"L{L}", layer=L, Y_source="ban"))
        specs.append(spec_row(task, "FULL_ban_band", "CONFIRM", s, P7[b],
                              make=G.make(b, ban_key(task, "W5"), list(BAND), full=True), stage="gen",
                              source_key=ban_key(task, "W5"), site="band12-23", Y_source="ban"))
    Yc = (T["landing"][0] if T["landing"] and T["landing"][0] in T["kept_Y"] else
          (max(T["kept_Y"], key=lambda y: T["adherence"][y]["share"]) if T["kept_Y"] else None))
    if Yc is not None:
        fk, pk_ = forced_key(task, 3, Yc), pad_key(task, 3, Yc)
        for s in range(30):
            specs.append(spec_row(task, f"PADBASE_F3_{Yc}", "BASE", s, P7[pk_], make=G.make(pk_, None, []),
                                  stage="gen"))
            specs.append(spec_row(task, f"FULLF3_{Yc}_L{L}", "CONFIRM", s, P7[pk_],
                                  make=G.make(pk_, fk, [L], full=True), stage="gen", source_key=fk, site=f"L{L}",
                                  layer=L, Y_source=Yc))
            specs.append(spec_row(task, f"FULLF3_{Yc}_band", "CONFIRM", s, P7[pk_],
                                  make=G.make(pk_, fk, list(BAND), full=True), stage="gen", source_key=fk,
                                  site="band12-23", Y_source=Yc))
    run_specs(model, tok, task, specs, f"CONF:{task}")
    wait_labels({s["sample_id"] for s in specs})
    landing = T["landing"] or T["kept_Y"][:1]
    base = counts(task, "BASE_W5", landing)
    fl = counts(task, f"FULL_ban_L{L}", landing)
    fb = counts(task, "FULL_ban_band", landing)
    tr_L = (fl["correct_Y"] - base["correct_Y"]) / 30
    tr_B = (fb["correct_Y"] - base["correct_Y"]) / 30
    site = "band" if tr_L < 0.5 * tr_B else "layer"
    conf = {"BASE_W5": base, f"FULL_ban_L{L}": fl, "FULL_ban_band": fb, "transfer_L": tr_L, "transfer_band": tr_B}
    if Yc is not None:
        pb = counts(task, f"PADBASE_F3_{Yc}", Yc)
        conf.update({"forced_Y": Yc, f"PADBASE_F3_{Yc}": pb, f"FULLF3_{Yc}_L{L}": counts(task, f"FULLF3_{Yc}_L{L}", Yc),
                     f"FULLF3_{Yc}_band": counts(task, f"FULLF3_{Yc}_band", Yc)})
    out = {"task": task, "L_star": L, "site": site, "profile": prof, "confirmation": conf,
           "fallback_rule": "band if TRANSFER(full@L*) < 0.5 x TRANSFER(band 12-23) on the W5 ban source",
           "band_transfer_lt_0.3": tr_B < 0.3}
    write_json(results7(f"site_{task}.json"), out)
    from commit7 import commit
    commit(f"commit1b_{task}", {"L_star": L, "site": site, "profile_single_layer_gain": prof["single_layer_gain"],
                                "profile_mean_gain": prof["mean_gain"], "confirmation": conf})
    logger.info(f"site {task}: {site} (L* {L}); transfer L {tr_L:.2f} band {tr_B:.2f}")
    return out


# ------------------------------------------------------------------------------------------------ STEP 7 fits
def build_ctx(model: Any, P7: dict, task: str, T: dict[str, Any], pos_kind: str = "spec", val: bool = False
              ) -> TFContext:
    blocks = site_blocks(task)
    tg = T["targets_val"] if val else T["targets"]
    return TFContext(model, P7, tg, Site(blocks, pos_kind), T["groups"], DEFAULT7[task])


def pair_lists(task: str, T: dict[str, Any], perm: dict[str, str] | None = None
               ) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    srcs = train_sources(task, T)
    if perm:
        srcs = [(s, perm[s]) for s, _ in srcs]
    bases = train_bases(task, T)
    tr = [(s, b, g) for s, g in srcs for b in bases]
    vb = val_bases(task)
    va = []
    for i, (s, g) in enumerate(srcs):
        for j in range(3):
            va.append((s, vb[(3 * i + j) % len(vb)], g))
    return tr, va


def save_map(task: str, name: str, W: torch.Tensor, meta: dict[str, Any]) -> str:
    MAPS7.mkdir(parents=True, exist_ok=True)
    p = MAPS7 / f"{task}_{name}.pt"
    torch.save({"basis": W.detach().float().cpu(), "meta": meta}, p)
    return sha256_file(p)


def load_map(task: str, name: str) -> torch.Tensor:
    return torch.load(MAPS7 / f"{task}_{name}.pt", map_location="cpu")["basis"]


@torch.no_grad()
def natural_states(model: Any, P7: dict, task: str, blocks: list[int], kinds: tuple[str, ...]
                   ) -> dict[str, np.ndarray]:
    """Spec-position states (fp32, CPU) of every prompt of the given kinds at the middle block of the site."""
    l = blocks[len(blocks) // 2]
    out = {}
    for k, r in P7.items():
        if r["task"] == task and r["kind"] in kinds:
            st = capture_states(model, r, [l], with_r=False)
            out[k] = st[l].float().cpu().numpy()
    return out


def pcs_centered(states: dict[str, np.ndarray], keys: list[str], n: int) -> tuple[np.ndarray, np.ndarray]:
    """Top-n principal directions of per-position-centred states (variance across prompts at each position)."""
    X = np.stack([states[k] for k in keys])                # [n_prompts, n_pos, D]
    Xc = X - X.mean(0, keepdims=True)
    M = torch.tensor(Xc.reshape(-1, X.shape[-1]), device="cuda")
    U, S, V = torch.pca_lowrank(M, q=min(n + 8, M.shape[0] - 1), center=False, niter=4)
    var = (S ** 2).cpu().numpy()
    return V[:, :n].T.cpu().numpy().astype(np.float32), var


def stage_fit(model: Any, P7: dict, task: str, randinit: bool = False, light: bool = False,
              objective: str = "C") -> dict[str, Any]:
    """light=True (T10, T03; deviation): the committed contrastive objective was shown degenerate on T2 (main and
    permuted-label fits both diverge), so only the committed MAIN fit is run (objective C; T03: none, MAIN_LY only);
    the permutation table, natural states, DIM-1, PCA-16 and the projection basis are produced as usual."""
    T = load_targets(task)
    blocks = site_blocks(task)
    ctx = build_ctx(model, P7, task, T)
    ctx_val = build_ctx(model, P7, task, T, val=True)
    tr, va = pair_lists(task, T)
    seed = SEEDS["das_init"][task]
    logger.info(f"fit {task}: site {blocks}; {len(tr)} train pairs, {len(va)} val pairs")
    res: dict[str, Any] = {"task": task, "site_blocks": blocks, "n_train_pairs": len(tr), "n_val_pairs": len(va)}
    fits = {}
    t0 = time.time()
    main = fit_das(ctx, tr, va, seed, ctx_val=ctx_val, n_steps=150, extend=75, log_name=f"{task}:MAIN",
                   objective=objective)
    n_steps = main["budget"]
    fits["MAIN"] = main
    # F3 fit failure rule: main val gain at k=16 must exceed the random-subspace gain
    rnd_val = []
    for rs in SEEDS["random_subspaces"]:
        Wr = random_basis(rs).to(ctx.dev)
        vn = {}
        g = []
        for (s, b_, gg) in va[:12]:
            C = ctx_val.contrast_rows(b_, gg, [{"none": True}, {"src": s, "B": Wr}])["C"]
            g.append(float(C[1] - C[0]))
        rnd_val.append(float(np.mean(g)))
    res["F3_check"] = {"main_val_gain_k16": main["val"][-1]["gain_by_k"][16] if main["val"] else None,
                       "best_val_mean_gain": main["best_val"], "random_val_gain_k16": rnd_val}
    if objective == "C" and main["val"] and max(v["gain_by_k"][16] for v in main["val"]) <= max(rnd_val):
        logger.warning(f"{task}: F3 fit failure -> refit lr 5e-3, fresh seed")
        main = fit_das(ctx, tr, va, seed + 100, ctx_val=ctx_val, lr=5e-3, n_steps=n_steps, log_name=f"{task}:REFIT")
        fits["MAIN"] = main
        res["F3_refit"] = True
    # permuted-label control
    srcs = train_sources(task, T)
    labels_ = [g for _, g in srcs]
    rng = np.random.default_rng(SEEDS["permutation"])
    perm_labels = list(rng.permutation(labels_))
    perm = {s: str(pl) for (s, _), pl in zip(srcs, perm_labels)}
    res["permutation"] = {"table": perm, "fraction_changed": float(np.mean([perm[s] != g for s, g in srcs]))}
    trp, vap = pair_lists(task, T, perm)
    if not light:
        fits["PERM"] = fit_das(ctx, trp, vap, seed, ctx_val=ctx_val, n_steps=n_steps, log_name=f"{task}:PERM")
        # read-position control
        ctx_r = build_ctx(model, P7, task, T, pos_kind="R")
        ctx_rv = build_ctx(model, P7, task, T, pos_kind="R", val=True)
        fits["RPOS"] = fit_das(ctx_r, tr, va, seed, ctx_val=ctx_rv, n_steps=n_steps, log_name=f"{task}:RPOS")
        ctx_r.free()
        ctx_rv.free()
    res["light"] = light
    res["objective_main"] = objective
    shas = {}
    for nm, f in fits.items():
        shas[nm] = save_map(task, nm, f["basis"], {k: v for k, v in f.items() if k not in ("basis",)})
    # non-fitted controls
    for i, rs in enumerate(SEEDS["random_subspaces"]):
        shas[f"RAND{i + 1}"] = save_map(task, f"RAND{i + 1}", random_basis(rs), {"seed": rs})
    nat = natural_states(model, P7, task, blocks, ("twin", "ban", "forced", "padtwin", "p0"))
    keys_forced_tr = [k for k, r in P7.items() if r["task"] == task and r["kind"] == "forced" and r["split"] == "train"]
    pca16, _ = pcs_centered(nat, keys_forced_tr, 16)
    shas["PCA16"] = save_map(task, "PCA16", torch.tensor(pca16), {"rule": "top-16 PCs of per-position-centred spec "
                                                                          "states of TRAIN forced prompts (all Y)"})
    # DIM-1 over TRAIN pairs (aligned by offset from p1) at the site's middle block
    lmid = blocks[len(blocks) // 2]
    diffs = []
    for (s, b_, g) in tr[:: max(1, len(tr) // 120)]:
        hs = nat.get(s)
        hb = nat.get(b_)
        if hs is not None and hb is not None:
            diffs.append((hs - hb).mean(0))
    dim = np.mean(diffs, 0)
    dim = dim / np.linalg.norm(dim)
    shas["DIM1"] = save_map(task, "DIM1", torch.tensor(dim[None].astype(np.float32)), {"block": lmid,
                                                                                         "n_pairs": len(diffs)})
    keys_nat = [k for k in nat if P7[k]["kind"] in ("twin", "ban", "forced")]
    p64, var_all = pcs_centered(nat, keys_nat, 64)
    np.save(MAPS7 / f"{task}_natural_pc64.npy", p64)
    W = fits["MAIN"]["basis"].float()
    Wp = torch.tensor(p64)
    proj = orthonormal_rows(W @ Wp.T @ Wp)
    shas["PROJ64"] = save_map(task, "PROJ64", proj, {"rule": "MAIN map projected on the top-64 natural "
                                                             "cross-condition PCs, re-orthonormalised (nested by rank: "
                                                             "QR of the projected rows keeps prefixes)"})
    res.update({"fits": {nm: {k: v for k, v in f.items() if k != "basis"} for nm, f in fits.items()},
                "map_sha256": shas, "n_steps_budget": n_steps, "seconds": round(time.time() - t0, 1)})
    write_json(results7(f"das_fits_{task}.json"), res)
    np.savez_compressed(ROOT / "cache" / f"natural_states_{task}.npz", **{k.replace("|", "__"): v.mean(0)
                                                                          for k, v in nat.items()})
    from commit7 import commit
    commit(f"commit2_{task}", {"map_sha256": shas, "seeds": SEEDS, "permutation": res["permutation"],
                               "site_blocks": blocks, "n_steps_budget": n_steps,
                               "k_star_rule": "smallest k with generation recovery >= 0.8 on the ban source, else 16"})
    ctx.free()
    ctx_val.free()
    return res


# ------------------------------------------------------------------------------------------------ STEP 8 TF eval
@torch.no_grad()
def stage_tfeval(model: Any, P7: dict, task: str) -> dict[str, Any]:
    T = load_targets(task)
    ctx = build_ctx(model, P7, task, T)
    ctx_r = build_ctx(model, P7, task, T, pos_kind="R")
    dev = ctx.dev
    maps = {}
    for nm in ("MAIN", "PERM", "RPOS", "RAND1", "RAND2", "RAND3", "PCA16", "DIM1", "PROJ64"):
        try:
            maps[nm] = load_map(task, nm).to(dev)
        except FileNotFoundError:
            maps[nm] = None
    rows = []
    for (s, b, g, kind) in held_pairs(task, T):
        edits = [("none", None), ("full", "FULL")]
        edits += [(f"DAS_k{k}", maps["MAIN"][:k]) for k in RANKS]
        edits += [(f"RAND{i}_k{k}", maps[f"RAND{i}"][:k]) for i in (1, 2, 3) for k in RANKS]
        if maps["PERM"] is not None:
            edits += [(f"PERM_k{k}", maps["PERM"][:k]) for k in RANKS]
        edits += [(f"PROJ_k{k}", maps["PROJ64"][:k]) for k in RANKS]
        edits += [("DIM1", maps["DIM1"]), ("PCA16", maps["PCA16"])]
        out = {}
        for c0 in range(2, len(edits), 8):
            chunk = edits[:2] + edits[c0:c0 + 8]
            rr = [{"none": True} if B is None else ({"src": s, "B": None} if isinstance(B, str) else
                                                     {"src": s, "B": B}) for _, B in chunk]
            o = ctx.contrast_rows(b, g, rr)
            for i, (nm, _) in enumerate(chunk):
                if nm not in out or c0 == 2:
                    out[nm] = (float(o["C"][i]), float(o["lmeY"][i]), float(o["lmeD"][i]))
        rmaps = [(nm, maps[nm] if nm in maps else None) for nm in ("RPOS",)]
        try:
            rmaps.append(("RPOSLY", load_map(task, "RPOS_LY").to(dev)))
        except FileNotFoundError:
            pass
        rr = [{"none": True}, {"src": s, "B": None}]
        names = ["none_R", "RPOSFULL"]
        for nm, Wm in rmaps:
            if Wm is None:
                continue
            rr += [{"src": s, "B": Wm[:k]} for k in RANKS]
            names += [f"{nm}_k{k}" for k in RANKS]
        o = ctx_r.contrast_rows(b, g, rr)
        for i, nm in enumerate(names):
            out[nm] = (float(o["C"][i]), float(o["lmeY"][i]), float(o["lmeD"][i]))
        for nm, (C, lY, lD) in out.items():
            rows.append({"task": task, "source": s, "base": b, "group": g, "kind": kind, "edit": nm, "C": C,
                         "lmeY": lY, "lmeD": lD})
    append_jsonl(ROOT / "data" / "tf_heldout.jsonl", rows)
    ctx.free()
    ctx_r.free()
    return summarize_tf(task, rows)


def summarize_tf(task: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    by = defaultdict(dict)
    for r in rows:
        by[(r["source"], r["base"])][r["edit"]] = r
    agg = defaultdict(lambda: defaultdict(list))
    for (s, b), d in by.items():
        kind = next(iter(d.values()))["kind"]
        kk = "forced" if kind.startswith("forced") else kind
        n0 = d["none"]["C"]
        full = d["full"]["C"] - n0
        for e, r in d.items():
            if e in ("none", "none_R"):
                continue
            base0 = d["none_R"]["C"] if e.startswith("RPOS") else n0
            agg[kk][e].append((r["C"] - base0, full, r["lmeY"] - (d["none_R"] if e.startswith("RPOS") else
                                                                  d["none"])["lmeY"],
                               r["lmeD"] - (d["none_R"] if e.startswith("RPOS") else d["none"])["lmeD"]))
    out = {}
    for kk, d in agg.items():
        out[kk] = {}
        for e, v in d.items():
            g = np.array([x[0] for x in v])
            f = np.array([x[1] for x in v])
            out[kk][e] = {"n": len(v), "mean_gain": float(g.mean()), "mean_full_gain": float(f.mean()),
                          "tf_recovery": float(g.sum() / f.sum()) if abs(f.sum()) > 1e-9 else None,
                          "d_lmeY": float(np.mean([x[2] for x in v])), "d_lmeD": float(np.mean([x[3] for x in v]))}
    res = {"task": task, "summary": out}
    write_json(results7(f"tf_eval_{task}.json"), res)
    return res


# ------------------------------------------------------------------------------------------------ dispatcher
def run_stage(st: str, model: Any, tok: Any, P7: dict, tasks: list[str]) -> None:
    import stages_c7 as C
    for task in tasks:
        t0 = time.time()
        if st == "targets":
            stage_targets(task, tok)
        elif st == "profile":
            if not results7(f"site_{task}.json").exists():
                stage_profile(model, tok, P7, task)
        elif st == "fit":
            if not results7(f"das_fits_{task}.json").exists():
                stage_fit(model, P7, task)
        elif st == "fitlight":
            if not results7(f"das_fits_{task}.json").exists():
                stage_fit(model, P7, task, light=True)
        elif st == "tfeval":
            stage_tfeval(model, P7, task)
        elif st == "fitly":
            if not results7(f"das_fits_ly_{task}.json").exists():
                stage_fit_ly(model, P7, task)
        elif st == "fitly3":
            if not results7(f"das_fits_ly_{task}.json").exists():
                stage_fit_ly(model, P7, task, with_rpos=False)
        elif st == "gen":
            C.stage_gen(model, tok, P7, task, fit="MAIN_LY")
        elif st == "genpilot":
            C.stage_gen(model, tok, P7, task, fit="MAIN", pilot=True)
        elif st == "genred":
            C.stage_gen(model, tok, P7, task, reduced=True, fit="MAIN_LY")
        elif st == "r":
            C.stage_r(model, tok, P7, task)
        elif st == "m":
            C.stage_m(model, P7, task)
        elif st == "mgen":
            C.stage_mgen(model, tok, P7, task)
        elif st == "seed2":
            C.stage_seed2(model, tok, P7, task)
        elif st == "randinit":
            del model
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            C.stage_randinit(None, P7, task)
            return
        else:
            raise ValueError(st)
        logger.info(f"stage {st} {task} done in {time.time() - t0:.0f}s")


# ------------------------------------------------------------------------------------------------ amendment: LME_Y fits
def stage_fit_ly(model: Any, P7: dict, task: str, with_rpos: bool = True) -> dict[str, Any]:
    """Amendment 1 (committed before any held-out generation): the committed contrastive objective rose to ~10x the
    full-state ceiling on validation (breakage of the default's likelihood). A second map is fitted with the bounded
    standard DAS objective, the log-mean-likelihood of the source's own programs (LME_Y), same map class, pairs,
    budget and seeds; its permuted-label twin gets the same budget. Both maps are evaluated in TF and generation."""
    T = load_targets(task)
    fits0 = read_json(results7(f"das_fits_{task}.json"))
    n_steps = fits0["n_steps_budget"]
    ctx = build_ctx(model, P7, task, T)
    ctx_val = build_ctx(model, P7, task, T, val=True)
    tr, va = pair_lists(task, T)
    seed = SEEDS["das_init"][task]
    t0 = time.time()
    main = fit_das(ctx, tr, va, seed, ctx_val=ctx_val, n_steps=n_steps, extend=75 if n_steps == 150 else 0,
                   log_name=f"{task}:MAIN_LY", objective="lmeY")
    perm = fits0["permutation"]["table"]
    trp, vap = pair_lists(task, T, perm)
    pf = fit_das(ctx, trp, vap, seed, ctx_val=ctx_val, n_steps=main["budget"], log_name=f"{task}:PERM_LY",
                 objective="lmeY")
    shas = {"MAIN_LY": save_map(task, "MAIN_LY", main["basis"], {k: v for k, v in main.items() if k != "basis"}),
            "PERM_LY": save_map(task, "PERM_LY", pf["basis"], {k: v for k, v in pf.items() if k != "basis"})}
    rf = None
    if with_rpos:
        ctx_r = build_ctx(model, P7, task, T, pos_kind="R")
        ctx_rv = build_ctx(model, P7, task, T, pos_kind="R", val=True)
        rf = fit_das(ctx_r, tr, va, seed, ctx_val=ctx_rv, n_steps=main["budget"], log_name=f"{task}:RPOS_LY",
                     objective="lmeY")
        shas["RPOS_LY"] = save_map(task, "RPOS_LY", rf["basis"], {k: v for k, v in rf.items() if k != "basis"})
        ctx_r.free()
        ctx_rv.free()
    p64 = torch.tensor(np.load(MAPS7 / f"{task}_natural_pc64.npy"))
    shas["PROJ64_LY"] = save_map(task, "PROJ64_LY", orthonormal_rows(main["basis"].float() @ p64.T @ p64), {})
    res = {"task": task, "objective": "LME_Y", "fits": {"MAIN_LY": {k: v for k, v in main.items() if k != "basis"},
                                                         "PERM_LY": {k: v for k, v in pf.items() if k != "basis"},
                                                         "RPOS_LY": ({k: v for k, v in rf.items() if k != "basis"}
                                                                     if rf else None)},
           "map_sha256": shas, "seconds": round(time.time() - t0, 1)}
    write_json(results7(f"das_fits_ly_{task}.json"), res)
    from commit7 import commit
    commit(f"amendment1_ly_{task}", {"reason": "contrastive validation gain ~10x the full-state ceiling (breakage); "
                                               "bounded LME_Y objective fitted as a second map before any held-out "
                                               "generation", "map_sha256": shas, "budget": main["budget"]})
    # TF evaluation of the LME_Y maps on the held-out pairs
    dev = ctx.dev
    maps = {nm: load_map(task, nm).to(dev) for nm in ("MAIN_LY", "PERM_LY", "PROJ64_LY")}
    rows = []
    with torch.no_grad():
        for (s, b, g, kind) in held_pairs(task, T):
            edits = [("none", None), ("full", "FULL")] + [(f"DASLY_k{k}", maps["MAIN_LY"][:k]) for k in RANKS]
            edits += [(f"PERMLY_k{k}", maps["PERM_LY"][:k]) for k in RANKS]
            edits += [(f"PROJLY_k{k}", maps["PROJ64_LY"][:k]) for k in RANKS]
            out = {}
            for c0 in range(2, len(edits), 8):
                chunk = edits[:2] + edits[c0:c0 + 8]
                rr = [{"none": True} if B is None else ({"src": s, "B": None} if isinstance(B, str) else
                                                         {"src": s, "B": B}) for _, B in chunk]
                o = ctx.contrast_rows(b, g, rr)
                for i, (nm, _) in enumerate(chunk):
                    if nm not in out or c0 == 2:
                        out[nm] = (float(o["C"][i]), float(o["lmeY"][i]), float(o["lmeD"][i]))
            for nm, (C, lY, lD) in out.items():
                rows.append({"task": task, "source": s, "base": b, "group": g, "kind": kind, "edit": nm, "C": C,
                             "lmeY": lY, "lmeD": lD})
    append_jsonl(ROOT / "data" / "tf_heldout_ly.jsonl", rows)
    s2 = summarize_tf(task + "_LY", rows)
    ctx.free()
    ctx_val.free()
    return s2
