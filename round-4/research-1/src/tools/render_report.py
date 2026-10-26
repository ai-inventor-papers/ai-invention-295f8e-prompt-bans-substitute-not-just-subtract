"""Render research_report.md (and cache/answer.md + cache/sources.json for the structured output) from the verified
evidence files, so every quote in the tables is copied from evidence/quotes.jsonl (status VERIFIED/VERIFIED-ABSTRACT).

Usage: python -I tools/render_report.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, EVID, WS  # noqa: E402

META = json.loads((EVID / "arxiv_meta.json").read_text())
QUOTES = [json.loads(l) for l in (EVID / "quotes.jsonl").read_text().splitlines()]
HITS = [json.loads(l) for l in (EVID / "saturation_hits.jsonl").read_text().splitlines()]
COUNTS = json.loads((EVID / "saturation_counts.json").read_text())
CORR = [json.loads(l) for l in (EVID / "corrections.jsonl").read_text().splitlines()]
INDEX_ROWS = [json.loads(l) for l in (CACHE / "index.jsonl").read_text().splitlines()]
QA = {}
if (EVID / "qa_second_pass.jsonl").exists():
    for l in (EVID / "qa_second_pass.jsonl").read_text().splitlines():
        r = json.loads(l)
        QA.setdefault(r["ref_key"], []).append(r["second_pass"])

# ------------------------------------------------------------------ sources (numbered once, shared everywhere)
S = []  # dicts: key, title, url, authors, year, summary, venue


def add(key, url, title=None, aid=None, summary="", year=None, authors=None, venue=None):
    m = META.get(aid or "", {})
    S.append({"key": key, "url": url, "title": title or m.get("title") or key,
              "authors": authors if authors is not None else (m.get("authors") or None),
              "year": year if year is not None else (int(m["v1_published"][:4]) if m.get("v1_published") else None),
              "summary": summary, "venue": venue})


def q_url(ref):
    for q in QUOTES:
        if q["ref_key"] == ref:
            return q["url"]
    raise KeyError(ref)


PAPERS = [  # key, arxiv id (or None), summary
    ("Lu2025-NeoCoder", "2407.09007", "NeoCoder / Denial Prompting (NAACL 2025): constraint following decays over successive denials; models may copy previous solutions; GPT-4 below human creativity."),
    ("Rana2026", "2601.08070", "Negative word constraints: priming failure (naming the forbidden word activates it) explains 87.5% of violations."),
    ("Yoon2026", "2610.09571", "Negation in LLMs: 37-71% repeat the original answer; mechanism suppresses the original and promotes a favoured in-category candidate."),
    ("Sclar2024", "2310.11324", "Prompt-format sensitivity up to 76 accuracy points (ICLR 2024)."),
    ("Heo2025", "2410.14516", "An input-embedding 'instruction-following dimension' predicts compliance and tracks prompt phrasing (ICLR 2025)."),
    ("Qi2025", "2406.05946", "Shallow safety alignment: alignment concentrated in the first few output tokens; prefilling effects (ICLR 2025 Outstanding Paper)."),
    ("Andriushchenko2025", "2404.02151", "Adaptive and prefilling jailbreak attacks (ICLR 2025)."),
    ("Zhu2024-AdapT", "2309.02772", "AdapT: high-loss 'challenging tokens' concentrate at the beginning of code blocks (AAAI 2024)."),
    ("Biagiola2026", "2606.21619", "Misaligned (incomplete) constrainers push code decoding into low-probability regions, cutting correctness by up to 97%."),
    ("Park2024-GAD", "2405.21047", "Grammar-constrained decoding distorts the LM distribution; grammar-aligned decoding (NeurIPS 2024)."),
    ("Zhang2025-NoveltyBench", "2504.05228", "NoveltyBench (COLM 2025): models generate less diversity than human writers; larger models often less diverse."),
    ("Jangra2026-DivAlgo", "2610.19157", "DivAlgo: algorithmic diversity of 24 code models vs human solutions (~31%; best strategy ~70%); prompt-based steering cannot reproduce human diversity."),
    ("Lee2025", "2503.00691", "Algorithmic diversity of model code is low; heterogeneous models and temperature > 1.0 raise it at a correctness cost (Findings of EMNLP 2025)."),
    ("Khalid2026-NoiseSteering", "2604.03380", "Noise steering (BEA @ ACL 2026): four internal injection sites vs high temperature for narrative diversity; residual noise best."),
    ("Zhu2026-STARS", "2601.22010", "STARS (ICLR 2026): Stiefel activation steering for diverse generation; TESTEVAL test cases with execution-checked validity and coverage vs temperature."),
    ("Kim2026-REI", "2605.11936", "Random soft prompts (random embedding injection) branch early tokens and widen Pass@N on math; code left to future work (ICML 2026 MI workshop spotlight)."),
    ("Ho2025-SPREAD", "2511.08305", "SPREAD (AAAI 2026): Riemannian activation steering for diverse reasoning, evaluated on math benchmarks."),
    ("Jerge2026-NoisyCoconut", "2605.08221", "NoisyCoconut: noise in latent reasoning trajectories for consensus and abstention."),
    ("Nagarajan2025-SeedCond", "2504.15266", "Seed-conditioning (input-layer noise) matches or beats output temperature on algorithmic-creativity tasks (ICML 2025)."),
    ("Deshpande2026", "2605.28664", "Activation steering for synthetic data: stronger steering reduces response diversity."),
    ("Fan2026-ASTEER", "2606.11599", "ASTEER: predicts under-/successful/over-steering of an activation-steering intervention from early hidden states (~0.7 macro-F1)."),
    ("Li2026-Routing", "2608.12321", "Implicit-constraint failures are routing, not knowledge, failures (probes + patching)."),
    ("Tan2026-Compliance", "2604.27251", "Reasoning-instruction compliance vs sensibility; instructions decodable without compliance; steering toward compliance (Findings of EMNLP 2026)."),
    ("Mishra2026", "2604.09839", "Steered activations are non-surjective: formal separation between white-box steering and black-box prompting."),
    ("Peeperkorn2024", "2405.00492", "Temperature weakly correlated with novelty, moderately with incoherence (ICCC 2024)."),
    ("Ahmed2025-IFG", "2506.09659", "Intent Factored Generation: sample intent hot, response cold; token-level methods paraphrase; pass@k gains on maths and code (ICML 2025 EXAIT workshop)."),
    ("Wang2025-PlanSearch", "2409.03733", "PlanSearch (ICLR 2025): searching natural-language plans mitigates the lack of diversity in code generation."),
    ("Wu2025-Monoculture", "2407.02209", "Generative monoculture (ICLR 2025): narrower range of algorithms than humans; sampling/prompting changes insufficient."),
    ("He2026-BeneathDiff", "2609.00077", "Beneath the Diff (EMNLP 2026): surface edit diversity stable while mechanism-level diversity collapses in code research loops."),
    ("Narula2026-Lottery", "2606.04057", "The Invisible Lottery (ICML 2026): incidental cues shift algorithm families up to 100 pp; direct naming is the best mitigation."),
    ("Zhang2026-DiversityInjection", "2606.10302", "Diversity Injection Framework: Level 0/1/2 diversity sources and a transmission score; text-level, no code, no activation site."),
    ("Yun2025-PriceOfFormat", "2505.18949", "Diversity collapse persists under high temperature; structural template tokens constrain output space."),
    ("Ravfogel2025-Gumbel", "2411.07180", "Gumbel counterfactual generation (ICLR 2025): joint distribution of strings and counterfactuals under the same sampling noise."),
    ("Dong2025-ERP", "2502.06258", "Emergent response planning (ICML 2025): prompt representations encode global attributes of the upcoming response."),
    ("Ma2026-WheresThePlan", "2605.07984", "Where's the Plan (ICML 2026 MI workshop): probe signal vs causal reliance on latent planning differ across models."),
    ("Chen2026-Brewing", "2606.17648", "From Brewing to Resolution: answers linearly recoverable before the model can use them (code reasoning); wording changed across versions."),
    ("Hendel2023", "2310.15916", "In-context learning compresses demonstrations into a task vector (Findings of EMNLP 2023)."),
    ("Todd2024", "2310.15213", "Function vectors carried by a few attention heads (ICLR 2024)."),
    ("Pal2023-FutureLens", "2311.04897", "Future Lens (CoNLL 2023): single hidden states anticipate subsequent tokens."),
    ("Wu2024-PlanAhead", "2404.00859", "Pre-caching vs breadcrumbs (COLM 2024)."),
    ("DiCicco2026", "2606.14530", "Code correctness linearly decodable from the final prompt token before generation; AUC differs by version (0.931 v1, 0.955 v2, 0.881 v3)."),
    ("Silva2026", "2607.05188", "Latent programming horizons in coding agents: probes predict future edit outcomes up to ~25 steps ahead."),
    ("Basu2026", "2603.18353", "Interpretability without actionability: 98.2% AUROC probes vs 45.1% output sensitivity; steering indistinguishable from random perturbation."),
    ("Wurgaft2026-ManifoldSteering", "2605.05115", "Manifold steering (ICML 2026 MI workshop spotlight): geodesic/MDS isometry; linear steering cuts off-manifold."),
    ("Rahman2026-CodeSteering", "2603.23629", "Difference-in-means steering toward target languages/libraries in code LLMs, even against opposite prompts."),
    ("Tang2026", "2604.07192", "Compact constraint encoding: counter-intuitive constraints opposing defaults fail 10-100%; 'implementation priors' (Sec. 5.3)."),
    ("Zhou2026-Negation", "2605.03052", "How LMs process negation (ICML 2026): construction + suppression; late-layer shortcut heads cause failures."),
    ("Bystronski2025", "2507.13874", "Manifold-based conditioning in embedding space increases generative diversity."),
    ("Novikov2025-AlphaEvolve", "2506.13131", "AlphaEvolve: evolutionary coding agent with evaluators discovers improved algorithms."),
    ("Bhushan2026-AgentCreativity", "2608.30047", "LLM agents show greater H-creativity than medal-winning humans but lower performance (LLM-judge novelty)."),
    ("GraphNovelty2025", "2507.06463", "LLMs excel at optimising/integrating established graph algorithms; inventing new techniques left as a frontier."),
    ("Jerge2026-NCGRPO", "2608.21595", "NC-GRPO: Gaussian noise in the prompt-encoding pass vs temperature/pixel noise for RLVR rollout diversity (VLMs)."),
    ("Zeng2026-ESamp", "2604.24927", "ESamp (ICML 2026): token-level sampling yields surface lexical variation; latent-novelty-guided decoding for semantic exploration (incl. LiveCodeBench)."),
    ("Geng2026-Gacha", "2610.01382", "Gacha Decoding: diversity as instruction following with an external RNG (text-level plan sampler)."),
    ("Maveli2026-AlgoREval", "2610.02438", "AlgoREval: code generation for named algorithms as parametric retrieval rather than synthesis."),
    ("Galeone2026-DetectionVsControl", "2606.24952", "Angle between detection and control directions (detection-intervention gap)."),
    ("Bhattarai2026-SteerabilitySignatures", "2609.14151", "Separation metrics in activation space predict steerability."),
    ("Zhang2026-SPARK", "2607.10296", "SPARK: length-controlled hidden-state susceptibility to diagnose reasoning-state activation and guide steering."),
    ("Fang2026-APTS", "2608.30345", "APTS (EMNLP 2026): hidden states of probed answers separate distinct solution paths in tree search."),
    ("Burtch2026-Hitchhiker", "2607.13077", "AI-assisted human code homogenises syntax, not ML-algorithm calls."),
]
for key, aid, summ in PAPERS:
    add(key, q_url(key), aid=aid, summary=summ)
# non-arXiv or abstract-only primary records with quotes
add("Kotawala2026", "https://neurips.cc/virtual/2026/168286", title="Probing and Steering Prompt Injection Compliance",
    authors=["Anany Kotawala"], year=2026,
    summary="NeurIPS 2026 workshop poster: a last-prompt-token probe predicts injection compliance (ROC-AUC 0.90); only partly steerable. Abstract-only (no arXiv record found).")
add("RomeraParedes2024-FunSearch", "https://www.nature.com/articles/s41586-023-06924-6",
    title="Mathematical discoveries from program search with large language models", authors=["Bernardino Romera-Paredes"], year=2024,
    summary="FunSearch (Nature 625, 468-475; published 14 Dec 2023): LLM + systematic evaluator in an evolutionary loop finds new cap-set constructions.")
OR = [("ICLR27-DiversityWithoutDiscovery", "wJ8HkA8vGN", "Diversity Without Discovery: Why Chain Perturbation Fails to Explore in Latent Test-Time Scaling",
       "ICLR 2027 submission (anonymous): perturbed latent chains add diversity without accuracy gains vs explicit sampling."),
      ("ICLR27-BeforeTheFirstToken", "knirOusGcq", "Before the First Token: A Shared Causal Subspace for Response-Length Planning in LLMs",
       "ICLR 2027 submission: causal pre-generation subspace for response length (parallel vs orthogonal intervention decomposition)."),
      ("ICLR27-AJR", "Dl1xo5fqnj", "AJR: Amortized Jacobian Readouts for Prompt-Adaptive Steering",
       "ICLR 2027 submission: reading states vs predicting intervention effects; decoders mispredict intervention effects."),
      ("ICLR27-RethinkingSteeringMath", "oag3wgNLRh", "Rethinking Activation Steering for Mathematical Reasoning: What Actually Drives Its Reasoning Gains?",
       "ICLR 2027 submission: steering redirects among already-supported trajectories; departure-matched decoding matches it."),
      ("ICLR27-BreakTheRules", "tZaHwMrvq2", "Where Do LLMs Decide to Break the Rules? Mechanistic Localization of Prompt Injection Compliance",
       "ICLR 2027 submission: injection compliance decodable early, causally decided in a late-layer bottleneck."),
      ("ICLR27-SilentCompliance", "L09agUoh7d", "Silent Compliance: Separating Constraint Echoing from Instruction Following",
       "ICLR 2027 submission: compliant answers to negative instructions often echo or reintroduce the excluded object.")]
for key, fid, title, summ in OR:
    add(key, f"https://openreview.net/forum?id={fid}", title=title, authors=None, year=2026, summary=summ + " Abstract read via the OpenReview API.")
# venue / policy evidence pages
VENUE_PAGES = [
    ("Policy-ICLR2027", "https://www.iclr.cc/Conferences/2027/ReviewerGuidelines", "ICLR 2027 Reviewer Guide", "Contemporaneous = published at a peer-reviewed venue within two months of the deadline; arXiv-only papers need not be compared."),
    ("Policy-ICLR2025", "https://iclr.cc/Conferences/2025/FAQ", "ICLR 2025 FAQ", "Earlier four-month contemporaneity rule."),
    ("Policy-ICLR2027-Dates", "https://iclr.cc/Conferences/2027/Dates", "ICLR 2027 Dates", "Abstract deadline Sep 18 '26, paper deadline Sep 25 '26 (AoE)."),
    ("Venue-ICML2025-IFG", "https://icml.cc/virtual/2025/51482", "ICML 2025 virtual page: Intent Factored Generation", "Listed as 'Poster in Workshop: Exploration in AI Today (EXAIT)'."),
    ("Venue-ICML2026-Manifold", "https://icml.cc/virtual/2026/79460", "ICML 2026 virtual page: Manifold Steering", "Listed as 'Spotlight in Workshop: Workshop on Mechanistic Interpretability'."),
    ("Venue-ICML2026-Lottery", "https://icml.cc/virtual/2026/poster/64782", "ICML 2026 virtual page: The Invisible Lottery", "Main-conference poster (Hall A #3510) with OpenReview link."),
    ("Venue-ICML2026-REI", "https://icml.cc/virtual/2026/79614", "ICML 2026 virtual page: Random Embedding Injection", "Listed as 'Spotlight in Workshop: Workshop on Mechanistic Interpretability'."),
    ("Venue-ACL-NeoCoder", "https://aclanthology.org/2025.naacl-long.141/", "ACL Anthology 2025.naacl-long.141", "NeoCoder in NAACL 2025 (Volume 1: Long Papers)."),
    ("Venue-ICLR2025-Awards", "https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/", "ICLR 2025 Outstanding Paper Awards", "Qi et al. listed among Outstanding Papers."),
    ("Venue-ICLR2025-Heo", "https://iclr.cc/virtual/2025/poster/28257", "ICLR 2025 poster page: Heo et al.", "ICLR 2025 poster."),
    ("Venue-ICLR2025-PlanSearch", "https://iclr.cc/virtual/2025/poster/31034", "ICLR 2025 poster page: PlanSearch", "ICLR 2025 poster."),
    ("Venue-ICLR2025-Monoculture", "https://iclr.cc/virtual/2025/poster/27717", "ICLR 2025 poster page: Generative Monoculture", "ICLR 2025 poster."),
    ("Venue-OR-NoveltyBench", "https://api2.openreview.net/notes/search?term=NoveltyBench&limit=10", "OpenReview API record: NoveltyBench", "Venue field 'COLM 2025'."),
    ("Venue-ACL-Lee2025", "https://aclanthology.org/2025.findings-emnlp.10/", "ACL Anthology 2025.findings-emnlp.10", "Lee et al. in Findings of EMNLP 2025."),
    ("Venue-ICML2025-SeedCond", "https://icml.cc/virtual/2025/poster/45769", "ICML 2025 page: Roll the dice & look before you leap", "Spotlight poster; Outstanding Paper 2025."),
]
for key, url, title, summ in VENUE_PAGES:
    add(key, url, title=title, authors=None, year=None, summary=summ)
# saturation hits screened without a quote
SAT_ONLY = [("2606.15092", "HiDRA random-projection steering (method variant; irrelevant)."),
            ("2607.05615", "Bernoulli sparse steering (method variant; irrelevant)."),
            ("2608.07852", "SAE anatomy of personas (irrelevant)."),
            ("2602.04297", "Prompt sensitivity from underspecified prompts (irrelevant to the claims)."),
            ("2604.18389", "Taylor-expansion account of prompt sensitivity (irrelevant)."),
            ("2604.01639", "Answer flips under meaning-preserving perturbations localised by patching (irrelevant)."),
            ("2605.30789", "Smaller models as explorers in GRPO (training-time; irrelevant)."),
            ("2606.29604", "Causal perturbative elicitation of latent behaviours (abstract screened)."),
            ("2604.12493", "Latent planning emerges with scale (ICLR 2026; abstract screened)."),
            ("2602.02103", "Latent planning horizon in CoT (ICML 2026; abstract screened)."),
            ("2607.05316", "Remaining output length decodable from the prompt's last hidden state (abstract screened)."),
            ("2602.07080", "Code correctness from attribution graphs (abstract screened)."),
            ("2605.29737", "Single-character prompt mutations flip code security; hidden-state signals (abstract screened)."),
            ("2610.25133", "One steering direction toward safer cryptographic API use (abstract screened)."),
            ("2604.13006", "Single-token lexical bans collapse helpfulness (abstract screened)."),
            ("2608.14669", "Automated novelty verification in Lean 4 (abstract screened)."),
            ("2606.08251", "Scientist ratings of LLM ideas: hivemind collapse (abstract screened)."),
            ("2605.11128", "Calibration as the diversity bottleneck (abstract screened)."),
            ("2602.20408", "Barriers to diversity in LLM ideas (abstract screened)."),
            ("2608.09351", "Where to inject diversity at the input level for test-time augmentation (abstract screened).")]
for aid, summ in SAT_ONLY:
    v = META[aid]["latest_version"]
    add(aid, f"https://arxiv.org/abs/{aid}{v}", aid=aid, summary=summ)
add("or:uVn7IU6iPN", "https://openreview.net/forum?id=uVn7IU6iPN", title="Does Prompt Sensitivity Improve Cross-Family Degradation Prediction?",
    authors=None, year=2026, summary="ICLR 2027 submission: black-box prompt sensitivity as a frozen predictor of accuracy loss (abstract screened).")
add("arXivAPI", "https://export.arxiv.org/api/query", title="arXiv API (id_list metadata: versions, v1 dates, comment and journal_ref lines)",
    authors=None, year=None, summary="Source of every version number, v1 date and comment-line venue claim in this artifact (queried 2026-10-21).")

NUM = {s["key"]: i + 1 for i, s in enumerate(S)}
NUM["Venue-NeurIPS2026-Kotawala"] = NUM["Kotawala2026"]
for k in ["Lu2025-NeoCoder", "Rana2026"]:
    assert k in NUM


def c(*keys):
    return "[" + ", ".join(str(NUM[k]) for k in keys) + "]"


def quote(ref, sel=""):
    for q in QUOTES:
        if q["ref_key"] == ref and sel in q["quote"]:
            return q
    raise KeyError((ref, sel))


def label(ref):
    q = quote(ref)
    src = S[NUM[ref] - 1]
    if ref.startswith("ICLR27"):
        return f"Anonymous, 2026, {q['venue_status']}, OpenReview {src['url'].rsplit('=', 1)[-1]} {c(ref)}"
    authors = src.get("authors") or ([q["first_author"]] if q.get("first_author") else [])
    parts = authors[0].split() if authors else [ref.split("2")[0]]
    surname = " ".join(parts[-2:]) if len(parts) > 1 and parts[-2] in {"Di", "De", "Da", "Van", "Von", "Le", "La", "Du"} else parts[-1]
    if ref == "Ho2025-SPREAD":
        surname = "Ly Tran Ho Khanh"
    multi = len(authors) > 1 or ref in {"RomeraParedes2024-FunSearch"}
    who = f"{surname} et al." if multi else surname
    import re as _re
    vy = _re.search(r"(20\d\d)", q.get("venue_status") or "")
    year = vy.group(1) if vy and "preprint" not in (q.get("venue_status") or "") else (src.get("year") or "")
    ident = f"arXiv {q['arxiv_id']}{q.get('latest_version_seen') or ''}" if q.get("arxiv_id") else "no arXiv record"
    return f"{who}, {year}, {q['venue_status']}, {ident} {c(ref)}"


def cell(t):
    return str(t).replace("|", "/").replace("\n", " ")


def subrow(no, claim, ref, sel, adds, verdict):
    q = quote(ref, sel)
    where = f"{q['url']}; {q['section_or_page']}"
    return f"| {no} | {cell(claim)} | {cell(label(ref))} | \"{cell(q['quote'])}\" | {cell(where)} | {q['retrieved_utc']} | {cell(adds)} | {cell(verdict)} |"


HEAD = ("| No. | Run claim (key numbers) | Nearest neighbour | Neighbour's finding (verbatim quote) | Where (URL; section) | Retrieved | "
        "What this run adds, or 'replication of X in Y' | Lane verdict |\n|---|---|---|---|---|---|---|---|")

# ------------------------------------------------------------------ Table 92b rows
B = [
    ("b1", "Snap-back under exposure bans: Qwen3-8B, 12 tasks, 33 shown algorithms, N=50/arm; default share 0.05 (copy twin) -> 0.72 (named ban) / 0.82 (unnamed ban 'uses a different algorithm from the one above'); Llama present-minor bans snap back in 0.72-0.93 of non-banned attempts (art_WiY4wqHLb9Gy; art_Q-qh-9HhPoWo)",
     [("Lu2025-NeoCoder", "copy previous solutions", "Replication of 'compliance decays under successive denials' (NeoCoder Table 3: GPT-4 constraint following 100.0 at t=0 to 14.4 at t=5) for algorithm bans. Addition NeoCoder does not measure: the replacement is the model's own unconditional default, measured against a copy-twin control, in two families.", "ADJACENT-ONLY"),
      ("Yoon2026", "promoting a favored", "Closest analogue (contemporaneous, v1 2026-10-07, arXiv only): under negation a favoured in-category candidate is promoted. The run adds the algorithm level, execution-checked labels, the copy twin, and that the promoted alternative is the unconditional default.", "(closest analogue)"),
      ("Rana2026", "priming failure", "Word-level priming. The run's unnamed ban snaps back more (0.82) than the named ban (0.72), so naming the banned item is not needed for snap-back.", "(adjacent)")]),
    ("b2", "Wording dominates compliance: 12 tasks x 5 templates; template SD 2.0 logits [1.1, 3.5]; likelihood ratio 374 (df 4); shuffled placebo p 0.39; template W4 ('X is not allowed here.') fails on 10/12 tasks (art_1AYTO1Epb_7t; art__5akZ9W9iZM4)",
     [("Sclar2024", "76 accuracy points", "Replication of prompt-format sensitivity (Sclar 2024) in algorithm-prohibition compliance, estimated as a template random effect with a shuffled placebo.", "PARTLY OCCUPIED"),
      ("Heo2025", "instruction-following dimension", "Heo ties instruction-following success to an internal dimension aligned with phrasing; the run adds algorithm prohibitions on code tasks and a variance-components estimate.", "(adjacent)")]),
    ("b3", "Ban enforced at the body opening: forcing the default's opening up to its first body token undoes the ban (P_open 0.98-1.00); a neutral def line undoes none (-0.12 to 0.01); the ban gives way at the first content token of the body (1 token on kth smallest, 10-30 elsewhere) (art__5akZ9W9iZM4)",
     [("Qi2025", "shallow safety alignment", "Replication of shallow-alignment / prefill fragility for a user-imposed algorithm prohibition. Addition: the locus is the first content token of the body after a neutral signature, not the first response tokens.", "ADJACENT-ONLY"),
      ("Zhu2024-AdapT", "challenging tokens", "Independent prior that the decisive (high-loss) code tokens sit at block openings, consistent with the run's locus.", "(supporting)"),
      ("Andriushchenko2025", "prefilling attack", "Prefilling is an established lever; the run applies it as a measurement (P_open), not an attack.", "(adjacent)")]),
    ("b4", "Signature vetoes respelled around: exact n-gram veto left 0 banned-sequence occurrences in 1,450 vetoed generations but the walk stalled on 6/6 tasks; the default returned by renaming (current_row/current_col), respelling (parent/parents) or near-miss syntax (T1 66-86% invalid); a sham veto kept the default; the distinctive veto cut T2 pass from 50/50 to 19/46 (art_ccAbfJVcv0LO; art_1AYTO1Epb_7t)",
     [("Biagiola2026", "low-probability regions", "These show constraint-induced distortion and correctness cost. The run adds that the ALGORITHM survives a lexical veto by respelling (the constraint moves the surface, not the idea), with a sham-veto control.", "ADJACENT-ONLY"),
      ("Park2024-GAD", "distort", "Pre-window (2024) distortion result; same addition.", "(adjacent)")]),
    ("b5", "No correct novel algorithm: 0/78 (iterations 1-2) and 0/38 (iteration 3) correct out-of-catalogue programs were novel (two blind judges + manual pass vs 472 known solutions); under the 2,000-word novelty instruction 84% of outputs claim novelty, 39% of those contain no code, 75% of the rest are catalogue algorithms (art_3tH2xtoZ7Gj2; art_ccAbfJVcv0LO)",
     [("Zhang2025-NoveltyBench", "less diversity than human writers", "Neighbours measure diversity or creativity relative to humans; none audits whether a correct program lies outside a known-solution catalogue. The run's zero is a different measurement (verified novelty).", "ADJACENT-ONLY"),
      ("Jangra2026-DivAlgo", "unable to reproduce", "Algorithmic diversity vs human solutions under prompting-based steering (no activation intervention; 'steer' means prompting).", "(adjacent)"),
      ("Lu2025-NeoCoder", "falls short", "Creativity vs humans with technique detection; no catalogue audit.", "(adjacent)")]),
    ("b6", "Random-push diversity: isotropic random directions at task-spec positions, layers 12-23, norm-matched to the ban displacement. kth smallest: 7/15 directions moved >=20% off the default, 5 reached correct-only Hill-1 >= 2 at pass >= 0.96 (best 2.92: size-k heap 19, quickselect 16, full sort 15; pass 1.00); two sum 2/3 at alpha 2; shortest path 3/15 at pass >= 0.88 (best Hill-1 1.97); no push moved a ban-failing task; a leave-one-task-out prohibition direction was no better than random (0/5) (art_pVlCZ272hDV7)",
     [("Khalid2026-NoiseSteering", "Residual stream noise consistently", "Activation noise for diversity is OCCUPIED as a method (the handbook's saturated lane). State the claim as idea-level (test-checked, mechanism-labelled), task-dependent (movable vs immovable tasks) and norm-calibrated to the ban, not as a new knob.", "PARTLY OCCUPIED (method occupied; idea-level measurement open)"),
      ("Zhu2026-STARS", "correctness check", "Closest FLAG-A candidate: activation steering, execution-checked outputs, temperature contrast; but the diversity object is test-input coverage, not which algorithm a program implements.", "(adjacent)"),
      ("Kim2026-REI", "code generation or open-ended", "Random embedding injection widens Pass@N on math only; code is explicitly open.", "(adjacent)"),
      ("ICLR27-DiversityWithoutDiscovery", "fairly compare", "Contemporaneous counterpoint: latent perturbation adds diversity without discovery (latent reasoners); consistent with the run's immovable tasks.", "(adjacent)"),
      ("Ho2025-SPREAD", "mathematical", "Pre-window (AAAI 2026) activation steering for diverse reasoning; math only.", "(adjacent)"),
      ("Jerge2026-NoisyCoconut", "latent trajectories", "Latent noise used for consensus/abstention, not solution-identity diversity.", "(adjacent)")]),
    ("b7", "Movability predicts compliance (screen): every task where some push at alpha <= 2 moved the default is a task where the ban works (6/6); no ban-failing task was moved (0/8), but 7 of those 8 had only 3 directions at alpha 1 (art_pVlCZ272hDV7; art_1AYTO1Epb_7t; art__5akZ9W9iZM4)",
     [("Fan2026-ASTEER", "macro-F1", "ASTEER predicts the outcome of the same white-box intervention; the run predicts a black-box PROMPT prohibition from ban-free white-box movability.", "ADJACENT-ONLY (FLAG B not fired)"),
      ("Kotawala2026", "linear probe", "Closest FLAG-B candidate: prompt-level compliance predicted from hidden states, but by a probe trained on compliance labels for prompt injection, not from perturbation sensitivity.", "(adjacent)"),
      ("Mishra2026", "Almost surely", "Formal reason why a white-box-to-black-box forecast is non-trivial.", "(context)"),
      ("Tan2026-Compliance", "decodability even without compliance", "Instruction decodable without compliance; steering toward compliance (no forecast from movability).", "(adjacent)"),
      ("Li2026-Routing", "routing problem", "Constraint knowledge present but not routed; no perturbation-sensitivity forecast.", "(adjacent)")]),
]

C = [
    ("C1", "Price of plan noise vs temperature and prompt knobs (H5 = best correct-only Hill-1 within 5 pass points): temperature 0.3-1.3 with top-k 10 / top-p 0.95 gave BFS 797/800 (thinking off) and 800/800 (on); with coupled seeds the algorithm changed in 0/30 seeds in 10/12 cells; semantic seed Hill-1 1.94 at 7 points; random pushes Hill-1 > 2 at 0-4 points on kth smallest and two sum (art_UoCVh2Qe5RZ0; art_pVlCZ272hDV7)",
     [("Ahmed2025-IFG", "token-level", "IFG is the text-level 'plan hot, words cold' analogue and reports pass@k gains on code. The run adds activation-level plan noise priced on the same tasks with test-checked labels and seed-coupled contrasts, but C1's contrast set lacks the text-level plan sampler.", "PARTLY OCCUPIED"),
      ("Ahmed2025-IFG", "higher temperature during the intent", "Fair tuning of the missing baseline: intent at its best temperature, response at default temperature.", "(baseline to add)"),
      ("Wang2025-PlanSearch", "lack of diversity", "Code-specific plan-level text sampler (observations -> plans -> code).", "(baseline to add)"),
      ("Lee2025", "low algorithmic diversity", "QUALIFIES the run: temperature > 1 can raise algorithmic diversity on other problems (at a correctness cost); the BFS null may be task-specific, so price temperature per task.", "(contradicting in part)"),
      ("Jangra2026-DivAlgo", "verbalized sampling Zhang", "Text-level knob baselines (temperature, verbalized sampling, iterative constrained generation) on algorithmic diversity.", "(adjacent)"),
      ("Narula2026-Lottery", "up to 100 pp", "Prompt cues as algorithm knobs; the run's semantic seed belongs to this family.", "(adjacent)"),
      ("ICLR27-RethinkingSteeringMath", "departure from greedy", "Reviewer-ready baseline: stochastic decoding matched to plan noise's departure from greedy.", "(baseline to add)"),
      ("Peeperkorn2024", "weakly correlated with novelty", "Consistent with the temperature null.", "(supporting)"),
      ("Zeng2026-ESamp", "surface-level lexical variation", "Token-level perturbation yields lexical, not strategy, variation (ICML 2026).", "(supporting)"),
      ("Geng2026-Gacha", "instruction-following problem", "Contemporaneous text-level plan sampler (instruction following + external RNG).", "(baseline candidate)"),
      ("Wu2025-Monoculture", "insufficient", "Sampling/prompting changes insufficient against algorithmic monoculture (ICLR 2025).", "(supporting)"),
      ("Burtch2026-Hitchhiker", "notably not affected", "Field evidence that AI assistance homogenises syntax rather than algorithms in human code.", "(adjacent)")]),
    ("C1-site", "Site specificity at matched dose on test-checked algorithm labels: task-spec positions at layers 12-23 vs read position, condition segment, generated tokens 1-32, layers 0-11, layers 24-35; entropy and word seeds (Level-1 sources) moved behaviour by <= 1 pp",
     [("Zhang2026-DiversityInjection", "fraction of source diversity", "Text-level framework (Level 0/1/2; WritingPrompts, Infinite Chats, NoveltyBench, Poetry Foundation, IBM ArgKP; GPT-5-mini, Qwen3-4B, DeepSeek-V3.2, Mistral-Large-3): no activation site, no code, no test-checked labels. The run adds sites inside the network at matched dose on algorithm labels; its <= 1 pp Level-1 seeds replicate the Level-1 < Level-2 ordering on code.", "PARTLY OCCUPIED"),
      ("Zhang2026-DiversityInjection", "no existing test-time method", "Positioning note: this gap claim omits IFG and PlanSearch (0 citations in the paper).", "(framing)"),
      ("Zhang2026-DiversityInjection", "evaluated only on Qwen3-4B", "Its temperature arm is single-model.", "(detail)"),
      ("Khalid2026-NoiseSteering", "only the last token position", "A site comparison exists (embedding / attention-logit / AENI / residual vs high temperature), but only at generated-token positions and on narrative diversity.", "(adjacent)"),
      ("Zhu2026-STARS", "two natural intervention points", "Intra-layer site comparison (o_proj vs MLP output) on test coverage.", "(adjacent)"),
      ("Jerge2026-NCGRPO", "prompt-encoding pass", "Prompt-state noise vs temperature, but during RL training on VLM geometry (contemporaneous, v1 2026-08-21).", "(adjacent)"),
      ("Nagarajan2025-SeedCond", "seed-conditioning", "Input-layer vs output-layer randomness on algorithmic-creativity tasks (ICML 2025).", "(adjacent)")]),
    ("C1-seed", "Same token seed across temperature vs plan-noise draws, thinking on and off: phrasing clusters rose from 3-4 (T 0.3) to 24-36 (T 1.3) on T1 with ideas fixed (art_UoCVh2Qe5RZ0; art_3iv5G76C3yoX)",
     [("Ravfogel2025-Gumbel", "same instantiation", "Methodological precedent for coupling sampling noise across interventions. No paper found that couples token seeds across temperatures and activation-noise draws to split idea changes from phrasing changes on test-checked labels; the design is the addition.", "ADJACENT-ONLY"),
      ("Ahmed2025-IFG", "dominated by changes in phrasing", "Asserted (citing Peeperkorn), not measured with coupled seeds.", "(adjacent)"),
      ("He2026-BeneathDiff", "surface-level edit diversity", "Surface vs mechanism split for agents' code edits (HiTemp baseline).", "(adjacent)"),
      ("Yun2025-PriceOfFormat", "structural tokens", "Collapse persists under high temperature.", "(supporting)")]),
    ("C2a", "Ban-free plan subspace (from forced-algorithm prompts at the task-specification states) must predict which random directions move the algorithm",
     [("ICLR27-BeforeTheFirstToken", "encoded before the first generated token", "Closest competitor (contemporaneous ICLR 2027 submission): a causal pre-generation subspace for a scalar (length). The run's addition: a categorical, test-checked object (algorithm) and a ban-free subspace that predicts the effect of RANDOM directions.", "PARTLY OCCUPIED"),
      ("ICLR27-BeforeTheFirstToken", "parallel and orthogonal", "Same decomposition the run's test implies; cite and contrast.", "(method overlap)"),
      ("Dong2025-ERP", "prompt representations", "Decodable plans in prompt states are occupied (ICML 2025).", "(occupied sub-claim)"),
      ("Ma2026-WheresThePlan", "only Gemma-3-27B", "Decodable is not causal.", "(adjacent)"),
      ("ICLR27-AJR", "mispredict intervention effects", "Why the run's prediction test is informative.", "(adjacent)"),
      ("Basu2026", "98.2% AUROC", "Knowledge-action gap; the handbook's bar for decodability claims.", "(context)"),
      ("DiCicco2026", "AUC of 0.881", "Code-specific decodability before generation (v3 number).", "(adjacent)"),
      ("Chen2026-Brewing", "linearly recoverable from the hidden representation", "Availability before readiness (v3 wording).", "(adjacent)"),
      ("Silva2026", "25 steps", "Latent programming horizon in agents.", "(adjacent)"),
      ("Galeone2026-DetectionVsControl", "detection-intervention gap", "Detection and control directions can diverge; the run's subspace-predicts-pushes test measures this gap for plans.", "(adjacent)"),
      ("Hendel2023", "single task vector", "Task vectors (pre-window) - compressed task representations.", "(background)"),
      ("Todd2024", "compact representation", "Function vectors (pre-window).", "(background)"),
      ("Pal2023-FutureLens", "48%", "Future tokens decodable from one hidden state (pre-window).", "(background)"),
      ("Wu2024-PlanAhead", "pre-caching", "Pre-caching vs breadcrumbs (pre-window).", "(background)")]),
    ("C2-geo", "Geometry and targeted pushes (default -> runner-up algorithm)",
     [("Wurgaft2026-ManifoldSteering", "cuts through off-manifold", "Geometry-aware steering with geodesic distances and an MDS isometry test exists (full-text grep: 'geodesic' 34 matches, 'MDS' 14, 'Isomap' 0). The run's addition is algorithm-level geometry on test-checked labels.", "PARTLY OCCUPIED"),
      ("Wurgaft2026-ManifoldSteering", "multidimensional scaling", "MDS isometry evidence.", "(method overlap)"),
      ("Rahman2026-CodeSteering", "difference-in-means", "Targeted code steering toward a chosen library or language anticipates the default -> runner-up push in kind; the run's object is the algorithm.", "(adjacent)"),
      ("Mishra2026", "formal separation", "Steered states are off the prompt-reachable manifold; relevant when comparing pushes with prompts.", "(context)")]),
    ("C3a", "Movability predicts ban compliance in a held-out family: a ban-free white-box quantity (escape fraction under random plan pushes) forecasts black-box prompt-ban compliance, with predictions committed before the family's first ban sample",
     [("Tang2026", "implementation priors", "Behavioural prior: constraints opposing defaults fail. The run adds a ban-free white-box forecast of prompt-ban compliance, pre-registered.", "OPEN (FLAG B not fired)"),
      ("Tang2026", "99%+ compliance", "Abstract wording is 'fail at rates of 10-100%'.", "(behavioural prior)"),
      ("Tang2026", "positive constraints", "Positive vs negative constraint asymmetry.", "(behavioural prior)"),
      ("Bhattarai2026-SteerabilitySignatures", "strongly correlate", "Predicts steerability (a white-box outcome), not prompt compliance.", "(adjacent)"),
      ("Yoon2026", "bias toward particular", "Mechanistic analogue of immovable defaults resisting prohibition.", "(adjacent)"),
      ("ICLR27-BreakTheRules", "late-layer bottleneck", "Compliance is decodable early but causally decided late.", "(adjacent)"),
      ("Fan2026-ASTEER", "steering refers exclusively", "ASTEER's 'steering' is activation engineering only; no prompting outcome is predicted.", "(adjacent)"),
      ("Kotawala2026", "only partly steerable", "Probe-readable compliance decision, only partly steerable (prompt injection).", "(adjacent)"),
      ("Heo2025", "instruction-following dimension", "Probe direction predicts compliance (instruction following).", "(adjacent)"),
      ("Li2026-Routing", "routing problem", "Routing, not knowledge.", "(adjacent)")]),
    ("C3b", "Ban landing: forecast WHICH alternative a prohibition installs (push-landing forecast, opening ladder)",
     [("Yoon2026", "promoting a favored", "Describes the landing mechanism at the fact level but does not forecast which alternative from a ban-free measure; the run's push-landing forecast is new.", "OPEN (closest: Yoon, contemporaneous)"),
      ("Zhou2026-Negation", "construction and suppression", "Negation as construction + suppression (ICML 2026).", "(adjacent)"),
      ("Narula2026-Lottery", "strict compliance is 73/120", "Positive naming nearly always lands; no prohibition-landing forecast.", "(adjacent)"),
      ("ICLR27-SilentCompliance", "reintroduce the excluded object", "Compliant answers still reintroduce excluded objects.", "(adjacent)"),
      ("Lu2025-NeoCoder", "copy previous solutions", "Denied solutions recur under stress-testing; no landing forecast.", "(adjacent)")]),
    ("C3c", "Novelty boundary: no correct off-catalogue algorithm up to breakage",
     [("RomeraParedes2024-FunSearch", "systematic evaluator", "Counter-reference: search + evaluator produces new programs. Scope the claim to single-sample generation under knobs, without search or an evaluator.", "ADJACENT-ONLY (scoped)"),
      ("Novikov2025-AlphaEvolve", "evaluators", "Same scope limit.", "(counter-reference)"),
      ("ICLR27-DiversityWithoutDiscovery", "borderline samples", "Supporting (contemporaneous).", "(supporting)"),
      ("ICLR27-RethinkingSteeringMath", "already supported by the model", "Supporting: steering moves among trajectories the model already supports.", "(supporting)"),
      ("Maveli2026-AlgoREval", "parametric code retrieval", "Supporting framing: named-algorithm code generation as retrieval.", "(supporting)"),
      ("Bhushan2026-AgentCreativity", "lack the capacity", "Contradicting in part: agents produce human-novel (LLM-judged) solutions, though not better ones.", "(contradicting in part)"),
      ("GraphNovelty2025", "established algorithms", "Hedged statement; the search-snippet wording 'not inventing novel techniques' is not in the paper.", "(supporting, hedged)"),
      ("Bystronski2025", "substantially increases generative diversity", "Diversity-boundary extension via embedding-space conditioning (diversity, not verified novelty).", "(adjacent)"),
      ("Deshpande2026", "steering strength reduces", "Stronger steering reduces diversity.", "(adjacent)"),
      ("Biagiola2026", "low-probability regions", "Pushing decoding into low-probability regions costs correctness - consistent with 'breakage before novelty'.", "(supporting)")]),
]


def table(rows):
    out = [HEAD]
    for no, claim, subs in rows:
        for j, (ref, sel, adds, verdict) in enumerate(subs):
            out.append(subrow(f"{no}{'abcdefghijklmnopqrstuvwxyz'[j]}", claim if j == 0 else "(same claim)", ref, sel, adds, verdict))
    return "\n".join(out)


def sat_table():
    out = ["| id | title | v1 date | venue status | claim(s) | O/I/C | verdict | contemp. (4 mo) | note |", "|---|---|---|---|---|---|---|---|---|"]
    for h in sorted(HITS, key=lambda h: (-h["score"], h["id"])):
        hid = h["id"]
        key = hid if hid in NUM else ("Kotawala2026" if hid == "venue:kotawala" else None)
        if key is None and hid.startswith("or:"):
            m = {"wJ8HkA8vGN": "ICLR27-DiversityWithoutDiscovery", "knirOusGcq": "ICLR27-BeforeTheFirstToken", "Dl1xo5fqnj": "ICLR27-AJR",
                 "oag3wgNLRh": "ICLR27-RethinkingSteeringMath", "tZaHwMrvq2": "ICLR27-BreakTheRules", "L09agUoh7d": "ICLR27-SilentCompliance"}
            key = m.get(hid[3:], hid if hid in NUM else None)
        if key is None:
            aid_to_ref = {q["arxiv_id"]: q["ref_key"] for q in QUOTES if q.get("arxiv_id")}
            key = aid_to_ref.get(hid)
        cit = c(key) if key in NUM else ""
        title = (h.get("title") or (S[NUM[key] - 1]["title"] if key in NUM else hid))[:80]
        ax = h["axes"]
        out.append(f"| {hid} {cit} | {cell(title)} | {h['v1_date']} | {cell(h['venue_status'])} | {h['claims']} | {ax['O']}/{ax['I']}/{ax['C']} | {h['verdict']} | {'yes' if h['contemporaneous_4mo'] else 'no'} | {cell(h['note'])} |")
    return "\n".join(out)


def counts_table():
    out = ["| family | identified (raw) | unique after de-dup | in window (screened) | passed keyword pre-screen | full-text checked & included | included (adjacent or occupying) |",
           "|---|---|---|---|---|---|---|"]
    for fam, v in COUNTS.items():
        if fam.startswith("_"):
            continue
        out.append(f"| {fam} | {v['identified_raw']} | {v['unique_after_dedup']} | {v['in_window_screened']} | {v['passed_keyword_prescreen']} | {v['full_text_checked_included']} | {v['included_adjacent_or_occupying']} |")
    t = COUNTS["_totals"]
    out.append(f"| total (unique records) | {t['raw_hits']} | {t['unique']} | {t['in_window']} | {t['keyword_pass_in_window']} | - | {t['verdict_counts'].get('adjacent', 0)} adjacent, {t['verdict_counts'].get('occupies the claim', 0)} occupying, {t['verdict_counts'].get('irrelevant', 0)} irrelevant (of {t['hits_given_verdicts']} scored) |")
    return "\n".join(out)


def hit_ref(hid):
    m = {"wJ8HkA8vGN": "ICLR27-DiversityWithoutDiscovery", "knirOusGcq": "ICLR27-BeforeTheFirstToken", "Dl1xo5fqnj": "ICLR27-AJR",
         "oag3wgNLRh": "ICLR27-RethinkingSteeringMath", "tZaHwMrvq2": "ICLR27-BreakTheRules", "L09agUoh7d": "ICLR27-SilentCompliance"}
    if hid.startswith("or:"):
        return m.get(hid[3:], hid if hid in NUM else None)
    if hid == "venue:kotawala":
        return "Kotawala2026"
    if hid in NUM:
        return hid
    return {q["arxiv_id"]: q["ref_key"] for q in QUOTES if q.get("arxiv_id")}.get(hid)


def claim_table():
    groups = [("b1 snap-back", "b1"), ("b2 wording", "b2"), ("b4 vetoes", "b4"), ("b6 random pushes", "b6"), ("b7 movability screen", "b7"),
              ("C1 knob price", "C1"), ("C1-site", "C1-site"), ("C1-seed", "C1-seed"), ("C2a plan subspace", "C2"),
              ("C2 geometry / targeted pushes", "C2-geometry"), ("C3a compliance forecast", "C3a"), ("C3b ban landing", "C3b"),
              ("C3c novelty boundary (b5)", "C3c"), ("FLAG A candidates", "FLAG-A"), ("FLAG B candidates", "FLAG-B")]
    out = ["| Claim | in-window hits scored | adjacent | occupying | contemporaneous adjacent (v1 > 2026-06-21 or ICLR 2027 submission) | closest in-window hits (score) |",
           "|---|---|---|---|---|---|"]
    for name, tag in groups:
        hs = [h for h in HITS if tag in h["claims"].split(",")]
        adj = [h for h in hs if h["verdict"] == "adjacent"]
        occ = [h for h in hs if h["verdict"].startswith("occupies")]
        con = [h for h in adj if h["contemporaneous_4mo"]]
        top = sorted(adj, key=lambda h: -h["score"])[:4]
        tops = "; ".join(f"{h['id']} {c(hit_ref(h['id'])) if hit_ref(h['id']) in NUM else ''} ({h['score']})" for h in top) or "none in window (closest neighbours are pre-window; see tables)"
        out.append(f"| {name} | {len(hs)} | {len(adj)} | {len(occ)} | {len(con)} | {tops} |")
    return "\n".join(out)


def corrections_table():
    out = ["| id | item | the run / plan says | the source says | status | replacement or action |", "|---|---|---|---|---|---|"]
    for r in CORR:
        out.append(f"| {r['id']} | {cell(r['item'])} | {cell(r['run_text_or_plan_says'])} | {cell(r['source_says'])} | {r['status']} | {cell(r['replacement_sentence'] or r['action'])} |")
    return "\n".join(out)


def search_log_summary():
    rows = [json.loads(l) for l in (EVID / "search_log.jsonl").read_text().splitlines()]
    agg = {}
    for r in rows:
        eng = r["engine"].split(" (")[0].split(" arXiv")[0] if r["engine"].startswith("E3") else r["engine"].split(" ")[0]
        if r["engine"].startswith("E3 arXiv web"):
            eng = "E3-web"
        k = (r["family"], eng)
        a = agg.setdefault(k, [0, 0, 0])
        a[0] += 1
        a[1] += r["n_results"] or 0
        a[2] += r["status"] == "ok"
    fams = sorted({k[0] for k in agg})
    engs = ["E1", "E2", "E3", "E3-web", "E4", "E5"]
    out = ["| family | " + " | ".join(engs) + " |", "|---|" + "---|" * len(engs)]
    for f in fams:
        cells = []
        for e in engs:
            a = agg.get((f, e))
            cells.append(f"{a[0]} calls / {a[1]} hits ({a[2]} ok)" if a else "-")
        out.append(f"| {f} | " + " | ".join(cells) + " |")
    return "\n".join(out), len(rows)


def qa_line():
    if not QA:
        return "Second pass not yet run."
    tot = sum(len(v) for v in QA.values())
    ok = sum(v.count("MATCH") for v in QA.values())
    return f"{ok}/{tot} quotes re-matched by an independent live fetch_grep pass (evidence/qa_second_pass.jsonl)"



def build():
    slog, n_calls = search_log_summary()
    t = COUNTS["_totals"]
    nq = len(QUOTES)
    nver = sum(q["status"] == "VERIFIED" for q in QUOTES)
    nabs = sum(q["status"] == "VERIFIED-ABSTRACT" for q in QUOTES)
    nrefs = len({q["ref_key"] for q in QUOTES})
    verdict_box = f"""## 2. Verdict box and flags (as of 2026-10-21)

