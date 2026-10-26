import json, sys, collections
P=sys.argv[1]
rows=[json.loads(l) for l in open(P+'/data/samples_v9.jsonl')]
MECH={"bfs":"BFS","dfs":"DFS","iddfs":"ID","astar":"HEUR","gbfs":"HEUR","bibfs":"BIDIR","biastar":"BIDIR","idastar":"ID","jps":"HEUR","dijkstra_unit":"BFS"}
for cell in ['A_k1','A_k2','A_k3','A_k4','A_k5','A_k5_ho','E_k1','E_k2','E_k3','E_k4','E_k5','E_k5_ho','C_desc','F_gptoss_ban']:
    rs=[r for r in rows if r['cell']==cell]
    banned=set(rs[0]['banned_set'])
    cb={MECH[b] for b in banned}
    comp=[r for r in rs if r.get('code') and r.get('runtime_label') not in (None,'invalid') and not r.get('truncated')]
    noncomp=[r for r in comp if MECH.get(r['runtime_label'],'OTHER') in cb]
    lexnc=[r for r in noncomp if r.get('lexical_L1')]
    c=collections.Counter(r['runtime_label'] for r in noncomp)
    cl=collections.Counter(r['runtime_label'] for r in lexnc)
    allc=collections.Counter(r['runtime_label'] for r in comp)
    print(cell, sorted(banned), 'n_comp',len(comp),'mech_noncomp',len(noncomp), 'lexOK&mechNC', len(lexnc), dict(cl), '| all runtime labels', dict(allc))
