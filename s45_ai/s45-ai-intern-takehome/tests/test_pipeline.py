"""
These tests capture the behavior the pipeline should have. Run them and make sure they pass —
without weakening what they check.

Run either way:
    python tests/test_pipeline.py        # plain
    pytest tests/                        # if you prefer pytest
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pipeline


def test_skips_malformed_without_crashing():
    # one clean record + one malformed (model_answer is null). The pipeline must not crash;
    # it should skip the bad record and keep going.
    records = [
        {"id": "a", "question": "q", "reference_answer": "Paris",
         "model_answer": "Paris", "category": "easy"},
        {"id": "b", "question": "q", "reference_answer": "Rome",
         "model_answer": None, "category": "easy"},
    ]
    res = pipeline.evaluate(records)
    assert res["num_skipped"] == 1
    assert res["num_evaluated"] == 1


def test_overall_score_is_micro_average():
    # easy: 3/3 correct (100%). hard: 0/1 correct (0%).
    # overall accuracy across all questions is 3/4 = 0.75 (micro), NOT mean(1.0, 0.0) = 0.5.
    records = [
        {"id": "1", "question": "", "reference_answer": "x", "model_answer": "x", "category": "easy"},
        {"id": "2", "question": "", "reference_answer": "y", "model_answer": "y", "category": "easy"},
        {"id": "3", "question": "", "reference_answer": "z", "model_answer": "z", "category": "easy"},
        {"id": "4", "question": "", "reference_answer": "a", "model_answer": "b", "category": "hard"},
    ]
    res = pipeline.evaluate(records)
    assert abs(res["overall_score"] - 0.75) < 1e-9


if __name__ == "__main__":
    failed = False
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_"):
            try:
                _fn()
                print("PASS", _name)
            except Exception as e:
                failed = True
                print("FAIL", _name, "->", repr(e))
    sys.exit(1 if failed else 0)
