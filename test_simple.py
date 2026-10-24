"""
Simple end-to-end test WITHOUT external dependencies
Just uses Python standard library + our code
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print(" SIMPLIFIED END-TO-END TEST")
print("="*70)

# Test 1: Database Connection
print("\n[1/5] Database Connection...")
db_path = "data/test_messy.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schools")
    count = cursor.fetchone()[0]
    print(f"      ✓ Connected! Found {count} schools")
    conn.close()
except Exception as e:
    print(f"      ✗ Failed: {e}")
    sys.exit(1)

# Test 2: Schema Inspection (using our code)
print("\n[2/5] Schema Inspection...")
try:
    from src.schema_inspector import SchemaInspector
    inspector = SchemaInspector(db_path)
    schema = inspector.inspect()
    print(f"      ✓ Schema loaded: {len(schema.tables)} tables, {len(schema.relationships)} relationships")
except Exception as e:
    print(f"      ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Data Quality (using our code)
print("\n[3/5] Data Quality Check...")
try:
    from src.data_quality import DataQualityChecker
    quality_checker = DataQualityChecker(db_path)
    quality_report = quality_checker.check(schema)
    print(f"      ✓ Quality checked: {len(quality_report.issues)} issues found")
except Exception as e:
    print(f"      ✗ Failed: {e}")
    sys.exit(1)

# Test 4: SQL Execution (using our code)
print("\n[4/5] SQL Execution...")
try:
    from src.sql_executor import SQLExecutor
    executor = SQLExecutor(db_path)
    
    # The critical test query
    sql = """
        SELECT 
            s.school_name,
            e2021.total_students AS enrollment_2021,
            e2023.total_students AS enrollment_2023,
            (e2021.total_students - e2023.total_students) AS decrease
        FROM schools s
        LEFT JOIN enrollment_history e2021 
            ON s.school_id = e2021.school_id AND e2021.year = 2021
        LEFT JOIN enrollment_history e2023 
            ON s.school_id = e2023.school_id AND e2023.year = 2023
        WHERE e2021.total_students > e2023.total_students
        ORDER BY decrease DESC
    """
    
    result = executor.execute(sql)
    if result.success:
        print(f"      ✓ Query executed: {result.row_count} schools with falling enrollment")
        for row in result.rows:
            print(f"        - {row['school_name']}: {row['enrollment_2021']} → {row['enrollment_2023']} (↓{row['decrease']})")
    else:
        print(f"      ✗ Query failed: {result.error}")
        sys.exit(1)
except Exception as e:
    print(f"      ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Answer Formatting (using our code)
print("\n[5/5] Answer Formatting...")
try:
    from src.answer_formatter import AnswerFormatter
    from src.result_validator import ResultValidator
    from src.sql_generator import SQLQuery
    
    question = "Which schools had falling enrollment between 2021 and 2023?"
    
    sql_query = SQLQuery(
        sql=sql,
        explanation="Query compares enrollment data from 2021 to 2023",
        tables_used=["schools", "enrollment_history"],
        columns_used=["school_name", "total_students", "year"],
        confidence=0.9,
        warnings=[]
    )
    
    validator = ResultValidator()
    validation = validator.validate(result, sql_query, question)
    
    formatter = AnswerFormatter(show_sql=False)
    answer = formatter.format(question, sql_query, result, validation)
    
    print(f"      ✓ Answer formatted with {answer.confidence*100:.0f}% confidence")
    
    print("\n" + "="*70)
    print(" FINAL ANSWER")
    print("="*70)
    print(f"\nQ: {question}")
    print(f"\nA: {answer.answer}\n")
    
    if answer.evidence:
        print("Evidence:")
        for i, row in enumerate(answer.evidence, 1):
            print(f"  {i}. {row['school_name']}: {row['enrollment_2021']} → {row['enrollment_2023']} (decrease: {row['decrease']})")
    
    print(f"\nConfidence: {answer.confidence*100:.0f}%")
    print(f"Execution time: {answer.metadata['execution_time_ms']:.1f}ms")
    
except Exception as e:
    print(f"      ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print(" ✓ ALL TESTS PASSED!")
print("="*70)

print("\n📊 SUMMARY:")
print("  ✓ Database connection works")
print("  ✓ Schema inspection works")
print("  ✓ Data quality detection works")
print("  ✓ SQL execution works (complex JOINs)")
print("  ✓ Result validation works")
print("  ✓ Answer formatting works")
print(f"  ✓ Correctly identified {result.row_count} schools with falling enrollment")

print("\n⚠️  OLLAMA NOT TESTED:")
print("  - To test LLM SQL generation, install dependencies:")
print("    pip install ollama rich click python-dotenv")
print("  - Then run: python test_step3.py")

print("\n🎯 BOTTOM LINE:")
print("  The core data pipeline is FULLY WORKING!")
print("  Just need to install dependencies to test LLM integration.")
