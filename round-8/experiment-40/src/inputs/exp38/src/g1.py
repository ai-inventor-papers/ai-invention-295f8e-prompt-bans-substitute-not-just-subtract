#!/usr/bin/env python3
"""G1: a circuit for the fork margin m = logsumexp(z[B]) - z['visited'] at the last c* position.

G1-P (edge-level path patching on raw components): nodes = 272 attention heads (the head's slice of the o_proj input)
and 34 MLP outputs, each at a position class FORK (p_f), CSTAR (response positions 0-30), SPEC (task spec + chat tail)
or COND (the condition sentence). Pairs: clean = DFS-leaning twin variant, corrupt = BFS-leaning variant of the same
template (identical length), 10 pairs; plus forced-DFS (clean) vs forced-BFS (corrupt) F1-F5 (5 pairs). Screen =
attribution patching (grad of m x (corrupt - clean)); exact activation patching (noising: clean run, node <- corrupt;
denoising: corrupt run, node <- clean) for the top 40 by |AtP| plus 20 random nodes; edges = path patching
sender -> receiver for the top 15 nodes (pass 2: clean run, sender <- corrupt, every other head and MLP frozen at clean,
receivers' outputs recorded; pass 3: clean run with only the receiver <- recorded value) and sender -> logits.
VALIDATION (stage g1v, always in the real model): ABLATE (node <- mean over the opposite-class prompts at aligned
positions) and STEER (node <- own + 2 x (opposite mean - own mean)) on 24 prompts, against 50 random nodes matched on
write norm per node; exact sign-flip permutation tests, Holm; joint top-5/top-10 vs 50 matched random sets; then
generation arms (N = 30, CRN)."""

from __future__ import annotations

import itertools
import json
import time
from typing import Any

import numpy as np
import torch
from loguru import logger

from cfg import (DATA_DIR, HEAD_DIM, N_HEADS, N_LAYERS, RESULTS_DIR, STATES_DIR, TEMPLATE_IDS, read_json,
                 read_jsonl, sha256_file, slot_key7, write_json)

CLASSES = ("FORK", "CSTAR", "SPEC", "COND")


# ================================================================================================ prompts
def g1_prompts() -> list[dict[str, Any]]:
    """10 BFS-leaning + 10 DFS-leaning variants (2 + 2 per template, by y_v) and forced F1/F5 x {BFS, DFS}."""
    import fork7 as FK

    V = {v["vid"]: v for v in FK.variants()}
    ys = {v["vid"]: v["y"] for v in read_json(RESULTS_DIR / "yv.json")["variants"]}
    out = []
    for w in TEMPLATE_IDS:
        vs = sorted([vid for vid in V if V[vid]["template"] == w], key=lambda k: ys[k])
        for rank, vid in enumerate(vs[:2]):
            out.append(dict(V[vid], cls="dfs", kind="variant", y=ys[vid], pair_rank=rank))
        for rank, vid in enumerate(vs[::-1][:2]):
            out.append(dict(V[vid], cls="bfs", kind="variant", y=ys[vid], pair_rank=rank))
    for f in ("F1", "F5"):
        for mode in ("bfs", "dfs"):
            p = FK.forced(mode, f, 3)
            out.append(dict(p, cls=mode, kind="forced", vid=f"forced|{f}|{mode}"))
    for p in out:
        p["pos"] = FK.positions(p)
        p["n"] = p["P"] + 32
    return out


