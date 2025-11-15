import json, sys, pathlib
try:
    from ruamel.yaml import YAML
except Exception as e:
    print("[ERR] ruamel.yaml 未安装，请先运行: pip install ruamel.yaml")
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = ROOT / "external" / "gri30.yaml"
if not src.exists():
    print(f"[ERR] 找不到 {src}")
    sys.exit(1)

# 目标九种：H2, O2, H2O, CH4, CO, CO2, OH, O, H
target = {"H2","O2","H2O","CH4","CO","CO2","OH","O","H"}

yaml = YAML(typ="safe")
data = yaml.load(src.read_text(encoding="utf-8"))

species_nodes = data.get("species", [])
out = {"source": "Cantera gri30.yaml (GRI-Mech 3.0)", "extracted_species": []}

for sp in species_nodes:
    name = sp.get("name")
    if name not in target:
        continue
    th = sp.get("thermo", {})
    tr = sp.get("transport", {})

    # NASA7
    nasa = {
        "model": th.get("model"),
        "T_ranges": th.get("temperature-ranges"),
        # data 是两段 [a1..a7]，低温/高温
        "coeffs": th.get("data"),
        "note": th.get("note", "")
    }

    # 输运（Lennard-Jones / 介电/极化/转动弛豫等，按 Cantera 字段原样保留）
    trans = {
        "model": tr.get("model"),
        "geometry": tr.get("geometry"),
        "well_depth": tr.get("well-depth", tr.get("well_depth", None)),       # epsilon/k_B [K]
        "diameter": tr.get("diameter", None),                                  # sigma [Å]
        "polarizability": tr.get("polarizability", None),                      # Å^3
        "rotational_relaxation": tr.get("rotational-relaxation", tr.get("rotational_relaxation", None)),
        "dipole": tr.get("dipole", None)
    }

    out["extracted_species"].append({
        "name": name,
        "thermo_NASA7": nasa,
        "transport_Cantera": trans
    })

# 落盘（路线B数据）
dst_dir = ROOT / "data" / "props"
dst_dir.mkdir(parents=True, exist_ok=True)
dst = dst_dir / "routeB_gri30_thermo_transport.json"
dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] 写入 {dst} ，共 {len(out['extracted_species'])} 种")

# 同时生成一个最小可读取的 EOS 入口 JSON（P-R 混合，仅示例，不覆盖现有）
mix = {
  "model": "pr_mixture",
  "params": {
    "species_thermo_source": "routeB_gri30_thermo_transport.json",
    # 组分示例（可以以后替换为预燃室/主燃烧室的真实摩尔分数）
    "mole_fractions": {"CH4":0.5, "O2":0.5}
  }
}
(mix_dst := dst_dir / "mix_pr_demo.json").write_text(json.dumps(mix, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] 写入 {mix_dst} 作为示例混合物入口（P-R 路线B）")
