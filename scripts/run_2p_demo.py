from ffsc.chapter_2.section_2_5_two_phase_mixed import build

pipe = build("tp_pipe", A=1e-4, k=1.0, k_dp=1.0)
dm = pipe.mass_flow_from_dp(rho_up=800.0, dp=1e5)
print("[2.82] dm =", dm)

from ffsc.chapter_2.section_2_5_two_phase_mixed import TwoPhaseValve
psi = TwoPhaseValve.psi_subcooled_no_choking(eta=0.7)
valve = build("tp_valve", A=1e-4, k=1.0, k_dp=1.0)
m_dot = valve.mass_flow(p_up=5e6, rho_up=800.0, psi=psi)
print("[2.93] m_dot =", m_dot)

from ffsc.chapter_2.section_2_5_two_phase_mixed import MixGasPipe
Cq = MixGasPipe.C_q_polynomial(eta=0.6)
Cm = MixGasPipe.C_m_piecewise(eta=0.6, gamma_s=1.3, rho_up=5.0, T_up=900.0, p_up=2e6)
m_dot_gas = MixGasPipe.m_dot_resistive(p_up=2e6, T_up=900.0, C_q=Cq, C_m=Cm)
print("[2.95] m_dot_gas =", m_dot_gas)
