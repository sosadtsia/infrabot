#!/usr/bin/env python3
"""
Example script showing how to use Infrabot programmatically
"""

import sys
sys.path.append('.')

from core.infrabot import InfraBot
from utils.ollama_client import OllamaClient

def main():
    """Example of using InfraBot programmatically"""

    # Check if Ollama is available
    ollama = OllamaClient()
    health = ollama.health_check()

    print("🔍 Ollama Health Check:")
    print(f"  Service Running: {health['service_running']}")
    print(f"  Model Available: {health['model_available']}")
    print(f"  Response Test: {health['response_test']}")

    if not health['service_running']:
        print("❌ Ollama is not running. Please start it with: ollama serve")
        return

    if not health['model_available']:
        print("❌ Model not found. Please install it with: ollama pull deepseek-coder")
        return

    # Initialize InfraBot
    bot = InfraBot(verbose=True)

    # Example tasks
    tasks = [
        "Check system uptime on localhost",
        "Show disk usage on localhost",
        "List running services on localhost"
    ]

    print(f"\n🚀 Running {len(tasks)} example tasks:\n")

    for i, task in enumerate(tasks, 1):
        print(f"📋 Task {i}: {task}")
        result = bot.execute_task(task)

        if result.get('error'):
            print(f"❌ Failed: {result['error']}")
        else:
            print(f"✅ Completed successfully")

        print("-" * 50)

    # Show memory stats
    stats = bot.memory.get_stats()
    print(f"\n📊 Memory Stats:")
    print(f"  Interactions: {stats['interactions']}")
    print(f"  Playbooks: {stats['playbooks']}")
    print(f"  Results: {stats['results']}")

if __name__ == "__main__":
    main()
