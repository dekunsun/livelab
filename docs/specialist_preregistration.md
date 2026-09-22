# Pre-registration: native multimodal against a specialist vision model, on the same inspections

Status: **registered 2026-09-21, before any specialist model was built or any feature
extracted.** Changes after this date are logged at the end.

## Why

[Pilot 1](results/pilot1_results.md) showed that on PDMS inspection photographs the models use the
picture: of the items they commit to, about three in four are right (57 and 74 of 100 overall),
and the labels stand up to a blind human check. It did not compare them with the alternative a lab
would actually weigh, which is a small vision model trained on the lab's own images, with or
without a language model deciding from its output.

This is the first half of the project's third question: **for a given inspection, is a native
multimodal model better, or cheaper, than a specialist vision pipeline?**

## What is already known

Registration has to say this plainly. **The native-multimodal results on the test set are already
known**: Opus 5 57 of 100, Gemini 3.8 Live 74 of 100, under pilot 1's C1 condition. The
predictions below are made knowing those numbers. The native arm is reused as collected and is
not rerun.

## Test set

Pilot 1's 100 items on 80 images: 30 matched normal/abnormal pairs, and 20 context-flip images
asked under two steps. Truth is the dataset annotation, which the owner's blind check supported
(14 of 15 agreed, none disagreed).

## Arms

| Arm | What decides | Status |
| --- | --- | --- |
| **N** | Opus 5 and Gemini, given the task context and the photograph (pilot 1, C1) | collected |
| **S** | A specialist vision model trained on this lab's images | new |
| **S+L** | Opus 5 and Gemini, given the task context and **S's output**, but not the photograph | new |

### S, the specialist

- **Features.** Image embeddings from **DINOv2 ViT-S/14**, a vision-only model with no language
  component, pretrained on natural images and used frozen. Nothing in it has seen a check or a
  label.
- **Classifier.** Each check is decided separately, by the item's `Detection_Content`. The
  classifier is **k-nearest neighbours**, with k = 5 and cosine similarity, among training
  annotations with the same check. The verdict is the majority label. S answers **UNKNOWN** when
  that check has fewer than 5 training annotations. There is one fixed setting and nothing is
  tuned on the test set.
- **Training data.** Every PDMS annotation **except**:
  - any annotation of the 80 test images;
  - any image whose embedding has cosine similarity **≥ 0.97** to any test image, a near-duplicate
    of it. PDMS repeats the same bench from the same camera, so without this the neighbour found
    could be the test image in all but name.

  The number of training annotations left, and of images excluded as near-duplicates, is reported.
  A count made before registering, from annotations only: removing the 80 test images leaves
  **2,604 training annotations**. The test set's **22 checks** have a median of 85 each, and
  none is all one label. One check has fewer than 5, which affects **1 test item**. The
  near-duplicate exclusion will reduce these counts, and the post-exclusion numbers are reported.
- **Sensitivity.** S is also reported with a stricter exclusion (cosine ≥ 0.90) and at reduced
  training sizes (10%, 25% and 50% of the eligible annotations, drawn with a fixed seed). This is
  **reported, not predicted**, except where Ps2 says otherwise.

### S+L, the specialist feeding a language model

Opus 5 and Gemini get pilot 1's instruction and task context. The photograph is replaced by one
sentence: *"An inspection classifier trained on this laboratory's past photographs judged this
check: <satisfied | not satisfied | could not judge>, with <k of 5> similar past photographs
agreeing."* This is the literal CV+LLM pipeline. The language model sees what the vision component
concluded, and decides.

## Measures

Accuracy on the 100 items (UNKNOWN is never correct, and its rate is reported beside it);
accuracy on pairs and on flip items; both-steps-right on flip images; and the **cost per
inspection** of each arm. S's cost is its compute, measured on this machine. N's and S+L's cost
is their API usage.

## Predictions (registered)

| # | Prediction |
| --- | --- |
| **Ps1** | **S is at least as accurate as the better N model** (Gemini, 74) on the 100 items. A small model trained on this lab's own photographs matches a general model that has never seen them |
| **Ps2** | At **10%** of the training data, S falls **below 74**: the specialist's advantage is bought with labelled examples |
| **Ps3** | **S+L is within 5 points of S** for both language models: given only the classifier's verdict, the language model adds little and changes little |
| **Ps4** | On flip images, S gets both steps right **at least as often as Gemini did (14 of 20)**, because it decides each check separately |

The reasoning, so that each can be wrong for a reason. PDMS photographs a small set of fixed
benches from fixed cameras, and the checks repeat. That is the setting where nearest neighbours in
a good image embedding do well, and where a general model's breadth buys least. Ps2 is the
counterweight: the specialist needs labels a lab has to collect, and the native model needs none.
If Ps1 fails, the general model is better even in the specialist's best case. That would be the
strongest result for native multimodal this project could produce on this data.

## How results will be read

| Outcome | Reading |
| --- | --- |
| Ps1 and Ps2 hold | On a repetitive inspection, a specialist trained on the lab's own photographs wins. The native model's advantage is that it needs no labelled data, and Ps2 prices that |
| Ps1 fails | The general model beats the specialist even where the specialist should be strongest |
| S+L well below S (Ps3 fails that way) | Handing a classifier's verdict to a language model loses accuracy. The pipeline's weak joint is the hand-off |
| S+L well above S | The language model corrects the classifier using the task context. That is the case for keeping it in the loop |
| Near-duplicate exclusion changes S by more than 10 points | S's accuracy is partly memory of the bench, and the stricter figure is the one reported first |

Differences under three items are not interpreted.

## Dependencies, and what they need

S needs PyTorch and the DINOv2 ViT-S/14 weights. Neither is installed. Both are downloads the
project owner approves before they happen, with sizes stated then. Everything runs on this
machine's CPU.

## Budget

S+L: 100 items × 2 models, text only. **Cap: US$3.**

## What this cannot show

- **One dataset of stills, one lab.** Nothing about time, streaming or live monitoring.
- **One specialist design.** k-NN on frozen DINOv2 is a standard and hard-to-dismiss baseline, but
  a tuned, fine-tuned model could do better. Where S wins, a better specialist would win by more.
  Where it loses, this does not show that every specialist would.
- **The native results were known before this was written.** The predictions are made in that
  knowledge, and say so.
- **S uses in-domain labels N never saw.** That is the comparison a lab faces, not an unfair
  advantage, and Ps2 measures what it costs.

## Deviations log

None yet.
