"""
Tests for Vector Store Module
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid

from src.vector_store import VectorStore


class TestVectorStoreInit:
    """Tests for VectorStore initialization."""

    def test_init_creates_collection(self, mock_chroma_client):
        """Test that init creates ChromaDB collection."""
        store = VectorStore()

        mock_chroma_client.assert_called_once()
        mock_chroma_client.return_value.get_or_create_collection.assert_called_once()

    def test_init_uses_correct_collection_name(self, mock_chroma_client):
        """Test that init uses the configured collection name."""
        store = VectorStore()

        call_args = mock_chroma_client.return_value.get_or_create_collection.call_args
        assert "ai_guru_knowledge" in str(call_args)

    def test_init_uses_cosine_similarity(self, mock_chroma_client):
        """Test that init configures cosine similarity."""
        store = VectorStore()

        call_args = mock_chroma_client.return_value.get_or_create_collection.call_args
        assert "cosine" in str(call_args)


class TestAddDocuments:
    """Tests for adding documents to the vector store."""

    @patch("src.vector_store.get_embeddings")
    def test_add_documents_success(self, mock_get_embeddings, mock_chroma_client, sample_chunks, sample_metadata):
        """Test successful document addition."""
        mock_get_embeddings.return_value = [[0.1] * 384 for _ in sample_chunks]

        store = VectorStore()
        metadatas = [sample_metadata.copy() for _ in sample_chunks]

        ids = store.add_documents(sample_chunks, metadatas)

        assert len(ids) == len(sample_chunks)
        mock_chroma_client.return_value.get_or_create_collection.return_value.add.assert_called_once()

    @patch("src.vector_store.get_embeddings")
    def test_add_documents_generates_ids(self, mock_get_embeddings, mock_chroma_client, sample_chunks):
        """Test that IDs are generated if not provided."""
        mock_get_embeddings.return_value = [[0.1] * 384 for _ in sample_chunks]

        store = VectorStore()
        metadatas = [{"source": "test"} for _ in sample_chunks]

        ids = store.add_documents(sample_chunks, metadatas)

        # Verify UUIDs were generated
        for id_ in ids:
            uuid.UUID(id_)  # Will raise if not valid UUID

    @patch("src.vector_store.get_embeddings")
    def test_add_documents_uses_provided_ids(self, mock_get_embeddings, mock_chroma_client, sample_chunks):
        """Test that provided IDs are used."""
        mock_get_embeddings.return_value = [[0.1] * 384 for _ in sample_chunks]

        store = VectorStore()
        metadatas = [{"source": "test"} for _ in sample_chunks]
        custom_ids = ["id1", "id2", "id3", "id4", "id5"]

        ids = store.add_documents(sample_chunks, metadatas, ids=custom_ids)

        assert ids == custom_ids

    @patch("src.vector_store.get_embeddings")
    def test_add_documents_empty_list(self, mock_get_embeddings, mock_chroma_client):
        """Test adding empty document list."""
        store = VectorStore()

        ids = store.add_documents([], [])

        assert ids == []
        mock_get_embeddings.assert_not_called()


class TestSearch:
    """Tests for vector store search."""

    @patch("src.vector_store.get_embedding")
    def test_search_returns_results(self, mock_get_embedding, mock_chroma_client, mock_chroma_collection):
        """Test that search returns formatted results."""
        mock_get_embedding.return_value = [0.1] * 384

        store = VectorStore()
        results = store.search("test query", top_k=5)

        assert isinstance(results, list)
        mock_chroma_collection.query.assert_called_once()

    @patch("src.vector_store.get_embedding")
    def test_search_result_format(self, mock_get_embedding, mock_chroma_client, mock_chroma_collection):
        """Test that search results have correct format."""
        mock_get_embedding.return_value = [0.1] * 384

        store = VectorStore()
        results = store.search("test query")

        for result in results:
            assert "text" in result
            assert "metadata" in result
            assert "similarity" in result
            assert "id" in result

    @patch("src.vector_store.get_embedding")
    def test_search_filters_by_similarity(self, mock_get_embedding, mock_chroma_client):
        """Test that results below threshold are filtered."""
        mock_get_embedding.return_value = [0.1] * 384

        # Create collection with low similarity results
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"source": "test"}, {"source": "test"}]],
            "distances": [[0.9, 0.95]],  # High distance = low similarity
            "ids": [["id1", "id2"]]
        }
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        results = store.search("test query")

        # Results with similarity < 0.3 should be filtered
        assert len(results) == 0

    @patch("src.vector_store.get_embedding")
    def test_search_with_filter(self, mock_get_embedding, mock_chroma_client, mock_chroma_collection):
        """Test search with metadata filter."""
        mock_get_embedding.return_value = [0.1] * 384

        store = VectorStore()
        store.search("test query", filter_metadata={"source": "specific.pdf"})

        call_args = mock_chroma_collection.query.call_args
        assert call_args.kwargs["where"] == {"source": "specific.pdf"}

    @patch("src.vector_store.get_embedding")
    def test_search_respects_top_k(self, mock_get_embedding, mock_chroma_client, mock_chroma_collection):
        """Test that search respects top_k parameter."""
        mock_get_embedding.return_value = [0.1] * 384

        store = VectorStore()
        store.search("test query", top_k=3)

        call_args = mock_chroma_collection.query.call_args
        assert call_args.kwargs["n_results"] == 3


class TestDeleteBySource:
    """Tests for deleting documents by source."""

    def test_delete_by_source_success(self, mock_chroma_client, mock_chroma_collection):
        """Test successful deletion by source."""
        store = VectorStore()
        deleted_count = store.delete_by_source("test.pdf")

        assert deleted_count == 2  # Based on mock fixture
        mock_chroma_collection.delete.assert_called_once_with(ids=["id1", "id2"])

    def test_delete_by_source_no_documents(self, mock_chroma_client):
        """Test deletion when no documents found."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        deleted_count = store.delete_by_source("nonexistent.pdf")

        assert deleted_count == 0
        mock_collection.delete.assert_not_called()


