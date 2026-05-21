"""
Explainer module for diagnosing retrieval regressions.

This module provides the :class:`Explainer` which analyses a given question,
compares its current retrieval results against a baseline (if available), and
identifies "interloper" chunks that may be pushing valid answers down the rank.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from longprobe.adapters import AbstractRetrieverAdapter
from longprobe.core.scorer import QuestionResult


@dataclass
class MissingChunkDetail:
    """Details about a chunk that is required but missing."""
    chunk_text_or_id: str
    baseline_rank: int | None
    current_extended_rank: int | None


@dataclass
class InterloperDetail:
    """Details about a chunk that pushed a valid answer out of the top-k."""
    chunk_id: str
    text: str
    current_rank: int
    score: float


@dataclass
class ExplainResult:
    """Diagnostic report for a specific question."""
    question_id: str
    question: str
    status: str
    current_recall: float
    baseline_recall: float | None
    missing_chunks: list[MissingChunkDetail]
    interlopers: list[InterloperDetail]
    recommendation: str


class Explainer:
    """Analyses retrieval regressions for a specific question."""

    def explain(
        self,
        question_id: str,
        question_text: str,
        required_chunks: list[str],
        current_result: QuestionResult,
        baseline_result: QuestionResult | None,
        adapter: AbstractRetrieverAdapter,
        top_k: int = 5,
        extended_top_k: int = 20,
    ) -> ExplainResult:
        """
        Diagnose why a question failed or regressed.

        Args:
            question_id: The ID of the golden question.
            question_text: The natural language query.
            required_chunks: The chunks that were expected to be retrieved.
            current_result: The freshly computed QuestionResult.
            baseline_result: The QuestionResult from the baseline, if any.
            adapter: The retriever adapter to query for extended results.
            top_k: The original top_k used for the test.
            extended_top_k: How deep to search to find where missing chunks went.

        Returns:
            An :class:`ExplainResult` with diagnostic information.
        """
        # Determine status
        if current_result.passed:
            status = "pass"
        elif baseline_result and baseline_result.passed:
            status = "regression"
        else:
            status = "fail"

        baseline_recall = baseline_result.recall_score if baseline_result else None

        # 1. Fetch current top-k chunks to identify interlopers
        # 2. Fetch extended top-k to find where missing chunks went
        # We can just fetch extended_top_k once.
        extended_docs = adapter.retrieve(question_text, extended_top_k)

        # Map out current extended ranks
        current_ranks: dict[str, int] = {}
        top_k_chunks: list[dict[str, Any]] = []

        for i, doc in enumerate(extended_docs):
            rank = i + 1
            doc_id = doc.get("id", str(i))
            doc_text = doc.get("text", "")
            doc_score = doc.get("score", 0.0)

            if rank <= top_k:
                top_k_chunks.append({
                    "id": doc_id,
                    "text": doc_text,
                    "score": doc_score,
                    "rank": rank,
                })

            # Index by ID and text for matching
            current_ranks[doc_id] = rank
            current_ranks[doc_text] = rank

        # Map out baseline ranks if possible
        # (Our baseline QuestionResult doesn't store exact ranks, but we know if they were in found_chunks)

        missing_details: list[MissingChunkDetail] = []
        for missing in current_result.missing_chunks:
            # Check if it was found in baseline
            was_in_baseline = False
            if baseline_result and missing in baseline_result.found_chunks:
                was_in_baseline = True

            # Find where it is now (in extended search)
            current_rank = current_ranks.get(missing)

            missing_details.append(
                MissingChunkDetail(
                    chunk_text_or_id=missing,
                    baseline_rank=1 if was_in_baseline else None,  # We don't have exact baseline rank, just presence
                    current_extended_rank=current_rank,
                )
            )

        # Identify interlopers (chunks in top-k that aren't required)
        interlopers: list[InterloperDetail] = []
        for chunk in top_k_chunks:
            # A chunk is an interloper if it's not in the required chunks
            # (Note: robust match checking would use the scorer's logic, but exact match is fine for diagnostic)
            is_required = False
            for req in required_chunks:
                if req == chunk["id"] or req in chunk["text"]:
                    is_required = True
                    break

            if not is_required:
                interlopers.append(
                    InterloperDetail(
                        chunk_id=chunk["id"],
                        text=chunk["text"],
                        current_rank=chunk["rank"],
                        score=chunk["score"] or 0.0,
                    )
                )

        # Generate recommendation
        recommendation = "Review the interlopers to see if they are semantically similar but incorrect."
        if any(m.current_extended_rank is not None for m in missing_details):
            recommendation = "Some missing chunks were found further down the ranking. Consider increasing top_k or improving the embedding index."

        if not baseline_result:
            recommendation += " (No baseline saved. Run `longprobe baseline save` to enable rank-shift tracking.)"

        return ExplainResult(
            question_id=question_id,
            question=question_text,
            status=status,
            current_recall=current_result.recall_score,
            baseline_recall=baseline_recall,
            missing_chunks=missing_details,
            interlopers=interlopers,
            recommendation=recommendation,
        )
