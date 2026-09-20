# Pre-registration: does "never abstains" hold across model families?

Status: **registered 2026-09-20, before any cross-model code is written.** No provider backend
exists yet; writing one is the first step after this file is committed. Changes after this date are
logged at the end, with reasons, and never made after results are seen unless recorded as
deviations.

## What is already measured

On Gemini 3.8 Live, at events where the delivered evidence supports only `UNKNOWN`, the model
answered `UNKNOWN` **0 of 1,986** times in the benchmark. A
[pre-registered probe](probe_preregistration.md) then ruled out three explanations — it knows which
sensors see which faults (81% balanced accuracy), an explicit instruction to abstain moved it 0 of
14, and renaming the enum moved it 0 of 14 — and Extended Thinking at HIGH abstained 0 of 41.
Across both models: **97 answers where only `UNKNOWN` is supported, 0 abstentions.**

Both models come from one family, served by one API, in one modality (audio-output Live sessions).
So the finding is currently about *Gemini 3.8 Live*, not about language models.

## The question

**Q: Is refusing to abstain a property of this model family and its serving stack, or of frontier
assistant models in general?**

Two sub-questions follow from it, and each has a different consequence:

| | If yes | What it would mean |
| --- | --- | --- |
| **G** Generalizes | every model tested abstains on ≲10% of U items | "cannot verify" must be a system state in any agent design, not this vendor's quirk |
| **C** Convention is fixable elsewhere | some model abstains once the definition is explicit (B2) | the behaviour is trainable or promptable, and the Gemini result is about its post-training |

## Models

| Role | Model | Why |
| --- | --- | --- |
| Reference | `gemini-3.8-live` | already measured; not rerun |
| Reference | `gemini-3.8-live-extended-thinking` | already measured; not rerun |
| Within-family control | `gemini-3.8-flash-live` | same family and API, smaller model: separates family from capability |
| Cross-family | one Anthropic frontier model | different family, different serving stack |
| Cross-family | one OpenAI frontier model | as above |

Exact model ids and access dates are recorded in the results file at run time, not guessed here.
A model that cannot take a tool/function-call schema with a fixed enum is out of scope and is
recorded as such rather than approximated with free text.

## What is held fixed, and what necessarily differs

The single largest threat to this comparison is **the harness, not the models**. On 2026-09-19 a
serving-stack failure produced silence that the harness recorded as the model declining to answer,
which would have been published as a finding about the model
([deviation 7](probe_preregistration.md)). A cross-model comparison multiplies exactly that risk:
whichever model has the shakier adapter looks worse.

**Held fixed, and checked by a test before any model runs:**

- the item text, byte for byte — the same single-turn prefix (events 0…24) the Gemini probes used;
- the instruction, byte for byte — frozen prompt v4 plus the same single-turn sentence;
- the answer schema — the same field names, the same enum values, the same required fields;
- one run per item, default sampling, no retry that changes any content;
- the scoring code, which reads only the submitted enum values.

**Necessarily different, and therefore confounds to state, never to explain away:**

- **Modality.** Gemini answers in an audio-output Live session; the others answer as text. The
  evidence is text in both cases, but the response channel differs.
- **Tool-call mechanics.** Sequential calls in one turn, blocking versus asynchronous behaviour,
  and whether a model narrates before calling.
- **Reasoning budget.** Where a model exposes a thinking setting, the default is used and recorded;
  no attempt is made to equalize compute across families.

For each model, the exact request sent for one item is committed verbatim, so the parity claim can
be checked rather than trusted.

## Items

The existing 38 in-context items, unchanged and already committed
(`data/probes/items.json`): **U = 14** (only `UNKNOWN` is supported), **N = 15** (`NORMAL`),
**A = 9** (`ANOMALOUS`). N and A are guards, not decoration: a model that abstains everywhere is
not calibrated, it is silent.

## Variants

