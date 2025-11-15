R_L_BAR_PER_MOL_K = 0.083145  # L·bar·mol^-1·K^-1（常用于mBWR文献），若JSON有不同取值以JSON为准
def assert_unit(actual: str, expected: str, what: str):
    if actual != expected:
        raise ValueError(f"Unit mismatch for {what}: got '{actual}', expected '{expected}'")
