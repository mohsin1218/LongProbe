import pytest

pytest_plugins = ["pytester"]

def test_golden_check_decorator_passes(pytester):
    # Create a dummy config
    pytester.makepyfile(
        longprobe_yaml="""
retriever:
  type: http
  http:
    url: "http://example.com"
        """
    )
    
    # Create a test file
    pytester.makepyfile(
        """
        import pytest
        from longprobe.pytest import golden_check
        
        # We mock the adapter retrieval since we don't have a real HTTP endpoint
        @pytest.fixture
        def longprobe_adapter(monkeypatch):
            class MockAdapter:
                def retrieve(self, query, top_k):
                    return [{"id": "doc1", "text": "This is a refund policy document."}]
            return MockAdapter()

        @golden_check(
            question="What is the refund policy?",
            must_contain=["refund policy"],
            top_k=5,
            match_mode="text"
        )
        def test_retrieval(probe_result):
            assert probe_result.passed
            assert probe_result.recall_score == 1.0
            assert "refund policy" in probe_result.found_chunks
        """
    )
    
    # Run pytest
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)

def test_golden_check_decorator_fails(pytester):
    pytester.makepyfile(
        """
        import pytest
        from longprobe.pytest import golden_check
        
        @pytest.fixture
        def longprobe_adapter():
            class MockAdapter:
                def retrieve(self, query, top_k):
                    # Doesn't return the required text
                    return [{"id": "doc1", "text": "Something unrelated."}]
            return MockAdapter()

        @golden_check(
            question="What is the refund policy?",
            must_contain=["refund policy"],
            top_k=5,
            match_mode="text"
        )
        def test_retrieval(probe_result):
            # We expect the probe_result to show failure
            assert not probe_result.passed
            assert probe_result.recall_score == 0.0
            assert "refund policy" in probe_result.missing_chunks
        """
    )
    
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
