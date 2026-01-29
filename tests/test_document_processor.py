"""
Tests for Document Processor Module
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import requests

from src.document_processor import DocumentProcessor, process_document
from src.utils.retry import RetryError


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    def test_init(self):
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor()
        assert processor.text_splitter is not None

    def test_clean_text(self):
        """Test text cleaning."""
        processor = DocumentProcessor()

        # Test whitespace normalization
        text = "  Hello    world  \n\n\n\n  test  "
        cleaned = processor._clean_text(text)
        assert "    " not in cleaned
        assert cleaned == "Hello world test"

    def test_clean_text_preserves_double_newlines(self):
        """Test that double newlines are preserved but not more."""
        processor = DocumentProcessor()
        text = "Paragraph 1\n\n\n\n\nParagraph 2"
        cleaned = processor._clean_text(text)
        assert "\n\n\n" not in cleaned

    def test_chunk_text(self):
        """Test text chunking."""
        processor = DocumentProcessor()
        long_text = "This is a test sentence. " * 100  # Create long text
        chunks = processor.chunk_text(long_text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_text_short_text(self):
        """Test chunking with text shorter than chunk size."""
        processor = DocumentProcessor()
        short_text = "Short text"
        chunks = processor.chunk_text(short_text)

        assert len(chunks) == 1
        assert chunks[0] == "Short text"


class TestProcessPDF:
    """Tests for PDF processing."""

    def test_process_pdf_file_not_found(self):
        """Test processing a non-existent PDF file."""
        processor = DocumentProcessor()

        with pytest.raises(FileNotFoundError) as exc_info:
            processor.process_pdf("/nonexistent/path/file.pdf")

        assert "PDF file not found" in str(exc_info.value)

    @patch("pdfplumber.open")
    def test_process_pdf_success(self, mock_pdfplumber, temp_dir):
        """Test successful PDF processing."""
        # Create a mock PDF file
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()

        # Mock pdfplumber
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is test content from page 1."

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdfplumber.return_value = mock_pdf

        processor = DocumentProcessor()
        chunks, metadata = processor.process_pdf(str(pdf_path))

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert metadata["type"] == "pdf"
        assert metadata["source"] == "test.pdf"
        assert "ingested_at" in metadata

    @patch("pdfplumber.open")
    def test_process_pdf_empty_pages(self, mock_pdfplumber, temp_dir):
        """Test PDF processing with empty pages."""
        pdf_path = temp_dir / "empty.pdf"
        pdf_path.touch()

        # Mock pdfplumber with empty pages
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdfplumber.return_value = mock_pdf

        processor = DocumentProcessor()
        chunks, metadata = processor.process_pdf(str(pdf_path))

        assert chunks == []
        assert "error" in metadata

    @patch("pdfplumber.open")
    def test_process_pdf_page_extraction_error(self, mock_pdfplumber, temp_dir):
        """Test PDF processing when page extraction fails."""
        pdf_path = temp_dir / "error.pdf"
        pdf_path.touch()

        # Mock one successful page and one failing page
        mock_page_ok = MagicMock()
        mock_page_ok.extract_text.return_value = "Content from page 1"

        mock_page_fail = MagicMock()
        mock_page_fail.extract_text.side_effect = Exception("Page extraction error")

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page_ok, mock_page_fail]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)

        mock_pdfplumber.return_value = mock_pdf

        processor = DocumentProcessor()
        chunks, metadata = processor.process_pdf(str(pdf_path))

        # Should still return content from successful page
        assert len(chunks) > 0
        assert "page_count" in metadata


class TestProcessPDFUpload:
    """Tests for uploaded PDF processing."""

    @patch.object(DocumentProcessor, "process_pdf")
    def test_process_pdf_upload(self, mock_process_pdf, temp_dir, mock_uploaded_file):
        """Test processing an uploaded PDF file."""
        mock_process_pdf.return_value = (["chunk1", "chunk2"], {"source": "test.pdf", "type": "pdf"})

        with patch("src.document_processor.DOCUMENTS_DIR", temp_dir):
            processor = DocumentProcessor()
            chunks, metadata = processor.process_pdf_upload(mock_uploaded_file, "test.pdf")

            assert chunks == ["chunk1", "chunk2"]
            mock_process_pdf.assert_called_once()


class TestProcessURL:
    """Tests for URL processing."""

    def test_process_url_success(self, mock_requests_get, sample_html_content):
        """Test successful URL processing."""
        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/article")

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert metadata["type"] == "url"
        assert metadata["source"] == "https://example.com/article"
        assert "title" in metadata
        assert "ingested_at" in metadata

    def test_process_url_extracts_title(self, mock_requests_get):
        """Test that URL processing extracts the title."""
        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/article")

        assert "Test Article - AI Research" in metadata["title"]

    def test_process_url_removes_scripts(self, mock_requests_get):
        """Test that scripts and navigation are removed."""
        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/article")

        # Check that script content is not in chunks
        all_content = " ".join(chunks)
        assert "console.log" not in all_content

    @patch("requests.get")
    def test_process_url_connection_error(self, mock_get):
        """Test URL processing with connection error."""
        mock_get.side_effect = requests.RequestException("Connection failed")

        processor = DocumentProcessor()

        with pytest.raises(RuntimeError) as exc_info:
            processor.process_url("https://example.com/failing")

        assert "Failed to fetch URL" in str(exc_info.value)

    @patch("requests.get")
    def test_process_url_retry_on_timeout(self, mock_get):
        """Test that URL fetching retries on timeout."""
        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.content = b"<html><body>Test content</body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_get.side_effect = [
            requests.Timeout("Timeout"),
            requests.Timeout("Timeout"),
            mock_response
        ]

        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/slow")

        assert mock_get.call_count == 3
        assert len(chunks) > 0

    @patch("requests.get")
    def test_process_url_empty_content(self, mock_get):
        """Test URL processing with empty content."""
        mock_response = MagicMock()
        mock_response.content = b"<html><body></body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/empty")

        assert chunks == []
        assert "error" in metadata

    @patch("requests.get")
    def test_process_url_truncates_long_content(self, mock_get):
        """Test that long URL content is truncated."""
        # Create content longer than MAX_CONTENT_LENGTH
        long_content = "<html><body>" + "x" * 200000 + "</body></html>"

        mock_response = MagicMock()
        mock_response.content = long_content.encode()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        processor = DocumentProcessor()
        chunks, metadata = processor.process_url("https://example.com/long")

        # Content should be truncated
        total_length = sum(len(c) for c in chunks)
        assert total_length < 200000


class TestProcessDocument:
    """Tests for the convenience function process_document."""

    @patch.object(DocumentProcessor, "process_url")
    def test_process_document_url(self, mock_process_url):
        """Test process_document with URL."""
        mock_process_url.return_value = (["chunk"], {"type": "url"})

        chunks, metadata = process_document("https://example.com/test")

        mock_process_url.assert_called_once_with("https://example.com/test")

    @patch.object(DocumentProcessor, "process_url")
    def test_process_document_http_url(self, mock_process_url):
        """Test process_document with HTTP URL."""
        mock_process_url.return_value = (["chunk"], {"type": "url"})

        chunks, metadata = process_document("http://example.com/test")

        mock_process_url.assert_called_once_with("http://example.com/test")

    @patch.object(DocumentProcessor, "process_pdf")
    def test_process_document_pdf(self, mock_process_pdf):
        """Test process_document with PDF path."""
        mock_process_pdf.return_value = (["chunk"], {"type": "pdf"})

        chunks, metadata = process_document("/path/to/document.pdf")

        mock_process_pdf.assert_called_once_with("/path/to/document.pdf")
