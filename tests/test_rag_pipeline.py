"""
Tests for RAG Pipeline Module
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRAGPipelineInit:
    """Tests for RAGPipeline initialization."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_init_creates_components(self, mock_doc_processor, mock_vector_store):
        """Test that init creates all required components."""
        from src.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()

        mock_vector_store.assert_called_once()
        mock_doc_processor.assert_called_once()
        assert pipeline.vector_store is not None
        assert pipeline.document_processor is not None


class TestIngestPDF:
    """Tests for PDF ingestion."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_pdf_success(self, mock_doc_processor, mock_vector_store):
        """Test successful PDF ingestion."""
        from src.rag_pipeline import RAGPipeline

        # Setup mocks
        mock_doc_processor.return_value.process_pdf.return_value = (
            ["chunk1", "chunk2"],
            {"source": "test.pdf", "type": "pdf", "ingested_at": "2024-01-01"}
        )
        mock_vector_store.return_value.add_documents.return_value = ["id1", "id2"]

        pipeline = RAGPipeline()
        result = pipeline.ingest_pdf("/path/to/test.pdf")

        assert result["success"] is True
        assert result["source"] == "test.pdf"
        assert result["type"] == "pdf"
        assert result["chunks_created"] == 2
        assert len(result["ids"]) == 2

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_pdf_error(self, mock_doc_processor, mock_vector_store):
        """Test PDF ingestion error handling."""
        from src.rag_pipeline import RAGPipeline

        mock_doc_processor.return_value.process_pdf.side_effect = FileNotFoundError("Not found")

        pipeline = RAGPipeline()

        with pytest.raises(FileNotFoundError):
            pipeline.ingest_pdf("/nonexistent/file.pdf")


class TestIngestPDFUpload:
    """Tests for uploaded PDF ingestion."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_pdf_upload_success(self, mock_doc_processor, mock_vector_store, mock_uploaded_file):
        """Test successful uploaded PDF ingestion."""
        from src.rag_pipeline import RAGPipeline

        mock_doc_processor.return_value.process_pdf_upload.return_value = (
            ["chunk1"],
            {"source": "uploaded.pdf", "type": "pdf", "ingested_at": "2024-01-01"}
        )
        mock_vector_store.return_value.add_documents.return_value = ["id1"]

        pipeline = RAGPipeline()
        result = pipeline.ingest_pdf_upload(mock_uploaded_file, "uploaded.pdf")

        assert result["success"] is True
        assert result["source"] == "uploaded.pdf"


