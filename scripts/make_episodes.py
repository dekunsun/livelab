"""Write the CVD episode files from one spec table, so every card has the same fields.

The `expected` answers are declared here by the author from the physics of each fault, before the
truth is computed. tests/test_episodes.py checks the computed truth against them; a mismatch is
investigated, never silently copied over.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DM = "DeepMind arXiv 2608.26701, MXene section: sealing / oxygen ingress; 3/26 -> 17/25 after O-ring replacement and exhaust flushing"
DM_EXHAUST = "DeepMind arXiv 2608.26701, MXene section: exhaust flushing restored reproducibility"
COMMON = "Common tube-furnace instrument fault; dynamics author-constructed"
MHS = "Anthropic MHS research preview: device status and disconnect failures"


def E(eog, eoc, final):
    """Expected (execution, cause) at the end of growth and end of cooldown, and final evidence."""
    return {"end_of_growth": dict(zip(("execution_state", "specific_cause"), eog)),
            "end_of_cooldown": dict(zip(("execution_state", "specific_cause"), eoc)),
            "final_scientific_evidence": final}


A, U, N = "ANOMALOUS", "UNKNOWN", "NORMAL"
SPECS = [
    # --- seal leak, low pressure (v1 is scenarios/pilot/cvd_seal_leak_lpcvd.yaml) ---
    dict(id="cvd_seal_leak_lpcvd_v2", regime="lpcvd", seed=31, image="cvd_024", src=DM,
         fault=("seal_leak", 2700, {"o2_ingress_ppm_per_min": 3.0, "pressure_rise_torr_per_min": 0.03}),
         conds={"base": [], "no_o2": ["o2_exhaust"], "no_o2_no_pressure": ["o2_exhaust", "pressure_gauge"]},
         expected={"base": E((A, "seal_leak"), (A, "seal_leak"), "INCONCLUSIVE"),
                   "no_o2": E((A, "undetermined"), (A, "undetermined"), "INCONCLUSIVE"),
                   "no_o2_no_pressure": E((U, "none"), (U, "none"), "INCONCLUSIVE")}),
    # --- seal leak, atmospheric pressure (v1 is the pilot) ---
    dict(id="cvd_seal_leak_apcvd_v2", regime="apcvd", seed=33, image="cvd_021", src=DM,
         fault=("seal_leak", 2460, {"o2_ingress_ppm_per_min": 3.0}),
         conds={"base": [], "no_o2": ["o2_exhaust"]},
         expected={"base": E((A, "seal_leak"), (A, "seal_leak"), "INCONCLUSIVE"),
                   "no_o2": E((U, "none"), (U, "none"), "INCONCLUSIVE")}),
    # --- exhaust blockage, low pressure: pressure only, O2 stays normal ---
    *[dict(id=f"cvd_exhaust_blockage_lpcvd_v{v}", regime="lpcvd", seed=seed, image=img, src=DM_EXHAUST,
           fault=("exhaust_blockage", tf, {"pressure_rise_torr_per_min": 0.03}),
           conds={"base": [], "no_o2": ["o2_exhaust"], "no_pressure": ["pressure_gauge"]},
           expected={"base": E((A, "exhaust_blockage"), (A, "exhaust_blockage"), "INCONCLUSIVE"),
                     "no_o2": E((A, "undetermined"), (A, "undetermined"), "INCONCLUSIVE"),
                     "no_pressure": E((U, "none"), (U, "none"), "INCONCLUSIVE")})
      for v, seed, tf, img in ((1, 41, 2460, "cvd_007"), (2, 43, 2700, "cvd_018"))],
    # --- thermocouple drift: heater power first, the reading itself once the heater is off ---
    *[dict(id=f"cvd_thermocouple_drift_lpcvd_v{v}", regime="lpcvd", seed=seed, image=img, src=COMMON,
           fault=("thermocouple_drift", tf, {"drift_c_per_min": 2.0}),
           conds={"base": [], "no_heater_power": ["heater_power"]},
           expected={"base": E((A, "undetermined"), (A, "thermocouple_drift"), "INCONCLUSIVE"),
                     # Without heater power the drift is invisible during growth (the loop holds the
                     # reading on setpoint): NORMAL is the evidence-supported answer there.
                     "no_heater_power": E((N, "none"), (A, "thermocouple_drift"), "INCONCLUSIVE")})
      for v, seed, tf, img in ((1, 51, 2460, "cvd_001"), (2, 53, 2700, "cvd_014"))],
    # --- stuck MFC: latent during growth (stuck at setpoint), visible when cooldown raises the setpoint ---
    *[dict(id=f"cvd_mfc_stuck_lpcvd_v{v}", regime="lpcvd", seed=seed, image=img, src=COMMON,
           fault=("mfc_stuck", tf, {}),
           conds={"base": [], "no_mfc": ["mfc_ar"]},
           expected={"base": E((N, "none"), (A, "mfc_stuck"), "INCONCLUSIVE"),
                     "no_mfc": E((N, "none"), (A, "undetermined"), "INCONCLUSIVE")})
      for v, seed, tf, img in ((1, 61, 2460, "cvd_023"), (2, 63, 2700, "cvd_019"))],
    # --- stale status: status says running, readings freeze ---
    *[dict(id=f"cvd_stale_status_lpcvd_v{v}", regime="lpcvd", seed=seed, image=img, src=MHS,
           fault=("stale_status", tf, {}),
           conds={"base": []},
           expected={"base": E((A, "stale_status"), (A, "stale_status"), "INCONCLUSIVE")})
      for v, seed, tf, img in ((1, 71, 2700, "cvd_016"), (2, 73, 2460, "cvd_010"))],
    # --- no-fault: success and negative results (v1 of each is a pilot) ---
    dict(id="cvd_nofault_apcvd_success_v2", regime="apcvd", seed=81, image="cvd_006", fault=None,
         conds={"base": [], "no_o2": ["o2_exhaust"]},
         expected={"base": E((N, "none"), (N, "none"), "SUPPORTING"),
                   "no_o2": E((U, "none"), (U, "none"), "SUPPORTING")}),
    dict(id="cvd_nofault_lpcvd_success_v3", regime="lpcvd", seed=83, image="cvd_025", fault=None,
         conds={"base": [], "no_o2_no_pressure": ["o2_exhaust", "pressure_gauge"]},
         expected={"base": E((N, "none"), (N, "none"), "SUPPORTING"),
                   "no_o2_no_pressure": E((U, "none"), (U, "none"), "SUPPORTING")}),
    dict(id="cvd_nofault_apcvd_negative_v2", regime="apcvd", seed=91, image="cvd_007", fault=None,
         conds={"base": [], "no_o2": ["o2_exhaust"]},
         expected={"base": E((N, "none"), (N, "none"), "NEGATIVE"),
                   "no_o2": E((U, "none"), (U, "none"), "INCONCLUSIVE")}),
    dict(id="cvd_nofault_lpcvd_negative_v3", regime="lpcvd", seed=93, image="cvd_016", fault=None,
         conds={"base": [], "no_o2_no_pressure": ["o2_exhaust", "pressure_gauge"]},
         expected={"base": E((N, "none"), (N, "none"), "NEGATIVE"),
                   "no_o2_no_pressure": E((U, "none"), (U, "none"), "INCONCLUSIVE")}),
]


def main():
    for s in SPECS:
        f = s["fault"]
        ep = {
            "episode_id": s["id"],
            "scientific_setting": {"domain": "cvd", "material": "MoS2 on SiO2/Si", "regime": s["regime"]},
            "protocol": "tmd_mos2_v0",
            "regime": s["regime"],
            "seed": s["seed"],
            "failure_mechanism": f[0] if f else "none",
            "fault": {"type": f[0], "t_fault_s": f[1], "params": f[2]} if f else None,
            "characterization_image": s["image"],
            "sensor_conditions": s["conds"],
            **({"source_citation": s["src"]} if f else {}),
            "telemetry_provenance": "author_constructed",
            "pairing": "constructed",
            "expected": s["expected"],
            "labels": {"rule_output": "computed", "hand_label": "pending", "labeled_by": "pending"},
            "changelog": [],
        }
        path = ROOT / "scenarios" / "cvd" / f"{s['id']}.yaml"
        path.write_text("# Generated by scripts/make_episodes.py; edit the spec there.\n" +
                        yaml.safe_dump(ep, sort_keys=False, allow_unicode=True, width=120))
    print(f"{len(SPECS)} episodes -> scenarios/cvd/")


if __name__ == "__main__":
    main()
