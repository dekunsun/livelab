"""Instrument simulator for a single-zone tube furnace. It simulates the instrument, never the material.

Normal dynamics and fault dynamics are author-constructed. Fault *types* cite documented
incidents (see the episode files); the curve shapes do not come from any real run.
"""
import math
from dataclasses import dataclass

import numpy as np

from .protocol import AMBIENT_C, Protocol

CHANNELS = ("T_tc", "P_heater", "F_Ar", "P_tube", "O2_exhaust")
SENSOR_OF = {"T_tc": "thermocouple", "P_heater": "heater_power", "F_Ar": "mfc_ar",
             "P_tube": "pressure_gauge", "O2_exhaust": "o2_exhaust"}
NOISE = {"T_tc": 0.3, "P_heater": 0.5, "F_Ar": 0.5, "P_tube": None, "O2_exhaust": 1.0}

# Furnace thermal model: dT/dt = A*u - B*(T - T_amb), u in [0, 1].
B = 1 / 1500.0                     # natural cooling time constant 25 min
A = B * (750 - AMBIENT_C) / 0.45   # ~45% heater power holds 750 C
KP, KI = 0.02, 2e-4
O2_AIR_PPM, O2_PURGE_TAU_S = 2.09e5, 60.0


@dataclass(frozen=True)
class Fault:
    type: str            # seal_leak | exhaust_blockage | thermocouple_drift | mfc_stuck | stale_status
    t_fault_s: int
    params: dict


def simulate(protocol: Protocol, regime: str, seed: int, fault: Fault | None = None) -> dict:
    """Return 1 Hz traces for every channel, plus setpoints and status."""
    rng = np.random.default_rng(seed)
    n = protocol.duration_s
    # Run-to-run variability, so reference bands are realistic rather than noise-only.
    t_amb = AMBIENT_C + rng.normal(0, 1.0)
    gain = A * (1 + rng.normal(0, 0.02))
    p_base = rng.normal(2.0, 0.05) if regime == "lpcvd" else rng.normal(760.0, 0.5)
    o2_base = max(1.0, rng.normal(5.0, 1.0))
    p = dict(fault.params) if fault else {}

    out = {c: np.empty(n) for c in CHANNELS}
    out["T_set"] = np.full(n, np.nan)
    out["F_Ar_set"] = np.empty(n)
    out["status"] = np.array(["running"] * n, dtype=object)
    noise = {c: rng.normal(0, 1, n) for c in CHANNELS}
    temp, integ, flow = t_amb, 0.0, 0.0
    for t in range(n):
        stage, _, _ = protocol.stage_at(t)
        t_set = protocol.setpoint(t)
        f_set = stage.f_ar_sccm
        since = t - fault.t_fault_s if fault and t >= fault.t_fault_s else None

        drift = p.get("drift_c_per_min", 0.5) * since / 60 if since is not None and fault.type == "thermocouple_drift" else 0.0
        reading = temp + drift
        if t_set is None:
            u = 0.0
        else:
            err = t_set - reading
            ff = B * (t_set - t_amb) / gain
            u_raw = ff + KP * err + KI * integ
            u = min(1.0, max(0.0, u_raw))
            if u == u_raw:
                integ += err
        temp += gain * u - B * (temp - t_amb)

        if not (since is not None and fault.type == "mfc_stuck"):
            flow += (f_set - flow) / 5.0

        pressure = p_base + (0.01 * flow if regime == "lpcvd" else 0.002 * flow)
        o2 = o2_base + O2_AIR_PPM * math.exp(-t / O2_PURGE_TAU_S)
        if since is not None and fault.type == "seal_leak":
            o2 += p.get("o2_ingress_ppm_per_min", 3.0) * since / 60
            if regime == "lpcvd":
                pressure += p.get("pressure_rise_torr_per_min", 0.01) * since / 60
        if since is not None and fault.type == "exhaust_blockage":
            pressure += p.get("pressure_rise_torr_per_min", 0.01 if regime == "lpcvd" else 0.5) * since / 60

        out["T_tc"][t] = reading + NOISE["T_tc"] * noise["T_tc"][t]
        out["P_heater"][t] = max(0.0, 100 * u + NOISE["P_heater"] * noise["P_heater"][t])
        out["F_Ar"][t] = flow + NOISE["F_Ar"] * noise["F_Ar"][t]
        out["P_tube"][t] = (pressure * (1 + 0.005 * noise["P_tube"][t]) if regime == "lpcvd"
                            else pressure + 0.3 * noise["P_tube"][t])
        out["O2_exhaust"][t] = o2 + NOISE["O2_exhaust"] * noise["O2_exhaust"][t]
        out["T_set"][t] = np.nan if t_set is None else t_set
        out["F_Ar_set"][t] = f_set

    if fault and fault.type == "stale_status":
        for c in CHANNELS:
            out[c][fault.t_fault_s:] = out[c][fault.t_fault_s - 1]
    return out
