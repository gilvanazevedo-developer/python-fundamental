"""
Vector Store Module
Handles ChromaDB operations for storing and retrieving document embeddings.
Supports both local persistent storage and ChromaDB Cloud.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid

from config.settings import (
    CHROMA_PERSIST_PATH,
    CHROMA_COLLECTION_NAME,
    CHROMA_USE_CLOUD,
    CHROMA_API_KEY,
    CHROMA_TENANT,
    CHROMA_DATABASE,
    TOP_K_RESULTS,
    SIMILARITY_THRESHOLD
)
from src.embeddings import get_embedding, get_embeddings
from src.logger import get_logger
from src.utils.retry import retry, RetryError

logger = get_logger(__name__)


def create_chroma_client():
    """
    Create the appropriate ChromaDB client based on configuration.

    Returns:
        ChromaDB client (either CloudClient or PersistentClient)
    """
    if CHROMA_USE_CLOUD:
        if not all([CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE]):
            raise ValueError(
                "ChromaDB Cloud requires CHROMA_API_KEY, CHROMA_TENANT, and CHROMA_DATABASE. "
                "Please set these in your .env file or set CHROMA_USE_CLOUD=false for local storage."
            )

        logger.info("Connecting to ChromaDB Cloud")
        logger.debug(f"Tenant: {CHROMA_TENANT}, Database: {CHROMA_DATABASE}")

        client = chromadb.CloudClient(
            api_key=CHROMA_API_KEY,
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE
        )
        logger.info("Connected to ChromaDB Cloud successfully")
        return client
    else:
        logger.info("Using local ChromaDB storage")
        logger.debug(f"ChromaDB path: {CHROMA_PERSIST_PATH}")

        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        logger.info("Local ChromaDB client created")
        return client


class VectorStore:
    """ChromaDB vector store for document embeddings."""

    def __init__(self):
        """Initialize ChromaDB client and collection."""
        logger.info("Initializing VectorStore")

        try:
            self.client = create_chroma_client()

            self.collection = self.client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(
                f"Collection '{CHROMA_COLLECTION_NAME}' ready with "
                f"{self.collection.count()} existing documents"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    @retry(max_attempts=3, base_delay=0.5, exceptions=(Exception,))
    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            texts: List of text chunks to store
            metadatas: List of metadata dicts for each chunk
            ids: Optional list of IDs (generated if not provided)

        Returns:
            List of document IDs
        """
        if not texts:
            logger.warning("No texts provided to add_documents")
            return []

        logger.info(f"Adding {len(texts)} documents to vector store")

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        logger.debug("Generating embeddings for documents")
        try:
            embeddings = get_embeddings(texts)
            logger.debug(f"Generated {len(embeddings)} embeddings")
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

        try:
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added {len(ids)} documents")
        except Exception as e:
            logger.error(f"Failed to add documents to collection: {e}")
            raise

        return ids

    @retry(max_attempts=3, base_delay=0.5, exceptions=(Exception,))
    def search(
        self,
        query: str,
        top_k: int = TOP_K_RESULTS,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of results with text, metadata, and distance
        """
        logger.debug(f"Searching for: {query[:50]}..., top_k={top_k}")

        try:
            query_embedding = get_embedding(query)
            logger.debug("Query embedding generated")
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            raise

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # Convert distance to similarity

                if similarity >= SIMILARITY_THRESHOLD:
                    formatted_results.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "similarity": similarity,
                        "id": results["ids"][0][i] if results["ids"] else None
                    })

        logger.info(
            f"Search returned {len(formatted_results)} results "
            f"(threshold: {SIMILARITY_THRESHOLD})"
        )

        return formatted_results

    def delete_by_source(self, source: str) -> int:
        """
        Delete all documents from a specific source.

        Args:
            source: Source identifier (filename or URL)

        Returns:
            Number of documents deleted
        """
        logger.info(f"Deleting documents for source: {source}")

        try:
            # Get all documents with this source
            results = self.collection.get(
                where={"source": source},
                include=["metadatas"]
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                deleted_count = len(results["ids"])
                logger.info(f"Deleted {deleted_count} documents for source: {source}")
                return deleted_count

            logger.info(f"No documents found for source: {source}")
            return 0

        except Exception as e:
            logger.error(f"Failed to delete documents for source {source}: {e}")
            raise

    def delete_by_ids(self, ids: List[str]) -> None:
        """Delete documents by their IDs."""
        if not ids:
            logger.warning("No IDs provided for deletion")
            return

        logger.info(f"Deleting {len(ids)} documents by ID")

        try:
            self.collection.delete(ids=ids)
            logger.debug(f"Deleted {len(ids)} documents")
        except Exception as e:
            logger.error(f"Failed to delete documents by ID: {e}")
            raise

    def get_all_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of all unique sources in the collection.

        Returns:
            List of source information with document counts
        """
        logger.debug("Getting all sources from collection")

        try:
            all_docs = self.collection.get(include=["metadatas"])

            sources = {}
            for metadata in all_docs["metadatas"]:
                source = metadata.get("source", "Unknown")
                source_type = metadata.get("type", "unknown")

                if source not in sources:
                    sources[source] = {
                        "source": source,
                        "type": source_type,
                        "chunk_count": 0
                    }
                sources[source]["chunk_count"] += 1

            source_list = list(sources.values())
            logger.debug(f"Found {len(source_list)} unique sources")

            return source_list

        except Exception as e:
            logger.error(f"Failed to get sources: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        logger.debug("Getting collection statistics")

        try:
            count = self.collection.count()
            sources = self.get_all_sources()

            stats = {
                "total_chunks": count,
                "total_sources": len(sources),
                "sources": sources,
                "storage_type": "cloud" if CHROMA_USE_CLOUD else "local"
            }

            logger.debug(
                f"Collection stats: {count} chunks, {len(sources)} sources"
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            raise

    def clear_collection(self) -> None:
        """Clear all documents from the collection."""
        logger.warning("Clearing entire collection")

        try:
            self.client.delete_collection(CHROMA_COLLECTION_NAME)
            logger.debug(f"Deleted collection: {CHROMA_COLLECTION_NAME}")

            self.collection = self.client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Collection cleared and recreated")

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise
