# What one frame costs, and what continuous watching costs

> **Correction (2026-09-21): the streaming column is not comparable, and the crossover drawn
> from it is withdrawn.** The Gemini Live figure is the list price for video input alone, a flat
> $0.002 a minute. It leaves out what a Live session also bills. Every turn re-bills the context
> held so far, and our sessions switched context compression off, so a benchmark replay reached
> 0.4–0.5M cumulative prompt tokens. Responses are billed too. The per-frame columns, meanwhile,
> assume a judgment on every frame, while the streaming column assumes watching without
> answering. The two sides were never held to the same answer rate, detection, false-alert rate
> or deadline, so neither the crossover (one frame every 63–108 s) nor "12× cheaper at 5 s" is
> supported. The per-frame token counts in the first table are measurements and stand.

Measured by `scripts/measure_frame_tokens.py`: one request with a frame, one without,
difference taken. The images are flat test patterns generated for the measurement —
they are a ruler, not evidence.

| Model | Frame | Baseline tokens | With frame | **Per frame** |
| --- | --- | --- | --- | --- |
| `claude-opus-5` | 320x240 | 17 | 128 | **111** |
| `claude-opus-5` | 640x480 | 17 | 434 | **417** |
| `claude-opus-5` | 1280x720 | 17 | 1,216 | **1,199** |
| `gpt-6-astra` | 320x240 | 14 | 111 | **97** |
| `gpt-6-astra` | 640x480 | 14 | 375 | **361** |
| `gpt-6-astra` | 1280x720 | 14 | 1,119 | **1,105** |

## One hour of watching

Frames per hour by cadence, times tokens per frame, times the model's input price.
Gemini Live streams video at a per-minute price instead, so its column is flat.

| Cadence | Frames/hour | `claude-opus-5` @ 640x480 | `gpt-6-astra` @ 640x480 | Gemini Live video, list price only (not comparable) |
| --- | --- | --- | --- | --- |
| every 120 s | 30 | $0.06 | $0.11 | $0.12 |
| every 30 s | 120 | $0.25 | $0.43 | $0.12 |
| every 5 s | 720 | $1.50 | $2.60 | $0.12 |
| every 1 s | 3,600 | $7.51 | $13.00 | $0.12 |

**What the table does show.** The per-frame routes scale linearly with how often you look: at
640x480, one hour costs $0.06 (Opus 5) at 120 s and $7.51 at 1 Hz. What a streaming session
costs at the same answer rate, with the same history held and the same accuracy, was not
measured, so this page does not say which architecture is cheaper at any cadence.

**What this does not include.** Only the image is counted: a real protocol also
resends text and context, which pushes the per-frame route higher. Against that, a
Live session carries a roughly 10-minute limit, needs resumption, and prices audio
and text separately. And neither column is the cheapest architecture — a detector at
the edge that escalates only what it flags sends almost no frames at all.
