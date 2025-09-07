#!/usr/bin/env python3
"""
Infrabot - AI-powered DevOps assistant
Automates Ansible tasks and Linux server management using local AI models.
"""

import click
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.infrabot import InfraBot
from utils.ollama_client import OllamaClient

console = Console()

@click.command()
@click.option('--model', '-m', default='deepseek-coder',
              help='Ollama model to use (default: deepseek-coder)')
@click.option('--inventory', '-i',
              help='Path to Ansible inventory file')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
@click.argument('task', required=False)
def main(model, inventory, verbose, task):
    """
    Infrabot - Your AI DevOps Assistant

    Examples:
      infrabot "Update all servers with security patches"
      infrabot --inventory hosts "Install Docker on web servers"
      infrabot --model mistral "Check disk usage across all servers"
    """

    # Display banner
    banner = Text("🛠️  INFRABOT", style="bold cyan")
    subtitle = Text("AI-powered DevOps Assistant", style="dim")
    console.print(Panel.fit(banner + "\n" + subtitle, border_style="cyan"))

    # Initialize Ollama client
    try:
        ollama = OllamaClient(model=model)
        if not ollama.is_available():
            console.print("[red]❌ Ollama is not running or model not found[/red]")
            console.print("[yellow]💡 Try: ollama serve && ollama pull deepseek-coder[/yellow]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to connect to Ollama: {e}[/red]")
        sys.exit(1)

    # Initialize InfraBot
    bot = InfraBot(
        model=model,
        inventory_path=inventory,
        verbose=verbose
    )

    if task:
        # Execute single task
        result = bot.execute_task(task)

        # Show detailed result for single task mode
        if result.get('raw_output'):
            console.print(f"\n[bold green]📋 Infrabot Result:[/bold green]")
            console.print(f"{result['raw_output']}")

        if result.get('error'):
            console.print(f"\n[red]❌ Error: {result['error']}[/red]")

    else:
        # Interactive mode
        bot.interactive_mode()

if __name__ == "__main__":
    main()
