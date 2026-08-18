from __future__ import annotations

import hashlib
import re

from .models import Claim, Evidence, ReferenceDocument
from .text import lexical_similarity


_CHUNK_RE = re.compile(r"[^.!?。！？\n]+(?:[.!?。！？]+|(?=\n)|$)")


class DocumentRetriever:
    def __init__(self, *, top_k: int = 5) -> None:
        self.top_k = top_k

    def retrieve(self, claim: Claim, documents: list[ReferenceDocument]) -> list[Evidence]:
        candidates: list[Evidence] = []
        for document in documents:
            for chunk in _chunks(document.text):
                exact_score = lexical_similarity(claim.text, chunk)
                relation_score = lexical_similarity(claim.text, chunk, mask_numbers=True)
                score = 0.4 * exact_score + 0.6 * relation_score
                if score < 0.08:
                    continue
                digest = hashlib.sha1(
                    f"{document.document_id}\0{chunk}".encode("utf-8")
                ).hexdigest()[:12]
                candidates.append(
                    Evidence(
                        evidence_id=f"e-{digest}",
                        document_id=document.document_id,
                        title=document.title,
                        text=chunk,
                        score=round(score, 4),
                        url=document.url,
                        published_at=document.published_at,
                    )
                )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: self.top_k]


def _chunks(text: str) -> list[str]:
    chunks: list[str] = []
    for match in _CHUNK_RE.finditer(text):
        chunk = match.group(0).strip()
        if chunk:
            chunks.append(chunk)
    return chunks
