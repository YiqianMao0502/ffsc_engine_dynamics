#!/usr/bin/env python
"""Regenerate Route-B saturation tables using CoolProp HEOS data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

try:
    from CoolProp.CoolProp import PropsSI
except ImportError as exc:  # pragma: no cover - requires optional dependency
    raise SystemExit(
        "CoolProp is required to rebuild the saturation table. Install it with 'pip install CoolProp'."
    ) from exc

SPECIES_GRID: Dict[str, List[float]] = {
    "CH4": [100, 110, 120, 130, 140, 150, 160, 170, 180],
    "O2": [90, 95, 100, 110, 120, 130, 140, 150],
}
MOLAR_MASS = {"CH4": 0.016043, "O2": 0.031998}


def sample_species(name: str, temps: List[float]) -> List[Dict[str, float]]:
    mm = MOLAR_MASS[name]
    out: List[Dict[str, float]] = []
    for T in temps:
        p_bar = PropsSI("P", "T", T, "Q", 0, name) / 1e5
        rho_l = PropsSI("D", "T", T, "Q", 0, name)
        rho_v = PropsSI("D", "T", T, "Q", 1, name)
        h_l = PropsSI("H", "T", T, "Q", 0, name)
        h_v = PropsSI("H", "T", T, "Q", 1, name)
        out.append(
            {
                "T_K": round(T, 3),
                "p_bar": round(p_bar, 5),
                "rho_l_mol_per_m3": rho_l / mm,
                "rho_v_mol_per_m3": rho_v / mm,
                "h_l_kJ_per_mol": h_l * mm / 1000.0,
                "h_v_kJ_per_mol": h_v * mm / 1000.0,
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=Path("data/props/saturation/saturation_table.json"),
        type=Path,
        help="Target JSON file",
    )
    args = parser.parse_args()

    payload = {
        "metadata": {
            "route": "Route-B",
            "description": "Saturation envelopes sampled from CoolProp 6.6.0 (HEOS).",
            "source": "CoolProp 6.6.0 (https://coolprop.org)",
        },
        "species": {},
    }
    for name, temps in SPECIES_GRID.items():
        payload["species"][name] = sample_species(name, temps)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
