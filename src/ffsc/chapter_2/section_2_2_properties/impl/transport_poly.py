"""
2.2.2 输运方程：单组分形式
ln(mu) = a_mu * ln T + b_mu / T + c_mu / T^2 + d_mu
ln(lambda) = a_l  * ln T + b_l  / T + c_l  / T^2 + d_l
这里不关心系数来源，只负责在给定 T 时计算 mu, lambda。
"""

import math
from typing import Mapping

def eval_viscosity(T: float, coeffs: Mapping[str, float]) -> float:
    """
    根据 ln(mu) 多项式（式(2.6)）计算单组分黏度 mu(T) [Pa·s]。
    coeffs: {"a":..., "b":..., "c":..., "d":...}
    """
    a = float(coeffs["a"])
    b = float(coeffs["b"])
    c = float(coeffs["c"])
    d = float(coeffs["d"])
    ln_mu = a * math.log(T) + b / T + c / (T * T) + d
    return math.exp(ln_mu)

def eval_thermal_conductivity(T: float, coeffs: Mapping[str, float]) -> float:
    """
    根据 ln(lambda) 多项式（式(2.7)）计算单组分导热系数 lambda(T) [W/(m·K)]。
    coeffs: {"a":..., "b":..., "c":..., "d":...}
    """
    a = float(coeffs["a"])
    b = float(coeffs["b"])
    c = float(coeffs["c"])
    d = float(coeffs["d"])
    ln_lam = a * math.log(T) + b / T + c / (T * T) + d
    return math.exp(ln_lam)
