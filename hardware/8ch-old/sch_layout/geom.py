import re,math,json
def parse(s):
    tok=re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+',s)
    st=[[]]
    for t in tok:
        if t=='(': st.append([])
        elif t==')': x=st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1] if t.startswith('"') else t)
    return st[0][0]
def kids(n,name): return [c for c in n if isinstance(c,list) and c and c[0]==name]
def kid(n,name):
    k=kids(n,name); return k[0] if k else None
def load(path):
    root=parse(open(path).read())
    libs={}
    for s in kids(kid(root,'lib_symbols'),'symbol'):
        name=s[1]; units={}
        for u in kids(s,'symbol'):
            m=re.search(r'_(\d+)_(\d+)$',u[1]); unit=int(m.group(1))
            pts=[];pins=[]
            for g in u[1:]:
                if not isinstance(g,list): continue
                if g[0]=='rectangle':
                    a=kid(g,'start');b=kid(g,'end'); pts+= [(float(a[1]),float(a[2])),(float(b[1]),float(b[2]))]
                elif g[0]=='polyline':
                    for xy in kids(kid(g,'pts'),'xy'): pts.append((float(xy[1]),float(xy[2])))
                elif g[0]=='circle':
                    c=kid(g,'center');r=float(kid(g,'radius')[1]); cx,cy=float(c[1]),float(c[2]); pts+=[(cx-r,cy-r),(cx+r,cy+r)]
                elif g[0]=='arc':
                    for k in ('start','mid','end'):
                        p=kid(g,k); pts.append((float(p[1]),float(p[2])))
                elif g[0]=='pin':
                    at=kid(g,'at'); ln=float(kid(g,'length')[1]); num=kid(g,'number')[1]
                    pins.append((num,float(at[1]),float(at[2]),float(at[3]) if len(at)>3 else 0,ln))
            units.setdefault(unit,{'pts':[],'pins':[]})
            units[unit]['pts']+=pts; units[unit]['pins']+=pins
        libs[name]=units
    syms=[]
    for s in kids(root,'symbol'):
        lib=kid(s,'lib_id')[1]; at=kid(s,'at'); x,y=float(at[1]),float(at[2]); rot=float(at[3]) if len(at)>3 else 0
        mir=kid(s,'mirror'); mir=mir[1] if mir else None
        unit=int(kid(s,'unit')[1]) if kid(s,'unit') else 1
        ref=[p[2] for p in kids(s,'property') if p[1]=='Reference'][0]
        syms.append(dict(ref=ref,lib=lib,x=x,y=y,rot=rot,mir=mir,unit=unit))
    return root,libs,syms
def xf(sym,px,py):
    py=-py
    if sym['mir']=='x': py=-py
    if sym['mir']=='y': px=-px
    a=math.radians(-sym['rot'])  # KiCad rotation is CCW on screen
    c,s=round(math.cos(a)),round(math.sin(a))
    return (round(sym['x']+px*c-py*s,2), round(sym['y']+px*s+py*c,2))
def body(sym,libs):
    u=libs[sym['lib']]
    pts=u.get(0,{'pts':[]})['pts']+u.get(sym['unit'],{'pts':[]})['pts']
    pins=u.get(0,{'pins':[]})['pins']+u.get(sym['unit'],{'pins':[]})['pins']
    # include pin roots (body side of each pin) so pin lines count as body
    allp=list(pts)
    for num,px,py,pr,ln in pins:
        a=math.radians(pr); allp.append((px+ln*round(math.cos(a)),py+ln*round(math.sin(a))))
    T=[xf(sym,px,py) for px,py in allp]
    tips={num:xf(sym,px,py) for num,px,py,pr,ln in pins}
    roots={}
    for num,px,py,pr,ln in pins:
        a=math.radians(pr); roots[num]=xf(sym,px+ln*round(math.cos(a)),py+ln*round(math.sin(a)))
    sym['roots']=roots
    if not T: return None,tips
    xs=[p[0] for p in T]; ys=[p[1] for p in T]
    return (min(xs),min(ys),max(xs),max(ys)),tips
