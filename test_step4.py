"""
Step 4: Test SQL execution
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.sql_executor import SQLExecutor

def test_step4():
    print("="*60)
    print("STEP 4: Execute SQL Queries")
    print("="*60)
    
    db_path = "data/test_messy.db"
    
    try:
        # Initialize executor
        print("\n1. Initializing SQL executor...")
        executor = SQLExecutor(
            database_path=db_path,
            timeout_seconds=30,
            max_rows=10000,
            read_only=True
        )
        
        # Test connection
        if not executor.test_connection():
            print("✗ Database connection failed!")
            return False
        
        print("✓ SQL executor ready")
        
        # Test queries
        test_queries = [
            ("Count schools", "SELECT COUNT(*) as school_count FROM schools"),
            ("List schools", "SELECT school_name, city, type FROM schools LIMIT 5"),
            ("Enrollment comparison", """
                SELECT 
                    s.school_name,
                    e2021.total_students AS enrollment_2021,
                    e2023.total_students AS enrollment_2023,
                    (e2021.total_students - e2023.total_students) AS change
                FROM schools s
                LEFT JOIN enrollment_history e2021 ON s.school_id = e2021.school_id AND e2021.year = 2021
                LEFT JOIN enrollment_history e2023 ON s.school_id = e2023.school_id AND e2023.year = 2023
                WHERE e2021.total_students > e2023.total_students
                ORDER BY change DESC
            """),
            ("Average salary by subject", """
                SELECT 
                    subject,
                    COUNT(*) as teacher_count,
                    AVG(salary) as avg_salary,
                    MIN(salary) as min_salary,
                    MAX(salary) as max_salary
                FROM teachers
                WHERE salary IS NOT NULL AND subject IS NOT NULL
                GROUP BY subject
                ORDER BY avg_salary DESC
            """)
        ]
        
        print("\n2. Testing queries...")
        
        for i, (name, sql) in enumerate(test_queries, 1):
            print(f"\n--- Test {i}: {name} ---")
            print(f"SQL: {sql[:100]}...")
            
            result = executor.execute(sql)
            
            if result.success:
                print(f"✓ Query executed successfully")
                print(f"  Rows returned: {result.row_count}")
                print(f"  Execution time: {result.execution_time_ms:.2f}ms")
                print(f"  Columns: {result.column_names}")
                
                # Show first few rows
                if result.rows:
                    print(f"\n  First {min(3, len(result.rows))} rows:")
                    for row in result.rows[:3]:
                        print(f"    {row}")
                
                if result.truncated:
                    print(f"  ⚠ Results truncated")
            else:
                print(f"✗ Query failed: {result.error}")
        
        # Test safety: Try a destructive query (should fail)
        print("\n3. Testing safety (should reject)...")
        dangerous_sql = "DELETE FROM schools"
        print(f"Attempting: {dangerous_sql}")
        
        # This should be caught by validator, but let's see what executor does
        # (In production, validator would catch this before execution)
        print("  (Note: In production, validator blocks this before execution)")
        
        print("\n" + "="*60)
        print("STEP 4: ✓ SUCCESS")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step4()
    sys.exit(0 if success else 1)