| Claim | Lane verdict | Deciding reference(s) |
|---|---|---|
| b1 snap-back under exposure bans | ADJACENT-ONLY | Yoon et al. fact-level favoured-candidate promotion {c('Yoon2026')}; NeoCoder compliance decay {c('Lu2025-NeoCoder')} |
| b2 wording dominates compliance | PARTLY OCCUPIED (replication in a new setting) | Sclar et al. {c('Sclar2024')}; Heo et al. {c('Heo2025')} |
| b3 ban enforced at the body opening | ADJACENT-ONLY (mechanism parallels shallow alignment; locus new) | Qi et al. {c('Qi2025')}; AdapT {c('Zhu2024-AdapT')} |
| b4 vetoes respelled around | ADJACENT-ONLY | Biagiola et al. {c('Biagiola2026')}; GAD {c('Park2024-GAD')} |
| b5 no correct novel algorithm | ADJACENT-ONLY (scope to single-sample generation) | NoveltyBench {c('Zhang2025-NoveltyBench')}; DivAlgo {c('Jangra2026-DivAlgo')}; FunSearch/AlphaEvolve {c('RomeraParedes2024-FunSearch', 'Novikov2025-AlphaEvolve')} |
| b6 random-push diversity | PARTLY OCCUPIED (method occupied; idea-level measurement open) | Noise Steering {c('Khalid2026-NoiseSteering')}; STARS {c('Zhu2026-STARS')}; REI {c('Kim2026-REI')} |
| b7 movability predicts compliance (screen) | ADJACENT-ONLY | ASTEER {c('Fan2026-ASTEER')}; Kotawala {c('Kotawala2026')} |
| C1 plan-noise price vs temperature/prompt knobs | PARTLY OCCUPIED (contrast set incomplete) | IFG {c('Ahmed2025-IFG')}; PlanSearch {c('Wang2025-PlanSearch')}; Lee et al. {c('Lee2025')}; departure-matched decoding {c('ICLR27-RethinkingSteeringMath')} |
| C1-site matched-dose site specificity | PARTLY OCCUPIED | 2606.10302 {c('Zhang2026-DiversityInjection')}; Noise Steering sites {c('Khalid2026-NoiseSteering')}; STARS B.3 {c('Zhu2026-STARS')} |
| C1-seed same-seed design | ADJACENT-ONLY (design is the addition) | Gumbel counterfactuals {c('Ravfogel2025-Gumbel')}; IFG {c('Ahmed2025-IFG')} |
| C2a ban-free plan subspace predicts push effects | PARTLY OCCUPIED (decodability and a causal length subspace occupied; prediction of random-push effects on algorithm choice open) | Before the First Token {c('ICLR27-BeforeTheFirstToken')}; ERP {c('Dong2025-ERP')}; AJR {c('ICLR27-AJR')} |
| C2 geometry and targeted pushes | PARTLY OCCUPIED | Manifold Steering {c('Wurgaft2026-ManifoldSteering')}; Rahman et al. {c('Rahman2026-CodeSteering')} |
| C3a movability forecasts ban compliance | OPEN | nearest: Tang {c('Tang2026')}; ASTEER {c('Fan2026-ASTEER')}; Kotawala {c('Kotawala2026')} |
| C3b ban landing forecast | OPEN | nearest: Yoon et al. {c('Yoon2026')}; Zhou et al. {c('Zhou2026-Negation')} |
| C3c novelty boundary | ADJACENT-ONLY (scoped) | FunSearch {c('RomeraParedes2024-FunSearch')}; AlphaEvolve {c('Novikov2025-AlphaEvolve')}; Diversity Without Discovery {c('ICLR27-DiversityWithoutDiscovery')} |

