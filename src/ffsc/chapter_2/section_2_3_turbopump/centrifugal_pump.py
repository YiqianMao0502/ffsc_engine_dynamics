"""§2.3 涡轮泵组件模型（Route-A 结构）。

本模块把论文第 2.3 节中给出的控制方程整理为可编程接口：

* 涡壳动量/连续方程 (2.14)–(2.38)
* 叶轮动能与压头关系 (2.39)–(2.55)
* 等熵效率与实验拟合表（表 9–12、图 21–23）

由于论文未在附录给出全部经验常数与效率拟合系数，本文件在缺参时会
抛出 :class:`~ffsc.common.exceptions.MissingPropertyData`，提醒调用者补充对
应的 JSON/表格数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, sin
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np

from ffsc.common.exceptions import MissingPropertyData


@dataclass
class VoluteCoefficients:
    """对应论文表 9 的常数 :math:`C_1…C_4`。"""

    C1: float
    C2: float
    C3: float
    C4: float


@dataclass
class VoluteGeometry:
    """记录涡壳周向坐标、截面积与壁速。"""

    area_profile: Callable[[float], float]
    wall_velocity: Callable[[float], float]
    relative_angle: Callable[[float], float]


@dataclass
class VoluteState:
    """最小状态量：密度、质量流率、相对速度分量等。"""

    rho_w: float
    m_dot: float
    v_theta: float
    v_r: float
    beta: float
    p: float


@dataclass
class VoluteModel:
    """实现 (2.14)–(2.33) 的数值包装。"""

    coeffs: VoluteCoefficients
    geom: VoluteGeometry

    def mass_balance(self, tau: float, state: VoluteState) -> float:
        """式 (2.15)：:math:`\mathrm{d}\dot m/\mathrm{d}\tau`。"""

        area = self.geom.area_profile(tau)
        beta = self.geom.relative_angle(tau)
        v_w = self.geom.wall_velocity(tau)
        term = state.rho_w * area * (v_w * cos(beta) + state.v_theta * sin(beta))
        return term

    def momentum_rhs(self, tau: float, state: VoluteState) -> float:
        """式 (2.26)–(2.28)：压降随角度变化。"""

        C1, C2, C3, C4 = self.coeffs.C1, self.coeffs.C2, self.coeffs.C3, self.coeffs.C4
        beta = self.geom.relative_angle(tau)
        area = self.geom.area_profile(tau)
        if area <= 0:
            raise ValueError("Volute area must be positive")
        v_w = self.geom.wall_velocity(tau)
        term_dynamic = C1 * state.rho_w * state.v_theta ** 2
        term_coupling = C2 * state.rho_w * state.v_theta * state.v_r * cos(beta)
        term_mass = C3 * state.m_dot / area
        term_geometry = C4 * v_w ** 2
        return term_dynamic + term_coupling + term_mass + term_geometry

    def integrate(
        self,
        tau_grid: Iterable[float],
        initial_state: VoluteState,
        stepper: Optional[Callable[[VoluteState, float, float], VoluteState]] = None,
    ) -> List[VoluteState]:
        """按照给定角度网格积分涡壳方程。

        Parameters
        ----------
        tau_grid:
            角度离散点（弧度）。必须从入口向出口单调递增。
        initial_state:
            入口处的初始状态。
        stepper:
            可选的状态更新器，默认为一阶欧拉法。
        """

        grid = list(tau_grid)
        if len(grid) < 2:
            raise ValueError("tau_grid 需要至少两个节点")
        if sorted(grid) != grid:
            raise ValueError("tau_grid 必须递增")

        def default_stepper(state: VoluteState, tau: float, dtau: float) -> VoluteState:
            dm = self.mass_balance(tau, state)
            dp = self.momentum_rhs(tau, state)
            new_state = VoluteState(
                rho_w=state.rho_w,
                m_dot=state.m_dot + dm * dtau,
                v_theta=state.v_theta,
                v_r=state.v_r,
                beta=self.geom.relative_angle(tau + dtau),
                p=state.p + dp * dtau,
            )
            return new_state

        states = [initial_state]
        current = initial_state
        for idx in range(len(grid) - 1):
            current_tau = grid[idx]
            dtau = grid[idx + 1] - grid[idx]
            if stepper is None:
                new_state = default_stepper(current, current_tau, dtau)
            else:
                new_state = stepper(current, current_tau, dtau)
            states.append(new_state)
            current = new_state
        return states


@dataclass
class ImpellerGeometry:
    r_in: float
    r_out: float
    b_in: float
    b_out: float
    blade_angle_in: float
    blade_angle_out: float


@dataclass
class ImpellerState:
    rho: float
    v_r_in: float
    v_r_out: float
    v_theta_out: float
    u_in: float
    u_out: float
    h_in: float
    h_out: float


@dataclass
class ImpellerModel:
    """式 (2.39)–(2.55)：叶轮能量平衡。"""

    geometry: ImpellerGeometry
    slip_factor: Callable[[float], float]
    loss_coefficients: Mapping[str, float] = field(default_factory=dict)

    def theoretical_head(self, state: ImpellerState) -> float:
        return (state.u_out * state.v_theta_out - state.u_in * state.v_r_in) / 9.81

    def actual_head(self, state: ImpellerState) -> float:
        sigma = self.slip_factor(state.v_r_out)
        H_t = self.theoretical_head(state)
        return sigma * H_t

    def hydraulic_efficiency(self, state: ImpellerState) -> float:
        sigma = self.slip_factor(state.v_r_out)
        losses = self.loss_coefficients
        k_h = losses.get("k_h", 0.0)
        return max(1e-8, sigma - k_h)

    def shaft_power(self, state: ImpellerState, m_dot: float) -> float:
        H = self.actual_head(state)
        eta_h = self.hydraulic_efficiency(state)
        if eta_h <= 0:
            raise ValueError("hydraulic efficiency must be positive")
        return m_dot * 9.81 * H / eta_h

    def outlet_enthalpy(self, state: ImpellerState, m_dot: float) -> float:
        power = self.shaft_power(state, m_dot)
        return state.h_in + power / m_dot


@dataclass
class PumpPerformanceCurve:
    """经验曲线，用于拟合实验数据 (表 11–12)。"""

    speed_rpm: float
    flow_rate: float
    head: float
    efficiency: float


@dataclass
class CentrifugalPump:
    volute: VoluteModel
    impeller: ImpellerModel
    performance_data: List[PumpPerformanceCurve] = field(default_factory=list)
    _head_fit: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    _efficiency_fit: Optional[np.ndarray] = field(default=None, init=False, repr=False)

    def interpolate_efficiency(self, speed_rpm: float, flow_rate: float) -> float:
        if not self.performance_data:
            raise MissingPropertyData("需要表 11/12 的性能曲线数据以插值效率")
        best = min(
            self.performance_data,
            key=lambda row: (abs(row.speed_rpm - speed_rpm) + abs(row.flow_rate - flow_rate)),
        )
        return best.efficiency

    def head_from_curve(self, speed_rpm: float, flow_rate: float) -> float:
        if not self.performance_data:
            raise MissingPropertyData("需要泵实验曲线以估算压头")
        best = min(
            self.performance_data,
            key=lambda row: (abs(row.speed_rpm - speed_rpm) + abs(row.flow_rate - flow_rate)),
        )
        return best.head

    def compute_operating_point(
        self,
        tau_grid: Iterable[float],
        volute_state: VoluteState,
        impeller_state: ImpellerState,
        m_dot: float,
        speed_rpm: float,
    ) -> Dict[str, float]:
        volute_profile = self.volute.integrate(tau_grid, volute_state)
        h_out = self.impeller.outlet_enthalpy(impeller_state, m_dot)
        eta = self.interpolate_efficiency(speed_rpm, m_dot)
        head = self.head_from_curve(speed_rpm, m_dot)
        return {
            "volute_profile": volute_profile,
            "outlet_enthalpy": h_out,
            "efficiency": eta,
            "head": head,
        }

    def _design_matrix(self) -> np.ndarray:
        flows = np.array([row.flow_rate for row in self.performance_data], dtype=float)
        speeds = np.array([row.speed_rpm for row in self.performance_data], dtype=float)
        ones = np.ones_like(flows)
        return np.column_stack([ones, flows, speeds, flows**2, speeds**2, flows * speeds])

    def _ensure_head_fit(self) -> None:
        if self._head_fit is not None or not self.performance_data:
            return
        heads = np.array([row.head for row in self.performance_data], dtype=float)
        coef, *_ = np.linalg.lstsq(self._design_matrix(), heads, rcond=None)
        self._head_fit = coef

    def _ensure_efficiency_fit(self) -> None:
        if self._efficiency_fit is not None or not self.performance_data:
            return
        eff = np.array([row.efficiency for row in self.performance_data], dtype=float)
        coef, *_ = np.linalg.lstsq(self._design_matrix(), eff, rcond=None)
        self._efficiency_fit = coef

    def predict_head(self, speed_rpm: float, flow_rate: float) -> float:
        self._ensure_head_fit()
        if self._head_fit is None:
            raise MissingPropertyData("缺少泵压头拟合数据")
        features = np.array(
            [1.0, flow_rate, speed_rpm, flow_rate**2, speed_rpm**2, flow_rate * speed_rpm], dtype=float
        )
        return float(features @ self._head_fit)

    def predict_efficiency(self, speed_rpm: float, flow_rate: float) -> float:
        self._ensure_efficiency_fit()
        if self._efficiency_fit is None:
            raise MissingPropertyData("缺少泵效率拟合数据")
        features = np.array(
            [1.0, flow_rate, speed_rpm, flow_rate**2, speed_rpm**2, flow_rate * speed_rpm], dtype=float
        )
        return float(features @ self._efficiency_fit)

    def flow_limits(self) -> Optional[Tuple[float, float]]:
        if not self.performance_data:
            return None
        flows = [row.flow_rate for row in self.performance_data]
        return min(flows), max(flows)

    def head_limits(self) -> Optional[Tuple[float, float]]:
        if not self.performance_data:
            return None
        heads = [row.head for row in self.performance_data]
        return min(heads), max(heads)


def build_from_tables(
    volute_coeffs: Mapping[str, float],
    area_profile: Callable[[float], float],
    wall_velocity: Callable[[float], float],
    relative_angle: Callable[[float], float],
    slip_factor: Callable[[float], float],
    performance_rows: Iterable[Mapping[str, float]],
    loss_coefficients: Optional[Mapping[str, float]] = None,
    impeller_geometry: Optional[Mapping[str, float]] = None,
) -> CentrifugalPump:
    coeffs = VoluteCoefficients(
        C1=float(volute_coeffs["C1"]),
        C2=float(volute_coeffs["C2"]),
        C3=float(volute_coeffs["C3"]),
        C4=float(volute_coeffs["C4"]),
    )
    geom = VoluteGeometry(area_profile=area_profile, wall_velocity=wall_velocity, relative_angle=relative_angle)
    volute = VoluteModel(coeffs=coeffs, geom=geom)

    if impeller_geometry is None:
        raise MissingPropertyData("build_from_tables 需要叶轮几何参数 (表 12)")

    imp_geom = ImpellerGeometry(
        r_in=float(impeller_geometry["r_in"]),
        r_out=float(impeller_geometry["r_out"]),
        b_in=float(impeller_geometry["b_in"]),
        b_out=float(impeller_geometry["b_out"]),
        blade_angle_in=float(impeller_geometry["blade_angle_in"]),
        blade_angle_out=float(impeller_geometry["blade_angle_out"]),
    )

    impeller = ImpellerModel(
        geometry=imp_geom,
        slip_factor=slip_factor,
        loss_coefficients=dict(loss_coefficients or {}),
    )

    curves = [
        PumpPerformanceCurve(
            speed_rpm=float(row["speed_rpm"]),
            flow_rate=float(row["flow_rate"]),
            head=float(row["head"]),
            efficiency=float(row["efficiency"]),
        )
        for row in performance_rows
    ]

    return CentrifugalPump(volute=volute, impeller=impeller, performance_data=curves)