class TestDeleteByIds:
    """Tests for deleting documents by IDs."""

    def test_delete_by_ids_success(self, mock_chroma_client, mock_chroma_collection):
        """Test successful deletion by IDs."""
        store = VectorStore()
        store.delete_by_ids(["id1", "id2", "id3"])

        mock_chroma_collection.delete.assert_called_once_with(ids=["id1", "id2", "id3"])

    def test_delete_by_ids_empty_list(self, mock_chroma_client, mock_chroma_collection):
        """Test deletion with empty ID list."""
        store = VectorStore()
        store.delete_by_ids([])

        mock_chroma_collection.delete.assert_not_called()


class TestGetAllSources:
    """Tests for getting all sources."""

    def test_get_all_sources(self, mock_chroma_client, mock_chroma_collection):
        """Test getting all sources."""
        store = VectorStore()
        sources = store.get_all_sources()

        assert isinstance(sources, list)
        # Based on mock fixture, should have one unique source
        assert len(sources) == 1
        assert sources[0]["source"] == "test.pdf"
        assert sources[0]["type"] == "pdf"
        assert sources[0]["chunk_count"] == 2

    def test_get_all_sources_empty_collection(self, mock_chroma_client):
        """Test getting sources from empty collection."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_collection.get.return_value = {"ids": [], "metadatas": []}
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        sources = store.get_all_sources()

        assert sources == []


class TestGetCollectionStats:
    """Tests for getting collection statistics."""

    def test_get_collection_stats(self, mock_chroma_client, mock_chroma_collection):
        """Test getting collection stats."""
        mock_chroma_collection.count.return_value = 10

        store = VectorStore()
        stats = store.get_collection_stats()

        assert "total_chunks" in stats
        assert "total_sources" in stats
        assert "sources" in stats
        assert stats["total_chunks"] == 10


class TestClearCollection:
    """Tests for clearing the collection."""

    def test_clear_collection(self, mock_chroma_client, mock_chroma_collection):
        """Test clearing the collection."""
        store = VectorStore()
        store.clear_collection()

        mock_chroma_client.return_value.delete_collection.assert_called_once()
        # Should recreate collection after deletion
        assert mock_chroma_client.return_value.get_or_create_collection.call_count == 2


class TestRetryLogic:
    """Tests for retry logic in vector store operations."""

    @patch("src.vector_store.get_embeddings")
    def test_add_documents_retries_on_failure(self, mock_get_embeddings, mock_chroma_client):
        """Test that add_documents retries on failure."""
        mock_get_embeddings.return_value = [[0.1] * 384]

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        # Fail twice, succeed on third try
        mock_collection.add.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            None
        ]
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        ids = store.add_documents(["test"], [{"source": "test"}])

        assert len(ids) == 1
        assert mock_collection.add.call_count == 3

    @patch("src.vector_store.get_embedding")
    def test_search_retries_on_failure(self, mock_get_embedding, mock_chroma_client):
        """Test that search retries on failure."""
        mock_get_embedding.return_value = [0.1] * 384

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        # Fail twice, succeed on third try
        mock_collection.query.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            {
                "documents": [["result"]],
                "metadatas": [[{"source": "test"}]],
                "distances": [[0.1]],
                "ids": [["id1"]]
            }
        ]
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        store = VectorStore()
        results = store.search("test query")

        assert len(results) == 1
        assert mock_collection.query.call_count == 3
