import sys
from libs import load, pins
for lid in sys.argv[1:]:
    n = load(lid, local_dir=".")
    print("==", lid)
    for k, v in sorted(pins(n).items(), key=lambda kv: (len(kv[0]), kv[0])):
        print(f"  {k:>3} {v[0]:<14} unit{v[4]} {v[5]} at({v[1]},{v[2]},{v[3]:.0f})")
