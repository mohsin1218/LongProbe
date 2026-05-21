from longprobe.core.explainer import Explainer
from longprobe.core.scorer import QuestionResult
from typing import Any


class MockAdapter:
    def retrieve(self, query: str, top_k: int) -> list[dict[str, Any]]:
        return [
            {"id": "doc1", "text": "Unrelated info A", "score": 0.9},
            {"id": "doc2", "text": "Unrelated info B", "score": 0.8},
            {"id": "doc_refund", "text": "Refund policy within 30 days", "score": 0.7},
            {"id": "doc4", "text": "Unrelated info C", "score": 0.6},
            {"id": "doc5", "text": "Unrelated info D", "score": 0.5},
        ]


def test_explainer_finds_missing_chunks():
    current_result = QuestionResult(
        question_id="q1",
        question="What is the refund policy?",
        recall_score=0.0,
        retrieved_chunk_ids=["doc1", "doc2"],  # top_k=2
        required_chunks=["doc_refund"],
        missing_chunks=["doc_refund"],
        found_chunks=[],
        passed=False,
        latency_ms=10.0
    )
    
    baseline_result = QuestionResult(
        question_id="q1",
        question="What is the refund policy?",
        recall_score=1.0,
        retrieved_chunk_ids=["doc_refund", "doc1"],
        required_chunks=["doc_refund"],
        missing_chunks=[],
        found_chunks=["doc_refund"],
        passed=True,
        latency_ms=10.0
    )

    explainer = Explainer()
    adapter = MockAdapter()
    
    explanation = explainer.explain(
        question_id="q1",
        question_text="What is the refund policy?",
        required_chunks=["doc_refund"],
        current_result=current_result,
        baseline_result=baseline_result,
        adapter=adapter,
        top_k=2,
        extended_top_k=5
    )
    
    assert explanation.status == "regression"
    assert explanation.baseline_recall == 1.0
    assert explanation.current_recall == 0.0
    
    # Check missing chunks tracking
    assert len(explanation.missing_chunks) == 1
    m = explanation.missing_chunks[0]
    assert m.chunk_text_or_id == "doc_refund"
    assert m.baseline_rank == 1  # Was in baseline found chunks
    assert m.current_extended_rank == 3  # Based on MockAdapter output
    
    # Check interlopers
    assert len(explanation.interlopers) == 2
    assert explanation.interlopers[0].chunk_id == "doc1"
    assert explanation.interlopers[0].current_rank == 1
    assert explanation.interlopers[1].chunk_id == "doc2"
    assert explanation.interlopers[1].current_rank == 2

def test_explainer_no_baseline():
    current_result = QuestionResult(
        question_id="q1",
        question="What is the refund policy?",
        recall_score=0.0,
        retrieved_chunk_ids=["doc1", "doc2"],
        required_chunks=["doc_refund"],
        missing_chunks=["doc_refund"],
        found_chunks=[],
        passed=False,
        latency_ms=10.0
    )
    
    explainer = Explainer()
    adapter = MockAdapter()
    
    explanation = explainer.explain(
        question_id="q1",
        question_text="What is the refund policy?",
        required_chunks=["doc_refund"],
        current_result=current_result,
        baseline_result=None,
        adapter=adapter,
        top_k=2,
        extended_top_k=5
    )
    
    assert explanation.status == "fail"
    assert explanation.baseline_recall is None
    assert len(explanation.missing_chunks) == 1
    assert explanation.missing_chunks[0].baseline_rank is None
    assert "No baseline saved" in explanation.recommendation
