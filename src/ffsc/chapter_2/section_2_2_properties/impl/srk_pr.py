from typing import Dict, Any, List
from .registry import register
import math

@register("pr_mixture")
def _factory_pr(params: Dict[str, Any]):
    # 读取物种与性质
    species = params["species"]  # list of {name,Tc,Pc,omega}
    names = [s["name"] for s in species]

    # 兼容 Xi 或 mole_fractions
    if "Xi" in params:
        Xi = params["Xi"]
        if len(Xi) != len(species):
            raise ValueError("len(Xi) must equal len(species)")
    elif "mole_fractions" in params:
        mf = params["mole_fractions"]  # dict name->x
        Xi = [float(mf.get(n, 0.0)) for n in names]
        s = sum(Xi)
        if s <= 0: raise ValueError("mole_fractions all zero")
        Xi = [x/s for x in Xi]
    else:
        raise KeyError("Provide either 'Xi' (list) or 'mole_fractions' (dict)")

    # --- 下面是你原有 PR 实现（占位：a(T), b(T)等），仅示意 ---
    # 临界与偏心
    Tc = [s["Tc"] for s in species]
    Pc = [s["Pc"] for s in species]
    omega = [s["omega"] for s in species]

    # Peng–Robinson 核心：kappa(ω)、a_c、b 等（示意；保持你文件里的实现）
    def kappa(w): return 0.37464 + 1.54226*w - 0.26992*w*w
    R = 8.314462618

    def build_evaluator():
        def evaluate(T: float, v: float) -> Dict[str, Any]:
            # 计算 a_i(T), b_i；本函数应与你原文件一致
            a_i = []
            b_i = []
            for i in range(len(species)):
                Tr = T / Tc[i]
                kap = kappa(omega[i])
                alpha = (1 + kap*(1 - math.sqrt(Tr)))**2
                a_c = 0.457235583 * (R*Tc[i])**2 / Pc[i]
                b_c = 0.07779607  * (R*Tc[i])      / Pc[i]
                a_i.append(a_c * alpha)
                b_i.append(b_c)

            # 简单混合法：a_mix (二次混合), b_mix (线性)
            a_mix = 0.0
            for i in range(len(species)):
                for j in range(len(species)):
                    a_mix += Xi[i]*Xi[j]*math.sqrt(a_i[i]*a_i[j])
            b_mix = sum(Xi[i]*b_i[i] for i in range(len(species)))

            # PR 状态方程：P = RT/(v-b) - a / (v^2 + 2 b v - b^2)
            P = R*T/(v - b_mix) - a_mix/(v*v + 2*b_mix*v - b_mix*b_mix)
            return {"P": P, "P_unit": "Pa", "a_mix": a_mix, "b_mix": b_mix}
        return evaluate

    return type("PRMixture", (), {"evaluate": staticmethod(build_evaluator())})
