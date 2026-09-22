# Pilot 2: can a person see a state in a CAXTON clip without the log?

Registered before any clip was chosen: [pilots_preregistration.md](../pilots_preregistration.md).
Fourteen clips of ten consecutive nozzle-camera frames, shuffled, shown with no parameters. That
is 9 flagged (8, plus one repeat) from the prints the authors excluded for large failures or poor
lighting, and 5 nominal (4, plus one repeat) from print 0 with every logged setting within 5% of
nominal (deviation 2). The reviewer is the project owner: a materials background, no experience
with these printers, judging as a non-expert (deviation 4). Their records are in
`results/review_raw/`. The clip-to-print key, kept out of the repository until the review was
done, is now in `results/pilot2/key.json`.

## The stop conditions, as registered

| # | Condition (CAXTON stops if it holds) | Observed | Holds? |
| --- | --- | --- | --- |
| 1 | Fewer than 4 of the 8 flagged clips get a medium- or high-confidence tag of *material built up* or *strings* | **6 of 8** (clips 02, 04, 05, 07, 08, 13) | no |
| 2 | **No** nominal clip is tagged *visible deposition* at medium or high confidence | **0 of 4** tagged it | **yes** |
| 3 | More than half of confident judgements revised once the log is shown | not run; condition 2 already decides | — |

**Condition 2 holds, so CAXTON leaves the line of zero-shot fault judgement**, as registered.
It is not rescued with more extreme examples.

## What the reviewer saw

- **Flagged clips mostly look wrong, and in ways a non-expert can name.** Six of eight carry
  material built up at the nozzle or strings, at medium or high confidence. Print 190 was shown
  twice and described the same way both times: a blob of material on the nozzle tip and sides,
  with loops hanging from it. One flagged clip (print 185) was too dark to judge, and one
  (print 183) looked like ordinary deposition.
- **The nominal clips do not make a clean control.** None was tagged *visible deposition*. Two
  (clips 10, 11) were described in the notes as continuous, orderly lines with no blobs, strings or
  loops, which is what normal deposition looks like, but that tag was not ticked. **They are not
  counted as tagged**, because re-reading the notes after seeing the result would be the move the
  registration exists to prevent. Two more nominal showings were tagged *strings*: clip 09, and
  the repeat of clip 01.
- **Consistency on repeats: one of two.** The print 190 clip got the same states and confidence
  both times. The nominal clip shown twice was tagged *too dark or blurred* the first time and
  *strings* the second.

## Reading

CAXTON's flagged prints do contain failures a non-expert can see without the log. That is worth
recording. What the pilot could not establish is a visual normal: strings and thin threads
appear in nominal-log clips too, and the only nominal clips available are from one print's first
minute. Without a normal that can be told apart from the flagged clips, a zero-shot "is this run
failing?" test on CAXTON would score a model against a boundary the reference judgement cannot
draw either.

So CAXTON stays in the project for what it answers well: whether a vision model reads process
settings from the picture, the question its authors built it for, where the log is the truth.

## What this cannot show

- **One reviewer, not an expert, on 14 clips**, some from the same print. None of these counts are
  rates.
- **The nominal pool was thin by construction**: four clips from the first minute of the first
  layer of one print (deviation 2). A normal control drawn from later layers of more prints might
  have separated better. The registration did not allow widening it, and this pilot does not claim
  it would.
