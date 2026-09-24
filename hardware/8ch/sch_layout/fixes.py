# Netlist fixes applied to the HEAD schematic before the layout pass.
import json,sys
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from kon import K
from geom import load,body
FIX={"K1":{"1":"RELAY_COM","4":"RELAY_NC","5":"RELAY_LOW"}}   # I-058
def apply(S):
    k=K(); k.load("sch_wiring","sch_analysis")
    root,libs,syms=load(S); SY={s['ref']:s for s in syms}
    labels=json.loads(k.call("list_schematic_labels",schematic=S))["labels"]
    for ref,pins in FIX.items():
        bb,tips=body(SY[ref],libs)
        for num,net in pins.items():
            x,y=tips[num]
            old=[l for l in labels if round(l['x'],2)==x and round(l['y'],2)==y]
            assert len(old)==1,(ref,num,old)
            r=k.call("delete_schematic_net_label",schematic=S,net=old[0]['net'],x=x,y=y); assert 'rror' not in r[:60],r
            r=k.call("add_schematic_net_label",schematic=S,net=net,x=x,y=y,rotation=old[0]['rotation']); assert 'rror' not in r[:60],r
    # I-057: the IA series moved to Converter_DCDC_Isolated in KiCad 10; same pins.
    # Konnect resolves the library through KICAD10_SYMBOL_DIR.
    k2=K(); k2.load("sch_components")
    r=k2.call("replace_component",schematic=S,reference="U12",new_lib_id="Converter_DCDC_Isolated:IA0505S"); assert '"units_replaced":1' in r,r
if __name__=="__main__": apply(sys.argv[1])
