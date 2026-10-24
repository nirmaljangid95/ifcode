"""
Test fixes for JOIN alias issues
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient

print("="*70)
print(" TESTING FIXES")
print("="*70)

# Initialize
llm_client = LLMClient(provider="ollama", model="llama3.2:3b")

if not llm_client.test_connection():
    print("✗ Ollama not running!")
    sys.exit(1)

agent = DataAnalystAgent(
    database_path="data/test_messy.db",
    llm_client=llm_client,
    max_retry_attempts=2
)

agent.initialize()
print("✓ Agent ready\n")

# Test the problematic question
question = "How many students are currently enrolled in each school?"

print(f"Question: {question}")
print("-"*70)

try:
    answer = agent.ask(question)
    
    print(f"\n✓ SUCCESS!")
    print(f"Answer: {answer.answer[:200]}")
    print(f"Confidence: {answer.confidence*100:.0f}%")
    
    if answer.evidence:
        print(f"\nFirst 3 results:")
        for i, row in enumerate(answer.evidence[:3], 1):
            print(f"  {i}. {row}")
    
    print(f"\nMetadata: {answer.metadata}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
