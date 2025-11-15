from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json

def main():
    # 这里的 loader 其实是通用工厂，能构造 transport_poly_mixture
    mix = load_eos_from_json("data/props/transport_demo.json")
    T = 900.0  # K
    X = {"CH4": 0.5, "O2": 0.5}  # 摩尔分数
    out = mix.evaluate(T=T, X=X)
    print(f"[Transport Demo] T={T} K, X={X} -> mu={out['mu']} Pa·s, lambda={out['lambda']} W/m/K")

if __name__ == "__main__":
    main()
