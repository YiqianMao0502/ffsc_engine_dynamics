from ffsc.chapter_2.section_2_2_properties.impl.loader import load_eos_from_json

def test_pr_demo():
    eos = load_eos_from_json("data/props/mix_pr_demo.json")
    out = eos.evaluate(T=900.0, v=1.0e-3)
    assert out["P_unit"] == "Pa"
    # 允许 ±1% 漂移（浮点/平台差异）
    refP = 7.616679e6
    assert abs(out["P"] - refP) / refP < 0.01
