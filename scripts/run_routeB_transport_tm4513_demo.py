from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json


def main():
    # 这里的 JSON 指向你刚才创建的 TM-4513 版混合物文件
    mix = load_eos_from_json("data/props/transport_tm4513_species.json")

    # 选一个代表性的温度，比如 900 K
    T = 900.0

    props = mix.transport(T)
    # 约定：props 里返回 mu_mix, lambda_mix（具体键名按你当前 transport.py 的实现来）
    print("[TM-4513] mixture at T = %.1f K" % T)
    for k, v in props.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

