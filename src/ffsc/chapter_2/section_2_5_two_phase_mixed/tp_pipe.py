from dataclasses import dataclass
import math
from .registry import register

@dataclass
@register("tp_pipe")
class TwoPhasePipe:
    """
    §2.5.1 两相流管路（R 型质量/焓流 + 摩擦/加速压降辅助）
    式(2.82) dm = ρ A /√k · √(2 dp k_dp / ρ)
    式(2.83) dh = dm · h_up
    Churchill 摩擦因子；两相平均粘度 1/μ̄ = x*/μ_v + (1-x*)/μ_l
    """
    A: float     # [m^2]
    k: float
    k_dp: float
    D: float | None = None
    epsilon: float | None = None

    def mass_flow_from_dp(self, rho_up: float, dp: float) -> float:
        if rho_up <= 0 or self.A <= 0 or self.k <= 0 or self.k_dp <= 0:
            raise ValueError("invalid inputs for (2.82)")
        return (rho_up * self.A / math.sqrt(self.k)) * math.sqrt((2.0 * abs(dp) * self.k_dp) / rho_up)

    @staticmethod
    def enthalpy_flow(dm: float, h_up: float) -> float:
        return dm * h_up

    @staticmethod
    def friction_factor_churchill(Re: float, epsilon_over_D: float) -> float:
        if Re <= 0:
            return float("inf")
        term1 = (8.0 / Re) ** 12
        inner = 1.0 / (((7.0 / Re) ** 0.9) + 0.27 * epsilon_over_D)
        term2 = (2.457 * math.log(inner)) ** 16
        term3 = (37530.0 / Re) ** 16
        denom = (term2 + term3) ** (3.0 / 2.0)
        return 8.0 * (term1 + 1.0 / denom) ** (1.0 / 12.0)

    @staticmethod
    def averaged_viscosity(mu_l: float, mu_v: float, x_mass: float) -> float:
        if mu_l <= 0 or mu_v <= 0:
            raise ValueError("mu_l, mu_v must be >0")
        x_mass = max(0.0, min(1.0, x_mass))
        inv_mu = x_mass / mu_v + (1.0 - x_mass) / mu_l
        return 1.0 / inv_mu
