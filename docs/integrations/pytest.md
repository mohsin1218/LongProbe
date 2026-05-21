# Pytest Integration

LongProbe integrates natively with existing Pytest test suites via a custom plugin. The star of this integration is the `@golden_check` decorator, which allows you to write sub-second, inline RAG regression checks directly alongside your unit and integration tests.

---

## The `@golden_check` Decorator

The `@golden_check` decorator performs automatic retrieval evaluation against a defined golden question inside a test function. It intercepts the call, retrieves the documents via your adapter, evaluates recall using your configuration, and injects the evaluation result (`probe_result`) directly into your test function.

### Basic Usage

```python
import pytest
from longprobe.pytest import golden_check

@golden_check(
    question="What is the refund policy?",
    must_contain=["refund policy", "30 days"],
    top_k=5,
    match_mode="text"
)
def test_refund_policy_retrieval(probe_result):
    assert probe_result.passed
    assert probe_result.recall_score >= 0.8
    assert "refund policy" in probe_result.found_chunks
```

### Decorator Parameters

The `@golden_check` decorator takes the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `question` | `str` | *Required* | The query text to send to the retriever. |
| `must_contain` | `list[str]` | *Required* | Chunks/texts that must be present in the retrieved results. |
| `top_k` | `int` | `5` | The number of results to retrieve. |
| `match_mode` | `str` | `"text"` | Strategy to match retrieved chunks. Must be one of `"id"`, `"text"`, or `"semantic"`. |
| `semantic_threshold` | `float` | `0.8` | Minimum similarity threshold for semantic matches (only used if `match_mode="semantic"`). |

---

## Configuration Discovery (Zero-Config)

LongProbe has two ways of establishing the connection between your pytest suite and your live retriever:

### 1. Auto-Discovery (Zero-Config)
By default, the `@golden_check` decorator will automatically search for `longprobe.yaml` in the root of your project directory. It loads the configuration and builds the adapter dynamically using your defined settings. This provides an elegant, magical, "zero-config" experience.

### 2. Explicit Fixture Override (The pythonic way)
For advanced, programmatic control (e.g. running tests against mock servers, passing runtime secrets, or configuring test databases), you can explicitly define a `longprobe_adapter` fixture in your `conftest.py`.

If Pytest finds a fixture named `longprobe_adapter` in the environment, the `@golden_check` decorator will skip auto-discovery and use your custom fixture instead:

```python
# conftest.py
import pytest
from longprobe.adapters import create_adapter

@pytest.fixture(scope="session")
def longprobe_adapter():
    # Return a mocked or programmatically configured adapter
    class MockAdapter:
        def retrieve(self, query, top_k):
            return [
                {"id": "doc1", "text": "This is a refund policy document."}
            ]
    return MockAdapter()
```

---

## Run Configurations & CLI Arguments

The LongProbe pytest plugin registers custom command line options so you can control your tests dynamically.

### CLI Flags

- `--longprobe-config`: Specify a custom path to `longprobe.yaml`.
  ```bash
  pytest --longprobe-config=configs/test_config.yaml
  ```

- `--longprobe-fail-threshold`: Override the default recall failure threshold globally.
  ```bash
  pytest --longprobe-fail-threshold=0.85
  ```

---

## Pytest Markers

The LongProbe pytest plugin registers a custom marker, `@pytest.mark.longprobe`, to allow you to easily isolate or skip RAG checks in your pipeline.

To run only your RAG regression tests:
```bash
pytest -m longprobe
```
