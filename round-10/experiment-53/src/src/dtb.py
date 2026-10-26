"""Decision-token branching (DTB) and its random-position placebo (RPB): lexer, entropy, position and token rules.

REQUEST 1 (T 1.0, top_p 1, max_tokens 48, logprobs 20) returns body token ids b[0..m-1] and the top-20 log probs at
each position. Position j is ELIGIBLE iff its token text is not whitespace-only and its first non-whitespace
character starts in CODE state (a token that opens a comment or a string is eligible; tokens inside are not).
DTB: j* = argmax_j H_j over eligible positions (ties -> earliest); RPB: j* uniform over eligible positions
(rng default_rng([seed, arm, call, 4])). Candidates: ranks 2..8 of the top-20 at j*, minus special ids, backtick
tokens, whitespace-only tokens and function-closing tokens. FORCED = uniform draw (rng [seed, arm, call, 3]).
Empty candidate set: DTB moves to the next-highest-entropy eligible position; RPB redraws (<= 10 times).
Fewer than 2 eligible positions, or no candidate anywhere -> NO_BRANCH (the unforced sample is kept).
Positions are 0-based here; the plan's 1-based j* equals j + 1.
"""
from __future__ import annotations

import keyword
import math

import numpy as np

CODE, COMMENT, STR_S, STR_D, STR_TS, STR_TD = range(6)
SPECIAL_MIN_ID = 151643  # every id >= this is a special / added token in the Qwen3 vocabulary
ARM_CODE = {"T1.0": 0, "T1.6": 1, "DTB": 2, "RPB": 3, "IDEA": 4, "NOSEL": 5}


def lex_states(text: str) -> list[int]:
    """State BEFORE each character of `text` (Python-aware: code / comment / 4 string kinds, with escapes)."""
    st, out, i, n = CODE, [], 0, len(text)
    while i < n:
        ch = text[i]
        if st == CODE:
            out.append(CODE)
            if ch == "#":
                st = COMMENT
            elif ch in "'\"":
                if text[i:i + 3] in ("'''", '"""'):
                    out.extend([CODE, CODE])
                    st = STR_TS if ch == "'" else STR_TD
                    i += 3
                    continue
                st = STR_S if ch == "'" else STR_D
            i += 1
        elif st == COMMENT:
            out.append(COMMENT)
            if ch == "\n":
                st = CODE
            i += 1
        else:
            out.append(st)
            if ch == "\\" and i + 1 < n:
                out.append(st)
                i += 2
                continue
            if st == STR_S and ch == "'" or st == STR_D and ch == '"':
                st = CODE
            elif st in (STR_S, STR_D) and ch == "\n":
                st = CODE  # unterminated single-line string: recover at the line end
            elif st == STR_TS and text[i:i + 3] == "'''" or st == STR_TD and text[i:i + 3] == '"""':
                out.extend([st, st])
                st = CODE
                i += 3
                continue
            i += 1
    return out[:n]


