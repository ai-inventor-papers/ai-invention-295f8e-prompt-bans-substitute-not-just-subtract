# gen_viz_2 — report_results

> Phase: `gen_paper_repo` · `gen_viz`
> Run: `gen_paper_repo_c164ac661673` — A Random Activation Push Changes a Code Model's Algorithm Where Temperature Does Not
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_viz_2` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-10-26 03:28:29 UTC

```
<research_methodology>
Create figures that belong in a top-venue paper.

- Every figure needs a clear takeaway visible at a glance.
- Choose chart types that match the data relationship (comparisons, trends, correlations, distributions).
- Include uncertainty (error bars, confidence intervals) when showing experimental results.
- Keep it clean — no clutter, clear labels with units, readable at print size.
</research_methodology>

<safeguard_research_reporting>
When the research concerns bypassin... [truncated, 247224 chars total]
```

### [2] SKILL-INPUT — aii-concept-fig-gen · 2026-10-26 03:33:41 UTC

The agent loaded the **aii-concept-fig-gen** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-concept-fig-gen
description: "Generates and edits CONCEPT FIGURES — architecture and pipeline diagrams, flow charts, cover and hero artwork — with OpenAI GPT Image and Gemini Nano Banana image models through OpenRouter, at a chosen aspect ratio and resolution, free or paid, in parallel batches. Use whenever a figure must be DRAWN because no dataset sits behind it, or an existing image needs editing from a text instruction. Triggers: concept figure, figure_type='concept', architecture diagram, pipeline diagram, flow chart, cover image, conceptual artwork, image generation, image editing, nano banana, gemini image. NOT for: anything with numbers behind it — bars, curves, heatmaps, confusion matrices, scaling laws — which an image model only approximates, so use aii-data-fig-gen; multi-round variant batches are amg-iter-image-gen-human; calling a TEXT model over OpenRouter is aii-openrouter-llms; displaying a file is amg-open-img-ubuntu."
---

# Image Generation & Editing (nano_banana)

> **Not for data figures.** An image model approximates numbers: bars come
> back close to but not equal to their labels, and axis ticks do not divide
> evenly. Nothing downstream detects it. If the figure has numbers behind
> it, use `aii-data-fig-gen`, which renders them deterministically.

Generate images via OpenRouter's dedicated images API (`/api/v1/images`) through the ability server, on four paid tiers tried in order with automatic fallback: `sunburst` (`openai/gpt-image-2.5-sunburst`, Sunburst 2.5, default) → `gpt` (`openai/gpt-5.4-image-2`) → `pro` (`google/gemini-3-pro-image-preview`, Nano Banana Pro) → `flash` (`google/gemini-3.1-flash-image-preview`, Nano Banana 2, the safety net every tier ends on). The `OPENROUTER_API_KEY` lives on the ability server — this skill routes requests through `call_server()`. Inside an AI Inventor run the call still goes to the run's `OPENROUTER_BASE_URL` on the run's own key, so every image counts against the run's OpenRouter budget; past it, generation fails with a message starting "AI Inventor per-run OpenRouter budget".

## Setup

```bash
SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-concept-fig-gen"
G="$SKILL_DIR/scripts/concept_fig_gen.py"
PY="$SKILL_DIR/../.ability_client_venv/bin/python"
```

## Generate Image

```bash
$PY $G --prompt "prompt describing the image" --output output.jpg --aspect-ratio 16:9
```

## Free vs paid — check before you generate

Two billing paths. **You do not normally choose**: the run's backend already
set the default, and the flags below only override it.

| Path | Cost | Editing |
|---|---|---|
| paid (default) | $0.2469/image (sunburst, max quality) | yes |
| `--free` | $0 | no |

The paid path is OpenRouter's `openai/gpt-image-2.5-sunburst` (`--model
sunburst`, the default); `--free` is Cloudflare Workers AI (FLUX / SDXL),
falling back to Hugging Face
`stabilityai/stable-diffusion-3-medium-diffusers` (SD3).

`--free` serves inside Cloudflare's 10,000-neuron **daily** free allocation.
None of the four paid tiers has a free image path, so this is the only
genuinely $0 route.

**None of the four tiers is one price, and `sunburst` is not tiered at all —
it always renders at the maximum.** `sunburst` ignores `--image-size`
entirely and always requests OpenRouter's highest quality setting for this
model (`quality: "max"` — its own catalog gives it an enum
`["auto","low","medium","high","xhigh","max"]` that no other tier has) at the
largest size OpenRouter accepts for the requested `--aspect-ratio` (a
3840px-longest-edge "size", OpenRouter's own ceiling for this model — see
below): $0.2469/image measured live (21:9 → 3840x1648). This is a standing
policy, not a per-call choice: Sunburst is meant to be the best a figure gets,
so it is never asked to render a cheaper draft. `gpt` is ~$0.04/image at 1K
but ~$0.19 at 2K and ~$0.42 at 4K (`size` and `quality: "high"` scale with
resolution — see below, and `gpt` DOES still honour `--image-size`, unlike
`sunburst`). `flash` is ~$0.067/image at 1K but ~$0.101 at 2K, measured live
at $0.1017 for a 2K edit. It matters because the figure step deliberately
uses both 1K and 2K for the non-`sunburst` tiers: it explores at 1K and then
makes exactly TWO 2K passes per figure. `pro` is flat at ~$0.134 across 1K
and 2K.

The paid path has four quality tiers, `sunburst` by default, selected with
`--model` (orthogonal to `--free`/`--paid`), tried in order with automatic
fallback down the chain:

| `--model` | ~Price | Falls back to |
|---|---|---|
| `sunburst` | $0.2469/image, always max/4K | `gpt`, `pro`, `flash` |
| `gpt` | $0.04 / $0.19 / $0.42 (1K / 2K / 4K) | `pro`, then `flash` |
| `pro` | $0.134 / $0.134 / $0.24 (1K / 2K / 4K) | `flash` |
| `flash` | $0.067 / $0.101 / $0.15 | none (it IS the fallback) |

`sunburst`'s 4K/max figure is measured live; its 1K/2K entries in the price
table exist only as area-scaled estimates because current code never
requests them for `sunburst` — a call that falls back off `sunburst` onto
`gpt` after exhausted retries drops the max override and resumes `gpt`'s own
tiered behaviour (including whatever `--image-size` the caller asked for).
Every call reports its real charge back, so the table only ever stands in for
a response that carried no `usage` block.

**You do not normally choose this**: the pipeline sets it from the run's
`gen_paper_repo.gen_viz.image_model` config, and every preset except Lite
picks `sunburst` (Lite keeps `flash`). A call that exhausts its retries on one
tier moves to the next one in
the chain, and every charge the provider reports is recorded — including one
on a response that came back priced and carrying no image, which is a refusal
(quota, moderation) rather than a blank a retry fills in. Such a response is
not asked for again at the same price, and the figure's failure still names
what the body said.

**The two OpenAI tiers ignore `resolution` outright** (verified live: they
return the same pixel dimensions whatever `resolution` tier is sent). Instead
this skill translates the requested size tier into an explicit `size` (pixel
width×height, derived from `--aspect-ratio`, both dimensions rounded to the
nearest multiple of 16 — OpenRouter rejects anything else live with HTTP 400
"Width and height must both be divisible by 16") plus a `quality` field —
`--aspect-ratio` itself is still honoured directly by all four models.
`gpt` uses whatever tier `--image-size` asked for, at `quality: "high"`.
**`sunburst` ignores `--image-size`, always resolving to the "4K" tier at
`quality: "max"`** — the largest size and highest quality OpenRouter accepts
for it, on any aspect ratio, regardless of what `--image-size` said (even a
missing or invalid value); a call that exhausts sunburst's retries and falls
back to `gpt` resumes `gpt`'s own tiered behaviour, not sunburst's max. Every
tier's `size` longest edge is capped at 3840px (OpenRouter's own ceiling: a
4096px request answers HTTP 400), so the "4K" tier renders at a 3840px
longest edge, not 4096. Edit mode (`--edit`) works identically across all
four tiers — the source image rides along the same way regardless of
`--model`.

- **On a free-tier run the default is already `--free`** (the backend exports
  `AII_FREE_TOOLS=1`). Do not pass `--paid` there: six figures on the paid
  path cost $0.81, which was 78% of a measured "free" run's entire bill.
- Pass `--paid` only when you must EDIT an existing image, which the free
  provider cannot do — it takes a prompt with no image input.
- The free path has TWO providers and walks between them. Cloudflare's
  10,000-neuron daily allocation is shared with the free LLM pool, so a busy day
  spends it; the call then fails over to Hugging Face automatically. You do not
  need to do anything for this.
- If BOTH are down the call fails. Do not silently fall back to paid on a free
  run: report it and continue without the figure.

### Free costs you the labels, not just the fidelity

The returned JSON's `model` field says which of the three served the image, and
it is worth reading: they are tiers apart on the thing concept figures are
mostly made of — words in boxes. Same prompt, same day, measured live:

| Model that served it | Diagram | Labels came out as |
|---|---|---|
| paid `gemini-3.1-flash-image-preview` | right | all three correct |
| CF `flux-1-schnell` | right | `Enc:der`, `conveged?` |
| HF SD3 medium | wrong | `erooder`, `routter` |

Three paid runs, three clean figures — every word right, and the flow chart
came back with the NO branch actually looping back, which neither free model
managed once. SD3 went the other way and put text in a figure that asked for
none: a prompt ending "no text of any kind" came back with `Kat q` and
`Wet ker wee Bir Sauh` lettered across it, in red and green as its two main
colours under `--style neurips`. Treat an HF-served image as a draft to check
hard, not a figure to ship.

That is where the $0.067 goes, so spend the verification effort to match: on a
free run read every word in the image letter by letter, and on a paid one look
first for the things a good speller still gets wrong — a stage you do not have,
an arrow the wrong way round.

None of it is checked automatically. `success: true` means a valid JPEG of the
right size arrived — nothing reads the words in it.

## Edit Image

```bash
$PY $G --edit input.jpg --prompt "Make the background blue" --output edited.jpg
```

**Parameters:**
- `--prompt` / `-p` (required) — image description or edit instruction
- `--output` / `-o` (default: `./generated_image.jpg`) — output file path (always saved as `.jpg`; suffix is forced)
- `--edit` — path to source image for editing (omit for generation)
- `--aspect-ratio` (default: `16:9`) — valid: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
- `--image-size` (default: `1K`) — resolution: `1K`, `2K`, `4K` (on `gpt` this becomes an explicit pixel `size`, not the `resolution` field — see above; `sunburst` ignores this flag entirely and always renders at its own max size)
- `--model` (default: `sunburst`) — paid tier: `sunburst` (`openai/gpt-image-2.5-sunburst`, Sunburst 2.5, always $0.2469/img at max quality/size regardless of `--image-size`, falls back to `gpt` then `pro` then `flash`), `gpt` (`openai/gpt-5.4-image-2`, ~$0.04-0.42/img depending on resolution, falls back to `pro` then `flash`), `pro` (Nano Banana Pro, ~$0.134/img @1K-2K, falls back to `flash`), or `flash` (Nano Banana 2, ~$0.067/img, cheapest, no further fallback). Normally set by the pipeline from `gen_paper_repo.gen_viz.image_model` (every preset except Lite picks `sunburst`); ignored on `--free`.
- `--style neurips` — appends NeurIPS academic style guidance
- `--negative-prompt` — things to exclude from the image
- `--system` — system-level style instruction
- `--timeout` (default: `180`) — the WHOLE call's deadline, and therefore the
  retry budget. Each attempt gets the lesser of 180 s and whatever is left, and
  the loop will not start one it cannot finish: with 180 s and fast failures
  (a connection error, a 5xx) every attempt in the chain runs — up to twelve
  for the default `sunburst` tier (3 attempts on each of sunburst, gpt, pro,
  flash), nine for `gpt`, six for
  `pro`, three for `flash` — while on slow responses it stops and says how
  much budget was left rather than being cut off mid-request. Raise it if you
  want the full budget under slow responses — nine attempts of 180 s would
  need up to 1638 s.

## Parallel Batch Generation

Use GNU `parallel` for multiple images:

```bash
export SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-concept-fig-gen"
export PY="$SKILL_DIR/../.ability_client_venv/bin/python"
export G="$SKILL_DIR/scripts/concept_fig_gen.py"
parallel -j 5 -k --group --will-cite 'eval {}' ::: \
  "\$PY \$G -p \"prompt 1\" -o output_1.jpg --aspect-ratio 21:9" \
  "\$PY \$G -p \"prompt 2\" -o output_2.jpg --aspect-ratio 16:9" \
  "\$PY \$G -p \"prompt 3\" -o output_3.jpg --aspect-ratio 1:1"
