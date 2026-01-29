"""
Tests for AI GURU Agent Module
"""

import pytest
from unittest.mock import MagicMock, patch
import anthropic


class TestAIGuruAgentInit:
    """Tests for AIGuruAgent initialization."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_init_success(self, mock_anthropic, mock_rag_pipeline):
        """Test successful agent initialization."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()

        assert agent.client is not None
        assert agent.rag_pipeline is not None
        assert agent.conversation_history == []

    @patch("src.agent.ANTHROPIC_API_KEY", None)
    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        from src.agent import AIGuruAgent

        with pytest.raises(ValueError) as exc_info:
            AIGuruAgent()

        assert "ANTHROPIC_API_KEY not found" in str(exc_info.value)


class TestGetGreeting:
    """Tests for greeting generation."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_get_greeting_returns_string(self, mock_anthropic, mock_rag_pipeline):
        """Test that get_greeting returns a string."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        greeting = agent.get_greeting()

        assert isinstance(greeting, str)
        assert len(greeting) > 0

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_get_greeting_contains_user_name(self, mock_anthropic, mock_rag_pipeline):
        """Test that greeting contains the user name."""
        from src.agent import AIGuruAgent
        from config.prompts import USER_NAME

        agent = AIGuruAgent()
        greeting = agent.get_greeting()

        assert USER_NAME in greeting


class TestChat:
    """Tests for chat functionality."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_success(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test successful chat response."""
        from src.agent import AIGuruAgent

        mock_anthropic.return_value.messages.create.return_value = mock_anthropic_response
        mock_rag_pipeline.return_value.retrieve_context.return_value = ("context", [])

        agent = AIGuruAgent()
        result = agent.chat("What is AI?")

        assert "response" in result
        assert "sources" in result
        assert "model" in result
        assert "tokens_used" in result

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_updates_history(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test that chat updates conversation history."""
        from src.agent import AIGuruAgent

        mock_anthropic.return_value.messages.create.return_value = mock_anthropic_response
        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        agent = AIGuruAgent()
        agent.chat("First message")

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[1]["role"] == "assistant"

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_without_rag(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test chat with RAG disabled."""
        from src.agent import AIGuruAgent

        mock_anthropic.return_value.messages.create.return_value = mock_anthropic_response

        agent = AIGuruAgent()
        result = agent.chat("Hello", use_rag=False)

        mock_rag_pipeline.return_value.retrieve_context.assert_not_called()
        assert "response" in result

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_includes_sources(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test that chat includes sources from RAG."""
        from src.agent import AIGuruAgent

        mock_anthropic.return_value.messages.create.return_value = mock_anthropic_response
        mock_rag_pipeline.return_value.retrieve_context.return_value = (
            "context",
            [{"source": "test.pdf", "type": "pdf", "similarity": 0.9}]
        )

        agent = AIGuruAgent()
        result = agent.chat("Query")

        assert len(result["sources"]) == 1
        assert result["sources"][0]["source"] == "test.pdf"

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_handles_api_error_gracefully(self, mock_anthropic, mock_rag_pipeline):
        """Test that chat handles API errors gracefully with fallback response."""
        from src.agent import AIGuruAgent
        from src.utils.retry import RetryError

        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        # Simulate all retries failing - the agent returns a fallback message
        mock_anthropic.return_value.messages.create.side_effect = anthropic.APIError(
            message="API Error",
            request=MagicMock(),
            body=None
        )

        agent = AIGuruAgent()

        # The agent handles RetryError gracefully and returns a fallback response
        result = agent.chat("Query")

        # Should return an error response rather than raising
        assert "error" in result
        assert "apologize" in result["response"].lower()


class TestChatStream:
    """Tests for streaming chat functionality."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_stream_yields_chunks(self, mock_anthropic, mock_rag_pipeline):
        """Test that chat_stream yields response chunks."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        # Mock streaming response
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Hello", " ", "world"])
        mock_anthropic.return_value.messages.stream.return_value = mock_stream

        agent = AIGuruAgent()
        chunks = list(agent.chat_stream("Hi"))

        # Should have: sources, text chunks, done
        text_chunks = [c for c in chunks if c["type"] == "text"]
        assert len(text_chunks) == 3
        assert text_chunks[0]["content"] == "Hello"

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_stream_yields_sources_first(self, mock_anthropic, mock_rag_pipeline):
        """Test that chat_stream yields sources before text."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.return_value = (
            "context",
            [{"source": "test.pdf", "type": "pdf", "similarity": 0.9}]
        )

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Response"])
        mock_anthropic.return_value.messages.stream.return_value = mock_stream

        agent = AIGuruAgent()
        chunks = list(agent.chat_stream("Query"))

        assert chunks[0]["type"] == "sources"
        assert chunks[0]["sources"][0]["source"] == "test.pdf"

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_stream_yields_done_at_end(self, mock_anthropic, mock_rag_pipeline):
        """Test that chat_stream yields done message at the end."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Response"])
        mock_anthropic.return_value.messages.stream.return_value = mock_stream

        agent = AIGuruAgent()
        chunks = list(agent.chat_stream("Query"))

        assert chunks[-1]["type"] == "done"
        assert "model" in chunks[-1]

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_chat_stream_updates_history(self, mock_anthropic, mock_rag_pipeline):
        """Test that chat_stream updates conversation history."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Hello", " ", "world"])
        mock_anthropic.return_value.messages.stream.return_value = mock_stream

        agent = AIGuruAgent()
        list(agent.chat_stream("Hi"))  # Consume the generator

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[1]["content"] == "Hello world"


