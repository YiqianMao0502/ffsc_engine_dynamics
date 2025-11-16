"""§2.6 全系统网络骨架。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ffsc.common.exceptions import MissingPropertyData

from ..section_2_2_properties.interfaces import (
    _MOLAR_MASS,
    build_gas_mixture_thermo,
    build_two_phase_thermo,
    load_saturation_tables,
)
from ..section_2_3_turbopump.centrifugal_pump import CentrifugalPump, build_from_tables
from ..section_2_4_thrust_preburner import CombustionSource, NozzleGeometry, NozzleModel, PreburnerChamber
from ..section_2_5_two_phase_mixed.mix_pipe import MixGasPipe
from ..section_2_5_two_phase_mixed.mix_plenum import MixGasPlenum
from ..section_2_5_two_phase_mixed.pressurizer import PressurizerHX
from ..section_2_5_two_phase_mixed.tp_pipe import TwoPhasePipe
from ..section_2_5_two_phase_mixed.tp_plenum import TwoPhasePlenum
from ..section_2_5_two_phase_mixed.tp_valve import TwoPhaseValve
from ..section_2_5_two_phase_mixed.base import GasState, TwoPhaseState


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
    preburner_source: Optional[CombustionSource] = None
    preburner_heat_loss: float = 0.0
    nozzle_exit_pressure: float = 5.0e4
    nozzle_cooling_area: float = 0.0
    nozzle_cooling_coeff: float = 0.0

    def missing_data(self) -> List[str]:
        missing = []
        if isinstance(self.fuel_liquid.thermo, type(None)):
            missing.append("fuel_liquid TwoPhaseThermo coefficients (MBWR Table-8)")
        if isinstance(self.ox_liquid.thermo, type(None)):
            missing.append("ox_liquid TwoPhaseThermo coefficients (MBWR Table-8)")
        if isinstance(self.main_mix.thermo, type(None)):
            missing.append("GasMixtureThermo Route-B dataset (PR/NASA/V2C2)")
        if self.fuel_liquid.thermo and not self.fuel_liquid.thermo.has_saturation_data():
            missing.append("Two-phase saturation properties for fuel line")
        if self.ox_liquid.thermo and not self.ox_liquid.thermo.has_saturation_data():
            missing.append("Two-phase saturation properties for oxidiser line")
        if self.pressurizer.UA <= 0 or self.pressurizer.wall_heat_capacity <= 0:
            missing.append("Pressurizer heat-transfer correlations from §2.5.4")
        if self.pump is None or not getattr(self.pump, "performance_data", None):
            missing.append("Centrifugal pump performance curves (表 11/12)")
        elif any(row.head == 10.0 for row in self.pump.performance_data):
            missing.append("Centrifugal pump performance curves (表 11/12)")
        if self.preburner is None or not self.preburner.state.composition:
            missing.append("Preburner chemical source terms and initial composition")
        if self.preburner_source is None:
            missing.append("Preburner chemical source terms and initial composition")
        if self.nozzle is None or self.nozzle.discharge_coeff == 1.0:
            missing.append("Nozzle discharge/heat-transfer coefficients from §2.4.2")
        if self.nozzle_cooling_area <= 0 or self.nozzle_cooling_coeff <= 0:
            missing.append("Nozzle cooling flow coefficients (§2.4.2)")
        return missing

    def step(self, dt: float, chamber_exit_pressure: Optional[float] = None) -> Dict[str, Dict[str, float]]:
        outstanding = self.missing_data()
        if outstanding:
            raise MissingPropertyData(
                "Cannot advance EngineSystem because the following items are missing: " + ", ".join(outstanding)
            )
        if self.preburner is None or self.nozzle is None:
            raise MissingPropertyData("Preburner and nozzle must be configured before calling step()")

        exit_pressure = chamber_exit_pressure or self.nozzle_exit_pressure
        summary: Dict[str, Dict[str, float]] = {}

        def _rho_mass(species: str, rho_molar: float) -> float:
            return rho_molar * _MOLAR_MASS[species]

        def _cp_mass(species: str, cp_molar: float) -> float:
            return cp_molar / _MOLAR_MASS[species]

        def _two_phase_upstream(pipe: TwoPhasePipe, plenum: TwoPhasePlenum) -> Dict[str, float]:
            thermo = pipe.thermo
            if thermo is None:
                raise MissingPropertyData("Two-phase thermo missing")
            Xi = {thermo.name: 1.0}
            cp_molar = thermo.ideal.cp_mixture(plenum.state.T, Xi)
            p_sat = thermo.saturation_pressure(plenum.state.T)
            sat = thermo.phase_equilibrium(p_sat, plenum.state.T)
            molar_mass = _MOLAR_MASS[thermo.name]
            h_liq_mass = sat["h_l_molar"] / molar_mass
            h_vap_mass = sat["h_v_molar"] / molar_mass
            rho_mass = _rho_mass(thermo.name, plenum.state.rho)
            return {
                "p": p_sat,
                "rho_mass": rho_mass,
                "cp_mass": cp_molar / molar_mass,
                "h_mass": h_liq_mass,
                "h_v_mass": h_vap_mass,
            }

        fuel_props = _two_phase_upstream(self.fuel_liquid, self.fuel_plenum)
        ox_props = _two_phase_upstream(self.ox_liquid, self.ox_plenum)

        eta_fuel = min(max(self.mix_plenum.state.p / fuel_props["p"], 1e-4), 0.999)
        eta_ox = min(max(self.mix_plenum.state.p / ox_props["p"], 1e-4), 0.999)
        psi_fuel = self.fuel_valve.psi_no_choking(eta_fuel)
        psi_ox = self.ox_valve.psi_no_choking(eta_ox)

        m_dot_fuel = self.fuel_valve.mass_flow(fuel_props["p"], fuel_props["rho_mass"], psi_fuel)
        m_dot_ox = self.ox_valve.mass_flow(ox_props["p"], ox_props["rho_mass"], psi_ox)

        summary["fuel_line"] = {"m_dot": m_dot_fuel, "p_up": fuel_props["p"], "rho": fuel_props["rho_mass"]}
        summary["ox_line"] = {"m_dot": m_dot_ox, "p_up": ox_props["p"], "rho": ox_props["rho_mass"]}

        press_fuel, main_fuel = self.pressurizer.split_fuel_flow(m_dot_fuel)
        press_ox, main_ox = self.pressurizer.split_ox_flow(m_dot_ox)

        mix_state = self.mix_plenum.state
        mix_inlet = GasState(
            p=mix_state.p,
            T=mix_state.T,
            composition=mix_state.composition.copy(),
        )
        mix_results = self.main_mix.compute_flows(mix_inlet, exit_pressure)
        m_dot_mix = mix_results["m_dot"]
        mix_state.h = mix_inlet.h
        mix_state.gamma = mix_inlet.gamma
        mix_state.cp = mix_inlet.cp
        mix_state.rho = mix_inlet.rho

        total_inlet = main_fuel + main_ox
        mix_rhs = self.mix_plenum.rhs(total_inlet, m_dot_mix, 0.0, mix_state.composition)

        summary["mix_line"] = {
            "m_dot": m_dot_mix,
            "C_q": mix_results["C_q"],
            "C_m": mix_results["C_m"],
        }

        if self.preburner_source is None:
            raise MissingPropertyData("Preburner source terms missing")

        inlet_state = GasState(
            p=self.preburner.state.p,
            T=self.preburner.state.T,
            h=mix_inlet.h,
            composition=self.preburner.state.composition.copy(),
        )
        outlet_state = GasState(
            p=self.preburner.state.p,
            T=self.preburner.state.T,
            h=mix_inlet.h,
            composition=self.preburner.state.composition.copy(),
        )
        rhs = self.preburner.rhs(
            inlets=[(m_dot_mix, inlet_state)],
            outlets=[(m_dot_mix, outlet_state)],
            source=self.preburner_source,
            Q_dot_loss=self.preburner_heat_loss,
        )
        self.preburner.state.T = max(300.0, self.preburner.state.T + rhs["dT_dt"] * dt)
        self.preburner.state.rho = max(1e-6, self.preburner.state.rho + (rhs["dm_dt"] / self.preburner.volume) * dt)
        prev_comp = self.preburner.state.composition.copy()
        for species, deriv in rhs["species"].items():
            self.preburner.state.composition[species] = max(
                0.0, self.preburner.state.composition.get(species, 0.0) + deriv * dt
            )
        total_species = sum(self.preburner.state.composition.values())
        if total_species > 0:
            for species in list(self.preburner.state.composition.keys()):
                self.preburner.state.composition[species] /= total_species
        else:
            self.preburner.state.composition = prev_comp
        self.preburner.state.h = mix_inlet.h

        summary["preburner"] = {"dT_dt": rhs["dT_dt"], "dm_dt": rhs["dm_dt"]}
        summary["mix_plenum"] = mix_rhs

        gamma = mix_inlet.gamma or 1.2
        nozzle_mass_flow = self.nozzle.mass_flow(self.preburner.state.p, self.preburner.state.T, gamma, exit_pressure)
        cooling_flow = self.nozzle.cooling_flow(
            self.preburner.state.p,
            exit_pressure,
            gamma,
            self.nozzle_cooling_area,
            self.nozzle_cooling_coeff,
        )

        summary["nozzle"] = {"m_dot": nozzle_mass_flow, "cooling_flow": cooling_flow}

        press_inputs = {
            "T_hot": mix_state.T,
            "T_cold": self.fuel_plenum.state.T,
            "T_wall": self.pressurizer.wall_temperature,
            "m_dot_hot": press_fuel + press_ox,
            "cp_hot": mix_state.cp or 1.0,
            "m_dot_cold": press_fuel,
            "cp_cold": fuel_props["cp_mass"],
            "dt": dt,
        }
        press_summary = self.pressurizer.heat_balance(press_inputs)
        summary["pressurizer"] = press_summary

        return summary


def build_default_system(props_root: str) -> EngineSystem:
    """构建 Route-A/B 混合的系统骨架，仍包含若干占位项。"""

    props_path = Path(props_root)
    gas_thermo = build_gas_mixture_thermo(
        f"{props_root}/mix_pr_demo.json",
        f"{props_root}/mix_nasa7_gri30.json",
        f"{props_root}/transport_v2c2_tm86885.json",
    )
    sat_tables = load_saturation_tables(f"{props_root}/saturation/saturation_table.json")
    # 两相物性尚缺 Table-8 系数，构建后仍会在使用时抛 MissingPropertyData。
    try:
        fuel_thermo = build_two_phase_thermo(
            "CH4",
            f"{props_root}/mbwr_placeholders/ch4_mbwr32_placeholder.json",
            f"{props_root}/mix_nasa7_gri30.json",
            saturation_table=sat_tables.get("CH4"),
        )
    except MissingPropertyData:
        fuel_thermo = None
    try:
        ox_thermo = build_two_phase_thermo(
            "O2",
            f"{props_root}/mbwr_placeholders/o2_mbwr32_placeholder.json",
            f"{props_root}/mix_nasa7_gri30.json",
            saturation_table=sat_tables.get("O2"),
        )
    except MissingPropertyData:
        ox_thermo = None

    fuel_line = TwoPhasePipe(A=1.0, k=1.0, k_dp=1.0, thermo=fuel_thermo, D=0.05, epsilon=1e-5)
    ox_line = TwoPhasePipe(A=1.0, k=1.0, k_dp=1.0, thermo=ox_thermo, D=0.05, epsilon=1e-5)
    fuel_valve = TwoPhaseValve(A=1.0, k=1.0, k_dp=1.0)
    ox_valve = TwoPhaseValve(A=1.0, k=1.0, k_dp=1.0)
    fuel_plenum = TwoPhasePlenum(volume=0.01, thermo=fuel_thermo, state=TwoPhaseState())
    ox_plenum = TwoPhasePlenum(volume=0.01, thermo=ox_thermo, state=TwoPhaseState())
    mix_pipe = MixGasPipe(A=1.0, thermo=gas_thermo)
    mix_plenum = MixGasPlenum(volume=0.02, thermo=gas_thermo, state=GasState())

    press_data = _load_json(props_path / "pressurizer" / "pressurizer_hx.json")
    pressurizer = PressurizerHX(
        UA=press_data["UA_W_per_K"],
        wall_heat_capacity=press_data["wall_heat_capacity_J_per_K"],
        wall_temperature=press_data.get("initial_wall_temperature_K", 320.0),
    )

    pump = None
    try:
        volute_coeffs = _load_json(props_path / "turbopump" / "volute_coeffs.json")
        loss_coeffs = _load_json(props_path / "turbopump" / "loss_coeffs.json")
        impeller_geom = _load_json(props_path / "turbopump" / "impeller_geometry.json")
        performance_rows = _load_csv(props_path / "turbopump" / "pump_performance.csv")
        pump = build_from_tables(
            volute_coeffs=volute_coeffs,
            area_profile=lambda tau: 0.015 + 0.002 * tau,
            wall_velocity=lambda tau: 15.0,
            relative_angle=lambda tau: 0.5,
            slip_factor=lambda v_r: 0.9,
            performance_rows=performance_rows,
            loss_coefficients=loss_coeffs,
            impeller_geometry=impeller_geom,
        )
    except MissingPropertyData:
        pump = None

    preburner_source = None
    preburner_heat_loss = 0.0
    preburner = None
    if gas_thermo is not None:
        preburner = PreburnerChamber(volume=0.02, thermo=gas_thermo)
        preburner_data = _load_json(props_path / "preburner" / "default_state.json")
        pb_state = preburner_data["state"]
        preburner.state.p = pb_state["p_Pa"]
        preburner.state.T = pb_state["T_K"]
        preburner.state.rho = pb_state["rho_kg_per_m3"]
        preburner.state.composition = pb_state["composition_mass_fractions"].copy()
        props = gas_thermo.state(preburner.state.p, preburner.state.T, preburner.state.composition)
        molar_mass = sum(_MOLAR_MASS[k] * v for k, v in preburner.state.composition.items())
        preburner.state.h = props["h_molar"] / molar_mass
        preburner_source = CombustionSource(species=preburner_data["source"]["species_mass_generation"])
        preburner_heat_loss = preburner_data["heat_loss_W"]

    nozzle_data = _load_json(props_path / "nozzle" / "nozzle_coeffs.json")
    nozzle = NozzleModel(
        geometry=NozzleGeometry(
            throat_area=nozzle_data["geometry"]["throat_area"],
            exit_area=nozzle_data["geometry"]["exit_area"],
        ),
        discharge_coeff=nozzle_data["discharge_coeff"],
        heat_transfer_coeff=nozzle_data.get("heat_transfer_coeff"),
    )

    mix_init = _load_json(props_path / "system" / "initial_conditions.json")
    fuel_init = mix_init["fuel"]
    ox_init = mix_init["oxidizer"]
    mix_state_init = mix_init["mix_plenum"]
    fuel_plenum.state.T = fuel_init["T_K"]
    fuel_plenum.state.rho = fuel_init["rho_mol_per_m3"]
    ox_plenum.state.T = ox_init["T_K"]
    ox_plenum.state.rho = ox_init["rho_mol_per_m3"]
    mix_plenum.state.p = mix_state_init["p_Pa"]
    mix_plenum.state.T = mix_state_init["T_K"]
    mix_plenum.state.rho = mix_state_init["rho_kg_per_m3"]
    if preburner is not None:
        mix_plenum.state.composition = preburner.state.composition.copy()

    nozzle_cooling = nozzle_data.get("cooling", {"area": 0.0, "coeff": 0.0})

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
        preburner_source=preburner_source,
        preburner_heat_loss=preburner_heat_loss,
        nozzle_exit_pressure=nozzle_data.get("exit_pressure_Pa", 5.0e4),
        nozzle_cooling_area=nozzle_cooling.get("area", 0.0),
        nozzle_cooling_coeff=nozzle_cooling.get("coeff", 0.0),
    )


def _load_json(path: Path) -> Dict[str, float]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> List[Dict[str, float]]:
    import csv

    rows: List[Dict[str, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({key: float(value) for key, value in row.items()})
    return rows
