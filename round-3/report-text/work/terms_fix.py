import re, sys
p='paper_draft.md'; t=open(p).read()
i3=t.index('# Iteration 3:'); iref=t.index('# References')
early, sec, refs = t[:i3], t[i3:iref], t[iref:]

def R(text, old, new, count=1):
    n=text.count(old)
    if n!=count:
        print('COUNT', n, 'expected', count, '|', old[:90]); sys.exit(1)
    return text.replace(old, new)

# ---------- earlier-section notes written in iteration 3 (marked corrections) ----------
early=R(early, "*(Correction, iteration 3: 'not pure subtraction', 'not aimed' and 'no coherent ladder' are not detectable with the current instrument; they are not findings.",
              "*(Correction, iteration 3: the three readings above, that the gains are not pure subtraction, that the residuals are not aimed, and that the generic profiles form no coherent ladder, are not detectable with the current instrument; they are not findings.")
early=R(early, "The direct route is not 'none'.", "The direct route is not zero.")
early=R(early, "so 'can' holds cleanly only for Floyd-Warshall)*", "so only Floyd-Warshall is written cleanly on request)*")
early=R(early, "*(Correction, iteration 3: this item belongs under 'not detected by an uncalibrated instrument', not under 'ruled out', and it conflicts with item 2 above.",
              "*(Correction, iteration 3: this item belongs among the effects that an uncalibrated instrument could not detect, not among the accounts ruled out, and it conflicts with item 2 above.")

# ---------- iteration 3 section ----------
# 3.1 review paragraph
sec=R(sec, "(a shared second choice on the shortest path task, and \"no coherent ladder\" among the things ruled out). The route claim was stated in the closing summary as \"the direct route none\", although two of the three readouts in the same artifact showed a direct route.",
           "(a shared second choice on the shortest path task, and the absence of a coherent ladder listed among the accounts ruled out). The closing summary stated that the direct route carried none of the ban, although two of the three readouts in the same artifact showed a direct route.")
# association forecast wording
sec=R(sec, "The *association forecast* is the model's frozen free-form answer to \"what is the standard alternative to X\", and the",
           "The *association forecast* is the model's frozen free-form answer when asked for the standard alternative to X, and the")
# n-gram convention + branch definitions after the event gate sentence
sec=R(sec, "The event gate stayed as in Section 2.2 (avoidance at least 0.5 and at least 20 attempts not banned).",
           "The event gate stayed as in Section 2.2 (avoidance at least 0.5 and at least 20 attempts not banned). The frozen contest rule names its outcomes, and we call these outcomes branches, written as the rule prints them: SUBTRACTION/LADDER when a ban-free family (subtraction or ladder) advances, followed by the family that advanced; SUBSTITUTION when association or proximity advances; NO FAMILY ADVANCES when none does, which we call aimed but unresolved when some family's top-1 still names the landing more often than chance; and, when no family's top-1 beats chance, the branch we call X specific but unaimed, the name Section 2.2 gave the same outcome. In the n-gram code spans of this section, ␣ marks a space and \\n a newline.")
# Table 80 rows
sec=R(sec, "| Two verdicts on the rival | Shared top rung in behaviour against \"no coherent ladder\" |",
           "| Two verdicts on the rival | A shared second choice in behaviour against a claimed absence of any coherent ladder |")
sec=R(sec, "| Route stated too strongly | \"Direct route none\" against two readouts with a direct route |",
           "| Route stated too strongly | A direct route of zero claimed against two readouts with a direct route |")
