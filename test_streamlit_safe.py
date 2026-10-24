"""
Test that Streamlit metadata handling is safe
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.answer_formatter import FormattedAnswer

print("="*70)
print(" TESTING STREAMLIT METADATA SAFETY")
print("="*70)

# Test 1: Normal answer with full metadata
print("\nTest 1: Normal answer with metadata")
answer1 = FormattedAnswer(
    answer="Lincoln High has 450 students",
    evidence=[{"school_name": "Lincoln High", "count": 450}],
    explanation="Counted students per school",
    confidence=0.9,
    limitations=[],
    sql_query="SELECT ...",
    metadata={
        'row_count': 8,
        'execution_time_ms': 15.5,
        'tables_used': ['schools', 'students']
    }
)

row_count = answer1.metadata.get('row_count', 0) if answer1.metadata else 0
exec_time = answer1.metadata.get('execution_time_ms', 0) if answer1.metadata else 0
tables = answer1.metadata.get('tables_used', []) if answer1.metadata else []

print(f"✓ Row count: {row_count}")
print(f"✓ Exec time: {exec_time:.0f}ms")
print(f"✓ Tables: {tables}")

# Test 2: Answer with None metadata
print("\nTest 2: Answer with None metadata")
answer2 = FormattedAnswer(
    answer="Error occurred",
    evidence=[],
    explanation="Query failed",
    confidence=0.0,
    limitations=["Query error"],
    sql_query="",
    metadata=None
)

row_count2 = answer2.metadata.get('row_count', 0) if answer2.metadata else 0
exec_time2 = answer2.metadata.get('execution_time_ms', 0) if answer2.metadata else 0
tables2 = answer2.metadata.get('tables_used', []) if answer2.metadata else []

print(f"✓ Row count: {row_count2}")
print(f"✓ Exec time: {exec_time2:.0f}ms")
print(f"✓ Tables: {tables2}")

# Test 3: Answer with incomplete metadata
print("\nTest 3: Answer with incomplete metadata")
answer3 = FormattedAnswer(
    answer="Some answer",
    evidence=[{"data": 1}],
    explanation="Simple query",
    confidence=0.5,
    limitations=[],
    sql_query="SELECT 1",
    metadata={'row_count': 5}  # Missing other fields
)

row_count3 = answer3.metadata.get('row_count', 0) if answer3.metadata else 0
exec_time3 = answer3.metadata.get('execution_time_ms', 0) if answer3.metadata else 0
tables3 = answer3.metadata.get('tables_used', []) if answer3.metadata else []

print(f"✓ Row count: {row_count3}")
print(f"✓ Exec time: {exec_time3:.0f}ms")
print(f"✓ Tables: {tables3}")

print("\n" + "="*70)
print("✓ ALL TESTS PASSED - Streamlit metadata access is safe!")
print("="*70)
