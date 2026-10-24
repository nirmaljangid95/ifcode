"""
Step 3: Test SQL generation with LLM
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_inspector import SchemaInspector
from src.data_quality import DataQualityChecker
from src.sql_generator import SQLGenerator
from src.models.llm_client import LLMClient

def test_step3():
    print("="*60)
    print("STEP 3: Convert English to SQL")
    print("="*60)
    
    db_path = "data/test_messy.db"
    
    try:
        # Setup
        print("\n1. Loading schema and quality data...")
        inspector = SchemaInspector(db_path)
        schema = inspector.inspect()
        
        quality_checker = DataQualityChecker(db_path)
        quality_report = quality_checker.check(schema)
        print("✓ Context loaded")
        
        # Initialize LLM
        print("\n2. Connecting to LLM (Ollama)...")
        llm_client = LLMClient(
            provider="ollama",
            model="llama3.2:3b",
            base_url="http://localhost:11434"
        )
        
        # Test connection
        if not llm_client.test_connection():
            print("✗ Ollama is not running!")
            print("\nTo start Ollama:")
            print("  1. Open a new terminal")
            print("  2. Run: ollama serve")
            print("  3. Make sure the model is available: ollama pull llama3.2:3b")
            return False
        
        print("✓ LLM connected")
        
        # Create SQL generator
        print("\n3. Initializing SQL generator...")
        sql_generator = SQLGenerator(
            llm_client=llm_client,
            schema=schema,
            quality_report=quality_report
        )
        print("✓ SQL generator ready")
        
        # Test questions
        test_questions = [
            "How many schools are there?",
            "Which schools had falling enrollment between 2021 and 2023?",
            "What is the average teacher salary by subject?"
        ]
        
        print("\n4. Testing SQL generation...")
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- Question {i} ---")
            print(f"Q: {question}")
            
            try:
                sql_query = sql_generator.generate(question)
                
                print(f"\nGenerated SQL:")
                print(sql_query.sql)
                print(f"\nExplanation: {sql_query.explanation}")
                print(f"Confidence: {sql_query.confidence:.2f}")
                print(f"Tables used: {sql_query.tables_used}")
                
                if sql_query.warnings:
                    print(f"Warnings: {sql_query.warnings}")
                
                print("✓ SQL generated successfully")
                
            except Exception as e:
                print(f"✗ Failed to generate SQL: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "="*60)
        print("STEP 3: ✓ SUCCESS")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_step3()
    sys.exit(0 if success else 1)
