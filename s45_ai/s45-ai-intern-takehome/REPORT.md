# Evaluation Pipeline Report

## What changed

I made the pipeline robust to imperfect batch input and corrected the aggregation logic. `load_records` now preserves a malformed JSON line as a skipped placeholder instead of aborting the entire run. `evaluate` validates the fields it needs (non-empty string reference answer, model answer, and category), skips invalid records, and continues with the rest of the batch. It reports both evaluated and skipped counts as required. The overall score is now a micro-average: total correct answers divided by total evaluated answers. This is the appropriate overall accuracy because each question should have equal weight. Per-category scores remain useful diagnostics, but averaging category percentages would overweight small categories.

I replaced exact string matching with a conservative normalization-based scorer. It normalizes Unicode, whitespace, case, common terminal punctuation, and unambiguous short-answer lead-ins such as “It’s ...” and “The answer is ...”. It treats equivalent decimal renderings (`83` and `83.0`) and a standalone numeric hedge such as “about 45” or “~45” as equal only when they represent exactly the reference number. The scorer intentionally does not use fuzzy matching or substring matching. For short factual answers those approaches can turn a different answer, partial answer, or answer containing a contradiction into a false positive. This implementation uses only the Python standard library and returns the required boolean/confidence shape.

## Reported Accuracy

Running the specified command on `data/predictions.jsonl` produces an overall accuracy of **74.16%**: 775 correct out of 1,045 evaluated records, with 15 malformed records skipped. The category breakdown is 85.99% easy, 73.95% medium, and 43.65% hard. The scorer agrees with all 155 occurrences represented by the provided human-labeled calibration IDs. I also ran the supplied pipeline tests; both pass.

## Scope Decision

I treat the provided `reference_answer` as the evaluation benchmark, rather than independently fact-checking answers against outside knowledge. This makes the reported number reproducible and answers the operational question “how often does the model agree with this labeled benchmark?” Some references may be factually questionable, but silently overriding them would make the scorer an undocumented second source of truth. In production, I would separately flag suspected reference errors for review and version the corrected benchmark.

## With Two More Days

I would expand the labeled set with ambiguous and adversarial examples, then measure precision and recall for each normalization rule and category. I would add unit tests for malformed JSON lines, missing fields, Unicode punctuation, numeric edge cases, and intentionally misleading near-matches. Finally, I would add an audit output containing each record's decision and normalization reason, plus confidence buckets and review sampling, so score changes can be inspected rather than treated as a single opaque number.
