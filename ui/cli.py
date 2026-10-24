"""
Command-line interface for the Data Analyst Agent.
"""

import sys
import logging
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import DataAnalystAgent
from src.models.llm_client import LLMClient

console = Console()


def setup_logging(log_level: str):
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler('logs/agent.log'), logging.StreamHandler()]
    )


@click.group()
def cli():
    """Data Analyst Agent - Answer questions about your database using AI."""
    pass


@cli.command()
@click.option('--db', required=True, help='Path to SQLite database')
@click.option('--question', required=True, help='Natural language question')
@click.option('--llm-provider', default='ollama', help='LLM provider (ollama, openai)')
@click.option('--llm-model', default='llama3.2:3b', help='LLM model name')
@click.option('--log-level', default='INFO', help='Logging level')
@click.option('--show-schema', is_flag=True, help='Show database schema before answering')
@click.option('--show-quality', is_flag=True, help='Show data quality report')
def ask(db, question, llm_provider, llm_model, log_level, show_schema, show_quality):
    """Ask a question about the database."""
    
    setup_logging(log_level)
    load_dotenv()
    
    console.print(Panel.fit(
        "[bold blue]Data Analyst Agent[/bold blue]\n"
        f"Database: {db}\n"
        f"Model: {llm_provider}/{llm_model}",
        border_style="blue"
    ))
    
    try:
        # Initialize LLM client
        console.print("\n[yellow]Initializing LLM client...[/yellow]")
        llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            base_url=os.getenv('LLM_BASE_URL'),
            api_key=os.getenv('LLM_API_KEY')
        )
        
        # Test connection
        if not llm_client.test_connection():
            console.print("[red]✗[/red] LLM connection failed!")
            console.print(f"\nMake sure {llm_provider} is running and accessible.")
            if llm_provider == 'ollama':
                console.print("Start Ollama with: ollama serve")
                console.print(f"Pull model with: ollama pull {llm_model}")
            sys.exit(1)
        
        console.print("[green]✓[/green] LLM connection successful")
        
        # Initialize agent
        console.print("[yellow]Initializing agent...[/yellow]")
        agent = DataAnalystAgent(
            database_path=db,
            llm_client=llm_client,
            max_retry_attempts=2,
            enable_validation=True
        )
        
        # Test database connection
        if not agent.test_connection():
            console.print("[red]✗[/red] Database connection failed!")
            sys.exit(1)
        
        console.print("[green]✓[/green] Database connection successful")
        
        # Initialize (inspect schema and check quality)
        console.print("[yellow]Analyzing database...[/yellow]")
        agent.initialize()
        console.print("[green]✓[/green] Database analysis complete")
        
        # Show schema if requested
        if show_schema:
            console.print("\n" + "="*60)
            console.print("[bold]DATABASE SCHEMA[/bold]")
            console.print("="*60)
            schema_summary = agent.get_schema_summary()
            console.print(schema_summary)
        
        # Show quality report if requested
        if show_quality:
            console.print("\n" + "="*60)
            console.print("[bold]DATA QUALITY REPORT[/bold]")
            console.print("="*60)
            quality_summary = agent.get_quality_summary()
            console.print(quality_summary)
        
        # Ask question
        console.print(f"\n[bold cyan]Question:[/bold cyan] {question}\n")
        console.print("[yellow]Generating answer...[/yellow]")
        
        answer = agent.ask(question)
        
        # Display answer
        console.print("\n" + "="*60)
        console.print("[bold green]ANSWER[/bold green]")
        console.print("="*60)
        console.print(Markdown(answer.answer))
        
        # Display evidence table
        if answer.evidence:
            console.print("\n[bold]EVIDENCE[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            
            # Add columns
            for col_name in answer.evidence[0].keys():
                table.add_column(col_name)
            
            # Add rows
            for row in answer.evidence[:20]:  # Limit to 20 rows in CLI
                table.add_row(*[str(v) if v is not None else "NULL" for v in row.values()])
            
            console.print(table)
            
            if len(answer.evidence) > 20:
                console.print(f"\n[dim]... and {len(answer.evidence) - 20} more rows[/dim]")
        
        # Display explanation
        console.print(f"\n[bold]EXPLANATION[/bold]")
        console.print(answer.explanation)
        
        # Display confidence
        conf_pct = answer.confidence * 100
        conf_color = "green" if conf_pct >= 80 else "yellow" if conf_pct >= 50 else "red"
        console.print(f"\n[bold]Confidence:[/bold] [{conf_color}]{conf_pct:.0f}%[/{conf_color}]")
        
        # Display limitations
        if answer.limitations:
            console.print(f"\n[bold yellow]⚠ LIMITATIONS & WARNINGS[/bold yellow]")
            for lim in answer.limitations:
                console.print(f"  • {lim}")
        
        # Display SQL
        if answer.sql_query:
            console.print(f"\n[bold]SQL QUERY[/bold]")
            console.print(Panel(answer.sql_query, border_style="dim"))
        
        # Display metadata
        console.print(f"\n[dim]Execution time: {answer.metadata['execution_time_ms']:.0f}ms | "
                     f"Rows: {answer.metadata['row_count']} | "
                     f"Tables: {', '.join(answer.metadata['tables_used'])}[/dim]")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logging.exception("Error in CLI")
        sys.exit(1)


@cli.command()
@click.option('--db', required=True, help='Path to SQLite database')
@click.option('--llm-provider', default='ollama', help='LLM provider')
@click.option('--llm-model', default='llama3.2:3b', help='LLM model name')
def inspect(db, llm_provider, llm_model):
    """Inspect database schema and data quality."""
    
    setup_logging('INFO')
    load_dotenv()
    
    console.print(Panel.fit(
        "[bold blue]Database Inspector[/bold blue]\n"
        f"Database: {db}",
        border_style="blue"
    ))
    
    try:
        # Initialize LLM client (needed for agent)
        llm_client = LLMClient(provider=llm_provider, model=llm_model)
        
        # Initialize agent
        agent = DataAnalystAgent(database_path=db, llm_client=llm_client)
        agent.initialize()
        
        # Show schema
        console.print("\n" + "="*60)
        console.print("[bold]DATABASE SCHEMA[/bold]")
        console.print("="*60)
        console.print(agent.get_schema_summary())
        
        # Show quality report
        console.print("\n" + "="*60)
        console.print("[bold]DATA QUALITY REPORT[/bold]")
        console.print("="*60)
        console.print(agent.get_quality_summary())
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--llm-provider', default='ollama', help='LLM provider')
@click.option('--llm-model', default='llama3.2:3b', help='LLM model')
def test(llm_provider, llm_model):
    """Test LLM connection."""
    
    load_dotenv()
    
    console.print(Panel.fit(
        f"[bold blue]Testing LLM Connection[/bold blue]\n"
        f"Provider: {llm_provider}\n"
        f"Model: {llm_model}",
        border_style="blue"
    ))
    
    try:
        llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            base_url=os.getenv('LLM_BASE_URL'),
            api_key=os.getenv('LLM_API_KEY')
        )
        
        console.print("\n[yellow]Testing connection...[/yellow]")
        
        if llm_client.test_connection():
            console.print("[green]✓ Connection successful![/green]")
            
            # Try a simple generation
            console.print("\n[yellow]Testing generation...[/yellow]")
            response = llm_client.generate(
                prompt="What is 2+2? Answer with just the number.",
                temperature=0.0,
                max_tokens=10
            )
            
            if response.success:
                console.print(f"[green]✓ Generation successful![/green]")
                console.print(f"\nResponse: {response.content}")
            else:
                console.print(f"[red]✗ Generation failed: {response.error}[/red]")
        else:
            console.print("[red]✗ Connection failed![/red]")
            
            if llm_provider == 'ollama':
                console.print("\n[yellow]Troubleshooting tips:[/yellow]")
                console.print("1. Make sure Ollama is running: ollama serve")
                console.print(f"2. Pull the model: ollama pull {llm_model}")
                console.print("3. Test manually: ollama run " + llm_model)
    
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    cli()
