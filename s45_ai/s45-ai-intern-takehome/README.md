# S45 AI Engineer Intern — Take-Home

The full brief was in your email. This repo is the starting point. Short version:

A teammate built a **rough first cut** of a pipeline to answer *"how accurate is our model at
answering user questions?"* — it loads model answers, scores each against a reference, and reports
an overall accuracy. **Get it producing a correct accuracy report, improve the scorer, and write
up what you did.**

## What's here
```
pipeline.py             # loads data, scores, aggregates, reports the accuracy
scorer.py               # decides if one answer is correct. Currently: exact string match.
data/predictions.jsonl  # {id, question, reference_answer, model_answer, category}
data/labeled_dev.jsonl  # a small human-labeled sample: {id, is_correct}
tests/test_pipeline.py  # checks that capture the behavior the pipeline should have
```

## The three parts
1. **Get it running** — run it and get a correct accuracy report through the run contract. The
   checks in `tests/` capture the behavior the pipeline should have — treat them as the spec.
2. **Scorer** — improve `scorer.py` so it agrees with human judgment (calibrate on
   `labeled_dev.jsonl`). Simpler is not penalized. No paid API keys.
3. **Report** — write `REPORT.md` (≈300–500 words, readable): what you changed, the accuracy
   you'd report, your open-scoping-decision call, and what you'd do with two more days.

## Run contract (graded automatically — keep these keys and types exactly)
```
python pipeline.py --in data/predictions.jsonl --out results.json
```
```json
{ "overall_score": 0.0, "num_evaluated": 0, "num_skipped": 0, "per_category": { "<category>": 0.0 } }
```

## Run the tests
```
python tests/test_pipeline.py       # or:  pytest tests/
```

## Deliver — modify this folder and send it back
Edit `pipeline.py` and `scorer.py` **in place**, add **`REPORT.md`** at the root, keep the
folder structure (`data/`, `tests/`), then **zip the whole folder back and reply to the email**.
Return the folder we sent you, populated — not a fresh repo or a link. If you used AI tools,
that's fine — if you're shortlisted, you'll walk through your code and report live, so submit only
what you can explain.

**Timeline:** shared evening of 8 July, due **midnight 10 July (IST)**. Please commit to the
deadline; if genuinely blocked, tell us before it passes.

*Environment: Python 3.10+. Standard library is enough; if you add a package, include a
`requirements.txt` and keep it lightweight.*
