import os
from pathlib import Path
# Artifact folder: set EXP29_DIR; defaults to the sibling folder art_lpQalcAXMGr1 of the published repository.
ART = Path(os.environ.get('EXP29_DIR', str(Path(__file__).resolve().parents[2] / 'art_lpQalcAXMGr1')))
import json, collections
from math import comb
base = str(ART) + '/'
rows=[json.loads(l) for l in open(base+'data/samples.jsonl')]
DEF={'T10':'union_find','T2':'dijkstra'}
# engine b T10 pooled sizes
c=collections.Counter()
for r in rows:
    if r['engine']=='b' and r['task']=='T10' and r['family']=='POP' and float(r['alpha'] or 0)==2.0:
        c[r['direction_seed']]+=1
print('b T10 alpha2 rows per direction', sorted(c.values()))
# screen slots: sample_id in (0,1) x 5 templates x 40 directions = 400 slots; pair by (direction, template, sample_id)
def key(r): return (r['direction_seed'], r['template'], int(r['sample_id']))
def mcn(b,c):
    n=b+c; k=min(b,c)
    p=sum(comb(n,i) for i in range(0,k+1))/2**n*2
    return min(1,p)
for task in ('T10','T2'):
    d={}
    for eng in 'abcd':
        d[eng]={}
        for r in rows:
            if r['engine']==eng and r['task']==task and r['family']=='POP' and float(r['alpha'] or 0)==2.0 and int(r['sample_id']) in (0,1):
                off = r['label'] not in ('invalid','disputed','other',DEF[task])
                d[eng][key(r)]=(off, r['label'])
    for x,y in [('a','d'),('c','d'),('b','d'),('a','c'),('a','b')]:
        ks=set(d[x])&set(d[y])
        n10=sum(1 for k in ks if d[x][k][0] and not d[y][k][0]); n01=sum(1 for k in ks if d[y][k][0] and not d[x][k][0])
        sx=sum(d[x][k][0] for k in ks)/len(ks); sy=sum(d[y][k][0] for k in ks)/len(ks)
        same=sum(d[x][k][1]==d[y][k][1] for k in ks)/len(ks)
        print(task,x,y,len(ks),round(sx,3),round(sy,3),n10,n01,'p',round(mcn(n10,n01),4),'same',round(same,3))
