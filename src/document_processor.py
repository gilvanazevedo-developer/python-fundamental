"""
Document Processor Module
Handles PDF and URL content extraction and text chunking.
"""

import re
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import pdfplumber
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DOCUMENTS_DIR,
    REQUEST_TIMEOUT,
    MAX_CONTENT_LENGTH
)
from src.logger import get_logger
from src.utils.retry import retry, RetryError

logger = get_logger(__name__)


class DocumentProcessor:
    """Processes documents (PDFs and URLs) for RAG ingestion."""

    def __init__(self):
        """Initialize the text splitter."""
        logger.info("Initializing DocumentProcessor")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        logger.debug(
            f"Text splitter configured with chunk_size={CHUNK_SIZE}, "
            f"chunk_overlap={CHUNK_OVERLAP}"
        )

    def process_pdf(self, file_path: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Extract text from PDF and split into chunks.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (list of text chunks, metadata dict)
        """
        logger.info(f"Processing PDF: {file_path}")
        path = Path(file_path)

        if not path.exists():
            logger.error(f"PDF file not found: {file_path}")
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        text_content = []
        page_count = 0

        try:
            with pdfplumber.open(path) as pdf:
                page_count = len(pdf.pages)
                logger.debug(f"PDF has {page_count} pages")

                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
                            logger.debug(
                                f"Extracted {len(page_text)} chars from page {page_num}"
                            )
                        else:
                            logger.warning(
                                f"No text extracted from page {page_num}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract text from page {page_num}: {e}. "
                            "Skipping page."
                        )
                        continue

        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            raise

        if not text_content:
            logger.warning(f"No text content extracted from PDF: {file_path}")
            return [], {
                "source": path.name,
                "type": "pdf",
                "path": str(path),
                "ingested_at": datetime.now().isoformat(),
                "error": "No text content extracted"
            }

        full_text = "\n\n".join(text_content)
        full_text = self._clean_text(full_text)

        chunks = self.text_splitter.split_text(full_text)
        logger.info(
            f"PDF processed: {path.name}, pages={page_count}, chunks={len(chunks)}"
        )

        metadata = {
            "source": path.name,
            "type": "pdf",
            "path": str(path),
            "page_count": page_count,
            "ingested_at": datetime.now().isoformat()
        }

        return chunks, metadata

    def process_pdf_upload(
        self,
        uploaded_file,
        filename: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process an uploaded PDF file (from Streamlit).

        Args:
            uploaded_file: Streamlit UploadedFile object
            filename: Name of the file

        Returns:
            Tuple of (list of text chunks, metadata dict)
        """
        logger.info(f"Processing uploaded PDF: {filename}")

        # Save to documents directory
        save_path = DOCUMENTS_DIR / filename

        try:
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            logger.debug(f"Saved uploaded file to: {save_path}")
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise

        return self.process_pdf(str(save_path))

    @retry(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(requests.RequestException, requests.Timeout)
    )
    def _fetch_url_content(self, url: str) -> requests.Response:
        """
        Fetch content from URL with retry logic.

        Args:
            url: Web URL to fetch

        Returns:
            Response object
        """
        logger.debug(f"Fetching URL: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AI-GURU-Bot/1.0)"
        }

        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.debug(f"URL fetched successfully: status={response.status_code}")

        return response

    def process_url(self, url: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Extract text content from a URL and split into chunks.

        Args:
            url: Web URL to process

        Returns:
            Tuple of (list of text chunks, metadata dict)
        """
        logger.info(f"Processing URL: {url}")

        try:
            response = self._fetch_url_content(url)
        except RetryError as e:
            logger.error(f"Failed to fetch URL after retries: {url}")
            raise RuntimeError(f"Failed to fetch URL: {e}") from e

        try:
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract text
            text = soup.get_text(separator="\n")
            text = self._clean_text(text)
            original_length = len(text)

            # Truncate if too long
            if len(text) > MAX_CONTENT_LENGTH:
                text = text[:MAX_CONTENT_LENGTH]
                logger.warning(
                    f"URL content truncated from {original_length} to "
                    f"{MAX_CONTENT_LENGTH} characters"
                )

            if not text.strip():
                logger.warning(f"No text content extracted from URL: {url}")
                return [], {
                    "source": url,
                    "type": "url",
                    "title": url,
                    "ingested_at": datetime.now().isoformat(),
                    "error": "No text content extracted"
                }

            chunks = self.text_splitter.split_text(text)

            # Extract title
            title = soup.find("title")
            title_text = title.get_text().strip() if title else url

            logger.info(
                f"URL processed: {title_text[:50]}..., "
                f"content_length={len(text)}, chunks={len(chunks)}"
            )

            metadata = {
                "source": url,
                "type": "url",
                "title": title_text,
                "content_length": len(text),
                "ingested_at": datetime.now().isoformat()
            }

            return chunks, metadata

        except Exception as e:
            logger.error(f"Failed to parse URL content: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        logger.debug(f"Chunking text of length {len(text)}")
        chunks = self.text_splitter.split_text(text)
        logger.debug(f"Created {len(chunks)} chunks")
        return chunks


def process_document(source: str) -> Tuple[List[str], Dict[str, Any]]:
    """
    Process a document from a file path or URL.

    Args:
        source: File path or URL

    Returns:
        Tuple of (list of text chunks, metadata dict)
    """
    logger.info(f"Processing document: {source}")
    processor = DocumentProcessor()

    if source.startswith(("http://", "https://")):
        return processor.process_url(source)
    else:
        return processor.process_pdf(source)
