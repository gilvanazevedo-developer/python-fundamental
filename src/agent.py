"""
AI GURU Agent Module
The main agent that combines RAG retrieval with Claude for responses.
"""

import random
from typing import List, Dict, Any, Optional, Generator

import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS, TEMPERATURE
from config.prompts import SYSTEM_PROMPT, GREETING_TEMPLATES, USER_NAME, AGENT_NAME
from src.rag_pipeline import RAGPipeline
from src.logger import get_logger
from src.utils.retry import retry, RetryError, retry_with_fallback

logger = get_logger(__name__)


class AIGuruAgent:
    """AI GURU - Personalized RAG Research Assistant."""

    def __init__(self):
        """Initialize the AI GURU agent."""
        logger.info(f"Initializing {AGENT_NAME} Agent")

        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not found in environment")
            raise ValueError(
                "ANTHROPIC_API_KEY not found. "
                "Please set it in your .env file."
            )

        try:
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.debug("Anthropic client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise

        self.rag_pipeline = RAGPipeline()
        self.conversation_history: List[Dict[str, str]] = []

        logger.info(f"{AGENT_NAME} Agent initialized successfully")

    def get_greeting(self) -> str:
        """Get a random greeting for the user."""
        greeting = random.choice(GREETING_TEMPLATES)
        logger.debug(f"Generated greeting for {USER_NAME}")
        return greeting

    @retry(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError)
    )
    def _call_claude_api(self, messages: List[Dict[str, str]]) -> anthropic.types.Message:
        """
        Make a call to the Claude API with retry logic.

        Args:
            messages: List of message dicts for the API

        Returns:
            Claude API response
        """
        logger.debug(f"Calling Claude API (model: {CLAUDE_MODEL})")

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        logger.debug(
            f"Claude API response received: "
            f"input_tokens={response.usage.input_tokens}, "
            f"output_tokens={response.usage.output_tokens}"
        )

        return response

    def chat(
        self,
        user_message: str,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user message and generate a response.

        Args:
            user_message: The user's message
            use_rag: Whether to retrieve context from knowledge base

        Returns:
            Dict containing response, sources, and metadata
        """
        logger.info(f"Processing chat message: {user_message[:50]}...")

        # Retrieve context if RAG is enabled
        context = ""
        sources = []

        if use_rag:
            logger.debug("RAG enabled, retrieving context")
            try:
                context, sources = self.rag_pipeline.retrieve_context(user_message)
                logger.debug(f"Retrieved {len(sources)} sources for context")
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG context: {e}. Proceeding without context.")
                context = ""
                sources = []

        # Build the messages
        messages = self._build_messages(user_message, context)

        # Call Claude API with retry
        try:
            response = self._call_claude_api(messages)
            assistant_message = response.content[0].text
        except RetryError as e:
            logger.error(f"Claude API call failed after retries: {e}")
            assistant_message = (
                f"I apologize, {USER_NAME}, but I'm having trouble connecting to my "
                "knowledge systems right now. Please try again in a moment."
            )
            return {
                "response": assistant_message,
                "sources": [],
                "model": CLAUDE_MODEL,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {e}")
            raise

        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        logger.info("Chat response generated successfully")

        return {
            "response": assistant_message,
            "sources": sources,
            "model": CLAUDE_MODEL,
            "tokens_used": {
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
        }

    def chat_stream(
        self,
        user_message: str,
        use_rag: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Process a user message and stream the response.

        Args:
            user_message: The user's message
            use_rag: Whether to retrieve context from knowledge base

        Yields:
            Dict containing response chunks or final metadata
        """
        logger.info(f"Processing streaming chat: {user_message[:50]}...")

        # Retrieve context if RAG is enabled
        context = ""
        sources = []

        if use_rag:
            logger.debug("RAG enabled, retrieving context")
            try:
                context, sources = self.rag_pipeline.retrieve_context(user_message)
                # Yield sources first
                yield {"type": "sources", "sources": sources}
                logger.debug(f"Retrieved {len(sources)} sources for context")
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG context: {e}. Proceeding without context.")
                context = ""
                sources = []
                yield {"type": "sources", "sources": []}

        # Build the messages
        messages = self._build_messages(user_message, context)

        # Stream from Claude API
        full_response = ""

        try:
            logger.debug(f"Starting Claude API stream (model: {CLAUDE_MODEL})")
            with self.client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield {"type": "text", "content": text}

            logger.debug(f"Stream completed, total response length: {len(full_response)}")

        except (anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError) as e:
            logger.error(f"Claude API stream error: {e}")
            error_message = (
                f"\n\n[I apologize, {USER_NAME}, but I encountered a connection issue. "
                "Please try again.]"
            )
            yield {"type": "text", "content": error_message}
            full_response += error_message

        except Exception as e:
            logger.error(f"Unexpected error in Claude API stream: {e}")
            raise

        # Update conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })

        logger.info("Streaming chat completed")

        # Yield final metadata
        yield {
            "type": "done",
            "model": CLAUDE_MODEL
        }

    def _build_messages(
        self,
        user_message: str,
        context: str
    ) -> List[Dict[str, str]]:
        """
        Build the message list for the API call.

        Args:
            user_message: Current user message
            context: Retrieved context (or empty string)

        Returns:
            List of message dicts for the API
        """
        messages = []

        # Add conversation history (keep last 10 exchanges)
        history_limit = 20  # 10 user + 10 assistant messages
        recent_history = self.conversation_history[-history_limit:]

        for msg in recent_history:
            messages.append(msg)

        logger.debug(f"Including {len(recent_history)} messages from history")

        # Add current user message with context
        if context:
            current_message = f"{context}\n\n## User Question\n{user_message}"
        else:
            current_message = user_message

        messages.append({
            "role": "user",
            "content": current_message
        })

        return messages

    def clear_history(self) -> None:
        """Clear the conversation history."""
        logger.info("Clearing conversation history")
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()

    # Knowledge base management methods (delegated to RAG pipeline)

    def ingest_pdf(self, file_path: str) -> Dict[str, Any]:
        """Ingest a PDF document."""
        logger.info(f"Agent ingesting PDF: {file_path}")
        return self.rag_pipeline.ingest_pdf(file_path)

    def ingest_pdf_upload(self, uploaded_file, filename: str) -> Dict[str, Any]:
        """Ingest an uploaded PDF file."""
        logger.info(f"Agent ingesting uploaded PDF: {filename}")
        return self.rag_pipeline.ingest_pdf_upload(uploaded_file, filename)

    def ingest_url(self, url: str) -> Dict[str, Any]:
        """Ingest content from a URL."""
        logger.info(f"Agent ingesting URL: {url}")
        return self.rag_pipeline.ingest_url(url)

    def delete_source(self, source: str) -> Dict[str, Any]:
        """Delete a source from the knowledge base."""
        logger.info(f"Agent deleting source: {source}")
        return self.rag_pipeline.delete_source(source)

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return self.rag_pipeline.get_knowledge_base_stats()

    def get_sources(self) -> List[Dict[str, Any]]:
        """Get all sources in the knowledge base."""
        return self.rag_pipeline.get_sources()

    def clear_knowledge_base(self) -> None:
        """Clear the knowledge base."""
        logger.warning("Agent clearing knowledge base")
        self.rag_pipeline.clear_knowledge_base()
