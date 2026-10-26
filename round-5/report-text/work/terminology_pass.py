"""Terminology pass over the iteration-5 text (run after assemble.py).

Applies the renames asked for by the terminology check: no label codes in the
text, no quoted coinages, and hyphenated coinages replaced by the field's word
or by a phrase defined once ("we call ...").  It touches only text written in
iteration 5: the iteration-5 section and the closing (everything from
"# Iteration 5" up to "# References"), and the iteration-5 correction notes in
earlier sections, which are addressed by exact strings that occur once.
Numbers, citations and [FIGURE:...] / [ARTIFACT:...] markers are not touched.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / 'paper_draft.md'

# ---------------------------------------------------------------------------
# 1. Iteration-5 section and closing: literal replacements, in order.
#    (old, new, minimum count)
# ---------------------------------------------------------------------------
MINE = [
    # --- label codes -------------------------------------------------------
    ('one 23 GB NVIDIA L4', 'one 23 GB NVIDIA GPU', 2),
    ('Confirmation on fresh slots (S2; N = 50 per cell;', 'Confirmation on fresh slots (N = 50 per cell;', 1),
    ('| twin S2 pass |', '| twin pass, fresh slots |', 1),
    ('We write H5 for the 5-point Hill-1 and DMD for departure-matched decoding in the tables; '
     "the margin D_t is plan noise's H5 minus the best text sampler's.",
     'In Table 207 the margin is the 5-point Hill-1 of plan noise minus that of the best text sampler.', 1),
    ('| Plan noise H5 [95%] |', '| Plan noise, 5-point Hill-1 [95%] |', 1),
    ('| Plan noise H5 |', '| Plan noise, 5-point Hill-1 |', 1),
    ('| Flag | Margin D_t |', '| Flag | Margin |', 1),
    ('with hull H5 within 0.08 of the committed hull', 'with the 5-point Hill-1 of the hull within 0.08 of the committed value', 1),
    ('| Task | α | DMD temperature | plan noise KL per token | DMD KL per token | plan noise | DMD | TWIN | McNemar PN vs DMD (PN-only/DMD-only, p) |',
     '| Task | α | Temperature at matched departure | plan noise KL per token | matched departure KL per token | plan noise | matched departure | TWIN | McNemar, plan noise against matched departure (only plan noise : only matched departure, p) |', 1),
    # Table 92d codes and cross references
    (' (92c C1b)', ' (Table 92c)', 1),
    (' (92c C1c)', ' (Table 92c)', 1),
    (' (92c C1-siteb/c)', ' (Table 92c)', 1),
    (' (92c C1j)', ' (Table 92c)', 1),
    (' (92c C1g)', ' (Table 92c)', 1),
    (' (92c C1-sitef)', ' (Table 92c)', 1),
    ('| (cross-ref 92c C3c) |', '| (see Table 92c) |', 1),
    ('| (cross-ref 92c) |', '| (see Table 92c) |', 6),
    # --- Table 168: report locations without quotes or internal labels ----
    ("| Site conclusions | 'At any dose' contradicted", '| Site conclusions | The phrase *at any dose* contradicted', 1),
    ("| 0a | Table 162 '4 of 4' |", '| 0a | Table 162, the count of 4 of 4 |', 1),
    ("| 0a | Section 4.10 'Inconclusive' entry |", '| 0a | Section 4.10, the entry under Inconclusive |', 1),
    ("| 0a | Closing paragraph 'Whether push movability predicts which bans a model obeys is open. ...' (last sentence) |",
     '| 0a | Closing paragraph on push movability as a forecast of which bans a model obeys (last sentence) |', 1),
    ("| 0b | 'Inconclusive: The site claim' (append) |", '| 0b | Section 4.10, the site claim under Inconclusive (append) |', 1),
    ("| 0c | Every 'the landing is a property of the task' (and closing paragraph 2 'where it can is a property of the task') |",
     '| 0c | Every statement that the landing is a property of the task (and the statement in closing paragraph 2 that where it can is a property of the task) |', 1),
    ('| 0d | Section 4.3 (PNPLAIN_a1, executed but not reported) |', '| 0d | Section 4.3 (plan noise on the plain prompt at alpha 1, executed but not reported) |', 1),
    ('| 0d | Table 122 exp21 row |', '| 0d | Table 122, row of the experiment of Section 4.5 |', 1),
    ('| 0e | exp21 seed-coupled plan-noise counts (Table 1ac / Section 4.5) |', '| 0e | Seed-coupled plan noise counts (Section 4.5) |', 1),
    ('| 0e | Tables 123, 126, 164 and closing paragraph 2 best-cell numbers |', '| 0e | Tables 123, 126, 164 and closing paragraph 2, numbers of the best cells |', 1),
    ("| 0e | Section 4.11 and 'What remains open' (signed progress) |", '| 0e | Section 4.11 and the open questions of the closing (signed progress) |', 1),
    ("| 0e | 'What remains open' |", '| 0e | The open questions of the closing |', 1),
    ("| 0g | Section 4.2.1 'reaches 1.5 within 20 points' sentence |", '| 0g | Section 4.2.1, the sentence on reaching 1.5 within 20 points |', 1),
    # --- quoted words in prose ---------------------------------------------
    ('the record\'s "22 of 35 cells" for signed progress', 'the record\'s count of *22 of 35 cells* for signed progress', 1),
    ('"at any dose"', '*at any dose*', 1),
    ("so the 'default' DFS came from a 10-sample pilot", 'so the default DFS came from a 10-sample pilot', 1),
    ("the forced 'can' rate", 'the forced can rate', 1),
    ("the forced 'can' count", 'the forced can count', 1),
    ("the conservative 'unknown' label of the array-scan Dijkstra probe", 'the conservative label unknown for the probe of Dijkstra with an array scan', 1),
    ("NOT 'first base-vs-tuned algorithm-level comparison' (premise flag partly fired)",
     'not the first comparison of base and tuned models at the algorithm level (premise flag partly fired)', 1),
    ("A random-task control for any 'targeting' claim", 'A control with random tasks for any claim of targeting', 1),
    ("| A per-task, pre-registered forecast of the landing identity (runner-up) scored on matched events — none found |",
     '| A preregistered forecast per task of the landing identity (runner-up) scored on matched events; none found |', 1),
    # --- possessive pairs that read as quoted spans --------------------------
    ("supported if plan noise's 5-point Hill-1 is at least the best text sampler's on at least 3",
     'supported if the 5-point Hill-1 of plan noise is at least that of the best text sampler on at least 3', 1),
    ("with Step 1's beta and iteration 4's escape fractions", 'with the beta of Step 1 and the escape fractions of iteration 4', 1),
    ("(the teacher-forced log-probability margin of the default's opening over the runner-up's)",
     '(the margin in log probability, under teacher forcing, of the opening of the default over that of the runner-up)', 1),
    ("the runtime merit gap of the runner-up's reference against the default's (",
     'the runtime merit gap between the reference programs of the runner-up and of the default (', 1),
    # --- defined terms of this iteration -------------------------------------
    ('A task is *base-diverse* when beta is at least 0.2, *base-collapsed* when beta is below 0.05, and intermediate between.',
     'We call a task *diverse in the base* when beta is at least 0.2 and *collapsed in the base* when beta is below 0.05; between the two it is intermediate.', 1),
    ('while the base model was base-diverse on 5 (kth smallest, shortest path, connected components, grid and top-k frequent), intermediate on 7 and base-collapsed on 3 (',
     'while 5 tasks were diverse in the base (kth smallest, shortest path, connected components, grid and top-k frequent), 7 intermediate and 3 collapsed in the base (', 1),
    ('while the base model was base-diverse on 5 and intermediate on 7', 'while 5 tasks were diverse in the base and 7 intermediate', 1),
    ('(base-diverse on 5 of the 15 existing tasks and intermediate on 7)', '(5 of the 15 existing tasks are diverse in the base and 7 intermediate)', 1),
    ('Base-collapsed tasks did not move', 'Tasks collapsed in the base did not move', 1),
    ('on new tasks base-diverse tasks that never move are common', 'on new tasks those diverse in the base that never move are common', 1),
    ('on 1 of 5 base-diverse Qwen3-8B tasks', 'on 1 of 5 Qwen3-8B tasks diverse in the base', 1),
    ('4 of 10 base-diverse new units', '4 of 10 new units diverse in the base', 1),
    ('what makes a base-diverse task immovable', 'what makes a task diverse in the base immovable', 2),
    ('base-diverse tasks such as count primes', 'tasks diverse in the base such as count primes', 1),
    ('exactly the base-diverse tasks whose', 'exactly the tasks diverse in the base whose', 1),
    # borrowed shift (another task's base direction)
    ("beats a matched-norm random displacement and a cross-task base shift (another task's base-minus-instruct direction at the same norm)",
     "beats a matched-norm random displacement and what we call a *borrowed shift* (another task's base minus instruct direction at the same norm)", 1),
    ("a cross-task base shift (another task's mean base-minus-instruct direction at the same norm)",
     "the borrowed shift (another task's mean base minus instruct direction at the same norm)", 1),
    ('against the cross-task control on kth smallest', 'against the borrowed shift on kth smallest', 1),
    ('| cross-task, ', '| borrowed shift, ', 12),
    ('| Against cross-task |', '| Against borrowed shift |', 1),
    ('the per-task mean D has cross-task cosine 0.76 to 0.88', 'the per-task mean D has a cosine across tasks of 0.76 to 0.88', 1),
    ('with a matched-random, a cross-task and a read-position control on the same slots',
     'with a matched random control, a borrowed shift and a transplant at the read position on the same slots', 1),
    ('Random and cross-task controls that copy', 'Random controls and borrowed shifts that copy', 1),
    ('and the cross-task control is itself broken', 'and the borrowed shift is itself broken', 1),
    ('an equally large random or cross-task displacement is destructive', 'an equally large random displacement or borrowed shift is destructive', 1),
    ('controls: read position, blocks 0-11/24-35, matched-random, cross-task |', 'controls: read position, blocks 0-11/24-35, matched random, borrowed shift |', 1),
    ('matched-norm random displacement and cross-task patch controls', 'matched-norm random displacement and patches borrowed from other tasks as controls', 1),
    ('an isotropic or cross-task displacement of comparable size', 'an isotropic displacement or borrowed shift of comparable size', 1),
    ('matched-random control |', 'matched random control |', 1),
    # decoding at matched departure
    ('the text-level plan samplers and departure-matched decoding (a decoding temperature',
     'the text-level plan samplers and what we call *decoding at matched departure* (a decoding temperature', 1),
    ('departure-matched decoding', 'decoding at matched departure', 14),
    # push toward the base (was: de-sharpening)
    ('- *The de-sharpening push* along the base-minus-instruct direction escapes',
     '- *The push toward the base*: a push along the base minus instruct direction, which we call a push toward the base, escapes', 1),
    ('de-sharpening push; reverse transplant', 'push toward the base; reverse transplant', 1),
    ('**The de-sharpening push and the reverse transplant.**', '**The push toward the base and the reverse transplant.**', 1),
    ('The de-sharpening claim is DISCONFIRMED.', 'The claim for the push toward the base is DISCONFIRMED.', 1),
    ('- *The de-sharpening push.* A push along', '- *The push toward the base.* A push along', 1),
    ('**Table 186.** De-sharpening push along unit(D)', '**Table 186.** Push toward the base along unit(D)', 1),
    ('| De-sharpening push | method and random-direction control occupied', '| Push toward the base | method and control with random directions occupied', 1),
    ('| De-sharpening push: push the instruct model along the base-minus-instruct direction vs isotropic pushes at matched norm |',
     '| Push toward the base: push the instruct model along the base minus instruct direction against isotropic pushes at matched norm |', 1),
    ('base-minus-instruct', 'base minus instruct', 4),
    ('instruct-minus-base', 'instruct minus base', 2),
    ('as a fraction of the instruct-to-base twin gap', 'as a fraction of the gap between the instruct and base twins', 1),
    ('replication of PASTA-style aligned-minus-base ablation in a new setting', 'replication of the PASTA ablation of the aligned minus base direction in a new setting', 1),
    ('ablation of an aligned-minus-base direction during decoding', 'ablation of an aligned minus base direction during decoding', 1),
    # enumerate and pick
    ('enumerate-and-pick (the model lists algorithms and an external random draw picks one)',
     'a sampler we call *enumerate and pick* (the model lists algorithms and an external random draw picks one)', 1),
    ('enumerate-and-pick', 'enumerate and pick', 4),
    ('Enumerate-and-pick', 'Enumerate and pick', 2),
    # base intent
    ('and a base-written intent (the base model writes a one-sentence intent and the instruct model writes the code)',
     'and what we call *base intent* (the base model writes an intent of one sentence and the instruct model writes the code)', 1),
    ('and a base-written intent, in which Qwen3-8B-Base writes', 'and base intent, in which Qwen3-8B-Base writes', 1),
    ('two sum the base-written intent won', 'two sum, base intent won', 1),
    ('rests on the base-written intent and enumerate and pick', 'rests on base intent and on enumerate and pick', 1),
    ('The base-written intent keeps the pass rate high', 'Base intent keeps the pass rate high', 1),
    ('a base-written intent won on connected components', 'base intent won on connected components', 1),
    ('The base-written intent, which beat plan noise', 'Base intent, which beat plan noise', 1),
    ('whether the base-written intent, the best knob', 'whether base intent, the best knob', 1),
    ('Base-intent arm = sentence-granularity instance of base-aligned collaboration;',
     'The base intent arm is an instance of base-aligned collaboration at the level of sentences;', 1),
    ('it is itself a sentence-level form of that collaboration', 'it is itself a form of that collaboration at the level of sentences', 1),
    # remeasurement
    ('each with a paired parent re-measure,', 'each with a paired remeasurement of its parent,', 1),
    ('(P parent re-measure, V variant;', '(P remeasured parent, V variant;', 1),
    ('(parent re-measure, pooled over both alphas)', '(remeasured parent, pooled over both alphas)', 1),
    ('re-measurement', 'remeasurement', 4),
    ('re-measured', 'remeasured', 4),
    # knobs outside the exposure class
    ('**Table 172.** Best non-exposure knob per task.', '**Table 172.** Best knob outside the exposure class per task.', 1),
    ('| Best non-exposure knob within 5 points |', '| Best knob outside the exposure class within 5 points |', 1),
    ('| A non-exposure knob reaches 1.5 within 20 points |', '| A knob outside the exposure class reaches 1.5 within 20 points |', 1),
    ('no non-exposure knob reaches', 'no knob outside the exposure class reaches', 2),
    # hyphenated names of the field and of models
    ('Clopper-Pearson', 'Clopper–Pearson', 1),
    ('Misra-Gries', 'Misra–Gries', 1),
    ('DeepSeek-Coder', 'DeepSeek Coder', 1),
    ('Boyer-Moore vote', 'Boyer–Moore majority vote', 8),
    ('Eratosthenes sieve', 'sieve of Eratosthenes', 6),
    ('Atkin sieve', 'sieve of Atkin', 5),
    ('Sundaram sieve', 'sieve of Sundaram', 1),
    ('NC-GRPO, Nagarajan et al.', 'Jerge et al., Nagarajan et al.', 1),
    # other hyphenated compounds, one place each
    ('Code; activation-noise comparison', 'Code; comparison with activation noise', 1),
    ('and arm-label shuffles centred at 1.6 wins', 'and shuffles of the arm labels centred at 1.6 wins', 1),
    ('| Ban-unit ratio |', '| Ban unit ratio |', 1),
    ('| ban-unit ratio (dose check) |', '| ban unit ratio (dose check) |', 3),
    ('## 5.9 Positioning: base-model variety,', '## 5.9 Positioning: variety in the base model,', 1),
    ('base-to-tuned activation patching [88, 89, 90]', 'activation patching from base into tuned models [88, 89, 90]', 1),
    ('replication of base-vs-aligned narrowing at the algorithm level on code', 'replication of the narrowing from base to aligned models at the algorithm level on code', 1),
    ('| Base-vs-instruct pairing (DivAlgo has none) |', '| Pairing of base and instruct models (DivAlgo has none) |', 1),
    ('| baseline-to-add |', '| baseline to add |', 1),
    ('excluded brute-force methods', 'excluded brute force methods', 1),
    ('measured on calibration-only prefixes', 'measured on prefixes used only for calibration', 1),
    ('with both models given identical chat-templated token ids', 'with both models given identical token ids under the chat template', 1),
    ('same chat-templated prompt for base and instruct', 'same prompt under the chat template for base and instruct', 1),
    ('Given the same chat-templated prompt,', 'Given the same prompt under the chat template,', 1),
    ('or the variants with a cluster-preserving permutation', 'or the variants with a permutation that preserves clusters', 1),
    ('shared the code-stage uniform stream', 'shared the uniform stream of the code stage', 1),
    ('| contradicts-in-part |', '| contradicts in part |', 4),
    ('One CPU-only evaluation repaired', 'One evaluation on CPU only repaired', 1),
    ('External cross-check with independent TheAlgorithms implementations', 'External check with independent TheAlgorithms implementations', 1),
    ('(post hoc, deviation D-assoc-mapping)', '(post hoc, logged as a deviation)', 1),
    ('| Default-drop sensitivity disconfirms;', '| The drop sensitivity disconfirms;', 1),
    ('Under the preregistered default-drop sensitivity it is DISCONFIRMED',
     'Under the preregistered sensitivity that measures compliance as the drop in the default share, which we call the *drop sensitivity*, it is DISCONFIRMED', 1),
    ('disconfirmed under the default-drop sensitivity', 'disconfirmed under the drop sensitivity', 2),
    ('| sensitivity: default-share drop |', '| sensitivity: drop in default share |', 1),
    ('Escaping direction-dose cells', 'Escaping cells (direction and dose)', 1),
    ('the edge-only hull deviation', 'the hull deviation restricted to edges', 1),
    ('| edge-restricted hull |', '| hull restricted to edges |', 1),
    ('| Knobs head-on: activation plan noise vs text-level plan samplers,', '| Knobs compared directly: activation plan noise against text-level plan samplers,', 1),
    ('instead of factual-recall log-probabilities', 'instead of log probabilities of factual recall', 1),
    ('so the five-task count rule is only weakly selective', 'so the count rule over five tasks is only weakly selective', 1),
    ('floating-point sqrt', 'floating point sqrt', 2),
    ('is a floating-point square root', 'is a floating point square root', 1),
    ('The text-level plan samplers were frame-matched, with', "The text-level plan samplers used the twin's frame, with", 1),
    ('instead of from-scratch models', 'instead of models trained from scratch', 1),
    ('Prices came from a full-simplex randomisation hull', 'Prices came from a randomisation hull over the full simplex', 1),
    ('35 of 35 hand-written variants', '35 of 35 handwritten variants', 1),
    ('at Holm-adjusted p of 7e-4 or less', 'at p of 7e-4 or less after Holm adjustment', 1),
    ('with Holm-adjusted p;', 'with p after Holm adjustment;', 1),
    ('| Human-solution diversity |', '| Diversity of human solutions |', 1),
    ('| human-solution diversity |', '| diversity of human solutions |', 3),
    ("from the dataset's input-output pairs", "from the dataset's input and output pairs", 1),
    ('intent-hot/response-cold text plan sampler', 'text plan sampler, hot for the intent and cold for the response', 1),
    ('memorised LeetCode-style tasks', 'memorised tasks in the style of LeetCode', 1),
    ('with the left-padded multi-stage samplers dropped,', 'with the multistage samplers dropped (they were padded on the left),', 1),
    ('| left-padded multi-stage samplers dropped (', '| multistage samplers dropped, padded on the left (', 1),
    ('instead of LLM-judge clusters', 'instead of clusters from an LLM judge', 1),
    ('logit-level base and tuned arithmetic', 'arithmetic on the logits of base and tuned models', 1),
    ('A measurement-error bootstrap gives', 'A bootstrap over measurement error gives', 1),
    ('| method-overlap |', '| method overlap |', 3),
    ('and added narrative-disguised variants of eight bench tasks',
     'and added what we call *disguised variants*, eight bench tasks rewritten as narratives', 1),
    ('what it called the narrowed-repertoire account', 'what it called the *narrowed repertoire account*', 1),
    ('The narrowed-repertoire account split in two.', 'The narrowed repertoire account split in two.', 1),
    ('Algorithm-level (not structural near-duplicate) diversity;', 'Diversity at the algorithm level (not structural near duplicates);', 1),
    ('without the no-default task', 'without the task that has no default', 3),
    ('the stable-stratum and noise-robust sensitivities agree', 'the sensitivities restricted to the stable stratum and robust to noise agree', 1),
    ('so the point-estimate specificity check fails while its noise-robust version holds',
     'so the specificity check on point estimates fails while its version robust to noise holds', 1),
    ('non-informative (<= 3 distinct values)', 'uninformative (<= 3 distinct values)', 2),
    ('| novelty-audit relabels applied |', '| relabels from the novelty audit applied |', 1),
    ('Novelty-instruction', 'Novelty instruction', 2),
    ('novelty-instruction', 'novelty instruction', 5),
    ('off-corr', 'off-default correct', 2),
    ('off-share', 'off-default share', 4),
    ('a parent-cluster permutation p below 0.01', 'a permutation p within parent clusters below 0.01', 1),
    ('the preregistered parent-cluster permutation was not run', 'the preregistered permutation within parent clusters was not run', 1),
    ('a pass-matched random push', 'a random push matched on pass rate', 1),
    ('| pass-matched random, ', '| random matched on pass, ', 1),
    ('| Against pass-matched random |', '| Against random matched on pass |', 1),
    ('Table 92d condenses the paste-ready neighbour table of the audit;', 'Table 92d condenses the neighbour table of the audit;', 1),
    ('the 624 per-direction cells of the escape screens', 'the 624 cells of single directions in the escape screens', 1),
    ('**Table 175.** Per-direction escape screens as distributions', '**Table 175.** Escape screens per direction as distributions', 1),
    ('Level-2 per-output specifications', 'Specifications per output at level 2', 1),
    ('training-time per-prompt forecasts exist', 'forecasts per prompt at training time exist', 1),
    ('per-prompt forecasts from the frozen base model', 'forecasts per prompt from the frozen base model', 1),
    ('(not training-time coverage loss)', '(not loss of coverage at training time)', 1),
    ('| Per-slot label agreement |', '| Label agreement per slot |', 2),
    ('| per-slot label agreement |', '| label agreement per slot |', 1),
    ('(per-slot agreement 0.74)', '(agreement per slot 0.74)', 1),
    ('their raw per-unit ingredients', 'their raw ingredients per unit', 1),
    ('**Table 214.** Gemma per-unit results:', '**Table 214.** Gemma results per unit:', 1),
    ('| PN plain-only / PN twin-only (p) |', '| plan noise only on plain : only on twin (p) |', 1),
    ('The update kept the plan-noise lead', 'The update kept the plan noise lead', 1),
    ('Plan-noise excess', 'Plan noise excess', 4),
    ('plan-noise excess', 'plan noise excess', 4),
    ('No correct plan-noise or escape program', 'No correct program from plan noise or from an escape cell', 1),
    ('Plan-sampler comparison', 'Plan sampler comparison', 1),
    ('plan-sampler', 'plan sampler', 7),
    ('power-sharpening under typicality bias [46]', 'sharpening of the distribution under typicality bias [46]', 1),
    ('on the same pre-commitment answers', 'on the same answers given before commitment', 1),
    ('was precision-sensitive (Table 213)', 'was sensitive to precision (Table 213)', 1),
    ('A pt-to-it transplant at lambda 1', 'A transplant from pt into it at lambda 1', 1),
    ('**Table 218.** pt-to-it transplant at lambda 1', '**Table 218.** Transplant from pt into it at lambda 1', 1),
    ('the read-position transplant broke', 'the transplant at the read position broke', 1),
    ('The read-position transplant shifted', 'The transplant at the read position shifted', 1),
    ('The read-position transplant and the three', 'The transplant at the read position and the three', 1),
    ('but the read-position state moves only', 'but the state at the read position moves only', 1),
    ('and a read-position transplant stay within 0.05', 'and a transplant at the read position stay within 0.05', 1),
    ('(2 transplant-only against 20 random-only flips; two-sided p 1.2e-4)',
     '(2 flips by the transplant alone against 20 by the random displacement alone; exact test, two sided, p 1.2e-4)', 1),
    ('| Two-sided permutation p |', '| Permutation p (two sided) |', 1),
    ('An independent re-derivation reproduced', 'An independent recomputation reproduced', 1),
    ('Two independent re-derivations matched', 'Two independent recomputations matched', 1),
    ('Independent re-derivations found no mismatch', 'Independent recomputations found no mismatch', 1),
    ('Two standard-library re-derivations matched', 'Two recomputations using only the standard library matched', 1),
    ('An independent standard-library script recomputed', 'An independent script using only the standard library recomputed', 1),
    ('two later re-freezes left the values identical', 'two later freezes left the values identical', 1),
    ('that re-select the best mixture inside every replicate', 'that select the best mixture again inside every replicate', 1),
    ('were re-verified live on 2026-10-21', 'were verified again live on 2026-10-21', 1),
    ('On the two path tasks those runners-up were exactly', 'On the two path tasks those runner-up algorithms were exactly', 1),
    ('at runtime-against-AST kappa of at least 0.8, runtime-against-adjudicated agreement of at least 0.9',
     'at a kappa of at least 0.8 between runtime and AST labels, an agreement of at least 0.9 between runtime and adjudicated labels', 1),
    ('judging every runtime-AST disagreement', 'judging every disagreement between runtime and AST labels', 1),
    ('(task-spec positions, blocks 12-23,', '(task specification positions, blocks 12-23,', 1),
    ('within the template-resampling null', 'within the null from resampling templates', 1),
    ('text-domain support [101]', 'support from the text domain [101]', 1),
    ('rests on a tied-baseline task and a mislabelled task', 'rests on a task with a tied baseline and a mislabelled task', 1),
    ('rather than a training-dynamics account', 'rather than an account of training dynamics', 1),
    ('the twin-as-push placebo', 'the placebo that treats the twin as a push', 1),
    ('agreed with a two-family judge adjudication', 'agreed with an adjudication by judges from two families', 1),
    ('a two-family base/instruct design (Qwen3-8B, gemma-3-4b)', 'a base and instruct design in two families (Qwen3-8B, gemma-3-4b)', 1),
    ('unit-bootstrap interval -0.75 to 0.95', 'bootstrap interval over units -0.75 to 0.95', 1),
    ('| McNemar (confirmed) P-only / V-only |', '| McNemar (confirmed), only P : only V |', 1),
    ('weight-level diversity restoration [92, 93]', 'restoration of diversity in weights [92, 93]', 1),
    ('Activation-space push; weight-space extrapolation is a reviewer baseline', 'Push in activation space; extrapolation in weight space is a reviewer baseline', 1),
    ('Algorithm-level (whole-solution) landings rather than token ranks', 'Landings at the algorithm level (whole solutions) rather than token ranks', 1),
    ('**Table 204.** Within-parent comparison of disguised variants', '**Table 204.** Comparison of disguised variants within parents', 1),
    ('for any later write-up:', 'for any later report:', 1),
    ('| partly-fires (', '| partly fires (', 4),
    ('(per-direction rows in `tables/direction_distributions.csv`)', '(rows per direction in `tables/direction_distributions.csv`)', 1),
    ('| BASE-DIVERSE |', '| diverse in the base |', 5),
    ('| BASE-COLLAPSED |', '| collapsed in the base |', 3),
    ('| INTERMEDIATE |', '| intermediate |', 7),
    ('| Base-collapsed units that are immovable |', '| Units collapsed in the base that are immovable |', 1),
    ('| Base-diverse units (beta at least 0.2) that are immovable |', '| Units diverse in the base (beta at least 0.2) that are immovable |', 1),
    ('**Table 219.** Base-collapsed controls of the transplant.', '**Table 219.** Controls collapsed in the base for the transplant.', 1),
    ('Departure-matched decoding applied', 'Decoding at matched departure applied', 1),
    ('two independent re-derivations found no mismatch', 'two independent recomputations found no mismatch', 1),
    ('this is a single-task observation:', 'this is an observation on a single task:', 1),
    ('An outcome-blind extension to N = 100', 'An extension blind to outcomes, to N = 100,', 1),
    ('**Table 185.** Outcome-blind extension to N = 100', '**Table 185.** Extension blind to outcomes, to N = 100,', 1),
]

# Regex rules for the iteration-5 region, applied after the literal ones.
MINE_RE = [
    # table cells naming the stratum
    (r'\| base-diverse \(', '| diverse in the base (', 5),
    (r'\| base-collapsed \(', '| collapsed in the base (', 3),
    # remaining base-diverse / base-collapsed with a counted noun
    (r'\b(\d+|two|three|five|seven) base-diverse (tasks|units)', r'\1 \2 diverse in the base', 1),
    (r'\b(\d+|two|three|five|seven) base-collapsed (tasks|units|controls)', r'\1 \2 collapsed in the base', 1),
    (r'\bbase-diverse (tasks|units|task|unit)', r'\1 diverse in the base', 0),
    (r'\bbase-collapsed (tasks|units|controls|unit)', r'\1 collapsed in the base', 0),
    (r'\bbase-diverse\b', 'diverse in the base', 0),
    (r'\bbase-collapsed\b', 'collapsed in the base', 0),
]

# ---------------------------------------------------------------------------
# 2. Iteration-5 correction notes in earlier sections: exact strings, once each.
# ---------------------------------------------------------------------------
EARLY = [
    ("(corrected in iteration 5 from 'at any dose';", '(corrected in iteration 5 from the phrase *at any dose*;'),
    ("*(Correction, iteration 5: 'at any dose' and 'the site is' say more than the experiment supports.",
     '*(Correction, iteration 5: two wordings here say more than the experiment supports, that the read position and the condition sentence change nothing at any dose, and that the task-specification states are the site of the choice.'),
    ("(Table 177; the record's '22 of 35 cells' was 22 of 24)", "(Table 177; the record's count of 22 of 35 cells was 22 of 24)"),
    ("'Correct-only diversity peaks at alpha 4' on three tasks is therefore a statement about 5 to 9 programs.",
     'The statement that correct-only diversity peaks at alpha 4 on three tasks is therefore a statement about 5 to 9 programs.'),
    ("ICLR 2027 submission knirOusGcq (OpenReview), 'Before the First Token' |", 'ICLR 2027 submission knirOusGcq (OpenReview) |'),
    ('A shared causal subspace for response-length planning,', 'A shared causal subspace for planning the length of a response,'),
    ('Jerge, Pelczar and Downes, arXiv 2608.21595 (NC-GRPO) | Scale-calibrated Gaussian noise in the last hidden layer of the prompt-encoding pass diversifies',
     'Jerge, Pelczar and Downes, arXiv 2608.21595 | Gaussian noise calibrated to the scale of the last hidden layer, added in the pass that encodes the prompt, diversifies'),
    ('Find duplicate is the counter-example in the same table:', 'Find duplicate is the counterexample in the same table:'),
    ('*(Correction, iteration 5: a single-task observation, with find duplicate as its counter-example:',
     '*(Correction, iteration 5: an observation on a single task, with find duplicate as its counterexample:'),
    ('find duplicate is the counter-example and two sum has no agreed neighbour', 'find duplicate is the counterexample and two sum has no agreed neighbour'),
    ('It is a single-task observation on connected components,', 'It is an observation on a single task, connected components,'),
    ('Movability as a forecast of ban compliance and the ban-landing contest are closed',
     'Movability as a forecast of ban compliance and the contest over where a ban lands are closed'),
    ('the next test is the narrowed-repertoire account, Section 5.1.)*', 'the next test is the narrowed repertoire account, Section 5.1.)*'),
    ('*(correction, iteration 5: except the preregistered default-drop sensitivity, which disconfirms the claim:',
     '*(correction, iteration 5: except the preregistered sensitivity that measures compliance as the drop in the default share, which disconfirms the claim:'),
    ('*(Correction, iteration 5: the default-drop row is the preregistered sensitivity,',
     '*(Correction, iteration 5: the row on the drop in the default share is the preregistered sensitivity,'),
    ('and DISCONFIRMED under the preregistered default-drop sensitivity (balanced accuracy 0.57,',
     'and DISCONFIRMED under the preregistered sensitivity on the drop in the default share (balanced accuracy 0.57,'),
    ('| without NO-DEFAULT tasks (added in iteration 5; the grid task) |', '| without tasks that have no default (added in iteration 5; the grid task) |'),
    ('(34 movers, 27 escaping direction-dose cells)', '(34 movers, 27 escaping cells of direction and dose)'),
    ('not to a further direction-level predictor on the same five', 'not to a further predictor at the level of directions on the same five'),
    ('| deviation D-hull-edges (added in iteration 5): the preregistered hull search is restricted to edges; it matched a full-simplex optimiser within 0.02',
     '| deviation on hull edges (added in iteration 5): the preregistered hull search is restricted to edges; it matched an optimiser over the full simplex within 0.02'),
    ('Algorithm-level labels; departure-matched decoding was not run in iteration 4', 'Algorithm-level labels; decoding at matched departure was not run in iteration 4'),
    ('this run adds task-specification-state noise against temperature', 'this run adds noise in the task-specification states against temperature'),
    ('the no-novelty bound (0 among 14,206 correct programs)', 'the bound on novelty (0 among 14,206 correct programs)'),
    ('42 non-null entries, 113 null', '42 entries with a value, 113 null'),
    ('| not re-evaluated |', '| not evaluated again |'),
    ('(Sections 4.3 and 4.6; per-direction distributions in Table 175)', '(Sections 4.3 and 4.6; distributions per direction in Table 175)'),
    ('*(Correction, iteration 5: these are not per-direction rates.', '*(Correction, iteration 5: these are not rates per direction.'),
    ('*(Correction, iteration 5: three qualifications. First, the random-direction numbers above are maxima',
     '*(Correction, iteration 5: three qualifications. First, the numbers for random directions above are maxima'),
    ('| random-direction cells | 0 of 36 qualify |', '| cells of random directions | 0 of 36 qualify |'),
    ('in the knob rows of the plan noise experiment a non-exposure knob reaches 1.5 within 20 pass points',
     'in the knob rows of the plan noise experiment a knob outside the exposure class reaches 1.5 within 20 pass points'),
]

DICT_CELL = re.compile(r"\{((?:\s*['\"][^'\"{}]+['\"]\s*:\s*-?\d+(?:\.\d+)?\s*,?)+)\s*\}")
DICT_ITEM = re.compile(r"['\"]([^'\"{}]+)['\"]\s*:\s*(-?\d+(?:\.\d+)?)")


def plain_counts(m):
    return ', '.join(f'{k} {v}' for k, v in DICT_ITEM.findall(m.group(1)))


def strip_unit_codes(text):
    out = []
    for line in text.split('\n'):
        if line.startswith('|'):
            line = re.sub(r'(?<=\| )[AB][1-9] (?=[a-z])', '', line)
        out.append(line)
    return '\n'.join(out)


def main():
    d = DRAFT.read_text()
    i5 = d.index('# Iteration 5')
    ref = d.index('\n# References')
    early, mine, tail = d[:i5], d[i5:ref], d[ref:]
    problems = []

    for old, new in EARLY:
        n = early.count(old)
        if n != 1:
            problems.append(f'EARLY x{n}: {old[:80]}')
            continue
        early = early.replace(old, new)

    for old, new, need in MINE:
        n = mine.count(old)
        if n < need:
            problems.append(f'MINE x{n} (need {need}): {old[:80]}')
        mine = mine.replace(old, new)

    mine = DICT_CELL.sub(plain_counts, mine)
    mine = strip_unit_codes(mine)
    for pat, rep, need in MINE_RE:
        mine, n = re.subn(pat, rep, mine)
        if n < need:
            problems.append(f'MINE_RE x{n}: {pat}')

    DRAFT.write_text(early + mine + tail)
    for p in problems:
        print('MISS', p)
    print('terminology pass done;', len(problems), 'misses')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
