from dataclasses import dataclass
from typing import List, Dict, Any
from .registry import register
from .nasa7 import NASA7Piece, NASA7Species, mix_ideal

@dataclass
class NASA7Mixture:
    species: List[NASA7Species]

    @staticmethod
    def from_params(params: Dict[str, Any]) -> "NASA7Mixture":
        sp_list = []
        for sp in params["species"]:
            Tlow, Tmid, Thigh = sp["T_ranges"]
            low  = NASA7Piece(*sp["low"], Tmin=Tlow, Tmax=Tmid)
            high = NASA7Piece(*sp["high"], Tmin=Tmid, Tmax=Thigh)
            # 分子量 M 可为 None；仅热容/焓/熵不需要 M
            sp_list.append(NASA7Species(name=sp["name"], low=low, high=high, Tmid=Tmid, M=sp.get("M", None), source=sp.get("ref","")))
        return NASA7Mixture(species=sp_list)

    # 对外暴露与文档一致的接口（molar 量）
    def cp_mixture(self, T: float, X: Dict[str, float]) -> float:
        Xi, spp = self._align(X)
        return mix_ideal({}, T=T, Xi=Xi, species=spp)["cp_molar"]

    def h_mixture(self, T: float, X: Dict[str, float]) -> float:
        Xi, spp = self._align(X)
        return mix_ideal({}, T=T, Xi=Xi, species=spp)["h_molar"]

    def s_mixture(self, T: float, X: Dict[str, float]) -> float:
        Xi, spp = self._align(X)
        return mix_ideal({}, T=T, Xi=Xi, species=spp)["s_molar"]

    # 简单按 species 名称对齐混合物组成
    def _align(self, X: Dict[str, float]):
        names = [s.name for s in self.species]
        Xi = []
        spp = []
        total = 0.0
        for n, s in zip(names, self.species):
            x = float(X.get(n, 0.0))
            Xi.append(x); spp.append(s); total += x
        if total <= 0:
            raise ValueError("Mixture fractions are all zero; provide nonzero mole fractions.")
        Xi = [x/total for x in Xi]
        return Xi, spp

@register("nasa7_mixture")
def build_nasa7_mixture(params: Dict[str, Any]) -> NASA7Mixture:
    return NASA7Mixture.from_params(params)
