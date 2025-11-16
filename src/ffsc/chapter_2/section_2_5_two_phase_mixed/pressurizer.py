"""§2.5.4 贮箱增压换热器模型。"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Tuple

from ffsc.common.exceptions import MissingPropertyData

from .registry import register


@dataclass
@register("pressurizer_hx")
class PressurizerHX:
    fuel_total_flow: float = 149.0
    fuel_press_flow: float = 1.94
    fuel_gas_vol: float = 0.0353
    fuel_tp_vol: float = 0.00377

    ox_total_flow: float = 536.0
    ox_press_flow: float = 4.97
    ox_gas_vol: float = 0.0589
    ox_tp_vol: float = 0.00377
    UA: float = 0.0
    wall_heat_capacity: float = 0.0
    wall_temperature: float = 300.0

    def split_fuel_flow(self, m_dot_fuel_total: float) -> Tuple[float, float]:
        r = self.fuel_press_flow / self.fuel_total_flow
        to_press = r * m_dot_fuel_total
        return to_press, m_dot_fuel_total - to_press

    def split_ox_flow(self, m_dot_ox_total: float) -> Tuple[float, float]:
        r = self.ox_press_flow / self.ox_total_flow
        to_press = r * m_dot_ox_total
        return to_press, m_dot_ox_total - to_press

    def heat_balance(self, inputs: Dict[str, float]) -> Dict[str, float]:
        if self.UA <= 0 or self.wall_heat_capacity <= 0:
            raise MissingPropertyData("PressurizerHX requires UA and wall heat capacity from §2.5.4")
        try:
            T_hot = inputs["T_hot"]
            T_cold = inputs["T_cold"]
            T_wall = inputs.get("T_wall", self.wall_temperature)
            m_dot_hot = inputs["m_dot_hot"]
            cp_hot = inputs["cp_hot"]
            m_dot_cold = inputs["m_dot_cold"]
            cp_cold = inputs["cp_cold"]
        except KeyError as exc:
            raise MissingPropertyData(f"Missing pressurizer input '{exc.args[0]}'") from exc

        delta_T1 = T_hot - T_wall
        delta_T2 = T_wall - T_cold
        if delta_T1 == delta_T2:
            LMTD = delta_T1
        else:
            ratio = delta_T1 / delta_T2 if delta_T2 != 0 else 1.0
            if ratio <= 0:
                ratio = abs(ratio) if ratio != 0 else 1.0
            LMTD = (delta_T1 - delta_T2) / (math.log(ratio) if ratio != 0 else 1.0)
        Q_dot = self.UA * LMTD
        dT_wall_dt = (Q_dot - m_dot_hot * cp_hot * (T_hot - T_wall) + m_dot_cold * cp_cold * (T_wall - T_cold)) / self.wall_heat_capacity
        self.wall_temperature = T_wall + dT_wall_dt * inputs.get("dt", 0.0)
        return {"Q_dot": Q_dot, "dT_wall_dt": dT_wall_dt, "T_wall": self.wall_temperature}
