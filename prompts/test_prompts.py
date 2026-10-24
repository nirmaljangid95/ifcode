"""
Test and preview prompts before using them
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompts.sql_generation_prompts import SQLPrompts, test_prompt_with_question, export_prompts_to_file
from src.schema_inspector import SchemaInspector
from src.data_quality import DataQualityChecker

def main():
    print("="*70)
    print(" PROMPT TESTING TOOL")
    print("="*70)
    
    # Load database
    db_path = "data/test_messy.db"
    print(f"\nLoading database: {db_path}")
    
    try:
        # Get schema
        inspector = SchemaInspector(db_path)
        schema = inspector.inspect()
        print(f"✓ Schema loaded: {len(schema.tables)} tables")
        
        # Get quality report
        quality_checker = DataQualityChecker(db_path)
        quality_report = quality_checker.check(schema)
        print(f"✓ Quality checked: {len(quality_report.issues)} issues")
        
        # Test questions
        test_questions = [
            "How many schools are there?",
            "What is the average teacher salary?",
            "Which schools had falling enrollment between 2021 and 2023?"
        ]
        
        print("\n" + "="*70)
        print(" TESTING PROMPTS WITH SAMPLE QUESTIONS")
        print("="*70)
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{i}. Testing: {question}")
            print("-"*70)
            
            # Build prompts
            schema_text = SQLPrompts.format_schema(schema)
            quality_text = SQLPrompts.format_quality_notes(quality_report)
            
            system_prompt = SQLPrompts.build_system_prompt(schema_text, quality_text)
            user_prompt = SQLPrompts.build_user_prompt(question)
            
            print("\nSYSTEM PROMPT (first 500 chars):")
            print(system_prompt[:500] + "...")
            
            print(f"\nUSER PROMPT:")
            print(user_prompt)
            
            print("\n" + "="*70)
        
        # Export to file
        print("\nExporting all prompts to file...")
        export_prompts_to_file("prompts/all_prompts.txt")
        
        print("\n✓ Test complete!")
        print("\nNext steps:")
        print("1. Review: prompts/all_prompts.txt")
        print("2. Edit: prompts/sql_generation_prompts.py")
        print("3. Test with LLM: python test_improved.py")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
