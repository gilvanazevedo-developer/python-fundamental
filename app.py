"""
AI GURU - Personalized RAG Research Assistant
Enhanced Streamlit application with modern UI.
"""

import streamlit as st
from datetime import datetime
import json

from src.agent import AIGuruAgent
from src.logger import get_logger
from config.prompts import AGENT_NAME, USER_NAME, EXPERTISE_AREAS

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title=f"{AGENT_NAME} - Research Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }

    /* Stats card styling */
    .stats-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }

    .stats-card h4 {
        margin: 0 0 0.5rem 0;
        color: #333;
    }

    .stats-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #667eea;
    }

    /* Source item styling */
    .source-item {
        background-color: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #28a745;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .source-item.url {
        border-left-color: #17a2b8;
    }

    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }

    .chat-message.user {
        background-color: #e3f2fd;
    }

    .chat-message.assistant {
        background-color: #f5f5f5;
    }

    /* Quick prompt buttons */
    .quick-prompt {
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        margin: 0.25rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .quick-prompt:hover {
        background-color: #667eea;
        color: white;
        border-color: #667eea;
    }

    /* Expertise card */
    .expertise-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
        transition: transform 0.2s;
    }

    .expertise-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .expertise-icon {
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #f0f2f6;
        border-radius: 8px;
    }

    /* File uploader */
    .stFileUploader {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 1rem;
    }

    /* Welcome message */
    .welcome-box {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid #667eea30;
    }

    /* Metrics row */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        flex: 1;
        background: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e0e0e0;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }

    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "agent" not in st.session_state:
        logger.info("Initializing new session")
        try:
            with st.spinner("🚀 Initializing AI GURU..."):
                st.session_state.agent = AIGuruAgent()
            logger.info("Agent initialized successfully for session")
        except ValueError as e:
            logger.error(f"Failed to initialize agent: {e}")
            st.error(f"⚠️ {str(e)}")
            st.info("Please check your `.env` file and ensure ANTHROPIC_API_KEY is set.")
            st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = None


