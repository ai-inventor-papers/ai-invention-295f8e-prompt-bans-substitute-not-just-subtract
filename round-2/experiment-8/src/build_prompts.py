#!/usr/bin/env python3
"""S1: frozen prompts (ban / mention / length-matched neutral twins for W1-W5), forced prompts, signature-token
sets, and the pre-registration commit.

Length matching: every neutral twin must have exactly the ban prompt's token length, identical ids at every
position >= p1 (the first token of 'Task:'), and differ only inside the condition span [p0, p1). All 718 neutral
candidates are single Qwen3 tokens, so the closest-token-count rule reduces to SUBTLEX frequency and the
object phrase is padded deterministically with companion nouns (forms below, fewest companions first).
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from cfg import (ALGOS, DISPLAY, FORCED_PARAPHRASES, INPUTS, PROMPTS_DIR, RESULTS_DIR, ROOT, SIGNATURE_VOCAB,
                 TASKS, TEMPLATE_IDS, TEMPLATE_TAIL, TEMPLATES, THRESHOLDS, X_KEY, N_BOOT, N_PERM_C5,
                 N_RANDOM_DIRS, KO_WINDOW, LAYER_BANDS, N_PROGRAMS, BEH_PER_TEMPLATE, cap_first, chat_ids,
                 model_path, sha256_file, sha256_text, spec_text, user_prompt, utc_now, write_json, MODEL_ID,
                 SCRUB_REGEX, DESCRIPTIVE_VARIANT, model_revision)

PAD_FORMS: list[tuple[int, str]] = [
    (0, "{N}"),
    (0, "the {N}"),
    (1, "{N} and {C1}"),
    (1, "{N} and the {C1}"),
    (1, "the {N} and the {C1}"),
    (2, "{N}, {C1} and {C2}"),
    (2, "{N}, the {C1} and {C2}"),
    (2, "{N}, the {C1} and the {C2}"),
    (2, "the {N}, the {C1} and the {C2}"),
    (3, "{N}, the {C1}, the {C2} and {C3}"),
    (3, "{N}, the {C1}, the {C2} and the {C3}"),
    (3, "the {N}, the {C1}, the {C2} and the {C3}"),
]
FROZEN = PROMPTS_DIR / "frozen_prompts.json"


def load_tokenizer():
    from transformers import AutoTokenizer

    from cfg import hf_kwargs

    return AutoTokenizer.from_pretrained(model_path(), **hf_kwargs())


def _positions(tok, ids: list[int], task: str) -> tuple[int, int]:
    head = tok("<|im_start|>user\n", add_special_tokens=False)["input_ids"]
    assert ids[:len(head)] == head, "unexpected chat header"
    suf = tok(spec_text(task) + TEMPLATE_TAIL, add_special_tokens=False)["input_ids"]
    p1 = len(ids) - len(suf)
    assert ids[p1:] == suf, "SPEC + template tail do not tokenize identically in context"
    return len(head), p1


def _prompt_record(tok, segment: str, task: str) -> dict[str, Any]:
    text = user_prompt(segment, task)
    ids = chat_ids(tok, text)
    p0, p1 = _positions(tok, ids, task)
    return {"segment": cap_first(segment), "user_text": text, "ids": ids, "P": len(ids), "p0": p0, "p1": p1,
            "ids_sha256": sha256_text(json.dumps(ids))}


def _candidates(tok) -> list[dict[str, Any]]:
    cand = json.loads((INPUTS / "dataset" / "neutral_noun_candidates.json").read_text())
    out = []
    for c in cand:
        w = c["input"]
        n = len(tok(" " + w, add_special_tokens=False)["input_ids"])
        out.append({"noun": w, "n_tok": n, "freq": int(c.get("metadata_subtlex_frequency") or 0),
                    "n_tok_dataset": c.get("metadata_qwen3_tokens_with_leading_space")})
    return out


def _match_neutral(tok, task: str, w: str, ban: dict[str, Any], noun: str, comps: list[str]) -> dict[str, Any] | None:
    neutral_t = TEMPLATES[w][2]
    for k, form in PAD_FORMS:
        phrase = form.format(N=noun, C1=comps[0], C2=comps[1], C3=comps[2])
        rec = _prompt_record(tok, neutral_t.replace("{N}", phrase), task)
        if rec["P"] != ban["P"] or rec["p1"] != ban["p1"] or rec["p0"] != ban["p0"]:
            continue
        if rec["ids"][rec["p1"]:] != ban["ids"][ban["p1"]:]:
            continue
        diff = [i for i, (a, b) in enumerate(zip(rec["ids"], ban["ids"])) if a != b]
        if not diff or min(diff) < ban["p0"] or max(diff) >= ban["p1"]:
            continue
        rec.update({"noun": noun, "phrase": phrase, "n_companions": k, "form": form,
                    "diff_span": [min(diff), max(diff) + 1], "n_diff_positions": len(diff)})
        return rec
    return None


def stage_prompts() -> dict[str, Any]:
    tok = load_tokenizer()
    cands = _candidates(tok)
    mism = sum(1 for c in cands if c["n_tok_dataset"] is not None and int(c["n_tok_dataset"]) != c["n_tok"])
    logger.info(f"{len(cands)} neutral candidates; token-count mismatches vs dataset field: {mism}")
    deviations: list[str] = []
    out: dict[str, Any] = {"model": MODEL_ID, "model_revision": model_revision(), "created_utc": utc_now(),
                           "spec": {t: spec_text(t) for t in TASKS}, "display": DISPLAY, "templates": TEMPLATES,
                           "pad_forms": PAD_FORMS, "tasks": {}}
    for task in TASKS:
        x = X_KEY[task]
        xname = DISPLAY[task][x]
        n_name = len(tok(" " + xname, add_special_tokens=False)["input_ids"])
        ranked = sorted(cands, key=lambda c: (abs(c["n_tok"] - n_name), -c["freq"], c["noun"]))
        bans = {w: _prompt_record(tok, TEMPLATES[w][0].replace("{X}", xname), task) for w in TEMPLATE_IDS}
        chosen: list[dict[str, Any]] = []
        for c in ranked:
            if len(chosen) == 2:
                break
            heads = [h["noun"] for h in chosen] + [c["noun"]]
            comps = [cc["noun"] for cc in sorted(cands, key=lambda z: (-z["freq"], z["noun"]))
                     if cc["n_tok"] == 1 and cc["noun"] not in heads][:3]
            per_w = {}
            for w in TEMPLATE_IDS:
                m = _match_neutral(tok, task, w, bans[w], c["noun"], comps)
                if m is None:
                    break
                per_w[w] = m
            if len(per_w) == len(TEMPLATE_IDS):
                chosen.append({"noun": c["noun"], "n_tok": c["n_tok"], "freq": c["freq"], "companions": comps,
                               "per_template": per_w})
        if len(chosen) < 2:
            raise RuntimeError(f"{task}: could not find two neutral nouns aligning on all templates (F4)")
        # companions of noun A must not use noun B as a companion and vice versa: recompute with both heads excluded
        heads = [chosen[0]["noun"], chosen[1]["noun"]]
        comps = [cc["noun"] for cc in sorted(cands, key=lambda z: (-z["freq"], z["noun"]))
                 if cc["n_tok"] == 1 and cc["noun"] not in heads][:3]
        for ch in chosen:
            if ch["companions"] != comps:
                ch["companions"] = comps
                ch["per_template"] = {w: _match_neutral(tok, task, w, bans[w], ch["noun"], comps)
                                      for w in TEMPLATE_IDS}
                assert all(v is not None for v in ch["per_template"].values())
        mentions = {w: _prompt_record(tok, TEMPLATES[w][1].replace("{X}", xname), task) for w in TEMPLATE_IDS}
        forced = {}
        for j in ALGOS[task]:
            forced[j] = {"paraphrases": [_prompt_record(tok, f.replace("{j}", DISPLAY[task][j]), task)
                                         for f in FORCED_PARAPHRASES],
                         "descriptive": _prompt_record(tok, DESCRIPTIVE_VARIANT[task][j], task)}
        tdata = {"x": x, "x_display": xname, "x_display_ntok": n_name, "templates": {}}
        for w in TEMPLATE_IDS:
            b = bans[w]
            nA = chosen[0]["per_template"][w]
            nB = chosen[1]["per_template"][w]
            tdata["templates"][w] = {"ban": b, "mention": mentions[w], "neutral_A": nA, "neutral_B": nB}
            logger.info(f"[{task} {w}] P={b['P']} p0={b['p0']} p1={b['p1']}\n   ban : {b['segment']}\n"
                        f"   neuA: {nA['segment']}  diff={nA['diff_span']}\n   neuB: {nB['segment']}  "
                        f"diff={nB['diff_span']}\n   ment: {mentions[w]['segment']} (P={mentions[w]['P']})")
        tdata["nouns"] = {"A": {k: v for k, v in chosen[0].items() if k != "per_template"},
                          "B": {k: v for k, v in chosen[1].items() if k != "per_template"}}
        tdata["forced"] = forced
        out["tasks"][task] = tdata
    # signature-token sets (first subwords), printed for the record
    sig = {}
    for key, vocab in SIGNATURE_VOCAB.items():
        firsts = {}
        for wd in vocab:
            base = wd.rstrip("()").split("(")[0].strip() if wd not in ("range(n - 1)",) else "range"
            for variant in (base, " " + base, "." + base):
                tid = tok(variant, add_special_tokens=False)["input_ids"][0]
                firsts[variant] = [tid, tok.decode([tid])]
        sig[key] = firsts
        logger.info(f"signature first-subwords {key}: { {k: v[1] for k, v in firsts.items()} }")
    out["signature_first_subwords"] = sig
    out["deviations"] = deviations
    write_json(FROZEN, out)
    logger.info(f"frozen prompts -> {FROZEN} sha256={sha256_file(FROZEN)}")
    return out


def stage_prereg() -> dict[str, Any]:
    """Hash-commit the frozen decision rules, prompts and analysis code BEFORE any arm is scored or sampled."""
    fp = json.loads(FROZEN.read_text())
    pre = {
        "title": "Where an algorithm ban takes effect (C2 route test + C5 compliance at R)",
        "created_utc": utc_now(),
        "model": MODEL_ID, "model_revision": model_revision(),
        "frozen_prompts_sha256": sha256_file(FROZEN),
        "analysis_py_sha256": sha256_file(ROOT / "analysis.py"),
        "templates": TEMPLATES,
        "nouns": {t: fp["tasks"][t]["nouns"] for t in TASKS},
        "signature_vocab": SIGNATURE_VOCAB, "scrub_regex": SCRUB_REGEX,
        "arms": {
            "a": "full ban (ban cache, ban R logits)", "b": "full neutral twin",
            "c": "PROMPT ROUTE: neutral condition segment [p0,p1) + ban task-spec/R cache, ban R logits",
            "d": "DIRECT ROUTE: ban condition segment + neutral task-spec/R cache, neutral R logits",
            "e": "R-only: neutral cache with position P-1 from ban, ban R logits",
            "f": "task-spec-only: neutral [0,p1) + ban [p1,P-1) + neutral P-1, neutral R logits",
            "pl": "placebo: neutral-A [0,p1) + neutral-B [p1,P), R from neutral-B, vs b with noun B",
            "K0": "condition-span attention knockout for all generated queries (cache a)",
            "K1": f"knockout for generated index < {KO_WINDOW}", "K2": f"knockout for generated index >= {KO_WINDOW}",
            "B1/B2/B3": f"knockout restricted to layer bands {LAYER_BANDS}", "K0b": "K0 on the neutral cache (control)"},
        "primary_readout": "FRLP drop D_X(arm) = L_X(arm) - L_X(b); L_j(c) = log mean_m exp(l(p_m|c) - l(p_m|F_j)), "
                           "mixture proposal over the forced paraphrases weighted by samples drawn per prompt",
        "decision_rules": {
            "prerequisite": "per task: D_X(a) < 0 with 95% bootstrap CI excluding 0, else 'no FRLP-level ban effect' "
                            "(excluded from the pool, reported)",
            "CONFIRMED_direct_route": f"pooled F_direct = sum_t D_t(d) / sum_t D_t(a) >= {THRESHOLDS['F_confirm']:.4f} "
                                      f"and its bootstrap 2.5th percentile > {THRESHOLDS['F_ci_lower']}",
            "DECIDED_BEFORE_WRITING": f"pooled F_prompt >= {THRESHOLDS['F_confirm']:.4f} (report whether 2.5th pct > "
                                      f"{THRESHOLDS['F_ci_lower']})",
            "MIXED": "otherwise; report interaction I = D(a) - D(c) - D(d) with CI",
            "ROBUST": "only if both tasks give the same branch",
            "early_late_veto": "early if R_K1 - R_K2 > 0 with CI excluding 0 (net of the neutral-prompt K0 control); "
                               "late if the reverse",
            "placebo": f"|D_X(pl)| < {THRESHOLDS['placebo_max_frac']} |D_X(a)| else splicing flagged as noisy",
            "C5": f"CONFIRMED if combined within-cell Spearman rho <= {THRESHOLDS['c5_rho']} and one-sided stratified "
                  f"permutation p < {THRESHOLDS['c5_alpha']}; PARTIAL if rho < 0 with p < 0.05 but rho > -0.5; NULL "
                  "otherwise; same for the decommitment axis; Holm over the two C5 axes",
        },
        "bootstrap": {"n_boot": N_BOOT, "levels": "templates, then programs within each half (crossed)",
                      "pooled": "ratio of sums across tasks"},
        "c5": {"n_perm": N_PERM_C5, "n_random_dirs": N_RANDOM_DIRS, "layers": "8-28 z-scored then averaged",
               "direction": "leave-one-experiment-out mean of normalised ban-minus-reference shifts"},
        "sampling": {"N_per_arm": 5 * BEH_PER_TEMPLATE, "temperature": 1.0, "top_p": 1.0, "max_new_tokens": 1024,
                     "crn": "one PCG64 uniform stream per (task, template, sample), inverse-CDF in vocabulary order"},
        "n_programs_per_algorithm": N_PROGRAMS,
        "gate": {"avoidance": THRESHOLDS["gate_avoidance"], "min_nonbanned": THRESHOLDS["gate_min_nonbanned"]},
        "drop_order": ["layer-band knockouts FRLP only", "tuned lens", "C5 new-template cells", "mention-twin FRLP",
                       "arms e, f, pl", "K1/K2 behaviour", "behaviour N 100 -> 50"],
        "thresholds": THRESHOLDS,
    }
    p = RESULTS_DIR / "prereg.json"
    write_json(p, pre)
    h = sha256_file(p)
    (RESULTS_DIR / "prereg_commit.txt").write_text(f"{h}  results/prereg.json  committed {utc_now()}\n")
    logger.info(f"pre-registration committed: sha256={h}")
    return pre
