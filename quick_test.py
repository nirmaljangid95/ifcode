"""Quick test of Ollama connection"""
import sys

try:
    import ollama
    print("✓ Ollama library imported")
    
    # Test connection
    print("\nTesting Ollama connection...")
    response = ollama.chat(
        model='llama3.2:3b',
        messages=[{'role': 'user', 'content': 'Say OK'}],
        options={'num_predict': 5}
    )
    
    print("✓ Ollama is working!")
    print(f"Response: {response['message']['content']}")
    
except ImportError:
    print("✗ Ollama library not installed")
    print("Run: pip install ollama")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nMake sure:")
    print("1. Ollama is running: ollama serve")
    print("2. Model is downloaded: ollama pull llama3.2:3b")
    sys.exit(1)