sec=R(sec, "FP8 prompt log probabilities; unscrubbed variant unvalidated on ban rows", "8-bit prompt log probabilities; unscrubbed variant unvalidated on ban rows")
# Table 79 hardware
sec=R(sec, "Qwen3-8B bf16; one NVIDIA L4, about 1.0 GPU hour", "Qwen3-8B bf16; one 23 GB NVIDIA GPU, about 1.0 GPU hour")
sec=R(sec, "Llama-3.1-8B-Instruct bf16; one NVIDIA L4, 0.98 GPU hours of logged generation (about 1.8 hours held)", "Llama-3.1-8B-Instruct bf16; one 23 GB NVIDIA GPU, 0.98 GPU hours of logged generation (about 1.8 hours held)")
sec=R(sec, "Qwen3-8B bf16 (HF); one NVIDIA L4, about 1.8 GPU hours", "Qwen3-8B bf16 (HF); one 23 GB NVIDIA GPU, about 1.8 GPU hours")
sec=R(sec, "Qwen3-8B with FP8 weight and activation linears (HF); one 16 GB RTX 2000 Ada", "Qwen3-8B with 8-bit floating point weight and activation linears (HF); one 16 GB RTX 2000 Ada GPU")
sec=R(sec, "Qwen3-8B bf16 (path tasks) and the official FP8 checkpoint (bench tasks); one NVIDIA L4", "Qwen3-8B bf16 (path tasks) and the official 8-bit floating point checkpoint (bench tasks); one 23 GB NVIDIA GPU")
# 3.2.1
sec=R(sec, "\"hit\" marks an argmax equal to the modal landing. On the grid task \"Dijkstra\" means unit weight Dijkstra. Source: record audit",
           "An argmax equal to the modal landing is marked as a hit. Source: record audit")
sec=R(sec, "both the F statistic for \"not pure subtraction\" and the X specific share are inflated.",
           "both the F statistic behind the reading that the gains are not pure subtraction and the X specific share are inflated.")
sec=R(sec, "| Model | Algorithm | Cells | Median ESS now (M = 20) | Median SD of log weights | Plug-in M5, median | Plug-in M5, 90th percentile | Lognormal M5, median |",
           "| Model | Algorithm | Cells | Median ESS now (M = 20) | Median SD of log weights | Plug-in programs needed, median | Plug-in programs needed, 90th percentile | Lognormal programs needed, median |")
sec=R(sec, "The ladder verdicts of Section 2.11 are reconciled as the review asked (correction in place there). Behaviour shows a shared top rung on the shortest path task:",
           "The ladder verdicts of Section 2.11 are reconciled as the review asked (correction in place there). We call a survivor that the ban and every generic perturbation reach a shared top rung. Behaviour shows a shared top rung on the shortest path task:")
sec=R(sec, "The order below the top rung is unmeasured, and \"a coherent latent ladder\" moves from ruled out to not detected by an uncalibrated instrument.",
           "The order below the top rung is unmeasured, and the latent ladder of Section 2.1 moves from the accounts ruled out to the effects that an uncalibrated instrument could not detect.")
# 3.2.2
sec=R(sec, "\"No circle\" is therefore powered only where the label confounds the geometry.",
           "The absence of a loop is therefore established with power only where the label confounds the geometry.")
# 3.2.3 other quotes and variant/miss
sec=R(sec, "The only place such a solution could have appeared in the run's data is among programs labelled \"other\".",
           "The only place such a solution could have appeared in the run's data is among programs with the label other.")
sec=R(sec, "It added 138 unique failing \"other\" programs written under bans (Set B) and the 12 failing \"other\" programs of the TOP ban list",
           "It added 138 unique failing programs labelled other and written under bans (Set B), and the 12 failing programs labelled other under the TOP ban list")
sec=R(sec, "agreed on the exact class for 60 of 78 and on all 78 once \"variant\" and \"miss\" are merged.",
           "agreed on the exact class for 60 of 78 and on all 78 once the catalogue variant and labeller miss classes are merged.")
# Table 92 header and verbatim quotes -> paraphrases
sec=R(sec, "| Claim in this run | Neighbour | Neighbour's finding (verbatim) | Relation | What this run adds |",
           "| Claim in this run | Neighbour | Neighbour's finding (paraphrased; the audit verified each against a verbatim quote) | Relation | What this run adds |")
