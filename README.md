# 🛠️ Infrabot

**Infrabot** is a local, AI-powered DevOps assistant that automates **Ansible tasks** and **Linux server management**.
It runs fully offline using **Ollama**, orchestrates tasks with **CrewAI**, and remembers context using **ChromaDB**.

> No APIs. No cloud. Just a self-hosted **AI ops bot** for your servers.

---

## 🚀 Features

- 🤖 **AI agents** (CrewAI) for planning and execution
- 📝 **Ansible playbook generation & execution**
- 🧠 **Local memory** with ChromaDB (remembers past runs, playbooks, logs)
- 🔒 **Fully offline** with Ollama (runs local models like Mistral, DeepSeek-Coder, LLaMA3)
- 🖥️ Works on **macOS** (Apple Silicon) and **Linux**

---

## 📋 Prerequisites

- **Operating System**: macOS (Apple Silicon) or Linux
- **Python**: 3.13 or higher
- **Ansible**: 2.18 or higher
- **RAM**: Minimum 8GB (16GB recommended for larger models)
- **Disk Space**: 10GB+ for models and ChromaDB storage
- **Network**: SSH access to target servers

---

## 📦 Installation

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Clone and setup project
```bash
git clone <your-repo-url>
cd infrabot
```

### 3. Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate.fish && echo "Virtual environment activated: $VIRTUAL_ENV"
pip install -r requirements.txt
```

### 4. Download AI models
```bash
ollama pull deepseek-coder
# Optional: ollama pull mistral
```

---

## 🎯 Usage

### Interactive Mode
```bash
python main.py
```

### Single Task Execution
```bash
python main.py "Update all servers with security patches"
python main.py -i hosts "Install Docker on web servers"
python main.py -v "Check disk usage across all servers"
```

### Programmatic Usage
```bash
python run_example.py  # See example script
```

### Example Interactions

**Security Updates:**
```
User: "Update all Debian servers with latest security patches"
Infrabot:
  - Plans update steps
  - Generates an Ansible playbook
  - Executes it against your inventory
  - Stores logs in memory for next time
  - Returns success message
```

**Package Management:**
```
User: "Install Docker on all Ubuntu servers"
Infrabot:
  - Analyzes current server state
  - Creates Docker installation playbook
  - Handles dependencies and configuration
  - Reports installation status
```

**System Monitoring:**
```
User: "Check disk usage across all servers"
Infrabot:
  - Generates monitoring playbook
  - Collects disk usage data
  - Provides summary report
```

---

## 📁 Project Structure

```
infrabot/
├── main.py              # CLI entry point
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Modern Python packaging
├── run_example.py       # Usage example script
├── core/                # Core bot logic
│   ├── infrabot.py      # Main orchestrator
│   └── memory.py        # ChromaDB memory system
├── agents/              # CrewAI agent definitions
│   └── crew.py          # Planning, execution, and review agents
└── utils/               # Helper utilities
    ├── ollama_client.py # Ollama API wrapper
    └── ansible_runner.py# Ansible execution utilities
```

---

## ⚙️ Configuration

Infrabot works with **any existing Ansible inventory** or defaults to localhost. No configuration files needed in the project.

### Using Your Inventory
```bash
# Use your existing inventory file
python main.py -i /path/to/your/hosts "Install Docker on web servers"

# Use specific inventory
python main.py --inventory production.ini "Update security patches"
```

### Example Inventory Format
```ini
[webservers]
web1.example.com
web2.example.com

[databases]
db1.example.com ansible_user=admin
db2.example.com ansible_user=admin

[all:vars]
ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### Model Selection
```bash
# Use different Ollama model
python main.py --model mistral "Check system status"
```

---

## 🧠 Local Memory

Infrabot stores everything in `~/.infrabot/memory/` using ChromaDB:
- Previous commands and results
- Generated playbooks (for context, not reuse)
- Execution logs and outcomes
- Task patterns and success rates

This enables context-aware operations and continuous improvement over time. The project folder stays clean - no artifacts are stored here.

---

## 🔧 Troubleshooting

### Common Issues

**Ollama not responding:**
```bash
ollama serve  # Start Ollama service
```

**ChromaDB connection errors:**
```bash
rm -rf ~/.infrabot/memory  # Reset memory database
```

**Ansible connection failures:**
- Verify SSH key access to target servers
- Check inventory file format
- Test with `ansible all -m ping`

---

## 🔮 Roadmap

- [ ] Add Git integration for playbook versioning
- [ ] Human approval step before destructive commands
- [ ] Expand inventory awareness
- [ ] TUI / Web UI
- [ ] Multi-cloud support (AWS, Azure, GCP)
- [ ] Real-time monitoring dashboard
- [ ] Rollback capabilities

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support

For questions or issues:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review Ollama and Ansible documentation