class TestBuildMessages:
    """Tests for message building."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_build_messages_includes_history(self, mock_anthropic, mock_rag_pipeline):
        """Test that _build_messages includes conversation history."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        agent.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        messages = agent._build_messages("New message", "")

        assert len(messages) == 3  # 2 history + 1 new
        assert messages[-1]["content"] == "New message"

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_build_messages_includes_context(self, mock_anthropic, mock_rag_pipeline):
        """Test that _build_messages includes context when provided."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()

        messages = agent._build_messages("Question", "Relevant context here")

        assert "Relevant context here" in messages[-1]["content"]
        assert "Question" in messages[-1]["content"]

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_build_messages_limits_history(self, mock_anthropic, mock_rag_pipeline):
        """Test that _build_messages limits conversation history."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        # Add more than 20 messages to history
        for i in range(30):
            agent.conversation_history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })

        messages = agent._build_messages("New message", "")

        # Should have 20 history messages + 1 new = 21
        assert len(messages) == 21


class TestConversationHistory:
    """Tests for conversation history management."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_clear_history(self, mock_anthropic, mock_rag_pipeline):
        """Test clearing conversation history."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        agent.conversation_history = [{"role": "user", "content": "Test"}]

        agent.clear_history()

        assert agent.conversation_history == []

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_get_conversation_history(self, mock_anthropic, mock_rag_pipeline):
        """Test getting conversation history copy."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        agent.conversation_history = [{"role": "user", "content": "Test"}]

        history = agent.get_conversation_history()

        # Should be a copy, not the same object
        assert history == agent.conversation_history
        assert history is not agent.conversation_history


class TestKnowledgeBaseManagement:
    """Tests for knowledge base management methods."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_ingest_pdf(self, mock_anthropic, mock_rag_pipeline):
        """Test PDF ingestion delegation."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.ingest_pdf.return_value = {"success": True}

        agent = AIGuruAgent()
        result = agent.ingest_pdf("/path/to/file.pdf")

        mock_rag_pipeline.return_value.ingest_pdf.assert_called_once_with("/path/to/file.pdf")
        assert result["success"] is True

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_ingest_url(self, mock_anthropic, mock_rag_pipeline):
        """Test URL ingestion delegation."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.ingest_url.return_value = {"success": True}

        agent = AIGuruAgent()
        result = agent.ingest_url("https://example.com")

        mock_rag_pipeline.return_value.ingest_url.assert_called_once_with("https://example.com")

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_delete_source(self, mock_anthropic, mock_rag_pipeline):
        """Test source deletion delegation."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.delete_source.return_value = {"success": True, "chunks_deleted": 5}

        agent = AIGuruAgent()
        result = agent.delete_source("test.pdf")

        mock_rag_pipeline.return_value.delete_source.assert_called_once_with("test.pdf")

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_get_knowledge_stats(self, mock_anthropic, mock_rag_pipeline):
        """Test getting knowledge stats."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.get_knowledge_base_stats.return_value = {
            "total_chunks": 100,
            "total_sources": 5
        }

        agent = AIGuruAgent()
        stats = agent.get_knowledge_stats()

        assert stats["total_chunks"] == 100

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_get_sources(self, mock_anthropic, mock_rag_pipeline):
        """Test getting sources list."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.get_sources.return_value = [
            {"source": "test.pdf", "type": "pdf"}
        ]

        agent = AIGuruAgent()
        sources = agent.get_sources()

        assert len(sources) == 1

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_clear_knowledge_base(self, mock_anthropic, mock_rag_pipeline):
        """Test clearing knowledge base."""
        from src.agent import AIGuruAgent

        agent = AIGuruAgent()
        agent.clear_knowledge_base()

        mock_rag_pipeline.return_value.clear_knowledge_base.assert_called_once()


class TestRetryLogic:
    """Tests for retry logic in agent."""

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_api_call_retries_on_error(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test that API calls retry on transient errors."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.return_value = ("", [])

        # Fail twice, succeed on third try
        mock_anthropic.return_value.messages.create.side_effect = [
            anthropic.APIConnectionError(request=MagicMock()),
            anthropic.APIConnectionError(request=MagicMock()),
            mock_anthropic_response
        ]

        agent = AIGuruAgent()
        result = agent.chat("Test query")

        assert mock_anthropic.return_value.messages.create.call_count == 3
        assert "response" in result

    @patch("src.agent.RAGPipeline")
    @patch("anthropic.Anthropic")
    def test_rag_failure_graceful_degradation(self, mock_anthropic, mock_rag_pipeline, mock_anthropic_response):
        """Test graceful degradation when RAG fails."""
        from src.agent import AIGuruAgent

        mock_rag_pipeline.return_value.retrieve_context.side_effect = Exception("RAG error")
        mock_anthropic.return_value.messages.create.return_value = mock_anthropic_response

        agent = AIGuruAgent()
        result = agent.chat("Test query")

        # Should still return a response, just without RAG context
        assert "response" in result
        assert result["sources"] == []
