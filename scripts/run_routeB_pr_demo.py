from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json

def main():
    eos = load_eos_from_json("data/props/mix_pr_demo.json")
    # 示例工况：T=900 K，v=1.0e-3 m^3/mol（体积越小压强越高）
    res = eos.evaluate(T=900.0, v=1.0e-3)
    print("[Route B] PR mixture at T=900 K, v=1.0e-3 m^3/mol ->", res)

if __name__ == "__main__":
    main()