def g1_pairs(prompts: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """(clean index, corrupt index): same template, same rank; forced F1/F5 DFS vs BFS."""
    pairs = []
    for w in TEMPLATE_IDS:
        for rank in (0, 1):
            c = [i for i, p in enumerate(prompts) if p["kind"] == "variant" and p["template"] == w
                 and p["cls"] == "dfs" and p["pair_rank"] == rank]
            x = [i for i, p in enumerate(prompts) if p["kind"] == "variant" and p["template"] == w
                 and p["cls"] == "bfs" and p["pair_rank"] == rank]
            pairs.append((c[0], x[0]))
    for f in ("F1", "F5"):
        c = [i for i, p in enumerate(prompts) if p.get("vid") == f"forced|{f}|dfs"][0]
        x = [i for i, p in enumerate(prompts) if p.get("vid") == f"forced|{f}|bfs"][0]
        pairs.append((c, x))
    for c, x in pairs:
        assert prompts[c]["n"] == prompts[x]["n"], "pair lengths differ"
    return pairs


def forced_extra_pairs() -> list[tuple[dict, dict]]:
    """Forced-DFS vs forced-BFS for F2-F4 (equal-length display names), used only in path patching."""
    import fork7 as FK

    out = []
    for f in ("F2", "F3", "F4"):
        c, x = FK.forced("dfs", f, 3), FK.forced("bfs", f, 3)
        for p in (c, x):
            p["pos"] = FK.positions(p)
            p["n"] = p["P"] + 32
            p["vid"] = f"forced|{f}|{p['mode']}"
            p["cls"] = p["mode"]
            p["kind"] = "forced"
        assert c["n"] == x["n"]
        out.append((c, x))
    return out


# ================================================================================================ activations
class Acts:
    """Per prompt: z [34, n, 2048] and mlp_out [34, n, 2560] (bf16, CPU), clean margin m."""

    def __init__(self, z: torch.Tensor, mlp: torch.Tensor, m: float):
        self.z, self.mlp, self.m = z, mlp, m


@torch.no_grad()
def collect(run: Any, ids: list[int]) -> Acts:
    from gen7 import edit_hooks
    import fork7 as FK

    zs: dict[int, torch.Tensor] = {}
    ms: dict[int, torch.Tensor] = {}
    cap = {}
    for l in range(N_LAYERS):
        cap[("z", l)] = (lambda x, l=l: zs.__setitem__(l, x[0].to(torch.bfloat16).cpu()))
        cap[("mlp", l)] = (lambda x, l=l: ms.__setitem__(l, x[0].to(torch.bfloat16).cpu()))
    import engine as EG

    with edit_hooks(run.model, [], cap):
        out = run.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
    m = float(FK.margin(EG.lm_logits(run.model, out.last_hidden_state[0, -1])))
    return Acts(torch.stack([zs[l] for l in range(N_LAYERS)]), torch.stack([ms[l] for l in range(N_LAYERS)]), m)


def atp_grads(run: Any, ids: list[int]) -> tuple[torch.Tensor, torch.Tensor, float]:
    """Gradients of m w.r.t. every z and mlp_out (total derivatives; embedding output made to require grad)."""
    import engine as EG
    import fork7 as FK

    keep: dict[tuple[str, int], torch.Tensor] = {}
    hs = []
    emb = run.model.model.embed_tokens

    def emb_hook(m, inp, out):
        return out.detach().requires_grad_(True)
    hs.append(emb.register_forward_hook(emb_hook))
    for l in range(N_LAYERS):
        blk = run.model.model.layers[l]

        def pre(m, args, l=l):
            args[0].retain_grad()
            keep[("z", l)] = args[0]
        hs.append(blk.self_attn.o_proj.register_forward_pre_hook(pre))

        def post(m, inp, out, l=l):
            out.retain_grad()
            keep[("mlp", l)] = out
        hs.append(blk.mlp.register_forward_hook(post))
    try:
        with torch.enable_grad():
            out = run.model.model(input_ids=torch.tensor([ids], device="cuda"), use_cache=False)
            mm = FK.margin(EG.lm_logits(run.model, out.last_hidden_state[0, -1]))
            mm.backward()
    finally:
        for h in hs:
            h.remove()
    gz = torch.stack([keep[("z", l)].grad[0].float().cpu() for l in range(N_LAYERS)])
    gm = torch.stack([keep[("mlp", l)].grad[0].float().cpu() for l in range(N_LAYERS)])
    m = float(mm.detach())
    del keep, out
    torch.cuda.empty_cache()
    return gz, gm, m


# ================================================================================================ nodes
def all_nodes() -> list[tuple[str, int, int, str]]:
    """(kind 'head'|'mlp', layer, head (-1 for mlp), class)."""
    out = []
    for c in CLASSES:
        for l in range(N_LAYERS):
            for h in range(N_HEADS):
                out.append(("head", l, h, c))
            out.append(("mlp", l, -1, c))
    return out


def node_key(n: tuple) -> str:
    return f"{n[0]}|L{n[1]}|H{n[2]}|{n[3]}"


def node_vals(a: Acts, node: tuple, pos: list[int]) -> torch.Tensor:
    kind, l, h, _ = node
    if kind == "head":
        return a.z[l, pos, h * HEAD_DIM:(h + 1) * HEAD_DIM]
    return a.mlp[l, pos]


def make_edit(node: tuple, pos: list[int], fn) -> Any:
    from gen7 import Edit

    kind, l, h, _ = node
    if kind == "head":
        return Edit("z", l, pos, fn, head=h, name=node_key(node))
    return Edit("mlp", l, pos, fn, name=node_key(node))


def const_fn(val: torch.Tensor):
    v = val.float().to("cuda")
    return lambda x, r, v=v: v[None].expand(x.shape[0], -1, -1).clone()


def steer_fn(delta: torch.Tensor):
    d = delta.float().cuda()
    return lambda x, r, d=d: x + d[None]


@torch.no_grad()
def margins_rows(run: Any, ids: list[int], edits_per_row: list[list[Any]], q_min: int = 0,
                 max_tokens: int = 12000, relative: bool = True) -> list[float]:
    """Per row (prompt repeated, each row with its own edits): dm = m(row) - m(unedited base row of the same
    chunk), so bf16 batch-shape/path offsets cancel exactly (relative=False returns raw m). Edit positions are
    ABSOLUTE and >= q_min: the prefix ids[:q_min] is prefilled once and reused (suffix forward)."""
    from transformers.cache_utils import DynamicCache

    import engine as EG
    import fork7 as FK
    from gen7 import Edit, edit_hooks

    n = len(ids)
    s = n - q_min
    out: list[float] = []
    if q_min > 0:
        pre = EG.prefill_single(run.model, ids[:q_min], 1)
        kv = pre["kv"]
    R = max(1, min(64, max_tokens // max(s, 1), int(2.0e9 / max(1, (n * 34 * 2 * 4 * 256 * 2))))) - 1
    R = max(R, 1)
    for b0 in range(0, len(edits_per_row), R):
        chunk = [[]] + list(edits_per_row[b0:b0 + R])          # row 0 = unedited base row of this chunk
        B = len(chunk)
        row_edits = []
        for i, eds in enumerate(chunk):
            for e in eds:
                e2 = Edit(e.site, e.layer, (e.pos - q_min).tolist(), e.fn, head=e.head, name=e.name)
                row_edits.append((e2, torch.tensor([i], device="cuda")))
        cache = None
        if q_min > 0:
            cache = DynamicCache()
            for l, (K, V) in enumerate(kv):
                cache.update(K.expand(B, -1, -1, -1).contiguous(), V.expand(B, -1, -1, -1).contiguous(), l)
        inp = torch.tensor([ids[q_min:]], device="cuda").expand(B, -1).contiguous()
        pos = torch.arange(q_min, n, device="cuda")[None].expand(B, -1)
        with edit_hooks(run.model, row_edits):
            o = run.model.model(input_ids=inp, past_key_values=cache, position_ids=pos, use_cache=cache is not None)
        lg = EG.lm_logits(run.model, o.last_hidden_state[:, -1])
        mm = FK.margin(lg)
        out += (mm[1:] - mm[0]).tolist() if relative else mm[1:].tolist()
        del o, cache
    return out


# ================================================================================================ stage g1p
def stage_g1p(args: Any) -> None:
    import commit as CM
    import fork7 as FK
    from gen7 import Runner

    t0 = time.time()
    run = Runner()
    cs = FK.cstar()
    prompts = g1_prompts()
    pairs = g1_pairs(prompts)
    extra = forced_extra_pairs()
    # all prompts used in path patching: the 24 + the 6 extra forced
    pp = list(prompts)
    for c, x in extra:
        pp.append(c)
        pp.append(x)
        pairs.append((len(pp) - 2, len(pp) - 1))
    acts = []
    for p in pp:
        acts.append(collect(run, p["ids"] + cs))
    logger.info(f"g1p: activations for {len(pp)} prompts in {time.time() - t0:.0f}s; {len(pairs)} pairs")
    nodes = all_nodes()
    # ---------------- smoke test: patch everything corrupt -> corrupt m; patch nothing -> clean m
    c, x = pairs[0]
    ids = pp[c]["ids"] + cs
    allpos = list(range(len(ids)))
    eds = []
    for l in range(N_LAYERS):
        for h in range(N_HEADS):
            eds.append(make_edit(("head", l, h, "ALL"), allpos, const_fn(node_vals(acts[x], ("head", l, h, ""), allpos))))
        eds.append(make_edit(("mlp", l, -1, "ALL"), allpos, const_fn(node_vals(acts[x], ("mlp", l, -1, ""), allpos))))
    m_all, m_none = margins_rows(run, ids, [eds, []], relative=False)
    m_base_rel = margins_rows(run, ids, [eds])[0]
    smoke = {"m_clean": acts[c].m, "m_corrupt": acts[x].m, "m_patch_all": m_all, "m_patch_none": m_none,
             "all_reproduces_corrupt": abs(m_all - acts[x].m) < 0.05, "none_reproduces_clean": abs(m_none - acts[c].m) < 0.05,
             "dm_patch_all_vs_in_batch_base": m_base_rel, "total_effect_pair": acts[x].m - acts[c].m,
             "note": "raw batched margins differ from the batch-1 clean margin by a bf16 batch-shape offset; every "
                     "reported dm is measured against an unedited base row of the same chunk"}
    logger.info(f"g1p smoke: {smoke}")
    # ---------------- AtP screen
    atp = np.zeros((len(pairs), len(nodes)))
    for pi, (c, x) in enumerate(pairs):
        gz, gm, _ = atp_grads(run, pp[c]["ids"] + cs)
        dz = acts[x].z.float() - acts[c].z.float()
        dm = acts[x].mlp.float() - acts[c].mlp.float()
        pos = pp[c]["pos"]
        for j, nd in enumerate(nodes):
            kind, l, h, cl = nd
            ps = pos[cl]
            if not ps:
                continue
            if kind == "head":
                sl = slice(h * HEAD_DIM, (h + 1) * HEAD_DIM)
                atp[pi, j] = float((gz[l, ps, sl] * dz[l, ps, sl]).sum())
            else:
                atp[pi, j] = float((gm[l, ps] * dm[l, ps]).sum())
        del gz, gm, dz, dm
    atp_mean = atp.mean(0)
    order = np.argsort(-np.abs(atp_mean))
    top40 = [int(j) for j in order[:40]]
    rng = np.random.default_rng(2026)
    rest = [int(j) for j in order[40:] if abs(atp_mean[j]) > 0 or True]
    rand20 = [int(j) for j in rng.choice(rest, size=20, replace=False)]
    exact_set = top40 + rand20
    logger.info(f"g1p: AtP done ({time.time() - t0:.0f}s); top AtP {[node_key(nodes[j]) for j in top40[:8]]}")
    # ---------------- exact patching (noising and denoising) for 60 nodes x all pairs
    noise = np.zeros((len(pairs), len(exact_set)))
    denoise = np.zeros((len(pairs), len(exact_set)))
    for pi, (c, x) in enumerate(pairs):
        for direction, (run_i, src_i, store) in (("noise", (c, x, noise)), ("denoise", (x, c, denoise))):
            ids = pp[run_i]["ids"] + cs
            by_q: dict[int, list[tuple[int, list[Any]]]] = {}
            for jj, j in enumerate(exact_set):
                nd = nodes[j]
                ps = pp[run_i]["pos"][nd[3]]
                if not ps:
                    continue
                e = make_edit(nd, ps, const_fn(node_vals(acts[src_i], nd, ps)))
                by_q.setdefault(min(ps), []).append((jj, [e]))
            base = acts[run_i].m
            for q, items in by_q.items():
                ms = margins_rows(run, ids, [it[1] for it in items], q_min=q)
                for (jj, _), mv in zip(items, ms):
                    store[pi, jj] = mv
                _ = base
    logger.info(f"g1p: exact patching done ({time.time() - t0:.0f}s)")
    from scipy.stats import pearsonr, spearmanr

    atp_e = atp[:, exact_set]
    atp_err = {"pearson": float(pearsonr(atp_e.ravel(), noise.ravel()).statistic),
               "spearman": float(spearmanr(atp_e.ravel(), noise.ravel()).statistic),
               "mean_abs_err": float(np.abs(atp_e - noise).mean()),
               "mean_abs_exact": float(np.abs(noise).mean())}
    eff = noise.mean(0)
    rank = np.argsort(-np.abs(eff))
    exact_rows = [{"node": node_key(nodes[exact_set[jj]]), "in_top40_atp": jj < 40,
                   "atp_mean": float(atp_mean[exact_set[jj]]), "noise_mean": float(noise[:, jj].mean()),
                   "noise_sd": float(noise[:, jj].std()), "denoise_mean": float(denoise[:, jj].mean()),
                   "noise_sign_consistency": float(np.mean(np.sign(noise[:, jj]) == np.sign(noise[:, jj].mean()))),
                   "noise_per_pair": noise[:, jj].tolist()} for jj in rank]
    total = float(np.mean([acts[x].m - acts[c].m for c, x in pairs]))
    # ---------------- edges among the top 15 nodes by exact effect
    top15 = [exact_set[jj] for jj in rank[:15]]
    edges = edge_patching(run, pp, acts, pairs, nodes, top15, cs)
    keep_thr = 0.05 * abs(total)
    edge_rows = [e for e in edges if abs(e["dm_mean"]) >= keep_thr]
    # ---------------- node selection for validation (top 10 by |mean noising effect|), random matched sets
    top10 = [exact_set[jj] for jj in rank[:10]]
    sel = selection(run, prompts, acts[:len(prompts)], nodes, top10)
    res = {"n_prompts_validation": len(prompts), "n_pairs": len(pairs), "smoke": smoke,
           "pairs": [{"clean": pp[c]["vid"], "corrupt": pp[x]["vid"], "m_clean": acts[c].m, "m_corrupt": acts[x].m}
                     for c, x in pairs],
           "total_effect_mean": total, "atp_error_vs_exact": atp_err, "exact": exact_rows,
           "atp_top40": [{"node": node_key(nodes[j]), "atp_mean": float(atp_mean[j])} for j in top40],
           "atp_class_mass": {cl: float(np.abs(atp_mean[[j for j, n in enumerate(nodes) if n[3] == cl]]).sum())
                              for cl in CLASSES},
           "edges_kept": edge_rows, "edges_all": edges, "edge_threshold": keep_thr,
           "top10": [node_key(nodes[j]) for j in top10], "seconds": time.time() - t0}
    write_json(RESULTS_DIR / "g1_pathpatch.json", res)
    torch.save({"selection": sel, "prompts": [{k: p[k] for k in ("vid", "cls", "kind", "template", "P", "spec_start",
                                                                    "seg_start", "ids")} for p in prompts]},
               STATES_DIR / "g1_selection.pt")
    c2 = CM.commit("commit2b", {"top10_nodes": [node_key(nodes[j]) for j in top10],
                               "selection_sha256": sha256_file(STATES_DIR / "g1_selection.pt"),
                               "random_matched_sets": sel["random_keys"], "joint_random_sets": sel["joint_keys"],
                               "matching": sel["matching"], "joint_total_write_norm": sel["joint_total_write_norm"],
                               "rules": {"ABLATE": "node <- mean over the 10 opposite-class prompts at aligned positions "
                                                   "(COND: same-template opposite-class prompts)",
                                         "STEER": "node <- own + 2 x (opposite-class mean - own-class mean)",
                                         "random_null": "50 random components of the same type and position class with "
                                                        "write norm within +/-25% (widened to +/-50%, then any type)"},
                               "generation_arms": ["twin", "top5_ablate_bfs", "rand5_ablate_bfs", "top5_steer_bfs",
                                                   "rand5_steer_bfs", "top10_ablate_bfs", "top5_ablate_dfs"]})
    logger.info(f"g1p done in {time.time() - t0:.0f}s; commit2 {c2['sha256'][:12]}; top10 {res['top10']}")
    run.free()


@torch.no_grad()
def edge_patching(run: Any, pp: list[dict], acts: list[Acts], pairs: list[tuple[int, int]], nodes: list[tuple],
                  senders: list[int], cs: list[int]) -> list[dict[str, Any]]:
    """Path patching sender -> receiver (top nodes downstream) and sender -> logits, averaged over pairs."""
    import engine as EG
    import fork7 as FK
    from gen7 import Edit, edit_hooks

    def order_key(nd: tuple) -> tuple[int, int]:
        return (nd[1], 0 if nd[0] == "head" else 1)

    acc: dict[tuple[int, int], list[float]] = {}
    acc_logit: dict[int, list[float]] = {}
    for c, x in pairs:
        ids = pp[c]["ids"] + cs
        n = len(ids)
        pos = pp[c]["pos"]
        Zc = acts[c].z.cuda()
        Mc = acts[c].mlp.cuda()
        # pass 2: one row per sender; every head/MLP frozen at clean, the sender's class positions <- corrupt;
        # each receiver's computed value is recorded before the freeze replaces it
        sender_nodes_all = [None] + [nodes[j] for j in senders]   # row 0 = no sender (all frozen at clean)
        S = len(sender_nodes_all)
        hooks = []
        cap_z: dict[int, torch.Tensor] = {}
        cap_m: dict[int, torch.Tensor] = {}
        Zx = acts[x].z.cuda()
        Mx = acts[x].mlp.cuda()
        sender_nodes = sender_nodes_all
        for l in range(N_LAYERS):
            blk = run.model.model.layers[l]

            def zpre(m, args, l=l):
                xv = args[0]
                cap_z[l] = xv.detach().clone()
                new = Zc[l][None].expand(xv.shape[0], -1, -1).clone().to(xv.dtype)
                for r, nd in enumerate(sender_nodes):
                    if nd is not None and nd[0] == "head" and nd[1] == l:
                        ps = torch.tensor(pos[nd[3]], device="cuda")
                        sl = slice(nd[2] * HEAD_DIM, (nd[2] + 1) * HEAD_DIM)
                        new[r, ps, sl] = Zx[l][ps, sl].to(xv.dtype)
                return (new,) + tuple(args[1:])

            def mpost(m, inp, out, l=l):
                cap_m[l] = out.detach().clone()
                new = Mc[l][None].expand(out.shape[0], -1, -1).clone().to(out.dtype)
                for r, nd in enumerate(sender_nodes):
                    if nd is not None and nd[0] == "mlp" and nd[1] == l:
                        ps = torch.tensor(pos[nd[3]], device="cuda")
                        new[r, ps] = Mx[l][ps].to(out.dtype)
                return new
            hooks.append(blk.self_attn.o_proj.register_forward_pre_hook(zpre))
            hooks.append(blk.mlp.register_forward_hook(mpost))
        try:
            inp = torch.tensor([ids], device="cuda").expand(S, -1).contiguous()
            o = run.model.model(input_ids=inp, use_cache=False)
            m2 = FK.margin(EG.lm_logits(run.model, o.last_hidden_state[:, -1])).tolist()
        finally:
            for h in hooks:
                h.remove()
        # m of the fully frozen clean run (no sender) for the direct-path baseline = clean m (frozen == clean)
        for r, j in enumerate(senders):
            acc_logit.setdefault(j, []).append(m2[r + 1] - m2[0])
        # pass 3: clean run, only the receiver <- its value recorded in pass 2 (row r = sender r)
        items = []
        for r, js in enumerate(senders):
            snd = nodes[js]
            for jr in senders:
                rcv = nodes[jr]
                if jr == js:
                    continue
                if order_key(rcv) <= order_key(snd):
                    continue
                ps = pos[rcv[3]]
                if not ps:
                    continue
                if rcv[0] == "head":
                    val = cap_z[rcv[1]][r + 1, ps, rcv[2] * HEAD_DIM:(rcv[2] + 1) * HEAD_DIM]
                else:
                    val = cap_m[rcv[1]][r + 1, ps]
                items.append(((js, jr), min(ps), make_edit(rcv, ps, const_fn(val))))
        del cap_z, cap_m
        by_q: dict[int, list] = {}
        for key, q, e in items:
            by_q.setdefault(q, []).append((key, e))
        for q, its in by_q.items():
            ms = margins_rows(run, ids, [[e] for _, e in its], q_min=q)
            for (key, _), mv in zip(its, ms):
                acc.setdefault(key, []).append(mv)
        del Zc, Mc, Zx, Mx
        torch.cuda.empty_cache()
    out = []
    for (js, jr), v in acc.items():
        out.append({"sender": node_key(nodes[js]), "receiver": node_key(nodes[jr]), "dm_mean": float(np.mean(v)),
                    "dm_sd": float(np.std(v)), "n_pairs": len(v)})
    for js, v in acc_logit.items():
        out.append({"sender": node_key(nodes[js]), "receiver": "logits(m)", "dm_mean": float(np.mean(v)),
                    "dm_sd": float(np.std(v)), "n_pairs": len(v)})
    return sorted(out, key=lambda e: -abs(e["dm_mean"]))


def write_norm(run: Any, a: Acts, node: tuple, pos: list[int]) -> float:
    kind, l, h, _ = node
    if kind == "head":
        Wo = run.model.model.layers[l].self_attn.o_proj.weight[:, h * HEAD_DIM:(h + 1) * HEAD_DIM].float()
        v = a.z[l, pos, h * HEAD_DIM:(h + 1) * HEAD_DIM].float().cuda()
        return float((v @ Wo.T).norm(dim=-1).mean())
    return float(a.mlp[l, pos].float().norm(dim=-1).mean())


def selection(run: Any, prompts: list[dict], acts: list[Acts], nodes: list[tuple], top10: list[int]) -> dict[str, Any]:
    """Write norms (mean over 6 prompts) of every node; 50 random nodes per top node of the same type and position
    class with write norm within +/-25% (widened to +/-50%, then any type by nearest norm); 50 joint random sets."""
    wn = {}
    for nd in nodes:
        ok = [i for i, p in enumerate(prompts) if p["pos"][nd[3]]][:6]
        wn[node_key(nd)] = float(np.mean([write_norm(run, acts[i], nd, prompts[i]["pos"][nd[3]]) for i in ok]))
    tk = [node_key(nodes[j]) for j in top10]
    rng = np.random.default_rng(7)
    rand_sets: dict[str, list[str]] = {}
    widen = {}
    for j in top10:
        nd = nodes[j]
        k = node_key(nd)
        pool = [n for n in nodes if n[3] == nd[3] and n[0] == nd[0] and node_key(n) not in tk]
        tol = 0.25
        cand = [n for n in pool if abs(wn[node_key(n)] - wn[k]) <= tol * wn[k]]
        if len(cand) < 50:
            tol = 0.5
            cand = [n for n in pool if abs(wn[node_key(n)] - wn[k]) <= tol * wn[k]]
        if len(cand) < 50:
            pool = [n for n in nodes if n[3] == nd[3] and node_key(n) not in tk]
            cand = sorted(pool, key=lambda n: abs(wn[node_key(n)] - wn[k]))[:50]
            tol = None
        widen[k] = {"tolerance": tol, "n_candidates": len(cand), "write_norm": wn[k]}
        pick = rng.choice(len(cand), size=min(50, len(cand)), replace=False)
        rand_sets[k] = [node_key(cand[i]) for i in pick]
    joint = {}
    for size in (5, 10):
        joint[str(size)] = [[rand_sets[tk[i]][(s_ * 7 + i) % len(rand_sets[tk[i]])] for i in range(size)]
                            for s_ in range(50)]
    jn = {sz: {"top": float(sum(wn[k] for k in tk[:int(sz)])),
               "random_mean": float(np.mean([sum(wn[x] for x in st) for st in joint[sz]]))} for sz in joint}
    return {"top10": tk, "random_keys": rand_sets, "joint_keys": joint, "write_norms": wn, "matching": widen,
            "joint_total_write_norm": jn}


class MeanCache:
    """Class means of node activations at aligned positions (non-COND classes are prompt-independent)."""

    def __init__(self, acts: list[Acts], prompts: list[dict]):
        self.acts, self.prompts, self.c = acts, prompts, {}

    def get(self, idx: list[int], node: tuple, ref: dict) -> torch.Tensor | None:
        key = (node_key(node), tuple(idx), ref["template"] if node[3] == "COND" else None,
               ref["P"] if node[3] == "COND" else None)
        if key not in self.c:
            v = class_mean(self.acts, self.prompts, idx, node, ref)
            self.c[key] = None if v is None else v.cuda()
        return self.c[key]


# ================================================================================================ stage g1v
def class_mean(acts: list[Acts], prompts: list[dict], idx: list[int], node: tuple, ref: dict) -> torch.Tensor:
    """Mean of the node's activation over prompts idx at positions aligned to prompt `ref`."""
    import fork7 as FK

    cl = node[3]
    vals = []
    for i in idx:
        p = prompts[i]
        if cl == "COND":
            if p["template"] != ref["template"] or p["P"] != ref["P"]:
                continue
            ps = p["pos"][cl]
        else:
            off = FK.offsets_from_end(ref, cl)
            L = p["P"] + 32
            ps = [L - 1 - o for o in off]
        vals.append(node_vals(acts[i], node, ps).float())
    if not vals:
        return None
    return torch.stack(vals).mean(0)


def stage_g1v(args: Any) -> None:
    import fork7 as FK
    from gen7 import Runner

    t0 = time.time()
    pp_res = read_json(RESULTS_DIR / "g1_pathpatch.json")
    run = Runner()
    cs = FK.cstar()
    prompts = g1_prompts()
    acts = [collect(run, p["ids"] + cs) for p in prompts]
    nodes = all_nodes()
    key2node = {node_key(n): n for n in nodes}
    sel = torch.load(STATES_DIR / "g1_selection.pt")["selection"]
    top10 = [key2node[k] for k in sel["top10"]]
    rand_sets = sel["random_keys"]
    joint = {int(k): v for k, v in sel["joint_keys"].items()}
    widen_log = sel["matching"]
    wn = sel["write_norms"]
    mc = MeanCache(acts, prompts)
    bfs_idx = [i for i, p in enumerate(prompts) if p["cls"] == "bfs" and p["kind"] == "variant"]
    dfs_idx = [i for i, p in enumerate(prompts) if p["cls"] == "dfs" and p["kind"] == "variant"]
    fb_idx = [i for i, p in enumerate(prompts) if p["cls"] == "bfs" and p["kind"] == "forced"]
    fd_idx = [i for i, p in enumerate(prompts) if p["cls"] == "dfs" and p["kind"] == "forced"]

    def opp_own(i: int) -> tuple[list[int], list[int]]:
        p = prompts[i]
        if p["kind"] == "forced":
            return (fd_idx, fb_idx) if p["cls"] == "bfs" else (fb_idx, fd_idx)
        return (dfs_idx, bfs_idx) if p["cls"] == "bfs" else (bfs_idx, dfs_idx)

    def edits_for(i: int, nds: list[tuple], mode: str) -> list[Any] | None:
        p = prompts[i]
        opp, own = opp_own(i)
        eds = []
        for nd in nds:
            ps = p["pos"][nd[3]]
            if not ps:
                continue
            mo = mc.get(opp, nd, p)
            if mo is None:
                continue
            if mode == "ablate":
                eds.append(make_edit(nd, ps, const_fn(mo)))
            else:
                mw = mc.get(own, nd, p)
                if mw is None:
                    continue
                eds.append(make_edit(nd, ps, steer_fn(2.0 * (mo - mw))))
        return eds

    rows = []
    for i, p in enumerate(prompts):
        ids = p["ids"] + cs
        sign = -1.0 if p["cls"] == "bfs" else 1.0           # oriented toward the opposite class
        jobs = []                                          # (tag, edits)
        for mode in ("ablate", "steer"):
            for nd in top10:
                k = node_key(nd)
                jobs.append(((mode, k, "node"), edits_for(i, [nd], mode)))
                for rk in rand_sets[k]:
                    jobs.append(((mode, k, rk), edits_for(i, [key2node[rk]], mode)))
            for size in (5, 10):
                jobs.append(((mode, f"joint{size}", "node"), edits_for(i, top10[:size], mode)))
                for s, st in enumerate(joint[size]):
                    jobs.append(((mode, f"joint{size}", f"rand{s}"), edits_for(i, [key2node[x] for x in st], mode)))
        by_q: dict[int, list] = {}
        for tag, eds in jobs:
            q = min(int(e.pos.min()) for e in eds) if eds else len(ids) - 1
            by_q.setdefault(q, []).append((tag, eds))
        res_i = {}
        for q, items in sorted(by_q.items()):
            ms = margins_rows(run, ids, [e for _, e in items], q_min=q)
            for (tag, _), mv in zip(items, ms):
                res_i[tag] = sign * mv
        rows.append({"prompt": p["vid"], "cls": p["cls"], "kind": p["kind"], "m": acts[i].m, "res": res_i})
        logger.info(f"g1v prompt {i + 1}/{len(prompts)} ({len(jobs)} rows) {time.time() - t0:.0f}s")
    out = validation_stats(rows, top10, rand_sets, joint)
    out.update({"write_norms_top10": {node_key(n): wn[node_key(n)] for n in top10}, "matching": widen_log,
                "seconds": time.time() - t0})
    write_json(RESULTS_DIR / "g1_validation.json", out)
    torch.save({"rows": rows, "rand_sets": rand_sets, "joint": joint}, STATES_DIR / "g1_validation_rows.pt")
    write_json(RESULTS_DIR / "g1_validation_rows.json", {"rows": [{"prompt": r["prompt"], "cls": r["cls"],
                                                                     "kind": r["kind"], "m": r["m"],
                                                                     "res": {"|".join(k): v for k, v in r["res"].items()}}
                                                                    for r in rows]})
    run.free()


def sign_flip_p(d: np.ndarray) -> float:
    """Exact one-sided sign-flip permutation p for mean(d) > 0 (all 2^n sign patterns, n <= 20)."""
    n = len(d)
    obs = d.mean()
    signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)[None]) & 1) * 2 - 1
    null = (signs * d[None]).mean(1)
    return float((null >= obs - 1e-12).mean())


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = np.zeros(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * ps[i])
        adj[i] = min(1.0, run)
    return adj.tolist()


