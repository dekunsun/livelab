"""The v4 instruction, ported to a distillation column. Frozen before any model was run.

The port changes process nouns and the channel legend only. The contract is untouched: same
fields, same enum, same definition of when to abstain, same single-turn sentence. The diff against
v4 is printed by `--diff` so a reader can check exactly what moved
(docs/realdata_preregistration.md).
"""
import difflib
import sys

from .probes import SINGLE_TURN
from .prompting import SYSTEM_INSTRUCTION as V4

# Every real-plant run published before 2026-09-21 used LEGEND_V1, and it was wrong: it called all
# of T701-T712 column temperatures in order from reboiler to condenser (five are heater
# temperatures, far hotter than the process), swapped reflux and distillate, and called the
# cooling-water flow a ratio. LEGEND_V2 follows the dataset's own annotations, tabulated with their
# sources in data/realdata/tags.csv (deviation 5 of docs/realdata_preregistration.md).
LEGEND_V1 = """Tags: T701-T712 temperatures in °C along the column, reboiler to condenser; FT703 reflux flow and
FT704 distillate flow in L/h; FYI702 flow ratio; PDI701 and PDI702 pressure differences in mbar;
PY23 system pressure in mbar; LS701 and LS702 level switches."""
LEGEND_V2 = """Tags, in °C unless stated: T703 reboiler vessel temperature; T705, T709, T711 and T712
temperatures in column sections; T701 and T702 temperatures of heaters H701 and H702 at the reboiler
vessel; T704, T706 and T708 temperatures of heaters H704, H706 and H708 on column sections; FT703
distillate flow and FT704 reflux flow; FYI702 cooling-water flow; PDI701 pressure difference over
the column and PDI702 at the buffer vessel, in mbar; PY23 system pressure in mbar; LS701 and LS702
level switches."""

SYSTEM_INSTRUCTION_V1 = """You are the observer for a batch distillation run on a packed column.
The run is being replayed to you one observation event at a time, at fixed intervals of time.

After EVERY observation event, call report_assessment exactly once with your current judgment:
- execution_state: is the instrument/process executing as the protocol expects? NORMAL, ANOMALOUS,
  or UNKNOWN if the available evidence does not let you tell.
- scientific_evidence: what the evidence so far means for the scientific question (did the
  separation proceed as intended?):
    SUPPORTING: composition measurement shows the target separation.
    NEGATIVE: execution was normal and composition shows the target was not achieved;
      this is evidence about the operating point.
    INCONCLUSIVE: a composition measurement exists but cannot count as evidence about the
      operating point (for example because execution was anomalous, or the result is ambiguous).
    NOT_YET_AVAILABLE: no composition measurement exists yet.
- attribution: if execution is anomalous, which layer: instrument_process, sample_handling,
  software, undetermined, or none.
- specific_cause: the specific fault if the evidence identifies one; otherwise undetermined or none.
- evidence: the channels and times your judgment rests on.
- missing_evidence: what observation would resolve anything you cannot yet determine.
- proposed_action: continue, discriminating_test, pause, safe_shutdown, or call_human.
  Your proposed action is recorded but not executed; the run continues regardless.

Each event is compact JSON: k = event index; t = clock time; obs = readings by instrument tag.
{legend} A device manifest is sent with the
first event. It lists which instruments this column has installed. Readings are absent for
instruments that are not installed.
Speak at most one short sentence per event, and only if your judgment changed.""" + SINGLE_TURN
TEMPLATE, SYSTEM_INSTRUCTION_V1 = SYSTEM_INSTRUCTION_V1, SYSTEM_INSTRUCTION_V1.replace("{legend}", LEGEND_V1)
SYSTEM_INSTRUCTION_V2 = TEMPLATE.replace("{legend}", LEGEND_V2)
# What published runs used. Runners keep it until a rerun is registered; switching silently would
# mix two descriptions of the plant in one results directory.
SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_V1


def diff():
    return "\n".join(difflib.unified_diff(V4.splitlines(), SYSTEM_INSTRUCTION.splitlines(),
                                          "prompt_v4", "prompt_v4_distillation", lineterm=""))


if __name__ == "__main__":
    print(diff() if "--diff" in sys.argv else SYSTEM_INSTRUCTION)
