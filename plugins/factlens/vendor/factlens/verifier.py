from __future__ import annotations

from .models import Claim, ClaimResult, Evidence, Verdict
from .text import has_negation, lexical_similarity, normalize, numbers


class EvidenceVerifier:
    """Conservative lexical baseline; ambiguous cases remain INSUFFICIENT."""

    def verify(self, claim: Claim, evidence: list[Evidence]) -> ClaimResult:
        if claim.checkability != "factual":
            return ClaimResult(
                claim=claim,
                label=Verdict.UNVERIFIABLE,
                confidence=0.95,
                evidence_ids=[],
                rationale="의견·평가 표현이 포함되어 사실 판정 대상에서 제외했습니다.",
            )

        if not evidence:
            return self._insufficient(claim, "관련 근거를 찾지 못했습니다.")

        best = evidence[0]
        direct_similarity = lexical_similarity(claim.text, best.text)
        relation_similarity = lexical_similarity(claim.text, best.text, mask_numbers=True)
        claim_numbers = numbers(claim.text)
        evidence_numbers = numbers(best.text)

        number_conflict = (
            bool(claim_numbers)
            and bool(evidence_numbers)
            and claim_numbers.isdisjoint(evidence_numbers)
            and relation_similarity >= 0.42
        )
        negation_conflict = has_negation(claim.text) != has_negation(best.text) and relation_similarity >= 0.55

        if number_conflict:
            return ClaimResult(
                claim=claim,
                label=Verdict.CONTRADICTED,
                confidence=round(min(0.96, 0.62 + relation_similarity * 0.3), 3),
                evidence_ids=[best.evidence_id],
                rationale=(
                    "주장의 수치·날짜와 가장 관련 높은 근거의 값이 다릅니다. "
                    f"주장: {', '.join(sorted(claim_numbers))} / 근거: {', '.join(sorted(evidence_numbers))}"
                ),
            )

        if negation_conflict:
            return ClaimResult(
                claim=claim,
                label=Verdict.CONTRADICTED,
                confidence=round(min(0.92, 0.58 + relation_similarity * 0.28), 3),
                evidence_ids=[best.evidence_id],
                rationale="주장과 근거의 긍정·부정 관계가 서로 다릅니다.",
            )

        normalized_claim = normalize(claim.text)
        normalized_evidence = normalize(best.text)
        exact_containment = normalized_claim and normalized_claim.rstrip("다") in normalized_evidence
        same_numbers = not claim_numbers or claim_numbers.issubset(evidence_numbers)
        if same_numbers and (
            exact_containment
            or direct_similarity >= 0.58
            or (direct_similarity >= 0.39 and relation_similarity >= 0.45)
        ):
            return ClaimResult(
                claim=claim,
                label=Verdict.SUPPORTED,
                confidence=round(min(0.97, 0.62 + direct_similarity * 0.34), 3),
                evidence_ids=[best.evidence_id],
                rationale="가장 관련 높은 근거가 주장의 핵심 관계와 값을 지지합니다.",
            )

        return self._insufficient(
            claim,
            "관련 문장은 찾았지만 주장을 지지하거나 반박하기에 충분하지 않습니다.",
            evidence_id=best.evidence_id if best.score >= 0.15 else None,
        )

    @staticmethod
    def _insufficient(claim: Claim, rationale: str, evidence_id: str | None = None) -> ClaimResult:
        return ClaimResult(
            claim=claim,
            label=Verdict.INSUFFICIENT,
            confidence=0.68 if evidence_id else 0.82,
            evidence_ids=[evidence_id] if evidence_id else [],
            rationale=rationale,
            missing_information="더 직접적이고 신뢰할 수 있는 근거가 필요합니다.",
        )
