"""Diagnostic failure summaries for LongProbe regression reports."""

from __future__ import annotations

from .scorer import QuestionResult


def explain_failure(result: QuestionResult) -> str:
    """Generate a human-readable diagnostic explanation for a question result."""
    if result.passed:
        return f"Question '{result.question_id}' passed with recall {result.recall_score:.2f}."

    lines = [f"Failure Analysis for Question '{result.question_id}':"]
    lines.append(f"  - Question text: \"{result.question}\"")
    lines.append(f"  - Recall score: {result.recall_score:.2f}")
    lines.append(f"  - Required chunks ({len(result.required_chunks)}): {', '.join(result.required_chunks)}")

    if result.missing_chunks:
        lines.append(f"  - Missing chunks ({len(result.missing_chunks)}): {', '.join(result.missing_chunks)}")

    retrieved = getattr(result, "retrieved_chunk_ids", [])
    if retrieved:
        lines.append("  - Top retrieved chunk IDs:")
        for idx, cid in enumerate(retrieved[:5], 1):
            lines.append(f"      {idx}. {cid}")
    else:
        lines.append("  - No chunks were returned by the retriever.")

    return "\n".join(lines)
