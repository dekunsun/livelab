# LiveLab Core: evaluation settings

Every Core run, one row per run folder, generated from the run records by `scripts/make_eval_settings.py`; never edited by hand. Results: [leaderboard](results/core_leaderboard.md). Registrations: one per study in `docs/`.

**Common to every run.** 80 frozen public items (30 hidden twins, 30 visible twins, 10 normal runs, 10 full-sensor faults); one run per item per folder (`.repN` = repeat N); temperature never set, so each provider's default applies; every request and response saved. The private hold-out is not listed and has not been run for any reported result.

**Runner v1** (`scripts/run_core.py`): records keep only the model and the final usage, so the call mode, cap and provider below are the runner's documented defaults, not read from each record: forced function call unless the run ends in `.auto`; 1,024-token output cap on Anthropic requests, which cut 128 Claude answers ([limitations](core_runner_v1_limitations.md)); Gemini 3.8 Live through a Live API session. **Runner v2** (`scripts/run_core_v2.py`): every field below is read from the records; up to two reminders for a missing submission; a missing submission is scored as wrong. The 8,192 output cap applies to Anthropic requests only; other providers use their default.

**Arms.** V0 nothing stated; V1 the gap stated; V1R remedy wording; B1 verifiability probe first; V1S the scoring rules stated.

**Spend** is estimated from saved token counts at the list prices in `scripts/run_core.py` (output includes reasoning tokens); billed amounts are in each registration's deviation log.

| Model | Run | Runner | Provider / endpoint | Call | Output cap | Records | Assessments returned | Items needing a reminder | Input tokens | Output tokens | Est. spend (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| claude-opus-5 | B1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 353,153 | 42,372 | 2.83 |
| claude-opus-5 | V0 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 333,633 | 34,914 | 2.54 |
| claude-opus-5 | V1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 338,993 | 38,042 | 2.65 |
| claude-opus-5 | V1.auto | v1 | anthropic | auto | 1,024 | 80 | 80 | — | 329,393 | 63,067 | 3.22 |
| claude-opus-5 | V1.rep1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 338,993 | 37,503 | 2.63 |
| claude-opus-5 | V1.rep1.auto | v1 | anthropic | auto | 1,024 | 80 | 80 | — | 329,393 | 62,865 | 3.22 |
| claude-opus-5 | V1.rep2 | v1 | anthropic | forced | 1,024 | 73 | 73 | — | 308,767 | 34,317 | 2.40 |
| claude-opus-5 | V1.rep2.auto | v1 | anthropic | auto | 1,024 | 80 | 80 | — | 329,393 | 62,468 | 3.21 |
| claude-opus-5 | V1R | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 340,433 | 37,696 | 2.64 |
| claude-opus-5-5 | B1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 343,073 | 77,667 | 2.93 |
| claude-opus-5-5 | V0 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 324,193 | 66,072 | 2.62 |
| claude-opus-5-5 | V1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 329,553 | 71,825 | 2.75 |
| claude-opus-5-5 | V1.rep1 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 329,553 | 73,477 | 2.79 |
| claude-opus-5-5 | V1.rep2 | v1 | anthropic | forced | 1,024 | 80 | 80 | — | 329,553 | 72,029 | 2.76 |
| gemini-3.1-pro-preview | B1 | v1 | gemini | forced | provider default | 80 | 80 | — | 516,435 | 91,006 | 2.12 |
| gemini-3.1-pro-preview | V0 | v1 | gemini | forced | provider default | 80 | 80 | — | 230,391 | 66,482 | 1.26 |
| gemini-3.1-pro-preview | V1 | v1 | gemini | forced | provider default | 80 | 80 | — | 236,385 | 89,010 | 1.54 |
| gemini-3.8-flash | B1 | v1 | gemini | forced | provider default | 80 | 80 | — | 548,270 | 159,723 | 1.01 |
| gemini-3.8-flash | V0 | v1 | gemini | forced | provider default | 80 | 80 | — | 230,391 | 137,318 | 0.69 |
| gemini-3.8-flash | V1 | v1 | gemini | forced | provider default | 80 | 80 | — | 249,386 | 356,349 | 1.52 |
| gemini-3.8-live | B1 | v1 | gemini live session | session | provider default | 80 | 80 | — | 205,252 | 1,656 | free tier |
| gemini-3.8-live | V0 | v1 | gemini live session | session | provider default | 80 | 80 | — | not saved | not saved | free tier |
| gemini-3.8-live | V1 | v1 | gemini live session | session | provider default | 80 | 80 | — | not saved | not saved | free tier |
| gpt-6-astra | B1 | v1 | openai_responses | forced | provider default | 80 | 80 | — | 413,198 | 26,581 | 5.46 |
| gpt-6-astra | V0 | v1 | openai_responses | forced | provider default | 80 | 80 | — | 196,067 | 24,227 | 3.17 |
| gpt-6-astra | V1 | v1 | openai_responses | forced | provider default | 80 | 80 | — | 199,297 | 25,010 | 3.24 |
| gpt-6-astra | V1.rep1 | v1 | openai_responses | forced | provider default | 80 | 80 | — | 199,297 | 25,263 | 3.26 |
| gpt-6-astra | V1.rep2 | v1 | openai_responses | forced | provider default | 80 | 80 | — | 199,297 | 25,218 | 3.25 |
| gpt-6-astra | V1R | v1 | openai_responses | forced | provider default | 80 | 80 | — | 200,167 | 25,514 | 3.28 |
| claude-opus-5-5 | V1.auto | v2 | anthropic | auto | 8,192 | 80 | 80 | 0 | 735,458 | 98,821 | 4.92 |
| claude-opus-5-5 | V1.rep1.auto | v2 | anthropic | auto | 8,192 | 80 | 80 | 0 | 735,349 | 98,916 | 4.92 |
| claude-opus-5-5 | V1.rep2.auto | v2 | anthropic | auto | 8,192 | 80 | 80 | 0 | 737,228 | 100,881 | 4.97 |
| claude-opus-5-5 | V1S.auto | v2 | anthropic | auto | 8,192 | 80 | 80 | 0 | 828,369 | 87,745 | 5.07 |
| gemini-3.1-pro-preview | V1.auto | v2 | gemini | auto | provider default | 80 | 76 | 0 | 615,814 | 100,840 | 2.44 |
| gemini-3.1-pro-preview | V1S.auto | v2 | gemini | auto | provider default | 80 | 79 | 0 | 639,725 | 97,289 | 2.45 |
| gemini-3.8-flash | V1.auto | v2 | gemini | auto | provider default | 80 | 80 | 1 | 799,793 | 327,939 | 1.83 |
| gemini-3.8-live | V1.auto | v2 | gemini_live | session | provider default | 80 | 80 | 0 | 277,181 | 9,973 | free tier |
| gpt-6-astra | V1 | v2 | openai_responses | forced | provider default | 80 | 80 | 0 | 425,494 | 97,477 | 9.13 |
| gpt-6-astra | V1S | v2 | openai_responses | forced | provider default | 80 | 80 | 0 | 483,754 | 93,430 | 9.51 |
| z-ai/glm-5.3-flash | V1.auto | v2 | openrouter | auto | provider default | 80 | 79 | 0 | 682,703 | 225,937 | 0.22 |
| z-ai/glm-5.3-flash | V1S.auto | v2 | openrouter | auto | provider default | 80 | 80 | 0 | 740,208 | 247,754 | 0.23 |
