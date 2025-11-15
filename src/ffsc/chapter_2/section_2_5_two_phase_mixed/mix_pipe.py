"""§2.5.3 混合气管路/阻性模型实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import GasMixtureThermo, _MOLAR_MASS

from .base import Component, GasState
from .registry import register


@dataclass
@register("mix_pipe")
class MixGasPipe(Component):
    """Route-A 混合气管路模型，对接 Route-B 物性接口。"""

    A: float
    L_c: Optional[float] = None
    A_hx: Optional[float] = None
    thermo: Optional[GasMixtureThermo] = field(default=None, repr=False)

    @staticmethod
    def m_dot_resistive(p_up: float, T_up: float, C_q: float, C_m: float) -> float:
        if T_up <= 0:
            raise ValueError("T_up must be >0")
        return C_q * C_m * p_up / math.sqrt(T_up)

    def h_dot_from_mdot(self, m_dot: float, upstream_state: GasState) -> float:
        if upstream_state.h is None:
            raise MissingPropertyData("Upstream enthalpy unknown; attach GasMixtureThermo or set state.h explicitly")
        return m_dot * upstream_state.h

    @staticmethod
    def C_q_polynomial(eta: float) -> float:
        return ((((-1.6827 * eta + 4.6) * eta - 3.9) * eta + 0.8415) * eta - 0.1) * eta + 0.8414

    @staticmethod
    def eta_critical(gamma_s: float) -> float:
        if gamma_s <= 0 or gamma_s == 1.0:
            raise ValueError("gamma_s must be >0 and !=1")
        return (2.0 * gamma_s / (gamma_s + 1.0)) ** (1.0 / (1.0 - gamma_s))

    @staticmethod
    def C_m_piecewise(eta: float, gamma_s: float, rho_up: float, T_up: float, p_up: float) -> float:
        if p_up <= 0 or T_up <= 0 or rho_up <= 0:
            raise ValueError("invalid upstream inputs")
        eta_cr = MixGasPipe.eta_critical(gamma_s)
        if eta > eta_cr:
            return math.sqrt(2.0 / (1.0 - gamma_s) * (rho_up * T_up / p_up) * (eta ** (2.0 * gamma_s) - eta ** (1.0 + gamma_s)))
        return (
            math.sqrt(2.0 / (1.0 + gamma_s) * (rho_up * T_up / p_up))
            * (2.0 * gamma_s / (gamma_s + 1.0)) ** (gamma_s / (1.0 - gamma_s))
        )

    @staticmethod
    def reynolds(m_dot_up: float, L_c: float, mu: float, A: float) -> float:
        if mu <= 0 or A <= 0 or L_c <= 0:
            raise ValueError("mu, A, L_c must be >0")
        return (m_dot_up * L_c) / (mu * A)

    @staticmethod
    def nusselt(Re: float, Pr: float, mu: float, mu_s: float, l_e_over_dh: float, Re1: float = 2300.0, Re2: float = 10000.0) -> float:
        if Re < Re1:
            return 1.86 * ((Re * Pr) / (l_e_over_dh)) ** (1.0 / 3.0) * (mu / mu_s) ** 0.14
        if Re > Re2:
            return 0.027 * (Re ** 0.8) * (Pr ** (1.0 / 3.0)) * (mu / mu_s) ** 0.14
        w = (Re - Re1) / (Re2 - Re1)
        nu_lam = 1.86 * ((Re1 * Pr) / (l_e_over_dh)) ** (1.0 / 3.0) * (mu / mu_s) ** 0.14
        nu_tur = 0.027 * (Re2 ** 0.8) * (Pr ** (1.0 / 3.0)) * (mu / mu_s) ** 0.14
        return (1.0 - w) * nu_lam + w * nu_tur

    @staticmethod
    def h_conv(Nu: float, lam: float, L_c: float) -> float:
        if L_c is None or L_c <= 0:
            raise ValueError("L_c must be >0")
        return Nu * lam / L_c

    def _ensure_thermo(self) -> GasMixtureThermo:
        if self.thermo is None:
            raise MissingPropertyData("MixGasPipe requires GasMixtureThermo to evaluate state")
        return self.thermo

    def _molar_mass_from_comp(self, composition: Dict[str, float]) -> float:
        total = sum(composition.values())
        if total <= 0.0:
            raise ValueError("Mixture composition needs non-zero fractions")
        try:
            return sum(_MOLAR_MASS[name] * frac for name, frac in composition.items()) / total
        except KeyError as exc:
            raise MissingPropertyData(f"No molar-mass entry for species '{exc.args[0]}'") from exc

    def compute_flows(self, upstream: GasState, p_down: float) -> Dict[str, float]:
        thermo = self._ensure_thermo()
        if upstream.p is None or upstream.T is None:
            raise ValueError("Upstream state must include pressure and temperature")

        composition = upstream.composition if upstream.composition else {sp.name: 1.0 for sp in thermo.pr.species}
        props = thermo.state(upstream.p, upstream.T, composition)

        upstream.rho = props["rho_mass"]
        upstream.gamma = props["gamma"]
        upstream.mu = props["mu"]
        upstream.lam = props["lambda"]
        molar_mass = self._molar_mass_from_comp(composition)
        upstream.h = props["h_molar"] / molar_mass
        upstream.cp = props["cp_molar"] / molar_mass
        upstream.cv = props["cv_molar"] / molar_mass

        eta = p_down / upstream.p
        C_q = self.C_q_polynomial(eta)
        C_m = self.C_m_piecewise(
            eta=eta,
            gamma_s=upstream.gamma,
            rho_up=upstream.rho,
            T_up=upstream.T,
            p_up=upstream.p,
        )
        m_dot = self.m_dot_resistive(upstream.p, upstream.T, C_q, C_m)
        h_dot = self.h_dot_from_mdot(m_dot, upstream)
        return {"m_dot": m_dot, "h_dot": h_dot, "C_q": C_q, "C_m": C_m}