```

## Preview

Do **NOT** open generated images in a GUI viewer (`loupe`, `xdg-open`, `eog`,
etc.). This skill is for automated / headless generation (e.g. pipeline figure
steps), and popping image windows clutters the user's desktop. Inspect images
programmatically if needed (read the file, check the returned JSON), not by
opening a viewer.

For interactive, human-curated review of multiple figure variants — where the
user wants to arrow-navigate batches in `loupe` — use the
`amg-iter-image-gen-human` skill instead; loupe-driven review is its job, not
this one's.

## Features

- **Model**: default `openai/gpt-5.4-image-2` (`--model gpt`); `--model pro` selects `gemini-3-pro-image-preview` (Nano Banana Pro); `--model flash` selects `gemini-3.1-flash-image-preview` (Nano Banana 2). Each tier that exhausts its retries falls back to the next one down the chain (gpt → pro → flash)
- **Auth**: API key on ability server (routed via `call_server()`)
- **Retries**: 3 attempts with exponential backoff per tier, then the next tier in the chain — as far as `--timeout` allows, since it is the deadline for the whole call
- **Edit mode**: Edit existing images with text instructions
- **Parallel**: GNU `parallel` with `-j 5` for batch generation
- **Headless**: never auto-opens a viewer (use `amg-iter-image-gen-human` for human review)

## Prompting Tips

- Name every element and where it sits — boxes, arrows, groupings, labels.
  The model places what you describe and invents what you leave out
- **Put the labels in their own closing sentence**, not inline in the sentence
  that describes the layout. "…three boxes joined by arrows. The boxes read
  Tokenizer, Transformer, Classifier." rendered all three words correctly;
  "…three labelled boxes left to right, Encoder, Router, Decoder, joined by
  arrows…" rendered `Enc:der`. Four out of four runs that stated the labels
  as a separate final sentence spelled every one of them right, including the
  same words the inline phrasing had corrupted. Word length was not the
  driver — `Transformer` and `Classifier` both came out clean
- Specify colors, fonts, layout, and what to exclude
- Use `--style neurips` for academic papers. It also pins the figure to the
  same colours every DATA figure in the paper uses — seaborn's `colorblind`
  — and tells the model not to let red-versus-green be the only difference
  between two elements, which is the one pairing that carries no meaning for
  about 8% of male readers
- Any number that DOES appear — a throughput on an arrow, a stage count —
  has to be stated explicitly, and read back off the image to check it
  survived. If the figure is mostly numbers, it is a data figure: stop and
  use `aii-data-fig-gen`, which renders them instead of approximating them
- 1K resolution is default and most reliable

## Figure type templates

An image model draws what you name and invents what you leave out, so the
prompt for each kind of concept figure has a different set of things it
cannot omit. Each entry below names the kind, its usual aspect ratio and those
things; start from the one that matches and add the specifics.

- **Architecture / pipeline diagram** (`21:9`) — every stage in order, left to
  right; what flows along each arrow and which way it points; which stages are
  yours vs. baseline or off-the-shelf; where the boundary of the system sits.
- **Flow chart** (`21:9` or `16:9`) — each decision point and both of its
  outcomes; where a branch rejoins; the start and the terminal states; that
  arrows are labelled, not bare.
- **Side-by-side comparison** (`16:9`) — what the two panels are, in which
  order; that both use the SAME visual vocabulary so only the difference
  differs; a caption strip or heading per panel.
- **Conceptual artwork / cover** (`1:1`, `16:9`) — the single idea in one
  sentence; the metaphor and what maps to what; that no text appears unless you
  asked for it, since invented labels are the usual failure.

Two things every entry shares: state the sans-serif requirement (`--style
neurips` does it for you), and read the image back to check that nothing was
invented — a stage that is not in your pipeline, an arrow that runs the wrong
way, a label you never wrote.

Reading it back is not optional, and re-running is a real fix. The same prompt
sent twice gave a correct three-box chain once and, the other time, four boxes
with `Encoder` in two of them and an arrow pointing at nothing — identical
text, different diagram. So a structure you cannot check by looking is a
structure you do not have; when it comes back wrong, generate it again rather
than editing the prompt, because the prompt was not what failed.

## Aspect Ratios

Pick by shape, not by venue. `--help` lists all ten; these are the ones a
paper figure normally wants.

| Ratio | Use Case |
|-------|----------|
| `21:9` | Ultra-wide — pipelines, architecture, the hero figure |
| `16:9` | Wide — side-by-side comparisons, multi-panel concepts |
| `4:3`, `3:2`, `5:4` | Standard — one diagram with room around it |
| `1:1` | Square — a symmetric diagram, a cover image |
| `9:16`, `3:4`, `2:3`, `4:5` | Vertical — a stacked flow or poster |

**If the ability server is not running**, nothing needs doing: the CLI already
falls back to running the same function in-process, so `concept_fig_gen.py`
works standalone. Verified — with no server reachable it still resolves the
free/paid path and reports its own errors ("OPENROUTER_API_KEY not set")
rather than a connection failure.

What it needs is the deps. If the import fails, install them INTO THE VENV
`$PY` names above — creating a `.venv` in whatever directory you happen to be
standing in leaves `$PY` pointing at the same broken interpreter:
```bash
CLIENT_VENV="$SKILL_DIR/../.ability_client_venv"
uv venv "$CLIENT_VENV" --python=3.12          # only if it is not there yet
uv pip install --python="$CLIENT_VENV/bin/python" \
  -r "$SKILL_DIR/scripts/server_requirements.txt"
