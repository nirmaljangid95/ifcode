"""
Quick test to check if JOIN alias issue is fixed
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_inspector import SchemaInspector
from src.sql_generator import SQLGenerator
from src.models.llm_client import LLMClient

print("="*70)
print(" QUICK JOIN ALIAS TEST")
print("="*70)

# Setup
llm_client = LLMClient(provider="ollama", model="llama3.2:3b", temperature=0.1)

if not llm_client.test_connection():
    print("✗ Ollama not running!")
    sys.exit(1)

inspector = SchemaInspector("data/test_messy.db")
schema = inspector.inspect()

generator = SQLGenerator(llm_client, schema)

# Test question
question = "How many students are currently enrolled in each school?"

print(f"\nQuestion: {question}")
print("-"*70)
print("\nGenerating SQL...\n")

try:
    sql_query = generator.generate(question)
    
    print(f"✓ SQL Generated:")
    print(f"\n{sql_query.sql}\n")
    print(f"Explanation: {sql_query.explanation}")
    print(f"Tables: {sql_query.tables_used}")
    print(f"Confidence: {sql_query.confidence*100:.0f}%")
    
    # Check for the bug
    if "s.school_name" in sql_query.sql and "FROM students s" in sql_query.sql:
        print("\n⚠ BUG STILL EXISTS: Using s.school_name when s = students!")
    elif "sc.school_name" in sql_query.sql or "schools.school_name" in sql_query.sql:
        print("\n✓ BUG FIXED: Using correct table alias/name for school_name!")
    else:
        print("\n? Cannot determine if bug is fixed from this SQL")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
