"""Recompute per-sample plan-noise counts per engine (engine control, art_lpQalcAXMGr1) on two definitions:
valid attempts off the default (the report's Table 238) and correct programs off the default."""
import os
from pathlib import Path
# Artifact folder: set EXP29_DIR; defaults to the sibling folder art_lpQalcAXMGr1 of the published repository.
ART = Path(os.environ.get('EXP29_DIR', str(Path(__file__).resolve().parents[2] / 'art_lpQalcAXMGr1')))

import json, collections, os
base = str(ART) + '/'
DEF = {'T10': 'union_find', 'T2': 'dijkstra'}
att = collections.defaultdict(lambda: [0, 0])
cor = collections.defaultdict(lambda: [0, 0])
for l in open(base + 'data/samples.jsonl'):
    r = json.loads(l)
    if r['family'] != 'PN':
        continue
    k = (r['task'], r['arm'], r['engine'])
    off = r['label'] not in ('other', 'invalid', 'disputed', DEF[r['task']])
    if r['label'] not in ('invalid', 'disputed'):
        att[k][1] += 1
        att[k][0] += off
    if r['passed']:
        cor[k][1] += 1
        cor[k][0] += off
for k in sorted(att):
    print(k, 'valid-attempt off-default', f'{att[k][0]}/{att[k][1]}', '| correct off-default', f'{cor[k][0]}/{cor[k][1]} correct (of 50)')
