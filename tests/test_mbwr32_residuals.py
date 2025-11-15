from ffsc.chapter_2.section_2_2_properties.impl import mbwr32


def build_simple_mbwr(b3: float = 0.5):
    params = {
        "R": 1.0,
        "R_unit": "placeholder",
        "rho_crit": 5.0,
        "rho_crit_unit": "placeholder",
        "b_unit": "placeholder",
        "p_unit": "arb",
        "rho_unit": "arb",
        "T_unit": "K",
    }
    coeffs = {f"b{i}": 0.0 for i in range(1, 33)}
    coeffs["b3"] = b3
    params["b"] = coeffs
    return mbwr32._factory(params)


def test_mbwr32_pressure_and_derivatives():
    eos = build_simple_mbwr(b3=0.5)
    T = 300.0
    rho = 2.0
    out = eos.evaluate(T=T, rho=rho)

    assert out["p"] == 602.0
    derivs = out["derivatives"]
    assert abs(derivs["dp_dT_rho"] - 2.0) < 1e-10
    assert abs(derivs["dp_drho_T"] - 302.0) < 1e-10
    assert abs(derivs["dp_dv_T"] + 1208.0) < 1e-6


def test_mbwr32_residual_properties():
    eos = build_simple_mbwr(b3=0.5)
    out = eos.evaluate(T=300.0, rho=2.0)
    res = out["residual"]
    assert abs(res["u"] - 1.0) < 1e-9
    assert abs(res["h"] - 2.0) < 1e-9
    assert abs(res["s"]) < 1e-9
    assert abs(res["cv"]) < 1e-9
    assert abs(res["cp"] + 0.006622516556291391) < 1e-12

    derivs = out["derivatives"]
    assert abs(derivs["du_drho_T_res"] - 0.5) < 1e-12
    assert abs(derivs["du_dv_T_res"] + 2.0) < 1e-9
    assert derivs["du_dT_rho_res"] == 0.0


def test_mbwr32_zero_density_limit():
    eos = build_simple_mbwr(b3=0.5)
    out = eos.evaluate(T=350.0, rho=0.0)
    assert out["p"] == 0.0
    res = out["residual"]
    assert res["u"] == 0.0
    assert res["h"] == 0.0
    assert res["s"] == 0.0
    assert res["cv"] == 0.0
    assert res["cp"] == 0.0
    assert abs(out["derivatives"]["du_drho_T_res"] - 0.5) < 1e-12
