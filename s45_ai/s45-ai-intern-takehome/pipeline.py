"""
Evaluation pipeline: load model answers, score each against its reference, and report an
overall accuracy plus a per-category breakdown.

Run:
    python pipeline.py --in data/predictions.jsonl --out results.json

A rough first cut — see the README / brief for what to do with it.
"""
import argparse
import json
from collections import defaultdict

import scorer


def load_records(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    # Keep one placeholder so evaluation counts the bad input as skipped.
                    records.append(None)
    return records


def evaluate(records, score_fn=scorer.score):
    """Score every record and aggregate into the results contract."""
    total = defaultdict(int)
    correct = defaultdict(int)
    num_evaluated = 0
    num_skipped = 0

    for r in records:
        # A bad row must not prevent the remaining batch from being reported.
        try:
            reference_answer = r["reference_answer"]
            model_answer = r["model_answer"]
            category = r["category"]
            if not all(isinstance(value, str) and value.strip()
                       for value in (reference_answer, model_answer, category)):
                raise ValueError("missing or invalid answer/category")

            result = score_fn(reference_answer, model_answer, r.get("question"))
            if not isinstance(result, dict) or not isinstance(result.get("is_correct"), bool):
                raise ValueError("invalid scorer result")
        except (KeyError, TypeError, ValueError, AttributeError):
            num_skipped += 1
            continue

        num_evaluated += 1
        total[category] += 1
        if result["is_correct"]:
            correct[category] += 1

    per_category = {c: correct[c] / total[c] for c in total}
    overall = sum(correct.values()) / num_evaluated if num_evaluated else 0.0

    return {
        "overall_score": overall,
        "num_evaluated": num_evaluated,
        "num_skipped": num_skipped,
        "per_category": per_category,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="predictions .jsonl")
    ap.add_argument("--out", dest="out", required=True, help="output results .json")
    args = ap.parse_args()

    records = load_records(args.inp)
    results = evaluate(records)

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
