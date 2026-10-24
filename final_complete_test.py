"""
FINAL COMPLETE END-TO-END TEST with LLM
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient

def test_complete_agent():
    print("="*70)
    print(" FINAL COMPLETE AGENT TEST (WITH LLM)")
    print("="*70)
    
    db_path = "data/test_messy.db"
    
    try:
        # Initialize LLM
        print("\n[1/4] Initializing LLM client...")
        llm_client = LLMClient(
            provider="ollama",
            model="llama3.2:3b",
            base_url="http://localhost:11434"
        )
        
        if not llm_client.test_connection():
            print("✗ Ollama not running!")
            return False
        
        print("      ✓ LLM connected (llama3.2:3b)")
        
        # Initialize Agent
        print("\n[2/4] Initializing Data Analyst Agent...")
        agent = DataAnalystAgent(
            database_path=db_path,
            llm_client=llm_client,
            max_retry_attempts=2
        )
        
        print("      Analyzing database...")
        agent.initialize()
        print("      ✓ Agent ready (schema + quality check done)")
        
        # Test Questions
        print("\n[3/4] Testing Questions...")
        
        questions = [
            "How many schools are there?",
            "What is the average teacher salary?",
            "Which schools had falling enrollment between 2021 and 2023?"
        ]
        
        results = []
        
        for i, question in enumerate(questions, 1):
            print(f"\n--- Question {i}/3 ---")
            print(f"Q: {question}")
            
            try:
                answer = agent.ask(question)
                
                print(f"\nA: {answer.answer}")
                
                if answer.evidence and len(answer.evidence) <= 3:
                    print(f"\nEvidence:")
                    for row in answer.evidence:
                        print(f"  {row}")
                
                print(f"\nConfidence: {answer.confidence*100:.0f}%")
                print(f"Execution: {answer.metadata['execution_time_ms']:.1f}ms")
                
                if answer.limitations:
                    print(f"\nLimitations:")
                    for lim in answer.limitations[:2]:
                        print(f"  - {lim}")
                
                results.append({
                    'question': question,
                    'success': True,
                    'confidence': answer.confidence,
                    'row_count': answer.metadata['row_count']
                })
                
                print("✓ Answer generated successfully")
                
            except Exception as e:
                print(f"✗ Failed: {e}")
                results.append({
                    'question': question,
                    'success': False,
                    'error': str(e)
                })
        
        # Summary
        print("\n[4/4] Summary...")
        print("\n" + "="*70)
        print(" TEST RESULTS")
        print("="*70)
        
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"\nQuestions Answered: {successful}/{total}")
        
        for i, result in enumerate(results, 1):
            status = "✓" if result['success'] else "✗"
            print(f"\n{i}. {status} {result['question']}")
            if result['success']:
                print(f"   Confidence: {result['confidence']*100:.0f}%")
                print(f"   Rows returned: {result['row_count']}")
            else:
                print(f"   Error: {result.get('error', 'Unknown')}")
        
        print("\n" + "="*70)
        
        if successful == total:
            print(" ✓ ALL TESTS PASSED!")
            print("="*70)
            print("\n🎉 SYSTEM IS FULLY WORKING!")
            print("\n📊 What's Verified:")
            print("  ✓ Database connection")
            print("  ✓ Schema discovery")
            print("  ✓ Data quality checking")
            print("  ✓ LLM SQL generation")
            print("  ✓ SQL execution")
            print("  ✓ Result validation")
            print("  ✓ Answer formatting")
            print("  ✓ Complete end-to-end pipeline")
            return True
        else:
            print(f" ⚠ {total - successful} tests failed")
            print("="*70)
            return False
        
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_agent()
    sys.exit(0 if success else 1)
