#!/usr/bin/env python
"""Regenerate the Route-B preburner state using Cantera equilibrium calculations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

try:
    import cantera as ct
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit("Install cantera (pip install cantera) to rebuild preburner data.") from exc

G0 = 9.80665
SUPPORTED_SPECIES = {
    "CH4": ("CH4",),
    "O2": ("O2", "O", "HO2"),
    "H2": ("H2",),
    "CO": ("CO",),
    "CO2": ("CO2",),
    "H2O": ("H2O", "OH"),
}


def _collapse_supported(composition: Dict[str, float]) -> Dict[str, float]:
    collapsed = {key: 0.0 for key in SUPPORTED_SPECIES}
    for species, frac in composition.items():
        target = None
        for key, aliases in SUPPORTED_SPECIES.items():
            if species == key or species in aliases:
                target = key
                break
        if target is not None:
            collapsed[target] += frac
    total = sum(collapsed.values())
    if total <= 0:
        raise ValueError("Collapsed composition lost all mass fractions")
    return {key: value / total for key, value in collapsed.items() if value > 0}


def build_payload(
    thrust_newton: float,
    isp_s: float,
    chamber_pressure: float,
    mixture_ratio: float,
    phi: float,
    inlet_temperature: float,
) -> Dict[str, object]:
    mdot = thrust_newton / (isp_s * G0)
    gas = ct.Solution("gri30.yaml")
    gas.TP = inlet_temperature, chamber_pressure
    gas.set_equivalence_ratio(phi, fuel="CH4", oxidizer="O2:1.0")
    gas.equilibrate("HP")
    raw_composition = {name: frac for name, frac in zip(gas.species_names, gas.Y) if frac > 1e-4}
    composition = _collapse_supported(raw_composition)

    y_fuel_in = 1.0 / (1.0 + mixture_ratio)
    y_ox_in = mixture_ratio / (1.0 + mixture_ratio)
    species_gen = {name: frac * mdot for name, frac in composition.items()}
    species_gen["CH4"] = species_gen.get("CH4", 0.0) - y_fuel_in * mdot
    species_gen["O2"] = species_gen.get("O2", 0.0) - y_ox_in * mdot

    return {
        "metadata": {
            "route": "Route-B",
            "description": "Cantera HP equilibrium for an oxygen-rich CH4/O2 preburner tied to Raptor thrust/Isp targets.",
            "source": [
                "https://github.com/KSP-RO/RealismOverhaul/blob/master/GameData/RealismOverhaul/Engine_Configs/Raptor_Config.cfg",
                "Cantera 3.0.0 (gri30.yaml)",
            ],
        },
        "state": {
            "p_Pa": chamber_pressure,
            "T_K": gas.T,
            "rho_kg_per_m3": gas.density,
            "composition_mass_fractions": composition,
        },
        "heat_loss_W": 1.5e6,
        "source": {
            "species_mass_generation": {name: round(value, 3) for name, value in species_gen.items()},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/props/preburner/default_state.json"))
    parser.add_argument("--thrust", type=float, default=2.2555295e6, help="Design thrust (N)")
    parser.add_argument("--isp", type=float, default=347.0, help="Design vacuum Isp (s)")
    parser.add_argument("--pressure", type=float, default=30e6, help="Chamber pressure (Pa)")
    parser.add_argument("--mixture-ratio", type=float, default=3.55, help="Overall O/F ratio")
    parser.add_argument("--phi", type=float, default=0.3, help="Equivalence ratio for the preburner")
    parser.add_argument("--Tin", type=float, default=300.0, help="Inlet mixture temperature (K)")
    args = parser.parse_args()

    payload = build_payload(
        thrust_newton=args.thrust,
        isp_s=args.isp,
        chamber_pressure=args.pressure,
        mixture_ratio=args.mixture_ratio,
        phi=args.phi,
        inlet_temperature=args.Tin,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
