import json, sys, collections, math, random
P=sys.argv[1]
rows=[json.loads(l) for l in open(P+'/results/retrace.jsonl')]
MECH={"bfs":"BFS","dfs":"DFS","iddfs":"ID","astar":"HEUR","gbfs":"HEUR","bibfs":"BIDIR","biastar":"BIDIR","idastar":"ID","jps":"HEUR","dijkstra_unit":"BFS"}
BAN={"BFS","DFS","ID","HEUR"}
def rc(r):
    lab=r.get('runtime_label')
    if not r.get('has_code') or lab in (None,'invalid'): return 'UNTRACEABLE'
    return MECH.get(lab,'OTHER')
by=collections.defaultdict(list)
for r in rows: by[r['config']].append(r)
gaps={}
tot_cov=collections.Counter(); tot_n=0
for c,rs in sorted(by.items(), key=lambda x:int(x[0][1:])):
    a=b=cc=d=0; cov=collections.Counter(); covtr=collections.Counter()
    for r in rs:
        if not r.get('has_code'): continue
        m=rc(r)
        if m=='UNTRACEABLE': continue
        lx=bool(r.get('lexical_L1')); mo= m not in BAN
        if lx and mo: a+=1
        elif lx and not mo:
            b+=1; cov[r.get('runtime_label')]+=1; covtr[r.get('order_class')]+=1
        elif (not lx) and mo: cc+=1
        else: d+=1
    n=a+b+cc+d
    gaps[c]=((a+b)/n-(a+cc)/n)
    tot_cov.update(cov); tot_n+=n
    print(c, n, 'lex',round((a+b)/n,3),'mech',round((a+cc)/n,3),'gap',round(gaps[c],3),'covert',b, dict(cov), 'tracer of covert', dict(covtr))
print('pooled equal weight', sum(gaps.values())/len(gaps))
print('covert by runtime label', dict(tot_cov), 'total covert', sum(tot_cov.values()), 'n', tot_n)
# gap if dijkstra_unit / jps / idastar counted as compliant (i.e. only bfs,dfs,iddfs,astar,gbfs labels non-compliant)
NAMEBAN={"bfs","dfs","iddfs","astar","gbfs"}
g2={}
for c,rs in by.items():
    a=b=cc=d=0
    for r in rs:
        if not r.get('has_code'): continue
        lab=r.get('runtime_label')
        if lab in (None,'invalid'): continue
        mo = lab not in NAMEBAN
        lx=bool(r.get('lexical_L1'))
        if lx and mo: a+=1
        elif lx and not mo: b+=1
        elif (not lx) and mo: cc+=1
        else: d+=1
    n=a+b+cc+d
    g2[c]=((a+b)-(a+cc))/n
print('gap if only the 5 banned runtime labels count as banned:', {k:round(v,3) for k,v in sorted(g2.items(), key=lambda x:int(x[0][1:]))}, 'pooled', round(sum(g2.values())/len(g2),3))
