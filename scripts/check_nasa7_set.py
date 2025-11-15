import json, sys
from pathlib import Path
from ffsc.chapter_2.section_2_2_properties.impl.nasa7 import NASA7Piece, NASA7Species, mix_ideal

def missing_fields(sp):
    miss = []
    for fld in ("M","Tmid","low","high"):
        if fld not in sp or sp[fld] is None: miss.append(fld)
    for side in ("low","high"):
        for k in ("Tmin","Tmax","a1","a2","a3","a4","a5","a6","a7"):
            if k not in sp.get(side,{}) or sp[side][k] is None: miss.append(f"{side}.{k}")
    return miss

def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    species = data["species"]
    ok, todo = 0, 0
    for sp in species:
        miss = missing_fields(sp)
        if miss: 
            todo += 1
            print(f"[MISSING] {sp['name']}: {', '.join(miss[:8])}{' ...' if len(miss)>8 else ''}")
        else:
            ok += 1
    print(f"[SUMMARY] completed={ok}, missing={todo}, total={len(species)}")
if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "data/props/thermo/sets/nasa7_full_set_placeholder.json")
