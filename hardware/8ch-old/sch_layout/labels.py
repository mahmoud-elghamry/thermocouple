import json,sys,collections,math
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from kon import K
from geom import load,body,kids,kid
G=1.27; EPS=1e-6
def tw(net): return 1.05*len(net)+0.6
def tbox(net,x,y,rot):
    w=tw(net)
    if rot==0:   return (x+0.25,y-1.9,x+0.25+w,y-0.15)
    if rot==180: return (x-0.25-w,y-1.9,x-0.25,y-0.15)
    if rot==90:  return (x-1.9,y-0.25-w,x-0.15,y-0.25)
    return (x-1.9,y+0.25,x-0.15,y+0.25+w)   # 270
def ov(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def field_boxes(root):
    out=[]
    for s in kids(root,'symbol'):
        for p in kids(s,'property'):
            if p[1] not in ('Reference','Value'): continue
            eff=kid(p,'effects')
            if eff and any(isinstance(e,list) and e[0]=='hide' and e[1]=='yes' for e in eff): continue
            if eff and 'hide' in eff: continue
            at=kid(p,'at'); x,y=float(at[1]),float(at[2]); r=float(at[3]) if len(at)>3 else 0
            w=1.05*len(p[2]); h=1.4
            j=kid(eff,'justify') if eff else None; j=j[1:] if j else []
            if int(r)%180==0:
                x0=x-w/2; 
                if 'left' in j: x0=x
                if 'right' in j: x0=x-w
                out.append((x0,y-h/2,x0+w,y+h/2))
            else:
                y0=y-w/2
                if 'left' in j: y0=y-w
                if 'right' in j: y0=y
                out.append((x-h/2,y0,x+h/2,y0+w))
    return out
def place(SCH,plan):
    k=K(); k.load("sch_wiring","sch_analysis","sch_export")
    pl=json.load(open(plan))
    root,libs,syms=load(SCH)
    obs=[]  # (box,weight)
    for s in syms:
        bb,t=body(s,libs)
        if bb: obs.append(((bb[0]+0.2,bb[1]+0.2,bb[2]-0.2,bb[3]-0.2),5))
        for num,tip in t.items():
            r=s['roots'][num]; obs.append(((min(r[0],tip[0])-1.4,min(r[1],tip[1])-1.4,max(r[0],tip[0])+1.4,max(r[1],tip[1])+1.4),2))
    for b in field_boxes(root): obs.append((b,3))
    for b in ((-50,-50,650,13.5),(-50,-50,13.5,500),(580,-50,700,500),(-50,406,700,500)): obs.append((b,20))
    W=[(float(kid(w,'pts')[1][1]),float(kid(w,'pts')[1][2]),float(kid(w,'pts')[2][1]),float(kid(w,'pts')[2][2])) for w in kids(root,'wire')]
    for x1,y1,x2,y2 in W: obs.append(((min(x1,x2)-0.1,min(y1,y2)-0.1,max(x1,x2)+0.1,max(y1,y2)+0.1),1))
    for n in kids(root,'no_connect'):
        at=kid(n,'at'); x,y=float(at[1]),float(at[2]); obs.append(((x-0.8,y-0.8,x+0.8,y+0.8),2))
    pts=set()
    for s in syms:
        bb,t=body(s,libs); pts|={(round(a,2),round(b,2)) for a,b in t.values()}
    for x1,y1,x2,y2 in W: pts|={(round(x1,2),round(y1,2)),(round(x2,2),round(y2,2))}
    labels=json.loads(k.call("list_schematic_labels",schematic=SCH))["labels"]
    byat=collections.defaultdict(list)
    for l in labels: byat[(l['net'],round(l['x'],2),round(l['y'],2))].append(l)
    routes=collections.defaultdict(list)
    for n,ka,best in pl["routes"]:
        g=pl["groupof"]["%s.%s"%tuple(ka)]
        routes[g]+=list(zip(best[:-1],best[1:]))
    placed=[]; ops_del=[]; ops_add=[]
    S={s['ref']:s for s in syms}
    import os
    ONLY=set(json.load(open(os.environ['ONLY']))) if os.environ.get('ONLY') else None
    for grp,gk in sorted(zip(pl["groups"],pl["gkeys"]),key=lambda z:-len(z[0])):
        net=grp[0][2]
        if ONLY is not None and not all(p[0] in ONLY for p in grp): continue
        cands=[]
        for (a,b) in routes.get(gk,[]):
            a=tuple(a);b=tuple(b)
            if abs(a[1]-b[1])<EPS:  # horizontal
                x0,x1=sorted((a[0],b[0])); y=a[1]
                n0=int(round(x0/G))+1; n1=int(round(x1/G))-1
                for i in range(n0,n1+1):
                    x=round(i*G,2)
                    if (x,y) in pts: continue
                    for r in (0,180): cands.append((x,y,r,0))
            else:
                y0,y1=sorted((a[1],b[1])); x=a[0]
                for i in range(int(round(y0/G))+1,int(round(y1/G))):
                    y=round(i*G,2)
                    if (x,y) in pts: continue
                    for r in (90,270): cands.append((x,y,r,1.5))
        for p in grp:   # pin-anchored fallbacks
            ref,num=p[0],p[1]
            for r in (0,90,180,270): cands.append((p[3],p[4],r,2.0))
        mine={(round(min(a[0],b[0]),2),round(min(a[1],b[1]),2),round(max(a[0],b[0]),2),round(max(a[1],b[1]),2)) for a,b in routes.get(gk,[])}
        def foreign(x,y):
            for x1,y1,x2,y2 in W:
                key=(round(min(x1,x2),2),round(min(y1,y2),2),round(max(x1,x2),2),round(max(y1,y2),2))
                if key in mine: continue
                if (abs(x1-x2)<EPS and abs(x-x1)<EPS and min(y1,y2)-EPS<=y<=max(y1,y2)+EPS) or (abs(y1-y2)<EPS and abs(y-y1)<EPS and min(x1,x2)-EPS<=x<=max(x1,x2)+EPS): return True
            return False
        cands=[c for c in cands if not foreign(c[0],c[1])]
        cx=sum(p[3] for p in grp)/len(grp); cy=sum(p[4] for p in grp)/len(grp)
        best=None
        for x,y,r,pen in cands:
            bx=tbox(net,x,y,r)
            sc=pen+sum(w for b,w in obs if ov(bx,b))*10+sum(10 for b in placed if ov(bx,b))
            sc+=0.02*(abs(x-cx)+abs(y-cy))
            if best is None or sc<best[0]: best=(sc,x,y,r)
        sc,x,y,r=best
        placed.append(tbox(net,x,y,r))
        for p in grp:
            for l in byat.get((net,p[3],p[4]),[]): ops_del.append((net,p[3],p[4]))
        ops_add.append((net,x,y,r))
    for net,x,y in ops_del:
        rr=k.call("delete_schematic_net_label",schematic=SCH,net=net,x=x,y=y); assert 'rror' not in rr[:60],rr
    for net,x,y,r in ops_add:
        rr=k.call("add_schematic_net_label",schematic=SCH,net=net,x=x,y=y,rotation=r); assert 'rror' not in rr[:60],rr
    print("labels removed",len(ops_del),"placed",len(ops_add))
if __name__=="__main__": place(sys.argv[1],sys.argv[2])
