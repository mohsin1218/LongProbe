"""Tests for longprobe edit state helper functions."""

from __future__ import annotations

from longprobe.cli.main import (
    edit_approve_all_drafts,
    edit_delete_question,
    edit_set_status,
    edit_update_question,
)
from longprobe.core.golden import GoldenQuestion, GoldenSet


def _build_test_golden_set() -> GoldenSet:
    return GoldenSet(
        name="test-set",
        version="1.0",
        questions=[
            GoldenQuestion(id="q1", question="What is Python?", required_chunks=["c1"], status="approved"),
            GoldenQuestion(id="q2", question="What is Rust?", required_chunks=["c2"], status="draft"),
            GoldenQuestion(id="q3", question="What is Go?", required_chunks=["c3"], status="draft"),
        ],
    )


def test_edit_approve_all_drafts():
    gs = _build_test_golden_set()
    count = edit_approve_all_drafts(gs)

    assert count == 2
    assert all(q.status == "approved" for q in gs.questions)


def test_edit_set_status():
    gs = _build_test_golden_set()
    updated = edit_set_status(gs, "q2", "approved")

    assert updated is True
    assert gs.questions[1].status == "approved"
    assert gs.questions[2].status == "draft"


def test_edit_update_question():
    gs = _build_test_golden_set()
    updated = edit_update_question(
        gs,
        question_id="q1",
        question_text="What is Python 3?",
        match_mode="text",
        status="draft",
    )

    assert updated is True
    q1 = gs.questions[0]
    assert q1.question == "What is Python 3?"
    assert q1.match_mode == "text"
    assert q1.status == "draft"


def test_edit_delete_question():
    gs = _build_test_golden_set()
    deleted = edit_delete_question(gs, "q2")

    assert deleted is True
    assert len(gs.questions) == 2
    assert [q.id for q in gs.questions] == ["q1", "q3"]
