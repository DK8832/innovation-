from __future__ import annotations

from .models import AnalysisSummary, ClaimResult, Verdict


_WEIGHTS = {"high": 1.5, "medium": 1.0, "low": 0.6}


def summarize(results: list[ClaimResult]) -> AnalysisSummary:
    counts = {verdict: 0 for verdict in Verdict}
    for result in results:
        counts[result.label] += 1

    verifiable = len(results) - counts[Verdict.UNVERIFIABLE]
    with_evidence = sum(bool(result.evidence_ids) for result in results if result.label != Verdict.UNVERIFIABLE)

    risk_total = 0.0
    weight_total = 0.0
    for result in results:
        if result.label == Verdict.UNVERIFIABLE:
            continue
        weight = _WEIGHTS.get(result.claim.importance, 1.0)
        weight_total += weight
        if result.label == Verdict.CONTRADICTED:
            risk_total += weight * result.confidence
        elif result.label == Verdict.INSUFFICIENT:
            risk_total += weight * 0.35 * result.confidence

    return AnalysisSummary(
        total_claims=len(results),
        supported=counts[Verdict.SUPPORTED],
        contradicted=counts[Verdict.CONTRADICTED],
        insufficient=counts[Verdict.INSUFFICIENT],
        unverifiable=counts[Verdict.UNVERIFIABLE],
        support_rate=_ratio(counts[Verdict.SUPPORTED], verifiable),
        contradiction_rate=_ratio(counts[Verdict.CONTRADICTED], verifiable),
        evidence_coverage=_ratio(with_evidence, verifiable),
        risk=round(risk_total / weight_total, 4) if weight_total else None,
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
