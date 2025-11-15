"""
NASA 7-coeff polynomials (two temperature ranges) for ideal-gas cp, h, s.
Form (per NASA Glenn/CEA): cp/R = a1 + a2 T + a3 T^2 + a4 T^3 + a5 T^4
h/(RT) = a1 + a2 T/2 + a3 T^2/3 + a4 T^3/4 + a5 T^4/5 + a6/T
s/R = a1 ln T + a2 T + a3 T^2/2 + a4 T^3/3 + a5 T^4/4 + a7
This file evaluates species-wise polynomials and mixes by mole fraction.
"""
from dataclasses import dataclass
from typing import Dict, Any, List

R = 8.314462618  # J/mol/K

@dataclass
class NASA7Piece:
    # a1..a7 and valid range [Tmin, Tmax]
    a1: float; a2: float; a3: float; a4: float; a5: float; a6: float; a7: float
    Tmin: float; Tmax: float

@dataclass
class NASA7Species:
    name: str
    low: NASA7Piece
    high: NASA7Piece
    Tmid: float
    M: float  # kg/mol
    source: str = ""

def _eval_piece(piece: NASA7Piece, T: float):
    a1,a2,a3,a4,a5,a6,a7 = piece.a1,piece.a2,piece.a3,piece.a4,piece.a5,piece.a6,piece.a7
    # dimensionless
    cp_R = a1 + a2*T + a3*T*T + a4*T**3 + a5*T**4
    h_RT = a1 + a2*T/2.0 + a3*T**2/3.0 + a4*T**3/4.0 + a5*T**4/5.0 + a6/T
    s_R  = a1 * (0.0 if T<=0 else (0.0 if T==1.0 else __import__("math").log(T))) + a2*T + a3*T*T/2.0 + a4*T**3/3.0 + a5*T**4/4.0 + a7
    return cp_R, h_RT, s_R

def eval_species(spec: NASA7Species, T: float) -> Dict[str, float]:
    piece = spec.low if T <= spec.Tmid else spec.high
    cp_R, h_RT, s_R = _eval_piece(piece, T)
    return {
        "cp": cp_R * R,                # J/mol/K
        "h":  h_RT * R * T,            # J/mol
        "s":  s_R * R                  # J/mol/K
    }

def mix_ideal(properties: Dict[str, Any], T: float, Xi: List[float], species: List[NASA7Species]) -> Dict[str, float]:
    # simple mole-fraction mixing for ideal-gas cp,h,s (molar)
    if len(Xi) != len(species):
        raise ValueError("Xi length mismatch species length")
    if abs(sum(Xi)-1.0) > 1e-9:
        raise ValueError("Xi must sum to 1")
    cp = h = s = 0.0
    for x, sp in zip(Xi, species):
        vals = eval_species(sp, T)
        cp += x * vals["cp"]
        h  += x * vals["h"]
        s  += x * vals["s"]
    return {"cp_molar": cp, "h_molar": h, "s_molar": s}
