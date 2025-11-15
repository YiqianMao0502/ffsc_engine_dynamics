"""Common state containers and abstract interfaces for §2.5 components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class FluidState:
    """Minimal thermodynamic state tracked in the component layer."""

    p: Optional[float] = None
    T: Optional[float] = None
    rho: Optional[float] = None
    h: Optional[float] = None
    u: Optional[float] = None
    s: Optional[float] = None
    cp: Optional[float] = None
    cv: Optional[float] = None
    gamma: Optional[float] = None
    extra: Dict[str, float] = field(default_factory=dict)


@dataclass
class TwoPhaseState(FluidState):
    """Two-phase specific augmentation, leaving placeholders for quality, etc."""

    x_quality: Optional[float] = None
    rho_v: Optional[float] = None
    rho_l: Optional[float] = None


@dataclass
class GasState(FluidState):
    """Gas-mixture state with composition tracking."""

    composition: Dict[str, float] = field(default_factory=dict)
    mu: Optional[float] = None
    lam: Optional[float] = None


class Component:
    """Base class to document §2.5 component interface expectations."""

    def compute_flows(self, *args, **kwargs):  # pragma: no cover - documentation hook
        raise NotImplementedError

    def rhs(self, *args, **kwargs):  # pragma: no cover - documentation hook
        raise NotImplementedError
