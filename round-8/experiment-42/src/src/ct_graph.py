#!/usr/bin/env python3
"""G1-T (timed attempt): circuit-tracer attribution graphs for the fork margin on Gemma Scope 2 per-layer transcoders
(mwhanna/gemma-scope-2-4b-it, transcoder_all/width_16k_l0_big_affine, nnsight backend, bf16).

Runs in the isolated .venv_ct (circuit-tracer pinned at a commit), so its transformers/nnsight pins cannot change the
main engine; data are exchanged through files. Target = the linearised fork margin
m_lin = sum_{t in B} w_t z_t - z_visited with w = softmax(z[B]) on the clean run, given as one CustomTarget direction
(attribution is linear in the target, so this equals combining the individual logit rows with weights (w_t, -1)).
Per prompt: replacement and completeness scores, the error-node share of total influence on the target, the number of
active features and pruned nodes, and the top feature nodes with their position class. Results are written after
every prompt, so a timeout keeps what finished.
Usage: .venv_ct/bin/python src/ct_graph.py <input.json> <output.json>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch


def main() -> None:
    inp = json.loads(Path(sys.argv[1]).read_text())
    out_path = Path(sys.argv[2])
    res: dict = {"status": "starting", "t_start": time.time(), "prompts": [], "config": inp["config"]}

    def dump() -> None:
        out_path.write_text(json.dumps(res, indent=1))

    t0 = time.time()
    try:
        from circuit_tracer import ReplacementModel, attribute
        from circuit_tracer.attribution.targets import CustomTarget
        from circuit_tracer.graph import compute_graph_scores, compute_node_influence, prune_graph, normalize_matrix

        rm = ReplacementModel.from_pretrained(inp["config"]["model"], inp["config"]["transcoders"], backend="nnsight",
                                              dtype=torch.bfloat16, lazy_decoder=True,
                                              lazy_encoder=bool(inp["config"].get("lazy_encoder", False)))
        res["load_seconds"] = time.time() - t0
        res["vram_after_load_gb"] = torch.cuda.memory_allocated() / 1e9
        res["status"] = "loaded"
        dump()
    except Exception as e:  # noqa: BLE001 - the attempt is timed; any failure is the reported outcome
        res["status"] = f"load_failed: {type(e).__name__}: {str(e)[:500]}"
        dump()
        return
    B, D = inp["B"], inp["D"]
    W_U = rm.unembed_weight if hasattr(rm, "unembed_weight") else None
    for p in inp["prompts"]:
        t1 = time.time()
        rec = {"vid": p["vid"], "cls": p["cls"]}
        try:
            ids = torch.tensor(p["ids"], dtype=torch.long)
            logits, acts = rm.get_activations(ids)
            z = logits[0, -1].float() if logits.dim() == 3 else logits[-1].float()
            m_rep = float(torch.logsumexp(z[B], 0) - z[D[0]])
            rec["m_replacement_with_errors"] = m_rep
            rec["m_real_main_engine"] = p["m_real"]
            rec["sanity_abs_diff"] = abs(m_rep - p["m_real"])
            w = torch.softmax(z[B], 0)
            # unembedding direction of the linearised margin
            if W_U is None:
                lm = rm._resolve_attr(rm, "lm_head") if hasattr(rm, "_resolve_attr") else None
                Wt = lm.weight if lm is not None else rm._model.lm_head.weight
            else:
                Wt = W_U
            Wt = Wt.detach()
            if Wt.shape[0] != z.shape[0]:
                Wt = Wt.T
            vec = (w.to(Wt.device, Wt.dtype)[:, None] * Wt[B]).sum(0) - Wt[D[0]]
            target = [CustomTarget(token_str="m_lin", prob=1.0, vec=vec.float())]
            g = attribute(ids, rm, attribution_targets=target, batch_size=inp["config"]["batch_size"],
                          max_feature_nodes=inp["config"]["max_feature_nodes"], offload="cpu", verbose=False)
            rep, comp = compute_graph_scores(g)
            pr = prune_graph(g, node_threshold=0.8, edge_threshold=0.98)
            n_logits = len(g.logit_targets)
            n_tok = len(g.input_tokens)
            n_feat = len(g.selected_features)
            err_s, err_e = n_feat, n_feat + n_tok * g.cfg.n_layers
            lw = torch.zeros(g.adjacency_matrix.shape[0], device=g.adjacency_matrix.device)
            lw[-n_logits:] = g.logit_probabilities
            infl = compute_node_influence(g.adjacency_matrix, lw)
            tot = float(infl[:err_e + n_tok].abs().sum())
            rec.update({"replacement_score": rep, "completeness_score": comp,
                        "error_node_share_of_influence": float(infl[err_s:err_e].abs().sum()) / max(tot, 1e-12),
                        "n_active_features": int(len(g.active_features)), "n_selected_features": n_feat,
                        "n_pruned_nodes_kept": int(pr.node_mask.sum())})
            fi = infl[:n_feat]
            top = torch.argsort(fi.abs(), descending=True)[:40]
            feats = []
            for j in top.tolist():
                layer, pos, fid = [int(x) for x in g.active_features[g.selected_features[j]].tolist()]
                feats.append({"layer": layer, "pos": pos, "feature": fid, "influence": float(fi[j]),
                              "activation": float(g.activation_values[j]),
                              "pos_class": p["pos_class"].get(str(pos), "OTHER")})
            rec["top_features"] = feats
            mass = {}
            for j in range(n_feat):
                pos = int(g.active_features[g.selected_features[j]][1])
                c = p["pos_class"].get(str(pos), "OTHER")
                mass[c] = mass.get(c, 0.0) + float(fi[j].abs())
            rec["feature_influence_by_pos_class"] = mass
            del g
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {str(e)[:500]}"
        rec["seconds"] = time.time() - t1
        rec["vram_peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        res["prompts"].append(rec)
        res["status"] = "running"
        dump()
        torch.cuda.empty_cache()
        if "error" in rec and "out of memory" in rec["error"].lower():
            res["status"] = "oom"
            dump()
            return
    res["status"] = "done"
    res["total_seconds"] = time.time() - t0
    dump()
    _ = normalize_matrix


if __name__ == "__main__":
    main()
