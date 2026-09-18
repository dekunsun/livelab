"""CVD protocols: stages, setpoints and the sensors each stage requires.

The values below are ILLUSTRATIVE and author-constructed. They are placeholders until the
DeepMind 2608.26701 Appendix B.5 / E recipe values are verified; nothing here is that recipe.
"""
from dataclasses import dataclass, field

AMBIENT_C = 23.0


@dataclass(frozen=True)
class Stage:
    name: str
    duration_s: int
    t_set_end: float | None      # None = heater off (natural cooling)
    f_ar_sccm: float
    required_sensors: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class Protocol:
    protocol_id: str
    stages: tuple[Stage, ...]

    @property
    def duration_s(self) -> int:
        return sum(s.duration_s for s in self.stages)

    def stage_at(self, t: float) -> tuple[Stage, float, float]:
        """Return (stage, stage start time, setpoint at stage start) for time t."""
        start, t_prev = 0, AMBIENT_C
        for s in self.stages:
            if t < start + s.duration_s:
                return s, start, t_prev
            start += s.duration_s
            t_prev = s.t_set_end if s.t_set_end is not None else t_prev
        return self.stages[-1], start - self.stages[-1].duration_s, t_prev

    def setpoint(self, t: float) -> float | None:
        stage, start, t_from = self.stage_at(t)
        if stage.t_set_end is None:
            return None
        frac = min(1.0, (t - start) / stage.duration_s)
        return t_from + (stage.t_set_end - t_from) * frac


TMD_MOS2_V0 = Protocol(
    protocol_id="tmd_mos2_v0",
    stages=(
        Stage("purge", 600, AMBIENT_C, 200.0, ("pressure_gauge", "o2_exhaust")),
        Stage("ramp", 1800, 750.0, 100.0, ("thermocouple", "pressure_gauge")),
        Stage("growth", 900, 750.0, 100.0, ("thermocouple", "pressure_gauge", "o2_exhaust")),
        # A hot sample oxidizes in air, so atmosphere integrity still matters while cooling.
        Stage("cooldown", 3600, None, 200.0, ("thermocouple", "pressure_gauge", "o2_exhaust")),
        Stage("characterization", 60, None, 0.0, ()),
    ),
)

PROTOCOLS = {p.protocol_id: p for p in (TMD_MOS2_V0,)}