```
````

### [3] SYSTEM-USER prompt · 2026-10-26 03:42:20 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [4] SYSTEM-USER prompt · 2026-10-26 03:44:12 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [5] SYSTEM-USER prompt · 2026-10-26 03:44:26 UTC

```
[Image: original 3456x538, displayed at 2000x311. Multiply coordinates by 1.73 to map to original image.]
```

### [6] SYSTEM-USER prompt · 2026-10-26 03:44:36 UTC

```
[Image: original 3072x344, displayed at 2000x224. Multiply coordinates by 1.54 to map to original image.]
```

### [7] SYSTEM-USER prompt · 2026-10-26 03:44:54 UTC

```
[Image: original 4916x175, displayed at 2000x71. Multiply coordinates by 2.46 to map to original image.]
```

### [8] SYSTEM-USER prompt · 2026-10-26 03:46:08 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [9] SYSTEM-USER prompt · 2026-10-26 03:46:26 UTC

```
[Image: original 3072x306, displayed at 2000x199. Multiply coordinates by 1.54 to map to original image.]
```

### [10] SYSTEM-USER prompt · 2026-10-26 03:46:32 UTC

```
[Image: original 2036x384, displayed at 2000x377. Multiply coordinates by 1.02 to map to original image.]
```

### [11] SYSTEM-USER prompt · 2026-10-26 03:46:34 UTC

```
[Image: original 2152x1228, displayed at 2000x1141. Multiply coordinates by 1.08 to map to original image.]
```

### [12] SYSTEM-USER prompt · 2026-10-26 03:46:38 UTC

```
[Image: original 5321x121, displayed at 2000x45. Multiply coordinates by 2.66 to map to original image.]
```

### [13] SYSTEM-USER prompt · 2026-10-26 03:49:26 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [14] SYSTEM-USER prompt · 2026-10-26 03:49:28 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [15] SYSTEM-USER prompt · 2026-10-26 03:49:44 UTC

```
[Image: original 3072x306, displayed at 2000x199. Multiply coordinates by 1.54 to map to original image.]
```

### [16] SYSTEM-USER prompt · 2026-10-26 03:49:46 UTC

```
[Image: original 3072x306, displayed at 2000x199. Multiply coordinates by 1.54 to map to original image.]
```

### [17] SYSTEM-USER prompt · 2026-10-26 03:49:54 UTC

```
[Image: original 5321x121, displayed at 2000x45. Multiply coordinates by 2.66 to map to original image.]
```

### [18] SYSTEM-USER prompt · 2026-10-26 03:49:56 UTC

```
[Image: original 5321x121, displayed at 2000x45. Multiply coordinates by 2.66 to map to original image.]
```

### [19] SYSTEM-USER prompt · 2026-10-26 03:50:10 UTC

```
[Image: original 3819x1043, displayed at 2000x546. Multiply coordinates by 1.91 to map to original image.]
```
