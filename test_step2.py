"""
Step 2: Test data quality inspection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_inspector import SchemaInspector
from src.data_quality import DataQualityChecker

def test_step2():
    print("="*60)
    print("STEP 2: Inspect Messy Data")
    print("="*60)
    
    db_path = "data/test_messy.db"
    
    try:
        # First get schema
        print("\nGetting schema...")
        inspector = SchemaInspector(db_path)
        schema = inspector.inspect()
        print("✓ Schema loaded")
        
        # Check data quality
        print("\nChecking data quality...")
        quality_checker = DataQualityChecker(db_path)
        quality_report = quality_checker.check(schema)
        
        print(f"\n✓ Quality check complete")
        print(f"Total issues found: {len(quality_report.issues)}")
        print(f"  - Critical: {len(quality_report.get_critical_issues())}")
        print(f"  - Warnings: {len(quality_report.get_warnings())}")
        
        # Show critical issues
        if quality_report.get_critical_issues():
            print("\n--- CRITICAL ISSUES ---")
            for issue in quality_report.get_critical_issues()[:5]:
                print(f"\n{issue.severity.upper()}: {issue.issue_type}")
                print(f"  Table: {issue.table}")
                if issue.column:
                    print(f"  Column: {issue.column}")
                print(f"  Description: {issue.description}")
                if issue.sample_values:
                    print(f"  Samples: {issue.sample_values[:3]}")
        
        # Show warnings
        if quality_report.get_warnings():
            print("\n--- WARNINGS ---")
            for issue in quality_report.get_warnings()[:5]:
                print(f"\n{issue.severity.upper()}: {issue.issue_type}")
                print(f"  {issue.description}")
        
        # Print summary
        print("\n" + "="*60)
        print("Data Quality Summary:")
        print("="*60)
        print(quality_checker.get_quality_summary(quality_report))
        
        print("\n" + "="*60)
        print("STEP 2: ✓ SUCCESS")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step2()
    sys.exit(0 if success else 1)