def validation_stats(rows: list[dict], top10: list[tuple], rand_sets: dict, joint: dict) -> dict[str, Any]:
    var_rows = [r for r in rows if r["kind"] == "variant"]
    out: dict[str, Any] = {"per_node": {}, "joint": {}}
    for mode in ("ablate", "steer"):
        ps, recs = [], []
        for nd in top10:
            k = node_key(nd)
            d, dnode, frac95 = [], [], []
            for r in var_rows:
                v = r["res"].get((mode, k, "node"))
                rv = [r["res"].get((mode, k, rk)) for rk in rand_sets[k]]
                rv = [x for x in rv if x is not None]
                if v is None or not rv:
                    continue
                d.append(v - float(np.mean(rv)))
                dnode.append(v)
                frac95.append(v > np.percentile(rv, 95))
            d = np.array(d)
            p = sign_flip_p(d) if len(d) else 1.0
            ps.append(p)
            forced = [r["res"].get((mode, k, "node")) for r in rows if r["kind"] == "forced"]
            recs.append({"node": k, "n": int(len(d)), "mean_d": float(d.mean()) if len(d) else None,
                         "median_d": float(np.median(d)) if len(d) else None, "p_sign_flip": p,
                         "mean_dm_node_oriented": float(np.mean(dnode)) if dnode else None,
                         "frac_prompts_above_null_p95": float(np.mean(frac95)) if frac95 else None,
                         "forced_prompts_dm_oriented": forced, "d_per_prompt": d.tolist()})
        adj = holm(ps)
        for rec, a in zip(recs, adj):
            rec["p_holm"] = a
        jres = {}
        for size in (5, 10):
            node_med = np.median([r["res"][(mode, f"joint{size}", "node")] for r in var_rows])
            rmeds = [np.median([r["res"][(mode, f"joint{size}", f"rand{s}")] for r in var_rows]) for s in range(50)]
            jres[size] = {"median_node_set": float(node_med), "median_random_sets": [float(x) for x in rmeds],
                          "frac_random_beaten": float(np.mean(np.array(rmeds) < node_med))}
        claim_joint5 = jres[5]["frac_random_beaten"] >= 0.95
        for rec in recs:
            rec["NODE_CLAIM"] = bool(rec["p_holm"] < 0.05 and (rec["median_d"] or 0) > 0 and claim_joint5)
        out["per_node"][mode] = recs
        out["joint"][mode] = jres
    out["n_node_claims"] = {m: sum(r["NODE_CLAIM"] for r in out["per_node"][m]) for m in out["per_node"]}
    out["distributed_circuit"] = {m: bool(out["joint"][m][5]["frac_random_beaten"] >= 0.95 and
                                          out["n_node_claims"][m] == 0) for m in out["per_node"]}
    return out


