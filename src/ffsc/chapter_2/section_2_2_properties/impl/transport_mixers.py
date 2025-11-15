"""
混合气输运混合法：
- 黏度: Wilke (Chem. Eng. Sci. 1950)
- 导热: 简化 Mason-Saxena 型（当前采取摩尔分数加权，后续可升级）
"""

from typing import List
import math

def wilke_viscosity(Xi: List[float], mu_pure: List[float], M: List[float]) -> float:
    """
    Wilke 黏度混合法:
    mu_mix = sum_i Xi_i * mu_i / sum_j Xi_j * phi_ij
    phi_ij = [1 + sqrt(mu_i/mu_j)*(M_j/M_i)**0.25]^2 / [sqrt(8)*(1 + M_i/M_j)**0.5]
    Xi : 摩尔分数数组（已归一化）
    mu_pure : 各组分黏度 [Pa·s]
    M : 各组分摩尔质量 [kg/mol]
    """
    n = len(Xi)
    assert len(mu_pure) == n and len(M) == n
    phi = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                phi[i][j] = 1.0
            else:
                phi[i][j] = (
                    (1.0 + math.sqrt(mu_pure[i] / mu_pure[j]) * (M[j] / M[i]) ** 0.25) ** 2
                    / (math.sqrt(8.0) * math.sqrt(1.0 + M[i] / M[j]))
                )
    denom = [sum(Xi[j] * phi[i][j] for j in range(n)) for i in range(n)]
    mu_mix = sum(Xi[i] * mu_pure[i] / denom[i] for i in range(n))
    return mu_mix

def mason_saxena_lambda(Xi: List[float], lam_pure: List[float], M: List[float]) -> float:
    """
    Mason-Saxena 导热混合的简化形式：lambda_mix = sum_i Xi_i * lambda_i
    完整 Mason-Saxena 形式会有附加项，后续如有需要可在此扩展。
    """
    assert len(Xi) == len(lam_pure) == len(M)
    return sum(x * l for x, l in zip(Xi, lam_pure))
