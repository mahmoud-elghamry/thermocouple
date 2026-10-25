import json,sys,math
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from kon import K
from geom import load,body,kids,kid
def pin_dir(sym,libs,num):
    bb,t=body(sym,libs); r=sym['roots'][num]; x=t[num]
    dx,dy=x[0]-r[0],x[1]-r[1]
    if abs(dx)>abs(dy): return 0 if dx>0 else 180
    return 270 if dy>0 else 90
def apply(SCH,spec,k=None):
    """spec: {ref:(x,y,rot)}"""
    k=k or K(); k.load("sch_components","sch_wiring","sch_analysis")
    root,libs,syms=load(SCH); S={s['ref']:s for s in syms}
    labels=json.loads(k.call("list_schematic_labels",schematic=SCH))["labels"]
    nc={(round(float(kid(n,'at')[1]),2),round(float(kid(n,'at')[2]),2)) for n in kids(root,'no_connect')}
    old={}
    for ref in spec:
        s=S[ref]; bb,tips=body(s,libs)
        old[ref]={num:([l for l in labels if round(l['x'],2)==xy[0] and round(l['y'],2)==xy[1]], xy in nc, xy) for num,xy in tips.items()}
    # remove labels / NC on the pins being moved
    for ref,pins in old.items():
        for num,(ls,isnc,xy) in pins.items():
            for l in ls:
                r=k.call("delete_schematic_net_label",schematic=SCH,net=l['net'],x=l['x'],y=l['y'])
                assert 'rror' not in r[:60],r
    ncs=[{"x":xy[0],"y":xy[1]} for pins in old.values() for (ls,isnc,xy) in pins.values() if isnc]
    if ncs: k.call("batch_delete_no_connect",schematic=SCH,positions=ncs)
    for ref,(x,y,rot) in spec.items():
        if S[ref]['rot']!=rot:
            r=k.call("rotate_schematic_component",schematic=SCH,reference=ref,rotation=rot); assert 'rror' not in r[:60],r
        r=k.call("move_schematic_component",schematic=SCH,reference=ref,x=x,y=y); assert 'rror' not in r[:60],r
    root,libs,syms=load(SCH); S={s['ref']:s for s in syms}
    newnc=[]
    for ref,pins in old.items():
        s=S[ref]; bb,tips=body(s,libs)
        assert (s['x'],s['y'],s['rot'])==tuple(float(v) for v in spec[ref]),(ref,s,spec[ref])
        for num,(ls,isnc,xy) in pins.items():
            nx=tips[num]
            for l in ls[:1]:
                r=k.call("add_schematic_net_label",schematic=SCH,net=l['net'],x=nx[0],y=nx[1],rotation=pin_dir(s,libs,num))
                assert 'rror' not in r[:60],r
            if isnc: newnc.append({"x":nx[0],"y":nx[1]})
    if newnc: k.call("batch_add_no_connect",schematic=SCH,positions=newnc)
    return k