| Variant | What it is | Isolates |
| --- | --- | --- |
| **B0** | the frozen benchmark wording | the headline behaviour |
| **B2** | one sentence defining `NORMAL` and when to answer `UNKNOWN` | whether an explicit norm moves this model |
| **B1** | `report_verifiability` first, then `report_assessment` | whether it states "cannot verify" and rules anyway |

B1 requires two tool calls in one turn. A model whose API cannot do that is recorded **not run**
for B1; B1 is never re-implemented as a single merged call, because that would no longer be the
same question the Gemini result answers. B3 (enum renaming) is not run: it moved Gemini 0 of 14 and
costs a quarter of the budget.

**Per model: 38 items × 3 variants = 114 calls.**

## Measures

Per model and variant, as in the probe study:

- **abstention on U** — the share of U items answered `UNKNOWN`;
- **over-abstention on N** and **detection on A** — the two guards;
- **conflation on U** (B1 only) — said atmosphere `cannot_verify`, then committed to a verdict;
- **coverage** — answered / registered, reported beside every rate.

Differences of fewer than about 3 items are not interpreted.

## Predictions (registered)

| # | Prediction | Supports |
| --- | --- | --- |
| **Pr1** | Every model's B0 abstention on U is ≤ 10% | G |
| **Pr2** | At least one non-Gemini model exceeds 50% abstention on U under B2, while its over-abstention on N stays ≤ 20% | C |
| **Pr3** | For every model that runs B1, conflation on U is ≥ 40% | G |
| **Pr4** | No model's over-abstention on N exceeds 20% under B0 | sanity |

Pr2 is the one I expect to be wrong, and it is registered because it is the cheapest way to be
shown wrong.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Every model ≤ 10% on U under B0 | **G.** The finding is about frontier assistant models, and the product implication generalizes |
| Gemini ≤ 10% but another family abstains substantially | The Gemini result is about its post-training, not about models. The README's claim narrows to Gemini, in the same sentence that reports the difference |
| B2 works somewhere but not on Gemini | **C** holds for that family: the norm is promptable there. Reported as a difference between families, never as a fix for Gemini |
| Coverage below 90% for a model | That model's rate is reported as **not read**. No comparison is drawn from it |
| A model differs and its adapter is newer | The difference is reported **with** the parity evidence, or not reported at all |

Whatever happens, the existing Gemini results stand as measured. This study places them; it does
not revise them.

## Non-answers, coverage, and controls

Carried forward from the probe study's deviation 7, and binding here from the start:

1. **Silence is never scored.** An item with no submitted call is excluded from every rate and
   counted in coverage. It is never read as the model declining.
2. **Before recording silence, a control runs.** The same request goes to a second model on the
   same provider; if the control answers and the model under test does not, the run stops and
   nothing is saved for that item.
3. **A measure below 90% coverage is reported as "not read"**, never as a number.
4. **Provider errors are retried, up to 3 attempts, and never saved.** Error codes are recorded per
   item.

## Budget

114 calls per model, about 2.7k input tokens each and a few hundred output — roughly **0.35M input
tokens per model**, so low single-digit dollars each at current frontier pricing. **A hard cap of
US$20 for the whole study**; if it is reached, the run stops and the partial result is reported
with its coverage. Prices are read at run time and recorded with the results, not estimated here.

## What this cannot show

- **Not a capability ranking.** Nothing here measures which model is better at monitoring a
  furnace. It measures one behaviour — whether a model ever says it cannot tell — on items where
  the answer is fixed by the evidence.
- **One run per item.** The Gemini pilot was near-deterministic across seeds; other models may not
  be, and a single run cannot separate a tendency from a sample.
- **Prompt-shaped.** Every model sees wording tuned, over four versions, against Gemini. A model
  that reads it differently is a finding about the wording as much as about the model.
- **The serving stack is part of what is measured.** Where an adapter shapes the result, this file
  requires that it be reported as such.

## Deviations log

None yet. Entries are added here, with dates and reasons, as they happen.
