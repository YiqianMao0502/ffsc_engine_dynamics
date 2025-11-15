"""§2.5.1 两相容腔骨架。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import TwoPhaseThermo, _MOLAR_MASS

from .base import Component, TwoPhaseState


@dataclass
class TwoPhasePlenum(Component):
    volume: float
    thermo: Optional[TwoPhaseThermo] = field(default=None, repr=False)
    state: TwoPhaseState = field(default_factory=TwoPhaseState)

    def accumulate_mass(self, m_dot_sum: float, dt: float):
        if self.volume <= 0:
            raise ValueError("volume must be >0")
        if self.state.rho is None:
            raise ValueError("state.rho required")
        self.state.rho += (m_dot_sum / self.volume) * dt

    def _ensure_thermo(self) -> TwoPhaseThermo:
        if self.thermo is None:
            raise MissingPropertyData("TwoPhasePlenum requires TwoPhaseThermo for thermodynamic derivatives")
        return self.thermo

    def rhs(
        self,
        m_dot_in: float,
        m_dot_out: float,
        Q_dot: float,
        extra_inputs: Dict[str, float] | None = None,
    ) -> Dict[str, float]:
        if self.state.T is None or self.state.rho is None:
            raise ValueError("state must include T and rho")
        thermo = self._ensure_thermo()
        props = thermo.state(self.state.T, self.state.rho)
        drho_dt = (m_dot_in - m_dot_out) / self.volume
        notes = []
        try:
            cv_molar = props["cv_molar"]
            molar_mass = _MOLAR_MASS.get(thermo.name)
            if molar_mass is None:
                raise MissingPropertyData(f"缺少 {thermo.name} 的摩尔质量信息")
            cv_mass = cv_molar / molar_mass
            dT_dt = (Q_dot - props["p"] * drho_dt) / (self.state.rho * cv_mass)
            derivs = props.get("derivatives", {})
            dp_dt = derivs.get("dp_drho_T", float("nan")) * drho_dt + derivs.get("dp_dT_rho", 0.0) * dT_dt
        except Exception:
            dT_dt = float("nan")
            dp_dt = float("nan")
            notes.append("Two-phase cv or pressure derivative missing; provide saturation data")
        return {
            "drho_dt": drho_dt,
            "dT_dt": dT_dt,
            "dp_dt": dp_dt,
            "notes": notes,
            "residual": props["residual"],
        }
