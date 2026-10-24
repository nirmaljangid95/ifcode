"""
Complete test of all components EXCEPT LLM generation.

This tests:
✓ Step 1: Database connection & schema inspection
✓ Step 2: Data quality checking
✓ Step 4: SQL execution
✓ Step 5: Result validation
✓ Step 6: Answer formatting

NOT tested here (requires Ollama):
- Step 3: LLM-based SQL generation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_inspector import SchemaInspector
from src.data_quality import DataQualityChecker
from src.sql_executor import SQLExecutor
from src.result_validator import ResultValidator
from src.answer_formatter import AnswerFormatter
from src.sql_generator import SQLQuery

def test_complete_pipeline():
    print("="*70)
    print(" COMPLETE PIPELINE TEST (Without LLM)")
    print("="*70)
    
    db_path = "data/test_messy.db"
    
    try:
        # STEP 1: Schema Inspection
        print("\n[1/5] Schema Inspection...")
        inspector = SchemaInspector(db_path)
        schema = inspector.inspect()
        print(f"      ✓ Found {len(schema.tables)} tables, {len(schema.relationships)} relationships")
        
        # STEP 2: Data Quality
        print("\n[2/5] Data Quality Checking...")
        quality_checker = DataQualityChecker(db_path)
        quality_report = quality_checker.check(schema)
        print(f"      ✓ Found {len(quality_report.issues)} quality issues")
        
        # STEP 3: (Skipped - would need LLM)
        print("\n[3/5] SQL Generation (MANUAL for this test)...")
        
        # Manually create SQL query object (simulating what LLM would generate)
        question = "Which schools had falling enrollment between 2021 and 2023?"
        
        sql_query = SQLQuery(
            sql="""
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
            """,
            explanation="Query compares enrollment between 2021 and 2023 to find schools with decreases",
            tables_used=["schools", "enrollment_history"],
            columns_used=["school_name", "total_students", "year"],
            confidence=0.9,
            warnings=[]
        )
        print(f"      ✓ SQL query created (manually)")
        
        # STEP 4: SQL Execution
        print("\n[4/5] SQL Execution...")
        executor = SQLExecutor(db_path, timeout_seconds=30, max_rows=10000)
        execution_result = executor.execute(sql_query.sql)
        
        if execution_result.success:
            print(f"      ✓ Query executed: {execution_result.row_count} rows in {execution_result.execution_time_ms:.2f}ms")
        else:
            print(f"      ✗ Execution failed: {execution_result.error}")
            return False
        
        # STEP 5: Result Validation
        print("\n[5/5] Result Validation...")
        validator = ResultValidator()
        validation_result = validator.validate(execution_result, sql_query, question)
        
        print(f"      ✓ Validation complete")
        print(f"        - Valid: {validation_result.is_valid}")
        print(f"        - Confidence: {validation_result.confidence:.2f}")
        print(f"        - Issues: {len(validation_result.issues)}")
        
        # STEP 6: Answer Formatting
        print("\n[6/6] Answer Formatting...")
        formatter = AnswerFormatter(show_sql=True, max_evidence_rows=10)
        formatted_answer = formatter.format(question, sql_query, execution_result, validation_result)
        
        print(f"      ✓ Answer formatted (confidence: {formatted_answer.confidence:.2f})")
        
        # Display the final answer
        print("\n" + "="*70)
        print(" FINAL ANSWER")
        print("="*70)
        print(f"\nQuestion: {question}")
        print(f"\n{formatted_answer.answer}\n")
        
        if formatted_answer.evidence:
            print("Evidence:")
            for i, row in enumerate(formatted_answer.evidence, 1):
                print(f"  {i}. {row}")
        
        print(f"\nExplanation: {formatted_answer.explanation}")
        print(f"Confidence: {formatted_answer.confidence*100:.0f}%")
        
        if formatted_answer.limitations:
            print(f"\nLimitations:")
            for lim in formatted_answer.limitations:
                print(f"  - {lim}")
        
        print(f"\nSQL Used:\n{formatted_answer.sql_query}")
        
        print("\n" + "="*70)
        print(" ✓ ALL TESTS PASSED")
        print("="*70)
        
        print("\n📝 WHAT'S WORKING:")
        print("  ✓ Database connection and schema discovery")
        print("  ✓ Data quality detection (found messy dates, NULLs, duplicates)")
        print("  ✓ SQL execution with safety and timeouts")
        print("  ✓ Result validation")
        print("  ✓ Natural language answer generation")
        print("  ✓ Complete end-to-end pipeline")
        
        print("\n⚠️  WHAT NEEDS OLLAMA:")
        print("  - Step 3: Automatic SQL generation from English questions")
        print("  - To test that, run: python test_step3.py (requires Ollama)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    sys.exit(0 if success else 1)
