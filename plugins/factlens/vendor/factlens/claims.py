from __future__ import annotations

import re

from .models import Claim


_SENTENCE_RE = re.compile(r"[^.!?。！？\n]+(?:[.!?。！？]+|(?=\n)|$)")
_EXPLICIT_CONNECTOR_RE = re.compile(r"(?:,\s*)?(?=(?:그리고|또한|하지만|그러나)\s+)|[;；]\s*")
_SUBJECTIVE_MARKERS = (
    "좋다고 생각",
    "나쁘다고 생각",
    "가장 아름다",
    "최고라고 생각",
    "추천하고 싶",
    "느낌이 든",
    "바람직하",
    "것 같다",
)


class HeuristicClaimExtractor:
    """Dependency-free baseline extractor that always preserves source offsets."""

    def extract(self, answer: str) -> list[Claim]:
        claims: list[Claim] = []
        for sentence_match in _SENTENCE_RE.finditer(answer):
            sentence_start, sentence_end = sentence_match.span()
            raw_sentence = sentence_match.group(0)
            for local_start, local_end in self._clause_spans(raw_sentence):
                absolute_start = sentence_start + local_start
                absolute_end = sentence_start + local_end
                absolute_start, absolute_end = _trim_span(answer, absolute_start, absolute_end)
                if absolute_start >= absolute_end:
                    continue
                quote = answer[absolute_start:absolute_end]
                if not re.search(r"[0-9A-Za-z가-힣]", quote):
                    continue
                checkability = "subjective" if any(marker in quote for marker in _SUBJECTIVE_MARKERS) else "factual"
                claims.append(
                    Claim(
                        claim_id=f"c{len(claims) + 1}",
                        text=quote,
                        exact_quote=quote,
                        start=absolute_start,
                        end=absolute_end,
                        checkability=checkability,
                        importance=_importance_of(quote),
                    )
                )
        return claims

    def _clause_spans(self, sentence: str) -> list[tuple[int, int]]:
        boundaries = [0]
        for match in _EXPLICIT_CONNECTOR_RE.finditer(sentence):
            boundaries.append(match.end())

        # Korean connective endings often join two independently checkable facts.
        for match in re.finditer(r"(?:했고|하였고|였고|이며|이고|태어나)\s+(?=[0-9A-Za-z가-힣])", sentence):
            boundaries.append(match.start() + len(match.group(0).rstrip()))

        boundaries.append(len(sentence))
        ordered = sorted(set(boundaries))
        spans: list[tuple[int, int]] = []
        for start, end in zip(ordered, ordered[1:]):
            trimmed_start, trimmed_end = _trim_span(sentence, start, end)
            if trimmed_end - trimmed_start >= 2:
                spans.append((trimmed_start, trimmed_end))
        return spans


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and (text[start].isspace() or text[start] in ",;；"):
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _importance_of(text: str) -> str:
    if re.search(r"\d|반드시|금지|위험|사망|최초|유일", text):
        return "high"
    return "medium"
