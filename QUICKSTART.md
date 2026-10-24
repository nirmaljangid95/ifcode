# Quick Start Guide

## 1. Installation

```powershell
# Navigate to project directory
cd data-analyst-agent

# Install dependencies (Python 3.9+ required)
pip install -r requirements.txt
```

## 2. Setup Ollama (Local LLM)

### Install Ollama

Download and install from: https://ollama.ai/download

### Pull the model

```powershell
ollama pull llama3.2:3b
```

### Start Ollama server

```powershell
ollama serve
```

## 3. Create Test Database

```powershell
python scripts/create_test_db.py
```

This creates `data/test_messy.db` with intentionally messy data to test the agent's capabilities.

## 4. Test the Agent

### Option A: Command Line Interface

```powershell
# Test LLM connection
python ui/cli.py test

# Inspect database
python ui/cli.py inspect --db data/test_messy.db

# Ask a question
python ui/cli.py ask --db data/test_messy.db --question "Which schools had falling enrollment between 2021 and 2023?"
```

###  Option B: Web Interface

```powershell
streamlit run ui/streamlit_app.py
```

Then open your browser to http://localhost:8501

## 5. Example Questions

Try asking these questions about the test database:

1. **Enrollment trends**
   - "Which schools had falling enrollment between 2021 and 2023?"
   - "What is the total enrollment across all schools in 2023?"

2. **Teacher analytics**
   - "What is the average teacher salary by subject?"
   - "Which school has the most teachers?"
   - "How many teachers teach Math?"

3. **Basic counts**
   - "How many schools are in District 1?"
   - "How many students are currently enrolled in each school?"
   - "What types of schools are in the database?"

4. **Aggregations**
   - "What is the average salary for all teachers?"
   - "Show me the top 3 schools by teacher count"

## 6. Using Your Own Database

To use your own SQLite database:

```powershell
python ui/cli.py ask --db path/to/your/database.db --question "Your question here"
```

Or in the Streamlit UI, change the database path in the sidebar.

## Troubleshooting

### Ollama not connecting

```powershell
# Check if Ollama is running
ollama list

# Test the model directly
ollama run llama3.2:3b
```

### Module not found errors

```powershell
# Make sure you're in the project directory
cd data-analyst-agent

# Reinstall dependencies
pip install -r requirements.txt
```

### Database errors

```powershell
# Verify database exists
dir data\test_messy.db

# Recreate if needed
python scripts/create_test_db.py
```

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Run tests: `pytest tests/ -v`
- Try different LLM models by editing `.env`
- Explore the BIRD benchmark evaluation in `evaluation/`

## Architecture Overview

```
User Question → Schema Inspection → Data Quality Check → 
SQL Generation (LLM) → Validation → Execution → 
Result Validation → Natural Language Answer
```

The agent automatically:
- Discovers database schema and relationships
- Detects data quality issues
- Generates safe, read-only SQL
- Validates results
- Retries on errors
- Provides clear answers with evidence
