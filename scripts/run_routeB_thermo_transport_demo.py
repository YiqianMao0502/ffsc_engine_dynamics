import json
from pathlib import Path
from ffsc.chapter_2.section_2_2_properties.impl.nasa7 import NASA7Species, NASA7Piece, mix_ideal
from ffsc.chapter_2.section_2_2_properties.impl.transport_poly import mix_transport
from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json

def load_nasa7_species(json_path: str):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    sp_list = []
    for sp in data["species"]:
        low = NASA7Piece(**{k: sp["low"][k] for k in ("a1","a2","a3","a4","a5","a6","a7","Tmin","Tmax")})
        high= NASA7Piece(**{k: sp["high"][k] for k in ("a1","a2","a3","a4","a5","a6","a7","Tmin","Tmax")})
        sp_list.append(NASA7Species(name=sp["name"], low=low, high=high, Tmid=sp["Tmid"], M=sp["M"], source=sp.get("citation","")))
    return sp_list

def load_transport_species(json_path: str):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    mu_list, lam_list, names = [], [], []
    for sp in data["species"]:
        names.append(sp["name"])
        mu_list.append(sp["mu"])
        lam_list.append(sp["lambda"])
    return names, mu_list, lam_list

def main():
    # 1) EOS pressure (already working via PR/SRK)
    eos = load_eos_from_json("data/props/mix_pr_demo.json")  # you can switch to SRK file
    resP = eos.evaluate(T=900.0, v=1.0e-3)
    print("[EOS] P:", resP["P"], resP["P_unit"])

    # 2) Ideal-gas thermo via NASA7 (needs you to fill coefficients in the JSON you choose)
    # Example expects a file like data/props/thermo/nasa7_set_demo.json with species and coefficients filled
    nasa_file = "data/props/thermo/nasa7_set_demo.json"
    if Path(nasa_file).exists():
        sp_list = load_nasa7_species(nasa_file)
        Xi = [1.0/len(sp_list)]*len(sp_list)  # demo equal fractions; replace with your mixture Xi
        resT = mix_ideal({}, T=900.0, Xi=Xi, species=sp_list)
        print("[NASA7] cp (J/mol/K):", resT["cp_molar"], "h (J/mol):", resT["h_molar"], "s (J/mol/K):", resT["s_molar"])
    else:
        print(f"[NASA7] {nasa_file} not found. Fill coefficients per schema and re-run.")

    # 3) Transport fits per Eq.(2.6),(2.7)
    tr_file = "data/props/transport/transport_set_demo.json"
    if Path(tr_file).exists():
        names, mu_list, lam_list = load_transport_species(tr_file)
        Xi = [1.0/len(names)]*len(names)
        resMuLam = mix_transport(T=900.0, Xi=Xi, mu_list=mu_list, lam_list=lam_list)
        print("[Transport] mu (Pa*s):", resMuLam["mu"], "lambda (W/m/K):", resMuLam["lambda"])
    else:
        print(f"[Transport] {tr_file} not found. Fill coefficients per schema and re-run.")

if __name__ == "__main__":
    main()
