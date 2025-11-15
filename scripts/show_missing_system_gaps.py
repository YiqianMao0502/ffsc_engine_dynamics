"""Quick helper to list outstanding data requirements for the §2.6 skeleton."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ffsc.chapter_2.section_2_6_system.system import build_default_system


def main():
    system = build_default_system(str(ROOT / "data" / "props"))
    print("Missing data / TODO list:")
    for item in system.missing_data():
        print(f" - {item}")


if __name__ == "__main__":
    main()