paras=[
 ("\"this dimension is more closely related to the phrasing of prompts rather than the inherent difficulty of the task or instructions\"", "a direction in input embedding space predicts instruction following, tracks prompt phrasing more than task difficulty, and raises success when intervened along"),
 ("\"With interventions on attention edges, we first identify two critical points where information propagates to the prediction\"", "interventions on attention edges locate two points where information flows to the prediction"),
 ("\"we demonstrate evidence of a \"task recognition\" point where the translation task is encoded into the input representations and attention to context is no longer necessary\"", "after a task recognition point the task is encoded in the input representations and attention to the context is no longer needed"),
 ("\"the instruction's explicit mention of the forbidden word paradoxically activates rather than suppresses the target representation\"", "explicitly mentioning a forbidden word activates its representation instead of suppressing it"),
 ("\"suppressing a concept requires internally activating it, which may prime rebound instead of avoidance\"", "suppressing a concept requires activating it internally, which can prime rebound rather than avoidance"),
 ("\"DENIAL PROMPTING which pushes LLMs to develop more creative solutions to a given problem by incrementally imposing new constraints on the previous solution\"", "denial prompting adds a new constraint on the previous solution at each step to push the model toward more creative solutions"),
 ("\"We also find that they don't transfer on\" (Gemma v1 2B)", "base model SAEs usually transfer to chat models, but not on Gemma v1 2B"),
 ("\"Incompleteness pushes the model into low-probability regions of the program space, causing the generation to frequently time out, and reducing functional correctness by up to 97%.\"", "an incomplete constraint at decoding time pushes the model into low-probability regions of program space, causing time-outs and up to 97% lower functional correctness"),
 ("\"suppressing retrieval of the original answer (e.g., \"Madrid\") while (2) promoting a favored candidate within the answer category\"", "negation suppresses retrieval of the original answer while promoting a favoured candidate in the same answer category"),
 ("\"models implement both mechanisms, with the \"constructive\" mechanism being more prominent\"", "models process negation by both suppression and construction, with construction more prominent"),
 ("\"the functions learned by ICL often have a very simple structure\"", "functions learned in context often have a very simple structure, a task vector"),
 ("\"a small number attention heads transport a compact representation of the demonstrated task, which we call a function vector (FV)\"", "a few attention heads transport a compact representation of the demonstrated task, a function vector"),
]
for o,n in paras: sec=R(sec, o, n)
# 3.3
sec=R(sec, "**Table 94.** Forecasts committed before any ban sample (top-1 survivor; \"undefined\" is scored as uniform). The distinctive n-gram is shown as tokenised; its source is the 8-bit pilot unless marked.",
           "**Table 94.** Forecasts committed before any ban sample (top-1 survivor; a forecast marked undefined is scored as uniform). The distinctive n-gram is shown as tokenised (␣ marks a space); its source is the 8-bit pilot unless marked.")
