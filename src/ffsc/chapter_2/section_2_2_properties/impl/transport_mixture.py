"""
2.2.2 输运方程 —— 混合气体模型
输入:
  - 各组分摩尔质量 M_i
  - ln(mu_i), ln(lambda_i) 的多项式系数 a,b,c,d
  - 混合物摩尔分数 X_i
输出:
  - mu_mix(T, X) [Pa·s]
  - lambda_mix(T, X) [W/(m·K)]
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from .registry import register
from .transport_poly import eval_viscosity, eval_thermal_conductivity
from .transport_mixers import wilke_viscosity, mason_saxena_lambda

@dataclass
class TransportPolyMixture:
    names: List[str]
    mu_coeffs: List[Dict[str, float]]
    lam_coeffs: List[Dict[str, float]]
    molar_masses: List[float]  # kg/mol

    @staticmethod
    def from_params(params: Dict[str, Any]) -> "TransportPolyMixture":
        names: List[str] = []
        mu_coeffs: List[Dict[str, float]] = []
        lam_coeffs: List[Dict[str, float]] = []
        molar_masses: List[float] = []
        for sp in params["species"]:
            names.append(sp["name"])
            mu_coeffs.append(sp["mu"])       # {"a","b","c","d"}
            lam_coeffs.append(sp["lambda"])  # {"a","b","c","d"}
            molar_masses.append(float(sp["M"]))
        return TransportPolyMixture(names, mu_coeffs, lam_coeffs, molar_masses)

    def _normalize_X(self, X: Dict[str, float]) -> List[float]:
        Xi_raw = [float(X.get(name, 0.0)) for name in self.names]
        s = sum(Xi_raw)
        if s <= 0.0:
            raise ValueError("Mixture mole fractions all zero; provide nonzero X.")
        return [x / s for x in Xi_raw]

    def evaluate(self, T: float, X: Dict[str, float]) -> Dict[str, float]:
        """
        返回混合物黏度与导热系数:
        {"mu": mu_mix [Pa·s], "lambda": lambda_mix [W/m/K]}
        """
        Xi = self._normalize_X(X)
        mu_i = [eval_viscosity(T, c) for c in self.mu_coeffs]
        lam_i = [eval_thermal_conductivity(T, c) for c in self.lam_coeffs]
        mu_mix = wilke_viscosity(Xi, mu_i, self.molar_masses)
        lam_mix = mason_saxena_lambda(Xi, lam_i, self.molar_masses)
        return {"mu": mu_mix, "lambda": lam_mix}

@register("transport_poly_mixture")
def build_transport_poly_mixture(params: Dict[str, Any]) -> TransportPolyMixture:
    return TransportPolyMixture.from_params(params)
