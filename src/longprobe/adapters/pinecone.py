from __future__ import annotations

import logging
from typing import Any

from .base import AbstractRetrieverAdapter

logger = logging.getLogger(__name__)


class PineconeAdapter(AbstractRetrieverAdapter):
    """Adapter for Pinecone vector indexes.

    Supports querying by embedding vector directly.  The Pinecone SDK
    is imported lazily so that the adapter can be instantiated without
    the library being present.
    """

    def __init__(
        self,
        index_name: str,
        api_key: str = "",
        namespace: str = "",
        top_k: int = 10,
    ) -> None:
        self.index_name = index_name
        self.api_key = api_key
        self.namespace = namespace
        self.top_k = top_k

    def retrieve(
        self,
        query_embedding: list[float] | None = None,
        query: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Query the Pinecone index for the most similar vectors.

        Args:
            query_embedding: Pre-computed query vector to search with.
            query: Text query (reserved for future text-based query support).
            top_k: Number of results to return.

        Returns:
            List of result dicts normalised to the LongProbe format.
        """
        # Handle case where first positional arg is text string from scorer
        vector: list[float] | None = None
        if isinstance(query_embedding, list):
            vector = query_embedding
        elif isinstance(query, list):
            vector = query
        elif isinstance(query_embedding, str) or isinstance(query, str):
            logger.warning(
                "Pinecone requires vector embeddings. Text query received: '%s'. "
                "Provide a pre-computed vector embedding.",
                query_embedding or query,
            )
            return []

        if not vector:
            logger.warning("No vector embedding provided for Pinecone retrieval.")
            return []

        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=self.api_key)
            index = pc.Index(self.index_name)
            response = index.query(
                vector=vector,
                top_k=top_k,
                namespace=self.namespace or None,
                include_metadata=True,
            )
        except Exception as exc:
            logger.warning("Pinecone query error: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for match in response.matches:
            results.append(
                {
                    "id": match.id,
                    "text": match.metadata.get("text", "") if match.metadata else "",
                    "score": float(match.score or 0.0),
                    "metadata": dict(match.metadata) if match.metadata else {},
                }
            )

        return results

    def health_check(self) -> bool:
        """Check connectivity by describing the configured index."""
        try:
            from pinecone import Pinecone
        except ImportError:
            return False

        try:
            pc = Pinecone(api_key=self.api_key)
            pc.Index(self.index_name).describe_index_stats()
            return True
        except Exception:
            logger.debug("Pinecone health check failed", exc_info=True)
            return False