def token_offsets(tok, ids: list[int]) -> tuple[list[str], list[int], str]:
    """Incremental decode: per-token text, start offsets and the full decoded text of the id sequence."""
    texts, starts, prev = [], [], ""
    for k in range(len(ids)):
        cur = tok.decode(ids[:k + 1], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        starts.append(len(prev))
        texts.append(cur[len(prev):])
        prev = cur
    return texts, starts, prev


def eligible_positions(texts: list[str], starts: list[int], full: str, limit: int | None = None) -> list[int]:
    """Eligible j: non-whitespace token whose first non-ws char is in CODE state, starting before `limit`."""
    states = lex_states(full)
    lim = len(full) if limit is None else limit
    out = []
    for j, (t, s) in enumerate(zip(texts, starts)):
        if not t.strip():
            continue
        off = s + (len(t) - len(t.lstrip()))
        if off >= lim or off >= len(states):
            continue
        if states[off] == CODE:
            out.append(j)
    return out


def entropy(top: dict[int, float]) -> float:
    """H = -sum p log p over the renormalised top-20."""
    lp = np.array(list(top.values()), dtype=np.float64)
    p = np.exp(lp - lp.max())
    p /= p.sum()
    return float(-(p * np.log(np.clip(p, 1e-300, None))).sum())


def column_at(full: str, offset: int) -> int:
    nl = full.rfind("\n", 0, offset)
    return offset - (nl + 1)


def candidate_ok(tok, tid: int, prefix_col: int) -> tuple[bool, str]:
    if tid >= SPECIAL_MIN_ID or tid in set(tok.all_special_ids):
        return False, "special"
    t = tok.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    if "`" in t:
        return False, "backtick"
    if not t.strip():
        return False, "whitespace"
    for k in range(len(t) - 1):
        if t[k] == "\n" and t[k + 1] not in " \t\n":
            return False, "dedent_col0"
    if prefix_col == 0 and t[0] not in " \t\n":
        # 'def ' / 'class ' at column 0 (the plan's rule); any other non-space character at column 0 would also
        # close the function body (generalisation, logged in the deviations).
        return False, "def_col0" if t.startswith(("def ", "class ")) else "dedent_col0"
    return True, "ok"


def ranked(top: dict[int, float]) -> list[tuple[int, float]]:
    return sorted(top.items(), key=lambda kv: (-kv[1], kv[0]))[:20]


def candidates_at(tok, top: dict[int, float], col: int) -> list[tuple[int, int, float]]:
    """(rank, id, logprob) for ranks 2..8 (1-based) that pass the filters."""
    out = []
    for r, (tid, lp) in enumerate(ranked(top), start=1):
        if 2 <= r <= 8 and candidate_ok(tok, tid, col)[0]:
            out.append((r, tid, lp))
    return out


def lexical_class(t: str) -> str:
    s = t.strip()
    if not s:
        return "whitespace"
    if s.startswith("#"):
        return "comment-opener"
    low = s.lower()
    if s[0] in "'\"" or (len(s) > 1 and low[0] in "rbfu" and s[1] in "'\"") or (
            len(s) > 2 and low[:2] in ("rb", "br", "fr", "rf") and s[2] in "'\""):
        return "string-opener"
    if s[0].isdigit() or (s[0] == "." and len(s) > 1 and s[1].isdigit()):
        return "number"
    if s[0].isalpha() or s[0] == "_":
        word = ""
        for ch in s:
            if ch.isalnum() or ch == "_":
                word += ch
            else:
                break
        return "keyword" if keyword.iskeyword(word) else "identifier"
    return "operator"


def choose_branch(tok, body_ids: list[int], tops: list[dict[int, float]], text_limit: int, mode: str,
                  seed: int, arm: str, call: int) -> dict:
    """Pick (j*, forced id) for DTB ('entropy') or RPB ('random'); returns the full log record."""
    texts, starts, full = token_offsets(tok, body_ids)
    m = len(body_ids)
    elig = [j for j in eligible_positions(texts, starts, full, text_limit) if j < len(tops) and tops[j]]
    H = [entropy(tops[j]) if j < len(tops) and tops[j] else float("nan") for j in range(m)]
    rec = {"m": m, "eligible": elig, "H": [round(h, 6) if math.isfinite(h) else None for h in H],
           "no_branch": False, "j_star": None, "fallback_steps": 0}
    if len(elig) < 2:
        rec["no_branch"] = True
        rec["no_branch_reason"] = "fewer than 2 eligible positions"
        return rec
    rng_pos = np.random.default_rng([seed, ARM_CODE[arm], call, 4])
    order = sorted(elig, key=lambda j: (-H[j], j)) if mode == "entropy" else None
    tries = 0
    chosen, cands = None, []
    while True:
        if mode == "entropy":
            if tries >= len(order):
                break
            j = order[tries]
        else:
            if tries >= 11:  # first draw + up to 10 redraws
                break
            j = int(elig[int(rng_pos.integers(len(elig)))])
        col = column_at(full, starts[j])
        cands = candidates_at(tok, tops[j], col)
        if cands:
            chosen = j
            break
        tries += 1
    rec["fallback_steps"] = tries
    if chosen is None:
        rec["no_branch"] = True
        rec["no_branch_reason"] = "no candidate at any tried position"
        return rec
    j = chosen
    rng_tok = np.random.default_rng([seed, ARM_CODE[arm], call, 3])
    r, tid, lp = cands[int(rng_tok.integers(len(cands)))]
    sorted_elig_H = sorted((H[e] for e in elig), reverse=True)
    forced_text = tok.decode([tid], skip_special_tokens=False, clean_up_tokenization_spaces=False)
    rec.update({
        "j_star": j, "H_j_star": H[j], "H_rank_among_eligible": 1 + sorted_elig_H.index(H[j]),
        "n_eligible": len(elig), "top20_at_j": [[int(a), float(b)] for a, b in ranked(tops[j])],
        "sampled_id": int(body_ids[j]), "sampled_text": texts[j], "forced_id": int(tid), "forced_text": forced_text,
        "forced_rank": int(r), "forced_logprob": float(lp), "forced_eq_sampled": int(tid) == int(body_ids[j]),
        "forced_class": lexical_class(forced_text), "sampled_class": lexical_class(texts[j]),
        "candidates": [[int(a), int(b), float(c)] for a, b, c in cands], "position_frac": j / max(1, m),
    })
    return rec
