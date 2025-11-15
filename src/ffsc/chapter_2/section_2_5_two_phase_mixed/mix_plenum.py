from dataclasses import dataclass, field

@dataclass
class FluidState:
    p: float | None = None
    T: float | None = None
    rho: float | None = None
    h: float | None = None
    v: float | None = None

@dataclass
class MixGasPlenum:
    """§2.5.3 混合气体容腔（不计沿程压降；守恒骨架同两相容腔）"""
    volume: float
    state: FluidState = field(default_factory=FluidState)

    def accumulate_mass(self, m_dot_sum: float, dt: float):
        if self.volume <= 0:
            raise ValueError("volume must be >0")
        if self.state.rho is None:
            raise ValueError("state.rho required")
        self.state.rho += (m_dot_sum / self.volume) * dt
        self.state.v = None
