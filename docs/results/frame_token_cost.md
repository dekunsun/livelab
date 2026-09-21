# What one frame costs, and what continuous watching costs

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

| Cadence | Frames/hour | `claude-opus-5` @ 640x480 | `gpt-6-astra` @ 640x480 | Gemini Live video |
| --- | --- | --- | --- | --- |
| every 120 s | 30 | $0.06 | $0.11 | $0.12 |
| every 30 s | 120 | $0.25 | $0.43 | $0.12 |
| every 5 s | 720 | $1.50 | $2.60 | $0.12 |
| every 1 s | 3,600 | $7.51 | $13.00 | $0.12 |

**The gap is a function of how often you look, not of the architecture.** At the
benchmark's own 120 s cadence the two are comparable, and per-frame is in fact cheaper; at 1 Hz it
costs 60x (Opus 5) to 110x (Astra) more. That is the same parameter that decides whether a
transient is observable at all
([undersampling](undersampling_results.md)), so the architecture question and the
observability question are one question.

**What this does not include.** Only the image is counted: a real protocol also
resends text and context, which pushes the per-frame route higher. Against that, a
Live session carries a roughly 10-minute limit, needs resumption, and prices audio
and text separately. And neither column is the cheapest architecture — a detector at
the edge that escalates only what it flags sends almost no frames at all.
