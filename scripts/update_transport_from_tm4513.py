import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
src = ROOT / "data/raw/nasa_tm4513_transport_table4.txt"
dst = ROOT / "data/props/transport_demo.json"

# 目前 demo 里用到的物种
TARGETS = ["H2", "O2", "H2O"]

# NASA TM-4513 文本中的搜索 key（H2O 在 OCR 里可能变成 H20，多配一个）
SEARCH_KEYS = {
    "H2": ["H2 V2C2 GORDON"],
    "O2": ["O2 V2C2 GORDON"],
    "H2O": ["H2O V2C2 GORDON", "H20 V2C2 GORDON"],
}

float_pattern = re.compile(r"[+-]?\d+\.\d+(?:E[+-]?\d+)?")

text = src.read_text(encoding="utf-8", errors="ignore")
lines = text.splitlines()


def find_species_block(symbol: str):
    """找到 symbol 对应的那一行索引."""
    keys = SEARCH_KEYS[symbol]
    if isinstance(keys, str):
        keys = [keys]
    for i, line in enumerate(lines):
        for key in keys:
            if key in line:
                return i
    raise RuntimeError(f"Cannot find block for species '{symbol}' in TM-4513 text")


def extract_segments(symbol: str):
    """
    从 TM-4513 中提取指定物种的 4 行 V/C 系数，
    并转换成我们 JSON 用的段结构。
    """
    start_idx = find_species_block(symbol)
    rows = []
    j = start_idx + 1
    # 往后扫，收集 4 行以 V/C 开头的行
    while j < len(lines) and len(rows) < 4:
        line = lines[j].strip()
        if line and line[0] in ("V", "C"):
            rows.append(line)
        j += 1

    if len(rows) != 4:
        raise RuntimeError(f"{symbol}: expected 4 V/C rows, got {len(rows)}")

    mu_segments = []
    k_segments = []

    for row in rows:
        kind = row[0]  # 'V' 或 'C'
        nums = [float(s.replace("D", "E")) for s in float_pattern.findall(row)]
        if len(nums) < 6:
            raise RuntimeError(f"{symbol}: row '{row}' ⇒ {len(nums)} floats (need 6)")
        Tmin, Tmax, A, B, C_, D_ = nums[:6]

        # 映射 NASA 形式 → 我们项目的形式
        segment = {
            "T_min": Tmin,
            "T_max": Tmax,
            "a": A,      # A · ln T
            "b": C_,     # C / T
            "c": D_,     # D / T^2
            "d": B,      # 常数项
        }

        if kind == "V":
            mu_segments.append(segment)
        else:
            k_segments.append(segment)

    mu_segments.sort(key=lambda s: s["T_min"])
    k_segments.sort(key=lambda s: s["T_min"])
    return mu_segments, k_segments


# 读入当前的 transport_demo.json
data = json.loads(dst.read_text(encoding="utf-8"))
species_list = data.get("species", [])
species_map = {sp["name"]: sp for sp in species_list}

for sym in TARGETS:
    if sym not in species_map:
        raise KeyError(f"Species '{sym}' not found in {dst}")
    mu, k = extract_segments(sym)
    species_map[sym]["mu"] = mu
    species_map[sym]["k"] = k

dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Updated {dst} with NASA TM-4513 transport coefficients for: {', '.join(TARGETS)}")
