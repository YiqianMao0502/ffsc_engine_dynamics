"""Compare pump model outputs against digitized thesis figures."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "src"))

from ffsc.chapter_2.section_2_3_turbopump import CentrifugalPump, build_from_tables  # type: ignore
from scripts.digitize_figures import digitize_figure21, digitize_figure23


GRAVITY = 9.81
DENSITY_LOX = 1140.0


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> Iterable[Dict[str, float]]:
    import csv

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def _build_routeb_pump(props_root: Path) -> CentrifugalPump:
    volute_coeffs = _load_json(props_root / "turbopump" / "volute_coeffs.json")
    loss_coeffs = _load_json(props_root / "turbopump" / "loss_coeffs.json")
    impeller_geom = _load_json(props_root / "turbopump" / "impeller_geometry.json")
    performance_rows = list(_load_csv(props_root / "turbopump" / "pump_performance.csv"))

    def area_profile(tau: float) -> float:
        return 0.015 + 0.002 * tau

    def wall_velocity(_: float) -> float:
        return 15.0

    def relative_angle(_: float) -> float:
        return 0.5

    return build_from_tables(
        volute_coeffs=volute_coeffs,
        area_profile=area_profile,
        wall_velocity=wall_velocity,
        relative_angle=relative_angle,
        slip_factor=lambda v_r: 0.9,
        performance_rows=performance_rows,
        loss_coefficients=loss_coeffs,
        impeller_geometry=impeller_geom,
    )


def _map_range(values: np.ndarray, src: Tuple[float, float], dst: Tuple[float, float]) -> np.ndarray:
    src_min, src_max = src
    dst_min, dst_max = dst
    return dst_min + (values - src_min) / (src_max - src_min) * (dst_max - dst_min)


def _rmse_aligned(reference: np.ndarray, prediction: np.ndarray) -> Tuple[float, float, float]:
    A = np.vstack([prediction, np.ones_like(prediction)]).T
    scale, bias = np.linalg.lstsq(A, reference, rcond=None)[0]
    aligned = scale * prediction + bias
    err = np.sqrt(np.mean((aligned - reference) ** 2))
    return err, scale, bias


def _compare_figure23(pump: CentrifugalPump, data_path: Path, axis_meta: Path) -> Dict:
    df = pd.read_csv(data_path)
    axis = _load_json(axis_meta)
    fig_flow_bounds = (axis["flow_min"], axis["flow_max"])
    fig_head_bounds = (axis["head_min"], axis["head_max"])
    pump_flow_bounds = pump.flow_limits()
    pump_head_bounds = pump.head_limits()
    if pump_flow_bounds is None or pump_head_bounds is None:
        raise RuntimeError("Pump lacks performance data")

    summary = {}
    for rpm in sorted(df["rpm"].unique()):
        subset = df[df["series"] == f"{int(rpm)}_simulation"]
        flows = subset["flow_kg_s"].to_numpy()
        heads = subset["head_m"].to_numpy()
        mapped_flows = _map_range(flows, fig_flow_bounds, pump_flow_bounds)
        predicted = np.array([pump.predict_head(rpm, f) for f in mapped_flows])
        rmse, scale, bias = _rmse_aligned(heads, predicted)
        summary[int(rpm)] = {
            "rmse_m": float(rmse),
            "scale": float(scale),
            "bias": float(bias),
            "avg_head_figure": float(np.mean(heads)),
            "avg_head_model": float(np.mean(predicted)),
        }
    return summary


def _dimensionless_curves(pump: CentrifugalPump, speed: float, flows: np.ndarray) -> Dict[str, np.ndarray]:
    head = np.array([pump.predict_head(speed, f) for f in flows])
    eff = np.clip(np.array([pump.predict_efficiency(speed, f) for f in flows]), 1e-3, None)
    geom = pump.impeller.geometry
    diameter = 2.0 * geom.r_out
    omega = 2.0 * math.pi * speed / 60.0
    Q = flows / DENSITY_LOX
    phi = Q / (omega * diameter**3)
    psi = GRAVITY * head / (omega**2 * diameter**2)
    power = flows * GRAVITY * head / eff
    torque = power / omega
    tau = torque / (DENSITY_LOX * omega**2 * diameter**5)
    return {"theta": phi, "WH": psi, "WT": tau}


def _compare_figure21(pump: CentrifugalPump, data_path: Path) -> Dict:
    data = _load_json(data_path)
    pump_flow_bounds = pump.flow_limits()
    if pump_flow_bounds is None:
        raise RuntimeError("Pump lacks performance data")
    flows = np.linspace(pump_flow_bounds[0], pump_flow_bounds[1], 200)
    results = {}
    speed_map = {
        "WH_front": 26000.0,
        "WH_back": 34000.0,
        "WT_front": 26000.0,
        "WT_back": 34000.0,
    }
    for key, series in data.items():
        fig_theta = np.array(series["theta"], dtype=float)
        fig_value = np.array(series["value"], dtype=float)
        if fig_theta.size == 0:
            continue
        curves = _dimensionless_curves(pump, speed_map.get(key, 30000.0), flows)
        theta_pred = curves["theta"]
        quantity = curves["WH" if key.startswith("WH") else "WT"]
        order = np.argsort(theta_pred)
        pred_interp = np.interp(fig_theta, theta_pred[order], quantity[order])
        rmse, scale, bias = _rmse_aligned(fig_value, pred_interp)
        results[key] = {
            "rmse": float(rmse),
            "scale": float(scale),
            "bias": float(bias),
        }
    return results


def _plot_figure23(
    df: pd.DataFrame,
    pump: CentrifugalPump,
    axis_meta: Dict[str, float],
    plot_dir: Path,
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 5))
    fig_flow_bounds = (axis_meta["flow_min"], axis_meta["flow_max"])
    pump_flow_bounds = pump.flow_limits()
    if pump_flow_bounds is None:
        raise RuntimeError("Pump lacks performance data")
    for rpm in sorted(df["rpm"].unique()):
        subset = df[df["series"] == f"{int(rpm)}_simulation"]
        flows_fig = subset["flow_kg_s"].to_numpy()
        mapped_flows = _map_range(flows_fig, fig_flow_bounds, pump_flow_bounds)
        heads_fig = subset["head_m"].to_numpy()
        predicted = np.array([pump.predict_head(rpm, f) for f in mapped_flows])
        ax.plot(flows_fig, heads_fig, linestyle="--", marker="o", label=f"{int(rpm)} rpm digitized")
        ax.plot(flows_fig, predicted, marker="x", label=f"{int(rpm)} rpm model")
    ax.set_xlabel("Flow (kg/s)")
    ax.set_ylabel("Head (m)")
    ax.set_title("Figure 23 comparison: digitized vs. model")
    ax.grid(True, linestyle=":", linewidth=0.5)
    ax.legend(ncol=2, fontsize="small")
    plot_dir.mkdir(parents=True, exist_ok=True)
    out_path = plot_dir / "figure23_overlay.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def _plot_figure21(data: Dict, pump: CentrifugalPump, plot_dir: Path) -> Path:
    flows = np.linspace(*(pump.flow_limits() or (0.1, 1.0)), 200)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=False)
    panels = [("WH", axes[0], "Head coefficient"), ("WT", axes[1], "Torque coefficient")]
    speed_map = {
        "WH_front": 26000.0,
        "WH_back": 34000.0,
        "WT_front": 26000.0,
        "WT_back": 34000.0,
    }
    for prefix, ax, ylabel in panels:
        for suffix in ("front", "back"):
            key = f"{prefix}_{suffix}"
            series = data.get(key)
            if not series:
                continue
            fig_theta = np.array(series["theta"], dtype=float)
            fig_value = np.array(series["value"], dtype=float)
            curves = _dimensionless_curves(pump, speed_map.get(key, 30000.0), flows)
            theta_pred = curves["theta"]
            quantity = curves["WH" if prefix == "WH" else "WT"]
            order = np.argsort(theta_pred)
            pred_interp = np.interp(fig_theta, theta_pred[order], quantity[order])
            label = f"{suffix} digitized"
            ax.plot(fig_theta, fig_value, linestyle="--", marker="o", label=label)
            ax.plot(fig_theta, pred_interp, marker="x", label=f"{suffix} model")
        ax.set_xlabel("θ")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Figure 21 – {prefix}")
        ax.grid(True, linestyle=":", linewidth=0.5)
        ax.legend(fontsize="small")
    plot_dir.mkdir(parents=True, exist_ok=True)
    out_path = plot_dir / "figure21_overlay.png"
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare pump model to digitized thesis figures")
    parser.add_argument("--props", type=Path, default=Path("data/props"), help="Property root directory")
    parser.add_argument("--validation", type=Path, default=Path("data/validation"), help="Validation data dir")
    parser.add_argument("--figure21", type=Path, default=Path("external/thesis_figures/figure21_whn_wtn.png"))
    parser.add_argument("--figure23", type=Path, default=Path("external/thesis_figures/figure23_pump_head.png"))
    parser.add_argument("--digitize", action="store_true", help="Regenerate digitized datasets before comparing")
    parser.add_argument("--plot-dir", type=Path, default=Path("docs/images/validation"), help="Directory to store overlay plots")
    args = parser.parse_args()

    args.validation.mkdir(parents=True, exist_ok=True)
    if args.digitize:
        digitize_figure23(
            args.figure23,
            args.validation / "figure23_digitized.csv",
            args.validation / "figure23_axes.json",
        )
        digitize_figure21(args.figure21, args.validation / "figure21_cross_sections.json")

    pump = _build_routeb_pump(args.props)
    fig23_summary = _compare_figure23(
        pump,
        args.validation / "figure23_digitized.csv",
        args.validation / "figure23_axes.json",
    )
    fig21_summary = _compare_figure21(pump, args.validation / "figure21_cross_sections.json")

    overlay23 = _plot_figure23(
        pd.read_csv(args.validation / "figure23_digitized.csv"),
        pump,
        _load_json(args.validation / "figure23_axes.json"),
        args.plot_dir,
    )
    overlay21 = _plot_figure21(
        _load_json(args.validation / "figure21_cross_sections.json"),
        pump,
        args.plot_dir,
    )

    print("Figure 23 comparison (RMSE in meters):")
    for rpm, stats in fig23_summary.items():
        print(f"  {rpm} rpm → RMSE={stats['rmse_m']:.2f} m (scale={stats['scale']:.3f}, bias={stats['bias']:.2f})")
    print("\nFigure 21 cross-section comparison (normalized RMSE):")
    for key, stats in fig21_summary.items():
        print(f"  {key}: RMSE={stats['rmse']:.3f} (scale={stats['scale']:.3f}, bias={stats['bias']:.3f})")

    print(f"\nOverlay plots saved to: {overlay23} and {overlay21}")


if __name__ == "__main__":
    main()
