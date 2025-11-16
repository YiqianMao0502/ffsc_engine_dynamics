r"""mBWR-32 方程（Route-A 结构）。

仅使用论文表 8 中的 \alpha_n(T) 结构（对应 32 个 b_i 系数）与式 (2.1) 的压力表达，
通过热力学基本恒等式推导 mBWR 模型在 Route-A 范围内可确定的“残余”性质：

* 压力 :math:`p(T, \rho)`
* 残余内部能、焓、熵 :math:`(u, h, s)^\text{res}`
* 残余定容、定压热容 :math:`(c_v, c_p)^\text{res}`
* 常见偏导：:math:`(\partial p/\partial T)_\rho`, :math:`(\partial p/\partial \rho)_T`,
  以及由这些导出到 :math:`(\partial /\partial v)_T`、:math:`(\partial u/\partial T)_\rho` 等

所有残余量均以“相对于同温度/摩尔密度的理想气体（:math:`p=\rho R T`）”为基准。
理想气体的 cp/cv/h/s 需由其它 Route-B 数据源（例如 NASA-7）叠加，本文件不引入论文之外的额外常数。
"""

from __future__ import annotations

from math import exp
from typing import Any, Callable, Dict, Tuple

from .registry import EOS, register
from ..utils.units import assert_unit


