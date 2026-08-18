from __future__ import annotations

import math
import re
from collections import Counter


_SPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[가-힣]{2,}|[a-zA-Z]{2,}|\d+(?:\.\d+)?")
_NUMBER_RE = re.compile(r"(?<!\d)\d+(?:[.,]\d+)*(?!\d)")


def normalize(text: str, *, mask_numbers: bool = False) -> str:
    lowered = text.casefold()
    if mask_numbers:
        lowered = _NUMBER_RE.sub(" <num> ", lowered)
    lowered = re.sub(r"[^0-9a-z가-힣<>]+", " ", lowered)
    return _SPACE_RE.sub(" ", lowered).strip()


def tokens(text: str, *, mask_numbers: bool = False) -> list[str]:
    return _TOKEN_RE.findall(normalize(text, mask_numbers=mask_numbers))


def numbers(text: str) -> set[str]:
    return {match.replace(",", "") for match in _NUMBER_RE.findall(text)}


def has_negation(text: str) -> bool:
    normalized = normalize(text)
    return bool(re.search(r"(?:아니|않|없|못하|불가능|금지)", normalized))


def character_ngrams(text: str, size: int = 2, *, mask_numbers: bool = False) -> Counter[str]:
    compact = normalize(text, mask_numbers=mask_numbers).replace(" ", "")
    if not compact:
        return Counter()
    if len(compact) < size:
        return Counter({compact: 1})
    return Counter(compact[index : index + size] for index in range(len(compact) - size + 1))


def cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def lexical_similarity(left: str, right: str, *, mask_numbers: bool = False) -> float:
    left_tokens = set(tokens(left, mask_numbers=mask_numbers))
    right_tokens = set(tokens(right, mask_numbers=mask_numbers))
    union = left_tokens | right_tokens
    token_score = len(left_tokens & right_tokens) / len(union) if union else 0.0
    char_score = cosine(
        character_ngrams(left, mask_numbers=mask_numbers),
        character_ngrams(right, mask_numbers=mask_numbers),
    )
    return min(1.0, 0.35 * token_score + 0.65 * char_score)
