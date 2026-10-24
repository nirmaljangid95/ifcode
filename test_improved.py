"""
Test improved SQL generation with better prompts
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient

def test_improved():
    print("="*70)
    print(" TESTING IMPROVED SQL GENERATION")
    print("="*70)
    
    # Initialize
    print("\nInitializing agent...")
    llm_client = LLMClient(provider="ollama", model="llama3.2:3b")
    
    if not llm_client.test_connection():
        print("✗ Ollama not running!")
        return False
    
    agent = DataAnalystAgent(
        database_path="data/test_messy.db",
        llm_client=llm_client,
        max_retry_attempts=1  # Just 1 retry
    )
    
    agent.initialize()
    print("✓ Agent ready\n")
    
    # Test questions
    questions = [
        ("Simple count", "How many schools are in the database?"),
        ("Simple average", "What is the average teacher salary?"),
        ("Complex comparison", "Which schools had falling enrollment between 2021 and 2023?")
    ]
    
    results = []
    
    for name, question in questions:
        print(f"\n{'='*70}")
        print(f"Test: {name}")
        print(f"Q: {question}")
        print("="*70)
        
        try:
            answer = agent.ask(question)
            
            print(f"\n✓ SUCCESS!")
            print(f"Answer: {answer.answer}")
            
            if answer.evidence and len(answer.evidence) <= 5:
                print(f"\nEvidence (first 5 rows):")
                for i, row in enumerate(answer.evidence[:5], 1):
                    print(f"  {i}. {row}")
            
            print(f"\nConfidence: {answer.confidence*100:.0f}%")
            print(f"Rows: {answer.metadata['row_count']}")
            print(f"Time: {answer.metadata['execution_time_ms']:.1f}ms")
            
            if answer.sql_query:
                print(f"\nSQL: {answer.sql_query[:100]}...")
            
            results.append({'name': name, 'success': True, 'confidence': answer.confidence})
            
        except Exception as e:
            print(f"\n✗ FAILED: {e}")
            results.append({'name': name, 'success': False, 'error': str(e)})
    
    # Summary
    print(f"\n{'='*70}")
    print(" SUMMARY")
    print("="*70)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\nTests Passed: {successful}/{total}")
    
    for r in results:
        status = "✓" if r['success'] else "✗"
        conf = f" ({r['confidence']*100:.0f}%)" if r['success'] else ""
        print(f"  {status} {r['name']}{conf}")
    
    if successful == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("\n✅ SQL GENERATION IS WORKING!")
        return True
    else:
        print(f"\n⚠️  {total - successful} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_improved()
    sys.exit(0 if success else 1)