**FLAG A: NOT FIRED.** No paper found measures test-checked, algorithm-level diversity under activation perturbation. Closest: STARS steers activations and checks generated tests by execution, but its diversity object is test-input coverage {c('Zhu2026-STARS')}. Random embedding injection is math-only and names code generation as future work {c('Kim2026-REI')}. NC-GRPO perturbs the prompt-encoding states during RL on VLM geometry {c('Jerge2026-NCGRPO')}. APTS uses probed-answer hidden states to separate solution paths by search, not perturbation {c('Fang2026-APTS')}. ESamp is a decoding method {c('Zeng2026-ESamp')}. DivAlgo's 'steering' is prompting {c('Jangra2026-DivAlgo')}.

**FLAG B: NOT FIRED.** No paper found predicts prompt-level ban or negative-constraint compliance from perturbation sensitivity or steerability. Closest: a supervised last-prompt-token probe predicts prompt-injection compliance (ROC-AUC 0.90; NeurIPS 2026 workshop) {c('Kotawala2026')}; Heo et al.'s instruction-following dimension {c('Heo2025')}; ASTEER predicts the success of the same white-box intervention, with only steering-strength-search baselines and zero matches for 'prompting' or 'compliance' {c('Fan2026-ASTEER')}; separation metrics predict steerability {c('Bhattarai2026-SteerabilitySignatures')}; SPARK uses hidden-state susceptibility to guide steering, not to forecast compliance {c('Zhang2026-SPARK')}.

