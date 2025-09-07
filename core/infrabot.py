"""
Core InfraBot class - orchestrates AI agents, memory, and task execution
"""

import tempfile
import subprocess
import platform
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from agents.crew import InfraCrew
from core.memory import BotMemory
from utils.ansible_runner import AnsibleRunner
from utils.ollama_client import OllamaClient

console = Console()

class InfraBot:
    """Main InfraBot orchestrator"""

    def __init__(self, model="deepseek-coder", inventory_path=None, verbose=False):
        self.model = model
        self.inventory_path = inventory_path
        self.verbose = verbose

        # Initialize components
        self.memory = BotMemory()
        self.ollama = OllamaClient(model=model)
        self.crew = InfraCrew(ollama_client=self.ollama, memory=self.memory)
        self.ansible = AnsibleRunner(inventory_path=inventory_path)

        console.print(f"[green]✓ InfraBot initialized with model: {model}[/green]")
        console.print(f"[green]✓ Platform: {platform.system()} {platform.release()}[/green]")

    def execute_task(self, task_description):
        """Execute a single task"""
        console.print(f"\n[bold blue]🎯 Task:[/bold blue] {task_description}")

        try:
            # First check if this is a simple informational query - prioritize direct execution
            simple_keywords = ['time', 'date', 'disk', 'space', 'usage', 'memory', 'uptime', 'status', 'show', 'check', 'get', 'user', 'users', 'list', 'who', 'whoami', 'name', 'current']
            if any(keyword in task_description.lower() for keyword in simple_keywords):
                # For informational queries, execute command directly without AI analysis
                console.print(f"[yellow]ℹ️  Executing query directly...[/yellow]")
                result = self._execute_simple_query(task_description)
                if result.get('success'):  # If we successfully handled the simple query
                    console.print("[green]✅ Task completed successfully[/green]")
                    return result

            # Store task in memory for context
            self.memory.store_interaction("user_request", task_description)

            # Get similar past tasks for context
            context = self.memory.get_context(task_description, limit=3)
            if context and self.verbose:
                console.print(f"[dim]📚 Found {len(context)} similar past tasks[/dim]")

            # Execute with crew for complex automation tasks
            with Live(Spinner('dots', text='🤖 AI agents analyzing task...'), console=console):
                result = self.crew.execute_task(task_description, context)

            # Display the AI agent output
            if result.get('raw_output') and self.verbose:
                console.print(f"[dim]🤖 AI Agent Output:[/dim]")
                console.print(f"[dim]{result['raw_output'][:1000]}...[/dim]" if len(result['raw_output']) > 1000 else f"[dim]{result['raw_output']}[/dim]")

            # Execute playbooks for complex automation tasks
            if result.get('playbook_content'):
                # Only execute playbooks for complex automation tasks
                self._execute_playbook(result['playbook_content'], task_description)
            elif result.get('raw_output'):
                # Show summary of what the agents determined
                console.print(f"[blue]📋 Result:[/blue] {result['raw_output'][:200]}..." if len(result['raw_output']) > 200 else f"[blue]📋 Result:[/blue] {result['raw_output']}")

            # Store results
            self.memory.store_interaction("task_result", result)

            console.print("[green]✅ Task completed successfully[/green]")
            return result

        except Exception as e:
            error_msg = f"Failed to execute task: {str(e)}"
            console.print(f"[red]❌ {error_msg}[/red]")
            self.memory.store_interaction("error", error_msg)
            return {"error": error_msg}

    def _execute_playbook(self, playbook_content, task_description):
        """Execute an Ansible playbook"""
        console.print("\n[yellow]📋 Executing Ansible playbook...[/yellow]")

        if self.verbose:
            console.print(f"[dim]Generated playbook:\n{playbook_content}[/dim]")

        # Create temporary playbook file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(playbook_content)
            playbook_path = f.name

        try:
            # Execute with ansible-runner
            result = self.ansible.run_playbook(playbook_path)

            if result['success']:
                console.print("[green]✅ Ansible playbook executed successfully[/green]")
            else:
                console.print(f"[red]❌ Ansible playbook failed: {result['error']}[/red]")

            # Store execution results
            self.memory.store_playbook_execution(task_description, playbook_content, result)

        finally:
            # Clean up temporary file
            Path(playbook_path).unlink(missing_ok=True)

    def _get_os_commands(self):
        """Get OS-specific command mappings"""
        system = platform.system()

        if system == "Darwin":  # macOS
            return {
                'time': 'date',
                'date': 'date',
                'disk': 'df -h',
                'disk space': 'df -h',
                'disk usage': 'df -h',
                'memory': 'vm_stat | head -10',
                'memory usage': 'vm_stat | head -10',
                'ram': 'vm_stat | head -10',
                'uptime': 'uptime',
                'load': 'uptime',
                'status': 'uptime && df -h && vm_stat | head -5',
                'system': 'uptime && df -h && vm_stat | head -5',
                'processes': 'ps aux | head -10',
                'cpu': 'top -l1 -s0 | head -15',
                'cpu usage': 'top -l1 -s0 | head -15',
                'user': 'whoami',
                'user name': 'whoami',
                'current user': 'whoami',
                'users': 'dscl . list /Users | grep -v ^_',
                'list users': 'dscl . list /Users | grep -v ^_',
                'local users': 'dscl . list /Users | grep -v ^_'
            }
        elif system == "Linux":  # Linux
            return {
                'time': 'date',
                'date': 'date',
                'disk': 'df -h',
                'disk space': 'df -h',
                'disk usage': 'df -h',
                'memory': 'free -h',
                'memory usage': 'free -h',
                'ram': 'free -h',
                'uptime': 'uptime',
                'load': 'uptime',
                'status': 'uptime && free -h && df -h',
                'system': 'uptime && free -h && df -h',
                'processes': 'ps aux | head -10',
                'cpu': 'top -bn1 | head -20',
                'cpu usage': 'top -bn1 | head -20',
                'user': 'whoami',
                'user name': 'whoami',
                'current user': 'whoami',
                'users': 'cut -d: -f1 /etc/passwd | grep -v ^# | sort',
                'list users': 'cut -d: -f1 /etc/passwd | grep -v ^# | sort',
                'local users': 'cut -d: -f1 /etc/passwd | grep -v ^# | sort'
            }
        else:  # Windows or other systems - basic commands
            return {
                'time': 'date' if system != "Windows" else 'echo %date% %time%',
                'date': 'date' if system != "Windows" else 'echo %date% %time%',
                'disk': 'df -h' if system != "Windows" else 'dir C:',
                'disk space': 'df -h' if system != "Windows" else 'dir C:',
                'disk usage': 'df -h' if system != "Windows" else 'dir C:',
                'memory': 'echo "Memory info not available on this platform"',
                'memory usage': 'echo "Memory info not available on this platform"',
                'ram': 'echo "Memory info not available on this platform"',
                'uptime': 'uptime' if system != "Windows" else 'systeminfo | findstr "Boot Time"',
                'load': 'uptime' if system != "Windows" else 'systeminfo | findstr "Boot Time"',
                'status': 'echo "System status not fully supported on this platform"',
                'system': 'echo "System info not fully supported on this platform"',
                'processes': 'ps aux | head -10' if system != "Windows" else 'tasklist /FI "STATUS eq RUNNING"',
                'cpu': 'echo "CPU info not available on this platform"',
                'cpu usage': 'echo "CPU info not available on this platform"',
                'user': 'whoami' if system != "Windows" else 'echo %username%',
                'user name': 'whoami' if system != "Windows" else 'echo %username%',
                'current user': 'whoami' if system != "Windows" else 'echo %username%',
                'users': 'echo "User listing not available on this platform"',
                'list users': 'echo "User listing not available on this platform"',
                'local users': 'echo "User listing not available on this platform"'
            }

    def _execute_simple_query(self, task_description: str):
        """Execute simple informational queries directly"""
        try:
                        # Get OS-specific command mappings
            query_map = self._get_os_commands()

            # Find matching command - prioritize longer/more specific matches
            command = None
            best_match_length = 0
            task_lower = task_description.lower()

            for keyword, cmd in query_map.items():
                if keyword in task_lower and len(keyword) > best_match_length:
                    command = cmd
                    best_match_length = len(keyword)

            if command:
                ansible_result = self.ansible.run_ad_hoc(
                    hosts="localhost",
                    module="shell",
                    args=command,
                    inventory=self.inventory_path
                )

                if ansible_result.get('success') and ansible_result.get('stdout'):
                    console.print(f"[green]📊 {ansible_result['stdout'].strip()}[/green]")
                    return {"success": True, "output": ansible_result['stdout'], "task": task_description}
                else:
                    console.print(f"[red]❌ Query failed: {ansible_result.get('stderr', 'No output')}[/red]")
                    return {"success": False, "error": ansible_result.get('stderr', 'No output')}
            else:
                console.print("[yellow]ℹ️  No direct command mapping found for this query[/yellow]")
                return {"success": False, "error": "No command mapping found"}

        except Exception as e:
            console.print(f"[red]❌ Failed to execute query: {e}[/red]")
            return {"success": False, "error": str(e)}

    def interactive_mode(self):
        """Run in interactive mode"""
        console.print("\n[bold green]🚀 Interactive mode activated[/bold green]")
        console.print("[dim]Type 'exit' or 'quit' to stop, 'help' for commands[/dim]\n")

        while True:
            try:
                task = Prompt.ask("[bold blue]Infrabot[/bold blue]")

                if task.lower() in ['exit', 'quit', 'q']:
                    console.print("[yellow]👋 Goodbye![/yellow]")
                    break
                elif task.lower() in ['help', 'h']:
                    self._show_help()
                elif task.lower() in ['history']:
                    self._show_history()
                elif task.lower() in ['clear']:
                    console.clear()
                elif task.strip():
                    self.execute_task(task)

            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
            except EOFError:
                break

    def _show_help(self):
        """Show help information"""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]
• help, h      - Show this help
• history      - Show recent task history
• clear        - Clear screen
• exit, quit, q - Exit interactive mode

[bold cyan]Example Tasks:[/bold cyan]
• "Update all Debian servers with security patches"
• "Install Docker on web servers"
• "Check disk usage across all servers"
• "Restart nginx service on production servers"
• "Deploy SSL certificates to web servers"
        """
        console.print(help_text)

    def _show_history(self):
        """Show recent task history"""
        history = self.memory.get_recent_history(limit=10)
        if history:
            console.print("[bold cyan]📜 Recent Tasks:[/bold cyan]")
            for i, item in enumerate(history, 1):
                console.print(f"  {i}. {item.get('content', 'N/A')}")
        else:
            console.print("[dim]No task history found[/dim]")
