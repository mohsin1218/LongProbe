from __future__ import annotations

import logging
from typing import Any

from .base import AbstractRetrieverAdapter

logger = logging.getLogger(__name__)


class QdrantAdapter(AbstractRetrieverAdapter):
    """Adapter for Qdrant vector databases.

    Supports querying by pre-computed embedding vector.  The Qdrant
    client SDK is imported lazily.
    """

    def __init__(
        self,
        collection_name: str,
        host: str = "localhost",
        port: int = 6333,
        api_key: str = "",
        url: str = "",
    ) -> None:
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.api_key = api_key
        self.url = url

    def _build_client(self) -> Any:
        """Create and return a QdrantClient instance."""
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError(
                "qdrant-client is required for QdrantAdapter. "
                "Install it with:  pip install qdrant-client"
            )

        if self.url:
            return QdrantClient(url=self.url, api_key=self.api_key or None)
        return QdrantClient(
            host=self.host, port=self.port, api_key=self.api_key or None
        )

    def retrieve(
        self,
        query_embedding: list[float] | None = None,
        query: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Query a Qdrant collection for the most similar vectors.

        Args:
            query_embedding: Pre-computed query vector.
            query: Text query (reserved for future use).
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
                "Qdrant requires vector embeddings. Text query received: '%s'. "
                "Provide a pre-computed vector embedding.",
                query_embedding or query,
            )
            return []

        if not vector:
            logger.warning("No vector embedding provided for Qdrant retrieval.")
            return []

        try:
            client = self._build_client()
            response = client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=top_k,
            )
        except Exception as exc:
            logger.warning("Qdrant query error for collection '%s': %s", self.collection_name, exc)
            return []

        results: list[dict[str, Any]] = []
        for point in response.points:
            results.append(
                {
                    "id": str(point.id),
                    "text": point.payload.get("text", "") if point.payload else "",
                    "score": float(point.score or 0.0),
                    "metadata": dict(point.payload) if point.payload else {},
                }
            )

        return results

    def health_check(self) -> bool:
        """Check connectivity by listing collections."""
        try:
            client = self._build_client()
            client.get_collections()
            return True
        except Exception:
            logger.debug("Qdrant health check failed", exc_info=True)
            return False