**Two framing consequences.**
1. A reviewer will name the text-level plan sampler first for C1: IFG intent-hot/response-cold {c('Ahmed2025-IFG')}, 2606.10302's Diverse Outline/Keyword {c('Zhang2026-DiversityInjection')}, PlanSearch {c('Wang2025-PlanSearch')} and, contemporaneously, Gacha Decoding {c('Geng2026-Gacha')}. A second likely reviewer baseline is decoding matched to the perturbation's departure from greedy {c('ICLR27-RethinkingSteeringMath')}. Until both are run, C1's wording should be 'beats the token-level and prompt-seed knobs tested'.
2. Activation noise for diversity is a saturated method lane {c('Khalid2026-NoiseSteering', 'Zhu2026-STARS', 'Kim2026-REI')}, and there are contemporaneous negative results on latent perturbation {c('ICLR27-DiversityWithoutDiscovery', 'ICLR27-RethinkingSteeringMath')}. The paper's claims should therefore be about where the algorithm is chosen (task-specification states), what is movable, and what this forecasts about bans, not about a new knob.
"""
    method = f"""# Checking our claims against published work

*Retrieval date: 2026-10-21. Scope: iteration-3 claims (Table 92b) and iteration-4 claims (Table 92c) of this run, plus a dated saturation search over papers with arXiv v1 dates 2026-01-01 to 2026-10-21. Every quote below is copied from the paper's own versioned text (arXiv HTML, else the PDF, else a venue or OpenReview abstract) and re-checked with the plan's normalisation rule.*

