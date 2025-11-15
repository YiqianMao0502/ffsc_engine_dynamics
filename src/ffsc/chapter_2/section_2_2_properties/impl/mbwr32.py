"""
mBWR-32 压力公式实现（仅依据式(2.1)与表8的alpha(T)结构）。
输入单位严格来自参数JSON：T[K], rho[指定单位，常见 mol/L], p 输出与alpha/R一致（常见 bar）。
"""
from math import exp
from typing import Dict, Any
from .registry import register, EOS
from ..utils.units import assert_unit

@register("mbwr32")
def _factory(params: Dict[str, Any]) -> EOS:
    # 断言必要字段存在（不引入任何默认）
    required = ["R", "R_unit", "rho_crit", "rho_crit_unit", "b", "b_unit", "p_unit", "rho_unit", "T_unit"]
    for k in required:
        if k not in params:
            raise KeyError(f"Missing '{k}' in mbwr32 params")
    # 单位：仅断言与JSON自描述一致；是否需要换算，等你确认后再写
    assert_unit(params["T_unit"], "K", "temperature")
    # 常见文献用 rho: mol/L, p: bar；如不同，JSON中需明示
    # 组装
    R = float(params["R"])              # e.g., 0.083145 L·bar·mol^-1·K^-1
    b = params["b"]                     # dict: {"b1":..., ..., "b32":...}
    rho_crit = float(params["rho_crit"])
    units = {k: params[k] for k in ["R_unit","rho_crit_unit","b_unit","p_unit","rho_unit","T_unit"]}

    class MBWR32(EOS):
        def evaluate(self, T: float, rho: float):
            a = self._alpha(T)
            # 式(2.1): p = sum_{n=1..9} a_n * rho^n + exp((rho/rho_crit)^2) * sum_{n=10..15} a_n * rho^{2n-17}
            s1 = 0.0
            for n in range(1, 10):
                s1 += a[n] * (rho**n)
            s2 = 0.0
            for n in range(10, 16):
                s2 += a[n] * (rho**(2*n - 17))
            p = s1 + exp((rho / rho_crit)**2) * s2
            return {
                "p": p,
                "p_unit": units["p_unit"],
                "inputs_unit": {"T": units["T_unit"], "rho": units["rho_unit"]},
                "note": "Only pressure implemented per Eq.(2.1). Other properties TODO."
            }

        def _alpha(self, T: float):
            # 表8：alpha_1..alpha_15
            # 注意：严格使用 b1..b32 与 T 的多项式/倒数/幂次关系；不做任何数值推测。
            a = {}
            # a1 = R*T
            a[1] = R * T
            # a2 = b1*T + b2*T^(1/2) + b3 + b4/T + b5/T^2
            a[2] = (b["b1"]*T + b["b2"]*(T**0.5) + b["b3"] + b["b4"]/T + b["b5"]/(T**2))
            # a3 = b6*T + b7 + b8/T + b9/T^2
            a[3] = (b["b6"]*T + b["b7"] + b["b8"]/T + b["b9"]/(T**2))
            # a4 = b10*T + b11 + b12/T
            a[4] = (b["b10"]*T + b["b11"] + b["b12"]/T)
            # a5 = b13
            a[5] = b["b13"]
            # a6 = b14/T + b15/T^2
            a[6] = (b["b14"]/T + b["b15"]/(T**2))
            # a7 = b16/T
            a[7] = (b["b16"]/T)
            # a8 = b17/T + b18/T^2
            a[8] = (b["b17"]/T + b["b18"]/(T**2))
            # a9 = b19/T^2
            a[9] = (b["b19"]/(T**2))
            # a10 = b20/T^2 + b21/T^3
            a[10] = (b["b20"]/(T**2) + b["b21"]/(T**3))
            # a11 = b22/T^2 + b23/T^4
            a[11] = (b["b22"]/(T**2) + b["b23"]/(T**4))
            # a12 = b24/T^2 + b25/T^3
            a[12] = (b["b24"]/(T**2) + b["b25"]/(T**3))
            # a13 = b26/T^2 + b27/T^4
            a[13] = (b["b26"]/(T**2) + b["b27"]/(T**4))
            # a14 = b28/T^2 + b29/T^3
            a[14] = (b["b28"]/(T**2) + b["b29"]/(T**3))
            # a15 = b30/T^2 + b31/T^3 + b32/T^4
            a[15] = (b["b30"]/(T**2) + b["b31"]/(T**3) + b["b32"]/(T**4))
            return a

    return MBWR32()
