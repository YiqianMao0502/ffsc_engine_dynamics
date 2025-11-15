from dataclasses import dataclass, field

@dataclass
class FluidState:
    p: float | None = None
    T: float | None = None
    rho: float | None = None
    h: float | None = None
    v: float | None = None  # 1/rho if rho provided

@dataclass
class TwoPhasePlenum:
    """
    §2.5.1 两相流容腔（只含守恒骨架；不含沿程压降）
    式(2.84) dρ/dt = (1/vol) Σ ṁ_i
    式(2.85) dU/dt = Ė + Σ ṁ_i h_i + Q̇  （返回 RHS 以便上层积分）
    式(2.86) dT/dt 公式中 c_v = (∂u/∂T)|_V，dv/dt = -1/ρ² · dρ/dt；
    式(2.87) 的 (∂p/∂v)|_T 与 (∂p/∂T)|_v 等 EOS 偏导由上层/物性模块提供（本模块不实现）。
    """
    volume: float
    state: FluidState = field(default_factory=FluidState)

    def accumulate_mass(self, m_dot_sum: float, dt: float):
        if self.volume <= 0:
            raise ValueError("volume must be >0")
        if self.state.rho is None:
            raise ValueError("state.rho required")
        self.state.rho += (m_dot_sum / self.volume) * dt
        self.state.v = None

    @staticmethod
    def energy_balance_rhs(E_dot: float, sum_m_dot_h: float, Q_dot: float) -> float:
        return E_dot + sum_m_dot_h + Q_dot
