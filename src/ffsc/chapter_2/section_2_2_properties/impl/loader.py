import json
from pathlib import Path

# 显式导入以触发注册
from . import srk_pr          # srk_mixture, pr_mixture
from . import mbwr32          # mbwr32
from . import nasa7_model     # nasa7_mixture
from . import transport_mixture  # transport_poly_mixture

from .registry import build

def load_eos_from_json(json_path: str):
    p = Path(json_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    # 兼容两种结构：{model, params} 和 {model, species, ...}
    params = data.get("params", data)
    return build(data["model"], params)
