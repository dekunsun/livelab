"""Replay one probe item and log EVERY raw message the Live API sends back.

The runner records function calls and transcription only, so an API-side failure is invisible to
it: no call is emitted, the server tells the client nothing, and the model says "a system error
occurred" (pre-registration, deviation 7). This prints the whole stream instead, which is how that
failure was identified. Pass a model to compare two of them on the identical request.

  ./.venv/bin/python scripts/diagnose_live_stream.py B0 <item_id> [model]
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from livelab.backends import load_dotenv  # noqa: E402
from livelab.probes import prefix_message, variant_setup  # noqa: E402
from livelab.prompting import tools_for  # noqa: E402

MODEL = "gemini-3.8-live-extended-thinking"        # sys.argv[3] overrides


async def main(variant, item_id, model=MODEL):
    from google import genai
    from google.genai import types
    load_dotenv()
    items = json.load(open(ROOT / "data/probes/items.json"))
    item = next(i for i in items["in_context"] if i["item_id"] == item_id)
    instruction, tools, required = variant_setup(variant)
    text = prefix_message(item["replay_id"], item["k"])
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"], system_instruction=instruction,
        tools=[{"function_declarations": tools_for(model, tools)}],
        output_audio_transcription={}, seed=0,
        **({"thinking_config": types.ThinkingConfig(thinking_level="HIGH")}
           if "extended" in model else {}))
    client = genai.Client()
    log, calls = [], []
    async with client.aio.live.connect(model=model, config=config) as session:
        await session.send_client_content(turns={"role": "user", "parts": [{"text": text}]}, turn_complete=True)
        t0 = asyncio.get_running_loop().time()
        stream = session.receive().__aiter__()
        while asyncio.get_running_loop().time() - t0 < 300:
            try:
                msg = await asyncio.wait_for(stream.__anext__(), 90)
            except (StopAsyncIteration, asyncio.TimeoutError) as exc:
                log.append({"end": type(exc).__name__, "t": round(asyncio.get_running_loop().time() - t0, 1)})
                print("STREAM END:", type(exc).__name__, flush=True)
                break
            d = msg.model_dump(exclude_none=True)
            d.pop("data", None)                       # raw audio bytes
            sc = d.get("server_content") or {}
            if isinstance(sc.get("model_turn"), dict):
                for p in sc["model_turn"].get("parts", []):
                    p.pop("inline_data", None)
            d["t"] = round(asyncio.get_running_loop().time() - t0, 1)
            log.append(d)
            print(json.dumps(d, default=str)[:700], flush=True)
            if getattr(msg, "tool_call", None):
                for fc in msg.tool_call.function_calls:
                    calls.append(fc.name)
                    await session.send_tool_response(function_responses=[types.FunctionResponse(
                        id=fc.id, name=fc.name, response={"result": "recorded"})])
                if not [r for r in required if r not in calls]:
                    break
    out = ROOT / f"results/diagnostics/{model}__{variant}__{item_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=1, default=str))
    print(f"\ncalls: {calls}\nfull log: {out}")


asyncio.run(main(*sys.argv[1:]))
