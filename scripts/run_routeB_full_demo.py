import json
from pathlib import Path
from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json
from ffsc.chapter_2.section_2_2_properties.impl.nasa7 import NASA7Piece, NASA7Species, mix_ideal
from ffsc.chapter_2.section_2_2_properties.impl.transport_poly import mix_transport
from ffsc.chapter_2.section_2_2_properties.impl.transport_mixers import wilke_viscosity, mason_saxena_lambda

def load_nasa7_species(json_path: str):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    spp = []
    for sp in data["species"]:
        low  = NASA7Piece(**{k: sp["low"][k]  for k in ("a1","a2","a3","a4","a5","a6","a7","Tmin","Tmax")})
        high = NASA7Piece(**{k: sp["high"][k] for k in ("a1","a2","a3","a4","a5","a6","a7","Tmin","Tmax")})
        spp.append(NASA7Species(name=sp["name"], low=low, high=high, Tmid=sp["Tmid"], M=sp["M"], source=sp.get("citation","")))
    return spp

def load_transport_set(json_path: str):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    names, mu_coeffs, lam_coeffs = [], [], []
    for sp in data["species"]:
        names.append(sp["name"])
        mu_coeffs.append(sp["mu"])
        lam_coeffs.append(sp["lambda"])
    return names, mu_coeffs, lam_coeffs

def main():
    T = 900.0
    v = 1.0e-3
    Xi = None  # 传入混合物组成（摩尔分数）

    # 1) EOS 压力（PR 或 SRK）
    eos = load_eos_from_json("data/props/mix_pr_demo.json")
    resP = eos.evaluate(T=T, v=v)
    print("[EOS] P =", resP["P"], resP["P_unit"])

    # 假设 mix_pr_demo.json 里 species 顺序与 NASA/Transport 的 species 顺序一致，
    # 并且 Xi 与 species 对齐。这里用等分作为示例，实际应替换为你的工况 Xi。
    nsp = len(json.loads(Path("data/props/mix_pr_demo.json").read_text())["params"]["species"])
    Xi = [1.0/nsp]*nsp

    # 2) NASA7 理想气 cp/h/s
    nasa_path = "data/props/thermo/sets/nasa7_full_set_placeholder.json"
    spp = load_nasa7_species(nasa_path)
    names_nasa = [s.name for s in spp][:nsp]
    spp = spp[:nsp]
    resTh = mix_ideal({}, T=T, Xi=Xi, species=spp)
    print("[NASA7] cp_molar(J/mol/K)=", resTh["cp_molar"], "h_molar(J/mol)=", resTh["h_molar"], "s_molar(J/mol/K)=", resTh["s_molar"])

    # 3) 输运：先用单物种对数多项式得到 mu_i, lambda_i，再用 Wilke/MS 混合
    import math
    from ffsc.chapter_2.section_2_2_properties.impl.transport_poly import eval_viscosity, eval_thermal_conductivity
    tr_path = "data/props/transport/transport_poly_full_set_placeholder.json"
    tr = json.loads(Path(tr_path).read_text(encoding="utf-8"))["species"][:nsp]
    mu_i = [eval_viscosity(T, sp["mu"]) for sp in tr]
    la_i = [eval_thermal_conductivity(T, sp["lambda"]) for sp in tr]
    M_i  = [s.M for s in spp]
    mu_mix = wilke_viscosity(T, Xi, mu_i, M_i)
    la_mix = mason_saxena_lambda(T, Xi, la_i, M_i)
    print("[TRANSPORT] mu_mix(Pa*s)=", mu_mix, "lambda_mix(W/m/K)=", la_mix)

if __name__ == "__main__":
    main()
