from dataclasses import dataclass
from .registry import register

@dataclass
@register("pressurizer_hx")
class PressurizerHX:
    """
    §2.5.4 贮箱增压路（仅存储表21给出的体积与分流；不实现换热公式）
    """
    fuel_total_flow: float = 149.0
    fuel_press_flow: float = 1.94
    fuel_gas_vol: float = 0.0353
    fuel_tp_vol: float = 0.00377

    ox_total_flow: float = 536.0
    ox_press_flow: float = 4.97
    ox_gas_vol: float = 0.0589
    ox_tp_vol: float = 0.00377

    def split_fuel_flow(self, m_dot_fuel_total: float) -> tuple[float, float]:
        r = self.fuel_press_flow / self.fuel_total_flow
        to_press = r * m_dot_fuel_total
        return to_press, m_dot_fuel_total - to_press

    def split_ox_flow(self, m_dot_ox_total: float) -> tuple[float, float]:
        r = self.ox_press_flow / self.ox_total_flow
        to_press = r * m_dot_ox_total
        return to_press, m_dot_ox_total - to_press