@register("mbwr32")
def _factory(params: Dict[str, Any]) -> EOS:
    """构造 mBWR-32 模型，输入参数完全来自 JSON。"""
    required = ["R", "R_unit", "rho_crit", "rho_crit_unit", "b", "b_unit", "p_unit", "rho_unit", "T_unit"]
    for k in required:
        if k not in params:
            raise KeyError(f"Missing '{k}' in mbwr32 params")

    assert_unit(params["T_unit"], "K", "temperature")

    R = float(params["R"])              # 例如 0.083145 L·bar·mol^-1·K^-1
    b = params["b"]                     # dict: {"b1":..., ..., "b32":...}
    rho_crit = float(params["rho_crit"])
    units = {k: params[k] for k in ["R_unit", "rho_crit_unit", "b_unit", "p_unit", "rho_unit", "T_unit"]}

    class MBWR32(EOS):
        """Route-A mBWR-32：压力 + 残余热力性质。"""

        def evaluate(self, T: float, rho: float) -> Dict[str, Any]:
            if T <= 0:
                raise ValueError("Temperature must be >0 K for mBWR-32 evaluation")
            if rho < 0:
                raise ValueError("Density must be >=0 for mBWR-32 Route-A evaluation")

            alpha, dalpha, d2alpha = self._alpha_all(T)
            eval_terms = self._evaluate_terms(T, rho, alpha, dalpha, d2alpha)
            residual_props = self._residual_properties(T, rho, alpha, dalpha, d2alpha, eval_terms)

            notes = [
                "Pressure from Eq.(2.1) with Table-8 coefficients.",
                "Residual properties only; ideal-gas contributions must be supplied separately (e.g. NASA-7).",
            ]

            return {
                "p": eval_terms["p"],
                "p_unit": units["p_unit"],
                "inputs_unit": {"T": units["T_unit"], "rho": units["rho_unit"]},
                "derivatives": {
                    "dp_dT_rho": eval_terms["dp_dT"],
                    "dp_drho_T": eval_terms["dp_drho"],
                    "dp_dv_T": self._rho_to_v_derivative(eval_terms["dp_drho"], rho),
                    "dp_dT_v": eval_terms["dp_dT"],
                    "du_drho_T_res": residual_props["du_drho_T"],
                    "du_dv_T_res": self._rho_to_v_derivative(residual_props["du_drho_T"], rho),
                    "du_dT_rho_res": residual_props["cv_res"],
                    "du_dT_v_res": residual_props["cv_res"],
                },
                "residual": {
                    "u": residual_props["u_res"],
                    "h": residual_props["h_res"],
                    "s": residual_props["s_res"],
                    "cv": residual_props["cv_res"],
                    "cp": residual_props["cp_res"],
                },
                "helpers": {"rho_crit": rho_crit, "R": R},
                "note": notes,
            }

        @staticmethod
        def _rho_to_v_derivative(deriv_rho: float, rho: float) -> float:
            if rho <= 0:
                return float("nan")
            return -deriv_rho * (rho ** 2)

        def _alpha_all(self, T: float) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
            a: Dict[int, float] = {}
            da: Dict[int, float] = {}
            d2a: Dict[int, float] = {}

            T_sqrt = T ** 0.5
            T_inv = 1.0 / T
            T_inv2 = T_inv ** 2
            T_inv3 = T_inv ** 3
            T_inv4 = T_inv ** 4
            T_inv5 = T_inv ** 5
            T_inv6 = T_inv ** 6

            a[1] = R * T
            da[1] = R
            d2a[1] = 0.0

            a[2] = (
                b["b1"] * T + b["b2"] * T_sqrt + b["b3"] + b["b4"] * T_inv + b["b5"] * T_inv2
            )
            da[2] = (
                b["b1"]
                + 0.5 * b["b2"] / T_sqrt
                - b["b4"] * T_inv2
                - 2.0 * b["b5"] * T_inv3
            )
            d2a[2] = (
                -0.25 * b["b2"] / (T_sqrt * T)
                + 2.0 * b["b4"] * T_inv3
                + 6.0 * b["b5"] * T_inv4
            )

            a[3] = b["b6"] * T + b["b7"] + b["b8"] * T_inv + b["b9"] * T_inv2
            da[3] = b["b6"] - b["b8"] * T_inv2 - 2.0 * b["b9"] * T_inv3
            d2a[3] = 2.0 * b["b8"] * T_inv3 + 6.0 * b["b9"] * T_inv4

            a[4] = b["b10"] * T + b["b11"] + b["b12"] * T_inv
            da[4] = b["b10"] - b["b12"] * T_inv2
            d2a[4] = 2.0 * b["b12"] * T_inv3

            a[5] = b["b13"]
            da[5] = 0.0
            d2a[5] = 0.0

            a[6] = b["b14"] * T_inv + b["b15"] * T_inv2
            da[6] = -b["b14"] * T_inv2 - 2.0 * b["b15"] * T_inv3
            d2a[6] = 2.0 * b["b14"] * T_inv3 + 6.0 * b["b15"] * T_inv4

            a[7] = b["b16"] * T_inv
            da[7] = -b["b16"] * T_inv2
            d2a[7] = 2.0 * b["b16"] * T_inv3

            a[8] = b["b17"] * T_inv + b["b18"] * T_inv2
            da[8] = -b["b17"] * T_inv2 - 2.0 * b["b18"] * T_inv3
            d2a[8] = 2.0 * b["b17"] * T_inv3 + 6.0 * b["b18"] * T_inv4

            a[9] = b["b19"] * T_inv2
            da[9] = -2.0 * b["b19"] * T_inv3
            d2a[9] = 6.0 * b["b19"] * T_inv4

            a[10] = b["b20"] * T_inv2 + b["b21"] * T_inv3
            da[10] = -2.0 * b["b20"] * T_inv3 - 3.0 * b["b21"] * T_inv4
            d2a[10] = 6.0 * b["b20"] * T_inv4 + 12.0 * b["b21"] * T_inv5

            a[11] = b["b22"] * T_inv2 + b["b23"] * T_inv4
            da[11] = -2.0 * b["b22"] * T_inv3 - 4.0 * b["b23"] * T_inv5
            d2a[11] = 6.0 * b["b22"] * T_inv4 + 20.0 * b["b23"] * T_inv6

            a[12] = b["b24"] * T_inv2 + b["b25"] * T_inv3
            da[12] = -2.0 * b["b24"] * T_inv3 - 3.0 * b["b25"] * T_inv4
            d2a[12] = 6.0 * b["b24"] * T_inv4 + 12.0 * b["b25"] * T_inv5

            a[13] = b["b26"] * T_inv2 + b["b27"] * T_inv4
            da[13] = -2.0 * b["b26"] * T_inv3 - 4.0 * b["b27"] * T_inv5
            d2a[13] = 6.0 * b["b26"] * T_inv4 + 20.0 * b["b27"] * T_inv6

            a[14] = b["b28"] * T_inv2 + b["b29"] * T_inv3
            da[14] = -2.0 * b["b28"] * T_inv3 - 3.0 * b["b29"] * T_inv4
            d2a[14] = 6.0 * b["b28"] * T_inv4 + 12.0 * b["b29"] * T_inv5

            a[15] = b["b30"] * T_inv2 + b["b31"] * T_inv3 + b["b32"] * T_inv4
            da[15] = -2.0 * b["b30"] * T_inv3 - 3.0 * b["b31"] * T_inv4 - 4.0 * b["b32"] * T_inv5
            d2a[15] = 6.0 * b["b30"] * T_inv4 + 12.0 * b["b31"] * T_inv5 + 20.0 * b["b32"] * T_inv6

            return a, da, d2a

        def _evaluate_terms(
            self,
            T: float,
            rho: float,
            alpha: Dict[int, float],
            dalpha: Dict[int, float],
            d2alpha: Dict[int, float],
        ) -> Dict[str, float]:
            s1 = 0.0
            s1_T = 0.0
            s1_TT = 0.0
            s1_rho = 0.0
            for n in range(1, 10):
                if rho == 0.0 and n > 1:
                    rho_pow = 0.0
                else:
                    rho_pow = rho ** n
                s1 += alpha[n] * rho_pow
                s1_T += dalpha[n] * rho_pow
                s1_TT += d2alpha[n] * rho_pow
                if rho == 0.0:
                    if n == 1:
                        s1_rho += alpha[n]
                else:
                    s1_rho += n * alpha[n] * (rho ** (n - 1))

            s2 = 0.0
            s2_T = 0.0
            s2_TT = 0.0
            s2_rho = 0.0
            exp_term = 1.0
            if rho != 0.0:
                rho_ratio = rho / rho_crit
                exp_term = exp((rho_ratio) ** 2)
                d_exp_d_rho = 2.0 * rho_ratio / rho_crit * exp_term
                poly = 0.0
                poly_T = 0.0
                poly_TT = 0.0
                poly_rho = 0.0
                for n in range(10, 16):
                    power = 2 * n - 17
                    rho_pow = rho ** power
                    poly += alpha[n] * rho_pow
                    poly_T += dalpha[n] * rho_pow
                    poly_TT += d2alpha[n] * rho_pow
                    poly_rho += alpha[n] * power * (rho ** (power - 1))
                s2 = exp_term * poly
                s2_T = exp_term * poly_T
                s2_TT = exp_term * poly_TT
                s2_rho = exp_term * poly_rho + poly * d_exp_d_rho

            p = s1 + s2
            dp_dT = s1_T + s2_T
            d2p_dT2 = s1_TT + s2_TT
            dp_drho = s1_rho + s2_rho

            return {
                "p": p,
                "dp_dT": dp_dT,
                "d2p_dT2": d2p_dT2,
                "dp_drho": dp_drho,
            }

        def _residual_properties(
            self,
            T: float,
            rho: float,
            alpha: Dict[int, float],
            dalpha: Dict[int, float],
            d2alpha: Dict[int, float],
            eval_terms: Dict[str, float],
        ) -> Dict[str, float]:
            p = eval_terms["p"]
            dp_dT = eval_terms["dp_dT"]
            d2p_dT2 = eval_terms["d2p_dT2"]
            dp_drho = eval_terms["dp_drho"]

            p_res = p - R * T * rho
            dp_dT_res = dp_dT - R * rho

            du_drho_T = (
                alpha[2] - T * dalpha[2]
                if rho == 0.0
                else (p_res - T * dp_dT_res) / (rho ** 2)
            )

            u_res = self._integrate_residual(
                lambda r: self._u_integrand(T, r, alpha, dalpha),
                rho,
                limit0=alpha[2] - T * dalpha[2],
            )
            s_res = self._integrate_residual(
                lambda r: self._s_integrand(T, r, alpha, dalpha),
                rho,
                limit0=-dalpha[2],
            )
            cv_res = self._integrate_residual(
                lambda r: self._cv_integrand(T, r, alpha, d2alpha),
                rho,
                limit0=-T * d2alpha[2],
            )

            if rho == 0.0:
                h_res = 0.0
                cp_res = 0.0
            else:
                h_res = u_res + p_res / rho
                cp_res = cv_res + T * (dp_dT ** 2) / (rho ** 2 * dp_drho) - R

            return {
                "u_res": u_res,
                "h_res": h_res,
                "s_res": s_res,
                "cv_res": cv_res,
                "cp_res": cp_res,
                "du_drho_T": du_drho_T,
            }

        def _u_integrand(
            self,
            T: float,
            rho: float,
            alpha: Dict[int, float],
            dalpha: Dict[int, float],
        ) -> float:
            if rho == 0.0:
                return alpha[2] - T * dalpha[2]
            eval_terms = self._evaluate_terms(T, rho, alpha, dalpha, {n: 0.0 for n in alpha})
            p_res = eval_terms["p"] - R * T * rho
            dp_dT_res = eval_terms["dp_dT"] - R * rho
            return (p_res - T * dp_dT_res) / (rho ** 2)

        def _s_integrand(
            self,
            T: float,
            rho: float,
            alpha: Dict[int, float],
            dalpha: Dict[int, float],
        ) -> float:
            if rho == 0.0:
                return -dalpha[2]
            eval_terms = self._evaluate_terms(T, rho, alpha, dalpha, {n: 0.0 for n in alpha})
            dp_dT_res = eval_terms["dp_dT"] - R * rho
            return -dp_dT_res / (rho ** 2)

        def _cv_integrand(
            self,
            T: float,
            rho: float,
            alpha: Dict[int, float],
            d2alpha: Dict[int, float],
        ) -> float:
            if rho == 0.0:
                return -T * d2alpha[2]
            eval_terms = self._evaluate_terms(T, rho, alpha, {n: 0.0 for n in alpha}, d2alpha)
            d2p_dT2 = eval_terms["d2p_dT2"]
            return -T * d2p_dT2 / (rho ** 2)

        def _integrate_residual(
            self,
            func: Callable[[float], float],
            rho: float,
            limit0: float,
            max_steps: int = 600,
        ) -> float:
            if rho == 0.0:
                return 0.0

            upper = abs(rho)
            if upper < 1e-12:
                return limit0 * rho

            steps = max(2, min(max_steps, int(200 * upper / (upper + 1.0)) * 2))
            if steps % 2 == 1:
                steps += 1
            h = upper / steps

            total = limit0 + func(upper)
            for i in range(1, steps):
                r_i = i * h
                coeff = 4 if i % 2 == 1 else 2
                total += coeff * func(r_i)
            integral = total * h / 3.0
            return integral if rho > 0 else -integral

    return MBWR32()
