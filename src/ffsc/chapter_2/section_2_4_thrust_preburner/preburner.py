"""推力室与预燃室组件模型（论文 §2.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Dict, Iterable, Mapping, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import GasMixtureThermo
from ..section_2_5_two_phase_mixed.base import GasState

R_UNIVERSAL = 8.314462618


@dataclass
class CombustionSource:
    """化学源项，存储各物种的质量生成率。"""

    species: Dict[str, float]

    def total(self) -> float:
        return sum(self.species.values())


@dataclass
class PreburnerChamber:
    """方程 (2.57)–(2.61) 的程序化形式。"""

    volume: float
    thermo: GasMixtureThermo
    state: GasState = field(default_factory=GasState)

    def _ensure_state(self):
        if self.state.rho is None or self.state.T is None or self.state.p is None:
            raise ValueError("Preburner state must include p, T, rho")
        if not self.state.composition:
            raise ValueError("Preburner state requires species composition")

    def mixture_props(self) -> Dict[str, float]:
        self._ensure_state()
        return self.thermo.state(self.state.p, self.state.T, self.state.composition)

    def rhs(
        self,
        inlets: Iterable[tuple[float, GasState]],
        outlets: Iterable[tuple[float, GasState]],
        source: Optional[CombustionSource] = None,
        Q_dot_loss: float = 0.0,
    ) -> Dict[str, float]:
        """Compute time-derivatives for mass, species, and temperature."""

        self._ensure_state()
        m_dot_in = sum(flow for flow, _ in inlets)
        m_dot_out = sum(flow for flow, _ in outlets)
        mass_balance = m_dot_in - m_dot_out
        dm_dt = mass_balance

        mixture = self.mixture_props()
        rho = mixture["rho_mass"]
        cv = mixture["cv_molar"] / self._molar_mass(self.state.composition)
        if cv <= 0:
            raise MissingPropertyData("cv must be positive; check NASA-7 dataset")

        dT_dt = (sum(flow * st.h for flow, st in inlets if st.h is not None) - m_dot_out * (self.state.h or 0.0) - Q_dot_loss) / (
            rho * self.volume * cv
        )

        species_deriv: Dict[str, float] = {}
        for species in self.state.composition:
            inflow = sum(flow * (st.composition.get(species, 0.0)) for flow, st in inlets)
            outflow = m_dot_out * self.state.composition.get(species, 0.0)
            gen = 0.0
            if source is not None:
                gen = source.species.get(species, 0.0)
            species_deriv[species] = (inflow - outflow + gen) / (rho * self.volume)

        return {"dm_dt": dm_dt, "dT_dt": dT_dt, "species": species_deriv}

    @staticmethod
    def _molar_mass(composition: Mapping[str, float]) -> float:
        from ..section_2_2_properties.interfaces import _MOLAR_MASS

        total = sum(composition.values())
        if total <= 0:
            raise ValueError("composition fractions sum to zero")
        try:
            return sum(_MOLAR_MASS[name] * frac for name, frac in composition.items()) / total
        except KeyError as exc:
            raise MissingPropertyData(f"Missing molar mass for species '{exc.args[0]}'") from exc


@dataclass
class NozzleGeometry:
    throat_area: float
    exit_area: float


@dataclass
class NozzleModel:
    """喷管等熵流模型，对应式 (2.62)–(2.69)。"""

    geometry: NozzleGeometry
    discharge_coeff: float = 1.0
    heat_transfer_coeff: Optional[float] = None

    def mass_flow(self, p_total: float, T_total: float, gamma: float, p_exit: float) -> float:
        if p_total <= 0 or T_total <= 0 or gamma <= 1.0:
            raise ValueError("invalid inputs for nozzle mass flow")
        eta = p_exit / p_total
        eta_crit = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        if eta <= eta_crit:
            term = sqrt(gamma / (R_UNIVERSAL * T_total) * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (gamma - 1.0)))
        else:
            term = sqrt((2.0 * gamma / (gamma - 1.0)) * (eta ** (2.0 / gamma) - eta ** ((gamma + 1.0) / gamma))) / sqrt(R_UNIVERSAL * T_total)
        return self.discharge_coeff * self.geometry.throat_area * p_total * term

    def cooling_flow(self, p_total: float, p_cool: float, gamma: float, area: float, coeff: float) -> float:
        if p_total <= 0 or p_cool <= 0:
            raise ValueError("pressures must be >0")
        return coeff * area * p_total * sqrt((2.0 * gamma / (gamma - 1.0)) * (1.0 - (p_cool / p_total) ** ((gamma - 1.0) / gamma)))

    def heat_flux(self, h_conv: float, area: float, T_wall: float, T_gas: float) -> float:
        return h_conv * area * (T_wall - T_gas)
