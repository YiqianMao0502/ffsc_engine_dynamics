"""Digitize thesis figures 21 & 23 for validation."""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import cv2  # type: ignore
import numpy as np


@dataclass
class AxisMap:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    flow_min: float
    flow_max: float
    head_min: float
    head_max: float

    @property
    def x_span(self) -> float:
        return self.x_max - self.x_min

    @property
    def y_span(self) -> float:
        return self.y_max - self.y_min

    def to_physical(self, xs: np.ndarray, ys: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        flows = self.flow_min + (xs - self.x_min) / self.x_span * (self.flow_max - self.flow_min)
        heads = self.head_max - (ys - self.y_min) / self.y_span * (self.head_max - self.head_min)
        return flows, heads


def _load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(
            f"{path} not found. Please copy the thesis bitmaps into external/thesis_figures/"
        )
    return img


def _color_mask(hsv: np.ndarray, ranges: Iterable[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]) -> np.ndarray:
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in ranges:
        lower_arr = np.array(lower, dtype=np.uint8)
        upper_arr = np.array(upper, dtype=np.uint8)
        mask |= cv2.inRange(hsv, lower_arr, upper_arr)
    return mask


def _clean_mask(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)


def digitize_figure23(image: Path, output_csv: Path, output_meta: Path) -> None:
    img = _load_image(image)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Axis calibration derived from OCR (Flow 3.6–5.2 kg/s, Head 550–900 m).
    axis = AxisMap(
        x_min=95.0,
        x_max=910.0,
        y_min=60.0,
        y_max=805.0,
        flow_min=3.6,
        flow_max=5.2,
        head_min=550.0,
        head_max=900.0,
    )
    color_ranges: Dict[str, Dict[str, Iterable[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]]] = {
        "36000": {
            "simulation": (
                ((95, 80, 80), (135, 255, 255)),  # blue
            ),
        },
        "33000": {
            "simulation": (
                ((40, 60, 60), (85, 255, 255)),  # green
            ),
        },
        "30000": {
            "simulation": (
                ((0, 50, 50), (25, 255, 255)),  # orange / red
                ((170, 50, 50), (179, 255, 255)),
            ),
        },
    }
    rows: List[Dict[str, float]] = []
    for rpm, kinds in color_ranges.items():
        for label, ranges in kinds.items():
            mask = _clean_mask(_color_mask(hsv, ranges))
            num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
            line_points: List[Tuple[float, float]] = []
            scatter_points: List[Tuple[float, float]] = []
            for idx in range(1, num):
                area = stats[idx, cv2.CC_STAT_AREA]
                width = stats[idx, cv2.CC_STAT_WIDTH]
                height = stats[idx, cv2.CC_STAT_HEIGHT]
                component_mask = labels == idx
                ys, xs = np.where(component_mask)
                if ys.size == 0:
                    continue
                flows, heads = axis.to_physical(xs.astype(float), ys.astype(float))
                if area > 400 or width > 3 * max(height, 1):
                    line_points.extend(zip(flows.tolist(), heads.tolist()))
                else:
                    scatter_points.append((float(np.mean(flows)), float(np.mean(heads))))
            if line_points:
                line_points = sorted(line_points, key=lambda p: p[0])
                flows = np.array([p[0] for p in line_points])
                heads = np.array([p[1] for p in line_points])
                bins = np.linspace(axis.flow_min, axis.flow_max, 40)
                digitized = np.digitize(flows, bins)
                for b in np.unique(digitized):
                    mask_idx = digitized == b
                    if np.count_nonzero(mask_idx) < 5:
                        continue
                    rows.append(
                        {
                            "series": f"{rpm}_simulation",
                            "rpm": float(rpm),
                            "flow_kg_s": float(np.mean(flows[mask_idx])),
                            "head_m": float(np.mean(heads[mask_idx])),
                        }
                    )
            for flow, head in scatter_points:
                rows.append(
                    {
                        "series": f"{rpm}_experiment",
                        "rpm": float(rpm),
                        "flow_kg_s": flow,
                        "head_m": head,
                    }
                )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["series", "rpm", "flow_kg_s", "head_m"])
        writer.writeheader()
        writer.writerows(rows)
    with output_meta.open("w", encoding="utf-8") as f:
        json.dump(axis.__dict__, f, indent=2)


@dataclass
class CrossSection:
    theta: np.ndarray
    value: np.ndarray

    def to_dict(self) -> Dict[str, List[float]]:
        return {"theta": self.theta.tolist(), "value": self.value.tolist()}


def _extract_cross_section(img: np.ndarray, roi: Tuple[int, int, int, int], theta_range: Tuple[float, float]) -> CrossSection:
    x0, y0, x1, y1 = roi
    sub = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
    mask = hsv[:, :, 1] > 40
    xs: List[float] = []
    ys: List[float] = []
    for col in range(mask.shape[1]):
        rows = np.where(mask[:, col])[0]
        if rows.size == 0:
            continue
        xs.append(col)
        ys.append(rows.min())
    if not xs:
        return CrossSection(theta=np.array([]), value=np.array([]))
    xs_arr = np.array(xs, dtype=float)
    ys_arr = np.array(ys, dtype=float)
    theta = theta_range[0] + (xs_arr - xs_arr.min()) / (xs_arr.max() - xs_arr.min()) * (
        theta_range[1] - theta_range[0]
    )
    # normalize value between 0 and 1 (top -> 1)
    value = 1.0 - (ys_arr - ys_arr.min()) / (ys_arr.max() - ys_arr.min())
    return CrossSection(theta=theta, value=value)


def digitize_figure21(image: Path, output_json: Path) -> None:
    img = _load_image(image)
    mid = img.shape[1] // 2
    left = img[:, :mid]
    right = img[:, mid:]
    # ROIs estimated manually for front/back slices.
    sections = {
        "WH_front": _extract_cross_section(left, (120, 250, 360, 680), (-1.5, 1.5)),
        "WH_back": _extract_cross_section(left, (420, 160, 650, 500), (-1.0, 1.0)),
        "WT_front": _extract_cross_section(right, (100, 240, 360, 690), (-1.5, 1.5)),
        "WT_back": _extract_cross_section(right, (430, 150, 680, 510), (-1.0, 1.0)),
    }
    serializable = {name: sec.to_dict() for name, sec in sections.items() if sec.theta.size}
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Digitize thesis figures 21 & 23")
    parser.add_argument(
        "--figure21",
        type=Path,
        default=Path("external/thesis_figures/figure21_whn_wtn.png"),
        help="Path to Figure 21 image",
    )
    parser.add_argument(
        "--figure23",
        type=Path,
        default=Path("external/thesis_figures/figure23_pump_head.png"),
        help="Path to Figure 23 image",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/validation"),
        help="Directory to store digitized datasets",
    )
    args = parser.parse_args()
    digitize_figure23(
        args.figure23,
        args.output_dir / "figure23_digitized.csv",
        args.output_dir / "figure23_axes.json",
    )
    digitize_figure21(
        args.figure21,
        args.output_dir / "figure21_cross_sections.json",
    )


if __name__ == "__main__":
    main()