sec=R(sec, "The frozen rule returned \"SUBTRACTION/LADDER (LADDER)\": on the five gated events,", "The frozen rule returned the SUBTRACTION/LADDER branch, with the ladder advancing: on the five gated events,")
sec=R(sec, "| Task | First | Second | Third | Fourth (`X is not allowed here`) | Fifth |", "| Task | First | Second | Third | Fourth | Fifth |")
# 3.4
sec=R(sec, "33 Y, of which 19 are \"priority\" Y whose frozen associate differs from the default.", "33 Y. We call the 19 whose frozen associate differs from the default priority Y.")
sec=R(sec, "(Qwen3-8B bf16, vLLM 0.11.0, one NVIDIA L4)", "(Qwen3-8B bf16, vLLM 0.11.0, one 23 GB NVIDIA GPU)")
sec=R(sec, "naming Y adds little beyond \"something else\".", "naming Y adds little beyond asking for a different algorithm.")
sec=R(sec, "so the frozen branch is \"SUBTRACTION/LADDER (LADDER)\".", "so the frozen branch is SUBTRACTION/LADDER, with the ladder advancing.")
sec=R(sec, "(\"none\" when the top two tie; \"n/a\" when the event is ungated or not disagreeing)", "(none when the top two tie; n/a when the event is ungated or its nominations do not disagree)")
sec=R(sec, "except \"exclude undefined subtraction\", which leaves 2 events and is undetermined.", "except the one that drops events with an undefined subtraction forecast, which leaves 2 events and is undetermined.")
sec=R(sec, "GPU time was about 1.0 GPU hour on one L4, judge spend", "GPU time was about 1.0 GPU hour, judge spend")
# 3.5
sec=R(sec, "No family advances; the preregistered branch is \"NO FAMILY ADVANCES (aimed, unresolved)\".", "No family advances; the preregistered branch is NO FAMILY ADVANCES, aimed but unresolved.")
sec=R(sec, "\"undefined\" is scored as uniform. Source: Llama bench experiment", "a forecast marked undefined is scored as uniform. Source: Llama bench experiment")
sec=R(sec, "leaves 5 disagreeing gated events and reads \"X specific but unaimed\".", "leaves 5 disagreeing gated events and reads X specific but unaimed.")
sec=R(sec, "all keep \"no family advances\".", "all keep NO FAMILY ADVANCES.")
sec=R(sec, "**Table 103.** Share of the banned algorithm among veto attempts per round (persistent, iterated arm; weighted counts for present minor events).",
           "**Table 103.** Share of the banned algorithm among veto attempts per round (persistent, iterated arm; weighted counts for present minor events; ␣ marks a space in the n-grams).")
sec=R(sec, "GPU time was 0.98 hours of logged generation on one L4 (about 1.8 hours held)", "GPU time was 0.98 hours of logged generation (about 1.8 hours with the GPU held)")
# 3.6
sec=R(sec, "on one NVIDIA L4 with batches of 40 rows of one shape class.", "on one 23 GB NVIDIA GPU with batches of 40 rows of one shape class.")
sec=R(sec, "The full knockout (K0) removes the condition span from the cache seen by generated tokens. The one-shot signature veto of the default (V1) runs under the twin,",
           "The full knockout arm removes the condition span from the cache seen by generated tokens. A one-shot veto arm applies the signature veto of the default under the twin,")
sec=R(sec, "the interaction I = 1 - F_prompt - F_direct, and F_K0 = (s_b - s_K0) / (s_b - s_a).",
           "the interaction I = 1 - F_prompt - F_direct, and the knockout fraction F_knockout = (s_b - s_knockout) / (s_b - s_a), where s_knockout is the default's share under the full knockout.")
sec=R(sec, "| Knockout (K0) | One-shot veto (V1) |", "| Full knockout | One-shot veto |")
sec=R(sec, "| Task | F_prompt | F_direct | Interaction | F_K0 | Reading |", "| Task | F_prompt | F_direct | Interaction | F_knockout | Reading |")
sec=R(sec, "| F_K0 | 0.621 |", "| F_knockout | 0.621 |")
sec=R(sec, "The committed prediction \"the grid one-shot veto does not suffice\" hit; \"the shortest path one-shot veto suffices and lands on Bellman-Ford/SPFA\" missed (V = 0).",
           "The committed prediction that the grid one-shot veto would not suffice hit; the prediction that the shortest path one-shot veto would suffice and land on Bellman-Ford/SPFA missed (V = 0).")
sec=R(sec, "GPU time was about 1.8 hours on one L4, judge spend USD 0.105.", "GPU time was about 1.8 GPU hours, judge spend USD 0.105.")
# 3.7
sec=R(sec, "Is there a task-general direction that carries \"leave your default\", and does writing it", "Is there a task-general direction that carries the instruction to abandon the default, and does writing it")
sec=R(sec, "Stricter companions: the fraction recovered relative to mean ablation passed", "Stricter companions: the fraction recovered relative to mean ablation (FR_mean) passed")
# 3.8
sec=R(sec, "Both cells reached \"rung 3 or more\" through the flagged fallback,", "Both cells were placed at rung 3 or more through the flagged fallback,")
sec=R(sec, "There the prompt read \"Do not use a size-k heap, heapify-and-pop, quickselect, median of medians or counting sort for this task.\", and all 50 programs implemented quickselect,",
           "There the prompt banned the size-k heap, heapify and pop, quickselect, median of medians and counting sort, and all 50 programs implemented quickselect,")
