"""(0f) Dated positioning rows (web check 2026-10-20). Each neighbour's abstract page was fetched with the aii-web-tools
fetch script into results/web/ (arXiv abstract pages; the Alignment Forum post through its greaterwrong mirror) and the
quote below is re-verified here by exact (whitespace-normalised) string match against that saved text. A row whose
quote is not found is marked 'unverified' and carries no paraphrase."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
from loguru import logger

from common.paths import RESULTS, TABLES, WS, write_json

DATE = "2026-10-20"
ROWS: list[dict[str, Any]] = [
    {"claim_id": "P1", "claim": "compliance at R: decodable (C5 within-cell Spearman -0.41 [-0.69, -0.17]) yet splicing R carries nothing (F_R about 0); one template (W4) produced every T1 fresh-pool failure",
     "neighbour": "Heo et al., ICLR 2025, arXiv 2410.14516", "file": "arxiv_2410.14516.md", "url": "https://arxiv.org/abs/2410.14516",
     "quote": "this dimension is more closely related to the phrasing of prompts rather than the inherent difficulty of the task or instructions",
     "relation": "replication (phrasing) + contrast (decodable but inert under splicing)",
     "adds": "a compliance-predictive direction that is decodable at R but causally inert when R alone is spliced (F_R ~ 0); the ban travels through task-spec states"},
    {"claim_id": "P2", "claim": "knockout method: condition-span attention knockouts and KV splicing locate the ban on the prompt route (F_prompt 0.85 pooled)",
     "neighbour": "Geva et al., EMNLP 2023, arXiv 2304.14767", "file": "arxiv_2304.14767.md", "url": "https://arxiv.org/abs/2304.14767",
     "quote": "With interventions on attention edges, we first identify two critical points where information propagates to the prediction",
     "relation": "extension (method)", "adds": "attention-edge knockouts applied to a prompt-level prohibition in code generation, with token-matched neutral twins"},
    {"claim_id": "P3", "claim": "the instruction is no longer needed after task recognition: direct route 0.05 [0.01, 0.09] on T2 (replication); counter-case on T1, direct route 0.35 [0.25, 0.45]",
     "neighbour": "Sia, Mueller and Duh, NeurIPS 2024, arXiv 2403.04510", "file": "arxiv_2403.04510.md", "url": "https://arxiv.org/abs/2403.04510",
     "quote": "we demonstrate evidence of a \"task recognition\" point where the translation task is encoded into the input representations and attention to context is no longer necessary",
     "relation": "replication (T2) + contrast (T1)", "adds": "the same redundancy for a prohibition on one task and its failure on another (T1 still reads the ban directly)"},
    {"claim_id": "P4a", "claim": "priming by naming: naming an absent algorithm in a ban raises its likelihood (8/9 in Qwen, 5/6 in Llama)",
     "neighbour": "Rana, arXiv 2601.08070", "file": "arxiv_2601.08070.md", "url": "https://arxiv.org/abs/2601.08070",
     "quote": "the instruction's explicit mention of the forbidden word paradoxically activates rather than suppresses the target representation",
     "relation": "replication", "adds": "the priming effect at the level of whole algorithms (program likelihoods), in two model families"},
    {"claim_id": "P4b", "claim": "priming by naming (as P4a)", "neighbour": "Mann et al., arXiv 2511.12381", "file": "arxiv_2511.12381.md",
     "url": "https://arxiv.org/abs/2511.12381",
     "quote": "suppressing a concept requires internally activating it, which may prime rebound instead of avoidance",
     "relation": "replication", "adds": "rebound measured on implemented mechanisms rather than tokens"},
    {"claim_id": "P5", "claim": "ban-list reimplementation: multi-name bans fail (TOP avoidance 0.13, TOP5 0.00); banned BFS/DFS re-implemented, 41-92% of the time without naming it",
     "neighbour": "Lu et al., arXiv 2407.09007 (NAACL 2025 per the plan; venue not shown on the abstract page)", "file": "arxiv_2407.09007.md",
     "url": "https://arxiv.org/abs/2407.09007",
     "quote": "DENIAL PROMPTING which pushes LLMs to develop more creative solutions to a given problem by incrementally imposing new constraints on the previous solution",
     "relation": "extension", "adds": "mechanism-level labels show the constraint is satisfied in name only: disguise rates of 41-92%"},
    {"claim_id": "P6", "claim": "SAE transfer: Qwen-Scope base SAEs fail on Qwen3-8B instruct (dCE ratio 3.29/1.95/1.59 at L15/L20/L27); the report proposed fine-tuning without citing the source of that remedy",
     "neighbour": "Kissane et al. 2024, Alignment Forum, 'SAEs (usually) transfer between base and chat models'", "file": "af_kissane_grep.md",
     "url": "https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models",
     "quote": "We also find that they don’t transfer on",
     "relation": "contrast (another family where transfer fails) + prior source of the fine-tuning remedy",
     "adds": "Qwen3-8B joins Gemma v1 2B as a base/chat pair where base SAEs do not transfer; the proposed remedy is Kissane et al.'s"},
    {"claim_id": "P7", "claim": "decoding-time constraints as the alternative to prompt bans",
     "neighbour": "Biagiola et al., arXiv 2606.21619", "file": "arxiv_2606.21619.md", "url": "https://arxiv.org/abs/2606.21619",
     "quote": "Incompleteness pushes the model into low-probability regions of the program space, causing the generation to frequently time out, and reducing functional correctness by up to 97%.",
     "relation": "contrast", "adds": "prompt bans are complied with at 0.86/0.84 for single names but fail for lists; decoding-time vetoes carry the cost Biagiola et al. measure"},
    {"claim_id": "P8a", "claim": "negation as suppression plus promotion: a single ban suppresses the default opening (0% import openings under the ban) and promotes one substitute (DFS 86/100, BF/SPFA 83/100)",
     "neighbour": "Yoon et al., arXiv 2610.09571", "file": "arxiv_2610.09571.md", "url": "https://arxiv.org/abs/2610.09571",
     "quote": "suppressing retrieval of the original answer (e.g., \"Madrid\") while (2) promoting a favored candidate within the answer category",
     "relation": "replication at program level", "adds": "suppression + promotion for algorithm choice; the promoted candidate is the shared top rung, not an X-specific substitute (C1 undecidable on this instrument)"},
    {"claim_id": "P8b", "claim": "negation mechanisms (as P8a)", "neighbour": "Zhou et al., ICML 2026, arXiv 2605.03052", "file": "arxiv_2605.03052.md",
     "url": "https://arxiv.org/abs/2605.03052",
     "quote": "models implement both mechanisms, with the \"constructive\" mechanism being more prominent",
     "relation": "contrast", "adds": "for a prohibition on code the route is carried by task-spec states; no construction of the negated phrase was tested"},
    {"claim_id": "P9a", "claim": "task and function vectors: the ban is carried by task-spec states (F_spec 0.86 / 0.81) and not by R alone (F_R about 0)",
     "neighbour": "Hendel et al., Findings of EMNLP 2023, arXiv 2310.15916", "file": "arxiv_2310.15916.md", "url": "https://arxiv.org/abs/2310.15916",
     "quote": "the functions learned by ICL often have a very simple structure",
     "relation": "contrast", "adds": "a prohibition does not compress into a single position's state (R splice carries ~0)"},
    {"claim_id": "P9b", "claim": "task and function vectors (as P9a)", "neighbour": "Todd et al., ICLR 2024, arXiv 2310.15213", "file": "arxiv_2310.15213.md",
     "url": "https://arxiv.org/abs/2310.15213",
     "quote": "a small number attention heads transport a compact representation of the demonstrated task, which we call a function vector (FV)",
     "relation": "contrast", "adds": "ban-specific heads exist (L21H17, L26H21, L26H25) but the effect is distributed over task-spec positions"},
]


def _norm(s: str) -> str:
    s = s.replace("**", "").replace("\\", "")
    return re.sub(r"\s+", " ", s).strip().lower()


def run() -> dict[str, Any]:
    out = []
    for r in ROWS:
        p = WS / "results" / "web" / r["file"]
        txt = p.read_text(errors="ignore") if p.exists() else ""
        ok = bool(txt) and _norm(r["quote"]) in _norm(txt)
        n_words = len(r["quote"].split())
        out.append({"claim_id": r["claim_id"], "this_run_claim": r["claim"], "neighbour": r["neighbour"],
                    "neighbour_finding_quote": r["quote"] if ok else "", "quote_words": n_words, "url": r["url"],
                    "relation": r["relation"] if ok else "unverified", "what_this_run_adds": r["adds"] if ok else "",
                    "verified": ok, "evidence_file": f"results/web/{r['file']}", "date": DATE})
    pd.DataFrame(out).to_csv(TABLES / "positioning.csv", index=False)
    res = {"rows": out, "n_verified": sum(r["verified"] for r in out), "n_rows": len(out), "date": DATE,
           "method": "aii-web-tools fetch of each abstract page (results/web/), exact quote re-verified at run time"}
    write_json(RESULTS / "positioning.json", res)
    logger.info(f"positioning: {res['n_verified']}/{res['n_rows']} verified")
    return res
