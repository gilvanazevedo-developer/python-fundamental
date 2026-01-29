"""
Pytest Configuration and Shared Fixtures
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import BytesIO

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set test API key (mocked in tests)
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-api-key-for-testing")
    yield


# ============================================================================
# Temporary Directories
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_chroma_dir(temp_dir):
    """Create a temporary directory for ChromaDB."""
    chroma_path = temp_dir / "chroma_db"
    chroma_path.mkdir(parents=True, exist_ok=True)
    return str(chroma_path)


# ============================================================================
# Sample Data
# ============================================================================

@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    Artificial Intelligence (AI) is transforming the business landscape.
    Machine learning algorithms enable organizations to extract insights from data.
    Natural Language Processing (NLP) allows computers to understand human language.
    Deep learning has revolutionized image recognition and speech processing.
    AI ethics and responsible AI practices are increasingly important.
    """


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing."""
    return [
        "Artificial Intelligence (AI) is transforming the business landscape.",
        "Machine learning algorithms enable organizations to extract insights from data.",
        "Natural Language Processing (NLP) allows computers to understand human language.",
        "Deep learning has revolutionized image recognition and speech processing.",
        "AI ethics and responsible AI practices are increasingly important."
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "source": "test_document.pdf",
        "type": "pdf",
        "path": "/path/to/test_document.pdf",
        "ingested_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def sample_url_metadata():
    """Sample URL metadata for testing."""
    return {
        "source": "https://example.com/article",
        "type": "url",
        "title": "Sample Article",
        "content_length": 1000,
        "ingested_at": "2024-01-01T00:00:00"
    }


# ============================================================================
# Mock PDF File
# ============================================================================

@pytest.fixture
def sample_pdf_content():
    """Create a simple PDF-like content for testing."""
    # This is a minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test PDF content) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
    return pdf_content


@pytest.fixture
def mock_pdf_file(temp_dir, sample_pdf_content):
    """Create a mock PDF file for testing."""
    pdf_path = temp_dir / "test_document.pdf"
    pdf_path.write_bytes(sample_pdf_content)
    return str(pdf_path)


@pytest.fixture
def mock_uploaded_file():
    """Create a mock Streamlit UploadedFile object."""
    mock_file = MagicMock()
    mock_file.name = "uploaded_test.pdf"
    mock_file.getbuffer.return_value = b"Mock PDF content for testing"
    return mock_file


# ============================================================================
# Mock HTML Content
# ============================================================================

@pytest.fixture
def sample_html_content():
    """Sample HTML content for URL testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Article - AI Research</title>
    </head>
    <body>
        <header>Navigation</header>
        <main>
            <h1>Introduction to AI</h1>
            <p>Artificial Intelligence is changing the world.</p>
            <p>Machine learning enables computers to learn from data.</p>
            <h2>Applications</h2>
            <p>AI has many applications in healthcare, finance, and technology.</p>
        </main>
        <footer>Copyright 2024</footer>
        <script>console.log('test');</script>
    </body>
    </html>
    """


# ============================================================================
# Mock Embeddings
# ============================================================================

@pytest.fixture
def mock_embedding():
    """Create a mock embedding vector."""
    # 384-dimensional embedding (matching all-MiniLM-L6-v2)
    return [0.1] * 384


@pytest.fixture
def mock_embeddings():
    """Create multiple mock embedding vectors."""
    return [[0.1 + i * 0.01] * 384 for i in range(5)]


@pytest.fixture
def mock_embedding_generator(mock_embedding, mock_embeddings):
    """Mock the embedding generator."""
    with patch("src.embeddings.EmbeddingGenerator") as mock_gen:
        instance = MagicMock()
        instance.generate_single.return_value = mock_embedding
        instance.generate_batch.return_value = mock_embeddings
        mock_gen.return_value = instance
        yield mock_gen


# ============================================================================
# Mock Anthropic Client
# ============================================================================

@pytest.fixture
def mock_anthropic_response():
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is a test response from AI GURU.")]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response):
    """Mock the Anthropic client."""
    with patch("anthropic.Anthropic") as mock_client:
        instance = MagicMock()
        instance.messages.create.return_value = mock_anthropic_response

        # Mock streaming
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["This ", "is ", "a ", "test ", "response."])
        instance.messages.stream.return_value = mock_stream

        mock_client.return_value = instance
        yield mock_client


# ============================================================================
# Mock Requests
# ============================================================================

@pytest.fixture
def mock_requests_get(sample_html_content):
    """Mock requests.get for URL testing."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = sample_html_content.encode()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_requests_get_failure():
    """Mock requests.get to simulate failure."""
    with patch("requests.get") as mock_get:
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")
        yield mock_get


# ============================================================================
# ChromaDB Fixtures
# ============================================================================

@pytest.fixture
def mock_chroma_collection():
    """Create a mock ChromaDB collection."""
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    mock_collection.add = MagicMock()
    mock_collection.query = MagicMock(return_value={
        "documents": [["Test document 1", "Test document 2"]],
        "metadatas": [[
            {"source": "test.pdf", "type": "pdf"},
            {"source": "test.pdf", "type": "pdf"}
        ]],
        "distances": [[0.1, 0.2]],
        "ids": [["id1", "id2"]]
    })
    mock_collection.get = MagicMock(return_value={
        "ids": ["id1", "id2"],
        "metadatas": [
            {"source": "test.pdf", "type": "pdf"},
            {"source": "test.pdf", "type": "pdf"}
        ]
    })
    mock_collection.delete = MagicMock()
    return mock_collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Mock the ChromaDB client via create_chroma_client function."""
    with patch("src.vector_store.create_chroma_client") as mock_create_client:
        instance = MagicMock()
        instance.get_or_create_collection.return_value = mock_chroma_collection
        instance.delete_collection = MagicMock()
        mock_create_client.return_value = instance
        yield mock_create_client


# ============================================================================
# Integration Test Helpers
# ============================================================================

@pytest.fixture
def clean_test_environment(temp_dir):
    """
    Set up a clean test environment with temporary directories.
    Patches settings to use temp directories.
    """
    documents_dir = temp_dir / "documents"
    chroma_dir = temp_dir / "chroma_db"
    logs_dir = temp_dir / "logs"

    documents_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    with patch.multiple(
        "config.settings",
        DOCUMENTS_DIR=documents_dir,
        CHROMA_DIR=chroma_dir,
        CHROMA_PERSIST_PATH=str(chroma_dir)
    ):
        yield {
            "documents_dir": documents_dir,
            "chroma_dir": chroma_dir,
            "logs_dir": logs_dir,
            "temp_dir": temp_dir
        }


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_valid_chunks(chunks):
    """Assert that chunks are valid."""
    assert isinstance(chunks, list)
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert all(len(chunk) > 0 for chunk in chunks)


def assert_valid_metadata(metadata, expected_type):
    """Assert that metadata is valid."""
    assert isinstance(metadata, dict)
    assert "source" in metadata
    assert "type" in metadata
    assert metadata["type"] == expected_type
    assert "ingested_at" in metadata


def assert_valid_search_result(result):
    """Assert that a search result is valid."""
    assert isinstance(result, dict)
    assert "text" in result
    assert "metadata" in result
    assert "similarity" in result
    assert 0 <= result["similarity"] <= 1
