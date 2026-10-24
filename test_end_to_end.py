"""
End-to-end test with actual agent to see if any issues remain
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient

print("="*70)
print(" END-TO-END TEST")
print("="*70)

# Initialize
llm_client = LLMClient(provider="ollama", model="llama3.2:3b", temperature=0.1)

if not llm_client.test_connection():
    print("✗ Ollama not running!")
    print("Start with: ollama serve")
    sys.exit(1)

print("✓ Ollama connected")

# Create agent
agent = DataAnalystAgent(
    database_path="data/test_messy.db",
    llm_client=llm_client,
    max_retry_attempts=2
)

agent.initialize()
print("✓ Agent initialized\n")

# Test simple question (should be fast)
questions = [
    "How many schools are there?",
]

for question in questions:
    print(f"\nQuestion: {question}")
    print("-"*70)
    
    try:
        answer = agent.ask(question)
        
        print(f"\n✓ Answer: {answer.answer}")
        print(f"  Confidence: {answer.confidence*100:.0f}%")
        
        # Check metadata
        if answer.metadata:
            print(f"  Metadata:")
            print(f"    - row_count: {answer.metadata.get('row_count', 'MISSING')}")
            print(f"    - execution_time_ms: {answer.metadata.get('execution_time_ms', 'MISSING')}")
            print(f"    - tables_used: {answer.metadata.get('tables_used', 'MISSING')}")
        else:
            print(f"  ⚠ Metadata is None!")
        
        if answer.sql_query:
            print(f"\n  SQL: {answer.sql_query[:100]}...")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print("Test complete")
print("="*70)
