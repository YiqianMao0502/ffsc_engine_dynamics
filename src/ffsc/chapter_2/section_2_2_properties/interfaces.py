"""Aggregated thermodynamic interfaces that bridge §2.2 models with §2.5 components."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, sqrt
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union

from ffsc.common.exceptions import MissingPropertyData

from .impl.loader import load_eos_from_json
from .impl.nasa7_model import NASA7Mixture
from .impl.transport_mixers import mason_saxena_lambda, wilke_viscosity

R_UNIVERSAL = 8.314462618  # J/mol/K
_BAR_TO_PA = 1e5
_MOL_PER_L_TO_MOL_PER_M3 = 1000.0
_BARL_PER_MOL_TO_J_PER_MOL = _BAR_TO_PA * 1e-3


_MOLAR_MASS = {
    "CH4": 16.043e-3,
    "O2": 31.998e-3,
    "H2O": 18.01528e-3,
    "CO": 28.0101e-3,
    "CO2": 44.0095e-3,
    "H2": 2.01588e-3,
    "H": 1.00794e-3,
    "OH": 17.007e-3,
    "O": 15.999e-3,
    "HO2": 33.006e-3,
}


@dataclass
class V2C2Segment:
    T_min: float
    T_max: float
    A: float
    B: float
    C: float
    D: float

    def evaluate(self, T: float) -> float:
        if not (self.T_min <= T <= self.T_max):
            raise ValueError(f"Temperature {T} K outside [{self.T_min}, {self.T_max}] K segment range")
        ln_val = self.A * log(T) + self.B + self.C / T + self.D / (T * T)
        return exp(ln_val)


@dataclass
class V2C2Species:
    name: str
    mu_segments: List[V2C2Segment]
    k_segments: List[V2C2Segment]

    def mu(self, T: float) -> float:
        for seg in self.mu_segments:
            if seg.T_min <= T <= seg.T_max:
                return seg.evaluate(T)
        raise ValueError(f"No viscosity segment covering {T} K for species {self.name}")

    def k(self, T: float) -> float:
        for seg in self.k_segments:
            if seg.T_min <= T <= seg.T_max:
                return seg.evaluate(T)
        raise ValueError(f"No conductivity segment covering {T} K for species {self.name}")


def _load_v2c2_table(json_path: Path) -> Dict[str, V2C2Species]:
    import json

    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    params = raw["params"]
    table: Dict[str, V2C2Species] = {}
    for name, entry in params["species"].items():
        mu_segments = [V2C2Segment(**seg) for seg in entry["mu"]]
        k_segments = [V2C2Segment(**seg) for seg in entry["k"]]
        table[name] = V2C2Species(name=name, mu_segments=mu_segments, k_segments=k_segments)
    return table


@dataclass
class PengRobinsonSpecies:
    name: str
    Tc: float
    Pc: float
    omega: float

    def kappa(self) -> float:
        return 0.37464 + 1.54226 * self.omega - 0.26992 * self.omega * self.omega

    def a_c(self) -> float:
        return 0.45724 * (R_UNIVERSAL * self.Tc) ** 2 / self.Pc

    def b_c(self) -> float:
        return 0.07780 * (R_UNIVERSAL * self.Tc) / self.Pc


@dataclass
class PengRobinsonMixture:
    species: List[PengRobinsonSpecies]
    binary_kij: Mapping[Tuple[int, int], float]

    @staticmethod
    def from_params(params: Mapping[str, Iterable]) -> "PengRobinsonMixture":
        species = [PengRobinsonSpecies(name=sp["name"], Tc=float(sp["Tc"]), Pc=float(sp["Pc"]), omega=float(sp["omega"])) for sp in params["species"]]
        kij_data = params.get("binary_interaction", {})
        kij: Dict[Tuple[int, int], float] = {}
        for (i_name, j_name), value in kij_data.items():
            i = next(idx for idx, sp in enumerate(species) if sp.name == i_name)
            j = next(idx for idx, sp in enumerate(species) if sp.name == j_name)
            kij[(i, j)] = kij[(j, i)] = float(value)
        return PengRobinsonMixture(species=species, binary_kij=kij)

    def _alphas(self, T: float) -> List[float]:
        alphas: List[float] = []
        for sp in self.species:
            kappa = sp.kappa()
            Tr = T / sp.Tc
            alpha = (1.0 + kappa * (1.0 - sqrt(Tr))) ** 2
            alphas.append(alpha)
        return alphas

    def a_i(self, T: float) -> List[float]:
        alphas = self._alphas(T)
        return [sp.a_c() * alpha for sp, alpha in zip(self.species, alphas)]

    def b_i(self) -> List[float]:
        return [sp.b_c() for sp in self.species]

    def mixture_a(self, T: float, Xi: List[float]) -> float:
        a_i = self.a_i(T)
        a_mix = 0.0
        for i, a_i_val in enumerate(a_i):
            for j, a_j_val in enumerate(a_i):
                kij = self.binary_kij.get((i, j), 0.0)
                a_mix += Xi[i] * Xi[j] * sqrt(a_i_val * a_j_val) * (1.0 - kij)
        return a_mix

    def mixture_b(self, Xi: List[float]) -> float:
        b_i = self.b_i()
        return sum(Xi[i] * b_i[i] for i in range(len(b_i)))

    def density(self, p: float, T: float, Xi: List[float]) -> float:
        """Return molar density [mol/m^3] using the real gas PR cubic."""

        a_mix = self.mixture_a(T, Xi)
        b_mix = self.mixture_b(Xi)

        A = a_mix * p / (R_UNIVERSAL ** 2 * T ** 2)
        B = b_mix * p / (R_UNIVERSAL * T)

        coeff_a = -(1.0 - B)
        coeff_b = A - 3.0 * B * B - 2.0 * B
        coeff_c = -(A * B - B * B - B ** 3)

        roots = _solve_cubic_real(coeff_a, coeff_b, coeff_c)
        if not roots:
            raise RuntimeError("No real compressibility root for PR mixture")
        Z = max(roots)
        v = Z * R_UNIVERSAL * T / p
        if v <= 0:
            raise RuntimeError("Computed non-positive specific volume from PR cubic")
        rho_molar = 1.0 / v
        return rho_molar


def _solve_cubic_real(a: float, b: float, c: float) -> List[float]:
    """Solve z^3 + a z^2 + b z + c = 0 and return all real roots."""

    import cmath
    import math

    p = b - a * a / 3.0
    q = (2.0 * a ** 3) / 27.0 - (a * b) / 3.0 + c
    discriminant = (q / 2.0) ** 2 + (p / 3.0) ** 3

    roots: List[float] = []
    if discriminant >= 0.0:
        sqrt_disc = cmath.sqrt(discriminant)
        u = (-q / 2.0 + sqrt_disc) ** (1.0 / 3.0)
        v = (-q / 2.0 - sqrt_disc) ** (1.0 / 3.0)
        root = u + v - a / 3.0
        roots.append(root.real)
    else:
        r = math.sqrt(-p ** 3 / 27.0)
        phi = math.acos(max(-1.0, min(1.0, -q / (2.0 * r))))
        m = 2.0 * math.sqrt(-p / 3.0)
        roots.append(m * math.cos(phi / 3.0) - a / 3.0)
        roots.append(m * math.cos((phi + 2.0 * math.pi) / 3.0) - a / 3.0)
        roots.append(m * math.cos((phi + 4.0 * math.pi) / 3.0) - a / 3.0)
    return roots


@dataclass
class GasMixtureThermo:
    """Aggregate PR + NASA7 + V2C2 properties for Route-B mixtures."""

    pr: PengRobinsonMixture
    nasa: NASA7Mixture
    transport: Dict[str, V2C2Species]

    def _normalize_X(self, composition: Mapping[str, float]) -> Tuple[List[float], List[str]]:
        names = [sp.name for sp in self.pr.species]
        Xi = [float(composition.get(name, 0.0)) for name in names]
        total = sum(Xi)
        if total <= 0.0:
            raise ValueError("Mixture composition contains no supported species")
        Xi = [x / total for x in Xi]
        return Xi, names

    def _molar_mass(self, Xi: List[float], names: List[str]) -> float:
        return sum(Xi[i] * _MOLAR_MASS[names[i]] for i in range(len(names)))

    def state(self, p: float, T: float, composition: Mapping[str, float]) -> Dict[str, float]:
        Xi, names = self._normalize_X(composition)
        rho_molar = self.pr.density(p, T, Xi)
        rho_mass = rho_molar * self._molar_mass(Xi, names)

        mixture_X = {name: comp for name, comp in zip(names, Xi)}
        thermo = self.nasa.cp_mixture(T, mixture_X)
        h = self.nasa.h_mixture(T, mixture_X)
        s = self.nasa.s_mixture(T, mixture_X)
        cp_molar = thermo
        cv_molar = cp_molar - R_UNIVERSAL
        gamma = cp_molar / cv_molar if cv_molar != 0 else float("nan")

        mu_i = []
        lam_i = []
        for name in names:
            species = self.transport.get(name)
            if species is None:
                raise MissingPropertyData(f"No V2C2 transport data for species '{name}'")
            mu_i.append(species.mu(T))
            lam_i.append(species.k(T))
        mu_mix = wilke_viscosity(Xi, mu_i, [_MOLAR_MASS[n] for n in names])
        lam_mix = mason_saxena_lambda(Xi, lam_i, [_MOLAR_MASS[n] for n in names])

        return {
            "rho_molar": rho_molar,
            "rho_mass": rho_mass,
            "cp_molar": cp_molar,
            "cv_molar": cv_molar,
            "h_molar": h,
            "s_molar": s,
            "gamma": gamma,
            "mu": mu_mix,
            "lambda": lam_mix,
        }


@dataclass
class SaturationPoint:
    T_K: float
    p_bar: float
    rho_l_mol_per_m3: float
    rho_v_mol_per_m3: float
    h_l_kJ_per_mol: Optional[float] = None
    h_v_kJ_per_mol: Optional[float] = None


class SaturationTable:
    def __init__(self, species: str, points: List[SaturationPoint]):
        if len(points) < 2:
            raise ValueError("Saturation table requires at least two points for interpolation")
        self.species = species
        self.points = sorted(points, key=lambda pt: pt.T_K)

    def _interp(self, T: float, attr: str) -> float:
        pts = self.points
        if T <= pts[0].T_K:
            value = getattr(pts[0], attr)
            if value is None:
                raise MissingPropertyData(f"Saturation table for {self.species} missing '{attr}' data")
            return value
        if T >= pts[-1].T_K:
            value = getattr(pts[-1], attr)
            if value is None:
                raise MissingPropertyData(f"Saturation table for {self.species} missing '{attr}' data")
            return value
        for low, high in zip(pts, pts[1:]):
            if low.T_K <= T <= high.T_K:
                span = high.T_K - low.T_K
                w = (T - low.T_K) / span if span > 0 else 0.0
                low_val = getattr(low, attr)
                high_val = getattr(high, attr)
                if low_val is None or high_val is None:
                    raise MissingPropertyData(
                        f"Saturation table for {self.species} missing '{attr}' data in interpolation window"
                    )
                return low_val * (1.0 - w) + high_val * w
        raise ValueError("Temperature interpolation failed")

    def pressure_bar(self, T: float) -> float:
        return self._interp(T, "p_bar")

    def rho_liquid(self, T: float) -> float:
        return self._interp(T, "rho_l_mol_per_m3")

    def rho_vapor(self, T: float) -> float:
        return self._interp(T, "rho_v_mol_per_m3")

    def h_liquid_kJ_per_mol(self, T: float) -> float:
        return self._interp(T, "h_l_kJ_per_mol")

    def h_vapor_kJ_per_mol(self, T: float) -> float:
        return self._interp(T, "h_v_kJ_per_mol")


@dataclass
class TwoPhaseThermo:
    """Wrapper that couples mBWR residuals with ideal-gas add-ons for Route-A/B."""

    name: str
    eos: object
    ideal: Optional[NASA7Mixture]
    saturation: Optional[SaturationTable] = None

    def state(self, T: float, rho_mol_per_m3: float) -> Dict[str, float]:
        if getattr(self.eos, "__class__", None) is None:
            raise RuntimeError("Invalid EOS instance passed to TwoPhaseThermo")
        # Convert rho back to mol/L for EOS call
        rho_input = rho_mol_per_m3 / _MOL_PER_L_TO_MOL_PER_M3
        try:
            eval_out = self.eos.evaluate(T, rho_input)
        except TypeError as exc:
            raise MissingPropertyData(
                f"mBWR coefficients for {self.name} are incomplete; provide Table-8 parameters to evaluate Route-A state"
            ) from exc
        residual = eval_out["residual"]

        p_bar = eval_out["p"]
        p = p_bar * _BAR_TO_PA
        u_res = residual["u"] * _BARL_PER_MOL_TO_J_PER_MOL
        h_res = residual["h"] * _BARL_PER_MOL_TO_J_PER_MOL
        s_res = residual["s"] * _BARL_PER_MOL_TO_J_PER_MOL
        cv_res = residual["cv"] * _BARL_PER_MOL_TO_J_PER_MOL
        cp_res = residual["cp"] * _BARL_PER_MOL_TO_J_PER_MOL
        derivatives = eval_out.get("derivatives", {})
        dp_dT = derivatives.get("dp_dT_rho")
        dp_drho = derivatives.get("dp_drho_T")
        du_dT_rho = derivatives.get("du_dT_rho_res")
        du_drho_T = derivatives.get("du_drho_T_res")
        converted_derivatives = {}
        if dp_dT is not None:
            converted_derivatives["dp_dT_rho"] = dp_dT * _BAR_TO_PA
        if dp_drho is not None:
            converted_derivatives["dp_drho_T"] = dp_drho * _BAR_TO_PA / _MOL_PER_L_TO_MOL_PER_M3
        if du_dT_rho is not None:
            converted_derivatives["du_dT_rho"] = du_dT_rho * _BARL_PER_MOL_TO_J_PER_MOL
        if du_drho_T is not None:
            converted_derivatives["du_drho_T"] = du_drho_T * _BARL_PER_MOL_TO_J_PER_MOL / _MOL_PER_L_TO_MOL_PER_M3

        ideal_add = {"cp": 0.0, "h": 0.0, "s": 0.0}
        if self.ideal is not None:
            Xi = {self.name: 1.0}
            try:
                ideal_add["cp"] = self.ideal.cp_mixture(T, Xi)
                ideal_add["h"] = self.ideal.h_mixture(T, Xi)
                ideal_add["s"] = self.ideal.s_mixture(T, Xi)
            except ValueError as exc:
                raise MissingPropertyData(
                    f"NASA-7 dataset does not contain species '{self.name}' for ideal contributions"
                ) from exc
        else:
            raise MissingPropertyData(
                f"Ideal-gas contribution for {self.name} missing; provide NASA-7 data to complete thermodynamic state"
            )

        cp_total = ideal_add["cp"] + cp_res
        cv_total = (ideal_add["cp"] - R_UNIVERSAL) + cv_res

        h_total = ideal_add["h"] + h_res
        u_total = h_total - p / rho_mol_per_m3 if rho_mol_per_m3 != 0 else float("nan")

        return {
            "p": p,
            "rho_molar": rho_mol_per_m3,
            "h_molar": h_total,
            "u_molar": u_total,
            "s_molar": ideal_add["s"] + s_res,
            "cp_molar": cp_total,
            "cv_molar": cv_total,
            "residual": residual,
            "derivatives": converted_derivatives,
        }

    def has_saturation_data(self) -> bool:
        return self.saturation is not None

    def saturation_pressure(self, T: float) -> float:
        if self.saturation is None:
            raise MissingPropertyData("Saturation curve data not yet supplied for TwoPhaseThermo")
        return self.saturation.pressure_bar(T) * _BAR_TO_PA

    def phase_equilibrium(self, p: float, T: float) -> Dict[str, float]:
        if self.saturation is None:
            raise MissingPropertyData("Phase-equilibrium solver requires vapor/liquid coexistence data from the thesis")
        h_l = self.saturation.h_liquid_kJ_per_mol(T)
        h_v = self.saturation.h_vapor_kJ_per_mol(T)
        return {
            "p_sat": self.saturation.pressure_bar(T) * _BAR_TO_PA,
            "rho_l": self.saturation.rho_liquid(T),
            "rho_v": self.saturation.rho_vapor(T),
            "h_l_molar": h_l * 1000.0,
            "h_v_molar": h_v * 1000.0,
        }


def _coerce_path(path: Union[str, Path]) -> Path:
    return path if isinstance(path, Path) else Path(path)


def build_gas_mixture_thermo(
    pr_json: Union[str, Path],
    nasa_json: Union[str, Path],
    transport_json: Union[str, Path],
) -> GasMixtureThermo:
    import json

    pr_data = json.loads(_coerce_path(pr_json).read_text(encoding="utf-8"))
    pr_params = pr_data.get("params", pr_data)
    pr_mixture = PengRobinsonMixture.from_params(pr_params)

    nasa_obj = load_eos_from_json(str(_coerce_path(nasa_json)))
    if not isinstance(nasa_obj, NASA7Mixture):
        raise TypeError("NASA JSON did not yield a NASA7Mixture instance")

    transport_table = _load_v2c2_table(_coerce_path(transport_json))

    return GasMixtureThermo(pr=pr_mixture, nasa=nasa_obj, transport=transport_table)


def build_two_phase_thermo(
    species_name: str,
    mbwr_json: Union[str, Path],
    nasa_json: Union[str, Path],
    saturation_table: Optional[SaturationTable] = None,
) -> TwoPhaseThermo:
    try:
        eos = load_eos_from_json(str(_coerce_path(mbwr_json)))
    except (TypeError, ValueError) as exc:
        raise MissingPropertyData(
            f"MBWR dataset at {mbwr_json} is incomplete; supply full Table-8 coefficients"
        ) from exc
    nasa_obj = load_eos_from_json(str(_coerce_path(nasa_json)))
    if not isinstance(nasa_obj, NASA7Mixture):
        raise TypeError("NASA JSON did not yield a NASA7Mixture instance")
    return TwoPhaseThermo(name=species_name, eos=eos, ideal=nasa_obj, saturation=saturation_table)


def load_saturation_tables(json_path: Union[str, Path]) -> Dict[str, SaturationTable]:
    import json

    raw = json.loads(_coerce_path(json_path).read_text(encoding="utf-8"))
    tables: Dict[str, SaturationTable] = {}
    for species, rows in raw.get("species", {}).items():
        points = [
            SaturationPoint(
                T_K=float(row["T_K"]),
                p_bar=float(row["p_bar"]),
                rho_l_mol_per_m3=float(row["rho_l_mol_per_m3"]),
                rho_v_mol_per_m3=float(row["rho_v_mol_per_m3"]),
                h_l_kJ_per_mol=row.get("h_l_kJ_per_mol"),
                h_v_kJ_per_mol=row.get("h_v_kJ_per_mol"),
            )
            for row in rows
        ]
        tables[species] = SaturationTable(species, points)
    return tables
