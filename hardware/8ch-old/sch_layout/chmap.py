import json,sys
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from kon import K
def channel_refs(SCH):
    k=K(); k.load("sch_export")
    d=json.loads(k.call("export_netlist_summary",schematic=SCH))
    N={c["reference"]:{p["number"]:p["net"] for p in c["pins"]} for c in d["components"]}
    def find(pred):
        r=[ref for ref,pins in N.items() if pred(ref,pins)]
        assert len(r)==1,(r); return r[0]
    out={}
    for n in range(1,9):
        P,Nn,RP,RN=f"TC{n}_FILT_P",f"TC{n}_FILT_N",f"TC{n}_RAW_P",f"TC{n}_RAW_N"
        U=find(lambda r,p: r.startswith("U") and p.get("4")==P)
        J=f"JTC{n}"
        R1=find(lambda r,p: r.startswith("R") and set(p.values())=={RP,P})
        R2=find(lambda r,p: r.startswith("R") and set(p.values())=={RN,Nn})
        C1=find(lambda r,p: r.startswith("C") and set(p.values())=={P,Nn})
        C2=find(lambda r,p: r.startswith("C") and set(p.values())=={P,"GND_SENS"})
        C3=find(lambda r,p: r.startswith("C") and set(p.values())=={Nn,"GND_SENS"})
        D7=find(lambda r,p: r.startswith("D") and p.get("3")==P)
        D8=find(lambda r,p: r.startswith("D") and p.get("3")==Nn)
        cs=N[U]["9"]; miso=N[U]["11"]
        Rpu=find(lambda r,p: r.startswith("R") and set(p.values())=={cs,"+3V3_SENS"})
        Rs=find(lambda r,p: r.startswith("R") and miso in p.values() and r!=U)
        # decoupling caps: the two +3V3/GND caps nearest this U (by current position)
        out[n]=(J,R1,R2,C1,C2,C3,None,None,D7,D8,U,Rpu,Rs)
    return out,d
