"""
Streamlit web interface for the Data Analyst Agent.
"""

import sys
import streamlit as st
import pandas as pd
from pathlib import Path
import logging
from dotenv import load_dotenv
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient


# Page configuration
st.set_page_config(
    page_title="Data Analyst Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)


def init_agent(db_path, llm_provider, llm_model):
    """Initialize the agent and cache it."""
    
    try:
        # Initialize LLM client
        llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            base_url=os.getenv('LLM_BASE_URL', 'http://localhost:11434'),
            api_key=os.getenv('LLM_API_KEY')
        )
        
        # Initialize agent
        agent = DataAnalystAgent(
            database_path=db_path,
            llm_client=llm_client,
            max_retry_attempts=2,
            enable_validation=True
        )
        
        # Initialize (inspect schema and check quality)
        with st.spinner("Analyzing database..."):
            agent.initialize()
        
        return agent
    
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        return None


def main():
    st.title("🤖 Data Analyst Agent")
    st.markdown("Ask questions about your database in plain English")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Database selection
        db_path = st.text_input(
            "Database Path",
            value="data/test_messy.db",
            help="Path to your SQLite database"
        )
        
        # LLM configuration
        st.subheader("LLM Settings")
        
        llm_provider = st.selectbox(
            "Provider",
            ["ollama", "openai"],
            help="Choose your LLM provider"
        )
        
        if llm_provider == "ollama":
            llm_model = st.text_input("Model", value="llama3.2:3b")
            st.info("Make sure Ollama is running: `ollama serve`")
        else:
            llm_model = st.text_input("Model", value="gpt-3.5-turbo")
            st.info("Set your API key in .env file")
        
        # Initialize button
        if st.button("🔄 Initialize Agent", type="primary"):
            st.session_state['agent'] = None  # Reset
            st.rerun()
    
    # Initialize agent if not in session state
    if 'agent' not in st.session_state or st.session_state['agent'] is None:
        if Path(db_path).exists():
            agent = init_agent(db_path, llm_provider, llm_model)
            if agent:
                st.session_state['agent'] = agent
                st.session_state['db_path'] = db_path
                st.success("✅ Agent initialized successfully!")
        else:
            st.warning(f"Database not found: {db_path}")
            st.info("Create a test database by running: `python scripts/create_test_db.py`")
            return
    
    agent = st.session_state.get('agent')
    
    if not agent:
        st.warning("Please configure and initialize the agent first.")
        return
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["💬 Ask Questions", "📊 Schema", "🔍 Data Quality"])
    
    with tab1:
        st.header("Ask a Question")
        
        # Example questions
        with st.expander("📝 Example Questions"):
            st.markdown("""
            - Which schools had falling enrollment between 2021 and 2023?
            - What is the average teacher salary by subject?
            - How many students are currently enrolled in each school?
            - Which school has the most teachers?
            - Show me schools in District 1
            - What is the total enrollment across all schools?
            """)
        
        # Question input
        question = st.text_area(
            "Your Question",
            height=100,
            placeholder="e.g., Which schools had falling enrollment last year?"
        )
        
        col1, col2 = st.columns([1, 5])
        
        with col1:
            ask_button = st.button("🚀 Ask", type="primary", use_container_width=True)
        
        if ask_button and question:
            with st.spinner("🤔 Thinking..."):
                try:
                    # Get answer
                    answer = agent.ask(question)
                    
                    # Display answer
                    st.markdown("### 💡 Answer")
                    st.markdown(answer.answer)
                    
                    # Confidence indicator
                    conf_pct = answer.confidence * 100
                    conf_color = "green" if conf_pct >= 80 else "orange" if conf_pct >= 50 else "red"
                    st.markdown(f"**Confidence:** :{conf_color}[{conf_pct:.0f}%]")
                    
                    # Evidence table
                    if answer.evidence:
                        st.markdown("### 📋 Evidence")
                        df = pd.DataFrame(answer.evidence)
                        st.dataframe(df, use_container_width=True)
                    
                    # Explanation
                    with st.expander("ℹ️ Explanation"):
                        st.info(answer.explanation)
                    
                    # SQL Query
                    if answer.sql_query:
                        with st.expander("🔍 SQL Query"):
                            st.code(answer.sql_query, language="sql")
                    
                    # Limitations
                    if answer.limitations:
                        with st.expander("⚠️ Limitations & Warnings"):
                            for lim in answer.limitations:
                                st.warning(lim)
                    
                    # Metadata
                    with st.expander("📊 Metadata"):
                        col1, col2, col3 = st.columns(3)
                        # Safe access to metadata
                        row_count = answer.metadata.get('row_count', 0) if answer.metadata else 0
                        exec_time = answer.metadata.get('execution_time_ms', 0) if answer.metadata else 0
                        tables = answer.metadata.get('tables_used', []) if answer.metadata else []
                        
                        col1.metric("Rows", row_count)
                        col2.metric("Execution Time", f"{exec_time:.0f}ms")
                        col3.metric("Tables Used", len(tables))
                
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logging.exception("Error processing question")
    
    with tab2:
        st.header("📊 Database Schema")
        
        try:
            schema_summary = agent.get_schema_summary()
            st.text(schema_summary)
        except Exception as e:
            st.error(f"Error loading schema: {e}")
    
    with tab3:
        st.header("🔍 Data Quality Report")
        
        try:
            quality_summary = agent.get_quality_summary()
            st.text(quality_summary)
        except Exception as e:
            st.error(f"Error loading quality report: {e}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "Built with ❤️ using Streamlit | "
        f"Database: {st.session_state.get('db_path', 'Not loaded')}"
    )


if __name__ == "__main__":
    main()
