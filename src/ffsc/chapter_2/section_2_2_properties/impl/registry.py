from typing import Protocol, Dict, Any

class EOS(Protocol):
    """统一接口：给 T[K], rho[单位见实现] -> 返回包含至少 p 的字典。"""
    def evaluate(self, T: float, rho: float) -> Dict[str, Any]: ...

REGISTRY = {}  # name -> factory(params: dict) -> EOS

def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco

def build(name: str, params: dict) -> EOS:
    if name not in REGISTRY:
        raise KeyError(f"EOS '{name}' not registered")
    return REGISTRY[name](params)
