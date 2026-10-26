"""Apply the iteration-6 record-audit corrections (art_aRTQM6CQ0Dre corrections.json) in place,
with report-writer overrides where the four-engine control of the same iteration supersedes
the audit's engine wording. Closing-section corrections are folded into the rewritten closing."""
import json, re, sys
SRC = str(__import__("pathlib").Path(__file__).resolve().parents[3] / 'round-6/evaluation-5/src/corrections.json')
c = json.load(open(SRC))['corrections']
txt = open('paper_draft.md').read()
CLOSING = {'C6-008', 'C6-009', 'C6-010', 'C6-015', 'C6-024', 'C6-034', 'C6-035'}
by = {it['id']: it for it in c}
over = {}
over['C6-002'] = by['C6-002']['new_text'] + ' At iteration 4\'s absolute unit, its direction seeds and its slots, the bf16 engine reproduces the 8-bit plan-noise column (Section 6.3; iteration-6 correction).'
over['C6-003'] = by['C6-003']['new_text'] + ' The four-engine control of Section 6.3 then tested the numerics directly: at iteration 4\'s own absolute displacement, direction seeds and slots, the bf16 engine reproduces the 8-bit rows (per-sample plan noise at alpha 2: connected components 25 of 50 valid attempts off the default under bf16 against 30 of 50 under the 8-bit engine; shortest path 22 of 50 under both), so the non-replication tagged here belongs to iteration 5\'s ban-free unit and direction seeds, not to the bf16 numerics.'
over['C6-005'] = ('(pooled contrast against temperature 0.545 [0.41, 0.67], p = 1.0e-5). *(Engine tag, iteration 6: HF-FP8-W8A8; the same-seed contrast itself was not rerun in bf16 [ARTIFACT:art_Yu6GN6pLxW8f]. Per-sample plan noise on the shortest path task did not replicate in iteration 5\'s bf16 cells at the ban-free unit (2 of 47 correct programs off the default at bf16 alpha 2 against 9 of 43 at FP8 alpha 1, bracket p 0.017), but at iteration 4\'s own absolute unit and seeds the bf16 engine reproduces it (22 of 50 valid attempts off the default at alpha 2 under both engines; Section 6.3).)*')
over['C6-006'] = ('at matched downstream displacement the plan site keeps a large advantage (indicator +2.15 [1.79, 2.51]; odds ratio 5.72 [3.94, 8.30]) *(engine tag, iteration 6: HF-FP8-W8A8 [ARTIFACT:art_Cx9JOh8soBw7], not rerun in that form. The bf16 rerun at the ban-free unit of Section 6.4 withdrew the committed site rule, because the condition-span arm never reached the plan site\'s downstream displacement and alpha 8 broke every plan-site program; a post-hoc model restricted to alpha of 4 or less puts the read position below the task-specification site on both tasks.)*')
over['C6-007'] = ('It wins kth smallest (5-point Hill-1 2.72) and connected components (2.09) at no pass cost *(engine tag, iteration 6: HF-FP8-W8A8 at the ban unit; under bf16 and the ban-free unit of iteration 5 the same prices are 1.98 and 1.09, and on connected components 1 of 50 correct programs left the default at bf16 alpha 2 against 30 of 50 at 8-bit alpha 2 (Fisher p 7.2e-11). The four-engine control of Section 6.3 traces that gap to the unit and the direction seeds, not to the numerics: at iteration 4\'s absolute unit and seeds, bf16 plan noise moves connected components in 25 of 50 valid attempts.)*')
over['C6-011'] = by['C6-011']['new_text'].replace('The figure (fig_beta_escape_l4l, iteration 6) plots', 'The figure, corrected in iteration 6, plots').replace('the new units.', 'the new units, both at iteration 5\'s ban-free unit.')
nt = by['C6-023']['new_text']
assert '; bf16-conditional. ' in nt
over['C6-023'] = nt.replace('; bf16-conditional. ', '; conditional on iteration 5\'s design (bf16 with the ban-free unit and its direction seeds; the four-engine control of Section 6.3 shows that the numerics alone do not shrink the escapes). ')
over['C6-025'] = ('the six screen-movable tasks of iteration 4 shrank to two under bf16 and the ban-free unit, for reasons this iteration did not establish. *(Iteration-6 correction: a dose-bracketed contrast rules out a scalar dose shortfall on connected components and shortest path, and the four-engine control rules out the bf16 numerics, since at iteration 4\'s absolute unit and seeds bf16 reproduces the 8-bit escapes (Section 6.3). What remains is the per-position and per-block profile of the ban-free unit, or the direction seeds; every verdict that rests on bf16 plan noise or escape fractions at the ban-free unit is conditional on that design.)*')
over['C6-026'] = ('and under the bf16 engine and ban-free unit plan noise moves more than 10% of programs only on kth smallest (conditional on iteration 5\'s design, bf16 with the ban-free unit and its direction seeds: at iteration 4\'s absolute unit and seeds the bf16 engine reproduces the 8-bit effects on connected components and the shortest path task, Section 6.3; iteration-6 correction).')
# report-writer additions (marked)
extra = [
 ('the other movable tasks escape on the 8-bit directions of the locus experiment.',
  'the other movable tasks escape on the 8-bit directions of the locus experiment. *(Correction, iteration 6: the screen\'s escapes are properties of the model, not of the 8-bit engine. Iteration 4\'s 40-direction escape fractions reproduce in bf16 at the same absolute displacement, and the screen\'s shortest path positive-control direction 9004 moves that task in bf16 as well (Section 6.3); the shrinkage of the screen under iteration 5\'s ban-free unit belongs to that unit and its direction seeds.)*'),
 ('Those two directions therefore do not explain the difference, and its cause is not established here.',
  'Those two directions therefore do not explain the difference, and its cause is not established here. *(Correction, iteration 6: the four-engine control of Section 6.3 establishes that the cause is not the bf16 numerics. At iteration 4\'s own absolute unit, direction seeds and slots, bf16 escapes on almost the same directions as the 8-bit engine (connected components 26 of 40 against 29 of 40; shortest path 6 of 40 against 8 of 40). The shrinkage belongs to iteration 5\'s ban-free unit or its direction seeds, and the heading should read that movability depends on the unit and the direction draw.)*'),
]
applied = []
for it in c:
    if it['id'] in CLOSING:
        continue
    old = it['old_text']; new = over.get(it['id'], it['new_text'])
    n = txt.count(old)
    if n != 1:
        print('COUNT', it['id'], n); sys.exit(1)
    # convert raw artifact ids not already in markers
    new = re.sub(r'(?<!ARTIFACT:)\b(art_[A-Za-z0-9_\-]{12})\b', r'[ARTIFACT:\1]', new)
    new = new.replace('[ARTIFACT:[ARTIFACT:', '[ARTIFACT:').replace(']]', ']')
    txt = txt.replace(old, new)
    applied.append(it['id'])
for old, new in extra:
    assert txt.count(old) == 1, old
    txt = txt.replace(old, new)
open('paper_draft.md', 'w').write(txt)
print('applied', len(applied), applied)
