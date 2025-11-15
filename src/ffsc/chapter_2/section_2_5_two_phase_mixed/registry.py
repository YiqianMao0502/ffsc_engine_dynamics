from typing import Dict, Type, Any

_REGISTRY: Dict[str, Type] = {}

def register(name: str):
    def deco(cls: Type):
        _REGISTRY[name] = cls
        return cls
    return deco

def build(name: str, *args, **kwargs) -> Any:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Component '{name}' not registered")
    return cls(*args, **kwargs)
