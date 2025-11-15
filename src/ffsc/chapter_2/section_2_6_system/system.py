"""§2.6 全系统网络骨架。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import build_gas_mixture_thermo, build_two_phase_thermo
from ..section_2_3_turbopump.centrifugal_pump import CentrifugalPump, build_from_tables
from ..section_2_4_thrust_preburner import NozzleGeometry, NozzleModel, PreburnerChamber
from ..section_2_5_two_phase_mixed.mix_pipe import MixGasPipe
from ..section_2_5_two_phase_mixed.mix_plenum import MixGasPlenum
from ..section_2_5_two_phase_mixed.pressurizer import PressurizerHX
from ..section_2_5_two_phase_mixed.tp_pipe import TwoPhasePipe
from ..section_2_5_two_phase_mixed.tp_plenum import TwoPhasePlenum
from ..section_2_5_two_phase_mixed.tp_valve import TwoPhaseValve


@dataclass
class EngineSystem:
    """高层封装：记录 §2.6 图 48 组件连线的骨架。"""

    fuel_liquid: TwoPhasePipe
    fuel_valve: TwoPhaseValve
    fuel_plenum: TwoPhasePlenum
    ox_liquid: TwoPhasePipe
    ox_valve: TwoPhaseValve
    ox_plenum: TwoPhasePlenum
    main_mix: MixGasPipe
    mix_plenum: MixGasPlenum
    pressurizer: PressurizerHX
    pump: Optional[CentrifugalPump] = None
    preburner: Optional[PreburnerChamber] = None
    nozzle: Optional[NozzleModel] = None

    def missing_data(self) -> List[str]:
        missing = []
        if isinstance(self.fuel_liquid.thermo, type(None)):
            missing.append("fuel_liquid TwoPhaseThermo coefficients (MBWR Table-8)")
        if isinstance(self.ox_liquid.thermo, type(None)):
            missing.append("ox_liquid TwoPhaseThermo coefficients (MBWR Table-8)")
        if isinstance(self.main_mix.thermo, type(None)):
            missing.append("GasMixtureThermo Route-B dataset (PR/NASA/V2C2)")
        missing.append("Two-phase saturation properties for plenum energy closure")
        missing.append("Pressurizer heat-transfer correlations from §2.5.4")
        if self.pump is None or not getattr(self.pump, "performance_data", None):
            missing.append("Centrifugal pump performance curves (表 11/12)")
        elif any(row.head == 10.0 for row in self.pump.performance_data):
            missing.append("Centrifugal pump performance curves (表 11/12)")
        if self.preburner is None or not self.preburner.state.composition:
            missing.append("Preburner chemical source terms and initial composition")
        if self.nozzle is None or self.nozzle.discharge_coeff == 1.0:
            missing.append("Nozzle discharge/heat-transfer coefficients from §2.4.2")
        return missing

    def step(self, dt: float):
        raise MissingPropertyData("System-level dynamic solver requires completion of outstanding TODO items")


def build_default_system(props_root: str) -> EngineSystem:
    """构建 Route-A/B 混合的系统骨架，仍包含若干占位项。"""

    gas_thermo = build_gas_mixture_thermo(
        f"{props_root}/mix_pr_demo.json",
        f"{props_root}/mix_nasa7_gri30.json",
        f"{props_root}/transport_v2c2_tm86885.json",
    )
    # 两相物性尚缺 Table-8 系数，构建后仍会在使用时抛 MissingPropertyData。
    try:
        fuel_thermo = build_two_phase_thermo(
            "CH4",
            f"{props_root}/mbwr_placeholders/ch4_mbwr32_placeholder.json",
            f"{props_root}/mix_nasa7_gri30.json",
        )
    except MissingPropertyData:
        fuel_thermo = None
    try:
        ox_thermo = build_two_phase_thermo(
            "O2",
            f"{props_root}/mbwr_placeholders/o2_mbwr32_placeholder.json",
            f"{props_root}/mix_nasa7_gri30.json",
        )
    except MissingPropertyData:
        ox_thermo = None

    fuel_line = TwoPhasePipe(A=1.0, k=1.0, k_dp=1.0, thermo=fuel_thermo, D=0.05, epsilon=1e-5)
    ox_line = TwoPhasePipe(A=1.0, k=1.0, k_dp=1.0, thermo=ox_thermo, D=0.05, epsilon=1e-5)
    fuel_valve = TwoPhaseValve(A=1.0, k=1.0, k_dp=1.0)
    ox_valve = TwoPhaseValve(A=1.0, k=1.0, k_dp=1.0)
    fuel_plenum = TwoPhasePlenum(volume=0.01, thermo=fuel_thermo)
    ox_plenum = TwoPhasePlenum(volume=0.01, thermo=ox_thermo)
    mix_pipe = MixGasPipe(A=1.0, thermo=gas_thermo)
    mix_plenum = MixGasPlenum(volume=0.02, thermo=gas_thermo)
    pressurizer = PressurizerHX(UA=0.0, wall_heat_capacity=0.0)

    pump = None
    try:
        pump = build_from_tables(
            volute_coeffs={"C1": 0.0, "C2": 0.0, "C3": 0.0, "C4": 0.0},
            area_profile=lambda tau: 1.0,
            wall_velocity=lambda tau: 0.0,
            relative_angle=lambda tau: 0.0,
            slip_factor=lambda v_r: 1.0,
            performance_rows=[
                {"speed_rpm": 30000.0, "flow_rate": 10.0, "head": 10.0, "efficiency": 0.5},
            ],
            loss_coefficients={"k_h": 0.0},
            impeller_geometry={
                "r_in": 0.05,
                "r_out": 0.1,
                "b_in": 0.02,
                "b_out": 0.015,
                "blade_angle_in": 0.52,
                "blade_angle_out": 0.35,
            },
        )
    except MissingPropertyData:
        pump = None

    preburner = None
    if gas_thermo is not None:
        preburner = PreburnerChamber(volume=0.02, thermo=gas_thermo)

    nozzle = NozzleModel(geometry=NozzleGeometry(throat_area=0.01, exit_area=0.1))

    return EngineSystem(
        fuel_liquid=fuel_line,
        fuel_valve=fuel_valve,
        fuel_plenum=fuel_plenum,
        ox_liquid=ox_line,
        ox_valve=ox_valve,
        ox_plenum=ox_plenum,
        main_mix=mix_pipe,
        mix_plenum=mix_plenum,
        pressurizer=pressurizer,
        pump=pump,
        preburner=preburner,
        nozzle=nozzle,
    )
