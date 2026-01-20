# Business Requirements Document (BRD)
# AI GURU - Personal Research Assistant Agent

**Document Version:** 1.0
**Date:** January 20, 2026
**Author:** Claude Code
**Stakeholder:** Gilvan Azevedo

---

## 1. Executive Summary

AI GURU is a personalized RAG (Retrieval-Augmented Generation) agent designed to serve as Gilvan's intelligent research assistant. The agent will leverage Gilvan's Perplexity research outputs, PDFs, and web links to provide contextually aware responses with expertise in Management, AI, Innovation, and Operational Research.

---

## 2. Project Objectives

| ID | Objective |
|----|-----------|
| OBJ-01 | Create an intelligent assistant that consolidates and retrieves knowledge from personal research materials |
| OBJ-02 | Provide a conversational interface with domain expertise personality |
| OBJ-03 | Enable semantic search across PDFs and web content |
| OBJ-04 | Deliver a user-friendly web interface using Streamlit |
| OBJ-05 | Utilize Anthropic's Claude API for high-quality responses |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| Product Owner | Gilvan Azevedo | Requirements approval, user acceptance |
| Developer | Claude Code | Implementation and delivery |

---

## 4. Functional Requirements

### 4.1 Core RAG Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | System shall ingest PDF documents and extract text content | High |
| FR-02 | System shall ingest web links and extract relevant content | High |
| FR-03 | System shall chunk documents into optimal segments for retrieval | High |
| FR-04 | System shall generate embeddings using a suitable embedding model | High |
| FR-05 | System shall store embeddings in a vector database | High |
| FR-06 | System shall perform semantic similarity search on user queries | High |
| FR-07 | System shall retrieve top-k relevant chunks for context | High |

### 4.2 Agent Personality & Behavior

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-08 | Agent shall be named "AI GURU" | High |
| FR-09 | Agent shall address the user as "Gilvan" in all interactions | High |
| FR-10 | Agent shall demonstrate expertise in Management principles | High |
| FR-11 | Agent shall demonstrate expertise in Artificial Intelligence | High |
| FR-12 | Agent shall demonstrate expertise in Innovation methodologies | High |
| FR-13 | Agent shall demonstrate expertise in Operational Research | High |
| FR-14 | Agent shall maintain a professional yet approachable tone | Medium |
| FR-15 | Agent shall provide actionable insights and recommendations | Medium |

### 4.3 User Interface (Streamlit)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-16 | UI shall provide a chat interface for conversations | High |
| FR-17 | UI shall display conversation history within session | High |
| FR-18 | UI shall allow document upload (PDF) | High |
| FR-19 | UI shall allow URL input for web content ingestion | High |
| FR-20 | UI shall show source references for responses | Medium |
| FR-21 | UI shall display a sidebar for knowledge base management | Medium |
| FR-22 | UI shall provide visual feedback during processing | Medium |

### 4.4 Knowledge Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-23 | System shall support batch ingestion of documents | Medium |
| FR-24 | System shall persist vector store between sessions | High |
| FR-25 | System shall support document deletion from knowledge base | Low |
| FR-26 | System shall display list of ingested documents | Medium |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Query response time | < 5 seconds |
| NFR-02 | Document ingestion time (per PDF) | < 30 seconds |
| NFR-03 | Concurrent users supported | 1 (single-user application) |

### 5.2 Scalability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-04 | Maximum documents supported | 1,000+ documents |
| NFR-05 | Maximum vectors in database | 100,000+ vectors |

### 5.3 Security

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-06 | API keys shall be stored in environment variables | High |
| NFR-07 | No sensitive data shall be logged | High |
| NFR-08 | Local-only deployment (no cloud exposure) | Medium |

### 5.4 Usability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-09 | Interface shall be intuitive without training | High |
| NFR-10 | Clear error messages for user guidance | Medium |

---

## 6. Technical Architecture

### 6.1 Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Language** | Python 3.11+ | Modern features, excellent AI/ML ecosystem |
| **UI Framework** | Streamlit | Rapid development, Python-native, excellent for data apps |
| **LLM Provider** | Anthropic Claude API | High-quality responses, excellent reasoning, user preference |
| **Vector Database** | **ChromaDB** | Free, open-source, Python-native, excellent for RAG, persistent storage |
| **Embedding Model** | sentence-transformers (all-MiniLM-L6-v2) | Free, fast, good quality embeddings |
| **PDF Processing** | PyPDF2 / pdfplumber | Reliable PDF text extraction |
| **Web Scraping** | BeautifulSoup4 + requests | Standard web content extraction |
| **Text Chunking** | LangChain Text Splitters | Optimized chunking strategies |