class TestIngestURL:
    """Tests for URL ingestion."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_url_success(self, mock_doc_processor, mock_vector_store):
        """Test successful URL ingestion."""
        from src.rag_pipeline import RAGPipeline

        mock_doc_processor.return_value.process_url.return_value = (
            ["chunk1", "chunk2", "chunk3"],
            {"source": "https://example.com", "type": "url", "title": "Test", "ingested_at": "2024-01-01"}
        )
        mock_vector_store.return_value.add_documents.return_value = ["id1", "id2", "id3"]

        pipeline = RAGPipeline()
        result = pipeline.ingest_url("https://example.com")

        assert result["success"] is True
        assert result["type"] == "url"
        assert result["chunks_created"] == 3

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_url_empty_content(self, mock_doc_processor, mock_vector_store):
        """Test URL ingestion with empty content."""
        from src.rag_pipeline import RAGPipeline

        mock_doc_processor.return_value.process_url.return_value = (
            [],
            {"source": "https://empty.com", "type": "url", "error": "No content"}
        )

        pipeline = RAGPipeline()
        result = pipeline.ingest_url("https://empty.com")

        assert result["success"] is False
        assert result["chunks_created"] == 0


class TestIngestChunks:
    """Tests for the internal _ingest_chunks method."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_chunks_adds_metadata(self, mock_doc_processor, mock_vector_store, sample_chunks):
        """Test that chunk metadata is properly added."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.add_documents.return_value = ["id1", "id2"]

        pipeline = RAGPipeline()
        result = pipeline._ingest_chunks(
            sample_chunks[:2],
            {"source": "test.pdf", "type": "pdf"}
        )

        # Verify metadata was added
        call_args = mock_vector_store.return_value.add_documents.call_args
        metadatas = call_args[0][1]  # Second positional arg

        assert all("chunk_index" in m for m in metadatas)
        assert all("chunk_total" in m for m in metadatas)
        assert metadatas[0]["chunk_index"] == 0
        assert metadatas[1]["chunk_index"] == 1

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_ingest_chunks_empty_list(self, mock_doc_processor, mock_vector_store):
        """Test ingesting empty chunk list."""
        from src.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        result = pipeline._ingest_chunks([], {"source": "empty", "type": "pdf"})

        assert result["success"] is False
        assert result["chunks_created"] == 0


class TestRetrieveContext:
    """Tests for context retrieval."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_retrieve_context_with_results(self, mock_doc_processor, mock_vector_store):
        """Test context retrieval with matching results."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.search.return_value = [
            {
                "text": "Relevant content about AI",
                "metadata": {"source": "ai_paper.pdf", "type": "pdf"},
                "similarity": 0.85,
                "id": "id1"
            },
            {
                "text": "More AI information",
                "metadata": {"source": "ai_paper.pdf", "type": "pdf"},
                "similarity": 0.75,
                "id": "id2"
            }
        ]

        pipeline = RAGPipeline()
        context, sources = pipeline.retrieve_context("What is AI?")

        assert "Relevant content about AI" in context
        # Sources list includes duplicates because each result has different similarity
        assert len(sources) == 2
        assert sources[0]["source"] == "ai_paper.pdf"

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_retrieve_context_no_results(self, mock_doc_processor, mock_vector_store):
        """Test context retrieval with no matching results."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.search.return_value = []

        pipeline = RAGPipeline()
        context, sources = pipeline.retrieve_context("Random query")

        assert "No directly relevant information" in context
        assert sources == []

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_retrieve_context_multiple_sources(self, mock_doc_processor, mock_vector_store):
        """Test context retrieval with multiple sources."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.search.return_value = [
            {
                "text": "Content from PDF",
                "metadata": {"source": "document.pdf", "type": "pdf"},
                "similarity": 0.85,
                "id": "id1"
            },
            {
                "text": "Content from URL",
                "metadata": {"source": "https://example.com", "type": "url"},
                "similarity": 0.75,
                "id": "id2"
            }
        ]

        pipeline = RAGPipeline()
        context, sources = pipeline.retrieve_context("test query")

        assert len(sources) == 2
        source_types = {s["type"] for s in sources}
        assert "pdf" in source_types
        assert "url" in source_types

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_retrieve_context_respects_top_k(self, mock_doc_processor, mock_vector_store):
        """Test that retrieve_context respects top_k parameter."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.search.return_value = []

        pipeline = RAGPipeline()
        pipeline.retrieve_context("test", top_k=3)

        mock_vector_store.return_value.search.assert_called_once_with("test", top_k=3)

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_retrieve_context_handles_search_error(self, mock_doc_processor, mock_vector_store):
        """Test context retrieval handles search errors gracefully."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.search.side_effect = Exception("Search failed")

        pipeline = RAGPipeline()
        context, sources = pipeline.retrieve_context("test query")

        # Should return no context template and empty sources
        assert sources == []


class TestDeleteSource:
    """Tests for source deletion."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_delete_source_success(self, mock_doc_processor, mock_vector_store):
        """Test successful source deletion."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.delete_by_source.return_value = 5

        pipeline = RAGPipeline()
        result = pipeline.delete_source("test.pdf")

        assert result["success"] is True
        assert result["source"] == "test.pdf"
        assert result["chunks_deleted"] == 5


class TestKnowledgeBaseStats:
    """Tests for knowledge base statistics."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_get_knowledge_base_stats(self, mock_doc_processor, mock_vector_store):
        """Test getting knowledge base stats."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.get_collection_stats.return_value = {
            "total_chunks": 100,
            "total_sources": 5,
            "sources": []
        }

        pipeline = RAGPipeline()
        stats = pipeline.get_knowledge_base_stats()

        assert stats["total_chunks"] == 100
        assert stats["total_sources"] == 5


class TestGetSources:
    """Tests for getting sources list."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_get_sources(self, mock_doc_processor, mock_vector_store):
        """Test getting all sources."""
        from src.rag_pipeline import RAGPipeline

        mock_vector_store.return_value.get_all_sources.return_value = [
            {"source": "doc1.pdf", "type": "pdf", "chunk_count": 10},
            {"source": "https://example.com", "type": "url", "chunk_count": 5}
        ]

        pipeline = RAGPipeline()
        sources = pipeline.get_sources()

        assert len(sources) == 2


class TestClearKnowledgeBase:
    """Tests for clearing the knowledge base."""

    @patch("src.rag_pipeline.VectorStore")
    @patch("src.rag_pipeline.DocumentProcessor")
    def test_clear_knowledge_base(self, mock_doc_processor, mock_vector_store):
        """Test clearing the knowledge base."""
        from src.rag_pipeline import RAGPipeline

        pipeline = RAGPipeline()
        pipeline.clear_knowledge_base()

        mock_vector_store.return_value.clear_collection.assert_called_once()
