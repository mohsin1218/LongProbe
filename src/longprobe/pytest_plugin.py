"""
LongProbe pytest plugin.

Registers pytest options and provides fixtures for RAG regression testing.

Usage in conftest.py::

    from longprobe import LongProbe, ChromaAdapter

    @pytest.fixture
    def probe():
        adapter = ChromaAdapter(collection_name="my_docs", persist_directory="./db")
        return LongProbe(adapter=adapter, goldens_path="goldens.yaml")

Usage in tests::

    def test_retrieval_recall(probe):
        report = probe.run()
        assert report.overall_recall >= 0.85, (
            f"Recall dropped to {report.overall_recall:.2f}. "
            f"Lost chunks: {probe.get_missing_chunks()}"
        )

Command line::

    pytest --longprobe-goldens goldens.yaml --longprobe-config longprobe.yaml
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TYPE_CHECKING, TypeVar

import pytest

from longprobe.core.golden import GoldenQuestion
from longprobe.core.scorer import RecallScorer

T = TypeVar("T", bound=Callable)
if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.fixtures import FixtureRequest
    from _pytest.nodes import Item


# ---------------------------------------------------------------------------
# Command-line options
# ---------------------------------------------------------------------------


def pytest_addoption(parser: Parser) -> None:
    """Register longprobe-specific pytest command line options."""
    group = parser.getgroup("longprobe")
    group.addoption(
        "--longprobe-goldens",
        action="store",
        dest="longprobe_goldens",
        default="goldens.yaml",
        help="Path to LongProbe golden questions YAML file (default: goldens.yaml)",
    )
    group.addoption(
        "--longprobe-config",
        action="store",
        dest="longprobe_config",
        default="longprobe.yaml",
        help="Path to LongProbe configuration YAML file (default: longprobe.yaml)",
    )
    group.addoption(
        "--longprobe-fail-threshold",
        action="store",
        dest="longprobe_fail_threshold",
        type=float,
        default=None,
        help=(
            "Minimum overall recall to pass. "
            "Fail tests if recall drops below this value."
        ),
    )


# ---------------------------------------------------------------------------
# Configuration hook
# ---------------------------------------------------------------------------


@pytest.hookimpl(trylast=True)
def pytest_configure(config: Config) -> None:
    """Store longprobe options on the config object for later access."""
    config._longprobe_goldens = config.getoption("longprobe_goldens", "goldens.yaml")  # type: ignore[attr-defined]
    config._longprobe_config = config.getoption("longprobe_config", "longprobe.yaml")  # type: ignore[attr-defined]
    config._longprobe_fail_threshold = config.getoption("longprobe_fail_threshold", None)  # type: ignore[attr-defined]
    config._longprobe_report = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def longprobe_goldens_path(request: FixtureRequest) -> str:
    """Fixture that returns the path to the golden questions file.

    The path is determined by the ``--longprobe-goldens`` CLI option (defaults
    to ``goldens.yaml``).
    """
    return request.config._longprobe_goldens  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def longprobe_config_path(request: FixtureRequest) -> str:
    """Fixture that returns the path to the longprobe config file.

    The path is determined by the ``--longprobe-config`` CLI option (defaults
    to ``longprobe.yaml``).
    """
    return request.config._longprobe_config  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def longprobe_fail_threshold(request: FixtureRequest) -> float | None:
    """Fixture that returns the configured fail threshold (or ``None``).

    Set via ``--longprobe-fail-threshold``.  When *None*, no automatic
    threshold check is applied.
    """
    return request.config._longprobe_fail_threshold  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Optional convenience fixture - auto-build a LongProbe instance
# ---------------------------------------------------------------------------


def _load_adapter_from_config(config_path: str) -> Any:
    """Helper to lazily build an adapter from the longprobe configuration file."""
    from pathlib import Path

    try:
        from longprobe.config import ProbeConfig
    except ImportError:
        pytest.skip("longprobe is not installed; skipping adapter")
        return None  # pragma: no cover

    config_file = Path(config_path)
    if not config_file.exists():
        pytest.skip(f"LongProbe config not found: {config_path}")
        return None

    try:
        cfg = ProbeConfig.from_yaml(str(config_file))
    except Exception as exc:
        pytest.skip(f"Cannot load longprobe config: {exc}")
        return None  # pragma: no cover

    try:
        from longprobe.cli.main import _create_adapter_from_config as create_adapter
        return create_adapter(cfg)
    except Exception as exc:
        pytest.skip(f"Failed to create adapter: {exc}")
        return None


@pytest.fixture(scope="session")
def longprobe_adapter(
    longprobe_config_path: str,
) -> Any:
    """Lazily build an adapter from the longprobe configuration file."""
    return _load_adapter_from_config(longprobe_config_path)


@pytest.fixture(scope="session")
def longprobe_probe(
    longprobe_adapter: Any,
    longprobe_goldens_path: str,
) -> Any:
    """Return a fully-initialised :class:`~longprobe.LongProbe` instance.

    This fixture depends on :fixture:`longprobe_adapter` which, by default,
    reads adapter settings from the config file.  Override either fixture in
    ``conftest.py`` for full control.
    """
    try:
        from longprobe import LongProbe
    except ImportError:
        pytest.skip("longprobe is not installed; skipping probe fixture")
        return None  # pragma: no cover

    if longprobe_adapter is None:
        pytest.skip("No adapter available; skipping probe fixture")
        return None  # pragma: no cover

    return LongProbe(adapter=longprobe_adapter, goldens_path=longprobe_goldens_path)


# ---------------------------------------------------------------------------
# Golden Check Decorator
# ---------------------------------------------------------------------------


def golden_check(
    question: str,
    must_contain: list[str],
    top_k: int = 5,
    match_mode: str = "text",
    threshold: float = 1.0,
    tags: list[str] | None = None,
) -> Callable[[T], T]:
    """Decorator to define an inline RAG regression test.

    This decorator executes a retrieval call using the active longprobe_adapter
    and injects the resulting QuestionResult as the `probe_result` argument
    into the decorated test function.
    """
    import inspect

    def decorator(fn: T) -> T:
        sig = inspect.signature(fn)

        # We need to tell pytest NOT to look for 'probe_result' as a fixture.
        # We also need to ensure pytest passes us the 'request' fixture.
        wrapper_params = []
        needs_request = True
        for name, p in sig.parameters.items():
            if name == "probe_result":
                continue
            if name == "request":
                needs_request = False
            wrapper_params.append(p)

        if needs_request:
            wrapper_params.append(
                inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )

        @functools.wraps(fn)
        @pytest.mark.longprobe
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.pop("request") if needs_request else kwargs["request"]

            # Get the adapter using the fixture.
            # If the user overrode 'longprobe_adapter' in their conftest, we get their mock.
            # Otherwise we get the default one which loads from longprobe.yaml.
            try:
                adapter = request.getfixturevalue("longprobe_adapter")
            except Exception as exc:
                pytest.skip(f"LongProbe adapter could not be loaded: {exc}")
                return None

            if adapter is None:
                pytest.skip("LongProbe adapter could not be loaded (returned None).")
                return None

            golden_q = GoldenQuestion(
                id=fn.__name__,
                question=question,
                match_mode=match_mode,
                required_chunks=must_contain,
                top_k=top_k,
                tags=tags or [],
            )

            # Retrieve docs
            import time
            start = time.perf_counter()
            retrieved_docs = adapter.retrieve(question, top_k)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            # Score
            scorer = RecallScorer(recall_threshold=threshold)
            result = scorer.score(golden_q, retrieved_docs)
            result.latency_ms = elapsed_ms

            # Print rich feedback on failure (if we can)
            if not result.passed:
                try:
                    from rich.console import Console
                    console = Console()
                    missing_str = ", ".join(f'"{c}"' for c in result.missing_chunks)
                    console.print(
                        f"\n[bold red]LongProbe Failure:[/bold red] "
                        f"Recall dropped to {result.recall_score:.2f} (Threshold: {threshold:.2f}). "
                        f"Missing chunks: {missing_str}"
                    )
                except ImportError:
                    pass

            # Inject the result into the original function
            kwargs["probe_result"] = result
            return fn(*args, **kwargs)

        # Apply the new signature so pytest knows what fixtures to inject
        wrapper.__signature__ = inspect.Signature(wrapper_params)  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Automatic threshold enforcement
# ---------------------------------------------------------------------------


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    session: Any,
    config: Config,
    items: list[Item],
) -> None:
    """Optionally inject a final summarising test that enforces the threshold.

    A synthetic test item is appended to the collected list when
    ``--longprobe-fail-threshold`` is provided.  The test reads
    ``config._longprobe_report`` (which a user's test is expected to store)
    and fails if the overall recall is below the threshold.
    """
    threshold = config._longprobe_fail_threshold  # type: ignore[attr-defined]
    if threshold is None:
        return

    from _pytest.python import Function

    # Define the test function inline.
    def _longprobe_threshold_check() -> None:
        report = config._longprobe_report  # type: ignore[attr-defined]
        if report is None:
            pytest.fail(
                "No LongProbe report was generated.  Make sure at least one "
                "test calls ``probe.run()`` and stores the result in "
                "``request.config._longprobe_report``."
            )
            return  # pragma: no cover
        if report.overall_recall < threshold:
            pytest.fail(
                f"LongProbe overall recall ({report.overall_recall:.2f}) is below "
                f"the configured threshold ({threshold:.2f})."
            )

    # Build a lightweight synthetic Function item.
    synthetic = Function.from_parent(
        parent=session,  # type: ignore[arg-type]
        name="longprobe_threshold_check",
        callobj=_longprobe_threshold_check,
    )
    items.append(synthetic)


# ---------------------------------------------------------------------------
# Session-finish summary
# ---------------------------------------------------------------------------


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Print a LongProbe summary table if a report was generated.

    The report is expected to be stored on the config object by user tests::

        request.config._longprobe_report = probe.run()
    """
    report = session.config._longprobe_report  # type: ignore[attr-defined]
    if report is None:
        return

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        # Fall back to plain-text output when rich is unavailable.
        _print_plain_summary(report)
        return

    console = Console()

    table = Table(title="LongProbe Results", show_header=True, header_style="bold cyan")
    table.add_column("Question ID", style="dim")
    table.add_column("Recall", justify="right")
    table.add_column("Missing Chunks")
    table.add_column("Status")

    for result in report.results:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        chunks_str = ", ".join(result.missing_chunks) if result.missing_chunks else "-"
        table.add_row(
            result.question_id,
            f"{result.recall_score:.2f}",
            chunks_str,
            status,
        )

    console.print()
    console.print(table)
    console.print(
        Panel(
            f"Overall Recall: {report.overall_recall:.2f} | "
            f"Pass Rate: {report.pass_rate:.2f}",
            style="bold",
        )
    )


# ---------------------------------------------------------------------------
# Plain-text fallback summary (when rich is not installed)
# ---------------------------------------------------------------------------


def _print_plain_summary(report: Any) -> None:
    """Print a minimal plain-text summary of a LongProbe report.

    This fallback is used when the ``rich`` library is not installed.
    It relies only on the Python standard library.
    """
    divider = "=" * 72
    print()
    print(divider)
    print("  LongProbe Results")
    print(divider)
    header = f"  {'Question ID':<30} {'Recall':>8}  {'Missing Chunks':<24} {'Status'}"
    print(header)
    print("-" * 72)
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        chunks_str = ", ".join(result.missing_chunks) if result.missing_chunks else "-"
        line = f"  {result.question_id:<30} {result.recall_score:>8.2f}  {chunks_str:<24} {status}"
        print(line)
    print(divider)
    print(
        f"  Overall Recall: {report.overall_recall:.2f}  |  "
        f"Pass Rate: {report.pass_rate:.2f}"
    )
    print(divider)
    print()
