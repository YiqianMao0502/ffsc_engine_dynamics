import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "props" / "transport_v2c2_tm86885.json"


def eval_property(T: float, segments):
    """
    对应论文(2.6)/(2.7)：ln(x) = A ln T + B + C/T + D/T^2
    segments: JSON 里给定某物种某性质的分段系数字典列表
    """
    seg = None
    for s in segments:
        if s["T_min"] <= T <= s["T_max"]:
            seg = s
            break
    if seg is None:
        raise ValueError(f"T={T} K not in any segment range")

    A = seg["A"]
    B = seg["B"]
    C = seg["C"]
    D = seg["D"]
    ln_x = A * math.log(T) + B + C / T + D / (T * T)
    return math.exp(ln_x)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    params = data["params"]
    table = params["species"]

    # 随便挑一个温度点做检查（完全是 Route-B 自检，不对应论文具体工况）
    T_test = 900.0  # K

    # 这里以 H2、O2、H2O 为例演示；其他物种你可以按需再查
    for specie in ["H2", "O2", "H2O"]:
        entry = table[specie]
        mu = eval_property(T_test, entry["mu"])
        lam = eval_property(T_test, entry["k"])
        print(f"{specie} @ T={T_test:.1f} K -> mu = {mu:.5e} Pa·s (相对单位), "
              f"lambda = {lam:.5e} W/m/K (相对单位)")


if __name__ == "__main__":
    main()
