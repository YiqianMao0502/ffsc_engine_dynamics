from dataclasses import dataclass
import math
from .registry import register

@dataclass
@register("mix_pipe")
class MixGasPipe:
    """
    §2.5.3 混合气体管路（R + 可选对流换热）
    式(2.95) ṁ = A C_q C_m p_up / √T_up
    式(2.96) ḣ = ṁ h(p_up,T_up)  (若无 h(p,T)，需上游 h_up；否则抛异常)
    式(2.97) C_q(η) 多项式；(2.98) 临界压比；(2.100) C_m 分段
    换热：Re(2.101), Nu(2.102), h_c(2.103)；过渡区线性平滑（避免引入外部假设）
    """
    A: float
    L_c: float | None = None
    A_hx: float | None = None

    @staticmethod
    def m_dot_resistive(p_up: float, T_up: float, C_q: float, C_m: float) -> float:
        if T_up <= 0:
            raise ValueError("T_up must be >0")
        return C_q * C_m * p_up / math.sqrt(T_up)

    @staticmethod
    def h_dot_from_mdot(m_dot: float, h_up: float | None, h_of_pT=None, p_up: float | None=None, T_up: float | None=None) -> float:
        if h_of_pT is not None:
            if p_up is None or T_up is None:
                raise ValueError("p_up, T_up required for h(p,T)")
            return m_dot * h_of_pT(p_up, T_up)
        if h_up is None:
            raise NotImplementedError("h(p,T) unavailable; provide h_up.")
        return m_dot * h_up

    @staticmethod
    def C_q_polynomial(eta: float) -> float:
        return ((((-1.6827 * eta + 4.6) * eta - 3.9) * eta + 0.8415) * eta - 0.1) * eta + 0.8414

    @staticmethod
    def eta_critical(gamma_s: float) -> float:
        """(2.98) η_cr = (p_dn/p_up)_cr = (2γ_s/(γ_s+1))^{1/(1−γ_s)}; 这里返回 η_cr。"""
        if gamma_s <= 0 or gamma_s == 1.0:
            raise ValueError("gamma_s must be >0 and !=1")
        return (2.0 * gamma_s / (gamma_s + 1.0)) ** (1.0 / (1.0 - gamma_s))

    @staticmethod
    def C_m_piecewise(eta: float, gamma_s: float, rho_up: float, T_up: float, p_up: float) -> float:
        if p_up <= 0 or T_up <= 0 or rho_up <= 0:
            raise ValueError("invalid upstream inputs")
        eta_cr = MixGasPipe.eta_critical(gamma_s)
        if eta > eta_cr:
            return math.sqrt(2.0/(1.0-gamma_s) * (rho_up*T_up/p_up) * (eta**(2.0*gamma_s) - eta**(1.0+gamma_s)))
        return math.sqrt(2.0/(1.0+gamma_s) * (rho_up*T_up/p_up)) * (2.0*gamma_s/(gamma_s+1.0))**(gamma_s/(1.0-gamma_s))

    @staticmethod
    def reynolds(m_dot_up: float, L_c: float, mu: float, A: float) -> float:
        """(2.101) Re = (m_dot_up · L_c) / (μ · A). 变量名与原文一致。"""
        if mu <= 0 or A <= 0 or L_c <= 0:
            raise ValueError("mu, A, L_c must be >0")
        return (m_dot_up * L_c) / (mu * A)

    @staticmethod
    def nusselt(Re: float, Pr: float, mu: float, mu_s: float, l_e_over_dh: float, Re1: float=2300.0, Re2: float=10000.0) -> float:
        if Re < Re1:
            return 1.86 * ((Re * Pr) / (l_e_over_dh)) ** (1.0/3.0) * (mu / mu_s) ** 0.14
        if Re > Re2:
            return 0.027 * (Re ** 0.8) * (Pr ** (1.0/3.0)) * (mu / mu_s) ** 0.14
        w = (Re - Re1) / (Re2 - Re1)
        nu_lam = 1.86 * ((Re1 * Pr) / (l_e_over_dh)) ** (1.0/3.0) * (mu / mu_s) ** 0.14
        nu_tur = 0.027 * (Re2 ** 0.8) * (Pr ** (1.0/3.0)) * (mu / mu_s) ** 0.14
        return (1.0 - w) * nu_lam + w * nu_tur

    @staticmethod
    def h_conv(Nu: float, lam: float, L_c: float) -> float:
        if L_c <= 0:
            raise ValueError("L_c must be >0")
        return Nu * lam / L_c
