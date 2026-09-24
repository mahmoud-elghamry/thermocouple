import json,sys,collections,itertools
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from geom import load,body
from segs import on_seg,seg_hits_box,EPS
SCH=sys.argv[1]
G=1.27
def R(v): return round(round(v/G)*G,2)
root,libs,syms=load(SCH)
from kon import K as _K
_k=_K(); _k.load("sch_export")
d=json.loads(_k.call("export_netlist_summary",schematic=SCH))
P=[]; boxes=[]; pinlines=[]
for s in syms:
    bb,tips=body(s,libs)
    if bb: boxes.append((s['ref'],bb))
    for num,t in tips.items(): pinlines.append((s['roots'][num],t))
for c in d["components"]:
    for p in c["pins"]:
        net=p["net"]
        if net=="~": net="~%s.%s"%(c["reference"],p["number"])
        P.append((c["reference"],p["number"],net,round(p["x"],2),round(p["y"],2)))
PWR=lambda n: n.startswith(("GND","+","CHASSIS"))
wires=[]   # (net,a,b)
def overlap_len(a,b,c,e):
    if abs(a[0]-b[0])<EPS and abs(c[0]-e[0])<EPS and abs(a[0]-c[0])<EPS:
        return min(max(a[1],b[1]),max(c[1],e[1]))-max(min(a[1],b[1]),min(c[1],e[1]))
    if abs(a[1]-b[1])<EPS and abs(c[1]-e[1])<EPS and abs(a[1]-c[1])<EPS:
        return min(max(a[0],b[0]),max(c[0],e[0]))-max(min(a[0],b[0]),min(c[0],e[0]))
    return -1
def path_ok(net,pts):
    segs=list(zip(pts,pts[1:]))
    for a,b in segs:
        if abs(a[0]-b[0])>EPS and abs(a[1]-b[1])>EPS: return None
        if abs(a[0]-b[0])<EPS and abs(a[1]-b[1])<EPS: return None
        for ref,bb in boxes:
            if seg_hits_box(a,b,bb): return None
        for (r,n,pn,x,y) in P:
            if pn!=net and on_seg((x,y),a,b): return None
        for ra,t in pinlines:
            if overlap_len(a,b,ra,t)>EPS: return None
            # perpendicular crossing of a pin lead (anything but touching its tip)
            if (abs(a[0]-b[0])<EPS)!=(abs(ra[0]-t[0])<EPS):
                v,h=((a,b),(ra,t)) if abs(a[0]-b[0])<EPS else ((ra,t),(a,b))
                X,Y=v[0][0],h[0][1]
                if min(h[0][0],h[1][0])-EPS<=X<=max(h[0][0],h[1][0])+EPS and min(v[0][1],v[1][1])-EPS<=Y<=max(v[0][1],v[1][1])+EPS:
                    if not (abs(X-t[0])<EPS and abs(Y-t[1])<EPS): return None
    cross=0
    for wn,c,e in wires:
        for a,b in segs:
            if wn!=net:
                if on_seg(c,a,b) or on_seg(e,a,b) or on_seg(a,c,e) or on_seg(b,c,e) or overlap_len(a,b,c,e)>EPS: return None
                # perpendicular interior crossing
                if (abs(a[0]-b[0])<EPS)!=(abs(c[0]-e[0])<EPS):
                    v,h=((a,b),(c,e)) if abs(a[0]-b[0])<EPS else ((c,e),(a,b))
                    if min(h[0][0],h[1][0])<v[0][0]<max(h[0][0],h[1][0]) and min(v[0][1],v[1][1])<h[0][1]<max(v[0][1],v[1][1]): cross+=1
            else:
                if overlap_len(a,b,c,e)>EPS: return None
    L=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in segs)
    return L+cross*20+(len(segs)-1)*2.5
def candidates(A,B):
    (ax,ay),(bx,by)=A,B
    yield [A,B]
    yield [A,(bx,ay),B]; yield [A,(ax,by),B]
    xs=sorted(set(R(ax+(bx-ax)*f) for f in (0.25,0.5,0.75))|{R(min(ax,bx)-k*G) for k in (2,4)}|{R(max(ax,bx)+k*G) for k in (2,4)})
    for mx in xs: yield [A,(mx,ay),(mx,by),B]
    ys=sorted(set(R(ay+(by-ay)*f) for f in (0.25,0.5,0.75))|{R(min(ay,by)-k*G) for k in (2,4)}|{R(max(ay,by)+k*G) for k in (2,4)})
    for my in ys: yield [A,(ax,my),(bx,my),B]
def dedup(pts):
    out=[pts[0]]
    for p in pts[1:]:
        if abs(p[0]-out[-1][0])>EPS or abs(p[1]-out[-1][1])>EPS: out.append(p)
    # merge collinear
    o=[out[0]]
    for i in range(1,len(out)-1):
        a,b,c=o[-1],out[i],out[i+1]
        if (abs(a[0]-b[0])<EPS and abs(b[0]-c[0])<EPS) or (abs(a[1]-b[1])<EPS and abs(b[1]-c[1])<EPS): continue
        o.append(b)
    o.append(out[-1]); return o
parent={}
def f(x):
    while parent.setdefault(x,x)!=x: x=parent[x]
    return x
import os
ONLY=set(json.load(open(os.environ['ONLY']))) if os.environ.get('ONLY') else None
bynet=collections.defaultdict(list)
for p in P:
    if not p[2].startswith("~") and (ONLY is None or p[0] in ONLY): bynet[p[2]].append(p)
edges=[]
for net,ps in bynet.items():
    lim=22.0 if PWR(net) else 40.0
    for a,b in itertools.combinations(ps,2):
        dd=abs(a[3]-b[3])+abs(a[4]-b[4])
        if dd<=lim: edges.append((dd,net,a,b))
edges.sort(key=lambda e:e[0])
acc=[];fail=0
for dd,net,a,b in edges:
    ka,kb=(a[0],a[1]),(b[0],b[1])
    if f(ka)==f(kb): continue
    if dd<EPS: parent[f(ka)]=f(kb); continue
    best=None
    for c in candidates((a[3],a[4]),(b[3],b[4])):
        c=dedup(c)
        sc=path_ok(net,c)
        if sc is not None and (best is None or sc<best[0]): best=(sc,c)
    if best:
        for u,v in zip(best[1],best[1][1:]): wires.append((net,u,v))
        parent[f(ka)]=f(kb); acc.append((net,ka,kb,best[1]))
    else: fail+=1
groups=collections.defaultdict(list)
for p in P:
    if not p[2].startswith("~"): groups[(p[2],f((p[0],p[1])))].append(p)
print("edges accepted",len(acc),"no route",fail,"wire segs",len(wires))
print("groups",len(groups),"nets",len(bynet))
json.dump({"routes":[(n,list(ka),best) for n,ka,kb,best in acc],"groupof":{"%s.%s"%k_:"%s.%s"%f(k_) for k_ in list(parent)},"wires":[(n,a,b) for n,a,b in wires],"groups":[[list(x) for x in g] for g in groups.values()],"gkeys":["%s.%s"%f((g[0][0],g[0][1])) for g in groups.values()]},open(sys.argv[2] if len(sys.argv)>2 else "plan.json","w"))