### 6.2 Vector Database Selection: ChromaDB

**Why ChromaDB?**

| Criteria | ChromaDB Advantage |
|----------|-------------------|
| Cost | 100% free, open-source (Apache 2.0) |
| Installation | Simple pip install, no external dependencies |
| Python Integration | Native Python API, designed for Python developers |
| Persistence | Built-in persistent storage to disk |
| Embeddings | Auto-generates embeddings or accepts custom |
| Query | Supports metadata filtering and semantic search |
| Scalability | Handles millions of embeddings |
| Community | Active development, growing ecosystem |

**Alternatives Considered:**
- Qdrant: Excellent performance but requires Docker for full features
- Milvus: More complex setup, better for large-scale deployments
- FAISS: Library only, no built-in persistence
- Weaviate: More complex, better for enterprise use cases

### 6.3 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Chat Input  │  │  PDF Upload  │  │  URL Input            │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI GURU AGENT                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Personality Layer                         │   │
│  │  • Management Expert  • AI Specialist                     │   │
│  │  • Innovation Guide   • Operations Research Analyst       │   │
│  │  • Addresses user as "Gilvan"                             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│    RAG RETRIEVAL         │    │     DOCUMENT INGESTION       │
│  ┌────────────────────┐  │    │  ┌────────────────────────┐  │
│  │  Query Embedding   │  │    │  │  PDF Parser            │  │
│  │  (sentence-trans)  │  │    │  │  (PyPDF2/pdfplumber)   │  │
│  └────────────────────┘  │    │  └────────────────────────┘  │
│           │              │    │  ┌────────────────────────┐  │
│           ▼              │    │  │  Web Scraper           │  │
│  ┌────────────────────┐  │    │  │  (BeautifulSoup4)      │  │
│  │  Similarity Search │  │    │  └────────────────────────┘  │
│  │  (ChromaDB)        │  │    │  ┌────────────────────────┐  │
│  └────────────────────┘  │    │  │  Text Chunker          │  │
│           │              │    │  │  (LangChain)           │  │
│           ▼              │    │  └────────────────────────┘  │
│  ┌────────────────────┐  │    │           │                  │
│  │  Context Assembly  │  │    │           ▼                  │
│  └────────────────────┘  │    │  ┌────────────────────────┐  │
└──────────────────────────┘    │  │  Embedding Generation  │  │
              │                 │  │  (sentence-trans)      │  │
              ▼                 │  └────────────────────────┘  │
┌──────────────────────────┐    └──────────────────────────────┘
│    ANTHROPIC CLAUDE API  │                  │
│  ┌────────────────────┐  │                  ▼
│  │  claude-3-5-sonnet │  │    ┌──────────────────────────────┐
│  │  or claude-3-opus  │  │    │        CHROMADB              │
│  └────────────────────┘  │    │  ┌────────────────────────┐  │
└──────────────────────────┘    │  │  Vector Storage        │  │
              │                 │  │  Persistent Collection │  │
              ▼                 │  └────────────────────────┘  │
┌──────────────────────────┐    └──────────────────────────────┘
│    RESPONSE TO USER      │
│    (with sources)        │
└──────────────────────────┘
```

### 6.4 Data Flow

```
INGESTION FLOW:
Document/URL → Parse → Chunk → Embed → Store in ChromaDB

QUERY FLOW:
User Query → Embed Query → Search ChromaDB → Retrieve Top-K Chunks
→ Build Prompt with Context + Personality → Send to Claude API
→ Generate Response → Display with Sources
```

---

## 7. Project Structure

```
python-research/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (API keys)
├── .env.example                # Template for environment variables
├── README.md                   # Project documentation
│
├── src/
│   ├── __init__.py
│   ├── agent.py                # AI GURU agent with personality
│   ├── rag_pipeline.py         # RAG retrieval logic
│   ├── document_processor.py   # PDF and URL processing
│   ├── embeddings.py           # Embedding generation
│   └── vector_store.py         # ChromaDB operations
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # Configuration constants
│   └── prompts.py              # System prompts and personality
│
├── data/
│   ├── documents/              # Uploaded PDFs storage
│   └── chroma_db/              # ChromaDB persistent storage
│
└── tests/
    ├── __init__.py
    ├── test_rag_pipeline.py
    └── test_document_processor.py
