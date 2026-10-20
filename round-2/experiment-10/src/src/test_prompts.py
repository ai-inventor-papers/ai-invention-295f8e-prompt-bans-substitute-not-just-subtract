#!/usr/bin/env python3
"""T2 prompt tests -> results/tests_prompts.json, plus results/rendered_examples.json and results/model_record.json.

- rebuilt prompt TEXT equals exp1's prompts/conditions.json wherever the template and the display name are shared
  (baseline segments, baseline_empty, listall, forced k0-4, free-form);
- every rendered prompt has one BOS at index 0, R = the two-newline token after <|end_header_id|>, 'Today Date: 26 Jul
  2024' (asserted in src/config.build), identical ids[spec_start:] across all conditions of a task;
- ban and neutral twins have equal total length and identical suffix for every X, w, h (and nonce / two-step);
- the token ids vLLM sampled from equal the ids HF scored (prompt sha256 per condition).
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd

from src.ws import CANON, FRLP_DIR, DATA, RESULTS, model_path, read_jsonl, write_json
from src import config as K
from loguru import logger


@logger.catch(reraise=True)
def main() -> None:
    import common as C  # canon

    conds = json.loads((CANON / "prompts" / "conditions.json").read_text())
    out: dict = {"conditions_json": {"match": 0, "mismatch": 0, "examples_mismatch": [], "compared": []}}
    for task in K.TASKS:
        cj = conds["tasks"][task]["conditions"]
        same_name = {m for m in K.MODES[task] if K.DISPLAY[task][m] == C.CATALOGUE[task][m]}
        pairs = [(f"baseline:{i}", K.p_baseline(task, i)["text"], cj["baseline"][i]["prompt"]) for i in range(5)]
        pairs.append(("baseline_empty", K.p_baseline_empty(task)["text"], cj["baseline_empty"][0]["prompt"]))
        if same_name == set(K.MODES[task]):
            pairs += [(f"listall:{p}", K.p_listall(task, p)["text"], cj["listall"][p]["prompt"]) for p in range(5)]
        for m in sorted(same_name):
            pairs += [(f"forced:{m}:{k}", K.p_forced(task, m, k)["text"], cj[f"forced:{m}"][k]["prompt"]) for k in range(5)]
            pairs.append((f"free:{m}", K.p_free(task, m)["text"], conds["tasks"][task]["elicit_free"][m]["prompt"]))
        for name, mine, theirs in pairs:
            ok = mine == theirs
            out["conditions_json"]["match" if ok else "mismatch"] += 1
            out["conditions_json"]["compared"].append(f"{task}:{name}")
            if not ok and len(out["conditions_json"]["examples_mismatch"]) < 5:
                out["conditions_json"]["examples_mismatch"].append({"cond": f"{task}:{name}", "mine": mine[:200], "exp1": theirs[:200]})
    # structure checks over every matrix condition
    sel = json.loads((RESULTS / "selections.json").read_text())
    struct = {}
    for task in K.TASKS:
        d, s = sel[f"{task}_default"], sel[f"{task}_substitute"]["s_star"]
        ps = [K.p_baseline(task, i) for i in range(5)] + [K.p_baseline_empty(task), K.p_novelty(task)]
        ps += [K.p_listall(task, p) for p in range(5)]
        twins = []
        for x in K.MODES[task]:
            for w in K.WS_:
                b = K.p_ban(task, x, w)
                ps += [b, K.p_mention(task, x, w)]
                for h in (1, 2):
                    n = K.p_neutral(task, x, w, h)
                    ps.append(n)
                    twins.append((b, n))
        for w in K.WS_:
            b, tb = K.p_nonce(task, w), K.p_twostep(task, d, s, w)
            ps += [b, tb]
            for h in (1, 2):
                n, tn = K.p_nonce_neutral(task, w, h), K.p_twostep_neutral(task, d, s, w, h)
                ps += [n, tn]
                twins += [(b, n), (tb, tn)]
        suffixes = {tuple(p["ids"][p["spec_start"]:]) for p in ps}
        struct[task] = {"n_prompts": len(ps), "identical_spec_suffix": len(suffixes) == 1,
                        "n_twin_pairs": len(twins),
                        "twins_equal_length": all(len(a["ids"]) == len(b["ids"]) for a, b in twins),
                        "twins_equal_spec_start": all(a["spec_start"] == b["spec_start"] for a, b in twins),
                        "max_padding_k": max(b["k"] for _, b in twins), "n_token_level_filler": sum(b["filler_inserted"] > 0 for _, b in twins),
                        "one_bos_and_R_asserted": True}
    out["structure"] = struct
    # sampled ids == scored ids
    raw = read_jsonl(DATA / "raw_gen.jsonl")
    samp = {}
    for r in raw:
        samp.setdefault((r["task"], r["condition"]), set()).add(r["prompt_sha"])
    scored = {}
    for task in K.TASKS:
        for f in (FRLP_DIR / "parts" / task).glob("*.parquet"):
            df = pd.read_parquet(f, columns=["cond", "prompt_sha"])
            scored[(task, df["cond"].iat[0])] = set(df["prompt_sha"])
    common_keys = [k for k in samp if k in scored]
    out["sampled_equals_scored"] = {"n_conditions_both": len(common_keys),
                                    "all_equal": all(samp[k] == scored[k] for k in common_keys),
                                    "mismatches": [list(k) for k in common_keys if samp[k] != scored[k]][:10]}
    out["all_pass"] = bool(out["conditions_json"]["mismatch"] == 0 and all(v["identical_spec_suffix"] and v["twins_equal_length"]
                                                                          for v in struct.values()) and out["sampled_equals_scored"]["all_equal"])
    write_json(RESULTS / "tests_prompts.json", out)
    # rendered examples (one per condition type)
    tok = K.tokenizer()
    ex = {}
    for p in [K.p_baseline("t1", 0), K.p_baseline_empty("t1"), K.p_ban("t1", "bfs", 1), K.p_mention("t1", "bfs", 1),
              K.p_neutral("t1", "bfs", 1, 1), K.p_nonce("t1", 4), K.p_nonce_neutral("t1", 4, 2), K.p_novelty("t1"),
              K.p_listall("t2", 0), K.p_twostep("t2", "dijkstra", "bf_spfa", 5), K.p_twostep_neutral("t2", "dijkstra", "bf_spfa", 5, 1),
              K.p_forced("t2", "dial", 0), K.p_forced("t2", "dial", 3, descriptive=True), K.p_free("t1", "bfs")]:
        ex[p["cond"] + f"@{p['task']}"] = {"rendered": tok.decode(p["ids"]), "n_tokens": len(p["ids"]), "seg_start": p["seg_start"],
                                           "spec_start": p["spec_start"], "R": p["R"], "k": p["k"]}
    write_json(RESULTS / "rendered_examples.json", ex)
    # model record
    from pathlib import Path

    mp = Path(model_path())
    rec = json.loads((RESULTS / "model_download.json").read_text())
    shards = {}
    for f in sorted(mp.glob("*.safetensors")):
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        shards[f.name] = {"sha256": h.hexdigest(), "bytes": f.stat().st_size}
    tc = json.loads((mp / "tokenizer_config.json").read_text())
    rec.update({"shards": shards, "chat_template": tc.get("chat_template"),
                "generation_config": json.loads((mp / "generation_config.json").read_text()),
                "local_path": "<run shared HF cache>/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/" + rec["commit_sha"]})
    write_json(RESULTS / "model_record.json", rec)
    print(json.dumps({k: v for k, v in out.items() if k != "conditions_json"} | {"conditions_json": {k: out["conditions_json"][k] for k in ("match", "mismatch")}}, indent=1))


if __name__ == "__main__":
    main()
