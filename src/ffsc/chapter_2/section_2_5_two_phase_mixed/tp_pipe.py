"""§2.5.1 两相管路模型骨架。"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import TwoPhaseThermo

from .base import Component, TwoPhaseState
from .registry import register


@dataclass
@register("tp_pipe")
class TwoPhasePipe(Component):
    A: float
    k: float
    k_dp: float
    D: Optional[float] = None
    epsilon: Optional[float] = None
    thermo: Optional[TwoPhaseThermo] = field(default=None, repr=False)

    def _ensure_thermo(self) -> TwoPhaseThermo:
        if self.thermo is None:
            raise MissingPropertyData("TwoPhasePipe requires TwoPhaseThermo to evaluate state")
        return self.thermo

    def mass_flow_from_dp(self, rho_up: float, dp: float) -> float:
        if rho_up <= 0 or self.A <= 0 or self.k <= 0 or self.k_dp <= 0:
            raise ValueError("invalid inputs for (2.82)")
        return (rho_up * self.A / math.sqrt(self.k)) * math.sqrt((2.0 * abs(dp) * self.k_dp) / rho_up)

    @staticmethod
    def enthalpy_flow(dm: float, h_up: float) -> float:
        return dm * h_up

    @staticmethod
    def lockhart_martinelli(x: float, rho_l: float, rho_v: float, mu_l: float, mu_v: float) -> float:
        if not (0.0 < x < 1.0):
            raise ValueError("quality x must be in (0,1)")
        return ((1.0 - x) / x) ** 0.9 * (rho_v / rho_l) ** 0.5 * (mu_l / mu_v) ** 0.1

    @staticmethod
    def phi_liquid_squared(X_tt: float) -> float:
        return 1.0 + 20.0 / X_tt + 1.0 / (X_tt ** 2)

    @staticmethod
    def phi_vapor_squared(X_tt: float) -> float:
        return 1.0 + X_tt + X_tt ** 2

    def friction_pressure_drop(
        self,
        length: float,
        G: float,
        rho_l: float,
        rho_v: float,
        mu_l: float,
        mu_v: float,
        x: float,
    ) -> float:
        if self.D is None or self.D <= 0:
            raise MissingPropertyData("TwoPhasePipe requires hydraulic diameter D to compute friction drop")
        if length <= 0:
            raise ValueError("length must be >0")
        if G <= 0:
            raise ValueError("mass flux G must be >0")

        Re_l = G * (1.0 - x) * self.D / mu_l
        f_l = self.friction_factor_churchill(Re_l, (self.epsilon or 0.0) / self.D)
        dpdz_liquid = f_l * (G ** 2) / (2.0 * rho_l * self.D)

        X_tt = self.lockhart_martinelli(x, rho_l, rho_v, mu_l, mu_v)
        phi_l_sq = self.phi_liquid_squared(X_tt)
        return dpdz_liquid * phi_l_sq * length

    def acceleration_pressure_drop(self, m_dot: float, area: float, d_alpha_dr: float, rho_l: float, rho_v: float) -> float:
        if area <= 0:
            raise ValueError("area must be >0")
        if rho_l <= 0 or rho_v <= 0:
            raise ValueError("phase densities must be >0")
        if d_alpha_dr == 0:
            return 0.0
        G = m_dot / area
        inv_rho_mix = (d_alpha_dr / rho_v) - (d_alpha_dr / rho_l)
        return -G ** 2 * inv_rho_mix

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

    def update_upstream_state(self, state: TwoPhaseState) -> TwoPhaseState:
        thermo = self._ensure_thermo()
        if state.T is None or state.rho is None:
            raise ValueError("TwoPhaseState must include T and rho before evaluation")
        props = thermo.state(state.T, state.rho)
        state.p = props["p"]
        state.h = props["h_molar"]
        state.u = props["u_molar"]
        state.s = props["s_molar"]
        state.cp = props["cp_molar"]
        state.cv = props["cv_molar"]
        state.extra.update({"residual": props["residual"]})
        return state
