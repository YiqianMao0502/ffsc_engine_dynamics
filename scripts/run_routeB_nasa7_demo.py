from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json

def main():
    eos = load_eos_from_json("data/props/mix_nasa7_gri30.json")
    thermo = eos  # NASA7Mixture 对象
    T = 1200.0
    X = {
        "CH4": 0.08,
        "O2":  0.21,
        "H2O": 0.10,
        "CO":  0.05,
        "CO2": 0.12,
        "H2":  0.02,
        "OH":  0.01,
        "O":   0.20,
        "H":   0.21
    }
    out = {
        "cp_molar_J_mol_K": thermo.cp_mixture(T, X),
        "h_molar_J_mol":    thermo.h_mixture(T, X),
        "s_molar_J_mol_K":  thermo.s_mixture(T, X)
    }
    print(out)

if __name__ == "__main__":
    main()
