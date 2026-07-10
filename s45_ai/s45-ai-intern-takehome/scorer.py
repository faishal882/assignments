"""
Decides whether a model answer is correct, given the reference answer.

The scorer deliberately supports only presentation-only differences. It does not try to
infer factual equivalence from loosely similar text, which would create false positives
for short factual answers.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation


_ANSWER_PREFIX = re.compile(
    r"^(?:(?:the )?answer(?: is|:)|(?:it is|it's)|"
    r"(?:i think|i believe)(?: the answer)?(?: is|:)|"
    r"(?:the capital is|the correct answer is))\s+",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION = re.compile(r"[\s.!?,;:]+$")
_NUMERIC_HEDGE = re.compile(r"^(?:about|around|approximately|approx\.?|~)\s*(.+)$")
_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?$")


def _normalise_answer(answer, strip_answer_prefix=False):
    """Remove non-semantic formatting commonly added to a short answer."""
    normalised = unicodedata.normalize("NFKC", answer).strip().casefold()
    if strip_answer_prefix:
        normalised = _ANSWER_PREFIX.sub("", normalised)
    normalised = _TRAILING_PUNCTUATION.sub("", normalised)
    return " ".join(normalised.split())


def _as_number(value):
    """Parse a plain decimal without accepting numeric text embedded in prose."""
    if not _NUMBER.fullmatch(value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _matches_numeric_answer(reference, answer):
    """Accept equivalent decimal rendering and an optional, standalone hedge."""
    reference_number = _as_number(reference)
    if reference_number is None:
        return False
    match = _NUMERIC_HEDGE.fullmatch(answer)
    candidate = match.group(1) if match else answer
    answer_number = _as_number(candidate)
    return answer_number is not None and answer_number == reference_number


def score(reference_answer, model_answer, question=None):
    """Return {"is_correct": bool, "confidence": float in [0,1]}.

    Keep this signature and return shape — the pipeline and the grader call it directly.
    """
    if not isinstance(reference_answer, str) or not isinstance(model_answer, str):
        return {"is_correct": False, "confidence": 0.0}

    reference = _normalise_answer(reference_answer)
    raw_answer = _normalise_answer(model_answer)
    answer = _normalise_answer(model_answer, strip_answer_prefix=True)
    if not reference or not raw_answer:
        return {"is_correct": False, "confidence": 0.0}

    is_correct = (
        raw_answer == reference
        or answer == reference
        or _matches_numeric_answer(reference, answer)
    )
    return {"is_correct": is_correct, "confidence": 1.0 if is_correct else 0.0}