def display_sidebar():
    """Display the sidebar with knowledge base management."""
    with st.sidebar:
        # Logo/Brand
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <span style="font-size: 3rem;">🧠</span>
            <h2 style="margin: 0.5rem 0 0 0;">AI GURU</h2>
            <p style="color: #666; font-size: 0.9rem;">Research Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Knowledge Base Stats
        st.markdown("### 📊 Knowledge Base")
        stats = st.session_state.agent.get_knowledge_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", stats['total_sources'])
        with col2:
            st.metric("Chunks", stats['total_chunks'])

        # Storage type indicator
        storage_type = stats.get('storage_type', 'local')
        storage_icon = "☁️" if storage_type == "cloud" else "💾"
        st.caption(f"{storage_icon} Storage: {storage_type.title()}")

        st.divider()

        # Document Upload Section
        with st.expander("📄 Upload PDF", expanded=True):
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=["pdf"],
                key="pdf_uploader",
                help="Upload PDF documents to add to your knowledge base"
            )

            if uploaded_file is not None:
                st.info(f"📎 Selected: {uploaded_file.name}")
                if st.button("⬆️ Ingest PDF", key="ingest_pdf", use_container_width=True):
                    logger.info(f"User uploading PDF: {uploaded_file.name}")
                    with st.spinner("Processing PDF..."):
                        try:
                            result = st.session_state.agent.ingest_pdf_upload(
                                uploaded_file,
                                uploaded_file.name
                            )
                            logger.info(
                                f"PDF ingested: {result['source']}, "
                                f"chunks={result['chunks_created']}"
                            )
                            st.success(
                                f"✅ Ingested '{result['source']}' "
                                f"({result['chunks_created']} chunks)"
                            )
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            logger.error(f"PDF ingestion failed: {e}")
                            st.error(f"❌ Error: {str(e)}")

        # URL Input Section
        with st.expander("🌐 Add Web Content", expanded=True):
            url_input = st.text_input(
                "Enter URL",
                placeholder="https://example.com/article",
                key="url_input",
                help="Add content from web pages to your knowledge base"
            )

            if st.button("🔗 Ingest URL", key="ingest_url", use_container_width=True):
                if url_input:
                    if not url_input.startswith(("http://", "https://")):
                        st.warning("⚠️ Please enter a valid URL starting with http:// or https://")
                    else:
                        logger.info(f"User ingesting URL: {url_input}")
                        with st.spinner("Fetching and processing URL..."):
                            try:
                                result = st.session_state.agent.ingest_url(url_input)
                                if result.get("success", True):
                                    logger.info(
                                        f"URL ingested: {result['source'][:50]}..., "
                                        f"chunks={result['chunks_created']}"
                                    )
                                    st.success(
                                        f"✅ Ingested successfully! "
                                        f"({result['chunks_created']} chunks)"
                                    )
                                    st.balloons()
                                else:
                                    logger.warning(f"URL ingestion returned no content: {url_input}")
                                    st.warning("⚠️ No content could be extracted")
                                st.rerun()
                            except Exception as e:
                                logger.error(f"URL ingestion failed: {e}")
                                st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Please enter a URL")

        st.divider()

        # Source List
        st.markdown("### 📚 Sources")
        sources = st.session_state.agent.get_sources()

        if sources:
            for source in sources:
                source_name = source["source"]
                display_name = source_name[:25] + "..." if len(source_name) > 25 else source_name
                icon = "📄" if source["type"] == "pdf" else "🌐"

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{icon} **{display_name}**")
                    st.caption(f"{source['chunk_count']} chunks")
                with col2:
                    if st.button("🗑️", key=f"del_{hash(source['source'])}", help="Delete this source"):
                        logger.info(f"User deleting source: {source['source']}")
                        with st.spinner("Deleting..."):
                            st.session_state.agent.delete_source(source["source"])
                        st.rerun()
        else:
            st.info("📭 No documents yet. Upload PDFs or add URLs above!")

        st.divider()

        # Actions
        st.markdown("### ⚡ Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
                logger.info("User clearing chat history")
                st.session_state.messages = []
                st.session_state.agent.clear_history()
                st.session_state.show_welcome = True
                st.rerun()
        with col2:
            if st.button("🧹 Clear KB", key="clear_kb", use_container_width=True):
                logger.warning("User clearing knowledge base")
                st.session_state.agent.clear_knowledge_base()
                st.rerun()

        # Export chat
        if st.session_state.messages:
            if st.button("📥 Export Chat", key="export_chat", use_container_width=True):
                chat_export = {
                    "exported_at": datetime.now().isoformat(),
                    "user": USER_NAME,
                    "messages": st.session_state.messages
                }
                st.download_button(
                    label="💾 Download JSON",
                    data=json.dumps(chat_export, indent=2),
                    file_name=f"ai_guru_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


def display_welcome():
    """Display welcome message with quick start options."""
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1>🧠 {AGENT_NAME}</h1>
        <p>Your Personalized Research Assistant</p>
    </div>
    """, unsafe_allow_html=True)

    # Welcome box
    st.markdown(f"""
    <div class="welcome-box">
        <h3>👋 Welcome, {USER_NAME}!</h3>
        <p>I'm your AI-powered research assistant specialized in <strong>Management</strong>,
        <strong>Artificial Intelligence</strong>, <strong>Innovation</strong>, and <strong>Operational Research</strong>.</p>
        <p>Upload documents or add URLs to build your knowledge base, then ask me anything!</p>
    </div>
    """, unsafe_allow_html=True)

    # Expertise areas
    st.markdown("### 🎯 My Expertise Areas")

    expertise_icons = {
        "management": "👔",
        "artificial_intelligence": "🤖",
        "innovation": "💡",
        "operational_research": "📊"
    }

    cols = st.columns(2)
    for idx, (key, area) in enumerate(EXPERTISE_AREAS.items()):
        with cols[idx % 2]:
            icon = expertise_icons.get(key, "📚")
            with st.container():
                st.markdown(f"""
                <div class="expertise-card">
                    <span class="expertise-icon">{icon}</span>
                    <strong>{area['name']}</strong>
                    <ul style="margin: 0.5rem 0 0 1rem; padding: 0; font-size: 0.85rem; color: #666;">
                        {''.join(f'<li>{topic}</li>' for topic in area['topics'][:3])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick prompts
    st.markdown("### 💬 Quick Start Prompts")
    st.caption("Click any prompt to start a conversation:")

    quick_prompts = [
        "What are the key principles of effective leadership?",
        "Explain how RAG systems work in AI applications",
        "What is design thinking and how can it drive innovation?",
        "How can operational research optimize business decisions?",
        "What are the ethical considerations in AI development?",
        "Compare different change management frameworks"
    ]

    cols = st.columns(2)
    for idx, prompt in enumerate(quick_prompts):
        with cols[idx % 2]:
            if st.button(f"💡 {prompt[:40]}...", key=f"quick_{idx}", use_container_width=True):
                st.session_state.selected_prompt = prompt
                st.session_state.show_welcome = False
                st.rerun()


def display_chat():
    """Display the main chat interface."""
    # Header
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"### 💬 Chat with {AGENT_NAME}")
    with col2:
        if st.button("🏠 Home"):
            st.session_state.show_welcome = True
            st.rerun()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🧠"):
            st.markdown(message["content"])

            # Display sources if available
            if message.get("sources"):
                with st.expander(f"📚 Sources ({len(message['sources'])})"):
                    for source in message["sources"]:
                        source_type = "📄" if source["type"] == "pdf" else "🌐"
                        relevance_color = "#28a745" if source['similarity'] > 0.7 else "#ffc107" if source['similarity'] > 0.5 else "#dc3545"
                        st.markdown(
                            f"{source_type} **{source['source']}** "
                            f"<span style='color: {relevance_color}'>(Relevance: {source['similarity']:.0%})</span>",
                            unsafe_allow_html=True
                        )

    # Check for quick prompt selection
    initial_prompt = None
    if st.session_state.selected_prompt:
        initial_prompt = st.session_state.selected_prompt
        st.session_state.selected_prompt = None

    # Chat input
    prompt = st.chat_input("Ask me anything...", key="chat_input")

    # Use either the chat input or the quick prompt
    if prompt or initial_prompt:
        user_message = prompt or initial_prompt
        logger.info(f"User query: {user_message[:50]}...")

        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_message
        })

        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_message)

        # Generate response
        with st.chat_message("assistant", avatar="🧠"):
            message_placeholder = st.empty()
            sources_placeholder = st.empty()

            full_response = ""
            sources = []

            logger.debug("Starting response stream")

            # Show typing indicator
            message_placeholder.markdown("🤔 Thinking...")

            # Stream the response
            try:
                for chunk in st.session_state.agent.chat_stream(user_message):
                    if chunk["type"] == "sources":
                        sources = chunk["sources"]
                        logger.debug(f"Received {len(sources)} sources")
                    elif chunk["type"] == "text":
                        full_response += chunk["content"]
                        message_placeholder.markdown(full_response + "▌")
                    elif chunk["type"] == "done":
                        message_placeholder.markdown(full_response)
                        logger.info("Response stream completed")
            except Exception as e:
                logger.error(f"Error during chat: {e}")
                message_placeholder.error(f"❌ An error occurred: {str(e)}")
                full_response = f"I apologize, but I encountered an error. Please try again."
                message_placeholder.markdown(full_response)

            # Display sources
            if sources:
                with sources_placeholder.expander(f"📚 Sources ({len(sources)})"):
                    for source in sources:
                        source_type = "📄" if source["type"] == "pdf" else "🌐"
                        relevance_color = "#28a745" if source['similarity'] > 0.7 else "#ffc107" if source['similarity'] > 0.5 else "#dc3545"
                        st.markdown(
                            f"{source_type} **{source['source']}** "
                            f"<span style='color: {relevance_color}'>(Relevance: {source['similarity']:.0%})</span>",
                            unsafe_allow_html=True
                        )

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "sources": sources
        })

        logger.debug(f"Response saved, length={len(full_response)}")
        st.rerun()


def main():
    """Main application entry point."""
    logger.info("Application starting")
    initialize_session_state()
    display_sidebar()

    # Show welcome or chat based on state
    if st.session_state.show_welcome and not st.session_state.messages:
        display_welcome()
    else:
        st.session_state.show_welcome = False
        display_chat()


if __name__ == "__main__":
    main()
