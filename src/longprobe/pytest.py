"""
Public re-export module for the ``@golden_check`` pytest decorator.

Usage::

    from longprobe.pytest import golden_check

    @golden_check(
        question="What is the refund policy?",
        must_contain=["refunds within 30 days"],
    )
    def test_refund_retrieval(probe_result):
        assert probe_result.recall_score >= 0.8
"""

from longprobe.pytest_plugin import golden_check  # noqa: F401

__all__ = ["golden_check"]