sec=R(sec, "**Table 114.** The token walk under the neutral twins (no ban text; N = 50 per round, 10 per template).",
           "**Table 114.** The token walk under the neutral twins (no ban text; N = 50 per round, 10 per template; ␣ marks a space in the n-grams).")
sec=R(sec, "The request's two instructions (\"Make a new algorithm\" and \"Make a fully novel algorithm never seen before\", each asking for a design rationale of about 2,000 words before the code) were run",
           "The request contains two long-form instructions, which we call the first long-form instruction (asking the model to make a new algorithm) and the second long-form instruction (asking for a fully novel algorithm never seen before); each asks for a design rationale of about 2,000 words before the code. They were run")
sec=R(sec, "under names such as \"Modified Bellman-Ford\", \"BFS with Dynamic Programming\" and \"Optimized Dijkstra with Early Termination\".",
           "under names that modify a catalogue algorithm, such as a modified Bellman-Ford, a BFS with dynamic programming, or an optimised Dijkstra with early termination.")
sec=R(sec, "**Table 118.** Long-form novelty instructions: composition of outputs per cell (first instruction \"Make a new algorithm\"; second \"Make a fully novel algorithm never seen before\").",
           "**Table 118.** Long-form novelty instructions: composition of outputs per cell (first and second long-form instructions as defined above).")
# 3.9
sec=R(sec, "**One wording, everywhere.** The fourth template (`X is not allowed here`) is the weakest wording", "**One wording, everywhere.** The fourth template of Table 40, which states only that X is not allowed here, is the weakest wording")
sec=R(sec, "| Qwen3-8B modal bench bans | 5 (5) | SUBTRACTION/LADDER (LADDER); no family advances if undefined forecasts do not count |",
           "| Qwen3-8B modal bench bans | 5 (5) | SUBTRACTION/LADDER, ladder advancing; NO FAMILY ADVANCES if undefined forecasts do not count as wins |")
sec=R(sec, "| Qwen3-8B exposure bans, named | 31 (30) | SUBTRACTION/LADDER (LADDER) |", "| Qwen3-8B exposure bans, named | 31 (30) | SUBTRACTION/LADDER, ladder advancing |")
sec=R(sec, "| 13 (11) | NO FAMILY ADVANCES (aimed, unresolved) |", "| 13 (11) | NO FAMILY ADVANCES, aimed but unresolved |")
# 3.10
sec=R(sec, "\"Not pure subtraction\", \"not aimed\" and \"no coherent ladder\" are not detectable with that instrument.",
           "Whether the gains are pure subtraction, whether their specific part is aimed, and whether the generic profiles form a ladder are all undetectable with that instrument.")
# closing
sec=R(sec, "the template `X is not allowed here` is the weakest in every artifact,", "the fourth template, which states only that X is not allowed here, is the weakest in every artifact,")

# ---------- n-gram code spans: strip inner quotes, show spaces as ␣ ----------
def conv(m):
    inner=m.group(1)
    if len(inner)>=2 and inner[0]==inner[-1] and inner[0] in "'\"":
        inner=inner[1:-1]
    elif not inner.startswith(' '):
        return m.group(0)
    return '`'+inner.replace(' ','␣')+'`'
sec2=re.sub(r'`([^`\n]+)`', conv, sec)
changed=sum(1 for a,b in zip(re.findall(r'`[^`\n]+`',sec), re.findall(r'`[^`\n]+`',sec2)) if a!=b)
sec=sec2
print('code spans converted:', changed)
t=early+sec+refs
open(p,'w').write(t)
print('ok')