## 1. Scope, date and method

- **Sources and versions.** Version numbers, v1 dates and comment or journal-reference lines for {len(META)} arXiv IDs come from the arXiv API {c('arXivAPI')}. Full texts of the latest versions were cached with the aii-web-tools fetch core: arXiv HTML first, PDF where HTML was missing (2604.03380v2 and 2604.07192v2). Earlier versions were fetched where the run's text depends on them (2606.14530 v1/v2, 2606.17648 v1/v2, 2610.09571 v1, 2604.03380 v1, 2605.11936 v1, 2604.07192 v1, 2605.07984 v1, 2604.27251 v1).
- **Quotes.** {nq} quotes from {nrefs} references were checked: {nver} VERIFIED against full text and {nabs} VERIFIED-ABSTRACT, where only an abstract record exists (OpenReview ICLR 2027 submissions, the NeurIPS 2026 workshop page). There were 0 MISMATCH. Matching collapses whitespace, undoes PDF line-end hyphenation, maps ligatures, curly quotes and dashes, and strips html2text emphasis and escapes. A quote with [...] matches only if every segment occurs in order. QA: {qa_line()}.
- **Venues.** Venue status comes only from arXiv comment or journal-ref lines or from proceedings and virtual-site pages: ACL Anthology, iclr.cc, icml.cc, neurips.cc, OpenReview API, Nature. Secondary sites were used for discovery only.
- **Saturation search.** 8 query families and 25 queries, each run on E1 (OpenAlex/Crossref scholarly search via the skill script), E3 (arXiv API newest-first, with arxiv.org/search as a logged fallback after HTTP 429) and E4 (Semantic Scholar API, year=2026). E5 (OpenReview ICLR 2027 pool) covered families S1, S3 and S4. There were 28 extra general-web E2 and lookup calls, plus forward citations of 6 nearest neighbours: {n_calls} logged calls in total. The search identified {t['raw_hits']} hits, {t['unique']} unique after de-duplication, and {t['in_window']} in the date window. Of these, {t['keyword_pass_in_window']} passed a documented keyword pre-screen on title and abstract, then a manual title and abstract screen; {t['hits_given_verdicts']} were scored on the rubric's three axes.
- **Rubric.** O = object (algorithm or solution identity checked by execution or a mechanism label); I = the claim-specific intervention; C = the claim-specific contrast. Each axis scores 1 for a match, 0.5 for a partial match and 0 otherwise. A hit with a total of 2.5 or more occupies the claim; 1 to 2 is adjacent; below 1 is irrelevant. This relaxes the plan's integer rubric so partial matches count; under the literal rubric, no hit occupies any claim either.
- **Contemporaneity.** The plan's convention tags v1 after 2026-06-21 as contemporaneous (four months). The ICLR 2027 Reviewer Guide rule is stricter for authors' obligations: two months, peer-reviewed publication only, and 'arXiv is not considered a peer-reviewed venue' {c('Policy-ICLR2027')}. Its stated 'September 16' deadline conflicts with the Dates page (paper deadline Sep 25 '26) {c('Policy-ICLR2027-Dates')}. The four-month rule was the ICLR 2025 FAQ's {c('Policy-ICLR2025')}.
- **Departures.** There was one screener, with no dual screening or inter-rater agreement. The keyword pre-screen reduced manual load. Semantic Scholar's forward-citation coverage of 2026 preprints was sparse (35 citers in total). OpenReview submissions were read at abstract level only.
"""
    sections = [method, verdict_box,
                "## 3. Table 92b - iteration-3 claims vs nearest published findings\n\n" + table(B),
                "## 4. Table 92c - iteration-4 claims vs nearest published findings\n\n" + table(C)]
    per_claim = f"""## 5. Saturation search (dated 2026-10-21)

### 5.1 Saturation verdict per claim

{claim_table()}

No hit occupies any claim. The ICLR 2027 pool contains the submissions of 2606.10302 (OpenReview AnsxpIWvcZ) and HiDRA (MxTe9wDyk8), and six other closely relevant submissions cited above.

### 5.2 Counts per query family (PRISMA-style)

{counts_table()}

### 5.3 Search log summary (calls / hits per family x engine; full log in evidence/search_log.jsonl)

{slog}

### 5.4 Scored hits (v1 2026-01-01 to 2026-10-21, plus ICLR 2027 submissions)

{sat_table()}
"""
    corr = "## 6. Corrections to the run's current citations\n\n" + corrections_table() + f"""

Sources for the venue rows: ICML 2025 EXAIT listing {c('Venue-ICML2025-IFG')}; ICML 2026 workshop listing for Manifold Steering {c('Venue-ICML2026-Manifold')}; ICML 2026 poster page for the Invisible Lottery {c('Venue-ICML2026-Lottery')}; ICML 2026 workshop listing for REI {c('Venue-ICML2026-REI')}; ACL Anthology for NeoCoder {c('Venue-ACL-NeoCoder')} and Lee et al. {c('Venue-ACL-Lee2025')}; ICLR 2025 award blog {c('Venue-ICLR2025-Awards')}; ICLR 2025 poster pages {c('Venue-ICLR2025-Heo', 'Venue-ICLR2025-PlanSearch', 'Venue-ICLR2025-Monoculture')}; OpenReview COLM 2025 record for NoveltyBench {c('Venue-OR-NoveltyBench')}; ICML 2025 page for seed-conditioning {c('Venue-ICML2025-SeedCond')}.
"""
    unver = """## 7. Unverified references (no numbers are taken from these)

- Chatzi et al., 'Counterfactual Token Generation in Large Language Models' (arXiv 2409.17027): a candidate second precedent for C1-seed. Its metadata request hit HTTP 429 and the text was not read.
- 'Rogue Scalpel' (arXiv 2509.22067): a search snippet said random-direction steering can raise harmful compliance. Not fetched.
- 'Belief Dynamics Reveal the Dual Nature of In-Context Learning and Activation Steering' (PMLR v306): seen only in a search result. Not fetched.
- AlphaResearch (arXiv 2511.08522): the snippet claim that LLM judges favour solutions within existing knowledge boundaries was not found in v2 (0 matches); not used.
- Interaction-smells study (arXiv 2603.09701): a snippet said a model broke confirmed negative constraints a turn later. HTML returned 404 and the text was not read.
- A secondary summary's '55,545 experiments' for the Invisible Lottery: not on the ICML page or arXiv v1, both of which say 46,535.
- DRUGS noise-injection library (github.com/EGjoni/DRUGS): software; not checked (optional in the plan).
- 'On the Effect of Sampling Diversity in Scaling LLM Inference' (arXiv 2502.11027v5): fetched but not quoted (optional, pre-window).
"""
    conf = f"""## 8. Confidence, contradicting evidence and what would change the verdicts

- **Confidence that no paper occupies C3a, C3b or the idea-level part of C1 (FLAG A and FLAG B not fired): moderate-high.** The basis is {t['unique']} unique records on four engines, the ICLR 2027 pool and forward citations. The residual risk is a competitor written in unexpected vocabulary, or one indexed after 2026-10-21. A single screener did the screening.
- **Contradicting or qualifying evidence.**
  - Temperature above 1.0 can raise algorithmic diversity in other code settings, at a correctness cost {c('Lee2025')}. DivAlgo counts temperature variation among its diversity strategies {c('Jangra2026-DivAlgo')}. The run's BFS null should therefore be presented as task-specific.
  - LLM agents show greater H-creativity than medal-winning humans under LLM-judged novelty {c('Bhushan2026-AgentCreativity')}.
  - Search with an evaluator produces new programs {c('RomeraParedes2024-FunSearch', 'Novikov2025-AlphaEvolve')}.
  - Departure-matched stochastic decoding recovers most of steering's gains in maths {c('ICLR27-RethinkingSteeringMath')}, which a reviewer may expect to hold for plan noise too.
- **What would change the verdicts.**
  - An ICLR 2027 or arXiv paper that measures algorithm identity under activation noise would turn C1 to OCCUPIED. That paper might come from the authors of STARS or REI, whose stated future work is code {c('Kim2026-REI')}.
  - A paper that forecasts prompt-ban compliance from steerability would turn C3a to OCCUPIED.
  - Full-text reading of the ICLR 2027 'Before the First Token' and 'AJR' submissions could raise C2a from PARTLY OCCUPIED to OCCUPIED, if either predicts the effects of random directions.
"""
    fu = """## 9. Follow-up questions

1. Must C1's contrast set add a text-level plan sampler on the same tasks with correct-only labels? Candidates are IFG intent sampling (intent at its best temperature, response at default), 2606.10302's Diverse Outline/Keyword, PlanSearch observations and Gacha Decoding. This is the comparison a reviewer will name first.
2. Should the knob artifact report a label-level transmission score, I(label; noise draw)/H(noise draw), for plan noise vs temperature, adapting 2606.10302's Definition 1 to algorithm labels?
3. Should the novelty claim (C3c/b5) be scoped explicitly to single-sample generation under knobs, without search or an evaluator, to pre-empt FunSearch and AlphaEvolve?
4. Venue corrections: keep 'ICML 2026' for 2606.04057 (confirmed main-track poster); downgrade 2605.05115 to an ICML 2026 MI-workshop spotlight; cite IFG as an ICML 2025 EXAIT workshop paper. Should the run's text adopt these now?
5. Tang wording: 'implementation priors' is verified in Sec. 5.3 of v1 and v2. Should the run cite the v2 PDF and quote the abstract as 'fail at rates of 10–100%'?
6. Should C1 also add a decoding baseline matched to plan noise's departure from greedy (as in the ICLR 2027 'Rethinking Activation Steering' submission)?
7. Should C2a be positioned explicitly against 'Before the First Token' (parallel vs orthogonal decomposition of interventions) and AJR (decoders mispredict intervention effects)?
"""
    report = "\n\n".join(sections + [per_claim, corr, unver, conf, fu])
    import re as _re
    cited = set()
    for m in _re.finditer(r"\[(\d+(?:,\s*\d+)*)\]", report.replace(sat_table(), "")):
        cited.update(int(x) for x in m.group(1).split(","))
    rest = [i + 1 for i in range(len(S)) if i + 1 not in cited]
    other = "### 5.5 Other screened records and evidence pages (cited for completeness)\n\n" + "\n".join(
        f"- {S[i - 1]['title']} [{i}]: {S[i - 1]['summary']}" for i in rest)
    report = report.replace("## 6. Corrections to the run's current citations", other + "\n\n## 6. Corrections to the run's current citations")
    # answer = same content minus the long scored-hits table (kept in the report)
    answer = report.replace("### 5.4 Scored hits (v1 2026-01-01 to 2026-10-21, plus ICLR 2027 submissions)\n\n" + sat_table() + "\n",
                            "### 5.4 Scored hits\n\nThe 57 scored hits with O/I/C scores, v1 dates, venue status and contemporaneity tags are in research_report.md section 5.4 and evidence/saturation_hits.jsonl.\n")
    return report, answer


def best_span(quote, raw, min_words):
    """Longest run of consecutive words of the quote that occurs LITERALLY (whitespace-collapsed only) in the fetched
    page text - no markdown, emphasis, ligature or hyphenation normalisation - so the passage is an exact substring of
    what a fetcher sees (html2text markdown for HTML, PyMuPDF text for PDFs, raw JSON for API records)."""
    import re as _re
    flat = _re.sub(r"\s+", " ", raw)
    best = ""
    for seg in _re.split(r"\s*\[\.\.\.\]\s*", quote):
        words = seg.split()
        for L in range(len(words), max(min_words, len(best.split()) + 1) - 1, -1):
            hit = next((" ".join(words[i:i + L]) for i in range(len(words) - L + 1) if " ".join(words[i:i + L]) in flat), None)
            if hit:
                best = hit
                break
    return best or None


VENUE_LOCATOR = {
    "venue_icml25_ifg": "page header: 'Poster in Workshop:' label, linking to this workshop",
    "venue_icml26_manifold": "page header: 'Spotlight in Workshop:' label, linking to this workshop",
    "venue_neurips26_injection": "page header: 'Poster in Workshop:' label, linking to this workshop",
}


def sources_json():
    from common import load_text
    out = []
    for i, s in enumerate(S):
        url = s["url"]
        if url.startswith("https://openreview.net/forum?id="):        # cite the record actually read (OpenReview API)
            via = next((r.get("via") for r in INDEX_ROWS if r.get("url") == url and r.get("via")), None)
            if via:
                url = via
        rec = {"index": i + 1, "url": url, "title": s["title"], "summary": s["summary"] or s["title"],
               "authors": s["authors"], "year": s["year"], "supporting_passages": []}
        for q in QUOTES:
            if NUM.get(q["ref_key"]) != i + 1 or q["url"] != s["url"] or len(rec["supporting_passages"]) >= 3:
                continue
            ckey = next((r["key"] for r in INDEX_ROWS if r["url"] == q["url"]), None)
            if ckey is None:
                continue
            venue = ckey.startswith(("venue_", "policy_"))
            span = best_span(q["quote"], load_text(ckey), 4 if venue else 6)
            if span and all(span != p["quote"] for p in rec["supporting_passages"]):
                loc = q["section_or_page"]
                if ckey in VENUE_LOCATOR and "page header" in loc:
                    loc = VENUE_LOCATOR[ckey]
                rec["supporting_passages"].append({"quote": span, "locator": loc})
        out.append(rec)
    return out


def main():
    report, answer = build()
    (WS / "research_report.md").write_text(report + "\n", encoding="utf-8")
    (CACHE / "answer.md").write_text(answer + "\n", encoding="utf-8")
    (CACHE / "sources.json").write_text(json.dumps(sources_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"report {len(report)} chars; answer {len(answer)} chars; sources {len(S)}")


if __name__ == "__main__":
    main()
