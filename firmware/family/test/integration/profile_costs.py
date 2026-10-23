"""Shared opaque-MCAL bounds for instruction accounting and live clock feedback."""
import re

def calibration_from(text):
    mcal=text
    calibration={}
    for kind, value, begin, end in re.findall(
            r"BEGIN (\d+) (\d+)\n.*?# cycles\s+(\d+)\n.*?END\n.*?# cycles\s+(\d+)",mcal,re.S):
        calibration.setdefault(int(kind),[]).append((int(value),int(end)-int(begin)))
    return calibration

def bounds(calibration):
    soft=max(c for _,c in calibration[9])
    # Conservative actual MCAL costs, including call/return and branch margin.
    # Soft SPI uses all-256-TX calibration; delay allows twice the requested time.
    costs={1:400,2:100,3:100,4:60,6:30,7:30,8:110,9:soft+16,
           10:100,11:40,12:300,13:300,14:100,15:40,16:60,17:20,18:80,
           19:100,20:10,21:20,22:100,23:150,24:150,25:80,26:20,
           27:100,28:100,29:100,30:80,31:60}
    costs[2]=max(c for _,c in calibration[2])+8
    costs[3]=max(c for _,c in calibration[3])+8
    costs[5]=max(c for value,c in calibration[5] if value==1)+8
    costs.update({32:max(c for _,c in calibration[38])+40,33:400,
                  34:max(c for _,c in calibration[37])+32,35:max(c for _,c in calibration[39])+32,36:40})
    return costs

def call_cost(costs,kind,arg):
    if kind==5: return costs[5] if arg==1 else 16*arg+40
    return costs[kind]
