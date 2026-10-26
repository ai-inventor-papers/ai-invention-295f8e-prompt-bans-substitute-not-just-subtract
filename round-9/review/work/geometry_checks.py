import json, sys, collections, statistics as st
# usage: python3 -I geometry_checks.py <path to the geometry artifact (gen_art_experiment_46)>
P=sys.argv[1]
red=json.load(open(P+'/results/rederive.json'))['manifolds']
print('== unit-weight Dijkstra g / median of non-banned g at k 15 (Table 435)')
for m,v in red.items():
    if 'k15' not in v: continue
    g=v['k15']['g']; med=st.median(g.values())
    print(' ',m,'ratio',round(g['dijkstra_unit']/med,3),'rank',sorted(g,key=g.get).index('dijkstra_unit')+1,'of',len(g),'class',v['k15']['classes']['dijkstra_unit'])
print('== RSA, all model matrices in rsa.json (Table 437 shows R_lex, R_beh, R_surface, R_len only)')
rsa=json.load(open(P+'/results/rsa.json'))
for m,v in rsa.items():
    if isinstance(v,dict) and 'models' in v:
        print(' ',m,{k:(round(x['rho'],2),round(x['p_exact'],3)) for k,x in v['models'].items()})
def fam(r):
    if r['label']=='dijkstra_unit': return 'unit-weight Dijkstra'
    o=(r.get('other_name') or '').lower()
    if 'bellman' in o or 'spfa' in o: return 'Bellman-Ford/SPFA'
    if 'deque' in o or 'bfs' in o: return 'BFS variant'
    return 'other known'
print('== placement of every iteration-8 survivor by family (Table 438 reports unit-weight Dijkstra only)')
pl=json.load(open(P+'/results/placement.json'))
for frame,v in pl.items():
    if not isinstance(v,dict) or 'rows' not in v: continue
    c=collections.defaultdict(collections.Counter)
    for r in v['rows']:
        if r['set']=='SURV': c[fam(r)][r['class']]+=1
    print(' ',frame,'LOO',round(v['G_place']['loo_accuracy'],2),'frame median g',round(v['frame_median'],1),{k:dict(x) for k,x in c.items()})
