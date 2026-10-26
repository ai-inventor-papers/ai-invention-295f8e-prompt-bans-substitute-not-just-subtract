import os
from pathlib import Path
# Artifact folder: set EXP29_DIR; defaults to the sibling folder art_lpQalcAXMGr1 of the published repository.
ART = Path(os.environ.get('EXP29_DIR', str(Path(__file__).resolve().parents[2] / 'art_lpQalcAXMGr1')))
import json, collections, sys
from math import comb
base = str(ART) + '/'
rows=[json.loads(l) for l in open(base+'data/samples.jsonl')]
labels=collections.Counter((r['task'],r['label']) for r in rows)
print(sorted(labels.items()))
DEF={'T10':'union_find','T2':'dijkstra'}
def binom_sf(k,n,p):
    return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
def share(rs,default):
    valid=[r for r in rs if r['label'] not in ('invalid','disputed')]
    off=sum(1 for r in valid if r['label'] not in ('other',default))
    n=len(valid); npass=sum(1 for r in rs if r['passed'])
    return dict(n=len(rs),nv=n,off=off,sh=off/n if n else float('nan'),ps=npass/len(rs) if rs else float('nan'))
out={}
for eng in 'abcd':
  for task in ('T10','T2'):
    R=[r for r in rows if r['engine']==eng and r['task']==task]
    tw=share([r for r in R if r['arm']=='TWIN' and int(r['sample_id'])<10],DEF[task])
    pop=collections.defaultdict(list)
    for r in R:
        if r['family']=='POP' and r['direction_seed'] is not None and float(r['alpha'])==2.0:
            pop[int(r['direction_seed'])].append(r)
    nrun=nscr=nconf=0
    for s,rr in sorted(pop.items()):
        first=[r for r in rr if int(r['sample_id']) in (0,1)]
        if not first: continue
        nrun+=1
        f=share(first,DEF[task]); pl=share([r for r in rr if 0<=int(r['sample_id'])<=5],DEF[task])
        scr = f['nv']>0 and f['sh']-tw['sh']>=0.2-1e-12 and f['ps']>=0.8*tw['ps']-1e-12
        nscr+=scr
        if scr and pl['n']>f['n']:
            p0=(tw['off']+0.5)/(tw['nv']+1)
            pb=binom_sf(pl['off'],pl['nv'],p0)
            if pl['sh']-tw['sh']>=0.2-1e-12 and pb<0.05 and pl['ps']>=0.8*tw['ps']-1e-12: nconf+=1
    print(eng,task,'twin',tw,'run',nrun,'screen',nscr,'conf',nconf, 'E', nconf/nrun if nrun else None)
