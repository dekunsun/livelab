"""Model-directed inspection: the crop is the region asked for, the loop hands regions back and stops at
the report, the control arm differs only in the tool, and stored records carry no image bytes."""
import asyncio
import io
import json
from pathlib import Path

from PIL import Image

from livelab.inspect_tool import INSPECT, crop, inspect_item
from scripts.run_pdms_inspect import ARMS, instruction_for, items_for
from scripts.run_pdms_pilot import INSTRUCTION, PILOT, REPORT

PHOTO = PILOT / "images" / Path(items_for("flip")[0]["image"]).name


def test_crop_takes_the_asked_region_and_magnifies_it():
    jpeg, px = crop(PHOTO, {"x0": 0.5, "y0": 0.25, "x1": 0.75, "y1": 0.75})
    assert px == [320, 120, 480, 360]
    assert max(Image.open(io.BytesIO(jpeg)).size) == 1024


def test_crop_orders_clamps_and_widens_degenerate_boxes():
    _, px = crop(PHOTO, {"x0": 1.4, "y0": 0.5, "x1": -0.2, "y1": 0.5})
    assert px[0] == 0 and px[2] == 640 and px[3] - px[1] == 16


def gemini_reply(*calls):
    return {"candidates": [{"content": {"role": "model", "parts": [
        {"functionCall": {"name": n, "args": a}} for n, a in calls]}}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 10}}


def run(replies, inspect=True):
    sent = []

    def post(url, headers, body):
        sent.append(body)
        return replies[len(sent) - 1]
    rec = asyncio.run(inspect_item("gemini", "gemini-3.8-flash", "inst", REPORT, "question", PHOTO,
                                   post=post, headers={}, inspect=inspect))
    return rec, sent


def test_loop_returns_the_region_then_takes_the_report():
    rec, sent = run([gemini_reply(("inspect_region", {"x0": 0, "y0": 0, "x1": 0.5, "y1": 0.5})),
                     gemini_reply(("report_inspection", {"verdict": "NORMAL", "observations": "capped tube"}))])
    assert rec["status"] == "submitted" and rec["answer"]["verdict"] == "NORMAL"
    assert len(rec["regions"]) == 1 and rec["regions"][0]["pixels"] == [0, 0, 320, 240]
    last_user = sent[1]["contents"][-1]["parts"]
    assert "functionResponse" in last_user[0] and "inlineData" in last_user[1]
    assert "base64 chars" in json.dumps(rec["requests"])          # no image bytes stored


def test_inspections_stop_at_the_limit():
    ask = ("inspect_region", {"x0": 0, "y0": 0, "x1": 1, "y1": 1})
    rec, _ = run([gemini_reply(ask)] * 4 + [gemini_reply(("report_inspection", {"verdict": "UNKNOWN",
                                                                                 "observations": "x"}))])
    assert len(rec["regions"]) == 3 and rec["status"] == "submitted"


def test_a_report_missing_a_field_gets_a_result_and_a_reminder():
    rec, sent = run([gemini_reply(("report_inspection", {"verdict": "NORMAL"})),
                     gemini_reply(("report_inspection", {"verdict": "NORMAL", "observations": "ok"}))])
    assert rec["status"] == "submitted_after_reminder"
    assert "functionResponse" in sent[1]["contents"][-1]["parts"][0]


def test_control_arm_differs_only_in_the_tool():
    rec, sent = run([gemini_reply(("report_inspection", {"verdict": "NORMAL", "observations": "ok"}))],
                    inspect=False)
    names = [d["name"] for d in sent[0]["tools"][0]["functionDeclarations"]]
    assert names == ["report_inspection"] and rec["regions"] == []
    assert instruction_for("C1") == INSTRUCTION and instruction_for("C1I").startswith(INSTRUCTION)
    assert set(ARMS) == {"C1", "C1I"} and INSPECT["name"] == "inspect_region"
