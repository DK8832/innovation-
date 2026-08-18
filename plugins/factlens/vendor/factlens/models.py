from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True)
class ReferenceDocument:
    document_id: str
    title: str
    text: str
    url: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    exact_quote: str
    start: int
    end: int
    checkability: str
    importance: str = "medium"


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    document_id: str
    title: str
    text: str
    score: float
    url: str | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    label: Verdict
    confidence: float
    evidence_ids: list[str]
    rationale: str
    missing_information: str | None = None


@dataclass(frozen=True)
class AnalysisSummary:
    total_claims: int
    supported: int
    contradicted: int
    insufficient: int
    unverifiable: int
    support_rate: float | None
    contradiction_rate: float | None
    evidence_coverage: float | None
    risk: float | None


@dataclass(frozen=True)
class AnalysisResult:
    analysis_id: str
    mode: str
    question: str
    answer: str
    as_of: str
    claims: list[ClaimResult]
    evidence: list[Evidence]
    summary: AnalysisSummary
    warnings: list[str] = field(default_factory=list)
    pipeline_version: str = "0.1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalyzeRequest:
    question: str
    answer: str
    mode: str
    reference_texts: list[ReferenceDocument]
    as_of: str

    @classmethod
    def from_dict(cls, value: Any, *, today: str) -> "AnalyzeRequest":
        if not isinstance(value, dict):
            raise ValueError("요청 본문은 JSON 객체여야 합니다.")

        question = _bounded_string(value.get("question", ""), "question", 10_000)
        answer = _bounded_string(value.get("answer", ""), "answer", 50_000)
        if not answer.strip():
            raise ValueError("answer는 비어 있을 수 없습니다.")

        mode = value.get("mode", "document")
        if mode not in {"document", "web"}:
            raise ValueError("mode는 document 또는 web이어야 합니다.")

        raw_references = value.get("reference_texts", [])
        if not isinstance(raw_references, list):
            raise ValueError("reference_texts는 배열이어야 합니다.")
        if len(raw_references) > 20:
            raise ValueError("기준 문서는 최대 20개까지 입력할 수 있습니다.")

        references: list[ReferenceDocument] = []
        for index, item in enumerate(raw_references, start=1):
            if isinstance(item, str):
                text = _bounded_string(item, f"reference_texts[{index - 1}]", 200_000)
                references.append(
                    ReferenceDocument(
                        document_id=f"doc-{index}",
                        title=f"기준 문서 {index}",
                        text=text,
                    )
                )
                continue
            if not isinstance(item, dict):
                raise ValueError("각 기준 문서는 문자열 또는 객체여야 합니다.")
            text = _bounded_string(item.get("text", ""), f"reference_texts[{index - 1}].text", 200_000)
            if not text.strip():
                continue
            title = _bounded_string(item.get("title", f"기준 문서 {index}"), "title", 300)
            url = _optional_string(item.get("url"), "url", 2_000)
            published_at = _optional_string(item.get("published_at"), "published_at", 100)
            references.append(
                ReferenceDocument(
                    document_id=f"doc-{index}",
                    title=title.strip() or f"기준 문서 {index}",
                    text=text,
                    url=url,
                    published_at=published_at,
                )
            )

        if mode == "document" and not references:
            raise ValueError("문서 기준 모드에는 기준 문서가 한 개 이상 필요합니다.")

        as_of = _bounded_string(value.get("as_of", today), "as_of", 30).strip() or today
        return cls(
            question=question,
            answer=answer,
            mode=mode,
            reference_texts=references,
            as_of=as_of,
        )


def _bounded_string(value: Any, field_name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name}는 문자열이어야 합니다.")
    if len(value) > maximum:
        raise ValueError(f"{field_name}는 {maximum:,}자를 넘을 수 없습니다.")
    return value


def _optional_string(value: Any, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, field_name, maximum)
