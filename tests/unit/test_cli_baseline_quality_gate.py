"""Tests for baseline save quality gate and strict approved-only draft filtering."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
import yaml

from longprobe.cli.main import baseline_save
from longprobe.core.baseline import BaselineStore


def _setup_test_environment(tmp_path: Path, questions: list[dict]) -> tuple[Path, Path, Path]:
    goldens_path = tmp_path / "goldens.yaml"
    config_path = tmp_path / "longprobe.yaml"
    db_path = tmp_path / "baselines.db"

    goldens_data = {
        "name": "test-gate",
        "version": "1.0",
        "questions": questions,
    }
    goldens_path.write_text(yaml.dump(goldens_data))

    config_data = {
        "retriever": {
            "type": "http",
            "url": "http://localhost:8000/retrieve",
        },
        "scoring": {
            "recall_threshold": 0.85,
        },
        "baseline": {
            "db_path": str(db_path),
        },
    }
    config_path.write_text(yaml.dump(config_data))

    return goldens_path, config_path, db_path


def test_baseline_save_succeeds_when_recall_above_threshold(tmp_path: Path, monkeypatch):
    questions = [
        {"id": "q1", "question": "Q1", "required_chunks": ["chunk-1"], "status": "approved"},
    ]
    goldens_path, config_path, db_path = _setup_test_environment(tmp_path, questions)

    mock_adapter = MagicMock()
    mock_adapter.retrieve.return_value = [{"id": "chunk-1", "text": "chunk-1"}]
    monkeypatch.setattr("longprobe.cli.main._create_adapter_from_config", lambda cfg: mock_adapter)

    baseline_save(
        label="test-v1",
        goldens=goldens_path,
        config=config_path,
        top_k=None,
        threshold=0.80,
        tag=[],
    )

    store = BaselineStore(db_path=str(db_path))
    b = store.load("test-v1")
    assert b is not None
    assert b.overall_recall == 1.0


def test_baseline_save_fails_when_recall_below_threshold(tmp_path: Path, monkeypatch):
    questions = [
        {"id": "q1", "question": "Q1", "required_chunks": ["chunk-1"], "status": "approved"},
    ]
    goldens_path, config_path, db_path = _setup_test_environment(tmp_path, questions)

    mock_adapter = MagicMock()
    mock_adapter.retrieve.return_value = [{"id": "chunk-wrong", "text": "wrong"}]
    monkeypatch.setattr("longprobe.cli.main._create_adapter_from_config", lambda cfg: mock_adapter)

    with pytest.raises(typer.Exit) as exc_info:
        baseline_save(
            label="test-fail",
            goldens=goldens_path,
            config=config_path,
            top_k=None,
            threshold=0.80,
            tag=[],
        )

    assert exc_info.value.exit_code == 1

    store = BaselineStore(db_path=str(db_path))
    b = store.load("test-fail")
    assert b is None


def test_baseline_save_strictly_uses_approved_questions(tmp_path: Path, monkeypatch):
    """Draft questions (which would fail) must be excluded from baseline save quality gate."""
    questions = [
        {"id": "q1", "question": "Q1", "required_chunks": ["chunk-1"], "status": "approved"},
        {"id": "q2", "question": "Q2", "required_chunks": ["chunk-2"], "status": "draft"},
    ]
    goldens_path, config_path, db_path = _setup_test_environment(tmp_path, questions)

    def mock_retrieve(query, top_k=5):
        if "Q1" in query:
            return [{"id": "chunk-1"}]
        return [{"id": "wrong-chunk"}]

    mock_adapter = MagicMock()
    mock_adapter.retrieve.side_effect = mock_retrieve
    monkeypatch.setattr("longprobe.cli.main._create_adapter_from_config", lambda cfg: mock_adapter)

    baseline_save(
        label="test-approved-only",
        goldens=goldens_path,
        config=config_path,
        top_k=None,
        threshold=0.90,
        tag=[],
    )

    store = BaselineStore(db_path=str(db_path))
    b = store.load("test-approved-only")
    assert b is not None
    assert b.overall_recall == 1.0
    assert len(b.results) == 1
