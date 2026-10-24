"""
Step 1: Test database connection and schema inspection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_inspector import SchemaInspector

def test_step1():
    print("="*60)
    print("STEP 1: Connect to Database and Read Schema")
    print("="*60)
    
    # Connect to test database
    db_path = "data/test_messy.db"
    print(f"\nConnecting to: {db_path}")
    
    try:
        inspector = SchemaInspector(db_path)
        print("✓ Connection successful")
        
        # Inspect schema
        print("\nInspecting database schema...")
        schema = inspector.inspect()
        
        print(f"\n✓ Found {len(schema.tables)} tables")
        
        # Print detailed schema
        for table_name, table_info in schema.tables.items():
            print(f"\n--- Table: {table_name} ---")
            print(f"Rows: {table_info.row_count}")
            print(f"Columns: {len(table_info.columns)}")
            
            for col in table_info.columns:
                pk = " [PK]" if col.primary_key else ""
                nullable = " [NULL]" if col.nullable else " [NOT NULL]"
                print(f"  - {col.name}: {col.data_type}{pk}{nullable}")
                if col.sample_values:
                    print(f"    Samples: {col.sample_values[:3]}")
            
            if table_info.foreign_keys:
                print(f"  Foreign Keys:")
                for fk in table_info.foreign_keys:
                    print(f"    - {fk['column']} -> {fk['references_table']}.{fk['references_column']}")
        
        # Print relationships
        print(f"\n✓ Found {len(schema.relationships)} relationships")
        for rel in schema.relationships:
            print(f"  - {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']} ({rel['type']})")
        
        print("\n" + "="*60)
        print("STEP 1: ✓ SUCCESS")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step1()
    sys.exit(0 if success else 1)
