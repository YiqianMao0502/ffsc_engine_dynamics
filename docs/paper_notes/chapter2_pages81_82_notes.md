# Chapter 2 Pages 81-82 – Implementation Notes

## Table 23 – Key Valves and Ignition Devices
- Provides mapping between component codes (MFV, PFV, POV, TFV, TOV, HFV, HOV, Ig_CH4_Pre, Ig_Main_CC, etc.) and their physical locations within the full-flow staged-combustion (FFSC) system.
- Codes align with existing CSV `data/props/table_23_valves_and_ignition.csv`; ensure model registries or component builders use these identifiers when wiring the system graph.
- Valve positioning informs routing for the pressurization loop, main/prechamber feeds, and oxidizer/fuel manifolds—critical for constructing the §2.6 network topology.

## Table 24 – Static Operating Point Comparison
- Lists steady-state targets for the FFSC engine: chamber pressure, total mass flow, pump outlet pressures, preburner pressures/temperatures, etc.
- Values correspond to CSV `data/props/table_24_static_params_comparison.csv`; use as reference when validating Route-A structural models or Route-B numerical baselines.
- Useful for system-level tests: e.g., assert simulated steady solutions match tabulated pressures/temperatures within tolerance.

## Section 2.7 Summary – Overall Takeaways
- Emphasizes coupling of turbo-pump, pressurization, preburner, and cooling subsystems to analyze dynamic behavior.
- Highlights that validated component models feed into the Amesim-based system study—mirrors our goal of assembling reusable components and verifying against Table 24 metrics.
- Notes the need for instrumentation/telemetry alignment (pressure, temperature, flow sensors) when performing system identification, suggesting future interfaces for logging and comparison.

