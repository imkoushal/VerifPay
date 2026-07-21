"""
VerifPay — RAG Retriever Service

Searches ChromaDB for fraud patterns similar to the input query.
Returns top matching chunks with metadata for context-augmented generation.
"""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class RAGRetriever:
    """ChromaDB-backed retriever for fraud pattern matching."""

    def __init__(self):
        self._collection = None
        self._client = None
        self._loaded = False

    def load(self) -> bool:
        """Connect to the persisted ChromaDB and load the collection."""
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._collection = self._client.get_collection(
                name="fraud_patterns",
                embedding_function=sentence_transformer_ef,
            )
            self._loaded = True
            logger.info(f"RAG Retriever ready: {self._collection.count()} chunks in collection")
            return True

        except Exception as e:
            logger.error(f"Failed to load RAG retriever: {e}")
            self._loaded = False
            return False

    def retrieve_fraud_patterns(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve top-k matching fraud patterns from ChromaDB.

        Args:
            query: The suspicious text to search for similar patterns.
            top_k: Number of results to return (default 5).

        Returns:
            List of dicts with keys: content, source, fraud_type, relevance_score
        """
        if not self._loaded:
            self.load()

        if not self._loaded:
            logger.warning("RAG retriever not loaded — returning empty results")
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            patterns = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0

                    # Convert distance to relevance score (ChromaDB uses L2 distance)
                    # Lower distance = higher relevance
                    relevance = max(0.0, 1.0 - (distance / 2.0))

                    patterns.append({
                        "content": doc,
                        "source": metadata.get("source", "unknown"),
                        "fraud_type": metadata.get("fraud_type", "UNKNOWN"),
                        "relevance_score": round(relevance, 4),
                    })

            logger.info(f"Retrieved {len(patterns)} patterns for query (top relevance: {patterns[0]['relevance_score']:.2%} | type: {patterns[0]['fraud_type']})" if patterns else "No patterns found")
            return patterns

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []


# Global singleton — loaded once and reused across requests
rag_retriever = RAGRetriever()
