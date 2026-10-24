"""
Setup script for Data Analyst Agent.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and print status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=False)
    
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    else:
        print(f"✅ Success: {description}")
        return True


def main():
    """Setup the Data Analyst Agent project."""
    
    print("""
╔══════════════════════════════════════════════════════════╗
║       Data Analyst Agent - Setup Script                 ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    project_root = Path(__file__).parent
    
    # Create necessary directories
    print("\n📁 Creating directories...")
    directories = ['data', 'logs', 'evaluation']
    for directory in directories:
        (project_root / directory).mkdir(exist_ok=True)
        print(f"   Created: {directory}/")
    
    # Create .env file if it doesn't exist
    env_file = project_root / '.env'
    if not env_file.exists():
        print("\n📝 Creating .env file...")
        env_example = project_root / '.env.example'
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("   Created .env from .env.example")
            print("   ⚠️  Please edit .env with your configuration")
        else:
            print("   ⚠️  .env.example not found, skipping")
    
    # Install dependencies
    print("\n📦 Installing Python dependencies...")
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing requirements"
    ):
        print("\n❌ Failed to install dependencies")
        return False
    
    # Create test database
    print("\n🗄️  Creating test database...")
    if not run_command(
        f"{sys.executable} scripts/create_test_db.py",
        "Creating test database"
    ):
        print("\n⚠️  Warning: Could not create test database")
        print("   You can create it later by running:")
        print("   python scripts/create_test_db.py")
    
    # Check if Ollama is available
    print("\n🤖 Checking LLM availability...")
    result = subprocess.run("ollama --version", shell=True, capture_output=True)
    
    if result.returncode == 0:
        print("   ✅ Ollama is installed")
        
        # Check if model is available
        result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
        if "llama3.2:3b" in result.stdout or "llama3.2" in result.stdout:
            print("   ✅ llama3.2:3b model is available")
        else:
            print("   ⚠️  llama3.2:3b model not found")
            print("\n   To install the model, run:")
            print("   ollama pull llama3.2:3b")
    else:
        print("   ⚠️  Ollama not found")
        print("\n   Install Ollama from: https://ollama.ai/download")
        print("   Then run: ollama pull llama3.2:3b")
    
    # Print completion message
    print(f"\n{'='*60}")
    print("✅ Setup Complete!")
    print(f"{'='*60}\n")
    
    print("Next steps:")
    print("  1. Make sure Ollama is running: ollama serve")
    print("  2. Test the CLI:")
    print('     python ui/cli.py test')
    print("  3. Try asking a question:")
    print('     python ui/cli.py ask --db data/test_messy.db --question "How many schools are there?"')
    print("  4. Or start the web interface:")
    print("     streamlit run ui/streamlit_app.py")
    print("\n")


if __name__ == "__main__":
    main()
