import csv
from pathlib import Path
BASE = Path(__file__).resolve().parents[1] / "data"
def preview_csv(name: str, n: int = 3):
    fp = BASE / name
    rows = []
    with open(fp, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            if i >= n: break
            rows.append(r)
    print(f"[OK] {name} preview:", rows)
if __name__ == "__main__":
    preview_csv("table_21_tank_pressurization.csv")
    preview_csv("table_23_valves_and_ignition.csv")
    preview_csv("table_24_static_params_comparison.csv")
    from ffsc.chapter_2.section_2_1_overview import MODEL as M21
    from ffsc.chapter_2.section_2_3_turbopump.centrifugal_pump import MODEL as M231
    print("[OK] imports:", M21.name, M231.name)
