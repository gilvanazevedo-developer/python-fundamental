"""
AI GURU Configuration Settings
Centralized configuration for the RAG research assistant.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# ChromaDB Configuration
CHROMA_USE_CLOUD = os.getenv("CHROMA_USE_CLOUD", "false").lower() == "true"

# ChromaDB Cloud Settings
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")

# ChromaDB Local Settings
CHROMA_COLLECTION_NAME = "ai_guru_knowledge"
CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", str(CHROMA_DIR))

# Text Chunking Configuration
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200  # characters

# RAG Configuration
TOP_K_RESULTS = 5  # Number of relevant chunks to retrieve
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score for retrieval

# Claude API Configuration
MAX_TOKENS = 4096
TEMPERATURE = 0.7

# Document Processing
SUPPORTED_PDF_EXTENSIONS = [".pdf"]
REQUEST_TIMEOUT = 30  # seconds for web requests
MAX_CONTENT_LENGTH = 100000  # characters for web content
