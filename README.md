# AI GURU - Personalized RAG Research Assistant

AI GURU is a personalized research assistant powered by Claude AI and RAG (Retrieval-Augmented Generation). It allows you to build a personal knowledge base from PDFs and web content, then have intelligent conversations with your documents.

## Features

- **Personal Knowledge Base**: Upload PDFs and ingest web content to build your research collection
- **RAG-Powered Responses**: Get answers grounded in your documents with source citations
- **Streaming Chat**: Real-time response streaming for a fluid conversation experience
- **Multi-Domain Expertise**: Specialized knowledge in Management, AI, Innovation, and Operational Research
- **Source Management**: View, manage, and delete sources from your knowledge base

## Prerequisites

- **Python 3.11 or 3.12** (Python 3.13+ not yet supported due to dependency constraints)
- **Anthropic API Key**: Get one from [Anthropic Console](https://console.anthropic.com/)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd python-research
```

### 2. Install Python 3.12 (if needed)

**macOS (Homebrew):**
```bash
brew install python@3.12
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv
```

### 3. Create Virtual Environment

```bash
# macOS with Homebrew Python
/opt/homebrew/bin/python3.12 -m venv venv

# Or on Linux/other systems
python3.12 -m venv venv
```

### 4. Activate Virtual Environment

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Configure API Key

Edit `.env` and add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your-api-key-here
```

### Optional Configuration

```env
# Claude model (default: claude-sonnet-4-20250514)
CLAUDE_MODEL=claude-sonnet-4-20250514

# Data storage paths
CHROMA_PERSIST_PATH=./data/chroma_db
DOCUMENTS_PATH=./data/documents
```

## Starting the Application

### Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
streamlit run app.py --server.headless true
```

### Access the Application

Open your browser and navigate to:
- **Local**: http://localhost:8501
- **Network**: http://your-ip:8501

## Usage

### Building Your Knowledge Base

1. **Upload PDFs**: Use the sidebar to upload PDF documents
2. **Add Web Content**: Enter URLs to ingest articles and web pages
3. **Manage Sources**: View and delete sources from the sidebar

### Chatting with AI GURU

1. Type your question in the chat input
2. AI GURU will search your knowledge base for relevant context
3. Responses include source citations when using your documents
4. View sources by expanding the "Sources" section below responses

### Example Questions

- "Summarize the key findings from my uploaded research paper"
- "What does my knowledge base say about innovation strategies?"
- "Compare the concepts from different sources I've uploaded"

## Project Structure

```
python-research/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .env                  # Your configuration (create from .env.example)
├── config/
│   ├── settings.py       # Application settings
│   └── prompts.py        # AI personality and prompts
├── src/
│   ├── agent.py          # Main AI agent
│   ├── rag_pipeline.py   # RAG retrieval pipeline
│   ├── vector_store.py   # ChromaDB vector store
│   ├── embeddings.py     # Sentence embeddings
│   └── document_processor.py  # PDF and URL processing
├── data/
│   ├── chroma_db/        # Vector database storage
│   └── documents/        # Uploaded documents
└── tests/                # Test files
```

## Troubleshooting

### Dependencies fail to install

Ensure you're using Python 3.11 or 3.12. Check your version:
```bash
python --version
```

### Application won't start

1. Verify your `.env` file exists and contains a valid API key
2. Ensure the virtual environment is activated
3. Check that all dependencies are installed

### "ANTHROPIC_API_KEY not found" error

Make sure your `.env` file is in the project root and contains:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

## License

This project is for personal research use.