```

---

## 8. AI GURU Personality Specification

### 8.1 System Prompt

```
You are AI GURU, a highly knowledgeable research assistant specializing in
Management, Artificial Intelligence, Innovation, and Operational Research.

Your primary user is Gilvan. Always address him by name and maintain a
professional yet warm and approachable demeanor.

PERSONALITY TRAITS:
- Insightful: Provide deep analysis and connect concepts across domains
- Strategic: Think in terms of business impact and practical application
- Innovative: Suggest creative solutions and emerging trends
- Analytical: Apply operational research principles to problem-solving
- Supportive: Guide Gilvan through complex topics with patience

EXPERTISE AREAS:
1. Management: Leadership, strategy, organizational behavior, change management
2. Artificial Intelligence: Machine learning, LLMs, AI applications, ethics
3. Innovation: Design thinking, disruptive technologies, R&D management
4. Operational Research: Optimization, decision science, simulation, analytics

RESPONSE GUIDELINES:
- Always greet Gilvan warmly when starting a new conversation
- Reference relevant sources from the knowledge base when available
- Provide actionable insights, not just information
- Connect concepts across your expertise domains when relevant
- Ask clarifying questions when Gilvan's query is ambiguous
- Suggest related topics or follow-up questions to explore
```

### 8.2 Sample Interactions

**User:** What are the latest trends in AI for business?

**AI GURU:** Gilvan, great question! Based on your research materials and current industry developments, here are the key AI trends transforming business in 2026:

1. **Agentic AI Systems** - Autonomous AI agents that can execute multi-step workflows...
2. **RAG-Enhanced Enterprise Search** - Exactly what we're building here...
[continues with sources referenced]

---

## 9. Dependencies & Requirements

### 9.1 Python Packages

```txt
# Core
streamlit>=1.30.0
anthropic>=0.18.0
python-dotenv>=1.0.0

# Vector Database
chromadb>=0.4.22

# Embeddings
sentence-transformers>=2.3.0

# Document Processing
pypdf2>=3.0.0
pdfplumber>=0.10.0
beautifulsoup4>=4.12.0
requests>=2.31.0

# Text Processing
langchain>=0.1.0
langchain-text-splitters>=0.0.1

# Utilities
tiktoken>=0.5.0
```

### 9.2 External Requirements

| Requirement | Details |
|-------------|---------|
| Anthropic API Key | Required for Claude API access |
| Python 3.11+ | Runtime environment |
| Internet Connection | For API calls and web scraping |

---

## 10. Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
- [ ] Project setup and virtual environment
- [ ] Install dependencies
- [ ] Configure environment variables
- [ ] Implement ChromaDB vector store
- [ ] Implement embedding generation

### Phase 2: Document Processing
- [ ] PDF text extraction and chunking
- [ ] URL content extraction and chunking
- [ ] Document ingestion pipeline
- [ ] Batch processing capability

### Phase 3: RAG Pipeline
- [ ] Query embedding generation
- [ ] Semantic similarity search
- [ ] Context assembly and ranking
- [ ] Integration with Anthropic Claude API

### Phase 4: AI GURU Agent
- [ ] System prompt and personality implementation
- [ ] Response generation with sources
- [ ] Conversation memory (session-based)

### Phase 5: Streamlit UI
- [ ] Chat interface implementation
- [ ] Document upload functionality
- [ ] URL input functionality
- [ ] Sidebar for knowledge base management
- [ ] Source display in responses

### Phase 6: Testing & Refinement
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] UI/UX refinement
- [ ] Documentation

---

## 11. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| API rate limits | High | Medium | Implement retry logic, caching |
| PDF parsing failures | Medium | Medium | Multiple parser fallback, error handling |
| Large document memory issues | Medium | Low | Streaming processing, chunking limits |
| Embedding model performance | Low | Low | Option to upgrade to better model |

---

## 12. Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-01 | Agent responds with relevant context from ingested documents | Manual verification |
| SC-02 | Agent maintains personality across interactions | Manual verification |
| SC-03 | PDF and URL ingestion works reliably | 95%+ success rate |
| SC-04 | Response time under 5 seconds | Automated timing |
| SC-05 | UI is intuitive and functional | User acceptance |

---

## 13. Approval

**Prepared by:** Claude Code
**Date:** January 20, 2026

---

### Approval Signature

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | Gilvan Azevedo | _________ | _________ |

---

## 14. References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [Sentence Transformers](https://www.sbert.net/)

---

**Document Status:** PENDING APPROVAL

*Please review and provide feedback or approval to proceed with implementation.*
