import json, sys, collections
P=sys.argv[1]
rows={json.loads(l)['uid']:json.loads(l) for l in open(P+'/data/samples_v9.jsonl')}
reads=[json.loads(l) for l in open(P+'/data/manual_reads_v9.jsonl')]
summ=json.load(open(P+'/results/manual_reads_summary.json'))
items={i['uid']:i for i in summ['items']}
MECH={"bfs":"BFS","dfs":"DFS","iddfs":"ID","astar":"HEUR","gbfs":"HEUR","bibfs":"BIDIR","biastar":"BIDIR","idastar":"ID","jps":"HEUR","dijkstra_unit":"BFS"}
for cell in ['A_k5','A_k5_ho','E_k5','E_k5_ho']:
    rs=[r for u,r in rows.items() if r['cell']==cell]
    cb={MECH[b] for b in rs[0]['banned_set']}
    comp=[r for r in rs if r.get('code') and r.get('runtime_label') not in (None,'invalid') and not r.get('truncated')]
    nc=[r for r in comp if MECH.get(r['runtime_label'],'OTHER') in cb]
    read=[r for r in nc if r['uid'] in items]
    c=collections.Counter((r['runtime_label'], items[r['uid']]['family'], items[r['uid']]['read_class']) for r in read)
    print(cell,'completed',len(comp),'runtime-noncompliant',len(nc),'of which hand-read',len(read), dict(c))
    # mechanism compliance if hand-read class replaces runtime class for read programs
    ok=0
    for r in comp:
        if r['uid'] in items:
            ok += items[r['uid']]['read_class'] not in cb
        else:
            ok += MECH.get(r['runtime_label'],'OTHER') not in cb
    print('   mech compliance runtime',round(1-len(nc)/len(comp),3),' with hand reads substituted', round(ok/len(comp),3), ' tracer', round(sum(1 for r in comp if r.get('order_class') not in cb)/len(comp),3))
