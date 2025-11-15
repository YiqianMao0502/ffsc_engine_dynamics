"""§2.5.3 混合气容腔模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import GasMixtureThermo, R_UNIVERSAL, _MOLAR_MASS

from .base import Component, GasState


@dataclass
class MixGasPlenum(Component):
    volume: float
    thermo: Optional[GasMixtureThermo] = field(default=None, repr=False)
    state: GasState = field(default_factory=GasState)

    def _ensure_state(self):
        if self.volume <= 0:
            raise ValueError("volume must be >0")
        if self.state.rho is None:
            raise ValueError("state.rho must be initialised before integration")
        if self.state.T is None or self.state.p is None:
            raise ValueError("state must include T and p")

    def _ensure_thermo(self) -> GasMixtureThermo:
        if self.thermo is None:
            raise MissingPropertyData("MixGasPlenum requires GasMixtureThermo for cv and cp evaluation")
        return self.thermo

    def accumulate_mass(self, m_dot_sum: float, dt: float):
        self._ensure_state()
        self.state.rho += (m_dot_sum / self.volume) * dt

    def rhs(
        self,
        m_dot_in: float,
        m_dot_out: float,
        Q_dot: float,
        composition: Dict[str, float],
    ) -> Dict[str, float]:
        self._ensure_state()
        thermo = self._ensure_thermo()
        props = thermo.state(self.state.p, self.state.T, composition)
        drho_dt = (m_dot_in - m_dot_out) / self.volume
        notes = []
        try:
            molar_mass = self._molar_mass(composition)
            cv_mass = props["cv_molar"] / molar_mass
            dT_dt = (Q_dot - self.state.p * drho_dt) / (self.state.rho * cv_mass)
            R_specific = R_UNIVERSAL / molar_mass
            dp_dt = R_specific * (self.state.rho * dT_dt + self.state.T * drho_dt)
        except Exception:
            dT_dt = float("nan")
            dp_dt = float("nan")
            notes.append("cv evaluation failed; requires complete NASA/transport data")
        return {"drho_dt": drho_dt, "dT_dt": dT_dt, "dp_dt": dp_dt, "notes": notes}

    def _molar_mass(self, composition: Dict[str, float]) -> float:
        total = sum(composition.values())
        if total <= 0:
            raise ValueError("composition fractions sum to zero")
        try:
            return sum(_MOLAR_MASS[name] * frac for name, frac in composition.items()) / total
        except KeyError as exc:
            raise MissingPropertyData(f"No molar-mass entry for species '{exc.args[0]}' in Route-B dataset") from exc
