from dataclasses import dataclass
import math
from .registry import register

@dataclass
@register("tp_valve")
class TwoPhaseValve:
    """
    §2.5.2 两相阀门/孔板（准静态；按你提供的“表20更正版”）
    (2.93) ṁ = 1/√k · A Ψ √(2 p_up ρ_up / k_dp)
    (2.94) ḣ = h_up · ṁ

    Ψ 取法（统一版）：
    - 过冷液体 & 两相流（考虑壅塞）：Ψ = sqrt( ((1-η_sat) + [ω η_sat ln(η_sat/η) − (ω−1)(η_sat−η)]) / (ω(η_sat/η − 1) + 1) )
      其中 η_sat = p_sat / p_up，ω 为压缩性因子
    - 过热蒸气（考虑壅塞，分段）：
        若 η > η_cr：Ψ = sqrt( 2/(1−γ_s) ) · sqrt( η^{2γ_s} − η^{1+γ_s} )
        若 η ≤ η_cr：Ψ = sqrt( 2γ_s/(1+γ_s) ) · ( 2γ_s/(1+γ_s) )^{ γ_s/(1−γ_s) }
      其中 γ_s = (p/ρ)(∂ρ/∂p)_s，η_cr = (2γ_s/(1+γ_s))^{1/(1−γ_s)}
    - 不考虑壅塞（过冷液体/两相流/过热蒸气通用）：Ψ = sqrt(1 − η)，η = p_dn/p_up
    """
    A: float
    k: float
    k_dp: float

    def mass_flow(self, p_up: float, rho_up: float, psi: float) -> float:
        if self.A <= 0 or self.k <= 0 or self.k_dp <= 0 or rho_up <= 0 or p_up < 0:
            raise ValueError("invalid inputs for (2.93)")
        return (self.A * psi / math.sqrt(self.k)) * math.sqrt((2.0 * p_up * rho_up) / self.k_dp)

    @staticmethod
    def enthalpy_flow(m_dot: float, h_up: float) -> float:
        return m_dot * h_up

    # —— Ψ：不考虑壅塞（通用）——
    @staticmethod
    def psi_no_choking(eta: float) -> float:
        if not (0.0 <= eta <= 1.0):
            raise ValueError("eta must be in [0,1]")
        return math.sqrt(max(0.0, 1.0 - eta))

    # —— Ψ：考虑壅塞 ——（过冷液体 & 两相流共用）
    @staticmethod
    def psi_liquid_or_twophase_with_choking(eta_sat: float, eta: float, omega: float) -> float:
        if eta <= 0 or eta_sat <= 0:
            raise ValueError("eta, eta_sat must be >0")
        num = (1.0 - eta_sat) + (omega * eta_sat * math.log(eta_sat / eta) - (omega - 1.0) * (eta_sat - eta))
        den = omega * (eta_sat / eta - 1.0) + 1.0
        if den <= 0:
            raise ValueError("den<=0 in psi_liquid_or_twophase_with_choking")
        return math.sqrt(max(0.0, num / den))

    # —— Ψ：考虑壅塞 ——（过热蒸气）
    @staticmethod
    def psi_superheated_with_choking(eta: float, gamma_s: float) -> float:
        if gamma_s <= 0 or gamma_s == 1.0:
            raise ValueError("gamma_s must be >0 and !=1")
        eta_cr = (2.0 * gamma_s / (1.0 + gamma_s)) ** (1.0 / (1.0 - gamma_s))
        if eta > eta_cr:
            return math.sqrt(2.0 / (1.0 - gamma_s)) * math.sqrt(max(0.0, eta ** (2.0 * gamma_s) - eta ** (1.0 + gamma_s)))
        return math.sqrt(2.0 * gamma_s / (1.0 + gamma_s)) * ((2.0 * gamma_s) / (1.0 + gamma_s)) ** (gamma_s / (1.0 - gamma_s))
