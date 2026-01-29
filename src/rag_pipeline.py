"""
RAG Pipeline Module
Orchestrates the retrieval-augmented generation process.
"""

from typing import List, Dict, Any, Optional, Tuple

from src.vector_store import VectorStore
from src.document_processor import DocumentProcessor
from src.logger import get_logger
from config.prompts import CONTEXT_TEMPLATE, NO_CONTEXT_TEMPLATE, SOURCE_CITATION_FORMAT

logger = get_logger(__name__)


class RAGPipeline:
    """RAG pipeline for document ingestion and retrieval."""

    def __init__(self):
        """Initialize the RAG pipeline components."""
        logger.info("Initializing RAG Pipeline")
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
        logger.debug("RAG Pipeline components initialized")

    def ingest_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a PDF document into the knowledge base.

        Args:
            file_path: Path to the PDF file

        Returns:
            Ingestion result with statistics
        """
        logger.info(f"Ingesting PDF: {file_path}")
        try:
            chunks, metadata = self.document_processor.process_pdf(file_path)
            result = self._ingest_chunks(chunks, metadata)
            logger.info(
                f"PDF ingestion complete: {result['source']}, "
                f"chunks={result['chunks_created']}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to ingest PDF {file_path}: {e}")
            raise

    def ingest_pdf_upload(self, uploaded_file, filename: str) -> Dict[str, Any]:
        """
        Ingest an uploaded PDF file.

        Args:
            uploaded_file: Streamlit UploadedFile object
            filename: Name of the file

        Returns:
            Ingestion result with statistics
        """
        logger.info(f"Ingesting uploaded PDF: {filename}")
        try:
            chunks, metadata = self.document_processor.process_pdf_upload(
                uploaded_file, filename
            )
            result = self._ingest_chunks(chunks, metadata)
            logger.info(
                f"Uploaded PDF ingestion complete: {result['source']}, "
                f"chunks={result['chunks_created']}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to ingest uploaded PDF {filename}: {e}")
            raise

    def ingest_url(self, url: str) -> Dict[str, Any]:
        """
        Ingest content from a URL into the knowledge base.

        Args:
            url: Web URL to ingest

        Returns:
            Ingestion result with statistics
        """
        logger.info(f"Ingesting URL: {url}")
        try:
            chunks, metadata = self.document_processor.process_url(url)

            if not chunks:
                logger.warning(f"No content extracted from URL: {url}")
                return {
                    "success": False,
                    "source": url,
                    "type": "url",
                    "chunks_created": 0,
                    "error": "No content extracted"
                }

            result = self._ingest_chunks(chunks, metadata)
            logger.info(
                f"URL ingestion complete: {url[:50]}..., "
                f"chunks={result['chunks_created']}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to ingest URL {url}: {e}")
            raise

    def _ingest_chunks(
        self,
        chunks: List[str],
        base_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ingest text chunks into the vector store.

        Args:
            chunks: List of text chunks
            base_metadata: Base metadata for all chunks

        Returns:
            Ingestion result with statistics
        """
        if not chunks:
            logger.warning("No chunks to ingest")
            return {
                "success": False,
                "source": base_metadata.get("source"),
                "type": base_metadata.get("type"),
                "chunks_created": 0,
                "ids": []
            }

        logger.debug(f"Ingesting {len(chunks)} chunks")

        # Create metadata for each chunk
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_total"] = len(chunks)
            metadatas.append(chunk_metadata)

        # Add to vector store
        try:
            ids = self.vector_store.add_documents(chunks, metadatas)
            logger.debug(f"Added {len(ids)} documents to vector store")
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}")
            raise

        return {
            "success": True,
            "source": base_metadata.get("source"),
            "type": base_metadata.get("type"),
            "chunks_created": len(chunks),
            "ids": ids
        }

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve relevant context for a query.

        Args:
            query: User query
            top_k: Number of results to retrieve

        Returns:
            Tuple of (formatted context string, list of source documents)
        """
        logger.info(f"Retrieving context for query: {query[:50]}...")
        logger.debug(f"Retrieving top {top_k} results")

        try:
            results = self.vector_store.search(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Vector store search failed: {e}")
            return NO_CONTEXT_TEMPLATE, []

        if not results:
            logger.info("No relevant context found for query")
            return NO_CONTEXT_TEMPLATE, []

        logger.info(f"Found {len(results)} relevant chunks")

        # Format context from results
        context_parts = []
        sources = []

        for i, result in enumerate(results, 1):
            source_name = result["metadata"].get("source", "Unknown")
            source_type = result["metadata"].get("type", "unknown")
            similarity = result["similarity"]

            logger.debug(
                f"Result {i}: source={source_name}, similarity={similarity:.2%}"
            )

            # Format the chunk with source info
            context_parts.append(
                f"### Excerpt {i} {SOURCE_CITATION_FORMAT.format(filename=source_name)}\n"
                f"Relevance: {similarity:.0%}\n\n"
                f"{result['text']}"
            )

            # Track unique sources
            source_info = {
                "source": source_name,
                "type": source_type,
                "similarity": similarity
            }
            if source_info not in sources:
                sources.append(source_info)

        context_str = "\n\n---\n\n".join(context_parts)
        formatted_context = CONTEXT_TEMPLATE.format(context=context_str)

        logger.debug(f"Context prepared with {len(sources)} unique sources")

        return formatted_context, sources

    def delete_source(self, source: str) -> Dict[str, Any]:
        """
        Delete a source from the knowledge base.

        Args:
            source: Source identifier (filename or URL)

        Returns:
            Deletion result
        """
        logger.info(f"Deleting source: {source}")

        try:
            deleted_count = self.vector_store.delete_by_source(source)
            logger.info(f"Deleted {deleted_count} chunks for source: {source}")

            return {
                "success": True,
                "source": source,
                "chunks_deleted": deleted_count
            }
        except Exception as e:
            logger.error(f"Failed to delete source {source}: {e}")
            raise

    def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        logger.debug("Getting knowledge base statistics")
        stats = self.vector_store.get_collection_stats()
        logger.debug(
            f"Knowledge base stats: {stats['total_chunks']} chunks, "
            f"{stats['total_sources']} sources"
        )
        return stats

    def get_sources(self) -> List[Dict[str, Any]]:
        """Get list of all sources in the knowledge base."""
        logger.debug("Getting all sources")
        sources = self.vector_store.get_all_sources()
        logger.debug(f"Found {len(sources)} sources")
        return sources

    def clear_knowledge_base(self) -> None:
        """Clear all documents from the knowledge base."""
        logger.warning("Clearing entire knowledge base")
        self.vector_store.clear_collection()
        logger.info("Knowledge base cleared")
