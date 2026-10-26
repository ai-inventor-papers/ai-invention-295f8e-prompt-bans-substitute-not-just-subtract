import os
from pathlib import Path
# Artifact folder: set EXP30_DIR; defaults to the sibling folder art_rMlbrjVB1c__ of the published repository.
ART = Path(os.environ.get('EXP30_DIR', str(Path(__file__).resolve().parents[2] / 'art_rMlbrjVB1c__')))
import json, collections
from math import comb
base = str(ART) + '/'
L=[json.loads(l) for l in open(base+'data/labels.jsonl')]
# dedupe by sample_id keep last
d={}
for r in L: d[r['sample_id']]=r
L=list(d.values())
c=collections.Counter((r['task'],r['arm'],r['cell']) for r in L)
tasks=sorted(set(r['task'] for r in L))
print(tasks)
cells=collections.defaultdict(list)
for r in L: cells[(r['task'], r['cell'] + ('_' + str(r['band']) if r.get('band') else ''))].append(r)
Y={'T2':'bf_spfa','T03':'quickselect','T10':'bfs','T05':'brute_force','T06':'index_marking','T1':'dfs'}
DEF={'T2':'dijkstra','T03':'full_sort','T10':'union_find','T05':'hash_map','T06':'hash_set','T1':'bfs'}
for t in ['T2','T03','T10','T05','T06','T1']:
    for (tt,cell),rs in sorted(cells.items()):
        if tt!=t: continue
        n=len(rs); 
        # Y share among all attempts? among correct? compute both
        corr=[r for r in rs if r['passed']]
        ycor=sum(1 for r in corr if r['label']==Y[t]); yall=sum(1 for r in rs if r['label']==Y[t])
        off=sum(1 for r in rs if r['label'] not in (DEF[t],'invalid','disputed','other'))
        comp=collections.Counter(r['label'] for r in corr)
        print(t,cell,n,'Y_attempts',yall,'Y_correct',ycor,'off_all',off,'pass',round(len(corr)/n,2),dict(comp))
