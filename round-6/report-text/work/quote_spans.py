import re,sys
t=open('paper_draft.md').read(); lines=t.split('\n')
s6=next(i for i,l in enumerate(lines) if l.startswith('# Iteration 6:'))
r=next(i for i,l in enumerate(lines) if l.startswith('# References'))
ch=set(int(x)-1 for x in open('work/changed_lines.txt').read().split())
maxw=int(sys.argv[1]) if len(sys.argv)>1 else 15
out=[]
for i,l in enumerate(lines[:r]):
    if not (i>=s6 or i in ch): continue
    pos=[m.start() for m in re.finditer(r"['\"‘’“”]",l)]
    for a,b in zip(pos,pos[1:]):
        inner=l[a+1:b]
        w=len(inner.split())
        if w<=maxw:
            punct=bool(re.search(r"[.,;:()\[\]*]",inner))
            out.append((i+1,w,punct,inner,l[max(0,a-50):b+30]))
for o in out:
    print(f"{o[0]} {o[1]}w {'P' if o[2] else '-'} <<{o[3]}>>\n      ctx: {o[4]}")
print('count',len(out),'nopunct',sum(1 for o in out if not o[2]))
