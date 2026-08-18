from __future__ import annotations

import uuid

from .claims import HeuristicClaimExtractor
from .models import AnalysisResult, AnalyzeRequest, Evidence
from .retrieval import DocumentRetriever
from .scoring import summarize
from .verifier import EvidenceVerifier


class AnalysisPipeline:
    def __init__(
        self,
        extractor: HeuristicClaimExtractor | None = None,
        retriever: DocumentRetriever | None = None,
        verifier: EvidenceVerifier | None = None,
    ) -> None:
        self.extractor = extractor or HeuristicClaimExtractor()
        self.retriever = retriever or DocumentRetriever()
        self.verifier = verifier or EvidenceVerifier()

    def analyze(self, request: AnalyzeRequest) -> AnalysisResult:
        if request.mode == "web":
            raise NotImplementedError("웹 검증 모드는 다음 구현 단계에서 연결됩니다.")

        claims = self.extractor.extract(request.answer)
        claim_results = []
        evidence_by_id: dict[str, Evidence] = {}
        for claim in claims:
            evidence = self.retriever.retrieve(claim, request.reference_texts)
            result = self.verifier.verify(claim, evidence)
            claim_results.append(result)
            for item in evidence:
                evidence_by_id[item.evidence_id] = item

        warnings = [
            "현재 판정기는 설치 없는 데모용 보수적 기준선입니다. 중요한 결정에는 사람의 확인이 필요합니다."
        ]
        if not claims:
            warnings.append("검증할 수 있는 문장을 찾지 못했습니다.")

        return AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            mode=request.mode,
            question=request.question,
            answer=request.answer,
            as_of=request.as_of,
            claims=claim_results,
            evidence=list(evidence_by_id.values()),
            summary=summarize(claim_results),
            warnings=warnings,
        )
