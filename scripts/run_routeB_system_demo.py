"""Run a coarse system-level simulation using the approximate Route-B dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ffsc.chapter_2.section_2_6_system.system import build_default_system


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--props-root", default="data/props", type=Path, help="Directory containing Route-B JSON/CSV files")
    parser.add_argument("--steps", type=int, default=10, help="Number of integration steps")
    parser.add_argument("--dt", type=float, default=0.05, help="Time step passed into EngineSystem.step")
    parser.add_argument("--summary", action="store_true", help="Print the final step dictionary as formatted JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    system = build_default_system(str(args.props_root))
    history = []
    for step in range(args.steps):
        result = system.step(args.dt)
        print(
            f"Step {step + 1}/{args.steps}: "
            f"fuel m_dot={result['fuel_line']['m_dot']:.2f} kg/s, "
            f"mix m_dot={result['mix_line']['m_dot']:.2f} kg/s"
        )
        history.append(result)
    if args.summary:
        print(json.dumps(history[-1], indent=2))


if __name__ == "__main__":
    main()