# ================================================================================================ stage g1gen
def stage_g1gen(args: Any) -> None:
    """Generation arms (N = 30 per arm; twin W1-W5 x 6 slots; prompt + c* prefilled; T = 1)."""
    import fork7 as FK
    from gen7 import Runner

    assert (STATES_DIR.parent.parent / "predictions" / "commit2b.json").exists(), "COMMIT #2b must precede G1 generation"
    pp_res = read_json(RESULTS_DIR / "g1_pathpatch.json")
    val = read_json(RESULTS_DIR / "g1_validation.json")
    run = Runner()
    cs = FK.cstar()
    prompts = g1_prompts()
    acts = [collect(run, p["ids"] + cs) for p in prompts]
    nodes = all_nodes()
    key2node = {node_key(n): n for n in nodes}
    sel = torch.load(STATES_DIR / "g1_selection.pt")["selection"]
    top = [key2node[k] for k in sel["top10"]]
    rand5 = [key2node[sel["random_keys"][node_key(nd)][0]] for nd in top[:5]]
    mc = MeanCache(acts, prompts)
    bfs_idx = [i for i, p in enumerate(prompts) if p["cls"] == "bfs" and p["kind"] == "variant"]
    dfs_idx = [i for i, p in enumerate(prompts) if p["cls"] == "dfs" and p["kind"] == "variant"]
    raw = DATA_DIR / "raw_g1gen.jsonl"
    done = {r["row_id"] for r in read_jsonl(raw)}
    for w in TEMPLATE_IDS:
        tw = dict(FK.twin(w))
        tw["pos"] = FK.positions(tw)
        tw["template"] = w
        ids = tw["ids"] + cs

        def eds(nds: list[tuple], mode: str, toward: str) -> list[Any]:
            tgt_idx, other_idx = (bfs_idx, dfs_idx) if toward == "bfs" else (dfs_idx, bfs_idx)
            out = []
            for nd in nds:
                ps = tw["pos"][nd[3]]
                if not ps:
                    continue
                mt = mc.get(tgt_idx, nd, tw)
                if mt is None:
                    continue
                if mode == "ablate":
                    out.append(make_edit(nd, ps, const_fn(mt)))
                else:
                    mo = mc.get(other_idx, nd, tw)
                    if mo is None:
                        continue
                    out.append(make_edit(nd, ps, steer_fn(2.0 * (mt - mo))))
            return out
        arms = {"twin": [], "top5_ablate_bfs": eds(top[:5], "ablate", "bfs"),
                "rand5_ablate_bfs": eds(rand5, "ablate", "bfs"), "top5_steer_bfs": eds(top[:5], "steer", "bfs"),
                "rand5_steer_bfs": eds(rand5, "steer", "bfs"), "top10_ablate_bfs": eds(top[:10], "ablate", "bfs"),
                "top5_ablate_dfs": eds(top[:5], "ablate", "dfs")}
        rows = []
        for arm, e in arms.items():
            for k in range(6):
                rid = f"g1|{arm}|{w}|{k}"
                if rid in done:
                    continue
                rows.append({"row_id": rid, "ukey": slot_key7("G1", w, k), "edits": e,
                             "meta": {"part": "G1", "cell": arm, "arm": arm, "template": w, "slot": k}})
        if rows:
            run.run_cell(ids, cs, rows, raw, f"G1:{w}")
    run.free()
    _ = (val, itertools, json)
